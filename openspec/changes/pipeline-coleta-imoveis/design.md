## Context

Projeto de disciplina com duração de 2 semestres. Atualmente temos um scraper da OLX (Selenium + Python) que gera JSON cru. Precisamos estruturar uma pipeline que normalize, filtre, exporte CSV e envie dados ao backend, preparando a arquitetura para múltiplas fontes futuras (Facebook, Zap, etc).

## Goals / Non-Goals

**Goals:**
- Pipeline de ETL: Extract (scraper) → Transform (normalizador) → Load (CSV + backend)
- Schema intermediário padronizado que qualquer fonte futura pode gerar
- Normalizador único que serve todas as fontes
- Filtros configuráveis (preço máximo, bairros, categorias)
- Exportação CSV e envio HTTP ao backend
- Agendamento semanal via cron

**Non-Goals:**
- Interface gráfica ou dashboard
- Geocoding (calcular distância exata até a universidade)
- Crawlers para outras fontes além da OLX (apenas arquitetura preparada)

## Decisions

### Schema intermediário: JSON Lines com campos _raw
Cada scraper gera um arquivo `.jsonl` onde cada linha é um objeto JSON com todos os campos em texto puro (sufixo `_raw`) + metadados (`fonte`, `external_id`, `data_coleta`). O normalizador é o único responsável por parsear e limpar.

**Alternativa considerada:** Cada scraper já sair com dados limpos. Rejeitada porque centralizar a lógica de parse evita duplicação quando novas fontes entrarem.

### Deduplicação: chave composta (fonte, external_id)
Cada anúncio é identificado unicamente pela combinação `(fonte, external_id)`. O `external_id` é o ID na plataforma de origem (ex: ID do item na OLX). Para o escopo atual isso é suficiente — um hash composto por conteúdo poderá ser adicionado futuramente se necessário.

### Filtros configuráveis por arquivo YAML ou variáveis de ambiente
Os critérios de filtro (preço_maximo, bairros_permitidos, categorias_permitidas) ficam num arquivo de configuração separado, não hardcoded no código. Isso permite ajustar sem mexer no código-fonte.

### Biblioteca HTTP: `requests` (Python)
Leve, madura, suficiente para o caso de uso. Alternativa (`httpx`) considerada mas não necessária — não precisamos de async.

### Agendamento: cron
Simples, nativo do Linux, sem dependências extras. O script principal (`pipeline.py`) é invocado diretamente.

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    pipeline.py (orquestrador)            │
│                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │
│  │ scraper_olx  │   │ normalizador │   │ backend_cli │ │
│  │ .py          │──▶│ .py          │──▶│ ent.py      │ │
│  └──────┬───────┘   └──────┬───────┘   └──────┬──────┘ │
│         │                  │                   │        │
│         ▼                  ▼                   ▼        │
│  dados_crus.jsonl   dados_limpos.csv    POST /api/      │
│                                           imoveis      │
└─────────────────────────────────────────────────────────┘
         │
         ▼
  cron: executa pipeline.py toda semana
```

### Fluxo de dados

```
scraper_olx.py
  │
  ├── extrai links das páginas de listagem
  ├── acessa cada anúncio
  └── escreve dados_crus_{timestamp}.jsonl
        │
        ▼
normalizador.py
  │
  ├── lê dados_crus_*.jsonl
  ├── parseia campos _raw → tipados
  ├── extrai bairro/cidade do endereço
  ├── aplica filtros configurados
  └── escreve dados_limpos_{timestamp}.csv
        │
        ▼
backend_client.py
  │
  ├── lê dados_limpos_*.csv
  ├── envia payload ao backend via POST
  └── salva .failed se houver erro
```

### Schema intermediário (formato de entrada do normalizador)

```json
{
  "fonte": "olx",
  "external_id": "1234567890",
  "url": "https://www.olx.com.br/item/1234567890",
  "titulo": "Apto 2 quartos Centro",
  "preco_raw": "R$ 1.200",
  "tipo_anuncio_raw": "aluguel",
  "categoria_raw": "apartamento",
  "endereco_raw": "Rua X, Bairro Y, Campina Grande",
  "quartos_raw": "2 quartos",
  "banheiros_raw": "1 banheiro",
  "area_raw": "50 m²",
  "condominio_raw": "R$ 300",
  "iptu_raw": null,
  "vagas_raw": "1 vaga",
  "descricao_raw": "Apartamento bem localizado...",
  "data_coleta": "06/07/2026",
  "fotos": ["https://..."]
}
```

### Schema do CSV de saída

external_id, titulo, preco, tipo_anuncio, categoria, cidade, bairro, quartos, banheiros, area_m2, condominio, iptu, vagas, url, data_coleta, descricao, fonte

## Risks / Trade-offs

- **[Alta] Selenium é frágil** → Mudanças no layout da OLX podem quebrar o scraper. Mitigação: usar múltiplos seletores CSS (fallbacks) como já feito. Se a OLX tiver API, considerar migração futura.
- **[Média] Extração de bairro por heurística** → Endereços mal formatados podem resultar em bairro nulo. Mitigação: anúncios sem bairro são filtrados apenas se o filtro exigir — ficam visíveis se o critério for apenas preço.
- **[Baixa] Backend pode mudar de API** → O contrato com o backend deve ser acordado cedo. Mitigação: endpoint e formato do payload configuráveis.
- **[Média] Sem testes** → O próximo semestre exige qualidade para simulação de mercado. Mitigação: incluir testes nas tasks.
