# Quickstart: Scoped Environment Resolution

**Purpose**: Quick reference for using and migrating to the new environment isolation API

**Created**: 2026-06-22

## Overview

The refactoring replaces global `os.environ` mutation with:
1. **Immutable environment mappings** from config loading
2. **Scoped context managers** for safe environment access
3. **Provider constructors** that accept environment mappings

This enables repeated harness usage in one process without environmental side effects.

---

## Using the New API

### Pattern 1: Read-Only Environment Mapping

**Simple lookup** (no context manager needed):

```python
from evaluator_harness.config import ConfigLoader

loader = ConfigLoader()
env = loader.resolve_environment()

# Lookup values (safe, no side effects)
langfuse_url = env.get('LANGFUSE_BASE_URL')
api_key = env.get('OPENAI_API_KEY')

# Cannot mutate (raises TypeError)
# env['NEW_KEY'] = 'value'  # ❌ TypeError
```

### Pattern 2: Scoped Environment Access

**Enter/exit scope** (context manager):

```python
from evaluator_harness.config import ConfigLoader

loader = ConfigLoader()

with loader.environment_scope() as env:
    # Environment values available here
    langfuse_url = env['LANGFUSE_BASE_URL']
    
    # Pass to providers
    my_client = MyProvider(env_mapping=env)
    result = my_client.process(...)
    
# Scope exited, cleanup complete
```

### Pattern 3: Legacy Client Support

**Temporarily inject into os.environ** (for clients that require it):

```python
from evaluator_harness.config import ConfigLoader

loader = ConfigLoader()

with loader.environment_scope(apply_to_os_environ=True) as env:
    # Values are temporarily in os.environ
    from langfuse import Langfuse
    
    langfuse = Langfuse()  # Reads from os.environ
    langfuse.trace(...)
    
# os.environ restored to original state
```

### Pattern 4: Nested Scopes

**Multiple independent environments** (for testing or multi-project harness):

```python
from evaluator_harness.config import ConfigLoader

loader_a = ConfigLoader('project_a')
loader_b = ConfigLoader('project_b')

with loader_a.environment_scope() as env_a:
    client_a = MyProvider(env_mapping=env_a)
    
    with loader_b.environment_scope() as env_b:
        client_b = MyProvider(env_mapping=env_b)
        
        # Both clients use independent environments
        result_a = client_a.process(...)  # Uses env_a
        result_b = client_b.process(...)  # Uses env_b
    
    # env_b scope exited, env_a still active
    result_a2 = client_a.process(...)  # Still uses env_a
```

---

## Migration Guide

### Step 1: Update Provider Constructors

**Before** (reads `os.environ` directly):

```python
class MyProvider:
    def __init__(self):
        self.api_key = os.environ.get('MY_API_KEY')
        self.host = os.environ.get('MY_HOST', 'https://api.example.com')
```

**After** (accepts optional env mapping):

```python
class MyProvider:
    def __init__(self, env_mapping=None):
        if env_mapping is None:
            env_mapping = os.environ  # Fallback for legacy callers
        
        self.api_key = env_mapping.get('MY_API_KEY')
        self.host = env_mapping.get('MY_HOST', 'https://api.example.com')
```

### Step 2: Update Harness Entry Points

**Before** (sets global state):

```python
def run_experiment(project_name):
    loader = ConfigLoader(project_name)
    # loader mutates os.environ here
    
    client = MyProvider()  # Reads from os.environ (has side effects)
    results = client.run(...)
    return results
```

**After** (uses scoped environment):

```python
def run_experiment(project_name):
    loader = ConfigLoader(project_name)
    
    with loader.environment_scope() as env:
        client = MyProvider(env_mapping=env)  # No global mutation
        results = client.run(...)
        return results
```

### Step 3: Update Tests

**Before** (had to mock/restore os.environ):

```python
def test_run_experiment():
    original_environ = os.environ.copy()
    
    try:
        result = run_experiment('test_project')
        assert result is not None
    finally:
        os.environ.clear()
        os.environ.update(original_environ)  # Manual restore
```

**After** (automatic cleanup):

```python
def test_run_experiment():
    # No setup/teardown needed
    result = run_experiment('test_project')
    assert result is not None
    # os.environ was never mutated
```

### Step 4: Test Isolation

**New test pattern** (verify multiple runs are independent):

```python
def test_repeated_invocation_isolation():
    for i in range(10):
        result = run_experiment('test_project')
        # Verify result is consistent each run
        assert result.project_name == 'test_project'
    
    # Verify os.environ was never mutated
    assert os.environ == ORIGINAL_ENVIRON
```

---

## API Reference

### ConfigLoader Methods

```python
class ConfigLoader:
    def resolve_environment(self) -> ResolvedEnvironment:
        """
        Return an immutable mapping of resolved environment variables.
        
        Precedence: shell > project-env > root-env > defaults
        
        Returns:
            ResolvedEnvironment: Immutable dict-like mapping
            
        Raises:
            EnvironmentError: If required variables are missing
        """
    
    def environment_scope(
        self, 
        apply_to_os_environ: bool = False
    ) -> EnvironmentScope:
        """
        Return a context manager for scoped environment access.
        
        Args:
            apply_to_os_environ: If True, temporarily write values to os.environ
                                for legacy clients that require it. Default: False
        
        Returns:
            EnvironmentScope: Context manager
            
        Example:
            with loader.environment_scope() as env:
                client = MyProvider(env_mapping=env)
        """
```

### ResolvedEnvironment Methods

```python
class ResolvedEnvironment:
    def get(self, key: str, default=None) -> str | None:
        """Get environment variable (safe, immutable)"""
    
    def __getitem__(self, key: str) -> str:
        """Get environment variable by key (raises KeyError if missing)"""
    
    def __contains__(self, key: str) -> bool:
        """Check if key is in environment"""
    
    def items(self) -> Iterator[tuple[str, str]]:
        """Iterate over (key, value) pairs"""
    
    def keys(self) -> Iterator[str]:
        """Iterate over keys"""
    
    def values(self) -> Iterator[str]:
        """Iterate over values"""
```

### EnvironmentScope Context Manager

```python
class EnvironmentScope:
    async def __aenter__(self) -> ResolvedEnvironment:
        """Enter scope, return resolved environment"""
    
    async def __aexit__(exc_type, exc_val, exc_tb) -> None:
        """Exit scope, restore os.environ (even on exception)"""
    
    def get(self, key: str, default=None) -> str | None:
        """Convenience method for accessing environment values"""
```

---

## Common Patterns

### Parallel Environment Usage

```python
import concurrent.futures
from evaluator_harness.config import ConfigLoader

def process_project(project_name):
    loader = ConfigLoader(project_name)
    with loader.environment_scope() as env:
        client = MyProvider(env_mapping=env)
        return client.run(...)

# Safe to run in parallel threads
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(process_project, f'project_{i}')
        for i in range(10)
    ]
    results = [f.result() for f in futures]
```

### Logging Environment State (for debugging)

```python
from evaluator_harness.config import ConfigLoader

loader = ConfigLoader('my_project')
env = loader.resolve_environment()

print("Resolved environment variables:")
for key in sorted(env.keys()):
    if 'SECRET' not in key and 'KEY' not in key:
        print(f"  {key}={env[key]}")
    else:
        print(f"  {key}=***REDACTED***")
```

### Fallback to Shell Environment (upgrade path)

```python
from evaluator_harness.config import ConfigLoader

loader = ConfigLoader('my_project')
env = loader.resolve_environment()

# Fallback to shell if not in resolved environment
api_key = env.get('API_KEY') or os.environ.get('API_KEY')
```

---

## FAQ

**Q: What if a client requires os.environ mutation?**

A: Use `apply_to_os_environ=True` in the context manager:
```python
with loader.environment_scope(apply_to_os_environ=True) as env:
    legacy_client = SomeThirdPartyLib()  # Reads os.environ
```

**Q: Can I create multiple loaders for different projects in one process?**

A: Yes! Scopes are independent:
```python
loader_a = ConfigLoader('project_a')
loader_b = ConfigLoader('project_b')

with loader_a.environment_scope() as env_a:
    with loader_b.environment_scope() as env_b:
        # Both safe, isolated, no cross-contamination
```

**Q: Does this work with concurrent/parallel code?**

A: Yes, if each thread/coroutine has its own context manager:
```python
# Each thread gets its own EnvironmentScope
with executor.map(process_with_isolation, projects):
    pass
```

**Q: What about os.environ persistence?**

A: Exit the context manager and os.environ is restored:
```python
original = os.environ.copy()

with loader.environment_scope() as env:
    # Potentially different values
    pass

assert os.environ == original  # Guaranteed
```

**Q: How do I test that my code doesn't mutate os.environ?**

A: Check `os.environ` before and after:
```python
original_environ = os.environ.copy()

result = run_experiment('test_project')

assert os.environ == original_environ, "os.environ was mutated!"
```

---

## Troubleshooting

### "ResolvedEnvironment does not support item assignment"

**Cause**: Attempting to mutate the immutable environment mapping

**Fix**: Don't modify the returned environment
```python
# ❌ Wrong
env['NEW_KEY'] = 'value'

# ✅ Right
new_value = env.get('NEW_KEY', 'default')
```

### "KeyError: 'REQUIRED_VAR'"

**Cause**: Required environment variable not found in any layer

**Fix**: Add the variable to `.env` or `.env.<project>`, or handle missing gracefully
```python
# ❌ Crashes
value = env['REQUIRED_VAR']

# ✅ Safe
value = env.get('REQUIRED_VAR', 'default')
```

### "os.environ was not restored after scope exit"

**Cause**: Likely a bug; context manager should always restore

**Fix**: File a bug report with the scenario; ensure using `with` statement correctly
```python
# ❌ Wrong (doesn't use with)
scope = loader.environment_scope()
scope.__enter__()
# ❌ Never restores!

# ✅ Right
with loader.environment_scope() as env:
    # Guaranteed to restore on exit
    pass
```

