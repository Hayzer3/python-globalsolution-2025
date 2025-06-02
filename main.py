import os
import time
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# configurações
download_dir = os.path.join(os.getcwd(), "dados_queimadas")
inpe_url = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/10min/"
chrome_path = r"c:\program files\google\chrome\application\chrome.exe"

# verifica se o chrome está instalado
def verificar_instalacao_chrome():
    if not os.path.exists(chrome_path):
        raise FileNotFoundError(
            f"chrome não encontrado em {chrome_path}\n"
            "instale o chrome ou ajuste o caminho no código."
        )

# configura o navegador para automação
def configurar_navegador():
    try:
        verificar_instalacao_chrome()
        chrome_options = Options()
        chrome_options.binary_location = chrome_path

        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
        })

        chrome_options.add_argument("--headless=new")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"erro ao configurar navegador: {e}")
        raise

# busca e baixa o arquivo csv mais recente do site do inpe
def baixar_arquivo_mais_recente(driver):
    try:
        print("acessando o site do inpe...")
        driver.get(inpe_url)
        time.sleep(3)

        print("buscando arquivos csv...")
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '.csv')]")

        if not links:
            raise Exception("nenhum arquivo csv encontrado!")

        limite_tempo = datetime.now() - timedelta(minutes=30)
        arquivos_validos = []

        for link in links:
            nome_arquivo = link.text
            try:
                partes = nome_arquivo.split('_')
                data_str = partes[2]
                hora_str = partes[3].split('.')[0]
                data_hora = datetime.strptime(f"{data_str}{hora_str}", "%Y%m%d%H%M")
                if data_hora >= limite_tempo:
                    arquivos_validos.append((data_hora, link))
            except:
                continue

        if not arquivos_validos:
            raise Exception("nenhum arquivo recente encontrado!")

        arquivos_validos.sort(reverse=True, key=lambda x: x[0])
        print(f"baixando arquivo: {arquivos_validos[0][1].text}")
        arquivos_validos[0][1].click()
        time.sleep(10)

        return arquivos_validos[0][0]
    except Exception as e:
        print(f"erro ao baixar arquivo: {e}")
        raise

# faz a geocodificação reversa para converter coordenadas em nome de local
def obter_localizacao(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 10,
            "addressdetails": 1
        }
        headers = {
            "user-agent": "queimadas-monitor/1.0"
        }
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            endereco = data.get("address", {})
            cidade = endereco.get("city") or endereco.get("town") or endereco.get("village") or ""
            estado = endereco.get("state", "")
            pais = endereco.get("country", "")
            return f"{cidade}, {estado}, {pais}".strip(", ")
        else:
            return "localização não encontrada"
    except Exception:
        return "erro ao buscar localização"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "dados_queimadas")

def converter_para_localizacao(latitude, longitude):
    """converte latitude e longitude para endereço legível"""
    try:
        geolocator = Nominatim(user_agent="monitor_queimadas")
        localizacao = geolocator.reverse(f"{latitude}, {longitude}", timeout=10)
        return localizacao.address if localizacao else "desconhecido"
    except GeocoderTimedOut:
        return "tempo esgotado"
    except Exception as e:
        return f"erro: {e}"

# processa os dados do csv e gera um json com coordenadas e nomes de local
def processar_dados():
    """processa o arquivo csv baixado e gera um json"""
    try:
        print("processando dados...")

        arquivos = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.csv')]
        if not arquivos:
            raise Exception("nenhum arquivo csv encontrado!")

        arquivo_mais_recente = max(
            [os.path.join(DOWNLOAD_DIR, f) for f in arquivos],
            key=os.path.getctime
        )
        print(f"arquivo selecionado: {arquivo_mais_recente}")

        # lê o csv corretamente, usando as colunas
        df = pd.read_csv(arquivo_mais_recente)

        print(f"linhas lidas do csv: {len(df)}")

        dados_processados = []
        for index, row in df.iterrows():
            try:
                lat = float(row['lat'])
                lon = float(row['lon'])
                satelite = str(row['satelite']).strip()
                data_hora = str(row['data']).strip()

                # aqui você pode chamar a função de localização se quiser
                localizacao = converter_para_localizacao(lat, lon)

                dados_processados.append({
                    "latitude": lat,
                    "longitude": lon,
                    "satelite": satelite,
                    "data_hora": data_hora,
                    "localizacao": localizacao
                })

            except Exception as e:
                print(f"erro ao processar linha {index}: {e}")
                continue

        if not dados_processados:
            raise Exception("nenhum dado processado!")

        json_path = os.path.join(DOWNLOAD_DIR, "dados_processados.json")
        pd.DataFrame(dados_processados).to_json(json_path, orient="records", date_format="iso")
        print(f"dados salvos em: {json_path}")

        return json_path

    except Exception as e:
        print(f"erro ao processar dados: {e}")
        raise


# execução principal do programa
if __name__ == "__main__":
    print("=== monitor de queimadas inpe ===")
    print("coleta automática a cada 10 minutos")
    print("pressione ctrl+c para encerrar\n")

    while True:
        try:
            inicio = datetime.now()
            print(f"\n>>> iniciando ciclo: {inicio.strftime('%d/%m/%Y %H:%M:%S')}")
            driver = None
            try:
                driver = configurar_navegador()
                data_arquivo = baixar_arquivo_mais_recente(driver)
                json_path = processar_dados()
                print(f"dados atualizados em: {data_arquivo}")
            except Exception as e:
                print(f"erro durante execução: {e}")
            finally:
                if driver:
                    driver.quit()

            tempo_execucao = (datetime.now() - inicio).total_seconds()
            espera = max(600 - tempo_execucao, 0)
            print(f"\npróxima execução em: {espera / 60:.1f} minutos")
            time.sleep(espera)

        except KeyboardInterrupt:
            print("\nencerrando monitoramento...")
            break
        except Exception as e:
            print(f"erro grave: {e}")
            print("reiniciando em 1 minuto...")
            time.sleep(60)