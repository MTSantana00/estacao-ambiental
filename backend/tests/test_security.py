import unittest

from app.security import is_authorized


class SecurityTest(unittest.TestCase):
    def test_chave_correta(self):
        self.assertTrue(is_authorized("segredo", "segredo"))

    def test_chave_errada_ou_vazia(self):
        self.assertFalse(is_authorized("outra", "segredo"))
        self.assertFalse(is_authorized("", "segredo"))

    def test_sem_chave_configurada_nega_tudo(self):
        self.assertFalse(is_authorized("", ""))
        self.assertFalse(is_authorized("qualquer", ""))


if __name__ == "__main__":
    unittest.main()
