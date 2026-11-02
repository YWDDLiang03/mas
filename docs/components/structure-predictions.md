# Structure predictions alongside a saved evaluation

[Components](README.md) · [Domain adapters](domain-adapters.md) · [Candidate assessment](assessment-and-qualification.md)

The [target-driven workflow](../target-workflow.md) explains the optional switch in Settings and study setup. New drug studies default to CDES off. When enabled, the workflow pins a selected result collection and adds a target-analysis stage after screening. Candidate observations and ranking values are taken from the new study's own snapshot.

The **CDES analysis** page connects supplied compound–target predictions to a completed study. It presents experimental potency, interaction predictions and the saved overall evaluation together. A prediction collection belongs to one task and one evaluation snapshot.

## Import a supplied result collection

Use [the importer](../../scripts/import_cdes_results.py) with a saved case export, its candidate library, its structure index and a supplied result archive:

```powershell
python scripts/import_cdes_results.py --archive PATH_TO_RESULTS.zip --case PATH_TO_CASE_EXPORT --universe PATH_TO_UNIVERSE.json --structures PATH_TO_SMILES.json --workspace var/my-study --target TARGET_LABEL=UNIPROT_ACCESSION --export var/my-study/structure-data.zip
```

Repeat `--target` for each target. Target labels correspond to the supplied `<label>_screen_results.csv` files. The current import format expects columns `Drug ChEMBL ID`, `Drug Name`, `SMILES`, `Gene Name`, `Protein`, `y_preds` and `y_scores`, plus the supplied `ADMET_evaluation.xlsx` workbook. The case export follows the source-data format used by the repository's saved example.

The importer checks candidate uniqueness within each target, consistent structures across targets, finite scores in [0,1] and agreement between the declared target and each table. Exact identifiers with identical stored SMILES establish a correspondence. A unique exact structure can establish a correspondence across identifiers. Different structure strings under the same identifier remain available for review; the importer performs no chemical standardization. Workbook associations use exact drug names because that sheet has no chemical identifiers.

The collection retains original files, raw score strings, source rows, protein sequences and hashes. It also retains the case tables that support the linked measurements and evaluation. Its location is `WORKSPACE/structure-results/TASK/INTEGRATION/`; the original study journal is read-only during this operation.

## Read and export

The page offers eligible candidates, matched study candidates, the full prediction library, unresolved correspondences and the supplied ADMET analysis. Search is applied before pagination. Candidate details link to the relevant experimental observations and to the original prediction rows.

| Resource | Contents |
|---|---|
| `GET /api/workbench/tasks/{task}/structure` | Collection summary and paginated comparison; accepts `snapshot`, `cohort`, `q`, `page`, `page_size` |
| `GET /api/workbench/tasks/{task}/structure/{candidate}` | Candidate profile, source positions and protein inputs |
| `GET /api/workbench/tasks/{task}/structure-export.csv` | Complete `predictions`, `mapping`, `original-only` or `admet` table selected with `kind` |
| `GET /api/workbench/tasks/{task}/structure-export.json` | Complete linked dataset |
| `GET /api/workbench/tasks/{task}/structure-export.zip` | JSON, CSV tables, original result files and linked case sources |
| `POST /api/workbench/tasks/{task}/structure-module` | Persist the completed study's CDES analysis-view switch using an `enabled` Boolean |

An incompatible snapshot returns `different_evaluation` with the linked snapshot identifier. The user can open that evaluation. Classification scores and measured potency retain their own scales. The saved eligibility, composite score and rank are displayed alongside the interaction profile.

## Deployment boundary

[`cdes.py`](../../src/mas/adapters/predict/cdes.py) defines `PairRequest` and `InteractionScorer.predict_pairs()`:

```python
PairRequest(candidate_id, smiles, target_uniprot, protein_sequence)
```

The response contains per-pair `results` and `errors`. Results carry the value, scale, determination basis and source; failures identify the pair and reason. `SavedResultScorer` currently reads the imported collection and checks exact compound structure and protein sequence. Collection storage and snapshot binding are shared by the workflow and workbench. A deployed model can implement the same interface later. Inference deployment and prediction-assisted changes to primary scoring remain subsequent work.

Verification covers source identity, partial request failure, snapshot isolation, full export and changed-data detection. The implementation uses Python's standard library for import and reading.
