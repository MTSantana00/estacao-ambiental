import unittest

from app.alerts import LogAlertObserver, ReadingObserver, ReadingPublisher
from app.domain import Estado, StoredReading


def armazenada(estado: Estado, condicoes=()) -> StoredReading:
    return StoredReading(1, 35, 20, 50, True, estado, condicoes, "2026-10-22T00:00:00+00:00")


class Gravador(ReadingObserver):
    def __init__(self):
        self.recebidas = []

    def on_reading(self, reading):
        self.recebidas.append(reading)


class ComDefeito(ReadingObserver):
    def on_reading(self, reading):
        raise RuntimeError("falhou")


class PublisherTest(unittest.TestCase):
    def test_notifica_todos_os_inscritos(self):
        a, b = Gravador(), Gravador()
        publisher = ReadingPublisher()
        publisher.subscribe(a)
        publisher.subscribe(b)
        leitura = armazenada(Estado.ALARME)
        publisher.notify(leitura)
        self.assertEqual(a.recebidas, [leitura])
        self.assertEqual(b.recebidas, [leitura])

    def test_observer_com_defeito_nao_impede_os_outros(self):
        bom = Gravador()
        publisher = ReadingPublisher()
        publisher.subscribe(ComDefeito())
        publisher.subscribe(bom)
        with self.assertLogs("estacao.alertas", level="ERROR"):
            publisher.notify(armazenada(Estado.NORMAL))
        self.assertEqual(len(bom.recebidas), 1)


class LogAlertObserverTest(unittest.TestCase):
    def test_alarme_gera_warning(self):
        with self.assertLogs("estacao.alertas", level="WARNING") as cm:
            LogAlertObserver().on_reading(armazenada(Estado.ALARME, ("temperatura_alta", "umidade_baixa")))
        self.assertIn("ALARME", cm.output[0])
        self.assertIn("temperatura_alta", cm.output[0])

    def test_atencao_gera_info(self):
        with self.assertLogs("estacao.alertas", level="INFO") as cm:
            LogAlertObserver().on_reading(armazenada(Estado.ATENCAO, ("luz_excessiva",)))
        self.assertIn("INFO", cm.output[0])

    def test_normal_e_desligado_nao_geram_log(self):
        for estado in (Estado.NORMAL, Estado.DESLIGADO):
            with self.subTest(estado=estado):
                with self.assertNoLogs("estacao.alertas", level="DEBUG"):
                    LogAlertObserver().on_reading(armazenada(estado))


if __name__ == "__main__":
    unittest.main()
