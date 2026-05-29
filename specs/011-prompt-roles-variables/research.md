# Research: Prompt Roles and Variables

## Decision: Use Markdown level-2 role headings

Role-based task prompts will be authored in Markdown files with message
boundaries marked by `## role: <role-label>` headings.

**Rationale**: Project authors already work with Markdown prompt files. Level-2
headings are readable in editors, easy to scan in reviews, and simple to parse
without introducing a new file type or inline project-config message syntax.

**Alternatives considered**:

- Structured YAML messages: precise but moves prompt content into project config
  and makes longer prompts harder to author.
- Frontmatter blocks: workable but less idiomatic for repeated message sections.
- XML-like tags: more custom syntax and noisier for non-technical authors.
- JSON prompts: precise but less friendly for long natural-language prompt text.

## Decision: Keep generic role labels but require exact provider support

Prompt role labels are generic strings; `system`, `user`, and `assistant` are
examples rather than the complete allowed set. The runtime sends configured
roles exactly when the selected provider supports them and fails validation
before model calls when it cannot.

**Rationale**: Generic labels preserve imported or project-specific prompt
semantics. Failing before provider calls avoids silent prompt changes that would
invalidate evaluation results.

**Alternatives considered**:

- Fixed role allowlist: too narrow for the requested feature.
- Automatic fallback mapping: risks silently changing prompt semantics.
- Explicit provider role mapping: useful but adds extra config and is deferred
  to a future feature.
- Flattening to text: loses role semantics and weakens comparison validity.

## Decision: Limit variables to dataset fields

The initial substitution namespace is `dataset.*`, with `{dataset.input}` as the
primary example. Other dataset columns can be referenced as
`{dataset.<field>}`.

**Rationale**: Dataset-scoped substitution covers the requested use case while
keeping security and validation clear. The harness should not use the same
syntax to expose environment variables, credentials, or arbitrary runtime state.

**Alternatives considered**:

- Support arbitrary variable namespaces now: unnecessary scope and harder to
  validate safely.
- Preserve existing `{{input}}` only: does not meet the requested syntax.
- Import variables from external prompt files: deferred until a concrete need.

## Decision: Validate variables against dataset columns

Prompt placeholders are validated against selected dataset columns before live
model calls. Empty per-row values render as empty strings.

**Rationale**: Column-level validation catches prompt typos early while allowing
intentionally blank row data. This keeps runs deterministic and avoids per-row
skips for normal empty values.

**Alternatives considered**:

- Fail on empty row values: too strict for real datasets.
- Validate only during rendering: later feedback and potentially partial runs.
- Leave unresolved placeholders in prompts: silently corrupts model input.

## Decision: Preserve legacy single-text prompts

Existing Markdown prompt files without role headings remain valid single-text
prompts and continue to render through the existing behavior.

**Rationale**: Backward compatibility is required for existing projects and
fixtures. Role-based prompts should be opt-in by file shape.

**Alternatives considered**:

- Require all prompts to migrate: unnecessary churn and a larger blast radius.
- Add a new required prompt type field: more config surface than needed.

## Decision: Expand prompt identity for role-aware prompts

Prompt identity metadata will include prompt shape, ordered role labels, content
hash, version, and variable references. Existing identity fields remain
available for compatibility.

**Rationale**: Reproducibility requires distinguishing a role-based prompt from
a flattened prompt with similar text, and role order can materially affect model
behavior.

**Alternatives considered**:

- Hash only raw file contents: insufficient for exports and trace inspection.
- Store full rendered prompts in identity: too large and may duplicate trace
  payloads unnecessarily.
