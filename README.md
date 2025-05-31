
# Monitor de Queimadas INPE 🔥🌎

> Projeto de Global Solution - FIAP 2025  
> Sistema de monitoramento automático de focos de queimadas utilizando dados do INPE

---

##  Pré-requisitos

- [Python 3.8+](https://www.python.org/downloads/) (*marque "Add to PATH" na instalação*)  
- [Google Chrome](https://www.google.com/chrome/) instalado  

---

##  Instalação Passo a Passo

1. **Baixe o projeto:**

   ```bash
   git clone https://github.com/seu-usuario/monitor-queimadas.git
   cd monitor-queimadas
   ```

2. **Configure o ambiente virtual:**

   ```bash
   python -m venv venv
   ```

3. **Ative o ambiente virtual:**

   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```

   - **Mac/Linux:**
     ```bash
     source venv/bin/activate
     ```

4. **Instale as dependências:**

   ```bash
   pip install selenium pandas webdriver-manager
   ```

---

##  Como Executar

```bash
python main.py
```

O sistema irá:

- Baixar automaticamente os dados mais recentes  
- Processar os dados para formato JSON  
- Repetir o processo a cada 10 minutos  

Para parar: **Pressione `Ctrl + C`**

---

##  Estrutura do Projeto

```
monitor-queimadas/
├── dados_queimadas/         # Pasta com dados baixados
│   ├── focos_*.csv          # Dados brutos do INPE
│   └── ultimos_dados.json   # Saída processada
├── main.py                  # Código principal
├── README.md                # Este arquivo
└── requirements.txt         # Dependências (gerado automaticamente)
```

---

## 🛠 Tecnologias Utilizadas

- Python 3  
- Selenium WebDriver  
- Pandas (processamento de dados)  
- Webdriver Manager (gerenciamento automático de drivers)  

---

##  Possiveis dúvidas

1. **Não consigo ativar o ambiente virtual**  
   Solução: Execute o terminal como administrador ou use:

   ```bash
   .\venv\Scripts\activate
   ```

2. **Chrome não está instalado no local padrão**  
   Edite o arquivo `main.py` e atualize o caminho:

   ```python
   CHROME_PATH = r"C:\caminho\para\chrome.exe"
   ```
