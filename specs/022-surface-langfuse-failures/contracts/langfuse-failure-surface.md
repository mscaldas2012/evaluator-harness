# Contract: Langfuse Failure Surface

## User-Facing Status Contract

Commands that run, compare, export, or route live Langfuse-backed evaluation data must surface a combined status:

- `success`: Model/evaluator work completed and required Langfuse linkage was persisted or confirmed.
- `success_with_warnings`: Model/evaluator work completed, but one or more recoverable Langfuse lookup or persistence operations failed or were incomplete.
- `failed`: Required live linkage or lookup failed and the requested output would be misleading.

## Warning Contract

Each warning shown in CLI output or exported artifacts must include:

- A concise message describing what was not persisted or confirmed.
- The operation category, such as baseline lookup, dataset item lookup, dataset run item recording, trace lookup, or score retrieval.
- At least one affected identity when available, such as run ID, item ID, trace ID, score name, dataset name, or baseline selector.
- Redacted diagnostic detail when useful.
- Aggregated counts when multiple records share the same failure.

Warnings must not include:

- Langfuse secret keys or public keys.
- Authorization headers.
- Raw credential values.
- Sensitive request headers.

## Expected Not-Found Contract

Expected not-found is not a persistence failure when:

- The live lookup completed successfully.
- The requested selector or identity was searched in the intended scope.
- No access, connectivity, pagination, malformed response, or unexpected service error occurred.

Expected not-found must remain distinguishable from failure in tests and user-facing messages.

## Fallback Contract

When live lookup fails and local or cached data is used:

- The output must record that fallback data was used.
- The original live lookup failure must remain visible as a warning.
- The output must not imply live confirmation succeeded.

## Blocking Contract

The workflow must fail rather than continue when:

- Required baseline identity cannot be established for a comparison.
- Required dataset identity cannot be established for dataset run item linkage and the requested output depends on that live linkage.
- Required score or trace confirmation failure would make the requested report misleading.

Recoverable failures may preserve local outputs when the requested command still has useful, truthful output with warnings.
