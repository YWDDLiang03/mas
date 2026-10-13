"""The evidence firewall: no case-source document may enter the system's own evidence.

`core.reading.is_case_source` is the gate (called by `derivation._excluded` and `evidence.gather`).
These tests use the real deployment's case-source title and sha256 so they pin the live
configuration, and they cover the two ways a case source used to slip through: words appended to
its title, and an uploaded copy whose title is only its filename. No network.
"""

from __future__ import annotations

import hashlib

from mas.adapters.literature import uploads
from mas.core import reading

CASE_TITLE = "Multi-target TME Reprogramming Awakens TLS-driven Immunity in Ovarian Cancer"
CASE_HASH = "4332685173c953ddaf7adb855965378da580958fa904fd97ca9017acb34153d2"

CASE_SOURCES = [{"title": CASE_TITLE,
                 "identifiers": [{"scheme": "sha256", "value": CASE_HASH},
                                 {"scheme": "doi", "value": "10.1/MS"}]}]


# --- titles -----------------------------------------------------------------------------------

def test_the_exact_case_source_title_is_excluded():
    assert reading.is_case_source({"title": CASE_TITLE}, CASE_SOURCES)


def test_case_and_punctuation_changes_do_not_defeat_the_gate():
    assert reading.is_case_source({"title": CASE_TITLE.upper() + "."}, CASE_SOURCES)
    assert reading.is_case_source({"title": "Multi‑target TME reprogramming awakens TLS–driven "
                                            "immunity in ovarian cancer"}, CASE_SOURCES)


def test_words_appended_to_the_case_source_title_are_excluded():
    # Each of these is the manuscript itself; appending words drags Jaccard under 0.85
    # (the supplement is 10/12 = 0.83), so containment is what catches them.
    for title in (f"{CASE_TITLE}: supplementary methods",
                  f"{CASE_TITLE} (Supplementary material)",
                  f"Author Correction: {CASE_TITLE}",
                  f"Supplementary material for: {CASE_TITLE}",
                  # one token changed as well as two appended: containment 9/10, at the threshold
                  "Multi-target TME Reprogramming Awakens TLS-driven Immunity in Ovarian "
                  "Carcinoma: supplementary methods"):
        assert reading.is_case_source({"title": title}, CASE_SOURCES), title


def test_a_truncated_case_source_title_is_excluded():
    # The other direction: a listing or index that cut the title short. Jaccard is 8/10 = 0.80.
    assert reading.is_case_source({"title": "Multi-target TME Reprogramming Awakens TLS-driven Immunity"},
                                  CASE_SOURCES)


def test_a_short_case_source_title_does_not_swallow_an_unrelated_paper():
    short = [{"title": "TLS and Immunity"}]
    assert not reading.is_case_source(
        {"title": "TLS and immunity in colorectal cancer: a prospective cohort study"}, short)
    assert not reading.is_case_source({"title": "Tumour immunity and TLS formation in mice"}, short)
    # the short title still matches itself, on the Jaccard path
    assert reading.is_case_source({"title": "TLS and immunity."}, short)


def test_unrelated_literature_and_textbooks_are_still_admitted():
    assert not reading.is_case_source({"title": "TLS biology in ovarian cancer: a review"}, CASE_SOURCES)
    assert not reading.is_case_source(
        {"title": "Reprogramming the tumour microenvironment to drive TLS immunity in ovarian cancer",
         "doi": "10.2/other"}, CASE_SOURCES)
    assert not reading.is_case_source(
        {"source": "bookshelf", "title": "Ovarian cancer: epidemiology and risk factors",
         "identifiers": [{"scheme": "nbk", "value": "NBK123456"}]}, CASE_SOURCES)


def test_declared_identifiers_still_match_as_before():
    assert reading.is_case_source({"doi": "10.1/ms", "title": "anything at all"}, CASE_SOURCES)
    assert reading.is_case_source({"identifiers": [{"scheme": "doi", "value": "10.1/MS"}]}, CASE_SOURCES)
    assert not reading.is_case_source({"doi": "10.1/elsewhere", "title": "anything at all"}, CASE_SOURCES)


# --- uploaded copies --------------------------------------------------------------------------

def test_a_filename_titled_upload_is_caught_by_the_declared_full_hash():
    hit = {"source": "uploads", "upload_file": "CELL1.pdf", "title": "CELL1", "sha256": CASE_HASH,
           "identifiers": [{"scheme": "sha256", "value": CASE_HASH}]}
    assert reading.is_case_source(hit, CASE_SOURCES)
    # nothing in the title could have caught it, and a truncated digest is not a match
    assert not reading.is_case_source({"title": "CELL1", "upload_file": "CELL1.pdf"}, CASE_SOURCES)
    assert not reading.is_case_source(
        {"title": "CELL1", "identifiers": [{"scheme": "sha256", "value": CASE_HASH[:16]}]}, CASE_SOURCES)


def _library(tmp_path, body: str, title: str) -> tuple[uploads.UploadLibrary, dict, str]:
    (tmp_path / "CELL1.md").write_text(body)
    (tmp_path / "manifest.toml").write_text(
        f'[[document]]\nfile = "CELL1.md"\ntitle = "{title}"\nlicense = "own work"\n'
        'llm_ingestion_permitted = true\n')
    library = uploads.UploadLibrary(tmp_path)
    digest = hashlib.sha256((tmp_path / "CELL1.md").read_bytes()).hexdigest()
    return library, library.documents()[0], digest


def test_an_uploaded_document_hit_carries_its_full_digest(tmp_path):
    library, entry, digest = _library(tmp_path, "# Notes\n\nSomething about rodents and the diets they were kept on.\n", "Rodent notes")
    hit = library.hit(entry, 0, "lead")
    assert hit["identifiers"] == [{"scheme": "sha256", "value": digest}]
    assert len(digest) == 64 and hit["sha256"] == digest


def test_an_upload_whose_bytes_match_the_declared_hash_is_excluded_whatever_its_title_says(tmp_path):
    library, entry, digest = _library(
        tmp_path, "# Reprogramming\n\nTLS-driven immunity in ovarian cancer, the manuscript itself.\n",
        "Quarterly notes on an unrelated subject")
    declared = [{"title": CASE_TITLE, "identifiers": [{"scheme": "sha256", "value": digest}]}]
    hit = library.hit(entry, 0, "lead")
    assert not (reading._tokens(hit["title"]) & reading._tokens(CASE_TITLE))  # titles share no tokens
    assert reading.is_case_source(hit, declared)
    # the same bytes found by search, not just by hand
    found = [v["value"] for v in uploads.UploadsSearch(library).invoke(
        "search", {"query": "ovarian cancer immunity"}).values]
    assert found and all(reading.is_case_source(h, declared) for h in found)


def test_the_uploads_reader_still_reads_a_hit_with_the_full_digest(tmp_path):
    library, entry, digest = _library(tmp_path, "# Absorption\n\nA cleared document about the absorption of a kinase inhibitor.\n",
                                      "Food effects")
    hit = library.hit(entry, 0, "lead")
    document = uploads.UploadsReader(library).invoke("read", {"hit": hit}).values[0]["value"]
    assert document["identifiers"] == {"sha256": digest, "file": "CELL1.md"}
    assert document["passages"][1]["section_path"] == ["Absorption"]
    assert not reading.is_case_source(hit, CASE_SOURCES)  # a cleared upload is not a case source
