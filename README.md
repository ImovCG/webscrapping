# ImovCG - Web Scrapping

Pipeline ETL para coleta semanal de anúncios de imóveis para aluguel em Campina Grande/PB, parte da plataforma **ImovCG**. Os dados são coletados da OLX e de um grupo do Facebook, normalizados, filtrados e enviados ao [backend ImovCG](https://github.com/ImovCG/backend).

## Arquitetura

```
scraper_olx.py      ┐   a cada N coletados (BACKEND_BATCH_SIZE):
scraper_facebook.py ┴──▶ normaliza (config.yaml) ─▶ dados_limpos_*.csv ─▶ POST /api/imoveis/lote
                    │
                    └──▶ dados_crus_*.jsonl (arquivo bruto + dedup)
```

O `pipeline.py` roda em **streaming por lotes**: cada scraper coleta `BACKEND_BATCH_SIZE` anúncios (default 20) e já dispara normalização + envio daquele lote, em vez de esperar coletar tudo. Assim os imóveis aparecem no backend de forma incremental. Os scrapers também gravam os dados crus (campos `_raw`) num JSONL unificado (distinguidos pelo campo `fonte`, usado pra deduplicação); o normalizador é único e fonte-agnóstico, traduzindo qualquer fonte para o schema de domínio. O scraper do Facebook é **opcional** — se os cookies de sessão não estiverem presentes, ele é pulado e só a OLX roda.

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

### Facebook (opcional)

O grupo do Facebook exige sessão logada — o FB bloqueia o conteúdo com um modal de login logo no 2º post. A coleta usa **cookies de sessão**, gerados uma vez manualmente e reusados pelo scraper. **Nenhuma senha é digitada de forma automatizada.**

Checklist do dev (o que é manual):

1. Tenha uma conta no Facebook (de preferência descartável, não a pessoal — automação pode levar a checkpoint/ban) e entre no grupo alvo.
2. Na **sua máquina** (com navegador/tela), gere os cookies:
   ```bash
   python salvar_cookies.py
   # abre o Chrome → faça login manualmente → aperte ENTER → gera artifacts/fb_cookies.json
   ```
3. Rodando local, já está pronto. Rodando em VM/Docker, copie o arquivo pra VM:
   ```bash
   scp artifacts/fb_cookies.json usuario@vm:~/imovcg/secrets/fb_cookies.json
   ```
   O `docker-compose.yml` monta `./secrets` no container e aponta `FB_COOKIES_PATH` pra ele.
4. Os cookies duram semanas. Quando o log acusar `Sessao do Facebook invalida/expirada`, repita os passos 2–3. Enquanto isso, o pipeline segue coletando só a OLX.

Variáveis de ambiente (opcionais, com defaults) em `.env.example`: `FB_GROUP_ID`, `FB_COOKIES_PATH`, `FB_MAX_SCROLLS`, `FB_SCROLL_PAUSA`.

> O `fb_cookies.json` é um segredo de sessão e está no `.gitignore` — nunca comite.

## Uso

### Execução manual completa

```bash
python pipeline.py
```

### Etapas individuais

```bash
python scraper_olx.py       # apenas coleta OLX
python scraper_facebook.py  # apenas coleta Facebook (requer cookies)
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
├── scraper_facebook.py     # Coleta posts de grupo do Facebook → JSONL cru
├── salvar_cookies.py       # Helper de login manual → gera fb_cookies.json
├── normalizador.py         # Normaliza e filtra → CSV limpo
├── backend_client.py       # Envia dados ao backend
├── pipeline.py             # Orquestrador das etapas
├── config.yaml             # Configuração de filtros
├── .env.example            # Template de credenciais do backend
├── .env                    # Credenciais do backend (ignorado pelo git)
├── .gitignore
├── artifacts/              # Dados e logs (ignorado pelo git)
│   ├── dados_crus_*.jsonl      # Dados brutos por coleta (OLX + Facebook)
│   ├── dados_limpos_*.csv      # Dados normalizados por coleta
│   ├── fb_cookies.json         # Cookies de sessão do Facebook (segredo)
│   ├── fb_posts_coletados.csv  # IDs de posts do FB já coletados (dedup)
│   ├── falhou_envio_*.json     # Payloads não enviados
│   └── pipeline_*.log          # Logs de execução
├── openspec/               # Specs e changes (OpenSpec)
└── requirements.txt
```

## Integração com o Backend

O backend ImovCG (Spring Boot, porta 8080, MySQL) define o contrato de domínio. O scraper se adapta a ele via normalizador. Para detalhes das alterações necessárias no backend, consulte [`backend-INTEGRACAO.md`](../backend-INTEGRACAO.md).
