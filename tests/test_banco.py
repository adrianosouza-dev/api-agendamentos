"""Testes do banco: migrations e a trava contra agendamentos sobrepostos."""

import threading
from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

from app.database import engine, migrar
from app.models import Agendamento
from app.routers import agendamentos as rotas
from tests.conftest import zerar_banco
from tests.test_agendamentos import agendar

so_postgres = pytest.mark.skipif(
    engine.dialect.name != "postgresql",
    reason="a trava contra sobreposição existe só no Postgres (defina TEST_DATABASE_URL)",
)


def versao_do_banco() -> str:
    with engine.connect() as conexao:
        return conexao.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def test_banco_novo_fica_na_ultima_versao(client):
    assert versao_do_banco() == "0002"


def test_banco_criado_antes_do_alembic_e_migrado(client):
    # Simula o banco de produção antigo: tabelas do create_all, sem alembic_version
    zerar_banco()
    SQLModel.metadata.create_all(engine)

    migrar()

    assert versao_do_banco() == "0002"
    assert "agendamento" in inspect(engine).get_table_names()


@so_postgres
def test_banco_barra_sobreposicao_mesmo_se_a_api_falhar(client, criar_servico, segunda, monkeypatch):
    servico = criar_servico()
    assert agendar(client, servico["id"], f"{segunda}T10:00:00").status_code == 201

    # Simula a corrida: a checagem da API "não enxerga" o agendamento do outro cliente
    monkeypatch.setattr(rotas, "_confirmados_entre", lambda *args: [])

    assert agendar(client, servico["id"], f"{segunda}T10:00:00", nome="Bia").status_code == 409
    assert agendar(client, servico["id"], f"{segunda}T09:30:00", nome="Caio").status_code == 201


@so_postgres
def test_dois_clientes_ao_mesmo_tempo(client, criar_servico, segunda):
    """Corrida de verdade: duas conexões checam juntas, as duas veem o horário livre."""
    servico = criar_servico()
    inicio = datetime.combine(segunda, time(10))
    fim = inicio + timedelta(minutes=30)
    todos_checaram = threading.Barrier(2)
    resultados = []

    def cliente(nome):
        with Session(engine) as session:
            livre = not rotas._confirmados_entre(session, inicio, fim)
            todos_checaram.wait()  # ninguém grava antes de os dois terem checado
            session.add(
                Agendamento(
                    cliente_nome=nome,
                    cliente_telefone="11912345678",
                    servico_id=servico["id"],
                    inicio=inicio,
                    fim=fim,
                )
            )
            try:
                session.commit()
                resultados.append((livre, "salvo"))
            except IntegrityError:
                resultados.append((livre, "recusado"))

    threads = [threading.Thread(target=cliente, args=(nome,)) for nome in ("Ana", "Bia")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # Os dois viram o horário livre, mas o banco aceitou só um
    assert sorted(resultados) == [(True, "recusado"), (True, "salvo")]
