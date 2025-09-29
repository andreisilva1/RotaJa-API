from fastapi import FastAPI
import requests
from scalar_fastapi import get_scalar_api_reference
from .apis.config import api_settings as settings

app = FastAPI()


@app.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title="AgilizaCEP API")


@app.get("/buscar/{cep}")
async def buscar_cep(cep: int):
    response = requests.get(f"{settings.VIACEP_URL}/{cep}/json/")
    return response.json()


@app.get("/formatar/{cep}")
async def formatar_cep(cep: int):
    response = requests.get(f"{settings.VIACEP_URL}/{cep}/json/")
    data = response.json()
    logradouro = data.get("logradouro")
    bairro = data.get("bairro")
    cidade = data.get("localidade")
    estado = data.get("uf")

    endereco_completo = f"{logradouro}, {bairro}, {cidade} - {estado}, Brasil"
    return endereco_completo


@app.get("/latitude_longitude/{endereco_completo}", include_in_schema=False)
async def obter_latitude_longitude(endereco_completo: str):
    response = requests.get(f"{settings.LOCATIONIQ_URL}{endereco_completo}&format=json")
    data = response.json()
    lat = data[0].get("lat")
    lon = data[0].get("lon")
    location_class = data[0].get("class")
    address_type = data[0].get("type")
    display_name = data[0].get("display_name")
    return {
        "lat": lat,
        "lon": lon,
        "display_name": display_name,
        "class": location_class,
        "type": address_type,
    }


@app.get("/referencias/{cep}")
async def pontos_de_referencia(cep: int, raio_em_metros: float):
    endereco_completo = await formatar_cep(cep)
    data = await obter_latitude_longitude(endereco_completo)
    longitude, latitude = data["lon"], data["lat"]
    response = requests.get(
        f"{settings.OVERPASS_URL}{raio_em_metros},{latitude},{longitude});out;"
    )
    data = response.json()
    return [element for element in data["elements"]]


@app.get("/")
async def read_root():
    return {"message": "Olá, Mundo!"}
