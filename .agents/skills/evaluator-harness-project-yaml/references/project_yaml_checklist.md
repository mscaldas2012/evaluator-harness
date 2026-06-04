# Project YAML Checklist

Use this checklist when generating an Evaluator Harness project YAML.

## Required Local Artifacts

- Dataset path and kind, usually `local_csv`
- Task prompt path and prompt version
- Evaluator prompt paths or rubric file
- Project slug and version
- Baseline model config
- Candidate model configs
- Score config definitions
- Optional human review policy

## Questions To Ask When Missing

Project identity:

- What project slug should be used?
- What project version should be used, usually `v1`?
- What Langfuse dataset name should be used?

Dataset:

- Which column is the model input?
- Is there a stable unique ID column?
- Are there ground truth or reference output columns?
- Should extra columns be passed into prompt/evaluator variables?

Task prompt:

- Which prompt file should the baseline use?
- What prompt version label should be used?
- Is the prompt text or chat-role based?
- Which dataset fields should populate prompt variables?

Baseline:

- Which provider/model/deployment should the baseline use?
- Which auth mode and environment variable names should be referenced?
- What parameters should be set, such as temperature, max tokens, seed, or top_p?
- What output field or observation role should be evaluated?

Candidates:

- Which candidate variants are planned?
- Is each variant changing prompt, model, parameters, or a mix?
- Does any candidate need `--confirm-mixed-variant` because it changes multiple
  axes?
- Should a candidate use the same task prompt as baseline or an override prompt?

Evaluators and scores:

- What dimensions should be scored?
- Is each dimension a single atomic metric?
- Should the evaluator target `observation/model_output` or another target?
- What score config name should each metric use?
- What score range or type should each metric use?
- Does any evaluator require `ground_truth`, `reference_output`, or
  `baseline_output`?

Human review:

- Should `human_review.enabled` be true?
- What queue name/version should be used?
- What score configs should reviewers see?
- What sample percent should be used?
- What `minimum_sample_count` should be used?
- Should `sample_strategy` be `stable` or `random`?

## Validation Commands

Local-only validation:

```powershell
uv run python run_experiment.py validate --project configs/projects/<project>.yaml
```

Remote sync preview:

```powershell
uv run python run_experiment.py sync-all --project configs/projects/<project>.yaml --dry-run
```

Remote sync apply:

```powershell
uv run python run_experiment.py sync-all --project configs/projects/<project>.yaml
```
