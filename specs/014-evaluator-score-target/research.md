# Research: Judge Evaluator Score Config Targeting

## Decision: Score Config Targeting Is Required Evaluator Rule Setup

**Decision**: Judge evaluator rule creation and update must include the
resolved score config ID as part of the remote evaluator rule setup.

**Rationale**: Local evaluator bindings already record the intended score
config, but that does not make Langfuse write judge scores into that score
definition. The remote evaluator rule itself must carry the score config target
so judge scores and human annotation scores share the same dimension.

**Alternatives considered**:

- Store only local binding metadata: rejected because it does not affect where
  Langfuse writes evaluator scores.
- Rely on score name matching after scores are produced: rejected because it is
  weaker than configuring the evaluator rule correctly and can produce
  ambiguous score history.

## Decision: Use Score Config IDs As The Authoritative Target

**Decision**: The evaluator rule target must use the resolved score config ID.
The score config name remains available for display, binding, and audit output.

**Rationale**: Langfuse score config IDs uniquely identify the score definition.
Names are useful to users but can be reused, archived, or renamed by sync logic.
The harness already resolves IDs during score config sync.

**Alternatives considered**:

- Target by score config name: rejected because names are not as stable as IDs.
- Target by evaluator score dimension only: rejected because dimensions do not
  identify a specific Langfuse score config.

## Decision: Block Apply When Required Score Config ID Is Missing

**Decision**: Applying judge evaluator setup must block or fail before creating
or updating an evaluator rule when the expected score config ID is unavailable.
Dry-run may still preview planned targets and explain that score config sync is
required.

**Rationale**: Creating an evaluator rule without a score config target repeats
the current bug. A clear block is safer than a partially configured evaluator.

**Alternatives considered**:

- Create evaluator rules without score config targets and patch later: rejected
  because it can produce scores in the wrong place before patching.
- Infer score config IDs from names at evaluator sync time without prior score
  config sync: rejected because score config sync already owns creation,
  compatibility checks, and archived duplicate handling.

## Decision: Normalize Remote Score Config ID Field Names

**Decision**: Remote evaluator rule normalization must recognize both
`scoreConfigId` and `score_config_id`, storing a normalized `score_config_id`.

**Rationale**: Existing code already normalizes multiple Langfuse field naming
styles for evaluator rule IDs and score config IDs in some objects. Audit and
safe update logic need a single canonical key to compare expected and remote
state.

**Alternatives considered**:

- Compare both field names at every call site: rejected because it spreads
  provider-specific normalization across the codebase.

## Decision: Treat Score Config Target As A Safe Operational Update

**Decision**: For evaluator rules proven to be harness-managed, a score config
target mismatch is eligible for safe update if Langfuse accepts updating that
field. If Langfuse rejects it, the sync result should fail with remediation
rather than deleting the evaluator rule.

**Rationale**: Score config targeting is operational evaluator rule state, not
judge prompt content. It must be repairable for rules created before this
feature. Deleting or recreating rules would risk ownership ambiguity and score
history confusion.

**Alternatives considered**:

- Always create a new evaluator rule version on mismatch: rejected because the
  evaluator definition did not necessarily change and duplicate active rules
  could produce duplicate scores.
- Delete and recreate mismatched rules: rejected by the existing safety model.

## Decision: Cover Custom And Catalog Evaluators Equally

**Decision**: Score config targeting must work for both custom evaluator
templates and Langfuse-managed catalog evaluators.

**Rationale**: Both source types create evaluator rules that produce scores.
The DFE project uses both custom readability judges and the managed Relevance
catalog evaluator, and both need comparable human/judge score dimensions.

**Alternatives considered**:

- Start with custom evaluators only: rejected because the current failure was
  discovered while adding a catalog evaluator and the risk applies equally.
