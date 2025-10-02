from datetime import datetime
from math import ceil
from uuid import UUID
from fastapi import HTTPException, Query, status, APIRouter
from googletrans import Translator
import requests

from app.dependencies import TrajetoServiceDep
from ..apis.config import api_settings as settings
from app.routers.cep import obter_coordenadas, retornar_trafego
from app.utils import comprimir_pontos_da_rota, formatar_numero

router = APIRouter(tags=["Trajeto"], prefix="/trajeto")
translator = Translator()


@router.get("/simples")
async def calcular_trajeto_simples(
    cep_origem: str,
    cep_destino: str,
    numero_origem: str = Query(None),
    numero_destino: str = Query(None),
):
    coordenadas_origem = await obter_coordenadas(cep_origem, numero_origem)
    coordenadas_destino = await obter_coordenadas(cep_destino, numero_destino)
    informacoes_trajeto = requests.get(
        f"https://api.tomtom.com/routing/1/calculateRoute/{coordenadas_origem['lat']},{coordenadas_origem['lon']}:{coordenadas_destino['lat']},{coordenadas_destino['lon']}/json?traffic=true&travelMode=car&key={settings.TOMTOM_KEY}"
    )

    if informacoes_trajeto.status_code == 200:
        trajeto_json = informacoes_trajeto.json()
        trajeto_formatado = {
            "distancia_em_km": formatar_numero(
                str(trajeto_json["routes"][0]["summary"]["lengthInMeters"] / 1000)
            ),
            "tempo_estimado_em_minutos": ceil(
                trajeto_json["routes"][0]["summary"]["travelTimeInSeconds"] / 60
            ),
            "tempo_estimado_em_horas": round(
                trajeto_json["routes"][0]["summary"]["travelTimeInSeconds"] / 3600, 2
            ),
            "veiculo_exemplo": trajeto_json["routes"][0]["sections"][0]["travelMode"],
        }
        return trajeto_formatado
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na API: Erro ao buscar informações do trajeto - {informacoes_trajeto.status_code}",
        )


@router.get("/completo")
async def calcular_trajeto_completo(
    cep_origem: str,
    cep_destino: str,
    service: TrajetoServiceDep,
    numero_origem: str = Query(None),
    numero_destino: str = Query(None),
    senha_trajeto: str = Query(None),
    dias_previsao_clima: int = 14,
):
    if dias_previsao_clima < 1 or dias_previsao_clima > 14:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"1 à 14 dias de previsão esperado, informado: {dias_previsao_clima}. Informe um valor válido ou deixe em branco para retornar a previsão dos próximos 14 dias.",
        )

    coordenadas_origem = await obter_coordenadas(cep_origem, numero_origem)
    coordenadas_destino = await obter_coordenadas(cep_destino, numero_destino)

    informacoes_trajeto = requests.get(
        f"https://api.tomtom.com/routing/1/calculateRoute/{coordenadas_origem['lat']},{coordenadas_origem['lon']}:{coordenadas_destino['lat']},{coordenadas_destino['lon']}/json?traffic=true&travelMode=car&key={settings.TOMTOM_KEY}"
    )

    if informacoes_trajeto.status_code == 200:
        trajeto_json = informacoes_trajeto.json()
        informacoes_basicas_trajeto = {
            "distancia_em_km": formatar_numero(
                str(trajeto_json["routes"][0]["summary"]["lengthInMeters"] / 1000)
            ),
            "tempo_estimado_em_minutos": ceil(
                trajeto_json["routes"][0]["summary"]["travelTimeInSeconds"] / 60
            ),
            "tempo_estimado_em_horas": round(
                trajeto_json["routes"][0]["summary"]["travelTimeInSeconds"] / 3600, 2
            ),
            "veiculo_exemplo": trajeto_json["routes"][0]["sections"][0]["travelMode"],
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na API: Erro ao buscar informações do trajeto - {informacoes_trajeto.status_code}",
        )

    trechos = []
    rota_filtrada = comprimir_pontos_da_rota(
        trajeto_json["routes"][0]["legs"][0]["points"]
    )
    for ponto in rota_filtrada:
        response = requests.get(
            f"{settings.LOCATIONIQ_REVERSE_GEOCODING_URL}{settings.LOCATIONIQ_KEY}&q=&lat={ponto['latitude']}&lon={ponto['longitude']}&format=json"
        )
        trechos.append(response.json())

    trechos_filtrados = []
    for trecho in trechos:
        trecho_filtrado = {
            "rua": trecho.get("address", {}).get("road", "não fornecido"),
            "bairro": trecho.get("address", {}).get("neighbourhood", "não fornecido"),
            "cidade": trecho.get("address", {}).get("town", "não fornecido"),
            "estado": trecho.get("address", {}).get("state", "não fornecido"),
            "cep": trecho.get("address", {}).get("postcode", "não fornecido"),
        }
        if trecho_filtrado["rua"] != "não fornecido":
            (
                trechos_filtrados.append(trecho_filtrado)
                if not trechos_filtrados
                or not any(
                    trecho_filtrado["rua"] == trecho["rua"]
                    for trecho in trechos_filtrados
                )
                else None
            )
        else:
            trechos_filtrados.append(trecho_filtrado)
    for trecho in trechos_filtrados:
        previsao_clima = []
        if trecho["cep"] != "não fornecido":
            trafego_atual = await retornar_trafego(trecho["cep"].replace("-", ""))
            trecho["trafego"] = trafego_atual
            coordenadas = await obter_coordenadas(trecho["cep"], numero=None)

            longitude, latitude = coordenadas["lon"], coordenadas["lat"]

            url = f"{settings.WEATHER_API_URL}{settings.WEATHER_API_KEY}&q={latitude},{longitude}&days={dias_previsao_clima}"

            response = requests.get(url)

            clima = response.json()
            for dia in clima["forecast"]["forecastday"]:
                clima_esperado = await translator.translate(
                    dia["day"]["condition"]["text"], src="en", dest="pt"
                )
                data_nao_formatada = datetime.strptime(dia["date"], "%Y-%m-%d")
                clima_dia = {
                    "data": data_nao_formatada.strftime("%d/%m/%Y"),
                    "temp_maxima": formatar_numero(str(dia["day"]["maxtemp_c"])),
                    "temp_minima": formatar_numero(str(dia["day"]["mintemp_c"])),
                    "temp_media": formatar_numero(str(dia["day"]["avgtemp_c"])),
                    "clima_esperado": clima_esperado.text,
                }
                previsao_clima.append(clima_dia)
            trecho["clima"] = previsao_clima
    trajeto = {
        "informacoes_basicas": informacoes_basicas_trajeto,
        "rota": trechos_filtrados,
    }
    if senha_trajeto:
        return await service.add_trajeto(senha_trajeto, trajeto)
    return trajeto


@router.get("/retornar")
async def retornar_trajeto(id: UUID, senha_trajeto: str, service: TrajetoServiceDep):
    trajeto = await service.get_trajeto(id, senha_trajeto)
    return trajeto.model_dump(exclude=["senha"])


@router.delete("/excluir_trajeto_salvo")
async def excluir_trajeto(id: UUID, senha_trajeto: str, service: TrajetoServiceDep):
    return await service.delete_trajeto(id, senha_trajeto)
