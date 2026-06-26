# Research: Campaign Calibration Report

## Decision: Baseline Run ID Is the User-Facing Campaign Anchor

**Rationale**: The current campaign implementation does not persist a first-class campaign ID. It already names comparison reports and exports around the baseline run ID, and existing comparison report generation takes `baseline_run_id` as its primary selector. Requiring `--baseline <baseline-run-id>` matches the current mental model and avoids inventing a new identifier.

**Alternatives considered**:
- `--campaign <campaign-id>`: rejected for v1 because no campaign ID exists today and adding one would require a broader campaign identity model.
- `--comparison <path>`: useful as a fallback but less ergonomic than a stable run ID and harder to use in repeated commands.

## Decision: Add a Campaign Manifest and Use It Before Fallback Artifacts

**Rationale**: Campaign execution currently returns baseline/candidate run IDs in memory, but the delayed calibration workflow may happen hours or days later. A local manifest gives the post-campaign command a durable source of truth for baseline and candidate run references. Existing comparison/export artifacts remain a fallback so older campaigns without a manifest can still be calibrated.

**Alternatives considered**:
- Only parse comparison/export artifacts: rejected because report/export parsing is a recovery path, not an explicit campaign record.
- Require a manifest and fail otherwise: rejected because it would block calibration for campaigns already run before this feature exists.

## Decision: Compose Existing Single-Run Calibration Capture and Summary

**Rationale**: `ExperimentRunner.calibration_capture()` and `ExperimentRunner.calibration_summary()` already implement trace/score retrieval, annotation queue matching, snapshot writing, and metric calculation. Campaign calibration should call those per run and aggregate the results rather than duplicate score-pairing logic.

**Alternatives considered**:
- Build a new campaign-specific pairing engine: rejected because it risks diverging from single-run calibration semantics.
- Generate only an HTML report from existing summaries: rejected because users need one command to capture and summarize after human review.

## Decision: Overwrite Campaign Calibration Artifacts on Rerun

**Rationale**: The user clarified that reruns should regenerate snapshots, summaries, and the HTML report from the latest available Langfuse state. This supports the expected workflow where annotations may be completed incrementally after the campaign.

**Alternatives considered**:
- Preserve richer snapshots: rejected by clarification in favor of latest-state overwrite.
- Require `--overwrite`: rejected because rerun-after-annotation is a normal workflow, not an exceptional destructive action.

## Decision: Treat Missing Human Annotations as Warnings, Technical Failures as Failures

**Rationale**: Partial human annotation is an expected operating mode, so missing labels or zero paired coverage should be visible warnings while allowing other runs to produce artifacts. Technical blockers that prevent resolving run IDs, reading required artifacts, or writing outputs should fail the command because automation cannot trust the result.

**Alternatives considered**:
- Fail on any missing annotation: rejected because the spec requires partial completion tolerance.
- Always exit success with warnings: rejected because unreadable artifacts or unresolved baseline/candidate identities are actionable execution failures.

## Decision: Static HTML Report Reuses Local Report Style but Uses Calibration-Specific Payload

**Rationale**: Existing `html_reports.py` provides a proven self-contained report style, but comparison report payloads are score/export oriented rather than calibration-summary oriented. A new campaign calibration report payload should include run coverage, evaluator alignment metrics, warnings, and paired detail rows while borrowing the visual conventions and plain-file output approach.

**Alternatives considered**:
- Extend `ComparisonReportPayload`: rejected because it would mix campaign comparison scores and calibration alignment metrics into one model.
- Emit JSON only: rejected because the user explicitly needs a shareable HTML report like the ad-hoc report.
