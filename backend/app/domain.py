from dataclasses import dataclass
from enum import Enum

from . import config
from .errors import DadosInvalidosError


class Estado(str, Enum):
    DESLIGADO = "desligado"
    NORMAL = "normal"
    ATENCAO = "atencao"
    ALARME = "alarme"


@dataclass(frozen=True)
class Reading:
    temperatura: float
    umidade: float
    luminosidade: float
    ligada: bool = True


@dataclass(frozen=True)
class Classification:
    estado: Estado
    condicoes: tuple


@dataclass(frozen=True)
class StoredReading:
    id: int
    temperatura: float
    umidade: float
    luminosidade: float
    ligada: bool
    estado: Estado
    condicoes: tuple
    criado_em: str


def _check(nome: str, valor: float, faixa: tuple) -> None:
    minimo, maximo = faixa
    if not (minimo <= valor <= maximo):  # também rejeita NaN
        raise DadosInvalidosError(f"{nome} deve estar entre {minimo} e {maximo}")


def validate_reading(reading: Reading) -> None:
    _check("temperatura", reading.temperatura, config.TEMPERATURA_FAIXA_C)
    _check("umidade", reading.umidade, config.UMIDADE_FAIXA_PCT)
    _check("luminosidade", reading.luminosidade, config.LUMINOSIDADE_FAIXA_PCT)
