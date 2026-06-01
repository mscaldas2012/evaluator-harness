# Langfuse Automation Backlog

The harness automates the Langfuse setup required to execute valid runs:
dataset sync/resolve, prompt sync, harness-managed score config sync, trace
logging, baseline references, LLM-as-Judge evaluator setup, annotation queue
setup, and configured annotation queue routing. The items below track
additional automation candidates so they can be implemented deliberately.

| ID | Automation Candidate | MVP Status | Notes |
| --- | --- | --- | --- |
| BL-001 | Evaluator prompt publication | Done | `sync-prompts` and `sync-all` publish task and evaluator prompts to Langfuse prompt management and record Langfuse prompt versions. |
| BL-002 | Evaluator setup | Done | `sync-judge-evaluators` and `sync-all` create or resolve Langfuse evaluator configs and variable mappings from project YAML. |
| BL-003 | Human Annotation Queue setup | Done | `sync-annotation-queue` and `sync-all` create or resolve managed queues. `run` automatically selects review items unless `--skip-human-review` is passed. |
| BL-004 | Dataset creation from traces | Backlog | Create or extend Langfuse datasets from selected traces or observations. |
| BL-005 | Comparison workspace setup | Backlog | Create saved views, tags, or dashboard links for common baseline-vs-candidate comparisons. |
| BL-006 | Scheduled regression runs | Backlog | Configure CI or scheduled jobs for recurring evaluations and regression alerts. |
| BL-007 | Evaluator calibration support | Backlog | Track human labels, evaluator disagreements, drift summaries, and calibration datasets. |
| BL-008 | LLM-as-Judge evaluator setup | Done | Create, reuse, audit, and safely update harness-managed evaluator jobs from rendered setup. Superseded harness-managed versions are inactivated where supported; evaluator resources are never deleted. |
| BL-009 | Evaluator score source audit | Backlog | Periodically verify human annotation scores use `ANNOTATION`, LLM-as-Judge scores use `EVAL`, and both point at the same canonical score config. |
| BL-010 | Score config compatibility repair guidance | Backlog | Detect incompatible active score configs and generate precise manual cleanup instructions instead of mutating user-owned or conflicting global configs. |

Backlog items must preserve the Langfuse-first boundary: the harness may
configure Langfuse resources, but it should not become a dashboard, custom
scoring engine, observability stack, or production inference service.
