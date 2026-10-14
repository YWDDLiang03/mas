"""The criteria review package: what it must say, and what must not move between two exports."""

import json

import pytest

from mas.core import criteria, criteria_export, ledger, pool as pool_mod, task
from mas.core.journal import actor
from mas.core.runtime import Core

OPERATOR = actor("human", "O1", "operator", identity_basis="recorded_attestation")
PROPOSER = actor("agent", "proposer-1", "proposer", model_family="test")

TASK_SPEC = {
    "objective_text": "Prioritize oral compounds engaging T1",
    "mode": "conditional",
    "scope_entities": [{"entity_kind": "target", "identifier": "T1", "identifier_scheme": "test",
                        "role": "required", "label": "T1"}],
    "candidate_universe": {"kind": "enumerated_set", "members": ["alpha", "beta"], "size_if_known": 2},
    "constraints": [{"text": "oral administration", "kind": "route", "hardness": "hard",
                     "provenance": "test"}],
    "evaluation_scope": {"comparison_basis": "all_pass_set", "abstention_allowed": True},
}

SURVIVOR = {
    "attribute": {
        "name": "Potency at T1",
        "definition": "Median curated potency against T1, as a pChEMBL value",
        "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better",
        "acceptable_value_sources": ["curated_measurement"], "aggregation": "median",
        "evidence_request": {"capability": "interaction_evidence_lookup", "question_kind": "pchembl_values",
                             "parameters": {"target_chembl_id": "T1"}},
    },
    "rule": {"rule_kind": "preference", "predicate_form": "ordering", "cutoff": None,
             "cutoff_basis": "none_evidence_insufficient", "on_missing": "unknown_no_penalty",
             "on_inapplicable": "unknown_no_penalty", "on_conflict": "unknown_no_penalty"},
    "dimension": "target_coverage",
    "expected_change": "Candidates with higher curated potency rank above candidates without it",
    "falsification_test": "If every candidate scores the same the attribute discriminates nothing",
}

PRUNED = {
    "attribute": {
        "name": "Potency at T1 from a second curation",
        "definition": "Median potency against T1 from an independent curation",
        "measurement_kind": "quantitative", "unit": "pChEMBL", "direction": "higher_better",
        "acceptable_value_sources": ["curated_measurement"], "aggregation": "median",
        "evidence_request": {"capability": "interaction_evidence_lookup", "question_kind": "gtopdb_affinity",
                             "parameters": {"target_chembl_id": "T1"}},
    },
    "rule": dict(SURVIVOR["rule"]),
    "dimension": "target_coverage",
    "expected_change": "A second curation fills cells the first one lacks",
    "falsification_test": "If the two curations disagree the aggregation is unsafe",
}

CLAIM = {
    "claim_text": "Inhibitors of this class reach pChEMBL values above 8 at the receptor.",
    "normalized_statement": "Inhibitors of this class reach pChEMBL values above 8 at the receptor.",
    "claim_type": "literature_extracted", "evidence_kind": "peer_reviewed",
    "determination_basis": "measured", "polarity": "supports", "unit": "pChEMBL", "value": 8,
    "reading_depth": "full_text", "question_purpose": "criterion_discovery",
    "source_ref": "src_doi_10.0000/test", "verification_status": "unverified",
    "scope": {"marker": "stated", "population_or_system": "inhibitors of this class"},
    "scope_match": "unknown",
    "location": {"location_kind": "paragraph", "locator_value": "sec1.p1",
                 "quoted_span": "Inhibitors of this class reach pChEMBL values above 8",
                 "section_path": ["1. Potency"], "span_checked_against_source": True},
}

SOURCE = {"source_id": "src_doi_10.0000/test", "source_status": "peer_reviewed_paper",
          "access_state": "full_text_available", "title": "A test paper", "container": "Journal of Tests",
          "issued_date": "2026-01-01", "license": "cc by",
          "identifiers": [{"scheme": "doi", "value": "10.0000/test"}]}


def _seed(root) -> tuple[str, str]:
    """A store holding one promoted criterion, one withdrawn pool item and a confirmed rule set."""
    with Core.open(root) as core:
        task_id, _ = task.record_version(core, TASK_SPEC, by=OPERATOR)
        run_id = "run_01TESTDERIVATION000000000"
        ledger.put_source(core, SOURCE)
        claim_id = ledger.record_claim(core, run_id, dict(CLAIM), by=PROPOSER, admission_state="admitted",
                                       admission_reasons=["quote_verified", "value_in_quote"])
        writer = pool_mod.Pool(core, task_id, by=PROPOSER, run_id=run_id)
        survivor = dict(SURVIVOR, supporting_claim_ids=[claim_id])
        pruned = dict(PRUNED, supporting_claim_ids=[claim_id])
        writer.at("propose", 0)
        kept = writer.add(survivor, reason_text="proposed for target_coverage")
        dropped = writer.add(pruned, reason_text="proposed for target_coverage")
        folded = writer.fold()
        writer.at("filter", 1).set_state(
            folded[dropped], "needs_refine", operation="revise", reason_kind="critic_findings",
            reason_text="no cited quote reports this quantity",
            item=dict(pruned, critic_findings=[{"check": "evidence_support", "referent": "attribute.definition",
                                                "severity": "material", "verdict": "fail",
                                                "finding": "no cited quote reports this quantity"}]))
        writer.at("refine", 1).set_state(folded[dropped], "withdrawn", operation="remove",
                                         reason_kind="withdrawn_by_reviser",
                                         reason_text="the finding is correct and cannot be repaired")
        attribute = dict(survivor["attribute"], attribute_id="attr_potency-at-t1",
                         supporting_claim_refs=[claim_id],
                         derived_from={"pool_criterion": f"{kept}@v1", "derivation_run": run_id})
        rule = dict(survivor["rule"], rule_id="rule_potency-at-t1",
                    expected_change=survivor["expected_change"],
                    falsification_test=survivor["falsification_test"])
        attr_ref, rule_ref = criteria.propose(core, task_id, attribute, rule, by=PROPOSER)
        writer.at("promote", 0).set_state(folded[kept], "promoted", operation="promote",
                                          reason_kind="accepted", reason_text="no material finding",
                                          extra={"promoted_as": {"attribute_ref": attr_ref,
                                                                 "rule_ref": rule_ref}})
        criteria.confirm_rule_set(core, task_id, by=OPERATOR, coverage_floor=0.5, allow_pending=True)
        return task_id, claim_id


@pytest.fixture
def seeded(tmp_path):
    root = tmp_path / "root"
    task_id, claim_id = _seed(root)
    with criteria_export.open_read_only(root) as core:
        yield core, task_id, claim_id


def test_the_export_reads_a_store_that_is_open_read_only(seeded):
    core, task_id, _ = seeded
    assert core.read_only
    payload = criteria_export.snapshot(core, task_id, with_board=False)
    assert payload["baseline_label"] == criteria_export.BASELINE_LABEL
    assert [card["criterion_key"] for card in payload["criteria"]] == ["attr_potency-at-t1"]


def test_two_exports_of_one_journal_sequence_are_byte_identical(seeded, tmp_path):
    core, task_id, _ = seeded
    seq = core.journal.last_seq(task_id)
    first = criteria_export.write(core, task_id, tmp_path / "one", at_seq=seq, with_board=False)
    second = criteria_export.write(core, task_id, tmp_path / "two", at_seq=seq, with_board=False)
    assert first["file_digests"] == second["file_digests"]
    assert first["payload_digest"] == second["payload_digest"]


def test_the_payload_digest_ignores_the_export_timestamp(seeded, tmp_path):
    core, task_id, _ = seeded
    seq = core.journal.last_seq(task_id)
    payload = criteria_export.snapshot(core, task_id, at_seq=seq, with_board=False)
    early = criteria_export.manifest(payload, store_root="r", digests={}, implementation={},
                                     exported_at="2026-01-01T00:00:00.000Z")
    late = criteria_export.manifest(payload, store_root="r", digests={}, implementation={},
                                    exported_at="2027-12-31T23:59:59.000Z")
    assert early["export_metadata"]["exported_at"] != late["export_metadata"]["exported_at"]
    assert early["payload_digest"] == late["payload_digest"]
    assert "exported_at" not in json.dumps(payload)


def test_an_export_pinned_to_an_earlier_sequence_does_not_see_the_later_rule_set(seeded, tmp_path):
    core, task_id, _ = seeded
    before = next(event.seq for event in core.journal.replay(task_id)
                  if event.event_type == "criterion.version_approved") - 1
    pinned = criteria_export.snapshot(core, task_id, at_seq=before, with_board=False)
    assert pinned["rule_sets"] == []
    assert pinned["criteria"][0]["use"]["status"] == "no_confirmed_rule_set"
    assert criteria_export.snapshot(core, task_id, with_board=False)["latest_rule_set_ref"] == "rules@v1"


def test_a_sequence_outside_the_stream_is_refused_rather_than_clamped(seeded):
    core, task_id, _ = seeded
    with pytest.raises(criteria_export.ExportError):
        criteria_export.snapshot(core, task_id, at_seq=core.journal.last_seq(task_id) + 1)


def test_a_withdrawn_item_is_in_the_lifecycle_section_and_not_among_the_survivors(seeded, tmp_path):
    core, task_id, _ = seeded
    payload = criteria_export.snapshot(core, task_id, with_board=False)
    withdrawn = payload["lifecycle"]["pool_items_not_promoted"]["withdrawn"]
    assert [item["name"] for item in withdrawn] == ["Potency at T1 from a second curation"]
    assert withdrawn[0]["reason_kind"] == "withdrawn_by_reviser"
    assert withdrawn[0]["critic_findings"][0]["severity"] == "material"
    assert "Potency at T1 from a second curation" not in {card["name"] for card in payload["criteria"]}
    rendered = criteria_export.render_markdown(payload)
    body, lifecycle = rendered.split("## Lifecycle", 1)
    assert "Potency at T1 from a second curation" in lifecycle
    assert "Potency at T1 from a second curation" not in body.split("## Cards", 1)[1]


def test_quote_checking_and_semantic_verification_are_reported_as_separate_fields(seeded):
    core, task_id, claim_id = seeded
    card = criteria_export.snapshot(core, task_id, with_board=False)["criteria"][0]
    quote = card["verification"]["quote_check"]
    semantic = card["verification"]["semantic_support"]
    assert quote["field"] != semantic["field"]
    # The seeded claim passed span checking and was never semantically verified. One field says so
    # and the other must not: conflating them publishes either "no quote was checked" or "the
    # passage was confirmed to support the bound", and neither happened (handoff §7.1).
    assert (quote["span_checked_against_source"], quote["quote_verified"]) == (1, 1)
    assert semantic["states"] == {"unverified": 1}
    claim = card["support"]["claims_by_polarity"]["supports"][0]
    assert claim["claim_id"] == claim_id
    assert claim["quote_check"] == {"span_checked_against_source": True, "quote_verified": True}
    assert claim["numerical_consistency"] == "value_in_quote"
    assert claim["semantic_support"]["verification_status"] == "unverified"


def test_a_card_carries_the_four_facets_the_recovery_rubric_compares(seeded):
    core, task_id, _ = seeded
    facets = criteria_export.snapshot(core, task_id, with_board=False)["criteria"][0]["matching_facets"]
    assert facets["operational_quantity"]["subject_parameters"] == [{"target_chembl_id": "T1"}]
    assert facets["operational_quantity"]["unit"] == "pChEMBL"
    assert facets["decision_semantics"]["decision_role"] == "preference"
    assert facets["decision_semantics"]["predicate"].startswith("orders candidates")
    assert facets["threshold"]["state"] == "explicitly_absent"
    assert facets["measurement_identity_sha256"] != facets["decision_identity_sha256"]
    # Applicability is nowhere in the attribute schema, so the facet is reported as absent rather
    # than inferred from the definition prose: a recovery mapping must not rest on the exporter's
    # reading of a paragraph.
    assert any(gap.startswith("applicability") for gap in facets["gaps"])
    assert facets["comparable_from_fields"] is False


def test_the_derived_set_for_a_recovery_comparison_excludes_the_pruned_and_the_repeated(seeded):
    core, task_id, _ = seeded
    payload = criteria_export.snapshot(core, task_id, with_board=False)
    recovery = payload["recovery_comparison_set"]
    assert recovery["included_count"] == 1
    assert recovery["by_origin"] == {"literature_derived": {"count": 1,
                                                            "attribute_refs": ["attr_potency-at-t1@v1"]}}
    assert recovery["excluded_as_pruned_pool_items"] == 1
    assert recovery["excluded_as_a_repeated_variant"] == []
    assert recovery["duplicate_measurement_identities"] == []


def test_the_counts_reconcile_the_registry_against_the_pool(seeded):
    core, task_id, _ = seeded
    counts = criteria_export.snapshot(core, task_id, with_board=False)["counts"]
    assert counts["proposals_added_to_pool"]["value"] == 2
    assert counts["promoted_pool_items"]["value"] == 1
    assert counts["pruned_pool_items"]["value"] == 1
    assert counts["registered_criteria"]["value"] == 1
    assert counts["bounds"]["value"]["no_cutoff_evidence_insufficient"] == 1
    reconciliation = criteria_export.render_reconciliation(
        criteria_export.snapshot(core, task_id, with_board=False))
    assert "Why 34 and 40 differ" in reconciliation


def test_the_written_package_is_the_four_files_section_eleven_names(seeded, tmp_path):
    core, task_id, _ = seeded
    record = criteria_export.write(core, task_id, tmp_path / "out", with_board=False)
    written = sorted(path.name for path in (tmp_path / "out").iterdir())
    assert written == sorted([criteria_export.REVIEW_MARKDOWN, criteria_export.REVIEW_JSON,
                              criteria_export.MANIFEST_JSON, criteria_export.RECONCILIATION_MARKDOWN])
    assert record["store"]["opened"] == "read_only"
    on_disk = json.loads((tmp_path / "out" / criteria_export.REVIEW_JSON).read_text(encoding="utf-8"))
    assert on_disk["journal_position"]["pinned_seq"] == core.journal.last_seq(task_id)
    manifest = json.loads((tmp_path / "out" / criteria_export.MANIFEST_JSON).read_text(encoding="utf-8"))
    assert manifest["file_digests"][criteria_export.REVIEW_JSON]["sha256"] == \
        criteria_export.sha256_hex_bytes((tmp_path / "out" / criteria_export.REVIEW_JSON).read_bytes())


def test_the_export_never_appends_to_the_store_it_reads(seeded):
    core, task_id, _ = seeded
    pinned_core, _ = criteria_export.pinned(core, task_id)
    with pytest.raises(criteria_export.ExportError):
        pinned_core.journal.append(task_id, "task.version_recorded", actor=OPERATOR, payload={})
