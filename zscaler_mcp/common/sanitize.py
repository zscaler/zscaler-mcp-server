"""Output sanitization for tool responses.

Defends against prompt-injection payloads that may have been smuggled
into Zscaler resources by other admins or upstream systems. Free-form
admin-editable fields (rule descriptions, location names, label
descriptions, custom URL category names, etc.) are returned to the AI
agent as-is by the Zscaler APIs. If an attacker — or even a careless
admin — embeds invisible control characters, HTML/Markdown markup, or
fenced code blocks with attacker-controlled info-strings into those
fields, the agent that consumes the tool response can be tricked into
following injected instructions.

Three independent sanitizers are applied to every string that flows
through tool results:

1. **Invisible / control-character stripping** — removes BiDi
   overrides, zero-width spaces, soft hyphens, and other Unicode
   characters that are invisible to humans but parsed by LLMs.
2. **HTML / Markdown sanitization** — strips raw HTML tags (script,
   img, a, iframe, …) and dangerous Markdown link/image syntax. We
   keep printable text, drop the markup. We do *not* try to "render"
   anything; the agent gets safe plain text.
3. **Code-fence info-string filtering** — collapses
   ``\u0060\u0060\u0060<info>`` fences whose info-string contains
   suspicious tokens (``system``, ``user``, ``assistant``, ``tool``,
   ``ignore``, ``override``, etc.) so an attacker cannot use a fake
   fence to mimic a chat role and hijack the agent.

Sanitization is applied recursively to ``dict`` / ``list`` / ``tuple``
structures and to bare strings. Non-string scalars (``int``,
``float``, ``bool``, ``None``) are returned unchanged.

Sanitization is **on by default** for every tool response. Operators
can disable it globally via the env var
``ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION=true`` (use only for
diagnostics — disabling it removes a defense-in-depth layer).

Public surface:
    * :func:`sanitize_text` — sanitize a single string.
    * :func:`sanitize_value` — recursively sanitize any JSON-shaped
      value (dict / list / tuple / scalar).
    * :func:`is_sanitization_enabled` — reflect the current toggle.
    * :func:`disable_sanitization` /
      :func:`enable_sanitization` — programmatic toggles (mainly for
      tests; production deployments should use the env var).
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

import bleach

__all__ = [
    "sanitize_text",
    "sanitize_value",
    "is_sanitization_enabled",
    "enable_sanitization",
    "disable_sanitization",
]


# ---------------------------------------------------------------------------
# 1. Invisible / control-character stripping
# ---------------------------------------------------------------------------
#
# Categories from `unicodedata.category`:
#   Cc  – Control
#   Cf  – Format (includes BiDi overrides RLO/LRO/RLI/LRI/PDI/PDF, ZWJ,
#         ZWNJ, soft hyphen, word joiner, etc.)
#   Co  – Private use
#   Cn  – Unassigned
# We keep \t (U+0009), \n (U+000A), \r (U+000D) because they are
# legitimate whitespace in tool output (think multi-line descriptions).

_ALLOWED_CONTROL = frozenset({"\t", "\n", "\r"})

# Explicit BiDi / invisible / homoglyph-ish characters that bypass the
# "Cf only" check or that we want to drop even if a future Unicode
# revision reclassifies them.
_EXPLICIT_INVISIBLE = frozenset(
    {
        "\u00a0",  # Non-breaking space → keep? No — agents/users see it as a space already; safer to normalise to U+0020
        "\u00ad",  # Soft hyphen
        "\u061c",  # Arabic letter mark
        "\u180e",  # Mongolian vowel separator
        "\u200b",  # Zero-width space
        "\u200c",  # Zero-width non-joiner
        "\u200d",  # Zero-width joiner
        "\u200e",  # Left-to-right mark
        "\u200f",  # Right-to-left mark
        "\u202a",  # LRE
        "\u202b",  # RLE
        "\u202c",  # PDF
        "\u202d",  # LRO
        "\u202e",  # RLO
        "\u2060",  # Word joiner
        "\u2061",  # Function application
        "\u2062",  # Invisible times
        "\u2063",  # Invisible separator
        "\u2064",  # Invisible plus
        "\u2066",  # LRI
        "\u2067",  # RLI
        "\u2068",  # FSI
        "\u2069",  # PDI
        "\ufeff",  # Zero-width no-break space / BOM
    }
)

# U+00A0 (NBSP) is in _EXPLICIT_INVISIBLE so we drop it from the
# control map but normalise it to a regular space below.
_NORMALIZE_TO_SPACE = frozenset({"\u00a0"})


def _strip_invisible(text: str) -> str:
    """Remove invisible / control characters that humans can't see but LLMs can.

    Preserves common whitespace (``\\t``, ``\\n``, ``\\r``).
    Normalises non-breaking space to a regular space.
    """
    if not text:
        return text
    out = []
    for ch in text:
        if ch in _NORMALIZE_TO_SPACE:
            out.append(" ")
            continue
        if ch in _EXPLICIT_INVISIBLE:
            continue
        if ch in _ALLOWED_CONTROL:
            out.append(ch)
            continue
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Cf", "Co", "Cn"):
            continue
        out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# 2. HTML / Markdown sanitization
# ---------------------------------------------------------------------------
#
# Strategy:
#   * Strip ALL HTML tags. The free-form admin fields in Zscaler
#     resources (rule descriptions, etc.) should never contain HTML;
#     if they do, that's already suspicious. We keep the inner text.
#   * Strip Markdown image syntax `![alt](url)` and link syntax
#     `[text](url)` to prevent click-bait / out-of-band instructions
#     embedded in URLs. Keep the visible text.
#   * Leave the rest of the Markdown alone (bold, italic, lists,
#     headings) — those are harmless and the agent needs to read them.

_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _sanitize_html_markdown(text: str) -> str:
    """Strip raw HTML and dangerous Markdown link/image syntax."""
    if not text:
        return text

    text = bleach.clean(
        text,
        tags=[],
        attributes={},
        protocols=[],
        strip=True,
        strip_comments=True,
    )

    text = _MD_IMAGE_RE.sub(lambda m: m.group(1) or "[image]", text)

    def _link_repl(m: re.Match) -> str:
        label = m.group(1).strip()
        url = m.group(2).strip()
        if not url:
            return label
        return f"{label} ({url})"

    text = _MD_LINK_RE.sub(_link_repl, text)
    return text


# ---------------------------------------------------------------------------
# 3. Code-fence info-string filtering
# ---------------------------------------------------------------------------
#
# A Markdown fenced code block looks like:
#     ```<info-string>
#     ...code...
#     ```
# Most agents ignore the info-string, but some render it or use it for
# routing. An attacker can stuff role-impersonation tokens
# ("system", "assistant", "tool_use") or override directives
# ("ignore_above", "new_instructions") into the info-string. We
# rewrite suspicious info-strings to a neutral "text" tag and keep the
# code body intact.

_SUSPICIOUS_INFO_TOKENS = (
    "system",
    "user",
    "assistant",
    "tool",
    "function",
    "developer",
    "ignore",
    "override",
    "instruction",
    "prompt",
    "role",
)

_FENCE_RE = re.compile(
    r"(?P<fence>`{3,}|~{3,})(?P<info>[^\n`~]*)\n",
    re.MULTILINE,
)


def _sanitize_code_fences(text: str) -> str:
    """Neutralize suspicious info-strings on Markdown code fences."""
    if not text or ("```" not in text and "~~~" not in text):
        return text

    def _repl(m: re.Match) -> str:
        info = m.group("info").strip().lower()
        if not info:
            return m.group(0)
        if any(tok in info for tok in _SUSPICIOUS_INFO_TOKENS):
            return f"{m.group('fence')}text\n"
        return m.group(0)

    return _FENCE_RE.sub(_repl, text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_ENABLED = os.environ.get(
    "ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION", ""
).strip().lower() not in ("1", "true", "yes", "on")


def is_sanitization_enabled() -> bool:
    """Return True if output sanitization is currently active."""
    return _ENABLED


def enable_sanitization() -> None:
    """Force sanitization on (mainly for tests)."""
    global _ENABLED
    _ENABLED = True


def disable_sanitization() -> None:
    """Force sanitization off (mainly for tests / diagnostics)."""
    global _ENABLED
    _ENABLED = False


def sanitize_text(text: str) -> str:
    """Apply all three sanitizers to a single string.

    Order matters: we strip invisible characters first so that
    subsequent regex / parsing steps see the canonical form.
    """
    if not isinstance(text, str) or not text:
        return text
    text = _strip_invisible(text)
    text = _sanitize_html_markdown(text)
    text = _sanitize_code_fences(text)
    return text


# Maximum recursion depth for sanitize_value. Protects us from
# pathological nested structures (cyclic refs would otherwise infinite-
# loop). 32 is generous — Zscaler tool results typically nest ~5 deep.
_MAX_DEPTH = 32


def sanitize_value(value: Any, _depth: int = 0) -> Any:
    """Recursively sanitize any JSON-shaped value.

    * ``str`` → run :func:`sanitize_text`.
    * ``dict`` → sanitize values (keys are NOT sanitized; they are
      typically machine-defined field names).
    * ``list`` / ``tuple`` → sanitize each element, preserving the
      container type.
    * Other scalars (``int``, ``float``, ``bool``, ``None``) →
      returned unchanged.
    * Anything past ``_MAX_DEPTH`` is returned as-is to avoid infinite
      recursion on pathological inputs.

    If sanitization is disabled (env var or :func:`disable_sanitization`),
    the input is returned unchanged.
    """
    if not _ENABLED:
        return value
    if _depth > _MAX_DEPTH:
        return value

    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, dict):
        return {k: sanitize_value(v, _depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_value(v, _depth + 1) for v in value]
    if isinstance(value, tuple):
        return tuple(sanitize_value(v, _depth + 1) for v in value)
    return value
