# Contract: Provider Final Output Observation Targeting

## Scope

This contract applies to baseline and candidate run logging, provider adapters,
and evaluator setup that targets model-output observations.

## Standard Evaluator Target

Standard content-quality LLM-as-Judge evaluators target:

```yaml
target: observation
target_observation_role: model_output
```

They should not require provider-specific observation names for normal model
output scoring.

## Required Trace Shape

For each completed dataset item run:

- Exactly one final output observation is eligible for standard model-output
  evaluators.
- Parent/container observations are present only for trace organization and are
  not eligible for standard model-output evaluators.
- The final output observation preserves project, run, dataset item, prompt,
  provider, model, and scenario metadata needed for filtering and review.

## Provider Adapter Responsibilities

Provider adapters MUST satisfy one of these paths:

1. **Harness-managed tracing**
   - The harness creates the parent/container observation.
   - The harness or provider path creates the final output observation.
   - Only the final output observation carries the model-output role.

2. **Native Langfuse tracing**
   - The provider integration propagates the final-output role to exactly one
     final output observation, or
   - The provider/project configuration declares an explicit final output
     observation selector.

3. **Dry-run or synthetic tracing**
   - Local verification still produces one evaluator-targetable final output
     for completed dataset items.

## Non-Goals

- Do not rewrite historical traces.
- Do not create local score aggregation.
- Do not require all providers to use the same observation name.
- Do not remove the ability to intentionally evaluate a named non-final
  observation.

## Acceptance Checks

### Manual Generation Provider

Given a provider path that creates a parent span and an inner generation span,
standard model-output evaluators match only the inner final output observation.

### Non-Generation Provider

Given a provider path that does not create an inner generation span, standard
model-output evaluators still match exactly one final output observation for the
completed dataset item.

### Native Langfuse Provider

Given a provider uses native Langfuse tracing, setup documentation or validation
identifies whether the provider propagates the standard final-output role or
requires explicit final-output targeting configuration.

### Multiple LLM Calls

Given a trace includes retries or intermediate calls, standard model-output
evaluators match only the final output intended for scoring.

### Explicit Non-Final Target

Given a project intentionally evaluates an intermediate or named observation,
explicit evaluator configuration can still target that observation without
changing the standard model-output contract.
