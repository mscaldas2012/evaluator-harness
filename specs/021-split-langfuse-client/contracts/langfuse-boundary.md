# Contract: Langfuse Gateway Boundary

## Purpose

The Langfuse gateway boundary is the active internal contract for Langfuse-backed workflows. Existing CLI commands and project YAML remain user-compatible, but internal project code should use gateway-backed operations instead of the deprecated `LangfuseClient` facade.

## Compatibility Rules

- CLI command names, project YAML semantics, dataset behavior, run behavior, exports, review routing, and Langfuse metadata remain compatible for users.
- Active internal workflows do not construct or depend on `LangfuseClient`.
- Callers use the gateway factory, gateway protocol, concrete gateways, or focused owner modules.
- External Langfuse SDK objects and dictionaries are normalized before downstream workflow code consumes them.
- Any remaining `LangfuseClient` symbol is explicitly deprecated and contains no workflow logic.

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
- a compatibility value that current CLI/workflow behavior already returns,
- or a `LangfuseError` with sanitized operation context.

Returned records must satisfy these rules:

- Required IDs are non-empty strings.
- Optional external fields have explicit defaults.
- Metadata dictionaries contain only values safe for downstream logging.
- Score values, prompt versions, and evaluator filters are normalized before use.
- Annotation queue object identifiers are stable strings.

## Implementation Roles

- **Gateway protocol**: operation shape used by active workflows.
- **Gateway factory**: selects in-memory, SDK-backed, or fallback-capable live behavior from runtime settings.
- **In-memory gateway**: deterministic local state implementing the same operation shape.
- **SDK gateway**: live SDK-backed behavior for supported capabilities.
- **REST fallback gateway**: explicit fallback for live capability gaps.
- **Owner modules**: workflow orchestration grouped by Langfuse responsibility.
- **Mappers**: external object/dictionary normalization.
- **Retry policy**: retry-after parsing, bounded retries, error wrapping, and redaction.
- **Legacy client**: deprecated non-runtime shim or removal target.

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

- active workflows no longer depend on `LangfuseClient`,
- gateway-backed workflows preserve current user-facing behavior,
- in-memory and live-compatible paths return the same public record shapes,
- mapper behavior for SDK objects, dictionaries, partial objects, and missing optional fields,
- fallback behavior for SDK capability gaps,
- retry and redaction behavior for representative live failures,
- source search confirms no active internal runtime imports of the legacy client,
- regenerated quality reports meet the specified Langfuse gateway quality bar.
