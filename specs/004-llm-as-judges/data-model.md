# Data Model: LLM-as-Judges

## JudgeEvaluator

Project-owned definition for one LLM-as-Judge evaluator.

Fields:

- `name`: stable evaluator identifier, unique within the project.
- `version`: evaluator definition version.
- `dimension`: single quality dimension being evaluated.
- `target`: `observation` by default; `trace` only when full workflow context
  is required.
- `target_observation_role`: default `model_output` for observation
  evaluators.
- `target_observation_name`: optional provider-specific observation name used
  only as an additional narrowing filter.
- `run_types`: allowed run types: `baseline`, `candidate`, or both.
- `mode`: `single_output` or `baseline_comparison`.
- `blind`: defaults to `true`; whether provider/model/run identity must be
  hidden from judge input.
- `non_blind_reason`: required only when `blind=false`; explains why provider,
  model, or run identity is intentionally part of the evaluation.
- `required_inputs`: required input names for the evaluator.
- `prompt_ref`: project prompt file and prompt version.
- `output_schema`: structured judge result schema.
- `score`: Langfuse score config reference.
- `filter_profile`: targeting rules for Langfuse evaluator configuration.

Validation:

- `name`, `version`, `dimension`, `target`, `run_types`, `mode`, `prompt_ref`,
  `output_schema`, `score`, and `filter_profile` are required.
- `dimension` must describe one evaluation dimension only.
- `target=observation` requires `target_observation_role`.
- `blind=true` forbids provider/model/vendor placeholders in prompt text.
- `blind=false` requires `non_blind_reason`.
- Model-quality and baseline/candidate comparison evaluators should remain
  blind unless the evaluator is intentionally provider-specific or diagnostic.
- `baseline_comparison` requires baseline output availability.

## JudgePrompt

Versioned prompt asset used to configure a Langfuse evaluator.

Fields:

- `path`: prompt file path.
- `version`: prompt version.
- `dimension`: evaluator dimension.
- `input_variables`: variables expected by the prompt.
- `output_schema`: expected structured fields.

Validation:

- Prompt version changes when scoring instructions materially change.
- Prompt must instruct the judge to evaluate only the declared dimension.
- Prompt must instruct the judge to return structured output.

## EvaluatorFilterProfile

Targeting definition for where a Langfuse evaluator should run.

Fields:

- `target`: `observation` or `trace`.
- `observation_role`: default `model_output`.
- `observation_name`: optional provider-specific observation name.
- `project`: project name.
- `project_version`: project version.
- `evaluator_set_id`: stable evaluator set identifier.
- `environment`: environment name when configured.
- `run_types`: allowed run types.

Validation:

- Must include project identity and evaluator set identity.
- Must not match all harness projects by default.
- Must not rely on item-specific trace names.
- Must not rely solely on provider-specific observation names.

## JudgeInputPackage

Sanitized values made available to a judge prompt.

Fields:

- `input`: original dataset input.
- `output`: model output under evaluation.
- `baseline_output`: optional baseline output.
- `ground_truth`: optional dataset ground truth.
- `anonymous_labels`: stable non-provider labels when comparing outputs.
- `metadata`: non-identifying evaluator context.

Validation:

- Blind packages exclude provider names, model names, vendor names, and run
  labels.
- Required inputs must be present before evaluator setup is considered valid.

## JudgeResultContract

Structured output contract expected from a Langfuse LLM-as-Judge evaluator.
The harness validates this contract during setup. Langfuse owns runtime
evaluator execution and score writes in the MVP.

Fields:

- `reasoning`: concise explanation of the score.
- `score`: numeric score within configured score range.
- `confidence`: numeric confidence value.
- `evaluator_name`: evaluator identity.
- `evaluator_version`: evaluator version.
- `score_config`: target score config.
- `trace_id`: evaluated trace context expected in Langfuse metadata.
- `observation_id`: evaluated observation context expected when target is
  observation.
- `dataset_item_id`: evaluated dataset item context expected in Langfuse
  metadata.

Validation:

- The configured score schema and examples must keep `score` within the score
  config range.
- `reasoning`, `score`, and `confidence` are required for setup examples.

## ScoreTarget

Canonical Langfuse score config used by automated judges and Human Annotation
Queues for one evaluator dimension.

Fields:

- `managed_by_harness`: whether the harness creates/reuses the score config.
- `name`: score name when harness-managed.
- `langfuse_score_config_id`: score config ID when user-owned.
- `data_type`: numeric or categorical.
- `min_value`: minimum allowed score for numeric scores.
- `max_value`: maximum allowed score for numeric scores.
- `description`: score purpose.
- `allowed_score_sources`: harness-normalized expected score origins:
  `llm_judge`, `human_annotation`, and optional future `api`.
- `langfuse_source_mapping`: mapping from harness-normalized score source to
  Langfuse native score source, where `llm_judge` maps to `EVAL`,
  `human_annotation` maps to `ANNOTATION`, and `api` maps to `API`.

Validation:

- Harness-managed scores use the project score prefix.
- Existing incompatible managed scores fail validation.
- LLM-as-Judge evaluators and Human Annotation Queues for the same evaluator
  dimension must reference the same score target.
- Score origin is represented with Langfuse's native score `source` field when
  available, interpreted through the harness-normalized source mapping.
- Score source must not be encoded into separate score config names for the
  same dimension.

## CalibrationReviewItem

Human review item used to calibrate or audit judge behavior.

Fields:

- `trace_id`: trace selected for review.
- `observation_id`: optional observation selected for review.
- `item_id`: dataset item ID.
- `selection_reason`: stable sample, score disagreement, malformed result, or
  other configured reason.
- `evaluator_name`: evaluator that triggered review, if applicable.
- `score`: automated score, if available.

Validation:

- Stable calibration sampling should use the existing deterministic review
  cohort so baseline and candidate runs can be reviewed consistently.
