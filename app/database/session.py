from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel
from .config import database_settings as settings

engine = create_async_engine(url=settings.DATABASE_URL)


async def create_db_tables():
    async with engine.begin() as conn:
        from .models import Trajeto  # noqa: F401

        await conn.run_sync(SQLModel.metadata.create_all)


async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
