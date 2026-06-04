# Implementation Plan: Shared Scenario Config References

**Branch**: `013-dfe-config-refs` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-dfe-config-refs/spec.md`

## Summary

Add a generic `config_refs.evaluation` project configuration reference that lets
scenario-specific project YAMLs reuse one shared evaluation configuration file
for evaluators, score definitions, judge setup, and human review policy. The
configuration loader will resolve the shared evaluation file before existing
Pydantic validation, reject conflicting local/shared evaluation fields, and keep
single-file project configs working unchanged. Add optional scenario identity
metadata that, when present, is validated and emitted into traces, exports, and
review payloads. Deliver the DFE audience projects as the first use case:
General public, Health care provider, and Public health SME project YAMLs that
reuse a single `dfe_readability.yaml` shared evaluation config while varying
dataset identity and task prompt.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing `pydantic`, `PyYAML`, `rich`, `pytest`, and
current harness config, runner, export, annotation queue, and Langfuse client
helpers.

**Python Environment Management**: For Python features, use `uv` for
environment management, dependency setup, lockfile management, and command
execution. Prefer `uv sync` and `uv run ...`.

**Storage**: Filesystem YAML only. No database or service. Shared evaluation
config files live under `configs/shared/`; scenario project configs remain under
`configs/projects/`.

**Testing**: `pytest` unit, contract, and integration tests. Default tests use
fake Langfuse/provider clients and do not require live credentials.

**Target Platform**: Local developer machines and CI runners.

**Project Type**: Local Python CLI.

**Performance Goals**: Resolving one shared evaluation config for a project
should add negligible validation overhead; validating the three DFE scenario
configs should complete within the same order of time as validating three
single-file project configs.

**Constraints**: Shared evaluation config may provide only evaluators, score
definitions, judge setup, and human review policy. Scenario-owned fields
including project identity, dataset, task prompt, baseline, and candidates must
remain in the scenario project config. Conflicting local/shared evaluation
fields fail validation. Scenario identity is optional globally, but complete
when present.

**Scale/Scope**: One project config is still loaded and run at a time. The first
use case has three DFE audience project configs sharing one evaluation config.
The design supports future scenario groups without hardcoded scenario names.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature improves project configuration and
  metadata sent to Langfuse. It does not replace Langfuse tracing, scoring,
  evaluator setup, dashboards, comparisons, or human annotation queues.
- **Thin harness scope**: PASS. The design adds small config-loading and
  metadata helpers inside the existing local Python CLI. No services,
  orchestration, custom dashboards, or local APIs are introduced.
- **Dataset simplicity**: PASS. Scenario projects still use ordinary project
  dataset definitions, including CSV with an `input` column as the default
  runnable shape.
- **Reproducibility metadata**: PASS. Scenario identity, when present, expands
  trace/export/review provenance while preserving existing project, provider,
  model, prompt, evaluator, dataset, baseline, and parameter metadata.
- **Baseline-centric workflow**: PASS. Each scenario project still runs the
  existing baseline-first workflow independently before candidate comparisons.
- **Minimal local state**: PASS. Local state remains YAML configs, datasets, and
  prompts. No persistent runtime store is added.
- **Human review awareness**: PASS. Shared human review policy remains
  Langfuse Human Annotation Queue based, and scenario metadata improves reviewer
  context.
- **Local-first execution**: PASS. Workflows remain runnable with
  `uv run python run_experiment.py ...`.

## Project Structure

### Documentation (this feature)

```text
specs/013-dfe-config-refs/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- project-config-config-refs.md
|   `-- cli-validation.md
|-- checklists/
|   `-- requirements.md
`-- spec.md
```

### Source Code (repository root)

```text
configs/
|-- projects/
|   |-- dfe-general-public.yaml
|   |-- dfe-healthcare-provider.yaml
|   `-- dfe-public-health-sme.yaml
`-- shared/
    `-- dfe_readability.yaml

src/
`-- evaluator_harness/
    |-- config.py
    |-- exports.py
    |-- langfuse_client.py
    `-- runner.py

tests/
|-- contract/
|   `-- test_cli_validate_config_refs.py
|-- integration/
|   `-- test_dfe_config_refs.py
`-- unit/
    |-- test_config_refs.py
    |-- test_scenario_metadata.py
    `-- test_exports.py
```

**Structure Decision**: Keep shared evaluation config resolution in
`config.py`, close to YAML loading and Pydantic validation. Keep scenario
metadata propagation in the existing runner/export/review payload surfaces that
already build trace, CSV, and annotation queue metadata. Do not add a new
scenario runner or multi-project orchestration layer.

## Complexity Tracking

No constitution violations.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Use application-level `config_refs.evaluation`, not YAML-native includes.
- Resolve shared config before `ProjectConfig` validation so all downstream
  workflows consume a normal effective project config.
- Reject conflicts instead of applying precedence.
- Keep shared evaluation config limited to evaluation/review sections.
- Make scenario identity optional, complete when present, and include it in
  traces, exports, and review payloads.

## Phase 1 Design

See [data-model.md](./data-model.md), [contracts/project-config-config-refs.md](./contracts/project-config-config-refs.md),
[contracts/cli-validation.md](./contracts/cli-validation.md), and
[quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Config reference schema**: add models for `config_refs.evaluation` and
   optional `scenario` identity while preserving existing single-file configs.
2. **Shared config resolution**: load shared evaluation YAML relative to the
   referencing project file, merge allowed sections, and reject conflicts or
   disallowed shared sections.
3. **Scenario metadata propagation**: attach scenario metadata to run metadata,
   trace metadata, exports, evaluator/review payloads, and Langfuse filtering
   metadata when present.
4. **DFE shared config and projects**: extract DFE readability evaluators, judge
   setup, and human review into `configs/shared/dfe_readability.yaml`; add the
   three DFE audience project configs with scenario identity and audience task
   prompts.
5. **Validation and regression tests**: cover config resolution, missing refs,
   disallowed sections, conflict rejection, optional scenario identity,
   metadata propagation, DFE validation, and existing config compatibility.
6. **Docs and quickstart**: document `config_refs.evaluation`, scenario identity,
   DFE audience commands, and the no-hardcoded-scenario-name rule.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. The design sends clearer metadata to Langfuse and
  continues using Langfuse-native scoring, evaluators, traces, exports, and
  review queues.
- **Thin harness scope**: PASS. The implementation remains a small local CLI
  config enhancement with no new service boundary.
- **Dataset simplicity**: PASS. Dataset definitions remain per-project and
  continue to support CSV with `input`.
- **Reproducibility metadata**: PASS. The effective config remains
  deterministic, and scenario fields improve provenance.
- **Baseline-centric workflow**: PASS. Baseline/candidate behavior is unchanged
  except for additional metadata.
- **Minimal local state**: PASS. Shared configs are static files; no runtime
  state is introduced.
- **Human review awareness**: PASS. Review payloads and queues gain scenario
  context without changing Langfuse as the review surface.
- **Local-first execution**: PASS. All validation, sync, run, export, and tests
  remain `uv run ...` workflows.
