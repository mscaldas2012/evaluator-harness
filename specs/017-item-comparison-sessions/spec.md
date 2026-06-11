# Feature Specification: Langfuse Item Comparison Sessions

**Feature Branch**: `017-item-comparison-sessions`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Implement the session according to the recommendation: use Langfuse sessions to keep baseline and candidate traces together for the same dataset item, while keeping run metadata as the authoritative aggregate comparison model."

## Clarifications

### Session 2026-06-11

- Q: Should v1 include session-level human or programmatic scores, or only official Langfuse session grouping? -> A: Only official Langfuse session grouping in v1; manual Langfuse UI session scoring is backlog.
- Q: How should candidate runs without an explicit baseline reference behave? -> A: Fail validation for candidate runs that lack an explicit baseline reference.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare One Item Across Runs (Priority: P1)

An evaluator owner can inspect a dataset item in Langfuse and see the baseline trace plus all candidate traces for that same item grouped in one session.

**Why this priority**: The primary value of sessions is item-level debugging. A whole-run session would be too noisy, while item-level sessions make it practical to compare baseline and candidate behavior for the exact same input.

**Independent Test**: Run one baseline and one candidate against the same dataset, then verify that the baseline trace and candidate trace for a chosen item share one Langfuse session and that another item uses a different session.

**Acceptance Scenarios**:

1. **Given** a baseline run logs traces for dataset items, **When** the traces are sent to Langfuse, **Then** each trace has a valid item-level comparison session identifier.
2. **Given** a candidate run is compared against a baseline run, **When** the candidate trace for an item is sent to Langfuse, **Then** it uses the same comparison session as the baseline trace for that item.
3. **Given** two different dataset items in the same baseline and candidate runs, **When** traces are inspected in Langfuse, **Then** the items do not share the same session.

---

### User Story 2 - Review Candidate Items With Baseline Context (Priority: P2)

A human reviewer can open an item selected for review and use the Langfuse session to understand how the candidate output compares with the corresponding baseline output.

**Why this priority**: Human annotation is most useful when the reviewer can see comparable context without manually searching by run IDs, item IDs, or trace metadata.

**Independent Test**: Queue a candidate item for review, open the corresponding Langfuse trace, and verify the linked session contains the candidate trace and its baseline trace for the same item.

**Acceptance Scenarios**:

1. **Given** an item is selected for human review because it is a failure, low-confidence item, or disputed item, **When** the reviewer opens its trace in Langfuse, **Then** the session groups the item-level baseline and candidate traces.
2. **Given** multiple candidate runs compare against the same baseline, **When** a reviewer inspects a reviewed item session, **Then** the session can contain all candidate traces for that item without grouping unrelated dataset items.

---

### User Story 3 - Preserve Run-Level Reporting (Priority: P3)

An operator can continue using run IDs, baseline references, exports, and reports as the source of truth for aggregate comparison while sessions provide additional item-level navigation.

**Why this priority**: Sessions should improve trace inspection without changing how the harness compares runs, generates reports, or targets evaluator scores.

**Independent Test**: Generate baseline and candidate reports after session logging is enabled and verify report content, run IDs, baseline references, and evaluator score aggregation remain unchanged except for optional session identifiers.

**Acceptance Scenarios**:

1. **Given** a baseline and candidate run complete successfully, **When** reports are generated, **Then** aggregate comparisons still use run metadata and baseline references, not session membership.
2. **Given** evaluator filters, prompt bindings, and score config bindings exist, **When** sessions are logged, **Then** those bindings continue to operate independently of session identifiers.

### Edge Cases

- Session identity inputs may contain spaces, punctuation, Unicode, or very long values; the system must produce a valid Langfuse session identifier that is US-ASCII and no longer than 200 characters.
- A candidate run without an explicit baseline reference must fail validation and must not create fallback comparison sessions.
- Re-running a baseline over the same dataset item must create a distinct comparison session family because the baseline run identity changed.
- Different projects, project versions, datasets, or dataset versions with the same item identifier must not collide into the same session.
- Existing Langfuse traces without sessions must remain usable and must not require backfill for current reports to work.
- If Langfuse logging is disabled or unavailable, the harness must continue run execution according to the existing Langfuse failure policy.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature applies to every evaluation project that logs baseline or candidate traces to Langfuse, including GSO and DFE projects, without requiring project-specific evaluator filters.
- **Dataset**: Feature MUST preserve existing CSV dataset support and use the dataset item identity already available to run and report workflows.
- **Langfuse Logging**: Feature MUST log a Langfuse session identifier on model-generation traces so baseline and candidate traces for the same dataset item and baseline comparison family are grouped together.
- **Prompt and Evaluator Versioning**: Feature MUST preserve existing prompt version, evaluator version, run ID, baseline run ID, dataset, and project metadata on traces and scores.
- **Baseline**: Feature consumes the selected or newly created baseline run as the comparison anchor; baseline traces use their own run identity as the baseline session anchor, and candidate traces use the referenced baseline run identity.
- **Human Review**: Feature MUST make it possible for reviewers to use the trace's Langfuse session to inspect baseline and candidate context for the same reviewed item.

### Functional Requirements

- **FR-001**: System MUST assign a deterministic item-level comparison session identifier to each Langfuse model-generation trace produced by baseline and candidate project runs.
- **FR-002**: System MUST group traces by project identity, project version when available, dataset identity, dataset version or compatible dataset fingerprint when available, baseline comparison anchor, and dataset item identity.
- **FR-003**: System MUST ensure the baseline trace for an item and all candidate traces for that same item and baseline comparison anchor use the same Langfuse session identifier.
- **FR-004**: System MUST ensure traces for different dataset items do not share a session identifier.
- **FR-005**: System MUST generate session identifiers that satisfy Langfuse session constraints: US-ASCII string values shorter than 200 characters.
- **FR-006**: System MUST sanitize, truncate, or hash identity components as needed while preserving deterministic grouping for the same comparison inputs.
- **FR-007**: System MUST continue to log existing run metadata, baseline references, prompt metadata, evaluator metadata, and comparison metadata independently from session membership.
- **FR-008**: System MUST NOT use Langfuse session membership as the authoritative source for aggregate reporting, evaluator targeting, or baseline/candidate matching.
- **FR-009**: System MUST expose the computed session identifier in trace metadata or local run output so operators can diagnose grouping issues without relying only on the Langfuse UI.
- **FR-010**: System MUST support multiple candidate runs sharing the same item-level comparison sessions when they compare against the same baseline anchor.
- **FR-011**: System MUST preserve existing human annotation queue selection behavior for failures, low-confidence items, and disputed items; sessions only add trace context for review.
- **FR-012**: System MUST include automated verification that proves same-item baseline/candidate traces share a session and different-item traces do not.
- **FR-013**: System MUST fail validation for candidate runs that do not have an explicit baseline reference before logging candidate comparison sessions.

### Key Entities *(include if feature involves data)*

- **Comparison Session**: A Langfuse session that groups model-generation traces for one dataset item across a baseline run and any candidate runs compared to that baseline.
- **Baseline Comparison Anchor**: The run identity used to define a comparison family; for baseline traces this is the baseline run's own ID, and for candidate traces this is the candidate's referenced baseline run ID.
- **Session Identity Inputs**: The stable fields used to derive a comparison session, including project identity, project version, dataset identity, dataset version or fingerprint, baseline comparison anchor, and dataset item identity.
- **Trace Session Link**: The trace-level Langfuse session identifier and companion metadata that lets users navigate from a trace or review item to the comparison session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test run with one baseline and one candidate over at least 3 dataset items, 100% of model-generation traces include a valid Langfuse session identifier.
- **SC-002**: For every tested item, the baseline trace and candidate trace share exactly one comparison session identifier, and no tested session contains traces from another item.
- **SC-003**: In a test with two candidate runs against the same baseline, candidate traces for the same item reuse the baseline item's comparison session.
- **SC-004**: Existing baseline and candidate report generation produces the same aggregate evaluator averages and run references as before session logging is enabled.
- **SC-005**: A reviewed candidate item can be traced to a Langfuse session containing its same-item baseline context without manual search by run ID.

## Assumptions

- Langfuse sessions are available through trace logging by setting a `sessionId` or equivalent SDK field on each trace.
- Langfuse treats identical session identifiers as one grouped session and ignores invalid session identifiers, so the harness must validate identifier shape before sending traces.
- Existing run IDs and baseline run references remain the canonical source for comparing and reporting experiment results.
- Session-level scoring, preference aggregation, and backfilling historical traces are out of scope for this feature.
- Manual session-level human scores in the Langfuse UI are a backlog enhancement after item-level session grouping is validated.
- Project-specific `.env.<project>` loading and automatic report generation are handled by prior work and are not changed by this feature.
