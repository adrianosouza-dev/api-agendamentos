"""Autenticação do administrador: senha com hash (bcrypt) e token JWT."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app import config
from app.database import get_session
from app.models import Usuario

ALGORITMO = "HS256"

# Diz ao FastAPI onde se faz login (habilita o botão "Authorize" no /docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SessionDep = Annotated[Session, Depends(get_session)]


def gerar_hash(senha: str) -> str:
    """Nunca guardamos a senha em si, só o hash dela."""
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    if len(senha.encode()) > 72:  # limite do bcrypt
        return False
    return bcrypt.checkpw(senha.encode(), senha_hash.encode())


def criar_token(usuario: str) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_EXPIRA_MINUTOS)
    return jwt.encode({"sub": usuario, "exp": expira}, config.SECRET_KEY, algorithm=ALGORITMO)


def usuario_atual(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep) -> Usuario:
    """Dependência que protege as rotas de admin: exige um token válido."""
    erro = HTTPException(
        status_code=401,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITMO])
    except jwt.PyJWTError:
        raise erro

    usuario = session.exec(select(Usuario).where(Usuario.usuario == payload.get("sub"))).first()
    if usuario is None:
        raise erro
    return usuario


AdminDep = Annotated[Usuario, Depends(usuario_atual)]


def criar_admin_inicial(session: Session) -> None:
    """Na primeira execução, cria o admin com os dados do .env."""
    if session.exec(select(Usuario)).first() is not None:
        return
    session.add(Usuario(usuario=config.ADMIN_USUARIO, senha_hash=gerar_hash(config.ADMIN_SENHA)))
    session.commit()
