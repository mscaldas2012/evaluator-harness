# Contract: Item Comparison Session Logging

## Scope

This contract defines observable behavior for baseline and candidate runs that
log model-generation traces to Langfuse.

## Inputs

- Project config path supplied to `run`.
- Run mode: `baseline` or `candidate`.
- Dataset item identity from the loaded dataset.
- Dataset sync result: name, version, and compatibility version.
- Baseline reference for candidate runs.
- Existing trace ID, run ID, and trace metadata.

## Session Identity

For each trace, the harness MUST compute one item comparison session ID from:

```text
project
project_version
dataset_name
dataset_version_or_compatibility
baseline_anchor
dataset_item_id
```

For baseline mode, `baseline_anchor` is the baseline run's own run ID.

For candidate mode, `baseline_anchor` is the candidate run's explicit
`baseline_reference.baseline_run_id`.

## Langfuse Logging

The computed session ID MUST be passed through the official Langfuse session
field for the trace. The same value MAY also be stored in trace metadata for
diagnostics and exports, but metadata alone does not satisfy this contract.

The metadata field name is:

```text
item_comparison_session_id
```

## Candidate Baseline Requirement

Candidate runs without an explicit baseline reference MUST fail validation
before candidate comparison traces are logged.

## Export Behavior

CSV exports SHOULD include the diagnostic session ID so users can audit grouping
without opening Langfuse.

Existing report aggregation MUST continue to use run IDs, baseline references,
and evaluator scores rather than session membership.

## Acceptance Examples

### Baseline And Candidate Share Session

Baseline trace:

```text
project=gso
dataset_item_id=42
run_id=baseline-abc
baseline_anchor=baseline-abc
```

Candidate trace:

```text
project=gso
dataset_item_id=42
run_id=candidate-def
baseline_anchor=baseline-abc
```

Expected result:

```text
item_comparison_session_id is identical
```

### Different Items Do Not Share Session

Trace A:

```text
dataset_item_id=42
baseline_anchor=baseline-abc
```

Trace B:

```text
dataset_item_id=43
baseline_anchor=baseline-abc
```

Expected result:

```text
item_comparison_session_id is different
```

### Missing Candidate Baseline Fails

Candidate run:

```text
baseline_reference=null
```

Expected result:

```text
ConfigError before candidate trace logging
```
