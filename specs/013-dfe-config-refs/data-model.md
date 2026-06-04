# Data Model: Shared Scenario Config References

## ConfigRefs

Represents optional shared configuration references declared by a project YAML.

Fields:

- `evaluation`: repository-relative or project-file-relative path to one shared
  evaluation configuration file.

Validation rules:

- `evaluation` is optional.
- When present, the referenced file must exist and be readable.
- The reference path must resolve inside the repository workspace.
- The named key must be `evaluation`; arbitrary unnamed includes are not part
  of this feature.

Relationships:

- A `ProjectConfigDocument` may have zero or one `ConfigRefs`.
- `ConfigRefs.evaluation` points to one `SharedEvaluationConfigDocument`.

## SharedEvaluationConfigDocument

Represents the shared evaluation configuration file referenced by one or more
scenario project configs.

Allowed fields:

- `evaluators`
- `judge_setup`
- `human_review`

Disallowed fields:

- `project`
- `dataset`
- `task_prompt`
- `baseline`
- `candidates`
- `config_refs`
- `scenario`

Validation rules:

- At least one evaluator must be present after resolving the effective config.
- Shared config files must not define scenario-owned fields.
- Shared evaluator definitions use the same validation rules as project-local
  evaluator definitions.
- Shared human review and judge setup use the same validation rules as
  single-file project configs.

Relationships:

- A shared evaluation config may be referenced by many scenario project configs.
- A shared evaluation config contributes fields to an `EffectiveProjectConfig`.

## ScenarioIdentity

Represents optional scenario metadata for a project config.

Fields:

- `group`: scenario family or use-case group, such as `dfe`.
- `name`: stable slug-like scenario identifier, such as `general_public`.
- `display_name`: user-facing scenario label, such as `General public`.

Validation rules:

- Scenario identity is optional.
- When scenario identity is present, all fields are required and non-empty.
- Scenario names and groups are project data and must not be hardcoded by the
  harness.

Metadata contract:

- Trace and run metadata include `scenario_group`, `scenario_name`, and
  `scenario_display_name` when scenario identity is present.
- CSV exports include scenario columns when scenario identity is present in
  trace metadata.
- Annotation queue payload `trace_context` includes scenario metadata when
  present.

Relationships:

- A `ProjectConfig` has zero or one `ScenarioIdentity`.
- Scenario identity is copied into metadata, not used to select datasets or
  prompts by itself.

## ScenarioProjectConfig

Represents a normal project config for one scenario.

Fields:

- Existing project-owned fields: `project`, `dataset`, `task_prompt`,
  `baseline`, and `candidates`.
- Optional `scenario`.
- Optional `config_refs.evaluation`.

Validation rules:

- Scenario-owned fields must remain local to the project config.
- If `config_refs.evaluation` supplies `evaluators`, the project config must not
  also define local `evaluators`.
- If `config_refs.evaluation` supplies `judge_setup`, the project config must
  not also define local `judge_setup`.
- If `config_refs.evaluation` supplies `human_review`, the project config must
  not also define local `human_review`.
- Existing single-file project configs without `config_refs` continue to
  validate unchanged.

Relationships:

- A scenario project config resolves to exactly one `EffectiveProjectConfig`.
- Multiple scenario project configs may point to the same
  `SharedEvaluationConfigDocument`.

## EffectiveProjectConfig

Represents the fully resolved project config consumed by all workflows.

Fields:

- All existing `ProjectConfig` fields.
- Optional `scenario`.
- Resolved evaluator, judge setup, and human review fields from either local
  project config or shared evaluation config.

Validation rules:

- Existing `ProjectConfig` validation applies after reference resolution.
- Effective config resolution must be deterministic.
- Config resolution must fail before any Langfuse mutation when references are
  missing, invalid, disallowed, or conflicting.

State transitions:

- `unresolved`: raw YAML loaded from project file.
- `resolved`: shared evaluation fields merged into the project document.
- `validated`: Pydantic validation succeeds and downstream workflows may use
  the config.
- `invalid`: missing, conflicting, or disallowed fields prevent validation.
