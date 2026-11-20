"""Tabelas iniciais: usuário (admin), serviço e agendamento.

Igual ao que o create_all gerava antes do Alembic. Bancos criados naquela época
recebem esta versão como "já aplicada" (veja app/database.py: migrar).

Revision ID: 0001
Revises:
Create Date: 2026-11-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "servico",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=60), nullable=False),
        sa.Column("duracao_minutos", sa.Integer(), nullable=False),
        sa.Column("preco", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario", sa.String(), nullable=False),
        sa.Column("senha_hash", sa.String(), nullable=False),
    )
    op.create_index("ix_usuario_usuario", "usuario", ["usuario"], unique=True)
    op.create_table(
        "agendamento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cliente_nome", sa.String(), nullable=False),
        sa.Column("cliente_telefone", sa.String(), nullable=False),
        sa.Column("servico_id", sa.Integer(), sa.ForeignKey("servico.id"), nullable=False),
        sa.Column("inicio", sa.DateTime(), nullable=False),
        sa.Column("fim", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("confirmado", "cancelado", name="statusagendamento"),
            nullable=False,
        ),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_agendamento_inicio", "agendamento", ["inicio"])


def downgrade() -> None:
    op.drop_index("ix_agendamento_inicio", table_name="agendamento")
    op.drop_table("agendamento")
    op.drop_index("ix_usuario_usuario", table_name="usuario")
    op.drop_table("usuario")
    op.drop_table("servico")
    sa.Enum(name="statusagendamento").drop(op.get_bind(), checkfirst=True)
