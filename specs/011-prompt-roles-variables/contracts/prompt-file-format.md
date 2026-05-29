# Contract: Markdown Prompt File Format

## Legacy Single-Text Prompt

A Markdown prompt file without role headings is a single-text prompt.

```markdown
Rewrite the following text:

{dataset.input}
```

Legacy `{{input}}` behavior may remain supported for existing projects, but new
dataset-aware prompts should use `{dataset.input}`.

## Role-Based Prompt

A role-based prompt file uses level-2 headings in the form
`## role: <role-label>`.

```markdown
## role: system

You are a careful editor.

## role: user

Rewrite the following text:

{dataset.input}

## role: reviewer-note

Preserve domain-specific terminology.
```

Rules:

- Each `## role: <role-label>` section becomes one ordered message.
- Role labels are generic. `system`, `user`, and `assistant` are examples, not
  the complete set.
- Message content is the Markdown between one role heading and the next role
  heading.
- Role order is preserved exactly.
- Non-empty content before the first role heading is invalid in a role-based
  file.
- `## role:` with no label is invalid.

## Dataset Variables

Variables use single braces and the `dataset.*` namespace.

```markdown
{dataset.input}
{dataset.ground_truth}
```

Rules:

- `{dataset.input}` resolves to the active dataset row's `input` value.
- Other `{dataset.<field>}` placeholders resolve to the matching dataset column.
- Referenced columns must exist in the selected dataset.
- Empty row values render as empty strings.
- Braces inside dataset values are literal data and are not reparsed.
- Unmatched braces are invalid.
- Environment variables, credentials, and arbitrary runtime values are not
  substituted through this syntax.
