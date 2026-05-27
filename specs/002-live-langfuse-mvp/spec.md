# Feature Specification: Live Langfuse MVP

**Feature Branch**: `002-live-langfuse-mvp`

**Created**: 2026-05-26

**Status**: Draft

**Input**: User description: "live Langfuse MVP"

## Clarifications

### Session 2026-05-26

- Q: What provider scope should the live MVP prove end to end? -> A: Live Langfuse plus live Azure OpenAI baseline only; candidate execution may use fake or dry-run providers.
- Q: What should happen when Langfuse connectivity or workspace access cannot be verified? -> A: Fail before any model call.
- Q: Where should baseline references and compatibility metadata be persisted? -> A: In Langfuse only.
- Q: How should live smoke coverage be handled? -> A: Add opt-in live integration tests that hit Langfuse and Azure OpenAI.
- Q: What should happen when baseline or candidate commands are rerun with the same config? -> A: Create distinct runs; keep sync and queue routing idempotent.
- Q: How should random human annotation samples behave across baseline and future candidate runs? -> A: Use a deterministic dataset-item cohort so the same dataset items are selected for baseline and all compatible candidate runs when the dataset version and review policy are unchanged.
- Q: How should dataset compatibility work if Langfuse does not expose a dataset version? -> A: Use a deterministic dataset compatibility version derived from stable dataset item IDs and input hashes.
- Q: How should dry-run candidate execution be represented? -> A: Add a first-class `dry_run` provider/config path so candidate smoke runs are explicit and do not rely on hidden fake injection.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Persist Baseline Runs in Langfuse (Priority: P1)

An engineer can run a baseline evaluation and trust that the dataset run,
traces, outputs, and baseline reference are persisted in Langfuse so later
commands and later work sessions can reuse the baseline.
No local baseline registry file is created for the live MVP.

**Why this priority**: Baseline reuse is the critical gap between the current
offline MVP and a usable live MVP. Without persisted baseline references,
candidate runs in separate command executions cannot compare against prior
baselines.

**Independent Test**: Run a baseline for the sample project using configured
Langfuse credentials, then open Langfuse and confirm the dataset run, traces,
metadata, outputs, and reusable baseline reference are present.

**Acceptance Scenarios**:

1. **Given** a valid project and reachable Langfuse workspace, **When** the
   engineer runs the baseline, **Then** Langfuse contains one run with trace
   records for every dataset item and all required reproducibility metadata.
2. **Given** a completed baseline run, **When** the engineer asks for the latest
   compatible baseline in a later command execution, **Then** the same baseline
   is found without rerunning it.
3. **Given** Langfuse is unreachable, **When** the engineer runs the baseline,
   **Then** the command fails before any model execution and explains that no
   valid live run was recorded.
4. **Given** the same baseline command is run again intentionally, **When** the
   engineer starts the command, **Then** a distinct live baseline run is created
   instead of overwriting the prior run.

---

### User Story 2 - Run Candidates Against Persisted Baselines (Priority: P2)

An engineer can run candidate model outputs or parameter variants on a later day
and compare them against a previously persisted compatible baseline in Langfuse.
For the live MVP, candidate execution may use fake or dry-run providers while
still persisting candidate runs, traces, and baseline references to Langfuse.

**Why this priority**: The harness is primarily useful when candidate models can
be evaluated incrementally without wasting time and cost rerunning the baseline.

**Independent Test**: Run the live Azure OpenAI baseline once, run one fake or
dry-run candidate in a separate command execution, and confirm the candidate run
references the persisted baseline in Langfuse with matching project, dataset,
prompt, evaluator, and baseline parameter metadata.

**Acceptance Scenarios**:

1. **Given** a persisted compatible baseline, **When** the engineer runs a
   candidate with `latest-compatible`, **Then** candidate traces are persisted
   with the baseline reference on every output.
2. **Given** a specific baseline run ID, **When** the engineer runs a candidate
   against that ID, **Then** the candidate run uses that exact baseline only if
   compatibility rules match.
3. **Given** no compatible baseline exists, **When** the engineer runs a
   candidate, **Then** the command fails before model execution and instructs
   the engineer to run or select a compatible baseline.
4. **Given** the same candidate command is run again intentionally, **When** the
   engineer starts the command, **Then** a distinct live candidate run is created
   and linked to the compatible baseline.

---

### User Story 3 - Sync Live Langfuse Assets Safely (Priority: P3)

An engineer can prepare a project by syncing or resolving required Langfuse
assets, including datasets and harness-managed score configurations, without
manual drift or accidental mutation of user-owned Langfuse resources.

**Why this priority**: Live runs depend on Langfuse assets being present and
compatible. Safe sync behavior prevents confusing evaluator or comparison
results.

**Independent Test**: Sync the sample project into a test Langfuse workspace and
confirm the dataset and harness-managed score configurations are present,
compatible, and reused on a second sync without modification.

**Acceptance Scenarios**:

1. **Given** a local dataset, **When** the engineer syncs the dataset, **Then**
   Langfuse contains corresponding dataset items with stable item identities.
2. **Given** an existing compatible harness-managed score configuration,
   **When** the engineer syncs score configurations, **Then** the existing
   configuration is reused.
3. **Given** an incompatible harness-managed score configuration, **When** the
   engineer syncs score configurations, **Then** the command fails with clear
   remediation instructions instead of updating or deleting the configuration.

---

### User Story 4 - Route Human Review Items to Langfuse (Priority: P4)

A prompt engineer can select review items from a live candidate run and route
them to an existing Langfuse Human Annotation Queue for manual calibration and
inspection.

**Why this priority**: Human review keeps automated evaluation honest and makes
the live MVP usable for real model decisions.

**Independent Test**: After a live candidate run has evaluator scores or failure
signals, select review items and confirm the expected items appear in the
configured Langfuse Human Annotation Queue without duplicates.

**Acceptance Scenarios**:

1. **Given** a live run with failed, low-confidence, disputed, and normal
   outputs, **When** the prompt engineer selects review items, **Then** at least
   the configured minimum review sample is selected with risky outputs
   prioritized.
2. **Given** an existing annotation queue ID, **When** selected items are routed,
   **Then** Langfuse contains queue items with source input, baseline output,
   candidate output, optional ground truth, and trace context.
3. **Given** the same review selection is run again, **When** queue routing is
   repeated, **Then** duplicate queue items are skipped.
4. **Given** a baseline run and later compatible candidate runs over the same
   dataset version, **When** random calibration review items are selected,
   **Then** the same dataset item IDs are selected for baseline and candidates
   unless the dataset version or review policy changes.

### Edge Cases

- Langfuse credentials are missing, invalid, or point to the wrong workspace;
  live commands fail before any model call.
- Langfuse is reachable at startup but becomes unavailable during a run.
- A baseline run exists but one compatibility field differs, such as dataset
  version, prompt version, evaluator set, baseline model, or baseline
  parameters.
- Langfuse does not expose a dataset version; the harness must derive a stable
  dataset compatibility version from item identities and input hashes.
- A live dataset sync finds duplicate or changed item identities.
- A score configuration exists with the managed name but incompatible schema.
- A provider call succeeds but token, cost, or latency metadata is unavailable.
- A candidate run partially succeeds, with some item failures and some item
  outputs.
- Human annotation queue routing is requested without a configured queue ID.
- Repeated commands must not create duplicate traces, baseline references,
  score configurations, or annotation queue items for the same logical action.
- Repeated baseline or candidate execution commands intentionally create
  distinct live runs and traces; repeated setup and review-routing operations
  remain idempotent.
- Baseline lookup must not depend on local state from a previous process or a
  local baseline registry file.
- Random human-review calibration samples must remain stable across compatible
  baseline and candidate runs by selecting from Langfuse Dataset item identity,
  not from per-run trace order.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST use the existing evaluation project model with
  datasets, baseline model configuration, candidate model configurations,
  evaluator definitions, score configuration references, and review policy.
- **Dataset**: Feature MUST preserve support for local CSV datasets with an
  `input` column and optional `ground_truth`, while making Langfuse Datasets the
  live system of record after sync or resolve. When Langfuse does not expose a
  dataset version, the harness MUST derive a deterministic dataset
  compatibility version from stable dataset item IDs and input hashes.
- **Langfuse Logging**: Feature MUST persist traces, run metadata, dataset item
  identity, model outputs, baseline references, evaluator-ready payload context,
  score configuration identity, annotation queue routing results, and failure
  context to Langfuse where the live workspace supports those records.
  Traces SHOULD be created through Langfuse Dataset experiment/run linkage when
  available so each trace remains correlated to the originating dataset item.
- **Prompt and Evaluator Versioning**: Feature MUST associate every live run
  with prompt version, evaluator names, evaluator versions, and evaluator set
  identity.
- **Baseline**: Feature MUST allow creation, lookup, reuse, and explicit
  selection of compatible baseline runs across separate command executions.
- **Human Review**: Feature MUST support selecting important outputs and routing
  them to an existing Langfuse Human Annotation Queue without creating queues in
  the MVP.

### Functional Requirements

- **FR-001**: The system MUST verify Langfuse connectivity and workspace access
  before any live model execution begins, and MUST fail before any model call
  when verification fails.
- **FR-002**: The system MUST create or resolve the configured Langfuse Dataset
  before a valid live baseline or candidate run.
- **FR-003**: The system MUST persist baseline run identity and compatibility
  metadata in Langfuse so `latest-compatible` can be resolved in later command
  executions without a local baseline registry file.
- **FR-004**: The system MUST reject candidate execution when no compatible
  baseline can be found or when an explicitly selected baseline is incompatible.
- **FR-005**: The system MUST persist candidate runs with a baseline reference,
  candidate model identity, model parameters, dataset identity, prompt version,
  evaluator set identity, timestamps, latency, token usage when available, cost
  when available, and per-item failure context, even when the candidate provider
  is fake or dry-run for the live MVP.
- **FR-005a**: Dry-run candidate execution MUST be represented by an explicit
  first-class `dry_run` provider/config path rather than hidden test-only
  provider injection.
- **FR-006**: The system MUST sync harness-managed score configurations by
  creating missing compatible configurations and reusing existing compatible
  configurations.
- **FR-007**: The system MUST NOT update, delete, archive, or overwrite
  existing Langfuse score configurations.
- **FR-008**: The system MUST treat user-owned score configuration references as
  externally managed and MUST NOT create or modify them.
- **FR-009**: The system MUST prepare evaluator-ready context for baseline and
  candidate outputs while preserving blind evaluator requirements that exclude
  provider, model, and vendor identity from judge inputs.
- **FR-010**: The system MUST support partial provider failures by recording
  successful outputs and failed item context in the same live run.
- **FR-011**: The system MUST route selected review items to an existing
  Langfuse Human Annotation Queue when a queue ID is configured.
- **FR-012**: The system MUST avoid duplicate annotation queue items for the
  same run, trace, and queue.
- **FR-012a**: The system MUST select random human-review calibration items
  deterministically from dataset item identity so baseline and compatible
  candidate runs use the same random sample when dataset version and review
  policy are unchanged.
- **FR-013**: The system MUST expose clear user-facing results for live sync,
  baseline run, candidate run, review selection, and export commands, including
  counts and identifiers needed to open or inspect Langfuse records.
- **FR-014**: The system MUST fail with actionable messages when live Langfuse
  credentials, workspace access, provider credentials, baseline compatibility,
  dataset sync, score configuration sync, or annotation queue routing are
  invalid.
- **FR-015**: The system MUST keep automated tests runnable without live
  Langfuse or provider credentials, while allowing separate live smoke checks
  for configured environments.
- **FR-016**: The live MVP MUST prove live provider execution for the Azure
  OpenAI baseline path; live candidate provider execution is outside the live
  MVP scope and may be represented by fake or dry-run candidate output.
- **FR-017**: The system MUST NOT persist live baseline registry state in local
  files for normal operation.
- **FR-018**: The system MUST include opt-in live integration tests that use
  configured credentials to exercise real Langfuse and Azure OpenAI baseline
  execution end to end.
- **FR-019**: The system MUST create a distinct live run for each baseline or
  candidate execution command, even when the project, model, parameters, and
  dataset are unchanged.
- **FR-020**: The system MUST keep dataset sync, score configuration sync, and
  annotation queue routing idempotent so repeat setup or review commands do not
  create duplicate assets or queue items.

### Key Entities *(include if feature involves data)*

- **Live Langfuse Workspace**: The remote experiment system that stores datasets,
  traces, runs, scores, evaluator outputs, and annotation queue items.
- **Langfuse Dataset Record**: A synced or resolved dataset with stable item
  identity and version or derived compatibility version information used for
  live runs.
- **Live Run Record**: A baseline or candidate execution record with project,
  dataset, model, prompt, evaluator, metadata, timestamps, and item outcomes.
- **Persisted Baseline Reference**: A reusable baseline identity and
  compatibility fingerprint stored so future candidate runs can find it.
- **Live Trace Record**: One item-level execution record with input, output or
  failure, trace metadata, links to the live run, and correlation to the
  originating Langfuse Dataset item.
- **Score Configuration Record**: A Langfuse scoring schema required by project
  evaluators, either harness-managed or user-owned.
- **Annotation Queue Item**: A live manual-review item containing review inputs,
  outputs, optional ground truth, selection reason, and trace context.
- **Stable Review Cohort**: A deterministic set of Langfuse Dataset item IDs
  selected for random human calibration across baseline and compatible
  candidate runs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An engineer can run the sample baseline and see all dataset item
  traces in Langfuse within 5 minutes after credentials are configured.
- **SC-002**: A candidate run launched in a separate command execution can reuse
  a previously created compatible baseline without rerunning the baseline.
- **SC-003**: 100% of live baseline and candidate traces include project,
  dataset, prompt version, evaluator set, model, parameter, timestamp, and item
  identity metadata.
- **SC-004**: Incompatible baseline selection fails before any candidate model
  calls are made.
- **SC-005**: A second score configuration sync reuses compatible live score
  configurations without creating duplicates.
- **SC-006**: Review selection routes at least the configured minimum sample to
  the configured annotation queue and skips duplicates on repeat execution.
- **SC-006a**: Running the same candidate command twice creates two distinct
  live candidate runs that both reference the same compatible baseline.
- **SC-006b**: Baseline and compatible candidate runs select the same random
  calibration dataset item IDs for human annotation when using the same dataset
  version and review policy.
- **SC-007**: Default automated tests complete without requiring live Langfuse,
  OpenAI, Azure, or Ollama credentials.
- **SC-008**: An opt-in live integration test workflow covers dataset sync,
  score config sync, live Azure OpenAI baseline execution, fake or dry-run
  candidate execution, review routing, and CSV export.

## Assumptions

- The existing offline harness MVP remains the starting point and should not be
  replaced with a service, dashboard, database, or inference gateway.
- Langfuse remains the system of record for live experiment data.
- Users provide valid Langfuse credentials and model provider credentials
  through environment variables or a secret manager.
- Live integration tests are intentionally separate from the default automated
  test suite and require explicit execution by a developer with credentials.
- Human Annotation Queues are created manually in Langfuse for the MVP; automatic
  queue creation remains backlog work.
- Live evaluator execution and score generation remain Langfuse-owned; the
  harness prepares context and syncs required score configuration schemas.
- Local CSV/JSON authoring remains supported for low-friction project setup, but
  valid live runs use synced or resolved Langfuse Dataset identity.
- Live candidate provider calls are deferred beyond this MVP; the live MVP still
  persists candidate comparison records using fake or dry-run candidate outputs.
