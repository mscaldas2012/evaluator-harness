# Feature Specification: Scoped Environment Resolution

**Feature Branch**: `024-scoped-env-resolution`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "Replace global environment mutation with scoped environment resolution"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Config Loader Returns Immutable Environment (Priority: P1)

The config loading system should return an immutable, resolved environment mapping instead of mutating `os.environ`. This allows client code to use resolved values without side effects.

**Why this priority**: Isolation is the foundational requirement. Without this, all other scenarios continue to suffer from global state mutation. This is the core refactoring needed.

**Independent Test**: Can be tested by creating a config instance, verifying that `os.environ` remains unchanged, and that the returned environment mapping contains all expected resolved values. Delivers isolation for a single harness instance.

**Acceptance Scenarios**:

1. **Given** config is loaded with custom env var overrides, **When** queried for a resolved environment, **Then** a new dict/mapping is returned without mutating `os.environ`
2. **Given** config instance A and config instance B with different env overrides, **When** each requests its resolved environment, **Then** each gets independent, non-overlapping values (no cross-contamination)
3. **Given** config is instantiated and closed, **When** checking `os.environ`, **Then** it is identical to the state before config instantiation

---

### User Story 2 - Environment Context Manager for Scoped Access (Priority: P2)

Provide an explicit scoped environment context that allows client code to safely use resolved values within a defined scope, with automatic cleanup.

**Why this priority**: Enables safer patterns for repeated harness usage. Once core isolation (P1) is in place, this provides a developer-friendly API for managing environment scope.

**Independent Test**: Can be tested by entering/exiting a context manager, verifying that environment values are available within scope and cleaned up afterwards. Delivers pattern for safe repeated usage.

**Acceptance Scenarios**:

1. **Given** within an environment context, **When** accessing resolved values, **Then** they are available and correct
2. **Given** exiting the environment context, **When** accessing `os.environ`, **Then** it is restored to pre-context state
3. **Given** nested environment contexts with different settings, **When** each accesses its values, **Then** each scope sees its own independent values

---

### User Story 3 - Provider/Client Construction Uses Scoped Env (Priority: P3)

Provider and client classes should accept the resolved environment mapping in their constructors, eliminating the need to read from `os.environ` directly.

**Why this priority**: Ensures the refactoring is actually used throughout the codebase. Once infrastructure (P1) and API (P2) are in place, this wires them into actual usage.

**Independent Test**: Can be tested by constructing clients with an explicit env mapping and verifying they function correctly without relying on global state.

**Acceptance Scenarios**:

1. **Given** a provider is constructed with an explicit env mapping, **When** initialized, **Then** it uses those values instead of reading from `os.environ`
2. **Given** multiple clients in one process with different env mappings, **When** each operates independently, **Then** no cross-contamination occurs
3. **Given** a client constructed with a scoped env, **When** testing integration with the resolved environment, **Then** all dependent services receive the correct values

---

### Edge Cases

- What happens when required environment variables are missing from the resolved mapping?
- How does the system handle environment variable precedence (overrides vs. defaults) in a scoped context?
- How do we handle cases where third-party libraries or global state readers expect values in `os.environ`?
- What happens if code attempts to modify the returned environment mapping?

## Requirements *(mandatory)*

### Technical Requirements

- **TR-001**: System MUST return a resolved environment mapping from config loading that does not mutate `os.environ`
- **TR-002**: System MUST ensure that each config instance receives an independent environment mapping that does not leak into other instances
- **TR-003**: System MUST provide an explicit context manager or scoped mechanism for managing environment lifecycle
- **TR-004**: System MUST support environment variable layering and override resolution within the scoped context
- **TR-005**: System MUST allow provider and client classes to accept resolved environment mappings in constructors
- **TR-006**: System MUST guarantee that exiting a scoped context restores the original `os.environ` state
- **TR-007**: System MUST handle missing required environment variables gracefully with clear error messages
- **TR-008**: System MUST return immutable or copy-safe environment mappings to prevent accidental mutations

### Key Entities

- **Config Instance**: Represents configuration state and resolved environment for a single harness/run
- **Environment Mapping**: An immutable or copy-safe dict containing resolved environment variables
- **Scoped Context**: A context manager that provides isolated environment access within a defined block

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Config loading produces zero mutations to `os.environ`
- **SC-002**: Multiple config instances in the same process maintain fully isolated environment states with zero cross-contamination
- **SC-003**: Repeated harness invocations in one process (10+ iterations) leave `os.environ` in its original state
- **SC-004**: All provider and client classes accept environment mappings without requiring reads from `os.environ`
- **SC-005**: Code coverage for new scoped environment mechanism is ≥ 90%
- **SC-006**: Integration tests demonstrate isolation with at least 3 concurrent config instances running independently

## Assumptions

- Existing environment variable resolution logic (layering, defaults, overrides) remains correct and functional
- Third-party libraries used by providers/clients do not require direct `os.environ` mutation (or wrappers are acceptable)
- The refactoring does not require changes to the public YAML/config file format
- Performance impact of returning environment mappings is negligible (copying small dictionaries)
- Existing users of config module can adapt to the new API over a transition period (if needed)
- Global environment mutation was introduced for convenience rather than strict necessity
