"""NCBI Bookshelf open-access books: discovery through E-utilities, text from the LitArch FTP.

NCBI does not allow systematic retrieval from the Bookshelf website; the LitArch
open-access FTP is the sanctioned route for automated access. Each book is published
there as one tarball (StatPearls is about 2 GB because it bundles images), so a book is
*synced* once: the tarball is streamed and only the chapter XML (BITS) is kept. After
that, searching uses E-utilities restricted to synced books and reading is local.

Hits are chapters. A hit's `rid` names the chapter file and the matched section, which
the reader resolves to passages with the publisher's own section ids.
"""

from __future__ import annotations

import csv
import html
import io
import json
import os
import re
import tarfile
import time
from pathlib import Path
from typing import Any, Callable

import requests

from mas.core.broker import ProviderResponse, ToolAbsent, ToolContract, ToolError

from . import http, jats

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
LITARCH = "https://ftp.ncbi.nlm.nih.gov/pub/litarch"
FILE_LIST_MAX_AGE_S = 7 * 24 * 3600


def default_cache_dir() -> Path:
    return Path(os.environ.get("MAS_CACHE") or Path.home() / ".cache" / "mas")


class BookshelfLibrary:
    """Local copy of the open-access books that have been synced (chapter XML only)."""

    def __init__(self, cache_dir: str | os.PathLike | None = None):
        self.root = Path(cache_dir or default_cache_dir()) / "bookshelf"

    # --- the open-access subset ------------------------------------------------------
    def file_list(self, *, refresh: bool = False) -> dict[str, dict[str, str]]:
        """Books in the LitArch open-access subset, by accession (NBK...)."""
        path = self.root / "file_list.csv"
        if refresh or not path.exists() or time.time() - path.stat().st_mtime > FILE_LIST_MAX_AGE_S:
            text = http.get(f"{LITARCH}/file_list.csv", expect="text", timeout_s=120)
            if not text:
                raise ToolError("upstream_server_error", "LitArch file_list.csv unavailable")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        books = {}
        for row in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))):
            accession = row.get("Accession ID")
            if accession:
                books[accession] = {"file": row["File"], "title": html.unescape(row.get("Title", "")),
                                    "publisher": html.unescape(row.get("Publisher", "")),
                                    "year": row.get("Publication Year", ""),
                                    "updated": row.get("Last Updated (YYYY-MM-DD HH:MM:SS)", "")}
        return books

    def synced(self) -> dict[str, dict[str, Any]]:
        out = {}
        if self.root.exists():
            for manifest in self.root.glob("NBK*/manifest.json"):
                record = json.loads(manifest.read_text(encoding="utf-8"))
                out[record["accession"]] = record
        return out

    def chapter_path(self, accession: str, article: str) -> Path:
        return self.root / accession / f"{article}.nxml"

    # --- sync ------------------------------------------------------------------------
    def sync(self, accession: str, *, progress: Callable[[str], None] | None = None) -> dict[str, Any]:
        """Stream one open-access book's tarball and keep its chapter XML. Re-syncs only if updated."""
        books = self.file_list(refresh=True)
        if accession not in books:
            raise ValueError(f"{accession} is not in the LitArch open-access subset; it cannot be read automatically")
        book = books[accession]
        current = self.synced().get(accession)
        if current and current.get("updated") == book["updated"]:
            return current
        target = self.root / accession
        partial = self.root / f".{accession}.partial"
        partial.mkdir(parents=True, exist_ok=True)
        url = f"{LITARCH}/{book['file']}"
        slug, kept, license_ = None, 0, None
        with requests.get(url, stream=True, timeout=300, headers={"User-Agent": http.USER_AGENT}) as reply:
            if reply.status_code != 200:
                raise ToolError("upstream_server_error", f"{reply.status_code} from {url}")
            reply.raw.decode_content = False
            with tarfile.open(fileobj=reply.raw, mode="r|gz") as tar:
                for member in tar:
                    if slug is None and "/" in member.name:
                        slug = member.name.split("/", 1)[0].rsplit("_", 1)[0]
                    if not (member.isfile() and member.name.endswith(".nxml")):
                        continue
                    name = Path(member.name).name
                    data = tar.extractfile(member).read()
                    (partial / name).write_bytes(data)
                    kept += 1
                    if license_ is None:
                        match = re.search(rb'license[^>]*xlink:href="([^"]+)"', data)
                        license_ = match.group(1).decode() if match else None
                    if progress and kept % 500 == 0:
                        progress(f"{accession}: {kept} chapters")
        manifest = {"accession": accession, "slug": slug, "title": book["title"], "publisher": book["publisher"],
                    "updated": book["updated"], "source_file": book["file"], "chapters": kept,
                    "license": license_, "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        (partial / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        if target.exists():
            for old in target.iterdir():
                old.unlink()
            target.rmdir()
        partial.rename(target)
        return manifest


def _article_and_section(rid: str) -> tuple[str | None, str | None]:
    """`NBK617063/article-164622.s5` → (`article-164622`, `article-164622.s5`)."""
    tail = rid.split("/", 1)[1] if "/" in rid else rid
    match = re.search(r"((?:[a-z]+-)*article-\d+)(\.[\w.-]+)?", tail)
    if not match:
        return None, None
    return match.group(1), (match.group(0) if match.group(2) else None)


class BookshelfSearch:
    contract = ToolContract(
        tool_id="tool_literature_bookshelf_search", capability="literature_retrieval", capability_kind="source_retrieval",
        question_kinds=("search",), contract_version="1", implementation_version="bookshelf-eutils-search-1",
        purpose_statement="Find chapters of synced open-access books (NCBI Bookshelf) for a query",
        evidence_kind_produced="reference_text", claim_strength_ceiling="curated", required_inputs=("query",),
        license_id="per-book licence (LitArch open-access subset)")

    def __init__(self, library: BookshelfLibrary | None = None):
        self.library = library or BookshelfLibrary()

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        books = {a: m for a, m in self.library.synced().items() if m.get("slug")}
        if not books:
            raise ToolAbsent("not_configured", "no open-access book is synced; run `mas sources sync bookshelf --book NBK...`")
        limit = max(1, min(int(inputs.get("limit", 10)), 50))
        query = re.sub(r"\[\w+\]", "", inputs["query"])   # field tags from other search engines do not apply here
        book_filter = " OR ".join(f"{m['slug']}[book]" for m in books.values())
        term = f"({query}) AND ({book_filter})"
        params = {"db": "books", "term": term, "retmode": "json", "retmax": limit * 4}
        if inputs.get("cutoff_date"):
            params.update({"datetype": "pdat", "mindate": "1900/01/01", "maxdate": inputs["cutoff_date"].replace("-", "/")})
        found = http.get(f"{EUTILS}/esearch.fcgi", params=params)
        ids = ((found or {}).get("esearchresult") or {}).get("idlist") or []
        if not ids:
            return ProviderResponse(values=[], records=[{"query": term, "hit_count": 0}], data_version="bookshelf")
        summary = http.get(f"{EUTILS}/esummary.fcgi", params={"db": "books", "id": ",".join(ids), "retmode": "json"})
        result = (summary or {}).get("result") or {}
        chapters: dict[str, dict[str, Any]] = {}
        for uid in result.get("uids", []):
            record = result[uid]
            book = record.get("bookaccessionid")
            chapter = record.get("chapteraccessionid")
            article, section = _article_and_section(record.get("rid", ""))
            if book not in books or not chapter or not article:
                continue
            path = self.library.chapter_path(book, article)
            if not path.exists():
                continue
            hit = chapters.get(chapter)
            if hit is None:
                parsed = jats.parse_bits(path.read_text(encoding="utf-8"))
                lead = " ".join(p["text"] for p in parsed["passages"] if p["kind"] == "abstract")[:2000]
                hit = chapters[chapter] = {
                    "source": "bookshelf", "identifiers": [{"scheme": "nbk", "value": chapter}], "nbk": chapter,
                    "book_accession": book, "article_file": article, "title": parsed["title"],
                    "journal": books[book]["title"], "year": (record.get("pubdate") or "")[:4] or parsed["year"],
                    "first_publication_date": (record.get("pubdate") or "")[:10].replace("/", "-") or None,
                    "authors": "", "is_open_access": True, "in_epmc": False, "pub_types": ["book chapter"],
                    "is_preprint": False, "is_review": True, "abstract_html": lead, "license": books[book].get("license"),
                    "matched_sections": [], "best_rank": len(chapters)}
            if section and section not in hit["matched_sections"]:
                hit["matched_sections"].append(section)
        hits = list(chapters.values())[:limit]
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits],
                                records=[{"query": term, "hit_count": len(ids), "returned": len(hits)}],
                                data_version="bookshelf:" + ",".join(f"{a}@{m['updated']}" for a, m in sorted(books.items())),
                                upstream_refs=[f"bookshelf:esearch:{term}"])


class BookshelfReader:
    contract = ToolContract(
        tool_id="tool_literature_bookshelf_reader", capability="document_reading", capability_kind="document_reading",
        question_kinds=("read",), contract_version="1", implementation_version="bookshelf-litarch-bits-1",
        purpose_statement="Read a synced open-access book chapter with located passages",
        evidence_kind_produced="reference_text", claim_strength_ceiling="curated",
        license_id="per-book licence (recorded on the document)")

    def __init__(self, library: BookshelfLibrary | None = None):
        self.library = library or BookshelfLibrary()

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        hit = inputs.get("hit") or {}
        path = self.library.chapter_path(hit.get("book_accession", ""), hit.get("article_file", ""))
        if not path.exists():
            raise ToolAbsent("not_configured", f"chapter {hit.get('nbk')} is not in a synced book")
        try:
            parsed = jats.parse_bits(path.read_text(encoding="utf-8"))
        except Exception as error:   # malformed XML is a parse failure, not a crash
            raise ToolError("parse_failed", f"{hit.get('nbk')}: {error}", retryable=False) from None
        document = dict(parsed, identifiers={"nbk": hit.get("nbk"), "book": hit.get("book_accession")},
                        access_state="full_text_available", reading_depth="full_text",
                        source_hit={k: hit.get(k) for k in ("nbk", "title", "journal", "year", "pub_types",
                                                            "first_publication_date", "matched_sections")})
        if not document["passages"]:
            return ProviderResponse(values=[], data_version="bookshelf")
        return ProviderResponse(values=[{"name": "document", "value": document, "value_kind": "curated"}],
                                data_version="bookshelf", upstream_refs=[f"nbk:{hit.get('nbk')}"])
