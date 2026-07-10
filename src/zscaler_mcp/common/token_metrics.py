"""Token accounting for tool responses (DESIGN.md §5).

A single place that answers "how many tokens does this string cost an agent?"
Used in two spots:

* **Runtime, opt-in.** When ``ZSCALER_MCP_REPORT_TOKENS=true`` the bridge attaches
  a ``token_usage`` block to each tool response so the agent (and the operator
  watching logs) can see the real per-call cost of the curated output.
* **Offline.** The token-comparison utility (``common/token_comparison.py``)
  reuses :func:`count_tokens` so the synthetic benchmark and the live runtime
  path measure with the exact same encoder.

Tokenizer choice (vendor-neutral by design)
============================================
This metric is a **model-agnostic proxy**, not a billing-grade per-vendor count.
We do not pin to any single LLM provider:

* By default we count with ``tiktoken``'s ``o200k_base`` BPE encoding because it
  is the only widely-installed tokenizer that runs **offline, deterministically,
  with zero credentials and no network call** — exactly what an always-on
  telemetry metric needs. It is NOT Claude's, Gemini's, or Llama's exact
  tokenizer.
* The encoding is **configurable** via ``ZSCALER_MCP_TOKEN_ENCODING`` (any name
  ``tiktoken`` understands, e.g. ``cl100k_base``), so an operator can align the
  proxy with their model family if they care about the absolute number.
* What the agent-first design actually optimizes is the **ratio** between a
  bloated and a curated response (e.g. "~88% smaller"). That ratio is stable
  across BPE tokenizers — every modern tokenizer treats JSON keys, punctuation,
  IDs, and repeated field names similarly — so the proxy answers "is this
  response lean or bloated?" correctly for *any* model, even when the absolute
  count is a few percent off.

To avoid implying the number is exact for whatever model a user runs, the
surfaced ``encoding`` label is suffixed ``-proxy`` and the usage block carries an
explicit ``proxy: true`` flag.

If ``tiktoken`` is unavailable we fall back to a coarse ``len(text) / 4``
byte-heuristic and flag the estimate as approximate, so the feature degrades
instead of crashing.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Optional

__all__ = [
    "DEFAULT_ENCODING",
    "resolve_encoding",
    "count_tokens",
    "token_usage_block",
    "is_token_reporting_enabled",
]

DEFAULT_ENCODING = "o200k_base"

# Suffix appended to the surfaced encoding label so the number never reads as a
# vendor-exact count. The metric is a model-agnostic proxy (see module docstring).
_PROXY_SUFFIX = "-proxy"


def resolve_encoding() -> str:
    """Return the tiktoken encoding to count with.

    Honours ``ZSCALER_MCP_TOKEN_ENCODING`` so operators can align the proxy with
    their model family (e.g. ``cl100k_base``); falls back to :data:`DEFAULT_ENCODING`.
    Kept vendor-neutral on purpose — we never hard-pin a single provider.
    """
    return os.getenv("ZSCALER_MCP_TOKEN_ENCODING", "").strip() or DEFAULT_ENCODING


@lru_cache(maxsize=4)
def _get_encoder(encoding_name: str):
    """Return a cached tiktoken encoder, or ``None`` if tiktoken isn't installed."""
    try:
        import tiktoken
    except ImportError:  # pragma: no cover - tiktoken is a dev/optional dep
        return None
    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception:  # pragma: no cover - defensive
        return None


def count_tokens(text: str, *, encoding_name: Optional[str] = None) -> tuple[int, bool]:
    """Return ``(token_count, exact)`` for ``text``.

    ``encoding_name`` defaults to :func:`resolve_encoding` (honours
    ``ZSCALER_MCP_TOKEN_ENCODING``) so the configured proxy applies at call time.

    ``exact`` is True when a real BPE tokenizer produced the count, False when
    we fell back to the ``len/4`` heuristic (tiktoken unavailable). Callers
    surface ``exact`` so an estimate is never mistaken for a measured value.

    Note the count is a model-agnostic *proxy* (see module docstring); ``exact``
    means "a real tokenizer ran", not "exact for the user's specific model".
    """
    if not text:
        return 0, True
    enc = _get_encoder(encoding_name or resolve_encoding())
    if enc is None:
        return max(1, len(text) // 4), False
    return len(enc.encode(text)), True


def is_token_reporting_enabled() -> bool:
    """True when ``ZSCALER_MCP_REPORT_TOKENS`` opts into per-response metrics."""
    return os.getenv("ZSCALER_MCP_REPORT_TOKENS", "").strip().lower() in ("true", "1", "yes")


def token_usage_block(
    response_text: str,
    *,
    row_count: Optional[int] = None,
    encoding_name: Optional[str] = None,
) -> dict[str, Any]:
    """Build a machine-readable token-usage summary for a response string.

    Args:
        response_text: the exact text block the agent receives (post-encoding).
        row_count: number of rows for a list response, used to derive
            ``tokens_per_row``. ``None`` for single-object responses.
        encoding_name: tiktoken encoding to measure against. Defaults to
            :func:`resolve_encoding` (honours ``ZSCALER_MCP_TOKEN_ENCODING``).

    The ``encoding`` value is a model-agnostic proxy label suffixed ``-proxy``
    and the block carries ``proxy: true`` so the number is never mistaken for a
    vendor-exact count (see module docstring). ``exact`` reports only whether a
    real BPE tokenizer ran (vs the ``len/4`` fallback).

    Returns:
        A dict suitable for embedding in ``structured_content`` under
        ``token_usage``, e.g.::

            {
              "response_tokens": 110,
              "response_bytes": 426,
              "encoding": "o200k_base-proxy",
              "proxy": true,
              "exact": true,
              "rows": 4,
              "tokens_per_row": 27.5
            }
    """
    resolved = encoding_name or resolve_encoding()
    tokens, exact = count_tokens(response_text, encoding_name=resolved)
    # The label always advertises "proxy" so a Claude/Gemini/etc. user never reads
    # the count as exact for their model. The len/4 fallback is its own label.
    label = f"{resolved}{_PROXY_SUFFIX}" if exact else "len/4-estimate"
    block: dict[str, Any] = {
        "response_tokens": tokens,
        "response_bytes": len(response_text.encode("utf-8")),
        "encoding": label,
        "proxy": True,
        "exact": exact,
    }
    if row_count is not None:
        block["rows"] = row_count
        if row_count > 0:
            block["tokens_per_row"] = round(tokens / row_count, 1)
    return block
