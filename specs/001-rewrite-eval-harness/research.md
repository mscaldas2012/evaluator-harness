# Research: Lightweight Langfuse Evaluation Harness

## Decision: Prefer Langfuse Datasets as execution dataset identity

**Decision**: Local CSV/JSON remains the easiest authoring path, but valid
baseline and candidate runs must create, update, or resolve a Langfuse Dataset
and record the Langfuse dataset identity and version.

**Rationale**: Langfuse Datasets are designed as the single source of truth for
test data, support UI/SDK workflows, and allow experiments to run against a
specific versioned dataset. This improves reproducibility and comparison while
preserving low-friction local authoring.

**Alternatives considered**:

- Local CSV only: simpler, but weaker reproducibility and less native Langfuse
  comparison support.
- Langfuse-only dataset authoring: strongest Langfuse alignment, but violates
  the low-friction CSV workflow for non-engineers.

**References**:

- https://langfuse.com/docs/evaluation/experiments/datasets
- https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk

## Decision: Use Langfuse SDK experiments and tracing instead of local scoring

**Decision**: The harness should use Langfuse SDK capabilities for datasets,
dataset runs, traces, scores, and experiment comparison. Local code should not
aggregate scores or implement dashboards.

**Rationale**: The constitution requires Langfuse-first evaluation. Langfuse
experiments via SDK support programmatic experiment loops and dataset runs while
keeping inspection and comparison in Langfuse.

**Alternatives considered**:

- Local score aggregation: rejected because it duplicates Langfuse scoring and
  comparison.
- Local dashboard/reporting: rejected for MVP because Langfuse already owns the
  user-facing analysis surface.

**References**:

- https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk
- https://langfuse.com/docs/evaluation/scores/overview

## Decision: Provider adapters for OpenAI-compatible APIs and Ollama

**Decision**: Implement a narrow provider interface with two MVP adapters:
OpenAI-compatible APIs and Ollama. Each adapter must first use a
Langfuse-supported SDK integration, instrumented client, or compatible provider
API when available. Manual generation tracing is allowed only when there is no
compatible Langfuse integration for the target provider or when the integration
cannot capture required experiment metadata. Tracing strategy is adapter-owned
implementation behavior and is not exposed in project configuration.

The first OpenAI-compatible implementation is Azure OpenAI with Azure AD
client-credentials authentication. Current Langfuse docs show
`langfuse.openai.AzureOpenAI` and `AsyncAzureOpenAI` as supported wrapped
clients for Azure OpenAI. Therefore the provider should use the
Langfuse-wrapped AzureOpenAI client with the required Azure AD token and APIM
subscription-key headers before considering manual tracing.

**Rationale**: This satisfies cloud and local model coverage without building a
plugin system. Many routed model providers can be reached through
OpenAI-compatible APIs, while Ollama covers common local experimentation.
Keeping tracing mode out of project YAML lets users define evaluation projects
instead of tracing plumbing, while maintainers can still document manual
fallback decisions in provider code and tests.

**Alternatives considered**:

- Support every named provider in MVP: too broad for the thin harness
  philosophy.
- OpenAI-compatible only: too narrow because local model comparison is an MVP
  requirement.
- Always manually trace provider calls: rejected because Langfuse-supported
  integrations are less error-prone and more likely to capture model metadata,
  usage, latency, and errors consistently.

**References**:

- https://langfuse.com/docs/integrations/openai
- https://langfuse.com/guides/cookbook/integration_openai_sdk

## Decision: Baseline compatibility is explicit and fingerprinted

**Decision**: A baseline can be reused only when project name/version, Langfuse
dataset identity/version, task prompt version, evaluator set identity,
baseline provider/model, and baseline model parameters match the candidate run
requirements.

**Rationale**: Users need to add candidate models over time without rerunning
baseline outputs, but compatibility must be strict enough to keep comparisons
valid.

**Alternatives considered**:

- Always rerun baseline: wasteful and blocks the desired "run candidates later"
  workflow.
- Reuse latest baseline by name only: too risky because changed datasets,
  prompts, or evaluators would silently corrupt comparisons.

## Decision: Fail fast when Langfuse is unreachable

**Decision**: The harness must stop before or during execution if Langfuse is
unreachable.

**Rationale**: Langfuse is the system of record. Running without Langfuse would
produce local-only state and undermine reproducibility and trace inspection.

**Alternatives considered**:

- Continue locally and sync later: useful later, but adds local persistence and
  recovery complexity that conflicts with MVP simplicity.
- Best-effort warning only: rejected because it can produce untraceable
  experiments.

## Decision: Human review uses configured Langfuse Human Annotation Queues

**Decision**: MVP supports routing selected review items to a configured
Langfuse Human Annotation Queue. Automatic queue creation/resolution remains
backlog item `BL-003`.

**Rationale**: Annotation Queues provide the Langfuse-native human review UI.
Requiring an explicit queue ID keeps MVP configuration predictable and avoids
accidental queue proliferation.

**Alternatives considered**:

- Build local review files/UI: rejected because Langfuse provides annotation
  workflows.
- Create queues automatically in MVP: useful but not required for first
  execution and already tracked as backlog.

**References**:

- https://langfuse.com/docs/evaluation/evaluation-methods/annotation-queues

## Decision: Headless CLI only for MVP

**Decision**: No local UI for MVP. The harness runs through CLI commands and
Langfuse provides the UI.

**Rationale**: The primary users are engineers and prompt engineers who can
operate config files and CLI commands. A local UI would duplicate Langfuse and
increase implementation surface.

**Alternatives considered**:

- Streamlit setup UI: may be useful later for non-technical users, but not
  necessary for MVP and should not become the main workflow.

## Decision: Treat Langfuse configuration automation as staged MVP plus backlog

**Decision**: MVP automates dataset sync/resolve, run metadata logging, and
harness-managed score config sync because those are required for valid
execution and stable evaluator/annotation schemas. Other Langfuse setup tasks
are tracked as backlog phases. Score config sync should create or resolve only
prefixed, harness-managed score config schemas, reuse compatible existing
configs, and fail on incompatible configs instead of updating, archiving, or
deleting Langfuse objects. Evaluator prompt publication, evaluator setup,
annotation queue setup, dataset creation from traces, comparison workspace
setup, scheduled regression runs, and evaluator calibration support remain
staged follow-ups.

**Rationale**: Langfuse exposes many useful APIs, but automating all setup at
once would expand the harness beyond the thin MVP. Tracking automation
opportunities explicitly lets the project tackle them step by step without
losing the roadmap.

**Alternatives considered**:

- Automate all Langfuse configuration in MVP: rejected as too broad and risky.
- Leave all Langfuse configuration manual forever: rejected because repeated
  setup should become reproducible as projects mature.

## Decision: Require automated test coverage for every feature slice

**Decision**: Every implemented feature slice must include automated tests.
Langfuse, model-provider, and local model boundaries should be tested with
fakes, mocks, or HTTP contracts so normal test runs do not need live credentials
or external services.

**Rationale**: Baseline compatibility, dataset identity, trace metadata, and
Langfuse fail-fast behavior are easy to break silently. Tests are needed before
implementation to keep the harness reproducible and safe to modify.

**Alternatives considered**:

- Manual smoke testing only: rejected because it does not protect baseline reuse
  or metadata contracts.
- Live Langfuse tests as the default: rejected because credentials and network
  availability would make routine verification brittle.
