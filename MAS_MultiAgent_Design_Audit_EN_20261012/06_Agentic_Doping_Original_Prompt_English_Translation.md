# Original Agentic Doping v1 Request: English Translation

Source: the original Chinese project request supplied by the user in this conversation. Translation prepared on 12 October 2026.

This is a historical reference for the intended interaction style, human intervention, progress visibility, proposal-review collaboration, and feedback cycle. The requests below describe desired capabilities; they do not establish that those capabilities were implemented or scientifically validated. The original materials-science scope and working directory are preserved for fidelity. They do not replace the current biomedical task or its `design_audit/` output directory. The current assignment requires detailed architecture and design documents only, with no implementation code.

## Translated original request

I want to build a chemistry agent system that can automatically generate doping candidates according to a user's requirements. For example, the user might provide a parent composition such as CsPbI3, or ask for unconditional generation. The model should be able to select a parent cell itself or use the supplied parent, propose elemental substitutions at specified fractions, such as replacing 0.05 of the Pb sites with Mn, build a supercell, use Python tools such as `doped` for preliminary computational validation, and then screen and score the resulting candidates.

The interface should initially be designed as a locally hosted, browser-based UI. Functionally, the system should investigate the literature automatically to determine the possible effects and trends associated with candidate dopants, whether an element is a plausible candidate, and whether a proposed idea is reasonable.

There should be an unconditional doping mode. When the user does not supply detailed requirements, the model should find a parent structure, propose a doping scheme, calculate the relevant properties, and return results. There should also be a leaderboard showing which doping candidates have been evaluated, their results, and their rankings. Users should be able to filter the results, for example by parent material or by the elements involved.

Users should be able to inspect a preliminary structural model of a proposed candidate, including a visualization of the generated CIF structure. After choosing the parent, the workflow should let them specify how many dopant elements to use and the fraction of each, construct the supercell, select which host atoms and sites to replace, and refine or relax the resulting structure.

Similarly, a conditional mode should support a user-provided parent material and choices concerning which elements to introduce and how many dopant elements to use. Both conditional and unconditional workflows must support human-in-the-loop intervention throughout. Users should be able to suggest or edit intermediate proposals, such as removing an element or changing a doping fraction. Analyze the specific interventions a human is likely to need.

Based on the proposed dopant elements and fractions, the system should attempt to construct a supercell and use appropriate tools for preliminary calculations of properties such as formation energy, defect formation energy, effective mass, and energy above hull.

The architecture must include human-in-the-loop support, including explicit interface locations for manually filtering candidates or proposing doping options. It should also support self-improvement and a data feedback cycle: existing or subsequently obtained DFT results, which have the second-highest priority, and wet-lab experimental data and conclusions should be usable to improve the agentic system. There must therefore be a place to receive, store, and analyze DFT and wet-lab results supplied by humans. These inputs may be text, local file paths, or uploaded files.

The reference materials are available for you to consult. I think the system should include an ARIS-like dual-agent collaboration mechanism: one agent proposes a scheme, while another supervises and evaluates it. The two agents should communicate and collaborate through files, progressively improving the feasibility of candidate proposals.

The system should also have literature retrieval and paper-reading capabilities like those in TASTE and iDeer, together with idea-generation capabilities specialized for doping. It should support both unconstrained generation of doping ideas and generation conditioned on supplied requirements. Because this is a chemistry-related project, include retrieval from ChemRxiv as well as journal literature. The reading workflow should support an initial title-based screening, a second screening using titles and abstracts, and close reading of the full text. Full-text reading should identify the reported material properties and analyze structural composition, doping fractions, physical properties, and reusable lessons.

At every step, humans should be able to see how the task is progressing. Provide progress bars similar to those in TASTE. Users do not need to see the model's raw responses; they need to see progress for the current task and for the overall task.

You can also inspect earlier projects for reusable ideas, including `D:\codex_work\ai4s\doping` and `D:\codex_work\ai4s\dataset`.

Your current task is to research and analyze what needs to be added to this plan and what weaknesses need improvement. Decompose the requested work into many small tasks, and analyze and refine each task. Identify existing open-source tools or Python packages that can support the project and explain the purpose of each. Then analyze which functions would require additional model training, what each model would need to do, what support it would require, the proposed technical approach, and the data needed to train and evaluate it.

Your current working directory is `D:\codex_work\ai4s\agentic_doping\claude_suggestion`. Create the following files:

- `suggestions.md`: weaknesses in the current plan and recommended improvements.
- `task.md`: a decomposition of the work into tasks.
- `module.md`: the independent modules you believe the system requires.
- `resources.md`: additional resources and models that need to be supplied or developed.
- `tools.md`: open-source tools and packages that could be used in the project, with detailed explanations of what each tool does, why it is useful, and how to use it.

Conduct additional research into related agentic systems and doping research to identify further lessons and possible improvements.

## How to use this reference in the current task

Transfer the intent of the local research workbench, visible task progress, inspectable candidates, explicit human interventions, proposal-review records, and feedback-driven method improvement. Design their biomedical equivalents: flexible research inputs, evidence and CQA inspection, candidate leaderboards, per-round changes, and expert decisions.

The current task has additional requirements: CDES is optional; screening rounds are adaptive rather than mandatory; the current drug and targets are one case; the leaderboard uses conservative evidence-based admission; and the next agent must conduct a current agent/RSI/self-evolving literature investigation. Follow the current main prompt where requirements differ. Neither this translation nor the available source excerpts authorize implementation during the architecture-design stage.
