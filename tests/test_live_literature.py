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
