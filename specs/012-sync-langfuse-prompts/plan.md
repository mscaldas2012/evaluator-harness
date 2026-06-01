# Implementation Plan: Sync Langfuse Prompts

**Branch**: `012-sync-langfuse-prompts` | **Date**: 2026-06-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-sync-langfuse-prompts/spec.md`

## Summary

Add an optional prompt publishing workflow that syncs repository task prompts
and evaluator prompts into Langfuse while preserving repository files as the
source of truth for validation and runs. The implementation will enumerate
project prompt artifacts, derive stable managed names and content identities,
dry-run/create Langfuse text or chat prompt versions, refuse changed content under
an already-synced configured prompt version, and expose synced prompt references
in trace metadata and exports when available.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `pydantic`, `PyYAML`, `rich`, `pytest`, existing
`langfuse` SDK, existing prompt parser/rendering helpers, existing CLI runner
and progress reporter.

**Python Environment Management**: For Python features, use `uv` for
environment management, dependency setup, lockfile management, and command
execution. Prefer `uv sync` and `uv run ...`.

**Storage**: No database or service. Optional local binding/reference file under
`configs/langfuse/prompt_bindings/` for last-known synced prompt references;
Langfuse remains the remote system of record for prompt artifacts.

**Testing**: `pytest` unit and contract tests, with optional live tests behind
the existing live-test guard for Langfuse prompt API smoke coverage.

**Target Platform**: Local developer machines and CI runners.

**Project Type**: Local Python CLI.

**Performance Goals**: Sync at least one task prompt plus 10 evaluator prompts
in under two minutes excluding Langfuse outages; repeat unchanged sync should
complete without creating prompt versions.

**Constraints**: Repository prompt files remain authoritative. Prompt sync is
optional and must not be required for validate, run, evaluator setup, export, or
review workflows. Configured `prompt_version` is a strict release label:
changed content under an already-synced managed prompt version must fail with a
version-bump remediation. Harness-managed prompt artifacts must not overwrite
user-owned Langfuse prompts.

**Scale/Scope**: One project at a time; expected prompt count is one task prompt
plus the project's evaluator prompts, typically fewer than 50 prompt artifacts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature uses Langfuse-native prompt artifacts
  through the SDK and only stores local references for reproducibility and
  conflict detection.
- **Thin harness scope**: PASS. The design adds CLI commands and small helper
  modules inside the existing local Python CLI. No service, worker, database, or
  orchestration layer is introduced.
- **Dataset simplicity**: PASS. Prompt sync does not change dataset shape and
  preserves CSV-with-`input` support.
- **Reproducibility metadata**: PASS. The feature expands prompt provenance with
  local prompt identity and optional synced Langfuse prompt references while
  preserving existing run metadata.
- **Baseline-centric workflow**: PASS. Prompt sync is independent of baseline
  generation and does not alter candidate comparison behavior.
- **Minimal local state**: PASS. Local state is limited to prompt files,
  configs, and optional prompt binding/reference files.
- **Human review awareness**: PASS. Synced prompt references improve reviewer
  visibility in Langfuse without presenting automated judgments as final truth.
- **Local-first execution**: PASS. All workflows remain runnable with
  `uv run python run_experiment.py ...`; prompt sync is optional.

## Project Structure

### Documentation (this feature)

```text
specs/012-sync-langfuse-prompts/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- cli-sync-prompts.md
|   `-- prompt-binding-file.md
|-- checklists/
|   `-- requirements.md
`-- spec.md
```

### Source Code (repository root)

```text
configs/
`-- langfuse/
    `-- prompt_bindings/
        `-- <project>.yaml

src/
`-- evaluator_harness/
    |-- cli.py
    |-- exports.py
    |-- langfuse_client.py
    |-- prompts.py
    |-- prompt_sync.py
    `-- runner.py

tests/
|-- contract/
|   `-- test_cli_sync_prompts.py
|-- integration/
|   `-- live/
|       `-- test_live_sync_prompts_smoke.py
`-- unit/
    |-- test_prompt_sync.py
    |-- test_prompt_bindings.py
    `-- test_prompt_provenance.py
```

**Structure Decision**: Keep prompt sync in a small `prompt_sync.py` module that
uses existing prompt parsing and Langfuse client abstractions. CLI and runner
changes should be thin orchestration only. Prompt binding files mirror the
existing evaluator binding pattern but remain optional cache/reference state.

## Complexity Tracking

No constitution violations.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Use Langfuse SDK prompt APIs to create text or chat prompt versions.
- Treat configured `prompt_version` as a strict release label; changed content
  under the same managed prompt version is a conflict.
- Use local prompt binding files as optional last-known references, not as a
  runtime dependency.
- Include local prompt identity metadata on every run; include synced Langfuse
  prompt references only when known.

## Phase 1 Design

See [data-model.md](./data-model.md), [contracts/cli-sync-prompts.md](./contracts/cli-sync-prompts.md),
[contracts/prompt-binding-file.md](./contracts/prompt-binding-file.md), and
[quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Prompt artifact discovery**: enumerate task and evaluator prompt files from
   project config, parse legacy and role-based prompt shapes, and compute
   stable content identities.
2. **Prompt binding store**: add load/save/validate helpers for optional prompt
   binding records under `configs/langfuse/prompt_bindings/`.
3. **Langfuse prompt client methods**: add list/get/create helpers for text and
   chat prompt artifacts using the installed Langfuse SDK.
4. **Dry-run and sync orchestration**: implement dry-run and apply paths
   with created, reused, changed, conflict, skipped, and failed statuses plus
   progress reporting.
5. **CLI integration**: add `sync-prompts --project ... [--dry-run]` and print
   concise per-prompt statuses and remediation text.
6. **Prompt provenance metadata**: add local prompt identity to run metadata and
   optional synced Langfuse prompt references when binding matches content.
7. **Exports and docs**: include prompt reference fields in CSV exports when
   present and document usage in quickstart/README as needed.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. The design relies on Langfuse prompt artifacts and
  does not rebuild a prompt registry locally.
- **Thin harness scope**: PASS. The implementation remains a local CLI with
  small helpers and no new service boundary.
- **Dataset simplicity**: PASS. Dataset loading is unchanged.
- **Reproducibility metadata**: PASS. Prompt provenance is expanded and remains
  available even when prompt sync is skipped.
- **Baseline-centric workflow**: PASS. Baseline behavior is unaffected.
- **Minimal local state**: PASS. Binding files are optional reproducibility
  references and conflict guards.
- **Human review awareness**: PASS. Reviewers get clearer prompt links in
  Langfuse.
- **Local-first execution**: PASS. All commands use `uv run python
  run_experiment.py ...`; prompt sync is opt-in.
