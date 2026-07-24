#!/usr/bin/env python3
"""Helper de login manual do Facebook.

Rode UMA VEZ na sua maquina (com navegador/tela) para gerar o arquivo de
cookies que o scraper_facebook reusa. O login e feito manualmente por voce
nesta janela do Chrome; nenhuma senha e digitada de forma automatizada.

Uso:
    python salvar_cookies.py

Depois copie o arquivo gerado (artifacts/fb_cookies.json) para a VM onde o
container roda (veja README).
"""
import json
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

FB_LOGIN_URL = 'https://www.facebook.com/'
COOKIES_PATH = os.getenv('FB_COOKIES_PATH', 'artifacts/fb_cookies.json')


def criar_driver_visivel() -> webdriver.Chrome:
    """Cria um Chrome NAO-headless para o login manual."""
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    chrome_bin = os.getenv('CHROME_BIN')
    if chrome_bin:
        chrome_options.binary_location = chrome_bin

    chromedriver_bin = os.getenv('CHROMEDRIVER_BIN')
    if chromedriver_bin:
        return webdriver.Chrome(options=chrome_options, service=Service(chromedriver_bin))

    return webdriver.Chrome(options=chrome_options)


def salvar_cookies() -> str:
    os.makedirs(os.path.dirname(COOKIES_PATH) or '.', exist_ok=True)

    driver = criar_driver_visivel()
    try:
        driver.get(FB_LOGIN_URL)
        print('=' * 70)
        print('1. Faca login na janela do Chrome que abriu.')
        print('2. Entre no grupo alvo (recomendado) e confirme que o feed carrega.')
        print('3. Volte aqui e aperte ENTER para salvar os cookies.')
        print('=' * 70)
        input('Pressione ENTER apos concluir o login... ')

        cookies = driver.get_cookies()
        if not any(c.get('name') == 'c_user' for c in cookies):
            print('AVISO: cookie de sessao (c_user) nao encontrado. '
                  'Voce esta realmente logado? Salvando mesmo assim.')

        with open(COOKIES_PATH, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        print(f'Cookies salvos em {COOKIES_PATH} ({len(cookies)} cookies).')
        return COOKIES_PATH
    finally:
        driver.quit()


if __name__ == '__main__':
    salvar_cookies()
