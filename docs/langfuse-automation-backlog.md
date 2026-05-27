# Langfuse Automation Backlog

The MVP automates only the Langfuse setup required to execute valid runs:
dataset sync/resolve, harness-managed score config sync, trace logging,
baseline references, and configured annotation queue routing. The items below
track additional automation candidates so they can be implemented deliberately.

| ID | Automation Candidate | MVP Status | Notes |
| --- | --- | --- | --- |
| BL-001 | Evaluator prompt publication | Backlog | Publish project evaluator prompts to Langfuse prompt management and record Langfuse prompt versions. |
| BL-002 | Evaluator setup | Backlog | Create or resolve Langfuse evaluator configs and variable mappings from project YAML. |
| BL-003 | Human Annotation Queue setup | Backlog | Create or resolve queues programmatically. MVP requires an existing `annotation_queue_id`. |
| BL-004 | Dataset creation from traces | Backlog | Create or extend Langfuse datasets from selected traces or observations. |
| BL-005 | Comparison workspace setup | Backlog | Create saved views, tags, or dashboard links for common baseline-vs-candidate comparisons. |
| BL-006 | Scheduled regression runs | Backlog | Configure CI or scheduled jobs for recurring evaluations and regression alerts. |
| BL-007 | Evaluator calibration support | Backlog | Track human labels, evaluator disagreements, drift summaries, and calibration datasets. |

Backlog items must preserve the Langfuse-first boundary: the harness may
configure Langfuse resources, but it should not become a dashboard, custom
scoring engine, observability stack, or production inference service.
