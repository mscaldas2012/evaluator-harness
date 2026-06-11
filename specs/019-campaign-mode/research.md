# Research: Campaign Mode

## Decision 1: Campaign mode creates a fresh baseline

**Decision**: A campaign always starts by running a new baseline and uses that exact baseline run ID for all included candidates.

**Rationale**: The specification requires baseline and candidates in one command and requires candidates to reference the campaign baseline. Reusing `latest-compatible` would reintroduce the user confusion this workflow is intended to remove.

**Alternatives considered**:

- Reuse `latest-compatible`: rejected because it can select an older baseline and make the campaign workbook incomplete or surprising.
- Accept an optional existing baseline ID: deferred because it complicates the MVP and overlaps with existing individual candidate run behavior.

## Decision 2: Candidate campaign participation is opt-out

**Decision**: Add candidate-level `exclude-from-campaign: bool = false`; candidates run in campaign mode unless explicitly set to `true`.

**Rationale**: The follow-up request changed the default so normal candidates do not need repetitive YAML. Dry-run, test, expensive, or experimental candidates can still be excluded explicitly.

**Alternatives considered**:

- Exclude all candidates by default: rejected by follow-up request because it adds repetitive YAML for the common campaign case.
- Add a separate project-level campaign list: rejected because it duplicates candidate names and increases config drift.

## Decision 3: Keep campaign execution sequential

**Decision**: Run baseline first, then included candidates sequentially.

**Rationale**: Sequential execution is simplest, keeps progress/output understandable, and avoids introducing concurrency concerns around provider rate limits, human review queue writes, and Langfuse mutations.

**Alternatives considered**:

- Parallel candidate runs: rejected for this feature because it increases failure handling and rate-limit complexity.
- Background campaign scheduler: rejected because it violates the thin local harness scope.

## Decision 4: Reuse existing run, export, and Excel report paths

**Decision**: Campaign mode composes `run(..., mode="baseline")`, `run(..., mode="candidate")`, `export(..., "csv")`, and `create_excel_report(...)`.

**Rationale**: These paths already enforce project validation, sync behavior, baseline compatibility, Langfuse metadata, human review selection, report export, and Excel workbook creation.

**Alternatives considered**:

- Implement a separate campaign runner from lower-level primitives: rejected because it risks diverging from individual run behavior.
- Generate workbook from in-memory run results: rejected because the existing Excel target is explicitly CSV-report based.

## Decision 5: Partial failure is reported, not hidden

**Decision**: The campaign summary includes successful runs, skipped candidates, failed candidates, CSV reports, workbook status, and warnings. Successful outputs remain usable when a later candidate fails.

**Rationale**: The spec requires partial results not be hidden. This is also pragmatic for long-running model evaluations where rerunning successful candidates would waste time and money.

**Alternatives considered**:

- Abort on first candidate failure: rejected because it discards useful work.
- Always return success if baseline succeeds: rejected because failed candidates must be visible to automation and users.
