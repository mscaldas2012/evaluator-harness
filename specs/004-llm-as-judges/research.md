# Research: LLM-as-Judges

## Decision: Default to Observation-Level Langfuse Evaluators

Use Langfuse observation-level evaluators as the default target for LLM-as-Judge
setup. The default target is the final model-output generation identified by
`observation_role=model_output` and project metadata. `OpenAI-generation` is
the current Azure/OpenAI observation name, not the durable cross-provider
contract.

**Rationale**: The harness evaluates model outputs, not the whole harness
workflow. Observation-level targeting is more precise, avoids judging wrapper
spans, and aligns with Langfuse's current guidance for live production
evaluation.

**Alternatives considered**:

- Trace-level judging: useful only when the evaluator needs full multi-step
  workflow context. Too broad as the default.
- Local judge execution: rejected because Langfuse owns LLM-as-Judge execution
  and score storage.

## Decision: Filter by Metadata, Not Item-Specific Trace Names

Evaluator filters should use the model-output role plus metadata fields:

- `metadata.observation_role = model_output`
- `metadata.project`
- `metadata.project_version`
- `metadata.evaluator_set_id`
- `metadata.environment`
- `metadata.run_type`

Provider-specific observation names, such as `OpenAI-generation`, may be used
as optional additional narrowing filters when appropriate.

**Rationale**: Trace names include dataset item identity for human inspection,
such as `rewrite-quality/baseline/item-1`. Exact trace-name filters would only
match one item. Metadata filters target all relevant items for the project while
remaining precise.

**Alternatives considered**:

- Prefix filters on trace names: brittle and less explicit than metadata.
- Observation name only: too broad because multiple projects and providers can
  emit similarly named generation observations.

## Decision: Store Filter Metadata on the Model-Output Observation

The model-output observation must carry the project and evaluator metadata
needed by Langfuse evaluator filters directly.

**Rationale**: Langfuse evaluator filtering can involve trace and observation
attributes. Storing the key project fields on the observation avoids ambiguity
and makes filter inspection easier in the Langfuse UI.

**Alternatives considered**:

- Rely only on parent trace metadata: may not be visible or propagated in every
  evaluator filtering view.
- Encode metadata in names: less structured and harder to validate.

## Decision: Keep Judge Results Structured and Minimal

Judge prompts must return at minimum:

- `reasoning`
- `score`
- `confidence`

**Rationale**: These fields support reviewability, numeric comparison, and
calibration without overbuilding local score processing.

**Alternatives considered**:

- Score-only output: too opaque for calibration and human review.
- Large custom schemas per evaluator: too complex for the MVP.

## Decision: Reuse Harness-Managed Score Config Rules

LLM-as-Judge evaluators use the existing score config synchronization rules:
harness-managed scores are created/reused by prefix and schema compatibility;
user-owned scores are referenced but not modified. For a given evaluator
dimension, LLM-as-Judge evaluators and Human Annotation Queues use the same
canonical Langfuse score config. Score origin is distinguished by Langfuse's
native score `source`, normalized by the harness as `llm_judge` for Langfuse
`EVAL` scores and `human_annotation` for Langfuse `ANNOTATION` scores.

**Rationale**: This keeps score ownership consistent with the rest of the
harness, avoids duplicate global score configs, and allows automated and human
scores to be compared apples-to-apples.

**Alternatives considered**:

- Create a new score config workflow for judges: duplicates existing logic.
- Require all score configs to be manual: creates unnecessary setup friction.
- Separate score configs for human and automated scores: rejected because it
  prevents direct comparison of the same evaluator dimension.

## Decision: Human Annotation Queues Remain Calibration Path

Use existing Human Annotation Queue workflows for sampled and disputed
LLM-as-Judge results.

**Rationale**: Automated qualitative evaluation is imperfect. Calibration and
spot-checking should happen in Langfuse, not a local review tool.

**Alternatives considered**:

- Local review CSVs: weak trace context and duplicates Langfuse review
  workflow.
- Fully automated evaluation only: conflicts with human review awareness.
