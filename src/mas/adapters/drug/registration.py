"""Drug adapter v1: registration of tools, identity rules, and criterion templates (design §2.1).

The core never imports this module; a composition root (the CLI or a script) calls
`register(broker)` and passes `ADAPTER` to the run controller.
"""

from __future__ import annotations

from mas.adapters.literature.europepmc import EuropePMCReader, EuropePMCSearch
from mas.adapters.literature.pubmed import PubMedSearch

from .chembl import ChEMBLBioactivity, TargetCache
from .pubchem import PubChemIdentity, PubChemProperty
from .universe import UniverseIdentity, UniverseRecordField

ADAPTER = {"adapter_id": "drug_prioritization", "adapter_version": "1", "primary_scheme": "inchikey"}

# Adapter capability labels bound to core capability kinds (ADR-29).
CAPABILITY_BINDINGS = {
    "identity_resolution": "entity_resolution",
    "interaction_evidence_lookup": "relationship_evidence_lookup",
    "interaction_estimate": "relationship_estimate",
    "property_estimate": "attribute_estimate",
    "literature_retrieval": "source_retrieval",
    "record_field_lookup": "attribute_estimate",
}

# Evidence kinds the adapter's sources produce (used in attributes' acceptable_value_sources).
EVIDENCE_KINDS = ("curated_measurement", "database_entry", "peer_reviewed", "preprint")


def register(broker, *, literature: bool = True, universe_file: str | None = None) -> None:
    """Register the adapter's tools. With a universe file, identity resolves from it first (PubChem stays as fallback)
    and target bioactivity is fetched once per target."""
    if universe_file:
        broker.register(UniverseIdentity(universe_file))
        broker.register(UniverseRecordField(universe_file))
    for provider in (PubChemIdentity(), PubChemProperty(), ChEMBLBioactivity(TargetCache() if universe_file else None)):
        broker.register(provider)
    if literature:
        for provider in (EuropePMCSearch(), PubMedSearch(), EuropePMCReader()):
            broker.register(provider)

# What the proposer may bind an attribute's evidence_request to. Parameters in angle
# brackets are filled by the proposer; {names} is filled per candidate at run time.
EVIDENCE_CATALOG = [
    {"capability": "property_estimate", "question_kind": "computed_property", "identifier_scheme": "inchikey",
     "parameters": {"property": "<one of MolecularWeight, XLogP, TPSA, HBondDonorCount, HBondAcceptorCount, "
                                "RotatableBondCount, HeavyAtomCount>"},
     "units": {"MolecularWeight": "g/mol", "XLogP": "log units", "TPSA": "Å²", "HBondDonorCount": "count",
               "HBondAcceptorCount": "count", "RotatableBondCount": "count", "HeavyAtomCount": "count"},
     "evidence_kind": "database_entry", "determination_basis": "derived",
     "note": "Computed descriptors from PubChem; derived values, never measurements."},
    {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values", "identifier_scheme": "inchikey",
     "parameters": {"target_chembl_id": "<a ChEMBL target id from the task's scope entities>"},
     "units": {"pchembl_value": "pChEMBL"}, "evidence_kind": "curated_measurement", "determination_basis": "measured",
     "note": "Curated potency records (pChEMBL = -log10 molar IC50/Ki/Kd/EC50) against one target; use aggregation max."},
    {"capability": "literature_retrieval", "question_kind": "search", "identifier_scheme": None,
     "parameters": {"query_template": "<Europe PMC query containing {names}, e.g. ({names}) AND \"oral bioavailability\">",
                    "relevance_terms": ["<terms a relevant title or abstract must contain>"], "search_limit": 10},
     "units": "any unit stated in the attribute; claims must report that unit",
     "evidence_kind": "peer_reviewed", "determination_basis": "measured",
     "note": "Reads the best open-access papers naming the candidate and extracts quote-checked claims."},
]

EVIDENCE_CATALOG.append(
    {"capability": "record_field_lookup", "question_kind": "record_field", "identifier_scheme": "inchikey",
     "parameters": {"field": "<one of oral, parenteral, topical, black_box_warning, withdrawn_flag, first_approval, max_phase>"},
     "units": {"oral": None, "parenteral": None, "topical": None, "black_box_warning": None, "withdrawn_flag": None,
               "first_approval": "year", "max_phase": "phase"},
     "evidence_kind": "database_entry", "determination_basis": "measured",
     "note": "ChEMBL molecule record. Route flags and warnings are booleans (use measurement_kind categorical, unit null, "
             "cutoff {comparator: '==', value: true or false}); they are often empty before approval, which gives unknown, "
             "never fail. first_approval is a year; max_phase is 0-4 (quantitative)."})

# Assessment dimensions offered to derivation; each is enumerated separately (design §8.3).
DIMENSIONS = [
    {"dimension": "target_coverage", "focus": "potency and selectivity against the required targets"},
    {"dimension": "oral_bioavailability", "focus": "absorption and oral bioavailability in humans"},
    {"dimension": "metabolic_stability", "focus": "metabolic stability, clearance, half-life, and drug-drug interaction liability"},
    {"dimension": "toxicological_safety", "focus": "toxicity and safety liabilities relevant to chronic oral dosing"},
]
