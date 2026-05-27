# CLI Contract: LLM-as-Judges

## Existing Commands Affected

### `validate`

```powershell
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
```

Additional validation responsibilities:

- Evaluator has name, version, dimension, target, prompt reference, output
  schema, score target, judging mode, run-type eligibility, blind setting, and
  filter profile.
- Evaluator dimension is singular.
- Blind evaluator prompts do not expose provider/model placeholders.
- Non-blind evaluator definitions include a non-empty reason.
- Required inputs are available from dataset, baseline output, candidate output,
  or ground truth as declared.
- Observation-level evaluator filters include project identity and
  evaluator-set identity.

Success output should include evaluator count and evaluator versions.

Failure output should identify the evaluator and the invalid field.

### `sync-score-configs`

```powershell
uv run python run_experiment.py sync-score-configs --project configs/projects/rewrite_quality.yaml
```

Additional behavior:

- Confirms every evaluator score target resolves to a Langfuse score config.
- Reuses compatible harness-managed score configs.
- Confirms Human Annotation Queue score configs align with evaluator score
  targets for the same evaluator dimensions.
- Fails on incompatible harness-managed score config schemas.
- Leaves user-owned score configs unchanged.

### `run`

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline
```

Additional behavior:

- Model-output observations include evaluator filter metadata:
  - `project`
  - `project_version`
  - `dataset_name`
  - `dataset_compatibility_version`
  - `run_type`
  - `evaluator_set_id`
  - `prompt_version`
  - `observation_role=model_output`

## New Command Candidate

### `render-judge-prompts`

```powershell
uv run python run_experiment.py render-judge-prompts `
  --project configs/projects/rewrite_quality.yaml
```

Purpose:

- Print or write Langfuse-ready judge prompt text for each evaluator.
- Include evaluator name, version, score target, target type, and expected
  filter profile.

Output:

```text
evaluator: clarity/v1
target: observation role=model_output
score: eh_rewrite_quality_clarity
shared_with_human_annotation_queue: true
score_sources:
  llm_judge: EVAL
  human_annotation: ANNOTATION
filters:
  project: rewrite-quality
  project_version: v1
  evaluator_set_id: clarity:v1
  run_type: baseline,candidate
  observation_role: model_output
optional_narrowing:
  observation_name: OpenAI-generation
prompt: prompts/rewrite_quality/evaluators/clarity.md
```

Exit codes:

- `0`: prompts rendered successfully.
- `1`: project validation failed.
- `2`: prompt file missing or contains invalid placeholders.

## New Command Candidate

### `export-evaluator-setup`

```powershell
uv run python run_experiment.py export-evaluator-setup `
  --project configs/projects/rewrite_quality.yaml
```

Purpose:

- Generate a lightweight setup document with evaluator names, prompt files,
  score configs, and Langfuse filters.
- This is a helper for manual Langfuse configuration, not a local evaluator
  engine.

Output:

```text
reports/evaluator-setup-rewrite-quality-v1.md
```

Exit codes:

- `0`: setup file written.
- `1`: validation failed.
