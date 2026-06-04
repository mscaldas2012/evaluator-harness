# Data Model: Judge Evaluator Score Config Targeting

## Judge Evaluator Rule

Represents a Langfuse evaluator rule created, reused, audited, updated, or
inactivated by the harness.

### Fields

- `id`: Remote evaluator rule identifier.
- `name`: Harness-managed evaluator rule display name.
- `source_type`: Evaluator source, such as custom, catalog, or user-owned.
- `target`: Rule target, such as trace or observation.
- `filters`: Conditions selecting the traces or observations the rule applies
  to.
- `variables`: Mapping from evaluator prompt variables to trace or observation
  data.
- `sampling_percent`: Percentage of matching items evaluated.
- `active`: Whether the rule is enabled.
- `score_config_id`: Remote score config ID the rule writes produced scores to.
- `score_config_name`: User-readable score config name for display and audit
  context when known.

### Validation Rules

- Harness-managed created rules must have a non-empty `score_config_id`.
- Custom and catalog source types must both carry score config targets.
- Existing remote rules without a normalized score target are not considered
  fully aligned with the expected plan.
- User-owned evaluator rules are not mutated by this feature.

## Score Config Target

Represents the score definition that automated judge scores and human
annotation scores share for one evaluator dimension.

### Fields

- `name`: Score config name visible to users.
- `score_config_id`: Remote Langfuse score config ID.
- `ownership`: Harness-managed or user-owned.
- `data_type`: Numeric, categorical, or boolean score type.
- `allowed_score_sources`: Sources that may write scores, including LLM judge
  and human annotation when both are intended.

### Validation Rules

- Harness-managed score configs must be synced before apply-mode judge
  evaluator setup can target them.
- User-owned score configs must provide an ID in project configuration.
- Score config IDs used by evaluator rules and annotation queues should match
  for shared human/judge dimensions.

## Evaluator Setup Plan

Represents the planned operation for an evaluator before applying remote
changes.

### Fields

- `operation`: Create, reuse, update, inactivate, block, skip, or fail.
- `evaluator_name`: Project evaluator identifier.
- `managed_display_name`: Remote evaluator rule name.
- `source_type`: Evaluator source type.
- `target`: Rule target.
- `score_target.name`: Expected score config name.
- `score_target.score_config_id`: Expected score config ID.
- `changes`: Safe changes needed to align an existing remote rule.
- `reason`: Human-readable summary of the plan.
- `remediation`: Actionable next step when blocked or failed.

### State Transitions

- Missing remote rule with score config ID available -> `create`.
- Missing remote rule with score config ID unavailable in apply mode -> `block`.
- Existing harness-managed rule with matching score config -> `reuse`.
- Existing harness-managed rule with mismatched score config and update support
  -> `update`.
- Existing harness-managed rule with mismatched score config and no safe update
  path -> `fail` or `block` with remediation.
- Existing remote rule without local ownership evidence -> existing
  missing-binding warning behavior.

## Evaluator Binding

Local YAML record connecting project evaluator definitions to remote evaluator
rules.

### Fields

- `project`
- `project_version`
- `evaluator_name`
- `evaluator_version`
- `source_type`
- `target`
- `langfuse_evaluator_id`
- `langfuse_display_name`
- `score_config_id`
- `score_config_name`
- `judge_model`
- `llm_connection`
- `sampling_percent`
- `historical_backfill`
- `active`
- `last_synced_at`

### Validation Rules

- Binding score config fields must match the applied plan after create or
  update.
- Bindings must not contain secrets.
- Binding path must remain repository-local.

## Score Source Pairing

Conceptual relationship between judge scores and human annotation scores for
the same dimension.

### Fields

- `score_config_id`: Shared score config ID.
- `score_config_name`: Shared score config name.
- `llm_judge_source`: Automated evaluator rule score source.
- `human_annotation_source`: Human Annotation Queue score source.
- `target`: Same trace or observation target for paired comparison.

### Validation Rules

- Pairing is valid when both human and judge scores use the same score config
  for the same dimension.
- Pairing is not guaranteed when evaluator rules omit or mismatch score config
  IDs.
