# Implementation Plan: Create Annotation Queues

**Branch**: `003-create-annotation-queues` | **Date**: 2026-05-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-create-annotation-queues/spec.md`

## Summary

Add project-managed Langfuse Human Annotation Queue automation to the existing
headless evaluation harness. The harness will create or reuse a project queue
from configuration, persist the resolved queue reference in lightweight local
state, and route stable human-review selections to that queue without requiring
`LANGFUSE_ANNOTATION_QUEUE_ID`.

The feature remains Langfuse-first: Langfuse owns queues and review items. The
harness only synchronizes queue references, ensures score configs exist before
queue creation, and routes selected traces to the resolved queue.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `langfuse>=3.0`, `pydantic`, `PyYAML`, `typer`,
`pytest`

**Python Environment Management**: Use `uv` for environment creation,
dependency setup, lockfile management, and command execution. Canonical setup is
`uv sync`; canonical run and test commands use `uv run ...`.

**Storage**: Langfuse is the system of record for annotation queues and queue
items. Local state is limited to a small project-managed queue reference file
under `.evaluator-harness/` so future local commands can resolve the same
Langfuse queue without secrets or manual environment variables.

**Testing**: `pytest` with unit, contract, fake integration, and opt-in live
integration tests. Default tests must not require Langfuse credentials or
network access. Live tests remain marked `live`.

**Target Platform**: Local developer machine and CI runners. Live tests require
network access to Langfuse.

**Project Type**: Headless Python CLI.

**Performance Goals**: Queue sync should complete in under 30 seconds for a
normal project after Langfuse credentials are configured. Review routing
overhead should remain small relative to experiment execution time.

**Constraints**: Queue creation requires compatible score config IDs. Queue
sync must be idempotent by project identity and managed queue name. User-owned
queue references must never be created, modified, or deleted by the harness.
Managed queue names use
`EH_<project-slug>_<project-version>_review_<review-policy-version>` unless
overridden, and local reference files use
`.evaluator-harness/queue-references/<project-slug>__<project-version>__<review-policy-version>.json`.

**Scale/Scope**: One managed annotation queue per project/review policy for the
MVP. Reviewer assignment management, queue deletion, queue migration, and
Langfuse permission configuration are out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. Langfuse remains the owner of annotation queues and
  review queue items. The harness creates/reuses Langfuse-native queues instead
  of building a local review queue.
- **Thin harness scope**: PASS. The design adds a CLI sync path and small local
  reference file only; no service runtime, UI, scheduler, or local queue system.
- **Dataset simplicity**: PASS. CSV with an `input` column remains unchanged.
  Queue sync does not affect dataset authoring.
- **Reproducibility metadata**: PASS. Queue references include project identity,
  review policy version, score config IDs, and sync status. Routed items retain
  trace/run/dataset item metadata.
- **Baseline-centric workflow**: PASS. Baseline and compatible candidate runs
  route selected items to the same resolved project queue.
- **Minimal local state**: PASS. Local state stores only non-secret queue
  references needed for repeatable local commands.
- **Human review awareness**: PASS. The feature strengthens Langfuse Human
  Annotation Queue use and keeps automated evaluation as decision support.
- **Local-first execution**: PASS. All workflows run through `uv run python
  run_experiment.py ...`.

## Project Structure

### Documentation (this feature)

```text
specs/003-create-annotation-queues/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- cli.md
|   `-- langfuse-annotation-queues.md
`-- checklists/
```

### Source Code (repository root)

```text
src/
`-- evaluator_harness/
    |-- cli.py
    |-- config.py
    |-- langfuse_client.py
    |-- runner.py
    |-- review_selection.py
    |-- annotation_queues.py
    `-- errors.py

tests/
|-- unit/
|-- contract/
|-- integration/
`-- fixtures/

configs/
`-- projects/
    `-- rewrite_quality.yaml

.evaluator-harness/
`-- queue-references/        # generated, ignored local state
```

**Structure Decision**: Extend the existing single-package CLI. Add an
annotation queue helper module only if it keeps Langfuse queue resolution and
local reference persistence out of the runner. Do not introduce a database,
service, or UI.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Use Langfuse annotation queue API/SDK methods to create and reuse queues.
- Require synced score config IDs before creating a managed queue because
  Langfuse queue creation accepts `score_config_ids`.
- Persist queue references in `.evaluator-harness/queue-references/` as
  non-secret local state keyed by project identity and review policy version.
- Derive managed queue names with the `EH_` prefix so queues created by the
  Evaluation Harness are identifiable in Langfuse.
- Keep user-owned queue references supported and read-only.
- Preserve `LANGFUSE_ANNOTATION_QUEUE_ID` as an optional explicit override for
  ad hoc live testing and backwards compatibility.

## Phase 1 Design

See [data-model.md](./data-model.md),
[contracts/cli.md](./contracts/cli.md),
[contracts/langfuse-annotation-queues.md](./contracts/langfuse-annotation-queues.md),
and [quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Config and local state contract**: add queue ownership fields, managed
   queue naming defaults, and a non-secret queue reference store.
2. **Queue sync command**: create/reuse a managed queue after score config sync
   and print created/reused/user-owned/skipped status.
3. **Review routing resolution**: make `select-review` resolve the project
   queue from config, local state, or optional environment override.
4. **Live review smoke update**: remove the hard requirement for
   `LANGFUSE_ANNOTATION_QUEUE_ID` when queue creation is supported.
5. **Coverage**: add offline unit/contract/fake integration tests plus opt-in
   live coverage for queue sync and routing.

## Test Strategy

- **Unit tests**: review queue policy validation, managed queue name
  derivation, queue reference serialization, user-owned read-only behavior,
  missing score config remediation, local state secret exclusion, and queue
  resolution order.
- **Contract tests**: CLI output and exit codes for `sync-annotation-queue`
  and `select-review` with managed, user-owned, disabled, and unavailable
  states.
- **Fake integration tests**: fake Langfuse queue create/list/get/item calls,
  idempotent repeated sync, duplicate routing skip, and baseline/candidate
  routing to the same queue.
- **Live integration tests**: opt-in tests that create or reuse a Langfuse
  annotation queue for the smoke project, route selected review items, and skip
  only when Langfuse queue automation is unavailable or credentials are absent.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Queue creation and review item routing use
  Langfuse-native annotation queues.
- **Thin harness scope**: PASS. The implementation stays CLI-only with a small
  helper and no new runtime service.
- **Dataset simplicity**: PASS. Dataset authoring remains unchanged.
- **Reproducibility metadata**: PASS. Queue references and routed items include
  project, review policy, score config, run, trace, and dataset item metadata.
- **Baseline-centric workflow**: PASS. A single resolved queue is reused for
  baseline and compatible candidate review routing.
- **Minimal local state**: PASS. Local queue reference files contain non-secret
  identifiers only.
- **Human review awareness**: PASS. Human review moves further into Langfuse
  Annotation Queues.
- **Local-first execution**: PASS. Quickstart uses `uv run python
  run_experiment.py`.

## Complexity Tracking

No constitution violations.
