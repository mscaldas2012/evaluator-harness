# Feature Specification: Create Annotation Queues

**Feature Branch**: `003-create-annotation-queues`

**Created**: May 26, 2026

**Status**: Draft

**Input**: User description: "Implement automatic Langfuse Human Annotation Queue creation so the live review routing smoke test and future project runs do not require a manually configured LANGFUSE_ANNOTATION_QUEUE_ID."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sync Project Review Queue (Priority: P1)

As an evaluation project owner, I want the harness to create or reuse the project's human annotation queue from the project configuration so I can run review routing without manually finding and copying a queue ID.

**Why this priority**: Human review is part of the evaluation workflow, and requiring manual queue setup blocks live review smoke tests and project onboarding.

**Independent Test**: Can be fully tested by running a queue sync command for a project that has no queue ID configured and verifying the project receives a reusable queue reference.

**Acceptance Scenarios**:

1. **Given** a project with human review enabled and no annotation queue reference, **When** the user syncs review assets, **Then** the harness creates a Langfuse Human Annotation Queue for the project and records the queue reference for later runs.
2. **Given** a project with an existing managed queue reference, **When** the user syncs review assets again, **Then** the harness reuses the existing queue instead of creating a duplicate.

---

### User Story 2 - Route Review Items Without Manual Queue Environment (Priority: P2)

As a user running baseline or candidate experiments, I want review selection to route selected items to the project queue automatically so baseline and future candidate runs use the same human review destination.

**Why this priority**: The selected review cohort must remain comparable across baseline and candidate runs, and manual queue configuration is easy to miss.

**Independent Test**: Can be fully tested by running an experiment, selecting review items, and verifying selected items are routed to the project-managed queue without `LANGFUSE_ANNOTATION_QUEUE_ID`.

**Acceptance Scenarios**:

1. **Given** a project with a managed annotation queue, **When** review selection runs for a baseline run, **Then** selected baseline items are routed to that queue.
2. **Given** the same project later runs a candidate model, **When** review selection runs for the candidate run, **Then** selected candidate items are routed to the same queue as the baseline.

---

### User Story 3 - Keep Manual Queue Override Available (Priority: P3)

As an advanced user, I want to keep using a manually supplied existing annotation queue when needed so I can route multiple related projects into a shared review workflow.

**Why this priority**: Some teams may already manage review queues in Langfuse and should not be forced into harness-created queues.

**Independent Test**: Can be fully tested by configuring an existing queue reference and verifying the harness does not create a managed queue.

**Acceptance Scenarios**:

1. **Given** a project configured with an explicit existing annotation queue reference, **When** review assets are synced, **Then** the harness uses that queue and reports it as user-owned.
2. **Given** the explicit queue reference is invalid or inaccessible, **When** review routing runs, **Then** the user receives a clear error that identifies the queue setup problem without losing experiment results.

---

### Edge Cases

- Human review is disabled for the project; queue sync should report that no queue is required.
- Langfuse credentials are missing or invalid; queue sync should fail before changing local project state.
- Langfuse does not support queue creation in the current workspace or deployment; the harness should report that manual queue configuration is required.
- A queue with the intended managed name already exists but is not known to the local project; the harness should reuse it only when it can confirm ownership or compatibility.
- Queue creation succeeds but local state cannot be updated; the user should receive recovery guidance that includes the created queue reference.
- Review routing runs before queue sync; the harness should attempt to resolve or create the queue, or fail with a clear next action.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST associate each review queue with a specific evaluation project identity so future runs for that project reuse the same queue.
- **Dataset**: Feature MUST preserve the stable human review cohort behavior across baseline and candidate runs.
- **Langfuse Logging**: Feature MUST record enough queue metadata in run or routing output for users to find the review queue and understand whether it was managed by the harness or user-owned.
- **Prompt and Evaluator Versioning**: Feature MUST preserve existing evaluator version metadata in routed review items.
- **Baseline**: Feature MUST support baseline-first workflows and candidate runs that reuse an existing baseline and the same review queue.
- **Human Review**: Feature MUST enable Human Annotation Queue routing without requiring `LANGFUSE_ANNOTATION_QUEUE_ID` for project-managed queues.

### Functional Requirements

- **FR-001**: System MUST allow a project to declare whether its human annotation queue is managed by the harness or supplied by the user.
- **FR-002**: System MUST create a project-managed Human Annotation Queue when human review is enabled and no compatible managed queue exists.
- **FR-003**: System MUST reuse an existing compatible managed queue for repeated syncs and future runs.
- **FR-004**: System MUST persist the managed queue reference in project-local state or project configuration so later baseline and candidate runs can route to the same queue.
- **FR-005**: System MUST continue to support user-owned queue references and MUST NOT modify or recreate those queues.
- **FR-006**: System MUST make review routing work without `LANGFUSE_ANNOTATION_QUEUE_ID` when a project-managed queue has been synced.
- **FR-007**: System MUST route baseline and candidate review items for the same project to the same resolved queue.
- **FR-008**: System MUST report queue sync results clearly, including created, reused, skipped, user-owned, and failed states.
- **FR-009**: System MUST fail clearly when Langfuse queue creation is unavailable, unauthorized, or unsupported, and MUST explain the manual fallback.
- **FR-010**: System MUST avoid creating duplicate queues during repeated syncs for the same project.
- **FR-011**: System MUST avoid storing Langfuse secrets in committed project configuration or generated queue state.
- **FR-012**: System MUST name harness-managed queues using `EH_<project-slug>_<project-version>_review_<review-policy-version>`, unless the project provides an explicit `queue_name`.
- **FR-013**: System MUST persist managed queue references under `.evaluator-harness/queue-references/<project-slug>__<project-version>__<review-policy-version>.json`.
- **FR-014**: System MUST validate generated and configured queue names as slug-safe values containing only letters, numbers, underscores, and hyphens.

### Key Entities *(include if feature involves data)*

- **Annotation Queue Reference**: Represents the resolved queue used by a project, including queue ID, queue name, ownership, project identity, creation or discovery status, and last sync time.
- **Review Queue Policy**: Represents whether human review is enabled, whether the queue is managed by the harness or user-owned, the intended queue name, and fallback behavior when automation is unavailable.
- **Review Routing Result**: Represents the output of sending selected review items to a queue, including queue ID, selected count, routed count, duplicate count, and any routing failures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can enable human review for a new project and prepare the annotation queue in one command without manually creating a queue in Langfuse.
- **SC-002**: Re-running queue sync for the same project creates zero duplicate queues.
- **SC-003**: Baseline and candidate review selections for the same project route to the same queue in 100% of successful runs.
- **SC-004**: Live review routing tests can run without `LANGFUSE_ANNOTATION_QUEUE_ID` when Langfuse queue creation is supported.
- **SC-005**: When queue creation is unavailable, the user receives a clear manual fallback message within the failed command output.

## Assumptions

- Langfuse Human Annotation Queue creation may be available for automation in supported Langfuse deployments, but the harness must handle deployments where it is unavailable.
- Project-managed queue state can be stored locally because the harness already uses lightweight local state for reproducibility and run references.
- User-owned queues remain valid for teams that prefer manual Langfuse setup or shared review workflows.
- Queue automation is limited to creating, resolving, and routing to queues; configuring detailed reviewer assignments or Langfuse permissions is out of scope for this feature.
