"""Live checks against Europe PMC and PubMed. Run with: pytest -m live"""

import pytest

from mas.adapters.literature.europepmc import EuropePMCReader, EuropePMCSearch
from mas.adapters.literature.pubmed import PubMedSearch
from mas.core import reading
from mas.core.broker import Broker
from mas.core.runtime import Core

pytestmark = pytest.mark.live


@pytest.fixture
def core(tmp_path):
    with Core.open(tmp_path / "root") as c:
        yield c


def test_europepmc_search_and_full_text_read(core):
    broker = Broker(core)
    broker.register(EuropePMCSearch())
    broker.register(EuropePMCReader())
    hits, coverage_id = reading.search(core, broker, "run_live", ['imatinib AND "oral bioavailability"'],
                                       cutoff_date="2026-10-13", limit_per_query=10, open_access_only=True)
    assert hits, core.artifacts.payload(coverage_id)
    with_pmc = [h for h in hits if h.get("pmcid")]
    assert with_pmc
    document = reading.read(core, broker, "run_live", with_pmc[0])
    assert document is not None
    assert document["access_state"] in ("full_text_available", "abstract_only")
    assert any(p["kind"] in ("paragraph", "abstract") for p in document["passages"])


def test_pubmed_fallback_search(core):
    broker = Broker(core)
    broker.register(PubMedSearch())
    hits, _ = reading.search(core, broker, "run_live", ["imatinib pharmacokinetics"], cutoff_date="2026-10-13",
                             limit_per_query=5)
    assert hits and all(h.get("pmid") for h in hits)


# --- sources added in iteration 2 ------------------------------------------------------------

def test_live_bookshelf_finds_and_reads_a_synced_chapter():
    from mas.adapters.literature import bookshelf
    library = bookshelf.BookshelfLibrary()
    if "NBK430685" not in library.synced():
        pytest.skip("StatPearls not synced (mas sources sync bookshelf --book NBK430685)")
    hits = [v["value"] for v in bookshelf.BookshelfSearch(library).invoke("search", {"query": "imatinib", "limit": 5}).values]
    assert hits and all(h["source"] == "bookshelf" and h["nbk"].startswith("NBK") for h in hits)
    document = bookshelf.BookshelfReader(library).invoke("read", {"hit": hits[0]}).values[0]["value"]
    assert document["reading_depth"] == "full_text" and len(document["passages"]) > 5
    assert document["license"].startswith("https://creativecommons.org/")


def test_live_bookshelf_relaxes_a_multi_term_dimension_query():
    """A query of the shape the planner writes for Europe PMC returned one chapter or none,
    because E-utilities ANDs every term; relaxation has to reach several."""
    from mas.adapters.literature import bookshelf
    library = bookshelf.BookshelfLibrary()
    if "NBK430685" not in library.synced():
        pytest.skip("StatPearls not synced (mas sources sync bookshelf --book NBK430685)")
    reply = bookshelf.BookshelfSearch(library).invoke("search", {
        "query": "oral bioavailability absorption food effect tyrosine kinase inhibitor",
        "limit": 25, "cutoff_date": "2026-10-13"})
    hits = [v["value"] for v in reply.values]
    attempts = [r for r in reply.records if "attempt" in r]
    assert len(hits) >= 5, reply.records
    assert 1 < len(attempts) <= bookshelf.MAX_SEARCHES_PER_QUERY
    assert [len(a["terms"]) for a in attempts] == sorted((len(a["terms"]) for a in attempts), reverse=True)
    assert any(h["is_reference_entry"] for h in hits), [h["title"] for h in hits]
    assert hits[0]["is_reference_entry"] or not any(h["is_reference_entry"] for h in hits)


@pytest.mark.parametrize("site", ["wikipedia", "wikibooks"])
def test_live_mediawiki_search_and_revision_pinned_read(site):
    from mas.adapters.literature import mediawiki
    query = "imatinib" if site == "wikipedia" else "receptor tyrosine kinase"
    hits = [v["value"] for v in mediawiki.MediaWikiSearch(site).invoke("search", {"query": query, "limit": 3}).values]
    assert hits
    document = mediawiki.MediaWikiReader(site).invoke("read", {"hit": hits[0], "cutoff_date": "2025-06-30"}).values[0]["value"]
    assert document["identifiers"]["revid"] and document["revision_timestamp"] <= "2025-06-30T23:59:59Z"
    assert any(p["kind"] == "paragraph" for p in document["passages"])


def test_live_gtopdb_affinity_for_a_known_pair():
    from mas.adapters.drug import gtopdb
    values = gtopdb.GtoPdbAffinity().invoke("gtopdb_affinity", {"identifier": "KTUFNOKKBVMGRW-UHFFFAOYSA-N",   # imatinib
                                                                "target_chembl_id": "CHEMBL1862"}).values          # ABL1
    assert values and all(v["unit"] == "pChEMBL" for v in values)
    assert any(5 <= (v.get("value") or v.get("value_high") or 0) <= 10 for v in values)
