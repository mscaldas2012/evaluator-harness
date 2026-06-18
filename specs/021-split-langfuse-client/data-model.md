# Data Model: Split Langfuse Client

## Legacy Langfuse Client Facade

**Purpose**: Deprecated former entry point for Langfuse workflows.

**Fields/State**:

- No active workflow state in the target architecture.
- If retained, only minimal compatibility metadata needed to direct users to gateway-backed workflows.

**Relationships**:

- Must not be used by active internal project workflows.
- Must not own dataset, run, trace, score, prompt, evaluator, annotation queue, retry, REST fallback, or mapping behavior.

**Validation Rules**:

- Internal source and tests must not depend on it for workflow execution.
- Any remaining symbol must be documented as deprecated.

## Langfuse Gateway

**Purpose**: Active internal boundary for Langfuse dataset, run, trace, score, prompt, evaluator, baseline, and annotation queue operations.

**Operations**:

- Dataset sync and dataset item lookup.
- Dataset run item recording and output lookup.
- Score config sync, lookup, and alignment.
- Prompt version lookup and prompt creation/sync behavior.
- Trace retrieval and score retrieval.
- Evaluator create/update/list/get operations.
- Annotation queue create/list/get/route operations.
- Baseline lookup and dataset run metadata retrieval.

**Relationships**:

- Implemented by in-memory, SDK-backed, and fallback-capable live behavior.
- Constructed through gateway factory inputs derived from existing project/runtime settings.
- Used directly or through focused owner modules by active project workflows.

**Validation Rules**:

- Must return stable internal records or raise explicit harness errors.
- Must keep secret values out of errors and records intended for logs.
- Must preserve dry-run and live-compatible behavior.

## Gateway Construction Context

**Purpose**: Carries the runtime values needed to construct the correct Langfuse gateway without relying on `LangfuseClient`.

**Fields/State**:

- Live settings and credentials metadata.
- Optional SDK client handle.
- Optional REST fallback inputs.
- In-memory/test-mode selection signals.
- Progress reporter where applicable.

**Relationships**:

- Created by runner/CLI orchestration or helper modules.
- Passed to the gateway factory.

**Validation Rules**:

- Must not require project YAML changes.
- Must select in-memory behavior without live credentials for tests and dry runs.

## In-Memory Langfuse Gateway

**Purpose**: Deterministic local implementation for tests, dry runs, and developer workflows without live credentials.

**Fields/State**:

- Dataset records.
- Run records.
- Trace records.
- Score records.
- Prompt records.
- Evaluator records.
- Annotation queue records.

**Relationships**:

- Implements the same gateway boundary as live behavior.
- Used by tests to verify public contracts without network access.

**Validation Rules**:

- Must be deterministic.
- Must expose the same internal record shapes as live-compatible behavior.

## SDK Langfuse Gateway

**Purpose**: SDK-backed implementation for supported live Langfuse capabilities.

**Fields/State**:

- SDK client handle.
- Live settings needed for host, credentials, and workspace access.
- Retry policy.
- REST fallback gateway for SDK gaps.

**Relationships**:

- Uses REST-compatible fallback behavior for operations not covered by the SDK.
- Uses mapper functions for all external object conversion.

**Validation Rules**:

- Must preserve workspace verification behavior.
- Must preserve existing pagination, retry, and contextual error behavior.

## REST-Compatible Fallback Behavior

**Purpose**: Handles live Langfuse operations where current SDK coverage is incomplete.

**Fields/State**:

- HTTP client or request helper.
- Host and credential metadata.
- Retry/error policy.

**Relationships**:

- Used by live behavior for evaluator, queue, score, prompt, or trace operations that require fallback.
- Uses the same mapper output as SDK-backed operations.

**Validation Rules**:

- Must preserve existing endpoint payload semantics.
- Must redact credentials and sensitive headers from failures.
- Must make fallback usage explicit in tests.

## Langfuse Records

**Purpose**: Typed internal records consumed by gateways, owner modules, and downstream harness modules.

**Record Types**:

- `DatasetRecord`: dataset identity and metadata.
- `DatasetItemRecord`: dataset item identity, input, expected output, and metadata.
- `RunRecord`: dataset run identity, run name, project identity, baseline metadata, and timestamps.
- `TraceRecord`: trace identity, run association, item association, output, observations, and metadata.
- `ScoreRecord`: score identity, score config identity, value, comment, trace association, and metadata.
- `ScoreConfigRecord`: score config identity, name, type, categories, archived status, and metadata.
- `PromptRecord`: prompt identity, name, version, labels, and prompt text metadata.
- `EvaluatorRecord`: evaluator identity, name, status, target, model/provider metadata, filters, and output schema metadata.
- `AnnotationQueueRecord`: queue identity, name, description, score config associations, and routed object identifiers.
- `OperationFailure`: operation name, sanitized message, original exception type, retryability, and redacted context.

**Validation Rules**:

- Identifiers required by downstream code must be non-null before records are returned.
- Optional external fields must have explicit defaults.
- External dictionaries and SDK objects must be normalized before workflow code consumes them.

## Focused Owner Modules

**Purpose**: Own workflow orchestration by Langfuse responsibility without centralizing behavior in a facade.

**Owner Areas**:

- Dataset sync and run item recording.
- Score config synchronization.
- Prompt version lookup and creation.
- Trace retrieval and output lookup.
- Score retrieval.
- Baseline lookup.
- Evaluator operations.
- Annotation queue operations.
- Observation/span operations.
- Retry and redaction policy.

**Relationships**:

- Use the gateway boundary and typed records.
- Are called by runner, CLI support modules, scripts, and tests.

**Validation Rules**:

- Must not import or depend on `LangfuseClient`.
- Must keep behavior local to their responsibility area.

## State Transitions

- **Gateway construction**: runtime settings determine whether in-memory or live-compatible behavior is selected.
- **Live operation**: caller delegates to gateway or owner module, gateway applies retry/error policy, external objects are normalized into records, caller receives compatibility output.
- **Fallback operation**: live gateway detects unsupported SDK capability and delegates to REST-compatible behavior.
- **Failure**: retry policy classifies the failure, retries if allowed, then raises sanitized `LangfuseError` with operation context.
- **Legacy deprecation**: internal callers migrate away from `LangfuseClient`; any remaining symbol is removed or retained only as documented non-runtime compatibility.
