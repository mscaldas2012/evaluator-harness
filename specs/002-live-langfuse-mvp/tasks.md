# Tasks: Live Langfuse MVP

**Input**: Design documents from `/specs/002-live-langfuse-mvp/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Tests are REQUIRED for this project. Write tests before
implementation tasks and cover success paths, validation failures, provider
failures, Langfuse failures, metadata correctness, CLI exit behavior, and
opt-in live smoke behavior where applicable.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in the same phase because it
  touches different files or only adds independent tests/docs.
- **[Story]**: Maps to user stories from [spec.md](./spec.md).
- Every task includes an exact file path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align environment, fixtures, and test conventions for live MVP
work.

- [X] T001 Update Langfuse environment examples to prefer `LANGFUSE_HOST` while preserving `LANGFUSE_BASE_URL` alias in `.env.example`
- [X] T002 [P] Add live smoke credential notes and skip expectations to `docs/user-guide.md`
- [X] T003 [P] Add live test fixture placeholders and required environment variable constants in `tests/fixtures/live_env.py`
- [X] T004 [P] Add dry-run candidate sample configuration to `configs/projects/rewrite_quality.yaml`
- [X] T005 Verify `langfuse`, `openai`, `azure-identity`, and `pytest` live marker dependencies remain declared in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared live infrastructure that must exist before user-story work.

**Critical**: No user story implementation should begin until these tasks are
complete.

### Tests for Foundation

- [X] T006 [P] Add unit tests for Langfuse host resolution, `.env` loading, and secret redaction in `tests/unit/test_live_settings.py`
- [X] T007 [P] Add unit tests for live trace metadata containing dataset item correlation fields in `tests/unit/test_live_trace_metadata.py`
- [X] T008 [P] Add unit tests for deterministic stable review cohort selection by dataset item ID in `tests/unit/test_stable_review_cohort.py`
- [X] T009 [P] Add contract tests for live CLI fail-fast behavior before provider calls in `tests/contract/test_cli_live_failfast.py`
- [X] T071 [P] Add unit tests for dataset compatibility version fallback from stable item IDs and input hashes in `tests/unit/test_dataset_compatibility_version.py`

### Implementation for Foundation

- [X] T010 Implement live settings resolution for `LANGFUSE_HOST`, `LANGFUSE_BASE_URL`, Langfuse keys, and Azure env references in `src/evaluator_harness/config.py`
- [X] T011 Add live connectivity verification and workspace-access abstraction to `src/evaluator_harness/langfuse_client.py`
- [X] T012 Add dataset item correlation fields to trace payload construction in `src/evaluator_harness/runner.py`
- [X] T013 Add stable review cohort data structures and deterministic selection helpers in `src/evaluator_harness/review_selection.py`
- [X] T014 Update fake Langfuse fixture to support live connectivity checks, dataset item IDs, dataset run item IDs, baseline metadata queries, and duplicate queue detection in `tests/fixtures/fake_langfuse.py`
- [X] T015 Update CLI error handling to preserve actionable live failure messages and non-zero exits in `src/evaluator_harness/cli.py`
- [X] T072 Implement dataset compatibility version derivation and propagation for sync, trace metadata, and baseline fingerprints in `src/evaluator_harness/dataset_loader.py`

**Checkpoint**: Foundation ready; user-story implementation can proceed.

---

## Phase 3: User Story 1 - Persist Baseline Runs in Langfuse (Priority: P1) MVP

**Goal**: A live Azure OpenAI baseline run creates a distinct Langfuse dataset
run, item traces, outputs, and reusable baseline reference without using a
local live baseline registry.

**Independent Test**: Run baseline with fake Langfuse/provider and confirm run
metadata, traces, dataset item correlation, baseline reference, fail-fast
behavior, and no local live registry dependency.

### Tests for User Story 1

- [X] T016 [P] [US1] Add unit tests for Azure OpenAI client construction with tenant ID, client ID, client secret, scope, APIM subscription key, and Langfuse `AzureOpenAI` preference in `tests/unit/test_live_azure_openai_provider.py`
- [X] T017 [P] [US1] Add unit tests for baseline compatibility fingerprint persistence payloads in `tests/unit/test_live_baseline_reference.py`
- [X] T018 [P] [US1] Add contract test for `run --mode baseline` live output fields and exit codes in `tests/contract/test_cli_live_run_baseline.py`
- [X] T019 [P] [US1] Add integration test with fakes for live baseline fail-fast before Azure token acquisition when Langfuse is unreachable in `tests/integration/test_live_baseline_failfast.py`
- [X] T020 [P] [US1] Add integration test with fakes for baseline dataset run creation, trace linkage, evaluator-ready payloads, and baseline reference recording in `tests/integration/test_live_run_baseline.py`
- [X] T021 [P] [US1] Add opt-in live smoke test for real Langfuse dataset sync plus Azure OpenAI baseline execution in `tests/integration/live/test_live_azure_baseline_smoke.py`

### Implementation for User Story 1

- [X] T022 [US1] Implement Langfuse client factory using real SDK credentials and a fake-injectable interface in `src/evaluator_harness/langfuse_client.py`
- [X] T023 [US1] Implement live dataset experiment/run creation or equivalent SDK-backed trace linkage for baseline runs in `src/evaluator_harness/langfuse_client.py`
- [X] T024 [US1] Update baseline execution to verify Langfuse before provider token acquisition or model calls in `src/evaluator_harness/runner.py`
- [X] T025 [US1] Update Azure OpenAI provider to prefer `langfuse.openai.AzureOpenAI` and expose manual fallback diagnostics only when needed in `src/evaluator_harness/providers/openai_compatible.py`
- [X] T026 [US1] Persist baseline references and compatibility metadata to Langfuse run/trace metadata in `src/evaluator_harness/runner.py`
- [X] T027 [US1] Replace live baseline lookup dependency on local `BaselineRegistry` with Langfuse-backed baseline reference access for live runs in `src/evaluator_harness/baseline_registry.py`
- [X] T028 [US1] Ensure baseline traces include dataset name, dataset version, local item ID, Langfuse dataset item ID when available, dataset run item ID when available, prompt version, evaluator set, model parameters, latency, token fields, and cost fields in `src/evaluator_harness/runner.py`
- [X] T029 [US1] Update baseline CLI success output with run ID, dataset identity, item counts, compatibility fingerprint, and Langfuse identifiers in `src/evaluator_harness/cli.py`
- [X] T030 [US1] Update fake provider and fake Langfuse fixtures for baseline partial failure scenarios in `tests/fixtures/fake_provider.py`

**Checkpoint**: US1 is independently complete when fake tests pass and the
opt-in live smoke baseline test can run with credentials.

---

## Phase 4: User Story 2 - Run Candidates Against Persisted Baselines (Priority: P2)

**Goal**: A dry-run candidate can be launched in a later command execution,
resolve a compatible baseline from Langfuse, and persist a distinct candidate
run linked to that baseline.

**Independent Test**: Seed a fake Langfuse baseline reference, run a dry-run
candidate with `latest-compatible`, and confirm candidate traces reference the
baseline and preserve dataset item identity.

### Tests for User Story 2

- [X] T031 [P] [US2] Add unit tests for Langfuse-backed `latest-compatible` and explicit baseline resolution in `tests/unit/test_live_baseline_resolution.py`
- [X] T032 [P] [US2] Add unit tests for incompatible explicit baseline rejection before candidate output generation in `tests/unit/test_live_candidate_compatibility.py`
- [X] T033 [P] [US2] Add contract test for `run --mode candidate --baseline latest-compatible` live output fields and exit codes in `tests/contract/test_cli_live_run_candidate.py`
- [X] T034 [P] [US2] Add integration test with fakes for dry-run candidate reuse of a persisted Langfuse baseline across separate runner instances in `tests/integration/test_live_run_candidate.py`
- [X] T035 [P] [US2] Add integration test that running the same dry-run candidate twice creates distinct candidate run IDs linked to the same baseline in `tests/integration/test_live_candidate_distinct_runs.py`
- [X] T073 [P] [US2] Add unit tests for first-class `dry_run` provider config validation and provider factory creation in `tests/unit/test_dry_run_provider.py`
- [X] T074 [P] [US2] Add integration test with fakes for candidate partial failures recording successful and failed items in one run in `tests/integration/test_live_candidate_partial_failure.py`
- [X] T078 [P] [US2] Add opt-in live smoke test for dry-run candidate execution against a real Langfuse-persisted baseline in `tests/integration/live/test_live_dry_run_candidate_smoke.py`

### Implementation for User Story 2

- [X] T036 [US2] Implement Langfuse baseline query and compatibility filtering for `latest-compatible` in `src/evaluator_harness/langfuse_client.py`
- [X] T037 [US2] Implement explicit baseline ID lookup and compatibility validation in `src/evaluator_harness/baseline_registry.py`
- [X] T038 [US2] Add a dry-run candidate provider path that returns deterministic fake output and traceable metadata in `src/evaluator_harness/providers/base.py`
- [X] T039 [US2] Update candidate execution to fail before provider generation when no compatible baseline exists in `src/evaluator_harness/runner.py`
- [X] T040 [US2] Persist candidate traces with baseline reference, dataset item identity, model parameters, prompt version, evaluator set, and per-item failure context in `src/evaluator_harness/runner.py`
- [X] T041 [US2] Update candidate CLI success and failure output for baseline selector, selected baseline ID, candidate run ID, and item counts in `src/evaluator_harness/cli.py`
- [X] T075 [US2] Add `DRY_RUN` provider enum value, config validation, provider factory registration, and dry-run provider module in `src/evaluator_harness/providers/dry_run.py`

**Checkpoint**: US2 is complete when candidate runs can reuse persisted
baselines without rerunning baseline.

---

## Phase 5: User Story 3 - Sync Live Langfuse Assets Safely (Priority: P3)

**Goal**: Dataset and harness-managed score config sync commands work safely
against live Langfuse, remain idempotent, and never mutate incompatible or
user-owned score configs.

**Independent Test**: Run sync twice against fakes and confirm dataset items
and compatible score configs are reused; incompatible managed configs fail with
clear remediation.

### Tests for User Story 3

- [X] T042 [P] [US3] Add unit tests for live dataset item upsert payloads with stable local and Langfuse item IDs in `tests/unit/test_live_dataset_sync.py`
- [X] T043 [P] [US3] Add unit tests for live score config create, reuse, incompatible conflict, archived conflict, and user-owned validation in `tests/unit/test_live_score_config_sync.py`
- [X] T044 [P] [US3] Add contract tests for `sync-dataset` and `sync-score-configs` live output fields and exit codes in `tests/contract/test_cli_live_sync_assets.py`
- [X] T045 [P] [US3] Add integration test with fakes for repeated dataset and score config sync idempotency in `tests/integration/test_live_sync_assets.py`
- [X] T046 [P] [US3] Add opt-in live smoke test for real Langfuse dataset and score config sync using the sample project in `tests/integration/live/test_live_sync_assets_smoke.py`
- [X] T076 [P] [US3] Add opt-in live smoke test for CSV export after live baseline and dry-run candidate runs in `tests/integration/live/test_live_export_smoke.py`

### Implementation for User Story 3

- [X] T047 [US3] Implement real Langfuse Dataset create/resolve and item upsert behavior in `src/evaluator_harness/langfuse_client.py`
- [X] T048 [US3] Implement real Langfuse score config create/reuse and incompatible conflict behavior in `src/evaluator_harness/langfuse_client.py`
- [X] T049 [US3] Update dataset sync command output with Langfuse dataset name, version, item count, rejected count, and status in `src/evaluator_harness/cli.py`
- [X] T050 [US3] Update score config sync command output with evaluator name, ownership, managed name or user-owned ID, Langfuse score config ID, and status in `src/evaluator_harness/cli.py`
- [X] T051 [US3] Ensure sync commands verify Langfuse workspace access but do not call Azure OpenAI or candidate providers in `src/evaluator_harness/runner.py`

**Checkpoint**: US3 is complete when setup commands are safe and repeatable
against fakes and live smoke credentials.

---

## Phase 6: User Story 4 - Route Human Review Items to Langfuse (Priority: P4)

**Goal**: Select stable random calibration items plus run-specific risk items
and route them to an existing Langfuse Human Annotation Queue without
duplicates.

**Independent Test**: Given baseline and candidate traces over the same dataset
version, review selection returns the same random calibration item IDs for both
runs and routes candidate review payloads idempotently.

### Tests for User Story 4

- [X] T052 [P] [US4] Add unit tests for stable calibration cohort seed material, item ordering, and dataset version or review policy changes in `tests/unit/test_stable_review_cohort.py`
- [X] T053 [P] [US4] Add unit tests for separating `stable_calibration` and `run_risk` review buckets in `tests/unit/test_review_selection.py`
- [X] T054 [P] [US4] Add unit tests for annotation queue payloads including input, baseline output, candidate output, ground truth, trace context, selection bucket, and blind evaluator metadata in `tests/unit/test_annotation_queue_payloads.py`
- [X] T055 [P] [US4] Add contract test for `select-review` live output fields, missing queue failure, and duplicate skip counts in `tests/contract/test_cli_live_select_review.py`
- [X] T056 [P] [US4] Add integration test with fakes showing baseline and compatible candidate runs select the same random calibration item IDs in `tests/integration/test_live_stable_review_selection.py`
- [X] T057 [P] [US4] Add integration test with fakes for idempotent annotation queue routing in `tests/integration/test_live_annotation_queue_routing.py`
- [X] T077 [P] [US4] Add opt-in live smoke test for review routing when `LANGFUSE_ANNOTATION_QUEUE_ID` is configured in `tests/integration/live/test_live_review_routing_smoke.py`

### Implementation for User Story 4

- [X] T058 [US4] Add `review_policy_version` or deterministic derived policy fingerprint support to `src/evaluator_harness/config.py`
- [X] T059 [US4] Update review selection to always include stable calibration items by dataset item ID before additive run-risk items in `src/evaluator_harness/review_selection.py`
- [X] T060 [US4] Update annotation queue payload builder to include `selection_bucket`, dataset item identity, baseline output, candidate output, ground truth, and trace context in `src/evaluator_harness/langfuse_client.py`
- [X] T061 [US4] Implement real Langfuse Annotation Queue item routing or API wrapper with duplicate detection by queue, run, and trace in `src/evaluator_harness/langfuse_client.py`
- [X] T062 [US4] Update `select-review` runner flow to fetch scores, build stable cohort, add risk items, route queue items, and return selected/queued/skipped counts in `src/evaluator_harness/runner.py`
- [X] T063 [US4] Update `select-review` CLI output for stable calibration count, risk count, queue ID, queued count, skipped duplicate count, and selection reasons in `src/evaluator_harness/cli.py`

**Checkpoint**: US4 is complete when stable review cohorts and annotation queue
routing are repeatable across baseline and compatible candidate runs.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, live smoke reliability, and full regression
verification.

- [X] T064 [P] Update live MVP workflow steps, `LANGFUSE_HOST`, dry-run candidate, stable review cohorts, and live smoke commands in `docs/user-guide.md`
- [X] T065 [P] Update README setup and quickstart references for live Langfuse MVP in `README.md`
- [X] T066 [P] Add troubleshooting notes for Langfuse unreachable, Azure token acquisition failure, incompatible baseline, incompatible score config, and missing annotation queue in `docs/user-guide.md`
- [X] T067 Run default offline tests with `uv run pytest` and fix regressions in `tests/`
- [X] T068 Run focused live-contract tests with `uv run pytest tests/contract -p no:cacheprovider` and fix regressions in `tests/contract/`
- [X] T069 Run opt-in live smoke tests with `uv run pytest -m live` when credentials are configured and confirm credential-dependent skips are reported by pytest
- [X] T070 Verify `uv run python run_experiment.py validate --project configs/projects/rewrite_quality.yaml` and sync/run command examples in `specs/002-live-langfuse-mvp/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **US1 Persist Baseline (Phase 3)**: Depends on Foundation; this is the MVP.
- **US2 Candidate Against Baseline (Phase 4)**: Depends on Foundation and uses
  US1 baseline metadata behavior.
- **US3 Safe Asset Sync (Phase 5)**: Depends on Foundation; can be developed in
  parallel with US1/US2 if shared `langfuse_client.py` edits are coordinated.
- **US4 Human Review Routing (Phase 6)**: Depends on Foundation and benefits
  from US1/US2 trace metadata.
- **Polish (Phase 7)**: Depends on completed story phases selected for release.

### User Story Dependencies

- **US1 (P1)**: Foundation only; delivers MVP baseline persistence.
- **US2 (P2)**: Requires Langfuse baseline reference semantics from US1.
- **US3 (P3)**: Foundation only for standalone sync commands, but shares live
  Langfuse client implementation with US1.
- **US4 (P4)**: Requires trace metadata from US1/US2 for useful review payloads.

### Within Each User Story

- Tests must be written before implementation tasks.
- Contract and integration tests should initially fail for live behavior.
- Implement Langfuse client boundaries before runner orchestration.
- Update CLI output after core behavior exists.
- Validate each story independently before moving to the next priority.

## Parallel Opportunities

- T002, T003, T004 can run in parallel after T001 is understood.
- T006, T007, T008, and T009 can run in parallel because they are independent
  test files.
- US1 test tasks T016 through T021 can run in parallel before implementation.
- US2 test tasks T031 through T035 can run in parallel after US1 contracts are
  clear.
- US3 test tasks T042 through T046 can run in parallel with US2 if
  `langfuse_client.py` implementation changes are coordinated.
- US4 test tasks T052 through T057 can run in parallel after stable cohort
  data requirements are agreed.
- Documentation tasks T064 through T066 can run in parallel during final polish.

## Parallel Example: User Story 1

```text
Task: "Add unit tests for Azure OpenAI client construction with tenant ID, client ID, client secret, scope, APIM subscription key, and Langfuse AzureOpenAI preference in tests/unit/test_live_azure_openai_provider.py"
Task: "Add unit tests for baseline compatibility fingerprint persistence payloads in tests/unit/test_live_baseline_reference.py"
Task: "Add integration test with fakes for baseline dataset run creation, trace linkage, evaluator-ready payloads, and baseline reference recording in tests/integration/test_live_run_baseline.py"
```

## Parallel Example: User Story 4

```text
Task: "Add unit tests for stable calibration cohort seed material, item ordering, and dataset version or review policy changes in tests/unit/test_stable_review_cohort.py"
Task: "Add unit tests for annotation queue payloads including input, baseline output, candidate output, ground truth, trace context, selection bucket, and blind evaluator metadata in tests/unit/test_annotation_queue_payloads.py"
Task: "Add integration test with fakes showing baseline and compatible candidate runs select the same random calibration item IDs in tests/integration/test_live_stable_review_selection.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 setup.
2. Complete Phase 2 foundation.
3. Complete Phase 3 US1 baseline persistence.
4. Stop and validate with fake tests plus live baseline smoke test when
   credentials are configured.

### Incremental Delivery

1. US1 creates live persisted baselines.
2. US2 adds dry-run candidate reuse of persisted baselines.
3. US3 hardens explicit sync commands and score config safety.
4. US4 adds stable human-review cohort selection and annotation queue routing.
5. Polish updates docs and runs full verification.

### Notes

- Keep live credentials out of committed files and test output.
- Default tests must remain credential-free.
- Live smoke tests must be opt-in and small.
- Avoid service APIs, dashboards, databases, or local scoring engines.
- Prefer Langfuse SDK integrations before manual tracing; document fallback
  reasons in provider diagnostics when fallback is used.

