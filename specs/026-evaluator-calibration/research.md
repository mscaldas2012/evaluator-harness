# Research: Automatic Evaluator Calibration Support

## Decision: Reuse Langfuse as the Source of Truth for Calibration Inputs

Calibration capture should read the same Langfuse traces, scores, and annotation queue records that already support run export and review selection.

**Rationale**: BL-007 is specifically about recording calibration evidence and summarizing disagreement. Langfuse already owns traces, evaluator scores, and human annotations, so duplicating that state locally would add complexity without improving fidelity.

**Alternatives considered**:

- Local calibration database: rejected because it would create a second system of record.
- CSV-only manual review exports: rejected because they lose the native Langfuse linkage and queue context.

## Decision: Use Existing Deterministic Review Sampling as the Calibration Cohort

The calibration snapshot should build on the current stable review cohort and review routing rules instead of introducing a new sampling scheme.

**Rationale**: Stable cohorts let baseline and compatible candidate runs be compared consistently. Reusing the existing selection logic also preserves the current meaning of `stable_calibration` versus run-risk review items.

**Alternatives considered**:

- Fresh calibration-only sampler: rejected because it would create a second cohort definition and make comparisons harder.
- Fully random sampling only: rejected because it would reduce reproducibility across runs.

## Decision: Represent Calibration Output as Filesystem Artifacts

Calibration capture should write run-scoped artifact files under the existing reports tree, with separate machine-readable outputs for snapshots, summaries, and drift views.

**Rationale**: The harness already emits CSV and report files locally. File artifacts are easy to inspect, diff, and reuse in later planning or analysis without requiring new infrastructure.

**Alternatives considered**:

- Database-backed summaries: rejected because the project constitution favors minimal local state.
- Langfuse-only calibration summaries: rejected because the backlog calls for exportable calibration datasets and disagreement summaries.

## Decision: Treat Missing Human Labels as Partial Data, Not a Hard Failure

If a review-selected item has not yet been labeled in Langfuse, the calibration snapshot should retain the record with a pending status.

**Rationale**: Human annotation completion may lag behind run completion. Failing the workflow would block useful snapshots and drift analysis for partially reviewed runs.

**Alternatives considered**:

- Fail on any missing label: rejected because it is too brittle for real review workflows.
- Drop unlabeled items silently: rejected because it hides the calibration coverage gap.

## Decision: Summaries Should Focus on Paired Coverage, Disagreement, and Score Delta

The first summary layer should report paired coverage, disagreement rate, mean absolute score delta, and directional bias by evaluator dimension.

**Rationale**: These metrics are easy to interpret, directly support prompt improvement, and align with the backlog goal of tracking evaluator disagreements and drift.

**Alternatives considered**:

- A broader statistical dashboard: rejected because it would overbuild the local harness.
- A single aggregate quality score: rejected because it obscures the direction and size of disagreement.

## Decision: Drift Should Compare Snapshot Windows, Not Live State

Drift summaries should compare one calibration snapshot window against a prior snapshot window for the same project and evaluator dimension.

**Rationale**: Snapshot-to-snapshot comparison is reproducible and easier to reason about than live rolling state.

**Alternatives considered**:

- Continuous live drift monitor: rejected because it implies a persistent service and more operational overhead.
- Manual spreadsheet comparison: rejected because it increases analysis friction and reduces repeatability.
