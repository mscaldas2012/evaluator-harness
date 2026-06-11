# Data Model: Project-Specific Environment Files

## Root Environment File

Represents repository-level environment settings shared by multiple projects.

**Fields**

- `path`: repository-relative path, conventionally `.env`
- `entries`: key/value pairs parsed from valid environment assignment lines
- `source`: `root`

**Validation Rules**

- Missing file is allowed.
- Blank lines and comments are ignored.
- Malformed lines and invalid variable names are ignored.
- Values are not logged.

## Project Environment File

Represents one project's local environment overrides.

**Fields**

- `project_name`: active configured project name
- `path`: `.env.<project_name>`
- `entries`: key/value pairs parsed from valid environment assignment lines
- `source`: `project`

**Validation Rules**

- Missing file is allowed.
- File name is derived from the active project name exactly.
- Same parsing rules as the root environment file.
- Values are not logged.

## Environment Value Resolution

Represents the effective value chosen for each environment key.

**Fields**

- `key`: environment variable name
- `value`: resolved value, never printed in diagnostics
- `source`: one of `shell`, `project_env`, or `root_env`

**Resolution Rules**

1. Values present in the shell environment before harness loading win.
2. Values from `.env.<project_name>` override root `.env` values.
3. Values from root `.env` fill missing keys.
4. Missing required keys are reported by variable name only.

## Active Project Identity

Represents the project whose command is being executed.

**Fields**

- `project_name`: configured project name
- `project_path`: project YAML path supplied to the command

**Relationships**

- Determines the project environment file path.
- Does not change dataset, prompt, evaluator, baseline, or Langfuse metadata
  identity.
