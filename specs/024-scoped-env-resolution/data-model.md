# Data Model: Scoped Environment Resolution

**Purpose**: Define the data structures and contracts for environment isolation refactoring

**Created**: 2026-06-22

## Entity Overview

### 1. ResolvedEnvironment

**Purpose**: Immutable, read-only mapping of resolved environment variables

**Type**: `types.MappingProxyType` (or equivalent copy-safe dict)

**Responsibility**:
- Hold the final, resolved values after all layering and precedence resolution
- Prevent accidental mutation by client code
- Support lookup by variable name
- Support iteration (for testing and debugging)

**Attributes**:
- Variable name → Variable value (str → str or str → None)
- Immutable (raises TypeError on mutation attempts)
- Copy-safe (no shared references with internal state)

**Example Usage**:
```python
env = config.resolve_environment()
print(env['LANGFUSE_BASE_URL'])    # Lookup: str
for key, value in env.items():     # Iteration: works
    env[key] = 'new_value'         # Mutation: raises TypeError
```

**Relationships**:
- Created by `ConfigLoader.resolve_environment()` 
- Consumed by `EnvironmentScope.bind()` and provider constructors
- Passed to `Provider.__init__(env_mapping=...)`

---

### 2. EnvironmentScope

**Purpose**: Context manager for temporary environment access with automatic cleanup

**Type**: Context manager (`__enter__`, `__exit__`)

**Responsibility**:
- Bind a ResolvedEnvironment for the lifetime of the context
- Optionally temporarily inject values into `os.environ` for legacy support
- Restore original `os.environ` state on exit (even on exception)
- Support nesting (each scope independent)

**Constructor Parameters**:
- `resolved_env: ResolvedEnvironment` — The environment mapping to manage
- `apply_to_os_environ: bool = False` — Whether to temporarily write to os.environ (for legacy clients)

**Attributes**:
- `resolved_env: ResolvedEnvironment` — The current environment mapping
- `_original_environ: dict[str, str]` — Snapshot of os.environ before changes (only if apply_to_os_environ=True)
- `_modified_keys: set[str]` — Keys we added or modified in os.environ (for cleanup)

**Methods**:
- `__enter__() → ResolvedEnvironment` — Enter context, return the resolved environment
- `__exit__(exc_type, exc_val, exc_tb) → None` — Exit context, restore os.environ
- `get(key: str, default=None) → str | None` — Get value from resolved environment
- `__getitem__(key: str) → str` — Get value by key (raises KeyError if missing)

**Example Usage**:
```python
# Pattern 1: Access via context manager
with EnvironmentScope(resolved_env) as env:
    langfuse_url = env['LANGFUSE_BASE_URL']
    client = MyProvider(env_mapping=env)
    # ... use client ...
# Original os.environ restored here

# Pattern 2: Legacy fallback (temporarily mutate os.environ)
with EnvironmentScope(resolved_env, apply_to_os_environ=True):
    gateway = DefaultLangfuseGateway.from_env()  # Reads from os.environ
    # ... use gateway ...
# os.environ restored here
```

**Relationships**:
- Created by `ConfigLoader.environment_scope()`
- Yields `ResolvedEnvironment` on entry
- Used by `run_experiment()` and other harness entry points
- Optionally updates `os.environ` for legacy client support

---

### 3. EnvironmentResolver

**Purpose**: Stateless utility to resolve environment variables with layering precedence

**Type**: Utility class (static methods or module-level functions)

**Responsibility**:
- Implement resolution precedence: shell > project-env > root-env > defaults
- Validate variable names
- Track sources (for debugging)
- Support environment file parsing

**Methods**:
- `resolve(root_vars: dict, project_vars: dict, shell_vars: dict) → dict[str, str]` — Merge with precedence
- `parse_env_file(path: str) → dict[str, str]` — Parse KEY=VALUE file (skip comments, validate)
- `load_with_precedence(root_file, project_file) → dict[str, str]` — Load and merge both files with shell

**Behavior**:
- Shell environment (pre-existing `os.environ` keys) always wins
- Project file can override root file values only (not shell)
- Root file uses set-if-missing (only fills gaps)
- Missing required variables raise clear errors

**Example Usage**:
```python
root_vars = EnvironmentResolver.parse_env_file('.env')
project_vars = EnvironmentResolver.parse_env_file('.env.dfe')
shell_vars = {k: v for k, v in os.environ.items()}
resolved = EnvironmentResolver.resolve(root_vars, project_vars, shell_vars)
```

**Relationships**:
- Used internally by `ConfigLoader` during setup
- Called during `ResolvedEnvironment` creation
- Independent (no state dependencies)

---

### 4. ConfigLoader Updates

**Current Behavior** (to be refactored):
- Mutates `os.environ` directly
- Tracks mutations in global `_MANAGED_ENV_VALUES` dict
- Returns config object only (not environment)

**New Behavior**:
- Never mutates `os.environ`
- Returns immutable `ResolvedEnvironment` via method
- Provides context manager for scoped access
- Exposes `resolve_environment() → ResolvedEnvironment`
- Exposes `environment_scope(apply_to_os_environ=False) → EnvironmentScope`

**Updated Methods**:
```python
class ConfigLoader:
    def resolve_environment(self) -> ResolvedEnvironment:
        """Return immutable mapping of resolved environment vars."""
        
    def environment_scope(self, apply_to_os_environ: bool = False) -> EnvironmentScope:
        """Return context manager for scoped environment access."""
```

---

## State Diagrams

### Environment Lifecycle

```
ConfigLoader created
    ↓
resolve_environment() called
    ↓
ResolvedEnvironment created (merged, layered, immutable)
    ↓
environment_scope() creates EnvironmentScope
    ↓
Enter scope: EnvironmentScope.__enter__() returns ResolvedEnvironment
    ↓
Code uses env (read-only, safe)
    ↓
Exit scope: EnvironmentScope.__exit__() restores os.environ (if modified)
    ↓
ConfigLoader destroyed (no global state left behind)
```

### Nesting Scopes

```
with EnvironmentScope(env_a) as env:    # Snapshot os.environ
    # env_a is active
    value_a = env['KEY']
    
    with EnvironmentScope(env_b) as env:  # Nested snapshot (if apply_to_os_environ=True)
        # env_b is active
        value_b = env['KEY']
    # Restore to env_a's state
    
# Restore to original state
```

---

## Validation Rules

### ResolvedEnvironment Immutability

- Type: `types.MappingProxyType` OR custom immutable wrapper
- Test: Attempt `env['KEY'] = 'new'` should raise `TypeError`
- Test: Attempt `env.pop('KEY')` should raise `TypeError`
- Test: Returned dict is not the same object as internal dict

### Environment Scope Isolation

- Test: Multiple scopes with different envs produce independent values
- Test: Nested scopes maintain independent snapshots
- Test: Exiting scope restores original `os.environ` exactly
- Test: Exception in scope doesn't prevent cleanup

### Precedence Correctness

- Test: Shell value > project file value
- Test: Project file value > root file value
- Test: Root file value > missing (raises or uses default)
- Test: Empty environment files handled gracefully

---

## Dependencies

**Internal**:
- `src/evaluator_harness/config.py` — ConfigLoader (to be refactored)

**Standard Library**:
- `types.MappingProxyType` — For immutable dict view
- `contextlib` — For context manager support (if using decorator)
- `os` — For `os.environ` access
- `dataclasses` (optional) — For structured ResolvedEnvironment if using frozen dataclass

**No external dependencies** (zero new third-party imports)

---

## Testing Strategy

**Unit Tests**:
1. `test_resolved_environment_is_immutable.py` — Verify immutability guarantees
2. `test_environment_scope_isolation.py` — Verify scopes don't contaminate each other
3. `test_environment_resolver_precedence.py` — Verify layering logic
4. `test_environment_scope_cleanup.py` — Verify os.environ restoration

**Integration Tests**:
1. `test_configloader_no_mutation.py` — ConfigLoader never mutates os.environ
2. `test_repeated_invocation_isolation.py` — 10+ repeated calls maintain isolation
3. `test_provider_with_env_mapping.py` — Providers work with passed env mappings
4. `test_nested_scopes.py` — Nested scopes work correctly

**Edge Cases**:
- Missing required environment variables
- Malformed .env files
- Exception raised inside scope
- Empty environment (all missing vars)
- Very large environment (100+ variables)
- Unicode characters in environment values

