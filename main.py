
import os # Manipulação de diretórios e arquivos
import pandas as pd # Leitura de CSV e manipulação de dados tabulares
from datetime import datetime # Data e hora
from geopy.geocoders import Nominatim # Geocodificação reversa (lat/lon -> município)
from geopy.exc import GeocoderTimedOut
from sklearn.cluster import DBSCAN  # Algoritmo de clusterização para detectar "grupos de queimadas"

# Operações com arrays numéricos
import numpy as np

# Manipulação de JSON
import json

# Define o diretório onde estão os dados
DOWNLOAD_DIR = os.path.join(os.getcwd(), "dados_queimadas")


def converter_para_municipio(lat, lon):
    """Converte coordenadas em nome de município (ou 'desconhecido')"""
    try:
        geolocator = Nominatim(user_agent="monitor_queimadas")
        localizacao = geolocator.reverse((lat, lon), timeout=10)
        if localizacao and 'address' in localizacao.raw:
            endereco = localizacao.raw['address']
            return endereco.get("city") or endereco.get("town") or endereco.get("village") or "desconhecido"
        return "desconhecido"
    except GeocoderTimedOut:
        return "desconhecido"
    except Exception:
        return "desconhecido"


def classificar_intensidade(coordenadas):
    """Classifica intensidade com base na densidade de queimadas (via DBSCAN)"""
    if not coordenadas:
        return []

    coords_array = np.array(coordenadas)
    kms_per_radian = 6371.0088
    eps_km = 10 / kms_per_radian  # 10 km de raio para formar um cluster
    db = DBSCAN(eps=eps_km, min_samples=2, metric='haversine').fit(np.radians(coords_array))

    labels = db.labels_
    resultado = []

    for label in set(labels):
        if label == -1:
            grupo = [tuple(c) for i, c in enumerate(coords_array) if labels[i] == -1]
            intensidade = "baixa"
        else:
            grupo = [tuple(c) for i, c in enumerate(coords_array) if labels[i] == label]
            tamanho = len(grupo)
            if tamanho >= 10:
                intensidade = "alta"
            elif tamanho >= 5:
                intensidade = "média"
            else:
                intensidade = "baixa"

        for coord in grupo:
            resultado.append((coord, intensidade))
    return resultado


def processar_regioes_queimadas():
    """Processa CSV e gera JSON com data, município e intensidade"""
    try:
        print("\nProcessando arquivo de queimadas...")

        arquivos = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.csv')]
        if not arquivos:
            raise Exception("Nenhum arquivo CSV encontrado no diretório.")

        arquivo_mais_recente = max(
            [os.path.join(DOWNLOAD_DIR, f) for f in arquivos],
            key=os.path.getctime
        )

        df = pd.read_csv(arquivo_mais_recente)
        if df.empty:
            print("⚠️ Arquivo CSV está vazio.")
            return

        data_hora_str = df['data_hora'].iloc[0] if 'data_hora' in df.columns else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        coordenadas = list(zip(df['lat'], df['lon']))
        intensidade_lista = classificar_intensidade(coordenadas)

        saida = []
        for (lat, lon), intensidade in intensidade_lista:
            municipio = converter_para_municipio(lat, lon)
            saida.append({
                "dataqueimada": data_hora_str,
                "municipio": municipio,
                "intensidadeQueimada": intensidade
            })

        json_path = os.path.join(DOWNLOAD_DIR, "regioes_queimadas.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(saida, f, indent=4, ensure_ascii=False)

        print(f"\n✅ JSON salvo em: {json_path}")
        print(json.dumps(saida, indent=4, ensure_ascii=False))

    except Exception as e:
        print(f"❌ Erro ao processar queimadas: {e}")


def exibir_menu():
    """Mostra o menu principal"""
    print("\n=== MENU DO MONITOR DE QUEIMADAS ===")
    print("1. Ver regiões com queimadas agora")
    print("2. Sair")


def executar_menu():
    """Loop principal do menu"""
    while True:
        exibir_menu()
        escolha = input("Escolha uma opção (1 ou 2): ").strip()
        if escolha == "1":
            processar_regioes_queimadas()
        elif escolha == "2":
            print("👋 Encerrando o programa...")
            break
        else:
            print("⚠️ Opção inválida. Tente novamente.")


# Ponto de entrada do programa
if __name__ == "__main__":
    print("🔥 Bem-vindo ao Monitor de Queimadas")
    executar_menu()
