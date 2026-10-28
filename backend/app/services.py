from datetime import datetime, timezone

from . import config
from .alerts import ReadingPublisher
from .classification import StateClassifier
from .domain import Reading, StoredReading, validate_reading
from .errors import DadosInvalidosError
from .repository import ReadingRepository


class ReadingService:
    """Depende só de abstrações (repositório, classificador, publisher): tudo injetado."""

    def __init__(self, repository: ReadingRepository, classifier: StateClassifier,
                 publisher: ReadingPublisher, clock=None):
        self._repository = repository
        self._classifier = classifier
        self._publisher = publisher
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def register(self, reading: Reading) -> StoredReading:
        validate_reading(reading)
        classification = self._classifier.classify(reading)
        stored = self._repository.add(reading, classification, self._clock().isoformat())
        self._publisher.notify(stored)
        return stored

    def latest(self, limit: int = config.LIMITE_PADRAO_LISTAGEM) -> list:
        if not 1 <= limit <= config.LIMITE_MAXIMO_LISTAGEM:
            raise DadosInvalidosError(
                f"limit deve estar entre 1 e {config.LIMITE_MAXIMO_LISTAGEM}"
            )
        return self._repository.latest(limit)
