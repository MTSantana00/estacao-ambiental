"""Padrão Observer: quem quiser reagir a uma leitura nova se inscreve no publisher."""
import logging
from abc import ABC, abstractmethod

from .domain import Estado, StoredReading

logger = logging.getLogger("estacao.alertas")


class ReadingObserver(ABC):
    @abstractmethod
    def on_reading(self, reading: StoredReading) -> None: ...


class ReadingPublisher:
    def __init__(self):
        self._observers = []

    def subscribe(self, observer: ReadingObserver) -> None:
        self._observers.append(observer)

    def notify(self, reading: StoredReading) -> None:
        for observer in self._observers:
            try:
                observer.on_reading(reading)
            except Exception:  # um observer com defeito não pode derrubar a ingestão
                logger.exception("Observer %s falhou", type(observer).__name__)


class LogAlertObserver(ReadingObserver):
    def on_reading(self, reading: StoredReading) -> None:
        causas = ", ".join(reading.condicoes)
        if reading.estado is Estado.ALARME:
            logger.warning("ALARME na leitura %s: %s", reading.id, causas)
        elif reading.estado is Estado.ATENCAO:
            logger.info("Atenção na leitura %s: %s", reading.id, causas)
