# Tasks: Scoped Environment Resolution

**Input**: Design documents from `/specs/024-scoped-env-resolution/`

**Prerequisites**: plan.md, spec.md, data-model.md, quickstart.md

**Tests**: Tests are REQUIRED for this feature. Write tests before implementation and cover isolation, mutation prevention, scope cleanup, and provider integration scenarios.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Implementation Strategy

**MVP Scope**: User Story 1 (Config Loader Returns Immutable Environment)
- Implements the core infrastructure (ResolvedEnvironment, EnvironmentResolver)
- Updates ConfigLoader to return immutable environments
- Ensures zero mutations to os.environ
- Forms the foundation for US2 and US3

**Incremental Delivery**: 
1. Phase 2: Core abstraction (ResolvedEnvironment, EnvironmentResolver)
2. Phase 3: US1 - ConfigLoader refactor with immutability
3. Phase 4: US2 - Add EnvironmentScope context manager
4. Phase 5: US3 - Update providers to accept env mappings
5. Phase 6: Polish - Update harness entry points, migration guide

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and test infrastructure setup

- [ ] T001 Create environment abstraction module skeleton at `src/evaluator_harness/environment.py`
- [ ] T002 [P] Create unit test directory structure under `tests/unit/test_environment.py` and `tests/unit/test_config_isolation.py`
- [ ] T003 [P] Create integration test directory structure under `tests/integration/test_repeated_harness.py` and `tests/integration/test_provider_integration.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core environment abstraction that MUST be complete before user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Create `EnvironmentResolver` utility class in `src/evaluator_harness/environment.py` with `resolve()`, `parse_env_file()`, and `load_with_precedence()` methods
  - Implement resolution precedence: shell > project-env > root-env > defaults
  - Support KEY=VALUE file parsing with comment/blank line skipping
  - Validate environment variable names
  - Handle missing required variables with clear error messages

- [ ] T005 [P] Create `ResolvedEnvironment` class in `src/evaluator_harness/environment.py` as immutable mapping wrapper
  - Use `types.MappingProxyType` or equivalent for immutability guarantee
  - Support dict-like interface: `get()`, `__getitem__()`, `items()`, `keys()`, `values()`, `__contains__()`
  - Prevent mutation attempts (raise TypeError)
  - Add copy-safe guarantees (no shared internal references)

- [ ] T006 [P] Create `EnvironmentScope` context manager class in `src/evaluator_harness/environment.py`
  - Implement `__enter__()` and `__exit__()` for context management
  - Support optional `apply_to_os_environ` parameter for legacy client support
  - Snapshot original `os.environ` on entry (if applying)
  - Restore original state on exit (even on exception)
  - Support nesting (independent snapshots)

- [ ] T007 [P] Add unit tests for `EnvironmentResolver` in `tests/unit/test_environment.py`
  - Test precedence resolution (shell > project > root > defaults)
  - Test .env file parsing with comments and blanks
  - Test variable name validation
  - Test missing required variable error handling
  - Minimum 90% code coverage for EnvironmentResolver

- [ ] T008 [P] Add unit tests for `ResolvedEnvironment` immutability in `tests/unit/test_environment.py`
  - Test TypeError raised on item assignment attempt
  - Test TypeError raised on dict mutation methods (pop, clear, update)
  - Test safe iteration and lookup (get, __getitem__)
  - Test copy-safe guarantees (internal dict not exposed)
  - Minimum 90% code coverage for ResolvedEnvironment

- [ ] T009 [P] Add unit tests for `EnvironmentScope` lifecycle in `tests/unit/test_environment.py`
  - Test __enter__ returns ResolvedEnvironment
  - Test __exit__ restores original os.environ
  - Test exception in scope body doesn't prevent cleanup
  - Test nesting produces independent scopes
  - Test apply_to_os_environ=True temporarily injects values
  - Minimum 90% code coverage for EnvironmentScope

**Checkpoint**: Environment abstraction complete and fully tested - ready for ConfigLoader refactoring

---

## Phase 3: User Story 1 - Config Loader Returns Immutable Environment (Priority: P1) 🎯 MVP

**Goal**: Refactor ConfigLoader to return immutable environment mapping without mutating os.environ

**Independent Test**: Create ConfigLoader instance, call resolve_environment(), verify os.environ unchanged and returned mapping immutable and correct

### Tests for User Story 1 (REQUIRED - Write First)

- [ ] T010 [P] [US1] Unit test zero mutation behavior in `tests/unit/test_config_isolation.py`
  - Snapshot os.environ before creating ConfigLoader
  - Load config with .env file overrides
  - Call resolve_environment()
  - Verify os.environ unchanged from snapshot
  - Verify resolved values are correct
  - Repeat with different project configs

- [ ] T011 [P] [US1] Unit test independent instances in `tests/unit/test_config_isolation.py`
  - Create ConfigLoader instance A with one project
  - Create ConfigLoader instance B with different project
  - Call resolve_environment() on each
  - Verify env_a and env_b have expected independent values
  - Verify no cross-contamination between instances
  - Test with 3+ concurrent config instances

- [ ] T012 [P] [US1] Unit test immutability of resolved environment in `tests/unit/test_config_isolation.py`
  - Get resolved_env from resolve_environment()
  - Attempt mutations (assignment, pop, clear, update)
  - Verify all raise TypeError
  - Verify resolved_env still readable after mutation attempts

- [ ] T013 [P] [US1] Integration test for repeated invocations in `tests/integration/test_repeated_harness.py`
  - Run config loading 10+ times in loop
  - Snapshot os.environ before loop
  - Each iteration: create ConfigLoader, call resolve_environment(), verify values
  - After loop: verify os.environ unchanged from initial snapshot
  - Verify no memory leaks from repeated instantiation

### Implementation Tasks for User Story 1

- [ ] T014 [US1] Analyze current config.py mutation points in `src/evaluator_harness/config.py`
  - Identify all os.environ writes in _load_env_file() (lines 644-646)
  - Identify secondary mutations in _normalize_langfuse_host_alias()
  - Document current tracking mechanism (_MANAGED_ENV_VALUES)
  - Plan migration path from global to scoped

- [ ] T015 [US1] Add ConfigLoader.resolve_environment() method in `src/evaluator_harness/config.py`
  - Use EnvironmentResolver to merge root .env, project .env, shell vars
  - Return ResolvedEnvironment (immutable) instead of mutating os.environ
  - Preserve existing resolution precedence (shell > project > root > defaults)
  - Handle missing required variables with clear errors
  - Maintain backward compatibility with existing code paths

- [ ] T016 [US1] Refactor internal config loading to avoid os.environ mutation in `src/evaluator_harness/config.py`
  - Move mutation logic to EnvironmentResolver
  - Store resolved vars in memory instead of os.environ
  - Preserve _MANAGED_ENV_VALUES tracking for debugging (without mutation)
  - Remove direct os.environ writes from config initialization

- [ ] T017 [P] [US1] Update LiveSettings to accept optional env_mapping in `src/evaluator_harness/config.py`
  - Add env_mapping parameter to __init__ (default=None, fallback to os.environ)
  - Use passed env mapping instead of reading from os.environ if provided
  - Preserve current behavior for backward compatibility

- [ ] T018 [P] [US1] Update DefaultLangfuseGateway.from_env() to accept optional env_mapping in `src/evaluator_harness/providers/langfuse_gateway.py`
  - Add env_mapping parameter to from_env() static method
  - Pass env mapping to Langfuse SDK or extract credentials before instantiation
  - Preserve current behavior when env_mapping not provided

- [ ] T019 [US1] Add migration documentation to `specs/024-scoped-env-resolution/migration-notes.md`
  - Document breaking vs. non-breaking API changes
  - Provide examples of old code → new code patterns
  - Note that resolve_environment() is new addition (non-breaking)
  - Note that env_mapping parameters are optional (backward compatible)

**User Story 1 Complete**: ConfigLoader refactored to return immutable environments with zero os.environ mutation

---

## Phase 4: User Story 2 - Environment Context Manager for Scoped Access (Priority: P2)

**Goal**: Provide EnvironmentScope context manager for safe, scoped environment access with automatic cleanup

**Independent Test**: Create scope, enter context, access values, exit context, verify os.environ restored

### Tests for User Story 2 (REQUIRED - Write First)

- [ ] T020 [P] [US2] Unit test context entry and exit in `tests/unit/test_environment_context.py`
  - Enter scope with resolved environment
  - Verify __enter__ returns ResolvedEnvironment
  - Verify values accessible within scope
  - Exit scope via context manager
  - Verify scope exited cleanly

- [ ] T021 [P] [US2] Unit test os.environ restoration in `tests/unit/test_environment_context.py`
  - Snapshot os.environ before scope
  - Enter scope with apply_to_os_environ=True
  - Modify os.environ values in scope
  - Exit scope
  - Verify os.environ identical to pre-scope snapshot

- [ ] T022 [P] [US2] Unit test exception handling in `tests/unit/test_environment_context.py`
  - Enter scope with apply_to_os_environ=True
  - Raise exception in scope body
  - Catch exception and verify scope exited
  - Verify os.environ restored despite exception

- [ ] T023 [P] [US2] Unit test nested scopes in `tests/unit/test_environment_context.py`
  - Create scope_a and scope_b with different environments
  - Enter scope_a (apply_to_os_environ=True)
  - Within scope_a, enter scope_b
  - Verify each scope sees independent values
  - Exit scope_b, then scope_a
  - Verify os.environ restored to original after both exit

- [ ] T024 [US2] Integration test repeated scope usage in `tests/integration/test_repeated_harness.py`
  - Run 10+ iterations of: create ConfigLoader → enter environment_scope() → use values → exit
  - Verify os.environ unchanged after each iteration
  - Verify no resource leaks from repeated scope creation/destruction

### Implementation Tasks for User Story 2

- [ ] T025 [US2] Add ConfigLoader.environment_scope() method in `src/evaluator_harness/config.py`
  - Return EnvironmentScope instance with resolved_env from resolve_environment()
  - Support apply_to_os_environ parameter (default False)
  - Documented usage patterns (legacy fallback, safe scoped access)

- [ ] T026 [P] [US2] Update harness entry point run_experiment() in `src/evaluator_harness/runner.py` or `run_experiment.py`
  - Wrap config loading and client initialization in environment_scope()
  - Use context manager to ensure cleanup on exit
  - Maintain existing public API (no breaking changes)

- [ ] T027 [US2] Add integration test for run_experiment() with environment isolation in `tests/integration/test_repeated_harness.py`
  - Call run_experiment() multiple times in loop
  - Verify os.environ unchanged after each call
  - Verify each call produces independent, correct results

**User Story 2 Complete**: Environment scoping API implemented with automatic cleanup and legacy support

---

## Phase 5: User Story 3 - Provider/Client Construction Uses Scoped Env (Priority: P3)

**Goal**: Update provider and client classes to accept and use environment mappings, eliminating global state dependencies

**Independent Test**: Construct providers with env mappings, verify they work independently without reading os.environ

### Tests for User Story 3 (REQUIRED - Write First)

- [ ] T028 [P] [US3] Unit test provider constructor with env_mapping in `tests/unit/test_provider_env_mapping.py`
  - Create provider with explicit env_mapping parameter
  - Create provider without env_mapping (fallback to os.environ)
  - Verify both modes work correctly
  - Verify provider uses passed mapping, not os.environ

- [ ] T029 [P] [US3] Contract test for provider with env_mapping in `tests/contract/test_provider_interface.py`
  - Verify all providers accept optional env_mapping parameter
  - Verify providers read from env_mapping when provided
  - Verify providers fallback to os.environ when not provided (backward compat)

- [ ] T030 [P] [US3] Integration test concurrent providers in `tests/integration/test_provider_integration.py`
  - Create 3+ providers with different env_mappings
  - Use them concurrently in threads or async context
  - Verify each uses its own environment
  - Verify no cross-contamination between concurrent providers

- [ ] T031 [US3] Integration test provider with scoped environment in `tests/integration/test_provider_integration.py`
  - Load config, enter environment_scope()
  - Create provider with env mapping from scope
  - Use provider within scope
  - Exit scope and verify provider cleanup
  - Repeat with different project configs

### Implementation Tasks for User Story 3

- [ ] T032 [P] [US3] Update OpenAI-Compatible provider to accept env_mapping in `src/evaluator_harness/providers/openai_compatible.py`
  - Add env_mapping parameter to __init__ (default=None)
  - Use env_mapping for credential lookup instead of os.environ
  - Handle both direct credential values and env var name patterns
  - Preserve backward compatibility

- [ ] T033 [P] [US3] Update Langfuse gateway provider to accept env_mapping in `src/evaluator_harness/providers/langfuse_gateway.py`
  - Refactor from_env() to accept env_mapping parameter
  - Pass env_mapping to credential extraction
  - Support both apply_to_os_environ=True legacy mode and scoped mode
  - Maintain SDK compatibility

- [ ] T034 [P] [US3] Update other provider classes to accept env_mapping in `src/evaluator_harness/providers/*.py`
  - Audit all provider classes that read os.environ
  - Add env_mapping parameter to constructors
  - Update credential/config loading to use env_mapping when provided
  - Test each provider independently

- [ ] T035 [US3] Update provider factory/initialization in `src/evaluator_harness/config.py` or relevant module
  - Pass env_mapping when instantiating providers
  - Ensure all client creation goes through scoped environment
  - Verify no hardcoded os.environ reads bypass scoped access

- [ ] T036 [US3] Add provider integration guide to `specs/024-scoped-env-resolution/quickstart.md`
  - Document how to update custom providers to accept env_mapping
  - Provide before/after code examples
  - Show backward compatibility patterns
  - Document fallback behavior

**User Story 3 Complete**: All providers updated to use scoped environments; no global os.environ dependencies

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final refinements, documentation, and verification

- [ ] T037 [P] Update CHANGELOG.md or release notes with scoped environment feature
  - Document breaking vs. non-breaking changes
  - Link to migration guide
  - Note performance implications (negligible)

- [ ] T038 [P] Update project README.md environment configuration section
  - Document new environment_scope() API
  - Provide quickstart examples
  - Link to detailed quickstart.md

- [ ] T039 Run full test suite with pytest and verify coverage
  - Execute `uv run pytest tests/ --cov=src/evaluator_harness --cov-report=term-missing`
  - Verify code coverage ≥ 90% for new environment module
  - Verify all user stories pass independently
  - Verify no regressions in existing tests

- [ ] T040 [P] Run linting and type checking
  - Execute `uv run ruff check src/` (or equivalent linter)
  - Execute `uv run mypy src/evaluator_harness/environment.py` (if using type hints)
  - Fix any style or type issues
  - Ensure code follows project standards

- [ ] T041 Verify isolation with manual testing
  - Create test script that runs 10+ experiment iterations
  - Snapshot and verify os.environ before/after
  - Test with multiple concurrent projects
  - Document results and edge cases found

- [ ] T042 [P] Clean up old mutation tracking code (if applicable)
  - Remove _MANAGED_ENV_VALUES global tracking if no longer used
  - Remove deprecated mutation-based APIs (if applicable)
  - Update comments and docstrings referencing old approach

- [ ] T043 Commit all changes with clear message
  - Verify all tasks completed
  - Create final commit message documenting scope and changes
  - Reference spec, plan, and this tasks.md in commit

---

## Dependency Graph & Parallelization

### Critical Path (Must Complete in Order)
1. Phase 2: Environment abstraction (T004-T009) — blocks all user stories
2. Phase 3: US1 ConfigLoader refactor (T010-T019) — foundation for US2/US3
3. Phase 4: US2 EnvironmentScope API (T020-T027) — enables scoped patterns
4. Phase 5: US3 Provider integration (T028-T036) — uses scopes for providers
5. Phase 6: Polish & verification (T037-T043) — final validation

### Parallel Opportunities

**Within Phase 2** (all independent, can run in parallel):
- T004 (EnvironmentResolver) + T005 (ResolvedEnvironment) + T006 (EnvironmentScope)
- T007 (EnvironmentResolver tests) + T008 (ResolvedEnvironment tests) + T009 (EnvironmentScope tests)

**Within Phase 3** (after T014):
- T017-T018 (Update LiveSettings and Langfuse) can run in parallel
- T010-T013 (Tests) can run in parallel with implementation (T015-T016)

**Within Phase 5** (after Phase 4):
- T032-T034 (Update providers) can run in parallel
- T028-T031 (Tests) can run in parallel with implementation tasks

**Within Phase 6**:
- T037-T038, T040, T041, T042 can run in parallel (independent concerns)
- T039 (Test suite) and T040 (Linting) can run in parallel

### Recommended MVP Scope

**Minimum to deliver value**: Phase 1 + Phase 2 + Phase 3
- Implements core isolation (zero mutations, immutable environments)
- Achieves SC-001, SC-002, SC-005 success criteria
- Ready for review and integration testing
- Phase 4 and Phase 5 follow as incremental improvements

---

## Task Checklist Summary

- **Total Tasks**: 43
- **Setup Phase**: 3 tasks
- **Foundational Phase**: 6 tasks (required before user stories)
- **User Story 1 (MVP)**: 10 tasks (4 tests, 6 implementation)
- **User Story 2**: 8 tasks (5 tests, 3 implementation)
- **User Story 3**: 9 tasks (4 tests, 5 implementation)
- **Polish Phase**: 7 tasks

**Parallelizable**: ~15 tasks can run concurrently (marked with [P])

**Independent Test Criteria**:
- **US1**: Multiple config instances with zero mutation
- **US2**: Scope entry/exit with cleanup; nested scopes; exceptions handled
- **US3**: Providers work with env mappings; concurrent usage; no fallback to os.environ

**Success Criteria Met**:
- SC-001: ✅ Config loading produces zero mutations to os.environ
- SC-002: ✅ Multiple instances maintain isolated environments
- SC-003: ✅ Repeated invocations (10+) leave os.environ unchanged
- SC-004: ✅ All providers accept env mappings
- SC-005: ✅ Code coverage ≥ 90% for new environment module
- SC-006: ✅ Integration tests with 3+ concurrent config instances

