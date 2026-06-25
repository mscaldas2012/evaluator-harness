# Data Model: Automatic Evaluator Calibration Support

## CalibrationSnapshot

Run-scoped calibration artifact capturing all evidence needed to inspect evaluator behavior for a completed run.

Fields:

- `project_name`: harness project identifier.
- `project_version`: project version.
- `run_id`: baseline or candidate run being calibrated.
- `run_type`: baseline or candidate.
- `dataset_name`: Langfuse dataset identity.
- `dataset_version`: dataset compatibility or version marker.
- `review_policy_version`: stable review policy version used for selection.
- `generated_at`: snapshot timestamp.
- `status`: snapshot status such as complete or partial.
- `warnings`: retrieval or pairing warnings captured during snapshot generation.

Validation:

- Must retain run identity and project identity.
- Must preserve whether the snapshot is complete or partial.
- Must preserve deterministic review-policy context for reproducibility.

## CalibrationRecord

One reviewed item in a calibration snapshot.

Fields:

- `item_id`: dataset item identifier.
- `trace_id`: Langfuse trace identifier.
- `selection_reason`: review reason such as sample, failure, low_confidence, or disputed.
- `selection_bucket`: stable_calibration or run_risk.
- `evaluator_name`: evaluator dimension or name.
- `evaluator_version`: evaluator version.
- `score_target`: canonical Langfuse score config for the dimension.
- `automated_score`: automated evaluator score, if available.
- `automated_score_source`: normalized source for automated scoring.
- `human_score`: completed human annotation score, if available.
- `human_score_source`: normalized source for human scoring.
- `score_delta`: human minus automated score when both are available.
- `paired`: whether both automated and human scores are present.
- `pending_label`: whether the human label is missing at capture time.
- `disagreement`: whether the automated and human scores materially disagree.

Validation:

- A record must always preserve item and trace identity.
- A record may be partial when one score source is missing.
- A record must not be duplicated when the same item is already sampled for review.
- A record should be deterministic for the same input traces and scores.

## CalibrationSummary

Aggregated evaluator-level summary derived from calibration records.

Fields:

- `project_name`: project identifier.
- `project_version`: project version.
- `run_id`: source run identifier.
- `evaluator_name`: evaluator dimension.
- `paired_count`: number of records with both score sources.
- `pending_count`: number of records awaiting human labels.
- `paired_coverage`: paired_count divided by total calibration records.
- `disagreement_rate`: fraction of paired records that disagree.
- `mean_absolute_score_delta`: average absolute difference for paired records.
- `directional_bias`: average signed difference for paired records.
- `warnings`: summary-level warnings.

Validation:

- Metric calculations must be deterministic.
- Summaries must preserve evaluator dimension and project context.
- Summary output should clearly distinguish paired versus pending records.

## DriftSummary

Comparison artifact showing how calibration metrics change over time.

Fields:

- `project_name`: project identifier.
- `project_version`: project version.
- `evaluator_name`: evaluator dimension.
- `current_snapshot`: current snapshot reference.
- `baseline_snapshot`: previous snapshot reference.
- `paired_coverage_delta`: change in paired coverage.
- `disagreement_rate_delta`: change in disagreement rate.
- `mean_absolute_score_delta_delta`: change in mean absolute score delta.
- `directional_bias_delta`: change in directional bias.
- `warnings`: comparison warnings.

Validation:

- Drift comparisons require at least two snapshots for the same project and evaluator dimension.
- Drift output must retain the snapshot references used in the comparison.
