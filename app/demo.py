"""Modo demonstração: dados de exemplo que se renovam todo dia.

Ligado com DEMO_MODO=true, na versão publicada para o portfólio. Quem visita encontra
serviços cadastrados, parte da agenda já ocupada e um login de admin público ("demo").
Como esse login é público, uma vez por dia tudo volta ao estado inicial.
"""

import random
import threading
from datetime import datetime, timedelta

from sqlmodel import Session, delete, select

from app import regras
from app.auth import gerar_hash
from app.database import engine
from app.models import Agendamento, Servico, Usuario

USUARIO = "demo"
SENHA = "demo1234"

# (nome, duração em minutos, preço)
SERVICOS = [
    ("Corte", 30, "40.00"),
    ("Barba", 30, "30.00"),
    ("Corte + barba", 60, "65.00"),
    ("Corte infantil", 30, "35.00"),
    ("Luzes", 90, "120.00"),
]

NOMES = [
    "Lucas", "Rafael", "Pedro", "Gabriel", "Mateus", "Felipe",
    "Bruno", "Thiago", "Caio", "Diego", "André", "Vinícius",
]

DIAS_COM_AGENDA = 14  # quantos dias à frente recebem agendamentos de exemplo
OCUPACAO = 0.35  # chance de cada horário da grade já estar ocupado


def resetar(session: Session, agora: datetime) -> None:
    """Apaga a agenda e recria os dados de exemplo a partir de "agora"."""
    session.exec(delete(Agendamento))

    # Serviços: mantém os de exemplo (pelo nome, para os ids não mudarem a cada dia)
    # e apaga os que os visitantes criaram.
    nomes = [nome for nome, _, _ in SERVICOS]
    session.exec(delete(Servico).where(Servico.nome.not_in(nomes)))
    existentes = {s.nome: s for s in session.exec(select(Servico)).all()}
    servicos = []
    for nome, duracao, preco in SERVICOS:
        servico = existentes.get(nome) or Servico(nome=nome, duracao_minutos=0, preco=0)
        servico.duracao_minutos = duracao
        servico.preco = preco
        servico.ativo = True
        session.add(servico)
        servicos.append(servico)

    if session.exec(select(Usuario).where(Usuario.usuario == USUARIO)).first() is None:
        session.add(Usuario(usuario=USUARIO, senha_hash=gerar_hash(SENHA)))

    session.flush()  # gera os ids dos serviços novos

    for i in range(DIAS_COM_AGENDA):
        dia = agora.date() + timedelta(days=i)
        sorteio = random.Random(dia.toordinal())  # mesma agenda se resetar duas vezes no dia
        ocupados: list[tuple[datetime, datetime]] = []
        # Percorre a grade do dia e ocupa alguns horários, sempre respeitando as regras
        for inicio in regras.horarios_livres(dia, 30, [], agora):
            if sorteio.random() > OCUPACAO:
                continue
            servico = sorteio.choice(servicos)
            if inicio not in regras.horarios_livres(dia, servico.duracao_minutos, ocupados, agora):
                continue
            fim = inicio + timedelta(minutes=servico.duracao_minutos)
            ocupados.append((inicio, fim))
            session.add(
                Agendamento(
                    cliente_nome=sorteio.choice(NOMES),
                    cliente_telefone=f"119{sorteio.randint(10_000_000, 99_999_999)}",
                    servico_id=servico.id,
                    inicio=inicio,
                    fim=fim,
                )
            )

    session.commit()


_ultimo_reset = None
_trava = threading.Lock()


def garantir_atualizada() -> None:
    """Reseta a demonstração se ainda não foi resetada hoje (no fuso da barbearia)."""
    global _ultimo_reset
    hoje = regras.agora_local().date()
    if _ultimo_reset == hoje:
        return
    with _trava:
        if _ultimo_reset == hoje:  # outra requisição pode ter resetado enquanto esperávamos
            return
        with Session(engine) as session:
            resetar(session, regras.agora_local())
        _ultimo_reset = hoje
