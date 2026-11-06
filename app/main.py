from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app import config
from app.auth import criar_admin_inicial
from app.database import criar_tabelas, engine
from app.routers import agendamentos, login, servicos


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Roda uma vez quando o servidor sobe
    criar_tabelas()
    with Session(engine) as session:
        criar_admin_inicial(session)
    yield


app = FastAPI(
    title="API de Agendamentos para Barbearias",
    description=(
        "Clientes consultam horários livres e marcam atendimentos; "
        "o administrador gerencia serviços e a agenda."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login.router)
app.include_router(servicos.router)
app.include_router(agendamentos.router)


@app.get("/", tags=["Status"])
def status():
    return {"status": "ok", "documentacao": "/docs"}
