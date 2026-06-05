from __future__ import annotations

from pathlib import Path


def test_provider_final_output_contract_documents_standard_role_filter() -> None:
    contract = Path(
        "specs/015-model-output-targeting/contracts/provider-final-output-contract.md"
    ).read_text(encoding="utf-8")

    assert "target_observation_role: model_output" in contract
    assert "Exactly one final output observation" in contract
    assert "Do not require all providers to use the same observation name" in contract
