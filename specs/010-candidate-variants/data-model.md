# Data Model: Candidate Variants

## Candidate Variant

Represents one named candidate alternative for comparison against a compatible
baseline.

**Fields**:

- `name`: stable unique candidate variant name within a project.
- `provider`: provider family used for generation.
- `auth_mode`: explicit authentication mode for the provider.
- `model`: provider model or deployment identifier.
- `task_prompt`: optional candidate prompt override.
- `parameters`: generation settings such as temperature, top-p, token limit,
  and seed.
- `metadata`: optional non-secret variant metadata.

**Validation rules**:

- Candidate names must be unique within a project.
- Existing model-only candidate configs remain valid without `task_prompt`.
- If `task_prompt` is present, it must point to a non-empty prompt file and
  declare all variables required by the project dataset.
- Provider credential rules remain unchanged and must not leak secrets.

## Prompt Identity

Represents the prompt used to produce a baseline or candidate output.

**Fields**:

- `path`: project-relative prompt file path.
- `version`: human-readable prompt version.
- `template_variables`: declared variables required by the prompt.
- `content_hash`: stable non-secret identity derived from prompt content.

**Validation rules**:

- Prompt version is required.
- Prompt content must be non-empty.
- Prompt content must include required placeholders, including `input`.
- Candidate prompt identity and baseline prompt identity must be recorded
  separately when they differ.

## Model Identity

Represents the provider/model side of a variant.

**Fields**:

- `provider`
- `auth_mode`
- `model`
- optional non-secret provider metadata

**Validation rules**:

- Model identity must be available for every baseline and candidate.
- Model identity must not include provider secrets or resolved credential
  values.

## Parameter Identity

Represents generation parameters used by a baseline or candidate.

**Fields**:

- `parameters`: normalized generation parameter mapping.
- `parameter_hash`: stable hash of provider, model, and generation parameters
  for existing compatibility with current metadata.
- `generation_parameter_hash`: stable hash of generation parameters only when
  a provider/model-independent comparison is needed.

**Validation rules**:

- Parameters must be explicit and serializable.
- Parameter identity changes when any configured generation parameter changes.

## Baseline Reference

Identifies the compatible baseline used by candidate variants.

**Fields**:

- `baseline_run_id`
- `langfuse_run_name`
- `project_name`
- `project_version`
- `dataset_name`
- `dataset_version`
- `prompt_version`
- `evaluator_set_id`
- `baseline_model`
- `baseline_parameters_hash`
- `created_at`

**Validation rules**:

- Candidate runs require a compatible baseline reference.
- Candidate prompt identity does not participate in baseline compatibility.
- Baseline prompt identity must remain visible for reproducibility.

## Variant Run

Represents one execution of a candidate variant over a dataset.

**Fields**:

- `run_id`: unique run identity.
- `candidate`: candidate variant name.
- `variant_identity`: stable identity for the configured candidate variant.
- `baseline_reference`: selected baseline reference.
- `dataset_identity`: dataset name, version, compatibility version, and item
  identity.
- `prompt_identity`: candidate prompt identity.
- `baseline_prompt_identity`: baseline prompt identity.
- `model_identity`: candidate model identity.
- `parameter_identity`: candidate parameter identity.

**Validation rules**:

- Repeated runs of the same candidate receive unique run IDs but retain stable
  variant identity when config is unchanged.
- Every trace, evaluator payload, review payload, and export row for a
  candidate run must include enough metadata to recover the variant and
  baseline reference.

## Mixed Variant Confirmation

Represents the pre-run decision required when a candidate changes more than one
comparison axis.

**Fields**:

- `changed_axes`: ordered list containing any of `model`, `prompt`, `params`.
- `confirmed`: boolean derived from `--confirm-mixed-variant` or interactive
  `Y`/`y` input.

**Validation rules**:

- No confirmation is required when zero or one axis changes.
- Confirmation is required when two or more axes change.
- In interactive mode, only `Y` or `y` confirms execution.
- Scripted runs may use `--confirm-mixed-variant`.
