import os
import tempfile
import unittest
from datetime import datetime, timezone

from app.alerts import ReadingObserver, ReadingPublisher
from app.classification import default_classifier
from app.domain import Estado, Reading
from app.errors import DadosInvalidosError
from app.repository import SqliteReadingRepository
from app.services import ReadingService

AGORA = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)


class Gravador(ReadingObserver):
    def __init__(self):
        self.recebidas = []

    def on_reading(self, reading):
        self.recebidas.append(reading)


class ReadingServiceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = SqliteReadingRepository(os.path.join(self._tmp.name, "s.db"))
        self.observer = Gravador()
        publisher = ReadingPublisher()
        publisher.subscribe(self.observer)
        self.service = ReadingService(self.repo, default_classifier(), publisher, clock=lambda: AGORA)

    def tearDown(self):
        self._tmp.cleanup()

    def test_register_classifica_salva_e_notifica(self):
        stored = self.service.register(Reading(35, 20, 50))
        self.assertEqual(stored.estado, Estado.ALARME)
        self.assertEqual(stored.criado_em, AGORA.isoformat())
        self.assertEqual(len(self.repo.latest(10)), 1)
        self.assertEqual(self.observer.recebidas, [stored])

    def test_valores_fora_da_faixa_sao_rejeitados_e_nada_e_salvo(self):
        invalidas = [
            Reading(-41, 50, 50),
            Reading(126, 50, 50),
            Reading(25, -1, 50),
            Reading(25, 101, 50),
            Reading(25, 50, -1),
            Reading(25, 50, 101),
            Reading(float("nan"), 50, 50),
            Reading(float("inf"), 50, 50),
        ]
        for leitura in invalidas:
            with self.subTest(leitura=leitura):
                with self.assertRaises(DadosInvalidosError):
                    self.service.register(leitura)
        self.assertEqual(self.repo.latest(10), [])
        self.assertEqual(self.observer.recebidas, [])

    def test_valores_nos_limites_da_faixa_sao_aceitos(self):
        self.service.register(Reading(-40, 0, 0))
        self.service.register(Reading(125, 100, 100))
        self.assertEqual(len(self.repo.latest(10)), 2)

    def test_latest_valida_limite(self):
        for limite in (0, -1, 501):
            with self.subTest(limite=limite):
                with self.assertRaises(DadosInvalidosError):
                    self.service.latest(limite)
        self.assertEqual(self.service.latest(500), [])

    def test_latest_padrao(self):
        for _ in range(60):
            self.service.register(Reading(25, 50, 50))
        self.assertEqual(len(self.service.latest()), 50)


if __name__ == "__main__":
    unittest.main()
