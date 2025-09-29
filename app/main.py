from math import ceil
from fastapi import FastAPI, Query
import requests
from scalar_fastapi import get_scalar_api_reference
from .apis.config import api_settings as settings

app = FastAPI()


@app.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title="AgilizaCEP API")


@app.get("/buscar/{cep}")
async def buscar_cep(cep: str):
    response = requests.get(f"{settings.VIACEP_URL}/{cep}/json/")
    return response.json()


@app.get("/formatar/{cep}")
async def formatar_cep(cep: str, numero: str = Query(None)):
    response = requests.get(f"{settings.VIACEP_URL}/{cep}/json/")
    data = response.json()
    logradouro = data.get("logradouro")
    bairro = data.get("bairro")
    cidade = data.get("localidade")
    estado = data.get("uf")
    endereco_completo = f"{logradouro}"
    if numero:
        endereco_completo += f", {numero}"
    endereco_completo += f", {bairro}, {cidade} - {estado}, Brasil"
    return endereco_completo


@app.get("/latitude_longitude/{endereco_completo}")
async def obter_coordenadas(endereco_completo: str):
    response = requests.get(f"{settings.LOCATIONIQ_URL}{endereco_completo}&format=json")
    data = response.json()
    lat = data[0].get("lat")
    lon = data[0].get("lon")
    location_class = data[0].get("class")
    address_type = data[0].get("type")
    display_name = data[0].get("display_name")
    bounding_box = data[0].get("boundingbox")

    return {
        "lat": lat,
        "lon": lon,
        "display_name": display_name,
        "class": location_class,
        "type": address_type,
        "bounding_box": bounding_box,
    }


@app.get("/referencias/{cep}")
async def pontos_de_referencia(
    cep: str, raio_em_metros: float = 300, numero: str = Query(None)
):
    endereco_completo = await formatar_cep(cep, numero if numero else None)
    coordenadas = await obter_coordenadas(endereco_completo)
    longitude, latitude = coordenadas["lon"], coordenadas["lat"]
    response = requests.get(
        f"{settings.OVERPASS_URL}{raio_em_metros},{latitude},{longitude});out;"
    )
    data = response.json()
    return [element for element in data["elements"]]


@app.get("/trafico/{cep}")
async def retornar_trafico(cep: str):
    endereco_completo = await formatar_cep(cep)
    coordenadas = await obter_coordenadas(endereco_completo)
    longitude, latitude = coordenadas["lon"], coordenadas["lat"]
    minY = coordenadas["bounding_box"][0]
    maxY = coordenadas["bounding_box"][1]
    minX = coordenadas["bounding_box"][2]
    maxX = coordenadas["bounding_box"][3]
    boundingBox = f"{minY},{maxY},{minX},{maxX}"
    incidentes = requests.get(
        f"{settings.TOMTOM_URL}/incidentViewport/{boundingBox}/0/{boundingBox}/22/true/json?key={settings.TOMTOM_KEY}&jsonp=callback"
    )
    congestionamento = requests.get(
        f"{settings.TOMTOM_URL}/flowSegmentData/absolute/10/json?point={latitude},{longitude}&unit=KMPH&fields=currentSpeed,freeFlowSpeed,confidence&key={settings.TOMTOM_KEY}"
    )
    incidentes = incidentes.json()
    congestionamento = congestionamento.json()
    lista_incidentes = incidentes["viewpResp"]["trafficState"].get("incidents", [])

    dados_incidentes = {
        "idade_das_informacoes_segundos": incidentes["viewpResp"]["trafficState"].get(
            "@trafficAge"
        ),
        "contagem_de_incidentes": len(lista_incidentes),
        "incidentes": lista_incidentes
        if lista_incidentes
        else "Não há incidentes registrados nesse trecho.",
    }
    dados_congestionamento = {
        "velocidadeAtual": congestionamento["flowSegmentData"]["currentSpeed"],
        "velocidadeLivre": congestionamento["flowSegmentData"]["freeFlowSpeed"],
        "tempoAproximado_em_VelocidadeAtual_minutos": ceil(
            congestionamento["flowSegmentData"]["currentTravelTime"] / 60
        ),
        "tempoAproximado_em_VelocidadeLivre_minutos": ceil(
            congestionamento["flowSegmentData"]["freeFlowTravelTime"] / 60
        ),
        "confiabilidade": congestionamento["flowSegmentData"]["confidence"],
        "rua_fechada": congestionamento["flowSegmentData"]["roadClosure"],
    }
    return {
        "incidentes_registrados": dados_incidentes,
        "taxa_de_congestionamento": dados_congestionamento,
    }
