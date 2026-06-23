# Migration Notes: Scoped Environment Resolution

**Feature**: Scoped Environment Resolution
**Branch**: `024-scoped-env-resolution`
**Date**: 2026-06-22

## What Changed

The harness no longer depends on config initialization mutating `os.environ` for its main execution path. Environment values are now resolved into an immutable mapping and threaded through the runner and gateway construction path explicitly.

## Backward-Compatible Behavior

- `load_env_file()` and `load_layered_env_files()` remain available for legacy callers and fixtures that still expect process-global environment mutation.
- `LiveSettings.from_env()` now accepts an optional `env_mapping` argument and can resolve values without touching `os.environ`.
- `DefaultLangfuseGateway.from_env()` now accepts an optional `env_mapping` argument for scoped gateway construction.
- `create_provider()` accepts an optional `env_mapping` argument and forwards it to mapping-aware providers when possible.

## New Preferred Pattern

```python
from evaluator_harness.config import environment_scope, resolve_environment
from evaluator_harness.providers import create_provider

resolved_env = resolve_environment(env_file=".env", project_env_file=".env.my-project")

with environment_scope(env_file=".env", project_env_file=".env.my-project") as env:
    provider = create_provider(model_config, env_mapping=env)
    gateway = DefaultLangfuseGateway.from_env(env_mapping=env)
```

## Legacy Pattern Still Supported

```python
from evaluator_harness.config import load_layered_env_files

load_layered_env_files(
    root_env_file=".env",
    project_env_file=".env.my-project",
)
# Existing code that reads os.environ continues to work here.
```

## Notes for Test Authors

- Prefer assertions against the returned resolved mapping instead of `os.environ`.
- Use scoped environment helpers for any test that needs temporary environment values.
- Keep direct `os.environ` mutation limited to fixtures that intentionally verify legacy behavior.
