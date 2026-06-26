# Feature Specification: Campaign Calibration Report

**Feature Branch**: `027-campaign-calibration-report`

**Created**: 2026-06-25

**Status**: Draft

**Input**: User description: "Say the user just ran a campaign and annotated the relevant items in the queue. We should be able to run the calibration capture and summarization for the baseline and any candidate run by the campaign. This has to be a separate execution from the campaign because of the human steps in the middle which could take hours or even days. Then the last task will be to generate the HTML report just like the ad-hoc you created; baseline-2e1c28df5f97-comparison.html."

## Clarifications

### Session 2026-06-25

- Q: What should be the required source for resolving campaign run IDs when the user runs campaign-calibration-report without listing every run? -> A: Use a campaign manifest first, then fall back to existing comparison/export artifacts.
- Q: What should the user pass to identify the campaign when running the post-campaign command? -> A: Use the baseline run ID as the campaign anchor.
- Q: When the user reruns campaign calibration after more annotations are completed, how should existing per-run calibration artifacts be handled? -> A: Always overwrite calibration snapshots, summaries, and HTML report from the latest Langfuse state.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture Campaign Calibration (Priority: P1)

An evaluator operator has already run a campaign and completed the relevant Langfuse annotation queue reviews. They want one follow-up command, anchored by the campaign baseline run ID, to capture calibration evidence for the campaign baseline and every candidate run created by that campaign, without rerunning the campaign.

**Why this priority**: This is the core workflow. Human annotation happens after campaign execution and may take hours or days, so calibration must be runnable later against existing campaign artifacts and run IDs.

**Independent Test**: Can be tested by using an existing campaign report/export with one baseline and multiple candidate runs, completed annotations for each run, and verifying that calibration snapshots are produced for every campaign run.

**Acceptance Scenarios**:

1. **Given** a completed campaign with one baseline run, two candidate runs, and completed annotation queue items for all three runs, **When** the user starts campaign calibration using the baseline run ID, **Then** the system captures calibration snapshots for the baseline and both candidate runs.
2. **Given** a campaign where one candidate has no completed annotation queue item, **When** campaign calibration runs, **Then** the system still processes the other campaign runs and clearly reports the candidate with missing calibration evidence.
3. **Given** a campaign was completed days earlier, **When** the user runs campaign calibration using its saved campaign artifacts, **Then** the system resolves run identities from the campaign manifest when available, otherwise from existing comparison/export artifacts, rather than requiring the campaign to be rerun.

---

### User Story 2 - Summarize Campaign Calibration (Priority: P2)

After campaign calibration snapshots are captured, the evaluator operator wants per-run evaluator summaries for the baseline and every candidate so they can compare human alignment across the whole campaign.

**Why this priority**: Summaries turn row-level score pairs into actionable evaluator-level alignment metrics and are needed before a useful report can be generated.

**Independent Test**: Can be tested by starting from existing calibration snapshots for a campaign and verifying that a summary exists for each baseline and candidate run with paired coverage, disagreement rate, mean absolute score delta, and directional bias.

**Acceptance Scenarios**:

1. **Given** campaign calibration snapshots exist for all campaign runs, **When** campaign summarization runs, **Then** each run receives a summary artifact with evaluator-level metrics.
2. **Given** one run has incomplete human annotations, **When** summaries are generated, **Then** that run's summary includes clear missing-label or zero-coverage warnings without blocking summaries for other runs.

---

### User Story 3 - Generate Campaign Calibration HTML Report (Priority: P3)

After campaign calibration capture and summary are complete, the evaluator operator wants a single HTML report, similar in usability to existing comparison reports, showing baseline and candidate calibration alignment side by side.

**Why this priority**: The report is the shareable artifact that lets reviewers inspect calibration outcomes without opening multiple JSON files.

**Independent Test**: Can be tested by using a campaign with completed calibration summaries and verifying that one HTML report is generated with a run overview, evaluator comparison, largest deltas, and detailed paired records.

**Acceptance Scenarios**:

1. **Given** a campaign has calibration summaries for its baseline and candidates, **When** the user generates the campaign calibration report, **Then** the report shows all campaign runs in one view.
2. **Given** evaluator metrics differ across candidates, **When** the report is opened, **Then** the user can identify which evaluators and runs have the largest human-versus-automated score deltas.
3. **Given** a run has warnings or missing calibration evidence, **When** the report is opened, **Then** the warning is visible in the report without hiding the completed runs.

---

### Edge Cases

- The campaign artifact exists, but one or more referenced run exports are missing.
- A campaign has no candidates, or only a baseline was completed.
- Completed annotation queue items exist for traces outside the campaign; they must not appear in this campaign's calibration output.
- A run has automated evaluator scores but no completed human annotations.
- A run has completed human annotations for only a subset of evaluators.
- The user runs campaign calibration more than once after additional annotations are completed; artifacts are regenerated from the latest available Langfuse state.
- The campaign includes multiple candidates that share the same baseline.
- Existing calibration snapshots or summaries already exist for some runs but not others.
- The HTML report is generated before all runs have complete calibration evidence.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST operate on an existing evaluation project and campaign, using the campaign's baseline run, candidate runs, evaluator definitions, and human review policy.
- **Dataset**: Feature MUST preserve the campaign dataset identity and item identities in calibration artifacts and report views.
- **Langfuse Logging**: Feature MUST consume existing Langfuse traces, automated evaluator scores, and human annotation scores; it MUST NOT require rerunning generation or evaluator scoring.
- **Prompt and Evaluator Versioning**: Feature MUST preserve prompt versions, evaluator versions, score targets, run identities, and score sources in campaign calibration outputs.
- **Baseline**: Feature MUST consume the baseline run associated with the campaign and include it alongside campaign candidates.
- **Human Review**: Feature MUST treat completed Langfuse Human Annotation Queue items as the source of human calibration labels and report missing or incomplete annotations clearly.

### Functional Requirements

- **FR-001**: Users MUST be able to start calibration for a completed campaign after human annotation is complete or partially complete by providing the campaign baseline run ID.
- **FR-002**: The system MUST identify the campaign baseline run and every candidate run created by the campaign.
- **FR-002a**: The system MUST resolve campaign run identities from a persisted campaign manifest when available, then fall back to existing comparison/export artifacts when the manifest is unavailable or incomplete.
- **FR-002b**: The system MUST fail with a clear, actionable message when neither the campaign manifest nor fallback artifacts can identify the baseline and candidate run IDs.
- **FR-002c**: The system MUST treat the provided baseline run ID as the campaign anchor and MUST include that baseline in the campaign calibration outputs.
- **FR-003**: The system MUST capture calibration evidence for each campaign run using completed annotation queue items that match traces from that run.
- **FR-004**: The system MUST generate per-run calibration summaries for every campaign run with captured calibration evidence.
- **FR-005**: The system MUST continue processing remaining campaign runs when one run has missing exports, missing scores, or missing annotations.
- **FR-006**: The system MUST produce clear warnings for campaign runs that cannot be captured, cannot be summarized, or have incomplete calibration coverage.
- **FR-007**: The system MUST make repeated campaign calibration execution safe by overwriting campaign calibration snapshots, summaries, and the HTML report from the latest available Langfuse state.
- **FR-008**: The system MUST generate one campaign-level HTML report after capture and summary steps complete.
- **FR-009**: The HTML report MUST include baseline and candidate run identities, reviewed item identities, paired coverage, disagreement rate, mean absolute score delta, directional bias, and warnings.
- **FR-010**: The HTML report MUST let users compare evaluator alignment across baseline and candidates without opening individual JSON files.
- **FR-011**: The system MUST store campaign calibration artifacts in a predictable campaign/project report location.
- **FR-012**: Campaign calibration MUST remain a separate user action from campaign execution because human annotation may be completed hours or days later.

### Key Entities *(include if feature involves data)*

- **Campaign Calibration Run**: A post-campaign calibration operation anchored by a baseline run ID that references one campaign and records which baseline and candidate runs were processed, skipped, warned, captured, summarized, and reported.
- **Campaign Run Reference**: A baseline or candidate run that belongs to a campaign, including run ID, role, candidate identity when applicable, report/export location, and related campaign metadata.
- **Calibration Snapshot**: Row-level paired or pending evidence for a single run, including item ID, trace ID, evaluator identity, automated score, human score, score source, selection reason, and metadata.
- **Calibration Summary**: Per-evaluator metrics for one run, including record count, paired count, pending count, paired coverage, disagreement rate, mean absolute score delta, directional bias, and warnings.
- **Campaign Calibration Report**: A shareable HTML artifact that aggregates campaign run references, summaries, warnings, and paired record details into a single review page.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can generate campaign calibration snapshots and summaries using one post-campaign action and the baseline run ID, even when the campaign has only the baseline run; candidate runs are included when discoverable.
- **SC-002**: For a campaign where all referenced runs have completed annotation queue items, 100% of campaign runs produce calibration summary artifacts.
- **SC-003**: For a campaign with partial annotation completion, completed runs are still captured and summarized, and incomplete runs are listed with warnings in the final result.
- **SC-004**: The generated HTML report includes all campaign baseline and candidate runs with calibration summaries in a single page.
- **SC-005**: Users can identify the highest-disagreement evaluator/run combinations from the HTML report in under two minutes.
- **SC-006**: Re-running campaign calibration after additional annotations are completed regenerates the affected run artifacts from the latest available Langfuse state without requiring campaign rerun.

## Assumptions

- The campaign has already produced a persisted campaign manifest, local campaign comparison artifacts, or equivalent saved run references that identify the baseline and candidate run IDs.
- Users complete human review in Langfuse before running campaign calibration, but the workflow must tolerate partial completion.
- Existing single-run calibration capture and summary behavior remains the source of truth for per-run pairing and metric definitions.
- The campaign calibration report should be a local static HTML artifact aligned with existing comparison report usability.
- Campaign calibration does not implement long-term drift comparison; drift remains a separate backlog capability.
