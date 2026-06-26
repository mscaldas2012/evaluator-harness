# Feature Specification: Automatic Evaluator Calibration Support

**Feature Branch**: `[026-evaluator-calibration]`

**Created**: 2026-06-23

**Status**: Draft

**Input**: User description: "Create a specification for BL-007 automatic evaluator calibration support based on the agreed implementation plan."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture Calibration Evidence (Priority: P1)

As an evaluation owner, I can generate a calibration snapshot for a completed run that includes selected calibration items, automated evaluator scores, and completed human annotation scores so that I can compare judge behavior against human labels.

**Why this priority**: The core value of BL-007 is to make calibration data available for iterative evaluator improvement. Without this, disagreement and drift analysis cannot happen.

**Independent Test**: Can be fully tested by running calibration capture for one completed run and verifying that the output contains joined item-level records for review selection, evaluator outputs, and human labels.

**Acceptance Scenarios**:

1. **Given** a completed run with review-selected items and available evaluator scores, **When** the user runs calibration capture, **Then** the system produces a calibration artifact with one record per eligible review item.
2. **Given** a completed run where some selected items do not yet have completed human annotations, **When** calibration capture runs, **Then** those items are included with a pending-label indicator instead of causing the command to fail.

---

### User Story 2 - Summarize Disagreement and Bias (Priority: P2)

As an evaluation owner, I can generate disagreement summaries between automated and human scores by evaluator dimension so that I can identify where evaluator prompts need tuning.

**Why this priority**: Teams need a concise signal for calibration quality, not only raw records.

**Independent Test**: Can be fully tested by generating a summary from one calibration snapshot and verifying metric outputs for disagreement rate, average absolute score delta, and directional bias.

**Acceptance Scenarios**:

1. **Given** a calibration snapshot with both automated and human scores, **When** summary generation runs, **Then** the system reports per-evaluator disagreement and score delta metrics.
2. **Given** a calibration snapshot where no paired human and automated scores exist for an evaluator, **When** summary generation runs, **Then** the system reports zero paired coverage for that evaluator with a clear warning.

---

### User Story 3 - Track Calibration Drift Over Time (Priority: P3)

As an evaluation owner, I can compare calibration summaries across multiple snapshots to detect drift in evaluator alignment over time.

**Why this priority**: Drift detection supports proactive prompt maintenance and prevents silent quality regression.

**Independent Test**: Can be fully tested by generating summaries for multiple run snapshots and validating that the drift view reports metric deltas between current and prior windows.

**Acceptance Scenarios**:

1. **Given** at least two calibration snapshots for the same project and evaluator dimension, **When** drift summary generation runs, **Then** the system reports metric changes between the latest window and prior baseline window.
2. **Given** only one available calibration snapshot, **When** drift summary generation runs, **Then** the system reports that drift cannot be computed yet and still returns current calibration metrics.

### Edge Cases

- A run has calibration selections but no evaluator scores due to score retrieval degradation.
- A run has evaluator scores but no completed human annotations in the queue yet.
- Multiple scores exist for the same trace and evaluator; the system must apply a deterministic selection rule.
- A project has mixed baseline and candidate calibration snapshots; outputs must preserve run type identity.
- Calibration summary is requested for a run that does not belong to the specified project scope.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST operate within the existing harness project identity (project name, project version, dataset identity, evaluator set, and review policy scope).
- **Dataset**: Feature MUST preserve existing dataset-based trace-to-item linkage and never require a new dataset format to enable calibration.
- **Langfuse Logging**: Feature MUST use Langfuse trace, score, and annotation queue records as the source evidence for calibration outputs.
- **Prompt and Evaluator Versioning**: Feature MUST preserve evaluator and prompt version context in calibration outputs so analysts can tie findings to evaluator prompt revisions.
- **Baseline**: Feature MUST support calibration capture for baseline runs, candidate runs, or both when data exists.
- **Human Review**: Feature MUST build on existing human review selection workflows and must not replace Langfuse Human Annotation Queue usage.

### Functional Requirements

- **FR-001**: The system MUST provide an explicit workflow to capture calibration data for a completed run.
- **FR-002**: The system MUST include review selection metadata in calibration capture outputs, including selection reason and selection bucket.
- **FR-003**: The system MUST include automated evaluator outputs and associated score source metadata for each calibration item where available.
- **FR-004**: The system MUST include completed human annotation scores for the same score target and item where available.
- **FR-005**: The system MUST preserve records with missing human labels and mark them as pending rather than dropping them silently.
- **FR-006**: The system MUST generate per-evaluator calibration summaries that include paired coverage, disagreement rate, mean absolute score delta, and directional bias.
- **FR-007**: The system MUST generate drift summaries that compare calibration metrics across snapshots for the same project and evaluator dimension.
- **FR-008**: The system MUST provide deterministic metric calculations so repeated processing of the same source records yields identical outputs.
- **FR-009**: The system MUST produce calibration artifacts in machine-readable forms that can be reused in downstream analysis.
- **FR-010**: The system MUST ensure calibration outputs retain run-level identity and distinguish baseline and candidate context.
- **FR-011**: The system MUST surface clear warnings when score retrieval or annotation retrieval is incomplete.
- **FR-012**: The system MUST remain optional and must not change baseline and candidate run execution behavior when calibration workflows are not invoked.
- **FR-013**: The system MUST avoid creating a parallel scoring engine and must treat Langfuse records as the source of truth.
- **FR-014**: The system MUST support the existing review sampling model so stable calibration cohorts remain comparable across compatible runs.

### Key Entities *(include if feature involves data)*

- **Calibration Snapshot**: A run-scoped artifact containing item-level calibration evidence including review metadata, automated scores, human labels, and pairing status.
- **Calibration Record**: One dataset item or trace record in a snapshot with evaluator dimension, score target, automated score, human score, score delta, and disagreement marker.
- **Calibration Summary**: Aggregated evaluator-level and run-level metrics derived from paired calibration records.
- **Drift Summary**: A comparison artifact showing changes in calibration metrics between a current snapshot window and a prior baseline window.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can generate a calibration snapshot for a completed run in a single workflow without manual data joins.
- **SC-002**: For runs with both score sources present, 100% of eligible reviewed items appear in calibration outputs with correct pairing status.
- **SC-003**: Calibration summary generation reports evaluator-level disagreement and score-delta metrics for 100% of evaluators that have paired scores.
- **SC-004**: Drift summaries identify metric changes between windows for 100% of evaluators with at least two snapshots.
- **SC-005**: Re-processing the same run inputs produces identical calibration summary values across repeated executions.
- **SC-006**: Calibration workflows do not alter run execution outcomes for users who do not invoke calibration capture or summary commands.

## Assumptions

- Existing human review selection and queue-routing workflows remain the calibration intake path.
- Langfuse remains the source of truth for evaluator and human annotation scores.
- Human annotation completion may lag behind run completion, so partial pairing is expected.
- The first release of BL-007 focuses on run-level calibration capture and summary outputs before any automated gating behavior.
- Existing project-level score target alignment rules remain enforced and are reused by calibration workflows.
