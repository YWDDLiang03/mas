"""Symbolic-regression scoring: the term grammar, the fit, and the deterministic gates (design §5.7).

The model contributes the structure — which features belong in a score, what transformation
each deserves, the required direction of every term, a prior magnitude, and the next
generation after reading the diagnostics. Everything in this module is the part that must be
checkable without trusting any of that, so it is pure: no I/O, no journal, like `assessor.py`.

* A term is parsed from structured JSON, never evaluated from text, and refused unless it is
  one of `FORMS` over offered feature names at depth 1 (a form applies to raw features and
  cannot nest), with a numeric constant exactly where its form takes one.
* The fit is ordinary least squares on standardised columns, shrunk toward the model's declared
  prior rather than toward zero, solved by Gaussian elimination with partial pivoting. A
  constant or all-missing column, too few complete rows, and an ill-conditioned design are
  refused with a reason instead of returning a number nobody could defend.
* A fitted coefficient whose sign contradicts its declared direction rejects the expression
  (`sign_violations`): the direction is the model's claim, and the data either agrees or it does not.
* `split_candidates` cuts the candidates three ways by hash, so the split does not depend on
  iteration order, and every reference outcome is excluded from all three.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Iterable, Sequence

from .canonical import sha256_hex

FITTER_VERSION = "sr-fit-1"
GRAMMAR_VERSION = "sr-grammar-1"

# The grammar: form -> how many features it takes. Depth is 1 by construction.
FORMS: dict[str, int] = {"identity": 1, "log1p": 1, "inverse": 1, "square": 1, "product": 2, "hinge": 1, "zscore": 1}
CONSTANT_FORMS = ("hinge",)
# A term's required direction is an attribute direction (criteria.DIRECTIONS); only these three
# can constrain the sign of a coefficient, so a term declaring any other direction is refused.
TERM_DIRECTIONS = ("higher_better", "lower_better", "non_directional")
MODES = ("potency", "leaderboard_score")
PROVENANCES = ("fitted", "expert_prior")
GROUNDINGS = ("mechanistic", "associational")
SPLIT_NAMES = ("train", "select", "holdout", "excluded")
# Selection metric per mode: a predicted value is compared on its own scale, a score on its order.
SELECTION_METRICS = {"potency": "validation_r2", "leaderboard_score": "kendall_tau"}
ADOPTION_METRIC = "kendall_tau"   # two scorers on different scales are only comparable on order

_EPSILON = 1e-12


class GrammarError(ValueError):
    """A proposed term or expression outside the grammar; refused with a reason, never coerced."""

    def __init__(self, reason: str, message: str):
        super().__init__(f"{reason}: {message}")
        self.reason = reason


class FitRefused(ValueError):
    """A design the fit will not stand behind (constant column, too few rows, ill-conditioned)."""

    def __init__(self, reason: str, message: str):
        super().__init__(f"{reason}: {message}")
        self.reason = reason


# --- terms ----------------------------------------------------------------------------------

@dataclass(frozen=True)
class Term:
    form: str
    features: tuple[str, ...]
    direction: str = "non_directional"
    constant: float | None = None
    prior_coefficient: float | None = None
    claim_refs: tuple[str, ...] = ()
    grounding: str = "associational"
    justification: str = ""

    def __post_init__(self):
        """The grammar, checked on construction as well as on parsing: a stored record is reconstructed
        through here too, so no path reaches a fit with a term outside the grammar."""
        if self.form not in FORMS:
            raise GrammarError("unknown_form", f"{self.form!r} is not one of {sorted(FORMS)}")
        if len(self.features) != FORMS[self.form]:
            raise GrammarError("arity", f"{self.form} takes {FORMS[self.form]} feature name(s), got {len(self.features)}")
        if self.direction not in TERM_DIRECTIONS:
            raise GrammarError("direction", f"{self.direction!r} is not one of {list(TERM_DIRECTIONS)}")
        if self.grounding not in GROUNDINGS:
            raise GrammarError("grounding", f"{self.grounding!r} is not one of {list(GROUNDINGS)}")
        if (self.constant is None) == (self.form in CONSTANT_FORMS):
            needs = "needs a numeric constant" if self.form in CONSTANT_FORMS else "takes no constant"
            raise GrammarError("constant", f"{self.form} {needs}")

    @property
    def text(self) -> str:
        """Canonical text of the term; expressions are ordered and tie-broken on it."""
        first = self.features[0]
        if self.form == "identity":
            return first
        if self.form == "product":
            return f"{first}*{self.features[1]}"
        if self.form == "log1p":
            return f"log1p({first})"
        if self.form == "inverse":
            return f"1/(1+{first})"
        if self.form == "square":
            return f"{first}**2"
        if self.form == "hinge":
            return f"hinge({first}, {self.constant:g})"
        return f"z({first})"

    @property
    def depth(self) -> int:
        return 0 if self.form == "identity" else 1

    @property
    def column_key(self) -> tuple:
        # After column standardisation z(x) and x are the same column, so they count as one.
        form = "identity" if self.form in ("identity", "zscore") else self.form
        return (form, self.features, self.constant)

    def raw_value(self, values: dict[str, Any]) -> float | None:
        """The term before standardisation, or None when a feature is missing or the form is undefined there."""
        args = []
        for name in self.features:
            value = values.get(name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return None
            args.append(float(value))
        first = args[0]
        if self.form in ("identity", "zscore"):
            return first
        if self.form == "log1p":
            return math.log1p(first) if first > -1.0 else None
        if self.form == "inverse":
            return 1.0 / (1.0 + first) if abs(1.0 + first) > _EPSILON else None
        if self.form == "square":
            return first * first
        if self.form == "product":
            return first * args[1]
        return max(0.0, first - float(self.constant))

    def record(self) -> dict[str, Any]:
        return {"form": self.form, "features": list(self.features), "direction": self.direction,
                "constant": self.constant, "prior_coefficient": self.prior_coefficient,
                "claim_refs": list(self.claim_refs), "grounding": self.grounding,
                "justification": self.justification, "text": self.text}


def term_from_record(record: dict[str, Any]) -> Term:
    return Term(form=record["form"], features=tuple(record["features"]), direction=record.get("direction", "non_directional"),
                constant=record.get("constant"), prior_coefficient=record.get("prior_coefficient"),
                claim_refs=tuple(record.get("claim_refs") or []), grounding=record.get("grounding", "associational"),
                justification=record.get("justification", ""))


def parse_term(spec: Any, features: Iterable[str]) -> Term:
    """One term from the model's structured proposal; nothing here parses or evaluates an expression string."""
    offered = set(features)
    if not isinstance(spec, dict):
        raise GrammarError("not_an_object", f"a term is an object, got {type(spec).__name__}")
    form = spec.get("form")
    if form not in FORMS:
        raise GrammarError("unknown_form", f"{form!r} is not one of {sorted(FORMS)}")
    names = [spec["features"]] if isinstance(spec.get("features"), str) else spec.get("features")
    if not isinstance(names, list) or len(names) != FORMS[form] or not all(isinstance(n, str) for n in names):
        raise GrammarError("arity", f"{form} takes {FORMS[form]} feature name(s), got {spec.get('features')!r}")
    unknown = [n for n in names if n not in offered]
    if unknown:
        raise GrammarError("unknown_feature", f"{unknown} was not offered as a feature")
    if form == "product" and names[0] == names[1]:
        raise GrammarError("arity", "x*y needs two different features; square one instead")
    direction = spec.get("direction", "non_directional")
    if direction not in TERM_DIRECTIONS:
        raise GrammarError("direction", f"{direction!r} is not one of {list(TERM_DIRECTIONS)}")
    constant = spec.get("constant")
    if form in CONSTANT_FORMS:
        if not isinstance(constant, (int, float)) or isinstance(constant, bool):
            raise GrammarError("constant", f"{form} needs a numeric constant")
        constant = float(constant)
    elif constant is not None:
        raise GrammarError("constant", f"{form} takes no constant")
    prior = spec.get("prior_coefficient")
    if prior is not None and (not isinstance(prior, (int, float)) or isinstance(prior, bool)):
        raise GrammarError("prior", f"prior_coefficient must be a number, got {prior!r}")
    return Term(form=form, features=tuple(names), direction=direction, constant=constant,
                prior_coefficient=None if prior is None else float(prior),
                claim_refs=tuple(str(c) for c in (spec.get("supporting_claim_ids") or [])),
                justification=str(spec.get("justification") or "")[:500])


def parse_terms(specs: Any, features: Iterable[str], *, max_terms: int) -> list[Term]:
    """Every term of one proposed expression, with the expression-level grammar checks."""
    if not isinstance(specs, list) or not specs:
        raise GrammarError("empty", "an expression needs at least one term")
    if len(specs) > max_terms:
        raise GrammarError("too_many_terms", f"{len(specs)} terms is more than the {max_terms} allowed")
    terms = [parse_term(spec, features) for spec in specs]
    seen: dict[tuple, str] = {}
    for term in terms:
        if term.column_key in seen:
            raise GrammarError("duplicate_term", f"{term.text} is the same column as {seen[term.column_key]}")
        seen[term.column_key] = term.text
    return terms


# --- expressions ------------------------------------------------------------------------------

@dataclass(frozen=True)
class Expression:
    terms: tuple[Term, ...]
    coefficients: tuple[float, ...]       # on the standardised columns, so signs are comparable
    intercept: float
    centers: tuple[float, ...]
    scales: tuple[float, ...]
    provenance: str = "fitted"
    fitter_version: str = FITTER_VERSION
    grammar_version: str = GRAMMAR_VERSION

    def __post_init__(self):
        if self.provenance not in PROVENANCES:
            raise GrammarError("provenance", f"{self.provenance!r} is not one of {list(PROVENANCES)}")
        if not len(self.terms) == len(self.coefficients) == len(self.centers) == len(self.scales):
            raise GrammarError("shape", "an expression has one coefficient, centre and scale per term")

    @property
    def canonical_text(self) -> str:
        return " + ".join(term.text for term in self.terms)

    @property
    def text(self) -> str:
        parts = [f"{coefficient:.6g}*{term.text}" for term, coefficient in zip(self.terms, self.coefficients)]
        return " + ".join(parts + [f"{self.intercept:.6g}"])

    @property
    def feature_refs(self) -> list[str]:
        return sorted({name for term in self.terms for name in term.features})

    @property
    def depth(self) -> int:
        return max((term.depth for term in self.terms), default=0)

    def record(self) -> dict[str, Any]:
        return {"terms": [term.record() for term in self.terms], "coefficients": list(self.coefficients),
                "intercept": self.intercept, "centers": list(self.centers), "scales": list(self.scales),
                "provenance": self.provenance, "fitter_version": self.fitter_version,
                "grammar_version": self.grammar_version, "canonical_text": self.canonical_text, "text": self.text,
                "feature_refs": self.feature_refs, "n_terms": len(self.terms), "depth": self.depth}


def expression_from_record(record: dict[str, Any]) -> Expression:
    return Expression(terms=tuple(term_from_record(t) for t in record["terms"]),
                      coefficients=tuple(float(c) for c in record["coefficients"]), intercept=float(record["intercept"]),
                      centers=tuple(float(c) for c in record["centers"]), scales=tuple(float(s) for s in record["scales"]),
                      provenance=record.get("provenance", "fitted"),
                      fitter_version=record.get("fitter_version", FITTER_VERSION),
                      grammar_version=record.get("grammar_version", GRAMMAR_VERSION))


def as_expression(value: Any) -> Expression:
    """An `Expression`, its record, or an ordering method carrying one (a resumed run has only records)."""
    if isinstance(value, Expression):
        return value
    if isinstance(value, dict):
        if "terms" in value:
            return expression_from_record(value)
        if isinstance(value.get("expression"), dict):
            return expression_from_record(value["expression"])
    raise TypeError("not a scoring expression")


# --- the fit ------------------------------------------------------------------------------------

def solve(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> list[float]:
    """Gaussian elimination with partial pivoting; `FitRefused` rather than a number from a singular system."""
    size = len(vector)
    rows = [[float(value) for value in matrix[index]] + [float(vector[index])] for index in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(rows[row][column]))
        if abs(rows[pivot][column]) <= _EPSILON:
            raise FitRefused("singular", f"no usable pivot in column {column}")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        for row in range(column + 1, size):
            factor = rows[row][column] / rows[column][column]
            if factor:
                for index in range(column, size + 1):
                    rows[row][index] -= factor * rows[column][index]
    out = [0.0] * size
    for column in reversed(range(size)):
        total = rows[column][size] - sum(rows[column][index] * out[index] for index in range(column + 1, size))
        out[column] = total / rows[column][column]
    return out


def condition_estimate(matrix: Sequence[Sequence[float]]) -> float:
    """Pivot-ratio estimate of a Gram matrix's condition number: cheap, and conservative where it errs."""
    size = len(matrix)
    rows = [[float(value) for value in row] for row in matrix]
    pivots = []
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(rows[row][column]))
        rows[column], rows[pivot] = rows[pivot], rows[column]
        value = abs(rows[column][column])
        if value <= _EPSILON:
            return math.inf
        pivots.append(value)
        for row in range(column + 1, size):
            factor = rows[row][column] / rows[column][column]
            for index in range(column, size):
                rows[row][index] -= factor * rows[column][index]
    return max(pivots) / min(pivots)


Row = tuple[dict[str, Any], float]


def design(terms: Sequence[Term], rows: Sequence[Row]) -> tuple[list[list[float]], list[float], int]:
    """Complete-case design matrix: a row enters only when every term has a value there."""
    matrix, targets, dropped = [], [], 0
    for values, target in rows:
        if not isinstance(target, (int, float)) or isinstance(target, bool):
            dropped += 1
            continue
        columns = [term.raw_value(values) for term in terms]
        if any(column is None for column in columns):
            dropped += 1
            continue
        matrix.append([float(column) for column in columns])
        targets.append(float(target))
    return matrix, targets, dropped


def _standardise(matrix: list[list[float]], terms: Sequence[Term], *, refuse_constant: bool) -> tuple[list[float], list[float]]:
    centers, scales = [], []
    for column in range(len(terms)):
        values = [row[column] for row in matrix]
        center = sum(values) / len(values) if values else 0.0
        variance = sum((value - center) ** 2 for value in values) / len(values) if values else 0.0
        scale = math.sqrt(variance)
        if scale <= _EPSILON:
            if refuse_constant:
                raise FitRefused("constant_column", f"{terms[column].text} does not vary over the usable rows")
            center, scale = (center if values else 0.0), 1.0
        centers.append(center)
        scales.append(scale)
    return centers, scales


@dataclass(frozen=True)
class Fit:
    expression: Expression
    diagnostics: dict[str, Any]


def fit(terms: Sequence[Term], rows: Sequence[Row], *, ridge: float, max_condition: float,
        intercept_prior: float = 0.0, stability: bool = False) -> Fit:
    """Least squares on standardised columns, shrunk toward the model's declared prior.

    The normal equations are divided by the row count, so the standardised columns have unit
    variance and `ridge` is directly the weight given to the prior against the data. Shrinking
    toward the prior instead of toward zero is what makes a thin column fall back on the
    model's cited magnitude rather than on silence.
    """
    matrix, targets, dropped = design(terms, rows)
    if len(matrix) < len(terms) + 2:
        raise FitRefused("too_few_rows", f"{len(matrix)} complete rows for {len(terms)} term(s)")
    centers, scales = _standardise(matrix, terms, refuse_constant=True)
    size = len(terms)
    standardised = [[(row[column] - centers[column]) / scales[column] for column in range(size)] for row in matrix]
    count = len(standardised)
    gram = [[sum(row[a] * row[b] for row in standardised) / count for b in range(size)] for a in range(size)]
    condition = condition_estimate(gram)
    if condition > max_condition:
        raise FitRefused("ill_conditioned", f"condition estimate {condition:.3g} is above {max_condition:.3g}")
    mean_target = sum(targets) / count
    right = [sum(standardised[i][column] * (targets[i] - mean_target) for i in range(count)) / count
             for column in range(size)]
    prior = [(term.prior_coefficient or 0.0) * scales[index] for index, term in enumerate(terms)]
    left = [[gram[row][column] + (ridge if row == column else 0.0) for column in range(size)] for row in range(size)]
    coefficients = solve(left, [right[index] + ridge * prior[index] for index in range(size)])
    expression = Expression(tuple(terms), tuple(coefficients), mean_target, tuple(centers), tuple(scales), "fitted")
    predicted = [expression.intercept + sum(coefficients[c] * standardised[i][c] for c in range(size)) for i in range(count)]
    residuals = sorted(targets[i] - predicted[i] for i in range(count))
    diagnostics = {"route": "fitted", "n_rows": count, "n_rows_dropped": dropped, "condition_estimate": condition,
                   "ridge": ridge, "r2_train": r_squared(predicted, targets),
                   "residual_quantiles": quantiles(residuals), "declared_priors": [t.prior_coefficient for t in terms],
                   "term_stability": (_stability(terms, rows, ridge=ridge, max_condition=max_condition,
                                                 intercept_prior=intercept_prior) if stability else None)}
    return Fit(expression, diagnostics)


def _stability(terms: Sequence[Term], rows: Sequence[Row], **kwargs) -> list[float | None]:
    """Per-term agreement between two deterministic halves of the rows, in [0, 1]; None when a half refuses.

    This is the only per-term diagnostic the proposer sees, and it is an aggregate: it says
    whether a coefficient survives dropping half the evidence, not which candidates those were.
    """
    halves: tuple[list[Row], list[Row]] = ([], [])
    for index, row in enumerate(rows):
        halves[index % 2].append(row)
    fits = []
    for half in halves:
        try:
            fits.append(fit(terms, half, stability=False, **kwargs))
        except FitRefused:
            return [None] * len(terms)
    left, right = (item.expression.coefficients for item in fits)
    return [None if abs(a) + abs(b) <= _EPSILON else round(1.0 - abs(a - b) / (abs(a) + abs(b)), 4)
            for a, b in zip(left, right)]


def expert_prior_expression(terms: Sequence[Term], rows: Sequence[Row], *, intercept_prior: float = 0.0) -> Fit:
    """The model's cited coefficients used directly, for a target with too few usable rows to fit.

    The declared prior is on the feature's own scale, so it is multiplied by the column's
    standard deviation to live on the standardised scale the rest of the module uses; where a
    column cannot be scaled the raw value is kept. Provenance says `expert_prior`, and the
    adoption gate applies to it exactly as to a fitted expression.
    """
    missing = [term.text for term in terms if term.prior_coefficient is None]
    if missing:
        raise FitRefused("no_declared_prior", f"no cited coefficient for {missing}")
    matrix, targets, dropped = design(terms, rows)
    centers, scales = _standardise(matrix, terms, refuse_constant=False)
    coefficients = [term.prior_coefficient * scales[index] for index, term in enumerate(terms)]
    intercept = sum(targets) / len(targets) if targets else float(intercept_prior)
    expression = Expression(tuple(terms), tuple(coefficients), intercept, tuple(centers), tuple(scales), "expert_prior")
    diagnostics = {"route": "expert_prior", "n_rows": len(matrix), "n_rows_dropped": dropped, "condition_estimate": None,
                   "ridge": None, "r2_train": None, "residual_quantiles": None,
                   "declared_priors": [term.prior_coefficient for term in terms], "term_stability": None}
    return Fit(expression, diagnostics)


def sign_violations(expression: Expression) -> list[dict[str, Any]]:
    """Terms whose fitted coefficient contradicts the direction the model declared for them."""
    wanted = {"higher_better": 1.0, "lower_better": -1.0}
    out = []
    for term, coefficient in zip(expression.terms, expression.coefficients):
        want = wanted.get(term.direction)
        if want is None or abs(coefficient) <= _EPSILON:
            continue
        if (coefficient > 0) != (want > 0):
            out.append({"term": term.text, "declared_direction": term.direction, "coefficient": coefficient})
    return out


def with_grounding(expression: Expression, labels: dict[str, str]) -> Expression:
    """Relabel each term `mechanistic` or `associational` from the gate's verdict on its citations."""
    terms = tuple(replace(term, grounding=labels.get(term.text, "associational")) for term in expression.terms)
    return replace(expression, terms=terms)


# --- scoring ------------------------------------------------------------------------------------

def term_contributions(expression: Any, values: dict[str, Any]) -> list[dict[str, Any]]:
    """Every term's contribution for one candidate, in the expression's own order."""
    expr = as_expression(expression)
    out = []
    for index, term in enumerate(expr.terms):
        raw = term.raw_value(values)
        standardised = None if raw is None else (raw - expr.centers[index]) / expr.scales[index]
        out.append({"term": term.text, "features": list(term.features), "form": term.form,
                    "coefficient": expr.coefficients[index], "value": raw, "standardised": standardised,
                    "contribution": None if standardised is None else expr.coefficients[index] * standardised,
                    "missing": raw is None, "direction": term.direction, "grounding": term.grounding,
                    "claim_refs": list(term.claim_refs),
                    "feature_values": {name: values.get(name) for name in term.features}})
    return out


def evaluate(expression: Any, values: dict[str, Any]) -> tuple[float | None, float]:
    """(score, coverage) for one candidate, mirroring `assessor.preference_scores`' per-candidate pair.

    Coverage is the weighted share of the expression's features that had a usable value, each
    feature weighted by the absolute standardised coefficients of the terms using it. A missing
    term contributes nothing, which on the standardised scale is the training mean; that is a
    surrogate by omission, so it is never hidden — it is exactly what coverage reports, and the
    ranking coverage floor is what keeps a thinly covered candidate out of the ranking.
    """
    expr = as_expression(expression)
    weights: dict[str, float] = {}
    for term, coefficient in zip(expr.terms, expr.coefficients):
        for name in term.features:
            weights[name] = weights.get(name, 0.0) + abs(coefficient)
    usable = {name: isinstance(values.get(name), (int, float)) and not isinstance(values.get(name), bool)
              for name in weights}
    total = sum(weights.values())
    if total > _EPSILON:
        coverage = sum(weight for name, weight in weights.items() if usable[name]) / total
    else:   # every coefficient shrank to zero: fall back to the plain share of features present
        coverage = (sum(usable.values()) / len(usable)) if usable else 0.0
    score, any_term = expr.intercept, False
    for item in term_contributions(expr, values):
        if item["contribution"] is not None:
            score += item["contribution"]
            any_term = True
    return (score if any_term else None), coverage


def quantiles(values: Sequence[float], points: Sequence[float] = (0.0, 0.25, 0.5, 0.75, 1.0)) -> dict[str, float] | None:
    """Linear-interpolation quantiles, keyed by percentage, or None when there is nothing to summarise."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    out = {}
    for point in points:
        position = point * (len(ordered) - 1)
        low, high = math.floor(position), math.ceil(position)
        value = ordered[low] + (ordered[high] - ordered[low]) * (position - low)
        out[f"p{round(point * 100)}"] = round(value, 6)
    return out


def r_squared(predicted: Sequence[float], actual: Sequence[float]) -> float | None:
    if len(predicted) < 2:
        return None
    mean = sum(actual) / len(actual)
    total = sum((value - mean) ** 2 for value in actual)
    if total <= _EPSILON:
        return None
    residual = sum((actual[index] - predicted[index]) ** 2 for index in range(len(actual)))
    return 1.0 - residual / total


def kendall_tau(left: Sequence[float], right: Sequence[float]) -> float | None:
    """Kendall tau-b: ties enter the denominator, so a scorer that cannot separate candidates is not rewarded."""
    size = len(left)
    if size < 2:
        return None
    concordant = discordant = tied_left = tied_right = 0
    for i in range(size):
        for j in range(i + 1, size):
            a, b = left[i] - left[j], right[i] - right[j]
            if a == 0 and b == 0:
                continue
            if a == 0:
                tied_left += 1
            elif b == 0:
                tied_right += 1
            elif (a > 0) == (b > 0):
                concordant += 1
            else:
                discordant += 1
    denominator = math.sqrt((concordant + discordant + tied_left) * (concordant + discordant + tied_right))
    if denominator <= _EPSILON:
        return None
    return (concordant - discordant) / denominator


def metric_on_rows(expression: Any, rows: Sequence[Row], *, mode: str) -> dict[str, Any]:
    """The mode's selection metric for one expression over the given rows."""
    if mode not in SELECTION_METRICS:
        raise ValueError(f"unknown symbolic-regression mode {mode!r}")
    predicted, actual = [], []
    for values, target in rows:
        score, _coverage = evaluate(expression, values)
        if score is None or not isinstance(target, (int, float)) or isinstance(target, bool):
            continue
        predicted.append(score)
        actual.append(float(target))
    name = SELECTION_METRICS[mode]
    value = r_squared(predicted, actual) if name == "validation_r2" else kendall_tau(predicted, actual)
    return {"metric": name, "value": value, "n": len(predicted), "n_rows": len(rows)}


def selection_score(metric_value: float | None, expression: Any, *, complexity_penalty: float) -> float | None:
    """The metric minus the complexity penalty on terms and depth; None when the metric is undefined."""
    if metric_value is None:
        return None
    expr = as_expression(expression)
    return metric_value - complexity_penalty * (len(expr.terms) + expr.depth)


def better(candidate: dict[str, Any], incumbent: dict[str, Any] | None) -> bool:
    """Selection order: higher selection score, then fewer terms, then canonical text."""
    if candidate.get("selection_score") is None:
        return False
    if incumbent is None or incumbent.get("selection_score") is None:
        return True
    key = (-candidate["selection_score"], candidate["n_terms"], candidate["canonical_text"])
    held = (-incumbent["selection_score"], incumbent["n_terms"], incumbent["canonical_text"])
    return key < held


# --- splits ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Split:
    assignment: dict[str, str]
    seed: int
    select_share: float
    holdout_share: float

    def of(self, candidate_ref: str) -> str:
        return self.assignment.get(candidate_ref, "excluded")

    def members(self, name: str) -> list[str]:
        if name not in SPLIT_NAMES:
            raise ValueError(f"unknown split {name!r}")
        return sorted(ref for ref, part in self.assignment.items() if part == name)

    def counts(self) -> dict[str, int]:
        return {name: sum(1 for part in self.assignment.values() if part == name) for name in SPLIT_NAMES}

    def record(self) -> dict[str, Any]:
        """What goes into the registered ordering method: the recipe and the sizes, not the member lists."""
        return {"seed": self.seed, "select_share": self.select_share, "holdout_share": self.holdout_share,
                "counts": self.counts(), "assignment_hash": sha256_hex(sorted(self.assignment.items())),
                "rule": "sha256(candidate_ref + seed): holdout, then select, then train; excluded members are never in any"}


def split_candidates(candidate_refs: Iterable[str], *, seed: int, select_share: float, holdout_share: float,
                     exclude: Iterable[str] = ()) -> Split:
    """Three-way split by candidate hash: train fits, select compares generations, holdout decides adoption.

    The hash makes the split independent of iteration order and stable across runs with the same
    seed, so a later generation cannot be handed a kinder split. Excluded refs (every reference
    outcome) are in none of the three and are scored only once the expression is frozen.
    """
    if select_share + holdout_share >= 1.0:
        raise ValueError("select_share + holdout_share must leave rows to fit on")
    excluded = set(exclude)
    assignment: dict[str, str] = {}
    for ref in candidate_refs:
        if ref in excluded:
            assignment[ref] = "excluded"
            continue
        draw = int(sha256_hex(ref + str(seed))[:8], 16) / float(1 << 32)
        assignment[ref] = ("holdout" if draw < holdout_share else
                           "select" if draw < holdout_share + select_share else "train")
    return Split(assignment, seed, select_share, holdout_share)
