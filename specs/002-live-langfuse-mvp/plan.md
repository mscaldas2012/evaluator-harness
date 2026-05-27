# Implementation Plan: Live Langfuse MVP

**Branch**: `002-live-langfuse-mvp` | **Date**: 2026-05-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-live-langfuse-mvp/spec.md`

## Summary

Add the first live execution path to the existing headless evaluation harness:
sync project datasets and score configs into Langfuse, verify Langfuse
connectivity before provider calls, run a real Azure OpenAI baseline, persist
baseline references and compatibility metadata in Langfuse only, and run a fake
or dry-run candidate against that persisted baseline in a later command.

This feature intentionally keeps live provider scope narrow. It proves the live
Langfuse system-of-record workflow end to end without adding a UI, local
database, custom scorer, or live candidate provider implementation.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `langfuse>=3.0`, `openai>=1.0`,
`azure-identity`, `httpx`, `pydantic`, `pydantic-settings`, `PyYAML`, `typer`,
`rich`

**Python Environment Management**: Use `uv` for environment creation,
dependency setup, lockfile management, and command execution. Canonical setup is
`uv sync`; canonical run and test commands use `uv run ...`.

**Storage**: Langfuse is the live system of record for datasets, dataset
runs/experiments, traces, score configs, scores, baseline references, and
annotation queue items. Local files remain limited to project configs, prompts,
local CSV/JSON authoring, docs, tests, and optional exports. No local baseline
registry file is used for live operation. Live traces should be created through
Langfuse Dataset experiment/run linkage where possible so each trace is
correlated to its originating dataset item.

**Testing**: `pytest` with unit, contract, fake integration, and opt-in live
integration tests. Default tests must not require Langfuse, Azure OpenAI,
OpenAI, Ollama, or network credentials. Live tests are marked `live` and require
explicit execution plus configured `.env` or host environment credentials.

**Target Platform**: Local developer machine and CI runners. Live smoke tests
require network access to Langfuse and Azure OpenAI.

**Project Type**: Headless Python CLI.

**Performance Goals**: A sample live baseline over a smoke dataset should
complete within 5 minutes after credentials are configured. Harness overhead
should remain small relative to provider latency.

**Constraints**: Fail before any model call when Langfuse connectivity or
workspace access cannot be verified. Baseline execution must use live Azure
OpenAI. Candidate execution may use fake or dry-run output for this MVP. Re-run
baseline and candidate commands intentionally create distinct live runs; sync
and queue-routing commands remain idempotent.

**Scale/Scope**: One live Azure OpenAI baseline path, Langfuse Dataset sync,
harness-managed score config sync, persisted baseline lookup from Langfuse,
fake/dry-run candidate persistence, optional annotation queue routing to an
existing queue, deterministic stable review cohorts by dataset item identity,
CSV export, and opt-in live smoke tests.
Dry-run candidate execution is a first-class provider/config path for the live
MVP, not hidden test-only provider injection.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature uses Langfuse Datasets and dataset
  runs/experiments for comparable runs, Langfuse traces for observability,
  Langfuse score configs and scores for evaluation results, and existing
  Langfuse Annotation Queues for human review. Azure OpenAI calls prefer the
  Langfuse OpenAI SDK integration when compatible with the required Azure AD
  token and APIM subscription-key setup.
- **Thin harness scope**: PASS. The live MVP remains a local Python CLI with
  narrow adapters and no service runtime, UI, database, orchestration framework,
  or local dashboard.
- **Dataset simplicity**: PASS. CSV with `input` remains the minimum local
  dataset shape. Syncing to Langfuse is a command responsibility, not an
  authoring burden.
- **Reproducibility metadata**: PASS. Live traces and run metadata include
  project, dataset, prompt version, evaluator set, provider, model, model
  parameters, timestamp, latency, token usage/cost when available, originating
  dataset item identity, and baseline reference where applicable.
- **Baseline-centric workflow**: PASS. Candidate runs resolve a compatible
  persisted baseline from Langfuse before any candidate output is generated.
- **Minimal local state**: PASS. Live baseline references are not persisted in
  local files. Langfuse stores the live state needed across command executions.
- **Human review awareness**: PASS. Human review is routed to existing
  Langfuse Annotation Queues, and automated evaluation remains decision
  support.
- **Local-first execution**: PASS. The workflow runs through `uv run python
  run_experiment.py ...`.
- **Test coverage**: PASS. The plan requires default credential-free tests plus
  explicit live integration coverage for Langfuse and Azure OpenAI.

## Project Structure

### Documentation (this feature)

```text
specs/002-live-langfuse-mvp/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- cli.md
|   `-- langfuse-live.md
`-- checklists/
```

### Source Code (repository root)

```text
configs/
|-- projects/
|   `-- rewrite_quality.yaml
`-- providers.yaml

datasets/
`-- rewrite_quality.csv

prompts/
`-- rewrite_quality/
    |-- task_prompt.md
    `-- evaluators/
        `-- clarity.md

src/
`-- evaluator_harness/
    |-- cli.py
    |-- config.py
    |-- dataset_loader.py
    |-- langfuse_client.py
    |-- runner.py
    |-- baseline_registry.py
    |-- review_selection.py
    |-- exports.py
    |-- errors.py
    `-- providers/
        |-- base.py
        |-- openai_compatible.py
        `-- ollama.py

tests/
|-- unit/
|-- contract/
|-- integration/
`-- fixtures/

run_experiment.py
pyproject.toml
.env.example
docs/
```

**Structure Decision**: Extend the existing single-package CLI. Add live
Langfuse behavior behind the current command surface and test it with fakes by
default plus opt-in `live` tests. Do not add new application layers.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Use Langfuse-hosted Datasets for valid live experiment runs because the
  Langfuse SDK creates dataset runs that are inspectable and comparable in the
  Langfuse UI, with traces linked to the originating dataset items. If Langfuse
  does not expose a dataset version, use a deterministic dataset compatibility
  version derived from stable item IDs and input hashes.
- Use Langfuse metadata/tags/traces to persist baseline references and
  compatibility fingerprints instead of writing local baseline registry state.
- Prefer `langfuse.openai.AzureOpenAI` for the Azure OpenAI baseline path when
  it supports the required `azure_ad_token` and default APIM subscription-key
  headers; fall back to explicit Langfuse trace/generation logging only if that
  integration cannot capture the required metadata.
- Sync only harness-managed score configs. Existing incompatible managed configs
  fail with remediation; user-owned score configs are referenced but never
  created or modified.
- Route human review items only to existing annotation queues in the MVP.
  Queue creation remains backlog automation.
- Select random human-review calibration items as a deterministic dataset-item
  cohort so baseline and compatible candidate runs use the same random sample.
  Run-specific risk items may be added separately.

## Phase 1 Design

See [data-model.md](./data-model.md), [contracts/cli.md](./contracts/cli.md),
[contracts/langfuse-live.md](./contracts/langfuse-live.md), and
[quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Live connectivity and settings**: load `.env`/environment settings,
   support `LANGFUSE_HOST` with `LANGFUSE_BASE_URL` compatibility, verify
   Langfuse workspace access, and fail before provider calls when unavailable.
2. **Langfuse asset sync**: create/resolve Langfuse Datasets and
   harness-managed score configs idempotently.
3. **Azure OpenAI baseline**: acquire Azure AD token from tenant ID, client ID,
   client secret, and scope; call Azure OpenAI with APIM subscription key; log
   traced outputs and metadata to Langfuse.
4. **Langfuse-only baseline lookup**: persist and resolve baseline references
   and compatibility fingerprints from Langfuse across command executions.
5. **Dry-run candidate against baseline**: create a distinct candidate dataset
   run with first-class dry-run provider outputs linked to the compatible
   persisted baseline.
6. **Review routing and export**: select the stable random calibration cohort by
   dataset item identity, add run-specific risk review items when present, route
   to a configured existing annotation queue when present, skip duplicates, and
   export a lightweight CSV summary.
7. **Live smoke coverage**: add opt-in integration tests covering real
   Langfuse dataset sync, score config sync, Azure OpenAI baseline execution,
   dry-run candidate execution, review routing where configured, and export.

## Test Strategy

- **Unit tests**: environment loading and secret redaction, Langfuse host alias
  resolution, baseline compatibility fingerprinting, live metadata construction,
  dataset item to trace correlation metadata, stable review cohort selection,
  managed score config compatibility, first-class dry-run provider
  configuration, dry-run candidate output, and Azure credential/client factory
  behavior with mocked dependencies.
- **Contract tests**: CLI arguments and exit codes for `validate`,
  `sync-dataset`, `sync-score-configs`, `run --mode baseline`,
  `run --mode candidate --baseline latest-compatible`, `select-review`, and
  `export`; Langfuse request/metadata shapes, including dataset item linkage.
- **Fake integration tests**: live flow using fake Langfuse and fake provider
  objects, including fail-fast Langfuse behavior, partial provider failures, and
  the same random calibration item IDs selected for baseline and compatible
  candidate runs.
- **Live integration tests**: `pytest -m live` tests that hit real Langfuse and
  Azure OpenAI only when explicit credentials are present. These tests must be
  skipped by default and must use small smoke datasets. The live suite covers
  dataset sync, score config sync, Azure OpenAI baseline execution, dry-run
  candidate execution, annotation queue routing when a queue ID is configured,
  and CSV export.

## Langfuse Automation Backlog

The live MVP automates only the assets required to run safely now. Additional
automation remains tracked for later phases:

1. Create or resolve Human Annotation Queues programmatically.
2. Publish or sync evaluator prompts to Langfuse Prompt Management.
3. Configure Langfuse LLM-as-a-Judge evaluators and variable mappings.
4. Trigger evaluator execution automatically after baseline/candidate runs.
5. Create saved comparison views or dashboard links for common run comparisons.
6. Build CI scheduling for nightly or release-gate live evaluations.
7. Add live candidate providers beyond dry-run output.
8. Add evaluator calibration reports that compare human annotations to judge
   scores.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Design artifacts assign live datasets, runs,
  traces, scores, comparisons, and human annotations to Langfuse. Local code
  executes experiments and logs metadata only.
- **Thin harness scope**: PASS. Contracts preserve CLI-only operation and keep
  candidate live execution out of scope for this MVP.
- **Dataset simplicity**: PASS. Local CSV remains simple; Langfuse Dataset sync
  makes it live-ready.
- **Reproducibility metadata**: PASS. Data model and live contract define the
  required metadata and baseline compatibility fields.
- **Baseline-centric workflow**: PASS. Candidate execution is blocked until a
  compatible baseline is resolved from Langfuse.
- **Minimal local state**: PASS. No local baseline registry is introduced.
- **Human review awareness**: PASS. Review uses Langfuse Annotation Queues and
  keeps automated scores separate from human judgment.
- **Local-first execution**: PASS. Quickstart uses `uv run python
  run_experiment.py`.
- **Test coverage**: PASS. The test strategy covers offline and live boundaries
  without requiring credentials in default test runs.

## Complexity Tracking

No constitution violations.
