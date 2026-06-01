# Feature Specification: Sync Langfuse Prompts

**Feature Branch**: `012-sync-langfuse-prompts`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "Sync repository task and evaluator prompts into Langfuse as an optional project artifact while keeping repository files as the source of truth. Benefits should include prompt version history, Langfuse visibility, run reproducibility metadata, review/debug support, and auditability without making live Langfuse prompt state required for local runs."

## Clarifications

### Session 2026-06-01

- Q: Should prompt sync allow changed prompt content under the same configured prompt version? -> A: No. Users must bump `prompt_version` whenever prompt content changes; sync fails when the same managed prompt version label already exists with different content.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publish Project Prompts (Priority: P1)

An evaluator harness user can publish a project's task prompt and evaluator prompts to Langfuse so reviewers can inspect the exact prompt content associated with an evaluation project.

**Why this priority**: Prompt visibility is the main value of the feature. Users need to see task and judge prompts in Langfuse without leaving the evaluation workspace.

**Independent Test**: Can be fully tested by syncing prompts for one configured project and confirming every configured prompt appears in Langfuse with the expected project identity, prompt role, prompt version, and content.

**Acceptance Scenarios**:

1. **Given** a project with one task prompt and multiple evaluator prompts, **When** the user syncs prompts, **Then** each prompt is represented in Langfuse with a stable name, version label, content, project, and prompt purpose.
2. **Given** a project prompt has already been synced and the local content has not changed, **When** the user syncs prompts again, **Then** the result reports that the existing Langfuse prompt version was reused and does not create duplicate equivalent versions.
3. **Given** a local prompt changes while keeping the same configured prompt version, **When** the user syncs prompts, **Then** the sync fails for that prompt and instructs the user to bump the prompt version before publishing.

---

### User Story 2 - Preserve Local Source of Truth (Priority: P1)

An evaluator harness user can continue running local validation, baseline runs, candidate runs, exports, and evaluator setup from repository prompt files even if Langfuse prompt sync has never been run or Langfuse is unavailable.

**Why this priority**: The harness must stay local-first and reproducible from the repository. Langfuse prompt sync is an artifact publishing workflow, not a new runtime dependency.

**Independent Test**: Can be fully tested by running a project without synced Langfuse prompts and confirming existing project workflows still use local prompt files and complete as before.

**Acceptance Scenarios**:

1. **Given** a valid project with local prompt files and no synced Langfuse prompt records, **When** the user validates or runs the project, **Then** the project uses local prompts and does not require Langfuse prompt records.
2. **Given** Langfuse is unavailable, **When** the user runs local-only workflows that do not require Langfuse, **Then** prompt sync state does not block those workflows.
3. **Given** Langfuse contains a prompt with the same name but different content, **When** the user runs the project locally, **Then** local repository content remains the source used for model and judge requests.

---

### User Story 3 - Trace Prompt Provenance (Priority: P2)

An evaluator harness user can inspect a run in Langfuse and identify which local prompt content and synced Langfuse prompt artifact were associated with each task or evaluator execution.

**Why this priority**: Prompt provenance supports debugging, comparison across runs, and audit review.

**Independent Test**: Can be fully tested by syncing prompts, running a project, and confirming traces and evaluator metadata include prompt identity fields that connect the run back to the local prompt content and synced Langfuse prompt artifact.

**Acceptance Scenarios**:

1. **Given** prompts have been synced before a run, **When** the run logs traces, **Then** trace metadata includes the local prompt path, configured prompt version, content identity, and Langfuse prompt reference where available.
2. **Given** prompts have not been synced before a run, **When** the run logs traces, **Then** trace metadata still includes local prompt path, configured prompt version, and content identity, while the Langfuse prompt reference is absent or marked unavailable.
3. **Given** a reviewer opens a trace in Langfuse, **When** they inspect metadata, **Then** they can determine which prompt content was used without relying on ambiguous free-text notes.

---

### User Story 4 - Dry-Run Prompt Sync State (Priority: P3)

An evaluator harness user can preview prompt sync actions before applying them and can check whether Langfuse prompt artifacts match the repository configuration without mutation.

**Why this priority**: Users need confidence before publishing or updating shared Langfuse artifacts, especially when multiple people use the same workspace.

**Independent Test**: Can be fully tested by running a dry-run against unchanged, changed, missing, and conflicting prompt artifacts and confirming the reported status is accurate.

**Acceptance Scenarios**:

1. **Given** no Langfuse prompt artifact exists for a configured local prompt, **When** the user audits prompt sync, **Then** the prompt is reported as missing and planned for creation.
2. **Given** a Langfuse prompt artifact exists with matching content identity, **When** the user audits prompt sync, **Then** the prompt is reported as reusable.
3. **Given** a Langfuse prompt artifact exists with the same managed name but unexpected ownership metadata, **When** the user audits prompt sync, **Then** the prompt is reported as a conflict and is not modified automatically.

### Edge Cases

- A configured prompt file is missing or unreadable when prompt sync is requested.
- Two configured prompts resolve to the same managed prompt name.
- A prompt contains role-based sections as well as single-text legacy content across different projects.
- Langfuse already contains a prompt with the managed name but without harness ownership metadata.
- Langfuse accepts the prompt content but returns a different prompt version identifier than expected.
- A prompt is renamed locally after it has already been synced.
- Prompt content changes while the configured prompt version remains the same.
- A user runs export or review workflows for historical traces created before prompt sync existed.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST support existing project identities and prompt definitions for task prompts and evaluator prompts.
- **Dataset**: Feature MUST preserve support for CSV datasets with an `input` column and MUST NOT require dataset changes to sync prompts.
- **Langfuse Logging**: Feature MUST define prompt artifact references that can be included in trace metadata, evaluator metadata, and exported reports when available.
- **Prompt and Evaluator Versioning**: Feature MUST associate each synced prompt with the configured prompt version, prompt purpose, project identity, and a content identity that changes when local content changes.
- **Baseline**: Feature MUST NOT require creating, selecting, or rerunning a baseline before prompt sync can be performed.
- **Human Review**: Feature MUST make synced prompt references visible enough for reviewers to inspect prompts used by runs and evaluator judgments in Langfuse.

### Functional Requirements

- **FR-001**: Users MUST be able to sync all prompt artifacts referenced by a project configuration, including the task prompt and every evaluator prompt with a local prompt file.
- **FR-002**: Users MUST be able to dry-run prompt sync state without modifying Langfuse.
- **FR-003**: Prompt sync MUST keep repository prompt files as the source of truth for run-time prompt rendering.
- **FR-004**: Prompt sync MUST create stable managed prompt names that distinguish project, project version, prompt purpose, evaluator identity where applicable, and configured prompt version.
- **FR-005**: Prompt sync MUST record a content identity for each local prompt so unchanged prompt content can be recognized on later syncs.
- **FR-006**: Prompt sync MUST avoid creating duplicate equivalent prompt versions when the local prompt content identity already exists in Langfuse.
- **FR-007**: Prompt sync MUST report one status per prompt artifact, including at least created, reused, changed, skipped, conflict, and failed outcomes.
- **FR-008**: Prompt sync MUST refuse to overwrite or mutate prompt artifacts that do not carry harness-managed ownership metadata.
- **FR-009**: Prompt sync MUST support both legacy single-text prompts and role-based prompt definitions without losing role order or role labels.
- **FR-010**: Runs MUST include local prompt identity metadata regardless of whether prompt sync has been performed.
- **FR-011**: Runs SHOULD include synced Langfuse prompt reference metadata when a matching synced prompt artifact is known.
- **FR-012**: Exports SHOULD include prompt artifact reference fields when they are present in trace metadata.
- **FR-013**: Prompt sync MUST provide clear user feedback for long operations, including progress across multiple prompts.
- **FR-014**: Prompt sync MUST fail with actionable messages when a prompt file is missing, a managed name collides, Langfuse is unreachable, or the remote prompt state conflicts with local ownership expectations.
- **FR-015**: Prompt sync MUST be optional; existing validate, run, evaluator setup, export, and review workflows MUST continue to work for projects that have never synced prompts.
- **FR-016**: Prompt sync MUST reject publishing changed content under an already-synced managed prompt version label and MUST instruct users to bump the relevant configured `prompt_version`.

### Key Entities *(include if feature involves data)*

- **Prompt Artifact**: A task or evaluator prompt referenced by a project. Key attributes include purpose, local path, configured version, prompt shape, roles when present, content identity, and project identity.
- **Synced Prompt Reference**: The Langfuse-side representation of a prompt artifact. Key attributes include managed name, Langfuse prompt identifier or version reference, content identity, ownership metadata, and sync status.
- **Prompt Sync Report**: The user-facing result of a sync or dry-run operation. Key attributes include project identity, prompt count, per-prompt status, conflicts, failures, and remediation text.
- **Prompt Provenance Metadata**: Metadata associated with traces, evaluator setup, and exports that identifies local prompt content and, when available, synced Langfuse prompt references.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can sync prompts for a project with at least 10 evaluator prompts and one task prompt in under 2 minutes, excluding external service outages.
- **SC-002**: Re-running prompt sync on unchanged project prompts reports 100% of prompt artifacts as reused or unchanged, with no duplicate equivalent prompt versions created.
- **SC-003**: For runs created after this feature, 100% of traces include local prompt identity metadata for the task prompt used in the run.
- **SC-004**: For evaluator prompts synced before judge setup or execution, 100% of related evaluator metadata includes a prompt artifact reference that can be traced back to the synced Langfuse prompt.
- **SC-005**: Audit mode identifies missing, matching, changed, and conflicting prompt artifacts accurately in at least one test case for each status.
- **SC-006**: Existing local-only workflows continue to complete without synced prompt artifacts, preserving current behavior for projects that do not opt into prompt sync.

## Assumptions

- Repository prompt files remain the authoritative prompt source for rendering and model calls.
- Prompt sync is a publishing and dry-run workflow, not a requirement for running an experiment.
- Managed prompt artifacts are identified by stable names plus harness ownership metadata.
- Prompt content identity is based on normalized prompt content and prompt shape metadata.
- Human-edited Langfuse prompt artifacts with matching names but missing ownership metadata are treated as conflicts rather than overwritten.
- Existing project prompt version fields are strict release labels; prompt content changes require a corresponding prompt version bump before publishing.
- Historical traces created before this feature may not have synced prompt reference metadata.
