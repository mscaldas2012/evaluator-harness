# Quickstart: Langfuse Item Comparison Sessions

## Goal

Verify that baseline and candidate traces for the same dataset item appear in
the same Langfuse session while reports still use run-level comparison
metadata.

## Run A Baseline

```powershell
uv run python run_experiment.py run --project configs/projects/gso.yaml --mode baseline
```

Record the returned baseline run ID.

## Run A Candidate Against The Baseline

```powershell
uv run python run_experiment.py run --project configs/projects/gso.yaml --mode candidate --candidate <candidate-name> --baseline <baseline-run-id>
```

## Verify In Langfuse

Open a candidate trace for one dataset item.

Expected behavior:

- The trace has an official Langfuse session.
- The session contains the candidate trace and the baseline trace for the same
  dataset item.
- Other dataset items are not grouped into that session.
- The trace metadata includes `item_comparison_session_id` for diagnostics.

## Verify Reports Still Work

Export or generate reports for the baseline and candidate runs.

Expected behavior:

- Report aggregation still uses `run_id`, `baseline_run_id`, and evaluator
  scores.
- Session membership does not change evaluator averages.
- CSV exports include the diagnostic session ID when implemented.

## Verification Commands

Run focused tests:

```powershell
uv run pytest -p no:cacheprovider tests/unit/test_session_identity.py tests/integration/test_item_comparison_sessions.py tests/contract/test_cli_item_comparison_sessions.py
```

Run existing trace/report tests that should remain compatible:

```powershell
uv run pytest -p no:cacheprovider tests/unit/test_live_trace_metadata.py tests/unit/test_exports.py tests/contract/test_cli_export.py
```

## Notes

- This feature does not add session-level human scores in v1.
- Manual Langfuse UI session scoring is backlog after grouping is validated.
- Candidate runs must provide or resolve an explicit baseline reference.
