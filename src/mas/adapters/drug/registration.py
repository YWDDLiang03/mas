"""Drug adapter v1: registration of tools, identity rules, and criterion templates (design §2.1).

The core never imports this module; a composition root (the CLI or a script) calls
`register(broker)` and passes `ADAPTER` to the run controller.
"""

from __future__ import annotations

from mas.adapters.literature import registry as literature_registry, tools as literature_tools
from mas.adapters.predict import admet

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
    "predicted_property_lookup": "attribute_estimate",
}

# Evidence kinds the adapter's sources produce (used in attributes' acceptable_value_sources).
#
# Derived rather than written out: the hand-written tuple listed five kinds and omitted the
# `reference_text`, `tertiary_reference` and `user_supplied_document` that this adapter's own
# literature registration produces, so it could not be used to check anything. It is the union of
# the kinds this adapter's catalog entries declare (filled in below, where the entries are) and the
# kinds the literature sources carry. The authoritative registry of the kinds a claim may carry at
# all is `vocab.DOMAINS["evidence_kind"]`; what a given machine can produce is
# `evidence.producible_evidence_kinds(broker)`, which is narrower whenever an optional tool is
# absent.
EVIDENCE_KINDS: tuple[str, ...] = ()


def register(broker, *, literature: bool = True, universe_file: str | None = None, cache_dir: str | None = None,
             upload_dir: str | None = None, predict: bool | None = None, predict_python: str | None = None) -> None:
    """Register the adapter's tools. With a universe file, identity resolves from it first (PubChem stays as fallback)
    and a target's bioactivity and mechanism records are each fetched once per target. Literature sources are
    registered for every task; which of them a search uses is the `search.sources` setting.

    `predict` governs the predicted-property panel, which needs a universe file (that is where a compound's
    structure is found) and an interpreter with the predictor installed:

      None (the default)  register it when that interpreter is found, and not otherwise. A machine without the
                          predictor keeps every other route and the panel is simply absent: a route bound to it
                          returns `not_attempted / not_configured`, which says "this installation has no such
                          tool" rather than "this compound has no such property".
      True                register it whatever is found, so a missing environment refuses loudly, once per cell,
                          with `environment_missing`. This is for a run that must not quietly score without the
                          panel -- a criterion bound to it would otherwise be silently unanswered.
      False               leave it out.

    `predict_python` names the interpreter (the `predict.python` setting); without it the search order of
    `predict.admet.candidates` applies. `mas predict check` prints what is found and warms nothing.
    """
    if universe_file:
        broker.register(UniverseIdentity(universe_file))
        broker.register(UniverseRecordField(universe_file))
    targets = TargetCache() if universe_file else None
    properties = PropertyCache() if universe_file else None   # a universe is swept rule by rule: one row per compound
    for provider in (PubChemIdentity(), PubChemProperty(properties), ChEMBLBioactivity(targets),
                     ChEMBLMechanism(targets), GtoPdbAffinity(GtoPdbData(cache_dir))):
        broker.register(provider)
    if universe_file and (predict if predict is not None else admet.available(predict_python)):
        structures, panel = admet.StructureIndex(universe_file), admet.PanelCache(cache_dir, python=predict_python)
        existing = admet.ExistingPanelProjection(structures, panel)
        broker.register(admet.AdmetPrediction(structures, panel, existing=existing))
        broker.register(admet.AdmetComputedDescriptors(structures, panel, existing=existing))
    if literature:
        literature_tools.register(broker, cache_dir=cache_dir, upload_dir=upload_dir)


def _panel_entries() -> dict[str, str]:
    """One line per endpoint of the predictor's panel, built from the panel itself so the catalog
    cannot drift from what the tool answers."""
    lines = {}
    for endpoint, spec in admet.ENDPOINTS.items():
        metric = ", ".join(f"{name.upper()} {value:g}" for name, value in (spec["metric"] or {}).items())
        if spec["training_dataset"] is None:
            how = "computed by RDKit from the structure; not a trained model"
        else:
            how = ("a classifier's probability of its positive class, in [0,1]"
                   if spec["task_type"] == "classification" else "a regression value")
            how += f"; TDC dataset {spec['training_dataset']} ({spec['training_rows']} rows)"
            how += f"; held out {metric}" if metric else ""
            how += f"; {spec['species']}" if spec["species"] else ""
        lines[endpoint] = f"{spec['name']} [{spec['category']}] in {spec['unit']}: {how}"
        if endpoint == "LD50_Zhu":
            lines[endpoint] += ("; this is a logarithmic reciprocal of molar LD50: a larger output means "
                                "a smaller LD50 and greater acute toxicity, not a larger tolerated dose")
        if endpoint == "Lipinski":
            lines[endpoint] += "; number of the four rule-of-five conditions satisfied, not a violation count"
    return lines

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

EVIDENCE_CATALOG.append(
    {"capability": "predicted_property_lookup", "question_kind": "admet_prediction", "identifier_scheme": "inchikey",
     "parameters": {"endpoint": f"<one of the {len(admet.ENDPOINTS) - len(admet.DESCRIPTOR_PROJECTIONS)} endpoint ids listed under `endpoints` below>"},
     "units": {key: value for key, value in admet.UNITS.items() if key not in admet.DESCRIPTOR_PROJECTIONS},
     "endpoints": {key: value for key, value in _panel_entries().items() if key not in admet.DESCRIPTOR_PROJECTIONS},
     "evidence_kind": "model_prediction", "determination_basis": "predicted",
     "note":
         "A local ADMET model panel (ADMET-AI: a Chemprop-RDKit ensemble per endpoint, trained on the "
         "Therapeutics Data Commons dataset named in each line above) run over the compound's own structure. "
         "This tool emits model_prediction/predicted records. Endpoints documented as computed RDKit descriptors "
         "are deterministic calculations, not trained predictions. For a standard descriptor already offered by "
         "property_estimate (such as MolecularWeight), prefer that exact descriptor route and its database_entry/derived "
         "provenance. Do not interchange different logP methods or other distinct quantities. An attribute bound to this entry must declare "
         "acceptable_value_sources: [\"model_prediction\"] and acceptable_determination_bases: [\"predicted\"] "
         "and nothing else -- the registry refuses `predicted` alongside any other basis, because a predicted "
         "value standing in for a measurement is a surrogate inside a verdict, so a predicted quantity is its "
         "own attribute with its own rule and is never a second route on a measured one. Without that "
         "declaration the default bases (measured, derived) set every value aside and the cell reads as no data. "
         "WHAT IT BUYS: it is computable for every compound that has a structure, so a criterion bound here "
         "scores the whole universe, where a measured absorption or toxicity quantity exists for a few dozen "
         "well-studied drugs and defers for everyone else. "
         "WHAT A VALUE IS: a classification endpoint returns the probability of its positive class as a number "
         "in [0,1] (unit `probability`), and the natural decision boundary of a binary classifier is 0.5 -- "
         "thresholding there is cutoff_basis model_decision_boundary, which needs no cited claim (no claim "
         "states a model's own line) and goes to review like any bound that claims an authority of its own. A "
         "regression endpoint returns a number in the unit given above; read the direction from what the "
         "endpoint measures (higher clearance is worse, higher solubility is better). "
         "HOW GOOD IT IS: each line gives the held-out metric of that endpoint's model. They are not alike: "
         "AUROC near 0.9 and AUROC near 0.7 are different grades of evidence, and a NEGATIVE R^2 (Half_Life_Obach, "
         "VDss_Lombardo) means the model does not beat predicting the training mean -- an endpoint like that "
         "carries no information about a particular compound and must not carry a criterion. Prefer a preference "
         "or an exploratory consideration to a hard exclusion: a hard exclusion on a predicted value deletes a "
         "candidate on a model's output. "
         "THE ELEVEN `Physicochemical` ENDPOINTS are RDKit calculations that the package reports in the same "
         "frame as its predictions; this legacy route keeps its original `predicted` contract. The four "
         "independently verified saved RDKit descriptors logP/BRENK_alert/NIH_alert/PAINS_alert also have a "
         "separate property_estimate / admet_computed_property route with database_entry/derived provenance. "
         "These four are omitted from this prediction catalog: new criteria must use their derived route. "
         "The other seven physicochemical endpoints retain their existing conservative predicted contract; "
         "their basis is not automatically changed by this addition. "
         "Do not bind both for one quantity. PubChem descriptors and distinct logP algorithms are separate "
         "measurement identities, not interchangeable aliases. "
         "A compound the universe has no structure for yields unknown, never a failure, so pair this with "
         "on_missing unknown_no_penalty."})

EVIDENCE_CATALOG.append({
    "capability": "property_estimate", "question_kind": "admet_computed_property", "identifier_scheme": "inchikey",
    "parameters": {"endpoint": "<one of logP, BRENK_alert, NIH_alert, PAINS_alert>"},
    "units": {endpoint: admet.UNITS[endpoint] for endpoint in admet.DESCRIPTOR_PROJECTIONS},
    "endpoints": {endpoint: admet.DESCRIPTOR_PROJECTIONS[endpoint]["algorithm"]
                  for endpoint in admet.DESCRIPTOR_PROJECTIONS},
    "evidence_kind": "database_entry", "determination_basis": "derived",
    "note": "Read exact pre-pinned ADMET-AI 2.0.1 physicochemical output, without running a model or recomputing "
            "a descriptor. logP is RDKit Crippen MolLogP, not PubChem XLogP or a trained lipophilicity endpoint. "
            "BRENK/NIH/PAINS values count FilterCatalog substructure matches, not toxicity measurements or "
            "classifier probabilities. Each saved value carries the original panel identity, structure and file "
            "hash plus the checked algorithm source version. Accept only database_entry/derived for this route. "
            "A missing pinned value stays unknown and never triggers computation. Old prediction-route records "
            "keep their original basis; changing an attribute to this route requires a new reviewed version."})

EVIDENCE_KINDS = tuple(sorted({entry["evidence_kind"] for entry in EVIDENCE_CATALOG if entry.get("evidence_kind")}
                              | set(literature_registry.EVIDENCE_KINDS)))

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
            #
            # WHY the literature is the third route and not a fourth criterion: the same argument, one step
            # further. A published kinase selectivity table reports exactly this quantity for exactly these
            # targets, and it is where the quantity exists for compounds no curation has reached -- 74 of the
            # 3,177 candidates carry any curated potency at the five required receptors. A separate literature
            # criterion would be the same measurement registered twice, with the double counting and the inflated
            # denominator the collapse above exists to undo. So it is one attribute with three routes, pooled by
            # the `median` it already declared: one quantity, every curation and every report of it that was
            # found. This needs two things the route cannot provide by itself -- `peer_reviewed` among the
            # accepted sources, because that is the evidence kind a paper's claims carry, and the molar-to-pChEMBL
            # conversion in `assessor.UNIT_CONVERSIONS`, because a table prints "IC50 = 4 nM" and this attribute
            # is on the pChEMBL scale. Without the conversion every literature claim here is set aside
            # `unit_unresolved` and the route costs reading and returns nothing.
            #
            # WHY the affinity predictor is NOT a route here, and why this attribute declares no
            # `determination_basis_precedence` (an explicit decision, not an omission): gap-filling would make
            # the cell fall back to a predicted potency wherever no measurement exists, and the board then
            # percentile-ranks that prediction against measured values across candidates. A random-forest
            # prediction shrinks toward its training mean, so the extremes of the ranking are collected by the
            # candidates that carry real measurements and the predicted ones pile up in the middle -- the
            # ordering would be reporting how well studied a compound is, under the name of how potent it is.
            # A required receptor's potency stays measured or curated; a predicted affinity, if it is wanted,
            # is its own attribute with its own rule, which is what the catalog already says.
            "attribute": {"name": f"{label} curated potency", "measurement_kind": "quantitative", "unit": "pChEMBL",
                          "definition": f"Median pChEMBL value (-log10 of the molar IC50, Ki, Kd or EC50) over "
                                        f"point measurements against {label} ({entity['identifier']}), pooled "
                                        f"across every available expert curation and every reported measurement "
                                        f"in the peer-reviewed literature",
                          "direction": "higher_better",
                          "acceptable_value_sources": ["curated_measurement", "peer_reviewed"],
                          "aggregation": "median",
                          "evidence_requests": [
                              {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
                               "identifier_scheme": "inchikey",
                               "parameters": {"target_chembl_id": entity["identifier"]}},
                              {"capability": "interaction_evidence_lookup", "question_kind": "gtopdb_affinity",
                               "identifier_scheme": "inchikey",
                               "parameters": {"target_chembl_id": entity["identifier"]}},
                              # The query is about this receptor's potency for this compound, not about the
                              # compound: the terms are the ones a selectivity table's caption and abstract
                              # carry, and the receptor's own label is required rather than optional, so a
                              # pharmacokinetics paper naming the compound does not answer here. The ChEMBL
                              # target id is in the definition and not in the query -- no paper cites it.
                              {"capability": "literature_retrieval", "question_kind": "search",
                               "identifier_scheme": None,
                               "parameters": {
                                   "query_template": f'({{names}}) AND "{label}" AND (IC50 OR Ki OR Kd OR EC50 '
                                                     f'OR potency OR selectivity OR "kinase selectivity")',
                                   "relevance_terms": [label, "IC50", "Ki", "Kd", "EC50", "nM", "selectivity",
                                                       "potency", "inhibition"],
                                   "search_limit": 10}}],
                          "rationale": f"{label} is a required target of the task"},
            "rule": {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
                     "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty"}})
    for index, constraint in enumerate(task_context.get("constraints", [])):
        text = (constraint.get("text") or "").lower()
        if constraint.get("hardness") == "hard" and constraint.get("kind") == "route" and "oral" in text:
            if task_context.get("qualification_policy") == "qualification_first_v1":
                from .clinical_routes import EXISTENCE_SEMANTICS
                items.append({"source_field": f"constraints[{index}]", "attribute": {
                    "name": "Documented oral administration", "measurement_kind": "categorical", "unit": None,
                    "definition": "Whether a product record or an explicit human clinical administration report documents an oral route for this compound",
                    "direction": "non_directional", "acceptable_value_sources": ["database_entry", "peer_reviewed"],
                    "aggregation": "any_true", "existence_semantics": dict(EXISTENCE_SEMANTICS),
                    "acceptable_determination_bases": ["measured", "derived", "asserted", "curated"],
                    "evidence_request": {"capability": "record_field_lookup", "question_kind": "record_field",
                        "identifier_scheme": "inchikey", "parameters": {"field": "oral"}},
                    "rationale": "the task requires documented oral administration; an absent database listing is unknown"},
                    "rule": {"rule_kind": "hard_exclusion", "predicate_form": "categorical_membership",
                        "cutoff": {"comparator": "==", "value": True, "unit": None}, "cutoff_basis": "task_constraint",
                        "on_missing": "unknown_blocks_recommendation"}})
                continue
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
            # criterion rather than a second route on the one above because this quantity is categorical
            # and pooled by `consensus`: `check_attribute` permits a literature route beside database
            # routes only on a quantitative attribute with a unit reduced by a numeric aggregation, where
            # every claim is checked against one scale. "Does a record state an oral route" and "does a
            # trial report say it was taken by mouth" have no such scale, and what agreement between the
            # two means is the policy nobody has set. Contextual, not a second hard gate, so one
            # requirement is not scored twice.
            items.append({
                "source_field": f"constraints[{index}]",
                "attribute": {"name": "Oral administration reported in the clinical literature",
                              "measurement_kind": "categorical", "unit": None,
                              "definition": "Whether a clinical report of the compound states that it was "
                                            "administered by mouth",
                              "direction": "non_directional",
                              # `peer_reviewed` and not `peer_reviewed_primary`: the readers stamp
                              # the source registry's kind on every claim
                              # (`adapters/literature/registry.Source.evidence_kind`), and that
                              # registry has no `primary` variant -- a journal article arrives as
                              # `peer_reviewed`. The stricter-sounding word named no kind at all, so
                              # every claim this criterion ever read was set aside
                              # `evidence_kind_not_accepted` and the one route meant to answer the
                              # oral-route question for the 1,262 candidates ChEMBL has no route
                              # flag for could never carry a value. `criteria.check_attribute` now
                              # refuses an unproducible kind outright.
                              "acceptable_value_sources": ["peer_reviewed"], "aggregation": "consensus",
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
