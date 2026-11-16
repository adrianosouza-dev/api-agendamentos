from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from app.auth import HASH_FALSO, SessionDep, criar_token, verificar_senha
from app.models import Token, Usuario

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    """Recebe usuário e senha (formulário) e devolve um token JWT."""
    usuario = session.exec(select(Usuario).where(Usuario.usuario == form.username)).first()
    # Mesma mensagem para usuário inexistente e senha errada: não damos pistas a um atacante.
    # Também conferimos a senha contra um hash falso quando o usuário não existe, para que
    # o tempo de resposta seja parecido nos dois casos.
    senha_hash = usuario.senha_hash if usuario else HASH_FALSO
    senha_ok = verificar_senha(form.password, senha_hash)
    if usuario is None or not senha_ok:
        raise HTTPException(
            status_code=401,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=criar_token(usuario.usuario))
