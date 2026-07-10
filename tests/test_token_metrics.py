"""Tests for the runtime token-metrics helper (common/token_metrics.py)."""

from __future__ import annotations

import zscaler_mcp.common.token_metrics as tm
from zscaler_mcp.common.token_metrics import (
    DEFAULT_ENCODING,
    count_tokens,
    is_token_reporting_enabled,
    resolve_encoding,
    token_usage_block,
)


def test_count_tokens_empty_string_is_zero():
    assert count_tokens("") == (0, True)


def test_count_tokens_returns_positive_for_text():
    tokens, exact = count_tokens("id,name\n1,HQ")
    assert tokens > 0
    assert isinstance(exact, bool)


def test_count_tokens_fallback_when_tiktoken_missing(monkeypatch):
    # Simulate tiktoken being unavailable: clear the encoder cache and force None.
    tm._get_encoder.cache_clear()
    monkeypatch.setattr(tm, "_get_encoder", lambda name: None)
    tokens, exact = count_tokens("abcdefgh")  # 8 chars -> 8//4 = 2
    assert exact is False
    assert tokens == 2


def test_token_usage_block_for_list():
    block = token_usage_block("id,name\n1,HQ\n2,Branch", row_count=2)
    assert block["response_tokens"] > 0
    assert block["response_bytes"] == len("id,name\n1,HQ\n2,Branch".encode("utf-8"))
    assert block["rows"] == 2
    assert "tokens_per_row" in block
    assert block["exact"] is True


def test_resolve_encoding_defaults_and_honours_env(monkeypatch):
    monkeypatch.delenv("ZSCALER_MCP_TOKEN_ENCODING", raising=False)
    assert resolve_encoding() == DEFAULT_ENCODING
    monkeypatch.setenv("ZSCALER_MCP_TOKEN_ENCODING", "cl100k_base")
    assert resolve_encoding() == "cl100k_base"
    # Blank/whitespace falls back to the default rather than an empty encoding.
    monkeypatch.setenv("ZSCALER_MCP_TOKEN_ENCODING", "   ")
    assert resolve_encoding() == DEFAULT_ENCODING


def test_token_usage_block_label_is_vendor_neutral_proxy(monkeypatch):
    monkeypatch.delenv("ZSCALER_MCP_TOKEN_ENCODING", raising=False)
    block = token_usage_block("id,name\n1,HQ", row_count=1)
    # Never advertise a bare vendor encoding name — always flagged as a proxy so
    # a Claude/Gemini user doesn't read it as exact for their model.
    assert block["proxy"] is True
    assert block["encoding"] == f"{DEFAULT_ENCODING}-proxy"
    assert block["encoding"].endswith("-proxy")


def test_token_usage_block_label_follows_configured_encoding(monkeypatch):
    monkeypatch.setenv("ZSCALER_MCP_TOKEN_ENCODING", "cl100k_base")
    block = token_usage_block("id,name\n1,HQ", row_count=1)
    assert block["encoding"] == "cl100k_base-proxy"
    assert block["proxy"] is True


def test_token_usage_block_fallback_still_flags_proxy(monkeypatch):
    tm._get_encoder.cache_clear()
    monkeypatch.setattr(tm, "_get_encoder", lambda name: None)
    block = token_usage_block("abcd", row_count=1)
    # The len/4 fallback keeps its own label but is still a proxy, never exact.
    assert block["encoding"] == "len/4-estimate"
    assert block["proxy"] is True
    assert block["exact"] is False


def test_token_usage_block_single_object_has_no_rows():
    block = token_usage_block('{"id": "1"}')
    assert "rows" not in block
    assert "tokens_per_row" not in block


def test_token_usage_block_estimate_labels_encoding(monkeypatch):
    tm._get_encoder.cache_clear()
    monkeypatch.setattr(tm, "_get_encoder", lambda name: None)
    block = token_usage_block("abcd", row_count=0)
    assert block["exact"] is False
    assert block["encoding"] == "len/4-estimate"
    # row_count == 0 must not divide-by-zero
    assert "tokens_per_row" not in block


def test_is_token_reporting_enabled(monkeypatch):
    monkeypatch.delenv("ZSCALER_MCP_REPORT_TOKENS", raising=False)
    assert is_token_reporting_enabled() is False
    for truthy in ("true", "1", "yes", "TRUE", " Yes "):
        monkeypatch.setenv("ZSCALER_MCP_REPORT_TOKENS", truthy)
        assert is_token_reporting_enabled() is True
    monkeypatch.setenv("ZSCALER_MCP_REPORT_TOKENS", "false")
    assert is_token_reporting_enabled() is False
