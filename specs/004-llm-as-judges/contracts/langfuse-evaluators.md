# Langfuse Evaluator Contract: LLM-as-Judges

## Default Evaluator Target

Default target:

```text
Observation
```

Default durable selector:

```text
metadata.observation_role = model_output
```

The current Azure/OpenAI provider emits the model-output observation with the
provider-specific name `OpenAI-generation`. Other providers may emit different
observation names. Evaluator filters must not depend solely on the
provider-specific observation name.

Trace-level evaluation is allowed only when the evaluator definition states
that full workflow context is required.

## Required Observation Metadata

Every model-output observation intended for judging must expose:

```json
{
  "project": "rewrite-quality",
  "project_version": "v1",
  "dataset_name": "rewrite_quality",
  "dataset_version": "latest",
  "dataset_compatibility_version": "string",
  "run_type": "baseline",
  "evaluator_set_id": "clarity:v1",
  "prompt_version": "v1",
  "observation_role": "model_output",
  "trace_id": "32-hex-trace-id",
  "trace_name": "rewrite-quality/baseline/item-1",
  "dataset_item_id": "1"
}
```

## Langfuse Filter Profile

For the initial `rewrite-quality` clarity evaluator:

```yaml
target: observation
metadata:
  project: rewrite-quality
  project_version: v1
  evaluator_set_id: clarity:v1
  observation_role: model_output
run_types:
  - baseline
  - candidate
optional_narrowing:
  observation_name: OpenAI-generation
```

The filter must not rely on exact trace names because trace names include
dataset item identity. The filter must not rely solely on observation name
because observation names can vary by provider.

## Score Config

For a given evaluator dimension, automated LLM-as-Judge scoring and Human
Annotation Queue scoring must use the same canonical Langfuse score config.

Harness-managed score config naming:

```text
<project.score_config_prefix><evaluator.score.name>
```

Example:

```text
eh_rewrite_quality_clarity
```

Rules:

- Reuse compatible active score configs.
- Fail on incompatible active score configs with the same managed name.
- Do not mutate user-owned score configs.
- Do not create separate score configs for human and automated scores for the
  same evaluator dimension.
- Use Langfuse's native score `source` field to distinguish score origin when
  available, rather than creating a different score config.

## Score Source Convention

The canonical score config identifies the evaluator dimension. The score source
identifies who or what produced a specific score.

Harness-normalized score sources:

| Harness source | Langfuse score source | Meaning |
| -------------- | --------------------- | ------- |
| `llm_judge` | `EVAL` | Score produced by a Langfuse LLM-as-Judge evaluator |
| `human_annotation` | `ANNOTATION` | Score produced through Langfuse UI annotation or Human Annotation Queue review |
| `api` | `API` | Future non-MVP programmatic score import |

Rules:

- Automated and human scores for the same evaluator dimension must reference
  the same score config name and config ID.
- The harness must show the normalized score source in rendered setup guidance
  and exported evaluator setup documents.
- The harness must not create score configs whose names encode source, such as
  `eh_rewrite_quality_clarity_llm_judge` or
  `eh_rewrite_quality_clarity_human`.
- If Langfuse exposes only its native `source` value in a view or API response,
  the mapping above is the authoritative interpretation.

## Judge Result Contract

LLM-as-Judge prompts must be configured to return structured output equivalent
to:

```json
{
  "reasoning": "The output is clear because ...",
  "score": 0.82,
  "confidence": 0.74
}
```

Validation:

- `reasoning` is required.
- `score` must fit the score config range in the declared schema and setup
  examples.
- `confidence` must be present.
- Langfuse owns runtime evaluator execution and score writes; the MVP harness
  does not intercept, approve, inspect, or export post-run judge results.

## Blind Evaluation

Evaluator definitions default to:

```yaml
blind: true
```

Blind evaluator inputs must exclude:

- provider name
- model name
- vendor name
- run label that implies model identity

Non-blind evaluators are allowed only when the evaluator is intentionally
provider-specific or diagnostic, and must include:

```yaml
blind: false
non_blind_reason: "Provider-specific schema compliance audit"
```

Comparison labels should use neutral names such as:

```text
Output A
Output B
```

The mapping between neutral label and run/model identity must remain outside
the judge prompt.

## Human Calibration

Automated judge scores should be sampled into Human Annotation Queues according
to the project review policy. The queue must reference the same score configs
as the automated evaluators for the corresponding evaluator dimensions. The
queue item should preserve trace and observation identifiers when available.
