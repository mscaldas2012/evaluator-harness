from __future__ import annotations


_TLS_TRUSTSTORE_CONFIGURED = False


def configure_tls_truststore() -> bool:
    """Use the OS certificate store when truststore is installed.

    This is especially important on Windows workstations behind enterprise TLS
    inspection, where Python's bundled CA set may not include the corporate CA.
    """
    global _TLS_TRUSTSTORE_CONFIGURED
    if _TLS_TRUSTSTORE_CONFIGURED:
        return False
    try:
        import truststore
    except Exception:
        return False
    truststore.inject_into_ssl()
    _TLS_TRUSTSTORE_CONFIGURED = True
    return True
