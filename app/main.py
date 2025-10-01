from datetime import datetime
import json
from math import ceil
import re
from uuid import UUID
from fastapi import FastAPI, HTTPException, Query, status
import requests
from scalar_fastapi import get_scalar_api_reference

from app.database.session import create_db_tables
from app.dependencies import TrajetoServiceDep
from .apis.config import api_settings as settings
from googletrans import Translator
from google import genai


async def lifespan_handler(app: FastAPI):
    await create_db_tables()
    yield


app = FastAPI(lifespan=lifespan_handler)

client = genai.Client(api_key=settings.GEMINI_KEY)
translator = Translator()


@app.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title="RotaJá API")


@app.get("/buscar/{cep}")
async def buscar_cep(cep: str):
    response = requests.get(f"{settings.VIACEP_URL}/{cep}/json/")
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na API: Erro ao buscar CEP - {response.status_code}.",
        )


@app.get("/formatar/{cep}")
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


@app.get("/coordenadas/{cep}")
async def obter_coordenadas(cep: str, numero: str = Query(None)):
    endereco_completo = await formatar_cep(cep, numero)
    response = requests.get(f"{settings.LOCATIONIQ_URL}{endereco_completo}&format=json")
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
    if response.status_code == 200:
        referencias = response.json()
        return [element for element in referencias["elements"]]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na API: Erro ao obter pontos de referência - {response.status_code}.",
        )


@app.get("/trafego/{cep}")
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


@app.get("/trajeto_simples")
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
            "veiculo_exemplo": trajeto_json["routes"][0]["sections"][0]["travelMode"],
        }
        return trajeto_formatado
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na API: Erro ao buscar informações do trajeto - {informacoes_trajeto.status_code}",
        )


@app.get("/trajeto_completo")
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
            f"{settings.LOCATIONIQ_REVERSE_GEOCODING_URL}{settings.LOCATIONIQ_KEY}&lat={ponto['latitude']}&lon={ponto['longitude']}&format=json"
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
            cep_infos = await buscar_cep(trecho["cep"])

            cidade = cep_infos.get("localidade")
            response = requests.get(
                f"{settings.WEATHER_API_URL}{cidade}&days={dias_previsao_clima}&key={settings.WEATHER_API_KEY}"
            )

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


@app.get("/retornar_trajeto")
async def retornar_trajeto(id: UUID, senha_trajeto: str, service: TrajetoServiceDep):
    return await service.get_trajeto(id, senha_trajeto)


@app.post("/ai_insights")
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


@app.get("/retornar_insight")
async def retornar_insight(id: UUID, senha_trajeto: str, service: TrajetoServiceDep):
    return await service.get_insight(id, senha_trajeto)


def limpar_resposta(texto: str):
    return re.sub(r"^```json\s*|\s*```$", "", texto, flags=re.MULTILINE)


def formatar_numero(texto: str):
    texto = texto.replace(".", "&")
    texto = texto.replace(",", ".")
    texto = texto.replace("&", ",")
    return texto


def comprimir_pontos_da_rota(pontos, max_ceps: int = 30):
    n = len(pontos)
    if n == 0:
        return []
    if n <= max_ceps:
        return pontos.copy()

    k = max_ceps
    step = (n - 1) / (k - 1)
    indices = []
    for i in range(k):
        idx = int(round(i * step))
        if idx < 0:
            idx = 0
        elif idx > n - 1:
            idx = n - 1
        indices.append(idx)

    seen = set()
    unique_indices = []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            unique_indices.append(idx)
    if unique_indices[0] != 0:
        unique_indices.insert(0, 0)
    if unique_indices[-1] != n - 1:
        unique_indices.append(n - 1)

    filtrado = [pontos[i] for i in unique_indices]
    return filtrado
