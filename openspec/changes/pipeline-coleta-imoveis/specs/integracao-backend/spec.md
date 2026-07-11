## ADDED Requirements

### Requirement: Enviar dados ao backend
O sistema SHALL enviar os anúncios normalizados para o backend via requisição HTTP, em lotes ou individualmente, conforme a interface definida pelo backend.

#### Scenario: Envio de lote
- **WHEN** o pipeline completa a normalização
- **THEN** os dados limpos são enviados ao endpoint configurado via POST
- **THEN** o sistema aguarda a resposta de confirmação do backend

#### Scenario: Falha na requisição
- **WHEN** o backend retorna erro (timeout, 5xx, conexão recusada)
- **THEN** o sistema registra o erro e salva os dados não enviados localmente para retentativa

### Requirement: Configurar endpoint e autenticação
O cliente HTTP SHALL ser configurável via variáveis de ambiente ou arquivo de configuração: URL do backend, token de autenticação (se necessário), timeout.

#### Scenario: Configuração por ambiente
- **WHEN** as variáveis BACKEND_URL e BACKEND_TOKEN estão definidas
- **THEN** o cliente usa esses valores para as requisições
