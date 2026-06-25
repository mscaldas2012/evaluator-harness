# Quickstart: Campaign Calibration Report

## 1. Run the Campaign

```text
uv run python run_experiment.py campaign --project configs/projects/dfe-general-public.yaml --report-format html
```

Record the baseline run ID printed by the campaign output. The campaign should also write normal run exports and comparison reports under `reports/<project>/`.

## 2. Complete Human Annotation

Open the Langfuse Human Annotation Queue items selected by the campaign and complete the relevant reviews. This may happen hours or days after the campaign command finishes.

The campaign calibration command can run with partial annotation completion. Missing labels appear as warnings and pending coverage in the final report.

## 3. Generate Campaign Calibration Artifacts

```text
uv run python run_experiment.py campaign-calibration-report --project configs/projects/dfe-general-public.yaml --baseline baseline-2e1c28df5f97
```

The command resolves the baseline and candidates from the campaign manifest when available, then falls back to existing comparison/export artifacts.
On success, the console output includes `report: reports/<project>/<baseline-run-id>-calibration-report.html`.

## 4. Inspect Outputs

Default outputs:

```text
reports/dfe-general-public/calibration/<run-id>.json
reports/dfe-general-public/calibration/<run-id>.csv
reports/dfe-general-public/calibration/<run-id>-summary.json
reports/dfe-general-public/<baseline-run-id>-calibration-report.html
```

Open the HTML report in a browser. It should show:

- baseline and candidate run identities
- evaluator-level paired coverage
- disagreement rate
- mean absolute score delta
- directional bias
- largest run/evaluator deltas
- warnings for missing annotations or failed run processing

## 5. Rerun After More Annotation

After additional queue items are annotated, rerun the same command:

```text
uv run python run_experiment.py campaign-calibration-report --project configs/projects/dfe-general-public.yaml --baseline baseline-2e1c28df5f97
```

Snapshots, summaries, and the HTML report are regenerated from the latest available Langfuse state.
