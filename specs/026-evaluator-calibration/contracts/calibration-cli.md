# CLI Contract: Automatic Evaluator Calibration Support

## Scope

Defines the CLI-facing calibration workflow for capturing snapshots, generating summaries, and comparing calibration drift.

## Existing Commands Affected

### `run`

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline
```

Calibration support must not change run execution semantics.

Additional behavior:

- Completed runs continue to emit the existing review selection result when human review is enabled.
- Run output remains the source for later calibration capture.

### `select-review`

```powershell
uv run python run_experiment.py select-review `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id>
```

Additional behavior:

- Review selection remains the intake path for stable calibration items and run-risk items.
- Selected items must preserve `selection_reason` and `selection_bucket` so calibration capture can distinguish cohort and risk items.

## New Command Candidate

### `calibration-capture`

```powershell
uv run python run_experiment.py calibration-capture `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id>
```

Purpose:

- Capture a run-scoped calibration snapshot from Langfuse traces, evaluator scores, and human annotation labels.
- Write a machine-readable calibration artifact under the project report directory.

Expected output:

```text
reports/rewrite-quality/calibration/<run-id>.json
reports/rewrite-quality/calibration/<run-id>.csv
```

Output responsibilities:

- include one record per calibration item
- preserve review selection metadata
- preserve evaluator and prompt versions when available
- mark unlabeled items as pending rather than failing the capture
- warn when score or annotation retrieval is incomplete

Exit codes:

- `0`: snapshot written successfully, including partial snapshots with warnings.
- `1`: project validation failed or the run cannot be resolved.

## New Command Candidate

### `calibration-summary`

```powershell
uv run python run_experiment.py calibration-summary `
  --project configs/projects/rewrite_quality.yaml `
  --run <run-id>
```

Purpose:

- Summarize one calibration snapshot by evaluator dimension.
- Report paired coverage, disagreement rate, mean absolute score delta, and directional bias.

Expected output:

```text
reports/rewrite-quality/calibration/<run-id>-summary.json
```

Exit codes:

- `0`: summary written successfully.
- `1`: snapshot cannot be loaded or is invalid.

## New Command Candidate

### `calibration-drift`

```powershell
uv run python run_experiment.py calibration-drift `
  --project configs/projects/rewrite_quality.yaml `
  --current <run-id> `
  --baseline <previous-run-id>
```

Purpose:

- Compare calibration summaries across two snapshots for the same project and evaluator dimension.
- Produce drift metrics and warnings when no prior comparable snapshot exists.

Expected output:

```text
reports/rewrite-quality/calibration/<current-run-id>-drift.json
```

Exit codes:

- `0`: drift output written successfully.
- `1`: snapshots cannot be resolved or are incompatible.

## Output Contract

Calibration artifacts must preserve:

- project identity
- project version
- run identity
- run type
- dataset identity
- review policy version
- evaluator identity and version
- score target identity
- score source metadata
- pairing status
- warnings for incomplete retrieval

## Validation Contract

- Calibration capture must not fail solely because a human label is missing.
- Calibration summaries must be deterministic for identical inputs.
- Drift summaries require at least two comparable snapshots.
- Calibration commands must remain optional and must not alter baseline or candidate execution semantics.
