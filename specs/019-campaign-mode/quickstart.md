# Quickstart: Campaign Mode

## Configure Candidate Inclusion

Campaign candidates are included by default. Set `exclude-from-campaign: true` only for candidates that should be skipped.

```yaml
candidates:
  - name: gpt5.2-dgw-default-prompt-v2
    provider: openai_compatible
    auth_mode: azure_client_credentials
    model: gpt5.2-dgw-default
    parameters:
      temperature: 0.2
      top_p: 1.0
      max_tokens: 2048

  - name: dry-run-candidate
    exclude-from-campaign: true
    provider: dry_run
    auth_mode: none
    model: dry-run
    parameters:
      temperature: 0.0
      top_p: 1.0
      max_tokens: 2048
```

Candidates that omit `exclude-from-campaign` are treated as included.

## Run Campaign

```powershell
uv run python run_experiment.py campaign `
  --project configs/projects/rewrite_quality.yaml
```

Expected summary shape:

```text
campaign: completed
baseline: baseline-abc123
candidate: gpt5.2-dgw-default-prompt-v2 candidate-def456
skipped: dry-run-candidate exclude-from-campaign=true
report: reports/rewrite-quality/baseline-abc123.csv
report: reports/rewrite-quality/candidate-def456.csv
excel-report: reports/rewrite-quality/baseline-abc123-comparison.xlsx
```

## Skip Sync Or Human Review

```powershell
uv run python run_experiment.py campaign `
  --project configs/projects/rewrite_quality.yaml `
  --skip-sync `
  --skip-human-review
```

## Recreate Workbook

Use `--overwrite` when the campaign workbook path already exists.

```powershell
uv run python run_experiment.py campaign `
  --project configs/projects/rewrite_quality.yaml `
  --overwrite
```

## No Eligible Candidates

If all candidates are excluded, campaign mode does not run the baseline:

```text
campaign: skipped
reason: no candidates eligible for campaign
```
