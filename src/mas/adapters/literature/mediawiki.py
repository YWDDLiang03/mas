"""MediaWiki sites (Wikipedia, Wikibooks): search and revision-pinned reading.

Every document is one *revision*: the reader fetches the latest revision at or before the
evidence cutoff, so a run with a cutoff never reads text written after it, and a
citation (`oldid`) points at exactly the text that was read.
"""

from __future__ import annotations

from typing import Any

from mas.core.broker import ProviderResponse, ToolContract, ToolError

from . import http, jats, textparse

SITES = {
    "wikipedia": {"api": "https://en.wikipedia.org/w/api.php", "base": "https://en.wikipedia.org", "title": "Wikipedia"},
    "wikibooks": {"api": "https://en.wikibooks.org/w/api.php", "base": "https://en.wikibooks.org", "title": "Wikibooks"},
}


def _query_terms(query: str) -> str:
    """Boolean syntax written for literature databases, reduced to words a wiki search understands."""
    for token in ("(", ")", " AND ", " OR ", " NOT "):
        query = query.replace(token, " ")
    return " ".join(query.split())


class MediaWikiSearch:
    def __init__(self, site_id: str):
        site = SITES[site_id]
        self.site_id, self.api = site_id, site["api"]
        self.contract = ToolContract(
            tool_id=f"tool_literature_{site_id}_search", capability="literature_retrieval",
            capability_kind="source_retrieval", question_kinds=("search",), contract_version="1",
            implementation_version=f"{site_id}-mediawiki-search-1",
            purpose_statement=f"Find {site['title']} pages for a query", evidence_kind_produced="tertiary_reference",
            claim_strength_ceiling="curated", required_inputs=("query",), license_id="CC BY-SA 4.0")

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        limit = max(1, min(int(inputs.get("limit", 10)), 50))
        terms = _query_terms(inputs["query"])
        body = http.get(self.api, params={"action": "query", "list": "search", "srsearch": terms, "srlimit": limit,
                                          "srnamespace": 0, "format": "json", "formatversion": 2})
        if body is None:
            raise ToolError("upstream_server_error", f"{self.site_id} search returned 404")
        results = (body.get("query") or {}).get("search") or []
        hits = [{"source": self.site_id, "identifiers": [{"scheme": self.site_id, "value": str(r["pageid"])}],
                 "pageid": r["pageid"], "title": r["title"], "abstract_html": jats.strip_html(r.get("snippet")),
                 "journal": SITES[self.site_id]["title"], "year": (r.get("timestamp") or "")[:4], "authors": "",
                 "is_open_access": True, "in_epmc": False, "pub_types": ["encyclopedia article" if self.site_id == "wikipedia"
                                                                         else "open textbook page"],
                 "is_preprint": False, "is_review": False, "license": "CC BY-SA 4.0", "best_rank": rank}
                for rank, r in enumerate(results)]
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits],
                                records=[{"query": terms, "hit_count": (body.get("query") or {}).get("searchinfo", {}).get("totalhits"),
                                          "returned": len(hits)}],
                                data_version=self.site_id, upstream_refs=[f"{self.site_id}:search:{terms}"])


class MediaWikiReader:
    def __init__(self, site_id: str):
        site = SITES[site_id]
        self.site_id, self.api, self.base = site_id, site["api"], site["base"]
        self.contract = ToolContract(
            tool_id=f"tool_literature_{site_id}_reader", capability="document_reading", capability_kind="document_reading",
            question_kinds=("read",), contract_version="1", implementation_version=f"{site_id}-mediawiki-parse-1",
            purpose_statement=f"Read one revision of a {site['title']} page with located passages",
            evidence_kind_produced="tertiary_reference", claim_strength_ceiling="curated", license_id="CC BY-SA 4.0")

    def _revision(self, pageid: int, cutoff_date: str | None) -> dict[str, Any] | None:
        params = {"action": "query", "prop": "revisions", "pageids": pageid, "rvlimit": 1,
                  "rvprop": "ids|timestamp", "format": "json", "formatversion": 2}
        if cutoff_date:
            params.update({"rvstart": f"{cutoff_date}T23:59:59Z", "rvdir": "older"})
        body = http.get(self.api, params=params)
        pages = ((body or {}).get("query") or {}).get("pages") or []
        revisions = pages[0].get("revisions") if pages else None
        return revisions[0] if revisions else None

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        hit = inputs.get("hit") or {}
        revision = self._revision(hit["pageid"], inputs.get("cutoff_date"))
        if revision is None:
            return ProviderResponse(values=[], data_version=self.site_id)   # page did not exist before the cutoff
        body = http.get(self.api, params={"action": "parse", "oldid": revision["revid"], "prop": "text",
                                          "disableeditsection": 1, "format": "json", "formatversion": 2})
        if body is None or "parse" not in body:
            raise ToolError("upstream_server_error", f"{self.site_id} parse failed for revision {revision['revid']}")
        title = body["parse"].get("title") or hit.get("title")
        passages = textparse.html_passages(body["parse"].get("text") or "", title=title)
        permalink = f"{self.base}/w/index.php?oldid={revision['revid']}"
        document = {"title": title, "year": revision["timestamp"][:4],
                    "identifiers": {self.site_id: str(hit["pageid"]), "revid": str(revision["revid"]), "url": permalink},
                    "passages": passages, "license": "CC BY-SA 4.0", "access_state": "full_text_available",
                    "reading_depth": "full_text", "revision_timestamp": revision["timestamp"],
                    "source_hit": {"title": title, "journal": SITES[self.site_id]["title"], "year": revision["timestamp"][:4],
                                   "pub_types": hit.get("pub_types"), "url": permalink}}
        if len(passages) <= 1:
            return ProviderResponse(values=[], data_version=self.site_id)
        return ProviderResponse(values=[{"name": "document", "value": document, "value_kind": "curated"}],
                                data_version=f"{self.site_id}:rev{revision['revid']}", upstream_refs=[permalink])
