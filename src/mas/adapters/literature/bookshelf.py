"""NCBI Bookshelf open-access books: discovery through E-utilities, text from the LitArch FTP.

NCBI does not allow systematic retrieval from the Bookshelf website; the LitArch
open-access FTP is the sanctioned route for automated access. Each book is published
there as one tarball (StatPearls is about 2 GB because it bundles images), so a book is
*synced* once: the tarball is streamed and only the chapter XML (BITS) is kept. After
that, searching uses E-utilities restricted to synced books and reading is local.

Hits are chapters. A hit's `rid` names the chapter file and the matched section, which
the reader resolves to passages with the publisher's own section ids. A `rid` that names
no section means the whole chapter matched, which is what happens when the query asks for
what a chapter is *about*; those are resolved through the local title index.

E-utilities joins every free-text term with AND, so a long boolean query written for
Europe PMC returns almost nothing here. Search therefore relaxes: the query as written is
tried first, then progressively fewer of its top-level clauses, keeping the ones the synced
corpus says are distinctive (`relaxation_plan`). Every attempt is recorded.

Hits are ordered by what the query asked for: a chapter whose own title *is* a query term first,
then one whose title merely contains a term, then the search engine's own order. Being a drug
monograph is not itself a reason to rank higher — it only breaks ties among chapters the query
already names by title, because that is where a number with a unit can be attributed to a named
compound. An unconditional genre bonus buried every topic and method chapter as soon as one
monograph matched, and the reading budget downstream is spent from the top of this list.
"""

from __future__ import annotations

import csv
import gzip
import html
import io
import json
import math
import os
import re
import tarfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import requests

from mas.core.broker import ProviderResponse, ToolAbsent, ToolContract, ToolError

from . import http, jats

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
LITARCH = "https://ftp.ncbi.nlm.nih.gov/pub/litarch"
FILE_LIST_MAX_AGE_S = 7 * 24 * 3600

INDEX_VERSION = 1
RELAXATION_TARGET = 5        # chapters a query should reach before relaxation stops
MAX_SEARCHES_PER_QUERY = 4   # E-utilities allows ~3 requests/s (http.get throttles); one query may not spend more

_SPACES = re.compile(r"\s+")
_XML_TAG = re.compile(rb"<[^>]+>")
_CHAPTER_TITLE = re.compile(rb"<title-group>\s*<title>(.*?)</title>", re.S)
_WORD = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
_WORD_BYTES = re.compile(rb"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")

# The publisher writes a drug chapter to one fixed template and a disease chapter to another, so
# the chapter's own top-level headings say which kind it is without reading a word of the text.
ENTRY_SECTIONS = ("indications", "mechanism of action", "administration", "adverse effects",
                  "contraindications", "monitoring")


def default_cache_dir() -> Path:
    return Path(os.environ.get("MAS_CACHE") or Path.home() / ".cache" / "mas")


def _words(text: str) -> tuple[str, ...]:
    return tuple(_WORD.findall(html.unescape(text or "").lower()))


def _normalized(title: str) -> str:
    return " ".join(_words(title))


def _stamp(books: dict[str, dict[str, Any]]) -> str:
    """Identifies a set of synced books: accession@last-updated, in accession order."""
    return ",".join(f"{a}@{m.get('updated')}" for a, m in sorted(books.items()))


@dataclass(frozen=True)
class BookshelfIndex:
    """What the synced corpus knows about itself: how many chapters there are, in how many of them
    a word occurs, and which file holds the chapter with a given title."""

    n_documents: int = 0
    frequencies: dict[str, int] = field(default_factory=dict)
    titles: dict[str, str] = field(default_factory=dict)

    def document_frequency(self, word: str) -> int:
        """Chapters containing `word`. 0 means no synced chapter contains it."""
        return self.frequencies.get(word, 0)

    def article_for_title(self, accession: str, title: str) -> str | None:
        return self.titles.get(f"{accession}/{_normalized(title)}")


_INDEX_MEMO: dict[tuple[str, str], BookshelfIndex] = {}


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

    def chapter_files(self, accession: str) -> list[Path]:
        """Chapter XML of one synced book (the book's table of contents is not a chapter)."""
        return [p for p in sorted((self.root / accession).glob("*.nxml")) if p.stem != "TOC"]

    def locate(self, accession: str, rid: str, *, title: str = "",
               index: BookshelfIndex | None = None) -> tuple[str | None, str | None]:
        """Which local file and which section a search result points at.

        A `rid` is either `chapter/file.section` (a section matched) or bare `chapter` (the whole
        chapter matched — what a title or keyword match on a drug entry looks like). Section ids
        and file names both contain dots and vary by book, so the split is decided by what is on
        disk; the bare form is resolved through the title index, which is where drug entries were
        being lost.
        """
        tail = rid.split("/", 1)[1] if "/" in rid else rid
        parts = tail.split(".")
        for cut in range(len(parts), 0, -1):
            stem = ".".join(parts[:cut])
            if "/" in stem or ".." in stem:        # a rid never names a path; do not follow one
                continue
            if self.chapter_path(accession, stem).exists():
                return stem, (tail if cut < len(parts) else None)
        article, section = _article_and_section(rid)   # section ids carrying a prefix, e.g. `table/article-12.t1`
        if article and self.chapter_path(accession, article).exists():
            return article, section
        if index is not None and title:
            stem = index.article_for_title(accession, title)
            if stem and self.chapter_path(accession, stem).exists():
                return stem, None
        return None, None

    # --- the local term and title index ----------------------------------------------
    def stamp(self) -> str:
        return _stamp(self.synced())

    def index(self, *, refresh: bool = False) -> BookshelfIndex:
        """Document frequencies and chapter titles of the synced corpus, built once and cached.

        The index is what lets the searcher decide which terms of a query are distinctive without
        a word list, and what resolves a whole-chapter hit to a file. It is rebuilt when a book is
        re-synced (the stamp changes) and kept in memory for the life of the process.
        """
        stamp = self.stamp()
        key = (str(self.root), stamp)
        if not refresh and key in _INDEX_MEMO:
            return _INDEX_MEMO[key]
        path = self.root / "term_index.json.gz"
        payload = None
        if path.exists() and not refresh:
            try:
                payload = json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
            except Exception:
                payload = None                      # a damaged cache is rebuilt, never fatal
            if payload and (payload.get("version") != INDEX_VERSION or payload.get("stamp") != stamp):
                payload = None                      # a book was re-synced since the index was built
        if payload is None:
            payload = self.build_index(stamp)
            if payload["n_documents"]:
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8"), 6))
                except OSError:
                    pass                            # an unwritable cache costs a rebuild, not a search
        index = BookshelfIndex(payload["n_documents"], payload["frequencies"], payload["titles"])
        _INDEX_MEMO[key] = index
        return index

    def build_index(self, stamp: str | None = None) -> dict[str, Any]:
        """One pass over the synced chapter XML: how many chapters hold each word, and title → file."""
        frequencies: dict[str, int] = {}
        titles: dict[str, str] = {}
        documents = 0
        for accession in sorted(self.synced()):
            for path in self.chapter_files(accession):
                raw = path.read_bytes()
                found = _CHAPTER_TITLE.search(raw)
                if found:
                    title = _normalized(_XML_TAG.sub(b" ", found.group(1)).decode("utf-8", "replace"))
                    if title:
                        titles.setdefault(f"{accession}/{title}", path.stem)
                documents += 1
                for word in set(_WORD_BYTES.findall(_XML_TAG.sub(b" ", raw).lower())):
                    key = word.decode("ascii", "ignore")
                    frequencies[key] = frequencies.get(key, 0) + 1
        return {"version": INDEX_VERSION, "stamp": stamp if stamp is not None else self.stamp(),
                "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "n_documents": documents, "frequencies": frequencies, "titles": titles}

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
        if progress:
            progress(f"{accession}: indexing {kept} chapters")
        self.index(refresh=True)          # the search needs it; building it here, once, not mid-run
        return manifest


def _article_and_section(rid: str) -> tuple[str | None, str | None]:
    """`NBK617063/article-164622.s5` → (`article-164622`, `article-164622.s5`)."""
    tail = rid.split("/", 1)[1] if "/" in rid else rid
    match = re.search(r"((?:[a-z]+-)*article-\d+)(\.[\w.-]+)?", tail)
    if not match:
        return None, None
    return match.group(1), (match.group(0) if match.group(2) else None)


# --- query terms and progressive relaxation ------------------------------------------------

_QUERY_TOKEN = re.compile(r'"[^"]*"|[()]|[^\s()]+')
_OPERATORS = {"and", "or", "not"}       # boolean glue: the only words that are not search terms
_FIELD_TAG = re.compile(r"\[\w+\]")
_RANGE_FILTER = re.compile(r"\b\w+:\s*\[[^\]]*\]")


def _clean_query(query: str) -> str:
    """Drop syntax that belongs to another search engine.

    Field tags (`[tiab]`, `[PUB_TYPE]`) and range filters (`FIRST_PDATE:[1900-01-01 TO 2026-10-13]`)
    have no meaning in Entrez, which searches the leftovers as words and ANDs them — a date filter
    written for Europe PMC takes a query from some hits to none. The cutoff is applied through
    esearch's own `maxdate` parameter instead.
    """
    text = _FIELD_TAG.sub(" ", _RANGE_FILTER.sub(" ", query or ""))
    for _ in range(3):                  # removals can leave empty groups and dangling operators
        text = re.sub(r"\(\s*\)", " ", text)
        text = re.sub(r"\b(AND|OR|NOT)\s*(?=\)|$)", " ", text, flags=re.I)
        text = re.sub(r"(?<=\()\s*\b(AND|OR)\b", " ", text, flags=re.I)
        text = re.sub(r"\b(AND|OR)\s+(?=(AND|OR)\b)", " ", text, flags=re.I)
    return _SPACES.sub(" ", text).strip()


@dataclass(frozen=True)
class _Clause:
    """One piece of a boolean query and the words it looks for."""
    text: str
    start: int = 0
    words: tuple[str, ...] = ()
    phrase: bool = False
    op: str | None = None
    members: tuple[_Clause, ...] = ()
    negated: bool = False


def _parse(query: str) -> _Clause:
    tokens = [(m.group(0), m.start(), m.end()) for m in _QUERY_TOKEN.finditer(query)]
    clause, _ = _parse_expression(query, tokens, 0)
    return clause


def _parse_expression(query: str, tokens: list[tuple[str, int, int]], position: int) -> tuple[_Clause, int]:
    """Parse tokens into one clause, stopping after an unmatched `)`. Returns the next position."""
    members: list[_Clause] = []
    operators: set[str] = set()
    negate = False
    start = tokens[position][1] if position < len(tokens) else 0
    while position < len(tokens):
        text, opens, closes = tokens[position]
        word = text.lower()
        position += 1
        if text == ")":
            break
        if word in _OPERATORS:
            if word == "not":
                negate = True
            else:
                operators.add(word.upper())
            continue
        if text == "(":
            inner, position = _parse_expression(query, tokens, position)
            ends = tokens[position - 1][2] if position else closes
            member = _Clause(text=query[opens:ends], start=opens, words=inner.words, op=inner.op,
                             members=inner.members, negated=negate)
        else:
            words = _words(text)
            member = _Clause(text=text, start=opens, words=words,
                             phrase=text.startswith('"') and len(words) > 1, negated=negate)
        negate = False
        if member.words or member.members:
            members.append(member)
    if len(members) == 1 and not operators:
        return members[0], position
    op = "OR" if "OR" in operators else ("AND" if len(members) > 1 else None)
    ends = tokens[position - 1][2] if position else len(query)
    return _Clause(text=query[start:ends], start=start, op=op, members=tuple(members),
                   words=tuple(w for m in members for w in m.words)), position


def _frequency(clause: _Clause, index: BookshelfIndex) -> int:
    """How many chapters a clause can match, as far as the corpus can tell (an upper bound):
    AND narrows to at most its narrowest member, OR widens to at most the sum of its members,
    and a phrase occurs at most as often as its rarest word."""
    if clause.members:
        counts = [_frequency(m, index) for m in clause.members]
        return min(index.n_documents, sum(counts)) if clause.op == "OR" else min(counts)
    counts = [index.document_frequency(word) for word in clause.words]
    return min(counts) if counts else index.n_documents


def _selectivity(clause: _Clause, index: BookshelfIndex) -> float:
    """How distinctive a clause is, so the least distinctive can be dropped first.

    WHY this definition: E-utilities ANDs every free-text term, so what decides whether a long
    query returns anything is its *rarest* clause, and rarity is measurable here — the corpus being
    searched is on disk, so `log(chapters / chapters containing it)` needs no word list and no
    judgement about which words are "generic". A clause no synced chapter contains can only return
    nothing, so it is dropped before anything else. A quoted phrase gets a small bonus because every
    further word can only narrow it, while the frequency above can only be measured on its rarest
    word. With no corpus measured yet, phrase structure and (in the caller's tie-break) length are
    all that is left.
    """
    frequency = _frequency(clause, index)
    if not index.n_documents:
        score = 0.0
    elif frequency <= 0:
        return -1.0
    else:
        score = math.log(index.n_documents / frequency)
    if clause.phrase:
        score += math.log(len(clause.words))
    return score


def relaxation_plan(query: str, index: BookshelfIndex, *,
                    max_searches: int = MAX_SEARCHES_PER_QUERY) -> list[dict[str, Any]]:
    """The query as written, then progressively fewer of its top-level clauses.

    Each step keeps the more distinctive half of the clauses, so n clauses are reduced to one in
    log2(n) + 1 searches and `max_searches` bounds the spend whatever n is. A query whose top level
    is an OR is already broad: there is nothing to drop, and it is searched once. An excluded
    clause (`NOT x`) is not a term the search needs, so a relaxed attempt leaves it out rather than
    carrying it along and inverting it.
    """
    root = _parse(query)
    members = list(root.members) if root.op == "AND" else []
    clauses = [c for c in members if not c.negated]
    excluded = [f"NOT {c.text}" for c in members if c.negated]
    ranked = sorted(clauses, key=lambda c: (-_selectivity(c, index), -len(c.text)))
    written = [f"NOT {c.text}" if c.negated else c.text for c in members]
    steps = [{"text": query, "terms": written or ([query] if query else []), "dropped": []}]
    keep = len(ranked)
    while len(steps) < max_searches and keep > 1:
        keep = (keep + 1) // 2
        kept = sorted(ranked[:keep], key=lambda c: c.start)
        steps.append({"text": " AND ".join(c.text for c in kept), "terms": [c.text for c in kept],
                      "dropped": [c.text for c in ranked[keep:]] + excluded})
    return steps


# --- monographs: a chapter about what the query asked for ----------------------------------

def _leaf_words(clause: _Clause) -> list[tuple[str, ...]]:
    """The words of every term the query asks for; an excluded term asks for nothing."""
    if clause.negated:
        return []
    if clause.members:
        return [words for member in clause.members for words in _leaf_words(member)]
    return [clause.words] if clause.words else []


def _stems(words: tuple[str, ...]) -> tuple[str, ...]:
    """Fold a plural, so a query for "tyrosine kinase inhibitor" recognises the chapter titled
    "Tyrosine Kinase Inhibitors"."""
    return tuple(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words)


def _title_match(title: str, terms: list[tuple[str, ...]]) -> int:
    """2 when the chapter is titled with a term the query asked for (an entry about it),
    1 when a term merely occurs in the title, 0 otherwise."""
    title_stems = _stems(_words(title))
    best = 0
    for words in terms:
        stems = _stems(words)
        if not stems or len(stems) > len(title_stems):
            continue
        if stems == title_stems:
            return 2
        if any(title_stems[i:i + len(stems)] == stems for i in range(len(title_stems) - len(stems) + 1)):
            best = 1
    return best


def _is_reference_entry(passages: list[dict[str, Any]]) -> bool:
    """Whether the chapter is a drug entry rather than a topic review.

    WHY the chapter's own headings: a drug entry is written to the publisher's drug template
    (Indications, Mechanism of Action, Administration, Adverse Effects, Contraindications,
    Monitoring) and a disease chapter to another one (Etiology, Epidemiology, Pathophysiology,
    History and Physical, Evaluation, Treatment), so the structure says which kind of chapter it is
    without reading a word of the text. It matters because the entry is where a measured quantity —
    bioavailability, half-life, dose — is attributable to the compound the chapter is named after,
    while a topic review mentions compounds without measuring them.
    """
    headings = {(p["section_path"][0].strip().lower() if p.get("section_path") else "") for p in passages}
    return sum(heading in headings for heading in ENTRY_SECTIONS) >= 3


class BookshelfSearch:
    contract = ToolContract(
        tool_id="tool_literature_bookshelf_search", capability="literature_retrieval", capability_kind="source_retrieval",
        question_kinds=("search",), contract_version="1", implementation_version="bookshelf-eutils-search-2",
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
        target = max(1, min(int(inputs.get("min_chapters") or RELAXATION_TARGET), limit))
        query = _clean_query(inputs["query"])
        index = self.library.index()
        book_filter = " OR ".join(f"{m['slug']}[book]" for m in books.values())
        records: list[dict[str, Any]] = []
        ids: list[str] = []
        for attempt, step in enumerate(relaxation_plan(query, index), start=1):
            term = f"({step['text']}) AND ({book_filter})"
            params = {"db": "books", "term": term, "retmode": "json", "retmax": limit * 4}
            if inputs.get("cutoff_date"):
                params.update({"datetype": "pdat", "mindate": "1900/01/01", "maxdate": inputs["cutoff_date"].replace("-", "/")})
            found = http.get(f"{EUTILS}/esearch.fcgi", params=params)
            result = ((found or {}).get("esearchresult") or {})
            returned = result.get("idlist") or []
            # one summary call for the attempts together, and no wider than a single search
            fresh = [uid for uid in returned if uid not in ids][: max(0, limit * 4 - len(ids))]
            ids += fresh
            records.append({"query": term, "attempt": attempt, "terms": step["terms"], "dropped": step["dropped"],
                            "relaxed": attempt > 1, "hit_count": len(returned),
                            "total_count": int(result.get("count") or 0), "new_ids": len(fresh), "target": target})
            if len(ids) >= target:
                break
        searches = len(records)
        version = "bookshelf:" + _stamp(books)
        if not ids:
            records.append({"query": query, "searches": searches, "target": target, "hit_count": 0, "returned": 0})
            return ProviderResponse(values=[], records=records, data_version=version)
        summary = http.get(f"{EUTILS}/esummary.fcgi", params={"db": "books", "id": ",".join(ids), "retmode": "json"})
        result = (summary or {}).get("result") or {}
        position = {uid: rank for rank, uid in enumerate(ids)}
        terms = _leaf_words(_parse(query))
        chapters: dict[str, dict[str, Any]] = {}
        ranking: dict[str, tuple[int, int]] = {}
        for uid in result.get("uids", []):
            record = result[uid]
            book = record.get("bookaccessionid")
            chapter = record.get("chapteraccessionid")
            if book not in books or not chapter or chapter == book:   # the book's own record is not a chapter
                continue
            article, section = self.library.locate(book, record.get("rid", ""), title=record.get("title", ""), index=index)
            if not article:
                continue
            hit = chapters.get(chapter)
            if hit is None:
                parsed = jats.parse_bits(self.library.chapter_path(book, article).read_text(encoding="utf-8"))
                lead = " ".join(p["text"] for p in parsed["passages"] if p["kind"] == "abstract")[:2000]
                entry = _is_reference_entry(parsed["passages"])
                matched = _title_match(parsed["title"], terms)
                hit = chapters[chapter] = {
                    "source": "bookshelf", "identifiers": [{"scheme": "nbk", "value": chapter}], "nbk": chapter,
                    "book_accession": book, "article_file": article, "title": parsed["title"],
                    "journal": books[book]["title"], "year": (record.get("pubdate") or "")[:4] or parsed["year"],
                    "first_publication_date": (record.get("pubdate") or "")[:10].replace("/", "-") or None,
                    "authors": "", "is_open_access": True, "in_epmc": False,
                    "pub_types": ["book chapter", "reference entry" if entry else "review"],
                    "is_preprint": False, "is_review": not entry, "is_reference_entry": entry,
                    "title_matched_query": bool(matched), "abstract_html": lead,
                    "license": books[book].get("license"), "matched_sections": [], "best_rank": len(chapters)}
                # Query-dependent relevance ranks; genre only breaks a tie between chapters the
                # query already names by title. `entry` stays on the hit and in `pub_types` as
                # metadata — it says what the chapter is, not that it answers this query.
                ranking[chapter] = (-matched, -(1 if matched and entry else 0), position.get(uid, len(ids)))
            if section and section not in hit["matched_sections"]:
                hit["matched_sections"].append(section)
        hits = sorted(chapters.values(), key=lambda h: ranking[h["nbk"]])[:limit]
        for rank, hit in enumerate(hits):
            hit["best_rank"] = rank
        records.append({"query": query, "searches": searches, "target": target, "hit_count": len(ids),
                        "returned": len(hits), "reference_entries": sum(1 for h in hits if h["is_reference_entry"])})
        return ProviderResponse(values=[{"name": "search_hit", "value": h, "value_kind": "curated"} for h in hits],
                                records=records, data_version=version,
                                upstream_refs=[f"bookshelf:esearch:{r['query']}" for r in records if "attempt" in r])


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
