"""Evidence-source registry: which text sources the system may search and read, and why.

Every source declares how it may be accessed automatically and whether its licence
permits a language model to read its text. A source whose permission is unknown or
refused is never queried: `permitted()` is checked before any search, so the rule is
the same for every task, not a per-case judgement.

Sources are ordered by evidential weight. Hits keep their `source` id so the reader,
the ledger and the leaderboard can say where a claim came from.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    source_id: str
    title: str
    kind: str                     # journal_literature | reference_text | tertiary_reference | user_documents
    search_tool: str | None
    reader_tool: str | None
    source_status: str            # ledger source_status for documents from this source
    automated_access: str         # how the text may be fetched automatically
    license: str
    llm_ingestion: str            # permitted | permitted_per_document | refused | unknown
    note: str = ""
    requires: str = ""            # what must be set up before the source can answer


SOURCES: dict[str, Source] = {s.source_id: s for s in (
    Source("europepmc", "Europe PMC", "journal_literature", "tool_literature_europepmc_search",
           "tool_literature_europepmc_reader", "peer_reviewed_paper",
           "REST API; open-access full text as JATS XML", "per-article licence, recorded on each document",
           "permitted_per_document",
           "Open-access subset is provided for text mining; other articles are read at abstract depth."),
    Source("pubmed", "PubMed", "journal_literature", "tool_literature_pubmed_search",
           "tool_literature_europepmc_reader", "peer_reviewed_paper",
           "NCBI E-utilities (3 requests/s without a key)", "abstracts; per-article licence for full text",
           "permitted_per_document", "Search only; documents are read through Europe PMC."),
    Source("bookshelf", "NCBI Bookshelf (open-access books)", "reference_text", "tool_literature_bookshelf_search",
           "tool_literature_bookshelf_reader", "reference_text",
           "E-utilities for discovery; text only from the NLM LitArch open-access FTP (site crawling is not allowed)",
           "per-book licence (e.g. StatPearls CC BY-NC-ND 4.0), recorded on each document", "permitted_per_document",
           "Only books in the LitArch open-access subset are read; a book must be synced once.",
           requires="mas sources sync bookshelf --book NBK..."),
    Source("wikipedia", "Wikipedia", "tertiary_reference", "tool_literature_wikipedia_search",
           "tool_literature_wikipedia_reader", "tertiary_reference",
           "MediaWiki API with an identifying user agent", "CC BY-SA 4.0", "permitted",
           "Tertiary: useful for discovering what matters, weak as a source of values. Citations pin the revision."),
    Source("wikibooks", "Wikibooks", "reference_text", "tool_literature_wikibooks_search",
           "tool_literature_wikibooks_reader", "tertiary_reference",
           "MediaWiki API with an identifying user agent", "CC BY-SA 4.0", "permitted",
           "Open textbooks; community-edited. Citations pin the revision."),
    Source("uploads", "Documents you supplied", "user_documents", "tool_literature_uploads_search",
           "tool_literature_uploads_reader", "user_supplied_document",
           "local folder with a manifest", "declared per document in the manifest", "permitted_per_document",
           "Each document needs a manifest entry declaring its licence and that a language model may read it.",
           requires="a manifest.toml in the upload folder (see `mas sources upload --help`)"),
    Source("openstax", "OpenStax", "reference_text", None, None, "reference_text",
           "catalogue API only", "CC BY / CC BY-NC-SA", "refused",
           "The book prefaces forbid ingestion into large language models without written permission."),
)}

DEFAULT_ORDER = ("europepmc", "pubmed", "bookshelf", "wikibooks", "wikipedia", "uploads")


class SourceRefused(ValueError):
    """A source whose licence or access terms do not permit automated reading by a language model."""


def permitted(source_id: str) -> Source:
    source = SOURCES.get(source_id)
    if source is None:
        raise SourceRefused(f"unknown evidence source {source_id!r}; known sources: {sorted(SOURCES)}")
    if source.llm_ingestion not in ("permitted", "permitted_per_document"):
        raise SourceRefused(f"{source.title}: {source.note or 'licence does not permit model ingestion'}")
    if source.search_tool is None or source.reader_tool is None:
        raise SourceRefused(f"{source.title} has no search and reading tools")
    return source


def resolve(source_ids) -> list[Source]:
    """The permitted sources, in the given order; refuses the whole list if any entry is refused."""
    return [permitted(s) for s in dict.fromkeys(source_ids)]


def for_hit(hit: dict) -> Source:
    return SOURCES[hit.get("source") or "europepmc"]
