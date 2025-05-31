import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta

# Configurações
DOWNLOAD_DIR = os.path.join(os.getcwd(), "dados_queimadas")
INPE_URL = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/10min/"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


# --- Funções ---
def verificar_instalacao_chrome():
    """Verifica se o Chrome está instalado no caminho especificado"""
    if not os.path.exists(CHROME_PATH):
        raise FileNotFoundError(
            f"Chrome não encontrado em {CHROME_PATH}\n"
            "Instale o Chrome ou ajuste o caminho no código."
        )


def configurar_navegador():
    """Configura o navegador Chrome para automação"""
    try:
        verificar_instalacao_chrome()

        chrome_options = Options()
        chrome_options.binary_location = CHROME_PATH

        # configurações de download
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
        })

        # modo headless (opcional - remova se quiser ver o navegador)
        chrome_options.add_argument("--headless=new")

        # configuração do webdriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver

    except Exception as e:
        print(f"Erro ao configurar navegador: {e}")
        raise


def baixar_arquivo_mais_recente(driver):
    """encontra e baixa o arquivo CSV mais recente do INPE"""
    try:
        print("Acessando o site do INPE...")
        driver.get(INPE_URL)
        time.sleep(3)

        print("Buscando arquivos CSV...")
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '.csv')]")

        if not links:
            raise Exception("Nenhum arquivo CSV encontrado!")

        # filtra arquivos dos últimos 30 minutos (ajuste conforme necessário)
        limite_tempo = datetime.now() - timedelta(minutes=30)
        arquivos_validos = []

        for link in links:
            nome_arquivo = link.text
            try:
                # extrai data/hora do nome do arquivo (ex: focos_10min_20250529_1200.csv)
                partes = nome_arquivo.split('_')
                data_str = partes[2]  # AAAAMMDD
                hora_str = partes[3].split('.')[0]  # HHMM
                data_hora = datetime.strptime(f"{data_str}{hora_str}", "%Y%m%d%H%M")

                if data_hora >= limite_tempo:
                    arquivos_validos.append((data_hora, link))
            except:
                continue

        if not arquivos_validos:
            raise Exception("Nenhum arquivo recente encontrado!")

        # Ordena do mais recente para o mais antigo
        arquivos_validos.sort(reverse=True, key=lambda x: x[0])

        # Baixa o mais recente
        print(f"Baixando arquivo: {arquivos_validos[0][1].text}")
        arquivos_validos[0][1].click()
        time.sleep(10)  # Tempo para download

        return arquivos_validos[0][0]  # Retorna a data do arquivo

    except Exception as e:
        print(f"Erro ao baixar arquivo: {e}")
        raise


def processar_dados():
    """Processa o arquivo CSV baixado e gera um JSON"""
    try:
        print("Processando dados...")

        # Lista arquivos CSV na pasta de downloads
        arquivos = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.csv')]
        if not arquivos:
            raise Exception("Nenhum arquivo CSV encontrado!")

        # Pega o arquivo mais recente
        arquivo_mais_recente = max(
            [os.path.join(DOWNLOAD_DIR, f) for f in arquivos],
            key=os.path.getctime
        )
        print(f"Arquivo selecionado: {arquivo_mais_recente}")

        # Lê o CSV (ajuste o separador se necessário)
        df = pd.read_csv(arquivo_mais_recente, header=None)

        # Processa cada linha (formato: lat,lon,satélite,data)
        dados_processados = []
        for linha in df[0]:
            if pd.isna(linha):
                continue
            partes = str(linha).split(',')
            if len(partes) >= 4:
                dados_processados.append({
                    "latitude": float(partes[0]),
                    "longitude": float(partes[1]),
                    "satelite": partes[2].strip(),
                    "data_hora": partes[3].strip()
                })

        # Salva como JSON
        json_path = os.path.join(DOWNLOAD_DIR, "dados_processados.json")
        pd.DataFrame(dados_processados).to_json(json_path, orient="records", date_format="iso")
        print(f"Dados salvos em: {json_path}")

        return json_path

    except Exception as e:
        print(f"Erro ao processar dados: {e}")
        raise


# --- Execução Principal ---
if __name__ == "__main__":
    print("=== Monitor de Queimadas INPE ===")
    print("Coleta automática a cada 10 minutos")
    print("Pressione Ctrl+C para encerrar\n")

    while True:
        try:
            # Registra hora de início
            inicio = datetime.now()
            print(f"\n>>> Iniciando ciclo: {inicio.strftime('%d/%m/%Y %H:%M:%S')}")

            # --- Seu código original aqui ---
            driver = None
            try:
                driver = configurar_navegador()
                data_arquivo = baixar_arquivo_mais_recente(driver)
                json_path = processar_dados()
                print(f"Dados atualizados em: {data_arquivo}")
            except Exception as e:
                print(f"Erro durante execução: {e}")
            finally:
                if driver:
                    driver.quit()
            # --- Fim do seu código original ---

            # Calcula tempo restante para próxima execução
            tempo_execucao = (datetime.now() - inicio).total_seconds()
            espera = max(600 - tempo_execucao, 0)  # Garante mínimo 10 minutos entre execuções

            print(f"\nPróxima execução em: {espera / 60:.1f} minutos")
            time.sleep(espera)

        except KeyboardInterrupt:
            print("\nEncerrando monitoramento...")
            break
        except Exception as e:
            print(f"ERRO GRAVE: {e}")
            print("Reiniciando em 1 minuto...")
            time.sleep(60)