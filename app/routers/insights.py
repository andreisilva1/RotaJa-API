import json
from uuid import UUID
from fastapi import APIRouter
from app.dependencies import TrajetoServiceDep
from ..apis.config import api_settings as settings
from app.routers.trajeto import retornar_trajeto
from google import genai

from app.utils import limpar_resposta

router = APIRouter(tags=["insights"], prefix="/insights")
client = genai.Client(api_key=settings.GEMINI_KEY)


@router.post("/criar_com_ia")
async def ai_insights(
    id: UUID, senha_trajeto: str, service: TrajetoServiceDep, salvar_no_banco: int = 0
):
    dados_trajeto = await retornar_trajeto(id, senha_trajeto, service)
    prompt = settings.PROMPT_BASE.format(dados_trajeto=dados_trajeto)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )
    resposta_formatada = json.loads(limpar_resposta(response.text))
    if salvar_no_banco == 1:
        await service.add_insight(id, senha_trajeto, resposta_formatada)
    return resposta_formatada


@router.get("/retornar")
async def retornar_insight(id: UUID, senha_trajeto: str, service: TrajetoServiceDep):
    return await service.get_insight(id, senha_trajeto)


@router.delete("/excluir_insight_salvo")
async def excluir_insight(id: UUID, senha_trajeto: str, service: TrajetoServiceDep):
    return await service.delete_insight(id, senha_trajeto)
