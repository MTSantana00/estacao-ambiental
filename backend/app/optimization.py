"""Pesquisa Operacional: escolhe quantas leituras por hora cada sensor deve fazer.

Modelo (programação linear):
    maximizar    soma(peso_i * x_i)
    sujeito a    soma(energia_i * x_i) <= orcamento     (mJ por hora)
                 min_i <= x_i <= max_i                   (leituras por hora)

x_i = leituras por hora do sensor i (variável contínua; o intervalo entre
leituras é 3600 / x_i segundos). Energia por leitura: E = V * I * t (mJ),
com V em volts, I em mA e t em segundos.

Solução exata: como há uma única restrição de orçamento, o ótimo é o método
guloso por razão peso/energia (problema da mochila fracionária com limites).
"""
import math
from dataclasses import dataclass

from .errors import DadosInvalidosError, OrcamentoInviavelError

TENSAO_V = 5.0
SEGUNDOS_POR_HORA = 3600


@dataclass(frozen=True)
class SensorSpec:
    nome: str
    corrente_ma: float
    tempo_s: float
    peso: float
    min_por_hora: float
    max_por_hora: float

    def __post_init__(self):
        if self.corrente_ma <= 0 or self.tempo_s <= 0 or self.peso <= 0:
            raise ValueError(f"{self.nome}: corrente, tempo e peso devem ser positivos")
        if not 0 < self.min_por_hora <= self.max_por_hora:
            raise ValueError(f"{self.nome}: exige 0 < min_por_hora <= max_por_hora")

    @property
    def energia_mj(self) -> float:
        return TENSAO_V * self.corrente_ma * self.tempo_s


@dataclass(frozen=True)
class SensorSchedule:
    nome: str
    leituras_por_hora: float
    intervalo_s: float
    energia_mj_hora: float


@dataclass(frozen=True)
class Schedule:
    orcamento_mj_hora: float
    energia_total_mj_hora: float
    valor_otimizado: float
    valor_uniforme: float
    sensores: tuple

    @property
    def ganho_percentual(self) -> float:
        return (self.valor_otimizado - self.valor_uniforme) / self.valor_uniforme * 100

    def to_dict(self) -> dict:
        return {
            "orcamento_mj_hora": round(self.orcamento_mj_hora, 2),
            "energia_total_mj_hora": round(self.energia_total_mj_hora, 2),
            "valor_otimizado": round(self.valor_otimizado, 2),
            "valor_uniforme": round(self.valor_uniforme, 2),
            "ganho_percentual": round(self.ganho_percentual, 1),
            "sensores": [
                {
                    "nome": s.nome,
                    "leituras_por_hora": round(s.leituras_por_hora, 2),
                    "intervalo_s": round(s.intervalo_s, 1),
                    "energia_mj_hora": round(s.energia_mj_hora, 2),
                }
                for s in self.sensores
            ],
        }


def optimize(sensores, orcamento_mj_hora: float) -> Schedule:
    if not (math.isfinite(orcamento_mj_hora) and orcamento_mj_hora > 0):
        raise DadosInvalidosError("orcamento_mj_hora deve ser um número maior que zero")

    custo_minimo = sum(s.energia_mj * s.min_por_hora for s in sensores)
    if custo_minimo > orcamento_mj_hora:
        raise OrcamentoInviavelError(
            f"orçamento de {orcamento_mj_hora} mJ/h não cobre o mínimo de leituras "
            f"({custo_minimo:.2f} mJ/h necessários)"
        )

    leituras = {s.nome: s.min_por_hora for s in sensores}
    restante = orcamento_mj_hora - custo_minimo
    for s in sorted(sensores, key=lambda s: (-s.peso / s.energia_mj, s.nome)):
        extra = max(0.0, min(s.max_por_hora - s.min_por_hora, restante / s.energia_mj))
        leituras[s.nome] += extra
        restante -= extra * s.energia_mj

    valor_otimizado = sum(s.peso * leituras[s.nome] for s in sensores)

    # Comparação: mesma frequência para todos os sensores, sem otimizar.
    x_uniforme = min(
        orcamento_mj_hora / sum(s.energia_mj for s in sensores),
        min(s.max_por_hora for s in sensores),
    )
    valor_uniforme = sum(s.peso for s in sensores) * x_uniforme

    return Schedule(
        orcamento_mj_hora=orcamento_mj_hora,
        energia_total_mj_hora=sum(s.energia_mj * leituras[s.nome] for s in sensores),
        valor_otimizado=valor_otimizado,
        valor_uniforme=valor_uniforme,
        sensores=tuple(
            SensorSchedule(
                nome=s.nome,
                leituras_por_hora=leituras[s.nome],
                intervalo_s=SEGUNDOS_POR_HORA / leituras[s.nome],
                energia_mj_hora=s.energia_mj * leituras[s.nome],
            )
            for s in sensores
        ),
    )
