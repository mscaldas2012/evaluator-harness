# Implementation Plan: Candidate Variants

**Branch**: `010-candidate-variants` | **Date**: 2026-05-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-candidate-variants/spec.md`

## Summary

Extend candidates from "alternate model only" into named experiment variants
that may differ by model, prompt, generation parameters, or a combination of
those axes. Candidate runs remain baseline-centric: a prompt-v2 candidate can
compare against an existing compatible prompt-v1 baseline, and all traces,
observations, evaluator payloads, scores, exports, and human-review routing
retain enough metadata to group by baseline reference, candidate variant, run,
dataset item, evaluator, prompt identity, model identity, and parameter
identity.

The design keeps the existing one-candidate-at-a-time CLI workflow. Candidate
prompt overrides are added as optional config on a candidate model entry, while
model and parameter variants continue to use the existing candidate model
configuration. To reduce accidental ambiguous comparisons, the CLI warns when
a candidate changes more than one comparison axis and requires either an
interactive `Y`/`y` confirmation or the explicit `--confirm-mixed-variant`
flag.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `pydantic`, `PyYAML`, `typer`, `rich`, `pytest`,
`httpx`, `langfuse>=3.0`, `openai`, `azure-identity`, existing provider
adapters.

**Python Environment Management**: Use `uv` for environment creation,
dependency setup, lockfile management, and command execution. Canonical setup is
`uv sync`; canonical run and test commands use `uv run ...`.

**Storage**: No new persistent storage. Project YAML stores candidate variant
definitions. Prompt files remain filesystem artifacts. Langfuse remains the
system of record for traces, observations, scores, comparison, and review.
Local reports may include non-secret variant metadata.

**Testing**: `pytest` with unit, contract, integration, and optional live
tests. Default tests must not require live Azure, Langfuse, or network
credentials. CLI confirmation behavior must be covered with Typer contract
tests.

**Target Platform**: Local developer machines and CI runners.

**Project Type**: Headless Python CLI.

**Performance Goals**: Variant validation and identity hashing should add
negligible overhead compared with model latency. Non-live fake-provider tests
must remain fast enough for the default suite.

**Constraints**: Do not add a service, worker, queue, local dashboard,
experiment database, or custom comparison engine. Do not require a new dataset
shape. Do not break existing model-only candidate configs. Do not require a new
baseline when only the candidate prompt changes. Do not store provider secrets
in variant metadata or local exports.

**Scale/Scope**: One or more named candidates per project, run one candidate at
a time through the existing CLI. The feature covers candidate generation,
metadata, validation, CLI confirmation, local exports, and docs. Batch campaign
scheduling is out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature keeps traces, observations, scores,
  comparisons, evaluator execution, dashboards, and human review in Langfuse.
  The harness only enriches generation/run metadata and local CLI guardrails.
- **Thin harness scope**: PASS. The design extends the existing Python CLI,
  config model, runner metadata, and exports. No service, API, scheduler, or
  orchestration framework is introduced.
- **Dataset simplicity**: PASS. Existing CSV datasets with an `input` column
  remain valid. Variant comparison continues to join baseline and candidate
  outputs by stable dataset item identity.
- **Reproducibility metadata**: PASS. Candidate runs record provider, model,
  parameters, prompt identity, evaluator versions, dataset identity, baseline
  reference, run identity, trace identity, and relevant non-secret variant
  identity metadata.
- **Baseline-centric workflow**: PASS. Candidate variants still require a
  compatible baseline reference. Prompt-v2 candidates are candidate-side
  changes and may compare to an existing prompt-v1 baseline.
- **Minimal local state**: PASS. No database or long-lived local store is
  added. Config, prompt files, datasets, reports, and Spec Kit artifacts remain
  the only local state.
- **Human review awareness**: PASS. Human Annotation Queue routing and review
  payloads preserve candidate variant and baseline reference metadata.
- **Local-first execution**: PASS. Workflows remain runnable with
  `uv run python run_experiment.py ...`.

## Project Structure

### Documentation (this feature)

```text
specs/010-candidate-variants/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- project-config.md
|   `-- cli-runtime.md
|-- checklists/
|   `-- requirements.md
`-- spec.md
```

### Source Code (repository root)

```text
configs/
`-- projects/
    `-- rewrite_quality.yaml

prompts/
`-- rewrite_quality/
    |-- task_prompt.md
    `-- task_prompt_v2.md

src/
`-- evaluator_harness/
    |-- cli.py
    |-- config.py
    |-- runner.py
    `-- exports.py

tests/
|-- contract/
|   |-- test_cli_run_candidate.py
|   `-- test_cli_validate.py
|-- integration/
|   |-- test_parameter_variants.py
|   |-- test_run_candidate.py
|   `-- test_evaluator_observation_metadata.py
|-- unit/
|   |-- test_config.py
|   |-- test_exports.py
|   `-- test_prompt_refs.py
`-- fixtures/
    `-- projects/
        |-- valid_parameter_variants.yaml
        `-- valid_prompt_variant_candidate.yaml
```

**Structure Decision**: Extend the existing single-package CLI and project
config. Candidate variants remain entries under `candidates`; optional
candidate-level prompt configuration is added only where needed. Shared variant
identity helpers live near runner/config behavior rather than as a separate
framework.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Keep candidate variants as named candidate config entries rather than adding
  a new top-level experiment campaign object.
- Add candidate-level task prompt override so prompt-v2 can be compared against
  prompt-v1 baseline outputs.
- Keep baseline compatibility anchored to baseline identity; candidate prompt
  changes do not force a new baseline when other baseline compatibility fields
  match.
- Compute stable non-secret prompt and parameter identities for trace,
  observation, export, and review metadata.
- Require CLI confirmation when a candidate changes multiple comparison axes,
  with `--confirm-mixed-variant` for scripted runs.
- Keep Langfuse evaluator filters based on project/evaluator metadata and
  `observation_role=model_output`, not provider-specific observation names.

## Phase 1 Design

See [data-model.md](./data-model.md),
[contracts/project-config.md](./contracts/project-config.md),
[contracts/cli-runtime.md](./contracts/cli-runtime.md), and
[quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Variant config model**: add optional candidate task prompt override,
   validate prompt files and variables, preserve existing model-only configs,
   and reject duplicate candidate names.
2. **Variant identity metadata**: compute candidate variant identity, prompt
   identity, model identity, and parameter identity; add these to run, trace,
   observation, evaluator payload, review payload, and export metadata.
3. **Prompt variant runtime**: render candidate prompts from the candidate
   override when present; keep baseline rendering from project task prompt.
4. **Baseline compatibility**: preserve existing baseline reference lookup for
   candidate prompt variants and keep baseline prompt identity separate from
   candidate prompt identity.
5. **Mixed-variant confirmation**: warn when a candidate changes more than one
   axis (`model`, `prompt`, `params`) and require interactive `Y`/`y` or
   `--confirm-mixed-variant`.
6. **Project examples and docs**: add rewrite-quality examples for prompt
   variants, parameter variants, model variants, and mixed variants.
7. **Coverage**: add unit, contract, integration, and optional live coverage
   for config validation, prompt rendering, metadata, exports, CLI guardrails,
   and Langfuse evaluator compatibility.

## Test Strategy

- **Unit tests**: candidate prompt override validation; duplicate candidate
  names; prompt identity hashing; parameter identity hashing; secret-free
  variant metadata; export row metadata.
- **Contract tests**: CLI candidate run prompts for mixed variants; `Y` and
  `y` proceed; any other input cancels; `--confirm-mixed-variant` bypasses the
  prompt; validation output lists candidate variants clearly.
- **Fake integration tests**: prompt-v2 candidate runs against existing
  prompt-v1 baseline; parameter-only variants share a baseline reference while
  producing distinct parameter identities; repeated candidate runs keep stable
  variant identity and unique run identity; mixed candidate traces remain
  evaluator-filterable.
- **Live tests**: optional smoke tests may run baseline, prompt variant, and
  parameter/model variants when credentials are available, then inspect
  Langfuse traces for prompt/model/parameter identity metadata and baseline
  references.
- **Default suite**: `uv run pytest -p no:cacheprovider` must pass without live
  Azure or Langfuse credentials.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. The feature adds metadata and CLI guardrails while
  leaving comparison, scoring, dashboards, evaluator execution, and human
  review in Langfuse.
- **Thin harness scope**: PASS. The implementation remains a small CLI/config/
  runner extension with no new services or local comparison engine.
- **Dataset simplicity**: PASS. No dataset shape changes.
- **Reproducibility metadata**: PASS. Candidate traces and exports carry
  prompt, model, parameter, variant, baseline, evaluator, dataset, and run
  identities.
- **Baseline-centric workflow**: PASS. Candidates still require a baseline
  reference, and prompt variants can reuse existing compatible baselines.
- **Minimal local state**: PASS. No new persistent local store.
- **Human review awareness**: PASS. Review payloads keep baseline and variant
  context.
- **Local-first execution**: PASS. All workflows use local `uv run ...`
  commands.

## Complexity Tracking

No constitution violations.
