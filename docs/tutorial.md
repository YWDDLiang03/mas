# Tutorial: from a research question to an inspectable result

[中文](zh/tutorial.md) · [Install](installation.md) · [Configuration](configuration.md) · [Published example](../examples/oral-multitarget/README.md)

For an executable handoff, start with [one-command agent runs](agent-run.md). For component inputs, code paths and worked modifications, use the [component walkthrough](component-walkthrough.md).

This walkthrough follows the latest completed oral multi-target study: what the researcher enters, what each agent or tool does, and how the result can be inspected. The saved study developed **18 enabled decision rules** and ranked Surufatinib **first among 10 eligible candidates**, score **0.7592592592592593**. Its complete export contains **3,177 candidates**; **1,305 have incomplete admission evidence and 1,862 are excluded for no admission support**.

| Your starting point | Route through this tutorial |
|---|---|
| Fresh clone; inspect the example | Read frozen exports and screenshots. Step 0 needs only Python and makes no model requests. |
| Fresh clone; restore and verify the case | Run `python scripts/agent_run.py replay --bootstrap --workspace var/agent-replay --open`. The optional release capsule restores the latest study and its fixed factual inputs. |
| Restored or original workspace | Inspect the saved study, or create a new study using its library and evidence collection. Steps 1–11 explain the recorded workflow and controls. |
| Fresh clone; conduct your own research | [Install and configure MAS](installation.md), initialize an empty workspace, then follow step 12 with your own CSV data. |

The checkout contains frozen exports. The optional [168 MB capsule](../examples/oral-multitarget/latest/reproduction/README.md) supplies the selected records, facts and caches needed to restore the latest study and prepare a new one. The private source database and credentials are not required for replay. Full texts and model traces remain outside the public capsule. The screenshots were captured on 28 October 2026 in the current Windows workbench, displaying this saved study. [Current screenshots and validation](current-status.md) identify their source version. A new model investigation records its own criteria and results.

## 0. Inspect the published result without starting a workflow

Open [report.md](../examples/oral-multitarget/latest/results/report.md), [task.json](../examples/oral-multitarget/latest/results/task.json), [current candidate CSV](../examples/oral-multitarget/latest/selection/workbench-export.csv), and [surufatinib.json](../examples/oral-multitarget/latest/results/surufatinib.json). The report is the recorded run export; this tutorial supplies the English explanation.

From the repository root, these PowerShell commands use Python's standard library:

```powershell
python -c "import csv,collections; from pathlib import Path; rows=list(csv.DictReader((Path('examples/oral-multitarget/latest/selection')/'workbench-export.csv').open(encoding='utf-8-sig',newline=''))); print('Exported candidates:',len(rows)); print('Selection:',dict(collections.Counter(r['selection_decision'] for r in rows)))"
python -c "import json; from pathlib import Path; r=json.loads((Path('examples/oral-multitarget/latest/results')/'surufatinib.json').read_text(encoding='utf-8'))['matches'][0]; print('Rank:',r['rank'],'Score:',r['score'],'Direct preference coverage:',r['preference_coverage'])"
```

The current export contains **3,177 rows**: `eligible: 10`, `evidence_incomplete: 1305` and `excluded: 1862`. Surufatinib has rank `1`, score `0.7592592592592593` and direct coverage `0.5882352941176471`. The commands read published files.

`selection_decision` matches the current interface. The export also preserves the older `qualification` field for tracing the saved snapshot. [Decision terminology](reference/decision-language.md) explains the current groups and their reasons.

## 1. Open Settings and record the run envelope

After completing [installation and provider configuration](installation.md), start your workspace:

```powershell
.\start_workbench.cmd -Store var\workspace\store -InitializeStore -Models var\workspace\store\models.toml -Config var\workspace\store\mas.toml -AllowOperations
```

This assumes the model/settings files have been copied and configured as described in the installation guide. Open [the workbench](http://127.0.0.1:8769/workbench/) and choose **Settings**. For an existing workspace, supply its actual store/configuration paths.

Set both workload controls to **Medium** (`mid`), the worker limit to **4** and the budget to **USD 10**, then choose **Save settings**. Current labels are **Literature workload** and **Textbook workload**. Settings apply to subsequent work; saved studies retain their original configuration.

| Setting | Latest saved study | New-task example/default |
|---|---:|---:|
| Workload | `mid` | `mid` |
| Concurrent candidates | 4 | 4 |
| Cost cap | **USD 5.50** | **USD 10.00** |
| Evidence mode | Saved evidence only | Select actual saved/uploaded inputs or explicit retrieval |
| Evaluation | Staged screening | Staged screening |

Use 5.50 to repeat the historical envelope with the same local inputs, or choose the budget appropriate to your new investigation. The saved workflow records **USD 4.2101472 estimated model cost**, not a final supplier invoice. Its historical model identity is `deepseek-v4-flash`; configuring a provider for new work does not change that identity.

![Current Settings and saved-study progress](assets/current/settings.jpg)

The screenshot shows future-work settings alongside the completed study's recorded progress. English / 中文 changes interface display; research records and source text retain their recorded language.

## 2. Create the task and state the decision precisely

Choose **New research**, select **Drugs & small molecules**, and use this exact saved objective when following the case:

```text
Identify a single orally administered agent that concurrently engages the tumour-microenvironment targets CSF1R, VEGFR1, VEGFR2, VEGFR3 and FGFR1, with a pharmacological profile suitable for clinical development. Use the saved evidence to develop and refine meaningful research criteria, then screen and rank the recorded compound library.
```

Enter these under **Targets or desired properties**, one per line:

```text
CSF1R
VEGFR1
VEGFR2
VEGFR3
FGFR1
```

Under **Constraints**, enter:

```text
Oral administration is required.
```

Give the study a readable name. Under **Evaluation options**, choose **Use saved or uploaded evidence** and **Staged screening**. With the restored case selected, **Research options → New study with this setup** opens these inputs for editing and starts a fresh criterion set when submitted.

The researcher defines the objective and requirements. The task-normalization role converts them into a versioned English task with explicit target identities and a route constraint. It does not require the researcher to supply the final evaluation criteria. If an essential requirement cannot be bound to a property, unit or conditions, answer the focused clarification presented by the workflow.

![Research objective, targets and oral constraint](assets/current/new-study.jpg)

The screenshot shows the new-study form before submission, with the saved study in the background.

## 3. Bind candidates and evidence separately

In **Candidates & evidence**, select the recorded library of **3,177 compounds** (`universe_chembl.json` in the historical workspace). Select the collection of **3,157 retained facts from 164 sources**, with displayed evidence cutoff **15 October 2026**. The selector shows its name, source count, record count and cutoff; its name and description can be edited for display.

![Candidate library and fixed evidence collection](assets/current/evidence-selection.jpg)

The library fixes who can be evaluated; the collection fixes which saved material informs criterion development. Collection names/descriptions are display metadata. The counts above refer to the fixed input manifest, not all historical tool observations used during candidate assessment.

The new study starts with an empty criterion set and uses **3,021 evidence records** for proposal generation. The source collection contains 3,157 records; 136 candidate-naming records were omitted from this generation subset. Candidate assessment uses the frozen evaluation framework and its bound sources.

After `replay` or `plan`, the restored workbench offers the prepared evidence collection and the recorded candidate library. Choose **Research options → New study with this setup** to start a new task; the prepared collection contains facts and an empty criterion set. The original source task remains in the saved research record, while the new setup points to the portable collection. An empty workspace has no collection until you supply one. For your own inputs, follow step 12.

## 4. Start once and interpret progress

Check the population, evidence mode and cap, then choose **Start research**. This starts the configured workflow and can make paid provider requests. **Save draft** only saves the form.

The controller coordinates task understanding, evidence preparation, discovery, refinement, decision resolution, freezing, screening and publication. Existing-only evidence preparation reuses bound facts; it does not imply another literature search or full-text pass.

The **proposer** writes evidence-backed candidates. The **critic** challenges relevance, definitions, thresholds and counter-evidence. The proposer responds with revisions, and the **adjudicator** handles merges/disputed decisions under the recorded policy. The controller manages transitions and termination; tools supply recorded observations for assessment. Role separation does not by itself mean independent model providers.

Open **Workflow & run details** to see the stages, latest activity, elapsed time and estimated cost. During a running study, batch counts describe the current stage. The saved example below has completed **8/8 stages**; its recorded duration and cost remain visible.

![Current workflow progress for the completed example](assets/current/progress.jpg)

## 5. Follow expansion and three refinement rounds

Open **Criteria** and its stage/history views. The working-item trajectory was:

```text
0 → 6 task requirements → 293 → 504 → 1,192 → 1,917
  → 147 after round 1 → 68 after round 2 → 53 after round 3
```

The six starting requirements are the five target potencies and documented oral administration. Four proposal dimensions then expand target coverage, oral properties, metabolic stability and safety. These counts include registered items plus unregistered working proposals; they are not final scoring-rule counts.

| Stage | What agents do | Count after stage |
|---|---|---:|
| Bind task requirements | Preserve the five targets and oral condition | 6 |
| Propose target coverage | Expand target-related quantities | 293 |
| Propose oral properties | Expand absorption/exposure quantities | 504 |
| Propose metabolic stability | Expand disposition/interaction quantities | 1,192 |
| Propose safety | Expand safety quantities | 1,917 |
| Round 1: filter → distill → refine → merge | Check evidence, clarify quantities, respond to findings, merge duplicates | 1,373 → 1,337 → 291 → 147 |
| Round 2: same sequence | Revise support and consolidate | 109 → 97 → 78 → 68 |
| Round 3: same sequence | Address remaining definitions and duplicates | 63 → 62 → 53 → 53 |

Read each change's reason and parent records. A merge preserves its inputs; removal records why an item was withdrawn. [stages.json](../examples/oral-multitarget/latest/results/stages.json) and [source-cqa-history.json](../examples/oral-multitarget/latest/results/source-cqa-history.json) retain the actual transitions.

![Current criteria and their roles](assets/current/criteria.jpg)

## 6. Open molecular weight and follow its lineage

Search **Molecular weight (Da)** in **Criteria**. Open **Lineage**, version history, the rule and linked evidence. In round 2, six proposals were merged because they measured the same structure-derived molecular weight through the same descriptor route and agreed on the lower-better direction. Da and g/mol describe the same molecular-mass scale here. The merged item retained six parents and median aggregation.

The round-3 critic challenged the counter-evidence support. The proposer added the Lipinski/small-molecule kinase-inhibitor discussion and recorded the interpretation of the **500 Da heuristic**. The working lineage is `cri_01M52KSFQBB9B84Y16HNPGBCM2@v1 → @v2 → @v3`, promoted to `attr_molecular-weight-da@v1` and `rule_molecular-weight-da@v1`.

The final rule is a **threshold preference, molecular weight ≤ 500 Da**. Meeting it gives its comparison point; exceeding it affects this preference but does not independently hard-reject a compound. Two compounds both below 500 Da do not receive different points from this threshold. Surufatinib's recorded value is **480.6 Da**, with a declared derived basis.

This connects six proposals, a merge, a criticism, a revision and an executable rule. The final criterion name alone would conceal the reasoning.

## 7. Freeze rules and inspect admission, scoring and contextual uses

Before screening, **Save evaluation rules** fixes versions, accepted routes, evidence scope and comparison policy. The final saved evaluation uses **`rules@v2`**.

| Final working population | Count | Use |
|---|---:|---|
| Condition requirement | 1 | Documented oral administration is required for admission |
| Required target evidence + scoring | 5 | Each target needs a usable direct observation; potency values also contribute to ranking |
| Other prioritization criteria | 12 | Contribute to ranking |
| Contextual observations | 13 | Support interpretation |
| Registered but deferred | 14 | Unresolved/non-executable rules withheld from evaluation |
| Unregistered pending proposals | 8 | Working items outside the registered evaluation set |

Therefore **53 = 18 enabled decision rules + 13 contextual observations + 22 items not used in this evaluation**, while **31 = 18 + 13** enter assessment. The five unresolved reviews are a subset of deferred items, not five additional criteria. An unresolved logP range proposal is distinct from the enabled continuous RDKit logP preference.

All **six eligibility requirements** are compulsory: the oral condition and direct observations for each of the five targets. The target criteria also supply five of the **17 scoring contributions**, so **6 + 17 − 5 = 18 unique decision rules**. Target potency values are compared during ranking; the saved admission test requires their direct evidence rather than a shared potency cutoff. Predictions retain their basis and remain outside direct-evidence coverage.

## 8. Assess candidates and inspect eligibility

Open **Candidates**. Staged mode checks hard conditions first and records downstream skips after hard failure. The saved run had **no explicit hard failure**, **0 skipped-after-rejection cells**, and **98,487 records = 3,177 × 31**, including unknown states. A complete sweep does not mean every cell has evidence.

For Surufatinib, open **Evidence** and inspect qualification: oral condition **1/1 passed**, required targets **5/5 with direct observations**, and final direct preference coverage **10/17 = 58.82%**.

The selected result is snapshot `_2` (`rules@v2`), with **10/17** direct coverage and the recorded **50% ranking floor**. The [saved overview](../examples/oral-multitarget/latest/results/overview.json) retains earlier evaluations and their links for readers who need the study history.

## 9. Read the leaderboard and explain the score

The Eligible group contains **10 candidates**. Surufatinib ranks **1**, followed by Pazopanib and Axitinib. The remaining candidates comprise **1,305 Evidence incomplete** and **1,862 Excluded**, with no admission support as the exclusion reason. There are **0 confirmed condition-requirement failures** and **0 incomplete candidate assessments**. The frozen export retains its historical `pending` label.

![Current Eligible leaderboard](assets/current/candidates.jpg)

Click Surufatinib's **Score**. The drawer shows each value, basis, comparison point, weight and contribution:

```text
17 applicable preferences; 15 have values; weight 1 each
11.38888888888889 total comparison points ÷ 15 available weight
= 0.7592592592592593
```

Five target preferences, five structural calculations and five predictions supply the 15 values. Human measured oral F% and Tmax remain missing. Missing preferences are excluded from the score average but remain in the applicable coverage denominator: **15 for the score, 17 for coverage**. Predictions may contribute to score while contributing zero to the direct-coverage numerator.

Continuous preferences compare available values among eligible candidates, with better values receiving higher points and ties sharing the average position:

```text
d = [W + (E - 1)/2] / (N - 1)
```

N is the number with values, W counts worse values and E includes all ties, including this candidate. For BRENK, N=10, W=2, E=8, giving **0.611111** comparison points and `0.611111/15` total-score contribution. Threshold preferences use 1 when met and 0 when not met. Expand **Calculation & evidence** for the particular row's calculation.

![Score details and direct evidence coverage](assets/current/score-details.jpg)

## 10. Trace FGFR1 from score to source observations

From the FGFR1 score row choose **Open the evidence for this preference**, or select **FGFR1 curated potency** in candidate **Evidence**. Expand the grouped sources, individual findings and source context.

One linked paper reports **FGFR1 IC50 = 34 nM** at `sec2.1.p1`: *Structural basis and selectivity of sulfatinib binding to FGFR and CSF-1R*, DOI `10.1038/s42004-023-01084-0`. The saved record retains assay/construct details, including ADP-Glo kinase inhibition and the FGFR1 kinase domain, and unknown conditions such as ATP concentration.

| Recorded observation | Value used on the pChEMBL scale |
|---|---:|
| Literature IC50 34 nM | `-log10(34 × 10^-9)` = 7.46852108296 |
| GtoPdb interaction 9769 | 7.28000020981 |
| ChEMBL activity 26132415 | 7.82 |
| ChEMBL activity 26187720 | 7.82 |

Sort the four values and take the median: `(7.46852108296 + 7.82)/2 ≈ 7.64426054148`, the saved assessment. The single 34 nM result and four-record aggregate are different explanation levels. Four records do not by themselves establish four independent experiments; inspect underlying sources and conditions when judging pooling.

![FGFR1 linked evidence](assets/current/evidence-fgfr1.jpg)

[surufatinib.json](../examples/oral-multitarget/latest/results/surufatinib.json) retains these assessment/evidence links for readers without the live workspace.

## 11. Export all candidates and retain the study identity

Choose **Export all candidates**. It covers the full population, not just the visible page or qualified ten. Confirm **3,177 CSV rows** and retain the snapshot reference. Step 0 checks the release's included export.

Keep [manifest.json](../examples/oral-multitarget/latest/results/manifest.json), [validation.json](../examples/oral-multitarget/latest/results/validation.json), [workflow.json](../examples/oral-multitarget/latest/results/workflow.json), [cqa.json](../examples/oral-multitarget/latest/results/cqa.json), and [source-cqa-history.json](../examples/oral-multitarget/latest/results/source-cqa-history.json). Preserve missing/conflicted cells and earlier outcomes when comparing later changes.

The final pin is task `task_01M52CBE5GYPK9F0MCZYBMPH84`, snapshot `lb_task_01M52CBE5GYPK9F0MCZYBMPH84_2`, run `run_01M52Q4VRB00T5Z3QJW08SSV96`.

The [criterion-comparison guide](reference/cqa-comparison.md) explains how to compare quantities, conditions and decision uses with a separate, explicitly synthetic baseline.

## 12. Start your own study with CSV inputs

In an empty workspace choose **Use own data**, then the appropriate type: drugs/small molecules, carriers/formulations, or other candidates. Fill the [candidate template](../config/examples/candidates.csv) and [measurement template](../config/examples/measurements.csv) with actual data; the supplied files contain headers only.

1. Import/paste the **candidate CSV**, map columns and validate. `candidate_id` must be unique. Choose **Use this candidate library**.
2. With that library selected, import the **measurement CSV**. Each row needs `candidate_id`, `property`, `value` and `basis`; numeric observations also need a unit. IDs match exactly, including leading zeros.
3. Declare `basis` as `measured`, `curated`, `predicted`, `simulated` or `derived` according to the observation. Include conditions and source identifiers. Distinct conditions stay distinct. Omit missing observations; observed zero and `false` are valid values.
4. Resolve mapping/validation issues and choose **Use these measurements**. Saving data does not launch research. Modified datasets receive new immutable identities.
5. State the objective, required observations, hard conditions and preferences, including units and relevant conditions. Choose optional saved evidence only if it actually exists in your workspace.
6. Check Settings, evidence/evaluation options and cap, then choose **Start research**. Follow the criterion, qualification, score and evidence checks above with your own recorded counts.

![CSV mapping and validation](assets/current/csv-import.jpg)

This preview uses two explicitly synthetic carrier records to illustrate the format. The preview was checked without importing the rows or starting research.

The generic upload path evaluates exact properties and conditions from your rows. The specialized recorded-drug-library path uses its declared drug capabilities and evidence routes. Your data create a new investigation: report its actual population, criteria, costs and outcomes. A fresh language-model run does not guarantee the historical 1,917 proposals, 53 working items or rank shown here.
