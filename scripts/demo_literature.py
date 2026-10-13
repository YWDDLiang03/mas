"""Demo: plan queries → search → read → summarize → extract checked claims, with LLM roles
answered through the subagent bridge. Usage: python scripts/demo_literature.py STORE_DIR EXCHANGE_DIR"""

import json
import sys
from pathlib import Path

from mas.adapters.literature.europepmc import EuropePMCReader, EuropePMCSearch
from mas.adapters.literature.pubmed import PubMedSearch
from mas.core import reading
from mas.core.broker import Broker
from mas.core.models import ExchangeAdapter, ModelRoster
from mas.core.runtime import Core

store_dir, exchange_dir = Path(sys.argv[1]), Path(sys.argv[2])
bridge = ExchangeAdapter("subagents", exchange_dir, model="claude-opus (subagent)", poll_s=1.0, timeout_s=3600)
roster = ModelRoster({"subagents": bridge}, {r: "subagents" for r in ("retriever", "reader", "summarizer")})
objective = "Assess oral bioavailability of approved kinase inhibitors for an oral-administration constraint"
candidate = {"candidate_id": "cand_name-imatinib", "labels": ["imatinib", "Gleevec", "STI571", "STI-571"]}
attribute = {"name": "Oral bioavailability", "definition": "Fraction of an oral dose reaching systemic circulation (F, %)",
             "unit": "%", "ref": "attr_oral-bioavailability@v1"}
with Core.open(store_dir) as core:
    broker = Broker(core)
    for provider in (EuropePMCSearch(), PubMedSearch(), EuropePMCReader()):
        broker.register(provider)
    stream = "run_demo"
    queries = reading.plan_queries(core, roster, stream, objective_text=objective,
                                   focus="oral bioavailability of imatinib in humans", entity_labels=candidate["labels"],
                                   max_queries=4)
    print("queries:", [q["query"] for q in queries], flush=True)
    hits, coverage = reading.search(core, broker, stream, [q["query"] for q in queries], cutoff_date="2026-10-13",
                                    limit_per_query=10, open_access_only=True)
    print("unique hits:", len(hits), flush=True)
    report = {"queries": queries, "documents": []}
    for hit in [h for h in hits if h.get("pmcid")][:2]:
        document = reading.read(core, broker, stream, hit)
        if not document:
            continue
        summary = reading.summarize(core, roster, stream, document, focus=attribute["name"] + " of imatinib",
                                    terms=candidate["labels"] + [attribute["name"]])
        claims = reading.extract_claims(core, roster, stream, document, {
            "purpose": "candidate_attribute", "objective_text": objective, "attribute": attribute, "candidate": candidate})
        report["documents"].append({
            "source_id": document["source_id"], "title": document["title"], "reading_depth": document["reading_depth"],
            "n_passages": len(document["passages"]), "summary_points": [p["point"] for p in summary["key_points"]],
            "claims": [{"state": c["admission_state"], "reasons": c["admission_reasons"], "statement": c["normalized_statement"],
                        "quote": c["location"]["quoted_span"], "passage": c["location"]["locator_value"], "value": c["value"],
                        "unit": c["unit"]} for c in claims]})
        print("read:", document["source_id"], "claims:", len(claims), flush=True)
    (exchange_dir / "DONE").write_text("done")
    print(json.dumps(report, indent=1, ensure_ascii=False))
