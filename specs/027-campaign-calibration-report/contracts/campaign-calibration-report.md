# CLI Contract: campaign-calibration-report

## Command

```text
eval campaign-calibration-report --project <project> --baseline <baseline-run-id> [options]
```

Equivalent script form:

```text
uv run python run_experiment.py campaign-calibration-report --project <project> --baseline <baseline-run-id>
```

## Required Options

### `--project <project>`

Project YAML path or project name resolvable by the existing project resolver.

### `--baseline <baseline-run-id>`

Baseline run ID that anchors the campaign. The command always includes this run in capture, summary, and report outputs.

## Optional Options

### `--reports-dir <path>`

Override the project reports directory used for manifest discovery, fallback CSV discovery, and report output.

### `--output <path>`

Write the campaign calibration HTML report to an explicit `.html` path.

### `--output-dir <path>`

Write the campaign calibration HTML report to a directory using the default filename `<baseline-run-id>-calibration-report.html`.

## Behavior

1. Load and validate the project config.
2. Resolve the campaign run list:
   - First read a campaign manifest for the provided baseline run ID when present.
   - If no usable manifest exists, discover the baseline and candidate run IDs from existing comparison/export artifacts.
   - If neither source identifies at least the baseline run, fail with a clear message.
3. For each resolved run reference:
   - Run calibration capture using existing single-run capture semantics.
   - Run calibration summary using existing single-run summary semantics.
   - Record warnings without stopping other runs when a run has missing annotations or zero paired coverage.
4. Generate one static HTML report after per-run processing.
5. Overwrite generated campaign calibration snapshots, summaries, and HTML report from the latest available Langfuse state on every run.

## Output Artifacts

Default locations are under the project reports directory:

```text
reports/<project>/
|-- campaign-manifests/
|   `-- <baseline-run-id>.json
|-- calibration/
|   |-- <run-id>.json
|   |-- <run-id>.csv
|   `-- <run-id>-summary.json
`-- <baseline-run-id>-calibration-report.html
```

## Console Output

On success or partial success, print:

```text
campaign-calibration: completed
baseline: <baseline-run-id>
runs: <count>
captured: <count>
summarized: <count>
report: <path>
warning-count: <count>
warning: <message>
```

When technical failures prevent report generation, print the existing CLI error format and exit nonzero.

## Exit Semantics

- Exit `0` when at least the baseline run can be processed and an HTML report is written, even if some runs have missing human annotations.
- Exit nonzero when the baseline run cannot be resolved, required artifacts cannot be read, Langfuse retrieval fails in a way that prevents capture, or output files cannot be written.

## Examples

Baseline-only campaign:

```text
eval campaign-calibration-report --project dfe-general-public --baseline baseline-2e1c28df5f97
```

Explicit output directory:

```text
eval campaign-calibration-report --project dfe-general-public --baseline baseline-2e1c28df5f97 --output-dir reports/dfe-general-public
```
