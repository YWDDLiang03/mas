"""Display aliases follow declared determination bases without renaming saved records."""

import copy

import pytest

from mas.ui.read_summaries import criterion_display_fields


@pytest.mark.parametrize(("name", "bases", "expected"), [
    ("Predicted structural descriptor", ["derived"], {"display_name": "structural descriptor (calculated)"}),
    ("Predicted model output", ["predicted"], {}),
    ("Predicted mixed-basis value", ["derived", "predicted"], {}),
    ("Predicted unsupported value", None, {}),
    ("Observed structural descriptor", ["derived"], {}),
    ("Predictedness index", ["derived"], {}),
])
def test_calculated_alias_requires_prediction_prefix_and_derived_only(name, bases, expected):
    attribute = {"name": name, "acceptable_determination_bases": bases}
    before = copy.deepcopy(attribute)
    assert criterion_display_fields(attribute) == expected
    assert attribute == before
