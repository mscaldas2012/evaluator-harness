# Research: Candidate Variants

## Decision: Model variants as named candidates

**Rationale**: The existing harness already runs one named candidate at a time,
records candidate names in Langfuse metadata, and resolves baselines before
candidate execution. Treating each variant as a named candidate preserves the
current CLI and mental model while adding prompt and identity metadata.

**Alternatives considered**:

- Add a new top-level `variants` collection. Rejected because it would duplicate
  candidate behavior and require unnecessary CLI changes.
- Add a batch campaign object. Rejected for MVP because users can already run
  named candidates one at a time, and campaign scheduling is out of scope.

## Decision: Add optional candidate-level prompt override

**Rationale**: The project-level task prompt remains the baseline default. A
candidate-level prompt override is the smallest config extension that allows
prompt-v2 candidate outputs to compare against prompt-v1 baseline outputs.

**Alternatives considered**:

- Make prompt version a run-time CLI argument. Rejected because prompt identity
  would be harder to validate and reproduce from project config.
- Require separate project files per prompt. Rejected because it fragments
  Langfuse comparison metadata and increases config duplication.

## Decision: Candidate prompt changes do not invalidate baseline compatibility

**Rationale**: The selected baseline represents the control output. Prompt-v2
is a candidate-side intervention. Requiring a new baseline for every candidate
prompt iteration would prevent the requested v2-vs-v1 comparison.

**Alternatives considered**:

- Include candidate prompt identity in baseline lookup. Rejected because it
  would make prompt variants impossible to compare to an existing prompt-v1
  baseline.
- Ignore baseline prompt identity entirely. Rejected because reproducibility
  requires knowing how the baseline output was generated.

## Decision: Record separate baseline and candidate prompt identities

**Rationale**: Langfuse comparisons need to show both the control prompt and
the candidate prompt. A human-readable version alone may be reused accidentally,
so non-secret content identity should also be recorded.

**Alternatives considered**:

- Store only prompt version labels. Rejected because two files can share the
  same version label accidentally.
- Store full prompt text in every metadata object. Rejected because traces
  already carry prompt input where appropriate, and metadata should remain
  compact and non-secret.

## Decision: Use parameter identity distinct from model identity

**Rationale**: Users need to distinguish parameter-only variants from
model-only variants. Keeping parameter identity separate supports clear
filtering and export analysis.

**Alternatives considered**:

- Encode parameters only in candidate names. Rejected because names are human
  labels and are not reliable enough for reproducibility.
- Treat parameter changes as model changes. Rejected because parameter tuning
  and model substitution are different experimental interventions.

## Decision: Require confirmation for mixed-axis variants

**Rationale**: A candidate that changes more than one of model, prompt, and
parameters can be useful, but it is less isolated. The CLI should alert users
before running such a comparison. `--confirm-mixed-variant` keeps the workflow
scriptable.

**Alternatives considered**:

- Block mixed variants entirely. Rejected because mixed candidates are useful
  for real evaluation campaigns.
- Only print a warning. Rejected because accidental mixed comparisons can
  consume live model spend and produce confusing score interpretation.

## Decision: Keep evaluator targeting stable

**Rationale**: LLM-as-Judge and human review workflows should continue to
target final model-output observations through project metadata and
`observation_role=model_output`. Variant details belong in metadata, not in
provider-specific observation names.

**Alternatives considered**:

- Create separate evaluator definitions per candidate variant. Rejected because
  this would fragment scores and make candidate comparison harder.
- Filter evaluators by candidate name. Rejected for MVP because the same
  evaluator set should judge baseline and candidate outputs consistently.
