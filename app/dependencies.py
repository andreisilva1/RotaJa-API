from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_session
from app.services.trajeto import TrajetoService


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def create_trajeto_service(session: SessionDep):
    return TrajetoService(session)


TrajetoServiceDep = Annotated[TrajetoService, Depends(create_trajeto_service)]
