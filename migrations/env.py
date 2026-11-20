"""Alembic: usa o mesmo banco (DATABASE_URL) e os mesmos modelos da aplicação."""

from logging.config import fileConfig

from alembic import context
from sqlmodel import SQLModel

from app import models  # noqa: F401  (registra as tabelas no metadata)
from app.database import engine

config = context.config

# Pela linha de comando ("alembic upgrade head") configura os logs do alembic.ini.
# Quando a própria API roda as migrations, ela mantém os logs do uvicorn.
if config.config_file_name and not config.attributes.get("chamado_pela_api"):
    fileConfig(config.config_file_name)


def rodar(conexao) -> None:
    context.configure(
        connection=conexao,
        target_metadata=SQLModel.metadata,
        render_as_batch=conexao.dialect.name == "sqlite",  # SQLite não altera colunas com ALTER TABLE
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=engine.url, target_metadata=SQLModel.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as conexao:
        rodar(conexao)
