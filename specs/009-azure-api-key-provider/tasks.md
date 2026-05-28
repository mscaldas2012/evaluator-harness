# Tasks: Azure API-Key Candidate Provider

**Input**: Design documents from `/specs/009-azure-api-key-provider/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover success paths, validation failures, provider failures, Langfuse trace metadata, trace nesting, secret redaction, and CLI-visible behavior.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the working context and test fixtures needed for all stories.

- [X] T001 Inspect existing Azure tenant/client provider tests and runner trace tests in `tests/unit/test_openai_compatible_provider.py`
- [X] T002 Inspect existing model config fixtures and rewrite-quality project config in `configs/projects/rewrite_quality.yaml`
- [X] T003 [P] Add Azure endpoint/API-key valid project fixture with explicit per-model `auth_mode` in `tests/fixtures/projects/valid_azure_api_key_candidate.yaml`
- [X] T004 [P] Add Azure endpoint/API-key invalid project fixture with missing credential refs in `tests/fixtures/projects/invalid_azure_api_key_candidate_missing_refs.yaml`
- [X] T005 [P] Add Azure endpoint/API-key invalid project fixture with unsafe literal secret values in `tests/fixtures/projects/invalid_azure_api_key_candidate_literal_secret.yaml`
- [X] T006 [P] Add mixed-auth Azure project fixture with tenant/client baseline and API-key candidate in `tests/fixtures/projects/valid_mixed_azure_auth_project.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared config and provider seams required before user stories can be implemented.

**CRITICAL**: No user story work should begin until this phase is complete.

### Tests for Foundation

- [X] T007 [P] Add config tests for Azure endpoint/API-key credential reference validation in `tests/unit/test_config.py`
- [X] T008 [P] Add provider auth-mode selection tests for API-key versus tenant/client Azure paths in `tests/unit/test_openai_compatible_provider.py`
- [X] T009 [P] Add provider tracing metadata tests for SDK-compatible versus manual-generation tracing strategy in `tests/unit/test_provider_factory.py`
- [X] T010 [P] Add config test proving auth mode is explicit and not inferred from environment availability in `tests/unit/test_config.py`
- [X] T011 [P] Add provider test proving separate baseline/candidate provider instances do not share resolved credentials in `tests/unit/test_openai_compatible_provider.py`

### Implementation for Foundation

- [X] T012 Add Azure endpoint/API-key credential reference model in `src/evaluator_harness/config.py`
- [X] T013 Update model config validation for API-key Azure candidates while preserving tenant/client Azure requirements in `src/evaluator_harness/config.py`
- [X] T014 Enforce mutually exclusive credential reference groups based on explicit `auth_mode` in `src/evaluator_harness/config.py`
- [X] T015 Update provider tracing metadata to expose explicit SDK/manual tracing strategy for API-key candidates in `src/evaluator_harness/providers/__init__.py`
- [X] T016 Update OpenAI-compatible provider auth-mode branching for tenant/client and API-key Azure paths in `src/evaluator_harness/providers/openai_compatible.py`

**Checkpoint**: Foundation ready. Config can distinguish tenant/client Azure, endpoint/API-key Azure, Ollama, and dry-run models without changing runner workflow.

---

## Phase 3: User Story 1 - Run Azure Endpoint API-Key Candidate (Priority: P1) MVP

**Goal**: A user can configure an Azure endpoint/API-key model deployment as a normal candidate and run it through the existing baseline-centric workflow.

**Independent Test**: Add an API-key-authenticated Azure candidate to project config, run the candidate workflow, and confirm candidate outputs, Langfuse traces, model-output observations, baseline reference metadata, and evaluator-targeting metadata are produced.

### Tests for User Story 1

- [X] T017 [P] [US1] Add provider REST request test for API-key headers, endpoint URL, deployment/model identifier, API version, and generation body in `tests/unit/test_openai_compatible_provider.py`
- [X] T018 [P] [US1] Add provider response parsing test for output text, prompt tokens, completion tokens, completion ID, and retry count in `tests/unit/test_openai_compatible_provider.py`
- [X] T019 [P] [US1] Add contract test proving Azure endpoint/API-key candidate config needs no new CLI mode or dataset shape in `tests/contract/test_config_driven_model_registration.py`
- [X] T020 [P] [US1] Add fake integration test for rewrite-quality API-key candidate output and baseline reference metadata in `tests/integration/test_run_candidate.py`
- [X] T021 [P] [US1] Add fake integration test for API-key candidate parent trace/span and nested model-output generation observation in `tests/integration/test_evaluator_observation_metadata.py`
- [X] T022 [P] [US1] Add optional live smoke test for rewrite-quality Azure API-key candidate run in `tests/integration/live/test_live_azure_api_key_candidate_smoke.py`

### Implementation for User Story 1

- [X] T023 [US1] Implement Azure endpoint/API-key auth config resolution from the current model config only in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T024 [US1] Implement Azure endpoint/API-key chat completion request path in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T025 [US1] Preserve max-token fallback behavior for API-key Azure responses in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T026 [US1] Ensure API-key candidate model responses expose non-secret raw metadata for Langfuse generation logging in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T027 [US1] Ensure runner request metadata for API-key candidates includes trace ID, trace name, parent observation ID, observation role, evaluator set ID, project identity, and baseline reference in `src/evaluator_harness/runner.py`
- [X] T028 [US1] Add Azure endpoint/API-key candidate example with project/model-specific env refs for rewrite-quality in `configs/projects/rewrite_quality.yaml`

**Checkpoint**: User Story 1 is functional. The Azure endpoint/API-key candidate can run through the existing candidate path and produce evaluator-ready Langfuse metadata.

---

## Phase 4: User Story 2 - Configure Secrets Safely (Priority: P2)

**Goal**: API-key candidate configuration uses environment variable references only and never exposes secret values in config, traces, artifacts, command output, or errors.

**Independent Test**: Validate safe and unsafe project configs, run provider failure paths with secret values in environment variables, and confirm output/errors do not contain secret values.

### Tests for User Story 2

- [X] T029 [P] [US2] Add config test rejecting literal API key and unsafe endpoint values in `tests/unit/test_config.py`
- [X] T030 [P] [US2] Add provider missing environment variable test with actionable variable-name error in `tests/unit/test_openai_compatible_provider.py`
- [X] T031 [P] [US2] Add provider service failure redaction test for API key, subscription key, and endpoint values in `tests/unit/test_secret_redaction.py`
- [X] T032 [P] [US2] Add CLI validation contract test for invalid Azure API-key candidate configs in `tests/contract/test_cli_validate.py`

### Implementation for User Story 2

- [X] T033 [US2] Extend config secret-reference validation for Azure API-key fields in `src/evaluator_harness/config.py`
- [X] T034 [US2] Extend provider redaction to include API-key credential refs, subscription-key refs, and endpoint refs in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T035 [US2] Improve provider error context for API-key Azure authentication, authorization, throttling, timeout, malformed response, and unsupported parameter failures in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T036 [US2] Ensure CLI validation and runtime errors report candidate name and environment variable names without secret values in `src/evaluator_harness/cli.py`

**Checkpoint**: User Story 2 is functional. Secret values remain outside committed config and all tested output paths.

---

## Phase 5: User Story 3 - Keep Existing Providers Stable (Priority: P3)

**Goal**: Existing Azure tenant/client, Ollama, and dry-run providers continue working without configuration or behavior changes.

**Independent Test**: Existing provider tests and rewrite-quality validation pass unchanged, and tenant/client Azure request behavior remains intact.

### Tests for User Story 3

- [X] T037 [P] [US3] Add regression test for tenant/client Azure auth config and REST headers in `tests/unit/test_openai_compatible_provider.py`
- [X] T038 [P] [US3] Add regression test for Ollama and dry-run provider factory behavior in `tests/unit/test_provider_factory.py`
- [X] T039 [P] [US3] Add rewrite-quality validation regression test with baseline plus existing candidates in `tests/integration/test_validate_project.py`
- [X] T040 [P] [US3] Add optional live smoke assertion that existing Azure baseline still runs before API-key candidate verification in `tests/integration/live/test_live_azure_baseline_smoke.py`

### Implementation for User Story 3

- [X] T041 [US3] Preserve tenant/client Azure SDK and REST request paths while adding API-key branching in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T042 [US3] Preserve Ollama and dry-run provider registration behavior in `src/evaluator_harness/providers/__init__.py`
- [X] T043 [US3] Preserve review routing and candidate output record behavior for all providers in `src/evaluator_harness/runner.py`

**Checkpoint**: All user stories are independently functional and existing providers remain stable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, live verification, and final consistency checks across the feature.

- [X] T044 [P] Update Azure endpoint/API-key candidate setup documentation with one-provider-family explicit-auth design in `README.md`
- [X] T045 [P] Update Azure endpoint/API-key candidate setup and troubleshooting documentation with env naming conventions in `docs/user-guide.md`
- [X] T046 [P] Update 009 quickstart with final candidate name, project/model-specific env var names, and verification results in `specs/009-azure-api-key-provider/quickstart.md`
- [X] T047 Verify evaluator filters for rewrite-quality do not rely on `Name = OpenAI-generation` or empty environment filters in `configs/projects/rewrite_quality.yaml`
- [X] T048 Run default non-live test suite and record command/result in `specs/009-azure-api-key-provider/quickstart.md`
- [X] T049 Run rewrite-quality validation command and record command/result in `specs/009-azure-api-key-provider/quickstart.md`
- [X] T050 Run live rewrite-quality baseline command when credentials are available and record command/result in `specs/009-azure-api-key-provider/quickstart.md`
- [X] T051 Run live rewrite-quality Azure API-key candidate command when credentials are available and record command/result in `specs/009-azure-api-key-provider/quickstart.md`
- [X] T052 Inspect Langfuse traces for baseline and API-key candidate nesting, model-output observation metadata, and secret absence; record findings in `specs/009-azure-api-key-provider/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational; delivers the MVP provider run path.
- **User Story 2 (Phase 4)**: Depends on Foundational; can be developed after or alongside US1 but must be complete before live use with real secrets.
- **User Story 3 (Phase 5)**: Depends on Foundational; validates no regressions in existing providers.
- **Polish (Phase 6)**: Depends on desired user stories being complete.

### User Story Dependencies

- **US1 Run Azure Endpoint API-Key Candidate**: MVP; no dependency on US2/US3 after foundation.
- **US2 Configure Secrets Safely**: Uses the credential model and provider path from foundation; should be complete before real live candidate runs.
- **US3 Keep Existing Providers Stable**: Can run in parallel with US1/US2 after foundation because it is mostly regression coverage.

### Within Each User Story

- Tests must be written and observed failing before implementation.
- Config model changes before provider runtime changes.
- Provider runtime changes before runner metadata changes.
- Fake integration verification before optional live verification.

## Parallel Opportunities

- Setup fixtures T003-T006 can be created in parallel.
- Foundation tests T007-T011 can be written in parallel.
- US1 tests T017-T022 can be written in parallel before implementation.
- US2 tests T029-T032 can be written in parallel before implementation.
- US3 tests T037-T040 can be written in parallel before implementation.
- Documentation tasks T044-T046 can run in parallel after implementation behavior stabilizes.

## Parallel Example: User Story 1

```text
Task: "Add provider REST request test for API-key headers, endpoint URL, deployment/model identifier, API version, and generation body in tests/unit/test_openai_compatible_provider.py"
Task: "Add contract test proving Azure endpoint/API-key candidate config needs no new CLI mode or dataset shape in tests/contract/test_config_driven_model_registration.py"
Task: "Add fake integration test for API-key candidate parent trace/span and nested model-output generation observation in tests/integration/test_evaluator_observation_metadata.py"
Task: "Add optional live smoke test for rewrite-quality Azure API-key candidate run in tests/integration/live/test_live_azure_api_key_candidate_smoke.py"
```

## Parallel Example: User Story 2

```text
Task: "Add config test rejecting literal API key and unsafe endpoint values in tests/unit/test_config.py"
Task: "Add provider missing environment variable test with actionable variable-name error in tests/unit/test_openai_compatible_provider.py"
Task: "Add provider service failure redaction test for API key, subscription key, and endpoint values in tests/unit/test_secret_redaction.py"
```

## Parallel Example: User Story 3

```text
Task: "Add regression test for tenant/client Azure auth config and REST headers in tests/unit/test_openai_compatible_provider.py"
Task: "Add regression test for Ollama and dry-run provider factory behavior in tests/unit/test_provider_factory.py"
Task: "Add rewrite-quality validation regression test with baseline plus existing candidates in tests/integration/test_validate_project.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup fixtures.
2. Complete Phase 2 foundational config/provider branching.
3. Write and fail US1 tests.
4. Implement API-key provider runtime and runner metadata preservation.
5. Validate US1 independently with fake integration tests.

### Incremental Delivery

1. Deliver US1 so the candidate can run through the harness.
2. Deliver US2 before using real API keys in live runs.
3. Deliver US3 to prove existing providers remain stable.
4. Complete live rewrite-quality baseline and API-key candidate verification.

### Required Final Verification

```powershell
uv run pytest -p no:cacheprovider
uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode baseline
uv run python run_experiment.py run --project configs/projects/rewrite_quality.yaml --mode candidate --candidate <azure-api-key-candidate>
```

Live baseline and candidate commands require configured Azure and Langfuse credentials and may be recorded as skipped when credentials are unavailable.

## Notes

- `[P]` tasks touch different files or can be completed without depending on incomplete tasks.
- `[US1]`, `[US2]`, and `[US3]` labels map to the user stories in [spec.md](./spec.md).
- Keep one Azure-compatible provider family with explicit per-model `auth_mode`; `mistral-large-3` is only the first sample deployment.
- Do not auto-detect auth mode from environment variables.
- Use project/model-specific environment variable names in examples.
- Preserve Langfuse trace hierarchy and observation metadata learned from feature 008.
- Do not commit or print API-key values.
