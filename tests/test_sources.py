"""Evidence sources: the licence gate, BITS/HTML/text parsing, Bookshelf, MediaWiki, uploads,
GtoPdb affinities, multi-source search, and breadth x depth enumeration. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mas.adapters.drug import gtopdb
from mas.adapters.literature import bookshelf, http, jats, mediawiki, registry, textparse, uploads
from mas.core import config as cfg
from mas.core import derivation, reading
from mas.core.broker import Broker, ProviderResponse, ToolAbsent, ToolContract
from mas.core.models import ModelRoster, ScriptedAdapter

FIXTURES = Path(__file__).parent / "fixtures"


# --- licence gate -----------------------------------------------------------------------

def test_registry_refuses_sources_whose_licence_forbids_model_reading():
    with pytest.raises(registry.SourceRefused, match="forbid"):
        registry.permitted("openstax")
    with pytest.raises(registry.SourceRefused, match="unknown"):
        registry.permitted("somewhere")
    assert [s.source_id for s in registry.resolve(["pubmed", "europepmc", "pubmed"])] == ["pubmed", "europepmc"]
    with pytest.raises(cfg.ConfigError, match="OpenStax"):
        cfg.resolve(project_file=None, environ={}, overrides={"search.sources": "europepmc,openstax"})


# --- parsing ------------------------------------------------------------------------------

def test_bits_chapter_keeps_publisher_section_ids_and_skips_back_matter():
    doc = jats.parse_bits((FIXTURES / "chapter.nxml").read_text(encoding="utf-8"))
    assert doc["title"] == "Exampletinib" and doc["container"] == "Synthetic Pharmacology Pearls"
    assert doc["license"] == "https://creativecommons.org/licenses/by/4.0/"
    ids = {p["passage_id"]: p for p in doc["passages"]}
    assert ids["article-9001.s1.p1"]["kind"] == "abstract"
    assert ids["article-9001.s2.1.p1"]["section_path"] == ["Mechanism of Action", "Selectivity"]
    assert not any("Ignored reference" in p["text"] for p in doc["passages"])


def test_html_and_markdown_become_located_passages():
    html = ('<p>Lead paragraph that summarises the whole page in one go.</p>'
            '<h2>Pharmacokinetics<span class="mw-editsection">[edit]</span></h2>'
            '<p>Oral bioavailability is about 60 percent in adults<sup class="reference">[3]</sup>.</p>'
            '<table class="infobox"><tr><td>should not appear anywhere at all</td></tr></table>'
            '<h2>References</h2><p>Reference text that must be dropped from the passages.</p>')
    passages = textparse.html_passages(html, title="Exampletinib")
    assert [(p["passage_id"], p["kind"]) for p in passages] == [("title", "title"), ("lead.p1", "abstract"), ("s1.p1", "paragraph")]
    assert passages[2]["text"] == "Oral bioavailability is about 60 percent in adults." and passages[2]["section_path"] == ["Pharmacokinetics"]
    md = textparse.text_passages("# Absorption\n\nFood increases exposure by about twofold in healthy volunteers.\n\n"
                                 "## Notes\n\nShort.\n")
    assert [(p["passage_id"], p["section_path"]) for p in md] == [("s1.p1", ["Absorption"])]


# --- Bookshelf -------------------------------------------------------------------------------

def synced_library(tmp_path) -> bookshelf.BookshelfLibrary:
    library = bookshelf.BookshelfLibrary(tmp_path)
    book = library.root / "NBK9"
    book.mkdir(parents=True)
    (book / "article-9001.nxml").write_text((FIXTURES / "chapter.nxml").read_text(encoding="utf-8"), encoding="utf-8")
    (book / "manifest.json").write_text(json.dumps({"accession": "NBK9", "slug": "pearls", "title": "Pearls",
                                                    "updated": "2026-10-01", "chapters": 1, "license": "CC BY"}))
    return library


def test_bookshelf_search_maps_section_hits_to_synced_chapters(tmp_path, monkeypatch):
    library = synced_library(tmp_path)
    calls = []

    def fake_get(url, params=None, **kw):
        calls.append((url, params))
        if url.endswith("esearch.fcgi"):
            return {"esearchresult": {"idlist": ["1", "2", "3"]}}
        return {"result": {"uids": ["1", "2", "3"],
                           "1": {"bookaccessionid": "NBK9", "chapteraccessionid": "NBK100", "rid": "NBK100/article-9001.s2",
                                 "pubdate": "2025/01/01 00:00"},
                           "2": {"bookaccessionid": "NBK9", "chapteraccessionid": "NBK100",
                                 "rid": "NBK100/table/article-9001.table1"},
                           "3": {"bookaccessionid": "NBK777", "chapteraccessionid": "NBK5", "rid": "NBK5/article-1.s1"}}}

    monkeypatch.setattr(http, "get", fake_get)
    reply = bookshelf.BookshelfSearch(library).invoke("search", {"query": '"exampletinib"[tiab] AND VEGFR2', "limit": 5,
                                                                 "cutoff_date": "2025-12-31"})
    hits = [v["value"] for v in reply.values]
    assert len(hits) == 1 and hits[0]["nbk"] == "NBK100" and hits[0]["title"] == "Exampletinib"
    assert hits[0]["matched_sections"] == ["article-9001.s2", "article-9001.table1"]
    assert "pearls[book]" in calls[0][1]["term"] and "[tiab]" not in calls[0][1]["term"]
    assert calls[0][1]["maxdate"] == "2025/12/31"
    document = bookshelf.BookshelfReader(library).invoke("read", {"hit": hits[0]}).values[0]["value"]
    assert document["identifiers"]["nbk"] == "NBK100" and document["reading_depth"] == "full_text"


def test_bookshelf_without_a_synced_book_is_not_configured(tmp_path):
    with pytest.raises(ToolAbsent) as absent:
        bookshelf.BookshelfSearch(bookshelf.BookshelfLibrary(tmp_path)).invoke("search", {"query": "x"})
    assert absent.value.absence_reason == "not_configured"


DRUG_ENTRY_SECTIONS = ("Indications", "Mechanism of Action", "Administration")
TOPIC_SECTIONS = ("Introduction", "Etiology", "Pathophysiology")


def _bits(article: str, title: str, headings, text: str) -> str:
    """A minimal BITS chapter: the section headings decide whether it reads as a drug entry."""
    sections = "".join(f'<sec id="{article}.s{n}"><title>{h}</title><p>{title}: {text}</p></sec>'
                       for n, h in enumerate(headings, 1))
    return ('<book-part-wrapper id="%s" content-type="chapter" dtd-version="2.0">'
            '<book-meta><book-title-group><book-title>Pearls</book-title></book-title-group>'
            '<pub-date><year>2025</year></pub-date></book-meta>'
            '<book-part book-part-type="chapter"><book-part-meta><title-group><title>%s</title></title-group>'
            '</book-part-meta><body>%s</body></book-part></book-part-wrapper>' % (article, title, sections))


def three_chapter_library(tmp_path) -> bookshelf.BookshelfLibrary:
    """Three synced chapters, so document frequency can tell the query's terms apart:
    `exampletinib` is in one chapter, `clearance` in two, `inhibitor` and `oral` in all three,
    and `metabolism` in none."""
    library = bookshelf.BookshelfLibrary(tmp_path)
    book = library.root / "NBK9"
    book.mkdir(parents=True)
    (book / "article-9001.nxml").write_text((FIXTURES / "chapter.nxml").read_text(encoding="utf-8"), encoding="utf-8")
    (book / "article-9002.nxml").write_text(_bits("article-9002", "Solid Tumour Management", TOPIC_SECTIONS,
                                                  "an oral inhibitor is chosen once clearance is known"),
                                            encoding="utf-8")
    (book / "article-9003.nxml").write_text(_bits("article-9003", "Monotinib", DRUG_ENTRY_SECTIONS,
                                                  "oral inhibitor with a clearance of 20 L/h"), encoding="utf-8")
    (book / "manifest.json").write_text(json.dumps({"accession": "NBK9", "slug": "pearls", "title": "Pearls",
                                                    "updated": "2026-10-01", "chapters": 3, "license": "CC BY"}))
    return library


LONG_QUERY = "exampletinib AND clearance AND inhibitor AND oral AND metabolism"


def _esummary(uids: dict[str, dict]) -> dict:
    return {"result": dict({"uids": list(uids)}, **uids)}


def test_bookshelf_relaxes_a_long_query_and_records_every_attempt(tmp_path, monkeypatch):
    library = three_chapter_library(tmp_path)
    searches = []

    def fake_get(url, params=None, **kw):
        if url.endswith("esearch.fcgi"):
            searches.append(params["term"])
            return {"esearchresult": {"count": "9", "idlist": ["1"] if len(searches) == 1 else ["1", "2", "3", "4", "5"]}}
        return _esummary({"1": {"bookaccessionid": "NBK9", "chapteraccessionid": "NBK100", "rid": "NBK100/article-9001.s2"}})

    monkeypatch.setattr(http, "get", fake_get)
    reply = bookshelf.BookshelfSearch(library).invoke("search", {"query": LONG_QUERY, "limit": 25})
    attempts = [r for r in reply.records if "attempt" in r]
    # the query as written first, then only its most distinctive clauses; the term the corpus does
    # not contain at all goes first, then the words every chapter has, keeping the rarest
    assert len(attempts) == 2 and len(searches) == 2 and attempts[0]["terms"] == LONG_QUERY.split(" AND ")
    assert attempts[1]["terms"] == ["exampletinib", "clearance", "inhibitor"]
    assert attempts[1]["dropped"] == ["oral", "metabolism"] and attempts[1]["relaxed"]
    assert "(exampletinib AND clearance AND inhibitor) AND (pearls[book])" == searches[1]
    assert reply.records[-1] == {"query": LONG_QUERY, "searches": 2, "target": 5, "hit_count": 5, "returned": 1,
                                 "reference_entries": 0}


def test_bookshelf_relaxation_is_bounded_and_stops_when_terms_run_out(tmp_path, monkeypatch):
    library = three_chapter_library(tmp_path)
    searches, calls = [], []

    def fake_get(url, params=None, **kw):
        calls.append(url)
        if url.endswith("esearch.fcgi"):
            searches.append(params["term"])
            return {"esearchresult": {"count": "1", "idlist": ["1"]}}
        return _esummary({"1": {"bookaccessionid": "NBK9", "chapteraccessionid": "NBK100", "rid": "NBK100/article-9001.s2"}})

    monkeypatch.setattr(http, "get", fake_get)
    reply = bookshelf.BookshelfSearch(library).invoke("search", {"query": LONG_QUERY, "limit": 25})
    attempts = [r for r in reply.records if "attempt" in r]
    # the target is never reached, so relaxation stops at the search bound, halving the terms each
    # time; the whole query costs that many searches plus the one summary call
    assert len(searches) == bookshelf.MAX_SEARCHES_PER_QUERY == len(attempts)
    assert len(calls) == bookshelf.MAX_SEARCHES_PER_QUERY + 1
    assert [len(a["terms"]) for a in attempts] == [5, 3, 2, 1] and attempts[-1]["terms"] == ["exampletinib"]
    assert len(reply.values) == 1          # the one chapter the single id resolves to


def test_bookshelf_ranks_a_drug_entry_above_a_topic_chapter(tmp_path, monkeypatch):
    library = three_chapter_library(tmp_path)

    def fake_get(url, params=None, **kw):
        if url.endswith("esearch.fcgi"):
            return {"esearchresult": {"count": "2", "idlist": ["1", "2"]}}
        return _esummary({"1": {"bookaccessionid": "NBK9", "chapteraccessionid": "NBK200", "rid": "NBK200/article-9002.s2"},
                          "2": {"bookaccessionid": "NBK9", "chapteraccessionid": "NBK300", "rid": "NBK300/article-9003.s1"}})

    monkeypatch.setattr(http, "get", fake_get)
    reply = bookshelf.BookshelfSearch(library).invoke("search", {"query": "monotinib clearance", "limit": 5,
                                                                 "min_chapters": 1})
    hits = [v["value"] for v in reply.values]
    # the search engine returned the topic chapter first; the entry the query named outranks it
    assert [h["title"] for h in hits] == ["Monotinib", "Solid Tumour Management"]
    assert [h["best_rank"] for h in hits] == [0, 1]
    assert hits[0]["is_reference_entry"] and not hits[0]["is_review"] and hits[0]["title_matched_query"]
    assert hits[0]["pub_types"] == ["book chapter", "reference entry"]
    assert hits[1]["is_review"] and not hits[1]["is_reference_entry"]
    assert hits[1]["pub_types"] == ["book chapter", "review"]
    # reading.search keeps the provider's order, so the entry is the first hit the reader sees
    assert reply.records[-1]["reference_entries"] == 1


# a drug entry and a topic chapter of the three-chapter library, as esummary returns them
ENTRY_RECORD = {"bookaccessionid": "NBK9", "chapteraccessionid": "NBK300", "rid": "NBK300/article-9003.s1"}
TOPIC_RECORD = {"bookaccessionid": "NBK9", "chapteraccessionid": "NBK200", "rid": "NBK200/article-9002.s2"}


def _fake_eutils(records: dict[str, dict]):
    """esearch returning the given uids in order, and the matching esummary."""
    def fake_get(url, params=None, **kw):
        if url.endswith("esearch.fcgi"):
            return {"esearchresult": {"count": str(len(records)), "idlist": list(records)}}
        return _esummary(records)
    return fake_get


def test_bookshelf_genre_alone_does_not_outrank_a_query_match(tmp_path, monkeypatch):
    """Being a drug entry is not relevance: it used to be added to every hit's score, so one
    monograph that merely mentioned a query word buried the chapter the query was about."""
    library = three_chapter_library(tmp_path)
    # the search engine puts the entry first; the query names the topic chapter by title
    monkeypatch.setattr(http, "get", _fake_eutils({"1": ENTRY_RECORD, "2": TOPIC_RECORD}))
    hits = [v["value"] for v in bookshelf.BookshelfSearch(library).invoke(
        "search", {"query": "solid tumour management clearance", "limit": 5, "min_chapters": 1}).values]
    assert [h["title"] for h in hits] == ["Solid Tumour Management", "Monotinib"]
    assert hits[0]["title_matched_query"] and not hits[1]["title_matched_query"]
    # the genre is still reported on the hit; it just does not rank
    assert hits[1]["is_reference_entry"] and hits[1]["pub_types"] == ["book chapter", "reference entry"]
    assert not hits[1]["is_review"] and hits[0]["is_review"]
    # with no title matching the query at all, the search engine's own order is kept
    monkeypatch.setattr(http, "get", _fake_eutils({"1": TOPIC_RECORD, "2": ENTRY_RECORD}))
    hits = [v["value"] for v in bookshelf.BookshelfSearch(library).invoke(
        "search", {"query": "clearance", "limit": 5, "min_chapters": 1}).values]
    assert [h["title"] for h in hits] == ["Solid Tumour Management", "Monotinib"]


def test_bookshelf_prefers_a_reference_entry_among_equal_title_matches(tmp_path, monkeypatch):
    """Genre still breaks a tie between chapters the query already names by title."""
    library = three_chapter_library(tmp_path)
    monkeypatch.setattr(http, "get", _fake_eutils({"1": TOPIC_RECORD, "2": ENTRY_RECORD}))
    hits = [v["value"] for v in bookshelf.BookshelfSearch(library).invoke(
        "search", {"query": '"solid tumour management" monotinib', "limit": 5, "min_chapters": 1}).values]
    assert all(h["title_matched_query"] for h in hits)
    assert [h["title"] for h in hits] == ["Monotinib", "Solid Tumour Management"]


def test_bookshelf_resolves_a_whole_chapter_hit_through_the_title_index(tmp_path, monkeypatch):
    library = three_chapter_library(tmp_path)
    assert library.index().article_for_title("NBK9", "Monotinib") == "article-9003"

    def fake_get(url, params=None, **kw):
        if url.endswith("esearch.fcgi"):
            return {"esearchresult": {"count": "2", "idlist": ["1", "2"]}}
        # a whole-chapter match carries no section, and the book's own record is not a chapter
        return _esummary({"1": {"bookaccessionid": "NBK9", "chapteraccessionid": "NBK300", "rid": "NBK300",
                                "title": "Monotinib"},
                          "2": {"bookaccessionid": "NBK9", "chapteraccessionid": "NBK9", "rid": "NBK9",
                                "title": "Pearls"}})

    monkeypatch.setattr(http, "get", fake_get)
    hits = [v["value"] for v in bookshelf.BookshelfSearch(library).invoke(
        "search", {"query": "monotinib", "min_chapters": 1}).values]
    assert [(h["nbk"], h["article_file"], h["matched_sections"]) for h in hits] == [("NBK300", "article-9003", [])]


def test_bookshelf_drops_query_syntax_written_for_another_search_engine(tmp_path, monkeypatch):
    library = three_chapter_library(tmp_path)
    searches = []

    def fake_get(url, params=None, **kw):
        if url.endswith("esearch.fcgi"):
            searches.append(params["term"])
            return {"esearchresult": {"count": "0", "idlist": []}}
        raise AssertionError("no summary call without ids")

    monkeypatch.setattr(http, "get", fake_get)
    reply = bookshelf.BookshelfSearch(library).invoke("search", {
        "query": '("exampletinib"[tiab] OR "monotinib") AND clearance AND FIRST_PDATE:[1900-01-01 TO 2026-10-13]',
        "cutoff_date": "2026-10-13", "limit": 5})
    # Entrez has no such fields; left in place they would be ANDed in as words and return nothing
    assert all("FIRST_PDATE" not in term and "[tiab]" not in term for term in searches)
    assert searches[0] == '(("exampletinib" OR "monotinib") AND clearance) AND (pearls[book])'
    assert reply.values == [] and reply.records[-1]["returned"] == 0


# --- MediaWiki -------------------------------------------------------------------------------

def test_wiki_reader_reads_the_revision_in_force_at_the_cutoff(monkeypatch):
    seen = []

    def fake_get(url, params=None, **kw):
        seen.append(params)
        if params.get("prop") == "revisions":
            return {"query": {"pages": [{"revisions": [{"revid": 111, "timestamp": "2024-05-01T00:00:00Z"}]}]}}
        return {"parse": {"title": "Exampletinib",
                          "text": "<p>Exampletinib is an oral kinase inhibitor approved in some countries.</p>"
                                  "<h2>Pharmacology</h2><p>It inhibits VEGFR2 with nanomolar potency in cell assays.</p>"}}

    monkeypatch.setattr(http, "get", fake_get)
    reply = mediawiki.MediaWikiReader("wikipedia").invoke("read", {"hit": {"pageid": 5, "title": "Exampletinib"},
                                                                    "cutoff_date": "2024-06-30"})
    document = reply.values[0]["value"]
    assert seen[0]["rvstart"] == "2024-06-30T23:59:59Z" and seen[0]["rvdir"] == "older"
    assert seen[1]["oldid"] == 111 and document["identifiers"]["revid"] == "111"
    assert document["identifiers"]["url"].endswith("oldid=111") and len(document["passages"]) == 3


# --- uploads ---------------------------------------------------------------------------------

def test_uploads_are_read_only_when_the_manifest_permits_it(tmp_path):
    (tmp_path / "ok.md").write_text("# Absorption\n\nExampletinib absorption doubles with a high-fat meal in volunteers.\n")
    (tmp_path / "no.md").write_text("# Secret\n\nExampletinib text that the owner did not clear for model reading.\n")
    (tmp_path / "stray.txt").write_text("Exampletinib stray file that nobody declared in the manifest.\n")
    (tmp_path / "manifest.toml").write_text(
        '[[document]]\nfile = "ok.md"\ntitle = "Food effects"\nlicense = "own work"\nllm_ingestion_permitted = true\n'
        '[[document]]\nfile = "no.md"\nlicense = "all rights reserved"\nllm_ingestion_permitted = false\n')
    library = uploads.UploadLibrary(tmp_path)
    report = library.check()
    assert report["readable"] == ["ok.md"] and len(report["refused"]) == 2
    hits = [v["value"] for v in uploads.UploadsSearch(library).invoke("search", {"query": '("exampletinib") AND food'}).values]
    assert [h["upload_file"] for h in hits] == ["ok.md"]
    document = uploads.UploadsReader(library).invoke("read", {"hit": hits[0]}).values[0]["value"]
    assert document["passages"][1]["section_path"] == ["Absorption"]
    (tmp_path / "ok.md").write_text("changed after it was found, so the reader must refuse it\n")
    with pytest.raises(Exception, match="changed"):
        uploads.UploadsReader(library).invoke("read", {"hit": hits[0]})


# --- GtoPdb ------------------------------------------------------------------------------------

def test_gtopdb_affinities_match_by_inchikey_and_uniprot(tmp_path):
    root = tmp_path / "gtopdb"
    root.mkdir()
    (root / "ligands.csv").write_text('"# GtoPdb Version: 2026.3"\n"Ligand ID","Name","InChIKey"\n"7","exampletinib","AAAA-BBBB-C"\n')
    (root / "interactions.csv").write_text(
        '"# GtoPdb Version: 2026.3"\n'
        '"Ligand ID","Target UniProt ID","Target Species","Affinity Units","Affinity High","Affinity Median","Affinity Low",'
        '"Original Affinity Relation","Action","Type","Selectivity","Primary Target","Assay Description","PubMed ID"\n'
        '"7","P35968","Human","pIC50","","8.5","","=","Inhibition","Inhibitor","","true","","123"\n'
        '"7","P35968","Human","pKd","8.9","","8.1","","Binding","Inhibitor","","false","","124"\n'
        '"7","P35968","Mouse","pIC50","","9.9","","=","Inhibition","Inhibitor","","","","125"\n'
        '"7","P35968","Human","pIC50","","5.0","",">","Inhibition","Inhibitor","","","","126"\n')
    (root / "chembl_target_uniprot.json").write_text(json.dumps({"CHEMBL279": ["P35968"]}))
    tool = gtopdb.GtoPdbAffinity(gtopdb.GtoPdbData(tmp_path))
    values = tool.invoke("gtopdb_affinity", {"identifier": "AAAA-BBBB-C", "target_chembl_id": "CHEMBL279"}).values
    assert [(v.get("value"), v.get("value_low"), v.get("value_high")) for v in values] == [(8.5, None, None), (None, 8.1, 8.9)]
    assert values[0]["unit"] == "pChEMBL" and values[0]["conditions"]["gtopdb_version"] == "GtoPdb Version: 2026.3"
    assert tool.invoke("gtopdb_affinity", {"identifier": "ZZZZ", "target_chembl_id": "CHEMBL279"}).values == []


# --- multi-source search and breadth x depth ---------------------------------------------------

def tool(tool_id, capability, kind, invoke):
    class T:
        contract = ToolContract(tool_id=tool_id, capability=capability, capability_kind=kind,
                                question_kinds=("search",) if capability == "literature_retrieval" else ("read",),
                                contract_version="1", implementation_version="f", purpose_statement="t",
                                evidence_kind_produced="peer_reviewed", claim_strength_ceiling="curated")
    T.invoke = staticmethod(lambda q, inputs: invoke(inputs))
    return T()


def paper(n):
    return {"doi": f"10.1/p{n}", "title": f"Paper {n}", "pmcid": f"PMC{n}", "is_review": True,
            "identifiers": [{"scheme": "doi", "value": f"10.1/p{n}"}]}


def unconfigured(inputs):
    raise ToolAbsent("not_configured", "nothing synced")


def test_search_queries_each_source_and_records_unavailable_ones(core):
    broker = Broker(core)
    broker.register(tool("tool_literature_europepmc_search", "literature_retrieval", "source_retrieval",
                         lambda i: ProviderResponse(values=[{"name": "search_hit", "value": paper(1), "value_kind": "curated"}])))
    broker.register(tool("tool_literature_bookshelf_search", "literature_retrieval", "source_retrieval", unconfigured))
    broker.register(tool("tool_literature_wikipedia_search", "literature_retrieval", "source_retrieval",
                         lambda i: ProviderResponse(values=[{"name": "search_hit", "value": dict(paper(1)), "value_kind": "curated"},
                                                            {"name": "search_hit", "value": {"title": "Wiki page", "pageid": 9,
                                                             "identifiers": [{"scheme": "wikipedia", "value": "9"}]},
                                                             "value_kind": "curated"}])))
    hits, coverage_id = reading.search(core, broker, "run_x", ["q1", "q2"], cutoff_date=None,
                                       sources=["europepmc", "bookshelf", "wikipedia"])
    coverage = core.artifacts.payload(coverage_id)
    assert coverage["sources_unavailable"] == {"bookshelf": "not_configured"}
    assert coverage["hits_by_source"] == {"europepmc": 1, "wikipedia": 1}
    assert {h["source"] for h in hits} == {"europepmc", "wikipedia"} and len(hits) == 2
    assert not coverage["retrieval_failures"]


def test_search_coverage_records_what_each_source_was_actually_asked(core):
    """The provider's own records — for Bookshelf the relaxation attempts, with the terms sent and
    dropped — reach the search_coverage artifact, not only the broker's tool-result artifact."""
    attempts = [{"query": "(a AND b) AND (pearls[book])", "attempt": 1, "terms": ["a", "b"], "dropped": [],
                 "relaxed": False, "hit_count": 0},
                {"query": "(a) AND (pearls[book])", "attempt": 2, "terms": ["a"], "dropped": ["b"],
                 "relaxed": True, "hit_count": 1}]
    broker = Broker(core)
    broker.register(tool("tool_literature_bookshelf_search", "literature_retrieval", "source_retrieval",
                         lambda i: ProviderResponse(values=[{"name": "search_hit", "value": paper(1), "value_kind": "curated"}],
                                                    records=[dict(a) for a in attempts])))
    broker.register(tool("tool_literature_europepmc_search", "literature_retrieval", "source_retrieval",
                         lambda i: ProviderResponse(values=[{"name": "search_hit", "value": paper(2), "value_kind": "curated"}])))
    _, coverage_id = reading.search(core, broker, "run_y", ["a AND b"], cutoff_date=None,
                                    sources=["bookshelf", "europepmc"])
    counts = {c["source"]: c for c in core.artifacts.payload(coverage_id)["result_counts"]}
    # the keys other code and tests read are unchanged; the provider detail sits under one new key
    assert set(counts["bookshelf"]) == {"query", "source", "returned", "tool_id", "provider_records"}
    assert counts["bookshelf"]["query"] == "a AND b" and counts["bookshelf"]["returned"] == 1
    assert counts["bookshelf"]["tool_id"] == "tool_literature_bookshelf_search"
    assert [r["terms"] for r in counts["bookshelf"]["provider_records"]] == [["a", "b"], ["a"]]
    assert counts["bookshelf"]["provider_records"][1]["dropped"] == ["b"]
    assert counts["europepmc"]["provider_records"] == []        # a provider that records nothing


def test_reading_order_reads_a_reference_entry_with_the_reviews():
    """Honest genre flags give a drug monograph is_review=False; it must not therefore sort below
    every review, because that put it out of reach of the per-dimension document budget."""
    review = {"title": "Review", "is_review": True, "pmcid": "PMC1", "found_by": ["q"], "best_rank": 3}
    entry = {"title": "Monotinib", "is_review": False, "is_reference_entry": True, "source": "bookshelf",
             "found_by": ["q"], "best_rank": 1}
    primary = {"title": "Trial report", "is_review": False, "pmcid": "PMC2", "found_by": ["q", "q2"], "best_rank": 0}
    assert [h["title"] for h in sorted([primary, review, entry], key=derivation.reading_order)] == [
        "Monotinib", "Review", "Trial report"]
    # among equally preferred genres the earlier keys still decide: reachable full text, then
    # how many queries found the hit, then the source's own rank
    entry_unreachable = dict(entry, source="mediawiki", title="Unreachable entry")
    assert [h["title"] for h in sorted([entry_unreachable, review], key=derivation.reading_order)] == [
        "Review", "Unreachable entry"]


def test_enumeration_runs_follow_up_rounds_with_decaying_breadth(core):
    rounds_seen = []

    def script(request):
        if request.role == "retriever":
            prompt = request.messages[0]["content"]
            rounds_seen.append(("follow-up" in prompt, prompt.rsplit("up to ", 1)[1]))
            return {"queries": [{"query": f"q{len(rounds_seen)}-{i}", "rationale": "r"} for i in range(4)]}
        if request.role == "reader":
            text = request.messages[0]["content"]
            n = text.split("Paper ")[1].split()[0] if "Paper " in text else "0"
            return {"claims": [{"passage_id": "sec1.p1", "quoted_span": f"topic {n} matters", "statement": f"topic {n}",
                                "determination_basis": "measured", "polarity": "supports", "attribute_hint": f"topic {n}"}]}
        raise AssertionError(request.role)

    served = {"n": 0}

    def search_tool(inputs):
        served["n"] += 1
        return ProviderResponse(values=[{"name": "search_hit", "value": paper(served["n"]), "value_kind": "curated"}])

    def read_tool(inputs):
        hit = inputs["hit"]
        n = hit["title"].split()[-1]
        return ProviderResponse(values=[{"name": "document", "value": {
            "title": hit["title"], "access_state": "full_text_available", "reading_depth": "full_text",
            "source_hit": {"is_preprint": False},
            "passages": [{"passage_id": "sec1.p1", "kind": "paragraph", "section_path": [], "text": f"Paper {n}: topic {n} matters."}]},
            "value_kind": "curated"}])

    broker = Broker(core)
    broker.register(tool("tool_s", "literature_retrieval", "source_retrieval", search_tool))
    broker.register(tool("tool_r", "document_reading", "document_reading", read_tool))
    roster = ModelRoster({"s": ScriptedAdapter("s", script)}, {"retriever": "s", "reader": "s"})
    out = derivation.enumerate_dimension(
        core, broker, roster, "task_x", task_context={"objective_text": "Rank oral inhibitors", "scope_entities": []},
        dimension={"dimension": "pk", "focus": "pharmacokinetics"}, cutoff_date=None,
        research={"breadth": 4, "depth": 3, "breadth_decay": 0.5, "results_per_query": 5, "max_documents": 50,
                  "max_records_screened": 100, "saturation_stop": 0.0, "sources": None})
    assert rounds_seen == [(False, "4 queries."), (True, "2 queries."), (True, "1 queries.")]
    assert [r["queries"] for r in out["rounds"]] == [4, 2, 1] and out["stop_reason"] == "depth_reached"
    assert out["documents_read"] == 7 and len(out["hints"]) == 7
