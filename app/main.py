from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlmodel import Session

from app import config, demo
from app.auth import SessionDep, criar_admin_inicial
from app.database import criar_tabelas, engine
from app.models import InfoBarbearia
from app.routers import agendamentos, login, servicos

PASTA_SITE = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Roda uma vez quando o servidor sobe
    criar_tabelas()
    with Session(engine) as session:
        criar_admin_inicial(session)
    if config.DEMO_MODO:
        demo.garantir_atualizada()
    yield


app = FastAPI(
    title="API de Agendamentos para Barbearias",
    description=(
        "Clientes consultam horários livres e marcam atendimentos; "
        "o administrador gerencia serviços e a agenda."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

if config.DEMO_MODO:

    @app.middleware("http")
    async def renovar_demo(request: Request, call_next):
        # Na virada do dia, a primeira requisição recria os dados de exemplo
        await run_in_threadpool(demo.garantir_atualizada)
        return await call_next(request)


app.include_router(login.router)
app.include_router(servicos.router)
app.include_router(agendamentos.router)


@app.get("/saude", tags=["Status"])
def saude(session: SessionDep):
    """Healthcheck: confirma que a API está no ar e que o banco responde."""
    try:
        session.connection().execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Banco de dados indisponível")
    return {"status": "ok", "banco": "ok"}


@app.get("/info", response_model=InfoBarbearia, tags=["Status"])
def info():
    """Público: horário de funcionamento (usado pelo site para montar o calendário)."""
    return InfoBarbearia(
        abertura=f"{config.HORA_ABERTURA:%H:%M}",
        fechamento=f"{config.HORA_FECHAMENTO:%H:%M}",
        intervalo_minutos=config.INTERVALO_MINUTOS,
        dias_funcionamento=sorted(config.DIAS_FUNCIONAMENTO),
        demo=config.DEMO_MODO,
    )


# Site de agendamento (HTML, CSS e JS simples, sem build), servido pela própria API
app.mount("/static", StaticFiles(directory=PASTA_SITE), name="static")


@app.get("/", include_in_schema=False)
def site():
    return FileResponse(PASTA_SITE / "index.html")
