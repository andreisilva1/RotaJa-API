from uuid import UUID, uuid4
from sqlalchemy import Column
from sqlmodel import JSON, Field, SQLModel
from sqlalchemy.dialects import postgresql


class Trajeto(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(postgresql.UUID, default=uuid4(), primary_key=True, index=True)
    )
    senha: str
    dados_trajeto: dict = Field(default_factory=dict, sa_column=Column(JSON))
