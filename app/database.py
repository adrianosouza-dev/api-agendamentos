"""Conexão com o banco de dados e migrations."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.config import DATABASE_URL

RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent


def _ajustar_url(url: str) -> str:
    # O Supabase/Postgres entrega URLs "postgres://" ou "postgresql://".
    # Aqui usamos o driver psycopg (versão 3), então indicamos isso na URL.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def _criar_engine(url: str):
    url = _ajustar_url(url)
    if url.startswith("sqlite"):
        opcoes = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            # Banco em memória (usado nos testes): uma única conexão compartilhada
            opcoes["poolclass"] = StaticPool
        return create_engine(url, **opcoes)
    return create_engine(url, pool_pre_ping=True)


engine = _criar_engine(DATABASE_URL)


def migrar() -> None:
    """Deixa o banco na versão mais recente das migrations (o mesmo que "alembic upgrade head").

    Roda quando a API sobe, então um deploy novo atualiza o banco sozinho.
    """
    config = Config(str(RAIZ_DO_PROJETO / "alembic.ini"))
    config.attributes["chamado_pela_api"] = True

    tabelas = inspect(engine).get_table_names()
    if "agendamento" in tabelas and "alembic_version" not in tabelas:
        # Banco criado antes do Alembic (pelo antigo create_all): as tabelas da
        # migration 0001 já existem, então só registramos que ela está aplicada.
        command.stamp(config, "0001")
    command.upgrade(config, "head")


def get_session():
    """Abre uma sessão por requisição e fecha ao final."""
    with Session(engine) as session:
        yield session
