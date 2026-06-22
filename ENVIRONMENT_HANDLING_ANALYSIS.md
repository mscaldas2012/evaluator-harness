# Environment Handling Architecture Analysis

## Overview

The EvaluatorHarness uses a **three-tier environment resolution pattern** with project-specific environment file support. Environment variables are loaded from files, layered with precedence rules, and tracked to prevent unintended shell variable overwrites.

---

## 1. How config.py Loads Environment Variables

### Primary Entry Points

| Function | Purpose | Behavior |
|----------|---------|----------|
| `load_env_file(path=".env")` | Loads single root env file | Set-if-missing; does not override shell vars |
| `load_layered_env_files(root_env_file, project_env_file)` | Loads root + project env files | Root first (set-if-missing), then project (can override if managed) |
| `LiveSettings.from_env(env_file, project_env_file, load_file=True)` | Reads Langfuse credentials | Optionally loads files, then reads from `os.environ` |

### File Parsing Logic (`_load_env_file()`)

- **Input**: Path to `.env` file
- **Parsing**:
  - Skips empty lines and comments (`#`)
  - Extracts `KEY=VALUE` pairs
  - Validates keys match pattern `^[A-Z_][A-Z0-9_]*$`
  - Strips quotes and whitespace from values
- **Tracking**: Records all loaded keys and ignored keys in `EnvLoadResult`
- **Non-fatal**: Missing files return empty `EnvLoadResult` (does not raise)

---

## 2. Where os.environ Is Mutated

### Direct Mutations in config.py

**Location**: `_load_env_file()` at line 644-646

```python
if key not in os.environ or (override_managed and not is_shell_value):
    os.environ[key] = value
    _MANAGED_ENV_VALUES[key] = _ManagedEnvValue(value=value, source=source)
    loaded_keys.add(key)
```

**Mutation Rules**:
1. **Shell values are preserved**: If a key exists in `os.environ` AND is not in `_MANAGED_ENV_VALUES`, it's considered a "shell value" and never overwritten
2. **Managed values can be overridden**: If a key was previously loaded from env files (tracked in `_MANAGED_ENV_VALUES`), a new file can override it
3. **override_managed flag controls project precedence**: 
   - Root `.env` uses `override_managed=False` (set-if-missing)
   - Project `.env.<name>` uses `override_managed=True` (can override root values)

### Secondary Mutation

**Location**: `_normalize_langfuse_host_alias()` at line 660

```python
if base_url and not os.getenv("LANGFUSE_HOST"):
    os.environ["LANGFUSE_HOST"] = base_url
```

Sets `LANGFUSE_HOST` from legacy `LANGFUSE_BASE_URL` if present.

### Mutation Tracking

**Global state**: `_MANAGED_ENV_VALUES: dict[str, _ManagedEnvValue]`

Records:
- The value that was loaded
- The source: `"root_env"` or `"project_env"`

This allows distinguishing shell-provided values from file-loaded values.

---

## 3. Current Environment Resolution Pattern

### Precedence Order (Highest to Lowest)

1. **Shell environment** (values in `os.environ` before harness code runs)
2. **Project-specific `.env.<project-name>`** (file-level override)
3. **Root `.env`** (default/fallback)
4. **Missing** (variable not set)

### Layered Loading Process

**Step 1**: Load root `.env`
```python
root_result = _load_env_file(
    ".env",
    override_managed=False,  # Set-if-missing
    source="root_env",
    normalize_alias=False,
)
```

**Step 2**: Load project `.env.<project-name>` (if provided)
```python
if project_env_file is not None:
    project_result = _load_env_file(
        project_env_file,
        override_managed=True,  # Can override root values (but not shell values)
        source="project_env",
        normalize_alias=False,
    )
```

**Step 3**: Normalize Langfuse alias
```python
_normalize_langfuse_host_alias()
```

### Project Env File Naming

Derived from project config name:
```python
project_env_file_path(project_name) -> Path(".env.<project-name>")
```

Examples:
- Project `gso` → `.env.gso`
- Project `dfe-general-public` → `.env.dfe-general-public`

---

## 4. Provider/Client Classes Reading from os.environ

### LiveSettings (Langfuse Credentials)

**File**: `config.py` lines 504-530

```python
class LiveSettings(BaseModel):
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None
    annotation_queue_id: str | None = None

    @classmethod
    def from_env(cls, ...) -> LiveSettings:
        # Optionally loads env files first
        if load_file:
            load_layered_env_files(root_env_file, project_env_file)
        _normalize_langfuse_host_alias()
        
        # Reads from os.environ after loading
        return cls(
            langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            langfuse_host=os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL"),
            annotation_queue_id=os.getenv("LANGFUSE_ANNOTATION_QUEUE_ID"),
        )
```

**Usage**: 
- Instantiated in `DefaultLangfuseGateway.from_env()` 
- Passed to Langfuse SDK client initialization

### OpenAI-Compatible Provider

**File**: `providers/openai_compatible.py` lines 309-377

```python
def _required_env(self, name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeDependencyError(f"Required env var not set: {name}")
    return value
```

**Reads**:
- Azure credential refs (tenant ID, client ID, secret, scope, subscription key, API version, endpoint)
- API key refs (api_key_env, endpoint_env, api_version_env, subscription_key_env)

**Pattern**: Config YAML contains environment **variable names**, not values. Provider resolves them at runtime.

### DefaultLangfuseGateway

**File**: `langfuse_default_gateway.py` lines 178-193

```python
@classmethod
def from_env(cls) -> DefaultLangfuseGateway:
    settings = LiveSettings.from_env()  # Reads from os.environ
    settings.require_langfuse()
    return cls(
        client=Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        ),
        settings=settings,
    )
```

### Annotation Queue Access

**File**: `annotation_queues.py` line 314

```python
queue_id = os.getenv("LANGFUSE_ANNOTATION_QUEUE_ID")
```

### Langfuse Settings Helpers

**File**: `langfuse_settings.py`

```python
def positive_float_env(name: str, *, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    # Parse and validate...
```

Reads:
- `EVALUATOR_HARNESS_LANGFUSE_TRACE_WAIT_SECONDS`
- `EVALUATOR_HARNESS_LANGFUSE_TRACE_POLL_INTERVAL_SECONDS`

### Langfuse Retry Configuration

**File**: `langfuse_retry.py` lines 59, 70

Reads retry settings from environment:
- `EVALUATOR_HARNESS_LANGFUSE_RETRY_*` variables

---

## 5. How Environment Variables Are Currently Layered/Overridden

### Layering Strategy: "Load Root First, Then Project With Managed Override"

**Design Decision** (from spec 016 research):
- Root `.env` fills missing keys (preserves shell environment)
- Project `.env.<name>` replaces only "managed" values (file-loaded, not shell-provided)

### Managed vs Shell Values

**Shell Value Definition**:
```python
is_shell_value = env_value is not None and (
    managed_value is None or managed_value.value != env_value
)
```

A key is a "shell value" if:
1. It exists in `os.environ`, AND
2. Either:
   - Not tracked in `_MANAGED_ENV_VALUES` (never loaded by harness), OR
   - The current value differs from what harness loaded (user changed it)

### Override Behavior

| Stage | File | override_managed | Behavior |
|-------|------|-----------------|----------|
| 1 | Root `.env` | `False` | Set-if-missing. Never override `os.environ` |
| 2 | Project `.env.<name>` | `True` | Override file-loaded values. Never override shell values |

**Result**: Shell environment always wins, project overrides root, root fills gaps.

### Example Resolution

Given:
- Shell: `LANGFUSE_HOST=https://shell.test` (user set before harness)
- Root `.env`: `LANGFUSE_HOST=https://root.test` and `PROJECT_ENDPOINT=https://root-endpoint.test`
- Project `.env.gso`: `PROJECT_ENDPOINT=https://project-endpoint.test`

**Resolution**:
- `LANGFUSE_HOST` → `https://shell.test` (shell wins)
- `PROJECT_ENDPOINT` → `https://project-endpoint.test` (project overrides root)

### Runner Integration

**File**: `runner.py` lines 179-190

```python
def _load_project_config(self, project_path: Path) -> ProjectConfig:
    config = load_project_config(project_path)
    load_layered_env_files(
        root_env_file=".env",
        project_env_file=project_env_file_path(config.project.name),
    )
    if not self._langfuse_gateway_provided and os.getenv("EVALUATOR_HARNESS_LIVE") in {"1", "true", ...}:
        self.langfuse_gateway = build_langfuse_gateway_from_env()
    return config
```

**Sequence**:
1. Load project YAML config
2. Load `.env` + `.env.<project>` (mutates `os.environ`)
3. Build Langfuse gateway (reads from mutated `os.environ`)

---

## Summary Table

| Aspect | Current Implementation |
|--------|------------------------|
| **Loading** | `_load_env_file()` parses KEY=VALUE, validates names, handles missing files gracefully |
| **Mutation** | Direct `os.environ[key] = value` with managed-value tracking |
| **Precedence** | Shell > Project > Root |
| **Providers** | Read from `os.environ` after env files are loaded |
| **Tracking** | `_MANAGED_ENV_VALUES` distinguishes file-loaded from shell values |
| **Layering** | Root set-if-missing; project can override managed values only |
| **Integration** | Runner calls `_load_project_config()` → loads files → builds clients |

---

## Key Architectural Constraints

1. **No destructive reload**: Does not clear/reload `os.environ` between commands
2. **Backward compatible**: Missing project `.env` files are non-fatal
3. **Shell-first design**: Pre-existing shell values are never overwritten
4. **File-level granularity**: Tracks which file sourced each key, not individual values
5. **No config YAML mutation**: Environment files only affect `os.environ`; project YAML stays unchanged
