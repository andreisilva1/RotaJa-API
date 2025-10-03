from fastapi import FastAPI

from .database.session import create_db_tables
from .routers import cep, insights, trajeto


async def lifespan_handler(app: FastAPI):
    await create_db_tables()
    yield


description = """
# Sobre

- RotaJá é uma API orquestradora que converte CEPs em informações geográficas, logísticas e de referência, além da possibilidade de insights gerados por IA. Ideal para estudos, testes e prototipagem; em fase de testes, **não recomendado para uso comercial**.

## Link para o repositório + documentação completa:
- [https://github.com/andreisilva1/RotaJa-API](https://github.com/andreisilva1/RotaJa-API)

## Observações
- Em caso de dúvidas, sugestões ou para relatar algum problema, envie um email para: contato@rotaja.com.br
"""

app = FastAPI(
    docs_url="/",
    lifespan=lifespan_handler,
    title="RotaJá API",
    version="1.0.0",
    description=description,
)

app.include_router(cep.router)
app.include_router(trajeto.router)
app.include_router(insights.router)
