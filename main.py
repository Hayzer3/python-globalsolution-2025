# importando as bibliotecas que vamos usar
import os  # pra trabalhar com pastas e arquivos
import io  # pra lidar com dados em memória
import json  # pra trabalhar com arquivos json
import requests  # pra fazer requisições na internet
import pandas as pd  # pra trabalhar com tabelas de dados
import numpy as np  # pra cálculos matemáticos
from datetime import datetime  # pra trabalhar com datas
from geopy.geocoders import Nominatim  # pra converter coordenadas em nomes de cidades
from geopy.exc import GeocoderTimedOut  # pra tratar erros de timeout
from sklearn.cluster import DBSCAN  # pra agrupar pontos próximos
from bs4 import BeautifulSoup  # pra ler html de páginas web

# pasta onde vamos salvar os dados
download_dir = "dados_queimadas"
os.makedirs(download_dir, exist_ok=True)  # cria a pasta se não existir

# caminho do arquivo json que vai guardar os dados
json_path = os.path.join(download_dir, "regioes_queimadas.json")
if not os.path.exists(json_path):  # se o arquivo não existir
    with open(json_path, "w", encoding="utf-8") as f:  # cria um arquivo vazio
        json.dump([], f, indent=4, ensure_ascii=False)

# função que pega coordenadas e devolve o nome da cidade
def converter_para_municipio(lat, lon):
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

# função que classifica se a queimada é baixa, média ou alta intensidade
def classificar_intensidade(coordenadas):
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

# pega o link do arquivo mais recente no site do inpe
def obter_url_ultimo_csv():
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
        ultimo_csv = sorted(arquivos_csv)[-1]  # pega o mais recente
        return url_base + ultimo_csv
    except Exception as e:
        print(f"erro ao obter o link do csv mais recente: {e}")
        return None

# processa os dados de queimadas
def processar_regioes_queimadas():
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
                "dataqueimada": data_hora_str,
                "municipio": municipio,
                "intensidadequeimada": intensidade,
                "latitude": lat,
                "longitude": lon
            })
        # salva tudo no arquivo json
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(saida, f, indent=4, ensure_ascii=False)
        print(f"\njson salvo em: {json_path}")
        print(json.dumps(saida, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"erro ao processar queimadas: {e}")

# mostra o menu pro usuário
def exibir_menu():
    print("\n=== menu do monitor de queimadas ===")
    print("1. ver regiões com queimadas agora")
    print("2. sair")

# controla o menu
def executar_menu():
    while True:  # CORREÇÃO: 'True' com T maiúsculo
        exibir_menu()
        escolha = input("escolha uma opção (1 ou 2): ").strip()
        if escolha == "1":
            processar_regioes_queimadas()
        elif escolha == "2":
            print("encerrando o programa...")
            break
        else:
            print("opção inválida. tente novamente.")

# inicia o programa
if __name__ == "__main__":
    print("bem-vindo ao monitor de queimadas")
    executar_menu()