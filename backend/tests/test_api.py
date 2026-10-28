"""Testes HTTP. Exigem fastapi e httpx instalados (pip install -r requirements.txt)."""
import os
import tempfile
import unittest

try:
    from fastapi.testclient import TestClient
    TEM_FASTAPI = True
except ImportError:
    TEM_FASTAPI = False

CHAVE = "chave-de-teste"
VALIDA = {"temperatura": 35, "umidade": 20, "luminosidade": 50, "ligada": True}


@unittest.skipUnless(TEM_FASTAPI, "fastapi/httpx não instalados")
class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        from app import config
        config.API_KEY = CHAVE
        config.DATABASE_PATH = os.path.join(cls._tmp.name, "api.db")
        from app import main
        cls.client = TestClient(main.app)
        cls.h = {"X-API-Key": CHAVE}

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_painel_web(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])
        self.assertIn("Estação Ambiental", r.text)

    def test_post_exige_chave(self):
        self.assertEqual(self.client.post("/readings", json=VALIDA).status_code, 401)
        self.assertEqual(
            self.client.post("/readings", json=VALIDA, headers={"X-API-Key": "errada"}).status_code, 401)

    def test_post_cria_e_classifica(self):
        r = self.client.post("/readings", json=VALIDA, headers=self.h)
        self.assertEqual(r.status_code, 201)
        corpo = r.json()
        self.assertEqual(corpo["estado"], "alarme")
        self.assertEqual(corpo["condicoes"], ["temperatura_alta", "umidade_baixa"])
        self.assertEqual(set(corpo), {"id", "temperatura", "umidade", "luminosidade",
                                      "ligada", "estado", "condicoes", "criado_em"})

    def test_post_valor_fora_da_faixa_da_422(self):
        r = self.client.post("/readings", json={**VALIDA, "temperatura": 500}, headers=self.h)
        self.assertEqual(r.status_code, 422)
        self.assertIn("temperatura", r.json()["detail"])

    def test_post_campo_faltando_da_422(self):
        r = self.client.post("/readings", json={"temperatura": 25}, headers=self.h)
        self.assertEqual(r.status_code, 422)

    def test_get_lista_mais_recente_primeiro(self):
        self.client.post("/readings", json={**VALIDA, "temperatura": 21}, headers=self.h)
        self.client.post("/readings", json={**VALIDA, "temperatura": 22}, headers=self.h)
        itens = self.client.get("/readings?limit=2").json()
        self.assertEqual([i["temperatura"] for i in itens], [22, 21])

    def test_get_limite_invalido_da_422(self):
        self.assertEqual(self.client.get("/readings?limit=0").status_code, 422)
        self.assertEqual(self.client.get("/readings?limit=501").status_code, 422)

    def test_schedule_padrao(self):
        r = self.client.get("/optimization/schedule")
        self.assertEqual(r.status_code, 200)
        corpo = r.json()
        self.assertEqual([s["nome"] for s in corpo["sensores"]],
                         ["temperatura", "umidade", "luminosidade"])
        self.assertAlmostEqual(corpo["energia_total_mj_hora"], 1000.0, places=1)

    def test_schedule_orcamento_inviavel_ou_invalido_da_422(self):
        self.assertEqual(self.client.get("/optimization/schedule?orcamento_mj_hora=10").status_code, 422)
        self.assertEqual(self.client.get("/optimization/schedule?orcamento_mj_hora=0").status_code, 422)


if __name__ == "__main__":
    unittest.main()
