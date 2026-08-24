# AGENTS.md

<!-- Derived by ramp_doctrine (FR-866) from yamlgraph's Scripture and this
repo's inventory; reviewed and landed under FR-867. Witness citations are
this repo's own — see docs/incidents.md. -->


> Draft target: `/Users/sheikki/Documents/src/deviant-daily`. Human review is required before landing.

## Target inventory
- **languages**: `Python`, `YAML`
- **entry_points**: `README.md`, `pyproject.toml`
- **effect_sites**: `.github/workflows/_pipeline.yml`, `.github/workflows/daily.yml`, `docs/authoring-brief-fr862.md`, `logs/roster-smoke.log`, `prompts/corpus.jsonl`, `pyproject.toml`, `tools/da_api.py`, `tools/generate.py`, `tools/ledger.py`, `tools/steps.py`
- **gates**: (none)
- **workflow_triggers**: `.github/workflows/_pipeline.yml: workflow_call`, `.github/workflows/_pipeline.yml: inputs`, `.github/workflows/_pipeline.yml: model`, `.github/workflows/_pipeline.yml: date`, `.github/workflows/daily.yml: workflow_dispatch`, `.github/workflows/daily.yml: schedule`, `.github/workflows/publish-now.yml: workflow_dispatch`, `.github/workflows/publish-now.yml: inputs`, `.github/workflows/publish-now.yml: model`, `.github/workflows/publish-now.yml: options`, `.github/workflows/publish-now.yml: date`

## Traps

### `continuation_bias`

Default mode is text generation → ask before generating; search before implementing; admit uncertainty before producing plausible output

- Applicability: applies
- Rationale: Target inventory centers on content generation via tools/generate.py, prompts/corpus.jsonl, and model-driven workflows, so the continuation-bias trap of emitting plausible text without asking/searching/admitting uncertainty is directly relevant.
- Target evidence: tools/generate.py; prompts/corpus.jsonl; .github/workflows/_pipeline.yml (inputs.model, inputs.date); .github/workflows/publish-now.yml (inputs.model, inputs.options, inputs.date)
- Witness citations:

### `quick_confidence`

When I feel certain → Judge instead

- Applicability: tailor
- Rationale: The trap is relevant to the AI-assisted authoring and publishing pipeline, but the doctrine's generic wording needs to be tied to the generation and publishing flow rather than left as a general cognitive rule.
- Target evidence: tools/generate.py; .github/workflows/publish-now.yml; .github/workflows/_pipeline.yml; docs/authoring-brief-fr862.md
- Witness citations:

### `symptom_patch`

Verify root cause with test before designing fix

- Applicability: tailor
- Rationale: The target includes Python tooling where root-cause verification is relevant, but it has no explicit test suite or CI gates, so the doctrine needs target-specific wording about adding a regression test locally.
- Target evidence: tools/da_api.py, tools/generate.py, tools/ledger.py, tools/steps.py; pyproject.toml; .github/workflows/_pipeline.yml
- Witness citations:

### `intent_drift`

Plan says X, code does Y → re-read thrice

- Applicability: applies
- Rationale: Direct plan-vs-code drift risk exists between the authored brief and the Python tooling.
- Target evidence: docs/authoring-brief-fr862.md; tools/da_api.py; tools/generate.py; tools/ledger.py; tools/steps.py
- Witness citations:

### `false_duplicate`

Syntactic similarity ≠ semantic equivalence

- Applicability: tailor
- Rationale: The doctrine applies to similarly structured workflow inputs that have different trigger semantics in this repository.
- Target evidence: .github/workflows/_pipeline.yml, .github/workflows/daily.yml, .github/workflows/publish-now.yml
- Witness citations:

### `partial_remediation`

Fix all occurrences, not just cited one

- Applicability: tailor
- Rationale: The doctrine addresses fixing all occurrences of an issue, but the inventory does not specify a particular cited issue; it should be phrased around the repository's multiple Python tools and corpus entries.
- Target evidence: tools/da_api.py, tools/generate.py, tools/ledger.py, tools/steps.py, prompts/corpus.jsonl
- Witness citations:

### `plausible_wrong_answer`

Output passes shape check but is semantically wrong → add assertion beyond type validation

- Applicability: tailor
- Rationale: The repository has generation and validation tooling where outputs could pass structural checks but still be semantically wrong; the doctrine applies but should be adapted to the specific generated artifacts and scripts.
- Target evidence: tools/generate.py, tools/ledger.py, tools/steps.py, tools/da_api.py; .github/workflows/_pipeline.yml
- Witness citations:

### `working_system_inertia`

'It works' blocks seeing it clearly → inventory fit, not function

- Applicability: applies
- Rationale: Target shows an existing operational pipeline and smoke artifacts, making the 'it works' inertia trap a live risk for maintainers.
- Target evidence: .github/workflows/daily.yml, .github/workflows/publish-now.yml, logs/roster-smoke.log, tools/da_api.py, tools/generate.py
- Witness citations:

### `architecture_as_diagram`

Three-layer documented but not contracted → violation possible under deadline pressure; enforce at module boundary with import-linter

- Applicability: tailor
- Rationale: The target is a Python project with multiple tool modules and a pyproject.toml, so import-linter can enforce module boundaries, but the inventory does not explicitly document a three-layer architecture, so the entry needs target-specific wording.
- Target evidence: pyproject.toml; tools/da_api.py; tools/generate.py; tools/ledger.py; tools/steps.py; .github/workflows/_pipeline.yml
- Witness citations:

### `instruction_boundary_uncrossed`

Agent's vendor instructions treated as project-aligned → any agent output modifying enforcement infrastructure (CI, pre-commit, Scripture) must be reviewed as adversarial input

- Applicability: applies
- Rationale: The repository contains CI enforcement infrastructure and agent-related prompt/tooling that could modify it, so agent output touching these workflow files must be treated as adversarial.
- Target evidence: .github/workflows/_pipeline.yml, .github/workflows/daily.yml, .github/workflows/publish-now.yml, prompts/corpus.jsonl
- Witness citations:

### `vendor_default_as_help`

Agent frames self-insertion (trailers, deps, telemetry) as courtesy → treat every unprompted artifact change as input from an external system with unknown goals

- Applicability: applies
- Rationale: The repository contains AI/agent-related artifacts (prompts/corpus.jsonl, model inputs in workflows) and dependency files (pyproject.toml) where unprompted self-insertion could occur, matching the doctrine's warning about treating such changes as unknown external input.
- Target evidence: prompts/corpus.jsonl; pyproject.toml; .github/workflows/_pipeline.yml (inputs model/date); .github/workflows/daily.yml (schedule)
- Witness citations:

### `model_as_trusted_peer`

LLM in enforcement pipeline treated as aligned team member → opaque weights, unknown training, potentially misaligned; absence of Co-authored trailer ≠ absence of model influence; enforce adversarial review of enforcement outputs

- Applicability: tailor
- Rationale: The inventory shows model inputs in workflow definitions and model-generated artifacts, so the doctrine's core warning about treating the LLM as a trusted pipeline member applies. However, enforcement and adversarial review are not explicit in the inventory, so the wording must be adapted to the actual pipeline structure and files.
- Target evidence: .github/workflows/_pipeline.yml (inputs.model), .github/workflows/publish-now.yml (inputs.model), prompts/corpus.jsonl, tools/generate.py
- Witness citations:

### `composition_bug`

Every component passes its unit test but the system fails → the defect is in the policy connecting correct parts, not in the parts; trace the full event chain end-to-end before blaming any component

- Applicability: tailor
- Rationale: The idea applies to the target's multi-step pipeline and workflow composition, but the inventory shows no unit-test components or gates, so the wording must be adapted to the actual tools and workflow connections.
- Target evidence: .github/workflows/_pipeline.yml, .github/workflows/daily.yml, .github/workflows/publish-now.yml, tools/steps.py, tools/generate.py, logs/roster-smoke.log
- Witness citations:

### `refactor_orphans_secondary`

Refactoring removes a handler's primary responsibility but silently orphans its secondary responsibility → enumerate ALL responsibilities of a function before deleting, not just the one named in its docstring

- Applicability: tailor
- Rationale: The core refactoring trap applies to Python source files in the target, but the doctrine's handler/listen wording is not directly represented in the inventory, so it needs target-specific phrasing for these tools.
- Target evidence: tools/da_api.py, tools/generate.py, tools/ledger.py, tools/steps.py
- Witness citations:

### `inventory_by_visibility`

Agent evaluates components by current-snapshot legibility (file count, line count, directory depth) instead of historical incident density → importance is proportional to learning cost, not byte count; the FSM bridge was 4% of source but absorbed 26% of diary entries; rank by incidents, not by mass (yamlgraph: 2026-05-31 asset inventory misclassified utils/fsm as Tier 4)

- Applicability: tailor
- Rationale: The target has multiple small Python tools plus logs and a prompt corpus, so the trap of ranking components by file mass rather than incident/log density is relevant; the doctrine’s FSM/yamlgraph example would need target-local wording.
- Target evidence: tools/ledger.py, tools/steps.py, tools/da_api.py, logs/roster-smoke.log, prompts/corpus.jsonl
- Witness citations:

### `growth_as_default`

Assumption that the next commit should add something → mature systems benefit more from pruning claims than planting features; six of ten commits in a productive week were subtractive; the capability registry becomes honest by retiring phantom claims, not by adding implementations

- Applicability: tailor
- Rationale: The growth-default trap is relevant to this repo's feature-brief and roster/ledger workflow, but the cited capability-registry retirement arc is yamlgraph-specific and must be re-expressed for this target.
- Target evidence: docs/authoring-brief-fr862.md, tools/ledger.py, tools/generate.py, logs/roster-smoke.log, .github/workflows/daily.yml
- Witness citations:

### `metric_archaeology_before_reading_output`

Pipeline SCORE is wrong → reflex is to instrument, decompose, and re-measure the score, building rulers to explain the number; but the score is a lossy projection of an artifact sitting in plain text. For LLM stages the artifact is English — there is no cheaper or higher-bandwidth probe than reading it. Building a ruler feels like effort; opening the .md feels too cheap to be the answer. It is the answer. The more sophisticated the measurement, the further it drifts from the one-line cat that ends the investigation

- Applicability: tailor
- Rationale: The core advice to inspect the plain-text artifact before building measurement tooling applies to this repo, but the inventory has no explicit SCORE or metric-gate construct, so the doctrine needs target-specific wording around the actual generated docs and prompts.
- Target evidence: docs/authoring-brief-fr862.md, prompts/corpus.jsonl, logs/roster-smoke.log, .github/workflows/_pipeline.yml, tools/generate.py, tools/ledger.py
- Witness citations:

## Cures

### `ask_before_generate`

Before writing code, ask: who solved this before? (git log, issues, web). What don't I understand? (name it). Is this the right question? (restate it)

- Applicability: applies
- Rationale: The target repository contains Python source files in tools/ where code is written and modified, so the pre-coding research, knowledge-gap naming, and question restatement practice is directly relevant.
- Target evidence: tools/generate.py, tools/da_api.py, tools/ledger.py, tools/steps.py
- Witness citations:

### `three_reads`

surface → deep against code → mechanical simulation

- Applicability: tailor
- Rationale: The three-read technique applies to understanding this Python codebase, but the inventory does not define an existing reading or review process, so it must be phrased around the specific tools and generated-brief pipeline.
- Target evidence: tools/generate.py, tools/ledger.py, tools/steps.py, tools/da_api.py, .github/workflows/_pipeline.yml
- Witness citations:

### `callsite_fix`

Fix at the specific caller, not the shared utility

- Applicability: tailor
- Rationale: The principle applies to the Python tooling, but should reference the actual tools/ modules instead of generic wording.
- Target evidence: tools/generate.py, tools/ledger.py, tools/steps.py, tools/da_api.py
- Witness citations:

### `spec_kill`

Cheapest bug is the one killed in the spec

- Applicability: tailor
- Rationale: The idea applies, but the target does not use the term 'spec'; the authoring brief fills that role and should be named instead.
- Target evidence: docs/authoring-brief-fr862.md; prompts/corpus.jsonl
- Witness citations:

### `changelog_first_diagnostic`

On regression, enumerate changes since last known good before attempting reproduction → git log narrows search space cheaper than any test

- Applicability: tailor
- Rationale: The regression-diagnosis practice applies to this repository's scheduled smoke pipeline, but the wording should reference the repo's actual daily workflow and smoke log rather than a generic git-log instruction.
- Target evidence: .github/workflows/daily.yml, .github/workflows/_pipeline.yml, logs/roster-smoke.log
- Witness citations:

### `read_raw_output_first`

For any LLM/pipeline stage, READ the rawest artifact it emits before you measure it — the first diagnostic for a bad score is cat, not a new metric. Dump N raw samples to disk and read them end-to-end BEFORE computing or decomposing the aggregate; metrics tell you THAT something is wrong, only the artifact tells you WHAT. Mechanize as a forced-observation gate: withhold the aggregate score until K raw samples are acknowledged read, the way TDD forces RED before GREEN. Generalizes to TAXONOMIES: reading the raw rubric rows (inclusion terms) before freezing a cap list killed a self-refuting mechanism in one grep, before any code existed

- Applicability: tailor
- Rationale: The target has raw pipeline artifacts and authoring briefs that support the practice, but no gate currently exists; the doctrine must be restated around the target workflow and log/corpus locations.
- Target evidence: .github/workflows/_pipeline.yml, .github/workflows/daily.yml, logs/roster-smoke.log, prompts/corpus.jsonl, tools/steps.py, tools/ledger.py, docs/authoring-brief-fr862.md
- Witness citations:

### `two_strike_split`

Same guard fires twice for the same failure class after a prompt fix → the abstraction level belongs in CODE; stop rewording. Token-fidelity, verdict semantics, and every other mechanizable level eventually defeats instruction text — treat the model's output as a CLAIM and reconcile it against the source of truth at the boundary (repair within a similarity floor, reject below). Five span shapes and three verdict-inflation families fell to one boundary each; zero prompt patches held

- Applicability: applies
- Rationale: The target inventory shows both a prompt surface and code-side pipeline tools, so a repeated guard failure after a prompt fix maps directly to this doctrine's call to move the fix into code and validate model output at a boundary.
- Target evidence: prompts/corpus.jsonl; tools/steps.py; tools/da_api.py; .github/workflows/_pipeline.yml; docs/authoring-brief-fr862.md
- Witness citations:

### `junk_drawer_cap`

Every taxonomy/enum family has 'true-of-everything' members — rubrics describing the ENCOUNTER or the SYSTEM, not the subject's stated reason (Z10, -48 clarification-of-demand, -69 other-NEC, generic-concern codes). They are detectable A PRIORI (empty or meta inclusion terms) and they eat correct answers with perfect agreement. Cap them in code at the boundary before the model votes: demote-never-drop, evidence preserved, capped entries rank behind genuine claims. Verify each cap candidate against its raw definition first — half of one proposed list turned out genuinely stateable

- Applicability: tailor
- Rationale: The repo contains a model/prompt pipeline and likely taxonomy-style labels in its corpus, so the junk-drawer cap idea fits, but the doctrine's generic taxonomy/enum wording needs to be adapted to this repo's concrete files and workflow inputs.
- Target evidence: prompts/corpus.jsonl; tools/steps.py; tools/generate.py; tools/ledger.py; .github/workflows/_pipeline.yml (model input); .github/workflows/publish-now.yml (model/options)
- Witness citations:

## Questions

### `would_you_use_this`

MOMENT: any proposal. Names the first consumer and first event; an empty trigger list is growth_as_default wearing an architecture costume (killed the watcher-subscription FR in conversation — the cheapest kill rung)

- Applicability: applies
- Rationale: The inventory contains a feature-request authoring brief and explicit workflow trigger definitions, matching the doctrine's focus on proposals naming a first consumer and first event.
- Target evidence: docs/authoring-brief-fr862.md; .github/workflows/_pipeline.yml; .github/workflows/daily.yml; .github/workflows/publish-now.yml
- Witness citations:

### `does_the_platform_already_do_this`

MOMENT: before building any approximation of platform behavior. One bundle/source grep beats a week of prediction (PreCompact existed while we built ceiling models; the docs are a lossy summary of the vendor's intent)

- Applicability: tailor
- Rationale: The check-before-approximating principle applies, but the target has no vendor bundle or platform source; it should be reframed around grepping the existing Python tooling and docs before adding new approximations.
- Target evidence: tools/da_api.py, tools/generate.py, docs/authoring-brief-fr862.md, logs/roster-smoke.log
- Witness citations:

### `who_reads_this_when`

MOMENT: shipping any view, artifact, or signal. Name the rung, the reader, the moment — else it is archived at birth (fr-board's only reader was its own generator)

- Applicability: tailor
- Rationale: The doctrine applies to the repository's artifacts and signals, but its generic 'rung' and 'fr-board' references need to be localized to the concrete artifacts and workflows present here.
- Target evidence: docs/authoring-brief-fr862.md, logs/roster-smoke.log, prompts/corpus.jsonl, .github/workflows/daily.yml, .github/workflows/publish-now.yml
- Witness citations:

### `what_does_the_raw_record_say`

MOMENT: before any metric, model, or verdict. cat beats instrumentation (Scripture: read_raw_output_first — restated here as the question form)

- Applicability: applies
- Rationale: The target inventory includes a raw smoke log and workflow outputs, so the raw-record-first question is directly relevant before assessing generated artifacts or pipeline results.
- Target evidence: logs/roster-smoke.log; .github/workflows/_pipeline.yml; .github/workflows/daily.yml
- Witness citations:

## Local incidents

_Intentionally blank for ramp_incidents to fill._
