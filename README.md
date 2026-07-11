# ImovCG - Web Scrapping

Pipeline ETL para coleta semanal de anúncios de imóveis para aluguel em Campina Grande/PB, parte da plataforma **ImovCG**. Os dados são coletados da OLX, normalizados, filtrados e enviados ao [backend ImovCG](https://github.com/ImovCG/backend).

## Arquitetura

```
scraper_olx.py → dados_crus_*.jsonl → normalizador.py → dados_limpos_*.csv → backend_client.py → POST /api/imoveis
                                       (filtros via config.yaml)
                                       pipeline.py orquestra as 3 etapas
```

O scraper gera dados crus (campos `_raw`); o normalizador é único e fonte-agnóstico, traduzindo qualquer fonte para o schema de domínio; o backend client envia ao backend via HTTP.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuração

Edite `config.yaml` para ajustar os filtros:

```yaml
filtros:
  preco_maximo: 1500
  bairros_permitidos: []       # vazio = aceita todos
  categorias_permitidas: []    # vazio = aceita todas
  remover_sem_preco: true
  remover_sem_bairro: false
```

Copie `.env.example` para `.env` e configure o backend:

```bash
cp .env.example .env
# edite .env com a URL e token do backend
```

```env
BACKEND_URL=http://localhost:8080/api/imoveis
BACKEND_TOKEN=seu_token_aqui
BACKEND_TIMEOUT=30
```

## Uso

### Execução manual completa

```bash
python pipeline.py
```

### Etapas individuais

```bash
python scraper_olx.py       # apenas coleta
python normalizador.py      # normaliza o último JSONL
python backend_client.py    # envia o último CSV
```

## Agendamento Semanal (cron)

```bash
crontab -e
```

Adicione a linha (executa todo sábado às 10h):

```
0 10 * * 6 cd /caminho/para/webscrapping && .venv/bin/python pipeline.py >> artifacts/cron.log 2>&1
```

## Estrutura de Arquivos

```
.
├── scraper_olx.py          # Coleta dados da OLX → JSONL cru
├── normalizador.py         # Normaliza e filtra → CSV limpo
├── backend_client.py       # Envia dados ao backend
├── pipeline.py             # Orquestrador das 3 etapas
├── config.yaml             # Configuração de filtros
├── .env.example            # Template de credenciais do backend
├── .env                    # Credenciais do backend (ignorado pelo git)
├── .gitignore
├── artifacts/              # Dados e logs (ignorado pelo git)
│   ├── dados_crus_*.jsonl      # Dados brutos por coleta
│   ├── dados_limpos_*.csv      # Dados normalizados por coleta
│   ├── falhou_envio_*.json     # Payloads não enviados
│   └── pipeline_*.log          # Logs de execução
├── openspec/               # Specs e changes (OpenSpec)
└── requirements.txt
```

## Integração com o Backend

O backend ImovCG (Spring Boot, porta 8080, MySQL) define o contrato de domínio. O scraper se adapta a ele via normalizador. Para detalhes das alterações necessárias no backend, consulte [`backend-INTEGRACAO.md`](../backend-INTEGRACAO.md).
