# Implementation Plan: Scoped Environment Resolution

**Branch**: `024-scoped-env-resolution` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/024-scoped-env-resolution/spec.md`

## Summary

Replace global environment mutation in `config.py` with scoped environment resolution. The config loader currently mutates `os.environ` and tracks managed values in global state, which leaks project-specific environment behavior across repeated runner calls in a single process. The refactoring will return an immutable resolved environment mapping and provide a scoped context manager for safe environment access within defined blocks. This eliminates cross-process contamination and enables safe repeated harness usage without environmental side effects.

## Technical Context

**Language/Version**: Python 3.11+ (project standard)

**Primary Dependencies**: 
- `src/evaluator_harness/config.py` (current module under refactoring)
- `dataclasses` or `typing.TypedDict` (for immutable environment structure)
- Standard library `contextlib` (for context manager implementation)

**Python Environment Management**: Use `uv sync` and `uv run ...` per project constitution

**Testing**: pytest (existing test framework in place)

**Target Platform**: Local CLI (Python script execution)

**Project Type**: Python library/CLI (thin harness)

**Performance Goals**: Negligible impact; copying small environment dicts is O(n) where n = ~20-50 variables

**Constraints**: Must preserve existing environment resolution logic (shell > project-env > root-env > defaults); no breaking changes to YAML format

**Scale/Scope**: Single config module refactoring; affects ~5-8 provider/client classes that read `os.environ`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ **Langfuse-first**: Feature is internal architecture, not user-facing; Langfuse usage unchanged
- ✅ **Thin harness scope**: Refactoring improves harness design; no new APIs or distributed systems added
- ✅ **Dataset simplicity**: No impact on dataset loading; CSV with `input` column unchanged
- ✅ **Reproducibility metadata**: Environment metadata tracking is preserved and improved (scoped isolation enables clearer tracking)
- ✅ **Baseline-centric workflow**: No impact on baseline or comparison workflows
- ✅ **Minimal local state**: Feature reduces global state by eliminating mutation; Langfuse remains system of record
- ✅ **Human review awareness**: No impact on annotation queues or human review
- ✅ **Local-first execution**: Feature is internal refactoring; `uv run python run_experiment.py` unchanged

**Constitutional Status**: **PASS** — Feature is a pure internal refactoring that strengthens isolation and reduces global state without violating any core principles.

## Project Structure

### Documentation (this feature)

```text
specs/024-scoped-env-resolution/
├── spec.md              # Feature specification ✓
├── plan.md              # This file ✓
├── research.md          # Phase 0 output (none needed)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (none needed - internal refactoring)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

**Modified Module**:
```text
src/evaluator_harness/
├── config.py                    # REFACTOR: Return immutable env, add context manager
├── environment.py               # NEW: Scoped environment abstraction
├── providers/
│   ├── openai_compatible.py    # UPDATE: Accept env mapping in constructor
│   ├── langfuse_gateway.py     # UPDATE: Accept env mapping in constructor
│   └── [other provider classes] # UPDATE: Accept env mapping
└── ...
```

**Test Structure**:
```text
tests/
├── unit/
│   ├── test_config_isolation.py         # NEW: Test zero mutation
│   ├── test_environment_context.py      # NEW: Test context manager
│   └── test_environment_layering.py     # NEW: Test env resolution in scope
├── integration/
│   ├── test_config_with_providers.py    # UPDATE: Test provider usage with env mapping
│   └── test_repeated_harness_usage.py   # NEW: Test 10+ repeated invocations
└── ...
```

**Structure Decision**: Single module refactoring with new `environment.py` abstraction. Providers are updated in-place to accept optional environment mapping parameter. Tests added to cover isolation, context management, and repeated usage scenarios.

## Complexity Tracking

No Constitutional Check violations. Feature is a pure internal refactoring that improves isolation without introducing new dependencies, frameworks, or system complexity.

---

## Phase 0: Research & Resolution

### Unknowns Resolved

No critical unknowns remain. The current environment handling pattern is well-documented:

1. **Environment Resolution Precedence** (Resolved):
   - Shell environment > Project `.env.<project>` > Root `.env` > defaults
   - Root uses `override_managed=False` (set-if-missing)
   - Project uses `override_managed=True` (override file values only)
   - Managed values tracked in `_MANAGED_ENV_VALUES` dict with source

2. **Current os.environ Mutation Scope** (Resolved):
   - Primary mutation in `_load_env_file()` (lines 644-646)
   - Secondary mutation in `_normalize_langfuse_host_alias()` for LANGFUSE_HOST aliasing
   - Tracked state allows cleanup on context exit

3. **Client Dependencies** (Resolved):
   - `LiveSettings` reads `LANGFUSE_*` vars
   - OpenAI-Compatible provider reads credential env var names
   - `DefaultLangfuseGateway.from_env()` uses Langfuse SDK credential loading
   - ~5-8 total client classes with env var dependencies

4. **Immutability Strategy** (Decision Made):
   - Use `types.MappingProxyType` for read-only dict view
   - Or return explicit copy + copy-on-read pattern
   - Validate no mutations occur in tests

---

## Phase 1: Design & Contracts

### 1. Data Model

**See**: [data-model.md](data-model.md)

Key entities:
- `ResolvedEnvironment`: Immutable mapping of resolved environment variables
- `EnvironmentScope`: Context manager for temporary environment access with automatic cleanup
- `EnvironmentResolver`: Stateless function to resolve environment with layering precedence

### 2. Component Contracts

**See**: [contracts/](contracts/)

Since this is an internal refactoring with no external interfaces exposed, contracts focus on:
- **Internal API Contract**: config.py function signatures and return types
- **Provider Interface**: Updated constructor signatures accepting optional env mapping
- **Test Contract**: Isolation guarantees and side-effect assertions

### 3. Quickstart Guide

**See**: [quickstart.md](quickstart.md)

Quick reference for:
- Using the new immutable environment API
- Entering/exiting environment scopes
- Migrating existing code to accept env mappings
- Testing environment isolation

---

## Next Steps

1. ✅ **Phase 0 Complete**: No unknowns remain; all research resolved
2. ⏳ **Phase 1 Execution**: Generate `data-model.md`, `quickstart.md`, and `/contracts/` in detail
3. ⏳ **Update Agent Context**: Point AGENTS.md to this plan file
4. ⏳ **Phase 2** (next command `/speckit-tasks`): Generate task breakdown and dependency graph
