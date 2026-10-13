import json

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
