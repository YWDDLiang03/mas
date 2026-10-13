import multiprocessing
import sqlite3

import pytest

from mas.core import vocab
from mas.core.artifacts import ArtifactStore
from mas.core.canonical import canonical_bytes, raw_sha256, sha256_hex, text_sha256
from mas.core.ids import new_id, prefix_of, slug, split_version, ulid, versioned
from mas.core.journal import Journal, actor
from mas.core.store import Store, StoreError, unsupported_root_reason


# --- canonical form (design §14.2) -------------------------------------------------

def test_canonical_bytes_ignore_key_order_and_line_endings():
    a = {"b": 1, "a": "line1\r\nline2", "c": [1.5, None, True]}
    b = {"c": [1.5, None, True], "a": "line1\nline2", "b": 1}
    assert canonical_bytes(a) == canonical_bytes(b)
    assert sha256_hex(a) == sha256_hex(b)


def test_canonical_bytes_normalize_unicode_to_nfc():
    composed = {"name": "café"}
    decomposed = {"name": "café"}
    assert canonical_bytes(composed) == canonical_bytes(decomposed)


def test_canonical_form_refuses_non_finite_numbers_and_non_string_keys():
    with pytest.raises(ValueError):
        canonical_bytes({"x": float("nan")})
    with pytest.raises(TypeError):
        canonical_bytes({1: "x"})


def test_supplied_files_hash_raw_bytes_but_text_hash_ignores_line_endings():
    assert raw_sha256(b"a\r\nb") != raw_sha256(b"a\nb")
    assert text_sha256("a\r\nb") == text_sha256("a\nb")


# --- identifiers (design §0.3) -----------------------------------------------------

def test_ulid_is_26_chars_and_time_sortable():
    early, late = ulid(1_000), ulid(2_000)
    assert len(early) == 26 and early < late


def test_new_id_refuses_unregistered_prefix():
    assert prefix_of(new_id("run")) == "run"
    with pytest.raises(ValueError):
        new_id("bogus")


def test_versioned_references_round_trip():
    ref = versioned("attr_oral-bioavailability", 3)
    assert split_version(ref) == ("attr_oral-bioavailability", 3)
    assert slug("Oral bioavailability (F%)") == "oral-bioavailability-f"


# --- state registry (C2) -----------------------------------------------------------

def test_vocabulary_refuses_unregistered_values():
    assert vocab.require("candidate", "provisional") == "provisional"
    with pytest.raises(vocab.VocabularyViolation):
        vocab.require("candidate", "maybe")
    with pytest.raises(vocab.VocabularyViolation):
        vocab.require_event_kind("run.exploded")


def test_unresolved_and_budget_exhausted_never_render_as_advancement():
    assert vocab.label("execution", "unresolved") == "unresolved"
    assert vocab.tone("termination_reason", "budget_exhausted") == "attention"
    assert vocab.label("verdict", "pass") == "pass"
    assert vocab.label("review", "none") == "no human review yet"


# --- store root (design §14.1) -----------------------------------------------------

def _try_open(path, queue):
    try:
        Store.open(path).close()
        queue.put("opened")
    except StoreError as error:
        queue.put(error.code)


def test_second_host_on_same_root_is_refused(tmp_path):
    root = tmp_path / "root"
    with Store.open(root):
        queue = multiprocessing.get_context("spawn").Queue()
        process = multiprocessing.get_context("spawn").Process(target=_try_open, args=(root, queue))
        process.start()
        process.join(30)
        assert queue.get(timeout=5) == "store_locked"
    # released when the first host closes
    with Store.open(root):
        pass


def test_synchronized_folders_are_unsupported(tmp_path):
    assert unsupported_root_reason(tmp_path / "Dropbox" / "mas") is not None
    assert unsupported_root_reason(tmp_path) is None


# --- journal (C1) ------------------------------------------------------------------

def test_seq_is_contiguous_per_stream(store):
    journal = Journal(store)
    who = actor("controller", "C15")
    run_a, run_b = new_id("run"), new_id("run")
    for _ in range(3):
        journal.append(run_a, "agent.heartbeat", actor=who)
    journal.append(run_b, "agent.heartbeat", actor=who)
    assert [e.seq for e in journal.replay(run_a)] == [1, 2, 3]
    assert [e.seq for e in journal.replay(run_b)] == [1]
    assert [e.seq for e in journal.replay(run_a, from_seq=2)] == [2, 3]
    journal.verify(run_a)


def test_journal_is_append_only(store):
    journal = Journal(store)
    run = new_id("run")
    journal.append(run, "run.created", actor=actor("controller", "C15"), state_to="queued")
    with pytest.raises(sqlite3.DatabaseError):
        store.db.execute("UPDATE events SET event_type = 'run.failed'")
    with pytest.raises(sqlite3.DatabaseError):
        store.db.execute("DELETE FROM events")


def test_journal_validates_kinds_states_and_streams(store):
    journal = Journal(store)
    run = new_id("run")
    who = actor("controller", "C15")
    with pytest.raises(vocab.VocabularyViolation):
        journal.append(run, "run.vanished", actor=who)
    with pytest.raises(vocab.VocabularyViolation):
        journal.append(run, "run.created", actor=who, state_to="half_done")
    with pytest.raises(ValueError):
        journal.append("not-a-stream", "run.created", actor=who)
    assert journal.last_seq(run) == 0


def test_events_round_trip_with_payload_hash(store):
    journal = Journal(store)
    task = new_id("task")
    written = journal.append(task, "task.version_recorded", actor=actor("human", "E1", "operator"),
                             payload={"version": 1, "objective_text": "x"})
    (read,) = journal.replay(task)
    assert read == written
    assert read.payload_hash == sha256_hex({"version": 1, "objective_text": "x"})


# --- artifacts (C3) ----------------------------------------------------------------

def test_artifacts_are_content_addressed_and_write_once(store):
    artifacts = ArtifactStore(store)
    first = artifacts.put("proposal", {"text": "a", "n": 1})
    again = artifacts.put("proposal", {"n": 1, "text": "a"})
    other = artifacts.put("proposal", {"text": "b", "n": 1})
    assert first == again != other
    assert artifacts.payload(first) == {"text": "a", "n": 1}
    with pytest.raises(sqlite3.DatabaseError):
        store.db.execute("DELETE FROM artifacts")
