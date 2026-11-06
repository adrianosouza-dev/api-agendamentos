from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.auth import AdminDep, SessionDep
from app.models import Servico, ServicoCriar, ServicoLeitura

router = APIRouter(prefix="/servicos", tags=["Serviços"])


def buscar_servico_ativo(session: Session, servico_id: int) -> Servico:
    servico = session.get(Servico, servico_id)
    if servico is None or not servico.ativo:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return servico


@router.get("", response_model=list[ServicoLeitura])
def listar(session: SessionDep):
    """Público: lista os serviços oferecidos."""
    consulta = select(Servico).where(Servico.ativo == True).order_by(Servico.nome)  # noqa: E712
    return session.exec(consulta).all()


@router.post("", response_model=ServicoLeitura, status_code=201)
def criar(dados: ServicoCriar, session: SessionDep, _admin: AdminDep):
    """Admin: cadastra um serviço."""
    servico = Servico.model_validate(dados)
    session.add(servico)
    session.commit()
    session.refresh(servico)
    return servico


@router.put("/{servico_id}", response_model=ServicoLeitura)
def atualizar(servico_id: int, dados: ServicoCriar, session: SessionDep, _admin: AdminDep):
    """Admin: altera nome, duração ou preço."""
    servico = buscar_servico_ativo(session, servico_id)
    servico.sqlmodel_update(dados.model_dump())
    session.commit()
    session.refresh(servico)
    return servico


@router.delete("/{servico_id}", status_code=204)
def desativar(servico_id: int, session: SessionDep, _admin: AdminDep):
    """Admin: tira o serviço da lista (os agendamentos antigos continuam no histórico)."""
    servico = buscar_servico_ativo(session, servico_id)
    servico.ativo = False
    session.commit()
