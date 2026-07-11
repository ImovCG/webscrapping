## Why

O projeto precisa de anúncios de imóveis acessíveis perto da universidade, coletados semanalmente. O scraper atual coleta dados crus da OLX, mas não há pipeline de normalização, exportação ou envio ao backend. Precisamos estruturar os dados de forma confiável e preparar a arquitetura para múltiplas fontes futuras (Facebook, Zap, etc).

## What Changes

- Reescrever o scraper da OLX para gerar JSON num schema cru padronizado (schema intermediário)
- Criar um normalizador único que parseia os campos crus (preços, endereços, características) em dados limpos e tipados
- Adicionar exportação para CSV com o schema definido
- Adicionar envio dos dados normalizados ao backend via requisição HTTP
- Preparar a arquitetura para múltiplas fontes: cada scraper gera JSON cru no mesmo formato, o normalizador é único

## Capabilities

### New Capabilities
- `scraper-olx`: Coleta anúncios da OLX e gera JSON cru no schema intermediário padronizado
- `normalizacao`: Pipeline única que transforma JSON cru de qualquer fonte em dados limpos, tipados e filtrados
- `integracao-backend`: Cliente HTTP que envia os dados normalizados para a API do backend
- `automacao-coleta`: Script de automação para execução semanal do pipeline completo (scraper → normalizador → backend)

### Modified Capabilities
*(Nenhuma — não há specs existentes)*

## Impact

- `scraper_olx.py` será reescrito com novo schema de saída
- `pipeline_coleta.py` (novo): orquestrador que encadeia as etapas
- `normalizador.py` (novo): parser e filtros dos dados
- `backend_client.py` (novo): requisições HTTP para o backend
- Dependências adicionadas: `requests` (para chamadas HTTP)
