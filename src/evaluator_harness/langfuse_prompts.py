from __future__ import annotations

from typing import Any

from evaluator_harness.errors import LangfuseError
from evaluator_harness.langfuse_mappers import object_to_prompt_dict


def list_prompt_versions_workflow(
    owner: Any,
    name: str | None = None,
) -> list[dict[str, Any]]:
    owner.check_reachable(operation="list-prompts")
    owner.calls.append(("list_prompt_versions", {"name": name}))
    if owner.client is not None:
        return live_list_prompt_versions(owner, name=name)
    if name is not None:
        return list(owner.prompt_versions.get(name, []))
    return [
        prompt for versions in owner.prompt_versions.values() for prompt in versions
    ]


def create_prompt_version_workflow(
    owner: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    owner.check_reachable(operation="create-prompt")
    owner.calls.append(("create_prompt_version", payload))
    if owner.client is not None:
        return live_create_prompt_version(owner, payload)
    versions = owner.prompt_versions.setdefault(str(payload["name"]), [])
    created = {"version": len(versions) + 1, **payload}
    versions.append(created)
    return created


def find_prompt_version_workflow(
    owner: Any,
    name: str,
    *,
    label: str,
) -> dict[str, Any] | None:
    for prompt in owner.list_prompt_versions(name):
        if prompt_has_label(prompt, label):
            return prompt
    return None


def live_list_prompt_versions(
    owner: Any,
    *,
    name: str | None = None,
) -> list[dict[str, Any]]:
    prompts_client = getattr(getattr(owner.client, "api", None), "prompts", None)
    list_prompts = getattr(prompts_client, "list", None)
    get_prompt = getattr(prompts_client, "get", None)
    if not callable(list_prompts):
        return []
    versions: list[dict[str, Any]] = []
    page_number = 1
    while True:
        try:
            page = list_prompts(name=name, page=page_number, limit=100)
        except Exception as exc:
            raise LangfuseError(f"Unable to list Langfuse prompts: {exc}") from exc
        versions.extend(_prompt_versions_from_page(page, name, get_prompt))
        meta = getattr(page, "meta", None)
        total_pages = int(getattr(meta, "total_pages", page_number) or page_number)
        if page_number >= total_pages:
            break
        page_number += 1
    return versions


def live_create_prompt_version(owner: Any, payload: dict[str, Any]) -> dict[str, Any]:
    prompts_client = getattr(getattr(owner.client, "api", None), "prompts", None)
    create = getattr(prompts_client, "create", None)
    if not callable(create):
        raise LangfuseError("Installed Langfuse SDK does not expose prompt creation")
    try:
        request = _prompt_create_request(payload)
        return object_to_prompt_dict(create(request=request))
    except Exception as exc:
        raise LangfuseError(
            f"Unable to create Langfuse prompt {payload.get('name')}: {exc}"
        ) from exc


def prompt_has_label(prompt: dict[str, Any], label: str) -> bool:
    labels = prompt.get("labels") or []
    if label in labels:
        return True
    config = prompt.get("config") or {}
    return isinstance(config, dict) and config.get("artifact_version") == label


def _prompt_versions_from_page(
    page: Any,
    name: str | None,
    get_prompt: Any,
) -> list[dict[str, Any]]:
    versions: list[dict[str, Any]] = []
    for item in getattr(page, "data", None) or []:
        meta = object_to_prompt_dict(item)
        prompt_name = str(meta.get("name") or name or "")
        prompt_versions = meta.get("versions") or []
        if callable(get_prompt) and prompt_versions:
            versions.extend(
                _resolved_prompt_versions(get_prompt, prompt_name, prompt_versions)
            )
        else:
            versions.append(meta)
    return versions


def _resolved_prompt_versions(
    get_prompt: Any,
    prompt_name: str,
    prompt_versions: list[Any],
) -> list[dict[str, Any]]:
    versions: list[dict[str, Any]] = []
    for version in prompt_versions:
        version_number = (
            version.get("version") if isinstance(version, dict) else version
        )
        try:
            versions.append(
                object_to_prompt_dict(
                    get_prompt(prompt_name, version=int(version_number), resolve=False)
                )
            )
        except Exception:
            continue
    return versions


def _prompt_create_request(payload: dict[str, Any]) -> Any:
    if payload.get("type") == "chat":
        from langfuse.api.prompts.types.chat_message import ChatMessage
        from langfuse.api.prompts.types.create_chat_prompt_request import (
            CreateChatPromptRequest,
        )
        from langfuse.api.prompts.types.create_chat_prompt_type import (
            CreateChatPromptType,
        )

        return CreateChatPromptRequest(
            name=payload["name"],
            type=CreateChatPromptType.CHAT,
            prompt=[
                ChatMessage(role=message["role"], content=message["content"])
                for message in payload["prompt"]
            ],
            labels=payload.get("labels"),
            tags=payload.get("tags"),
            config=payload.get("config"),
            commit_message=payload.get("commit_message"),
        )

    from langfuse.api.prompts.types.create_text_prompt_request import (
        CreateTextPromptRequest,
    )
    from langfuse.api.prompts.types.create_text_prompt_type import (
        CreateTextPromptType,
    )

    return CreateTextPromptRequest(
        name=payload["name"],
        type=CreateTextPromptType.TEXT,
        prompt=str(payload["prompt"]),
        labels=payload.get("labels"),
        tags=payload.get("tags"),
        config=payload.get("config"),
        commit_message=payload.get("commit_message"),
    )
