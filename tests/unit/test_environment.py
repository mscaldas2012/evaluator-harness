"""
Unit tests for environment isolation module.

Tests cover:
- EnvironmentResolver: precedence resolution, file parsing, validation
- ResolvedEnvironment: immutability, dict-like interface, copy-safety
- EnvironmentScope: context management, cleanup, nesting, os.environ handling
"""

import os
import tempfile
from pathlib import Path

import pytest

from evaluator_harness.environment import (
    EnvironmentResolver,
    EnvironmentScope,
    ResolvedEnvironment,
)


class TestEnvironmentResolver:
    """Tests for EnvironmentResolver utility class."""
    
    def test_parse_env_file_basic(self):
        """Test basic .env file parsing with KEY=VALUE pairs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('API_KEY=secret123\n')
            f.write('HOST=localhost\n')
            f.write('PORT=8080\n')
            fname = f.name
        
        try:
            result = EnvironmentResolver.parse_env_file(fname)
            assert result == {
                'API_KEY': 'secret123',
                'HOST': 'localhost',
                'PORT': '8080'
            }
        finally:
            try:
                os.unlink(fname)
            except OSError:
                pass
    
    def test_parse_env_file_with_comments(self):
        """Test .env file parsing skips comments and blank lines."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('# This is a comment\n')
            f.write('API_KEY=secret123\n')
            f.write('\n')
            f.write('# Another comment\n')
            f.write('HOST=localhost\n')
            fname = f.name
        
        try:
            result = EnvironmentResolver.parse_env_file(fname)
            assert result == {'API_KEY': 'secret123', 'HOST': 'localhost'}
        finally:
            try:
                os.unlink(fname)
            except OSError:
                pass
    
    def test_parse_env_file_invalid_name(self):
        """Test .env file parsing rejects invalid variable names."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write('invalid-name=value\n')
            fname = f.name
        
        try:
            with pytest.raises(ValueError):
                EnvironmentResolver.parse_env_file(fname)
        finally:
            try:
                os.unlink(fname)
            except OSError:
                pass
    
    def test_parse_env_file_missing(self):
        """Test .env file parsing raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            EnvironmentResolver.parse_env_file('/nonexistent/file.env')
    
    def test_resolve_precedence_shell_wins(self):
        """Test that shell environment (pre-existing values) wins all precedence."""
        shell_vars = {'API_KEY': 'shell_value', 'HOST': 'shell_host'}
        root_vars = {'API_KEY': 'root_value', 'PORT': '8080'}
        project_vars = {'API_KEY': 'project_value', 'HOST': 'project_host'}
        
        result = EnvironmentResolver.resolve(root_vars, project_vars, shell_vars)
        
        # Shell values should win
        assert result['API_KEY'] == 'shell_value'
        assert result['HOST'] == 'shell_host'
        # Root/project only values
        assert result['PORT'] == '8080'
    
    def test_resolve_precedence_project_over_root(self):
        """Test that project file overrides root file (but not shell)."""
        shell_vars = {}
        root_vars = {'API_KEY': 'root_value', 'PORT': '8080'}
        project_vars = {'API_KEY': 'project_value', 'DEBUG': 'true'}
        
        result = EnvironmentResolver.resolve(root_vars, project_vars, shell_vars)
        
        # Project overrides root
        assert result['API_KEY'] == 'project_value'
        # Root-only values preserved
        assert result['PORT'] == '8080'
        # Project additions included
        assert result['DEBUG'] == 'true'
    
    def test_resolve_with_defaults(self):
        """Test resolution with default values."""
        shell_vars = {}
        root_vars = {}
        project_vars = {}
        defaults = {'API_KEY': 'default_value', 'HOST': 'localhost'}
        
        result = EnvironmentResolver.resolve(
            root_vars, project_vars, shell_vars, defaults
        )
        
        assert result['API_KEY'] == 'default_value'
        assert result['HOST'] == 'localhost'
    
    def test_load_with_precedence(self, tmp_path: Path):
        """Test load_with_precedence with actual files."""
        root_file = tmp_path / '.env'
        root_file.write_text('API_KEY=root_key\nPORT=8080\n', encoding='utf-8')

        project_file = tmp_path / '.env.project'
        project_file.write_text('API_KEY=project_key\nDEBUG=true\n', encoding='utf-8')

        # Mock shell environment
        original_environ = os.environ.copy()
        try:
            os.environ.clear()
            os.environ['SHELL_VAR'] = 'shell_value'

            result = EnvironmentResolver.load_with_precedence(root_file, project_file)

            # Verify precedence
            assert result['API_KEY'] == 'project_key'  # Project wins over root
            assert result['PORT'] == '8080'  # Root-only value
            assert result['DEBUG'] == 'true'  # Project-only value
            assert result['SHELL_VAR'] == 'shell_value'  # Shell value
        finally:
            os.environ.clear()
            os.environ.update(original_environ)


class TestResolvedEnvironment:
    """Tests for ResolvedEnvironment immutable mapping."""
    
    def test_immutability_item_assignment(self):
        """Test that item assignment raises TypeError."""
        env = ResolvedEnvironment({'API_KEY': 'value'})
        
        with pytest.raises(TypeError):
            env['API_KEY'] = 'new_value'
    
    def test_immutability_del(self):
        """Test that deleting items raises TypeError."""
        env = ResolvedEnvironment({'API_KEY': 'value'})
        
        with pytest.raises(TypeError):
            del env['API_KEY']
    
    def test_immutability_pop(self):
        """Test that pop() raises AttributeError (MappingProxyType doesn't have pop)."""
        env = ResolvedEnvironment({'API_KEY': 'value'})
        
        with pytest.raises(AttributeError):
            env.pop('API_KEY')
    
    def test_immutability_clear(self):
        """Test that clear() raises AttributeError."""
        env = ResolvedEnvironment({'API_KEY': 'value'})
        
        with pytest.raises(AttributeError):
            env.clear()
    
    def test_get_existing_key(self):
        """Test get() returns value for existing key."""
        env = ResolvedEnvironment({'API_KEY': 'secret123'})
        
        assert env.get('API_KEY') == 'secret123'
    
    def test_get_missing_key_with_default(self):
        """Test get() returns default for missing key."""
        env = ResolvedEnvironment({'API_KEY': 'secret123'})
        
        assert env.get('MISSING_KEY', 'default') == 'default'
    
    def test_getitem_existing_key(self):
        """Test __getitem__ returns value for existing key."""
        env = ResolvedEnvironment({'API_KEY': 'secret123'})
        
        assert env['API_KEY'] == 'secret123'
    
    def test_getitem_missing_key(self):
        """Test __getitem__ raises KeyError for missing key."""
        env = ResolvedEnvironment({'API_KEY': 'secret123'})
        
        with pytest.raises(KeyError):
            _ = env['MISSING_KEY']
    
    def test_contains(self):
        """Test __contains__ checks for key presence."""
        env = ResolvedEnvironment({'API_KEY': 'secret123'})
        
        assert 'API_KEY' in env
        assert 'MISSING_KEY' not in env
    
    def test_items_iteration(self):
        """Test items() iteration works."""
        data = {'API_KEY': 'secret', 'HOST': 'localhost'}
        env = ResolvedEnvironment(data)
        
        items = dict(env.items())
        assert items == data
    
    def test_keys_iteration(self):
        """Test keys() iteration works."""
        data = {'API_KEY': 'secret', 'HOST': 'localhost'}
        env = ResolvedEnvironment(data)
        
        keys = list(env.keys())
        assert set(keys) == {'API_KEY', 'HOST'}
    
    def test_values_iteration(self):
        """Test values() iteration works."""
        data = {'API_KEY': 'secret', 'HOST': 'localhost'}
        env = ResolvedEnvironment(data)
        
        values = list(env.values())
        assert set(values) == {'secret', 'localhost'}
    
    def test_copy_safety(self):
        """Test that ResolvedEnvironment is copy-safe (no shared internal references)."""
        original_data = {'API_KEY': 'secret'}
        env = ResolvedEnvironment(original_data)
        
        # Mutate original dict
        original_data['API_KEY'] = 'new_value'
        original_data['NEW_KEY'] = 'new'
        
        # ResolvedEnvironment should be unchanged
        assert env['API_KEY'] == 'secret'
        assert 'NEW_KEY' not in env


class TestEnvironmentScope:
    """Tests for EnvironmentScope context manager."""
    
    def test_enter_returns_resolved_environment(self):
        """Test __enter__ returns the ResolvedEnvironment."""
        env_data = ResolvedEnvironment({'API_KEY': 'secret'})
        scope = EnvironmentScope(env_data)
        
        with scope as env:
            assert env is env_data
            assert env['API_KEY'] == 'secret'
    
    def test_exit_without_os_environ_changes(self):
        """Test __exit__ when apply_to_os_environ=False (no changes)."""
        original_environ = dict(os.environ)
        env_data = ResolvedEnvironment({'API_KEY': 'secret'})
        scope = EnvironmentScope(env_data, apply_to_os_environ=False)
        
        with scope:
            # os.environ should not be modified
            pass
        
        # Verify os.environ unchanged
        assert dict(os.environ) == original_environ
    
    def test_exit_restores_os_environ(self):
        """Test __exit__ restores original os.environ when apply_to_os_environ=True."""
        original_environ = dict(os.environ)
        env_data = ResolvedEnvironment({'TEMP_KEY': 'temp_value'})
        scope = EnvironmentScope(env_data, apply_to_os_environ=True)
        
        try:
            with scope:
                # Inside scope, value should be in os.environ
                assert os.environ.get('TEMP_KEY') == 'temp_value'
            
            # After exit, original state should be restored
            assert dict(os.environ) == original_environ
        finally:
            # Ensure cleanup even if test fails
            os.environ.clear()
            os.environ.update(original_environ)
    
    def test_exception_in_scope_still_restores(self):
        """Test that os.environ is restored even if exception raised in scope."""
        original_environ = dict(os.environ)
        env_data = ResolvedEnvironment({'TEMP_KEY': 'temp_value'})
        scope = EnvironmentScope(env_data, apply_to_os_environ=True)
        
        try:
            try:
                with scope:
                    assert os.environ.get('TEMP_KEY') == 'temp_value'
                    raise RuntimeError("Test exception")
            except RuntimeError:
                pass
            
            # Should still restore despite exception
            assert dict(os.environ) == original_environ
        finally:
            os.environ.clear()
            os.environ.update(original_environ)
    
    def test_nested_scopes_independent(self):
        """Test nested scopes maintain independent snapshots."""
        original_environ = dict(os.environ)
        
        env_a = ResolvedEnvironment({'KEY_A': 'value_a'})
        env_b = ResolvedEnvironment({'KEY_B': 'value_b'})
        
        try:
            with EnvironmentScope(env_a, apply_to_os_environ=True):
                assert os.environ.get('KEY_A') == 'value_a'
                
                with EnvironmentScope(env_b, apply_to_os_environ=True):
                    # env_b should be in scope, env_a may be overwritten
                    assert os.environ.get('KEY_B') == 'value_b'
                
                # After exiting inner scope, outer scope values restored
                assert os.environ.get('KEY_A') == 'value_a'
        finally:
            os.environ.clear()
            os.environ.update(original_environ)
    
    def test_scope_get_convenience_method(self):
        """Test that scope.get() provides convenient access."""
        env_data = ResolvedEnvironment({'API_KEY': 'secret'})
        scope = EnvironmentScope(env_data)
        
        assert scope.get('API_KEY') == 'secret'
        assert scope.get('MISSING', 'default') == 'default'
    
    def test_scope_getitem_convenience_method(self):
        """Test that scope['KEY'] provides convenient access."""
        env_data = ResolvedEnvironment({'API_KEY': 'secret'})
        scope = EnvironmentScope(env_data)
        
        assert scope['API_KEY'] == 'secret'
        
        with pytest.raises(KeyError):
            _ = scope['MISSING']
