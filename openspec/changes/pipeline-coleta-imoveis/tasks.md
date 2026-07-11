## 1. Limpeza e preparacao do scraper OLX

- [x] 1.1 Extrair logica do scraper para funcoes reutilizaveis (coletar_links, extrair_anuncio)
- [x] 1.2 Modificar extracao para gerar JSON Lines no schema intermediario (campos _raw + metadados)
- [x] 1.3 Adicionar campo `fonte: "olx"` e reconstruir `url` a partir do external_id
- [x] 1.4 Garantir que external_id seja extraido corretamente do `/item/ID` na URL
- [x] 1.5 Remover duplicatas intra-execucao por external_id

## 2. Normalizador de dados

- [x] 2.1 Implementar parser de precos (preco_raw, condominio_raw, iptu_raw → float)
- [x] 2.2 Implementar parser de caracteristicas (quartos_raw, banheiros_raw, vagas_raw → int; area_raw → float)
- [x] 2.3 Implementar extracao de bairro e cidade a partir de endereco_raw
- [x] 2.4 Integrar filtros: preco maximo, lista de bairros, categorias permitidas
- [x] 2.5 Gerar CSV de saida com cabecalho e dados normalizados

## 3. Integracao com backend

- [x] 3.1 Implementar cliente HTTP com requests.post para o endpoint configurado
- [x] 3.2 Suporte a configuracao via BACKEND_URL e BACKEND_TOKEN (ambiente ou .env)
- [x] 3.3 Tratamento de falhas: registrar erro e salvar payload nao enviado em arquivo .failed
- [x] 3.4 Acordar schema do payload com o time de backend

## 4. Orquestrador e automacao

- [x] 4.1 Criar pipeline.py que executa as 3 etapas em sequencia: scraper → normalizador → backend
- [x] 4.2 Adicionar logging com timestamp por etapa
- [x] 4.3 Configurar cron semanal para execucao automatica
- [x] 4.4 Documentar setup do cron e dependencias no README

## 5. Qualidade e validacao

- [x] 5.1 Testar pipeline completa com dados reais da OLX (Campina Grande, aluguel)
- [x] 5.2 Validar CSV gerado contra o schema definido
- [x] 5.3 Verificar que falha no backend nao interrompe o pipeline (dados salvos localmente)
