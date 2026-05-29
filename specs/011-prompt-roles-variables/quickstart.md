# Quickstart: Prompt Roles and Variables

## 1. Create a Role-Based Prompt File

Create a Markdown prompt file with role headings:

```markdown
## role: system

You are a careful editor. Preserve the author's intent.

## role: user

Rewrite the following text:

{dataset.input}
```

Role labels are generic. `system`, `user`, and `assistant` are common examples,
but project-specific labels may be used when the selected provider can send
them faithfully.

## 2. Reference the Prompt from Project Config

Use the normal `task_prompt` reference:

```yaml
task_prompt:
  path: prompts/dfe/task_prompt.md
  version: v1
  template_variables:
    - dataset.input
```

Candidate overrides replace the full prompt:

```yaml
candidates:
  - name: dfe-role-prompt-v2
    provider: openai_compatible
    auth_mode: azure_client_credentials
    model: gpt-4.1
    task_prompt:
      path: prompts/dfe/task_prompt_v2.md
      version: v2
      template_variables:
        - dataset.input
```

## 3. Validate the Project

```powershell
uv run python run_experiment.py validate `
  --project configs/projects/rewrite_quality.yaml
```

Validation should fail before model calls when:

- A role heading is malformed.
- Content appears before the first role heading in a role-based file.
- A `{dataset.<field>}` placeholder references a missing dataset column.
- The selected provider cannot send the configured role labels exactly.

## 4. Run Baseline or Candidate

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode baseline
```

```powershell
uv run python run_experiment.py run `
  --project configs/projects/rewrite_quality.yaml `
  --mode candidate `
  --candidate dfe-role-prompt-v2 `
  --baseline latest-compatible
```

Expected behavior:

- Role order is preserved.
- `{dataset.input}` is replaced with the active dataset row value.
- Empty row values render as empty strings.
- OpenAI-compatible providers receive chat messages when roles are supported.
- Prompt identity metadata distinguishes role-based prompts from single-text
  prompts.

## 5. Inspect Langfuse and Exports

In Langfuse, inspect traces and observations for prompt metadata:

- prompt version
- prompt shape
- ordered prompt roles
- baseline and candidate prompt identities
- dataset item identity

Local exports should retain enough prompt metadata to compare runs that used
different prompt shapes or role labels.
