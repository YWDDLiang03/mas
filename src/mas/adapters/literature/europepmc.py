"""Europe PMC: literature search and open-access full-text reading (`tools.md` §2.7)."""

from __future__ import annotations

from typing import Any

from mas.core.broker import ProviderResponse, ToolContract, ToolError

from . import http, jats

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def _journal(record: dict[str, Any]) -> str:
    info = record.get("journalInfo") or {}
    return ((info.get("journal") or {}).get("title")) or record.get("bookOrReportDetails", {}).get("publisher", "") or ""


def normalize_hit(record: dict[str, Any]) -> dict[str, Any]:
    pub_types = ((record.get("pubTypeList") or {}).get("pubType")) or []
    if isinstance(pub_types, str):
        pub_types = [pub_types]
    is_preprint = record.get("source") == "PPR" or any("preprint" in p.lower() for p in pub_types)
    identifiers = []
    for scheme, key in (("doi", "doi"), ("pmid", "pmid"), ("pmcid", "pmcid"), ("epmc", "id")):
        if record.get(key):
            identifiers.append({"scheme": scheme, "value": str(record[key])})
    return {
        "identifiers": identifiers, "doi": record.get("doi"), "pmid": record.get("pmid"), "pmcid": record.get("pmcid"),
        "epmc_id": f"{record.get('source')}:{record.get('id')}",
        "title": jats.strip_html(record.get("title")), "authors": record.get("authorString", ""),
        "journal": _journal(record), "year": record.get("pubYear"),
        "first_publication_date": record.get("firstPublicationDate"),
        "is_open_access": record.get("isOpenAccess") == "Y", "in_epmc": record.get("inEPMC") == "Y",
        "pub_types": pub_types, "is_preprint": is_preprint, "is_review": any("review" in p.lower() for p in pub_types),
        "abstract_html": record.get("abstractText"), "cited_by_count": record.get("citedByCount", 0),
        "license": record.get("license"),
    }


class EuropePMCSearch:
    contract = ToolContract(
        tool_id="tool_literature_europepmc_search", capability="literature_retrieval", capability_kind="source_retrieval",
        question_kinds=("search",), contract_version="1", implementation_version="europepmc-rest-search-1",
        purpose_statement="Find literature records (title, abstract, identifiers, open-access flag) for a query",
        evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated", required_inputs=("query",),
        license_id="Europe PMC terms; per-article licenses vary")

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        query = f"({inputs['query']})"
        if inputs.get("cutoff_date"):
            query += f" AND FIRST_PDATE:[1900-01-01 TO {inputs['cutoff_date']}]"
        if inputs.get("open_access_only"):
            query += " AND OPEN_ACCESS:y"
        limit = max(1, min(int(inputs.get("limit", 25)), 100))
        body = http.get(f"{BASE}/search", params={"query": query, "format": "json", "resultType": "core",
                                                  "pageSize": limit, "sort": inputs.get("sort", "")})
        if body is None:
            raise ToolError("upstream_server_error", "search endpoint returned 404")
        results = (body.get("resultList") or {}).get("result") or []
        hits = [normalize_hit(r) for r in results]
        return ProviderResponse(
            values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits],
            records=[{"query": query, "hit_count": body.get("hitCount"), "returned": len(hits)}],
            data_version=f"europepmc:{body.get('version', 'unknown')}",
            upstream_refs=[f"europepmc:search:{query}"])


class EuropePMCReader:
    contract = ToolContract(
        tool_id="tool_literature_europepmc_reader", capability="document_reading", capability_kind="document_reading",
        question_kinds=("read",), contract_version="1", implementation_version="europepmc-fulltext-jats-1",
        purpose_statement="Read an article: open-access full text with located passages, otherwise the abstract",
        evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated",
        license_id="per-article license (recorded on the document)")

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        hit = inputs.get("hit") or {}
        pmcid = inputs.get("pmcid") or hit.get("pmcid")
        document = None
        if pmcid:
            xml_text = http.get(f"{BASE}/{pmcid}/fullTextXML", expect="text", timeout_s=120)
            if xml_text:
                try:
                    parsed = jats.parse(xml_text)
                except Exception as error:  # malformed XML is a parse failure, not a crash
                    raise ToolError("parse_failed", f"{pmcid}: {error}", retryable=False) from None
                document = dict(parsed, access_state="full_text_available", reading_depth="full_text")
        if document is None:
            if not hit:
                hits = http.get(f"{BASE}/search", params={"query": f"EXT_ID:{inputs.get('pmid')}", "format": "json",
                                                         "resultType": "core", "pageSize": 1}) if inputs.get("pmid") else None
                results = ((hits or {}).get("resultList") or {}).get("result") or []
                hit = normalize_hit(results[0]) if results else {}
            passages = jats.abstract_passages(hit.get("abstract_html"), hit.get("title"))
            depth = "title_abstract" if any(p["kind"] == "abstract" for p in passages) else "title_only"
            document = {"title": hit.get("title", ""), "year": hit.get("year"), "identifiers": {}, "passages": passages,
                        "license": hit.get("license"),
                        "access_state": "abstract_only" if depth == "title_abstract" else "metadata_only",
                        "reading_depth": depth}
        document["source_hit"] = {k: hit.get(k) for k in ("doi", "pmid", "pmcid", "title", "authors", "journal", "year",
                                                          "is_preprint", "is_review", "pub_types", "first_publication_date")}
        if not document["passages"]:
            return ProviderResponse(values=[], data_version="europepmc")
        return ProviderResponse(values=[{"name": "document", "value": document, "value_kind": "curated"}],
                                data_version="europepmc", upstream_refs=[f"pmcid:{pmcid}" if pmcid else f"pmid:{hit.get('pmid')}"])
