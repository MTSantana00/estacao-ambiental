# Estação Ambiental (ExpoTech 2026.2, categoria Interface)

Equipe: Matheus, Gheovanne e Vitor.

Uma estação que lê **temperatura, umidade e luminosidade**. Um circuito digital
(simulado no Logisim) acende um LED verde, amarelo ou vermelho conforme o risco. As leituras
vão para uma **API na nuvem (Azure)**, que classifica com a mesma regra do circuito, guarda tudo
em um **banco PostgreSQL gerenciado** e usa **programação linear** para decidir quantas vezes por
hora cada sensor deve ler, aproveitando ao máximo um orçamento de energia.

O "ponto de contato" entre o circuito e a nuvem é o script `integracao/enviar_casos.py`: ele envia
à API os mesmos 5 casos testados no circuito e mostra que os dois dão o mesmo resultado.

## Estrutura do repositório

```
expotech/
├── backend/                 API em Python (FastAPI), testes, README técnico
│   ├── app/                 código (regras, banco, otimização, HTTP)
│   │   └── static/index.html   painel web (estado atual, simulador, histórico, otimização)
│   ├── tests/               testes automáticos
│   ├── function_app.py      entrada da API na Azure Functions
│   └── host.json            configuração da Azure Functions
├── estacao/                 circuito do Logisim
│   ├── estacao_final_att.circ        circuito principal
│   ├── estacao_caso_1..5_*.circ      os 5 casos de teste
│   ├── print estação caso *.png      evidências dos testes
│   └── Padrões de Projeto e SOLID ... .docx
├── integracao/
│   └── enviar_casos.py      envia os 5 casos do circuito para a API
├── segredos-azure.txt       chave da API e senha do banco (só no seu PC, nunca no GitHub)
├── testar.bat               teste com dois cliques (Windows)
├── ci-cd.yml                testes + publicação automática na Azure
│                            (no GitHub fica em .github/workflows/ci-cd.yml)
├── Arquitetura C4 - ....pdf         diagramas C4 (contexto, contêineres, componentes)
└── Circuito e Física - ....pdf      circuito, tabela-verdade e cálculos de física
```

## Como os requisitos do edital são cobertos

| Requisito | Onde está |
|---|---|
| Eletrônica digital: circuito com sensor/atuador e lógica | `estacao/estacao_final_att.circ`, tabela-verdade e prints no PDF de Circuito e Física |
| Física: corrente, tensão, potência | PDF de Circuito e Física (resumo abaixo) |
| Arquitetura C4/UML | PDF Arquitetura C4 |
| 2 padrões GoF + SOLID | Strategy em `backend/app/classification.py`, Observer em `backend/app/alerts.py`; explicação no .docx |
| Nuvem pública com banco gerenciado | Azure Functions + Azure Database for PostgreSQL (`backend/app/repository.py`) |
| Segredos fora do código | `API_KEY` e `DATABASE_URL` só em variáveis de ambiente (`backend/.env.example`) |
| CI/CD com GitHub Actions | `.github/workflows/ci-cd.yml` (no PC está como `ci-cd.yml` na raiz) |
| Pesquisa Operacional | `backend/app/optimization.py` e rota `GET /optimization/schedule` |

## A regra (igual no circuito e na API)

- A = temperatura > 30 °C · B = umidade < 30 % · C = luminosidade > 80 %
- Nenhuma condição = **normal** (verde) · uma = **atenção** (amarelo) · duas ou mais = **alarme** (vermelho)
- Estação desligada (EN = 0) = nenhum LED / estado `desligado`

Expressões: `ALARME = EN·(AB + AC + BC)` · `NORMAL = EN·A'B'C'` · `ATENÇÃO = EN·(A+B+C)·ALARME'`

### Os 5 casos de teste

| Caso | TEMP | UMID | LUZ | EN | LED no circuito | Estado na API |
|---|---|---|---|---|---|---|
| 1 | 0x17 (23 °C) | 0x20 (32 %) | 0x20 (32 %) | 1 | verde | `normal` |
| 2 | 0x23 (35 °C) | 0x20 | 0x20 | 1 | amarelo | `atencao` |
| 3 | 0x17 | 0x0E (14 %) | 0x20 | 1 | amarelo | `atencao` |
| 4 | 0x23 | 0x0E | 0x20 | 1 | vermelho | `alarme` |
| 5 | 0x23 | 0x0E | 0x20 | 0 | nenhum | `desligado` |

## Física (resumo; detalhes no PDF)

- **Resistor do LED** (5 V, 10 mA desejados): R = (5 − 2,0) / 0,010 = 300 Ω → comercial **330 Ω**;
  corrente real ≈ 9,1 mA; potência no resistor ≈ 27 mW (bem abaixo de 1/4 W).
- **Consumo dos LEDs**: só um acende por vez → pior caso ≈ 5 V × 9,1 mA ≈ 45 mW.
- **Sensor de temperatura (LM35)**: 10 mV/°C; com um conversor de 8 bits e referência de 2,56 V,
  cada código vale 10 mV = 1 °C.
- **Energia por leitura** (entra na otimização): E = V · I · t, com V = 5 V.

## Pesquisa Operacional (otimização)

Variáveis: leituras por hora de cada sensor. Objetivo: maximizar `3·temperatura + 2·umidade + 1·luz`
(pesos definidos pela equipe: a temperatura é a que mais indica risco, a luz é a que mais varia
naturalmente). Restrições: energia total ≤ orçamento por hora, e mínimo/máximo de leituras por sensor.
A API devolve a frequência ótima e a compara com uma distribuição uniforme.

## Rodar no seu PC (Windows)

Atalho: dê dois cliques em `testar.bat` (cria o ambiente, instala, roda os testes e, se você colar a
`API_KEY`, confere os 5 casos contra a Azure). Ou, no PowerShell:

```powershell
cd C:\Users\j_exp\Desktop\expotech\backend
uv pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest          # esperado: OK (skipped=5)

$env:API_KEY = "minha-chave-local"
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Abra http://localhost:8000/docs. Em **outro** PowerShell, rode a integração:

```powershell
cd C:\Users\j_exp\Desktop\expotech\integracao
$env:API_KEY = "minha-chave-local"
..\backend\.venv\Scripts\python.exe enviar_casos.py
```

O esperado é `5 de 5 casos: circuito e API concordam.`

Os 5 testes pulados no PC são os do PostgreSQL. Eles rodam de verdade no GitHub Actions
(que sobe um PostgreSQL só para o teste) e podem rodar contra o banco da Azure definindo `TEST_DATABASE_URL`.

## Na nuvem (Azure): já está no ar

**Painel (front-end):** https://estacao-api-87rj.azurewebsites.net/

**API (Swagger):** https://estacao-api-87rj.azurewebsites.net/docs

| Recurso | Nome | Tipo |
|---|---|---|
| Grupo de recursos | `rg-expotech` | Brazil South |
| Banco gerenciado | `estacao-db-87rj` | Azure Database for PostgreSQL, servidor flexível, B1ms, 32 GiB |
| API | `estacao-api-87rj` | Azure Functions, plano de consumo flexível, Python 3.12 |
| Armazenamento | `stestacao87rj` | conta de armazenamento exigida pela Function App |
| Monitoramento | `estacao-api-87rj` | Application Insights (logs da API) |

- A API roda na **Azure Functions** em vez do App Service: a assinatura de avaliação veio com cota zero
  para planos do App Service (F1 e B1). O código é o mesmo; `backend/function_app.py` só entrega o
  FastAPI à Azure (`host.json` tira o prefixo `/api` das rotas). Localmente continua `uvicorn app.main:app`.
- `API_KEY` e `DATABASE_URL` estão nas **variáveis de ambiente** da Function App, nunca no código.
  Os valores ficam no arquivo `segredos-azure.txt` do seu PC (fora do GitHub).
- O banco só aceita conexões de serviços da Azure (regra de firewall "permitir serviços da Azure").

Testes feitos em 28/10/2026: todos os testes passaram contra o PostgreSQL da Azure (num banco
separado, `estacao_teste`); em um PC com Windows rodam 52 testes (47 + 5 do PostgreSQL pulados);
e `enviar_casos.py` contra a API publicada deu 5 de 5.

Para testar você mesmo (PowerShell, na pasta integracao):

```powershell
$env:API_KEY = "<API_KEY do arquivo segredos-azure.txt>"
..\backend\.venv\Scripts\python.exe enviar_casos.py --url https://estacao-api-87rj.azurewebsites.net
```

### CI/CD (GitHub Actions)

1. O repositório já existe no GitHub (o `.gitignore` deixa de fora `.env`, `.venv` e bancos locais) e o
   workflow já está em `.github/workflows/ci-cd.yml`: os testes rodam a cada push.
2. Para ligar a publicação automática, faça os passos 3 e 4 (um segredo, uma vez só).
3. No portal da Azure, abra `estacao-api-87rj` > *Obter perfil de publicação* e baixe o arquivo.
4. No GitHub, em *Settings > Secrets and variables > Actions*, crie o segredo
   `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` com o conteúdo desse arquivo.
5. A cada push na `main`, o Actions roda os testes (com um PostgreSQL próprio) e, se passarem, publica a API.
   Sem o segredo, o pipeline fica verde e apenas pula a publicação.

### Prazo da conta gratuita

A conta é uma avaliação de 30 dias (até cerca de 26/11/2026), suficiente para a entrega do vídeo (3/11)
e a avaliação individual (09 a 13/11). Se a equipe for chamada para o evento (28/11), o projeto é
recriado em outra conta da Azure seguindo os comandos desta seção: o código não muda, só os nomes e os
valores das variáveis de ambiente.

Nunca coloque senha ou chave no código nem no GitHub: elas só existem nas variáveis de ambiente.
