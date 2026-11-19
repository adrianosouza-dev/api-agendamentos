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

# Modo demonstração (versão pública do portfólio): cria dados de exemplo e um login
# "demo" público, e renova tudo uma vez por dia. Veja app/demo.py.
DEMO_MODO = os.getenv("DEMO_MODO", "false").strip().lower() in ("1", "true", "sim")

# Segurança: com banco de produção (Postgres), não deixa subir com a chave ou senha de exemplo.
# Com a chave padrão, qualquer pessoa que leu este código conseguiria forjar um token de admin.
if not DATABASE_URL.startswith("sqlite"):
    if SECRET_KEY == "troque-esta-chave-em-producao" or len(SECRET_KEY) < 32:
        raise RuntimeError("Defina uma SECRET_KEY aleatória com 32+ caracteres (veja o .env.example)")
    if ADMIN_SENHA in ("admin123", "troque-esta-senha"):
        raise RuntimeError("Defina uma ADMIN_SENHA própria (veja o .env.example)")
