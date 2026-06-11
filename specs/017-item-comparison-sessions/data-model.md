# Data Model: Langfuse Item Comparison Sessions

## Comparison Session

Represents the official Langfuse session used to group one dataset item's
baseline trace and candidate trace(s).

**Fields**

- `session_id`: deterministic Langfuse session identifier, US-ASCII and shorter
  than 200 characters
- `project`: project name
- `project_version`: project version
- `dataset_name`: synced Langfuse dataset name or configured dataset identity
- `dataset_version`: synced dataset version or compatibility version
- `baseline_anchor`: baseline run ID for the comparison family
- `dataset_item_id`: local dataset item identity

**Relationships**

- Has one baseline trace for the item when the baseline run completed or failed
  after trace creation.
- Has zero or more candidate traces for the same item and baseline anchor.
- Does not own scores or reports; it only groups traces in Langfuse.

**Validation Rules**

- `session_id` must be deterministic for the same identity inputs.
- `session_id` must be US-ASCII and shorter than 200 characters.
- Different item IDs, project identities, dataset identities, or baseline
  anchors must produce different `session_id` values.

## Baseline Comparison Anchor

Represents the run identity that defines which baseline a candidate is compared
against.

**Fields**

- `baseline_run_id`: run ID of the baseline comparison anchor
- `source`: `baseline_self` for baseline traces or `candidate_reference` for
  candidate traces

**Relationships**

- Baseline traces use their own `run_id` as `baseline_run_id`.
- Candidate traces use `baseline_reference.baseline_run_id`.

**Validation Rules**

- Candidate runs must have an explicit baseline reference before trace logging.
- Missing candidate baseline references raise `ConfigError`.

## Trace Session Link

Represents the fields written to trace logging so Langfuse can create the
official session and operators can diagnose grouping.

**Fields**

- `trace_id`: existing deterministic trace ID
- `run_id`: existing run ID
- `session_id`: official Langfuse session identifier passed to the SDK/client
- `metadata.item_comparison_session_id`: same value for export/debug visibility
- `metadata.item_comparison_session_inputs`: non-secret identity summary used
  to derive the session ID

**Relationships**

- Belongs to one Comparison Session.
- Remains associated with existing dataset run item records, evaluator scores,
  and exports through current trace/run metadata.

**Validation Rules**

- `metadata.item_comparison_session_id` must match the official session field.
- Session metadata must not include prompt text, model output text, credentials,
  or secret values.

## Session Identity Inputs

Represents the canonical payload used to derive `session_id`.

**Fields**

- `project`
- `project_version`
- `dataset_name`
- `dataset_version_or_compatibility`
- `baseline_anchor`
- `dataset_item_id`

**Derivation Rules**

1. Normalize values to strings.
2. Use a stable key order.
3. Hash the canonical payload.
4. Prefix with a short readable namespace such as `eh-item-`.
5. Ensure the final value satisfies Langfuse session constraints.
