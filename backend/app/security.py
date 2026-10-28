import hmac


def is_authorized(provided: str, expected: str) -> bool:
    """Compara a chave enviada com a esperada. Sem chave configurada, nega tudo."""
    if not expected:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())
