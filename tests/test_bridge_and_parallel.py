import json
import os

from mas.cli import bridge
from mas.core.controller import RunController
from mas.core import leaderboard
from tests.test_run_end_to_end import OPERATOR, make_controller, setup_task  # noqa: F401  (fixtures reused)
from mas.core.runtime import Core


def test_bridge_claims_split_requests_between_agents(tmp_path, capsys):
    root = tmp_path / "x"
    (root / "requests").mkdir(parents=True)
    (root / "responses").mkdir()
    for name in ("r1", "r2"):
        (root / "requests" / f"{name}.json").write_text(json.dumps({"request_id": name}))
    assert bridge.cmd_next(root, 0, "agent-a") == 0
    first = json.loads(capsys.readouterr().out)["request_id"]
    assert bridge.cmd_next(root, 0, "agent-b") == 0
    second = json.loads(capsys.readouterr().out)["request_id"]
    assert {first, second} == {"r1", "r2"}
    assert bridge.cmd_next(root, 0, "agent-a") == 0                # re-delivered to the agent that claimed it
    assert json.loads(capsys.readouterr().out)["request_id"] == first
    assert bridge.cmd_next(root, 0, "agent-c") == 2                # nothing unclaimed is left


def test_a_done_marker_from_an_earlier_run_does_not_end_the_next_one(tmp_path, capsys):
    """A DONE marker left behind cost a whole stage once: `next --wait` returned at once, the
    polling agent concluded the work was over, and the run waited for an answer nobody was
    coming to give. A marker older than the newest request is treated as what it is."""
    root = tmp_path / "x"
    (root / "requests").mkdir(parents=True)
    (root / "responses").mkdir()
    (root / "DONE").write_text("")

    assert bridge.cmd_next(root, 0, "agent-a") == 3                      # nothing pending, marker is current
    assert json.loads(capsys.readouterr().out)["status"] == "done"

    request = root / "requests" / "r1.json"
    request.write_text(json.dumps({"request_id": "r1"}))
    os.utime(root / "DONE", (1, 1))                                      # the marker predates the request
    assert bridge.cmd_next(root, 0, "agent-a") == 0                      # delivered, not declared finished
    assert json.loads(capsys.readouterr().out)["request_id"] == "r1"

    (root / "responses" / "r1.json").write_text(json.dumps({"request_id": "r1"}))
    assert bridge.cmd_next(root, 0, "agent-b") == 2                      # answered, and the stale marker stays inert
    assert json.loads(capsys.readouterr().out)["status"] == "no_pending_request"


def test_parallel_literature_cells_give_the_same_board(tmp_path):
    results = []
    for workers in (1, 4):
        with Core.open(tmp_path / f"root{workers}") as core:
            task_id = setup_task(core)
            controller = make_controller(core)
            controller.workers = workers
            run_id = controller.start(task_id, by=OPERATOR, sweep_seed=3)
            assert controller.current_state(run_id) == "completed"
            (snapshot,) = leaderboard.snapshots(core, task_id)
            results.append([(e["candidate_ref"], e["state"], e["position"]) for e in snapshot["candidate_entries"]])
            core.journal.verify(run_id)
    assert results[0] == results[1]


def test_the_sweep_hands_every_literature_cell_the_configured_read_worker_count(tmp_path, monkeypatch):
    """Through the seam a run goes through, not past it. `concurrency.read_workers` is read off the
    bound settings by their dotted key, so a key that does not match the one `config.SETTINGS`
    registers would leave every cell reading sequentially while the setting said otherwise -- and
    `.get(key, 1)` cannot report that, it can only default."""
    from mas.core import config as config_mod, evidence

    asked = []
    gather = evidence.gather

    def spy(*args, **kwargs):
        asked.append(kwargs.get("document_workers"))
        return gather(*args, **kwargs)

    monkeypatch.setattr(evidence, "gather", spy)
    with Core.open(tmp_path / "root") as core:
        task_id = setup_task(core)
        settings = config_mod.resolve(project_file=None, environ={}, overrides={"concurrency.read_workers": 4})
        controller = make_controller(core)
        run_id = controller.start(task_id, by=OPERATOR, sweep_seed=3, settings=settings)
        assert controller.current_state(run_id) == "completed"
    assert asked and set(asked) == {4}
