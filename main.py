"""
Monitoramento de Queimadas - INPE
Script para coletar, processar e classificar dados de focos de incêndio.
"""

# 1. IMPORTAÇÕES (agrupadas por categoria)
# ----------------------------------------
# Bibliotecas padrão
import os
import io
import json
from datetime import datetime

# Bibliotecas de terceiros
import requests
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from sklearn.cluster import DBSCAN
from bs4 import BeautifulSoup

# 2. CONSTANTES E CONFIGURAÇÕES
# -----------------------------
DOWNLOAD_DIR = "dados_queimadas"
JSON_PATH = os.path.join(DOWNLOAD_DIR, "regioes_queimadas.json")
API_ENDPOINT = "http://localhost:8080/api/ponto-queimadas/batch"
API_HEADERS = {"Content-Type": "application/json"}

# 3. FUNÇÕES AUXILIARES (sem dependências entre si)
# -------------------------------------------------
def criar_diretorio_se_nao_existir():
    """Cria o diretório de downloads se não existir"""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def inicializar_arquivo_json():
    """Cria um arquivo JSON vazio se não existir"""
    if not os.path.exists(JSON_PATH):
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4, ensure_ascii=False)

def formatar_data_para_api(data_str):
    """Converte o formato de data para o padrão ISO 8601 (com 'T')"""
    return data_str.replace(" ", "T")

# 4. FUNÇÕES PRINCIPAIS (com dependências lógicas)
# -----------------------------------------------
def converter_para_municipio(lat, lon):
    """Converte coordenadas geográficas em nome de município"""
    try:
        # usa o nominatim (openstreetmap) pra achar a cidade
        geolocator = Nominatim(user_agent="monitor_queimadas_v2")
        localizacao = geolocator.reverse((lat, lon), timeout=15, language='pt-br')
        if localizacao and 'address' in localizacao.raw:
            endereco = localizacao.raw['address']
            # tenta pegar o nome da cidade de vários campos possíveis
            return (endereco.get("city")
                    or endereco.get("town")
                    or endereco.get("village")
                    or endereco.get("municipality")
                    or endereco.get("county")
                    or endereco.get("state_district")
                    or "desconhecido")
        return "desconhecido"
    except GeocoderTimedOut:  # se demorar muito, tenta de novo
        try:
            return converter_para_municipio(lat, lon)
        except:
            return "desconhecido"
    except Exception as e:  # se der outro erro
        print(f"erro na geocodificação: {str(e)} | coord: ({lat}, {lon})")
        return "desconhecido"

def classificar_intensidade(coordenadas):
    """Classifica a intensidade dos focos de queimada"""
    if not coordenadas:  # se não tiver coordenadas
        return []
    coords_array = np.array(coordenadas)
    kms_per_radian = 6371.0088  # raio da terra em km
    eps_km = 10 / kms_per_radian  # considera 10km como limite
    # usa o dbscan pra agrupar pontos próximos
    db = DBSCAN(eps=eps_km, min_samples=2, metric='haversine').fit(np.radians(coords_array))
    labels = db.labels_
    resultado = []
    for label in set(labels):
        if label == -1:  # pontos isolados
            grupo = [tuple(c) for i, c in enumerate(coords_array) if labels[i] == -1]
            intensidade = "baixa"
        else:  # pontos agrupados
            grupo = [tuple(c) for i, c in enumerate(coords_array) if labels[i] == label]
            tamanho = len(grupo)
            # define a intensidade pelo tamanho do grupo
            if tamanho >= 10:
                intensidade = "alta"
            elif tamanho >= 3:
                intensidade = "média"
            else:
                intensidade = "baixa"
        for coord in grupo:
            resultado.append((coord, intensidade))
    return resultado

def obter_url_ultimo_csv():
    """Obtém a URL do arquivo CSV mais recente do INPE"""
    url_base = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/10min/"
    try:
        response = requests.get(url_base)
        soup = BeautifulSoup(response.content, "html.parser")
        links = soup.find_all("a")
        # pega todos os links que terminam com .csv
        arquivos_csv = [
            link.get("href") for link in links if link.get("href", "").endswith(".csv")
        ]
        if not arquivos_csv:
            raise Exception("nenhum arquivo csv encontrado no site do inpe.")
        ultimo_csv = sorted(arquivos_csv)[-2]  # pega o mais recente
        return url_base + ultimo_csv
    except Exception as e:
        print(f"erro ao obter o link do csv mais recente: {e}")
        return None

def processar_regioes_queimadas():
    """Processa os dados principais de queimadas"""
    try:
        print("\nprocessando arquivo de queimadas do inpe...")
        url_csv = obter_url_ultimo_csv()
        if not url_csv:
            return
        # baixa o arquivo csv
        response = requests.get(url_csv)
        response.encoding = "utf-8"
        df = pd.read_csv(io.StringIO(response.text))  # lê o csv
        if df.empty:
            print("o arquivo csv está vazio.")
            return
        # pega a data do arquivo ou usa a data atual (formato corrigido)
        data_hora_str = df['data_hora'].iloc[0] if 'data_hora' in df.columns else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        coordenadas = list(zip(df['lat'], df['lon']))  # pega todas as coordenadas
        intensidade_lista = classificar_intensidade(coordenadas)  # classifica a intensidade
        saida = []
        for (lat, lon), intensidade in intensidade_lista:
            municipio = converter_para_municipio(lat, lon)  # pega o nome da cidade
            saida.append({
                "dataQueimada": data_hora_str,
                "intensidadeQueimada": intensidade,
                "municipio": municipio,
                "latitudeQueimada": lat,
                "longitudeQueimada": lon
            })
        # salva tudo no arquivo json
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(saida, f, indent=4, ensure_ascii=False)
        print(f"\njson salvo em: {JSON_PATH}")
        print(json.dumps(saida, indent=4, ensure_ascii=False))

        endpoint = "http://localhost:8080/api/ponto-queimadas/batch"
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(endpoint, json=saida, headers=headers)
            response.raise_for_status()  # Levanta um erro para respostas não-sucedidas
            print(f"\nDados enviados com sucesso para {endpoint}")
            print(f"Resposta do servidor: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"\nErro ao enviar dados para o endpoint: {e}")
    except Exception as e:
        print(f"erro ao processar queimadas: {e}")

# 5. FUNÇÕES DE INTERFACE (menu e execução)
# -----------------------------------------
def exibir_menu():
    """Mostra o menu de opções para o usuário"""
    print("\n=== Menu do monitor de queimadas ===")
    print("1. Ver regiões com queimadas nos últimos 10 munitos")
    print("2. Sair")

def executar_menu():
    """Controla o fluxo do programa baseado nas escolhas do usuário"""
    while True:
        exibir_menu()
        escolha = input("escolha uma opção (1 ou 2): ").strip()
        if escolha == "1":
            processar_regioes_queimadas()
        elif escolha == "2":
            print("encerrando o programa...")
            break
        else:
            print("opção inválida. tente novamente.")


# 6. BLOCO PRINCIPAL
# ------------------
if __name__ == "__main__":
    # Inicialização
    criar_diretorio_se_nao_existir()
    inicializar_arquivo_json()

    # Mensagem de boas-vindas
    print("Bem-vindo ao Monitor de Queimadas")

    # Iniciar interface
    executar_menu()