# Contract: CLI Runtime for Candidate Variants

## Candidate Run Command

The existing candidate command remains the primary workflow:

```powershell
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode candidate --candidate <candidate-name> --baseline latest-compatible
```

`--baseline` remains optional and defaults to `latest-compatible`.

## Mixed Variant Confirmation

Before a candidate run begins, the CLI compares the selected candidate against
the project baseline across these axes:

- `model`: provider/auth/model identity differs
- `prompt`: candidate prompt identity differs from baseline prompt identity
- `params`: generation parameters differ

If more than one axis changed and `--confirm-mixed-variant` is absent, the CLI
must print an alert and prompt:

```text
Candidate variant changes multiple comparison axes: model, params.
Type Y to continue:
```

Only `Y` or `y` proceeds. Any other input cancels the run with a non-zero exit
code and a message:

```text
Candidate run cancelled.
```

Scripted runs may bypass the interactive prompt:

```powershell
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode candidate --candidate azure-mistral-large-3 --confirm-mixed-variant
```

## Metadata Contract

Candidate traces, model-output observations, evaluator payloads, review
payloads, and exports must include:

- candidate variant name
- run ID and run type
- baseline reference
- baseline prompt identity
- candidate prompt identity
- model identity
- parameter identity
- evaluator set ID
- dataset item identity
- observation role `model_output`

## Error Contract

Validation and runtime errors should identify:

- candidate name
- missing or invalid prompt identity when relevant
- baseline selector when baseline lookup fails
- changed axes when mixed-variant confirmation is required

Errors must not include provider credential values or other secrets.
