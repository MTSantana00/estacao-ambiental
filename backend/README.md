# Backend da Estação Ambiental (ExpoTech 2026.2, Interface)

API em Python (FastAPI) que recebe as leituras dos sensores, classifica o estado
(igual ao circuito Logisim), guarda tudo em banco e calcula a frequência ótima de leitura.

## Rodar localmente
```
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
$env:API_KEY="minha-chave-local"   # PowerShell  (Linux/Mac: export API_KEY=minha-chave-local)
uvicorn app.main:app --reload
```
Abra http://localhost:8000/ (painel) e http://localhost:8000/docs (tela interativa Swagger).

## Testes
```
python -m unittest -v
```
Os testes HTTP (`tests/test_api.py`) só rodam com `fastapi` e `httpx` instalados.

## Endpoints
| Método | Rota | Auth | O que faz |
|---|---|---|---|
| GET | `/` | não | Painel web (estado atual, simulador, histórico e otimização) |
| GET | `/health` | não | Verifica se a API está no ar |
| POST | `/readings` | header `X-API-Key` | Registra leitura e devolve o estado (201) |
| GET | `/readings?limit=50` | não | Últimas leituras, mais recente primeiro (limit 1 a 500) |
| GET | `/optimization/schedule?orcamento_mj_hora=1000` | não | Frequência ótima de cada sensor |

Corpo do POST: `{"temperatura": 35, "umidade": 20, "luminosidade": 50, "ligada": true}`
(temperatura em °C de -40 a 125; umidade e luminosidade em % de 0 a 100).
Estados possíveis: `desligado`, `normal`, `atencao`, `alarme`. Erros de dados voltam como 422 com `detail`.

## Regras (iguais ao circuito)
A = temperatura > 30 · B = umidade < 30 · C = luminosidade > 80.
Nenhuma = normal · uma = atenção · duas ou mais = alarme · `ligada=false` = desligado.

## Otimização (Pesquisa Operacional)
Maximizar soma(peso x leituras/h) com soma(energia x leituras/h) <= orçamento e
mínimo/máximo por sensor. Energia por leitura E = V·I·t (V = 5 V). Solução exata por método
guloso (razão peso/energia), verificada nos testes contra enumeração de vértices.
**Os pesos e as correntes/tempos em `app/config.py` são premissas ilustrativas**: ajuste e justifique no documento.

## Arquitetura e padrões
| Arquivo | Papel |
|---|---|
| `domain.py`, `errors.py` | Entidades e validação |
| `classification.py` | **Strategy**: cada `Rule` é uma condição intercambiável |
| `alerts.py` | **Observer**: `ReadingPublisher` notifica `ReadingObserver`s (ex.: log de alertas) |
| `repository.py` | Interface de persistência + implementações SQLite (local) e PostgreSQL (Azure) |
| `services.py` | Orquestra: valida, classifica, salva, notifica |
| `optimization.py` | Modelo e solução do problema de otimização |
| `main.py` | Só HTTP; é onde as peças são ligadas |

SOLID: **S** um módulo por responsabilidade · **O** nova `Rule` ou novo observer sem mexer no existente
(há teste) · **L** qualquer `ReadingRepository` serve no lugar de outro · **I** interfaces pequenas
(`Rule`, `ReadingObserver`, `ReadingRepository`) · **D** o serviço recebe tudo por injeção.

## Banco de dados
- Sem `DATABASE_URL`: SQLite local no arquivo `DATABASE_PATH` (padrão `estacao.db`).
- Com `DATABASE_URL`: PostgreSQL (o banco gerenciado da Azure). Nenhuma rota muda.
- `tests/test_repository.py` roda **os mesmos testes** nos dois bancos (Liskov). Para incluir o PostgreSQL:
  defina `TEST_DATABASE_URL` com a conexão de um banco de teste (o teste apaga e recria a tabela `readings`).

## Segredos
`API_KEY`, `DATABASE_PATH` e `DATABASE_URL` vêm de variáveis de ambiente (veja `.env.example`). Nada de segredo no código.
