# Feature Specification: Langfuse Judge Setup

**Feature Branch**: `008-langfuse-judge-setup`

**Created**: 2026-05-27

**Status**: Draft

**Input**: User description: "let's implement backlog 008 - enabling the harness to setup the llm-as-judge directly in langfuse"

## Clarifications

### Session 2026-05-27

- Q: Which harness-managed evaluator fields may be updated in place? -> A: Allow in-place updates only for operational fields like filters, sampling, variable mappings, catalog reference metadata, and enabled state. Prompt version, evaluator version, score target, source type, target type, or scoring semantics changes require a new evaluator identity. When creating a new evaluator version, the harness should inactivate older harness-managed versions and add rename/comment context where Langfuse supports it safely.
- Q: Should newly created Langfuse judge evaluators be active immediately after setup? -> A: New evaluators are active immediately after setup apply. Preview remains non-mutating and reports that apply will activate them.
- Q: How should multi-evaluator setup handle partial failures? -> A: Apply evaluators independently. Successful evaluator changes remain in place, failed evaluators are reported with remediation, and no rollback or deletes are attempted.
- Q: What sampling behavior should apply when no evaluator sampling policy is configured? -> A: Default to evaluating 100% of matching observations unless the project config specifies a different sampling policy. Preview and apply summaries must show the effective sampling policy.
- Q: How should the harness prove a remote evaluator is harness-managed before update or inactivation? -> A: Require a stored local binding plus remote compatibility checks. Use evaluator display name as a lookup hint, and use remote evaluator metadata only if Langfuse exposes it.
- Q: Should evaluator setup backfill historical observations by default? -> A: Evaluate only newly ingested matching observations by default. Historical backfill requires explicit project configuration and is applied only when Langfuse supports it for the evaluator target.
- Q: How should setup choose the Langfuse judge model or LLM connection? -> A: Allow a project-level default judge model or LLM connection, with evaluator-level override. Setup is blocked when neither is available.
- Q: Where should evaluator binding records be stored? -> A: Store non-secret evaluator binding records in the local repository, keyed by project/evaluator identity and remote Langfuse evaluator ID.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create or Update Managed Langfuse Judge Evaluators (Priority: P1)

An evaluator harness user can apply a validated project configuration and have the harness create, reuse, or safely update the matching harness-managed Langfuse LLM-as-Judge evaluator setup directly in the user's Langfuse project.

**Why this priority**: Users currently receive rendered setup guidance but still need to manually configure evaluators. Direct setup removes the most error-prone step while preserving Langfuse as the owner of evaluator execution and scoring.

**Independent Test**: Can be tested by running setup for a project with one valid judge evaluator and confirming the user receives a clear result showing the Langfuse evaluator was created, reused, or safely updated with the expected target, score config, filter profile, prompt, and variable mappings.

**Acceptance Scenarios**:

1. **Given** a valid project with one harness-managed LLM-as-Judge evaluator, **When** the user requests Langfuse judge setup, **Then** the harness creates or resolves a matching Langfuse evaluator and reports its identity.
2. **Given** a matching Langfuse evaluator already exists and is compatible with the project definition, **When** the user requests setup again, **Then** the harness reuses it without creating a duplicate.
3. **Given** a harness-managed Langfuse evaluator exists and differs from the project definition in an update-safe field, **When** the user applies setup, **Then** the harness updates the evaluator and reports the changed fields.
4. **Given** a user-owned Langfuse evaluator exists but differs in target, filters, score config, prompt, or variable mapping, **When** the user requests setup, **Then** the harness fails with a clear incompatibility report and remediation guidance.
5. **Given** a project defines a new version of a harness-managed evaluator, **When** setup is applied, **Then** the harness creates the new evaluator identity and inactivates older harness-managed versions for the same project, dimension, source type, and target where this can be done safely.
6. **Given** setup creates a new Langfuse judge evaluator, **When** apply completes successfully, **Then** the evaluator is active immediately and the setup result reports that activation.
7. **Given** a project defines multiple judge evaluators, **When** setup applies successfully for some evaluators and fails for others, **Then** successful evaluator changes remain in place and failed evaluators are reported with remediation without rollback or deletion.
8. **Given** a project evaluator does not configure sampling, **When** setup is previewed or applied, **Then** the effective sampling policy is reported as 100% of matching observations.
9. **Given** a project evaluator does not explicitly request historical backfill, **When** setup is applied, **Then** the evaluator applies only to newly ingested matching observations after setup.
10. **Given** a project evaluator explicitly requests historical backfill, **When** Langfuse supports backfill for the selected evaluator target, **Then** setup applies the requested backfill setting and reports it in the setup summary.
11. **Given** a project evaluator explicitly requests historical backfill, **When** Langfuse does not support backfill for the selected evaluator target, **Then** setup blocks that evaluator with remediation instead of silently ignoring the request.
12. **Given** a project defines a default judge model or LLM connection, **When** an evaluator does not override it, **Then** setup uses the project default.
13. **Given** an evaluator defines its own judge model or LLM connection, **When** setup runs, **Then** the evaluator-level setting overrides the project default.
14. **Given** neither project nor evaluator defines a judge model or LLM connection and Langfuse cannot provide one safely, **When** setup runs, **Then** setup blocks that evaluator with remediation.
15. **Given** setup creates or updates a harness-managed evaluator, **When** setup succeeds, **Then** the harness records a non-secret local binding that links the project evaluator identity to the remote Langfuse evaluator ID.
16. **Given** a future setup run finds a remote evaluator with the managed display name but no matching local binding, **When** update or inactivation would be required, **Then** the harness treats it as user-owned unless explicitly configured otherwise.
17. **Given** a project defines multiple judge evaluators, **When** setup completes, **Then** each evaluator is independently created, reused, updated, inactivated, skipped, blocked, or failed and the result identifies per-evaluator status.

---

### User Story 2 - Bind Judge Inputs and Score Targets Safely (Priority: P2)

An evaluator harness user can rely on the harness to map project evaluator inputs to the Langfuse variables and score target needed for automated judging.

**Why this priority**: Automated evaluator creation is only useful if the resulting Langfuse evaluator reads the correct source data and remains comparable with human annotation for the same evaluator dimension.

**Independent Test**: Can be tested by inspecting the setup result and confirming every declared evaluator input is mapped, the evaluator dimension is recorded, and human annotation for the same dimension uses the canonical score config.

**Acceptance Scenarios**:

1. **Given** an evaluator requires input text and generated output, **When** Langfuse setup is applied, **Then** both required values are mapped to Langfuse evaluator variables.
2. **Given** an evaluator requires baseline output or ground truth, **When** those inputs are unavailable for the project, **Then** setup is blocked before any incompatible evaluator is enabled.
3. **Given** a Human Annotation Queue exists for the same evaluator dimension, **When** Langfuse setup is applied, **Then** the harness records the intended canonical score config for calibration while Langfuse automated judge scores remain comparable by evaluator dimension, evaluator name, and score source.
4. **Given** Langfuse supports multiple score value types, **When** the evaluator is configured, **Then** the score target type and judge result contract match the project evaluator definition.
5. **Given** a project evaluator chooses a Langfuse catalog evaluator, **When** setup is applied, **Then** the harness references the selected catalog evaluator and maps project inputs, filters, and score target without requiring custom judge prompt text.
6. **Given** a project evaluator chooses a custom evaluator, **When** setup is applied, **Then** the harness configures the custom prompt, result contract, variable mappings, filters, and score target from the project definition.

---

### User Story 3 - Preview and Audit Planned Langfuse Changes (Priority: P3)

An evaluator harness user can preview planned Langfuse evaluator setup before applying it and can later audit the configured evaluators against the project definition.

**Why this priority**: Direct Langfuse changes need operator confidence, especially in shared projects where evaluator filters or score configs can affect production monitoring cost and score quality.

**Independent Test**: Can be tested by running setup in preview mode and confirming it reports planned creates, reuses, updates, blocked changes, filters, sampling policy, variables, prompts or catalog references, and score targets without modifying Langfuse.

**Acceptance Scenarios**:

1. **Given** a project has valid judge evaluators, **When** the user previews setup, **Then** the harness reports all intended Langfuse evaluator creates, reuses, updates, skips, and blocked changes without applying them.
2. **Given** setup was previously applied, **When** the user audits the project, **Then** the harness reports whether Langfuse evaluator configuration still matches the project definition.
3. **Given** an evaluator filter would match data outside the intended project, **When** preview or apply runs, **Then** setup is blocked with the unsafe filter details.
4. **Given** Langfuse credentials or required project permissions are missing, **When** the user requests setup, **Then** the harness reports the missing access requirement without exposing secrets.

### Edge Cases

- Langfuse service access is unavailable, rate-limited, or returns a partial failure during multi-evaluator setup.
- The Langfuse project has an evaluator with the intended name but a different score target, target type, prompt, or variable mapping.
- The evaluator prompt has changed locally but the evaluator version was not changed.
- Langfuse requires an LLM connection or judge model selection that is missing from the project setup inputs.
- The project uses observation-level judging, but the filter profile lacks `observation_role=model_output` or project identity.
- The evaluator is configured for baseline and candidate runs, but the Langfuse filter would only match one run type.
- A score config exists with the correct name but an incompatible score type or range.
- The requested setup would create duplicate active evaluators for the same project, evaluator version, target, and run types.
- A dry-run preview and the later apply see different remote Langfuse state.
- The evaluator definition uses a user-owned prompt, score config, or evaluator that the harness must not overwrite.
- A harness-managed evaluator exists, but the requested change would alter evaluator identity, historical meaning, score semantics, or ownership.
- A Langfuse catalog evaluator is renamed, removed, unavailable in the user's plan, or no longer compatible with the configured score target.
- A newer harness-managed evaluator version is created while older active versions for the same project, dimension, source type, and target still exist.
- A newly active evaluator has no explicit sampling policy and therefore evaluates all matching observations.
- A project explicitly requests historical backfill for an evaluator target where Langfuse does not support backfill.
- A remote evaluator matches a managed display name but has no corresponding local binding record.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST use project-level evaluator definitions as the source of truth for Langfuse LLM-as-Judge setup.
- **Dataset**: Feature MUST preserve existing CSV and Langfuse dataset workflows; setup MUST verify evaluator-required inputs are available from declared project data or run metadata.
- **Langfuse Logging**: Feature MUST keep Langfuse as the system of record for evaluator execution, evaluator-produced scores, execution traces, score storage, dashboards, and comparisons.
- **Prompt and Evaluator Versioning**: Feature MUST associate each Langfuse evaluator setup with explicit evaluator and prompt versions from the project definition.
- **Baseline**: Feature MUST support setup for evaluators that apply to baseline runs, candidate runs, or both, according to project run-type eligibility.
- **Human Review**: Feature MUST preserve Human Annotation Queue calibration and MUST keep automated judge and human annotation scores comparable for the same evaluator dimension. Human annotation uses the canonical score config; Langfuse LLM-as-Judge scores may use the evaluator name as the score name when the evaluator API does not expose score-config binding.

### Functional Requirements

- **FR-001**: Users MUST be able to request direct Langfuse LLM-as-Judge evaluator setup for a project after project validation succeeds.
- **FR-002**: Users MUST be able to preview planned Langfuse evaluator setup without modifying Langfuse.
- **FR-003**: The system MUST create a Langfuse evaluator when no compatible evaluator exists for the project evaluator name, version, target, score target, prompt, variables, filters, and run-type eligibility.
- **FR-004**: The system MUST reuse an existing Langfuse evaluator when it is compatible with the project evaluator definition.
- **FR-005**: The system MUST safely update an existing harness-managed Langfuse evaluator when ownership is verified and the requested changes preserve evaluator identity, score semantics, and historical auditability.
- **FR-006**: The system MUST reject setup when an existing user-owned Langfuse evaluator with the intended identity is incompatible.
- **FR-007**: The system MUST block evaluator changes that would require deleting, recreating, or silently changing the meaning of historical scores.
- **FR-008**: In-place updates to harness-managed evaluators MUST be limited to operational fields such as filters, sampling, variable mappings, catalog reference metadata, and enabled state.
- **FR-009**: Changes to prompt version, evaluator version, score target, evaluator source type, target type, or scoring semantics MUST require a new evaluator identity.
- **FR-010**: When a new harness-managed evaluator version supersedes older harness-managed versions for the same project, dimension, source type, and target, the system MUST inactivate the older versions where Langfuse supports safe inactivation.
- **FR-011**: When older harness-managed evaluator versions are inactivated, the system SHOULD add rename or comment context indicating the superseding evaluator version where Langfuse supports that safely.
- **FR-012**: The system MUST report per-evaluator setup status as created, reused, updated, inactivated, skipped, blocked, or failed.
- **FR-013**: The system MUST support both Langfuse catalog evaluators and project-defined custom evaluators.
- **FR-014**: For Langfuse catalog evaluators, the system MUST resolve the selected catalog evaluator and bind project filters, variables, score target, run-type eligibility, ownership, and setup metadata.
- **FR-015**: For project-defined custom evaluators, the system MUST configure or reference the custom judge prompt, result contract, variables, filters, score target, run-type eligibility, ownership, and setup metadata.
- **FR-016**: The system MUST distinguish evaluator source type in setup results as Langfuse catalog, custom harness-managed, or user-owned.
- **FR-017**: The system MUST support a project-level default Langfuse judge model or LLM connection for evaluator setup.
- **FR-018**: Evaluator-level judge model or LLM connection settings MUST override the project-level default for that evaluator.
- **FR-019**: Setup MUST block an evaluator when neither evaluator-level nor project-level judge model or LLM connection is available and Langfuse cannot safely provide one.
- **FR-020**: Preview, apply, and audit summaries MUST show the effective judge model or LLM connection for each evaluator.
- **FR-021**: The system MUST use deterministic, slug-safe names for harness-managed Langfuse evaluator resources, consistent with existing harness-managed Langfuse entity naming.
- **FR-022**: Harness-managed evaluator names MUST include the project slug, project version, evaluator dimension, evaluator version, evaluator source type, and target type unless the project provides an explicit managed display name.
- **FR-023**: Harness-managed evaluator names MUST avoid encoding score source such as human annotation versus automated judge, because score origin is represented by Langfuse score source and not by separate score configs.
- **FR-024**: The system MUST store a local evaluator binding for each harness-managed Langfuse evaluator it creates or updates.
- **FR-025**: Before updating or inactivating a remote evaluator, the system MUST verify the local binding and confirm the remote evaluator remains compatible with the project evaluator identity.
- **FR-026**: Managed display names MAY be used as lookup hints, but MUST NOT be the only proof that a remote evaluator is harness-managed.
- **FR-027**: Remote evaluator metadata MAY be used as additional ownership evidence only when Langfuse exposes it for evaluator resources.
- **FR-028**: The system MUST treat evaluators without a matching local binding as user-owned unless the project explicitly configures them as read-only references.
- **FR-029**: Local evaluator bindings MUST be non-secret and safe to store in the repository.
- **FR-030**: Local evaluator bindings MUST be keyed by project identity, project version, evaluator name, evaluator version, evaluator source type, evaluator target type, and remote Langfuse evaluator ID.
- **FR-031**: Preview, apply, and audit summaries MUST report binding status for harness-managed evaluators.
- **FR-032**: The system MUST configure evaluator targets according to the project definition, defaulting to the final model-output observation unless full-trace judging is explicitly required.
- **FR-033**: The system MUST configure evaluator filters that include project identity, project version, evaluator set identity, environment, run type eligibility, and the model-output observation role for observation-level evaluators.
- **FR-034**: The system MUST block setup for evaluator filters that could match all harness projects by default.
- **FR-035**: The system MUST map every declared judge input to a Langfuse evaluator variable before an evaluator can be created, reused, or updated.
- **FR-036**: The system MUST block setup when any required judge input cannot be mapped to available trace, observation, dataset, baseline, candidate, or ground-truth data.
- **FR-037**: The system MUST record the intended canonical Langfuse score config for each evaluator dimension in local evaluator bindings and setup summaries.
- **FR-038**: The system MUST verify that Human Annotation Queue scores for the same dimension use the canonical score config, and MUST report when Langfuse LLM-as-Judge evaluator scores are emitted under the evaluator name instead of a score config.
- **FR-039**: The system MUST verify score type, score range, and result contract compatibility before enabling a Langfuse evaluator.
- **FR-040**: The system MUST configure or reference the judge prompt text and prompt version used by each custom Langfuse evaluator.
- **FR-041**: The system MUST block setup when custom local prompt content changes without a corresponding evaluator or prompt version change.
- **FR-042**: The system MUST support user-owned Langfuse evaluators by resolving and validating them without mutating them.
- **FR-043**: The system MUST avoid deleting Langfuse evaluators, score configs, prompts, traces, scores, or annotation queues as part of this feature.
- **FR-044**: The system MUST provide clear remediation guidance when setup is blocked by incompatible remote Langfuse state.
- **FR-045**: The system MUST handle missing credentials, insufficient permissions, Langfuse service unavailability, and rate limits with actionable errors that do not expose secrets.
- **FR-046**: Newly created Langfuse judge evaluators MUST be active immediately after successful setup apply.
- **FR-047**: Preview mode MUST remain non-mutating and MUST report that successful apply will activate newly created evaluators.
- **FR-048**: Multi-evaluator setup MUST apply each evaluator independently.
- **FR-049**: When one evaluator fails during apply, successful evaluator changes already applied MUST remain in place.
- **FR-050**: The system MUST NOT roll back, delete, or destructively mutate successful evaluator changes because another evaluator failed.
- **FR-051**: The setup result MUST clearly distinguish full success, partial success, and full failure.
- **FR-052**: If an evaluator does not configure a sampling policy, the system MUST default the effective sampling policy to 100% of matching observations.
- **FR-053**: Preview, apply, and audit summaries MUST show the effective sampling policy for each evaluator.
- **FR-054**: If an evaluator does not explicitly request historical backfill, the system MUST configure the evaluator for newly ingested matching observations only.
- **FR-055**: Historical backfill MUST be opt-in through explicit project configuration.
- **FR-056**: When historical backfill is explicitly requested, the system MUST apply it only if Langfuse supports backfill for the selected evaluator target.
- **FR-057**: When historical backfill is explicitly requested but unsupported for the selected target, the system MUST block that evaluator with remediation instead of silently ignoring the request.
- **FR-058**: Preview, apply, and audit summaries MUST show whether historical backfill is disabled, enabled, unsupported, or not applicable for each evaluator.
- **FR-059**: The system MUST produce an auditable setup summary that records evaluator identity, source type, target, filters, variables, score target, prompt or catalog reference, version, ownership, binding status, effective judge model or LLM connection, activation state, sampling policy, backfill policy, setup status, and remediation for failures.
- **FR-060**: Users MUST be able to audit existing Langfuse evaluator setup against the current project evaluator definitions.
- **FR-061**: The system MUST keep setup idempotent so repeated setup requests do not create duplicate active evaluators for the same project evaluator version and target.
- **FR-062**: The system MUST preserve the Langfuse-first boundary by not running judge LLM calls locally and not implementing a local evaluator scheduler, score store, dashboard, or comparison engine.

### Naming Requirements

- **NR-001**: Harness-managed score configs continue to use the existing project `score_config_prefix` pattern, such as `eh_rewrite_quality_clarity`.
- **NR-002**: Harness-managed Human Annotation Queues continue to use the existing `EH_<project-slug>_<project-version>_review_<review-policy-version>` pattern.
- **NR-003**: Harness-managed Langfuse judge evaluators MUST use a comparable deterministic display name: `EH_<project-slug>_<project-version>_judge_<evaluator-dimension>_<evaluator-version>_<source-type>_<target-type>`.
- **NR-004**: Valid evaluator source type labels are `catalog` for Langfuse catalog evaluators and `custom` for project-defined custom evaluators.
- **NR-005**: Valid target type labels are `observation`, `trace`, or `experiment`, matching the evaluator target selected in the project definition.
- **NR-006**: User-owned evaluator display names are not rewritten by the harness; the harness records and validates their provided references.
- **NR-007**: Setup summaries MUST show both the human-readable Langfuse display name and the stable project evaluator identity so users can connect Langfuse resources back to project configuration.

### Key Entities *(include if feature involves data)*

- **Langfuse Judge Setup Request**: A user-initiated request to preview, apply, or audit evaluator setup for one project.
- **Evaluator Setup Plan**: The planned Langfuse changes for each project evaluator, including create, reuse, update, inactivate, skip, block, and failure decisions.
- **Langfuse Evaluator Binding**: The relationship between a project evaluator definition and the matching Langfuse evaluator, including source type, target, filters, variables, score target, prompt or catalog reference, run types, and ownership.
- **Langfuse Catalog Evaluator**: A pre-canned Langfuse evaluator selected by reference and configured with project-specific filters, variables, score target, and run eligibility.
- **Custom Judge Evaluator**: A project-defined evaluator with custom prompt text, result contract, filters, variables, score target, and run eligibility.
- **Variable Mapping**: The mapping from project evaluator required inputs to Langfuse evaluator variables such as source input, generated output, baseline output, ground truth, and metadata.
- **Managed Evaluator Name**: The deterministic display name used for harness-managed Langfuse judge evaluators so they can be identified, reused, updated, and audited.
- **Evaluator Binding Record**: Local non-secret repository state that records the relationship between a project evaluator identity and a remote Langfuse evaluator identity created or updated by the harness.
- **Setup Result**: The auditable result of preview, apply, or audit, including overall outcome, per-evaluator status, remote evaluator identity when available, binding status, effective judge model or LLM connection, activation state, sampling policy, backfill policy, changed fields, incompatibilities, partial-failure details, and remediation guidance.
- **Remote Compatibility Check**: A comparison between project evaluator definitions and existing Langfuse evaluator, prompt, score config, and filter state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can set up one valid project LLM-as-Judge evaluator directly in Langfuse in under 2 minutes after credentials and required Langfuse project prerequisites are available.
- **SC-002**: Re-running setup for an unchanged project produces zero duplicate active Langfuse evaluators in 100% of tested cases.
- **SC-003**: 100% of setup previews identify planned creates, reuses, updates, inactivations, skips, blocked changes, score targets, filters, prompts or catalog references, and variable mappings before apply.
- **SC-004**: 100% of incompatible existing evaluator configurations are blocked with a field-level compatibility report.
- **SC-005**: 100% of created, reused, or updated observation-level evaluators include project-scoped filters and `observation_role=model_output`.
- **SC-006**: 100% of created, reused, or updated evaluators have all declared required inputs mapped to Langfuse variables.
- **SC-007**: 100% of evaluator dimensions continue to use one canonical score config for human annotation, while automated judge score names are documented and comparable by score source when Langfuse emits them under evaluator names.
- **SC-008**: 100% of missing credential, permission, Langfuse availability, and rate-limit failures return actionable messages without exposing secret values.
- **SC-009**: At least 95% of users validating a successful setup can identify the Langfuse evaluator, source type, score config, prompt or catalog reference, version, and target filter from the setup summary without opening source files.
- **SC-010**: 100% of harness-managed evaluator display names follow the managed naming convention unless the project explicitly provides a valid managed display name override.
- **SC-011**: 100% of newly created evaluators are active immediately after successful apply and are reported as active in the setup summary.
- **SC-012**: 100% of partial setup failures preserve successful evaluator changes and report failed evaluators with remediation guidance without attempting rollback or deletion.
- **SC-013**: 100% of evaluator setup summaries show the effective sampling policy, including 100% matching-observation evaluation when no explicit sampling policy is configured.
- **SC-014**: 100% of evaluator update and inactivation attempts require a matching local binding plus a successful remote compatibility check before mutation.
- **SC-015**: 100% of evaluator setup summaries show the historical backfill policy, and evaluators without explicit backfill configuration apply only to newly ingested matching observations.
- **SC-016**: 100% of evaluator setup summaries show the effective judge model or LLM connection selected from evaluator override or project default.
- **SC-017**: 100% of harness-managed evaluator create and update successes produce or refresh a non-secret local binding record containing the remote Langfuse evaluator ID.

## Assumptions

- Langfuse supports creating or resolving LLM-as-Judge evaluators with target selection, filters, variable mapping, prompt or catalog evaluator selection, score target selection, and sampling controls through externally accessible project operations.
- Langfuse evaluator execution continues to happen inside Langfuse after setup; the harness does not call the judge model locally.
- Existing project evaluator definitions from the LLM-as-Judges feature remain the source of truth.
- Existing score config synchronization remains responsible for creating or resolving canonical score configs before evaluator setup.
- Existing Human Annotation Queue support remains the human calibration path and is not replaced by this feature.
- Current Langfuse LLM-as-Judge evaluator APIs expose evaluator output definitions and evaluation rules, but do not expose a score config binding field. Automated judge scores may therefore use the evaluator name as the score name, while Human Annotation Queue scores use the canonical score config name.
- User-owned Langfuse resources are validated but not mutated unless a future feature explicitly adds an ownership policy for controlled updates.
- Harness-managed evaluator updates are limited to changes that preserve evaluator identity and auditability; deletes, destructive cleanup, and archive or disable workflows remain out of scope for this feature.
- Older harness-managed evaluator versions may be inactivated when superseded, but they are not deleted and their historical score relationships remain auditable.
- Applying setup is treated as an intentional operator action that enables newly created judge evaluators immediately; preview is the safe review step before activation.
- Multi-evaluator setup is not transactional across evaluators because external rollback could require destructive Langfuse mutations.
- Unless configured otherwise, active evaluators judge all matching observations selected by their filters.
- Historical backfill is disabled by default and is only configured when explicitly requested and supported by Langfuse for the selected target.
- Langfuse evaluator resources may not expose arbitrary metadata; ownership proof therefore relies on local binding records and remote compatibility checks, with remote metadata used only if available.
- A project may define a default Langfuse judge model or LLM connection for evaluator setup; individual evaluators may override it.
- Evaluator binding records are local, non-secret, reviewable project artifacts and are not a separate database or service.

## Technical Debt

- **TD-001**: Langfuse evaluator setup temporarily maintains two live adapter paths. The SDK implementation remains in place for stable future SDK evaluator CRUD, while the active fallback uses Langfuse's unstable `/api/public/unstable/evaluation-rules` REST API for create, list, lookup, and safe update/inactivation because the installed SDK does not expose evaluator operations yet. Remove the REST fallback once Langfuse releases stable SDK support for LLM-as-Judge evaluator CRUD. Deletes remain out of scope.
- **TD-002**: Langfuse evaluator rules currently do not expose a score config binding field. The harness records the intended canonical score config in local bindings for calibration, but Langfuse LLM-as-Judge scores may be emitted under the evaluator name and source `EVAL`; Human Annotation Queue scores continue to use the canonical score config and source `ANNOTATION`.
