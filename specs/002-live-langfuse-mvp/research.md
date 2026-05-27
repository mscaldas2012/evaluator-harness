# Research: Live Langfuse MVP

## Decision: Use Langfuse Datasets for Valid Live Runs

**Decision**: Local CSV/JSON files remain the easiest way to author datasets,
but valid live baseline and candidate runs must sync or resolve a Langfuse
Dataset first.

**Rationale**: Langfuse-hosted datasets let the SDK create dataset runs that can
be inspected and compared in Langfuse. Local-only experiments create traces but
do not provide the same dataset-run comparison workflow.

**Alternatives considered**:

- Keep datasets local and log only traces: rejected because it weakens
  Langfuse-native experiment comparison.
- Require users to manually create all Langfuse datasets: rejected because it
  raises setup friction and breaks the thin-harness goal.

## Decision: Derive Dataset Compatibility Version When Needed

**Decision**: Baseline compatibility uses the Langfuse dataset version when the
SDK/API exposes one. If no usable version is exposed, the harness derives a
deterministic dataset compatibility version from stable dataset item IDs and
input hashes.

**Rationale**: Baseline lookup must be stable across command executions. A
fallback content-derived version prevents `latest-compatible` from depending on
an ambiguous `latest` label.

**Alternatives considered**:

- Use `latest` whenever Langfuse lacks a version: rejected because it can match
  incompatible dataset content.
- Store a local dataset version file: rejected because live baseline lookup must
  not depend on local state.

## Decision: Store Baseline References in Langfuse Only

**Decision**: Persist baseline run identity and compatibility metadata in
Langfuse run/trace metadata and query Langfuse to resolve `latest-compatible`.
Do not write a live local baseline registry file.

**Rationale**: The user explicitly chose Langfuse-only persistence for live
baseline references. This also keeps the workspace portable across machines and
avoids stale local state.

**Alternatives considered**:

- Keep the existing local baseline registry for live runs: rejected because a
  later command on another machine would not see the baseline.
- Store a local cache plus Langfuse metadata: rejected for MVP because it adds
  synchronization failure modes without enough benefit.

## Decision: Prefer Langfuse OpenAI Integration for Azure OpenAI

**Decision**: The Azure OpenAI baseline adapter should first attempt the
Langfuse OpenAI drop-in integration, including `AzureOpenAI`, when it supports
the required `azure_ad_token`, `azure_endpoint`, `api_version`, timeout,
retry, and default APIM subscription-key headers.

**Rationale**: The constitution prefers Langfuse provider APIs when available
because tracing is more complete and less error-prone. Current Langfuse docs
list an OpenAI drop-in replacement with `AzureOpenAI`.

**Fallback**: If the Langfuse integration cannot support the required Azure AD
client-credentials/APIM shape, use the official OpenAI Azure client and create
Langfuse traces/generation observations manually inside the provider adapter.
The fallback reason must be visible in diagnostics or trace metadata.

## Decision: Fail Fast on Langfuse Before Provider Calls

**Decision**: Live commands that execute models must verify Langfuse
connectivity, authentication, and target workspace access before acquiring
provider tokens or calling models.

**Rationale**: The live MVP is valuable only if results are persisted. A model
call that succeeds while Langfuse is unreachable spends cost without recording
a valid experiment.

## Decision: Sync Only Harness-Managed Score Configs

**Decision**: The harness creates missing compatible score configs only when an
evaluator marks the score as harness-managed. It reuses compatible configs and
fails on incompatible same-name configs. It never updates, archives, or deletes
score configs.

**Rationale**: Langfuse score configs can be shared across the workspace. A
prefix makes harness-created configs identifiable, while no-update behavior
prevents accidental mutation of user-owned evaluation configuration.

**Alternatives considered**:

- Update incompatible score configs automatically: rejected because score
  schemas affect historical and future evaluation meaning.
- Treat all score configs as harness-managed: rejected because teams may manage
  some score dimensions directly in Langfuse.

## Decision: Use Existing Annotation Queues in MVP

**Decision**: The MVP can route selected review items to an existing queue ID
but does not create queues.

**Rationale**: Langfuse supports managing annotation queues via API, but queue
creation requires score config choices, assignees, and review process decisions
that are better handled manually until the run pipeline is proven.

**Backlog**: Add queue creation/resolution automation after the live run path is
stable.

## Decision: Use Stable Dataset-Item Review Cohorts

**Decision**: The random human-review calibration sample is selected
deterministically from stable dataset item IDs. Baseline and compatible
candidate runs use the same random item IDs when dataset version and review
policy are unchanged. Run-specific risk items are added separately.

**Rationale**: Human review is more comparable when annotators inspect the same
dataset items across baseline and candidate runs. Selecting by trace ID or
per-run order would produce different samples for each model and weaken
baseline-vs-candidate interpretation.

**Alternatives considered**:

- Randomize independently per run: rejected because annotations would not be
  directly comparable across models.
- Review only risky run-specific items: rejected because it loses a stable
  calibration sample and biases human review toward failures.

## Decision: Make Live Tests Explicit and Small

**Decision**: Add `pytest.mark.live` integration tests that require explicit
execution and live credentials. Default tests continue to use fakes and mocks.

**Rationale**: The user wants smoke tests that hit Langfuse and Azure OpenAI,
but routine development and CI should remain credential-free unless explicitly
configured.

## Decision: Keep Candidate Execution Dry-Run for This MVP

**Decision**: Candidate runs use a first-class `dry_run` provider/config path
for the live MVP while still creating real Langfuse dataset runs/traces linked
to the persisted baseline.

**Rationale**: The clarified scope is live Langfuse plus live Azure OpenAI
baseline first. Dry-run candidates prove baseline reuse and comparison plumbing
without expanding live model provider scope. Making dry-run explicit avoids
hidden test-only provider injection in user-facing workflows.
