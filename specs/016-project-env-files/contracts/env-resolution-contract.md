# Contract: Project Environment Resolution

## Scope

This contract defines the observable behavior for project-scoped commands that
load environment values from local files.

## Inputs

- Project config path supplied to a project-scoped command.
- Root environment file at `.env`, when present.
- Project environment file at `.env.<project-name>`, when present.
- Shell environment values already present when the command starts.

## Resolution Order

For any environment key, the effective value MUST be resolved in this order:

1. Shell environment value present before harness loading.
2. Value from `.env.<project-name>`.
3. Value from root `.env`.
4. Missing.

## File Naming

Given a project with configured name `gso`, the project environment file is:

```text
.env.gso
```

Given a project with configured name `dfe-general-public`, the project
environment file is:

```text
.env.dfe-general-public
```

## Command Behavior

Project-scoped commands MUST consider both root and project-specific env files
before credentials or optional environment-driven settings are resolved.

Commands without an active project MUST keep existing root `.env` behavior.

## Error Behavior

- Missing project-specific files are ignored.
- Missing required credentials are reported by variable name.
- Secret values from either file are never printed in command output, trace
  metadata, exports, or errors.

## Acceptance Examples

### Project File Overrides Root

Root `.env`:

```text
MODEL_ENDPOINT=https://shared.example
```

Project `.env.gso`:

```text
MODEL_ENDPOINT=https://gso.example
```

Effective value for project `gso`:

```text
MODEL_ENDPOINT=https://gso.example
```

### Shell Overrides Project File

Shell:

```text
MODEL_ENDPOINT=https://shell.example
```

Project `.env.gso`:

```text
MODEL_ENDPOINT=https://gso.example
```

Effective value:

```text
MODEL_ENDPOINT=https://shell.example
```
