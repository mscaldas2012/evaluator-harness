# Implementation Plan: Prompt Roles and Variables

**Branch**: `011-prompt-roles-variables` | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-prompt-roles-variables/spec.md`

## Summary

Extend task prompts from a single rendered text string into a parsed prompt
definition that can remain legacy single-text or become an ordered set of
role-labeled Markdown message sections. Role-based prompt files use level-2
headings in the form `## role: <role-label>`. Dataset variables use
`{dataset.<field>}` placeholders, validate against selected dataset columns,
and render empty row values as empty strings.

The runtime keeps existing single-text prompt behavior, adds a rendered prompt
payload that can carry role messages, updates provider adapters to either send
role messages exactly or fail validation before a model call, and preserves
prompt identity, trace metadata, evaluator payloads, review payloads, and
exports.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `pydantic`, `PyYAML`, `typer`, `rich`, `pytest`,
`httpx`, `langfuse>=3.0`, `openai`, `azure-identity`, existing provider
adapters.

**Python Environment Management**: Use `uv` for environment creation,
dependency setup, lockfile management, and command execution. Canonical setup is
`uv sync`; canonical run and test commands use `uv run ...`.

**Storage**: No new persistent storage. Prompt definitions remain Markdown
files; project YAML continues to reference prompt paths and versions. Langfuse
remains the system of record for traces, observations, scores, run metadata,
comparison, and review. Local exports may include non-secret prompt shape
metadata.

**Testing**: `pytest` with unit, contract, integration, and optional live
tests. Default tests must not require live Azure, Langfuse, or network
credentials. Tests should cover prompt parsing, dataset variable validation,
provider role support validation, rendering, prompt identity, metadata, and
backward compatibility.

**Target Platform**: Local developer machines and CI runners.

**Project Type**: Headless Python CLI.

**Performance Goals**: Prompt parsing and variable substitution should add
negligible overhead compared with model latency. Validation should run within
the existing project validation flow without requiring provider calls.

**Constraints**: Preserve existing single-text prompt files and candidate prompt
override behavior. Do not add a service, dashboard, database, prompt registry,
external template engine, or provider role mapping in this feature. Provider
adapters must send configured role labels exactly when supported or fail before
model calls when unsupported.

**Scale/Scope**: One project prompt and optional full candidate prompt override
per model entry, rendered once per dataset item. Dataset variables are limited
to the `dataset.*` namespace for available dataset columns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. The feature changes prompt rendering and provider
  request shape only; traces, observations, scores, dashboards, comparison, and
  review remain Langfuse-native.
- **Thin harness scope**: PASS. The design adds parser/rendering helpers and
  provider adapter support inside the existing Python CLI. No services,
  orchestration, APIs, or prompt registry are introduced.
- **Dataset simplicity**: PASS. CSV with an `input` column remains the default
  runnable dataset shape. Additional dataset columns are optional prompt
  variable sources.
- **Reproducibility metadata**: PASS. Prompt identity expands to include prompt
  shape, message roles, content hash, version, and variable references while
  preserving existing run metadata.
- **Baseline-centric workflow**: PASS. Baseline creation, reuse, compatibility,
  and candidate comparison remain unchanged except for prompt identity awareness.
- **Minimal local state**: PASS. Local state remains prompt files, datasets,
  configs, reports, and Spec Kit artifacts. No long-lived store is added.
- **Human review awareness**: PASS. Review payloads keep prompt, dataset, and
  baseline/candidate context for human inspection in Langfuse.
- **Local-first execution**: PASS. Workflows remain runnable through
  `uv run python run_experiment.py ...`.

## Project Structure

### Documentation (this feature)

```text
specs/011-prompt-roles-variables/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- project-config.md
|   |-- prompt-file-format.md
|   `-- provider-runtime.md
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
|-- rewrite_quality/
|   `-- task_prompt.md
`-- dfe/
    `-- task_prompt.md

src/
`-- evaluator_harness/
    |-- config.py
    |-- runner.py
    |-- exports.py
    |-- prompts.py
    `-- providers/
        |-- base.py
        |-- dry_run.py
        |-- ollama.py
        `-- openai_compatible.py

tests/
|-- contract/
|   |-- test_cli_validate.py
|   `-- test_prompt_file_format.py
|-- integration/
|   |-- test_run_baseline.py
|   |-- test_run_candidate.py
|   `-- test_evaluator_observation_metadata.py
|-- unit/
|   |-- test_config.py
|   |-- test_exports.py
|   |-- test_prompt_refs.py
|   |-- test_prompt_roles.py
|   `-- test_provider_role_support.py
`-- fixtures/
    |-- prompts/
    `-- projects/
```

**Structure Decision**: Keep the existing single-package CLI. Add prompt parsing
and rendering helpers near current prompt behavior, preferably in a small
`src/evaluator_harness/prompts.py` module so `config.py`, `runner.py`, and
provider tests can share one parser. Provider adapters continue to implement
the existing local adapter pattern; `ModelRequest` grows to carry a rendered
prompt payload while preserving the legacy string prompt for compatibility.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Use Markdown `## role: <role-label>` headings for role-based task prompt
  files.
- Keep `dataset.*` as the only substitution namespace in this feature.
- Validate placeholders against dataset columns, not per-row non-empty values.
- Send role labels exactly for providers that support them; fail before model
  calls for providers that cannot faithfully send configured role labels.
- Defer explicit provider role mapping to a future feature.
- Include role-aware prompt shape in prompt identity metadata.

## Phase 1 Design

See [data-model.md](./data-model.md), [contracts/project-config.md](./contracts/project-config.md),
[contracts/prompt-file-format.md](./contracts/prompt-file-format.md),
[contracts/provider-runtime.md](./contracts/provider-runtime.md), and
[quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Prompt parser and data model**: parse legacy single-text files and
   role-based Markdown files, validate role headings, reject unassigned content,
   and expose a stable prompt definition model.
2. **Dataset variable validation and rendering**: parse `{dataset.<field>}`
   placeholders, validate against dataset columns, render row values including
   empty strings, and treat braces inside values as literal content.
3. **Config validation integration**: validate project and candidate prompt
   files, preserving legacy `template_variables` compatibility while adding
   dataset-column validation during project validation and run preparation.
4. **Runtime request payload**: extend model requests to carry either legacy
   text or ordered role messages; update runner tracing and evaluator/review
   payloads to consume the rendered prompt payload.
5. **Provider adapter support**: update OpenAI-compatible provider paths to send
   messages directly; define dry-run deterministic hashing for role messages;
   fail validation for providers that cannot faithfully send configured roles.
6. **Prompt identity and exports**: include prompt shape, message roles,
   variable references, and content hash in identity metadata and exports while
   keeping existing fields.
7. **Docs and examples**: add role-based prompt examples and validation guidance
   to user docs and fixtures.
8. **Coverage**: add unit, contract, integration, and optional live coverage for
   parsing, validation, provider behavior, metadata, and backward compatibility.

## Test Strategy

- **Unit tests**: Markdown role parser; malformed headings; unassigned content;
  placeholder extraction; column validation; empty value rendering; braces in
  data values; prompt identity hashing; provider role capability checks.
- **Contract tests**: CLI validation accepts role-based prompt files, rejects
  malformed role files, rejects unavailable dataset columns, and reports clear
  errors.
- **Fake integration tests**: baseline and candidate runs preserve role order,
  candidate prompt overrides replace the full prompt, prompt metadata appears
  on traces and evaluator payloads, and legacy single-text projects still pass.
- **Provider tests**: OpenAI-compatible SDK and REST payloads send configured
  role messages; dry-run hashing is stable for role messages; unsupported
  providers fail before model calls.
- **Live tests**: Optional smoke coverage may run role-based OpenAI-compatible
  prompts when credentials are available.
- **Default suite**: `uv run pytest -p no:cacheprovider` must pass without live
  Azure or Langfuse credentials.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. Langfuse remains the system of record; role-aware
  prompt data is additional metadata on existing traces and observations.
- **Thin harness scope**: PASS. Design adds local parsing/rendering and provider
  payload changes only.
- **Dataset simplicity**: PASS. CSV datasets remain valid; additional columns
  are optional variables.
- **Reproducibility metadata**: PASS. Prompt identity explicitly includes shape,
  roles, content, variables, and version.
- **Baseline-centric workflow**: PASS. Existing baseline reuse and comparison
  rules remain in place.
- **Minimal local state**: PASS. No new local state outside existing file
  artifacts.
- **Human review awareness**: PASS. Human review payloads retain prompt and
  dataset context.
- **Local-first execution**: PASS. All workflows remain local `uv run` commands.

## Complexity Tracking

No constitution violations.
