# Research: Model Output Observation Targeting

## Decision: Use Metadata Role, Not Observation Name, As The Primary Contract

**Decision**: Standard model-output evaluators will continue targeting
observations by provider-neutral metadata role. Exactly one final output
observation per dataset item run should carry `observation_role=model_output`.
Parent/container observations must carry a different role.

**Rationale**: Observation names vary across providers and Langfuse SDK
integrations. A hardcoded name such as `OpenAI-generation` fixes one current
path but breaks dry-run and future Gemini, Claude, Ollama, or native Langfuse
provider integrations. Metadata role is already the current evaluator filter
intent and is more portable.

**Alternatives considered**:

- **Filter by `OpenAI-generation`**: Rejected because it is provider-specific
  and would skip providers that do not emit that name.
- **Target traces instead of observations**: Rejected because evaluator inputs
  need the final model output observation and trace-level matching can be too
  broad for multi-call traces.
- **Use score config name as targeting key**: Rejected because score configs
  define score destinations, not which observation should be judged.

## Decision: Parent/Container Spans Must Not Use `model_output`

**Decision**: Parent or orchestration observations should use a non-final role
such as `run_item` or `harness_run_item`, while final model outputs retain
`model_output`.

**Rationale**: The observed 48-count issue maps to two observations per trace
matching the same evaluator filter. Keeping parent spans visible in Langfuse is
useful, but they must not be eligible for content-quality judges.

**Alternatives considered**:

- **Remove role metadata from parent spans entirely**: Possible, but a
  non-final role is clearer for trace inspection and diagnostics.
- **Keep parent spans as model output and exclude by name**: Rejected because
  name-based exclusion is brittle across providers.

## Decision: Provider Adapters Own Final-Output Eligibility

**Decision**: Each provider adapter path must result in one final output
observation eligible for standard evaluators. Harness-managed tracing can set
metadata directly. Native Langfuse tracing providers must either propagate the
contract or expose explicit targeting configuration.

**Rationale**: The runner cannot reliably infer final output if a provider
creates multiple native Langfuse observations internally. Provider adapters are
the correct boundary for declaring tracing strategy and final-output semantics.

**Alternatives considered**:

- **Global post-processing of traces**: Rejected because Langfuse is the system
  of record and historical trace mutation is out of scope.
- **Require all providers to use harness-managed spans**: Rejected because the
  constitution prefers Langfuse SDK integrations when they provide correct
  tracing.

## Decision: Diagnostics Should Be Added Where Detectable

**Decision**: Unit/integration tests must prove the harness creates one
model-output target per dataset item for supported paths. User-facing validation
or audit should warn when configuration depends on provider-specific names or
when sample trace data shows missing/duplicate model-output markers.

**Rationale**: Preventing double matches is the primary fix, but future provider
adapters can regress the contract. Diagnostics make the issue visible before
expensive evaluator runs.

**Alternatives considered**:

- **Rely only on Langfuse evaluator counts**: Rejected because users discover
  problems after judges have already run.
- **Block all explicit observation-name filters**: Rejected because some
  projects intentionally evaluate named non-final observations.
