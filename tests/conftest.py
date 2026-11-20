import os

# Configuração fixa para os testes, definida ANTES de importar a aplicação.
# Assim os testes não dependem do seu .env nem criam arquivo de banco.
os.environ.update(
    {
        # Banco em memória por padrão. Para testar no Postgres (como no CI), defina
        # TEST_DATABASE_URL com a URL de um banco vazio, só para testes.
        "DATABASE_URL": os.environ.get("TEST_DATABASE_URL") or "sqlite://",
        "SECRET_KEY": "chave-so-para-testes-com-32-bytes-ou-mais",
        "ADMIN_USUARIO": "admin",
        "ADMIN_SENHA": "senha-de-teste",
        "FUSO_HORARIO": "America/Sao_Paulo",
        "HORA_ABERTURA": "09:00",
        "HORA_FECHAMENTO": "19:00",
        "INTERVALO_MINUTOS": "30",
        "DIAS_FUNCIONAMENTO": "0,1,2,3,4,5",
    }
)

from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402


def zerar_banco():
    SQLModel.metadata.drop_all(engine)
    with engine.begin() as conexao:
        conexao.execute(text("DROP TABLE IF EXISTS alembic_version"))


@pytest.fixture
def client():
    """Cliente HTTP de teste com banco zerado a cada teste."""
    zerar_banco()
    with TestClient(app) as c:  # o "with" roda o lifespan: migrations e admin
        yield c


@pytest.fixture
def admin_headers(client):
    resposta = client.post("/auth/login", data={"username": "admin", "password": "senha-de-teste"})
    token = resposta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def criar_servico(client, admin_headers):
    def _criar(nome="Corte", duracao_minutos=30, preco="35.00"):
        resposta = client.post(
            "/servicos",
            json={"nome": nome, "duracao_minutos": duracao_minutos, "preco": preco},
            headers=admin_headers,
        )
        assert resposta.status_code == 201, resposta.text
        return resposta.json()

    return _criar


@pytest.fixture
def segunda():
    """Uma segunda-feira daqui a pelo menos uma semana (sempre no futuro)."""
    dia = date.today() + timedelta(days=7)
    while dia.weekday() != 0:
        dia += timedelta(days=1)
    return dia
