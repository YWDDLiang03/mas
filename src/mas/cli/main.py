"""`mas`: the terminal client (`ui_ux_spec.md` §15.3).

    mas init                                   create a store root and an example models.toml
    mas task new --from FILE.json | task list | task show TASK
    mas criteria propose TASK --from FILE.json  propose attribute+rule pairs written by a person
    mas criteria derive TASK [--dimension D ...] [--continues RUN] [--single-pass]
                                               derive criteria from literature: a round of the pool workflow
    mas criteria pool TASK [--all]             the criteria pool: states, versions, lineage
    mas rules confirm TASK [--allow-pending] | rules show TASK
    mas review list [TASK] | review decide ITEM --decision D --reason TEXT --exposure E
    mas run start TASK [--seed N] [--limit N] [--tool-calls N] [--llm-turns N] | run show RUN | run resume RUN
    mas board show TASK [--all] | candidate show TASK CANDIDATE
    mas score show TASK                        the ordering method: a fitted expression, its fit and its holdout test
    mas models show
    mas config show [--explain] | validate | save NAME | estimate [--dimensions N] [--candidates N]
    mas sources list | check | sync bookshelf --book NBK... | template   evidence sources and their set-up
    mas bridge next|answer|status ...          answer LLM requests as an outside agent

Global options: --store DIR (default $MAS_STORE or ./var/store), --models FILE (default STORE/models.toml),
--config FILE (default ./mas.toml, else STORE/mas.toml), --preset quick|standard|deep, --profile NAME,
--set KEY=VALUE (repeatable; outranks MAS__SECTION__KEY environment variables).
Expert decisions are confirmed on the terminal itself; a script cannot supply the confirmation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from mas.core import config as config_mod
from mas.core import criteria, leaderboard, projection, review, sr_stage, task, vocab
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

# DeepSeek V4.1 Flash (1M context). The key is read at call time from the variable or the file.
# Extraction and judging roles run with thinking disabled so temperature 0 is honoured;
# prices (USD per million tokens, peak rates) let the run account its spend.
# [providers.deepseek]
# kind = "openai_compatible"
# base_url = "https://api.deepseek.com"
# model = "deepseek-flash"
# api_key_env = "DEEPSEEK_API_KEY"
# api_key_file = "~/deepseek-key"
# thinking = false
# price_input_per_mtok = 0.30
# price_output_per_mtok = 1.20
#
# [providers.deepseek_thinking]
# kind = "openai_compatible"
# base_url = "https://api.deepseek.com"
# model = "deepseek-flash"
# api_key_env = "DEEPSEEK_API_KEY"
# api_key_file = "~/deepseek-key"
# thinking = true
# reasoning_effort = "high"
# price_input_per_mtok = 0.30
# price_output_per_mtok = 1.20

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


def _cache_dir(args) -> str | None:
    return _settings(args)["sources.cache_dir"] or None


def _upload_dir(args) -> Path:
    return Path(_settings(args)["sources.upload_dir"] or _store_dir(args) / "uploads")


def _broker(core: Core, context: dict[str, Any] | None = None, args=None) -> Broker:
    from mas.adapters.drug.registration import register
    broker = Broker(core)
    register(broker, universe_file=_universe_file(context), cache_dir=_cache_dir(args) if args else None,
             upload_dir=str(_upload_dir(args)) if args else None)
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


def _config_file(args) -> Path | None:
    if getattr(args, "config", None):
        return Path(args.config)
    for candidate in (Path(config_mod.PROJECT_FILE), _store_dir(args) / config_mod.PROJECT_FILE):
        if candidate.exists():
            return candidate
    return None


def _settings(args) -> "config_mod.Config":
    try:
        return config_mod.resolve(preset=getattr(args, "preset", None) or "standard", project_file=_config_file(args),
                                  profile=getattr(args, "profile", None),
                                  overrides=config_mod.parse_overrides(getattr(args, "set", None) or []))
    except config_mod.ConfigError as error:
        sys.exit(f"configuration: {error}")


def _roster(args, required: bool = True) -> ModelRoster | None:
    settings = _settings(args)
    if settings.providers and not args.models:
        source = _config_file(args)
        return ModelRoster.from_tables(settings.providers, settings.roles, source.parent if source else _store_dir(args))
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
        elif args.action == "shortlist":
            from mas.core import staging
            new_task = staging.shortlist_task(core, args.task, top_k=args.top, by=_person("operator"))
            context = task.get(core, new_task)
            print(f"{new_task}@v1  {context['candidate_universe']['size_if_known']} candidates "
                  f"({context['candidate_universe']['source']})")
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
        elif args.action == "pool":
            _show_pool(core, args.task, show_all=args.all)
        else:
            from mas.adapters.drug.registration import DIMENSIONS, EVIDENCE_CATALOG, objective_templates
            from mas.core import derivation, derivation_run
            from mas.core.budget import from_config
            dimensions = [d for d in DIMENSIONS if not args.dimension or d["dimension"] in args.dimension]
            settings = _settings(args)
            research = derivation.research_params(settings)
            if args.max_documents:
                research["max_documents"] = args.max_documents
            budget = from_config(settings, envelope={"llm_turns": args.llm_turns} if args.llm_turns else None)
            broker = _broker(core, task.get(core, args.task), args)
            cutoff = args.cutoff or settings["search.date_to"] or None
            if args.single_pass:
                record = derivation.derive(core, broker, _roster(args), args.task, dimensions=dimensions,
                                           catalog=EVIDENCE_CATALOG, by=_person("operator"), cutoff_date=cutoff,
                                           templates=objective_templates, research=research, budget=budget)
                _print({k: record[k] for k in ("dimensions", "mandated", "accepted", "disputed", "considered_and_rejected",
                                               "revisions")})
                return
            try:
                record = derivation_run.derive_iterative(
                    core, broker, _roster(args), args.task, dimensions=dimensions, catalog=EVIDENCE_CATALOG,
                    by=_person("operator"), research=research, inner_iterations=settings["criteria.inner_iterations"],
                    stall_rounds=settings["criteria.stall_rounds"], stage_names=tuple(settings["criteria.stages"]),
                    max_refines=settings["criteria.max_refines"], merge_overlap=settings["criteria.merge_overlap"],
                    cutoff_date=cutoff, budget=budget, templates=objective_templates,
                    continues_run_id=args.continues, settings=settings, implementation=_implementation())
            except derivation_run.DerivationError as error:
                sys.exit(str(error))
            print(f"{record['run_id']}  round {record['round_index']}  {record['termination_reason']}  "
                  f"pool {record['pool_states']}")
            for e in record.get("enumeration", []):
                print(f"  {e['dimension']:<28} {e['documents_read']} documents, {e['n_topics']} topics ({e['stop_reason']})")
            for i in record.get("iterations", []):
                print(f"  iteration {i['iteration']}: " + "; ".join(f"{k} {v}" for k, v in i.items()
                                                                   if k not in ("iteration", "pool_changed")))
            promotion = record.get("promotion") or {}
            for key in ("accepted", "disputed"):
                for item in promotion.get(key, []):
                    print(f"  {key:<9} {item['rule_ref']:<44} {item['rule_kind']:<16} {item['name']}")
            for item in promotion.get("deferred", []):
                print(f"  deferred  {item['name']}: {'; '.join(item['problems'])[:100]}")
            print(f"  next: {record['continuation_decision']['decision']}"
                  + (f" (continue with --continues {record['run_id']})" if record['continuation_decision']['decision']
                     == "continue_next_round" else ""))


def _show_pool(core: Core, task_id: str, *, show_all: bool) -> None:
    from mas.core import pool as pool_mod
    folded = pool_mod.fold(core, task_id)
    if not folded:
        sys.exit("the criteria pool is empty; run `mas criteria derive TASK`")
    counts: dict[str, int] = {}
    for entry in folded.values():
        counts[entry["state"]] = counts.get(entry["state"], 0) + 1
    print("pool: " + ", ".join(f"{vocab.label('criterion_pool_state', k)} {v}" for k, v in sorted(counts.items())))
    order = ("promoted", "candidate", "needs_refine", "deferred_next_round", "merged_away", "withdrawn", "filtered_out")
    for entry in sorted(folded.values(), key=lambda e: (order.index(e["state"]), e["item"]["attribute"].get("name", ""))):
        if not show_all and entry["state"] in ("merged_away", "withdrawn", "filtered_out"):
            continue
        attribute = entry["item"]["attribute"]
        line = (f"  {entry['criterion_id']}@v{entry['version']:<3} {vocab.label('criterion_pool_state', entry['state']):<26} "
                f"{attribute.get('name', '')[:48]:<48} {attribute.get('unit') or ''}")
        if entry["promoted_as"]:
            line += f"  -> {entry['promoted_as']['rule_ref']}"
        print(line)
        if entry["parents"]:
            print(f"      merged from {', '.join(entry['parents'])}")
        if show_all:
            last = entry["history"][-1]
            print(f"      last: {last['operation']} at {last['stage']} ({last['reason_kind']}) {last['reason_text'][:80]}")
    if not show_all:
        print("  (merged, withdrawn and filtered items hidden; show them with --all)")


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
        settings = _settings(args)
        workers = args.workers or settings["assess.workers"]
        controller = RunController(core, _broker(core, context, args), _roster(args, required=False), adapter=ADAPTER,
                                   implementation=_implementation(), workers=workers)
        try:
            if args.action == "start":
                envelope = {k: v for k, v in (("tool_calls", args.tool_calls), ("llm_turns", args.llm_turns)) if v}
                seed = args.seed if args.seed is not None else settings["run.seed"]
                limit = args.limit or settings["assess.max_candidates"] or None
                run_id = controller.start(args.task, by=_person("operator"), sweep_seed=seed, budget_envelope=envelope,
                                          candidate_limit=limit, evidence_cutoff=args.cutoff or settings["search.date_to"] or None,
                                          execute=False, settings=settings)
                print(run_id, flush=True)
                controller.execute(run_id)
            elif args.action == "resume":
                run_id = args.run
                bound = (_bound_settings(core, run_id) or {}).get("config_hash")
                if bound and bound != settings.hash() and not args.allow_config_drift:
                    sys.exit(f"the settings changed since {run_id} was bound (hash {bound[:12]} -> {settings.hash()[:12]}); "
                             "resume with the original settings or pass --allow-config-drift")
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
        if snap.get("abstention_reason"):
            print(f"  {vocab.label('result_kind', snap['result_kind'])}: "
                  f"{vocab.label('abstention_reason', snap['abstention_reason'])}")
        method = snap.get("ordering_method") or {}
        if method.get("kind") == "symbolic_expression":
            print(f"  score = {method['expression_text']}  ({method['provenance']}; `mas score show` for the fit)")
        args.top = args.top or _settings(args)["rank.top_n"]
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
        explained = sr_stage.rationale_of(core, snap["run_id"], entry["candidate_ref"])
        if explained:
            print(f"  score {explained['score']:.4f} · coverage {explained['coverage']:.2f} · "
                  f"intercept {explained['intercept']:+.4f}; terms by contribution:")
            for item in explained["terms"]:
                share = f"{(item['share'] or 0) * 100:3.0f}%"
                print(f"    {item['contribution']:+9.4f} {share}  {item['term']:<34} value {item['value']:<12.4g}"
                      f" × {item['coefficient']:+.4f}  {item['grounding']}")
                for claim_id in item["claim_refs"][:3]:
                    print(f"        evidence {claim_id}")
            for missing in explained["terms_missing"]:
                print(f"    {'no value':>14}  {missing['term']:<34} missing "
                      f"{', '.join(missing['missing_features'])}")
        for event in core.journal.replay(snap["run_id"]):
            if event.event_type == "candidate.assessed" and event.payload["candidate_ref"] == entry["candidate_ref"]:
                cell = core.artifacts.payload(event.payload["artifact_id"])
                reason = core.artifacts.payload(event.payload["reason_artifact_id"])
                print(f"  {cell['attribute_ref']:<44} {vocab.label('verdict', cell['verdict']):<20} {reason['reason_text']}")
                for claim_id in cell["value_source_claim_refs"][:3]:
                    print(f"      evidence {claim_id}")


def cmd_score(args) -> None:
    """How the published score was produced, and what the alternative scored on the holdout."""
    with _open(args) as core:
        shots = leaderboard.snapshots(core, args.task)
        if not shots:
            sys.exit("no snapshot yet")
        snap = shots[-1]
        method = snap.get("ordering_method") or {}
        rules = criteria.rule_set(core, args.task, snap["rules@v"])
        print(f"{snap['snapshot_id']}  rules {snap['rules@v']}  ordering method: "
              f"{method.get('kind', 'weighted_preference')}")
        print(f"  acceptance: {vocab.label('acceptance_label', rules['acceptance_label'])}"
              + ("".join(f"\n    - {reason}" for reason in rules.get("acceptance_reasons") or [])))
        if method.get("kind") == "symbolic_expression":
            print(f"  score = {method['expression_text']}")
            print(f"  {method['provenance']} · mode {method['mode']} · {method['fitter_version']} · "
                  f"{method['expression_ref']} · splits {method['split']['counts']} (seed {method['split']['seed']})")
            for item in method["coefficients"]:
                print(f"    {item['coefficient']:+9.4f}  {item['term']:<34} {item['direction']:<15} {item['grounding']}")
            adoption = method["metrics"]["adoption"]
            print(f"  holdout {adoption['metric']}: expression {adoption['expression']:+.3f} vs baseline "
                  f"{adoption['baseline']:+.3f} → margin {adoption['margin']:+.3f} "
                  f"(needed {adoption['min_improvement']:+.3f}) over {adoption['compared_n']} candidates")
        record = sr_stage.record_of(core, snap["run_id"])
        if record is None:
            print("  no symbolic-regression attempt was recorded for this run")
            return
        print(f"  attempt: sr.mode {record['mode_setting']} · rank.method {record['rank_method']} · "
              f"adopted {record['adopted']}" + (f" · {record['not_installed']}" if record.get("not_installed") else "")
              + (f" · {record['not_attempted']}" if record.get("not_attempted") else ""))
        for attempt in record["attempts"]:
            print(f"  {attempt['mode']}{' ' + attempt['target_rule_ref'] if attempt.get('target_rule_ref') else ''}: "
                  f"coefficients {attempt.get('route', '-')} · {len(attempt.get('generations', []))} generation(s) · "
                  f"stopped {attempt['stopped']}")
            for feature in attempt.get("features_refused") or []:
                print(f"    refused feature {feature['name']}: {feature['reason']} ({feature['detail']})")
            for generation in attempt.get("generations") or []:
                for expression in generation["expressions"]:
                    metric = expression["metric"]
                    print(f"    gen {generation['generation']}  {metric['metric']} "
                          f"{metric['value'] if metric['value'] is None else round(metric['value'], 4)}  "
                          f"selection {expression['selection_score']}  {expression['text']}")
                for rejected in generation["rejected"]:
                    print(f"    gen {generation['generation']}  rejected: {rejected['reason']} — {rejected['detail'][:90]}")
            if attempt.get("adoption"):
                print(f"    holdout: {attempt['adoption']['reason']} (margin {attempt['adoption']['margin']})")


def _bound_settings(core: Core, run_id: str) -> dict[str, Any] | None:
    created = core.journal.replay(run_id, 1, 1)
    if not created or created[0].event_type != "run.created":
        return None
    return core.artifacts.payload(created[0].payload["binding_artifact_id"]).get("settings")


def cmd_config(args) -> None:
    settings = _settings(args)
    if args.action == "validate":
        print(f"valid  preset {settings.preset}  profile {settings.profile or '-'}  hash {settings.hash()[:12]}  "
              f"source {_config_file(args) or 'defaults only'}")
    elif args.action == "save":
        if not args.name:
            sys.exit("config save needs a profile NAME")
        target = config_mod.PROFILE_DIR / f"{args.name}.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        lines, section = [f"# saved by `mas config save` (preset {settings.preset})"], None
        for key, value in settings.non_default().items():
            head, leaf = key.rsplit(".", 1)
            if head != section:
                lines.append(f"\n[{head}]")
                section = head
            lines.append(f"{leaf} = {json.dumps(value)}")
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"saved {len(settings.non_default())} non-default settings to {target}")
    elif args.action == "estimate":
        _print(config_mod.estimate(settings, dimensions=args.dimensions, candidates=args.candidates))
    else:
        if not args.explain:
            _print({"preset": settings.preset, "profile": settings.profile, "config_hash": settings.hash(),
                    "settings": settings.values, "providers": sorted(settings.providers), "roles": settings.roles})
            return
        print(f"preset {settings.preset}  profile {settings.profile or '-'}  hash {settings.hash()[:12]}")
        for row in settings.layer_record()["settings"]:
            unit = f" {row['unit']}" if row["unit"] else ""
            print(f"  {row['key']:<36} {json.dumps(row['value']) + unit:<28} [{row['layer']}]  {row['doc']}")


UPLOAD_TEMPLATE = """# Documents you supply. A file is read only when its entry declares a licence and that a
# language model may read it. Formats: PDF (needs pdftotext), .txt/.md, .html, JATS/BITS .xml.
#
# [[document]]
# file = "pk-handbook-ch3.pdf"
# title = "Oral absorption of kinase inhibitors"
# year = 2021
# authors = "A. Author"
# license = "licensed copy for internal research"
# llm_ingestion_permitted = true
"""


def cmd_sources(args) -> None:
    from mas.adapters.literature import registry
    from mas.adapters.literature.bookshelf import BookshelfLibrary
    from mas.adapters.literature.uploads import MANIFEST, UploadLibrary
    settings = _settings(args)
    library = BookshelfLibrary(_cache_dir(args))
    uploads = UploadLibrary(_upload_dir(args))
    if args.action == "list":
        active = set(settings["search.sources"])
        synced = library.synced()
        for source in registry.SOURCES.values():
            if source.llm_ingestion in ("refused", "unknown"):
                state = "refused"
            elif source.source_id == "bookshelf":
                state = f"{len(synced)} book(s) synced" if synced else "needs a synced book"
            elif source.source_id == "uploads":
                readable = len(uploads.check()["readable"])
                state = f"{readable} readable document(s)" if readable else "no readable documents"
            else:
                state = "ready"
            print(f"{'*' if source.source_id in active else ' '} {source.source_id:<10} {state:<26} {source.title}")
            print(f"    licence: {source.license}; model reading: {source.llm_ingestion.replace('_', ' ')}")
            if source.note:
                print(f"    {source.note}")
        print("\n* = in search.sources")
    elif args.action == "check":
        for accession, book in sorted(library.synced().items()):
            print(f"bookshelf {accession}  {book['title']}  {book['chapters']} chapters  updated {book['updated']}  {book['license']}")
        report = uploads.check()
        print(f"uploads at {uploads.root}:")
        for key in ("readable", "refused", "missing"):
            for item in report[key]:
                print(f"  {key:<9} {item}")
    elif args.action == "template":
        target = uploads.root / MANIFEST
        if target.exists():
            sys.exit(f"{target} already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(UPLOAD_TEMPLATE, encoding="utf-8")
        print(f"wrote {target}")
    else:
        if args.source != "bookshelf" or not args.book:
            sys.exit("usage: mas sources sync bookshelf --book NBK...")
        open_access = library.file_list(refresh=True)
        for accession in args.book:
            if accession not in open_access:
                sys.exit(f"{accession} is not in the NLM LitArch open-access subset; it cannot be read automatically")
            print(f"syncing {accession} {open_access[accession]['title']} (streams the whole book once; keeps chapter XML)",
                  flush=True)
            manifest = library.sync(accession, progress=lambda m: print(f"  {m}", flush=True))
            print(f"  {manifest['chapters']} chapters, licence {manifest['license']}")


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
    parser.add_argument("--config", help="settings file (default ./mas.toml, else STORE/mas.toml)")
    parser.add_argument("--preset", choices=sorted(config_mod.PRESETS))
    parser.add_argument("--profile", help="settings profile from ~/.config/mas/profiles/NAME.toml")
    parser.add_argument("--set", action="append", metavar="KEY=VALUE", help="override one setting (repeatable)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)

    t = sub.add_parser("task")
    t.add_argument("action", choices=("new", "list", "show", "shortlist"))
    t.add_argument("task", nargs="?")
    t.add_argument("--from", dest="file")
    t.add_argument("--top", type=int, default=20, help="shortlist: top K positions (ties at the boundary included)")
    t.set_defaults(func=cmd_task)

    c = sub.add_parser("criteria")
    c.add_argument("action", choices=("propose", "derive", "mandated", "pool"))
    c.add_argument("task")
    c.add_argument("--continues", metavar="RUN", help="derive: continue the pool from this earlier derivation round")
    c.add_argument("--single-pass", action="store_true", help="derive: one propose/critique/revise pass, no pool")
    c.add_argument("--all", action="store_true", help="pool: include merged, withdrawn and filtered items")
    c.add_argument("--from", dest="file")
    c.add_argument("--dimension", action="append")
    c.add_argument("--cutoff", help="evidence cutoff date YYYY-MM-DD")
    c.add_argument("--max-documents", type=int, help="documents read per dimension (default: read.max_papers_full_read)")
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
    u.add_argument("--seed", type=int)
    u.add_argument("--limit", type=int)
    u.add_argument("--tool-calls", type=int)
    u.add_argument("--llm-turns", type=int)
    u.add_argument("--cutoff")
    u.add_argument("--workers", type=int, help="concurrent literature cells (default: assess.workers)")
    u.add_argument("--allow-config-drift", action="store_true", help="resume although the settings changed")
    u.set_defaults(func=cmd_run)

    b = sub.add_parser("board")
    b.add_argument("action", choices=("show",))
    b.add_argument("task")
    b.add_argument("--top", type=int, help="rows to show (default: rank.top_n)")
    b.add_argument("--all", action="store_true")
    b.set_defaults(func=cmd_board)

    d = sub.add_parser("candidate")
    d.add_argument("action", choices=("show",))
    d.add_argument("task")
    d.add_argument("candidate")
    d.set_defaults(func=cmd_candidate)

    s = sub.add_parser("score")
    s.add_argument("action", choices=("show",))
    s.add_argument("task")
    s.set_defaults(func=cmd_score)

    g = sub.add_parser("config")
    g.add_argument("action", choices=("show", "validate", "save", "estimate"))
    g.add_argument("name", nargs="?")
    g.add_argument("--explain", action="store_true", help="show the layer each value came from")
    g.add_argument("--dimensions", type=int, default=1)
    g.add_argument("--candidates", type=int, default=0)
    g.set_defaults(func=cmd_config)

    so = sub.add_parser("sources")
    so.add_argument("action", choices=("list", "check", "sync", "template"))
    so.add_argument("source", nargs="?")
    so.add_argument("--book", action="append", help="NCBI Bookshelf accession to sync (repeatable)")
    so.set_defaults(func=cmd_sources)

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
