"""Predicted molecular properties from a local ADMET model panel (ADMET-AI over TDC datasets).

WHY this capability exists: of the evidence routes the drug adapter offers, three read a record
somebody curated (ChEMBL potency, ChEMBL molecule fields, PubChem descriptors) and one reads
papers. Absorption, metabolic stability and toxicity are measured for a few dozen well-studied
drugs and for nobody else, so every criterion about them defers and scores nothing over a
3,177-compound universe. A prediction is computable for every compound that has a structure, so a
criterion bound here scores the whole sweep -- and a classifier's decision boundary is a line the
model states rather than a preference somebody prefers.

WHAT IT IS NOT. A prediction is not a measurement and never stands in for one: every value carries
`value_kind: "predicted"` and `determination_basis: "predicted"`, the contract's
`claim_strength_ceiling` is `predicted`, and `criteria.check_attribute` already refuses an attribute
that accepts `predicted` alongside any other basis -- so a predicted quantity is its own attribute
with its own rule, and `assessor.usable_claims` sets its claims aside for every attribute that did
not ask for them by name.

HOW THE PREDICTOR IS REACHED. ADMET-AI needs torch, chemprop, rdkit and pandas; `mas` needs
`requests`. The two dependency sets never meet: the predictor lives in its own interpreter and is
reached by a subprocess running `_admet_worker.py`, which imports only `admet_ai` and the standard
library. A missing interpreter or a missing package is a deterministic, non-retryable refusal
(`environment_missing`) rather than an empty answer, because an empty answer reads as "no data"
about the compound when it is a fact about this machine.

WHAT THE PANEL HOLDS. `ENDPOINTS` below is the package's whole base panel, in the package's own
order, as `admet_ai.admet_info` reports it: 41 endpoints predicted by a Chemprop-RDKit ensemble
trained on a Therapeutics Data Commons dataset, and 11 physicochemical descriptors that ADMET-AI
computes with RDKit rather than predicting. Nothing is curated away: which endpoint answers a
question is the deriving agents' decision, not this module's. The 11 descriptors are calculations,
not predictions, and are stamped `predicted` with the rest -- the conservative reading of one route
with one basis, since a calculation treated as a prediction can only be trusted less than it
deserves, never more. Each value says so in its own provenance (`model`, `training_dataset`), and
`PubChem computed_property` remains the route for a descriptor that should count as `derived`.

A compound with no structure in the universe's structure file yields no value -- unknown, as a
ChEMBL field nobody filled yields unknown -- and never a failure.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

from mas.adapters.literature.bookshelf import default_cache_dir
from mas.core.broker import ProviderResponse, ToolContract, ToolError

PACKAGE = "admet_ai"
PACKAGE_DISTRIBUTION = "admet-ai"
WORKER = Path(__file__).with_name("_admet_worker.py")
# The cache is keyed by this as well as by the structure, so a package or table change serves new
# values instead of values a different panel produced.
PANEL_VERSION = "admet-ai-2-panel-1"
PERCENTILE_LABEL = "drugbank_approved_percentile"
# Every classifier in the panel is trained on a binary label and returns the probability of the
# positive class, so 0.5 is the decision boundary the task itself defines. Stated once, generically,
# rather than per endpoint: it is a property of a binary classifier, not of any one of these.
DECISION_BOUNDARY = 0.5
PHYSICOCHEMICAL = "Physicochemical"


def _endpoint(name: str, category: str, task_type: str, unit: str, package_units: str, species: str,
              training_rows: int | None, metric: dict[str, float], reference: str) -> dict[str, Any]:
    """One row of the package's panel table, with the unit spelled as this repository spells units.

    `unit` is the executable one: an attribute bound to an endpoint declares it, and
    `assessor.usable_claims` drops a claim whose unit is not the attribute's. A classifier returns
    the probability of its positive class, which this repository has no unit word for, so it is
    given one (`probability`) rather than left null -- `criteria.check_attribute` refuses a
    quantitative attribute without a unit, which would make every classifier in the panel
    unbindable. `package_units` keeps the package's own spelling so the normalization is auditable.
    """
    return {"name": name, "category": category, "task_type": task_type, "unit": unit,
            "package_units": package_units, "species": None if species == "-" else species,
            "training_rows": training_rows, "metric": metric, "reference": reference,
            "model": ("RDKit calculation (not a trained model)" if category == PHYSICOCHEMICAL
                      else "Chemprop-RDKit ensemble over the TDC dataset of the same id"),
            "decision_boundary": DECISION_BOUNDARY if task_type == "classification" else None}


# The whole base panel, in the package's order. Verified against the installed package
# (`tests/test_live_predict.py::test_the_recorded_panel_is_the_panel_the_package_reports`) and
# against the worker's own panel record on every batch (`PanelCache._check_panel`).
ENDPOINTS: dict[str, dict[str, Any]] = {
    "molecular_weight": _endpoint("Molecular Weight", "Physicochemical", "regression", "g/mol", "Dalton", "-", None,
                                  {},
                                  "https://www.rdkit.org/docs/source/rdkit.Chem.Descriptors.html#rdkit.Chem.Descriptors.MolWt"),
    "logP": _endpoint("LogP", "Physicochemical", "regression", "log units", "log-ratio", "-", None, {},
                      "https://www.rdkit.org/docs/source/rdkit.Chem.Crippen.html#rdkit.Chem.Crippen.MolLogP"),
    "hydrogen_bond_acceptors": _endpoint("Hydrogen Bond Acceptors", "Physicochemical", "regression", "count", "#",
                                         "-", None, {},
                                         "https://www.rdkit.org/docs/source/rdkit.Chem.rdMolDescriptors.html#rdkit.Chem.rdMolDescriptors.CalcNumHBA"),
    "hydrogen_bond_donors": _endpoint("Hydrogen Bond Donors", "Physicochemical", "regression", "count", "#", "-",
                                      None, {},
                                      "https://www.rdkit.org/docs/source/rdkit.Chem.rdMolDescriptors.html#rdkit.Chem.rdMolDescriptors.CalcNumHBD"),
    "Lipinski": _endpoint("Lipinski Rule of 5", "Physicochemical", "regression", "count", "# of 4", "-", None, {},
                          "https://en.wikipedia.org/wiki/Lipinski%27s_rule_of_five#Components_of_the_rule"),
    "QED": _endpoint("Quantitative Estimate of Druglikeness (QED)", "Physicochemical", "regression", "score", "-",
                     "-", None, {}, "https://www.rdkit.org/docs/source/rdkit.Chem.QED.html#rdkit.Chem.QED.qed"),
    "stereo_centers": _endpoint("Stereo Centers", "Physicochemical", "regression", "count", "#", "-", None, {},
                                "https://www.rdkit.org/docs/source/rdkit.Chem.rdMolDescriptors.html#rdkit.Chem.rdMolDescriptors.CalcNumAtomStereoCenters"),
    "tpsa": _endpoint("Topological Polar Surface Area (TPSA)", "Physicochemical", "regression", "Å²", "Å^2", "-",
                      None, {},
                      "https://www.rdkit.org/docs/source/rdkit.Chem.rdMolDescriptors.html#rdkit.Chem.rdMolDescriptors.CalcTPSA"),
    "PAINS_alert": _endpoint("PAINS Alert", "Physicochemical", "regression", "count", "#", "-", None, {},
                             "https://www.rdkit.org/docs/GettingStartedInPython.html#filtering-unwanted-substructures"),
    "BRENK_alert": _endpoint("BRENK Alert", "Physicochemical", "regression", "count", "#", "-", None, {},
                             "https://www.rdkit.org/docs/GettingStartedInPython.html#filtering-unwanted-substructures"),
    "NIH_alert": _endpoint("NIH Alert", "Physicochemical", "regression", "count", "#", "-", None, {},
                           "https://www.rdkit.org/docs/GettingStartedInPython.html#filtering-unwanted-substructures"),
    "HIA_Hou": _endpoint("Human Intestinal Absorption", "Absorption", "classification", "probability", "-", "human",
                         578, {"auprc": 0.9995, "auroc": 0.994},
                         "https://tdcommons.ai/single_pred_tasks/adme/#hia-human-intestinal-absorption-hou-et-al"),
    "Bioavailability_Ma": _endpoint("Oral Bioavailability", "Absorption", "classification", "probability", "-",
                                    "human", 640, {"auprc": 0.87, "auroc": 0.7164},
                                    "https://tdcommons.ai/single_pred_tasks/adme/#bioavailability-ma-et-al"),
    "Solubility_AqSolDB": _endpoint("Aqueous Solubility", "Absorption", "regression", "log(mol/L)", "log(mol/L)",
                                    "-", 9980, {"r2": 0.8166, "mae": 0.6921},
                                    "https://tdcommons.ai/single_pred_tasks/adme/#solubility-aqsoldb"),
    "Lipophilicity_AstraZeneca": _endpoint("Lipophilicity", "Absorption", "regression", "log units", "log-ratio",
                                           "-", 4200, {"r2": 0.7712, "mae": 0.407},
                                           "https://tdcommons.ai/single_pred_tasks/adme/#lipophilicity-astrazeneca"),
    "HydrationFreeEnergy_FreeSolv": _endpoint("Hydration Free Energy", "Absorption", "regression", "kcal/mol",
                                              "kcal/mol", "-", 642, {"r2": 0.8877, "mae": 0.7826},
                                              "https://tdcommons.ai/single_pred_tasks/adme/#hydration-free-energy-freesolv"),
    "Caco2_Wang": _endpoint("Cell Effective Permeability", "Absorption", "regression", "log(10^-6 cm/s)",
                            "log(10^-6 cm/s)", "human", 906, {"r2": 0.7065, "mae": 0.3115},
                            "https://tdcommons.ai/single_pred_tasks/adme/#caco-2-cell-effective-permeability-wang-et-al"),
    "PAMPA_NCATS": _endpoint("PAMPA Permeability", "Absorption", "classification", "probability", "-",
                             "artificial membrane", 2034, {"auprc": 0.9549, "auroc": 0.7864},
                             "https://tdcommons.ai/single_pred_tasks/adme/#pampa-permeability-ncats"),
    "Pgp_Broccatelli": _endpoint("P-glycoprotein Inhibition", "Absorption", "classification", "probability", "-",
                                 "human pgp / mouse cells", 1212, {"auprc": 0.9581, "auroc": 0.9475},
                                 "https://tdcommons.ai/single_pred_tasks/adme/#pgp-p-glycoprotein-inhibition-broccatelli-et-al"),
    "BBB_Martins": _endpoint("Blood-Brain Barrier Penetration", "Distribution", "classification", "probability", "-",
                             "human", 1975, {"auprc": 0.959, "auroc": 0.9004},
                             "https://tdcommons.ai/single_pred_tasks/adme/#bbb-blood-brain-barrier-martins-et-al"),
    "PPBR_AZ": _endpoint("Plasma Protein Binding Rate", "Distribution", "regression", "%", "%", "human", 1614,
                         {"r2": 0.5889, "mae": 6.8517},
                         "https://tdcommons.ai/single_pred_tasks/adme/#ppbr-plasma-protein-binding-rate-astrazeneca"),
    "VDss_Lombardo": _endpoint("Volume of Distribution at Steady State", "Distribution", "regression", "L/kg",
                               "L/kg", "human", 1111, {"r2": -1.2107, "mae": 5.0394},
                               "https://tdcommons.ai/single_pred_tasks/adme/#vdss-volumn-of-distribution-at-steady-state-lombardo-et-al"),
    "Half_Life_Obach": _endpoint("Half Life", "Excretion", "regression", "h", "hr", "human", 665,
                                 {"r2": -2.3857, "mae": 31.8474},
                                 "https://tdcommons.ai/single_pred_tasks/adme/#half-life-obach-et-al"),
    "Clearance_Hepatocyte_AZ": _endpoint("Drug Clearance (Hepatocyte)", "Excretion", "regression",
                                         "uL/min/10^6 cells", "uL/min/10^6 cells", "human & rat", 1020,
                                         {"r2": 0.264, "mae": 32.7257},
                                         "https://tdcommons.ai/single_pred_tasks/adme/#clearance-astrazeneca"),
    "Clearance_Microsome_AZ": _endpoint("Drug Clearance (Microsome)", "Excretion", "regression", "uL/min/mg",
                                        "uL/min/mg", "human", 1102, {"r2": 0.2767, "mae": 26.7376},
                                        "https://tdcommons.ai/single_pred_tasks/adme/#clearance-astrazeneca"),
    "CYP1A2_Veith": _endpoint("CYP1A2 Inhibition", "Metabolism", "classification", "probability", "-", "human",
                              12579, {"auprc": 0.9352, "auroc": 0.9411},
                              "https://tdcommons.ai/single_pred_tasks/adme/#cyp-p450-1a2-inhibition-veith-et-al"),
    "CYP2C19_Veith": _endpoint("CYP2C19 Inhibition", "Metabolism", "classification", "probability", "-", "human",
                               12665, {"auprc": 0.8753, "auroc": 0.9062},
                               "https://tdcommons.ai/single_pred_tasks/adme/#cyp-p450-2c19-inhibition-veith-et-al"),
    "CYP2C9_Veith": _endpoint("CYP2C9 Inhibition", "Metabolism", "classification", "probability", "-", "human",
                              12092, {"auprc": 0.8224, "auroc": 0.9077},
                              "https://tdcommons.ai/single_pred_tasks/adme/#cyp-p450-2c9-inhibition-veith-et-al"),
    "CYP2D6_Veith": _endpoint("CYP2D6 Inhibition", "Metabolism", "classification", "probability", "-", "human",
                              13130, {"auprc": 0.7255, "auroc": 0.8861},
                              "https://tdcommons.ai/single_pred_tasks/adme/#cyp-p450-2d6-inhibition-veith-et-al"),
    "CYP3A4_Veith": _endpoint("CYP3A4 Inhibition", "Metabolism", "classification", "probability", "-", "human",
                              12328, {"auprc": 0.8734, "auroc": 0.9116},
                              "https://tdcommons.ai/single_pred_tasks/adme/#cyp-p450-3a4-inhibition-veith-et-al"),
    "CYP2C9_Substrate_CarbonMangels": _endpoint("CYP2C9 Substrate", "Metabolism", "classification", "probability",
                                                "-", "human", 666, {"auprc": 0.3696, "auroc": 0.6279},
                                                "https://tdcommons.ai/single_pred_tasks/adme/#cyp2c9-substrate-carbon-mangels-et-al"),
    "CYP2D6_Substrate_CarbonMangels": _endpoint("CYP2D6 Substrate", "Metabolism", "classification", "probability",
                                                "-", "human", 664, {"auprc": 0.6602, "auroc": 0.82},
                                                "https://tdcommons.ai/single_pred_tasks/adme/#cyp2d6-substrate-carbon-mangels-et-al"),
    "CYP3A4_Substrate_CarbonMangels": _endpoint("CYP3A4 Substrate", "Metabolism", "classification", "probability",
                                                "-", "human", 667, {"auprc": 0.7272, "auroc": 0.7048},
                                                "https://tdcommons.ai/single_pred_tasks/adme/#cyp3a4-substrate-carbon-mangels-et-al"),
    "hERG": _endpoint("hERG Blocking", "Toxicity", "classification", "probability", "-", "human", 648,
                      {"auprc": 0.9062, "auroc": 0.8388},
                      "https://tdcommons.ai/single_pred_tasks/tox/#herg-blockers"),
    "ClinTox": _endpoint("Clinical Toxicity", "Toxicity", "classification", "probability", "-", "human", 1459,
                         {"auprc": 0.6069, "auroc": 0.9275}, "https://tdcommons.ai/single_pred_tasks/tox/#clintox"),
    "AMES": _endpoint("Mutagenicity", "Toxicity", "classification", "probability", "-", "salmonella typhimurium",
                      7255, {"auprc": 0.8958, "auroc": 0.8816},
                      "https://tdcommons.ai/single_pred_tasks/tox/#ames-mutagenicity"),
    "DILI": _endpoint("Drug Induced Liver Injury", "Toxicity", "classification", "probability", "-", "human", 475,
                      {"auprc": 0.8777, "auroc": 0.8815},
                      "https://tdcommons.ai/single_pred_tasks/tox/#dili-drug-induced-liver-injury"),
    "Carcinogens_Lagunin": _endpoint("Carcinogenicity", "Toxicity", "classification", "probability", "-", "rodent",
                                     278, {"auprc": 0.6083, "auroc": 0.7723},
                                     "https://tdcommons.ai/single_pred_tasks/tox/#carcinogens"),
    "LD50_Zhu": _endpoint("Acute Toxicity LD50", "Toxicity", "regression", "log(1/(mol/kg))", "log(1/(mol/kg))",
                          "rat", 7342, {"r2": 0.5959, "mae": 0.4515},
                          "https://tdcommons.ai/single_pred_tasks/tox/#acute-toxicity-ld50"),
    "Skin_Reaction": _endpoint("Skin Reaction", "Toxicity", "classification", "probability", "-", "mouse", 404,
                               {"auprc": 0.873, "auroc": 0.718},
                               "https://tdcommons.ai/single_pred_tasks/tox/#skin-reaction"),
    "NR-AR": _endpoint("Androgen Receptor (Full Length)", "Toxicity", "classification", "probability", "-", "human",
                       7258, {"auprc": 0.5151, "auroc": 0.7795},
                       "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "NR-AR-LBD": _endpoint("Androgen Receptor (Ligand Binding Domain)", "Toxicity", "classification", "probability",
                           "-", "human", 6751, {"auprc": 0.6722, "auroc": 0.8834},
                           "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "NR-AhR": _endpoint("Aryl Hydrocarbon Receptor", "Toxicity", "classification", "probability", "-", "human", 6542,
                        {"auprc": 0.636, "auroc": 0.9044}, "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "NR-Aromatase": _endpoint("Aromatase", "Toxicity", "classification", "probability", "-", "human", 5815,
                              {"auprc": 0.4748, "auroc": 0.9056},
                              "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "NR-ER": _endpoint("Estrogen Receptor (Full Length)", "Toxicity", "classification", "probability", "-", "human",
                       6186, {"auprc": 0.4583, "auroc": 0.7488},
                       "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "NR-ER-LBD": _endpoint("Estrogen Receptor (Ligand Binding Domain)", "Toxicity", "classification", "probability",
                           "-", "human", 6948, {"auprc": 0.4838, "auroc": 0.8265},
                           "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "NR-PPAR-gamma": _endpoint("Peroxisome Proliferator-Activated Receptor Gamma", "Toxicity", "classification",
                               "probability", "-", "human", 6443, {"auprc": 0.439, "auroc": 0.9164},
                               "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "SR-ARE": _endpoint("Nuclear Factor (Erythroid-Derived 2)-Like 2/Antioxidant Responsive Element", "Toxicity",
                        "classification", "probability", "-", "human", 5825, {"auprc": 0.5195, "auroc": 0.8378},
                        "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "SR-ATAD5": _endpoint("ATPase Family AAA Domain-Containing Protein 5 (ATAD5)", "Toxicity", "classification",
                          "probability", "-", "human", 7065, {"auprc": 0.3116, "auroc": 0.8791},
                          "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "SR-HSE": _endpoint("Heat Shock Factor Response Element", "Toxicity", "classification", "probability", "-",
                        "human", 6460, {"auprc": 0.4275, "auroc": 0.8427},
                        "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "SR-MMP": _endpoint("Mitochondrial Membrane Potential", "Toxicity", "classification", "probability", "-",
                        "human", 5804, {"auprc": 0.6983, "auroc": 0.9247},
                        "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
    "SR-p53": _endpoint("Tumor Protein p53", "Toxicity", "classification", "probability", "-", "human", 6767,
                        {"auprc": 0.4411, "auroc": 0.8803}, "https://tdcommons.ai/single_pred_tasks/tox/#tox21"),
}

for _endpoint_id, _spec in ENDPOINTS.items():
    # The TDC dataset behind a trained endpoint is the endpoint's own id, which is how the
    # reference URL names it; the eleven descriptors have no dataset because they have no model.
    _spec["endpoint"] = _endpoint_id
    _spec["training_dataset"] = None if _spec["category"] == PHYSICOCHEMICAL else _endpoint_id

# Fields of the recorded table that the installed package also reports, so they can be compared.
PANEL_FIELDS_CHECKED = ("name", "category", "task_type", "package_units")
CLASSIFIERS = tuple(e for e, spec in ENDPOINTS.items() if spec["task_type"] == "classification")
REGRESSIONS = tuple(e for e, spec in ENDPOINTS.items() if spec["task_type"] == "regression")
# Trained endpoints against computed descriptors: the first are predictions, the second are RDKit
# calculations the package reports in the same frame (see this module's docstring).
MODEL_ENDPOINTS = tuple(e for e, spec in ENDPOINTS.items() if spec["category"] != PHYSICOCHEMICAL)
DESCRIPTOR_ENDPOINTS = tuple(e for e, spec in ENDPOINTS.items() if spec["category"] == PHYSICOCHEMICAL)
UNITS = {endpoint: spec["unit"] for endpoint, spec in ENDPOINTS.items()}
CATEGORIES = tuple(dict.fromkeys(spec["category"] for spec in ENDPOINTS.values()))


# --- the predictor environment ----------------------------------------------------------------

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def candidates(python: str | Path | None = None) -> list[str]:
    """Interpreters that might run the predictor, best first.

    An interpreter named explicitly is the only candidate: an operator who points at the wrong
    environment is told so, rather than quietly served by another one that happens to work.
    No path is written into this module -- a checkout elsewhere keeps working, and an environment
    somewhere else is named once in `predict.python` or `MAS_ADMET_PYTHON`.
    """
    if python:
        return [str(python)]
    named = os.environ.get("MAS_ADMET_PYTHON")
    if named:
        return [named]
    root = _repo_root()
    found = [str(root / "admet-env" / "bin" / "python"), str(root.parent / "admet-env" / "bin" / "python")]
    if importlib.util.find_spec(PACKAGE) is not None:
        found.append(sys.executable)     # the predictor is installed beside `mas` after all
    return found


def _probe(python: str) -> bool:
    """Whether `python` can import the predictor, asked without importing it.

    `find_spec` loads no module, so the probe costs one interpreter start (measured: 50 ms)
    instead of the fifteen seconds importing torch and the ensembles costs.
    """
    if not (os.path.isabs(python) and os.path.exists(python)) and shutil.which(python) is None:
        return False
    try:
        done = subprocess.run([python, "-c", f"import importlib.util,sys;"
                                             f"sys.exit(0 if importlib.util.find_spec({PACKAGE!r}) else 1)"],
                              capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


_PROBED: dict[str, bool] = {}
_PROBE_LOCK = threading.Lock()


def has_package(python: str) -> bool:
    with _PROBE_LOCK:
        if python not in _PROBED:
            _PROBED[python] = _probe(python)
        return _PROBED[python]


def interpreter(python: str | Path | None = None) -> str | None:
    """The interpreter that will run the predictor, or None when no candidate has the package."""
    return next((c for c in candidates(python) if has_package(c)), None)


def available(python: str | Path | None = None) -> bool:
    """Whether the predictor can be reached at all. Registration's default rests on this."""
    return interpreter(python) is not None


def _refuse_environment(python: str | Path | None) -> ToolError:
    tried = candidates(python)
    return ToolError("environment_missing",
                     f"no interpreter with the {PACKAGE_DISTRIBUTION} package: tried {', '.join(tried)}. "
                     f"Set predict.python (or MAS_ADMET_PYTHON) to the interpreter of an environment "
                     f"with {PACKAGE_DISTRIBUTION} installed; `mas predict check` reports what is found",
                     retryable=False, diagnostic={"tried": tried, "worker": str(WORKER)})


# --- structures -------------------------------------------------------------------------------

def structure_file_for(universe_file: str | Path) -> Path:
    """The structure file of a universe: `universe_smiles.json` beside the universe file."""
    return Path(universe_file).parent / "universe_smiles.json"


class StructureIndex:
    """InChIKey -> canonical SMILES for the members of one universe.

    The universe file carries no structure (a member is an InChIKey, a ChEMBL id, a name, a phase
    and some record fields), and a predictor needs one, so the structures are a separate documented
    file: a flat JSON object mapping ChEMBL id to canonical SMILES, or to null where the source has
    no structure for that compound. A member with no structure is unknown to this route, which is a
    fact about that compound; a structure file that is not there at all is a fact about the
    installation, and refuses rather than reporting 3,177 unknowns.
    """

    def __init__(self, universe_file: str | Path, structure_file: str | Path | None = None):
        self.universe_file = Path(universe_file)
        self.structure_file = Path(structure_file) if structure_file else structure_file_for(universe_file)
        self._lock = threading.Lock()
        self._by_key: dict[str, str] | None = None
        self._all: dict[str, str] = {}
        self._source = ""

    def _load(self) -> dict[str, str]:
        if self._by_key is not None:
            return self._by_key      # read once, then read without the lock: a sweep asks per cell
        with self._lock:
            if self._by_key is None:
                if not self.structure_file.exists():
                    raise ToolError("environment_missing",
                                    f"no structure file at {self.structure_file}: this route needs canonical "
                                    f"SMILES for the universe's members, keyed by ChEMBL id",
                                    retryable=False, diagnostic={"structure_file": str(self.structure_file)})
                try:
                    universe = json.loads(self.universe_file.read_text(encoding="utf-8"))
                    smiles = json.loads(self.structure_file.read_text(encoding="utf-8"))
                except (OSError, ValueError) as error:
                    raise ToolError("parse_failed", f"the universe or its structure file cannot be read: {error}",
                                    retryable=False) from None
                self._source = universe.get("source", "unknown")
                self._by_key = {member["inchikey"]: smiles[member["chembl_id"]]
                                for member in universe["universe"]
                                if smiles.get(member["chembl_id"])}
                self._all = {member["chembl_id"]: member["inchikey"] for member in universe["universe"]}
            return self._by_key

    @property
    def source(self) -> str:
        self._load()
        return self._source

    def smiles_for(self, inchikey: str) -> str | None:
        """The member's canonical SMILES, or None when the universe has no structure for it."""
        return self._load().get(inchikey)

    def structures(self) -> list[str]:
        """Every distinct structure in the universe, in the universe's own order."""
        return list(dict.fromkeys(self._load().values()))

    def coverage(self) -> dict[str, int]:
        self._load()
        return {"members": len(self._all), "with_structure": len(self._by_key),
                "without_structure": len(self._all) - len(self._by_key)}


# --- the prediction cache ---------------------------------------------------------------------

def digest(smiles: str) -> str:
    return hashlib.sha256(smiles.encode("utf-8")).hexdigest()


class PanelCache:
    """One structure's whole panel, computed once and served to every endpoint asked of it.

    Keyed by the canonical SMILES (hashed), on disk under the adapter's cache directory, because
    the prediction is a function of the structure. Without this a universe sweep pays a model run
    per (compound, endpoint) -- 52 endpoints over 3,177 compounds -- where one run per compound
    answers every endpoint, and it pays the whole cost again on the next run.

    HOW DETERMINISTIC, EXACTLY: the ensembles run in `inference_mode` with no dropout, so nothing
    is sampled -- but the value is not bit-for-bit independent of the batch it was scored in,
    because float32 partial sums are accumulated in an order that depends on how the batch was
    assembled. Measured: between a batch of 3 and the warm run's batches of 256, 75 of 156 values
    over three universe compounds differ at all, the worst by 2.8e-6 relative (Half_Life_Obach);
    between a batch of 1 and a batch of 5, 1.9e-5 relative (Clearance_Microsome_AZ). So agreement
    is five to six significant figures, which is far below any decision this repository takes on a
    number -- a probability against 0.5, a value against a cutoff; no classifier verdict changed
    side in that sample. Caching by structure is therefore sound, but a cached value is not a
    bit-exact replay of a recomputation and nothing should compare two of them for equality.

    `warm` is why the cache is a batch object rather than a memo: loading the ensembles costs about
    what predicting two hundred molecules costs (measured: 17 s against 17 s), so the expensive
    thing is starting the predictor, not asking it. One subprocess scores the whole universe and
    the sweep then reads files. The per-structure path stays, for a compound a warm run missed; it
    is serialized behind one lock, which is deliberate -- two threads each loading the ensembles
    would spend a minute of model loading to answer two questions.
    """

    def __init__(self, cache_dir: str | Path | None = None, *, python: str | Path | None = None,
                 chunk_size: int = 256, timeout_s: float = 7200.0):
        self.root = Path(cache_dir or default_cache_dir()) / "admet" / PANEL_VERSION
        self.python = str(python) if python else None
        self.chunk_size = int(chunk_size)
        self.timeout_s = float(timeout_s)
        self.predictor: dict[str, Any] = {}
        self._memo: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    # --- storage ------------------------------------------------------------------------------
    def path(self, smiles: str) -> Path:
        key = digest(smiles)
        return self.root / key[:2] / f"{key}.json"

    def stored(self, smiles: str) -> dict[str, Any] | None:
        """This structure's cached panel row, or None. Never raises on a damaged file."""
        if smiles in self._memo:
            return self._memo[smiles]
        path = self.path(smiles)
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None       # a half-written file is a miss, not a failure: it is recomputed
        self._memo[smiles] = record
        return record

    def _store(self, record: dict[str, Any]) -> None:
        path = self.path(record["smiles"])
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".part")
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        temporary.replace(path)        # one rename, so a reader never sees half a row
        self._memo[record["smiles"]] = record

    # --- the worker ---------------------------------------------------------------------------
    def _check_panel(self, endpoints: list[dict[str, Any]]) -> None:
        """Refuse a package whose panel is not the panel this module records.

        The recorded table says what each number means -- its unit, whether it is a probability,
        which dataset stands behind it -- and a package that moved an endpoint would have the
        values labelled by the old table. That is the one failure this route must not have, so it
        is checked on every batch rather than trusted.
        """
        reported = {entry["id"]: entry for entry in endpoints}
        problems = [f"{endpoint} is not in the installed panel" for endpoint in ENDPOINTS if endpoint not in reported]
        problems += [f"{endpoint} is in the installed panel and not in the recorded one" for endpoint in reported
                     if endpoint not in ENDPOINTS]
        for endpoint, spec in ENDPOINTS.items():
            entry = reported.get(endpoint)
            for field in PANEL_FIELDS_CHECKED:
                if entry is not None and entry.get(field) != spec[field]:
                    problems.append(f"{endpoint}.{field}: recorded {spec[field]!r}, installed {entry.get(field)!r}")
        if problems:
            raise ToolError("schema_violation",
                            f"the installed {PACKAGE_DISTRIBUTION} panel differs from the one this adapter records: "
                            f"{'; '.join(problems[:8])}", retryable=False,
                            diagnostic={"problems": problems, "panel_version": PANEL_VERSION})

    def _run(self, smiles: list[str], progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, int]:
        """Score these structures in one subprocess, storing each row as it arrives."""
        python = interpreter(self.python)
        if python is None:
            raise _refuse_environment(self.python)
        self.root.mkdir(parents=True, exist_ok=True)
        log = self.root / "worker.log"
        counts = {"computed": 0, "refused": 0}
        done = False
        with log.open("w", encoding="utf-8") as errors:
            # The worker's stderr goes to a file rather than a pipe nobody drains: it prints an
            # RDKit line per molecule, which would fill a pipe buffer and deadlock the batch.
            # utf-8 explicitly, not the locale's encoding: one endpoint's unit is reported as
            # "Angstrom^2" with the Angstrom sign in it, and under a C locale the default decoder
            # would turn the panel record into a decode error -- a refusal with nothing wrong.
            process = subprocess.Popen([python, str(WORKER), str(self.chunk_size)], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=errors, text=True, encoding="utf-8")
            watchdog = threading.Timer(self.timeout_s, process.kill)
            watchdog.start()
            try:
                try:
                    process.stdin.write("".join(json.dumps(s) + "\n" for s in smiles))
                    process.stdin.close()
                except OSError as error:
                    # The worker died before it had read the structures (a broken import, a kill):
                    # a raw OSError out of a provider becomes `internal_error`, which says the
                    # adapter has a bug rather than that the predictor could not be run.
                    process.kill()
                    raise ToolError("model_unavailable",
                                    f"the prediction worker ended before reading the structures: {error}; "
                                    f"its diagnostics are in {log}", retryable=False,
                                    diagnostic={"log": str(log), "tail": _tail(log)}) from None
                for line in process.stdout:
                    record = json.loads(line)
                    if record["kind"] == "meta":
                        self.predictor = {k: v for k, v in record.items() if k not in ("kind", "requested", "tasks")}
                    elif record["kind"] == "panel":
                        self._check_panel(record["endpoints"])
                    elif record["kind"] == "row":
                        self._store({"smiles": record["smiles"], "values": record.get("values"),
                                     "percentiles": record.get("percentiles"), "error": record.get("error"),
                                     "predictor": self.predictor, "panel_version": PANEL_VERSION})
                        counts["refused" if record.get("error") else "computed"] += 1
                        if progress is not None:
                            progress(dict(counts, smiles=record["smiles"]))
                    elif record["kind"] == "done":
                        done = True
            except (ValueError, KeyError) as error:
                process.kill()
                raise ToolError("parse_failed", f"the prediction worker wrote something this adapter cannot read: "
                                                f"{error}; its diagnostics are in {log}", retryable=False) from None
            finally:
                watchdog.cancel()
                try:
                    status = process.wait(timeout=60) if done else None
                except subprocess.TimeoutExpired:
                    status = None
                if status is None:
                    # Either this stopped reading early -- a refused panel, an unreadable line --
                    # in which case the worker is blocked writing rows into a pipe nobody will
                    # drain, or it will not end on its own. Waiting on it would hang the run.
                    process.kill()
                    status = process.wait()
                process.stdout.close()
        if not done or status != 0:
            raise ToolError("model_unavailable",
                            f"the prediction worker ended with status {status} after "
                            f"{counts['computed'] + counts['refused']} of {len(smiles)} structure(s); "
                            f"its diagnostics are in {log}", retryable=False,
                            diagnostic=dict(counts, requested=len(smiles), log=str(log), tail=_tail(log)))
        return counts

    def row(self, smiles: str) -> dict[str, Any]:
        """This structure's panel row, from the cache or from the predictor."""
        record = self.stored(smiles)
        if record is not None:
            return record
        with self._lock:
            record = self.stored(smiles)
            if record is None:
                self._run([smiles])
                record = self.stored(smiles)
            if record is None:
                raise ToolError("model_unavailable", f"the predictor returned no row for the structure {smiles}",
                                retryable=False)
            return record

    def warm(self, smiles: list[str], *, progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        """Precompute every structure that is not cached yet, in one subprocess. Returns a report."""
        wanted = list(dict.fromkeys(s for s in smiles if s))
        missing = [s for s in wanted if self.stored(s) is None]
        started = time.monotonic()
        counts = self._run(missing, progress=progress) if missing else {"computed": 0, "refused": 0}
        return {"requested": len(wanted), "already_cached": len(wanted) - len(missing), **counts,
                "elapsed_s": round(time.monotonic() - started, 1), "cache_dir": str(self.root),
                "predictor": self.predictor, "panel_version": PANEL_VERSION,
                "endpoints": len(ENDPOINTS)}


def _tail(path: Path, lines: int = 12) -> list[str]:
    try:
        return [line.rstrip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]]
    except OSError:
        return []


# --- the provider -----------------------------------------------------------------------------

class AdmetPrediction:
    """One predicted endpoint for one compound, with the predictor named in its provenance.

    The contract declares `determinism: deterministic`, which is true of the model (it samples
    nothing) to about eight significant figures; `PanelCache` records what was measured and why
    two values must not be compared for bit equality.
    """

    contract = ToolContract(
        tool_id="tool_predict_admet_panel", capability="predicted_property_lookup",
        capability_kind="attribute_estimate", question_kinds=("admet_prediction",), contract_version="1",
        implementation_version="admet-ai-2-chemprop-rdkit-panel-1",
        purpose_statement="Predicted ADMET endpoints for a compound's structure (predictions, never measurements)",
        evidence_kind_produced="model_prediction", claim_strength_ceiling="predicted",
        determinism="deterministic", cost_latency_class="long", timeout_ms=600_000,
        identity_inputs=("identifier",), required_inputs=("endpoint",), execution_location="local_subprocess",
        license_id="ADMET-AI: MIT; TDC training data: per-dataset licences (see each endpoint's reference)")

    def __init__(self, structures: StructureIndex, cache: PanelCache):
        self.structures = structures
        self.cache = cache

    def invoke(self, question_kind: str, inputs: dict[str, Any]) -> ProviderResponse:
        endpoint = inputs["endpoint"]
        spec = ENDPOINTS.get(endpoint)
        if spec is None:
            raise ToolError("input_invalid", f"unsupported endpoint {endpoint!r}; the panel holds "
                                             f"{len(ENDPOINTS)} endpoints", retryable=False,
                            diagnostic={"endpoints": sorted(ENDPOINTS)})
        version = f"{PACKAGE_DISTRIBUTION} {self.cache.predictor.get('version') or 'unknown'}; {PANEL_VERSION}"
        smiles = self.structures.smiles_for(inputs["identifier"])
        if smiles is None:
            # No structure, so nothing to predict from: unknown, exactly as a record field nobody
            # filled is unknown. The warning says which it was, so the cell's absence check records
            # a missing structure rather than a silent empty answer.
            return ProviderResponse(values=[], data_version=version,
                                    warnings=[f"the universe has no structure for {inputs['identifier']}, "
                                              f"so no endpoint of this panel can be predicted for it"])
        record = self.cache.row(smiles)
        version = f"{PACKAGE_DISTRIBUTION} {(record.get('predictor') or {}).get('version') or 'unknown'}; {PANEL_VERSION}"
        key = digest(smiles)
        if record.get("error"):
            return ProviderResponse(values=[], data_version=version,
                                    warnings=[f"the predictor refused the structure of {inputs['identifier']}: "
                                              f"{record['error']}"])
        value = (record.get("values") or {}).get(endpoint)
        if value is None:
            return ProviderResponse(values=[], data_version=version,
                                    warnings=[f"the predictor returned no {endpoint} for {inputs['identifier']}"])
        percentile = (record.get("percentiles") or {}).get(endpoint)
        return ProviderResponse(
            values=[{"name": endpoint, "value": float(value), "unit": spec["unit"], "value_kind": "predicted",
                     "determination_basis": "predicted",
                     "source_record_ref": f"admet_ai_{endpoint}_{key[:16]}",
                     "conditions": provenance(endpoint, smiles, record, percentile)}],
            records=[{"endpoint": endpoint, "canonical_smiles": smiles, "smiles_sha256": key,
                      "predictor": record.get("predictor") or {}}],
            data_version=version, upstream_refs=[f"{PACKAGE_DISTRIBUTION}:{endpoint}:{key[:16]}", spec["reference"]])


def provenance(endpoint: str, smiles: str, record: dict[str, Any], percentile: float | None) -> dict[str, Any]:
    """What a reader needs to check one predicted number: the predictor, the endpoint, the model
    and the dataset behind it, and the structure it was predicted from."""
    spec = ENDPOINTS[endpoint]
    predictor = record.get("predictor") or {}
    return {"predictor_package": PACKAGE_DISTRIBUTION, "predictor_version": predictor.get("version"),
            "panel_version": PANEL_VERSION, "endpoint": endpoint, "endpoint_name": spec["name"],
            "endpoint_category": spec["category"], "task_type": spec["task_type"],
            "model": spec["model"], "training_dataset": spec["training_dataset"],
            "training_rows": spec["training_rows"], "holdout_metric": spec["metric"] or None,
            "species": spec["species"], "decision_boundary": spec["decision_boundary"],
            "unit": spec["unit"], "unit_as_package_reports_it": spec["package_units"],
            "reference": spec["reference"], "canonical_smiles": smiles, "smiles_sha256": digest(smiles),
            PERCENTILE_LABEL: percentile, "model_ensembles": predictor.get("num_ensembles"),
            "device": predictor.get("device")}


# --- batch precompute -------------------------------------------------------------------------

def warm_universe(universe_file: str | Path, *, structure_file: str | Path | None = None,
                  cache_dir: str | Path | None = None, python: str | Path | None = None,
                  chunk_size: int = 256, limit: int = 0,
                  progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Precompute the panel for every structure of one universe, so a sweep reads files.

    One subprocess for the whole universe: the ensembles load once, and the structures are scored
    in chunks whose rows are written as they arrive, so an interrupted run resumes where it stopped.
    """
    index = StructureIndex(universe_file, structure_file)
    cache = PanelCache(cache_dir, python=python, chunk_size=chunk_size)
    structures = index.structures()
    if limit:
        structures = structures[:limit]
    report = cache.warm(structures, progress=progress)
    return {"universe_file": str(index.universe_file), "structure_file": str(index.structure_file),
            **index.coverage(), **report}


def check(universe_file: str | Path | None = None, *, structure_file: str | Path | None = None,
          cache_dir: str | Path | None = None, python: str | Path | None = None) -> dict[str, Any]:
    """What this route can and cannot do here, without loading the predictor."""
    found = interpreter(python)
    report: dict[str, Any] = {"panel_version": PANEL_VERSION, "endpoints": len(ENDPOINTS),
                              "classifiers": len(CLASSIFIERS), "regressions": len(REGRESSIONS),
                              "interpreter": found, "interpreters_tried": candidates(python),
                              "worker": str(WORKER), "worker_present": WORKER.exists(),
                              "cache_dir": str(PanelCache(cache_dir, python=python).root),
                              "available": bool(found)}
    if universe_file:
        index = StructureIndex(universe_file, structure_file)
        report["universe_file"] = str(index.universe_file)
        report["structure_file"] = str(index.structure_file)
        report["structure_file_present"] = index.structure_file.exists()
        if report["structure_file_present"]:
            try:
                report.update(index.coverage())
                cache = PanelCache(cache_dir, python=python)
                report["cached"] = sum(1 for s in index.structures() if cache.stored(s) is not None)
            except ToolError as error:
                report["problem"] = str(error)
    return report
