# Feature Specification: Azure API-Key Candidate Provider

**Feature Branch**: `009-azure-api-key-provider`

**Created**: 2026-05-28

**Status**: Draft

**Input**: User description: "I've deployed mistral-large-3 on a different azure account that uses API Keys instead of tenant/client. can you implement a LLM provider so I can use this as a candidate?" Refined scope: support any Azure-hosted model deployment that is accessed through an endpoint and API key; `mistral-large-3` is the first concrete example, not a model-specific limitation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Azure Endpoint API-Key Candidate (Priority: P1)

A harness user can add any Azure-hosted candidate model deployment that authenticates with an API key and endpoint, run it through the existing experiment workflow, and compare its results against the configured baseline without needing tenant ID, client ID, client secret, or token scope credentials for that candidate.

**Why this priority**: This is the direct blocker for evaluating models deployed in Azure accounts that expose endpoint/API-key access instead of tenant/client authentication.

**Independent Test**: Can be fully tested by adding an API-key-authenticated Azure candidate to a project configuration, running the candidate workflow, and confirming outputs, traces, observations, and comparison metadata are produced for that candidate.

**Acceptance Scenarios**:

1. **Given** a project has an Azure endpoint/API-key candidate with valid endpoint, deployment or model identifier, service version when required, API key reference, and generation parameters, **When** the user runs the candidate workflow, **Then** the harness sends prompts to that candidate and records model outputs for comparison.
2. **Given** the project baseline uses tenant/client credentials and a candidate uses API-key credentials, **When** the project is validated and run, **Then** both models are accepted and each model uses only its configured authentication method.
3. **Given** Langfuse tracing is enabled, **When** the API-key candidate produces an output, **Then** the trace and model-output observation include the same project, run, provider, model, and evaluator-targeting metadata expected from other live candidates.
4. **Given** multiple Azure-hosted models are configured in one project, **When** the harness creates provider instances, **Then** each baseline or candidate uses its own explicit `auth_mode` and credential references rather than auto-detecting credentials from the environment.

---

### User Story 2 - Configure Secrets Safely (Priority: P2)

A harness user can configure the API-key candidate using environment variable references so no API key value is committed to project files, docs, traces, error messages, or local result artifacts.

**Why this priority**: API-key-backed Azure deployments rely on bearer secrets, so safe secret handling is required before any such candidate can be used reliably.

**Independent Test**: Can be tested by validating a project that stores only environment variable names, running with the secret set in the environment, and verifying that command output, trace metadata, errors, and generated files do not expose the secret value.

**Acceptance Scenarios**:

1. **Given** a project configuration contains an API-key candidate, **When** the configuration is reviewed, **Then** it contains only environment variable names for credentials and not literal secret values.
2. **Given** the API key environment variable is missing, **When** the user runs validation or execution, **Then** the harness reports the missing variable name with an actionable message and does not print any secret value.
3. **Given** the Azure service returns an authentication or authorization error, **When** the harness reports the failure, **Then** the message is redacted and identifies the candidate that failed.

---

### User Story 3 - Keep Existing Providers Stable (Priority: P3)

A harness user can continue running existing Azure tenant/client, Ollama, and dry-run providers without changing their project configuration or behavior.

**Why this priority**: The new provider path must not regress the baseline and local candidate workflows already used by the harness.

**Independent Test**: Can be tested by running the existing validation and non-live test suite with no changes to existing provider configurations.

**Acceptance Scenarios**:

1. **Given** an existing project uses Azure tenant/client credentials, **When** the project is validated or run, **Then** the current credential requirements and request behavior remain unchanged.
2. **Given** an existing project uses local or dry-run candidates, **When** the project is validated or run, **Then** those providers remain unaffected by the new API-key support.

### Edge Cases

- Missing API key, endpoint, service version when required, deployment or model identifier, or generation parameters must fail before or during execution with an actionable provider-specific error.
- Literal API key values in committed project configuration must be rejected or clearly identified as unsafe.
- Authentication, permission, quota, throttling, timeout, malformed response, and unsupported-parameter failures from the Azure-hosted candidate must be reported without leaking credentials.
- Candidate names and model identifiers may include Azure deployment naming characters and must remain usable in Langfuse metadata and local reports.
- The API-key candidate must still work when the baseline is hosted in a different Azure account using tenant/client credentials.
- Multiple baselines or candidates may reference different Azure accounts, endpoints, API versions, and auth modes in the same project without credential cross-talk.

## Requirements *(mandatory)*

### Experiment Requirements

- **Project**: Feature MUST allow project configurations to define an Azure-hosted API-key-authenticated candidate model alongside existing baseline and candidate model configurations.
- **Dataset**: Feature MUST preserve support for existing local CSV datasets with an `input` column.
- **Langfuse Logging**: Feature MUST log API-key candidate traces, observations, run metadata, provider metadata, model metadata, baseline references, evaluator metadata, and comparison metadata consistently with other live candidates.
- **Prompt and Evaluator Versioning**: Feature MUST preserve existing prompt version and evaluator version metadata for runs that include the API-key candidate.
- **Baseline**: Feature MUST consume the existing configured baseline reference and MUST NOT require the baseline to use the same Azure account or authentication method as the candidate.
- **Human Review**: Feature MUST preserve existing Human Annotation Queue routing and review selection behavior for outputs produced by the API-key candidate.

### Functional Requirements

- **FR-001**: Users MUST be able to configure a candidate model that authenticates to an Azure-hosted model endpoint with an API key by providing endpoint, deployment or model identifier, service version, API key environment variable reference, and generation parameters through project configuration.
- **FR-002**: For Azure OpenAI deployment-style endpoints, users MUST provide an API/service version environment variable reference; future endpoint shapes that do not require a service version MUST declare that explicitly in configuration and validation.
- **FR-003**: The system MUST NOT require tenant ID, client ID, client secret, or token scope references for API-key-authenticated candidates.
- **FR-004**: The system MUST continue to support tenant/client-authenticated Azure models without configuration changes.
- **FR-005**: The system MUST reject or fail safely when required API-key candidate configuration or environment variables are missing.
- **FR-006**: The system MUST keep literal secret values out of project configuration, Langfuse trace metadata, local reports, generated artifacts, command output, and exception messages.
- **FR-007**: The system MUST record API-key candidate outputs with the same run identity, project identity, dataset identity, prompt identity, baseline reference, evaluator targeting metadata, and observation role metadata used by other candidates.
- **FR-008**: The system MUST allow the API-key candidate to participate in the existing candidate run workflow and downstream Langfuse evaluator and human review workflows.
- **FR-009**: The system MUST provide a clear example configuration for an Azure-hosted API-key candidate, using `mistral-large-3` only as a sample deployment.
- **FR-010**: The system MUST report Azure service failures with candidate name, deployment or model identifier, status category when available, and redacted diagnostic text.
- **FR-011**: The system MUST treat Azure endpoint/API-key and Azure tenant/client authentication as variants of the same Azure-compatible provider family rather than requiring separate user-facing workflow commands.
- **FR-012**: The system MUST instantiate provider behavior per configured baseline or candidate so one project can safely use different Azure accounts, endpoints, auth modes, and credential refs in the same run.
- **FR-013**: The system MUST select authentication from explicit project configuration and MUST NOT auto-detect auth mode from environment variables that happen to be set.
- **FR-014**: Documentation and examples SHOULD use project/model-specific environment variable names to prevent credential collisions across baselines and candidates.

### Key Entities *(include if feature involves data)*

- **Azure-Compatible Model Config**: A baseline or candidate model configuration for an Azure-hosted model deployment. Key attributes include model name, provider family, explicit authentication mode, endpoint reference, deployment or model identifier, service version reference, credential references, and generation parameters.
- **API-Key Candidate Model**: A configured candidate model that specializes Azure-Compatible Model Config for endpoint/API-key authentication. It contributes the API key credential reference and, for Azure OpenAI deployment-style endpoints, a required service version reference.
- **Credential Reference**: A non-secret environment variable name used to retrieve a required provider credential or service setting at runtime.
- **Provider Failure**: A redacted execution failure associated with a candidate model, including operation, provider, deployment or model identifier, retry context when available, and actionable remediation.
- **Candidate Output Record**: The generated output and metadata recorded for each dataset item, including trace ID, observation ID, provider, model, parameters, token usage when available, latency when available, and baseline reference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can add an Azure endpoint/API-key candidate to an existing project and run validation successfully in under 5 minutes once environment variables are set.
- **SC-002**: 100% of required API-key candidate fields produce explicit validation or runtime errors when missing.
- **SC-003**: 100% of error paths covered by tests avoid printing configured secret values.
- **SC-004**: Existing non-live provider tests and project validation tests continue to pass after the feature is added.
- **SC-005**: A live candidate run with valid API-key credentials records one Langfuse trace and one model-output observation per dataset item attempted.
- **SC-006**: The API-key candidate can be compared against the existing baseline using the same evaluator and human review workflows as other candidates.

## Assumptions

- The first concrete example is `mistral-large-3`, but the feature is intended for any Azure-hosted model deployment that exposes compatible endpoint/API-key access.
- The project configuration will store environment variable names only; actual API keys and endpoint secrets remain in `.env`, the shell environment, or a secret manager.
- The existing baseline may continue using tenant/client credentials in a different Azure account.
- Authentication mode is explicit in each baseline or candidate config. The harness does not infer auth mode by checking which environment variables are set.
- Environment variable names are chosen by the user, but examples use project/model-specific names such as `REWRITE_QUALITY_BASELINE_AZURE_ENDPOINT` and `REWRITE_QUALITY_MISTRAL_LARGE_3_API_KEY`.
- The feature should extend the existing candidate workflow rather than introducing a separate command or local judging engine.
- The initial scope is candidate generation. It does not add a new evaluator judge model connection type unless needed by a later feature.
