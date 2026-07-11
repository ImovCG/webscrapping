## ADDED Requirements

### Requirement: Parsear campos de preço
O normalizador SHALL converter strings de preço (`preco_raw`, `condominio_raw`, `iptu_raw`) para valores numéricos (float), lidando com formatos como "R$ 1.200", "R$1.200,00", "a combinar", "Não informado", etc.

#### Scenario: Preço válido
- **WHEN** preco_raw = "R$ 1.200"
- **THEN** preco_normalizado = 1200.0

#### Scenario: Preço ausente ou inválido
- **WHEN** preco_raw = null ou "a combinar"
- **THEN** preco_normalizado = null

### Requirement: Parsear características do imóvel
O normalizador SHALL converter strings de características (`quartos_raw`, `banheiros_raw`, `area_raw`, `vagas_raw`) para valores numéricos.

#### Scenario: Característica numérica
- **WHEN** quartos_raw = "2 quartos" ou "2 dormitórios"
- **THEN** quartos_normalizado = 2

#### Scenario: Área
- **WHEN** area_raw = "50 m²"
- **THEN** area_m2_normalizado = 50.0

### Requirement: Extrair bairro e cidade do endereço
O normalizador SHALL extrair bairro e cidade a partir do campo `endereco_raw`, usando heurísticas baseadas em separadores comuns (",", "-", " — ") e lista de bairros conhecidos de Campina Grande.

#### Scenario: Endereço estruturado
- **WHEN** endereco_raw = "Rua João XXIII, Centro, Campina Grande"
- **THEN** bairro_normalizado = "Centro", cidade_normalizado = "Campina Grande"

#### Scenario: Endereço não parseável
- **WHEN** endereco_raw = null ou não contém separadores reconhecíveis
- **THEN** bairro_normalizado = null, cidade_normalizado = null

### Requirement: Filtrar anúncios por relevância
O normalizador SHALL aplicar filtros configuráveis: faixa de preço máxima, lista de bairros de interesse, categorias permitidas (apartamento, casa, kitnet), e remover anúncios com dados críticos ausentes (sem preço, sem external_id).

#### Scenario: Filtro de preço
- **WHEN** preco_normalizado > PRECO_MAXIMO configurado
- **THEN** o anúncio é removido do dataset final

#### Scenario: Filtro de bairro
- **WHEN** bairro_normalizado não está na lista de bairros configurada
- **THEN** o anúncio é filtrado

#### Scenario: Anúncio sem preço
- **WHEN** preco_normalizado = null
- **THEN** o anúncio é removido

### Requirement: Exportar CSV limpo
O normalizador SHALL gerar um arquivo CSV com os dados normalizados e filtrados, no schema: external_id, titulo, preco, tipo_anuncio, categoria, cidade, bairro, quartos, banheiros, area_m2, condominio, iptu, vagas, url, data_coleta, descricao, fonte.

#### Scenario: Geração de CSV
- **WHEN** o normalizador finaliza o processamento
- **THEN** um CSV é escrito com cabeçalho e uma linha por anúncio filtrado
- **THEN** campos numéricos são formatados sem separador de milhar
