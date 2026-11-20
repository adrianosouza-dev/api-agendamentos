"""Tabelas do banco e formatos de entrada/saída da API."""

import re
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import NaiveDatetime, field_validator
from sqlmodel import Field, SQLModel

from app.regras import agora_local, para_horario_local

# ---------------------------------------------------------------- Usuários (admin)


class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario: str = Field(index=True, unique=True)
    senha_hash: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------- Serviços


class ServicoBase(SQLModel):
    nome: str = Field(min_length=2, max_length=60)
    duracao_minutos: int = Field(gt=0, le=240)
    preco: Decimal = Field(ge=0, max_digits=8, decimal_places=2)

    @field_validator("nome", mode="before")
    @classmethod
    def tirar_espacos(cls, valor):
        # Antes de checar o tamanho: "   " não pode passar como nome válido
        return valor.strip() if isinstance(valor, str) else valor


class Servico(ServicoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ativo: bool = True  # "apagar" um serviço só desativa, para não perder o histórico


class ServicoCriar(ServicoBase):
    pass


class ServicoLeitura(ServicoBase):
    id: int


# ---------------------------------------------------------------- Agendamentos


class StatusAgendamento(str, Enum):
    confirmado = "confirmado"
    cancelado = "cancelado"


class Agendamento(SQLModel, table=True):
    # No Postgres, o banco também impede dois confirmados com horários sobrepostos
    # (constraint criada em migrations/versions/0002_bloqueia_sobreposicao.py).
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_nome: str
    cliente_telefone: str
    servico_id: int = Field(foreign_key="servico.id")
    # Horário local da barbearia, guardado sem fuso (NaiveDatetime).
    # A partir do SQLModel 0.0.45, um "datetime" comum exige fuso horário no banco.
    inicio: NaiveDatetime = Field(index=True)
    fim: NaiveDatetime
    status: StatusAgendamento = Field(default=StatusAgendamento.confirmado)
    criado_em: NaiveDatetime = Field(default_factory=agora_local)


class AgendamentoCriar(SQLModel):
    cliente_nome: str = Field(min_length=2, max_length=80)
    cliente_telefone: str = Field(max_length=20)
    servico_id: int
    inicio: datetime

    @field_validator("cliente_nome", mode="before")
    @classmethod
    def tirar_espacos(cls, valor):
        # Antes de checar o tamanho: "   " não pode passar como nome válido
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("cliente_telefone")
    @classmethod
    def validar_telefone(cls, valor: str) -> str:
        digitos = re.sub(r"\D", "", valor)  # aceita "(45) 99999-9999" e guarda só os números
        if len(digitos) not in (10, 11):
            raise ValueError("Telefone deve ter DDD + número (10 ou 11 dígitos)")
        return digitos

    @field_validator("inicio")
    @classmethod
    def normalizar_fuso(cls, valor: datetime) -> datetime:
        return para_horario_local(valor)


class AgendamentoLeitura(SQLModel):
    id: int
    cliente_nome: str
    cliente_telefone: str
    servico_id: int
    inicio: datetime
    fim: datetime
    status: StatusAgendamento
    criado_em: datetime


class HorariosLivres(SQLModel):
    data: date
    servico_id: int
    horarios: list[str]


class InfoBarbearia(SQLModel):
    abertura: str
    fechamento: str
    intervalo_minutos: int
    dias_funcionamento: list[int]  # 0 = segunda ... 6 = domingo
    demo: bool
