# Quickstart: Candidate Variants

## Validate the Project

```powershell
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
```

Expected output includes the project, dataset, baseline, candidates,
evaluators, evaluator targets, and score targets.

## Run or Reuse a Baseline

```powershell
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode baseline
```

Save the baseline run ID from the command output, or use
`--baseline latest-compatible` for later candidate runs.

## Run a Model Variant

```powershell
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode candidate --candidate azure-mistral-large-3 --baseline latest-compatible
```

If the candidate changes multiple axes, the CLI asks for confirmation before
execution. Type `Y` or `y` to proceed.

For scripted runs:

```powershell
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode candidate --candidate azure-mistral-large-3 --baseline latest-compatible --confirm-mixed-variant
```

## Configure a Prompt Variant

Add a candidate-level prompt override:

```yaml
candidates:
  - name: gpt5.2-dgw-default-prompt-v2
    provider: openai_compatible
    auth_mode: azure_client_credentials
    model: gpt5.2-dgw-default
    task_prompt:
      path: prompts/rewrite_quality/task_prompt_v2.md
      version: v2
      template_variables:
        - input
    parameters:
      temperature: 0.2
      top_p: 1.0
      max_tokens: 2048
      token_limit_parameter: max_completion_tokens
```

Then run:

```powershell
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode candidate --candidate gpt5.2-dgw-default-prompt-v2 --baseline latest-compatible
```

Prompt-v2 candidate output is compared against the existing compatible
prompt-v1 baseline output.

## Configure Parameter Variants

Use separate candidate names for each parameter set:

```yaml
candidates:
  - name: gpt5.2-dgw-default-temp-02
    model: gpt5.2-dgw-default
    parameters:
      temperature: 0.2
      top_p: 1.0
      max_tokens: 2048
  - name: gpt5.2-dgw-default-temp-08
    model: gpt5.2-dgw-default
    parameters:
      temperature: 0.8
      top_p: 1.0
      max_tokens: 2048
```

Run each candidate separately and compare scores in Langfuse by project,
dataset item, evaluator, baseline reference, candidate variant, and run ID.

## Verify

Default non-live verification:

```powershell
uv run pytest -p no:cacheprovider
```

Optional live verification requires Langfuse and provider credentials:

```powershell
$env:RUN_LIVE_TESTS='1'
uv run pytest --no-cov -m live -vv
```

## Verification Notes

Recorded on 2026-05-28:

- `uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml`
  passed. Output included `rewrite-quality/v1`, dataset `local_csv (2 items)`,
  baseline `gpt5.2-dgw-default`, candidates
  `gpt5.2-dgw-default-prompt-v2`, `gpt5.2-dgw-default-temp-high`,
  `dry-run-candidate`, and `azure-mistral-large-3`, evaluator target
  `clarity=observation/model_output`, and score target
  `clarity=eh_rewrite_quality_clarity`.
- `uv run pytest -p no:cacheprovider` was attempted but pytest-cov failed
  before test collection with `PermissionError: [WinError 5] Access is denied:
  '.coverage'`.
- `uv run pytest --no-cov -p no:cacheprovider` passed with `240 passed,
  8 skipped`.
- Optional live smoke tests were not run in this implementation pass because
  they require live Langfuse/provider credentials and network access.
- Langfuse trace inspection was covered by fake-client tests for variant
  metadata, baseline reference, prompt identity, parameter identity, and secret
  absence; manual live workspace inspection was not run.
