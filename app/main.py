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


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}
