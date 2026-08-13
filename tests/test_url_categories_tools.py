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
            "contains_url",
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

    def test_lookup_routes_the_custom_question_to_contains_url(self):
        """Field tests 1 and 4: the model stopped at lookup and answered the
        CUSTOM question from PREDEFINED data. The lookup description must state
        it is predefined-only and hand the custom question to the one-call
        recipe, so the chain is named rather than left for the model to invent.
        """
        text = " ".join(_spec("zia_url_lookup").description.split())
        assert "PREDEFINED classification ONLY" in text
        assert "contains_url" in text
        assert "custom_only=True" in text

    def test_lookup_no_longer_claims_the_listing_has_no_urls(self):
        """Stale claim from the /lite design — the listing DOES return the URL
        lists now (that is the whole token problem). An agent believing this
        would never scan a listing, but it would also mis-explain results.
        """
        text = " ".join(_spec("zia_url_lookup").description.split())
        assert "without any URLs" not in text

    def test_listing_documents_contains_url_as_the_one_call_answer(self):
        text = " ".join(_spec("zia_list_url_categories").description.split())
        assert "contains_url" in text
        assert "_url_match" in text


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


class TestContainsUrl:
    """`contains_url` — 'which custom category contains app.box.com?' in one call.

    Modeled directly on the customer's field tests against a real tenant, where
    app.box.com lives in CUSTOM_44 "Box Domains" as the entry `.app.box.com`:

    * Tests 1 & 4: the model answered the custom question from predefined data,
      or listed everything and matched wrongly. The matching now happens here.
    * Test 2: `custom_only=True` returned 5 categories at ~21,600 tokens each
      because non-matching categories shipped their full URL lists. Only the
      matching categories may come back.
    """

    BOX = {
        "id": "CUSTOM_44",
        "configured_name": "Box Domains",
        "custom_category": True,
        "urls": [".app.box.com"],
        "db_categorized_urls": [".box.com"],
    }
    # The fat bystander: must never ship when it does not match (field test 2).
    FAT = {
        "id": "CUSTOM_45",
        "configured_name": "Huge Allow List",
        "custom_category": True,
        "urls": [f"host{i}.example.com" for i in range(500)],
        "db_categorized_urls": [],
    }

    def _client(self, rows):
        class _Row:
            def __init__(self, d):
                self._d = d

            def as_dict(self):
                return dict(self._d)

        class _API:
            @staticmethod
            def list_categories(query_params=None):
                return ([_Row(r) for r in rows], None, None)

        class _Client:
            class zia:
                url_categories = _API()

        return _Client

    def _call(self, rows, **kwargs):
        spec = _spec("zia_list_url_categories")
        with patch(
            "zscaler_mcp.tools.zia.url_categories.get_zscaler_client",
            return_value=self._client(rows),
        ):
            return spec.fn(spec.input_model(**kwargs))

    def test_only_matching_categories_are_returned(self):
        """Field test 2: the non-matching fat category must not ship at all."""
        out = self._call([self.BOX, self.FAT], contains_url="app.box.com")
        assert [r["id"] for r in out] == ["CUSTOM_44"]

    def test_leading_dot_entry_matches_the_bare_host(self):
        """The customer's tenant holds `.app.box.com`; the user asks about
        `app.box.com`. A literal string comparison misses — this was field
        test 4's wrong 'not found'."""
        out = self._call([self.BOX], contains_url="app.box.com")
        assert out and out[0]["id"] == "CUSTOM_44"

    def test_a_parent_domain_entry_covers_subdomains(self):
        """ZIA semantics: `.box.com` (and bare `box.com`) cover app.box.com."""
        rows = [{"id": "C1", "urls": [".box.com"]}, {"id": "C2", "urls": ["box.com"]}]
        out = self._call(rows, contains_url="app.box.com")
        assert [r["id"] for r in out] == ["C1", "C2"]

    def test_suffix_matching_is_anchored_at_a_label_boundary(self):
        """`box.com` must not match `notbox.com` — endswith alone would."""
        rows = [{"id": "C1", "urls": ["box.com"]}]
        assert self._call(rows, contains_url="notbox.com") == []

    def test_the_input_may_be_a_full_url(self):
        """Users paste URLs, not hosts: scheme, path, query, port, case."""
        out = self._call([self.BOX], contains_url="HTTPS://APP.BOX.COM:443/folder/x?y=1")
        assert out and out[0]["id"] == "CUSTOM_44"

    def test_db_categorized_urls_are_searched_too(self):
        """The retaining-parent-category list is a real place the answer lives —
        the customer's own screenshot showed `.box.com` there."""
        rows = [{"id": "C1", "urls": [], "db_categorized_urls": [".box.com"]}]
        out = self._call(rows, contains_url="app.box.com")
        assert out and out[0]["id"] == "C1"

    def test_no_match_returns_an_empty_list(self):
        """Authoritative 'no custom category contains it' — not an error."""
        assert self._call([self.BOX, self.FAT], contains_url="twilio.com") == []

    def test_the_match_annotation_names_the_matching_entries(self):
        """The agent must be able to say WHY a category matched (the customer's
        good run reported 'Match reason: the category contains .app.box.com').
        The annotation is additive — the verbatim record stays intact (#88)."""
        out = self._call([self.BOX], contains_url="app.box.com")
        record = out[0]
        assert record["_url_match"]["url"] == "app.box.com"
        assert {m["entry"] for m in record["_url_match"]["matched"]} == {
            ".app.box.com",
            ".box.com",
        }
        # every original key survives untouched
        for key, value in self.BOX.items():
            assert record[key] == value

    def test_contains_url_combines_with_custom_only(self):
        """The recipe is one call: custom_only goes upstream, matching is local."""
        captured: list = []

        class _Row:
            def __init__(self, d):
                self._d = d

            def as_dict(self):
                return dict(self._d)

        class _API:
            @staticmethod
            def list_categories(query_params=None):
                captured.append(query_params)
                return ([_Row(TestContainsUrl.BOX)], None, None)

        class _Client:
            class zia:
                url_categories = _API()

        spec = _spec("zia_list_url_categories")
        with patch(
            "zscaler_mcp.tools.zia.url_categories.get_zscaler_client",
            return_value=_Client,
        ):
            out = spec.fn(spec.input_model(custom_only=True, contains_url="app.box.com"))
        assert captured == [{"custom_only": True}]
        assert [r["id"] for r in out] == ["CUSTOM_44"]

    def test_camelcase_records_match_too(self):
        """A raw passthrough record carries `dbCategorizedUrls`; both spellings
        must be searched — same both-spellings rule as `custom_only` before the
        endpoint switch."""
        rows = [{"id": "C1", "dbCategorizedUrls": [".box.com"]}]
        out = self._call(rows, contains_url="app.box.com")
        assert out and out[0]["id"] == "C1"
