# Feature Specification: LLM-as-Judges

**Feature Branch**: `004-llm-as-judges`

**Created**: 2026-05-27

**Status**: Draft

**Input**: User description: "Let's move onto setting up the LLM-as-Judges."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Judge Evaluators for a Project (Priority: P1)

An evaluator harness user can define one or more LLM-as-Judge evaluators for an evaluation project so that each evaluator measures one clear quality dimension and can be run consistently against baseline and candidate outputs.

**Why this priority**: The harness cannot compare model runs meaningfully until project evaluators are defined in a reusable, versioned way.

**Independent Test**: Can be tested by creating a project with a clarity judge evaluator and confirming the project clearly identifies the evaluator name, version, score target, prompt source, judging mode, and required inputs.

**Acceptance Scenarios**:

1. **Given** a project with a dataset and baseline model, **When** the user adds a judge evaluator, **Then** the evaluator definition includes a stable name, version, score target, prompt reference, judging mode, and output schema.
2. **Given** a project with multiple judge evaluators, **When** the project is reviewed, **Then** each evaluator measures one dimension only and has an independent prompt.
3. **Given** a user changes a judge prompt meaningfully, **When** they update the project, **Then** the evaluator version changes so future scores can be distinguished from prior scores.
4. **Given** a model-quality or baseline/candidate comparison evaluator, **When** the evaluator is validated, **Then** blind evaluation is enabled by default and any non-blind evaluator must provide an explicit reason.

---

### User Story 2 - Prepare Langfuse Evaluator Setup (Priority: P2)

An evaluator harness user can use project evaluator definitions to prepare the Langfuse setup needed to run LLM-as-Judge evaluations and write results into the correct score configurations.

**Why this priority**: The project philosophy delegates evaluation execution, scoring, comparison, and dashboards to Langfuse, so users need a clear path from harness project config to Langfuse evaluators and scores.

**Independent Test**: Can be tested by defining a project evaluator and confirming the user can identify the matching Langfuse score config, judge prompt, evaluator inputs, and expected structured result.

**Acceptance Scenarios**:

1. **Given** a judge evaluator definition, **When** the user prepares Langfuse, **Then** the corresponding score config name and score type are known before evaluations run.
2. **Given** an evaluator is harness-managed, **When** score configs are synced, **Then** the user can select the harness-managed score in Langfuse when configuring the evaluator.
3. **Given** an evaluator is user-owned, **When** the project is validated, **Then** the project identifies the externally managed score config to use.
4. **Given** multiple projects emit similarly named model observations, **When** a Langfuse evaluator is configured, **Then** its filters target only the relevant project, project version, evaluator set, run type, and model-output observation.
5. **Given** a Human Annotation Queue is configured for the same evaluator dimension, **When** the automated judge is configured, **Then** both automated and human review workflows use the same Langfuse score config.

---

### User Story 3 - Run Blind and Comparable Judging (Priority: P3)

An evaluator harness user can configure judge prompts and inputs so that automated evaluation is blind to provider identity and comparable across baseline and candidate runs.

**Why this priority**: LLM-as-Judge results are only useful when known bias risks are reduced and the same scoring logic applies to baseline and candidate outputs.

**Independent Test**: Can be tested by reviewing generated judge inputs and confirming they exclude provider/model names, use stable candidate labels, include baseline or ground truth only when the evaluator requires it, and return the same structured schema.

**Acceptance Scenarios**:

1. **Given** a blind judge evaluator, **When** judge inputs are prepared, **Then** provider names, model names, vendor names, and run labels are not exposed to the judge prompt.
2. **Given** a comparison judge evaluator, **When** candidate and baseline outputs are included, **Then** their order is stable or intentionally randomized according to the project policy and the mapping is preserved outside the judge prompt.
3. **Given** a judge evaluator is prepared for Langfuse, **When** its expected result contract is reviewed, **Then** the setup defines score, reasoning, confidence, evaluator version, and score target expectations before Langfuse executes the evaluator.

---

### Edge Cases

- A project defines an evaluator but omits a score target.
- A judge prompt references fields that are not present in the dataset, trace, baseline output, candidate output, or ground truth.
- A judge prompt asks for multiple quality dimensions in one evaluator.
- A baseline run has no available output for an item when a comparison evaluator requires one.
- A dataset item has no ground truth even though an evaluator is configured to require reference output.
- A judge result schema example is malformed, missing a score, outside the allowed score range, or not parseable as structured output.
- A score config with the intended managed name already exists but has an incompatible schema.
- A Human Annotation Queue references a different score config than the LLM-as-Judge evaluator for the same dimension.
- A judge prompt exposes provider or model identity despite the evaluator being configured as blind.
- A Langfuse evaluator filter is too broad and would match traces or observations from another project.
- The model-output observation lacks propagated project metadata required by the evaluator filter.
- A trace contains multiple observations and only one observation should be judged.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST support project-level evaluator definitions that belong to a specific evaluation project and can differ across projects.
- **Dataset**: Feature MUST support existing CSV and Langfuse dataset flows, including optional `ground_truth` values when an evaluator requires reference output.
- **Langfuse Logging**: Feature MUST define how evaluator identity, evaluator version, score target, judging mode, and expected judge result metadata are represented in the Langfuse setup contract for traces, observations, and score configs.
- **Langfuse Evaluator Targeting**: Feature MUST define the evaluator target and filters needed to restrict judging to relevant project traces or observations only.
- **Prompt and Evaluator Versioning**: Feature MUST require judge prompts and evaluator definitions to have explicit versions before scores are produced.
- **Baseline**: Feature MUST support judging baseline runs and candidate runs so baseline scores can serve as the evaluation baseline.
- **Human Review**: Feature MUST preserve Human Annotation Queue workflows for calibration, disputed scores, and manual review of sampled outputs.

### Functional Requirements

- **FR-001**: Users MUST be able to define LLM-as-Judge evaluators as project-level configuration.
- **FR-002**: Each evaluator MUST have a stable evaluator name, evaluator version, score target, prompt reference, judging mode, and output schema.
- **FR-003**: Each evaluator MUST measure exactly one quality dimension.
- **FR-004**: Each evaluator MUST declare whether it evaluates baseline outputs, candidate outputs, or candidate outputs relative to a baseline output.
- **FR-005**: Each evaluator MUST declare whether it requires dataset ground truth, baseline output, candidate output, or only the original input and generated output.
- **FR-006**: Evaluators MUST be blind by default so judge inputs exclude provider names, model names, vendor identity, and run labels.
- **FR-007**: The system MUST validate that blind evaluator prompts do not include known provider or model identity placeholders.
- **FR-007a**: A non-blind evaluator MUST be explicitly configured with `blind: false` and a non-empty `non_blind_reason`; model-quality and baseline/candidate comparison evaluators SHOULD remain blind unless the evaluator is intentionally provider-specific or diagnostic.
- **FR-008**: The system MUST define a structured judge result schema containing at minimum `reasoning`, `score`, and `confidence`.
- **FR-009**: The system MUST validate that configured judge result schemas and examples require scores within the configured score range before users configure Langfuse evaluators.
- **FR-010**: The system MUST define the Langfuse setup contract that associates future judge scores with evaluator name, evaluator version, score config, project, run, trace or observation, dataset item, and prompt version.
- **FR-011**: Users MUST be able to sync or identify Langfuse score configs required by project evaluators before judge runs are configured.
- **FR-012**: Harness-managed score configs MUST use the existing project score prefix and MUST be reused when compatible.
- **FR-013**: The system MUST fail validation when a harness-managed score config exists with the same name but an incompatible schema.
- **FR-013a**: For a given project evaluator dimension, automated LLM-as-Judge evaluators and Human Annotation Queues MUST use the same canonical Langfuse score config.
- **FR-013b**: The system MUST represent score origin with Langfuse's native score `source` field when available, using the harness-normalized values `llm_judge` for Langfuse `EVAL` scores and `human_annotation` for Langfuse `ANNOTATION` scores, rather than separate score configs for the same dimension.
- **FR-014**: Users MUST be able to generate or assemble Langfuse judge prompt text from project evaluator definitions and prompt files.
- **FR-015**: Judge prompts MUST clearly instruct the judge to evaluate only the evaluator's declared dimension.
- **FR-016**: Judge prompts MUST instruct the judge to return structured results matching the declared output schema.
- **FR-017**: The system MUST support baseline evaluation even when no ground truth is present, provided the evaluator does not require ground truth.
- **FR-018**: The system MUST surface a clear validation error when an evaluator requires ground truth or baseline output that is unavailable.
- **FR-019**: The system MUST preserve calibration workflow support by routing sampled or disputed items to Human Annotation Queues.
- **FR-020**: The system MUST document the high-level Langfuse steps needed to configure judge evaluators, select score configs, run evaluations, and compare resulting scores.
- **FR-021**: The system MUST avoid implementing custom dashboards, aggregate scoring engines, or local evaluator execution when Langfuse can own those workflows.
- **FR-022**: Each evaluator definition MUST declare its Langfuse evaluation target, such as the final model-output observation or the full trace when full workflow context is required.
- **FR-023**: The default evaluator target SHOULD be the final model-output observation rather than the full trace.
- **FR-024**: Each evaluator definition MUST include a filter profile that identifies the intended project, project version, evaluator set, environment, run type eligibility, and model-output observation role; provider-specific observation names MAY be used only as additional narrowing filters.
- **FR-025**: The system MUST ensure the model-output observation carries or inherits the project metadata needed by Langfuse evaluator filters.
- **FR-026**: The system MUST validate that evaluator filters cannot match all harness projects by default.
- **FR-027**: The system MUST allow evaluators to opt into baseline-only, candidate-only, or both baseline and candidate run types.
- **FR-028**: The system MUST document the expected Langfuse filter values for each project evaluator so users can reproduce the configuration manually.

### Key Entities *(include if feature involves data)*

- **Judge Evaluator**: A project-owned evaluator definition with name, version, dimension, judging mode, run-type eligibility, blind setting, optional non-blind reason, prompt reference, required inputs, score target, and result schema.
- **Judge Prompt**: Versioned prompt text used by a Langfuse evaluator to produce a structured judgment for one dimension.
- **Judge Result Contract**: Structured output contract expected from Langfuse evaluator execution, containing reasoning, score, confidence, evaluator identity, score target, and trace or observation context.
- **Score Target**: The canonical Langfuse score config that receives automated judge and human annotation scores for a specific evaluator dimension.
- **Evaluator Filter Profile**: The project-owned targeting definition that restricts where a Langfuse evaluator runs, including project identity, project version, evaluator set, run type, environment, and target observation or trace name.
- **Judge Input Package**: The sanitized input values made available to the judge prompt, such as source input, generated output, optional baseline output, optional ground truth, and stable anonymous labels.
- **Calibration Review Item**: A sampled or disputed item selected for human review to calibrate or audit automated judge behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can add one new LLM-as-Judge evaluator to an existing project in under 10 minutes using the documented project pattern.
- **SC-002**: 100% of evaluator definitions fail validation when they lack evaluator version, score target, prompt reference, judging mode, or output schema.
- **SC-003**: 100% of blind judge input packages exclude provider and model identity fields.
- **SC-004**: 100% of configured judge result schemas and examples contain reasoning, score, confidence, evaluator version, and score target.
- **SC-005**: Users can identify the Langfuse score config for every project evaluator before running automated evaluation.
- **SC-006**: Baseline and candidate runs can be evaluated with the same evaluator definition and compared by their resulting scores.
- **SC-007**: At least 5% of judged items can be routed to human review for calibration when the project review policy enables sampling.
- **SC-008**: 100% of evaluator definitions produce a concrete filter profile before they are considered ready for Langfuse setup.
- **SC-009**: 100% of model-output observations used for judging expose the project metadata required by the evaluator filter profile.
- **SC-010**: 100% of evaluator dimensions use one shared score config for both automated judge scores and human annotation scores.

## Assumptions

- Langfuse remains the system of record for evaluator execution, score storage, dashboards, comparison, and trace inspection.
- The harness focuses on project configuration, validation, prompt assets, score config synchronization, trace metadata, and documentation needed to configure Langfuse evaluators.
- Judge prompts are project assets and can differ between projects.
- The first evaluator dimension remains clarity for the rewrite-quality project, but the feature must support future projects and dimensions.
- Existing harness-managed score config naming rules remain in force.
- Existing Human Annotation Queue support is reused for calibration rather than creating a separate local review system.
- Detailed Langfuse evaluator automation may be phased; the MVP must clearly track what can be automated later.
- The first supported target for automated judges is the final model-output observation identified by `observation_role=model_output` and project metadata. The current Azure/OpenAI implementation emits this observation with the provider-specific name `OpenAI-generation`; trace-level judging remains available only when an evaluator explicitly requires full workflow context.
