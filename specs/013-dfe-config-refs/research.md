# Research: Shared Scenario Config References

## Decision: Use Application-Level `config_refs.evaluation`

Use a harness schema field:

```yaml
config_refs:
  evaluation: configs/shared/dfe_readability.yaml
```

The reference is resolved by the harness config loader. This is intentionally
not treated as a generic YAML include.

**Rationale**: YAML has no standard cross-file include feature, and project
configs should make the harness-specific behavior explicit. A named
`evaluation` reference leaves room for future named references without implying
arbitrary import semantics.

**Alternatives considered**:

- YAML anchors: rejected because anchors are file-local.
- Generic `include`: rejected because it implies YAML-level import behavior and
  hides the harness-specific contract.
- Dedicated `evaluation_config_ref`: rejected because `config_refs` is more
  extensible while still explicit.

## Decision: Resolve To A Normal Effective Project Config

Resolve the shared evaluation reference before constructing the final
`ProjectConfig`. Downstream validation, sync, run, export, evaluator setup, and
review workflows should receive a regular project config with evaluators, judge
setup, and human review populated.

**Rationale**: Existing code expects a complete `ProjectConfig`. Resolving early
keeps changes localized and avoids spreading reference awareness across runner,
Langfuse, export, and annotation queue logic.

**Alternatives considered**:

- Pass unresolved references through runtime workflows: rejected because it
  would widen the implementation surface and make behavior harder to reason
  about.
- Generate project YAML files from templates: rejected because it avoids code
  changes but keeps drift-prone generated artifacts and does not create a
  reusable harness capability.

## Decision: Reject Local/Shared Conflicts

If a scenario project defines local evaluator, judge setup, score, or human
review fields also supplied by `config_refs.evaluation`, validation fails with
a clear conflict message.

**Rationale**: The user goal is to maintain shared evaluation content in one
place. Implicit precedence creates drift and makes it unclear whether a scenario
is actually using the shared evaluation configuration.

**Alternatives considered**:

- Local overrides win: rejected because it permits silent drift.
- Shared config wins: rejected because it hides local configuration mistakes.
- Explicit override fields: deferred until there is a concrete use case.

## Decision: Limit Shared Config Scope To Evaluation And Review

The shared evaluation config may provide only:

- `evaluators`
- `judge_setup`
- `human_review`

Score definitions are included through each evaluator's `score` contract.
Scenario-owned fields such as project identity, dataset, task prompt, baseline,
and candidates are invalid in shared evaluation files.

**Rationale**: Scenarios vary by dataset, prompt, and often model or candidate
choices. Keeping those fields local preserves provenance and avoids making the
shared file a hidden project definition.

**Alternatives considered**:

- Share model configs too: rejected for this feature because the user asked to
  share the evaluation harness, not scenario-owned generation setup.
- Allow any project section: rejected because it blurs scenario identity and
  increases conflict handling complexity.

## Decision: Scenario Identity Is Optional, But Complete When Present

Add optional scenario identity to project configs. When absent, existing
projects behave as non-scenario projects. When present, scenario identity must
include:

- `group`
- `name`
- `display_name`

The values are emitted into trace metadata, run metadata, CSV exports, and
review payload context.

**Rationale**: Not all projects use scenarios, but projects that do need stable
metadata for filtering, comparison, exports, and reviewer context. Project name
or dataset name alone is convention-based and fragile.

**Alternatives considered**:

- Infer scenario from project name: rejected because it reintroduces naming
  convention dependence.
- Require scenario identity for all projects: rejected because it would break
  simple existing projects with no scenario concept.

## Decision: Keep One-Project-At-A-Time Execution

This feature does not add a multi-scenario run command.

**Rationale**: The current harness already runs one project config at a time.
The immediate pain is duplicated evaluation configuration, not orchestration.

**Alternatives considered**:

- Add `--scenario` to a single multi-scenario project config: rejected for now
  because it touches CLI behavior, dataset naming, prompt resolution, run
  orchestration, and review routing more broadly than needed.
