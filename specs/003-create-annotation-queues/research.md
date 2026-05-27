# Research: Create Annotation Queues

## Decision: Use Langfuse Annotation Queues For Managed Review Queues

Langfuse exposes annotation queue operations for creating queues, listing
queues, reading queues, and adding queue items. The installed Langfuse SDK also
exposes these operations through `client.api.annotation_queues`.

**Rationale**: This satisfies the Langfuse-first principle. The harness should
not create a local human review queue or custom review workflow when Langfuse
already owns that capability.

**Alternatives considered**:

- Keep requiring `LANGFUSE_ANNOTATION_QUEUE_ID`: rejected because it blocks
  onboarding and live review smoke tests.
- Store review items locally and upload later: rejected because Langfuse should
  remain the system of record.

## Decision: Queue Creation Depends On Score Config Sync

Managed queue creation requires the score config IDs associated with the review
workflow. The harness will sync score configs first, then create/reuse the
annotation queue using the resolved score config IDs.

**Rationale**: This keeps queue setup aligned with project evaluators and avoids
creating queues that cannot capture the intended review dimensions.

**Alternatives considered**:

- Create queues without score configs: rejected because the queue would not
  reflect project evaluator expectations.
- Ask users to copy score config IDs manually: rejected because score config
  sync already manages those IDs.

## Decision: Persist Queue References In Lightweight Local State

Managed queue references will be stored in `.evaluator-harness/queue-references/`
using non-secret metadata: project identity, review policy version, queue name,
queue ID, ownership, score config IDs, and sync timestamp.
The filename convention is
`<project-slug>__<project-version>__<review-policy-version>.json`.

**Rationale**: The harness needs to reuse the same queue across future command
executions without relying on a manually exported environment variable. This
fits the existing minimal local state rule because it stores only durable
references, not experiment results or secrets.

**Alternatives considered**:

- Write the queue ID back into committed project YAML: rejected because local
  users may not want generated environment-specific IDs in repo config.
- Store queue references only in Langfuse metadata: rejected for MVP because
  local commands still need a deterministic way to resolve the managed queue
  before routing.

## Decision: Prefix Managed Queue Names With EH

Harness-managed Langfuse queues use the format
`EH_<project-slug>_<project-version>_review_<review-policy-version>`.

**Rationale**: The prefix makes harness-created queues easy to recognize in
Langfuse, while the project, version, and review policy components prevent
cross-project or incompatible policy collisions.

**Alternatives considered**:

- Use free-form project names only: rejected because ownership would be unclear
  in Langfuse.
- Include dataset version in the queue name: rejected for MVP because the queue
  belongs to the project review workflow, while item-level compatibility remains
  captured by review cohort and run metadata.

## Decision: Keep User-Owned Queue References Read-Only

Projects may still declare a user-owned queue ID. The harness will validate and
route to it, but will not create, update, delete, or rename it.

**Rationale**: Some teams will share queues across projects or manage reviewer
assignment manually in Langfuse.

**Alternatives considered**:

- Force all projects into harness-managed queues: rejected because it would
  remove useful Langfuse workflow flexibility.

## Decision: Preserve Environment Override For Compatibility

`LANGFUSE_ANNOTATION_QUEUE_ID` remains an optional override for ad hoc live
testing and backwards compatibility, but it is no longer required for
project-managed queues.

**Rationale**: Existing live test habits should continue to work while the new
managed path becomes the preferred workflow.

**Alternatives considered**:

- Remove the environment variable entirely: rejected because it would break
  existing manual setups and shared-queue workflows.
