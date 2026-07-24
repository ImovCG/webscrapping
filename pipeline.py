#!/usr/bin/env python3
import logging
import os
import sys
from datetime import date

os.makedirs('artifacts', exist_ok=True)

from scraper_olx import scraper_olx
from scraper_facebook import scraper_facebook
from normalizador import normalizar_lista, escrever_csv, carregar_config
from backend_client import enviar_lote

BATCH_SIZE = int(os.getenv('BACKEND_BATCH_SIZE', '20'))
LOTE_STREAM_CSV = 'artifacts/_lote_stream.csv'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f'artifacts/pipeline_{date.today().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def pipeline():
    logger.info('=== INICIO DA COLETA (streaming em lotes de %d) ===', BATCH_SIZE)

    config = carregar_config()
    timestamp = date.today().strftime('%Y%m%d')
    csv_consolidado = f'artifacts/dados_limpos_{timestamp}.csv'
    estado = {'coletados': 0, 'enviados': 0, 'falhas': 0, 'primeira_escrita': True}

    def flush(anuncios_crus: list[dict]) -> None:
        """Normaliza, filtra e envia UM lote assim que ele e coletado."""
        estado['coletados'] += len(anuncios_crus)
        normalizados = normalizar_lista(anuncios_crus, config)
        if not normalizados:
            logger.info('Lote sem registros validos apos normalizacao/filtro.')
            return

        # Arquiva no CSV consolidado (cabecalho so na primeira vez) e envia so este lote.
        escrever_csv(normalizados, csv_consolidado, incluir_cabecalho=estado['primeira_escrita'])
        escrever_csv(normalizados, LOTE_STREAM_CSV, incluir_cabecalho=True)
        estado['primeira_escrita'] = False

        resultado = enviar_lote(LOTE_STREAM_CSV)
        estado['enviados'] += resultado['enviados']
        estado['falhas'] += resultado['falhas']
        logger.info('Lote: %d coletados -> %d validos -> %d enviados, %d falhas '
                    '(acumulado: %d enviados)',
                    len(anuncios_crus), len(normalizados),
                    resultado['enviados'], resultado['falhas'], estado['enviados'])

    logger.info('Etapa 1/2: Scraper OLX (coleta + envio em lotes)')
    scraper_olx(flush_callback=flush, batch_size=BATCH_SIZE)

    logger.info('Etapa 2/2: Scraper Facebook (coleta + envio em lotes)')
    scraper_facebook(flush_callback=flush, batch_size=BATCH_SIZE)

    if estado['coletados'] == 0:
        logger.warning('Nenhum dado novo coletado (OLX e Facebook).')

    logger.info('=== COLETA FINALIZADA: %d coletados, %d enviados, %d falhas ===',
                estado['coletados'], estado['enviados'], estado['falhas'])


if __name__ == '__main__':
    pipeline()
