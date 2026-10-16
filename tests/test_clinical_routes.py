"""Existing quote -> typed route, with explicit Boolean/absence and legacy boundaries."""
from copy import deepcopy

from mas.adapters.drug.clinical_routes import ClinicalRouteCache, EXISTENCE_SEMANTICS, load_source_records, supports_attribute
from mas.adapters.drug.registration import objective_templates
from mas.core import assessor, criteria, ledger
from mas.core.canonical import sha256_hex
from mas.core.journal import actor

CATALOG = [{"name": "Fixturemed", "inchikey": "FIXTURE-A", "chembl_id": "CHEMBL_SYN_A", "synonyms": ["Shared alias"]},
           {"name": "Othermed", "inchikey": "FIXTURE-B", "synonyms": ["Shared alias"]}]
SOURCE = {"source_id": "src_clinical", "source_status": "peer_reviewed_paper", "title": "A phase II trial in adult patients",
          "pub_types": ["Clinical Trial, Phase II"], "issued_date": "2023", "retraction_state": "unknown"}


def claim(text, *, cid="claim_fixture", scope_match="unknown"):
    return {"claim_id": cid, "source_ref": "src_clinical", "admission_state": "admitted", "evidence_kind": "peer_reviewed",
            "determination_basis": "asserted", "value": 250, "unit": "mg", "scope_match": scope_match,
            "location": {"quoted_span": text, "locator_value": "sec2.p1", "location_kind": "paragraph", "span_checked_against_source": True}}


def template(policy):
    context = {"qualification_policy": policy, "constraints": [{"kind": "route", "hardness": "hard", "text": "oral administration"}]}
    return objective_templates(context)


def test_cached_explicit_clinical_quote_is_bound_and_projected_without_changing_dose_or_source(core):
    original = claim("In both cohorts, Fixturemed was administered orally at 250 mg once daily.")
    before = deepcopy(original)
    cache = ClinicalRouteCache([original], {"src_clinical": SOURCE}, CATALOG,
        source_provenance={original["claim_id"]: {"artifact_id": "art_original", "sha256": sha256_hex(original)}}, cutoff_date="2026-10-16")
    (projected,) = cache.claims_for("cand_inchikey-FIXTURE-A", attribute_ref="attr_oral@v1")
    assert projected["value"] is True and projected["unit"] is None and projected["evidence_kind"] == "peer_reviewed"
    assert projected["derived_from"]["value"] == 250 and projected["derived_from"]["unit"] == "mg"
    assert projected["derived_from"]["determination_basis"] == "asserted"
    assert projected["derived_from"]["claim_sha256"] == sha256_hex(original)
    assert original == before and projected["location"] == original["location"]
    assert cache.claims_for("FIXTURE-A") and cache.claims_for("CHEMBL_SYN_A")
    assert cache.claims_for({"candidate_id": "cand_inchikey-FIXTURE-A"})
    assert not cache.claims_for("FIXTURE-B")
    assert cache.manifest()["projected_fact_count"] == 1
    assert projected["reading_depth"] == "not_read" and projected["normalized_statement"]
    ledger.record_claim(core, "run_projection_fixture", projected, by=actor("tool", "clinical_route_projection_v1"),
                        admission_state="admitted", admission_reasons=projected["admission_reasons"])
    assert ledger.claims(core, ["run_projection_fixture"])[0]["value"] is True


def test_animals_generic_oral_and_ambiguous_entities_do_not_become_route_positive():
    texts = ["Fixturemed was administered orally at 250 mg to mice.", "Fixturemed is an oral kinase inhibitor.",
             "Shared alias was administered orally at 250 mg once daily.",
             "Patients will receive Fixturemed (250 mg QD PO).", "Fixturemed has oral bioavailability of 80%."]
    cache = ClinicalRouteCache([claim(text, cid=f"claim_{i}") for i, text in enumerate(texts)], {"src_clinical": SOURCE}, CATALOG)
    assert not cache.claims_for("FIXTURE-A") and not cache.claims_for("FIXTURE-B")
    (combo,) = ClinicalRouteCache([claim("Patients received Fixturemed (250 mg QD PO) with Othermed (240 mg Q3W IV).")],
        {"src_clinical": SOURCE}, CATALOG).claims_for("FIXTURE-A")
    assert combo["value"] is True
    assert not ClinicalRouteCache([claim("Patients received Fixturemed (250 mg QD PO) with Othermed (240 mg Q3W IV).")],
        {"src_clinical": SOURCE}, CATALOG).claims_for("FIXTURE-B")


def test_new_any_true_is_opt_in_and_database_absence_is_unknown_not_failure():
    legacy, modern = template("legacy"), template("qualification_first_v1")
    assert len(legacy) == 2 and len(modern) == 1
    assert not supports_attribute(legacy[0]["attribute"]) and supports_attribute(modern[0]["attribute"])
    attr = dict(modern[0]["attribute"], attribute_id="attr_oral", version=1)
    rule = dict(modern[0]["rule"], rule_id="rule_oral", version=1)
    criteria.check_attribute(attr)
    criteria.check_rule(rule, attr)
    db = {"claim_id": "claim_database", "source_ref": "src_database", "admission_state": "admitted", "evidence_kind": "database_entry",
          "determination_basis": "measured", "value": False, "unit": None}
    positive = ClinicalRouteCache([claim("Fixturemed was administered orally at 250 mg once daily.")],
        {"src_clinical": SOURCE}, CATALOG).claims_for("FIXTURE-A", attribute_ref="attr_oral@v1")[0]
    def assess(items):
        return assessor.assess_cell(candidate={"candidate_id": "FIXTURE-A"}, attribute=attr, rule=rule, rule_set_ref="rules@v1",
                                   claims=items, resolved=True, qualification_policy=assessor.QUALIFICATION_POLICY)[0]
    assert assess([db])["verdict"] == "unknown_missing"
    assert assess([db, positive])["verdict"] == "pass"
    assert assess([dict(positive, value=250, unit="mg")])["verdict"] == "unknown_missing"
    negative = ClinicalRouteCache([claim("Fixturemed cannot be administered orally.", scope_match="matched")],
        {"src_clinical": SOURCE}, CATALOG).claims_for("FIXTURE-A")[0]
    assert assess([negative])["verdict"] == "fail"
    assert assess([negative, positive])["verdict"] == "unknown_conflicted"
    assert not ClinicalRouteCache([claim("Fixturemed cannot be administered orally.")], {"src_clinical": SOURCE}, CATALOG).claims_for("FIXTURE-A")


def test_source_metadata_helper_pins_payload_hash_without_reading_documents(core):
    aid = core.artifacts.put("source", SOURCE)
    rows = load_source_records(core, ["src_clinical", "src_absent"])
    assert rows == {"src_clinical": {"source": SOURCE, "artifact_id": aid, "sha256": sha256_hex(SOURCE)}}
