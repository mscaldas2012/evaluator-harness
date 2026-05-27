# Langfuse Contract: Annotation Queues

## Queue Creation

Managed queue sync creates a Langfuse Human Annotation Queue with:

- name: project-managed queue name using
  `EH_<project-slug>_<project-version>_review_<review-policy-version>` unless
  explicitly configured
- description: project identity and review policy version
- score config IDs: resolved project evaluator score config IDs

Expected result:

- Langfuse returns a queue ID.
- The harness stores a non-secret local reference to that queue ID.
- Repeated sync resolves the existing compatible queue.

## Queue Lookup

Queue lookup supports:

- get queue by known queue ID
- list queues to find compatible managed queue names when local state is
  missing

Compatibility checks:

- queue name matches the managed name
- score config IDs are compatible with the current evaluator set
- local reference project identity matches the current project

## Queue Item Routing

Review routing adds selected trace objects to the resolved queue.

Required routing fields:

- queue ID
- object ID: trace ID for the selected item
- object type: trace
- status: pending or equivalent default review state

Harness-side metadata retained for reporting:

- run ID
- dataset item ID
- selection reason
- selection bucket
- baseline or candidate context

## Error Handling

The harness must surface clear errors for:

- queue creation unavailable in the configured Langfuse deployment
- unauthorized queue creation
- inaccessible user-owned queue ID
- duplicate queue item attempts
- missing score config IDs

Duplicate queue item attempts should not fail the whole review command when the
item is already queued for the same queue and trace.
