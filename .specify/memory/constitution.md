<!--
Sync Impact Report
Version change: 1.2.0 -> 1.3.0
Modified principles:
- IX. Local-First Execution updated to require `uv` for Python environment setup and command execution
Added sections:
- None
Removed sections:
- None
Templates requiring updates:
- Updated .specify/templates/plan-template.md
- Updated .specify/templates/tasks-template.md
- Reviewed .specify/templates/spec-template.md; no further change required
- Reviewed .specify/templates/checklist-template.md; no change required
- No .specify/templates/commands directory present
Follow-up TODOs: None
-->

# EvaluatorHarness Constitution

## Core Principles

### I. Langfuse-First

When Langfuse already provides a capability, this project MUST use Langfuse
instead of rebuilding that capability locally. Evaluations, LLM-as-a-Judge,
experiment comparison, baseline comparison, dashboards, trace inspection, and
scoring MUST remain Langfuse-native unless a feature documents a concrete
Langfuse gap and a smaller workaround is impossible. The local harness exists
only to execute experiments and log complete experiment metadata into Langfuse.
For LLM provider calls, supported Langfuse SDK integrations or Langfuse-compatible
provider APIs MUST be preferred when they provide correct generation tracing,
token usage, model metadata, latency, and error capture. Manual tracing MAY be
used only when Langfuse does not provide a compatible integration for the target
provider or when a documented integration gap prevents correct experiment
metadata capture.

Rationale: Langfuse is the system of record. Rebuilding its evaluation or
observability surface locally would increase maintenance cost and distort the
project into a platform it is explicitly not.

### II. Thin Harness Philosophy

The harness MUST remain small, understandable, and locally runnable. Preferred
designs are a Python CLI, simple provider adapters, lightweight YAML or JSON
configuration, CSV or minimal JSON datasets, and explicit control flow. Features
MUST NOT introduce microservices, distributed systems, orchestration frameworks,
enterprise abstractions, or local APIs unless a constitution check records why
the experiment cannot be run without them.

Rationale: The project is an offline experimentation tool, not a production
inference gateway or custom observability stack.

### III. Dataset Simplicity

Datasets MUST be easy for non-engineers to create and edit. A valid project
dataset MUST be runnable from a CSV containing an `input` column. Additional
columns MAY be used for labels, metadata, grouping, expected attributes,
reference outputs, or project-specific context, but complicated schemas MUST be
justified in the feature plan. Minimal JSON is allowed when CSV cannot represent
the source data clearly.

Rationale: Low setup friction is a core product requirement. Dataset complexity
directly slows experimentation.

### IV. Reproducibility

Every experiment MUST log enough information to reproduce the run: project
identity, provider, model name, model parameters, prompt version, evaluator
versions, latency, token usage, timestamps, dataset identity, baseline
reference, run identity, and relevant configuration values. Prompt and
evaluator versions MUST always be tracked. Any feature that changes prompting,
evaluation, provider behavior, model configuration, or dataset loading MUST
preserve this metadata contract.

Rationale: Experiment results without reproducible inputs and configuration are
not useful for model comparison.

### V. Baseline-Centric Evaluation

Evaluation workflows MUST be organized around a designated project baseline
model and parameter set. Baseline outputs MUST be generated, selected, or reused
before candidate comparison. Candidate runs MUST be logged in a way that
Langfuse can compare them against the compatible baseline. The harness MUST NOT
implement custom scoring logic unless the feature documents why Langfuse-native
scoring or comparison cannot satisfy the need.

Rationale: Baseline-relative comparison keeps model evaluation interpretable,
allows later candidate runs to reuse known baselines, and avoids ungrounded
absolute scores.

### VI. Minimal Local State

Langfuse MUST be the system of record for traces, scores, experiments, and run
metadata. Local state SHOULD be limited to filesystem datasets, prompt files,
configuration files, generated baseline outputs when needed for reproducibility,
and temporary run artifacts. Databases, queues, services, and long-lived local
stores MUST NOT be introduced unless the feature plan proves that plain files
and Langfuse cannot support the workflow.

Rationale: The harness is intended to remain portable, disposable, and easy to
reset.

### VII. Human Review Awareness

Automated evaluation results MUST be presented as decision support, not
objective truth. LLM-as-a-Judge workflows MUST acknowledge evaluator bias,
provider bias, verbosity bias, stochastic scoring, and prompt sensitivity.
Features that expose evaluation outcomes SHOULD preserve trace links, review
handles, or Langfuse Human Annotation Queue entries so humans can inspect
disputed or important outputs in Langfuse.

Rationale: Human review remains necessary for calibration, trust, and final
judgment on qualitative project-specific evaluation outcomes.

### VIII. Extensibility Without Complexity

New models and providers MUST be addable with minimal code. Preferred extension
points are provider adapters, config-driven registration, and OpenAI-compatible
APIs. Provider adapters MUST first evaluate whether a Langfuse SDK integration,
instrumented client, or Langfuse-compatible provider API can be used so tracing
is automatic and complete. Manual provider tracing MUST remain a fallback with a
documented reason. The project MUST NOT add elaborate plugin systems, dependency
injection frameworks, or generic extension architectures unless multiple real
providers already require the added structure.

Rationale: Extensibility matters, but abstraction cost must be paid only when it
removes real duplication or unlocks real providers.

### IX. Local-First Execution

The default workflow MUST run locally from a simple command such as
`uv run python run_experiment.py`. Python environment management, dependency
setup, lockfile management, and Python command execution MUST use `uv`. No
Kubernetes, cloud deployment, hosted worker, or managed infrastructure may be
required to execute experiments. Docker support is optional and MUST NOT become
the only supported execution path.

Rationale: The harness is intended to be easy to clone, inspect, modify, and run
on a developer machine.

### X. Practicality Over Perfection

Designs MUST favor understandable code, rapid iteration, explicit behavior, and
fewer abstractions. Premature optimization, speculative infrastructure,
enterprise architecture patterns, and production-platform concerns MUST be
rejected unless tied to a concrete experiment requirement. The smallest clear
solution that logs complete data to Langfuse is preferred.

Rationale: The project exists to accelerate experimentation, not to become a
general-purpose evaluation platform.

## Project Boundaries

EvaluatorHarness is a lightweight offline AI evaluation harness. It is not a
production platform, inference gateway, custom observability stack, or
replacement for Langfuse. Its responsibilities are limited to:

- Running project datasets against multiple LLMs or model parameter sets.
- Capturing provider outputs, timings, token usage, prompt versions, and run
  metadata.
- Tracking project definitions, evaluator versions, and reusable baseline
  references.
- Logging traces and experiment metadata to Langfuse.
- Supporting baseline-first comparison workflows through Langfuse.
- Remaining simple enough for rapid local modification.

Any feature that expands these boundaries MUST document the experiment need, the
Langfuse-native alternative considered, and the simpler local approach rejected.

## Development Workflow

Plans, specifications, and tasks MUST include a constitution check for
Langfuse-first behavior, thin-harness scope, dataset simplicity,
reproducibility metadata, baseline handling, local state, and local-first
execution. Features SHOULD start from the simplest runnable CLI path and add
abstraction only after concrete duplication appears.

Implementation work MUST keep generated artifacts and operational assumptions
transparent. Configuration defaults, dataset requirements, prompt versions, and
provider settings MUST be discoverable from files or Langfuse metadata. Reviews
MUST reject features that hide experiment behavior behind unnecessary services
or custom dashboards.

## Governance

This constitution supersedes conflicting project practices, implementation
plans, and feature-level preferences. Amendments require an explicit update to
this file, a semantic version change, and review of affected Spec Kit templates.

Versioning policy:

- MAJOR: Principle removals, incompatible governance changes, or redefinition
  of project purpose.
- MINOR: New principles, materially expanded constraints, or new mandatory
  workflow gates.
- PATCH: Clarifications, wording fixes, and non-semantic refinements.

Compliance review is required during planning and before implementation.
Constitution violations are allowed only when the relevant plan records the
violation, explains why it is required, and names the simpler alternative that
was rejected.

**Version**: 1.3.0 | **Ratified**: 2026-05-22 | **Last Amended**: 2026-05-22
