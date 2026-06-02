---
name: evaluator-harness-project-yaml
description: Create or update an Evaluator Harness project YAML from local dataset and prompt artifacts. Use when the user asks to set up a new harness project, generate a configs/projects project YAML file, wire datasets/prompts/evaluator prompts/score configs, or decide baseline, candidate, evaluator, and human review settings for an evaluation project.
---

# Evaluator Harness Project YAML

## Overview

Generate a complete Evaluator Harness project config from the user's dataset,
task prompt, evaluator prompts, and intended model variants. Treat repository
artifacts as the source of truth and ask focused questions only for settings
that cannot be inferred safely.

For detailed field and question checklists, read
`references/project_yaml_checklist.md` when creating or materially changing a
project config.

## Workflow

1. Read local context before asking questions:
   - `AGENTS.md`
   - `README.md`
   - `docs/user-guide.md` when present
   - similar files under `configs/projects/`
   - the provided dataset file and prompt files
   - evaluator rubric CSV or evaluator prompt folder when present

2. Inspect the dataset:
   - Identify row count, column names, likely ID column, input column, optional
     `ground_truth`, `reference_output`, tags, or notes columns.
   - Prefer explicit IDs when unique; otherwise use the repository's existing
     hash/row-position strategy.
   - Do not upload or sync anything to Langfuse unless the user explicitly asks.

3. Inspect prompts:
   - Identify task prompt path, prompt role format, variables, and version.
   - Identify evaluator prompt paths and the variables each prompt requires.
   - Ensure evaluator prompts compare the intended source fields to the output
     being judged.

4. Infer from local patterns:
   - Match naming style, score config prefix style, prompt binding paths, judge
     setup shape, and human review policy shape from existing project YAMLs.
   - Prefer the closest existing project as a template instead of inventing a
     new schema.

5. Ask the user for missing choices:
   - Batch related questions, but keep the list short and actionable.
   - Ask about baseline model/provider/auth/parameters, candidate variants,
     evaluator dimensions, score ranges, Langfuse dataset name, and human review
     sampling only when not inferable.
   - Offer conservative defaults when the repo already shows a local pattern.

6. Create or update `configs/projects/<project>.yaml`:
   - Use `apply_patch` for edits.
   - Keep changes scoped to the new project unless the user asks for shared
     schema or docs changes.
   - Use YAML anchors only when they clearly reduce repetition; explain them if
     the user is unfamiliar.

7. Validate locally:
   - Run `uv run python run_experiment.py validate --project configs/projects/<project>.yaml`.
   - If validation fails, fix local config issues and rerun.
   - Do not treat `validate` as a Langfuse check; sync commands validate remote
     artifacts.

8. Finish with:
   - Created/updated file path.
   - Assumptions made.
   - Validation result.
   - Next commands: usually `sync-all --dry-run`, `sync-all`, then baseline run.

## Guardrails

- Never put secrets in project YAML. Store only environment variable names.
- Do not fabricate model credentials, deployment names, or Langfuse IDs.
- Keep score config names within Langfuse limits used by the harness.
- Keep evaluator dimensions atomic.
- Candidate warnings matter when prompt changes are mixed with model or
  parameter changes; model changes can naturally imply parameter changes.
- For first setup, prefer local CSV datasets unless the user explicitly wants a
  Langfuse-authored dataset reference.
