# Research: Project-Specific Environment Files

## Decision: Preserve Shell Environment As Highest Priority

**Rationale**: Shell-provided values are explicit operator or automation
overrides. Preserving them avoids surprising CI jobs, one-off local debugging,
and secret-manager-injected values. Project-specific env files still override
root `.env` values loaded by the harness.

**Alternatives considered**:

- Let `.env.<project>` override shell values. Rejected because it makes local
  files unexpectedly stronger than explicit process environment values.
- Let root `.env` override project-specific values. Rejected because it defeats
  the feature's purpose.

## Decision: Derive Project Env File From Project Name

**Rationale**: The spec requires `.env.<project-name>`, and project names are
already slug-safe enough for examples such as `.env.gso` and
`.env.dfe-general-public`. This avoids adding another project config field that
could drift from project identity.

**Alternatives considered**:

- Add an `env_file` field to project YAML. Rejected for this feature because it
  would put secret-file routing in project config and is unnecessary for the
  requested convention.
- Derive from scenario identity for scenario projects. Rejected because the
  active project identity is the command's configured project and existing
  bindings/configs use project identity as the primary scope.

## Decision: Load Root First, Then Project File With File-Level Override

**Rationale**: Existing env loading uses set-if-missing behavior. To satisfy the
required precedence while preserving shell overrides, root `.env` should fill
missing values first, then `.env.<project>` should replace only values that came
from root/local env files and not values that were already present in the shell
before loading.

**Alternatives considered**:

- Reuse the existing root loader twice. Rejected because set-if-missing would
  prevent `.env.<project>` from overriding root `.env`.
- Clear and reload environment values for each command. Rejected because it
  risks deleting legitimate process state and is brittle in tests.

## Decision: Apply To Project-Scoped Commands Only

**Rationale**: Project-specific file selection requires knowing the active
project name. Commands without a project path should keep the current root
`.env` behavior.

**Alternatives considered**:

- Globally discover all `.env.*` files. Rejected because it is ambiguous and
  could leak settings between unrelated projects.
- Require users to pass an env-file option. Rejected for this feature because
  the requested behavior is automatic by project name.

## Decision: Keep Missing Project Env File Non-Fatal

**Rationale**: Existing projects should continue to work with only root `.env`.
Required variable validation should still occur where credentials are consumed.

**Alternatives considered**:

- Fail when `.env.<project>` is absent. Rejected because it would break
  existing projects and make project-specific files mandatory.
