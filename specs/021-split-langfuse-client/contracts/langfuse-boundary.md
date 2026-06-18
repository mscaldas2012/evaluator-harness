# Contract: Langfuse Boundary

## Purpose

The Langfuse boundary defines the internal contract between the retained `LangfuseClient` facade and the extracted Langfuse behavior modules. It is not a new user-facing API. Existing CLI commands, project YAML, and callers continue to use the facade.

## Compatibility Rules

- Current public `LangfuseClient` methods remain callable by existing harness modules and scripts.
- Callers do not choose SDK, REST, or in-memory implementations directly.
- The facade returns the same user-facing data shapes and errors currently expected by tests and workflows.
- External Langfuse SDK objects and dictionaries are not consumed directly by downstream harness workflow code.

## Boundary Responsibilities

The boundary must support these operation groups:

- Dataset sync and dataset item identity lookup.
- Dataset run item recording and output lookup.
- Score config listing, creation, synchronization, and alignment.
- Prompt version lookup and prompt synchronization.
- Trace retrieval for dataset runs and run items.
- Score retrieval for traces and dataset runs.
- Evaluator list, get, create, update, and payload shaping.
- Annotation queue list, get, create, object identity lookup, and review routing.
- Baseline lookup and dataset run metadata retrieval.
- Bounded retry, pagination, operation naming, and redacted error reporting.

## Record Contract

Each boundary operation must return one of:

- a typed internal record,
- a collection of typed internal records,
- a compatibility value that the current facade already returns,
- or a `LangfuseError` with sanitized operation context.

Returned records must satisfy these rules:

- Required IDs are non-empty strings.
- Optional external fields have explicit defaults.
- Metadata dictionaries contain only values safe for downstream logging.
- Score values, prompt versions, and evaluator filters are normalized before use.
- Annotation queue object identifiers are stable strings.

## Implementation Roles

- **Facade**: compatibility methods, workflow-level orchestration, dependency selection.
- **Gateway protocol**: operation shape used by the facade.
- **In-memory gateway**: deterministic local state implementing the same operation shape.
- **SDK gateway**: live SDK-backed behavior for supported capabilities.
- **REST fallback gateway**: explicit fallback for live capability gaps.
- **Mappers**: external object/dictionary normalization.
- **Retry policy**: retry-after parsing, bounded retries, error wrapping, and redaction.

## Error Contract

All live failures must include:

- operation name,
- sanitized message,
- preserved exception chaining where useful,
- no secret values,
- no raw credential-bearing headers.

Failures that currently raise `LangfuseError` must continue to raise `LangfuseError`.

## Test Contract

The implementation must provide tests that verify:

- facade compatibility for existing callers,
- in-memory and live-compatible paths return the same public record shapes,
- mapper behavior for SDK objects, dictionaries, partial objects, and missing optional fields,
- fallback behavior for SDK capability gaps,
- retry and redaction behavior for representative live failures,
- regenerated quality reports meet the specified Langfuse facade quality bar.

