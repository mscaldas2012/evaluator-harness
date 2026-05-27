# Implementation Plan: Lightweight Langfuse Evaluation Harness

**Branch**: `001-rewrite-eval-harness` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-rewrite-eval-harness/spec.md`

## Summary

Build a headless Python CLI that runs generic evaluation projects against a
baseline model and candidate model configurations, logs traces and complete
metadata to Langfuse, and delegates datasets, experiment comparison,
evaluators, scores, annotation queues, dashboards, and trace inspection to
Langfuse. The first project is rewrite quality, but the harness is project
driven so future use cases can provide different datasets and evaluator
prompts without changing the core runner.

The implementation will keep local CSV/JSON authoring for low setup friction,
then create, update, or resolve a Langfuse Dataset before valid baseline or
candidate execution. Baselines are reusable when project, dataset version,
prompt version, evaluator set, baseline model, and baseline parameters remain
compatible.

## Technical Context

**Language/Version**: Python 3.12+ recommended; compatible with Python 3.11+

**Primary Dependencies**: `langfuse`, `openai`, `azure-identity`, `httpx`,
`pydantic`, `pydantic-settings`, `PyYAML`, `typer`, `rich`

**Python Environment Management**: Use `uv` for environment creation,
dependency setup, lockfile management, and command execution. Canonical setup is
`uv sync`; canonical run and test commands use `uv run ...`.

**Storage**: Local filesystem for project configs, prompt files, and local
dataset authoring/import artifacts; Langfuse Datasets, traces, scores,
annotation queues, and dataset runs are the system of record

**Testing**: `pytest`, `respx` or `pytest-httpx` for HTTP mocking, temporary
filesystem fixtures for project/dataset validation. Tests are mandatory for
every feature slice and must cover success paths, validation failures, provider
failures, Langfuse failures, metadata correctness, and CLI exit behavior where
applicable.

**Target Platform**: Local developer machine and CI runners with network access
to Langfuse and selected model providers

**Project Type**: Headless Python CLI

**Performance Goals**: 10-item smoke project completes baseline plus one
candidate in under 15 minutes after credentials are configured; per-item
overhead from harness metadata handling stays below model-provider latency

**Constraints**: Must fail fast when Langfuse is unreachable; no local UI, local
dashboard, local scoring engine, database, service API, orchestration framework,
or production inference gateway in MVP

**Scale/Scope**: MVP supports Azure OpenAI via the Langfuse-wrapped AzureOpenAI
client with Azure AD client-credentials authentication, Ollama, local CSV/JSON
authoring, Langfuse Dataset sync/resolve, baseline creation/reuse, candidate
runs, harness-managed Langfuse score config sync, configured Human Annotation
Queue routing, and optional lightweight exports

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. Datasets are resolved into Langfuse Datasets before
  valid runs; traces, evaluator execution, scores, annotation queues,
  dashboards, comparison, and inspection remain Langfuse-owned. The harness
  only executes models, validates project inputs, selects review candidates, and
  logs metadata. Provider adapters must prefer Langfuse SDK integrations or
  Langfuse-compatible provider APIs before manual tracing.
- **Thin harness scope**: PASS. The design is a local Python CLI with project
  configs, provider adapters, dataset import/resolve helpers, and no service
  runtime or UI.
- **Dataset simplicity**: PASS. Users can author CSV files with only `input`;
  optional IDs and metadata are supported. Langfuse Dataset sync is automatic
  run setup, not a manual schema burden.
- **Reproducibility metadata**: PASS. The plan records project identity,
  dataset identity/version, prompt version, evaluator versions, provider,
  model, model parameters, baseline reference, run identity, timestamps,
  latency, token usage, and costs when available.
- **Baseline-centric workflow**: PASS. Candidate runs require a compatible
  baseline reference and can reuse prior baselines when compatibility rules
  match.
- **Minimal local state**: PASS. Local state is limited to configs, prompts,
  local dataset authoring files, and optional exports. Langfuse remains the
  system of record.
- **Human review awareness**: PASS. Human review is routed through configured
  Langfuse Human Annotation Queues; automated evaluation is decision support.
- **Local-first execution**: PASS. The primary workflow is `uv run python
  run_experiment.py` or equivalent CLI entrypoint. Docker is optional and not
  required.
- **Test coverage**: PASS. The plan requires automated tests for validation,
  dataset identity, Langfuse Dataset sync/resolve, baseline compatibility,
  candidate execution, provider tracing mode selection, fail-fast Langfuse
  behavior, human review selection, and CLI exit behavior. Langfuse calls are
  tested with fakes/mocks or HTTP contracts, not live credentials.

## Project Structure

### Documentation (this feature)

```text
specs/001-rewrite-eval-harness/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- cli.md
|   `-- project-config.schema.yaml
`-- tasks.md
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
|-- evaluator_harness/
|   |-- __init__.py
|   |-- cli.py
|   |-- config.py
|   |-- dataset_loader.py
|   |-- langfuse_client.py
|   |-- runner.py
|   |-- baseline_registry.py
|   |-- review_selection.py
|   |-- exports.py
|   `-- providers/
|       |-- __init__.py
|       |-- base.py
|       |-- openai_compatible.py
|       `-- ollama.py
`-- tests/
    |-- unit/
    |-- integration/
    `-- fixtures/

run_experiment.py
pyproject.toml
README.md
docs/
`-- user-guide.md
```

**Structure Decision**: Use a single Python CLI package under
`src/evaluator_harness` with one root-level `run_experiment.py` convenience
entrypoint. Keep sample project configs, datasets, and prompts as filesystem
artifacts so they are easy to inspect and modify. Do not introduce `api/`,
`workers/`, `reports/` services, a database, or a local UI.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Prefer Langfuse Datasets as the experiment dataset system of record after
  local authoring/import.
- Use Langfuse SDK experiment/dataset run capabilities rather than building
  local comparison or scoring.
- Model providers are simple adapters: OpenAI-compatible API and Ollama for
  MVP. Adapters prefer Langfuse-supported or instrumented clients where
  available and use manual generation observations only as a documented
  fallback. The first OpenAI-compatible adapter is Azure OpenAI using tenant ID,
  client ID, client secret, scope, APIM subscription key, API version, and Azure
  endpoint.
- Human annotation uses configured Langfuse Human Annotation Queues in MVP;
  automatic queue creation remains backlog item `BL-003`.

## Phase 1 Design

See [data-model.md](./data-model.md), [contracts/cli.md](./contracts/cli.md),
[contracts/project-config.schema.yaml](./contracts/project-config.schema.yaml),
and [quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Project and dataset setup**: validate project YAML, prompt versions,
   dataset shape, provider declarations, and Langfuse reachability.
2. **Langfuse asset sync**: sync or resolve Langfuse Datasets and
   harness-managed score config schemas required by project evaluators. Score
   config sync is MVP scope because evaluator and annotation scores need stable
   schemas before valid runs.
3. **Baseline execution and reuse**: run or resolve compatible baselines and
   record baseline references.
4. **Candidate execution**: run candidate models or parameter variants against a
   compatible baseline.
5. **Review and export helpers**: select human review samples and provide
   lightweight exports without replacing Langfuse reporting.

## Test Strategy

- **Unit tests**: project config validation, dataset item identity generation,
  duplicate ID rejection, prompt/evaluator version loading, baseline
  compatibility fingerprints, score config prefix and compatibility validation,
  provider tracing mode selection, review sample selection, and metadata
  construction.
- **Contract tests**: CLI command arguments and exit codes, project config schema
  examples, Langfuse Dataset sync/resolve request shape, score config sync
  request/result behavior, trace metadata shape, and annotation queue item
  request shape.
- **Integration tests with fakes**: baseline run flow, candidate run with
  `latest-compatible`, candidate run with incompatible baseline rejection,
  Langfuse unreachable fail-fast behavior, provider timeout/retry behavior, and
  configured Human Annotation Queue routing.
- **No live-credential test dependency**: automated tests must not require
  Langfuse API keys, OpenAI keys, or a running Ollama instance unless explicitly
  marked as optional manual smoke tests.

## Langfuse Automation Backlog

The MVP automates only what is needed to execute valid runs and preserve
Langfuse as the system of record: dataset sync, run logging, and
harness-managed score config sync. Additional Langfuse configuration automation
is tracked here so it can be implemented incrementally:

1. **Evaluator prompt publication**: publish project LLM-as-a-Judge prompts to
   Langfuse prompt management and record prompt versions.
2. **Evaluator setup**: create or resolve Langfuse evaluator configuration and
   variable mappings for project evaluators.
3. **Human Annotation Queue setup**: create or resolve annotation queues and add
   the selected review sample idempotently.
4. **Dataset creation from traces**: create or extend datasets from selected
   Langfuse traces or observations.
5. **Comparison workspace setup**: create or link saved views, tags, or
   dashboards for common baseline-vs-candidate comparisons.
6. **Scheduled regression runs**: configure CI or scheduled jobs for repeat
   evaluations and regression alerts.
7. **Evaluator calibration support**: track human labels, evaluator outputs,
   disagreement summaries, and calibration datasets.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Contracts define Langfuse Dataset identity/version,
  trace metadata, baseline references, evaluator versions, and queue IDs; no
  local evaluation UI or scoring store is introduced. Provider contracts require
  checking Langfuse-compatible APIs/integrations before manual tracing.
- **Thin harness scope**: PASS. The CLI contract is file/config driven and
  provider adapters stay narrow.
- **Dataset simplicity**: PASS. CSV with `input` is the minimum dataset. Dataset
  sync/resolve hides Langfuse Dataset mechanics from non-engineer authors.
- **Reproducibility metadata**: PASS. Data model includes run fingerprints,
  dataset version, prompt/evaluator versions, model parameters, and baseline
  compatibility inputs.
- **Baseline-centric workflow**: PASS. Data model includes `BaselineReference`
  and explicit compatibility rules.
- **Minimal local state**: PASS. Persistent local artifacts are configs,
  prompts, local datasets, and optional exports only.
- **Human review awareness**: PASS. Review selection and annotation queue
  routing are modeled, but automated scores remain decision support.
- **Local-first execution**: PASS. Quickstart uses `uv run python
  run_experiment.py`.
- **Test coverage**: PASS. Test strategy covers all MVP feature slices and
  external integration boundaries without requiring live credentials.

## Complexity Tracking

No constitution violations.
