from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from app.auth import SessionDep, criar_token, verificar_senha
from app.models import Token, Usuario

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    """Recebe usuário e senha (formulário) e devolve um token JWT."""
    usuario = session.exec(select(Usuario).where(Usuario.usuario == form.username)).first()
    # Mesma mensagem para usuário inexistente e senha errada: não damos pistas a um atacante
    if usuario is None or not verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(
            status_code=401,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=criar_token(usuario.usuario))
