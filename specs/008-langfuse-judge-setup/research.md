# Research: Langfuse Judge Setup

## Decision: Use observation-level Langfuse evaluators by default

**Rationale**: Langfuse currently recommends observation-level evaluators for
live production evaluation because they evaluate individual operations, support
operation-level filtering, and complete faster than trace-level evaluators.
This matches the existing harness filter metadata on the final model-output
observation.

**Alternatives considered**:

- Trace-level default: rejected because Langfuse describes trace-level
  evaluators as legacy for live workflows and less precise for final-output
  judging.
- Experiment-level default: rejected because this feature targets direct
  Langfuse evaluator setup for live model-output observations; experiment
  evaluators remain possible when explicitly configured later.

Reference: https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge

## Decision: Support Langfuse catalog evaluators and custom evaluators

**Rationale**: Langfuse setup offers managed/catalog evaluators and custom
evaluators. The harness should model both rather than forcing all teams to
write custom prompts. Catalog evaluators require a catalog reference and
project-specific bindings; custom evaluators require prompt text, result
contract, score target, and variable mappings.

**Alternatives considered**:

- Custom-only setup: rejected because it ignores the Langfuse evaluator catalog
  and creates unnecessary prompt maintenance.
- Catalog-only setup: rejected because project-specific dimensions such as
  rewrite clarity may require custom rubrics.

Reference: https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge

## Decision: Require judge model or LLM connection via project default with evaluator override

**Rationale**: Langfuse LLM-as-Judge setup requires an LLM Connection and a
judge model that supports structured output. A project-level default keeps
config concise, while evaluator-level override supports dimensions that need a
different judge model.

**Alternatives considered**:

- Rely on mutable Langfuse project defaults: rejected because preview/audit
  would not be reproducible from project config.
- Require every evaluator to specify a model: rejected because it duplicates
  common setup across evaluator definitions.

Reference: https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge

## Decision: Default sampling to 100% matching observations unless configured

**Rationale**: The user selected active evaluators immediately after apply and
100% matching-observation evaluation by default. The plan mitigates cost risk
by making preview and apply summaries show effective sampling for every
evaluator.

**Alternatives considered**:

- Require explicit sampling: rejected by user preference.
- Default to a small percentage: rejected by user preference.

Reference: https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge

## Decision: Disable historical backfill by default and make it explicit opt-in

**Rationale**: Langfuse documents historical backfill as a separate action for
observation-level LLM-as-Judge evaluation. The harness should not trigger
backfill implicitly because it can create cost and score-volume surprises.
When explicitly requested, setup applies it only if the Langfuse surface
supports the selected target; otherwise it blocks with remediation.

**Alternatives considered**:

- Backfill by default: rejected because active evaluators already default to
  100% matching observations and surprise backfill would increase cost.
- Never support backfill: rejected because explicit opt-in may be useful when
  Langfuse exposes a safe operation.

Reference: https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge

## Decision: Store non-secret local binding records for harness-managed evaluator ownership

**Rationale**: The harness needs stronger proof than a display name before it
updates or inactivates a remote evaluator. Current Langfuse docs clearly
document metadata for traces and observations, but do not establish arbitrary
metadata on evaluator resources. Local binding records keyed by project
evaluator identity and remote evaluator ID keep ownership proof reviewable and
repo-local.

**Alternatives considered**:

- Use evaluator metadata only: rejected because evaluator metadata support is
  not confirmed.
- Trust managed display names: rejected because a user can manually create or
  rename a remote evaluator to the same name.
- Store bindings only in reports: rejected because reports are not an
  authoritative ownership source for safe mutation.

References:

- https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge
- https://langfuse.com/docs/observability/features/metadata

## Decision: Apply evaluator setup independently and avoid rollback

**Rationale**: Setup touches remote Langfuse resources and deletes are out of
scope. If evaluator N fails after evaluator N-1 succeeds, rollback could
require destructive or ambiguous remote mutations. Per-evaluator apply with
partial-success reporting is safer and testable.

**Alternatives considered**:

- All-or-nothing rollback: rejected because it conflicts with no-delete and
  safe remote mutation requirements.
- Stop-on-first-failure: rejected because it leaves unaffected evaluators
  unapplied even though the result can report partial success clearly.

## Decision: Treat API surface gaps as explicit blocked setup states

**Rationale**: Langfuse docs describe evaluator setup concepts, but the exact
SDK/API resource surface for evaluator CRUD may vary by installed version. The
harness should discover capability through its Langfuse adapter and fail
specific operations with actionable remediation rather than silently degrading.

**Alternatives considered**:

- Assume all evaluator CRUD operations are available: rejected because it can
  produce fragile live behavior.
- Keep manual setup only: rejected because BL-008 explicitly targets direct
  Langfuse setup automation.
