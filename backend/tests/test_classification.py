import unittest

from app.classification import Rule, StateClassifier, default_classifier
from app.domain import Estado, Reading


def leitura(a: bool, b: bool, c: bool, ligada: bool = True) -> Reading:
    """a = temperatura alta, b = umidade baixa, c = luz excessiva."""
    return Reading(
        temperatura=35 if a else 25,
        umidade=20 if b else 50,
        luminosidade=90 if c else 50,
        ligada=ligada,
    )


class TabelaVerdadeDoCircuito(unittest.TestCase):
    """As 8 linhas da tabela-verdade do circuito Logisim (com EN = 1)."""

    TABELA = [
        (0, 0, 0, Estado.NORMAL),
        (0, 0, 1, Estado.ATENCAO),
        (0, 1, 0, Estado.ATENCAO),
        (0, 1, 1, Estado.ALARME),
        (1, 0, 0, Estado.ATENCAO),
        (1, 0, 1, Estado.ALARME),
        (1, 1, 0, Estado.ALARME),
        (1, 1, 1, Estado.ALARME),
    ]

    def test_oito_combinacoes(self):
        classifier = default_classifier()
        for a, b, c, esperado in self.TABELA:
            with self.subTest(A=a, B=b, C=c):
                resultado = classifier.classify(leitura(bool(a), bool(b), bool(c)))
                self.assertEqual(resultado.estado, esperado)

    def test_desligado_ignora_sensores(self):
        resultado = default_classifier().classify(leitura(True, True, True, ligada=False))
        self.assertEqual(resultado.estado, Estado.DESLIGADO)
        self.assertEqual(resultado.condicoes, ())


class CasosDeTesteDoCircuito(unittest.TestCase):
    """Os 5 arquivos estacao_caso_*.circ (valores em hexadecimal convertidos)."""

    def test_cinco_casos(self):
        casos = [
            (Reading(0x17, 0x20, 0x20, True), Estado.NORMAL),
            (Reading(0x23, 0x20, 0x20, True), Estado.ATENCAO),
            (Reading(0x17, 0x0E, 0x20, True), Estado.ATENCAO),
            (Reading(0x23, 0x0E, 0x20, True), Estado.ALARME),
            (Reading(0x23, 0x0E, 0x20, False), Estado.DESLIGADO),
        ]
        classifier = default_classifier()
        for reading, esperado in casos:
            with self.subTest(reading=reading):
                self.assertEqual(classifier.classify(reading).estado, esperado)


class Limiares(unittest.TestCase):
    """Os limites são estritos (> e <), como nos comparadores do circuito."""

    def setUp(self):
        self.c = default_classifier()

    def test_temperatura(self):
        self.assertEqual(self.c.classify(Reading(30.0, 50, 50)).estado, Estado.NORMAL)
        self.assertEqual(self.c.classify(Reading(30.1, 50, 50)).estado, Estado.ATENCAO)

    def test_umidade(self):
        self.assertEqual(self.c.classify(Reading(25, 30.0, 50)).estado, Estado.NORMAL)
        self.assertEqual(self.c.classify(Reading(25, 29.9, 50)).estado, Estado.ATENCAO)

    def test_luz(self):
        self.assertEqual(self.c.classify(Reading(25, 50, 80.0)).estado, Estado.NORMAL)
        self.assertEqual(self.c.classify(Reading(25, 50, 80.1)).estado, Estado.ATENCAO)

    def test_nomes_das_condicoes(self):
        r = self.c.classify(Reading(35, 20, 50))
        self.assertEqual(r.condicoes, ("temperatura_alta", "umidade_baixa"))


class AbertoParaExtensao(unittest.TestCase):
    def test_nova_regra_sem_mexer_no_classificador(self):
        class Sempre(Rule):
            name = "sempre"

            def triggered(self, reading):
                return True

        classifier = StateClassifier([Sempre()], alarm_threshold=2)
        resultado = classifier.classify(Reading(25, 50, 50))
        self.assertEqual(resultado.estado, Estado.ATENCAO)
        self.assertEqual(resultado.condicoes, ("sempre",))


if __name__ == "__main__":
    unittest.main()
