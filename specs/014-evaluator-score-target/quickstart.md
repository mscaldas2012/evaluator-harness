# Quickstart: Judge Evaluator Score Config Targeting

## Goal

Verify that Langfuse LLM-as-Judge evaluator rules target the same score configs
used by human annotation queues, enabling judge and human scores to be compared
under the same evaluation dimensions.

## 1. Validate The Project Config

```powershell
uv run python run_experiment.py validate --project configs/projects/dfe-general-public.yaml
```

Expected result: validation lists the project evaluators and score targets,
including `relevance=eh_gp_relevance`.

## Implementation Note

Evaluator setup uses local `score_config_id` as the normalized field name in
plans and bindings. Langfuse evaluator rule requests send that same target as
`scoreConfigId`. Project YAML should keep score intent by name; remote score
config IDs belong in sync results and binding files.

## 2. Sync Score Configs

```powershell
uv run python run_experiment.py sync-score-configs --project configs/projects/dfe-general-public.yaml
```

Expected result: each evaluator score config has a Langfuse score config ID.
These IDs are the targets for both judge evaluator rules and human annotation
queues.

## 3. Preview Judge Evaluator Setup

```powershell
uv run python run_experiment.py sync-judge-evaluators --project configs/projects/dfe-general-public.yaml --dry-run
```

Expected result: every planned judge evaluator shows the intended score config
name and ID. If an ID is unavailable, the preview explains that score config
sync must be applied before judge evaluator setup.

## 4. Apply Judge Evaluator Setup

```powershell
uv run python run_experiment.py sync-judge-evaluators --project configs/projects/dfe-general-public.yaml
```

Expected result: each created or updated Langfuse evaluator rule targets the
resolved score config ID for its evaluator dimension.

## 5. Sync Human Annotation Queue

```powershell
uv run python run_experiment.py sync-annotation-queue --project configs/projects/dfe-general-public.yaml
```

Expected result: the queue uses the same score config IDs as the judge
evaluator rules.

## 6. Run Regression Tests

```powershell
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_langfuse_evaluator_rest.py tests/unit/test_judge_setup_planner.py tests/unit/test_judge_setup_audit.py tests/integration/test_sync_judge_evaluators.py tests/contract/test_cli_sync_judge_evaluators.py
```

Expected result: tests pass and fail if evaluator rule creation omits score
config targeting.

## Notes

- Generated binding files are local sync state unless the team intentionally
  shares the same Langfuse project IDs.
- Apply-mode judge evaluator setup should not create evaluator rules without
  score config IDs.
- Existing remote evaluator rules without local harness-managed binding evidence
  should not be silently mutated.
