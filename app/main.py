from math import ceil
from fastapi import FastAPI, HTTPException, Query, status
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
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Falha na API: Erro ao obter endereço - {response.status_code}.",
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


@app.get("/latitude_longitude/{endereco_completo}")
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
    endereco_completo = await formatar_cep(cep)
    coordenadas = await obter_coordenadas(endereco_completo)
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
    congestionamento = congestionamento.json()
    if congestionamento.status_code == 200:
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

    return {"informacoes_trajeto": informacoes_trajeto, "rota": trechos_filtrados}


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
