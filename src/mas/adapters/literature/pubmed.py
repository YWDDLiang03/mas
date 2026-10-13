"""NCBI E-utilities (PubMed): fallback literature search with abstracts (`tools.md` §2.8)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from mas.core.broker import ProviderResponse, ToolContract, ToolError

from . import http

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _text(element) -> str:
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


class PubMedSearch:
    contract = ToolContract(
        tool_id="tool_literature_pubmed_search", capability="literature_retrieval", capability_kind="source_retrieval",
        question_kinds=("search",), contract_version="1", implementation_version="eutils-esearch-efetch-1",
        purpose_statement="Find PubMed records with abstracts for a query (fallback finder)",
        evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated", required_inputs=("query",),
        license_id="NCBI usage policy")

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        params = {"db": "pubmed", "term": inputs["query"], "retmode": "json",
                  "retmax": max(1, min(int(inputs.get("limit", 25)), 100)), "tool": "mas"}
        if inputs.get("cutoff_date"):
            params.update({"datetype": "pdat", "mindate": "1900/01/01", "maxdate": inputs["cutoff_date"].replace("-", "/")})
        found = http.get(f"{BASE}/esearch.fcgi", params=params)
        ids = ((found or {}).get("esearchresult") or {}).get("idlist") or []
        if not ids:
            return ProviderResponse(values=[], data_version="pubmed")
        xml_text = http.get(f"{BASE}/efetch.fcgi", params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml", "tool": "mas"},
                            expect="text")
        try:
            root = ET.fromstring(xml_text or "<PubmedArticleSet/>")
        except ET.ParseError as error:
            raise ToolError("parse_failed", str(error), retryable=False) from None
        hits = []
        for article in root.findall("PubmedArticle"):
            pmid = _text(article.find(".//PMID"))
            title = _text(article.find(".//ArticleTitle"))
            parts = []
            for part in article.findall(".//Abstract/AbstractText"):
                label = part.get("Label")
                parts.append((f"<h4>{label}</h4>" if label else "") + _text(part))
            doi = next((_text(i) for i in article.findall(".//ArticleId") if i.get("IdType") == "doi"), None)
            pmcid = next((_text(i) for i in article.findall(".//ArticleId") if i.get("IdType") == "pmc"), None)
            pub_types = [_text(p) for p in article.findall(".//PublicationType")]
            hits.append({"identifiers": [x for x in ({"scheme": "pmid", "value": pmid},
                                                     {"scheme": "doi", "value": doi} if doi else None,
                                                     {"scheme": "pmcid", "value": pmcid} if pmcid else None) if x],
                         "doi": doi, "pmid": pmid, "pmcid": pmcid, "title": title,
                         "authors": ", ".join(_text(a.find("LastName")) for a in article.findall(".//Author")[:6]),
                         "journal": _text(article.find(".//Journal/Title")), "year": _text(article.find(".//PubDate/Year")),
                         "is_open_access": bool(pmcid), "pub_types": pub_types,
                         "is_preprint": any("preprint" in p.lower() for p in pub_types),
                         "is_review": any("review" in p.lower() for p in pub_types),
                         "abstract_html": "".join(parts), "cited_by_count": 0, "license": None})
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits],
                                records=[{"query": inputs["query"], "returned": len(hits)}], data_version="pubmed",
                                upstream_refs=[f"pubmed:esearch:{inputs['query']}"])
