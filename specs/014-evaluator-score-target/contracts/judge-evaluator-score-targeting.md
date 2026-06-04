# Contract: Judge Evaluator Score Config Targeting

## Scope

This contract defines expected behavior for commands and setup flows that sync,
preview, audit, or apply Langfuse LLM-as-Judge evaluator rules.

## Commands In Scope

```powershell
uv run python run_experiment.py sync-score-configs --project <project-yaml>
uv run python run_experiment.py sync-judge-evaluators --project <project-yaml> --dry-run
uv run python run_experiment.py sync-judge-evaluators --project <project-yaml>
uv run python run_experiment.py sync-all --project <project-yaml> --dry-run
uv run python run_experiment.py sync-all --project <project-yaml>
```

## Preconditions

- The project config validates.
- Each LLM-as-Judge evaluator has a score definition.
- Harness-managed score configs are synced before applying judge evaluator
  setup, or the sync command performs score config sync first.
- User-owned score configs include a configured score config ID.

## Dry-Run Behavior

Dry-run judge evaluator setup MUST:

- Show each evaluator's intended score config name.
- Show each evaluator's intended score config ID when available.
- Avoid creating or updating Langfuse evaluator rules.
- Clearly indicate when score config IDs are unavailable because score config
  sync has not been applied.

## Apply Behavior

Apply-mode judge evaluator setup MUST:

- Create new evaluator rules with the expected score config ID.
- Reuse existing harness-managed evaluator rules only when their remote score
  config target matches the expected score config ID.
- Update existing harness-managed evaluator rules when the only mismatch is a
  safe operational field, including score config target when supported.
- Preserve existing evaluator filters, variable mappings, sampling, activation,
  evaluator source, and judge model or connection behavior.
- Write evaluator bindings that include the applied score config ID and name.

## Audit Behavior

Audit MUST:

- Report whether each evaluator rule is aligned with its expected score config.
- Identify expected and remote score config IDs when a mismatch exists.
- Preserve existing missing-binding warnings for remote rules not proven to be
  harness-managed.

## Failure Behavior

The system MUST block or fail with a clear remediation when:

- A required score config ID is missing before apply.
- Langfuse rejects evaluator rule creation with the specified score config
  target.
- A remote evaluator rule has a score config mismatch that cannot be safely
  updated.
- The evaluator rule is not proven to be harness-managed and would require
  mutation.

## Acceptance Checks

### Created Custom Evaluator Rule

Given a custom LLM-as-Judge evaluator with resolved score config ID
`score-config-1`, apply-mode setup creates an evaluator rule whose remote setup
targets `score-config-1`.

### Created Catalog Evaluator Rule

Given a Langfuse-managed catalog evaluator with resolved score config ID
`score-config-2`, apply-mode setup creates an evaluator rule whose remote setup
targets `score-config-2`.

### Existing Matching Rule

Given a harness-managed evaluator binding and a remote rule already targeting
the expected score config ID, audit and sync report the rule as reusable.

### Existing Mismatched Rule

Given a harness-managed evaluator binding and a remote rule targeting a
different score config ID, audit reports the mismatch and apply either aligns
the target or fails with remediation.

### Missing Score Config ID

Given score config sync has not produced an ID, apply-mode judge evaluator setup
does not create an evaluator rule without a target score config.
