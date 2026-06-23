"""
Environment abstraction module for scoped environment resolution.

This module provides immutable environment mapping and context management
to eliminate global os.environ mutation while supporting isolated,
repeated harness usage within a single process.

Core Classes:
- EnvironmentResolver: Stateless utility for environment variable resolution
- ResolvedEnvironment: Immutable, read-only mapping of resolved variables
- EnvironmentScope: Context manager for scoped environment access

Usage:
    # Simple read-only access
    env = config.resolve_environment()
    api_key = env.get('API_KEY')
    
    # Scoped access with automatic cleanup
    with config.environment_scope() as env:
        client = MyProvider(env_mapping=env)
        result = client.run(...)
    
    # Legacy client support (temporary os.environ injection)
    with config.environment_scope(apply_to_os_environ=True) as env:
        legacy_client = OldAPI()  # Reads from os.environ
"""

from types import MappingProxyType
from collections.abc import Mapping, Iterator
from typing import Dict, Optional, Tuple
import os
import re
from contextlib import contextmanager


class EnvironmentResolver:
    """
    Stateless utility for resolving environment variables with layering precedence.
    
    Resolution precedence (highest to lowest):
    1. Shell environment (pre-existing os.environ values)
    2. Project-specific .env file values
    3. Root .env file values (set-if-missing)
    4. Defaults (if provided)
    
    No side effects: Does not mutate os.environ.
    """
    
    # Valid environment variable name pattern
    ENV_VAR_PATTERN = re.compile(r'^[A-Z_][A-Z0-9_]*$')
    
    @staticmethod
    def parse_env_file(path: str) -> Dict[str, str]:
        """
        Parse a KEY=VALUE environment file.
        
        - Skips comments (lines starting with #)
        - Skips blank lines
        - Validates variable names
        - Returns dict of parsed variables
        
        Args:
            path: Path to .env file
            
        Returns:
            Dict of parsed environment variables
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If variable names are invalid
        """
        result = {}
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Environment file not found: {path}")
        
        with open(path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                # Strip whitespace
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE
                if '=' not in line:
                    raise ValueError(f"Invalid env line at {path}:{line_num}: {line}")
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Validate variable name
                if not EnvironmentResolver.ENV_VAR_PATTERN.match(key):
                    raise ValueError(f"Invalid env var name at {path}:{line_num}: {key}")
                
                result[key] = value
        
        return result
    
    @staticmethod
    def resolve(
        root_vars: Dict[str, str],
        project_vars: Dict[str, str],
        shell_vars: Dict[str, str],
        defaults: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Resolve environment variables with precedence: shell > project > root > defaults.
        
        - Shell environment always wins (pre-existing os.environ values)
        - Project file can override root file values only (not shell)
        - Root file uses set-if-missing (only fills gaps)
        - Defaults are lowest priority
        
        Args:
            root_vars: Variables from root .env file
            project_vars: Variables from project .env file
            shell_vars: Variables from pre-existing os.environ
            defaults: Optional default values
            
        Returns:
            Resolved dict with precedence applied
        """
        result = {}
        
        # Start with defaults (lowest priority)
        if defaults:
            result.update(defaults)
        
        # Add root vars (set-if-missing pattern)
        for key, value in root_vars.items():
            if key not in result:
                result[key] = value
        
        # Add project vars (can override root, but not shell)
        for key, value in project_vars.items():
            if key not in shell_vars:
                result[key] = value
        
        # Add shell vars (highest priority - never override)
        result.update(shell_vars)
        
        return result
    
    @staticmethod
    def load_with_precedence(
        root_file: Optional[str],
        project_file: Optional[str],
        defaults: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Load and merge environment files with shell environment.
        
        Args:
            root_file: Path to root .env file (or None)
            project_file: Path to project .env file (or None)
            defaults: Optional default values
            
        Returns:
            Resolved environment dict
        """
        root_vars = EnvironmentResolver.parse_env_file(root_file) if root_file else {}
        project_vars = EnvironmentResolver.parse_env_file(project_file) if project_file else {}
        shell_vars = dict(os.environ)
        
        return EnvironmentResolver.resolve(root_vars, project_vars, shell_vars, defaults)


class ResolvedEnvironment(Mapping[str, str]):
    """
    Immutable, read-only mapping of resolved environment variables.
    
    Provides dict-like interface (get, __getitem__, items, keys, values, __contains__)
    but prevents any mutations. Uses MappingProxyType for true immutability.
    """
    
    def __init__(self, data: Dict[str, str]):
        """
        Initialize ResolvedEnvironment.
        
        Args:
            data: Environment variables dict (will be made immutable)
        """
        # Create a copy to prevent external mutations
        self._data = dict(data)
        # Wrap in MappingProxyType for true read-only access
        self._proxy = MappingProxyType(self._data)
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get value by key with optional default."""
        return self._proxy.get(key, default)
    
    def __getitem__(self, key: str) -> str:
        """Get value by key (raises KeyError if missing)."""
        return self._proxy[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._proxy

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys."""
        return iter(self._proxy)
    
    def items(self) -> Iterator[Tuple[str, str]]:
        """Iterate over (key, value) pairs."""
        return self._proxy.items()
    
    def keys(self) -> Iterator[str]:
        """Iterate over keys."""
        return self._proxy.keys()
    
    def values(self) -> Iterator[str]:
        """Iterate over values."""
        return self._proxy.values()
    
    def __len__(self) -> int:
        """Get number of variables."""
        return len(self._proxy)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ResolvedEnvironment({dict(self._proxy)})"


class EnvironmentScope:
    """
    Context manager for scoped environment access with automatic cleanup.
    
    Provides safe, isolated environment access within a defined scope.
    Optionally temporarily injects values into os.environ for legacy clients.
    Always restores original os.environ state on exit (even on exception).
    
    Supports nesting: each scope maintains independent snapshots.
    """
    
    def __init__(self, resolved_env: ResolvedEnvironment, apply_to_os_environ: bool = False):
        """
        Initialize EnvironmentScope.
        
        Args:
            resolved_env: ResolvedEnvironment instance to manage
            apply_to_os_environ: If True, temporarily inject values into os.environ
                               Default: False (safe scoped access without mutations)
        """
        self.resolved_env = resolved_env
        self.apply_to_os_environ = apply_to_os_environ
        self._original_environ: Optional[Dict[str, str]] = None
        self._modified_keys: set = set()
    
    def __enter__(self) -> ResolvedEnvironment:
        """
        Enter context: return ResolvedEnvironment.
        
        If apply_to_os_environ=True, snapshot os.environ and prepare to inject values.
        """
        if self.apply_to_os_environ:
            # Snapshot original os.environ
            self._original_environ = dict(os.environ)
            # Inject resolved values into os.environ
            for key, value in self.resolved_env.items():
                os.environ[key] = value
                self._modified_keys.add(key)
        
        return self.resolved_env
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit context: restore original os.environ.
        
        Always restores state, even if exception occurred in body.
        """
        if self.apply_to_os_environ and self._original_environ is not None:
            # Restore original os.environ
            # Remove keys we added
            for key in self._modified_keys:
                if key not in self._original_environ:
                    del os.environ[key]
            
            # Restore original values
            for key, value in self._original_environ.items():
                os.environ[key] = value
            
            # Clean up
            self._original_environ = None
            self._modified_keys.clear()
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Convenience method to get value from resolved environment."""
        return self.resolved_env.get(key, default)
    
    def __getitem__(self, key: str) -> str:
        """Convenience method to get value by key."""
        return self.resolved_env[key]
