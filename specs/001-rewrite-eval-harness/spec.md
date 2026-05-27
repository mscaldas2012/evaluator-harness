# Feature Specification: Lightweight Langfuse Evaluation Harness

**Feature Branch**: `001-rewrite-eval-harness`

**Created**: 2026-05-22

**Status**: Draft

**Input**: User description: "Lightweight Langfuse Rewrite Evaluation Harness - Offline Evaluation Specification v1.1, May 2026"

## Clarifications

### Session 2026-05-22

- Q: How should dataset item identity work when a dataset has no stable `id` or has duplicate IDs? -> A: Allow missing `id`; generate stable item IDs from row position plus input hash, and reject duplicate explicit IDs.
- Q: What should happen when Langfuse is unreachable during a local experiment? -> A: Fail fast: stop the experiment immediately if Langfuse is unreachable.
- Q: Which model providers are required for the MVP? -> A: MVP supports OpenAI-compatible APIs and Ollama only; other providers are future adapters.
- Q: What human review sampling rule should apply to evaluated outputs? -> A: Select at least 5%, prioritizing failures, low-confidence, and disputed outputs before random sampling.
- Q: What is the scope of the harness relative to rewrite quality? -> A: The harness is generic; rewrite quality is the first evaluation project, defined by its datasets, baseline model configuration, candidate model configurations, and evaluator prompts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define an Evaluation Project (Priority: P1)

An AI engineer can define an evaluation project that groups the dataset,
baseline model configuration, candidate model configurations, and evaluators
needed for one evaluation use case. The first project is rewrite quality, but
future projects can use different datasets and evaluator prompts without
changing the harness.

**Why this priority**: The harness must be generic enough to compare model
outputs for many future use cases. Rewrite quality is an initial project, not
the identity of the tool.

**Independent Test**: Can be fully tested by defining a rewrite-quality project
with a simple dataset, a baseline model configuration, one candidate model, and
at least one evaluator prompt, then confirming the project can be selected for a
run.

**Acceptance Scenarios**:

1. **Given** a project definition with datasets, a baseline model
   configuration, candidate model configurations, and evaluators, **When** the
   engineer starts a run for that project, **Then** the harness uses the
   project-scoped dataset, model settings, and evaluator metadata.
2. **Given** a future evaluation use case with different evaluator prompts,
   **When** the engineer defines it as a new project, **Then** the harness does
   not require code changes to understand the new evaluation dimensions.

---

### User Story 2 - Run or Reuse a Baseline (Priority: P2)

An AI engineer can run the baseline for a project once and reuse that baseline
for later candidate runs when the project, dataset version, baseline model
configuration, and evaluator set remain compatible.

**Why this priority**: Model comparison often happens over time. Users need to
add candidate runs tomorrow without rerunning a baseline that already exists.

**Independent Test**: Can be tested by running a baseline today, then running a
new candidate later against the same project and confirming the existing
baseline is selected instead of rerun.

**Acceptance Scenarios**:

1. **Given** a project has no compatible baseline run, **When** the engineer
   starts a comparison run, **Then** the harness requires or creates a baseline
   before candidate results are considered comparable.
2. **Given** a project has a compatible baseline run, **When** the engineer runs
   new candidate models later, **Then** the harness reuses the existing
   baseline and records which baseline run was used for comparison.
3. **Given** the dataset version, baseline model parameters, or evaluator set
   has changed, **When** the engineer attempts to reuse a baseline, **Then** the
   harness reports that the baseline is not compatible and requires a new
   baseline or explicit selection of a compatible one.

---

### User Story 3 - Compare Candidate Models or Parameters (Priority: P3)

An AI engineer can run one or more candidate models or model-parameter variants
against a project so the results can be compared with the project baseline in
Langfuse.

**Why this priority**: The primary purpose of the harness is to compare outputs
from different models or model parameters while delegating scoring, dashboards,
and trace inspection to Langfuse.

**Independent Test**: Can be tested by running two candidate model
configurations against the same project baseline and confirming both runs are
associated with the same project and baseline reference.

**Acceptance Scenarios**:

1. **Given** a compatible baseline exists, **When** the engineer runs `llama3`
   today and `mistral` plus `glm-5` tomorrow, **Then** all candidate runs are
   recorded under the same project comparison context without rerunning the
   baseline.
2. **Given** two candidate runs use the same model but different parameters,
   **When** the engineer compares them, **Then** the harness records the
   parameter differences as part of each run identity.

---

### User Story 4 - Review Outcomes in Langfuse (Priority: P4)

A prompt engineer can open the project experiment in Langfuse, inspect traces,
review automated evaluator outcomes, and use Langfuse Human Annotation Queues
for selected outputs that need manual review.

**Why this priority**: The project must keep evaluation and reporting
Langfuse-first while making human calibration practical.

**Independent Test**: Can be tested by completing a baseline and candidate run,
then confirming traces, metadata, evaluator-ready fields, and selected review
items are available through Langfuse, including Human Annotation Queues where
configured.

**Acceptance Scenarios**:

1. **Given** a project with baseline and candidate outputs, **When** the prompt
   engineer opens Langfuse, **Then** traces, run metadata, evaluator outputs,
   and comparison context are available for inspection.
2. **Given** selected outputs require human review, **When** annotation queues
   are configured for the project, **Then** the selected outputs can be routed
   to Langfuse Human Annotation Queues with source input, baseline output,
   candidate output, evaluator output, and trace context.

---

### User Story 5 - Add a New Model With Minimal Changes (Priority: P5)

An agent developer can add a new cloud or local model through configuration or a
small provider adapter without changing project workflow code.

**Why this priority**: Provider coverage matters, but extensibility must not
turn the harness into a plugin platform.

**Independent Test**: Can be tested by registering a new model, running it on a
two-row project dataset, and confirming its outputs and metadata appear
alongside the project baseline.

**Acceptance Scenarios**:

1. **Given** an OpenAI-compatible model endpoint, **When** the developer adds the
   model configuration, **Then** the model can be selected for a candidate run.
2. **Given** a local model endpoint, **When** the developer configures it with
   required generation settings, **Then** the harness records the provider,
   model, and local runtime metadata for each output.

### Edge Cases

- Project definition is missing a dataset, baseline model configuration, or
  evaluator set.
- Dataset is missing the required `input` column.
- Dataset contains blank, duplicate, very long, or malformed rows.
- Dataset omits item IDs and requires generated stable item identifiers.
- Dataset provides duplicate explicit item IDs.
- Existing baseline is incompatible with the selected project, dataset version,
  baseline parameters, prompt version, or evaluator set.
- Candidate run is requested without a compatible baseline.
- A model provider times out, rate-limits, or returns invalid output.
- Prompt version is missing, changed, or mismatched across compared runs.
- Token usage, cost, or latency fields are unavailable from a provider.
- Langfuse is unreachable before or during a run.
- Langfuse accepts only partial records for a dataset item or model output.
- Local model metadata such as hardware or token counts is unavailable.
- Automated evaluator output is missing, malformed, low-confidence, or disputed.
- Human Annotation Queue routing is requested but the queue is not configured.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST support project-scoped evaluation definitions. A
  project owns datasets, baseline model configuration, candidate model
  configurations, evaluator definitions, and review policy.
- **Dataset**: Feature MUST support CSV datasets with an `input` column as the
  default authoring path. Minimal JSON and Langfuse-hosted datasets MAY also be
  supported. Accepted local datasets SHOULD be imported or resolved as Langfuse
  Datasets before valid experiment execution so runs can reference a Langfuse
  dataset identity and version. Datasets MAY include optional `ground_truth`
  values that evaluators can use as reference answers, labels, or expected
  outputs.
- **Langfuse Logging**: Feature MUST define and record trace, dataset-run,
  project, run, score-ready, evaluator, baseline-reference, and comparison
  metadata in Langfuse.
- **Prompt and Evaluator Versioning**: Feature MUST associate every run and
  trace with the project prompt version and evaluator prompt versions selected
  by the user or resolved from project metadata.
- **Baseline**: Feature MUST create, select, or reuse a compatible baseline
  model run before candidate comparisons are considered complete.
- **Human Review**: Feature MUST preserve enough Langfuse context for users to
  inspect important, disputed, failed, or low-confidence outputs, and MUST use
  Langfuse Human Annotation Queues when project review policy requires queueing.

### Functional Requirements

- **FR-001**: Users MUST be able to define an evaluation project with at least
  one dataset, one baseline model configuration, one candidate model
  configuration, and one evaluator definition.
- **FR-002**: Users MUST be able to run a project from a local dataset
  containing at least an `input` field.
- **FR-002a**: When a project uses a local CSV or JSON dataset, the system MUST
  create, update, or resolve a corresponding Langfuse Dataset before executing
  valid baseline or candidate runs.
- **FR-002b**: The system MUST record the Langfuse dataset name or ID and
  dataset version used by each run.
- **FR-002c**: Local CSV, local JSON, and Langfuse datasets MAY include optional
  `ground_truth` per item. Missing `ground_truth` MUST NOT block baseline or
  candidate execution.
- **FR-003**: Users MUST be able to identify the baseline model and generation
  parameters for each project.
- **FR-004**: The system MUST execute or select a compatible baseline before
  candidate models are considered comparable.
- **FR-004a**: Baseline runs MUST create evaluator-ready Langfuse records for
  baseline-mode evaluators, including `input`, baseline `output`, optional
  `ground_truth`, evaluator versions, and trace context.
- **FR-004b**: When evaluator automation is configured and available through
  Langfuse, baseline runs SHOULD trigger or enqueue Langfuse-owned baseline
  evaluator execution. The harness MUST NOT implement local evaluator scoring.
- **FR-004c**: Baseline evaluator readiness and Langfuse-owned evaluator
  execution MUST NOT depend on `ground_truth` being present. Evaluators that do
  require ground truth must declare that requirement in their variables or
  Langfuse configuration.
- **FR-005**: The system MUST allow candidate runs to reuse a previous
  compatible baseline without rerunning it.
- **FR-006**: The system MUST record the baseline run identity used by each
  candidate run.
- **FR-007**: The system MUST reject baseline reuse when the project, dataset
  version, prompt version, baseline parameters, or evaluator set is
  incompatible.
- **FR-008**: Users MUST be able to run one or more candidate models or
  model-parameter variants against the same project and compatible baseline.
- **FR-009**: The system MUST record one trace or equivalent inspectable record
  for each model output and dataset item.
- **FR-009a**: When a dataset item has no explicit `id`, the system MUST
  generate a stable item identifier from row position and input hash.
- **FR-009b**: When a dataset contains duplicate explicit item IDs, the system
  MUST reject the dataset before experiment execution.
- **FR-010**: Each output record MUST include provider, model name, model
  parameters, prompt version, evaluator set identity, latency, timestamp, run
  identity, dataset identity, project identity, and baseline reference.
- **FR-011**: Each output record MUST include token usage and estimated cost when
  the provider makes those values available.
- **FR-012**: The system MUST mark unavailable provider metadata explicitly
  rather than silently omitting it.
- **FR-013**: Users MUST be able to configure project prompts and evaluator
  prompts separately from datasets and model selection.
- **FR-014**: The system MUST support repeated runs for the same project,
  dataset, prompt, evaluator set, model, and parameters so users can assess
  variance.
- **FR-015**: The system MUST support retry behavior for transient provider
  failures and record retry outcomes.
- **FR-016**: The system MUST support cloud and local model execution paths in a
  consistent project workflow.
- **FR-017**: The MVP MUST support OpenAI-compatible provider behavior for cloud
  or routed model endpoints.
- **FR-017a**: Provider execution MUST prefer Langfuse-supported SDK
  integrations, instrumented clients, or Langfuse-compatible provider APIs when
  they can capture required generation tracing metadata.
- **FR-017b**: Manual generation tracing MAY be used only when no compatible
  Langfuse provider integration exists or when the integration cannot capture
  required experiment metadata.
- **FR-017e**: Project configuration MUST NOT require users to choose tracing
  mode. Provider adapters MUST select the tracing strategy internally and expose
  manual fallback rationale through adapter code or diagnostics for maintainers.
- **FR-017c**: The first OpenAI-compatible MVP provider implementation MUST
  support Azure OpenAI authentication with tenant ID, client ID, client secret,
  token scope, APIM subscription key, API version, and Azure endpoint.
- **FR-017d**: The Azure OpenAI provider MUST use the Langfuse-wrapped
  `AzureOpenAI` client when compatible with the required Azure AD token and
  subscription-key headers; manual tracing is allowed only if that client cannot
  support the required authentication flow.
- **FR-017f**: Project configuration MUST store only environment variable names
  or secret reference names for provider credentials. Secret values, including
  tenant IDs, client IDs, client secrets, subscription keys, tokens, and API
  keys, MUST be loaded from `.env`, the host environment, or a secret manager
  and MUST NOT be committed in project config files.
- **FR-018**: The MVP MUST support Ollama as the required local model provider.
- **FR-018a**: Anthropic, Google Gemini, OpenRouter, Azure OpenAI, LM Studio,
  vLLM, and llama.cpp support are future adapters unless they are reachable
  through the OpenAI-compatible provider path.
- **FR-019**: The system MUST send project and run data to Langfuse so Langfuse
  can own evaluator execution, scoring, dashboards, comparison views, Human
  Annotation Queues, and trace inspection.
- **FR-019a**: The system MUST stop experiment execution immediately when
  Langfuse is unreachable before or during a run.
- **FR-019b**: The system MUST report which dataset item, model, and operation
  were active when Langfuse connectivity failed.
- **FR-020**: The system MUST NOT implement local dashboards, local comparison
  engines, or local score aggregation as part of the MVP.
- **FR-021**: Users MUST be able to tag or name projects and runs so they can be
  found and compared later.
- **FR-022**: Users MUST be able to distinguish environment, project, dataset,
  prompt version, evaluator version, baseline run, candidate run, and run
  identity in recorded metadata.
- **FR-023**: The system MUST make baseline outputs available to Langfuse-native
  comparison and evaluation workflows.
- **FR-023a**: Evaluator definitions MUST declare whether they support
  `baseline`, `candidate`, or both modes so baseline outputs can be evaluated
  before any candidate run exists.
- **FR-023b**: Evaluator definitions that require Langfuse scores MUST declare
  a score config contract including score name, data type, and constraints such
  as numeric range or allowed categories.
- **FR-023c**: Score configs created by the harness MUST use a project-configured
  prefix so they are identifiable as harness-managed Langfuse score configs.
  `score_config_prefix` MUST be non-empty, slug-safe using only ASCII letters,
  numbers, `_`, and `-`, project-specific, end with `_` or `-`, and leave enough
  name length budget for the evaluator score name. The prefix MUST be no more
  than 64 characters, and the derived managed score config name SHOULD be no
  more than 128 characters unless Langfuse documents a different limit.
- **FR-023d**: The harness MUST implement score config sync as MVP setup
  behavior through `sync-score-configs` or equivalent run preparation. This sync
  creates missing harness-managed Langfuse score configs and reuses compatible
  existing configs.
- **FR-023e**: The harness MUST only create or reuse score configs explicitly
  marked `managed_by_harness`. If a matching score config already exists with
  incompatible schema, the harness MUST fail with remediation guidance and MUST
  NOT update, archive, or delete the existing Langfuse score config.
- **FR-023f**: If a harness-managed score config needs to change, users MUST
  manually delete or rename the existing score config in Langfuse before
  resyncing. Archiving alone MUST be treated as still conflicting unless the
  Langfuse API no longer returns or reserves the same score config name. The
  harness may then create the new compatible config.
- **FR-023g**: Score configs not marked `managed_by_harness` MUST be treated as
  user-owned Langfuse configuration. The harness MAY validate or reference them
  by ID/name but MUST NOT create, update, archive, or delete them.
- **FR-023h**: Score config compatibility MUST compare score name, data type,
  numeric min/max bounds, categorical labels/values, boolean/text constraints
  exposed by Langfuse, and archived status. Description differences SHOULD be
  reported but MUST NOT make an otherwise compatible score config fail sync.
- **FR-024**: The system MUST support optional lightweight result exports for
  sharing or archival without replacing Langfuse reporting.
- **FR-025**: Automated evaluation outputs MUST be treated as decision support
  and not presented as objective truth.
- **FR-026**: Evaluation workflows MUST avoid exposing provider or model identity
  to judge prompts when blind judging is used.
- **FR-026a**: When an evaluator has `blind: true`, evaluator payloads MUST use
  neutral labels such as baseline and candidate or output A and output B, while
  provider, model, vendor, cost, and latency metadata remain available only in
  trace/run metadata outside the judge prompt.
- **FR-027**: The system MUST support selection of items for human review,
  including low-confidence, failed, sampled, or disputed outputs.
- **FR-027a**: When automated evaluations are used, the system MUST select at
  least 5% of evaluated outputs for human review, prioritizing failures,
  low-confidence outputs, and disputed outputs before random sampling.
- **FR-027b**: When a project configures a Langfuse Human Annotation Queue, the
  system MUST route selected review items to that queue with source input,
  baseline output, candidate output, evaluator output, and trace context.
- **FR-028**: The MVP MUST keep advanced governance, CI/CD gating, drift
  monitoring, multi-judge consensus, and custom reporting outside initial scope
  unless they are provided by Langfuse-native capabilities.
- **FR-029**: Every implemented feature slice MUST include automated tests that
  cover success paths, validation failures, provider failures, Langfuse
  failures, metadata correctness, and CLI exit behavior where applicable.
- **FR-030**: Integration points with Langfuse MUST be covered by tests using
  fakes, mocks, or recorded contracts so test runs do not require live Langfuse
  credentials.

### Key Entities *(include if feature involves data)*

- **Evaluation Project**: A named evaluation use case. It owns one or more
  datasets, baseline model configuration, candidate model configurations,
  prompt versions, evaluator definitions, and human review policy. Rewrite
  quality is the first project.
- **Dataset**: A collection of project inputs, minimally containing `input` and
  optionally `id`, tags, notes, expected attributes, reference output, or
  baseline output. Datasets may also include `ground_truth` as a project-defined
  reference value for baseline and candidate evaluators. Explicit `id` values
  must be unique when present. Local files are an authoring/import format;
  Langfuse Datasets are the preferred experiment dataset system of record.
- **Dataset Item**: One input row or object to be evaluated through baseline and
  candidate runs. Identity is the explicit unique `id` when present; otherwise
  it is a generated stable identifier based on row position and input hash.
- **Prompt Version**: The project task instruction associated with a run and its
  generated outputs.
- **Evaluator Definition**: A project-scoped evaluator such as an LLM-as-a-Judge
  prompt or deterministic metric definition. Evaluator definitions determine
  what quality dimensions are assessed for that project and whether the
  evaluator supports baseline mode, candidate mode, or both. Evaluators also
  declare the Langfuse score config contract they require.
- **Baseline Model Configuration**: The model, provider, parameters, prompt
  version, and relevant runtime settings that define the comparison baseline for
  a project.
- **Candidate Model Configuration**: A model, provider, and parameter set to be
  compared against a compatible baseline.
- **Run**: A single execution pass for a baseline or candidate configuration
  over a project dataset under specific prompt and evaluator versions.
- **Baseline Reference**: The compatible baseline run identity associated with a
  candidate run.
- **Output Record**: The generated model output plus trace identifiers,
  metadata, latency, token usage, cost where available, evaluator context, and
  error state if applicable.
- **Evaluation Result**: Langfuse-owned score, reasoning, confidence, or
  evaluator output associated with an output record.
- **Human Annotation Queue Item**: A selected output routed to Langfuse for
  manual review and calibration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A non-engineer can create a valid two-column project dataset in
  under 5 minutes.
- **SC-002**: A single engineer can define a project, configure models, run a
  baseline, run at least one candidate, and open the resulting Langfuse
  comparison context in under 15 minutes after credentials are available.
- **SC-003**: For a 10-item dataset, 100% of successful model outputs are linked
  to inspectable project records with provider, model, parameters, prompt
  version, timestamp, latency, run identity, and baseline reference.
- **SC-004**: For providers that return token usage, 100% of successful outputs
  include input token and output token counts.
- **SC-005**: A baseline run created on one day can be reused by at least two
  later candidate runs without rerunning the baseline when compatibility rules
  are satisfied.
- **SC-006**: A baseline run and at least one candidate run can be compared in
  Langfuse without exporting data to a custom dashboard.
- **SC-007**: At least 5% of evaluated outputs can be selected for manual
  review, with failures, low-confidence outputs, and disputed outputs selected
  before random sampling.
- **SC-008**: When a Langfuse Human Annotation Queue is configured, selected
  review items include source input, baseline output, candidate output,
  evaluator output, and trace context.
- **SC-009**: Adding a new compatible model requires no change to the dataset
  format or project workflow.
- **SC-010**: Failed model calls are visible to the user with dataset item,
  provider, model, retry count, and failure reason.
- **SC-011**: Automated tests cover project validation, dataset identity,
  Langfuse Dataset sync/resolve, baseline compatibility, candidate execution,
  provider tracing mode selection, fail-fast Langfuse behavior, and human review
  selection.

## Backlog

- **BL-001: Automatic evaluator prompt publication**: Add optional automation
  that publishes project LLM-as-a-Judge prompts to Langfuse prompt management,
  records prompt versions, and links evaluator definitions to the published
  prompt versions.
- **BL-002: Automatic LLM-as-a-Judge evaluator setup**: Add optional automation
  that creates or resolves Langfuse evaluator configuration for project
  evaluator definitions, including variable mapping for `input`,
  `baseline_output`, `candidate_output`, and optional reference fields.
- **BL-003: Automatic Human Annotation Queue setup**: Add an optional project
  setting that lets the harness create or resolve a Langfuse Human Annotation
  Queue programmatically, then add the selected review sample to it. The review
  sample MUST include at least 5% of evaluated outputs, prioritizing failures,
  low-confidence outputs, and disputed outputs before random sampling. The
  implementation MUST avoid duplicate queue items across reruns and MUST allow
  users to provide an explicit existing queue ID.
- **BL-004: Automatic dataset creation from production traces**: Add optional
  automation to create or extend project datasets from selected Langfuse traces
  or observations, preserving source trace references and review status.
- **BL-005: Automatic comparison workspace setup**: Add optional automation that
  creates or links saved Langfuse views, tags, or dashboards needed to compare a
  project baseline with candidate runs.
- **BL-006: Automatic scheduled regression runs**: Add optional automation for
  CI or scheduled jobs that run selected projects against compatible baselines
  and alert on Langfuse-native score or annotation changes.
- **BL-007: Automatic evaluator calibration support**: Add optional automation
  that exports or records calibration samples, human labels, evaluator outputs,
  and disagreement summaries for iterative evaluator prompt improvement.

## Assumptions

- The first deliverable is an MVP aligned with the lightweight constitution, not
  a production inference platform.
- The harness is generic. Rewrite quality is the first evaluation project, not
  a hard-coded harness purpose.
- Langfuse is the system of record for traces, evaluations, scoring,
  dashboards, comparison, Human Annotation Queues, and inspection.
- Local exports are convenience artifacts only and do not replace Langfuse.
- The default dataset authoring format is CSV with an `input` column.
- Valid experiment runs use a Langfuse Dataset identity and version, even when
  the dataset was authored locally first.
- Prompt versions and evaluator prompt versions are controlled through named or
  versioned project artifacts selected at run time.
- Providers beyond OpenAI-compatible APIs and Ollama are future enhancements
  unless they work through the OpenAI-compatible provider path.
- The first OpenAI-compatible implementation uses Azure OpenAI with Azure AD
  client-credentials authentication and an APIM subscription key.
- Advanced capabilities such as CI/CD gates, drift monitoring, multi-judge
  voting, and custom reports are future enhancements unless Langfuse can provide
  them without expanding local harness scope.
- Human review sampling selects at least 5% of evaluated outputs when automated
  evaluations are used, prioritizing failures, low-confidence outputs, and
  disputed outputs before random sampling.
