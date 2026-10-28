"""The evidence firewall: no case-source document may enter the system's own evidence.

`core.reading.is_case_source` is the gate (called by `derivation._excluded` and `evidence.gather`).
These tests use a synthetic case-source title and digest, and they cover the two ways a case source used to slip through: words appended to
its title, and an uploaded copy whose title is only its filename. No network.
"""

from __future__ import annotations

import hashlib

from mas.adapters.literature import uploads
from mas.core import reading

CASE_TITLE = "Evidence Guided Candidate Evaluation Improves Selection Across Diverse Research Tasks"
CASE_HASH = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

CASE_SOURCES = [{"title": CASE_TITLE,
                 "identifiers": [{"scheme": "sha256", "value": CASE_HASH},
                                 {"scheme": "doi", "value": "10.1/MS"}]}]


# --- titles -----------------------------------------------------------------------------------

def test_the_exact_case_source_title_is_excluded():
    assert reading.is_case_source({"title": CASE_TITLE}, CASE_SOURCES)


def test_case_and_punctuation_changes_do_not_defeat_the_gate():
    assert reading.is_case_source({"title": CASE_TITLE.upper() + "."}, CASE_SOURCES)
    assert reading.is_case_source({"title": "Evidence-guided candidate evaluation improves selection "
                                            "across diverse research tasks"}, CASE_SOURCES)


def test_words_appended_to_the_case_source_title_are_excluded():
    # Each of these is the manuscript itself; appending words drags Jaccard under 0.85
    # (the supplement is 10/12 = 0.83), so containment is what catches them.
    for title in (f"{CASE_TITLE}: supplementary methods",
                  f"{CASE_TITLE} (Supplementary material)",
                  f"Author Correction: {CASE_TITLE}",
                  f"Supplementary material for: {CASE_TITLE}",
                  # one token changed as well as two appended: containment 9/10, at the threshold
                  "Evidence Guided Candidate Evaluation Improves Selection Across Diverse Research "
                  "Studies: supplementary methods"):
        assert reading.is_case_source({"title": title}, CASE_SOURCES), title


def test_a_truncated_case_source_title_is_excluded():
    # The other direction: a listing or index that cut the title short. Jaccard is 8/10 = 0.80.
    assert reading.is_case_source({"title": "Evidence Guided Candidate Evaluation Improves Selection Across Diverse"},
                                  CASE_SOURCES)


def test_a_short_case_source_title_does_not_swallow_an_unrelated_paper():
    short = [{"title": "Evidence and Selection"}]
    assert not reading.is_case_source(
        {"title": "Evidence and selection in colorectal cancer: a prospective cohort study"}, short)
    assert not reading.is_case_source({"title": "Unrelated observations and measurements in samples"}, short)
    # the short title still matches itself, on the Jaccard path
    assert reading.is_case_source({"title": "Evidence and selection."}, short)


def test_unrelated_literature_and_textbooks_are_still_admitted():
    assert not reading.is_case_source({"title": "General evidence quality: a review"}, CASE_SOURCES)
    assert not reading.is_case_source(
        {"title": "Comparing candidate measurements across independently recorded research studies",
         "doi": "10.2/other"}, CASE_SOURCES)
    assert not reading.is_case_source(
        {"source": "bookshelf", "title": "Research methods: terminology and measurement",
         "identifiers": [{"scheme": "nbk", "value": "NBK123456"}]}, CASE_SOURCES)


def test_declared_identifiers_still_match_as_before():
    assert reading.is_case_source({"doi": "10.1/ms", "title": "anything at all"}, CASE_SOURCES)
    assert reading.is_case_source({"identifiers": [{"scheme": "doi", "value": "10.1/MS"}]}, CASE_SOURCES)
    assert not reading.is_case_source({"doi": "10.1/elsewhere", "title": "anything at all"}, CASE_SOURCES)


# --- uploaded copies --------------------------------------------------------------------------

def test_a_filename_titled_upload_is_caught_by_the_declared_full_hash():
    hit = {"source": "uploads", "upload_file": "private_source.pdf", "title": "private_source", "sha256": CASE_HASH,
           "identifiers": [{"scheme": "sha256", "value": CASE_HASH}]}
    assert reading.is_case_source(hit, CASE_SOURCES)
    # nothing in the title could have caught it, and a truncated digest is not a match
    assert not reading.is_case_source({"title": "private_source", "upload_file": "private_source.pdf"}, CASE_SOURCES)
    assert not reading.is_case_source(
        {"title": "private_source", "identifiers": [{"scheme": "sha256", "value": CASE_HASH[:16]}]}, CASE_SOURCES)


def _library(tmp_path, body: str, title: str) -> tuple[uploads.UploadLibrary, dict, str]:
    (tmp_path / "private_source.md").write_text(body)
    (tmp_path / "manifest.toml").write_text(
        f'[[document]]\nfile = "private_source.md"\ntitle = "{title}"\nlicense = "own work"\n'
        'llm_ingestion_permitted = true\n')
    library = uploads.UploadLibrary(tmp_path)
    digest = hashlib.sha256((tmp_path / "private_source.md").read_bytes()).hexdigest()
    return library, library.documents()[0], digest


def test_an_uploaded_document_hit_carries_its_full_digest(tmp_path):
    library, entry, digest = _library(tmp_path, "# Notes\n\nSomething about rodents and the diets they were kept on.\n", "Rodent notes")
    hit = library.hit(entry, 0, "lead")
    assert hit["identifiers"] == [{"scheme": "sha256", "value": digest}]
    assert len(digest) == 64 and hit["sha256"] == digest


def test_an_upload_whose_bytes_match_the_declared_hash_is_excluded_whatever_its_title_says(tmp_path):
    library, entry, digest = _library(
        tmp_path, "# Evidence\n\nCandidate evidence selection, the private study itself.\n",
        "Quarterly notes on an unrelated subject")
    declared = [{"title": CASE_TITLE, "identifiers": [{"scheme": "sha256", "value": digest}]}]
    hit = library.hit(entry, 0, "lead")
    assert not (reading._tokens(hit["title"]) & reading._tokens(CASE_TITLE))  # titles share no tokens
    assert reading.is_case_source(hit, declared)
    # the same bytes found by search, not just by hand
    found = [v["value"] for v in uploads.UploadsSearch(library).invoke(
        "search", {"query": "candidate evidence selection"}).values]
    assert found and all(reading.is_case_source(h, declared) for h in found)


def test_the_uploads_reader_still_reads_a_hit_with_the_full_digest(tmp_path):
    library, entry, digest = _library(tmp_path, "# Absorption\n\nA cleared document about the absorption of a kinase inhibitor.\n",
                                      "Food effects")
    hit = library.hit(entry, 0, "lead")
    document = uploads.UploadsReader(library).invoke("read", {"hit": hit}).values[0]["value"]
    assert document["identifiers"] == {"sha256": digest, "file": "private_source.md"}
    assert document["passages"][1]["section_path"] == ["Absorption"]
    assert not reading.is_case_source(hit, CASE_SOURCES)  # a cleared upload is not a case source
