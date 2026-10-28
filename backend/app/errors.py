class DadosInvalidosError(ValueError):
    """Dados fora do aceitável. Na API vira HTTP 422."""


class OrcamentoInviavelError(DadosInvalidosError):
    """O orçamento de energia não cobre nem o mínimo de leituras exigido."""
