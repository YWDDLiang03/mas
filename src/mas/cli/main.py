"""`mas`: the terminal client (`ui_ux_spec.md` §15.3).

    mas init                                   create a store root and an example models.toml
    mas task new --from FILE.json | task list | task show TASK
    mas criteria propose TASK --from FILE.json  propose attribute+rule pairs written by a person
    mas criteria derive TASK [--dimension D ...] derive criteria from literature (LLM roles)
    mas rules confirm TASK [--allow-pending] | rules show TASK
    mas review list [TASK] | review decide ITEM --decision D --reason TEXT --exposure E
    mas run start TASK [--seed N] [--limit N] [--tool-calls N] [--llm-turns N] | run show RUN | run resume RUN
    mas board show TASK [--all] | candidate show TASK CANDIDATE
    mas models show
    mas bridge next|answer|status ...          answer LLM requests as an outside agent

Global options: --store DIR (default $MAS_STORE or ./var/store), --models FILE (default STORE/models.toml).
Expert decisions are confirmed on the terminal itself; a script cannot supply the confirmation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from mas.core import criteria, leaderboard, projection, review, task, vocab
from mas.core.broker import Broker
from mas.core.controller import RunController, RunError
from mas.core.journal import actor
from mas.core.models import ModelRoster
from mas.core.runtime import Core
from mas.core.store import StoreError

EXAMPLE_MODELS = '''# Model providers and role bindings. API keys are read from the environment, never stored.
#
# kind = "exchange"          requests go to a folder and are answered by an outside agent
#                            (for example Claude subagents via `mas bridge`)
# kind = "anthropic"         Anthropic Messages API (api_key_env, model)
# kind = "openai_compatible" any OpenAI-compatible endpoint (base_url, api_key_env, model)

[providers.subagents]
kind = "exchange"
exchange_dir = "llm_exchange"
model = "claude-opus (subagent)"
provider_family = "anthropic"

# [providers.anthropic]
# kind = "anthropic"
# model = "claude-opus-5-5"
# api_key_env = "ANTHROPIC_API_KEY"

# [providers.my_provider]
# kind = "openai_compatible"
# base_url = "https://api.example.com/v1"
# api_key_env = "MY_PROVIDER_API_KEY"
# model = "my-model"

[roles]
retriever = "subagents"
reader = "subagents"
summarizer = "subagents"
proposer = "subagents"
critic = "subagents"
'''


def _person(role: str) -> dict[str, Any]:
    name = os.environ.get("MAS_PERSON") or os.environ.get("USER") or "operator"
    return actor("human", name, role, identity_basis="recorded_attestation", via={"surface": "terminal"})


def _store_dir(args) -> Path:
    return Path(args.store or os.environ.get("MAS_STORE") or "var/store")


def _open(args) -> Core:
    try:
        return Core.open(_store_dir(args))
    except StoreError as error:
        sys.exit(f"cannot open store: {error}")


def _implementation() -> dict[str, Any]:
    """Package version and source commit, bound into every run so its strategy is identifiable."""
    import subprocess
    import mas
    commit, dirty = None, None
    try:
        root = Path(mas.__file__).resolve().parents[2]
        commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or None
        dirty = bool(subprocess.run(["git", "-C", str(root), "status", "--porcelain", "src"], capture_output=True,
                                    text=True).stdout.strip())
    except OSError:
        pass
    return {"package_version": mas.__version__, "code_commit": commit, "uncommitted_changes": dirty}


def _universe_file(context: dict[str, Any] | None) -> str | None:
    path = ((context or {}).get("candidate_universe") or {}).get("access_path")
    return path if path and path.endswith(".json") and Path(path).exists() else None


def _broker(core: Core, context: dict[str, Any] | None = None) -> Broker:
    from mas.adapters.drug.registration import register
    broker = Broker(core)
    register(broker, universe_file=_universe_file(context))
    return broker


def _expand_universe(spec: dict[str, Any]) -> dict[str, Any]:
    """A universe given as a documented file (access_path) is expanded into members at task creation."""
    universe = dict(spec.get("candidate_universe") or {})
    path = universe.get("access_path")
    if path and path.endswith(".json") and not universe.get("members"):
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        universe.update({"members": [m["inchikey"] for m in record["universe"]], "size_if_known": len(record["universe"]),
                         "source": universe.get("source") or record["source"],
                         "as_of": universe.get("as_of") or record["retrieved_at"], "kind": universe.get("kind", "named_library")})
    return dict(spec, candidate_universe=universe)


def _roster(args, required: bool = True) -> ModelRoster | None:
    path = Path(args.models) if args.models else _store_dir(args) / "models.toml"
    if not path.exists():
        if required:
            sys.exit(f"no model configuration at {path}; run `mas init` or pass --models")
        return None
    return ModelRoster.from_toml(path)


def _print(data: Any) -> None:
    print(json.dumps(data, indent=1, ensure_ascii=False, default=str))


def _confirm_on_terminal(prompt: str, expected: str) -> bool:
    """Read the confirmation from the terminal itself, never from stdin or a flag."""
    try:
        with open("/dev/tty", "r+") as tty:
            tty.write(f"{prompt}\nconfirm by typing {expected}: ")
            tty.flush()
            return tty.readline().strip() == expected
    except OSError:
        return False


# --- commands ---------------------------------------------------------------------------

def cmd_init(args) -> None:
    root = _store_dir(args)
    with Core.open(root):
        pass
    models = root / "models.toml"
    if not models.exists():
        models.write_text(EXAMPLE_MODELS, encoding="utf-8")
    print(f"store ready at {root}; model configuration at {models}")


def cmd_task(args) -> None:
    with _open(args) as core:
        if args.action == "new":
            spec = _expand_universe(json.loads(Path(args.file).read_text(encoding="utf-8")))
            task_id, version = task.record_version(core, spec, by=_person("operator"))
            print(f"{task_id}@v{version}")
        elif args.action == "list":
            for context in task.list_tasks(core):
                print(f"{context['task_context_id']}@v{context['version']}  {context['group_id']}  {context['objective_text'][:80]}")
        else:
            _print(task.get(core, args.task))


def cmd_criteria(args) -> None:
    with _open(args) as core:
        if args.action == "propose":
            pairs = json.loads(Path(args.file).read_text(encoding="utf-8"))
            for pair in pairs:
                refs = criteria.propose(core, args.task, pair["attribute"], pair["rule"], by=_person("operator"))
                print("proposed", *refs)
        elif args.action == "mandated":
            from mas.adapters.drug.registration import objective_templates
            from mas.core import derivation
            _print(derivation.objective_criteria(core, args.task, templates=objective_templates, by=_person("operator")))
        else:
            from mas.adapters.drug.registration import DIMENSIONS, EVIDENCE_CATALOG, objective_templates
            dimensions = [d for d in DIMENSIONS if not args.dimension or d["dimension"] in args.dimension]
            from mas.core import derivation
            from mas.core.budget import Budget
            record = derivation.derive(core, _broker(core, task.get(core, args.task)), _roster(args), args.task, dimensions=dimensions,
                                       catalog=EVIDENCE_CATALOG, by=_person("operator"), cutoff_date=args.cutoff,
                                       max_documents=args.max_documents, templates=objective_templates,
                                       budget=Budget({"llm_turns": args.llm_turns} if args.llm_turns else {}))
            _print({k: record[k] for k in ("dimensions", "mandated", "accepted", "disputed", "considered_and_rejected",
                                           "revisions")})


def cmd_rules(args) -> None:
    with _open(args) as core:
        if args.action == "confirm":
            print(criteria.confirm_rule_set(core, args.task, by=_person("operator"), allow_pending=args.allow_pending,
                                            coverage_floor=args.coverage_floor,
                                            defer_capabilities=tuple(args.defer_capability or ()),
                                            defer_reason=args.defer_reason or ""))
            return
        rules = criteria.rule_set(core, args.task)
        print(f"{rules['rule_set_ref']}  acceptance: {rules['acceptance_label']}  pending: {rules['pending']}")
        for item in rules.get("deferred", []):
            print(f"  deferred {item['rule_ref']} ({item['capability']}): {item['reason']}")
        for entry in rules["entries"]:
            rule = criteria.load(core, entry["rule_ref"], args.task)
            attribute = criteria.load(core, entry["attribute_ref"], args.task)
            cutoff = rule.get("cutoff") or {}
            print(f"  {entry['rule_ref']:<44} {rule['rule_kind']:<16} {attribute['name']}: "
                  f"{cutoff.get('comparator', rule.get('predicate_form', ''))} {cutoff.get('value', '')} {cutoff.get('unit', '')}"
                  f"  [{entry['confirmed_by']}]")


def cmd_review(args) -> None:
    with _open(args) as core:
        streams = [args.task] if getattr(args, "task", None) else core.journal.streams("task_") + core.journal.streams("run_")
        items = review.items(core, streams)
        if args.action == "list":
            for item in items.values():
                if item["state"] in ("open", "in_review"):
                    print(f"{item['item_id']}  {item['subject']['kind']:<14} {item['subject']['id']:<40} {item['why_expert_required']}")
            return
        item = items.get(args.item)
        if item is None:
            sys.exit(f"no such review item {args.item}")
        person = _person("expert")
        entry = "interactive" if _confirm_on_terminal(
            f"{args.decision} {item['subject']['kind']} {item['subject']['id']} as {person['id']} "
            f"(original-list exposure: {args.exposure})", item["item_id"]) else "scripted"
        try:
            decision = review.decide(core, item, decision=args.decision, actor=person, reason_text=args.reason or "",
                                     entry=entry, historical_list_exposure=args.exposure)
        except review.ReviewError as error:
            sys.exit(f"{vocab.label('command_outcome', error.code)}: {error}")
        print(f"{vocab.label('command_outcome', 'applied')}: {decision['decision_id']}")


def cmd_run(args) -> None:
    with _open(args) as core:
        from mas.adapters.drug.registration import ADAPTER
        task_id = args.task if args.action == "start" else None
        if task_id is None:
            created = core.journal.replay(args.run, 1, 1)
            task_id = created[0].payload["task_id"] if created else None
        context = task.get(core, task_id) if task_id else None
        controller = RunController(core, _broker(core, context), _roster(args, required=False), adapter=ADAPTER,
                                   implementation=_implementation())
        try:
            if args.action == "start":
                envelope = {k: v for k, v in (("tool_calls", args.tool_calls), ("llm_turns", args.llm_turns)) if v}
                run_id = controller.start(args.task, by=_person("operator"), sweep_seed=args.seed, budget_envelope=envelope,
                                          candidate_limit=args.limit, evidence_cutoff=args.cutoff, execute=False)
                print(run_id, flush=True)
                controller.execute(run_id)
            elif args.action == "resume":
                run_id = args.run
                controller.resume(run_id)
            else:
                run_id = args.run
        except RunError as error:
            sys.exit(str(error))
        view = projection.progress(core, run_id)
        print(f"{run_id}: {view['state_label']}  ({view['termination_reason']})  snapshot {view['snapshot_id']}")
        for row in view["progress"]:
            percent = f" {row['percent']}%" if "percent" in row else ""
            print(f"  {row['scope']:<16} {row['completed']} / {row['planned']} {row['denominator_kind']}{percent}")
        print(f"  verdicts: {view['verdict_counts']}")


def cmd_board(args) -> None:
    with _open(args) as core:
        shots = leaderboard.snapshots(core, args.task)
        if not shots:
            sys.exit("no snapshot yet")
        snap = shots[-1]
        print(f"{snap['snapshot_id']}  {snap['result_kind']}  rules {snap['rules@v']}  evidence {snap['evidence_snapshot_id']}")
        tuple_ = snap["reporting_tuple"]
        print(f"  admitted {tuple_['admitted_n']} · precision n/a without labels · coverage {tuple_['coverage_fraction']:.2f}"
              f" · sweep completeness {tuple_['sweep_completeness']:.2f} · abstentions {tuple_['abstention_n_by_reason']}")
        rows = snap["candidate_entries"] if args.all else snap["candidate_entries"][: args.top]
        for e in rows:
            score = "" if e["preference_score"] is None else f"{e['preference_score']:.2f}"
            position = e["position"] or "-"
            print(f"  {str(position):>4}  {vocab.label('candidate', e['state']):<12} {score:>5}  "
                  f"{(e['identity_labels'][0] or e['candidate_ref'])[:28]:<28} {e['state_reason'][:60]}")
        if not args.all and len(snap["candidate_entries"]) > args.top:
            print(f"  … {len(snap['candidate_entries']) - args.top} more (show all with --all)")


def cmd_candidate(args) -> None:
    with _open(args) as core:
        snap = leaderboard.snapshots(core, args.task)[-1]
        entry = next((e for e in snap["candidate_entries"] if e["candidate_ref"] == args.candidate
                      or args.candidate.lower() in (e["identity_labels"][0] or "").lower()), None)
        if entry is None:
            sys.exit("candidate not in the latest snapshot")
        print(f"{entry['candidate_ref']}  {entry['identity_labels'][0]}  {vocab.label('candidate', entry['state'])}"
              f"  position {entry['position']}  score {entry['preference_score']}")
        print(f"  reason: {entry['state_reason']}")
        for event in core.journal.replay(snap["run_id"]):
            if event.event_type == "candidate.assessed" and event.payload["candidate_ref"] == entry["candidate_ref"]:
                cell = core.artifacts.payload(event.payload["artifact_id"])
                reason = core.artifacts.payload(event.payload["reason_artifact_id"])
                print(f"  {cell['attribute_ref']:<44} {vocab.label('verdict', cell['verdict']):<20} {reason['reason_text']}")
                for claim_id in cell["value_source_claim_refs"][:3]:
                    print(f"      evidence {claim_id}")


def cmd_models(args) -> None:
    roster = _roster(args)
    _print(roster.role_bindings())


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "bridge":
        from mas.cli.bridge import main as bridge_main
        return bridge_main(argv[1:])
    parser = argparse.ArgumentParser(prog="mas", description=__doc__.split("\n")[0])
    parser.add_argument("--store")
    parser.add_argument("--models")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)

    t = sub.add_parser("task")
    t.add_argument("action", choices=("new", "list", "show"))
    t.add_argument("task", nargs="?")
    t.add_argument("--from", dest="file")
    t.set_defaults(func=cmd_task)

    c = sub.add_parser("criteria")
    c.add_argument("action", choices=("propose", "derive", "mandated"))
    c.add_argument("task")
    c.add_argument("--from", dest="file")
    c.add_argument("--dimension", action="append")
    c.add_argument("--cutoff", help="evidence cutoff date YYYY-MM-DD")
    c.add_argument("--max-documents", type=int, default=6)
    c.add_argument("--llm-turns", type=int)
    c.set_defaults(func=cmd_criteria)

    r = sub.add_parser("rules")
    r.add_argument("action", choices=("confirm", "show"))
    r.add_argument("task")
    r.add_argument("--allow-pending", action="store_true")
    r.add_argument("--coverage-floor", type=float, default=1.0)
    r.add_argument("--defer-capability", action="append", help="list rules needing this capability as deferred")
    r.add_argument("--defer-reason")
    r.set_defaults(func=cmd_rules)

    v = sub.add_parser("review")
    v.add_argument("action", choices=("list", "decide"))
    v.add_argument("item", nargs="?")
    v.add_argument("--task")
    v.add_argument("--decision", choices=sorted(vocab.DOMAINS["hd_decision"]))
    v.add_argument("--reason")
    v.add_argument("--exposure", default="undeclared", choices=sorted(vocab.DOMAINS["historical_list_exposure"]))
    v.set_defaults(func=cmd_review)

    u = sub.add_parser("run")
    u.add_argument("action", choices=("start", "show", "resume"))
    u.add_argument("task_or_run")
    u.add_argument("--seed", type=int, default=0)
    u.add_argument("--limit", type=int)
    u.add_argument("--tool-calls", type=int)
    u.add_argument("--llm-turns", type=int)
    u.add_argument("--cutoff")
    u.set_defaults(func=cmd_run)

    b = sub.add_parser("board")
    b.add_argument("action", choices=("show",))
    b.add_argument("task")
    b.add_argument("--top", type=int, default=25)
    b.add_argument("--all", action="store_true")
    b.set_defaults(func=cmd_board)

    d = sub.add_parser("candidate")
    d.add_argument("action", choices=("show",))
    d.add_argument("task")
    d.add_argument("candidate")
    d.set_defaults(func=cmd_candidate)

    m = sub.add_parser("models")
    m.add_argument("action", choices=("show",))
    m.set_defaults(func=cmd_models)

    args = parser.parse_args(argv)
    if args.command == "run":
        args.task = args.run = args.task_or_run
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
