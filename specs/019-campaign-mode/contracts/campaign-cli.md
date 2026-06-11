# Contract: Campaign CLI

## Command

```powershell
uv run python run_experiment.py campaign `
  --project configs/projects/rewrite_quality.yaml
```

## Purpose

Run a complete baseline-centered evaluation campaign for a project: fresh baseline, all non-excluded candidates, CSV report exports, and final Excel comparison workbook.

## Options

| Option | Required | Description |
|--------|----------|-------------|
| `--project` | Yes | Project YAML path. |
| `--skip-sync` | No | Skip dataset and score-config sync before each run. |
| `--skip-human-review` | No | Disable automatic human review selection for campaign runs. |
| `--no-report` | No | Do not export CSV reports or create the Excel workbook. |
| `--overwrite` | No | Permit replacing an existing Excel workbook. |
| `--confirm-mixed-variant` | No | Permit included candidates that change prompt plus another comparison axis. |

## Selection Rules

1. Load and validate the project.
2. Include candidates that omit `exclude-from-campaign` or set `exclude-from-campaign: false`.
3. Skip candidates with `exclude-from-campaign: true`.
4. If no candidates are included, exit without running a baseline.

## Execution Rules

1. Run the baseline first.
2. Use the created baseline run ID as `--baseline` for every included candidate.
3. Attempt included candidates sequentially.
4. Export CSV reports under `reports/<project-name>/` unless `--no-report` is passed.
5. Create the Excel workbook from `reports/<project-name>/` after all attempted runs unless `--no-report` is passed.

## Successful Output

Console output MUST include:

```text
campaign: completed
baseline: <baseline-run-id>
candidate: <candidate-name> <candidate-run-id>
skipped: <candidate-name> <reason>
report: <csv-path>
excel-report: <xlsx-path>
```

When no candidates are eligible:

```text
campaign: skipped
reason: no candidates eligible for campaign
```

## Failure Output

If one or more candidate runs fail after the baseline succeeds, console output MUST include:

```text
campaign: completed-with-failures
failed: <candidate-name> <message>
```

The command MUST exit non-zero when baseline execution fails or when any included candidate fails. Successful run IDs and report paths MUST still be printed when available.
