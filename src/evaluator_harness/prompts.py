from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from evaluator_harness.errors import ConfigError


PromptShape = Literal["text", "messages"]

ROLE_HEADING_RE = re.compile(r"^##[ \t]+role:[ \t]*(?P<role>.*)$", re.MULTILINE)
PLACEHOLDER_RE = re.compile(r"(?<!\{)\{([^{}]+)\}(?!\})")


@dataclass(frozen=True)
class DatasetVariableReference:
    raw: str
    namespace: str
    field: str

    @property
    def name(self) -> str:
        return f"{self.namespace}.{self.field}"


@dataclass(frozen=True)
class PromptMessage:
    role: str
    content: str
    index: int
    variable_references: list[DatasetVariableReference] = field(default_factory=list)

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "index": self.index,
            "variable_references": [ref.name for ref in self.variable_references],
        }


@dataclass(frozen=True)
class PromptDefinition:
    path: Path
    version: str | None
    shape: PromptShape
    text: str
    messages: list[PromptMessage] = field(default_factory=list)
    variable_references: list[DatasetVariableReference] = field(default_factory=list)


@dataclass(frozen=True)
class RenderedPromptMessage:
    role: str
    content: str

    def model_dump(self, mode: str = "python") -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class RenderedPrompt:
    shape: PromptShape
    text: str
    messages: list[RenderedPromptMessage] = field(default_factory=list)
    display_text: str = ""

    def __post_init__(self) -> None:
        if not self.display_text:
            object.__setattr__(self, "display_text", rendered_display_text(self))

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return {
            "shape": self.shape,
            "text": self.text,
            "messages": [message.model_dump(mode=mode) for message in self.messages],
            "display_text": self.display_text,
        }


def parse_prompt_file(path: Path | str, *, version: str | None = None) -> PromptDefinition:
    prompt_path = Path(path)
    text = prompt_path.read_text(encoding="utf-8")
    return parse_prompt_text(text, path=prompt_path, version=version)


def parse_prompt_text(
    text: str,
    *,
    path: Path | str = Path("<prompt>"),
    version: str | None = None,
) -> PromptDefinition:
    prompt_path = Path(path)
    role_matches = list(ROLE_HEADING_RE.finditer(text))
    if not role_matches:
        refs = prompt_placeholders(text, path=prompt_path)
        return PromptDefinition(
            path=prompt_path,
            version=version,
            shape="text",
            text=text,
            variable_references=refs,
        )

    first_heading_start = role_matches[0].start()
    if text[:first_heading_start].strip():
        raise ConfigError(f"Prompt {prompt_path} has unassigned content before first role heading")

    messages: list[PromptMessage] = []
    for index, match in enumerate(role_matches):
        role = match.group("role").strip()
        if not role:
            raise ConfigError(f"Prompt {prompt_path} has malformed role heading")
        content_start = match.end()
        content_end = role_matches[index + 1].start() if index + 1 < len(role_matches) else len(text)
        content = text[content_start:content_end].strip("\r\n")
        refs = prompt_placeholders(content, path=prompt_path)
        messages.append(
            PromptMessage(
                role=role,
                content=content,
                index=index,
                variable_references=refs,
            )
        )

    return PromptDefinition(
        path=prompt_path,
        version=version,
        shape="messages",
        text=text,
        messages=messages,
        variable_references=_unique_refs(
            ref for message in messages for ref in message.variable_references
        ),
    )


def prompt_placeholders(
    text: str,
    *,
    path: Path | str = Path("<prompt>"),
) -> list[DatasetVariableReference]:
    prompt_path = Path(path)
    _validate_braces(text, path=prompt_path)
    refs: list[DatasetVariableReference] = []
    for match in PLACEHOLDER_RE.finditer(text):
        raw = match.group(0)
        name = match.group(1).strip()
        parts = name.split(".", 1)
        if len(parts) != 2 or parts[0] != "dataset" or not parts[1]:
            raise ConfigError(
                f"Prompt {prompt_path} contains unsupported placeholder {raw}; "
                "expected {dataset.<field>}"
            )
        refs.append(DatasetVariableReference(raw=raw, namespace=parts[0], field=parts[1]))
    return _unique_refs(refs)


def validate_dataset_variables(
    prompt: PromptDefinition,
    columns: set[str],
) -> None:
    missing = [ref.name for ref in prompt.variable_references if ref.field not in columns]
    if missing:
        raise ConfigError(
            f"Prompt {prompt.path} references missing dataset columns: "
            + ", ".join(missing)
        )


def render_prompt(
    prompt: PromptDefinition,
    row: dict[str, Any],
) -> RenderedPrompt:
    if prompt.shape == "messages":
        messages = [
            RenderedPromptMessage(
                role=message.role,
                content=_render_text(message.content, row),
            )
            for message in prompt.messages
        ]
        return RenderedPrompt(
            shape="messages",
            text="",
            messages=messages,
        )
    return RenderedPrompt(
        shape="text",
        text=_render_text(prompt.text, row),
        messages=[],
    )


def rendered_display_text(rendered: RenderedPrompt) -> str:
    if rendered.shape == "messages":
        return "\n\n".join(
            f"## role: {message.role}\n\n{message.content}" for message in rendered.messages
        )
    return rendered.text


def prompt_identity(path: Path | str, version: str) -> dict[str, Any]:
    definition = parse_prompt_file(path, version=version)
    payload: dict[str, Any] = {
        "shape": definition.shape,
        "text": definition.text if definition.shape == "text" else None,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in definition.messages
        ],
    }
    return {
        "path": Path(path).as_posix(),
        "version": version,
        "content_hash": hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "shape": definition.shape,
        "roles": [message.role for message in definition.messages],
        "variable_references": [ref.name for ref in definition.variable_references],
    }


def _render_text(text: str, row: dict[str, Any]) -> str:
    rendered = text
    for ref in prompt_placeholders(text):
        value = row.get(ref.field)
        rendered = rendered.replace(ref.raw, "" if value is None else str(value))
    for key, value in row.items():
        rendered = rendered.replace("{{" + key + "}}", "" if value is None else str(value))
    return rendered


def _validate_braces(text: str, *, path: Path) -> None:
    scrubbed = text.replace("{{", "").replace("}}", "")
    if scrubbed.count("{") != scrubbed.count("}"):
        raise ConfigError(f"Malformed placeholder in prompt {path}")


def _unique_refs(refs: Any) -> list[DatasetVariableReference]:
    unique: dict[str, DatasetVariableReference] = {}
    for ref in refs:
        unique.setdefault(ref.name, ref)
    return list(unique.values())
