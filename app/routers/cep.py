from math import ceil
from math import ceil
from fastapi import HTTPException, Query, status, APIRouter
import requests

from ..apis.config import api_settings as settings

router = APIRouter(tags=["CEP"], prefix="/cep")


@router.get("/buscar/{cep}")
async def buscar_cep(cep: str):
    response = requests.get(f"{settings.VIACEP_URL}/{cep}/json/")
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na API: Erro ao buscar CEP - {response.status_code}.",
        )


@router.get("/formatar/{cep}")
async def formatar_cep(cep: str, numero: str = Query(None)):
    response = requests.get(f"{settings.VIACEP_URL}/{cep}/json/")
    if response.status_code == 200:
        endereco_completo = response.json()
        logradouro = endereco_completo.get("logradouro")
        bairro = endereco_completo.get("bairro")
        cidade = endereco_completo.get("localidade")
        estado = endereco_completo.get("uf")
        endereco_formatado = f"{logradouro}"
        if numero:
            endereco_formatado += f", {numero}"
        endereco_formatado += f", {bairro}, {cidade} - {estado}, Brasil"
        return endereco_formatado
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na API: Erro ao obter endereço - {response.status_code}.",
        )


@router.get("/coordenadas/{cep}")
async def obter_coordenadas(cep: str, numero: str = Query(None)):
    endereco_completo = await formatar_cep(cep, numero)
    response = requests.get(
        f"{settings.LOCATIONIQ_URL}&q={endereco_completo}&format=json"
    )
    if response.status_code == 200:
        coordenadas = response.json()
        lat = coordenadas[0].get("lat")
        lon = coordenadas[0].get("lon")
        location_class = coordenadas[0].get("class")
        address_type = coordenadas[0].get("type")
        display_name = coordenadas[0].get("display_name")
        bounding_box = coordenadas[0].get("boundingbox")

        return {
            "lat": lat,
            "lon": lon,
            "display_name": display_name,
            "class": location_class,
            "type": address_type,
            "bounding_box": bounding_box,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na API: Erro ao obter coordenadas - {response.status_code}.",
        )


@router.get("/referencias/{cep}")
async def pontos_de_referencia(
    cep: str, raio_em_metros: float = 300, numero: str = Query(None)
):
    coordenadas = await obter_coordenadas(cep, numero)
    longitude, latitude = coordenadas["lon"], coordenadas["lat"]
    response = requests.get(
        f"{settings.OVERPASS_URL}{raio_em_metros},{latitude},{longitude});out;"
    )
    if response.status_code == 200:
        referencias = response.json()
        return [element for element in referencias["elements"]]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na API: Erro ao obter pontos de referência - {response.status_code}.",
        )


@router.get("/trafego/{cep}")
async def retornar_trafego(cep: str):
    coordenadas = await obter_coordenadas(cep, numero=None)

    longitude, latitude = coordenadas["lon"], coordenadas["lat"]
    minY = coordenadas["bounding_box"][0]
    maxY = coordenadas["bounding_box"][1]
    minX = coordenadas["bounding_box"][2]
    maxX = coordenadas["bounding_box"][3]
    boundingBox = f"{minY},{maxY},{minX},{maxX}"
    incidentes = requests.get(
        f"{settings.TOMTOM_URL}/incidentViewport/{boundingBox}/0/{boundingBox}/22/true/json?key={settings.TOMTOM_KEY}"
    )
    congestionamento = requests.get(
        f"{settings.TOMTOM_URL}/flowSegmentData/absolute/10/json?point={latitude},{longitude}&unit=KMPH&fields=currentSpeed,freeFlowSpeed,confidence&key={settings.TOMTOM_KEY}"
    )
    if incidentes.status_code == 200:
        incidentes = incidentes.json()

        lista_incidentes = incidentes["viewpResp"]["trafficState"].get("incidents", [])
        dados_incidentes = {
            "idade_das_informacoes_segundos": incidentes["viewpResp"][
                "trafficState"
            ].get("@trafficAge"),
            "contagem_de_incidentes": len(lista_incidentes),
            "incidentes": lista_incidentes
            if lista_incidentes
            else "Não há incidentes registrados nesse trecho.",
        }
    else:
        dados_incidentes = {
            "erro": f"Falha na API: Erro ao processar indicentes - {incidentes.status_code}"
        }
    if congestionamento.status_code == 200:
        dados_congestionamento = congestionamento.json()
        dados_congestionamento = {
            "velocidadeAtual": dados_congestionamento["flowSegmentData"][
                "currentSpeed"
            ],
            "velocidadeLivre": dados_congestionamento["flowSegmentData"][
                "freeFlowSpeed"
            ],
            "tempoAproximado_em_VelocidadeAtual_minutos": ceil(
                dados_congestionamento["flowSegmentData"]["currentTravelTime"] / 60
            ),
            "tempoAproximado_em_VelocidadeLivre_minutos": ceil(
                dados_congestionamento["flowSegmentData"]["freeFlowTravelTime"] / 60
            ),
            "tempoAproximado_em_VelocidadeAtual_horas": round(
                dados_congestionamento["flowSegmentData"]["currentTravelTime"] / 3600, 2
            ),
            "tempoAproximado_em_VelocidadeLivre_horas": round(
                dados_congestionamento["flowSegmentData"]["freeFlowTravelTime"] / 3600,
                2,
            ),
            "confiabilidade": dados_congestionamento["flowSegmentData"]["confidence"],
            "rua_fechada": dados_congestionamento["flowSegmentData"]["roadClosure"],
        }
    else:
        dados_congestionamento = {
            f"Falha na API: Erro ao processar congestionamento - {congestionamento.status_code}"
        }
    return {
        "incidentes_registrados": dados_incidentes,
        "taxa_de_congestionamento": dados_congestionamento,
    }
