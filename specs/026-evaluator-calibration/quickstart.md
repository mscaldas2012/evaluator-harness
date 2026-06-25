# Quickstart: Automatic Evaluator Calibration Support

This guide describes the intended workflow for capturing and analyzing calibration data for an existing harness project.

## 1. Run a Baseline or Candidate

Use the normal harness workflow to produce a completed run:

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline
```

Calibration support builds on the run you already executed. It does not change baseline or candidate execution.

## 2. Select Calibration Items

Use the existing review workflow to sample or route important traces into Langfuse Human Annotation Queues:

```powershell
uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id>
```

Stable calibration cohorts should remain comparable across compatible runs. Risk-priority review items remain additive.

## 3. Capture a Calibration Snapshot

Capture a calibration snapshot for the completed run:

```powershell
uv run python run_experiment.py calibration-capture `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id>
```

Expected outputs:

- a machine-readable calibration snapshot file
- a row-level CSV beside the JSON snapshot
- warnings when live Langfuse trace retrieval is incomplete and the local run export is used to complete run context
- item-level records showing selection reason, score source, prompt/evaluator metadata, and pairing status

When completed Langfuse annotation queue items exist for the run, capture uses
those queue items as the primary calibration cohort. It intersects completed
queue item trace IDs with the run trace IDs, then retains evaluator rows with
both automated `EVAL` and human `ANNOTATION` scores. If no completed queue items
exist for the run, capture falls back to the stable review selection policy and
can emit pending-label rows.

## 4. Summarize Calibration Results

Generate per-evaluator calibration summaries from one snapshot:

```powershell
uv run python run_experiment.py calibration-summary `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id>
```

Expected summary fields:

- paired coverage
- disagreement rate
- mean absolute score delta
- directional bias
- pending label coverage

## 5. Inspect Results in Langfuse

Use Langfuse to inspect:

- the source traces
- evaluator scores
- human annotation scores
- disputed or low-confidence items
- the calibration queue items that fed the snapshot

Human review remains the calibration path; the harness only captures and summarizes what Langfuse already stores.

## 6. Verify the Feature Locally

Run the focused tests after implementation:

```powershell
uv run pytest --no-cov -p no:cacheprovider `
  tests/unit/test_calibration.py `
  tests/unit/test_langfuse_scores.py `
  tests/contract/test_cli_calibration.py `
  tests/integration/test_calibration_capture.py -vv
```

Calibration drift comparison is intentionally backlogged and is not part of the
active capture/summary workflow.
