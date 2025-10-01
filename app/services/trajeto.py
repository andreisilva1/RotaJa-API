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

    async def add_trajeto(self, senha_trajeto: str, trajeto: dict):
        novo_trajeto = Trajeto(
            id=uuid4(),
            senha=ph.hash(senha_trajeto),
            dados_trajeto=trajeto,
            insights=None,
        )
        self.session.add(novo_trajeto)
        await self.session.commit()
        return {
            "dados_para_busca": {"id": novo_trajeto.id, "senha": senha_trajeto},
            "trajeto": trajeto,
        }

    async def get_trajeto(self, id: UUID, senha_trajeto: str):
        trajeto = await self.session.execute(select(Trajeto).where(Trajeto.id == id))
        trajeto_formatado = trajeto.scalar_one_or_none()
        try:
            if trajeto_formatado and ph.verify(trajeto_formatado.senha, senha_trajeto):
                return trajeto_formatado
        except argon2.exceptions.VerifyMismatchError:
            pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não foram encontrados trajetos armazenados com as informações fornecidas.",
        )

    async def add_insight(self, id: UUID, senha_trajeto: str, resposta_formatada: dict):
        trajeto = await self.session.execute(select(Trajeto).where(Trajeto.id == id))
        trajeto_formatado = trajeto.scalar_one_or_none()
        try:
            if trajeto_formatado and ph.verify(trajeto_formatado.senha, senha_trajeto):
                trajeto_formatado.insights = resposta_formatada
                self.session.add(trajeto_formatado)
                await self.session.commit()
                await self.session.refresh(trajeto_formatado)
                return resposta_formatada
        except argon2.exceptions.VerifyMismatchError:
            pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não foram encontrados trajetos armazenados com as informações fornecidas.",
        )

    async def get_insight(self, id: UUID, senha_trajeto: str):
        trajeto = await self.get_trajeto(id, senha_trajeto)
        if not trajeto or not trajeto["insights"]:
            return {
                "detail": "Não foram encontrados insights para o trajeto fornecido."
            }
        else:
            return trajeto["insights"]

    async def delete_trajeto(self, id: UUID, senha_trajeto: str):
        trajeto = await self.get_trajeto(id, senha_trajeto)
        if trajeto:
            await self.session.delete(trajeto)
            await self.session.commit()
            return {"detail": f"Trajeto de id {id} removido."}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trajeto não encontrado com as informações fornecidas.",
        )

    async def delete_insight(self, id: UUID, senha_trajeto: str):
        trajeto = await self.get_trajeto(id, senha_trajeto)
        if trajeto and trajeto.insights:
            trajeto.insights = None
            self.session.add(trajeto)
            await self.session.commit()
            await self.session.refresh(trajeto)
            return {"detail": f"Insight removido para o trajeto de id {id}"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight não encontrado para o trajeto fornecido.",
        )
