"""O banco recusa agendamentos confirmados com horários sobrepostos.

A API já confere conflitos antes de salvar, mas essa checagem tem uma brecha:
se dois clientes pedirem o mesmo horário ao mesmo tempo, os dois consultam o banco,
os dois veem o horário livre e os dois salvam. Com esta constraint, o Postgres
aceita só o primeiro; o segundo recebe erro e a API responde 409.

  EXCLUDE USING gist (tsrange(inicio, fim) WITH &&)
    "nenhum par de linhas pode ter intervalos [inicio, fim) que se sobreponham (&&)"
  WHERE (status = 'confirmado')
    "...considerando só os confirmados": cancelar libera o horário

O intervalo é [inicio, fim), então 10:00-10:30 e 10:30-11:00 não conflitam.
Só existe no Postgres; no SQLite (desenvolvimento local) vale apenas a checagem da API.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-20
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        "ALTER TABLE agendamento ADD CONSTRAINT agendamento_fim_depois_do_inicio "
        "CHECK (fim > inicio)"
    )
    op.execute(
        "ALTER TABLE agendamento ADD CONSTRAINT agendamento_sem_sobreposicao "
        "EXCLUDE USING gist (tsrange(inicio, fim) WITH &&) "
        "WHERE (status = 'confirmado')"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE agendamento DROP CONSTRAINT agendamento_sem_sobreposicao")
    op.execute("ALTER TABLE agendamento DROP CONSTRAINT agendamento_fim_depois_do_inicio")
