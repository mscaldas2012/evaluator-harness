from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from evaluator_harness.config import ModelConfig
from evaluator_harness.errors import FailureContext, ProviderError, RuntimeDependencyError
from evaluator_harness.providers.base import ModelRequest, ModelResponse


class OpenAICompatibleProvider:
    uses_manual_langfuse_generation = True

    def __init__(
        self,
        config: ModelConfig,
        *,
        credential_class: type | None = None,
        azure_openai_class: type | None = None,
        generator: Callable[[ModelRequest], ModelResponse] | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.config = config
        self._credential_class = credential_class
        self._azure_openai_class = azure_openai_class
        self._generator = generator
        self._max_attempts = max(1, max_attempts)

    def generate(self, request: ModelRequest) -> ModelResponse:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                if self._generator is not None:
                    response = self._generator(request)
                elif self.config.azure is not None and self._has_required_azure_env():
                    response = self._generate_with_azure_openai(request)
                else:
                    response = ModelResponse(
                        output=f"Generated response for: {request.prompt}",
                        raw={"provider_stub": True},
                    )
                return ModelResponse(
                    output=response.output,
                    latency_ms=response.latency_ms,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cost_usd=response.cost_usd,
                    raw={**response.raw, "retry_count": attempt - 1},
                )
            except Exception as exc:  # pragma: no cover - exercised through retries
                last_error = exc

        raise ProviderError(
            f"OpenAI-compatible provider failed after {self._max_attempts} attempts: "
            f"{self._redact(str(last_error))}",
            context=FailureContext(
                operation="model-generate",
                provider=self.config.provider.value,
                model=self.config.model,
                details={"attempts": self._max_attempts},
            ),
        ) from last_error

    def _generate_with_azure_openai(self, request: ModelRequest) -> ModelResponse:
        if self._azure_openai_class is None:
            return self._generate_with_azure_rest(request)
        return self._generate_with_azure_openai_sdk(request)

    def _generate_with_azure_openai_sdk(self, request: ModelRequest) -> ModelResponse:
        client = self._build_azure_openai_client(timeout=60)
        create = client.chat.completions.create
        kwargs = self._completion_kwargs(request)
        try:
            completion = create(**kwargs)
        except Exception as exc:
            if not self._requires_max_completion_tokens(exc):
                raise
            completion = create(
                **self._completion_kwargs(
                    request,
                    use_max_completion_tokens=True,
                )
            )
        choice = completion.choices[0]
        usage = getattr(completion, "usage", None)
        output = choice.message.content or ""
        return ModelResponse(
            output=output,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            raw={
                "tracing_strategy": "manual_langfuse_generation",
                "completion_id": getattr(completion, "id", None),
            },
        )

    def _generate_with_azure_rest(self, request: ModelRequest) -> ModelResponse:
        auth = self._azure_auth_config()
        payload = self._completion_kwargs(request)
        payload.pop("model", None)
        try:
            response_json = self._post_azure_chat_completion(auth, payload)
        except Exception as exc:
            if not self._requires_max_completion_tokens(exc):
                raise
            payload = self._completion_kwargs(request, use_max_completion_tokens=True)
            payload.pop("model", None)
            response_json = self._post_azure_chat_completion(auth, payload)

        choice = response_json["choices"][0]
        message = choice.get("message") or {}
        usage = response_json.get("usage") or {}
        return ModelResponse(
            output=message.get("content") or "",
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw={
                "tracing_strategy": "manual_langfuse_generation",
                "completion_id": response_json.get("id"),
            },
        )

    def _post_azure_chat_completion(
        self,
        auth: dict[str, str],
        payload: dict[str, object],
    ) -> dict[str, Any]:
        try:
            import httpx
        except Exception as exc:  # pragma: no cover - dependency present in normal env
            raise RuntimeDependencyError("httpx is required for Azure OpenAI REST calls") from exc

        endpoint = auth["azure_endpoint"].rstrip("/")
        deployment = quote(self.config.model, safe="")
        url = (
            f"{endpoint}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={auth['api_version']}"
        )
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {auth['token']}",
                "Ocp-Apim-Subscription-Key": auth["subscription_key"],
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        if response.status_code >= 400:
            raise RuntimeDependencyError(
                f"Azure OpenAI REST call failed with {response.status_code}: "
                f"{self._redact(response.text)}"
            )
        return response.json()

    def _completion_kwargs(
        self,
        request: ModelRequest,
        *,
        use_max_completion_tokens: bool = False,
    ) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": self.config.parameters.temperature,
            "top_p": self.config.parameters.top_p,
        }
        token_limit = self.config.parameters.max_tokens
        if token_limit is not None:
            key = (
                "max_completion_tokens"
                if use_max_completion_tokens
                else self.config.parameters.token_limit_parameter
            )
            kwargs[key] = token_limit
        return kwargs

    def _requires_max_completion_tokens(self, exc: Exception) -> bool:
        message = str(exc)
        return "max_tokens" in message and "max_completion_tokens" in message

    def _build_azure_openai_client(self, *, timeout: float):
        if self.config.azure is None:
            raise RuntimeDependencyError("Azure credential references are not configured")

        azure_client_class = self._resolve_azure_openai_client_class()
        auth = self._azure_auth_config()

        return azure_client_class(
            api_version=auth["api_version"],
            azure_endpoint=auth["azure_endpoint"],
            azure_ad_token=auth["token"],
            default_headers={"Ocp-Apim-Subscription-Key": auth["subscription_key"]},
            timeout=timeout,
            max_retries=0,
        )

    def _azure_auth_config(self) -> dict[str, str]:
        if self.config.azure is None:
            raise RuntimeDependencyError("Azure credential references are not configured")

        credential_class = self._resolve_azure_credential_class()
        refs = self.config.azure

        tenant_id = self._required_env(refs.tenant_id_env)
        client_id = self._required_env(refs.client_id_env)
        client_secret = self._required_env(refs.client_secret_env)
        scope = self._required_env(refs.scope_env)
        subscription_key = self._required_env(refs.subscription_key_env)
        api_version = self._required_env(refs.api_version_env)
        azure_endpoint = self._required_env(refs.endpoint_env)

        credential = credential_class(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

        try:
            token = credential.get_token(scope).token
        except Exception as exc:
            raise RuntimeDependencyError(
                f"Error acquiring Azure AD token for scope {scope}: "
                f"{self._redact(str(exc))}"
            ) from exc

        return {
            "token": token,
            "subscription_key": subscription_key,
            "api_version": api_version,
            "azure_endpoint": azure_endpoint,
        }

    def _required_env(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeDependencyError(f"Required environment variable is not set: {name}")
        return value

    def _resolve_azure_credential_class(self) -> type:
        if self._credential_class is not None:
            return self._credential_class
        try:
            from azure.identity import ClientSecretCredential
        except Exception as exc:  # pragma: no cover - dependency present in normal env
            raise RuntimeDependencyError(
                "azure-identity is required for Azure client credential auth"
            ) from exc
        return ClientSecretCredential

    def _resolve_azure_openai_client_class(self) -> type:
        if self._azure_openai_class is not None:
            return self._azure_openai_class
        try:
            from openai import AzureOpenAI
        except Exception as exc:  # pragma: no cover - dependency present in normal env
            raise RuntimeDependencyError("openai.AzureOpenAI is required") from exc
        return AzureOpenAI

    def _has_required_azure_env(self) -> bool:
        if self.config.azure is None:
            return False
        refs = self.config.azure
        return all(
            os.getenv(name)
            for name in (
                refs.tenant_id_env,
                refs.client_id_env,
                refs.client_secret_env,
                refs.scope_env,
                refs.subscription_key_env,
                refs.api_version_env,
                refs.endpoint_env,
            )
        )

    def _redact(self, message: str) -> str:
        redacted = message
        if self.config.azure is None:
            return redacted
        for env_name in (
            self.config.azure.tenant_id_env,
            self.config.azure.client_id_env,
            self.config.azure.client_secret_env,
            self.config.azure.scope_env,
            self.config.azure.subscription_key_env,
            self.config.azure.api_version_env,
            self.config.azure.endpoint_env,
        ):
            value = os.getenv(env_name)
            if value:
                redacted = redacted.replace(value, "[REDACTED]")
        return redacted
