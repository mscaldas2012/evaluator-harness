# Research: Split Langfuse Client

## Decision: Deprecate `LangfuseClient` as an active runtime facade

**Rationale**: The updated spec supersedes the earlier compatibility-facade decision. The first refactor reduced the god object but still left a legacy central entry point. Migrating internal project callers to the gateway boundary removes the remaining architectural dependency and prevents new workflows from accumulating in `langfuse_client.py`.

**Alternatives considered**:

- Keep `LangfuseClient` as the permanent public facade: rejected because the updated scope explicitly requests complete deprecation in favor of gateways and classes.
- Delete `LangfuseClient` immediately before migrating callers: rejected because callers must move first so behavior remains testable and rollback-friendly.
- Keep a compatibility shim forever: acceptable only if documented as deprecated and containing no workflow logic.

## Decision: Use `LangfuseGateway` as the internal integration surface

**Rationale**: The gateway already separates in-memory, SDK-backed, and REST-compatible behavior. Internal workflows need a single construction and operation boundary without knowing which concrete implementation is selected.

**Alternatives considered**:

- Have every caller instantiate concrete gateways directly: rejected because it duplicates selection logic and makes dry-run/live behavior harder to keep consistent.
- Introduce a dependency injection framework: rejected by thin-harness scope and unnecessary for a small number of gateway variants.

## Decision: Migrate workflow callers, not CLI/project contracts

**Rationale**: Users should not see changes to CLI commands, project YAML, dataset behavior, or Langfuse metadata. The migration should be internal: `runner.py`, `annotation_queues.py`, `prompt_sync.py`, `langfuse_evaluator_setup.py`, and scripts should receive gateway-backed collaborators instead of constructing the legacy client.

**Alternatives considered**:

- Change CLI commands to expose gateway concepts: rejected because gateways are internal architecture, not user-facing concepts.
- Keep callers unchanged and hide everything in `LangfuseClient`: rejected because it preserves the dependency being deprecated.

## Decision: Keep focused owner modules as workflow homes

**Rationale**: Dataset, score config, prompt, trace, score, baseline, evaluator, annotation queue, observation, retry, and mapping logic now have focused modules. Migrated callers should use those modules and the gateway boundary rather than reintroducing orchestration into a new central service.

**Alternatives considered**:

- Create a replacement god service with a new name: rejected because it would repeat the original problem.
- Move workflow behavior onto record classes: rejected because records should remain data carriers.

## Decision: Verify migration with source search and behavioral tests

**Rationale**: This is a dependency migration as much as a behavior-preserving refactor. Passing tests alone may miss dead imports or dormant callers. Acceptance must include source search for active `LangfuseClient` usage, focused gateway tests, workflow regression tests, and live tests when available.

**Alternatives considered**:

- Use quality reports only: rejected because static reports cannot prove all callers migrated correctly.
- Use source search only: rejected because behavior preservation still requires tests.
