"""Testes do modo demonstração (dados de exemplo da versão publicada)."""

from datetime import datetime, timedelta

from sqlmodel import Session, select

from app import demo, regras
from app.database import engine
from app.models import Agendamento, Servico

AGORA = datetime(2030, 1, 7, 8, 0)  # uma segunda-feira, antes de abrir


def resetar():
    with Session(engine) as session:
        demo.resetar(session, AGORA)


def test_cria_servicos_e_agenda(client):
    resetar()
    with Session(engine) as session:
        servicos = session.exec(select(Servico)).all()
        agendamentos = session.exec(select(Agendamento)).all()

    assert sorted(s.nome for s in servicos) == sorted(nome for nome, _, _ in demo.SERVICOS)
    assert len(agendamentos) > 20  # parte da agenda já vem ocupada


def test_agenda_de_exemplo_respeita_as_regras(client):
    resetar()
    with Session(engine) as session:
        agendamentos = session.exec(select(Agendamento).order_by(Agendamento.inicio)).all()
        duracoes = {s.id: s.duracao_minutos for s in session.exec(select(Servico)).all()}

    for a in agendamentos:
        regras.validar_horario(a.inicio, duracoes[a.servico_id], AGORA)  # não levanta erro
        assert a.inicio.date() < AGORA.date() + timedelta(days=demo.DIAS_COM_AGENDA)
    for anterior, atual in zip(agendamentos, agendamentos[1:]):
        assert not regras.conflita(anterior.inicio, anterior.fim, atual.inicio, atual.fim)


def test_reset_desfaz_mudancas_dos_visitantes(client, admin_headers, criar_servico):
    resetar()
    ids_antes = {s["nome"]: s["id"] for s in client.get("/servicos").json()}

    criar_servico("Serviço de visitante", 30, "10.00")
    client.delete(f"/servicos/{ids_antes['Barba']}", headers=admin_headers)
    resetar()

    ids_depois = {s["nome"]: s["id"] for s in client.get("/servicos").json()}
    assert ids_depois == ids_antes  # mesmos serviços, com os mesmos ids


def test_login_de_demonstracao(client):
    resetar()
    resposta = client.post("/auth/login", data={"username": demo.USUARIO, "password": demo.SENHA})
    assert resposta.status_code == 200
