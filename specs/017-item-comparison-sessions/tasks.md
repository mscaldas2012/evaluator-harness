# Tasks: Langfuse Item Comparison Sessions

**Input**: Design documents from `specs/017-item-comparison-sessions/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this project. Write tests before implementation tasks and cover session identity correctness, official Langfuse session propagation, candidate baseline validation, human review trace context, export/report compatibility, and CLI exit behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Python CLI source lives under `src/evaluator_harness/`
- Unit tests live under `tests/unit/`
- Integration tests live under `tests/integration/`
- Contract tests live under `tests/contract/`
- Use `uv run ...` for Python commands and tests

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm existing trace/logging surfaces and identify fixtures needed by later tests.

- [X] T001 Inspect current trace construction and candidate baseline lookup in `src/evaluator_harness/runner.py`
- [X] T002 Inspect current live/fake trace logging behavior in `src/evaluator_harness/langfuse_client.py`
- [X] T003 [P] Inspect current export column mapping in `src/evaluator_harness/exports.py`
- [X] T004 [P] Inspect existing trace, runner, and CLI fixtures in `tests/unit/`, `tests/integration/`, and `tests/contract/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define shared session identity behavior before story-specific trace, review, and export work.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 [P] Add unit tests for deterministic session identity generation in `tests/unit/test_session_identity.py`
- [X] T006 [P] Add unit tests for US-ASCII and under-200-character session ID constraints in `tests/unit/test_session_identity.py`
- [X] T007 [P] Add unit tests proving project, dataset, baseline anchor, and item changes produce distinct IDs in `tests/unit/test_session_identity.py`
- [X] T008 Implement session identity input and derivation helpers in `src/evaluator_harness/session_identity.py`
- [X] T009 Export the session identity helper from `src/evaluator_harness/session_identity.py` with no dependency on Langfuse client state
- [X] T010 Verify foundational behavior with `uv run pytest -p no:cacheprovider tests/unit/test_session_identity.py`

**Checkpoint**: Session IDs can be computed and validated independently of run execution.

---

## Phase 3: User Story 1 - Compare One Item Across Runs (Priority: P1) MVP

**Goal**: Baseline and candidate traces for the same dataset item and baseline anchor share one official Langfuse session, while different items do not.

**Independent Test**: Run one fake baseline and one fake candidate against the same dataset, then verify matching same-item session IDs and distinct different-item session IDs in recorded traces.

### Tests for User Story 1 (REQUIRED)

- [X] T011 [P] [US1] Add integration test for baseline traces containing official and metadata session IDs in `tests/integration/test_item_comparison_sessions.py`
- [X] T012 [P] [US1] Add integration test proving baseline and candidate traces for the same item share a session ID in `tests/integration/test_item_comparison_sessions.py`
- [X] T013 [P] [US1] Add integration test proving different dataset items do not share a session ID in `tests/integration/test_item_comparison_sessions.py`
- [X] T014 [P] [US1] Add integration test proving two candidate runs against the same baseline reuse same-item sessions in `tests/integration/test_item_comparison_sessions.py`
- [X] T015 [P] [US1] Add contract test for candidate runs without explicit baseline reference failing before trace logging in `tests/contract/test_cli_item_comparison_sessions.py`

### Implementation for User Story 1

- [X] T016 [US1] Compute baseline item comparison session inputs in `_run_baseline` in `src/evaluator_harness/runner.py`
- [X] T017 [US1] Compute candidate item comparison session inputs from `baseline_reference.baseline_run_id` in `_run_candidate` in `src/evaluator_harness/runner.py`
- [X] T018 [US1] Add `session_id`, `metadata.item_comparison_session_id`, and `metadata.item_comparison_session_inputs` to trace payloads in `src/evaluator_harness/runner.py`
- [X] T019 [US1] Pass official session fields to live Langfuse trace creation/update calls in `src/evaluator_harness/langfuse_client.py`
- [X] T020 [US1] Preserve official session fields in fake `LangfuseClient.traces` storage in `src/evaluator_harness/langfuse_client.py`
- [X] T021 [US1] Tighten candidate baseline validation so missing explicit baseline references raise `ConfigError` before trace logging in `src/evaluator_harness/runner.py`
- [X] T022 [US1] Verify US1 with `uv run pytest -p no:cacheprovider tests/unit/test_session_identity.py tests/integration/test_item_comparison_sessions.py tests/contract/test_cli_item_comparison_sessions.py`

**Checkpoint**: User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Review Candidate Items With Baseline Context (Priority: P2)

**Goal**: Human review selections retain their current behavior while queued candidate traces carry session context that links to the same-item baseline trace.

**Independent Test**: Queue a candidate item selected for failure, low confidence, or dispute and verify the queued trace retains a session ID that matches the baseline trace for that item.

### Tests for User Story 2 (REQUIRED)

- [X] T023 [P] [US2] Add integration test for selected review candidate traces retaining `item_comparison_session_id` in `tests/integration/test_item_comparison_sessions.py`
- [X] T024 [P] [US2] Add unit test proving `ReviewCandidate.from_trace` preserves existing selection behavior when session metadata is present in `tests/unit/test_review_selection.py`
- [X] T025 [P] [US2] Add integration test proving failures, low-confidence items, and disputed items are still selected independently of session metadata in `tests/integration/test_item_comparison_sessions.py`

### Implementation for User Story 2

- [X] T026 [US2] Ensure annotation queue payload construction carries existing trace/session metadata without changing selection reasons in `src/evaluator_harness/langfuse_client.py`
- [X] T027 [US2] Ensure review selection reads traces with session metadata without changing `ReviewCandidate` classification in `src/evaluator_harness/review_selection.py`
- [X] T028 [US2] Verify US2 with `uv run pytest -p no:cacheprovider tests/unit/test_review_selection.py tests/integration/test_item_comparison_sessions.py`

**Checkpoint**: Human review selection behavior is unchanged, with added same-item session context available on traces.

---

## Phase 5: User Story 3 - Preserve Run-Level Reporting (Priority: P3)

**Goal**: Exports and reports continue to use run IDs, baseline references, and evaluator scores as the authoritative aggregate comparison model while exposing session IDs for diagnostics.

**Independent Test**: Export baseline and candidate runs after session logging and confirm aggregate evaluator averages and baseline references are unchanged while CSV rows include the diagnostic session ID.

### Tests for User Story 3 (REQUIRED)

- [X] T029 [P] [US3] Add unit test for CSV exports including `item_comparison_session_id` in `tests/unit/test_exports.py`
- [X] T030 [P] [US3] Add contract test proving CLI export output remains compatible after session columns are added in `tests/contract/test_cli_export.py`
- [X] T031 [P] [US3] Add regression test proving evaluator scores remain grouped by `trace_id` rather than session membership in `tests/unit/test_exports.py`

### Implementation for User Story 3

- [X] T032 [US3] Add `item_comparison_session_id` to export field mapping in `src/evaluator_harness/exports.py`
- [X] T033 [US3] Ensure report generation paths do not use Langfuse session membership for aggregate comparison in `src/evaluator_harness/runner.py`
- [X] T034 [US3] Verify US3 with `uv run pytest -p no:cacheprovider tests/unit/test_exports.py tests/contract/test_cli_export.py`

**Checkpoint**: Reports remain run-level and session IDs are available for export diagnostics.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup across the feature.

- [X] T035 [P] Update user-facing session notes in `docs/user-guide.md`
- [X] T036 [P] Review `specs/017-item-comparison-sessions/quickstart.md` against final command behavior
- [X] T037 Run focused feature suite with `uv run pytest -p no:cacheprovider tests/unit/test_session_identity.py tests/integration/test_item_comparison_sessions.py tests/contract/test_cli_item_comparison_sessions.py`
- [X] T038 Run regression suite with `uv run pytest -p no:cacheprovider tests/unit/test_live_trace_metadata.py tests/unit/test_exports.py tests/unit/test_review_selection.py tests/contract/test_cli_export.py`
- [X] T039 Run targeted project validation with `uv run python run_experiment.py validate --project configs/projects/gso.yaml`
- [X] T040 Confirm no unrelated binding/report artifacts are staged with `git status --short`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational; MVP scope
- **User Story 2 (Phase 4)**: Depends on US1 because review context requires trace session IDs
- **User Story 3 (Phase 5)**: Depends on US1 because exports need populated trace session metadata
- **Polish (Phase 6)**: Depends on desired user stories being complete

### User Story Dependencies

- **US1**: No dependency on other user stories after Foundational
- **US2**: Depends on US1 trace session metadata but preserves independent review selection behavior
- **US3**: Depends on US1 trace session metadata but preserves independent reporting behavior

### Within Each User Story

- Write tests first and verify they fail for the expected missing behavior
- Implement the smallest code change to pass the story tests
- Run the story-specific verification command before moving on

## Parallel Opportunities

- T003 and T004 can run in parallel with T001 and T002
- T005, T006, and T007 can run in parallel before T008
- T011, T012, T013, T014, and T015 can run in parallel after Foundational
- T023, T024, and T025 can run in parallel after US1
- T029, T030, and T031 can run in parallel after US1
- T035 and T036 can run in parallel after behavior stabilizes

## Parallel Example: User Story 1

```text
Task: "T011 [US1] Add integration test for baseline traces containing official and metadata session IDs in tests/integration/test_item_comparison_sessions.py"
Task: "T012 [US1] Add integration test proving baseline and candidate traces for the same item share a session ID in tests/integration/test_item_comparison_sessions.py"
Task: "T013 [US1] Add integration test proving different dataset items do not share a session ID in tests/integration/test_item_comparison_sessions.py"
Task: "T014 [US1] Add integration test proving two candidate runs against the same baseline reuse same-item sessions in tests/integration/test_item_comparison_sessions.py"
Task: "T015 [US1] Add contract test for candidate runs without explicit baseline reference failing before trace logging in tests/contract/test_cli_item_comparison_sessions.py"
```

## Parallel Example: User Story 2

```text
Task: "T023 [US2] Add integration test for selected review candidate traces retaining item_comparison_session_id in tests/integration/test_item_comparison_sessions.py"
Task: "T024 [US2] Add unit test proving ReviewCandidate.from_trace preserves existing selection behavior when session metadata is present in tests/unit/test_review_selection.py"
Task: "T025 [US2] Add integration test proving failures, low-confidence items, and disputed items are still selected independently of session metadata in tests/integration/test_item_comparison_sessions.py"
```

## Parallel Example: User Story 3

```text
Task: "T029 [US3] Add unit test for CSV exports including item_comparison_session_id in tests/unit/test_exports.py"
Task: "T030 [US3] Add contract test proving CLI export output remains compatible after session columns are added in tests/contract/test_cli_export.py"
Task: "T031 [US3] Add regression test proving evaluator scores remain grouped by trace_id rather than session membership in tests/unit/test_exports.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 only.
3. Verify baseline/candidate same-item session grouping with targeted tests.
4. Stop and demo official Langfuse item comparison sessions.

### Incremental Delivery

1. Deliver US1 to create official Langfuse item comparison sessions.
2. Deliver US2 to confirm human review workflows retain behavior and gain session context.
3. Deliver US3 to expose diagnostic session IDs in exports while preserving aggregate report semantics.
4. Run Phase 6 verification before committing.

### Notes

- Use the official Langfuse session field; metadata-only storage is not sufficient.
- Do not add session-level human or programmatic scoring in this feature.
- Do not use session membership as the source of truth for reports or baseline/candidate matching.
- Preserve existing evaluator filters, prompt bindings, score config bindings, and report generation behavior.
