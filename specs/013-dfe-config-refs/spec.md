# Feature Specification: Shared Scenario Config References

**Feature Branch**: `013-dfe-config-refs`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Use config_refs so projects with multiple scenarios can share the same evaluation harness configuration across scenario-specific project configs. For the first use case, use a single shared dfe_readability.yaml file and create DFE audience project configs for General public, Health care provider, and public health SME as project-specific examples that reuse the shared config while varying dataset and task prompt. Those DFE audience names must not be hardcoded into the solution."

## Clarifications

### Session 2026-06-04

- Q: How should conflicts behave when a scenario project locally defines fields also supplied by `config_refs`? -> A: Reject conflicts; validation fails when a scenario project defines local evaluator, judge setup, score, or human review fields also supplied by `config_refs`.
- Q: Which project sections may a shared config provide? -> A: Shared config may provide only evaluators, score definitions, judge setup, and human review policy.
- Q: How should scenario identity be handled? -> A: Scenario identity is optional for normal projects; when present, it must be complete and used for trace, export, and review metadata/filtering. The initial DFE audience configs must include scenario identity.
- Q: What shape should `config_refs` use for the shared evaluation config? -> A: Use a named evaluation reference, such as `config_refs: { evaluation: configs/shared/dfe_readability.yaml }`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Share Evaluation Configuration Across Scenarios (Priority: P1)

As an evaluation maintainer, I want common evaluators, score definitions, judge setup, and human review policy maintained in one shared evaluation configuration so that scenario-specific project configs do not drift from each other.

**Why this priority**: This is the core duplication problem. Without it, each scenario project must repeat the full evaluator list and review setup.

**Independent Test**: Can be tested by defining one shared evaluation configuration and confirming that a scenario project using it validates with the same evaluator, score, judge, and human review behavior as an equivalent single-file project.

**Acceptance Scenarios**:

1. **Given** a shared evaluation configuration and a scenario project that references it, **When** the project is validated, **Then** the project includes the shared evaluator definitions, score definitions, judge setup, and human review policy.
2. **Given** a shared evaluation configuration is updated, **When** each referencing scenario project is validated, **Then** all referencing projects use the updated shared configuration without manually editing each project file.

---

### User Story 2 - Run Scenario-Specific Project Configs (Priority: P2)

As an evaluator, I want separate project configs for each scenario so that each scenario can use its own tuned task prompt and dataset while keeping evaluation criteria consistent.

**Why this priority**: Each scenario may have different generation instructions and source items, but the score comparison should remain consistent across scenarios.

**Independent Test**: Can be tested by validating multiple scenario project configs and confirming that each one has its own dataset identity, task prompt path, and Langfuse dataset name while sharing the same evaluation configuration. The initial examples are the DFE audience configs.

**Acceptance Scenarios**:

1. **Given** a scenario project config, **When** it is validated, **Then** it uses that scenario's configured task prompt and dataset identity.
2. **Given** another scenario project config referencing the same shared evaluation configuration, **When** it is validated, **Then** it uses its own configured task prompt and dataset identity while sharing the same evaluation criteria.
3. **Given** the DFE audience example project configs, **When** they are validated, **Then** each one uses its configured DFE audience task prompt and dataset identity without requiring the audience names to be built into the harness.

---

### User Story 3 - Preserve Scenario Provenance In Runs (Priority: P3)

As a reviewer comparing results in Langfuse, I want traces, datasets, prompts, scores, and review queues to make the scenario visible so that outputs are not mixed across related scenario evaluations.

**Why this priority**: Shared evaluators are useful only if scenario-specific run provenance remains clear for inspection, scoring, export, and review workflows.

**Independent Test**: Can be tested by running or dry-running setup for an audience project and confirming that generated names, metadata, and review artifacts identify the audience while preserving shared score dimensions.

**Acceptance Scenarios**:

1. **Given** two scenario projects share the same evaluation configuration, **When** they are synced or run, **Then** their Langfuse dataset names and trace metadata distinguish the scenarios.
2. **Given** a human review queue is managed for a scenario project, **When** outputs are selected for review, **Then** the queue identity or metadata prevents reviewers from confusing one scenario's outputs with another's.

### Edge Cases

- If a referenced shared evaluation configuration is missing, validation must fail with a clear message that names the missing reference.
- If a referenced shared evaluation configuration omits required evaluation content, validation must fail before any sync or run command mutates Langfuse.
- If a scenario project defines local evaluator, judge setup, score, or human review fields that are also supplied by the shared evaluation configuration, validation must fail with a clear conflict message.
- Shared configuration must not provide scenario-owned fields such as project identity, dataset, task prompt, baseline model, or candidate model definitions.
- If a project defines scenario identity incompletely, validation must fail with a clear message that names the missing scenario fields.
- If a scenario dataset is not yet finalized, validation must identify the missing dataset path rather than silently falling back to another scenario's dataset.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST support scenario-specific project identities that can reuse a shared evaluation configuration. Scenario names and counts MUST be supplied by project configuration, not built into the harness.
- **Dataset**: Feature MUST preserve support for scenario-specific CSV datasets with an `input` column and distinct Langfuse dataset names for each scenario.
- **Langfuse Logging**: Feature MUST preserve trace, observation, score, run metadata, evaluator metadata, baseline reference, prompt identity, and comparison metadata logging while adding or preserving scenario identity in project-level metadata.
- **Prompt and Evaluator Versioning**: Feature MUST track each scenario task prompt version independently while referencing projects reuse the same shared evaluator and score versions.
- **Baseline**: Feature MUST support the existing baseline-first workflow for each scenario project independently.
- **Human Review**: Feature MUST keep Human Annotation Queue support enabled for each scenario project and prevent scenario outputs from being routed ambiguously.

### Functional Requirements

- **FR-001**: The system MUST allow a project config to reference one shared evaluation configuration using `config_refs`.
- **FR-001a**: The `config_refs` field MUST use a named `evaluation` reference for shared evaluation configuration.
- **FR-002**: The shared evaluation configuration MUST be able to provide evaluator definitions, score definitions, judge setup, and human review policy for a referencing project.
- **FR-002a**: The shared evaluation configuration MUST NOT provide scenario-owned project sections such as project identity, dataset, task prompt, baseline model, or candidate model definitions.
- **FR-003**: The system MUST validate a project after resolving its shared configuration references.
- **FR-004**: The system MUST fail validation when a shared configuration reference cannot be found or cannot be read.
- **FR-005**: The system MUST fail validation when the resolved project lacks required evaluator, score, judge setup, dataset, task prompt, baseline, or human review information.
- **FR-006**: The system MUST support any number of scenario project configs that reference a shared evaluation configuration and vary only scenario-specific fields such as project identity, dataset identity, task prompt, and scenario metadata.
- **FR-007**: The initial DFE General public example project config MUST use the existing DFE General public task prompt.
- **FR-008**: The initial DFE Health care provider example project config MUST use the existing DFE Health care provider task prompt.
- **FR-009**: The initial DFE Public health SME example project config MUST use the existing DFE Public health SME task prompt.
- **FR-010**: Each scenario project MUST use a distinct project name and Langfuse dataset name so setup, runs, exports, scores, and review queues remain scenario-scoped.
- **FR-011**: Existing single-file project configs MUST continue to validate and run without requiring `config_refs`.
- **FR-012**: Shared configuration resolution MUST be deterministic so repeated validation of the same project produces the same effective project definition.
- **FR-013**: The shared configuration pattern MUST be usable by future projects with multiple scenarios, not only by the DFE audience use case.
- **FR-014**: The system MUST reject conflicting local and shared evaluation fields rather than applying implicit precedence.
- **FR-015**: Scenario identity MUST be optional for existing and non-scenario projects.
- **FR-016**: When scenario identity is present, the system MUST validate that it includes a scenario group, scenario name, and display label.
- **FR-017**: When scenario identity is present, the system MUST include it in trace metadata, exports, review payloads, and any filtering metadata used for Langfuse inspection.
- **FR-018**: The initial DFE audience project configs MUST define scenario identity.

### Key Entities *(include if feature involves data)*

- **Shared Evaluation Configuration**: The common evaluation package reused by scenario projects. It contains evaluator definitions, score setup, judge setup, and human review policy. For the first use case, this is the DFE readability configuration.
- **Scenario Project Config**: A project definition for one scenario. It identifies the scenario-specific dataset, task prompt, project metadata, baseline, candidates, and shared configuration reference. For the first use case, each scenario is a DFE target audience.
- **Effective Project Config**: The complete project definition after shared references are resolved. This is what validation, sync, run, export, and review workflows consume.
- **Scenario Identity**: The scenario name and slug used to distinguish datasets, prompts, traces, runs, exports, and review artifacts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Multiple scenario project configs validate successfully using a shared evaluation configuration, including the initial DFE audience examples.
- **SC-002**: Shared evaluator and review content is maintained in one shared evaluation configuration instead of being duplicated in all scenario project configs.
- **SC-003**: A change to one shared evaluator definition is reflected in all referencing scenario projects after validation, without editing the scenario project files.
- **SC-004**: Existing non-DFE project configs and existing single-file project configs continue to validate successfully.
- **SC-005**: Each scenario project exposes a distinct project name and Langfuse dataset name so users can identify the scenario in setup output, run metadata, exports, and review workflows.
- **SC-006**: At least one future non-DFE scenario group can be represented by the same shared configuration reference pattern without adding hardcoded scenario names or changing the project config concept.

## Assumptions

- The first target scenario group is DFE, with example audience project configs for General public, Health care provider, and Public health SME.
- Scenario names, counts, and meanings are project data and must not be hardcoded into shared configuration resolution.
- Existing task prompts under `prompts/dfe/` remain the source of truth for audience-specific generation instructions.
- The shared readability evaluators and score dimensions remain the same across the initial DFE audience examples.
- The audience datasets may initially reuse an existing DFE CSV while the final audience-specific datasets are prepared, but the project configs must make scenario-specific dataset identity explicit.
- The first implementation should keep running one project at a time rather than introducing a multi-scenario run command.
