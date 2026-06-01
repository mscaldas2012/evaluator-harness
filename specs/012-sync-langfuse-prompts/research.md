# Research: Sync Langfuse Prompts

## Decision: Use Langfuse prompt artifacts through the SDK

**Rationale**: The installed Langfuse SDK exposes prompt operations for listing,
retrieving, creating, and deleting prompt versions. The create request supports
text prompts and chat prompts, labels, tags, config, and commit messages. This
matches the existing prompt parser, which already distinguishes legacy
single-text prompts from role-based message prompts.

**Alternatives considered**:

- Store prompt copies only in trace metadata. Rejected because reviewers would
  not get Langfuse-native prompt visibility or version history.
- Build a local prompt registry. Rejected because Langfuse already provides the
  registry surface and the constitution requires Langfuse-first behavior.
- Fetch prompts from Langfuse at runtime. Rejected for this feature because the
  repository must remain the prompt source of truth.

## Decision: Treat configured prompt_version as a strict release label

**Rationale**: The clarified spec requires users to bump `prompt_version`
whenever prompt content changes. Sync should detect changed content under an
already-synced managed prompt version and fail with remediation rather than
publishing ambiguous versions.

**Alternatives considered**:

- Allow multiple content identities under the same configured version. Rejected
  because it weakens the meaning of prompt versions in reports and reviews.
- Overwrite a remote prompt version. Rejected because it destroys auditability.

## Decision: Use content identity as a conflict and reuse guard

**Rationale**: Content identity lets sync distinguish unchanged content from
changed content and prevents duplicate equivalent prompt versions. It should be
based on normalized prompt content plus prompt shape and role metadata so text
and chat prompts cannot accidentally collide.

**Alternatives considered**:

- Use file modification time. Rejected because it is not stable across clones or
  checkouts.
- Use configured prompt version only. Rejected because it cannot detect changed
  content under the same version label.

## Decision: Keep optional local prompt binding references

**Rationale**: Binding files provide last-known Langfuse prompt references and
ownership metadata without making Langfuse prompt state required for local
runs. This mirrors the existing evaluator binding pattern and supports audit,
conflict detection, and trace metadata enrichment.

**Alternatives considered**:

- No local binding file. Rejected because later runs would have no local way to
  know a prompt was synced without querying Langfuse each time.
- Required local binding file. Rejected because prompt sync must remain
  optional.

## Decision: Record prompt provenance even when sync is skipped

**Rationale**: The run must remain reproducible from repository files. Trace
metadata should always include local prompt path, configured prompt version,
prompt shape, roles when present, and content identity. Synced Langfuse prompt
references are added only when a matching binding or remote record is known.

**Alternatives considered**:

- Only record Langfuse prompt references. Rejected because unsynced projects and
  offline workflows would lose prompt provenance.
- Embed full prompt text in every metadata block. Rejected because traces
  already carry inputs and observations, and prompt artifacts provide a cleaner
  inspection path.

## Decision: Add a dedicated sync-prompts command with dry-run mode

**Rationale**: Prompt publishing has different semantics from dataset sync,
score config sync, and judge evaluator setup. A dedicated command makes the
workflow explicit and supports a no-mutation dry-run path.

**Alternatives considered**:

- Fold prompt sync into validate. Rejected because validate should not mutate
  external systems.
- Fold prompt sync into run. Rejected because prompt sync is optional and should
  not block local-first runs.
