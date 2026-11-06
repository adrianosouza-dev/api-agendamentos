from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app import regras
from app.auth import AdminDep, SessionDep
from app.models import (
    Agendamento,
    AgendamentoCriar,
    AgendamentoLeitura,
    HorariosLivres,
    StatusAgendamento,
)
from app.routers.servicos import buscar_servico_ativo

router = APIRouter(tags=["Agendamentos"])


def _limites_do_dia(dia: date) -> tuple[datetime, datetime]:
    inicio = datetime.combine(dia, time.min)
    return inicio, inicio + timedelta(days=1)


def _confirmados_entre(session: Session, inicio: datetime, fim: datetime) -> list[Agendamento]:
    """Agendamentos confirmados que se sobrepõem ao intervalo [inicio, fim)."""
    consulta = select(Agendamento).where(
        Agendamento.status == StatusAgendamento.confirmado,
        Agendamento.inicio < fim,
        Agendamento.fim > inicio,
    )
    return list(session.exec(consulta).all())


def _buscar_agendamento(session: Session, agendamento_id: int) -> Agendamento:
    agendamento = session.get(Agendamento, agendamento_id)
    if agendamento is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return agendamento


# ---------------------------------------------------------------- Rotas públicas


@router.get("/horarios-livres", response_model=HorariosLivres)
def horarios_livres(data: date, servico_id: int, session: SessionDep):
    """Público: horários disponíveis em um dia para um serviço. Ex.: ?data=2026-11-16&servico_id=1"""
    servico = buscar_servico_ativo(session, servico_id)
    inicio_dia, fim_dia = _limites_do_dia(data)
    ocupados = [(a.inicio, a.fim) for a in _confirmados_entre(session, inicio_dia, fim_dia)]

    livres = regras.horarios_livres(data, servico.duracao_minutos, ocupados, regras.agora_local())
    return HorariosLivres(
        data=data,
        servico_id=servico.id,
        horarios=[h.strftime("%H:%M") for h in livres],
    )


@router.post("/agendamentos", response_model=AgendamentoLeitura, status_code=201)
def criar_agendamento(dados: AgendamentoCriar, session: SessionDep):
    """Público: o cliente marca um horário."""
    servico = buscar_servico_ativo(session, dados.servico_id)

    try:
        regras.validar_horario(dados.inicio, servico.duracao_minutos, regras.agora_local())
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))

    fim = dados.inicio + timedelta(minutes=servico.duracao_minutos)
    if _confirmados_entre(session, dados.inicio, fim):
        raise HTTPException(status_code=409, detail="Esse horário já está ocupado")

    agendamento = Agendamento(
        cliente_nome=dados.cliente_nome.strip(),
        cliente_telefone=dados.cliente_telefone,
        servico_id=servico.id,
        inicio=dados.inicio,
        fim=fim,
    )
    session.add(agendamento)
    session.commit()
    session.refresh(agendamento)
    return agendamento


# ---------------------------------------------------------------- Rotas do admin


@router.get("/agendamentos", response_model=list[AgendamentoLeitura])
def listar_agendamentos(
    session: SessionDep,
    _admin: AdminDep,
    data: Optional[date] = None,
    incluir_cancelados: bool = False,
):
    """Admin: agenda, opcionalmente filtrada por dia."""
    consulta = select(Agendamento).order_by(Agendamento.inicio)
    if data is not None:
        inicio_dia, fim_dia = _limites_do_dia(data)
        consulta = consulta.where(Agendamento.inicio >= inicio_dia, Agendamento.inicio < fim_dia)
    if not incluir_cancelados:
        consulta = consulta.where(Agendamento.status == StatusAgendamento.confirmado)
    return session.exec(consulta).all()


@router.get("/agendamentos/{agendamento_id}", response_model=AgendamentoLeitura)
def ver_agendamento(agendamento_id: int, session: SessionDep, _admin: AdminDep):
    return _buscar_agendamento(session, agendamento_id)


@router.patch("/agendamentos/{agendamento_id}/cancelar", response_model=AgendamentoLeitura)
def cancelar_agendamento(agendamento_id: int, session: SessionDep, _admin: AdminDep):
    """Admin: cancela e libera o horário (o registro continua no histórico)."""
    agendamento = _buscar_agendamento(session, agendamento_id)
    if agendamento.status == StatusAgendamento.cancelado:
        raise HTTPException(status_code=409, detail="Agendamento já está cancelado")
    agendamento.status = StatusAgendamento.cancelado
    session.commit()
    session.refresh(agendamento)
    return agendamento
