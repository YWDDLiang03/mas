# `mas` Multi-Agent Drug Screening System: Acceptance Final Goal, Technical Audit & System Remediation Blueprint

> **FIREWALL & SECURITY CLASSIFICATION NOTICE**
> * **Sections 1–5 & Appendix (Cleared for Agent & External Reviewer Distribution)**: Safe to share with your local coding agent and external reviewers. Contains zero ground-truth leakage of the sealed 11 Critical Quality Attributes (CQAs).
> * **Section 6 (STRICTLY SEALED — Coordinator & Isolated Evaluator Only)**: Contains the unblinded 11 CQAs extracted from Figure 1A(d) of the reference manuscript (`CELL-正文.pdf`) and the post-freeze evaluation rubric. **DO NOT feed Section 6 into the coding agent's context or commit it to the repository prior to freezing the derived criteria.**

---

## 1. The North Star: Acceptance Final Goal & Methodological Bar

Every architectural decision, bug fix, and evaluation protocol in `mas` is governed by a single overarching **Acceptance Final Goal**.

### 1.1 Core Methods Claim (Reconstruction, Not De Novo Discovery)
* **What We Are NOT Claiming**: We are not claiming to discover **surufatinib** de novo; it is already an approved drug and its multi-kinase target profile is published in the literature.
* **What We ARE Claiming (The Methods Claim)**: We claim that an autonomous multi-agent system can **reconstruct the scientific reasoning** that leads to surufatinib—starting strictly from a high-level task statement, primary scientific literature, and public bioactivity databases—with **every quantitative threshold traceable to a verbatim quoted source**, and with the **entire derivation lineage auditable afterward**.
* **What Is Being Built**: An agentic system that takes a task statement and produces a **reasoned, sourced, ranked answer**. It autonomously searches the literature, proposes candidate screening criteria with quantitative thresholds drawn from quoted passages, prunes and consolidates them via deduplication, semantic merging, and a proposer/critic debate, and screens a candidate compound universe to output a ranked list annotated with explicit **measurement coverage** and **epistemic uncertainty**.
* **Zero Hard-Coding Invariant**: The screening criteria are **autonomously derived, not supplied**. Nothing about the specific drug case (surufatinib) is hard-coded into the prompts, scoring functions, or registry rules. Where experimental measurement is absent in public databases, the system explicitly reports absence; it does not impute or predict missing bioactivities.

### 1.2 The Bar `mas` Must Clear (Reference Baseline vs. `mas`)
To prove its methodological value, `mas` must clear a substantially higher explanatory and evidentiary bar than the computational pipeline used in the original reference study:

| Dimension | Original Reference Pipeline (`CELL-正文.pdf`)[cite: 3, 4, 5] | `mas` Acceptance Target (The Higher Bar) |
| :--- | :--- | :--- |
| **Target Input** | Literature-selected 5 TME receptors: `CSF1R`, `VEGFR1` (`FLT1`), `VEGFR2` (`KDR`), `VEGFR3` (`FLT4`), and `FGFR1`[cite: 2, 4]. | Same 5 receptors provided only as the high-level task statement (`CSF1R`, `VEGFR1/2/3`, `FGFR1`). |
| **Candidate Universe** | 3,171 FDA-approved or Phase-III clinical compounds. | ~3,177 approved and Phase-III clinical compounds. |
| **Stage 1 Target Filtering** | Black-box deep learning DTI predictor (**CDES**: ChemBERTa + GCN for SMILES, ESM2 + CNN for proteins, bidirectional cross-attention) trained on ~1M pairs[cite: 3, 4]; filters 3,171 $\rightarrow$ 140 compounds via an unsourced probability cutoff (`Probability > 0.9` on all 5 targets). | **Autonomous Literature Derivation + Public Experimental Bioactivity Lookup**: Derives quantitative potency thresholds ($K_i, K_d, \text{IC}_{50}$) traced to verbatim literature quotes and evaluates experimental records from ChEMBL and IUPHAR without black-box DTI imputation. |
| **Stage 2 Pharmacological Gate** | Binary "Pass/Fail" hard gate across **11 CQAs** (Oral Bioavailability, Metabolic Stability, Toxicological Safety) using unsourced classifier probability cutoffs (`> 0.5` or `< 0.5`), reducing 140 $\rightarrow$ 1 compound (Surufatinib). | **Auditable Proposer/Critic Derivation & Continuous Uncertainty-Aware Ranking**: Derives druggability, PK, and safety criteria from literature quotes, consolidates them via deduplication/merge/debate, and ranks all candidates with per-compound reasons, coverage, and uncertainty. |
| **Explainability & Auditability** | **No sourced thresholds, no per-compound failure reasons, no continuous ranking, and no literature derivation loop**[cite: 4, 5]. | **Every threshold traced to a quoted passage; full per-compound audit trail; explicit coverage and uncertainty reporting.** |

### 1.3 How We Will Know It Worked: The Two One-Shot Acceptance Measurements
Validation rests on **two strictly one-shot measurements** executed on the single acceptance benchmark case (five receptors: `CSF1R`, `VEGFR1/2/3`, `FGFR1` across ~3,177 approved and Phase-III compounds):

1. **Measurement 1 — Criteria Recovery (Primary Acceptance Test)**:
   * *Question*: Do the screening criteria autonomously derived and frozen by the agent match the **11 Critical Quality Attributes (CQAs)** used by the original authors?
   * *Reporting Format*: Evaluated by an isolated evaluator after criteria freeze and categorized as **`Exact` / `Near-Equivalent` / `Missed` / `Extra`**.
   * *Why Primary*: Autonomous criteria generation from primary literature is the agent's core methodological competence.
2. **Measurement 2 — Rank of the Known Answer (Secondary Acceptance Test)**:
   * *Question*: Does ranking the ~3,177-compound universe under the autonomously derived criteria place **surufatinib in the Top 5**?

### 1.4 Strict One-Shot Firewall & Explicit Falsification Conditions
Both validation measurements are deliberately **one-shot**:
* **The CQA Firewall**: The 11-CQA ground-truth list is sealed—held outside the repository and outside both the agent's and the coordinator's operational context—and is opened **once**, after the derived criteria are frozen, by an isolated evaluator. If the 11 CQAs were visible during derivation, criteria recovery would measure copying rather than autonomous scientific derivation.
* **The Ranking Firewall**: A criterion or scoring rule adjusted because it improves surufatinib's ranking position is not valid evidence about the agent's capability.
* **Proven Enforcement in Practice (§7 Rejection)**: One candidate modification (allowing non-human orthologue or cell-based potency measurements to count toward human target criteria) was explicitly rejected on this exact ground: empirical testing showed it improved the score of only **1 out of 34 evaluated compounds—surufatinib and no other**. Rather than being quietly dropped, this rejection is permanently documented in **§7 of `design_audit/situation_report.md`** as proof of firewall integrity.

> **FALSIFICATION CONDITIONS (What Would Falsify the Claim)**
> The methodological claim of `mas` is **falsified**—regardless of how high surufatinib ranks in the final output—if **any** of the following occur:
> 1. **Target-Directed Tuning**: Surufatinib ranks high (Top 5) *only* after criteria, weights, or aggregation rules are selectively adjusted toward it.
> 2. **CQA Contamination**: Derived criteria match the 11 CQAs *only* after the sealed CQA list has been seen or leaked into prompts/code.
> 3. **Unsourced Thresholds**: Quantitative thresholds in the active registry cannot be traced back to verbatim quoted passages in primary literature.

---

## 2. Candid Diagnosis of Current System State (`situation_report.md` Audit)

Before freezing the pipeline for the one-shot acceptance evaluation, an internal audit identified **four critical gaps** in the current implementation that must be remediated using strictly task-agnostic engineering invariants:

| Gap ID | Affected Component | Current Defect & Impact on Acceptance Final Goal |
| :--- | :--- | :--- |
| **Gap 1: Uncommitted Core Artifact** | `var/primary/store` (`.gitignore`) | The **34 currently derived criteria** reside inside `var/primary/store`, which is git-ignored. External domain experts cannot inspect the single most reviewable artifact in the repository to judge whether the derived criteria are scientifically sound. |
| **Gap 2: Incomplete Generator Loop** | `src/mas/core/derivation_stages.py` | The criteria generator has **never executed its full consolidation loop**: across all historical runs, the **merge stage performed zero merges (0 merges)**, and **no proposer/critic debate ever reached a formal conclusion**. Thus, the 34 criteria currently in the store are raw, unmerged outputs of an incomplete pipeline. |
| **Gap 3: "Fail-Open" Authority Vulnerability** | `src/mas/core/criteria.py` & `adjudication.py` | Even though the merge stage executed 0 merges and debates never concluded, the pipeline failed **OPEN** rather than **CLOSED**—allowing 34 unmerged, unadjudicated candidate criteria to enter the active registry and drive `assessor.py` rankings. This grants the Proposer agent implicit authority without Critic oversight. |
| **Gap 4: Four Post-Ranking Data Defects** | `src/mas/core/pool.py` & `assessor.py` | Four distinct data/scoring defects reached a previously published ranking and had to be caught by manual human inspection, even though **every single defect was programmatically detectable from stored data invariants alone**. |

---

## 3. Actionable System Remediation Blueprint (How to Modify the System Now)

To prepare `mas` for the one-shot acceptance freeze without breaching the firewall, execute the following **six task-agnostic engineering modifications**:

### Step 1: Export the Current 34 Criteria Snapshot to Git (Fixes Gap 1)
* **Target File**: Create and commit `design_audit/derived_criteria_v0_unmerged.md`.
* **Implementation**:
  1. Export all 34 criteria currently stored in `var/primary/store`.
  2. Include every attribute for each criterion: `Criterion ID`, `Name`, `Target/Property Category`, `Definition`, `Unit`, `Direction`, `Aggregation Rule`, `Threshold`, `Verbatim Quoted Passage + PMID/DOI Citation`, and `Dispute/Debate Status`.
  3. **Add an Explicit Header Banner**: State clearly that this file represents the **v0 Pre-Remediation Snapshot** (generated while the merge stage performed 0 merges and debates were unconcluded), preserved for audit transparency and ablation comparison against the upcoming post-fix `v1_frozen` criteria set.

### Step 2: Fix the Merge Stage & Debate Termination in `src/mas/core/derivation_stages.py` (Fixes Gap 2)
Why did the pipeline produce 34 criteria when the reference funnel used 5 targets + 11 CQAs? Because a zero-merge pipeline leaves multiple literature quotes for the same receptor or physicochemical property as separate, redundant criteria. When `assessor.py` scores compounds across 34 unmerged criteria, heavily cited targets (such as `VEGFR2` in angiogenesis papers) or redundant Lipinski rules get counted 3–6 times, diluting essential targets like `CSF1R` and `FGFR1`[cite: 2, 4].

* **Modification 2A — Deterministic Ontology Pre-Grouping Before LLM Merging**:
  Group candidate criteria deterministically by `(canonical_target_or_property_id, assay_parameter_family)` prior to invoking the LLM merge agent:
  * **Canonical Target Synonym Resolution (Map to UniProt IDs)**:
    * `CSF1R` / `c-FMS` / `CD115` / `FMS` $\rightarrow$ `P07333`
    * `VEGFR1` / `FLT1` / `FLT-1` $\rightarrow$ `P17948`
    * `VEGFR2` / `KDR` / `FLK1` / `CD309` $\rightarrow$ `P35968`
    * `VEGFR3` / `FLT4` / `FLT-4` $\rightarrow$ `P35916`
    * `FGFR1` / `FLT2` / `bFGFR` $\rightarrow$ `P11362`
  * **Canonical ADMET / Physicochemical Property Buckets**:
    * Group oral absorption rules (`%F`, `HIA`, `Caco-2`, `Lipinski Ro5`, `Veber TPSA`), metabolic stability rules (`t1/2`, `CLint`, `CYP450 inhibition`, `BCRP/P-gp efflux`), and safety/tolerability rules (`hERG`, `MTD`, `Clinical Phase / Approval status`) into canonical ontology buckets.
  * **Intra-Bucket Consolidation**: Whenever $>1$ candidate criterion maps to the same canonical bucket, force a mandatory merge pass that synthesizes a single consolidated criterion while preserving the union of all supporting literature quotes (`source_lineage_list`).
* **Modification 2B — Bounded Proposer/Critic Debate State Machine**:
  * Fix the unconcluded debate bug by enforcing a strict `MAX_DEBATE_ROUNDS = 3` protocol with structured schema outputs:
    * *Round 1 (Proposer)*: Presents the consolidated criterion, quantitative threshold, and verbatim literature quotes.
    * *Round 2 (Critic)*: Challenges biological context (e.g., distinguishing a $10\,\mu\text{M}$ primary HTS hit cutoff from a $\le 100\text{ nM}$ clinical kinase inhibitor requirement), unit validity, or residual redundancy.
    * *Round 3 (Adjudicator)*: Emits a mandatory terminal state token in `{"ACCEPTED", "MODIFIED_AND_ACCEPTED", "MERGED_INTO_CANONICAL", "REJECTED"}`.
  * Any debate failing to emit a terminal state token within 3 rounds must raise a `DebateNonConvergenceError` rather than silently passing.

### Step 3: Enforce a "Fail-Closed" Authority Model in `src/mas/core/criteria.py` & `adjudication.py` (Fixes Gap 3)
* **Modification 3A — Registry Admission Invariants (`criteria.py`)**:
  Prevent any unmerged or unadjudicated criterion from entering the active scoring registry:
  ```python
  def enforce_registry_admission_invariants(
      criteria_batch: list[Criterion],
      pipeline_summary: PipelineExecutionSummary,
  ) -> None:
      # 1. Merge stage must have executed and reduced redundancy
      if not pipeline_summary.merge_stage_completed:
          raise RegistryInvariantError("FAIL-CLOSED: Merge stage did not complete.")
      if pipeline_summary.initial_candidate_count > 15 and pipeline_summary.merges_executed == 0:
          raise RegistryInvariantError(
              f"FAIL-CLOSED: Zero merges executed across {pipeline_summary.initial_candidate_count} "
              "candidates. Halting registry write."
          )

      # 2. Every active criterion must have a concluded debate and traceable quote
      for crit in criteria_batch:
          if crit.adjudication_status not in {"ACCEPTED", "MODIFIED_AND_ACCEPTED"}:
              raise AuthorityViolationError(
                  f"FAIL-CLOSED: Criterion {crit.id} has non-terminal status '{crit.adjudication_status}'. "
                  "Proposer cannot bypass Critic adjudication."
              )
          if not crit.verbatim_quotes or crit.threshold_value is None:
              raise TraceabilityInvariantError(
                  f"FAIL-CLOSED: Criterion {crit.id} lacks a verbatim literature quote or threshold."
              )