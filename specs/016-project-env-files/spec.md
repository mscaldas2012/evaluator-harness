# Feature Specification: Project-Specific Environment Files

**Feature Branch**: `016-project-env-files`

**Created**: 2026-06-09

**Status**: Draft

**Input**: User description: "lets add a feature that a project run tries to load .env.<project> as well as .env (root). .env.<Project> should supercede the root, i.e,., if the same key is defined on both, the more specific .env.<project> wins. the idea is common keys reside in root .env, while project specific keys resides in .env.<project>"

## Clarifications

### Session 2026-06-09

- Q: What precedence should apply when shell environment, root `.env`, and `.env.<project>` define the same key? -> A: Shell environment > `.env.<project>` > root `.env`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Use Project-Specific Credentials (Priority: P1)

An evaluation user can keep common credentials and settings in the root `.env`
file while placing project-specific provider, Langfuse, or queue settings in a
project-specific environment file. When the project runs, the project-specific
values take precedence over root defaults.

**Why this priority**: Users need to run multiple evaluation projects from the
same repository without repeatedly editing one shared `.env` file or risking
credential collisions between projects.

**Independent Test**: Can be fully tested by defining the same environment key
in both the root environment file and the active project's environment file,
running any project command that reads credentials, and confirming the
project-specific value is used.

**Acceptance Scenarios**:

1. **Given** root `.env` defines a shared key and `.env.gso` defines the same
   key with a different value, **When** the `gso` project is validated or run,
   **Then** the project uses the value from `.env.gso`.
2. **Given** root `.env` defines a shared key that `.env.gso` does not define,
   **When** the `gso` project is validated or run, **Then** the project uses the
   value from root `.env`.
3. **Given** `.env.gso` defines a key that does not exist in root `.env`,
   **When** the `gso` project is validated or run, **Then** the key is available
   to that project command.

---

### User Story 2 - Keep Existing Projects Working (Priority: P2)

An existing evaluation project can continue using only the root `.env` file
when no project-specific environment file exists.

**Why this priority**: The feature must be safe for existing projects and
automation that already rely on the current root `.env` behavior.

**Independent Test**: Can be tested by running an existing project that has no
matching project-specific environment file and confirming it resolves the same
environment values as before.

**Acceptance Scenarios**:

1. **Given** a project has no `.env.<project>` file, **When** the project is
   validated or run, **Then** the command succeeds or fails exactly as it would
   with only root `.env`.
2. **Given** a user has already set a value in the shell environment, **When**
   root and project-specific environment files also contain that key, **Then**
   the command preserves the user's shell-provided value.

---

### User Story 3 - Make Environment Source Predictable (Priority: P3)

An evaluation maintainer can understand which environment files are considered
for a project and can diagnose missing credentials without exposing secret
values.

**Why this priority**: Multiple environment files improve usability only if the
loading order and missing-file behavior are predictable and safe.

**Independent Test**: Can be tested by running a project command with present,
missing, and partially defined environment files and confirming the command
reports missing variable names without printing secret values.

**Acceptance Scenarios**:

1. **Given** the active project is `dfe-general-public`, **When** a project
   command starts, **Then** `.env` and `.env.dfe-general-public` are the
   expected environment file names.
2. **Given** a project-specific environment file is missing, **When** a project
   command starts, **Then** the missing file is ignored and root `.env` remains
   the fallback.
3. **Given** required variables are unavailable after all applicable environment
   files are considered, **When** the command fails, **Then** the error names the
   missing variables without exposing values from any environment file.

### Edge Cases

- Root `.env` and `.env.<project>` define the same key with different values.
- A shell environment variable is already set before the command starts.
- The project-specific environment file is absent.
- The project-specific environment file exists but is empty.
- The project-specific environment file contains comments, blank lines, quoted
  values, or malformed lines.
- A project name contains hyphens or underscores, such as `dfe-general-public`.
- A user runs multiple project commands in separate processes with different
  project-specific environment files.
- A project command loads configuration before project identity is known.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST use the active project identity to determine the
  project-specific environment file name. Project configuration MUST continue
  to store environment variable names rather than secret values.
- **Dataset**: Feature MUST NOT change dataset formats, dataset loading, or
  dataset sync behavior.
- **Langfuse Logging**: Feature MUST NOT log secret values from root or
  project-specific environment files. Existing trace, observation, score, run,
  evaluator, baseline, and comparison metadata behavior remains unchanged.
- **Prompt and Evaluator Versioning**: Feature MUST NOT change how prompt
  versions or evaluator versions are tracked.
- **Baseline**: Feature MUST preserve baseline creation, lookup, reuse, and
  candidate comparison behavior while allowing baseline provider credentials to
  come from project-specific environment files.
- **Human Review**: Feature MUST preserve Human Annotation Queue behavior while
  allowing queue and Langfuse settings to come from project-specific
  environment files.

### Functional Requirements

- **FR-001**: System MUST attempt to load the root `.env` file for project
  commands that currently support environment-file loading.
- **FR-002**: System MUST attempt to load a project-specific environment file
  named `.env.<project-name>` for the active project.
- **FR-003**: Values from `.env.<project-name>` MUST override values loaded from
  root `.env` when both files define the same key.
- **FR-004**: Values already present in the shell environment before the command
  starts MUST take precedence over both project-specific and root environment
  file values, producing the precedence order: shell environment,
  `.env.<project-name>`, then root `.env`.
- **FR-005**: Missing project-specific environment files MUST be treated as
  optional and MUST NOT fail commands by themselves.
- **FR-006**: The project-specific file name MUST be derived from the configured
  project name exactly as used by the harness, including hyphens and other
  slug-safe characters.
- **FR-007**: The feature MUST apply consistently to validate, sync, setup,
  run, review, and export commands that load project configuration.
- **FR-008**: Non-project commands or commands that cannot determine an active
  project MUST preserve existing root `.env` behavior.
- **FR-009**: Environment-file parsing MUST continue to ignore comments, blank
  lines, malformed lines, and invalid variable names.
- **FR-010**: Command output and errors MUST report missing variable names when
  credentials are unavailable, but MUST NOT print secret values.
- **FR-011**: The feature MUST allow common keys such as shared Langfuse host or
  shared tenant settings to remain in root `.env` while project-specific
  provider keys, API keys, endpoints, queue IDs, or project-specific Langfuse
  settings reside in `.env.<project-name>`.
- **FR-012**: Documentation or command guidance MUST explain the precedence
  order: shell environment, project-specific environment file, then root
  environment file.

### Key Entities *(include if feature involves data)*

- **Root Environment File**: The repository-level environment file containing
  common non-committed settings shared by multiple projects.
- **Project Environment File**: The non-committed environment file named for one
  project that contains settings specific to that project.
- **Environment Value Resolution**: The effective value chosen for each
  environment key after shell, project-specific, and root sources are considered.
- **Active Project Identity**: The configured project name used to derive the
  project-specific environment file name.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can switch between two projects with different provider
  credentials without editing root `.env`.
- **SC-002**: 100% of tested duplicate keys in root and project-specific
  environment files resolve to the project-specific value when no shell value is
  pre-set.
- **SC-003**: 100% of tested pre-set shell variables remain unchanged after
  root and project-specific environment files are considered.
- **SC-004**: Existing projects without project-specific environment files keep
  their current command behavior.
- **SC-005**: Missing credential failures identify missing variable names in
  100% of tested cases without printing secret values.

## Assumptions

- Project-specific environment files are local secret-bearing artifacts and are
  not committed to source control.
- Project names are already slug-safe enough to use in file names, such as
  `.env.gso` and `.env.dfe-general-public`.
- The root `.env` remains the place for common settings shared across projects.
- Shell-provided environment variables remain the highest-priority source so
  automation can override local files explicitly.
- This feature does not add encrypted secret management or remote secret-store
  integration.
