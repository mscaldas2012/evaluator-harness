# Research: Azure API-Key Candidate Provider

## Decision: Treat endpoint/API-key Azure deployments as a provider auth variant

**Rationale**: The harness already models provider and authentication mode as
separate concepts. The user need is not a Mistral-specific provider; it is an
Azure-hosted deployment that uses endpoint/API-key access instead of
tenant/client credentials. Modeling this as an auth variant keeps the runner,
dataset, baseline, evaluator, and review workflows unchanged.

**Alternatives considered**:

- Add a `mistral` provider: rejected because the deployment is hosted behind an
  Azure endpoint and the requirement should cover any compatible model.
- Add a separate CLI command: rejected because candidates should remain
  config-driven and use the existing candidate run workflow.
- Force users to adapt the existing tenant/client Azure config: rejected
  because API-key Azure accounts do not provide tenant/client/token scope
  credentials for this use case.

## Decision: Use explicit per-model auth mode, not environment auto-detection

**Rationale**: A single project may contain a baseline using tenant/client
credentials and one or more candidates using API keys, potentially across
different Azure accounts. Auth mode must therefore be selected by each model
configuration, and the harness should instantiate provider behavior per
baseline or candidate config. Auto-detecting from available environment
variables would be ambiguous and could route a model through the wrong account
or credential set.

**Alternatives considered**:

- Auto-detect based on whichever environment variables are set: rejected
  because developer shells may contain credentials for several projects,
  baselines, and candidates at once.
- Split into separate user-facing provider families for tenant/client and
  API-key auth: rejected because most request construction, response parsing,
  retry behavior, trace metadata, and redaction behavior is shared.
- Hard-code environment variable names by role: rejected because teams need to
  choose deployment-specific names, but examples should show safe naming
  conventions.

## Decision: Use project/model-specific environment variable names in examples

**Rationale**: The harness only stores environment variable names, and users
may run several Azure deployments in the same shell. Examples should encourage
names that include project and model or role, such as
`REWRITE_QUALITY_BASELINE_AZURE_ENDPOINT` and
`REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY`, so values do not collide across
baselines and candidates.

**Alternatives considered**:

- Generic names such as `AZURE_MODEL_API_KEY`: rejected for examples because
  they become ambiguous as soon as a project has multiple Azure models.
- Harness-generated env var names: rejected because users already manage
  secrets in `.env`, shell environments, and secret managers.

## Decision: Store only non-secret credential references in project YAML

**Rationale**: API keys are bearer secrets. Project configuration is intended
to be committed, reviewed, and reused, so it must contain environment variable
names rather than literal key values. This preserves the project's existing
secret-handling contract.

**Alternatives considered**:

- Store API keys directly in project YAML: rejected because it would expose
  secrets in git, traces, diffs, and support output.
- Require a dedicated secret manager integration now: rejected because the
  current harness standard is environment-variable references and `.env`
  loading for local execution.

## Decision: Keep API-key candidate generation in the existing candidate workflow

**Rationale**: The feature should let users compare the new Azure deployment
against the existing baseline and downstream evaluators. Reusing the current
candidate workflow ensures baseline references, run IDs, Langfuse metadata,
review routing, and evaluator targeting remain consistent.

**Alternatives considered**:

- Add a standalone provider smoke command: rejected because it would not prove
  baseline comparison or evaluator metadata compatibility.
- Add a local comparison/export path: rejected because Langfuse remains the
  comparison and observability system of record.

## Decision: Preserve the established Langfuse trace hierarchy

**Rationale**: Feature 008 established that Langfuse evaluators should target
the final model-output observation by project metadata and
`observation_role=model_output`, not by provider-specific observation names.
The API-key Azure candidate must therefore attach its generation under the
same run/item trace and parent workflow span as existing providers, with the
model-output metadata copied onto the generation observation itself.

**Alternatives considered**:

- Let the provider integration create independent traces: rejected because it
  would break baseline/candidate comparison, review routing, and evaluator
  filters that expect one run/item trace.
- Filter evaluators by generation name: rejected because candidate providers
  can use different observation names and the user explicitly needs the same
  evaluator to judge different candidates.
- Store evaluator metadata only on the parent trace: rejected because
  observation-level evaluators need the matching metadata on the observation
  being evaluated.

## Decision: Prefer Langfuse SDK instrumentation only when it preserves the contract

**Rationale**: The constitution requires preferring Langfuse SDK integrations
when they provide correct generation tracing, token usage, model metadata,
latency, and error capture. For this feature, the SDK path must also preserve
the existing parent trace/span and nested model-output observation structure.
If the SDK cannot attach the API-key Azure generation correctly, the existing
manual generation path is the smaller and safer fallback.

**Alternatives considered**:

- Always use manual REST plus manual tracing: rejected because a compatible
  Langfuse SDK/provider integration would reduce custom tracing maintenance.
- Always use SDK instrumentation: rejected because incorrect trace nesting or
  missing observation metadata would break evaluator targeting.

## Decision: Make `rewrite_quality` the end-to-end verification project

**Rationale**: The user explicitly asked that the plan ensure `rewrite_quality`
tests run the baseline and the new candidate. This project already exercises
dataset loading, prompt rendering, baseline reference metadata, candidate
generation, Langfuse tracing, judge evaluator metadata, and human review
configuration.

**Alternatives considered**:

- Test only with synthetic fixtures: rejected because it would miss the real
  project wiring the user intends to run.
- Require live tests in the default suite: rejected because default tests must
  not require Azure or Langfuse credentials.

## Decision: Preserve current tenant/client Azure behavior unchanged

**Rationale**: Existing baseline and live smoke workflows depend on the
tenant/client Azure path. API-key support must be additive so projects can mix
Azure accounts and authentication modes in the same experiment.

**Alternatives considered**:

- Replace the existing Azure credential model: rejected because it would risk
  regressions in the baseline workflow.
- Split the runner by auth mode: rejected because the auth mode should be a
  provider concern, not a workflow concern.

## Decision: Redact API key and configured sensitive values in all failures

**Rationale**: Provider failures often include request URLs, headers, or
service messages. API-key deployments must not leak keys or sensitive endpoint
values through exception text, command output, reports, or trace metadata.

**Alternatives considered**:

- Redact only API keys: rejected because some deployments treat endpoint hosts
  or subscription headers as sensitive operational data.
- Rely on upstream SDK redaction: rejected because the harness owns its output
  and must protect secrets consistently across provider paths.
