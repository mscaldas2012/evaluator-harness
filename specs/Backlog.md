# Evaluator Harness Backlog

This file consolidates cross-feature backlog and technical debt items that are
not owned by a single active feature spec.

## Technical Debt From Graphify Review

- **TD-GRAPH-001: Split `LangfuseClient` into focused adapters**
  - Source: Graphify review of `src/evaluator_harness/langfuse_client.py`.
  - Problem: `LangfuseClient` is a god object that mixes in-memory fake state,
    SDK adapter behavior, REST adapter behavior, retry policy, data
    normalization, prompt/version lookup, queue routing, and trace retrieval.
  - Improvement: Introduce a small gateway/protocol boundary and split concrete
    behavior into `InMemoryLangfuseGateway`, `LangfuseSdkGateway`,
    `LangfuseRestGateway`, and mapper/helper modules.

- **TD-GRAPH-002: Surface live Langfuse partial persistence and lookup failures**
  - Source: Graphify review of `src/evaluator_harness/langfuse_client.py`.
  - Current status: Implemented by `specs/022-surface-langfuse-failures`.
    Langfuse persistence and lookup paths now use structured outcomes/warnings
    so recoverable partial persistence is visible, expected not-found cases stay
    distinct from lookup failures, and required live linkage can block
    misleading exports.
  - Follow-up: The behavior is covered by non-live and live test suites.
    Remaining cleanup is general lint debt in the broad Langfuse/runner Ruff
    glob, primarily line-length and enum modernization findings.
  - Likely modules: `langfuse_baselines.py`, `langfuse_dataset.py`,
    `langfuse_traces.py`, and `langfuse_scores.py`.

- **TD-GRAPH-003: Extract shared run-item execution from `ExperimentRunner`**
  - Source: Graphify review of `src/evaluator_harness/runner.py`.
  - Problem: Baseline and candidate execution duplicate trace creation, prompt
    rendering, session identity, request metadata, provider invocation, trace
    logging, dataset run item recording, and failure trace logging.
  - Improvement: Extract a `RunExecutor` or equivalent shared per-item execution
    path with separate baseline and candidate run plans.

- **TD-GRAPH-004: Replace global environment mutation with scoped environment resolution**
  - Source: Graphify review of `src/evaluator_harness/config.py`.
  - Problem: Config loading mutates `os.environ` and tracks managed values in
    global state, which can leak project-specific environment behavior across
    repeated runner calls in one process.
  - Improvement: Return an immutable resolved environment mapping from layered
    env loading and pass it into provider/client construction, or add an
    explicit scoped environment context.

- **TD-GRAPH-005: Move CLI result presentation out of command bodies**
  - Source: Graphify review of `src/evaluator_harness/cli.py`.
  - Problem: CLI commands combine project resolution, runner invocation, output
    formatting, and exit-code decisions. This makes command tests sensitive to
    presentation details and keeps command bodies large.
  - Improvement: Add presenter functions/classes per command group and keep
    Typer command functions thin.

## Consolidated Feature Backlog

- **BL-001: Automatic evaluator prompt publication**
  - Source: `specs/001-rewrite-eval-harness/spec.md`.
  - Add optional automation that publishes project LLM-as-a-Judge prompts to
    Langfuse prompt management, records prompt versions, and links evaluator
    definitions to the published prompt versions.

- **BL-002: Automatic LLM-as-a-Judge evaluator setup**
  - Source: `specs/001-rewrite-eval-harness/spec.md`.
  - Add optional automation that creates or resolves Langfuse evaluator
    configuration for project evaluator definitions, including variable mapping
    for `input`, `baseline_output`, `candidate_output`, and optional reference
    fields.

- **BL-003: Automatic Human Annotation Queue setup**
  - Sources: `specs/001-rewrite-eval-harness/spec.md`,
    `specs/002-live-langfuse-mvp/spec.md`.
  - Add an optional project setting that lets the harness create or resolve a
    Langfuse Human Annotation Queue programmatically, then route selected review
    samples to it. The implementation must avoid duplicate queue items across
    reruns and allow users to provide an explicit existing queue ID.

- **BL-004: Automatic dataset creation from production traces**
  - Source: `specs/001-rewrite-eval-harness/spec.md`.
  - Add optional automation to create or extend project datasets from selected
    Langfuse traces or observations while preserving source trace references and
    review status.

- **BL-005: Automatic comparison workspace setup**
  - Source: `specs/001-rewrite-eval-harness/spec.md`.
  - Add optional automation that creates or links saved Langfuse views, tags, or
    dashboards needed to compare a project baseline with candidate runs.

- **BL-006: Automatic scheduled regression runs**
  - Source: `specs/001-rewrite-eval-harness/spec.md`.
  - Add optional CI or scheduled jobs that run selected projects against
    compatible baselines and alert on Langfuse-native score or annotation
    changes.

- **BL-007: Automatic evaluator calibration support**
  - Source: `specs/001-rewrite-eval-harness/spec.md`.
  - Add optional automation that exports or records calibration samples, human
    labels, evaluator outputs, and disagreement summaries for iterative
    evaluator prompt improvement.

- **BL-008: Provider adapters beyond OpenAI-compatible APIs and Ollama**
  - Source: `specs/001-rewrite-eval-harness/spec.md`.
  - Add direct provider adapters beyond the MVP provider set when they cannot be
    reached through the OpenAI-compatible provider path.

- **BL-009: Advanced experiment governance and reporting**
  - Source: `specs/001-rewrite-eval-harness/spec.md`.
  - Add advanced capabilities such as CI/CD gates, drift monitoring,
    multi-judge voting, and custom reports when Langfuse-native capabilities are
    insufficient.

- **BL-010: Live candidate provider calls for the live Langfuse MVP**
  - Source: `specs/002-live-langfuse-mvp/spec.md`.
  - Replace fake or dry-run candidate comparison records with live candidate
    provider calls in the live MVP flow.

- **BL-011: Detailed reviewer assignment and Langfuse permission automation**
  - Source: `specs/003-create-annotation-queues/spec.md`.
  - Extend queue automation beyond create/resolve/route behavior to configure
    detailed reviewer assignments or Langfuse permissions.

- **BL-012: Explicit role mapping for constrained model providers**
  - Source: `specs/011-prompt-roles-variables/spec.md`.
  - Add explicit mapping from configured role labels to providers with narrower
    supported role sets.

- **BL-013: Evaluator prompt roles**
  - Source: `specs/011-prompt-roles-variables/spec.md`.
  - Extend role-based prompt support from model generation prompts to evaluator
    prompts.

- **BL-014: Partial prompt inheritance for candidate prompt overrides**
  - Source: `specs/011-prompt-roles-variables/spec.md`.
  - Support partial role or message inheritance for candidate-level prompt
    overrides instead of requiring a full prompt replacement.

- **BL-015: Session-level scoring and aggregation**
  - Source: `specs/017-item-comparison-sessions/spec.md`.
  - Add session-level scoring, preference aggregation, historical trace
    backfilling, and manual session-level human scores in Langfuse after
    item-level session grouping is validated.

- **BL-016: Baseline-only campaign mode**
  - Source: `specs/019-campaign-mode/spec.md`.
  - Add an explicit option for campaign mode to run a baseline-only campaign
    when no candidates are eligible.

- **BL-017: Interactive HTML comparison report filtering**
  - Source: `specs/020-html-comparison-report/spec.md`.
  - Add interactive filtering or live data loading to HTML comparison reports if
    later specified.

## Existing Technical Debt

- **TD-001: Remove Langfuse unstable evaluator REST fallback**
  - Source: `specs/008-langfuse-judge-setup/spec.md`.
  - Langfuse evaluator setup temporarily maintains both SDK and REST adapter
    paths. Remove the unstable `/api/public/unstable/evaluation-rules` REST
    fallback once Langfuse releases stable SDK support for LLM-as-Judge
    evaluator CRUD. Deletes remain out of scope.

- **TD-002: Reconcile evaluator rule score config binding**
  - Source: `specs/008-langfuse-judge-setup/spec.md`.
  - Langfuse evaluator rules currently do not expose a score config binding
    field. The harness records the intended canonical score config in local
    bindings for calibration, while Langfuse LLM-as-Judge scores may be emitted
    under the evaluator name and source `EVAL`; Human Annotation Queue scores
    continue to use the canonical score config and source `ANNOTATION`.
