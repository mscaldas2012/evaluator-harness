# Contract: Run Item Execution Behavior

This contract describes the behavior that must remain stable while baseline and candidate per-item execution move to a shared path.

## Shared Item Execution

For every baseline or candidate dataset item, the harness must:

1. Create a trace id from the current run id and dataset item id.
2. Create the same trace name format currently used for that run type.
3. Render the applicable prompt against the dataset row context.
4. Build item comparison session identity from project, dataset, baseline anchor, and item identity.
5. Build provider request metadata with project, dataset, prompt, parameter, trace, session, and evaluator-set identity.
6. Open the existing trace span behavior when available.
7. Validate provider prompt roles before provider invocation.
8. Invoke the provider once for the item.
9. Log a success trace when provider invocation succeeds.
10. Log a failure trace when validation or provider invocation fails after trace preparation.
11. Attempt dataset run item recording for success and failure traces when item and trace identity are available.
12. Preserve Langfuse warning collection and run-result status behavior.

## Baseline-Specific Behavior

Baseline runs must:

- Create a new baseline run id and baseline reference.
- Use the project task prompt.
- Use the new baseline run id as the session baseline anchor.
- Enqueue baseline evaluator payloads only for successful item executions.
- Include evaluator score configuration references in baseline evaluator payloads.
- Record the baseline reference after item execution.
- Return a baseline run result with the same user-visible fields as today.

## Candidate-Specific Behavior

Candidate runs must:

- Resolve a compatible baseline before item execution.
- Fail before item execution when no compatible baseline reference is available.
- Use the candidate prompt override when configured, otherwise the project task prompt.
- Use the resolved baseline run id as the session baseline anchor.
- Enqueue candidate evaluator payloads only for successful item executions.
- Include baseline output, baseline reference, prompt identities, parameter identity, generation parameter hash, and variant identity in candidate evaluator payloads.
- Return a candidate run result with the same user-visible fields as today.

## Failure Behavior

When prompt validation or provider invocation fails after item preparation:

- The failed item count increments.
- Completed item count does not increment.
- A failure trace is logged with item id, run id, trace id, trace name, prompt evidence, session identity, dataset identity, model/provider metadata, and redacted error information.
- Dataset run item recording is attempted when item and trace identity are available.
- No evaluator payload is enqueued for that failed item.

## Behavior Preservation Rule

The implementation must preserve current user-visible behavior exactly unless a baseline/candidate parity fix is explicitly identified in implementation notes or tests. Any parity fix must have regression coverage showing the intended shared behavior for both run types.
