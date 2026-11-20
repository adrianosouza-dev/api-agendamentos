# Imagem da API. Para rodar com Postgres, use o docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependências primeiro: enquanto o requirements.txt não muda, o Docker reaproveita
# esta camada e o build fica rápido mesmo alterando o código.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app

# Não roda como root. A pasta /app fica com o usuário da API para o caso de usar SQLite.
RUN useradd --create-home --uid 1000 api && chown api /app
USER api

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/saude', timeout=4)"

# Ao subir, a API aplica as migrations pendentes sozinha (veja app/database.py).
# PORT permite rodar em hospedagens que escolhem a porta (Render, Railway...).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
