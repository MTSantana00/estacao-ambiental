"""Camada HTTP (FastAPI). Só traduz HTTP <-> serviços; as regras ficam nos outros módulos."""
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from . import config
from .alerts import LogAlertObserver, ReadingPublisher
from .classification import default_classifier
from .domain import Reading, StoredReading
from .errors import DadosInvalidosError
from .optimization import optimize
from .repository import PostgresReadingRepository, SqliteReadingRepository
from .security import is_authorized
from .services import ReadingService

if not config.API_KEY:
    raise RuntimeError("Defina a variável de ambiente API_KEY antes de iniciar a API.")

# Composição: aqui (e só aqui) as peças concretas são escolhidas e ligadas.
publisher = ReadingPublisher()
publisher.subscribe(LogAlertObserver())
repository = (
    PostgresReadingRepository(config.DATABASE_URL)
    if config.DATABASE_URL
    else SqliteReadingRepository(config.DATABASE_PATH)
)
service = ReadingService(
    repository,
    default_classifier(),
    publisher,
)

app = FastAPI(title="Estação Ambiental - ExpoTech 2026.2", version="1.0.0")


class ReadingIn(BaseModel):
    temperatura: float
    umidade: float
    luminosidade: float
    ligada: bool = True


class ReadingOut(BaseModel):
    id: int
    temperatura: float
    umidade: float
    luminosidade: float
    ligada: bool
    estado: str
    condicoes: list[str]
    criado_em: str


class SensorOut(BaseModel):
    nome: str
    leituras_por_hora: float
    intervalo_s: float
    energia_mj_hora: float


class ScheduleOut(BaseModel):
    orcamento_mj_hora: float
    energia_total_mj_hora: float
    valor_otimizado: float
    valor_uniforme: float
    ganho_percentual: float
    sensores: list[SensorOut]


def to_out(stored: StoredReading) -> ReadingOut:
    return ReadingOut(
        id=stored.id,
        temperatura=stored.temperatura,
        umidade=stored.umidade,
        luminosidade=stored.luminosidade,
        ligada=stored.ligada,
        estado=stored.estado.value,
        condicoes=list(stored.condicoes),
        criado_em=stored.criado_em,
    )


def require_api_key(x_api_key: str = Header(default="")) -> None:
    if not is_authorized(x_api_key, config.API_KEY):
        raise HTTPException(status_code=401, detail="Chave de API inválida")


@app.exception_handler(DadosInvalidosError)
async def dados_invalidos_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


PAINEL_HTML = Path(__file__).parent / "static" / "index.html"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def painel():
    """Painel web (front-end) da estação."""
    return PAINEL_HTML.read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/readings", response_model=ReadingOut, status_code=201,
          dependencies=[Depends(require_api_key)])
def create_reading(body: ReadingIn):
    stored = service.register(
        Reading(body.temperatura, body.umidade, body.luminosidade, body.ligada)
    )
    return to_out(stored)


@app.get("/readings", response_model=list[ReadingOut])
def list_readings(limit: int = config.LIMITE_PADRAO_LISTAGEM):
    return [to_out(s) for s in service.latest(limit)]


@app.get("/optimization/schedule", response_model=ScheduleOut)
def get_schedule(orcamento_mj_hora: float = config.ORCAMENTO_PADRAO_MJ_HORA):
    return ScheduleOut(**optimize(config.SENSORES, orcamento_mj_hora).to_dict())
