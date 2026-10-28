"""O MESMO conjunto de testes roda nos dois bancos (princípio de Liskov na prática).

- SQLite: roda sempre.
- PostgreSQL: roda quando a variável TEST_DATABASE_URL aponta para um banco real
  (por exemplo, o da Azure) e o driver psycopg está instalado. Sem isso, é pulado.
  ATENÇÃO: o teste apaga e recria a tabela `readings` desse banco.
"""
import os
import tempfile
import unittest

from app.domain import Classification, Estado, Reading
from app.repository import PostgresReadingRepository, SqliteReadingRepository

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
try:
    import psycopg  # noqa: F401
    TEM_PSYCOPG = True
except ImportError:
    TEM_PSYCOPG = False


class RepositoryContract:
    """Comportamento que todo ReadingRepository precisa ter."""

    def make_repo(self):
        raise NotImplementedError

    def test_add_devolve_leitura_com_id(self):
        stored = self.repo.add(Reading(35, 20, 50), Classification(Estado.ALARME, ("a", "b")), "t1")
        self.assertEqual(stored.id, 1)
        self.assertEqual(stored.estado, Estado.ALARME)
        self.assertEqual(stored.condicoes, ("a", "b"))

    def test_latest_mais_recente_primeiro_e_respeita_limite(self):
        for i in range(5):
            self.repo.add(Reading(20 + i, 50, 50), Classification(Estado.NORMAL, ()), f"t{i}")
        ultimas = self.repo.latest(3)
        self.assertEqual([r.id for r in ultimas], [5, 4, 3])
        self.assertEqual(ultimas[0].temperatura, 24)

    def test_roundtrip_dos_campos(self):
        self.repo.add(Reading(35.5, 20.25, 91.0, False), Classification(Estado.DESLIGADO, ()), "2026-10-22T10:00:00+00:00")
        lida = self.repo.latest(1)[0]
        self.assertEqual((lida.temperatura, lida.umidade, lida.luminosidade), (35.5, 20.25, 91.0))
        self.assertIs(lida.ligada, False)
        self.assertEqual(lida.estado, Estado.DESLIGADO)
        self.assertEqual(lida.condicoes, ())
        self.assertEqual(lida.criado_em, "2026-10-22T10:00:00+00:00")

    def test_dados_persistem_entre_instancias(self):
        self.repo.add(Reading(25, 50, 50), Classification(Estado.NORMAL, ()), "t")
        outra = self.make_repo()
        self.assertEqual(len(outra.latest(10)), 1)

    def test_banco_vazio(self):
        self.assertEqual(self.repo.latest(10), [])


class SqliteRepositoryTest(RepositoryContract, unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "teste.db")
        self.repo = self.make_repo()

    def tearDown(self):
        self._tmp.cleanup()

    def make_repo(self):
        return SqliteReadingRepository(self.path)


@unittest.skipUnless(TEST_DATABASE_URL and TEM_PSYCOPG,
                     "defina TEST_DATABASE_URL (e instale psycopg) para testar no PostgreSQL")
class PostgresRepositoryTest(RepositoryContract, unittest.TestCase):
    def setUp(self):
        import psycopg
        with psycopg.connect(TEST_DATABASE_URL) as conn:
            conn.execute("DROP TABLE IF EXISTS readings")
        self.repo = self.make_repo()

    def make_repo(self):
        return PostgresReadingRepository(TEST_DATABASE_URL)


if __name__ == "__main__":
    unittest.main()
