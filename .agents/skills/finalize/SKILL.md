---
name: finalize
description: Finalize a Speckit feature implementation after the user invokes /finalize or asks to finalize/check in a completed Speckit implementation. Run every available project test and required verification command first, stop immediately if any runnable test fails, and only after all verification passes commit the current changes, push the branch, and open a GitLab merge request with glab.
---

# Finalize

## Overview

Finish a Speckit implementation only when the repository is verifiably green. This workflow is intentionally gated: no commit, push, or merge request is allowed while any available test or required verification command is failing.

## Workflow

1. Read the active feature context before running commands.
   - Read `AGENTS.md` if present.
   - Read the active Speckit `plan.md`, `tasks.md`, and `quickstart.md` when present. Prefer the current branch's matching `specs/<feature>/` directory; otherwise use the Speckit path referenced by `AGENTS.md`.
   - Use `uv` for setup, tests, scripts, and Python tooling.

2. Identify available verification.
   - Include every test command listed in the feature plan, quickstart, or tasks.
   - Include the repository's broad non-live test suite when present, usually `uv run pytest --no-cov -p no:cacheprovider -m "not live"`.
   - Include live tests only when the required credentials and services appear available. If live tests are not available, report them as skipped due to missing prerequisites.
   - Include required project verification commands from the plan, such as Ruff, Pyright, contract tests, integration tests, or feature-specific pytest invocations.
   - Ruff verification may ignore `E501` and `UP042`. Prefer adding `--ignore E501,UP042` to Ruff commands, or use the repository's equivalent Ruff configuration when it already ignores those rules.

3. Run verification before any GitLab write action.
   - Run each available command with `uv run ...` where applicable.
   - If any runnable test or required verification command fails, stop. Do not commit, push, or create a merge request.
   - If Ruff reports only `E501` or `UP042`, rerun Ruff with those rules ignored and continue only if the rerun passes. Any other Ruff failure is blocking.
   - Tell the user which command failed and summarize the failure at a level useful for the next fix.
   - Do not proceed after a failure unless the user explicitly asks for a fix and the fix has been implemented and reverified.

4. Refresh generated project graph after code changes.
   - If `graphify-out/graph.json` exists, run `graphify update .` after verification and before staging so graph metadata is current.
   - If `graphify update .` fails, stop and report the failure. Do not create a merge request.

5. Commit the implementation state.
   - Inspect `git status --short` and `git diff --stat`.
   - Stage the current feature changes, including generated graph updates when present.
   - Use a concise commit message tied to the Speckit feature, for example `Finalize <feature-name>`.
   - Never revert or discard unrelated changes. If the worktree contains changes that clearly do not belong to the feature, pause and ask the user whether to include them.

6. Push and open a GitLab merge request.
   - Use `glab` for GitLab operations.
   - Push the current branch to the GitLab remote.
   - Create a merge request against the repository's default branch unless the user specifies another target.
   - The MR title should name the feature. The MR description must include:
     - Summary of the implementation.
     - Verification commands that passed.
     - Any unavailable tests and the exact reason they were unavailable.
     - Link or reference to the Speckit spec directory when useful.

## GitLab Commands

Prefer non-interactive commands. Useful defaults:

```powershell
git status --short
git diff --stat
git add <feature files>
git commit -m "Finalize <feature-name>"
git push -u origin HEAD
glab mr create --fill --target-branch <default-branch>
```

If `glab mr create --fill` omits important verification detail, use explicit `--title` and `--description` arguments instead.

## Stop Conditions

Stop without committing, pushing, or creating an MR when:

- Any runnable test fails.
- Any required quality or verification command fails, except Ruff findings limited to ignored `E501` or `UP042`.
- `graphify update .` fails when `graphify-out/graph.json` exists.
- The worktree contains changes that cannot confidently be attributed to the feature.
- GitLab authentication, remote discovery, push, or MR creation fails.

## Final Response

When successful, report the commit SHA, branch, merge request URL, and verification commands that passed. When stopped, report the failed command or blocker and state explicitly that no MR was created.
