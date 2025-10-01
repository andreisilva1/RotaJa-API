from uuid import UUID, uuid4
import argon2
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database.models import Trajeto
from argon2 import PasswordHasher

ph = PasswordHasher()


class TrajetoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, senha: str, trajeto: dict):
        novo_trajeto = Trajeto(id=uuid4(), senha=ph.hash(senha), dados_trajeto=trajeto)
        self.session.add(novo_trajeto)
        await self.session.commit()
        return {
            "dados_para_busca": {"id": novo_trajeto.id, "senha": senha},
            "trajeto": trajeto,
        }

    async def get(self, id: UUID, senha: str):
        trajeto = await self.session.execute(select(Trajeto).where(Trajeto.id == id))
        trajeto_formatado = trajeto.scalar_one_or_none()
        try:
            if trajeto_formatado and ph.verify(trajeto_formatado.senha, senha):
                return trajeto_formatado.model_dump(exclude=["senha"])
        except argon2.exceptions.VerifyMismatchError:
            pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não foram encontrados trajetos armazenados com as informações fornecidas.",
        )
