# Tasks: Campaign Calibration Report

**Input**: Design documents from `/specs/027-campaign-calibration-report/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/campaign-calibration-report.md, quickstart.md

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover success paths, validation failures, Langfuse/provider failures, metadata correctness, and CLI exit behavior where applicable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or does not depend on incomplete tasks
- **[Story]**: User story label for story phases only
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the shared file/module structure and fixture scaffolding used by all campaign calibration stories.

- [X] T001 Create campaign calibration orchestration module scaffold in `src/evaluator_harness/campaign_calibration.py`
- [X] T002 Create campaign calibration HTML report module scaffold in `src/evaluator_harness/campaign_calibration_reports.py`
- [X] T003 [P] Create campaign calibration unit test scaffold in `tests/unit/test_campaign_calibration.py`
- [X] T004 [P] Create campaign calibration report unit test scaffold in `tests/unit/test_campaign_calibration_reports.py`
- [X] T005 [P] Create campaign calibration CLI contract test scaffold in `tests/contract/test_cli_campaign_calibration_report.py`
- [X] T006 [P] Create campaign calibration integration test scaffold in `tests/integration/test_campaign_calibration_flow.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define durable campaign run references, manifest persistence, and fallback discovery before story-specific orchestration.

**CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundation

- [X] T007 [P] Add unit tests for `CampaignRunReference` and `CampaignManifest` validation in `tests/unit/test_campaign_calibration.py`
- [X] T008 [P] Add unit tests for writing a manifest from `CampaignRunResult` in `tests/unit/test_campaign_calibration.py`
- [X] T009 [P] Add unit tests for loading a manifest by baseline run ID from `reports/<project>/campaign-manifests/` in `tests/unit/test_campaign_calibration.py`
- [X] T010 [P] Add unit tests for fallback run discovery from existing CSV export artifacts when no manifest exists in `tests/unit/test_campaign_calibration.py`
- [X] T011 [P] Add unit tests for clear failure when neither manifest nor fallback artifacts identify the baseline in `tests/unit/test_campaign_calibration.py`

### Implementation for Foundation

- [X] T012 Define `CampaignRunReference`, `CampaignManifest`, and manifest validation helpers in `src/evaluator_harness/campaign_calibration.py`
- [X] T013 Implement manifest path resolution for `reports/<project>/campaign-manifests/<baseline-run-id>.json` in `src/evaluator_harness/campaign_calibration.py`
- [X] T014 Implement manifest serialization and deserialization in `src/evaluator_harness/campaign_calibration.py`
- [X] T015 Implement conversion from `CampaignRunResult` to `CampaignManifest` in `src/evaluator_harness/campaign_calibration.py`
- [X] T016 Update `src/evaluator_harness/campaigns.py` to write a campaign manifest after campaign runs finish and report/export paths are known
- [X] T017 Implement fallback discovery of campaign run references from existing CSV exports using `discover_reports_with_warnings()` in `src/evaluator_harness/campaign_calibration.py`
- [X] T018 Ensure fallback discovery always includes the provided baseline run ID and supports baseline-only campaigns in `src/evaluator_harness/campaign_calibration.py`

**Checkpoint**: Manifest and fallback run discovery are implemented and testable without running calibration capture.

---

## Phase 3: User Story 1 - Capture Campaign Calibration (Priority: P1) MVP

**Goal**: A user can run one post-campaign command anchored by the baseline run ID and capture calibration snapshots for the baseline and every discoverable candidate without rerunning the campaign.

**Independent Test**: Use a fake runner/gateway and a manifest with one baseline plus two candidates, then verify snapshots are requested for all three runs and missing annotation warnings do not stop remaining runs.

### Tests for User Story 1

- [X] T019 [P] [US1] Add unit test for resolving run references from manifest before fallback artifacts in `tests/unit/test_campaign_calibration.py`
- [X] T020 [P] [US1] Add unit test for baseline-only campaign capture in `tests/unit/test_campaign_calibration.py`
- [X] T021 [P] [US1] Add unit test for continuing capture when a candidate capture returns missing-annotation warnings in `tests/unit/test_campaign_calibration.py`
- [X] T022 [P] [US1] Add contract test for `campaign-calibration-report --project --baseline` invoking runner capture flow in `tests/contract/test_cli_campaign_calibration_report.py`
- [X] T023 [P] [US1] Add integration test with fake Langfuse/calibration inputs for campaign capture artifacts in `tests/integration/test_campaign_calibration_flow.py`

### Implementation for User Story 1

- [X] T024 [US1] Define `CampaignRunCalibrationResult` and `CampaignCalibrationRun` result models in `src/evaluator_harness/campaign_calibration.py`
- [X] T025 [US1] Implement `resolve_campaign_run_references()` with manifest-first and fallback-second behavior in `src/evaluator_harness/campaign_calibration.py`
- [X] T026 [US1] Implement `capture_campaign_calibration()` to call existing per-run calibration capture callback for each run reference in `src/evaluator_harness/campaign_calibration.py`
- [X] T027 [US1] Add warning aggregation for missing exports, missing scores, missing annotations, and per-run capture failures in `src/evaluator_harness/campaign_calibration.py`
- [X] T028 [US1] Add `ExperimentRunner.campaign_calibration_report()` capture orchestration entry point in `src/evaluator_harness/runner.py`
- [X] T029 [US1] Add `campaign-calibration-report` Typer command with `--project`, `--baseline`, `--reports-dir`, `--output`, and `--output-dir` options in `src/evaluator_harness/cli.py`
- [X] T030 [US1] Add `present_campaign_calibration_result()` initial console output for capture counts and warnings in `src/evaluator_harness/cli_presenters.py`

**Checkpoint**: User Story 1 works independently: campaign run IDs resolve from a baseline anchor and calibration snapshots are captured for every resolved run.

---

## Phase 4: User Story 2 - Summarize Campaign Calibration (Priority: P2)

**Goal**: After campaign snapshots are captured, each baseline/candidate run receives a calibration summary with evaluator-level alignment metrics and warnings.

**Independent Test**: Start from fake snapshot outputs for one baseline and one candidate, run campaign summarization, and verify per-run summary artifacts and aggregate warnings are reported.

### Tests for User Story 2

- [X] T031 [P] [US2] Add unit test for summarizing every successfully captured run in `tests/unit/test_campaign_calibration.py`
- [X] T032 [P] [US2] Add unit test for zero paired coverage warning propagation in `tests/unit/test_campaign_calibration.py`
- [X] T033 [P] [US2] Add unit test that candidate summary failure does not block baseline summary result in `tests/unit/test_campaign_calibration.py`
- [X] T034 [P] [US2] Add contract test for CLI output showing summarized count and warning count in `tests/contract/test_cli_campaign_calibration_report.py`
- [X] T035 [P] [US2] Add integration test verifying `<run-id>-summary.json` files are produced for resolved runs in `tests/integration/test_campaign_calibration_flow.py`

### Implementation for User Story 2

- [X] T036 [US2] Implement `summarize_campaign_calibration()` to call existing per-run calibration summary callback after capture in `src/evaluator_harness/campaign_calibration.py`
- [X] T037 [US2] Update `CampaignRunCalibrationResult` population with summary path, summary count, paired count, and pending count in `src/evaluator_harness/campaign_calibration.py`
- [X] T038 [US2] Implement status classification `completed`, `warning`, and `failed` for per-run campaign calibration results in `src/evaluator_harness/campaign_calibration.py`
- [X] T039 [US2] Update `ExperimentRunner.campaign_calibration_report()` to execute capture then summary for each resolved run in `src/evaluator_harness/runner.py`
- [X] T040 [US2] Update `present_campaign_calibration_result()` to print summarized count, failed run warnings, and zero coverage warnings in `src/evaluator_harness/cli_presenters.py`

**Checkpoint**: User Story 2 works independently from the report renderer: campaign snapshots produce per-run summaries and warnings.

---

## Phase 5: User Story 3 - Generate Campaign Calibration HTML Report (Priority: P3)

**Goal**: Generate one static HTML report that shows baseline and candidate calibration alignment side by side with evaluator metrics, largest deltas, paired records, and warnings.

**Independent Test**: Use completed campaign calibration summaries and snapshot records, generate the report, and verify the HTML contains run overview, evaluator comparison, largest deltas, detailed paired records, and warnings.

### Tests for User Story 3

- [X] T041 [P] [US3] Add unit test for building `CampaignCalibrationReportPayload` from run results, summaries, and snapshots in `tests/unit/test_campaign_calibration_reports.py`
- [X] T042 [P] [US3] Add unit test for report output path derivation and `.html` validation in `tests/unit/test_campaign_calibration_reports.py`
- [X] T043 [P] [US3] Add unit test that report HTML includes baseline/candidate identities, paired coverage, disagreement rate, mean absolute score delta, directional bias, and warnings in `tests/unit/test_campaign_calibration_reports.py`
- [X] T044 [P] [US3] Add contract test for CLI output showing final HTML report path in `tests/contract/test_cli_campaign_calibration_report.py`
- [X] T045 [P] [US3] Add integration test that `campaign-calibration-report` writes `<baseline-run-id>-calibration-report.html` in `tests/integration/test_campaign_calibration_flow.py`

### Implementation for User Story 3

- [X] T046 [US3] Define `CampaignCalibrationReportPayload` and report output model in `src/evaluator_harness/campaign_calibration_reports.py`
- [X] T047 [US3] Implement loading of per-run summary JSON and snapshot JSON/CSV details for report payload generation in `src/evaluator_harness/campaign_calibration_reports.py`
- [X] T048 [US3] Implement report output path derivation for `reports/<project>/<baseline-run-id>-calibration-report.html` plus `--output` and `--output-dir` overrides in `src/evaluator_harness/campaign_calibration_reports.py`
- [X] T049 [US3] Implement self-contained HTML rendering for run overview, evaluator comparison, largest deltas, paired detail records, pending records, and warnings in `src/evaluator_harness/campaign_calibration_reports.py`
- [X] T050 [US3] Integrate HTML report generation into `ExperimentRunner.campaign_calibration_report()` after capture and summary complete in `src/evaluator_harness/runner.py`
- [X] T051 [US3] Update `present_campaign_calibration_result()` to print final report path and aggregate counts in `src/evaluator_harness/cli_presenters.py`

**Checkpoint**: All user stories are independently functional and the end-to-end post-campaign calibration report workflow is available from the CLI.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and verification across the full feature.

- [X] T052 [P] Update `specs/027-campaign-calibration-report/quickstart.md` with any final CLI option names or artifact paths changed during implementation
- [X] T053 [P] Update `specs/027-campaign-calibration-report/contracts/campaign-calibration-report.md` if final console output or exit semantics changed during implementation
- [X] T054 [P] Add or update CLI presenter snapshots/assertions for warning formatting in `tests/unit/test_cli_presenters.py`
- [X] T055 Run `uv run pytest tests/unit/test_campaign_calibration.py tests/unit/test_campaign_calibration_reports.py tests/contract/test_cli_campaign_calibration_report.py tests/integration/test_campaign_calibration_flow.py` and fix failures
- [X] T056 Run `uv run pytest -p no:cacheprovider` for the full non-live suite and fix regressions
- [X] T057 Run `graphify update .` to refresh the local code graph after implementation changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundation**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2; MVP scope.
- **Phase 4 US2**: Depends on Phase 2 and reuses US1 orchestration/results when implemented sequentially.
- **Phase 5 US3**: Depends on Phase 2 and consumes snapshot/summary artifacts from US1/US2.
- **Phase 6 Polish**: Depends on selected user stories being complete.

### User Story Dependencies

- **US1 Capture Campaign Calibration**: Can start after foundation and is the MVP.
- **US2 Summarize Campaign Calibration**: Can start after foundation, but final integration is simpler after US1 result models exist.
- **US3 Generate HTML Report**: Can start report payload tests after foundation, but full integration depends on US1 and US2 artifacts.

### Parallel Opportunities

- T003-T006 can run in parallel after T001-T002.
- T007-T011 can run in parallel because they are separate foundation behaviors.
- T019-T023 can run in parallel before US1 implementation.
- T031-T035 can run in parallel before US2 implementation.
- T041-T045 can run in parallel before US3 implementation.
- Documentation polish tasks T052-T054 can run in parallel once implementation stabilizes.

## Parallel Example: User Story 1

```bash
# Tests can be written together before implementation:
Task: "Add unit test for resolving run references from manifest before fallback artifacts in tests/unit/test_campaign_calibration.py"
Task: "Add contract test for campaign-calibration-report --project --baseline invoking runner capture flow in tests/contract/test_cli_campaign_calibration_report.py"
Task: "Add integration test with fake Langfuse/calibration inputs for campaign capture artifacts in tests/integration/test_campaign_calibration_flow.py"
```

## Parallel Example: User Story 3

```bash
# Report tests can be written without touching orchestration internals:
Task: "Add unit test for building CampaignCalibrationReportPayload from run results, summaries, and snapshots in tests/unit/test_campaign_calibration_reports.py"
Task: "Add unit test that report HTML includes baseline/candidate identities and calibration metrics in tests/unit/test_campaign_calibration_reports.py"
Task: "Add contract test for CLI output showing final HTML report path in tests/contract/test_cli_campaign_calibration_report.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 setup.
2. Complete Phase 2 foundation for manifest and fallback run discovery.
3. Complete Phase 3 capture orchestration and CLI entry point.
4. Stop and validate US1 independently with unit, contract, and integration tests.

### Incremental Delivery

1. Foundation -> manifest/fallback discovery works.
2. US1 -> campaign capture works from a baseline run ID.
3. US2 -> campaign summaries are generated for captured runs.
4. US3 -> campaign-level HTML report is generated from summaries/snapshots.
5. Polish -> docs, full test suite, graph update.

### Notes

- Keep Langfuse as the system of record; local manifest and report files are resumability/reporting artifacts only.
- Do not duplicate single-run score pairing or summary metric calculations; compose existing calibration functions.
- Reruns overwrite campaign calibration artifacts from latest available Langfuse state.
- Baseline-only campaigns are valid and must remain covered by tests.
