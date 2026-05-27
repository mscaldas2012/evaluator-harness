# Tasks: Lightweight Langfuse Evaluation Harness

**Input**: Design documents from `/specs/001-rewrite-eval-harness/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: REQUIRED. Write tests before implementation tasks and cover success paths, validation failures, provider failures, Langfuse failures, metadata correctness, and CLI exit behavior using fakes or mocks.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently after the shared foundation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the lightweight Python CLI project shape from the implementation plan.

- [X] T001 Create `pyproject.toml` with package metadata, Python 3.11+ support, runtime dependencies, dev test dependencies, and `uv`-compatible dependency metadata
- [X] T002 Create package structure in `src/evaluator_harness/` with `__init__.py`, `cli.py`, `config.py`, `dataset_loader.py`, `langfuse_client.py`, `runner.py`, `baseline_registry.py`, `review_selection.py`, `exports.py`, and `providers/`
- [X] T003 Create root CLI shim in `run_experiment.py` that delegates to `src/evaluator_harness/cli.py`
- [X] T004 [P] Create test directory structure in `tests/unit/`, `tests/contract/`, `tests/integration/`, and `tests/fixtures/`
- [X] T005 [P] Add sample rewrite project config in `configs/projects/rewrite_quality.yaml`
- [X] T006 [P] Add sample rewrite dataset in `datasets/rewrite_quality.csv`
- [X] T007 [P] Add sample task prompt and evaluator prompt in `prompts/rewrite_quality/task_prompt.md` and `prompts/rewrite_quality/evaluators/clarity.md`
- [X] T008 Configure pytest defaults, import path, markers for optional live smoke tests, and coverage settings in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared models, fakes, error handling, and contracts needed by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T009 [P] Add fake Langfuse client test fixture with dataset, run, trace, score, and annotation queue calls in `tests/fixtures/fake_langfuse.py`
- [X] T010 [P] Add fake model provider fixture with success, timeout, rate-limit, invalid-output, and usage-metadata scenarios in `tests/fixtures/fake_provider.py`
- [X] T011 [P] Add CLI runner and temporary project file fixtures in `tests/fixtures/cli_fixtures.py`
- [X] T012 [P] Add representative valid and invalid project YAML fixtures in `tests/fixtures/projects/`
- [X] T013 Define shared domain dataclasses or Pydantic models for project, dataset, prompt, evaluator, model config, run, baseline reference, output record, and review selection in `src/evaluator_harness/config.py`
- [X] T014 Define harness exception types and user-facing failure context in `src/evaluator_harness/errors.py`
- [X] T015 Define provider interface, model request, and model response objects in `src/evaluator_harness/providers/base.py`
- [X] T016 Define provider factory skeleton for `openai_compatible` and `ollama` in `src/evaluator_harness/providers/__init__.py`
- [X] T017 Define Langfuse client wrapper skeleton for reachability checks, dataset sync, score config sync, run creation, trace logging, baseline lookup, score fetch, and annotation queue routing in `src/evaluator_harness/langfuse_client.py`
- [X] T018 Define runner orchestration skeleton for validation, dataset sync, baseline execution, candidate execution, review selection, and export dispatch in `src/evaluator_harness/runner.py`
- [X] T019 Define Typer CLI commands and exit code handling for `validate`, `sync-dataset`, `sync-score-configs`, `run`, `select-review`, and `export` in `src/evaluator_harness/cli.py`

**Checkpoint**: Foundation ready. User story work can now proceed in priority order or in parallel by story.

---

## Phase 3: User Story 1 - Define an Evaluation Project (Priority: P1) MVP

**Goal**: An engineer can define a generic evaluation project with dataset, baseline, candidates, task prompt, evaluator definitions, and review policy without code changes for future project types.

**Independent Test**: Run `uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml` against fakes and confirm project settings, dataset shape, prompt versions, evaluator versions, baseline config, and candidate configs are accepted.

### Tests for User Story 1

- [X] T020 [P] [US1] Add unit tests for valid and invalid project config loading in `tests/unit/test_config.py`
- [X] T021 [P] [US1] Add unit tests for CSV and JSON dataset loading, optional `ground_truth`, generated stable item IDs, blank input rejection, and duplicate explicit ID rejection in `tests/unit/test_dataset_loader.py`
- [X] T022 [P] [US1] Add unit tests for task prompt and evaluator prompt version validation, evaluator `modes`, score config contract validation, harness-managed score config prefix validation, and baseline/candidate evaluator variable validation in `tests/unit/test_prompt_refs.py`
- [X] T023 [P] [US1] Add contract tests for `validate` CLI success and failure output in `tests/contract/test_cli_validate.py`
- [X] T024 [P] [US1] Add integration test for validating the sample rewrite project without model calls in `tests/integration/test_validate_project.py`

### Implementation for User Story 1

- [X] T025 [US1] Implement YAML project config parsing and validation in `src/evaluator_harness/config.py`
- [X] T026 [US1] Implement local CSV and minimal JSON dataset loading with optional `ground_truth` and explicit-or-hash item identity in `src/evaluator_harness/dataset_loader.py`
- [X] T027 [US1] Implement prompt and evaluator prompt file loading with required version checks, evaluator modes, score config contract validation, harness-managed score config prefix validation, user-owned score config ID validation, and variable validation in `src/evaluator_harness/config.py`
- [X] T028 [US1] Implement project validation service that checks dataset, baseline, candidates, evaluators, provider declarations, and review policy in `src/evaluator_harness/runner.py`
- [X] T029 [US1] Implement `validate` CLI output and non-zero validation failure exits in `src/evaluator_harness/cli.py`
- [X] T030 [US1] Update sample rewrite project artifacts to pass validation in `configs/projects/rewrite_quality.yaml`, `datasets/rewrite_quality.csv`, and `prompts/rewrite_quality/`

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - Run or Reuse a Baseline (Priority: P2)

**Goal**: An engineer can sync a dataset to Langfuse, run the baseline once, and reuse a compatible baseline on later candidate runs.

**Independent Test**: Run a baseline with fake Langfuse and fake Azure OpenAI, then resolve `latest-compatible` for the same project without rerunning the baseline.

### Tests for User Story 2

- [X] T031 [P] [US2] Add contract tests for `sync-dataset` CLI output and failure exits in `tests/contract/test_cli_sync_dataset.py`
- [X] T032 [P] [US2] Add unit tests for Langfuse dataset create, update, resolve, and unreachable fail-fast behavior in `tests/unit/test_langfuse_dataset_sync.py`
- [X] T033 [P] [US2] Add unit tests for baseline compatibility fingerprint fields and mismatch rejection in `tests/unit/test_baseline_registry.py`
- [X] T034 [P] [US2] Add unit tests for Langfuse score config create, compatible reuse, user-owned reference validation, incompatible schema failure, archived same-name conflict handling, and no update/delete behavior in `tests/unit/test_langfuse_score_config_sync.py`
- [X] T035 [P] [US2] Add unit tests for Azure OpenAI client construction with tenant ID, client ID, client secret, token scope, APIM subscription key, API version, and endpoint env vars in `tests/unit/test_openai_compatible_provider.py`
- [X] T036 [P] [US2] Add unit tests verifying Azure secrets are never included in trace metadata, local output, or exceptions in `tests/unit/test_secret_redaction.py`
- [X] T037 [P] [US2] Add integration test for baseline run trace metadata, project tags, run tags, environment, dataset run identity, retry recording, token metadata, latency metadata, baseline evaluator-ready payloads with optional `ground_truth`, configured Langfuse-owned baseline evaluator trigger/enqueue behavior, baseline reference persistence, and failed-call trace context with dataset item, provider, model, retry count, and failure reason in `tests/integration/test_run_baseline.py`
- [X] T038 [P] [US2] Add contract tests for `sync-score-configs` and `run --mode baseline` success, incompatible score config, provider failure, and Langfuse failure exit codes in `tests/contract/test_cli_run_baseline.py`

### Implementation for User Story 2

- [X] T039 [US2] Implement Langfuse reachability check and fail-fast context reporting in `src/evaluator_harness/langfuse_client.py`
- [X] T040 [US2] Implement Langfuse Dataset create, update, and resolve behavior for local and Langfuse-hosted datasets in `src/evaluator_harness/langfuse_client.py`
- [X] T041 [US2] Implement harness-managed Langfuse score config create-or-reuse sync with prefix enforcement, user-owned reference validation, compatibility checks, archived same-name conflict handling, incompatible schema failure, and no update/delete behavior in `src/evaluator_harness/langfuse_client.py`
- [X] T042 [US2] Implement baseline compatibility fingerprint generation and lookup helpers in `src/evaluator_harness/baseline_registry.py`
- [X] T043 [US2] Implement Azure OpenAI client-credentials auth using `azure-identity` and Langfuse-wrapped `AzureOpenAI` in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T044 [US2] Implement provider retry handling with recorded retry outcomes in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T045 [US2] Implement baseline execution flow, per-item success and failure trace logging, output records, project/run tag and environment propagation, baseline evaluator-ready record creation with `input`, baseline `output`, optional `ground_truth`, evaluator versions, and trace context, configured Langfuse-owned baseline evaluator trigger/enqueue behavior, failed-call context persistence, and reusable baseline reference creation in `src/evaluator_harness/runner.py`
- [X] T046 [US2] Implement `sync-dataset`, `sync-score-configs`, and `run --mode baseline` CLI commands in `src/evaluator_harness/cli.py`

**Checkpoint**: User Story 2 is independently functional and baseline reuse data is available for candidate runs.

---

## Phase 5: User Story 3 - Compare Candidate Models or Parameters (Priority: P3)

**Goal**: An engineer can run one or more candidate models or parameter variants against a compatible baseline and inspect all comparison metadata in Langfuse.

**Independent Test**: Run `llama3-local` today and another candidate config tomorrow against the same fake compatible baseline and confirm both candidate runs record the same baseline reference.

### Tests for User Story 3

- [X] T047 [P] [US3] Add unit tests for `latest-compatible`, explicit baseline run ID, and incompatible baseline resolution in `tests/unit/test_baseline_resolution.py`
- [X] T048 [P] [US3] Add unit tests for Ollama request, response, timeout, usage-unavailable metadata, and manual tracing fallback in `tests/unit/test_ollama_provider.py`
- [X] T049 [P] [US3] Add integration test for candidate run metadata linking project, project tags, run tags, environment, dataset version, prompt version, evaluator set, model parameters, optional `ground_truth`, and baseline reference in `tests/integration/test_run_candidate.py`
- [X] T050 [P] [US3] Add integration test for two candidate parameter variants and repeated same-config candidate runs associated with the same compatible baseline, preserving distinct run IDs and Langfuse run references in `tests/integration/test_parameter_variants.py`
- [X] T051 [P] [US3] Add contract tests for `run --mode candidate --candidate <name> --baseline latest-compatible` success and failure exits in `tests/contract/test_cli_run_candidate.py`

### Implementation for User Story 3

- [X] T052 [US3] Implement baseline resolver for `latest-compatible` and explicit baseline run IDs in `src/evaluator_harness/baseline_registry.py`
- [X] T053 [US3] Implement Ollama provider adapter with HTTP client, timeout handling, retry outcomes, and explicit unavailable token or cost metadata in `src/evaluator_harness/providers/ollama.py`
- [X] T054 [US3] Implement candidate execution flow with strict compatible baseline requirement, repeated same-config run support, and distinct run identity creation in `src/evaluator_harness/runner.py`
- [X] T055 [US3] Implement candidate trace metadata including parameter hash, baseline reference, evaluator set identity, prompt version, dataset version, optional `ground_truth`, project tags, run tags, environment, latency, token usage, cost, timestamps, and failure context when provider calls fail in `src/evaluator_harness/langfuse_client.py`
- [X] T056 [US3] Implement `run --mode candidate`, `--candidate`, and `--baseline` CLI behavior in `src/evaluator_harness/cli.py`
- [X] T057 [US3] Add a second sample candidate parameter variant to `configs/projects/rewrite_quality.yaml`

**Checkpoint**: User Story 3 is independently functional and candidate comparison context is Langfuse-ready.

---

## Phase 6: User Story 4 - Review Outcomes in Langfuse (Priority: P4)

**Goal**: A prompt engineer can select review items, prioritize risky outputs, and route selected items to a configured Langfuse Human Annotation Queue.

**Independent Test**: Given fake scored outputs with failures, low confidence, disputed outcomes, and normal samples, run `select-review` and confirm at least 5% are selected with queue payloads containing source input, baseline output, candidate output, evaluator output, and trace context.

### Tests for User Story 4

- [X] T058 [P] [US4] Add unit tests for human review selection minimum sample size, priority ordering, deterministic random fill, and disabled policy behavior in `tests/unit/test_review_selection.py`
- [X] T059 [P] [US4] Add unit tests for annotation queue payload shape, baseline-mode and candidate-mode evaluator payloads, optional `ground_truth`, blind evaluator payload sanitization, and duplicate queue item avoidance in `tests/unit/test_annotation_queue_payloads.py`
- [X] T060 [P] [US4] Add integration test for `select-review` with configured queue routing through fake Langfuse in `tests/integration/test_select_review.py`
- [X] T061 [P] [US4] Add contract tests for `select-review --run <candidate-run-id>` success, missing queue, and Langfuse failure exits in `tests/contract/test_cli_select_review.py`

### Implementation for User Story 4

- [X] T062 [US4] Implement review result loading and baseline/candidate evaluator payload construction with optional `ground_truth`, preserving blind evaluator sanitization that excludes provider, model, and vendor identity when `blind: true` in `src/evaluator_harness/langfuse_client.py`
- [X] T063 [US4] Implement review selection algorithm with failures, low-confidence, disputed, and sampled reasons in `src/evaluator_harness/review_selection.py`
- [X] T064 [US4] Implement Human Annotation Queue routing with configured queue IDs and no queue creation in `src/evaluator_harness/langfuse_client.py`
- [X] T065 [US4] Implement `select-review` CLI command output for selected count, reasons, queue ID, queued count, and skipped duplicate count in `src/evaluator_harness/cli.py`

**Checkpoint**: User Story 4 is independently functional and keeps human review Langfuse-native.

---

## Phase 7: User Story 5 - Add a New Model With Minimal Changes (Priority: P5)

**Goal**: An agent developer can add a model through configuration or a small adapter without changing project workflow code.

**Independent Test**: Add a new OpenAI-compatible or Ollama candidate config, run it on a two-row dataset with fakes, and confirm outputs and metadata appear beside the baseline without workflow changes.

### Tests for User Story 5

- [X] T066 [P] [US5] Add unit tests for provider factory selection, unsupported provider errors, and internal tracing strategy selection in `tests/unit/test_provider_factory.py`
- [X] T067 [P] [US5] Add contract tests proving a new OpenAI-compatible candidate config can be added without changing CLI arguments or dataset format in `tests/contract/test_config_driven_model_registration.py`
- [X] T068 [P] [US5] Add integration test for a newly configured candidate model using existing runner workflow and fake provider in `tests/integration/test_new_model_config.py`

### Implementation for User Story 5

- [X] T069 [US5] Complete provider factory wiring for configuration-driven model selection in `src/evaluator_harness/providers/__init__.py`
- [X] T070 [US5] Implement internal provider tracing strategy metadata that prefers Langfuse integrations and documents manual fallback reasons in provider adapter code in `src/evaluator_harness/providers/__init__.py`
- [X] T071 [US5] Add developer notes for adding OpenAI-compatible and local provider configs in `docs/user-guide.md`

**Checkpoint**: User Story 5 is independently functional and model additions remain config-first.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, documentation, and small supporting utilities that affect multiple stories.

- [X] T072 [P] Add optional lightweight CSV export tests for summary fields without score aggregation in `tests/unit/test_exports.py`
- [X] T073 Implement optional CSV summary export for archival only in `src/evaluator_harness/exports.py`
- [X] T074 Wire `export --format csv` CLI behavior without custom score aggregation in `src/evaluator_harness/cli.py`
- [X] T075 [P] Update `README.md` with headless setup, credentials, quickstart commands, and testing workflow
- [X] T076 [P] Update `docs/user-guide.md` with `--baseline latest-compatible`, explicit baseline run IDs, configured annotation queue behavior, and harness-managed score config sync behavior
- [X] T077 [P] Add automation backlog traceability notes for `BL-001` through `BL-007` in `docs/langfuse-automation-backlog.md`
- [X] T078 Review source modules for unnecessary abstractions, local state, service APIs, dashboards, or local scoring logic and simplify in `src/evaluator_harness/`
- [X] T079 Run `uv run pytest` and fix failures across `tests/`
- [X] T080 Run `uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml` with fakes or documented dry-run behavior and fix failures
- [X] T081 Verify generated trace metadata fields, repeated-run identity behavior, tag/environment propagation, score config sync behavior, and failed-call context against `specs/001-rewrite-eval-harness/contracts/cli.md` and update tests or implementation as needed
- [X] T082 Verify no live Langfuse, OpenAI, Azure, or Ollama credentials are required for default automated tests in `tests/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2. Delivers the MVP project definition and validation slice.
- **Phase 4 US2**: Depends on Phase 2 and uses validated project artifacts from US1.
- **Phase 5 US3**: Depends on Phase 4 for reusable baseline references.
- **Phase 6 US4**: Depends on Phase 5 for candidate run outputs and evaluator-ready metadata.
- **Phase 7 US5**: Depends on Phase 2 and can be developed after US3 validates the runner workflow.
- **Phase 8 Polish**: Depends on all desired stories.

### User Story Dependencies

- **US1 (P1)**: Required first MVP slice.
- **US2 (P2)**: Requires the project validation and dataset loading behavior from US1.
- **US3 (P3)**: Requires baseline run or reuse behavior from US2.
- **US4 (P4)**: Requires candidate outputs and Langfuse context from US3.
- **US5 (P5)**: Can proceed after foundation but is most useful after US3 confirms candidate execution.

### Within Each User Story

- Tests must be written and observed failing before implementation tasks.
- Config and data models come before services.
- Provider adapters come before runner integration.
- Runner behavior comes before CLI wiring.
- CLI contract tests should pass before each story checkpoint is considered complete.

---

## Parallel Opportunities

- Setup tasks T004 through T007 can run in parallel.
- Foundational fixture tasks T009 through T012 can run in parallel.
- All test tasks within each user story can run in parallel because they target separate test files.
- US4 review selection work can start after fake score/output fixtures exist, while US3 runner details are still being finished.
- US5 provider factory tests can start after Phase 2 because they do not require live provider implementations.

## Parallel Example: User Story 3

```text
Task: "T047 Add unit tests for latest-compatible, explicit baseline run ID, and incompatible baseline resolution in tests/unit/test_baseline_resolution.py"
Task: "T048 Add unit tests for Ollama request, response, timeout, usage-unavailable metadata, and manual tracing fallback in tests/unit/test_ollama_provider.py"
Task: "T049 Add integration test for candidate run metadata linking project, dataset version, prompt version, evaluator set, model parameters, and baseline reference in tests/integration/test_run_candidate.py"
Task: "T051 Add contract tests for run --mode candidate --candidate <name> --baseline latest-compatible success and failure exits in tests/contract/test_cli_run_candidate.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 so a generic project can be validated.
3. Complete US2 so a baseline can be run and reused.
4. Complete US3 for one candidate model against `latest-compatible`.
5. Stop and validate with tests plus the quickstart flow before adding review routing or additional provider extensibility.

### Incremental Delivery

1. US1 delivers project definition and dataset/prompt/evaluator validation.
2. US2 adds Langfuse Dataset sync, Azure baseline execution, and reusable baseline references.
3. US3 adds candidate execution and comparison-ready Langfuse metadata.
4. US4 adds Langfuse-native human review routing.
5. US5 confirms model additions stay config-first and adapter-light.

### Quality Gates

- No default test may require live Langfuse, Azure OpenAI, OpenAI, or Ollama credentials.
- Every Langfuse integration boundary must be covered by fakes, mocks, or contract tests.
- Manual tracing must appear only where a Langfuse-supported integration is unavailable or incompatible.
- The harness must not introduce a local dashboard, local score aggregation engine, database, service API, or orchestration framework.

## Extension Hooks

**Optional Pre-Hook**: git  
Command: `/speckit-git-commit`  
Description: Auto-commit before task generation  
Prompt: Commit outstanding changes before task generation?

**Optional Hook**: git  
Command: `/speckit-git-commit`  
Description: Auto-commit after task generation  
Prompt: Commit task changes?
