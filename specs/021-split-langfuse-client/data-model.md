# Data Model: Split Langfuse Client

## Langfuse Client Facade

**Purpose**: Stable public entry point used by existing harness workflows.

**Fields/State**:

- `gateway`: selected Langfuse boundary implementation.
- `settings`: current live/in-memory configuration and credentials metadata.
- `progress_reporter`: existing progress surface.

**Relationships**:

- Delegates workflow operations to `LangfuseGateway`.
- Does not expose whether the backing implementation is in-memory, SDK-backed, or REST-compatible.

**Validation Rules**:

- Must preserve current public method names and caller expectations.
- Must not require project YAML or CLI changes.

## Langfuse Gateway

**Purpose**: Boundary for Langfuse dataset, run, trace, score, prompt, evaluator, and annotation queue operations.

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
- Uses mapper functions to produce stable records.
- Uses retry/error policy for live operations.

**Validation Rules**:

- Must return stable internal records or raise explicit harness errors.
- Must keep secret values out of errors and records intended for logs.

## In-Memory Langfuse Behavior

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
- Must not require live credentials.
- Must expose the same internal record shapes as live-compatible behavior.

## Live Langfuse Behavior

**Purpose**: SDK-backed implementation for supported live Langfuse capabilities.

**Fields/State**:

- SDK client handle.
- Live settings needed for host, credentials, and workspace access.
- Retry policy.

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

**Purpose**: Typed internal records consumed by the facade and downstream harness modules.

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
- External dictionaries and SDK objects must be normalized before use by workflow code.

## Retry and Error Policy

**Purpose**: Shared behavior for bounded retry, retry-after parsing, contextual operation naming, and secret redaction.

**Fields/State**:

- Retry attempts.
- Retry interval and backoff rules.
- Retryable status/error classification.
- Operation name.

**Relationships**:

- Used by SDK and REST-compatible live behavior.
- Raises `LangfuseError` with sanitized context.

**Validation Rules**:

- Must not retry indefinitely.
- Must preserve current operation-specific error messages where tests assert them.
- Must not include secret values in output.

## State Transitions

- **Facade construction**: settings determine whether in-memory or live-compatible behavior is selected.
- **Live operation**: facade delegates to gateway, gateway applies retry/error policy, external objects are normalized into internal records, facade returns compatibility output.
- **Fallback operation**: live gateway detects an unsupported SDK capability and delegates to REST-compatible behavior.
- **Failure**: retry policy classifies the failure, retries if allowed, then raises sanitized `LangfuseError` with operation context.
- **Quality acceptance**: reports are regenerated after implementation and compared with the current baseline.

