## ADDED Requirements

### Requirement: Executar pipeline completo semanalmente
O sistema SHALL orquestrar a execução semanal completa: scraper → normalizador → envio ao backend.

#### Scenario: Execução completa
- **WHEN** o script de automação é invocado
- **THEN** ele executa o scraper da OLX
- **THEN** executa o normalizador sobre os dados gerados
- **THEN** envia os dados normalizados ao backend
- **THEN** registra o timestamp da coleta e o resumo (total de anúncios coletados, normalizados, enviados)

### Requirement: Agendamento via cron ou equivalente
O script SHALL ser agendável via cron (Linux) ou Task Scheduler (Windows) para rodar automaticamente toda semana.

#### Scenario: Agendamento via cron
- **WHEN** configurado no crontab
- **THEN** o pipeline executa automaticamente no dia/horário configurado

### Requirement: Logging e notificação de falhas
O sistema SHALL registrar logs da execução (início, fim, erros) em arquivo e exibir resumo no terminal.

#### Scenario: Registro de log
- **WHEN** o pipeline executa
- **THEN** um arquivo de log é gerado/com rotina de logs com timestamp, etapa e status
- **THEN** erros críticos são exibidos no terminal ao final da execução
