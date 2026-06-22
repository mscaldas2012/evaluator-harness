# Research: Surface Live Langfuse Failures

## Decision: Represent live operations with explicit outcomes

**Rationale**: The current debt exists because live SDK/API exceptions can collapse into `None`, `{}`, or `[]`, making failure indistinguishable from absence. A small outcome record lets each workflow report success, expected not-found, partial success, and failure with consistent context.

**Alternatives considered**:

- Raise exceptions for every live failure: rejected because some failures happen after model work completes and should preserve local outputs with warnings.
- Keep sentinel values and add logs: rejected because command results and reports would still look successful.
- Return ad hoc tuples per workflow: rejected because warning aggregation and CLI/export behavior would drift across modules.

## Decision: Keep expected not-found as non-error state

**Rationale**: Missing compatible baselines, absent optional traces, or empty score sets can be legitimate when a complete lookup succeeded. Classifying them as failures would make normal selection workflows noisy.

**Alternatives considered**:

- Treat all absence as failure: rejected because it would break valid baseline-selection and score-inspection workflows.
- Treat all absence as success: rejected because it hides pagination, permission, and service lookup failures.

## Decision: Aggregate warnings at gateway/run-result boundary

**Rationale**: The affected operations live in focused Langfuse owner modules, but users consume outcomes through CLI commands, exports, and run summaries. Aggregating at the gateway/run-result boundary keeps module internals focused and gives every user-facing surface the same warning set.

**Alternatives considered**:

- Print warnings directly inside owner modules: rejected because it couples low-level workflows to the CLI and makes tests brittle.
- Only expose warnings in logs: rejected because reports and command summaries must carry the confidence status.
- Add a new persistent warning store: rejected because it violates minimal local state and is unnecessary for local run outputs.

## Decision: Fail only when missing live data invalidates requested output

**Rationale**: If model output completed but a trace confirmation failed, users still benefit from local outputs plus a warning. If a required baseline or dataset identity cannot be established, continuing could produce misleading comparisons or review links.

**Alternatives considered**:

- Always continue with warnings: rejected because some downstream outputs would be invalid.
- Always fail fast on first warning: rejected because recoverable late-stage persistence issues would discard useful completed work.

## Decision: Reuse existing secret redaction in diagnostics

**Rationale**: The feature surfaces more live service diagnostic information. Existing redaction policy should remain the single source of truth so headers, keys, and credentials are not exposed.

**Alternatives considered**:

- Manually redact in each workflow: rejected because it is error-prone and duplicates security-sensitive logic.
- Suppress all diagnostic details: rejected because users need enough context to identify affected runs, traces, and items.
