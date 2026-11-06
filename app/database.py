"""Conexão com o banco de dados."""

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import DATABASE_URL


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


def criar_tabelas() -> None:
    from app import models  # noqa: F401  (registra as tabelas antes de criar)

    SQLModel.metadata.create_all(engine)


def get_session():
    """Abre uma sessão por requisição e fecha ao final."""
    with Session(engine) as session:
        yield session
