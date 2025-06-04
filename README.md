
# Monitor de Queimadas INPE

> Projeto de Global Solution - FIAP 2025  
> Sistema de monitoramento automático de focos de queimadas utilizando dados do INPE

---

## 📋 Funcionalidades
- Processa arquivos CSV com coordenadas de queimadas
- Classifica intensidade (alta/média/baixa) usando DBSCAN
- Converte latitude/longitude em nomes de municípios
- Gera relatório em JSON com dados organizados
- Interface de menu interativa



##  Estrutura do Projeto
├── monitor_queimadas.py    # Código principal
├── dados_queimadas/        # Pasta de dados
│   ├── queimadas.csv       # Exemplo de arquivo de entrada
│   └── regioes_queimadas.json  # Saída gerada
└── README.md               # Este arquivo
   
## Dependências

pip install pandas geopy scikit-learn numpy

