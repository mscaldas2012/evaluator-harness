# Research: Split Langfuse Client

## Decision: Keep `LangfuseClient` as a compatibility facade

**Rationale**: The clarified spec requires existing callers to continue using the current public facade. A facade limits blast radius, keeps CLI/project behavior stable, and lets internal responsibilities move without forcing changes throughout `runner.py`, `annotation_queues.py`, `langfuse_evaluator_setup.py`, scripts, and tests.

**Alternatives considered**:

- Migrate callers directly to new focused services: rejected because it increases caller churn and makes behavior preservation harder to verify.
- Deprecate `LangfuseClient` immediately: rejected because the refactor goal is maintainability, not a public API transition.

## Decision: Use a small gateway protocol behind the facade

**Rationale**: The current client mixes in-memory fake state, SDK calls, REST fallbacks, retry handling, and mapping. A small boundary lets the facade choose an in-memory, SDK-backed, or fallback-capable implementation while callers remain unaware of the backing behavior.

**Alternatives considered**:

- A broad abstract base class: rejected because inheritance would add ceremony without value for a local harness.
- A dependency injection framework: rejected by the thin-harness constitution and unnecessary for a small number of concrete gateways.

## Decision: Split SDK and REST-compatible fallback behavior

**Rationale**: Current behavior uses SDK capabilities where available and REST-compatible paths where SDK coverage is incomplete. Keeping those roles separate makes fallback behavior explicit, testable, and easier to remove later if Langfuse SDK support catches up.

**Alternatives considered**:

- Keep REST fallback methods in the facade: rejected because this is one of the current sources of mixed responsibility and complexity.
- Merge SDK and REST operations into one live module: rejected because it hides capability boundaries and makes tests less precise.

## Decision: Normalize external objects into typed internal records

**Rationale**: Pyright findings in `langfuse_client.py` show optional calls, unknown object attributes, nullable IDs, and object context-manager uncertainty. Typed records make mapper output explicit before downstream workflow code consumes SDK objects or dictionaries.

**Alternatives considered**:

- Continue using `dict[str, Any]` everywhere: rejected because it preserves the current type uncertainty.
- Introduce Pydantic models for every Langfuse response: rejected because the harness only needs stable internal records, not full external schema enforcement.

## Decision: Extract mapper functions before changing workflow logic

**Rationale**: Current Radon hotspots include `_object_to_evaluator_dict`, `_object_to_score_dict`, `_object_to_score_config_dict`, `_object_to_queue_dict`, `_object_to_prompt_dict`, and REST payload conversion helpers. Moving these into focused mappers reduces facade complexity while creating low-risk test targets.

**Alternatives considered**:

- Rewrite dataset sync first: rejected because dataset sync depends on many mapping and live-operation helpers.
- Only auto-format and line-wrap existing code: rejected because it would not address responsibility concentration.

## Decision: Keep retry and error policy explicit

**Rationale**: Langfuse failures must preserve contextual operation names and secret redaction. A dedicated retry/error helper keeps bounded retry behavior and error wrapping consistent across SDK and REST operations.

**Alternatives considered**:

- Let each gateway handle retries independently: rejected because it risks inconsistent messages and retry behavior.
- Add a generic resilience library: rejected as unnecessary dependency and contrary to thin-harness scope.

## Decision: Use quality reports as acceptance evidence, not design drivers alone

**Rationale**: The reports identify hotspots, but tests and behavior compatibility remain the primary correctness signal. The plan therefore targets the report baseline while requiring non-live and full live suites before acceptance.

**Alternatives considered**:

- Optimize only for Radon scores: rejected because moving code without preserving behavior would not satisfy the feature.
- Ignore reports after extraction: rejected because the user explicitly requires improved Radon outcomes.

