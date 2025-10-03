# RotaJá - Tudo em um só ~~lugar~~ CEP ![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)![FastAPI](https://img.shields.io/badge/FastAPI-0.117.1-green?logo=fastapi&logoColor=white)

**RotaJá** é uma API orquestradora que converte CEPs em informações geográficas, logísticas e de referência, com insights gerados por IA. Ideal para estudos, testes e prototipagem.

[Clique aqui para acessar o site oficial](https://api.rotaja.com.br/)

## 🚀 Tecnologias

- FastAPI, SQLModel, SQLAlchemy, Pydantic, argon2, googletrans, google-genai, asyncpg, uvicorn, requests.

## 📚 APIs de apoio

- ![LocationIQ](https://img.shields.io/badge/LocationIQ-Location-blue?style=for-the-badge)  
  Fornece geocodificação e reverse geocoding, convertendo endereços em coordenadas e vice-versa.  
  [Documentação](https://locationiq.com/)

- ![Overpass API](https://img.shields.io/badge/Overpass_API-OSM-blue?style=for-the-badge)  
  Permite consultar dados do OpenStreetMap de forma flexível, como ruas, POIs e outros elementos geográficos.  
  [Documentação](https://wiki.openstreetmap.org/wiki/Overpass_API)

- ![Weather API](https://img.shields.io/badge/Weather_API-Forecast-blue?style=for-the-badge)  
  Fornece dados meteorológicos em tempo real e previsões. Auxilia em funcionalidades dependentes de clima.  
  [Documentação](https://www.weatherapi.com/docs/)

- ![ViaCEP](https://img.shields.io/badge/ViaCEP-CEP-brightgreen?style=for-the-badge)  
  Serviço brasileiro para consulta de endereços via CEP. Útil para validar e formatar endereços automaticamente.  
  [Documentação](https://viacep.com.br/)

- ![Gemini](https://img.shields.io/badge/Gemini-AI-purple?style=for-the-badge)  
  Utilizada para geração de insights e processamento avançado de dados.  
  [Documentação](https://ai.google.dev/gemini-api/docs)

- ![TomTom](https://img.shields.io/badge/TomTom-Maps-red?style=for-the-badge)  
  Oferece mapas, rotas e tráfego em tempo real, ideal para cálculos de rotas e geolocalização avançada.  
  [Documentação](https://developer.tomtom.com/documentation)

## 📘 Endpoints + exemplos

Url base:

```
https://www.api.rotaja.com.br
```

### 📍 **CEP**

**GET -> /cep/buscar/{cep}:**

**Recebe:**

- CEP (apenas números).

**Retorna:**

- cep, logradouro, complemento, unidade, bairro, localidade, uf, estado, regiao, ibge, gia, ddd, siafi.

**Exemplo:**

`/cep/buscar/01001000`

**Retorno:**

```json
{
  "cep": "01001-000",
  "logradouro": "Praça da Sé",
  "complemento": "lado ímpar",
  "unidade": "",
  "bairro": "Sé",
  "localidade": "São Paulo",
  "uf": "SP",
  "estado": "São Paulo",
  "regiao": "Sudeste",
  "ibge": "3550308",
  "gia": "1004",
  "ddd": "11",
  "siafi": "7107"
}
```

---

**GET -> /cep/formatar/{cep}:**

**Recebe:**

- CEP (apenas números).
- número: opcional, para retornar um endereço mais completo

**Retorna:**

- logradouro, bairro, localidade, uf, Brasil

**Exemplo:**

`/cep/formatar/01001000`

**Retorno:**

```json
"Praça da Sé, Sé, São Paulo - SP, Brasil"
```

---

**GET -> /cep/coordenadas/{cep}:**

**Recebe:**

- CEP (apenas números) e número (opcional: da casa ou estabelecimento, fornece maior precisão)

**Retorna:**

- latitude, longitude e outras informações específicas de coordenadas.

**Exemplo:**

`/cep/coordenadas/01001000`

Retorno:

```json
{
  "lat": "-23.550389799999998",
  "lon": "-46.633080956332904",
  "display_name": "Sé Square, Rua Onze de Agosto, Glicério, Sé, São Paulo, Região Imediata de São Paulo, Região Metropolitana de São Paulo, Região Geográfica Intermediária de São Paulo, São Paulo, Southeast Region, 01018-010, Brazil",
  "class": "tourism",
  "type": "attraction",
  "bounding_box": ["-23.5517242", "-23.5491629", "-46.6342888", "-46.6319455"]
}
```

---

**GET -> /cep/referencias/{cep}:**

**Recebe:**

- CEP (apenas números), raio_em_metros (padrão: 300) e número (opcional: da casa ou estabelecimento, fornece maior precisão).

**Retorna:**

- pontos de referência próximos cadastrados (rua, cep, número, tipo de estabelecimento).

**Exemplo:**

`/cep/referencias/01001000`

**Retorno (exemplo com raio_em_metros = 100):**

```json
[
  {
    "type": "node",
    "id": 5020407096,
    "lat": -23.5497406,
    "lon": -46.632915,
    "tags": {
      "addr:city": "São Paulo",
      "addr:housenumber": "29",
      "addr:postcode": "01016-010",
      "addr:street": "Rua Irmã Simpliciana",
      "amenity": "fast_food",
      "name": "Central da Copa"
    }
  },
  {
    "type": "node",
    "id": 5034583277,
    "lat": -23.5495652,
    "lon": -46.6329023,
    "tags": {
      "amenity": "parking_entrance"
    }
  },
  {
    "type": "node",
    "id": 6579411555,
    "lat": -23.5500267,
    "lon": -46.6334686,
    "tags": {
      "amenity": "clock",
      "date": "no",
      "display": "analog",
      "faces": "4",
      "name": "Relógio",
      "support": "pole",
      "visibility": "street"
    }
  }
]
```

---

**GET -> /cep/trafego/{cep}:**

**Recebe:**

- CEP (apenas números)

**Retorna:**

- dados de tráfego na região (incidentes, congestionamento, velocidade atual e "livre" no trecho + tempo na velocidade atual e livre para percorrer o trecho)

**Exemplo:**

`/cep/trafego/01001000`

**Retorno:**

```json
{
  "incidentes_registrados": {
    "idade_das_informacoes_segundos": 39,
    "contagem_de_incidentes": 0,
    "incidentes": "Não há incidentes registrados nesse trecho."
  },
  "taxa_de_congestionamento": {
    "velocidadeAtual": 23,
    "velocidadeLivre": 23,
    "tempoAproximado_em_VelocidadeAtual_minutos": 3,
    "tempoAproximado_em_VelocidadeLivre_minutos": 2.12,
    "tempoAproximado_em_VelocidadeAtual_horas": 0.05,
    "tempoAproximado_em_VelocidadeLivre_horas": 0.04,
    "confiabilidade": 1,
    "rua_fechada": false
  }
}
```

---

### 🛣️ **Trajeto**

**GET -> /trajeto/simples:**

**Recebe:**

- cep_origem e cep_destino (obrigatórios, apenas números), numero_origem e numero_destino (opcionais, podem fornecer maior precisão)

**Retorna:**

- distância em km, tempo estimado em minutos, tempo estimado em horas e veículo de exemplo.

**Exemplo:**

```bash
/trajeto/simples?cep_origem=01001000&cep_destino=20000000
```

**Retorno:**

```json
{
  "distancia_em_km": "1461,007",
  "tempo_estimado_em_minutos": 1037,
  "tempo_estimado_em_horas": 17.27,
  "veiculo_exemplo": "car"
}
```

---

**GET -> /trajeto/completo:**

**Recebe:**

- cep_origem e cep_destino: obrigatórios, apenas números;
- numero_origem, numero_destino: opcionais, podem fornecer maior precisão;
- senha_trajeto: opcional, usuário deve fornecer uma senha caso deseje salvar o trajeto em banco de dados para consulta mais rápida.
- dias_previsao_clima: quantos dias (até 14) o usuário deseja saber a previsão do clima em trechos do trajeto.

**Retorna:**

- id e senha: se a senha foi fornecida, o id e a senha devem ser armazenado, pois eles serão usados para as consultas;
- informacoes_basicas: distância em km, tempo estimado em minutos, tempo estimado em horas, veiculo de exemplo;

Além disso, divide o trajeto em 30 trechos e, em cada um deles:

Obtém as informações do tráfego e do clima esperado na região para os próximos {dias_previsao_clima} dias.

**Exemplo:**

`/trajeto/completo?cep_origem=01001000&cep_destino=20000000&dias_previsao_clima=14`

**Retorno (primeiro trecho, primeiros 6 dias):**

```json
{
  "informacoes_basicas": {
    "distancia_em_km": "1460,957",
    "tempo_estimado_em_minutos": 1039,
    "tempo_estimado_em_horas": 17.3,
    "veiculo_exemplo": "car"
  },
  "rota": [
    {
      "rua": "Rua Santa Teresa",
      "bairro": "não fornecido",
      "cidade": "não fornecido",
      "estado": "São Paulo",
      "cep": "01016-020",
      "trafego": {
        "incidentes_registrados": {
          "idade_das_informacoes_segundos": 45,
          "contagem_de_incidentes": 0,
          "incidentes": "Não há incidentes registrados nesse trecho."
        },
        "taxa_de_congestionamento": {
          "velocidadeAtual": 23,
          "velocidadeLivre": 23,
          "tempoAproximado_em_VelocidadeAtual_minutos": 3,
          "tempoAproximado_em_VelocidadeLivre_minutos": 2.12,
          "tempoAproximado_em_VelocidadeAtual_horas": 0.05,
          "tempoAproximado_em_VelocidadeLivre_horas": 0.04,
          "confiabilidade": 1,
          "rua_fechada": false
        }
      },
      "clima": [
        {
          "data": "02/10/2025",
          "temp_maxima": "29,1",
          "temp_minima": "17,6",
          "temp_media": "21,3",
          "clima_esperado": "Chuva irregular nas proximidades"
        },
        {
          "data": "03/10/2025",
          "temp_maxima": "29,9",
          "temp_minima": "18,1",
          "temp_media": "22,3",
          "clima_esperado": "Chuva irregular nas proximidades"
        },
        {
          "data": "04/10/2025",
          "temp_maxima": "30,3",
          "temp_minima": "18,5",
          "temp_media": "23,7",
          "clima_esperado": "Chuva irregular nas proximidades"
        },
        {
          "data": "05/10/2025",
          "temp_maxima": "34,7",
          "temp_minima": "19,7",
          "temp_media": "27,2",
          "clima_esperado": "Ensolarado"
        },
        {
          "data": "06/10/2025",
          "temp_maxima": "37,2",
          "temp_minima": "22,7",
          "temp_media": "30,2",
          "clima_esperado": "Ensolarado"
        },
        {
          "data": "07/10/2025",
          "temp_maxima": "19,1",
          "temp_minima": "14,8",
          "temp_media": "17,6",
          "clima_esperado": "Chuva irregular nas proximidades"
        },
```

---

**GET -> /trajeto/retornar:**

**Recebe:**

- id: retornado em /trajeto/completo, se uma senha foi fornecida pelo usuário;
- senha: fornecida pelo usuário em /trajeto/completo

**Retorna:**

- O trajeto completo salvo, caso haja algum com o id e senha fornecidos.

**Exemplo:**

`/trajeto/retornar?id=ID_TRAJETO&senha_trajeto=SENHA_TRAJETO
`

---

**DELETE -> /trajeto/excluir_trajeto_salvo:**

**Recebe:**

- id e senha do trajeto.

**Retorna:**

- Mensagem de confirmação de exclusão ou erro 404, em caso de falha.

**Exemplo:**

```
/trajeto/excluir_trajeto_salvo?id=ID_TRAJETO&senha_trajeto=SENHA_TRAJETO
```

### 🤖 **Insights**

**POST -> /insight/criar_com_ia:**

**Recebe:**

- id e senha do trajeto;
- salvar_no_banco: 0 apenas para retornar, 1 para salvar em banco para consulta rápida.

**Retorna:**

- Insight criado pela IA, com resumo do trajeto, principais observações sobre clima e tráfego, além de observações extras.

**Exemplo:**

```
/insights/criar_com_ia?id=ID_TRAJETO&senha_trajeto=SENHA_TRAJETO&salvar_no_banco=1
```

**GET -> /insight/retornar:**

**Recebe:**

- id e senha do trajeto.

**Retorna:**

- O insight salvo no banco de dados para aquele trajeto, caso houver.

**Exemplo:**

```
/insights/retornar?id=ID_TRAJETO&senha_trajeto=SENHA_TRAJETO
```

**DELETE -> /insight/excluir_insight_salvo:**

**Recebe:**

- id e senha do trajeto.

**Retorna:**

- Mensagem de confirmação de exclusão ou erro 404, em caso de falha.

**Exemplo:**

```
/insights/excluir_insight_salvo?id=ID_TRAJETO&senha_trajeto=SENHA_TRAJETO
```

## Como rodar localmente

## 1. Configuração inicial do repositório

Primeiro, clone o repositório do GitHub e navegue até a pasta principal.

```
git clone https://github.com/andreisilva1/RotaJa-API.git
cd RotaJa-API/app

```

## 2. Ambiente virtual

Crie e ative o ambiente virtual para isolar as dependências do projeto.

**Linux/macOS:**

```
cd backend
python -m venv venv
source venv/bin/activate

```

**Windows (PowerShell):**

```
cd backend
python -m venv venv
venv\scripts\activate

```

## 3. Instalação das dependências

Instale todas as dependências necessárias listadas em `requirements.txt`

```
pip install -r requirements.txt

```

## 4. Variáveis de ambiente

Crie o arquivo `.env` baseado em `.env.example` e armazene suas variáveis, seguindo as instruções.

**Linux/macOS:**

```
cp .env.example .env

```

**Windows:**

```
copy .env.example .env

```

Abra o `.env` e atualize os valores de acordo com sua configuração local.

## 5. Testando a aplicação

Vá até o diretório raiz do projeto (app) e inicie o servidor do FastAPI.

```
cd ../backend
venv\scripts\activate
fastapi run

```

A API estará disponível em: `http://localhost:8000/`.

## Observações

- Sempre utilize `.env.example` como template do `.env`.
