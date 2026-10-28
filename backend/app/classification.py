"""Padrão Strategy: cada Rule é uma condição de alerta intercambiável.

O StateClassifier (contexto) não conhece as regras concretas: conta quantas
dispararam. Espelha o circuito: 0 = normal, 1 = atenção, 2 ou mais = alarme.
"""
from abc import ABC, abstractmethod
from typing import Sequence

from . import config
from .domain import Classification, Estado, Reading


class Rule(ABC):
    name: str

    @abstractmethod
    def triggered(self, reading: Reading) -> bool: ...


class HighTemperature(Rule):
    name = "temperatura_alta"

    def __init__(self, limit: float):
        self._limit = limit

    def triggered(self, reading: Reading) -> bool:
        return reading.temperatura > self._limit


class LowHumidity(Rule):
    name = "umidade_baixa"

    def __init__(self, limit: float):
        self._limit = limit

    def triggered(self, reading: Reading) -> bool:
        return reading.umidade < self._limit


class ExcessiveLight(Rule):
    name = "luz_excessiva"

    def __init__(self, limit: float):
        self._limit = limit

    def triggered(self, reading: Reading) -> bool:
        return reading.luminosidade > self._limit


class StateClassifier:
    def __init__(self, rules: Sequence[Rule], alarm_threshold: int):
        self._rules = tuple(rules)
        self._alarm_threshold = alarm_threshold

    def classify(self, reading: Reading) -> Classification:
        if not reading.ligada:
            return Classification(Estado.DESLIGADO, ())
        condicoes = tuple(r.name for r in self._rules if r.triggered(reading))
        if not condicoes:
            return Classification(Estado.NORMAL, ())
        if len(condicoes) < self._alarm_threshold:
            return Classification(Estado.ATENCAO, condicoes)
        return Classification(Estado.ALARME, condicoes)


def default_classifier() -> StateClassifier:
    return StateClassifier(
        [
            HighTemperature(config.LIMITE_TEMPERATURA_ALTA_C),
            LowHumidity(config.LIMITE_UMIDADE_BAIXA_PCT),
            ExcessiveLight(config.LIMITE_LUZ_ALTA_PCT),
        ],
        config.LIMITE_CONDICOES_ALARME,
    )
