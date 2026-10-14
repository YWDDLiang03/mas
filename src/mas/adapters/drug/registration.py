"""Drug adapter v1: registration of tools, identity rules, and criterion templates (design §2.1).

The core never imports this module; a composition root (the CLI or a script) calls
`register(broker)` and passes `ADAPTER` to the run controller.
"""

from __future__ import annotations

from mas.adapters.literature import tools as literature_tools

from .chembl import ChEMBLBioactivity, ChEMBLMechanism, TargetCache
from .gtopdb import GtoPdbAffinity, GtoPdbData
from .pubchem import PropertyCache, PubChemIdentity, PubChemProperty
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


def register(broker, *, literature: bool = True, universe_file: str | None = None, cache_dir: str | None = None,
             upload_dir: str | None = None) -> None:
    """Register the adapter's tools. With a universe file, identity resolves from it first (PubChem stays as fallback)
    and a target's bioactivity and mechanism records are each fetched once per target. Literature sources are
    registered for every task; which of them a search uses is the `search.sources` setting."""
    if universe_file:
        broker.register(UniverseIdentity(universe_file))
        broker.register(UniverseRecordField(universe_file))
    targets = TargetCache() if universe_file else None
    properties = PropertyCache() if universe_file else None   # a universe is swept rule by rule: one row per compound
    for provider in (PubChemIdentity(), PubChemProperty(properties), ChEMBLBioactivity(targets),
                     ChEMBLMechanism(targets), GtoPdbAffinity(GtoPdbData(cache_dir))):
        broker.register(provider)
    if literature:
        literature_tools.register(broker, cache_dir=cache_dir, upload_dir=upload_dir)

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
     "note": "Curated potency records (pChEMBL = -log10 molar IC50/Ki/Kd/EC50) against one target; use aggregation "
             "median (a maximum rises with the number of assays, favouring heavily studied compounds)."},
    {"capability": "interaction_evidence_lookup", "question_kind": "gtopdb_affinity", "identifier_scheme": "inchikey",
     "parameters": {"target_chembl_id": "<a ChEMBL target id from the task's scope entities>"},
     "units": {"affinity": "pChEMBL"}, "evidence_kind": "curated_measurement", "determination_basis": "measured",
     "note": "Expert-curated affinities from the IUPHAR/BPS Guide to Pharmacology (pIC50, pKi, pKd; -log10 molar, the "
             "pChEMBL scale), with action type and selectivity. An independent curation from ChEMBL: it can cover "
             "compound-target pairs ChEMBL lacks. Use aggregation median."},
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

EVIDENCE_CATALOG.append(
    {"capability": "interaction_evidence_lookup", "question_kind": "mechanism_records", "identifier_scheme": "inchikey",
     "parameters": {"target_chembl_id": "<a ChEMBL target id from the task's scope entities>"},
     "units": {"target_engagement": None}, "evidence_kind": "database_entry", "determination_basis": "curated",
     "note": "ChEMBL's curated mechanism-of-action table: one record per curated statement, with its references "
             "(PubMed ids, FDA and EMA labels, DailyMed label sections), that this compound engages this target; the "
             "action type (INHIBITOR, AGONIST, ...), the direct-interaction flag and any selectivity comment are in "
             "each claim's conditions for a narrative to cite. A curation independent of the activity table: it covers "
             "compound-target pairs that have no pChEMBL record at all, though the table is small (a few dozen records "
             "per target) and reaches little beyond approved and late-stage drugs. Every record carries the same "
             "categorical value, engagement on record (use measurement_kind "
             "categorical, unit null, cutoff {comparator: '==', value: true}); curation is sparse outside developed "
             "drugs, so absence must give unknown, never fail. A record is an expert assertion carrying references, "
             "not a measurement of anything, so every claim from it is stamped determination_basis curated: an "
             "attribute bound to this entry must declare acceptable_determination_bases: [\"curated\"], because the "
             "default bases (measured, derived) set every one of these claims aside and the attribute then sees no "
             "evidence at all. It is NOT a potency value and must never stand in for "
             "one: a record says that engagement is documented, not how strong it is, and a compound with a record is "
             "not thereby more potent than one measured at pChEMBL 9. Bind it as evidence of engagement alongside a "
             "potency attribute, never as that attribute's source."})

# Assessment dimensions offered to derivation; each is enumerated separately (design §8.3).
DIMENSIONS = [
    {"dimension": "target_coverage", "focus": "potency and selectivity against the required targets"},
    {"dimension": "oral_bioavailability", "focus": "absorption and oral bioavailability in humans"},
    {"dimension": "metabolic_stability", "focus": "metabolic stability, clearance, half-life, and drug-drug interaction liability"},
    {"dimension": "toxicological_safety", "focus": "toxicity and safety liabilities relevant to chronic oral dosing"},
]


def objective_templates(task_context: dict) -> list[dict]:
    """Criteria the task mandates: potency at each required target; an approved route for a route constraint.

    No cutoff is invented: potency is an ordering preference (median pChEMBL, higher is better);
    the route constraint is a hard exclusion that an expert must confirm.
    """
    items = []
    for index, entity in enumerate(task_context.get("scope_entities", [])):
        if entity.get("role") != "required" or entity.get("identifier_scheme") != "chembl_target":
            continue
        label = entity.get("label") or entity["identifier"]
        items.append({
            "source_field": f"scope_entities[{index}]",
            # WHY both curations on one attribute: a required receptor's potency is one quantity, and binding the
            # mandated attribute to ChEMBL alone left the pool to notice IUPHAR/BPS separately and propose a second
            # attribute for it. Measured on the manuscript registry: ten promoted rules for five quantities, with
            # identical unit, direction, aggregation, acceptable sources and target id, differing only in which
            # database answered. Every receptor was therefore scored twice, a compound well covered by one curation
            # got double credit, and five quantities that do not exist inflated the coverage denominator -- 34 of
            # 3,177 compounds cleared the ranking floor where 99 clear it once each receptor is one quantity. Both
            # routes declare `curated_measurement` on the pChEMBL scale, so `median` aggregates them as one set.
            "attribute": {"name": f"{label} curated potency", "measurement_kind": "quantitative", "unit": "pChEMBL",
                          "definition": f"Median pChEMBL value over curated point measurements against {label} "
                                        f"({entity['identifier']}), across every available expert curation",
                          "direction": "higher_better", "acceptable_value_sources": ["curated_measurement"],
                          "aggregation": "median",
                          "evidence_requests": [
                              {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
                               "identifier_scheme": "inchikey",
                               "parameters": {"target_chembl_id": entity["identifier"]}},
                              {"capability": "interaction_evidence_lookup", "question_kind": "gtopdb_affinity",
                               "identifier_scheme": "inchikey",
                               "parameters": {"target_chembl_id": entity["identifier"]}}],
                          "rationale": f"{label} is a required target of the task"},
            "rule": {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
                     "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty"}})
    for index, constraint in enumerate(task_context.get("constraints", [])):
        text = (constraint.get("text") or "").lower()
        if constraint.get("hardness") == "hard" and constraint.get("kind") == "route" and "oral" in text:
            items.append({
                "source_field": f"constraints[{index}]",
                # WHY the name and definition no longer say "approved": the task admits an approved OR a
                # Phase III compound, and a Phase III compound has no approved product by definition, so a
                # criterion asking for an approved oral route can never be satisfied by half the population
                # the task declares eligible -- it asked a stricter question than the user did. Measured on
                # the manuscript universe: 1,262 of 3,177 candidates have no approval record at all, so this
                # cell is unknown for them and its `unknown_blocks_recommendation` policy held every one of
                # them at `provisional`. The remedy is not to weaken the constraint -- oral administration is
                # stated as hard -- but to ask about the route itself and let the companion criterion below
                # answer it for compounds no approval register covers. ChEMBL's route flags are derived from
                # approved-product records and are the only route field in the catalog, so for a Phase III
                # compound the database genuinely cannot answer and the literature is the only source.
                "attribute": {"name": "Oral route on record", "measurement_kind": "categorical", "unit": None,
                              "definition": "Whether a product or trial record of the compound states an oral route",
                              "direction": "non_directional", "acceptable_value_sources": ["database_entry"],
                              "aggregation": "consensus",
                              "evidence_request": {"capability": "record_field_lookup", "question_kind": "record_field",
                                                   "identifier_scheme": "inchikey", "parameters": {"field": "oral"}},
                              "acceptable_determination_bases": ["measured", "derived"],
                              "rationale": "the task's hard constraint: oral administration"},
                "rule": {"rule_kind": "hard_exclusion", "predicate_form": "categorical_membership",
                         "cutoff": {"comparator": "==", "value": True, "unit": None}, "cutoff_basis": "task_constraint",
                         "on_missing": "unknown_blocks_recommendation"}})
            # The companion that can answer for a compound no approval register covers. It is a separate
            # criterion rather than a second route on the one above because `check_attribute` refuses an
            # attribute that mixes a literature route with a database route: the two take different code
            # paths and pooling a read passage with a record field under one aggregation needs a policy
            # nobody has set. Contextual, not a second hard gate, so one requirement is not scored twice.
            items.append({
                "source_field": f"constraints[{index}]",
                "attribute": {"name": "Oral administration reported in the clinical literature",
                              "measurement_kind": "categorical", "unit": None,
                              "definition": "Whether a clinical report of the compound states that it was "
                                            "administered by mouth",
                              "direction": "non_directional",
                              "acceptable_value_sources": ["peer_reviewed_primary"], "aggregation": "consensus",
                              "acceptable_determination_bases": ["asserted", "measured"],
                              "evidence_request": {
                                  "capability": "literature_retrieval", "question_kind": "search",
                                  "identifier_scheme": None,
                                  "parameters": {"query_template": "({names}) AND (oral OR orally OR \"by mouth\")",
                                                 "relevance_terms": ["oral", "orally", "capsule", "tablet"],
                                                 "search_limit": 10}},
                              "rationale": "the task admits a Phase III compound, whose route no approval "
                                           "register records; the trial literature states it"},
                "rule": {"rule_kind": "exploratory_consideration", "predicate_form": "qualitative_judgment",
                         "cutoff": None, "cutoff_basis": "none_evidence_insufficient",
                         "on_missing": "unknown_no_penalty"}})
    return items
