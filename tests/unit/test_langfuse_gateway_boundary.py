from __future__ import annotations

from pathlib import Path


def test_active_code_uses_gateway_runtime_boundary() -> None:
    roots = [Path("src"), Path("tests"), Path("scripts")]
    forbidden = (
        "Langfuse" + "Client",
        "langfuse" + "_" + "client",
        "Langfuse" + "Runtime",
        "langfuse" + "_" + "runtime",
    )
    offenders: list[str] = []

    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path}:{token}")

    assert offenders == []
