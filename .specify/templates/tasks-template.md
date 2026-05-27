---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for this project. Write tests before implementation
tasks and cover success paths, validation failures, provider failures, Langfuse
failures, metadata correctness, and CLI exit behavior where applicable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Default project shape**: Python CLI files at repository root or under
  `src/`, tests under `tests/`, datasets under `datasets/`, project prompts and
  evaluator prompts under `prompts/`, and lightweight configs under `configs/`.
- **Python environment**: Use `uv` for environment setup and execution. Prefer
  `uv sync`, `uv run python ...`, and `uv run pytest` over direct Python or
  pytest commands.
- **Provider adapters**: Keep provider-specific code in small adapter modules;
  prefer OpenAI-compatible APIs where practical.
- **Avoid by default**: `backend/`, `frontend/`, service APIs, databases,
  orchestration layers, and dashboards unless plan.md records a constitution
  violation and justification.
- Paths shown below assume the lightweight harness shape - adjust based on the
  concrete plan.md structure.

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The /speckit-tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/

  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment

  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T004 Define lightweight config loading for projects, providers, models, prompts, evaluators, and Langfuse settings
- [ ] T005 [P] Add or update CSV dataset loading with required `input` column validation
- [ ] T006 [P] Add or update prompt/evaluator version loading and run metadata capture
- [ ] T007 Implement Langfuse trace and experiment metadata logging
- [ ] T008 Add baseline run selection, generation, or reuse support
- [ ] T009 Configure minimal error handling and local logging for CLI execution
- [ ] T010 Define test fixtures and fakes for Langfuse, model providers, local datasets, and CLI execution

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (REQUIRED)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Unit test for [behavior] in tests/unit/test_[name].py
- [ ] T012 [P] [US1] Contract test for [interface] in tests/contract/test_[name].py
- [ ] T013 [P] [US1] Integration test with fakes for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 1

- [ ] T014 [P] [US1] Add or update provider adapter in src/providers/[provider].py
- [ ] T015 [P] [US1] Add or update prompt/config fixture in prompts/ or configs/
- [ ] T016 [US1] Implement experiment execution flow in src/[location]/[file].py
- [ ] T017 [US1] Log project, provider, model, prompt version, evaluator versions, baseline reference, temperature, latency, token usage, timestamps, and run identifiers to Langfuse
- [ ] T018 [US1] Add validation and clear CLI error handling
- [ ] T019 [US1] Preserve Langfuse trace links or identifiers for human review

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (REQUIRED)

- [ ] T018 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T019 [P] [US2] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 2

- [ ] T020 [P] [US2] Add or update provider adapter/config in src/providers/ or configs/
- [ ] T021 [US2] Implement candidate or baseline workflow in src/[location]/[file].py
- [ ] T022 [US2] Log comparison-ready metadata and baseline references to Langfuse
- [ ] T023 [US2] Integrate with User Story 1 components only where needed

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (REQUIRED)

- [ ] T024 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T025 [P] [US3] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 3

- [ ] T026 [P] [US3] Add or update lightweight config, dataset, or prompt artifact
- [ ] T027 [US3] Implement CLI-visible behavior in src/[location]/[file].py
- [ ] T028 [US3] Ensure Langfuse logging, evaluator metadata, and baseline comparison metadata are preserved

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Remove unnecessary abstractions or local state introduced during implementation
- [ ] TXXX [P] Additional unit tests (if requested) in tests/unit/
- [ ] TXXX Verify Langfuse traces, prompt versions, evaluator versions, baseline references, and token/latency fields are present
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
