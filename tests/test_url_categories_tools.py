"""URL-category tools — the response-size surface a customer actually hit.

Unfiltered, `/urlCategories` returns every category with all of its URLs, which
for a real tenant runs to six figures of tokens. A customer on a token-limited
gateway hit this because their agent used the full listing to answer "which
category does twilio.com belong to?" — a question `zia_url_lookup` answers in a
few hundred tokens.

The fix is to use the endpoint's own filters rather than to add a cheaper second
tool: two listing tools left the choice to the model, and "list all URL
categories" gives it nothing to choose on. So there is exactly ONE listing tool,
`custom_only` and `type` go upstream so the agent never has to filter with a
hand-written JMESPath expression, and the docstring tells it to ask for scope
first — the endpoint neither paginates nor offers a way to omit the URL lists,
so narrowing before the call is the only lever the API gives us.

These tests pin that: the tool count, the parameters it advertises (none the API
ignores), that they reach the API rather than being dropped, and the descriptions
that route the URL question to `zia_url_lookup`.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from zscaler_mcp.registry.registry import REGISTRY
from zscaler_mcp.server import build_server


@pytest.fixture(scope="module", autouse=True)
def _registry():
    build_server()


def _spec(name):
    spec = REGISTRY.get(name)
    assert spec is not None, f"{name} is not registered"
    return spec


class TestThereIsExactlyOneListingTool:
    def test_no_second_lite_tool_exists(self):
        """A `_lite` sibling would re-create the ambiguity this replaced.

        The server cannot arbitrate: only the model picks the tool, and a plain
        "list all URL categories" carries no signal favouring either one.
        """
        listing = [
            name
            for name in REGISTRY.names()
            if name.startswith("zia_list_url_categor")  # categories / categories_lite
        ]
        assert listing == ["zia_list_url_categories"]


class TestParametersMatchTheAPI:
    def test_the_listing_advertises_no_pagination(self):
        """`/urlCategories` does not paginate.

        `page` / `page_size` were advertised and silently dropped by the API,
        telling an agent it could page through a huge result when it could not.
        """
        fields = set(_spec("zia_list_url_categories").input_model.model_fields)
        assert "page" not in fields and "page_size" not in fields

    def test_exactly_the_parameters_the_endpoint_honours_are_advertised(self):
        """`include_only_url_keyword_counts` is absent on purpose.

        It was exposed on the assumption that it swaps the URL/keyword/IP lists
        for counts. A tenant response captured with it on and off is equivalent —
        `dbCategorizedUrls` and `ipRanges` populated in both — so it joins
        `page` / `page_size` as a parameter the API ignores, and this repo does
        not advertise those.
        """
        assert set(_spec("zia_list_url_categories").input_model.model_fields) == {
            "search",
            "custom_only",
            "type",
        }


class TestDescriptionsSteerToolSelection:
    """The descriptions are the mechanism. An agent picks from them alone."""

    def test_the_listing_says_it_omits_urls_and_names_where_to_get_them(self):
        text = _spec("zia_list_url_categories").description
        assert "zia_get_url_category" in text
        assert "zia_url_lookup" in text

    def test_the_listing_tells_the_agent_to_ask_for_scope_first(self):
        """Advisory, but it is the only lever against an unbounded response.

        The endpoint does not paginate and a filter cannot cap the row count —
        `custom_only=True` on a tenant with 5000 custom categories still returns
        5000. Narrowing has to happen before the call, which means asking. Same
        pattern as the ZDX guidance in CLAUDE.md.
        """
        # Collapse wrapping: the docstring is hard-wrapped, so a phrase can span
        # a newline and a substring check would fail on formatting alone.
        text = " ".join(_spec("zia_list_url_categories").description.split())
        assert "ASK THE USER FOR SCOPE" in text
        # The ask must come with the reason, or it reads as optional politeness.
        assert "does not paginate" in text
        # ...and must precede the parameter reference, so the agent knows to ask
        # before it knows what to pass.
        assert text.index("ASK THE USER FOR SCOPE") < text.index("custom_only=True")

    def test_lookup_claims_the_which_category_question(self):
        text = _spec("zia_url_lookup").description.lower()
        assert "which category" in text
        # and warns off the expensive path
        assert "zia_list_url_categories" in _spec("zia_url_lookup").description

    def test_lookup_states_its_two_real_limits(self):
        text = _spec("zia_url_lookup").description
        assert "100 URLs" in text
        assert "MISCELLANEOUS_OR_UNKNOWN" in text
        assert "PREDEFINED" in text or "predefined" in text


class TestListingTool:
    """The filters must actually reach the API, not be dropped or re-implemented."""

    def _client(self, rows, *, captured=None):
        class _Row:
            def __init__(self, d):
                self._d = d

            def as_dict(self):
                return dict(self._d)

        class _API:
            @staticmethod
            def list_categories(query_params=None):
                if captured is not None:
                    captured.append(query_params)
                return ([_Row(r) for r in rows], None, None)

            @staticmethod
            def list_categories_lite():  # pragma: no cover - must never be called
                raise AssertionError(
                    "the lite endpoint takes no parameters and omits configuredName; "
                    "the listing tool must use /urlCategories with its own filters"
                )

        class _Client:
            class zia:
                url_categories = _API()

        return _Client

    def _call(self, client, **kwargs):
        spec = _spec("zia_list_url_categories")
        with patch(
            "zscaler_mcp.tools.zia.url_categories.get_zscaler_client",
            return_value=client,
        ):
            return spec.fn(spec.input_model(**kwargs))

    def _query_params(self, **kwargs):
        captured: list = []
        self._call(self._client([], captured=captured), **kwargs)
        assert len(captured) == 1
        return captured[0]

    def test_returns_records_verbatim(self):
        rows = [{"id": "OTHER_ADULT_MATERIAL", "customCategory": False, "customUrlsCount": 0}]
        assert self._call(self._client(rows)) == rows, "records pass through unshaped (issue #88)"

    def test_no_parameters_are_sent_when_none_were_asked_for(self):
        """Sending a value the caller never chose is us inventing API behaviour."""
        assert self._query_params() == {}

    def test_custom_only_is_sent_to_the_api_not_applied_here(self):
        """Filtering upstream is the point: the predefined categories never ship.

        Regression this replaces: with no such parameter an agent wrote
        ``[?customCategory]`` as a JMESPath `query` against a record whose key is
        ``custom_category``, got an empty list, and could not distinguish that
        from a tenant with no custom categories.
        """
        assert self._query_params(custom_only=True)["custom_only"] is True
        assert self._query_params(custom_only=False)["custom_only"] is False

    def test_type_is_sent_to_the_api(self):
        assert self._query_params(type="TLD_CATEGORY")["type"] == "TLD_CATEGORY"

    def test_search_is_forwarded_for_the_sdk_to_apply(self):
        """`search` is the one parameter the SDK filters locally, on configured_name."""
        assert self._query_params(search="partner")["search"] == "partner"

    def test_api_errors_surface_with_the_tool_name(self):
        class _API:
            @staticmethod
            def list_categories(query_params=None):
                return (None, None, "403 Forbidden")

        class _Client:
            class zia:
                url_categories = _API()

        with pytest.raises(RuntimeError, match="Failed to list URL categories"):
            self._call(_Client)
