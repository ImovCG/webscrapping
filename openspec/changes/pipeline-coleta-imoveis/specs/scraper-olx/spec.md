## ADDED Requirements

### Requirement: Coletar links de anúncios da OLX
O scraper SHALL navegar pelas páginas de listagem da OLX e coletar URLs individuais de cada anúncio na região configurada (Campina Grande, Guarabira e região — aluguel).

#### Scenario: Navegação por páginas
- **WHEN** o scraper acessa a URL base com paginação (?o=N)
- **THEN** ele extrai todos os links de anúncios da página atual
- **THEN** ele avança para a próxima página até o limite configurado ou até não encontrar mais anúncios

### Requirement: Extrair dados crus de cada anúncio
O scraper SHALL acessar cada URL de anúncio e extrair os campos no schema intermediário, mantendo valores em texto puro (raw) sem parse ou limpeza.

#### Scenario: Extração completa
- **WHEN** o scraper acessa uma página de anúncio
- **THEN** ele extrai: external_id (do /item/ID na URL), titulo, preco_raw, tipo_anuncio_raw, categoria_raw, endereco_raw, quartos_raw, banheiros_raw, area_raw, condominio_raw, iptu_raw, vagas_raw, descricao_raw, url, data_coleta, fotos

#### Scenario: Campo ausente
- **WHEN** um campo não é encontrado na página
- **THEN** o scraper salva o campo como null, sem interromper a extração

### Requirement: Gerar saída no schema intermediário padronizado
O scraper SHALL gerar um arquivo JSON Lines (`.jsonl`) onde cada linha é um objeto JSON no schema intermediário, independente da fonte.

#### Scenario: Formato de saída
- **WHEN** o scraper finaliza a coleta
- **THEN** um arquivo .jsonl é gerado com uma linha por anúncio
- **THEN** cada linha contém o campo `fonte` com valor "olx"

### Requirement: Evitar re-coleta de anúncios já processados
O scraper SHALL manter um registro dos external_id já coletados para não processar o mesmo anúncio múltiplas vezes na mesma execução.

#### Scenario: Deduplicação intra-execucão
- **WHEN** o scraper encontra um external_id já visitado nesta execução
- **THEN** ele pula o anúncio sem re-extrair os dados
