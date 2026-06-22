# Data Model: Surface Live Langfuse Failures

## LangfuseOperationOutcome

**Purpose**: Represents the result of a single live Langfuse lookup or persistence operation.

**Fields**:

- `operation`: Stable operation name such as baseline lookup, dataset item lookup, trace lookup, score retrieval, or run item recording.
- `status`: One of `success`, `expected_not_found`, `partial_success`, or `failure`.
- `severity`: One of `info`, `warning`, or `error`.
- `message`: User-facing summary.
- `project_name`: Optional project identity.
- `run_id`: Optional run identity.
- `dataset_name`: Optional dataset identity.
- `item_id`: Optional local dataset item identity.
- `trace_id`: Optional Langfuse trace identity.
- `score_name`: Optional score identity.
- `baseline_selector`: Optional baseline selector used by lookup.
- `details`: Redacted diagnostic fields safe for CLI/report output.

**Validation rules**:

- `operation`, `status`, `severity`, and `message` are required.
- `failure` outcomes must include a warning or error severity.
- `expected_not_found` must not be used when a service/API exception occurred.
- `details` must not contain raw secrets, credentials, or sensitive headers.

## LangfuseWarning

**Purpose**: User-facing warning derived from one or more operation outcomes.

**Fields**:

- `code`: Stable warning code suitable for assertions and aggregation.
- `message`: User-facing warning text.
- `operation`: Operation that produced the warning.
- `affected_count`: Number of affected records represented by this warning.
- `examples`: Representative affected identities such as item IDs or trace IDs.
- `details`: Redacted diagnostic fields.

**Validation rules**:

- `affected_count` is at least 1.
- `examples` are bounded to avoid noisy output.
- Warning text must identify what confidence is reduced and what object is affected.

## RunCompletionSummary

**Purpose**: Combines model/evaluator completion counts with Langfuse persistence and lookup confidence.

**Fields**:

- `run_id`: Run identity.
- `run_type`: Baseline or candidate.
- `completed_count`: Count of completed run items.
- `failed_count`: Count of model/evaluator failures.
- `langfuse_status`: `complete`, `complete_with_warnings`, or `failed_required_linkage`.
- `warnings`: List of `LangfuseWarning`.

**State transitions**:

- Starts as `complete` when model/evaluator work completes and no Langfuse warnings exist.
- Moves to `complete_with_warnings` when recoverable live Langfuse persistence or lookup warnings exist.
- Moves to `failed_required_linkage` when required baseline, dataset identity, or comparison linkage cannot be established.

## ExpectedNotFoundResult

**Purpose**: Records that a live lookup completed successfully but did not find the requested object.

**Fields**:

- `operation`: Lookup operation.
- `selector`: User or workflow selector.
- `searched_scope`: Dataset, run, trace, or score scope searched.
- `message`: User-facing absence explanation.

**Validation rules**:

- Must only be emitted after lookup completed without service/API failure.
- Must not be aggregated as a persistence warning unless downstream behavior needs user attention.

## LiveLookupFailure

**Purpose**: Records that live Langfuse lookup confidence is incomplete due to access, connectivity, service, pagination, malformed response, or unexpected client failure.

**Fields**:

- `operation`: Lookup operation.
- `scope`: Search scope.
- `reason`: Redacted reason category.
- `message`: User-facing failure summary.
- `details`: Redacted diagnostic fields.

**Validation rules**:

- Must not be converted to an unqualified empty result.
- Must become a warning or blocking error depending on whether the requested output can remain valid.
