# Contract: Project Config References

## Scenario Project Shape

Scenario project configs remain normal project YAML files. They may add
`scenario` and `config_refs`:

```yaml
project:
  name: dfe-general-public
  description: Evaluate DFE rewrites for the General public scenario.
  version: v1
  score_config_prefix: eh_dfe_
  metadata:
    environment: local
    tags:
      - dfe
      - readability

scenario:
  group: dfe
  name: general_public
  display_name: General public

config_refs:
  evaluation: configs/shared/dfe_readability.yaml

dataset:
  kind: local_csv
  path: datasets/DFE.csv
  langfuse_dataset_name: dfe/general-public/v1
  item_id_strategy: explicit_or_hash

task_prompt:
  path: prompts/dfe/task_prompt_generic.md
  version: v1
  template_variables:
    - dataset.input

baseline:
  ...

candidates:
  ...
```

## Shared Evaluation Config Shape

The referenced shared evaluation file may define only evaluation and review
sections:

```yaml
judge_setup:
  default_judge_model: gpt-4.1
  default_sampling_percent: 100
  historical_backfill: disabled

evaluators:
  - name: lists_preserved
    type: llm_as_judge
    version: v1
    ...

human_review:
  enabled: true
  queue_ownership: managed_by_harness
  review_policy_version: default
  minimum_sample_percent: 5
  prioritize:
    - failures
    - low_confidence
    - disputed
```

## Resolution Semantics

1. Load the scenario project YAML.
2. If `config_refs.evaluation` is absent, validate the project as today.
3. If `config_refs.evaluation` is present:
   - Resolve the path relative to the project file first, then relative to the
     repository root for existing project-style paths.
   - Load the shared evaluation YAML.
   - Reject any disallowed fields in the shared evaluation YAML.
   - Reject any local fields that conflict with supplied shared fields:
     `evaluators`, `judge_setup`, or `human_review`.
   - Merge allowed shared fields into the raw project document.
4. Validate the merged effective project config.

## Error Contract

Validation must fail before Langfuse mutation with clear messages for:

- Missing shared evaluation reference.
- Unreadable or invalid shared evaluation YAML.
- Disallowed shared config sections such as `dataset`, `task_prompt`,
  `baseline`, or `candidates`.
- Local/shared conflicts on `evaluators`, `judge_setup`, or `human_review`.
- Incomplete scenario identity when `scenario` is present.

## Metadata Contract

When scenario identity is present, emitted metadata includes:

```text
scenario_group
scenario_name
scenario_display_name
```

These fields must be included in:

- Langfuse run metadata.
- Langfuse trace metadata.
- CSV exports.
- Annotation queue review payload `trace_context`.
