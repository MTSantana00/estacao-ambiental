"""Todos os valores ajustáveis ficam aqui. Segredos vêm de variáveis de ambiente."""
import os

from .optimization import SensorSpec

# Limiares: os mesmos do circuito Logisim (condições A, B e C).
LIMITE_TEMPERATURA_ALTA_C = 30.0   # A: temperatura > 30
LIMITE_UMIDADE_BAIXA_PCT = 30.0    # B: umidade < 30
LIMITE_LUZ_ALTA_PCT = 80.0         # C: luminosidade > 80
LIMITE_CONDICOES_ALARME = 2        # 2 ou mais condições = alarme

# Faixas aceitas nas leituras (fora delas a API responde 422).
TEMPERATURA_FAIXA_C = (-40.0, 125.0)
UMIDADE_FAIXA_PCT = (0.0, 100.0)
LUMINOSIDADE_FAIXA_PCT = (0.0, 100.0)

LIMITE_PADRAO_LISTAGEM = 50
LIMITE_MAXIMO_LISTAGEM = 500

# Otimização. Valores ILUSTRATIVOS (ordem de grandeza de datasheets):
# trocar pelos valores justificados no documento de física.
# Pesos: importância relativa de cada medição (premissa do projeto).
SENSORES = (
    SensorSpec("temperatura", corrente_ma=0.06, tempo_s=0.1, peso=3, min_por_hora=6, max_por_hora=360),
    SensorSpec("umidade", corrente_ma=1.5, tempo_s=2.0, peso=2, min_por_hora=6, max_por_hora=120),
    SensorSpec("luminosidade", corrente_ma=0.25, tempo_s=0.1, peso=1, min_por_hora=6, max_por_hora=360),
)
ORCAMENTO_PADRAO_MJ_HORA = 1000.0

# Segredos e ambiente (nunca no código).
DATABASE_PATH = os.getenv("DATABASE_PATH", "estacao.db")
# Se DATABASE_URL existir (Azure), a API usa PostgreSQL; sem ela, usa SQLite local.
DATABASE_URL = os.getenv("DATABASE_URL", "")
API_KEY = os.getenv("API_KEY", "")
