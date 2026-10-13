"""Layered run settings (design §14.1): one resolved configuration per run, with provenance.

Settings are flat dotted keys with a declared type and range, so that layering,
validation and provenance need no schema classes. Layers, lowest precedence first:

    code defaults -> preset -> ./mas.toml -> profile -> MAS__SECTION__KEY env -> --set k=v

The command line deliberately outranks the environment: a run-time override that an
environment variable could silently win over is a known source of unreproducible runs.

`providers` and `roles` stay free-form tables (they are model bindings, not scalars)
and are merged table-by-table in the same layer order.

The resolved values are hashed; `layer_record()` says which layer produced each value,
so a run can be replayed and a surprising number can be traced to its source.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .canonical import sha256_hex

LAYERS = ("default", "preset", "project", "profile", "environment", "override")

ENV_PREFIX = "MAS__"
PROJECT_FILE = "mas.toml"
PROFILE_DIR = Path.home() / ".config" / "mas" / "profiles"


class ConfigError(ValueError):
    """A setting that is unknown, mistyped, out of range, or inconsistent with another."""


@dataclass(frozen=True)
class Setting:
    default: Any
    doc: str
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[Any, ...] | None = None
    unit: str = ""
    const_id: str | None = None   # registered as a constant when it can affect a published verdict
    item_type: type | None = None  # for list settings


def _s(default, doc, **kw) -> Setting:
    return Setting(default, doc, **kw)


# --- the settings -------------------------------------------------------------------

SETTINGS: dict[str, Setting] = {
    # literature breadth and depth
    "search.sources": _s(["europepmc", "pubmed"], "evidence sources to query, in order of preference", item_type=str),
    "search.breadth": _s(4, "queries generated per dimension per round", minimum=1, maximum=20, unit="queries",
                         const_id="const_search_breadth"),
    "search.depth": _s(2, "follow-up search rounds after the first", minimum=1, maximum=6, unit="rounds",
                       const_id="const_search_depth"),
    "search.breadth_decay": _s(0.5, "factor applied to breadth at each follow-up round", minimum=0.1, maximum=1.0),
    "search.results_per_query": _s(20, "hits requested per query", minimum=1, maximum=200, unit="records"),
    "search.max_records_screened": _s(300, "upper bound on records screened per dimension", minimum=10, maximum=5000,
                                      unit="records", const_id="const_search_max_records"),
    "search.saturation_stop": _s(0.10, "stop a dimension when the share of newly relevant records falls below this",
                                 minimum=0.0, maximum=1.0, unit="fraction", const_id="const_search_saturation_stop"),
    "search.date_from": _s("", "earliest publication date to admit (YYYY-MM-DD, empty for no bound)"),
    "search.date_to": _s("", "evidence cutoff date (YYYY-MM-DD, empty for no bound)"),
    # reading
    "read.max_papers_full_read": _s(40, "documents read in full per dimension", minimum=1, maximum=500,
                                    unit="documents", const_id="const_read_max_documents"),
    "read.evidence_k": _s(10, "passages kept per document for extraction", minimum=1, maximum=50, unit="passages"),
    "read.max_claims_per_paper": _s(8, "claims extracted per document per attribute", minimum=1, maximum=50,
                                    unit="claims"),
    "read.max_content_chars": _s(60000, "characters of a document offered to the reader", minimum=1000,
                                 maximum=500000, unit="characters"),
    "read.prefer_full_text": _s(True, "read full text where available, else the abstract"),
    "read.require_verbatim_span": _s(True, "refuse a claim whose quote is not found in the source"),
    # criteria pool workflow
    "criteria.inner_iterations": _s(3, "filter/distill/merge/refine passes within one round", minimum=1, maximum=10,
                                    unit="iterations", const_id="const_criteria_inner_iterations"),
    "criteria.stages": _s(["filter", "distill", "merge", "refine"], "pool stages run each iteration, in order",
                          item_type=str),
    "criteria.n_critics": _s(1, "independent critics per proposal", minimum=1, maximum=5, unit="critics"),
    "criteria.stall_rounds": _s(2, "unchanged iterations that end a round early", minimum=1, maximum=5,
                                unit="iterations", const_id="const_criteria_stall_rounds"),
    "criteria.on_stall": _s("finalize", "what to do when the pool stops changing",
                            choices=("finalize", "pivot", "escalate")),
    "criteria.pool_target_size": _s(0, "target number of surviving criteria; 0 leaves the count to the evidence",
                                    minimum=0, maximum=100, unit="criteria", const_id="const_criteria_pool_target"),
    # sweep
    "assess.max_candidates": _s(0, "candidates assessed; 0 means the whole universe", minimum=0, maximum=1000000),
    "assess.workers": _s(1, "concurrent literature cells", minimum=1, maximum=32),
    # ranking
    "rank.method": _s("weighted_preference", "how the leaderboard score is produced",
                      choices=("weighted_preference", "symbolic_expression")),
    "rank.coverage_floor": _s(0.5, "minimum share of scoring inputs a candidate needs to be ranked",
                              minimum=0.0, maximum=1.0, unit="fraction", const_id="const_ranking_coverage_floor"),
    "rank.top_n": _s(25, "rows shown by default on the leaderboard", minimum=1, maximum=1000),
    "sr.mode": _s("off", "what the symbolic regression models",
                  choices=("off", "potency", "leaderboard_score", "both")),
    "sr.generations": _s(4, "proposal/diagnostic rounds offered to the model", minimum=1, maximum=12,
                         unit="generations", const_id="const_sr_generations"),
    "sr.max_terms": _s(4, "terms allowed in an expression", minimum=1, maximum=8, unit="terms",
                       const_id="const_sr_max_terms"),
    "sr.min_improvement": _s(0.02, "holdout gain over the weighted-preference baseline required for adoption",
                             minimum=0.0, maximum=1.0, const_id="const_sr_min_improvement"),
    "sr.min_training_rows": _s(12, "usable rows below which coefficients come from cited priors instead of a fit",
                               minimum=2, maximum=10000, unit="rows", const_id="const_sr_min_training_rows"),
    "sr.select_share": _s(0.25, "share of candidates held back for comparing generations", minimum=0.05,
                          maximum=0.45, unit="fraction", const_id="const_sr_select_share"),
    "sr.holdout_share": _s(0.25, "share of candidates touched once, for the adoption decision", minimum=0.05,
                           maximum=0.45, unit="fraction", const_id="const_sr_holdout_share"),
    "sr.ridge": _s(0.1, "shrinkage toward the model's declared prior", minimum=0.0, maximum=100.0,
                   const_id="const_sr_ridge"),
    "sr.complexity_penalty": _s(0.01, "score deducted per term and per depth level", minimum=0.0, maximum=1.0,
                                const_id="const_sr_complexity_penalty"),
    "sr.max_condition": _s(1e8, "design-matrix condition number above which a fit is refused", minimum=1.0,
                           maximum=1e15, const_id="const_sr_max_condition"),
    "sr.use_rdkit": _s(False, "add locally computed RDKit descriptors (optional dependency)"),
    "sr.use_pysr": _s(False, "search further with PySR, seeded by the model's expressions (optional dependency)"),
    # budget
    "budget.usd_max": _s(20.0, "provider spend allowed for one run", minimum=0.0, maximum=100000.0, unit="USD",
                         const_id="const_budget_usd_max"),
    "budget.warn_at": _s(0.8, "share of the cap at which the run warns", minimum=0.1, maximum=1.0, unit="fraction"),
    "budget.on_exhaust": _s("warn_continue", "what happens when the cap is reached",
                            choices=("warn_continue", "finalize_partial", "ask", "abort")),
    "budget.llm_turns": _s(0, "model calls allowed; 0 means no limit", minimum=0, maximum=1000000),
    "budget.tool_calls": _s(0, "tool calls allowed; 0 means no limit", minimum=0, maximum=1000000),
    "budget.wall_clock_s": _s(0, "seconds a run may take; 0 means no limit", minimum=0, maximum=1000000, unit="s"),
    # concurrency
    "concurrency.max_parallel_agents": _s(4, "model calls in flight", minimum=1, maximum=64),
    "concurrency.per_host_min_interval_s": _s(0.4, "minimum gap between requests to one host", minimum=0.0,
                                              maximum=60.0, unit="s"),
    # interaction
    "interaction.mode": _s("checkpoint", "how often the run stops for a person",
                           choices=("autonomous", "checkpoint", "interactive")),
    "interaction.checkpoints": _s(["criteria_final", "pre_rank"], "points at which a checkpoint run pauses",
                                  item_type=str),
    "interaction.escalate_on": _s(["stall", "budget_warn"], "conditions that raise a review item", item_type=str),
    # run
    "run.seed": _s(0, "sweep seed; also seeds the symbolic-regression splits", minimum=0, maximum=2**31 - 1),
    "run.save_prompts": _s(True, "keep full prompts and replies in trace artifacts (expert/auditor visibility)"),
}

CHECKPOINTS = ("search_plan", "criteria_final", "pre_rank", "report")

PRESETS: dict[str, dict[str, Any]] = {
    "quick": {
        "search.breadth": 2, "search.depth": 1, "search.max_records_screened": 60,
        "read.max_papers_full_read": 10, "read.evidence_k": 5,
        "criteria.inner_iterations": 1, "criteria.n_critics": 1,
        "sr.generations": 2, "budget.usd_max": 2.0, "interaction.mode": "autonomous",
        "interaction.checkpoints": [],
    },
    "standard": {},
    "deep": {
        "search.breadth": 8, "search.depth": 4, "search.max_records_screened": 1500,
        "read.max_papers_full_read": 200, "read.evidence_k": 15,
        "criteria.inner_iterations": 6, "criteria.n_critics": 3,
        "sr.generations": 8, "budget.usd_max": 100.0,
    },
}


# --- resolution ----------------------------------------------------------------------

def _flatten(table: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten a TOML table into dotted keys, stopping at list and scalar values."""
    flat: dict[str, Any] = {}
    for key, value in table.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, f"{dotted}."))
        else:
            flat[dotted] = value
    return flat


def _coerce(key: str, raw: Any) -> Any:
    """Coerce a string from the environment or the command line to the setting's type."""
    setting = SETTINGS[key]
    want = type(setting.default)
    if not isinstance(raw, str) or want is str:
        return raw
    text = raw.strip()
    if want is bool:
        if text.lower() in ("true", "yes", "1", "on"):
            return True
        if text.lower() in ("false", "no", "0", "off"):
            return False
        raise ConfigError(f"{key}: {raw!r} is not a true/false value")
    if want is list:
        return [part.strip() for part in text.split(",") if part.strip()]
    try:
        return want(text) if want is not float else float(text)
    except ValueError:
        raise ConfigError(f"{key}: {raw!r} is not a {want.__name__}") from None


def _check(key: str, value: Any) -> Any:
    setting = SETTINGS[key]
    want = type(setting.default)
    if want is float and isinstance(value, int) and not isinstance(value, bool):
        value = float(value)
    if want is bool and not isinstance(value, bool):
        raise ConfigError(f"{key}: expected true/false, got {value!r}")
    if want is not bool and isinstance(value, bool):
        raise ConfigError(f"{key}: expected {want.__name__}, got a boolean")
    if not isinstance(value, want):
        raise ConfigError(f"{key}: expected {want.__name__}, got {type(value).__name__}")
    if setting.item_type is not None:
        bad = [v for v in value if not isinstance(v, setting.item_type)]
        if bad:
            raise ConfigError(f"{key}: list entries must be {setting.item_type.__name__}; got {bad!r}")
    if setting.choices is not None and value not in setting.choices:
        raise ConfigError(f"{key}: {value!r} is not one of {list(setting.choices)}")
    if setting.minimum is not None and value < setting.minimum:
        raise ConfigError(f"{key}: {value} is below the minimum {setting.minimum}")
    if setting.maximum is not None and value > setting.maximum:
        raise ConfigError(f"{key}: {value} is above the maximum {setting.maximum}")
    return value


def _env_overrides(environ: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, raw in environ.items():
        if not name.startswith(ENV_PREFIX):
            continue
        key = name[len(ENV_PREFIX):].replace("__", ".").lower()
        if key not in SETTINGS:
            raise ConfigError(f"{name}: no setting named {key!r}")
        out[key] = raw
    return out


def parse_overrides(pairs: list[str] | tuple[str, ...]) -> dict[str, Any]:
    """Parse `--set key=value` arguments."""
    out: dict[str, Any] = {}
    for pair in pairs or ():
        if "=" not in pair:
            raise ConfigError(f"--set expects key=value, got {pair!r}")
        key, raw = pair.split("=", 1)
        key = key.strip()
        if key not in SETTINGS:
            raise ConfigError(f"no setting named {key!r}")
        out[key] = raw
    return out


@dataclass
class Config:
    values: dict[str, Any]
    sources: dict[str, str]
    providers: dict[str, Any] = field(default_factory=dict)
    roles: dict[str, str] = field(default_factory=dict)
    preset: str = "standard"
    profile: str | None = None

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def section(self, name: str) -> dict[str, Any]:
        prefix = f"{name}."
        return {k[len(prefix):]: v for k, v in self.values.items() if k.startswith(prefix)}

    def hash(self) -> str:
        return sha256_hex({"values": self.values, "providers": self.providers, "roles": self.roles})

    def layer_record(self) -> dict[str, Any]:
        """Provenance artifact: every value with the layer that produced it."""
        return {"preset": self.preset, "profile": self.profile, "config_hash": self.hash(),
                "settings": [{"key": k, "value": self.values[k], "layer": self.sources[k],
                              "unit": SETTINGS[k].unit, "doc": SETTINGS[k].doc} for k in sorted(self.values)]}

    def registered_constants(self) -> list[tuple[str, Any, str]]:
        """Settings that can affect a published verdict, as (const_id, value, unit)."""
        return [(SETTINGS[k].const_id, self.values[k], SETTINGS[k].unit)
                for k in sorted(self.values) if SETTINGS[k].const_id]

    def non_default(self) -> dict[str, Any]:
        return {k: v for k, v in sorted(self.values.items()) if self.sources[k] != "default"}


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{path}: {error}") from None


def resolve(*, preset: str = "standard", project_file: str | os.PathLike | None = PROJECT_FILE,
            profile: str | None = None, profile_dir: str | os.PathLike = PROFILE_DIR,
            overrides: dict[str, Any] | None = None, environ: dict[str, str] | None = None,
            extra_tables: dict[str, dict[str, Any]] | None = None) -> Config:
    """Resolve the layers into one validated configuration."""
    if preset not in PRESETS:
        raise ConfigError(f"unknown preset {preset!r}; known presets are {sorted(PRESETS)}")
    values = {key: setting.default for key, setting in SETTINGS.items()}
    sources = {key: "default" for key in SETTINGS}
    providers: dict[str, Any] = {}
    roles: dict[str, str] = {}

    def apply(flat: dict[str, Any], layer: str) -> None:
        for key, raw in flat.items():
            if key not in SETTINGS:
                raise ConfigError(f"{layer}: no setting named {key!r}")
            values[key] = _check(key, _coerce(key, raw))
            sources[key] = layer

    def apply_tables(table: dict[str, Any], layer: str) -> None:
        for name, spec in (table.get("providers") or {}).items():
            providers[name] = dict(spec)
        roles.update(table.get("roles") or {})

    apply({k: v for k, v in PRESETS[preset].items()}, "preset")
    for layer, path in (("project", Path(project_file) if project_file else None),
                        ("profile", Path(profile_dir) / f"{profile}.toml" if profile else None)):
        if path is None:
            continue
        if not path.exists():
            if layer == "profile":
                raise ConfigError(f"no profile at {path}")
            continue
        table = _load_toml(path)
        apply_tables(table, layer)
        apply(_flatten({k: v for k, v in table.items() if k not in ("providers", "roles")}), layer)
    for layer, table in (extra_tables or {}).items():
        apply_tables(table, layer)
        apply(_flatten({k: v for k, v in table.items() if k not in ("providers", "roles")}), layer)
    apply(_env_overrides(environ if environ is not None else dict(os.environ)), "environment")
    apply(dict(overrides or {}), "override")

    config = Config(values, sources, providers, roles, preset=preset, profile=profile)
    validate(config)
    return config


def validate(config: Config) -> None:
    """Checks that span more than one setting."""
    v = config.values
    if v["sr.select_share"] + v["sr.holdout_share"] > 0.7:
        raise ConfigError("sr.select_share + sr.holdout_share must leave at least 30% of candidates for fitting")
    if v["rank.method"] == "symbolic_expression" and v["sr.mode"] == "off":
        raise ConfigError("rank.method = symbolic_expression needs sr.mode set to potency, leaderboard_score or both")
    unknown = [c for c in v["interaction.checkpoints"] if c not in CHECKPOINTS]
    if unknown:
        raise ConfigError(f"interaction.checkpoints: unknown {unknown}; known checkpoints are {list(CHECKPOINTS)}")
    if v["interaction.mode"] == "autonomous" and v["interaction.checkpoints"]:
        raise ConfigError("interaction.mode = autonomous cannot list checkpoints; clear interaction.checkpoints "
                          "or choose the checkpoint mode")
    if v["concurrency.max_parallel_agents"] < v["assess.workers"]:
        raise ConfigError("assess.workers cannot exceed concurrency.max_parallel_agents")
    if config.roles:
        missing = sorted(set(config.roles.values()) - set(config.providers))
        if missing:
            raise ConfigError(f"roles bound to providers that are not configured: {missing}")


# --- recording and estimating --------------------------------------------------------

def register_constants(core, config: Config, *, by: dict[str, Any], stream_id: str | None = None) -> list[str]:
    """Register the verdict-affecting settings as constants (design §8.4) before a run uses them."""
    from . import constants
    registered = []
    for const_id, value, unit in config.registered_constants():
        kwargs = {"unit": unit or "count", "scope": "core_policy",
                  "cutoff_basis": "operator_configuration", "set_by": by}
        if stream_id is not None:
            kwargs["stream_id"] = stream_id
        constants.register(core, const_id, value, **kwargs)
        registered.append(const_id)
    return registered


def estimate(config: Config, *, dimensions: int = 1, candidates: int = 0) -> dict[str, Any]:
    """Volume and cost estimate for `--dry-run`: no network, no model calls."""
    v = config.values
    breadth, queries = float(v["search.breadth"]), 0.0
    for _ in range(v["search.depth"]):
        queries += max(1.0, breadth)
        breadth *= v["search.breadth_decay"]
    queries *= dimensions
    records = min(queries * v["search.results_per_query"], v["search.max_records_screened"] * dimensions)
    documents = min(records, v["read.max_papers_full_read"] * dimensions)
    # one query-planning call and one extraction call per document, per inner iteration pass
    reads = documents * v["criteria.inner_iterations"]
    pool_calls = dimensions * len(v["criteria.stages"]) * v["criteria.inner_iterations"] * max(1, v["criteria.n_critics"])
    sr_calls = 0 if v["sr.mode"] == "off" else v["sr.generations"] * (2 if v["sr.mode"] == "both" else 1)
    llm_calls = int(queries + reads + pool_calls + sr_calls)
    sweep = candidates or v["assess.max_candidates"]
    return {"search_queries": int(queries), "records_screened": int(records), "documents_read": int(documents),
            "llm_calls": llm_calls, "pool_stage_calls": int(pool_calls), "symbolic_regression_calls": int(sr_calls),
            "candidates_assessed": int(sweep),
            "note": "model calls are an upper bound: caching, saturation stop and stall detection all reduce them",
            "budget_usd_max": v["budget.usd_max"], "on_exhaust": v["budget.on_exhaust"]}
