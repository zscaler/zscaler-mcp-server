"""Output sanitization for tool responses.

Ported from v1 (``zscaler_mcp/common/sanitize.py``). Defends against
prompt-injection payloads smuggled into admin-editable Zscaler fields (rule
descriptions, location names, label descriptions, custom URL category names).
Three independent sanitizers run on every string in every tool result:

1. **Invisible / control-character stripping** — BiDi overrides, zero-width
   spaces, soft hyphens, and other characters invisible to humans but parsed
   by LLMs.
2. **HTML / Markdown sanitization** — strips raw HTML tags and dangerous
   Markdown link/image syntax; keeps printable text.
3. **Code-fence info-string filtering** — neutralises ``\u0060\u0060\u0060<info>`` fences
   whose info-string contains role/override tokens.

On by default. Disable for diagnostics via
``ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION=true`` (removes a defense layer).
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

_ALLOWED_CONTROL = frozenset({"\t", "\n", "\r"})

_EXPLICIT_INVISIBLE = frozenset(
    {
        "\u00a0",  # Non-breaking space (normalised to a regular space below)
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

_NORMALIZE_TO_SPACE = frozenset({"\u00a0"})


def _strip_invisible(text: str) -> str:
    """Remove invisible / control characters; keep ``\\t \\n \\r``; NBSP → space."""
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

_ENABLED = os.environ.get("ZSCALER_MCP_DISABLE_OUTPUT_SANITIZATION", "").strip().lower() not in (
    "1",
    "true",
    "yes",
    "on",
)


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
    """Apply all three sanitizers to a single string (invisible → HTML → fences)."""
    if not isinstance(text, str) or not text:
        return text
    text = _strip_invisible(text)
    text = _sanitize_html_markdown(text)
    text = _sanitize_code_fences(text)
    return text


_MAX_DEPTH = 32


def sanitize_value(value: Any, _depth: int = 0) -> Any:
    """Recursively sanitize any JSON-shaped value (dict / list / tuple / scalar).

    Dict keys are NOT sanitized (machine-defined field names). Returns the
    input unchanged when sanitization is disabled or past ``_MAX_DEPTH``.
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
