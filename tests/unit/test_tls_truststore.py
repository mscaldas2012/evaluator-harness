from __future__ import annotations

import types

from evaluator_harness import certificates


def test_configure_tls_truststore_injects_once(monkeypatch) -> None:
    calls = []
    fake_truststore = types.SimpleNamespace(
        inject_into_ssl=lambda: calls.append("injected")
    )
    monkeypatch.setattr(certificates, "_TLS_TRUSTSTORE_CONFIGURED", False)
    monkeypatch.setitem(__import__("sys").modules, "truststore", fake_truststore)

    assert certificates.configure_tls_truststore() is True
    assert certificates.configure_tls_truststore() is False
    assert calls == ["injected"]


def test_configure_tls_truststore_is_optional(monkeypatch) -> None:
    monkeypatch.setattr(certificates, "_TLS_TRUSTSTORE_CONFIGURED", False)
    monkeypatch.setitem(__import__("sys").modules, "truststore", None)

    assert certificates.configure_tls_truststore() is False
