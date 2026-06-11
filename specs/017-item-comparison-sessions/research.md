# Research: Langfuse Item Comparison Sessions

## Decision: Use Official Langfuse Sessions

**Rationale**: Langfuse sessions group observations and traces when the official
session field is set. A metadata-only `session_id` would be searchable but would
not provide the native session grouping and replay/inspection workflow.

**Alternatives considered**:

- Store only `session_id` in trace metadata. Rejected because it does not create
  Langfuse session grouping.
- Build local comparison pages from exports. Rejected because Langfuse is the
  system of record and already provides trace/session inspection.

## Decision: One Session Per Dataset Item Comparison Family

**Rationale**: A run-level or campaign-level session would group too many traces
and make review noisy. Item-level sessions let an evaluator inspect exactly one
input across its baseline and candidate outputs.

**Alternatives considered**:

- One session per baseline/candidate run pair. Rejected because it still groups
  unrelated dataset items.
- One session per trace. Rejected because it provides no comparison value.

## Decision: Baseline Run ID Is The Comparison Anchor

**Rationale**: Candidate comparison already depends on a baseline reference. The
baseline run ID is the stable identity that lets later candidates join the same
item-level comparison family. Baseline traces use their own run ID as the
anchor; candidate traces use the referenced baseline run ID.

**Alternatives considered**:

- Use candidate run ID in the session. Rejected because each candidate would
  create a separate session and lose cross-candidate comparison.
- Use only dataset item ID. Rejected because it would collide across projects,
  datasets, versions, and baseline reruns.

## Decision: Deterministic Sanitized/Hashed Session IDs

**Rationale**: Langfuse session identifiers must be US-ASCII and shorter than
200 characters. Existing project, dataset, and item identities may contain
punctuation, spaces, long values, or future non-ASCII input. A deterministic
canonical payload plus a short hash keeps grouping stable and valid.

**Alternatives considered**:

- Concatenate raw identity fields. Rejected because raw values may violate
  Langfuse constraints or exceed the length limit.
- Use a random UUID. Rejected because candidate runs could not reproduce the
  baseline item's session ID.

## Decision: Keep Run Metadata Authoritative

**Rationale**: Existing reports, evaluator targeting, baseline lookup, and
human review selection operate on run IDs, baseline references, trace metadata,
and scores. Sessions improve navigation but should not become the source of
truth for aggregate comparison.

**Alternatives considered**:

- Use Langfuse session membership to infer baseline/candidate matching.
  Rejected because that would make reporting depend on observability grouping
  and complicate backfill/historical trace behavior.

## Decision: Fail Candidate Runs Without Baseline Reference

**Rationale**: Candidate sessions must join the correct baseline item session.
Allowing a fallback session would hide an invalid candidate comparison and make
later reports harder to trust.

**Alternatives considered**:

- Create run-local candidate sessions. Rejected because it contradicts the
  baseline-centric workflow and obscures configuration errors.
- Make fallback behavior configurable. Rejected for v1 because the feature
  should have one clear comparison contract.

## Decision: Defer Session-Level Scoring

**Rationale**: Session-level human or programmatic scoring is valuable only
after grouping is reliable. Keeping v1 focused avoids coupling a new review
scoring workflow to the session infrastructure.

**Alternatives considered**:

- Include manual Langfuse UI session scores in v1. Deferred to backlog.
- Include programmatic session scores via SDK/API in v1. Deferred because the
  current need is trace organization, not a new scoring contract.
