"""Configurações da aplicação, lidas de variáveis de ambiente (arquivo .env)."""

import os
from datetime import time

from dotenv import load_dotenv

# Lê o arquivo .env (se existir). Variáveis já definidas no sistema têm prioridade.
load_dotenv()


def _hora(valor: str) -> time:
    horas, minutos = valor.split(":")
    return time(int(horas), int(minutos))


# Banco de dados: SQLite local por padrão. Em produção, use a URL do Postgres (ex.: Supabase).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agendamentos.db")

# Autenticação
SECRET_KEY = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")
TOKEN_EXPIRA_MINUTOS = int(os.getenv("TOKEN_EXPIRA_MINUTOS", "60"))
ADMIN_USUARIO = os.getenv("ADMIN_USUARIO", "admin")
ADMIN_SENHA = os.getenv("ADMIN_SENHA", "admin123")

# Funcionamento da barbearia
FUSO_HORARIO = os.getenv("FUSO_HORARIO", "America/Sao_Paulo")
HORA_ABERTURA = _hora(os.getenv("HORA_ABERTURA", "09:00"))
HORA_FECHAMENTO = _hora(os.getenv("HORA_FECHAMENTO", "19:00"))
INTERVALO_MINUTOS = int(os.getenv("INTERVALO_MINUTOS", "30"))
# 0 = segunda ... 6 = domingo
DIAS_FUNCIONAMENTO = {int(d) for d in os.getenv("DIAS_FUNCIONAMENTO", "0,1,2,3,4,5").split(",")}

# Sites autorizados a chamar a API pelo navegador (CORS), separados por vírgula
CORS_ORIGINS = [
    origem.strip()
    for origem in os.getenv("CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",")
    if origem.strip()
]
