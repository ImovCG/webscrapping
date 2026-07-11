#!/usr/bin/env python3
import glob
import logging
import os
import sys
from datetime import date

os.makedirs('artifacts', exist_ok=True)

from scraper_olx import scraper_olx
from normalizador import normalizar
from backend_client import enviar_lote

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
    logger.info('=== INICIO DA COLETA ===')

    logger.info('Etapa 1/3: Scraper OLX')
    arquivo_cru = scraper_olx()
    if not arquivo_cru:
        logger.warning('Nenhum dado novo coletado. Encerrando.')
        return
    logger.info(f'Scraper concluido: {arquivo_cru}')

    logger.info('Etapa 2/3: Normalizacao')
    crus = sorted(glob.glob('artifacts/dados_crus_*.jsonl'))
    arquivo_limpo = normalizar(crus[-1])
    logger.info(f'Normalizacao concluida: {arquivo_limpo}')

    logger.info('Etapa 3/3: Envio ao backend')
    limpos = sorted(glob.glob('artifacts/dados_limpos_*.csv'))
    resultado = enviar_lote(limpos[-1])
    logger.info(f'Envio concluido: {resultado["enviados"]} enviados, {resultado["falhas"]} falhas')

    logger.info('=== COLETA FINALIZADA ===')


if __name__ == '__main__':
    pipeline()
