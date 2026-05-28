# Implementation Plan: Azure API-Key Candidate Provider

**Branch**: `009-azure-api-key-provider` | **Date**: 2026-05-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-azure-api-key-provider/spec.md`

## Summary

Add config-driven support for Azure-hosted model deployments that authenticate
with endpoint/API-key credentials instead of tenant/client credentials. The
harness will allow these deployments to be used as normal candidate models in
the existing baseline-centric experiment workflow, preserve current
tenant/client Azure behavior, keep secret values out of committed files and
logs, and ensure Langfuse trace/observation metadata remains consistent for
downstream judge evaluators and human review.

The first concrete example will be a `rewrite_quality` candidate for an Azure
API-key deployment such as `mistral-large-3`, but the provider contract is
generic for compatible Azure endpoint/API-key model deployments.

The provider design uses one Azure/OpenAI-compatible provider family with
explicit per-model authentication mode. Each configured baseline or candidate
gets its own provider instance and credential references, so a single project
can run one Azure model with tenant/client credentials and another Azure model
with endpoint/API-key credentials. Auth mode is never inferred from whichever
environment variables happen to be present.

The design must preserve the Langfuse trace and observation structure learned
from the judge setup work: one deterministic trace per dataset item, a
parent workflow span for the run/item, a nested final model-output generation
observation, and metadata on the model-output observation that lets Langfuse
LLM-as-Judge evaluators target observations by project metadata and
`observation_role=model_output` instead of provider-specific observation names.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `pydantic`, `PyYAML`, `typer`, `rich`, `pytest`,
`httpx`, `langfuse>=3.0`, existing `openai`/Azure dependencies for the current
Azure tenant/client path. Use a Langfuse SDK/provider integration for the new
API-key path when it satisfies the trace nesting, token usage, metadata, and
redaction requirements; otherwise use the existing manual Langfuse generation
path and document why the SDK path did not fit.

**Python Environment Management**: Use `uv` for environment creation,
dependency setup, lockfile management, and command execution. Canonical setup is
`uv sync`; canonical run and test commands use `uv run ...`.

**Storage**: No new persistent storage. Project YAML stores non-secret
environment variable references and candidate settings. Langfuse remains the
system of record for traces, observations, scores, comparisons, and review
workflows. Local reports and artifacts must not contain API-key values.

**Testing**: `pytest` with unit, contract, integration, and optional live tests.
Default tests must not require Azure, Langfuse, or network credentials. Live
checks require explicit environment variables and should be skipped by default.

**Target Platform**: Local developer machine and CI runners. Optional live
checks require network access to Langfuse and the configured Azure endpoint.

**Project Type**: Headless Python CLI.

**Performance Goals**: Provider config validation should add negligible
overhead. Candidate request overhead should be dominated by model latency and
should preserve the existing retry behavior. Fake/non-live test execution
should remain fast enough for the default suite.

**Constraints**: Do not add a service, worker, queue, local inference gateway,
or custom observability stack. Do not store API-key values in project YAML,
trace metadata, local artifacts, reports, or exception text. Preserve existing
Azure tenant/client behavior. The baseline may remain in a different Azure
account and use a different authentication mode from the candidate. Do not
flatten or duplicate Langfuse traces: the API-key candidate must use the same
parent trace/span plus nested model-output generation structure as other live
runs. Do not auto-detect auth mode from environment variables; `auth_mode` and
credential refs must be explicit per configured model.

**Scale/Scope**: One or more Azure endpoint/API-key candidates per project;
first example added to `rewrite_quality`; same candidate workflow, evaluator
targeting metadata, baseline reference, and human review routing as other live
candidates. The feature covers candidate generation only; judge-model
connection setup remains out of scope unless added by a later feature.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Langfuse-first**: PASS. Provider calls continue to log Langfuse-native
  traces and observations through the existing harness tracing path. A Langfuse
  SDK/provider integration must be preferred if it can preserve the required
  trace hierarchy, generation metadata, token usage, and redaction behavior;
  otherwise the plan permits the existing manual Langfuse generation path. The
  design does not replace Langfuse scoring, dashboards, comparisons, judge
  evaluators, or human review.
- **Thin harness scope**: PASS. The design extends the existing local CLI,
  config model, and provider adapter path. No service, orchestration framework,
  plugin system, or local API is introduced.
- **Dataset simplicity**: PASS. Existing CSV datasets with an `input` column,
  including `rewrite_quality`, remain valid.
- **Reproducibility metadata**: PASS. Candidate runs preserve provider, model
  or deployment identifier, parameters, prompt version, evaluator versions,
  latency, token usage when available, timestamps, project identity, dataset
  identity, baseline reference, run identity, trace name, trace ID,
  observation role, evaluator set ID, and relevant non-secret configuration
  values.
- **Baseline-centric workflow**: PASS. The baseline is generated, selected, or
  reused before candidate comparisons. The API-key candidate participates in
  the existing candidate comparison workflow.
- **Minimal local state**: PASS. No database or long-lived local store is
  added. Local state remains project config, prompts, datasets, and normal run
  artifacts.
- **Human review awareness**: PASS. Outputs from API-key candidates remain
  routable to Langfuse Human Annotation Queues and comparable with automated
  evaluator results.
- **Local-first execution**: PASS. Workflows remain runnable through
  `uv run python run_experiment.py ...`.

## Project Structure

### Documentation (this feature)

```text
specs/009-azure-api-key-provider/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- project-config.md
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

src/
`-- evaluator_harness/
    |-- config.py
    |-- providers/
    |   |-- __init__.py
    |   `-- openai_compatible.py
    |-- runner.py
    `-- errors.py

tests/
|-- unit/
|   |-- test_config.py
|   |-- test_openai_compatible_provider.py
|   |-- test_provider_factory.py
|   `-- test_secret_redaction.py
|-- contract/
|   `-- test_config_driven_model_registration.py
|-- integration/
|   |-- test_new_model_config.py
|   |-- test_run_candidate.py
|   `-- live/
|       |-- test_live_azure_baseline_smoke.py
|       `-- test_live_azure_api_key_candidate_smoke.py
`-- fixtures/
    `-- projects/
```

**Structure Decision**: Extend the existing single-package CLI and the current
OpenAI-compatible/Azure provider path rather than adding a separate framework.
The implementation should choose the smallest provider/config boundary that
allows tenant/client Azure and endpoint/API-key Azure candidates to coexist
without changing the runner workflow. Use one provider family/adapter with
auth-mode-specific credential resolution instead of separate tenant/client and
API-key provider classes unless implementation evidence shows the request
shapes diverge beyond authentication.

## Phase 0 Research

See [research.md](./research.md). Key decisions:

- Model API-key Azure deployments as a first-class authentication variant for
  Azure-hosted candidate models, while preserving current tenant/client Azure
  behavior.
- Use explicit per-model `auth_mode`; never infer auth mode from available
  environment variables. One provider instance is created for each configured
  baseline or candidate, so independent Azure accounts and credential sets can
  coexist safely.
- Encourage project/model-specific environment variable names in examples to
  avoid collisions across baseline and candidate deployments.
- Store only environment variable names in project YAML. Actual API keys,
  endpoints when considered sensitive, and service settings are read from the
  runtime environment.
- Use the same candidate workflow and Langfuse observation metadata as other
  providers so LLM-as-Judge filters and Human Annotation Queue routing continue
  to work.
- Preserve the existing Langfuse trace hierarchy: deterministic trace ID and
  stable trace name per dataset item, parent workflow span for the run/item,
  nested model-output generation observation, and model-output metadata copied
  onto the observation itself.
- Keep provider and Langfuse entity naming consistent with current harness
  conventions: trace names remain item/run scoped, model/provider details live
  in metadata, Human Annotation Queues keep the `EH_<project>_<version>_review`
  pattern, and LLM-as-Judge evaluators keep the
  `EH_<project>_<version>_judge_<dimension>_<evaluator-version>_<source>_<target>`
  pattern from feature 008.
- Prefer Langfuse SDK/provider instrumentation only if it can attach the
  generation to the existing parent trace/span and emit the required
  observation metadata; otherwise keep the manual generation instrumentation
  used by the current Azure/OpenAI path.
- Add `rewrite_quality` coverage that validates the project, runs the existing
  baseline, and runs the new API-key candidate in opt-in live testing.
- Keep the provider generic for compatible Azure endpoint/API-key model
  deployments; `mistral-large-3` is documentation/test data, not a hard-coded
  provider branch.

## Phase 1 Design

See [data-model.md](./data-model.md),
[contracts/project-config.md](./contracts/project-config.md),
[contracts/provider-runtime.md](./contracts/provider-runtime.md), and
[quickstart.md](./quickstart.md).

## MVP Delivery Phases

1. **Config model**: add a non-secret API-key Azure credential reference shape
   or equivalent config option for endpoint/API-key Azure candidates; preserve
   validation for existing tenant/client Azure references. Make the credential
   groups mutually exclusive by explicit `auth_mode`.
2. **Provider runtime**: route API-key Azure candidates through the existing
   provider workflow, send requests with API-key authentication, preserve retry
   behavior, and redact all configured secret values from failures. Provider
   instances must be constructed per model config and must not share resolved
   credentials between baseline and candidate configs.
3. **Langfuse tracing path**: evaluate whether the Langfuse SDK/provider
   instrumentation fits the API-key Azure request path. Use it only if it
   preserves the existing parent trace/span, nested generation observation,
   token/cost capture, and metadata contract; otherwise use the current manual
   Langfuse generation path.
4. **Project example**: add a disabled-by-default or documented
   `rewrite_quality` API-key Azure candidate example using project/model-
   specific env refs and `mistral-large-3` only as the sample deployment name.
5. **Metadata alignment**: verify API-key candidate outputs include provider,
   model/deployment, run, baseline reference, trace ID/name, parent observation
   ID when available, observation role, evaluator set, project metadata, and
   non-secret parameters expected by Langfuse evaluators and review routing.
6. **Coverage**: add unit, contract, fake integration, and optional live tests
   for config validation, provider request headers/body, secret redaction,
   existing-provider regression, `rewrite_quality` validation, baseline run,
   API-key candidate run, trace hierarchy, and evaluator-filter compatibility.
7. **Docs**: update README/user guide/quickstart with API-key candidate setup,
   environment variables, and live test commands.

## Test Strategy

- **Unit tests**: config accepts endpoint/API-key candidate references and
  rejects missing or unsafe credential references; tenant/client Azure config
  remains unchanged; provider sends API-key auth without tenant/client token
  requirements; provider errors redact API keys and endpoint values configured
  as secret refs; provider factory/tracing metadata remains stable; SDK-vs-
  manual tracing selection is explicit and documented in provider metadata;
  multiple provider instances with different auth modes do not share
  credentials; auth mode is not auto-detected from environment availability.
- **Contract tests**: project config examples validate; adding a new Azure
  endpoint/API-key candidate requires no new CLI mode or dataset shape; invalid
  API-key configs produce actionable errors.
- **Fake integration tests**: `rewrite_quality` fixture can include the new
  candidate and still build baseline references, candidate outputs, Langfuse
  parent trace/span records, nested model-output generation records, evaluator-
  targeting metadata, and review routing metadata. Tests must assert evaluator
  filters can match on project metadata plus `observation_role=model_output`
  without requiring `Name = OpenAI-generation`.
- **Live tests**: opt-in tests must cover:
  - `uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml`
  - `uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode baseline`
  - `uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode candidate --candidate <azure-api-key-candidate>`
  - verification that the baseline trace and API-key candidate trace appear in
    Langfuse with matching project/version/evaluator metadata.
  - verification that the candidate generation is nested under the item trace
    rather than creating an unrelated top-level trace.
  - verification that no empty environment filter or provider-specific
    observation-name filter prevents the evaluator from picking up candidate
    observations.
- **Default suite**: `uv run pytest -p no:cacheprovider` must pass without live
  Azure or Langfuse credentials.

## Post-Design Constitution Check

- **Langfuse-first**: PASS. The design continues to log runs to Langfuse and
  depends on Langfuse for comparison, evaluator execution, scores, dashboards,
  and human review. SDK/provider instrumentation is preferred when it fits the
  established trace hierarchy; otherwise manual generation instrumentation is
  an allowed fallback.
- **Thin harness scope**: PASS. The design adds a small provider/config
  extension only, with one Azure-compatible provider family and explicit
  auth-mode branching rather than separate workflow commands.
- **Dataset simplicity**: PASS. No dataset shape changes.
- **Reproducibility metadata**: PASS. API-key candidate runs carry the same
  reproducibility metadata, trace hierarchy, and observation-level evaluator
  metadata as other candidate runs.
- **Baseline-centric workflow**: PASS. The plan explicitly verifies
  `rewrite_quality` baseline execution before the API-key candidate run.
- **Minimal local state**: PASS. No new persistent state is introduced.
- **Human review awareness**: PASS. Review routing metadata remains part of the
  candidate output contract.
- **Local-first execution**: PASS. All commands use `uv run ...`.

## Complexity Tracking

No constitution violations.
