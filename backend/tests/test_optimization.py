import itertools
import random
import unittest

from app import config
from app.errors import DadosInvalidosError, OrcamentoInviavelError
from app.optimization import SensorSpec, optimize


def melhor_vertice(sensores, orcamento):
    """Verificação independente: o ótimo de um PL está em um vértice.
    Testa todo vértice (variáveis no mínimo, no máximo ou 'livre' fechando o orçamento)."""
    melhor = None
    for escolha in itertools.product(("min", "max", "livre"), repeat=len(sensores)):
        if escolha.count("livre") > 1:
            continue
        x = [None] * len(sensores)
        for i, (s, c) in enumerate(zip(sensores, escolha)):
            if c == "min":
                x[i] = s.min_por_hora
            elif c == "max":
                x[i] = s.max_por_hora
        if "livre" in escolha:
            i = escolha.index("livre")
            usado = sum(s.energia_mj * x[j] for j, s in enumerate(sensores) if j != i)
            x[i] = (orcamento - usado) / sensores[i].energia_mj
            if not sensores[i].min_por_hora <= x[i] <= sensores[i].max_por_hora:
                continue
        if sum(s.energia_mj * xi for s, xi in zip(sensores, x)) > orcamento + 1e-9:
            continue
        valor = sum(s.peso * xi for s, xi in zip(sensores, x))
        melhor = valor if melhor is None else max(melhor, valor)
    return melhor


class ModeloPadrao(unittest.TestCase):
    def test_energia_por_leitura(self):
        temperatura, umidade, luminosidade = config.SENSORES
        self.assertAlmostEqual(temperatura.energia_mj, 0.03)   # 5 V * 0,06 mA * 0,1 s
        self.assertAlmostEqual(umidade.energia_mj, 15.0)       # 5 V * 1,5 mA * 2 s
        self.assertAlmostEqual(luminosidade.energia_mj, 0.125)  # 5 V * 0,25 mA * 0,1 s

    def test_orcamento_padrao_calculado_a_mao(self):
        s = optimize(config.SENSORES, 1000.0)
        por_nome = {x.nome: x for x in s.sensores}
        # temperatura e luminosidade (maior peso/energia) vão ao máximo
        self.assertAlmostEqual(por_nome["temperatura"].leituras_por_hora, 360)
        self.assertAlmostEqual(por_nome["luminosidade"].leituras_por_hora, 360)
        # umidade fica com o que sobra: 6 + (1000 - 90.9 - 354*0,03 - 354*0,125) / 15
        sobra = 1000 - (6 * 0.03 + 6 * 15 + 6 * 0.125) - 354 * 0.03 - 354 * 0.125
        self.assertAlmostEqual(por_nome["umidade"].leituras_por_hora, 6 + sobra / 15, places=6)
        self.assertAlmostEqual(s.energia_total_mj_hora, 1000.0, places=6)
        self.assertGreater(s.valor_otimizado, s.valor_uniforme)

    def test_intervalo_e_inverso_da_frequencia(self):
        s = optimize(config.SENSORES, 1000.0)
        for x in s.sensores:
            self.assertAlmostEqual(x.intervalo_s, 3600 / x.leituras_por_hora)


class CasosExtremos(unittest.TestCase):
    def test_orcamento_minimo_exato_deixa_tudo_no_minimo(self):
        minimo = sum(s.energia_mj * s.min_por_hora for s in config.SENSORES)
        resultado = optimize(config.SENSORES, minimo)
        for s, r in zip(config.SENSORES, resultado.sensores):
            self.assertAlmostEqual(r.leituras_por_hora, s.min_por_hora)

    def test_orcamento_abundante_deixa_tudo_no_maximo(self):
        resultado = optimize(config.SENSORES, 1e9)
        for s, r in zip(config.SENSORES, resultado.sensores):
            self.assertAlmostEqual(r.leituras_por_hora, s.max_por_hora)

    def test_orcamento_abaixo_do_minimo_e_inviavel(self):
        with self.assertRaises(OrcamentoInviavelError):
            optimize(config.SENSORES, 10.0)

    def test_orcamentos_invalidos(self):
        for valor in (0, -5, float("nan"), float("inf")):
            with self.subTest(valor=valor):
                with self.assertRaises(DadosInvalidosError):
                    optimize(config.SENSORES, valor)

    def test_sensor_invalido_e_rejeitado(self):
        with self.assertRaises(ValueError):
            SensorSpec("x", corrente_ma=0, tempo_s=1, peso=1, min_por_hora=1, max_por_hora=2)
        with self.assertRaises(ValueError):
            SensorSpec("x", corrente_ma=1, tempo_s=1, peso=1, min_por_hora=5, max_por_hora=2)


class OtimalidadeComprovada(unittest.TestCase):
    def test_igual_ao_melhor_vertice_em_200_instancias_aleatorias(self):
        rng = random.Random(2026)
        for n in range(200):
            sensores = []
            for k in range(rng.randint(2, 4)):
                minimo = rng.uniform(1, 10)
                sensores.append(SensorSpec(
                    f"s{k}", corrente_ma=rng.uniform(0.05, 3), tempo_s=rng.uniform(0.05, 3),
                    peso=rng.uniform(0.5, 5), min_por_hora=minimo,
                    max_por_hora=minimo + rng.uniform(0, 300)))
            custo_min = sum(s.energia_mj * s.min_por_hora for s in sensores)
            custo_max = sum(s.energia_mj * s.max_por_hora for s in sensores)
            orcamento = rng.uniform(custo_min, custo_max * 1.2)
            with self.subTest(instancia=n):
                resultado = optimize(sensores, orcamento)
                esperado = melhor_vertice(sensores, orcamento)
                self.assertLess(abs(resultado.valor_otimizado - esperado), 1e-6 * max(1.0, esperado))
                # viabilidade
                self.assertLessEqual(resultado.energia_total_mj_hora, orcamento + 1e-9)
                for s, r in zip(sensores, resultado.sensores):
                    self.assertGreaterEqual(r.leituras_por_hora, s.min_por_hora - 1e-9)
                    self.assertLessEqual(r.leituras_por_hora, s.max_por_hora + 1e-9)

    def test_nenhuma_amostra_aleatoria_viavel_supera_o_resultado(self):
        rng = random.Random(7)
        sensores = config.SENSORES
        resultado = optimize(sensores, 1000.0)
        for _ in range(20000):
            x = [rng.uniform(s.min_por_hora, s.max_por_hora) for s in sensores]
            if sum(s.energia_mj * xi for s, xi in zip(sensores, x)) <= 1000.0:
                valor = sum(s.peso * xi for s, xi in zip(sensores, x))
                self.assertLessEqual(valor, resultado.valor_otimizado + 1e-9)


class Saida(unittest.TestCase):
    def test_to_dict_tem_o_formato_da_api(self):
        d = optimize(config.SENSORES, 1000.0).to_dict()
        self.assertEqual(
            set(d), {"orcamento_mj_hora", "energia_total_mj_hora", "valor_otimizado",
                     "valor_uniforme", "ganho_percentual", "sensores"})
        self.assertEqual([s["nome"] for s in d["sensores"]], ["temperatura", "umidade", "luminosidade"])
        self.assertEqual(set(d["sensores"][0]),
                         {"nome", "leituras_por_hora", "intervalo_s", "energia_mj_hora"})


if __name__ == "__main__":
    unittest.main()
