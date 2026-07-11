import csv
import json
import os
import re
from datetime import date
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =============================================================================
# CONFIGURACAO
# =============================================================================
BASE_URL = 'https://www.olx.com.br/imoveis/aluguel/estado-pb/paraiba/campina-grande-guarabira-e-regiao'
FONTE = 'olx'
TIPO_ANUNCIO = 'aluguel'
MAX_PAGINAS = 10
PAGINA_INICIAL = 1
WAIT_TIMEOUT = 10
MAX_TENTATIVAS = 2
HEADER = 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'


def criar_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_argument(HEADER)
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=chrome_options)


def extrair_external_id(link: str) -> Optional[str]:
    match = re.search(r'(\d{7,})$', link)
    return match.group(1) if match else None


CATEGORIAS_CONHECIDAS = [
    'apartamento', 'casa', 'kitnet', 'kitnete', 'studio', 'loft',
    'sala', 'comercial', 'loja', 'galpao', 'galpão', 'deposito',
    'terreno', 'lote', 'fazenda', 'sítio', 'sitio', 'chácara', 'chacara',
    'predio', 'prédio', 'pousada', 'hotel',
]


def extrair_categoria(driver, jsonld: Optional[dict], link: str) -> Optional[str]:
    if jsonld:
        for chave in ('category', 'additionalType'):
            val = jsonld.get(chave) or jsonld.get('Object', {}).get(chave)
            if val and isinstance(val, str) and val.strip():
                return val.strip()

    try:
        breadcrumb = driver.find_elements(
            By.CSS_SELECTOR,
            'nav[aria-label*="breadcrumb" i] li, [data-testid="breadcrumb"] li, .breadcrumb li',
        )
        if breadcrumb and len(breadcrumb) >= 3:
            categoria_texto = breadcrumb[-1].text.strip()
            if categoria_texto:
                return categoria_texto
    except:
        pass

    slug = link.lower()
    for cat in CATEGORIAS_CONHECIDAS:
        if cat in slug:
            if cat in ('kitnete',):
                return 'kitnet'
            if cat in ('galpão',):
                return 'galpao'
            if cat in ('prédio',):
                return 'predio'
            if cat in ('sítio',):
                return 'sitio'
            if cat in ('chácara',):
                return 'chacara'
            return cat

    return None


def coletar_links() -> list[str]:
    pagina = PAGINA_INICIAL
    todos_links: set[str] = set()
    links_novos: list[str] = []

    os.makedirs('artifacts', exist_ok=True)

    if os.path.exists('artifacts/links_imovel.csv'):
        with open('artifacts/links_imovel.csv', 'r') as f:
            for linha in csv.reader(f):
                if linha:
                    todos_links.add(linha[0])

    while pagina <= MAX_PAGINAS:
        url = f'{BASE_URL}?o={pagina}'
        print(f'Acessando pagina {pagina}... ({url})')
        driver = criar_driver()
        driver.set_page_load_timeout(30)
        try:
            driver.get(url=url)
        except TimeoutException:
            print(f'Timeout ao carregar pagina {pagina}. Pulando...')
            driver.quit()
            pagina += 1
            continue

        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, 'a'))
            )
        except TimeoutException:
            print(f'Pagina {pagina} nao carregou a tempo. Pulando...')
            driver.quit()
            pagina += 1
            continue

        all_a = driver.find_elements(By.TAG_NAME, 'a')
        cards = []
        for a in all_a:
            href = a.get_attribute('href')
            if href and 'pb.olx.com.br/paraiba/imoveis/' in href:
                cards.append(a)

        encontrados = 0
        for card in cards:
            try:
                link = card.get_attribute('href')
                if link and link not in todos_links:
                    with open('artifacts/links_imovel.csv', 'a', newline='') as f:
                        csv.writer(f).writerow([link])
                    todos_links.add(link)
                    links_novos.append(link)
                    encontrados += 1
            except:
                continue

        print(f'Encontrados {encontrados} links na pagina {pagina}.')
        driver.quit()

        if encontrados == 0:
            print('Fim das paginas.')
            break
        pagina += 1

    print(f'Foram encontrados: {len(links_novos)} imoveis novos.')
    print(f'Total de links: {len(todos_links)}')
    return links_novos


def extrair_texto_primeiro(driver, *seletores: str) -> Optional[str]:
    for sel in seletores:
        try:
            return driver.find_element(By.CSS_SELECTOR, sel).text
        except:
            continue
    return None


def extrair_jsonld(driver) -> Optional[dict]:
    try:
        for s in driver.find_elements(By.TAG_NAME, 'script'):
            if 'application/ld+json' in (s.get_attribute('type') or ''):
                return json.loads(s.get_attribute('innerHTML') or '{}')
    except:
        pass
    return None


def extrair_valor_por_rotulo(driver, rotulo: str) -> Optional[str]:
    try:
        valor = driver.find_element(
            By.XPATH,
            f'//span[contains(text(), "{rotulo}")]/parent::div/following-sibling::span[1]'
        ).text
        return valor if valor.strip() else None
    except:
        return None


def formatar_preco_jsonld(price_str: str) -> Optional[str]:
    try:
        valor = float(price_str)
        return f'R$ {valor:,.0f}'.replace(',', '.')
    except (ValueError, TypeError):
        return None


def extrair_anuncio(driver: webdriver.Chrome, link: str) -> Optional[dict]:
    external_id = extrair_external_id(link)
    if not external_id:
        print(f'Link sem external_id: {link}. Pulando...')
        return None

    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                'h1, [data-testid="ad-title"], .typo-title-medium',
            ))
        )
    except TimeoutException:
        print(f'Pagina do anuncio nao carregou a tempo: {link}. Pulando...')
        return None

    jsonld = extrair_jsonld(driver)
    categoria = extrair_categoria(driver, jsonld, link)

    preco_raw = None
    try:
        for el in driver.find_elements(By.CSS_SELECTOR, '.typo-body-small.text-neutral-110'):
            text = (el.text or '').strip()
            if text.startswith('R$') and len(text) > 4:
                preco_raw = text
                break
    except:
        pass

    if not preco_raw and jsonld:
        price = jsonld.get('priceSpecification', {}).get('price') or jsonld.get('offers', {}).get('price')
        if price:
            preco_raw = formatar_preco_jsonld(price)

    if not preco_raw:
        preco_raw = extrair_texto_primeiro(driver, '.typo-body-small.text-neutral-110')

    condominio_raw = extrair_valor_por_rotulo(driver, 'Condomínio')
    iptu_raw = extrair_valor_por_rotulo(driver, 'IPTU')

    endereco_raw = extrair_texto_primeiro(
        driver,
        '.typo-body-small.font-semibold.text-neutral-110',
        '.typo-body-small.text-neutral-120.font-regular',
    )

    if jsonld and jsonld.get('Object', {}).get('description'):
        descricao_raw = jsonld['Object']['description']
    else:
        descricao_raw = extrair_texto_primeiro(
            driver,
            'div[data-section="description"] span.typo-body-medium',
            '.typo-body-medium',
        )

    if jsonld and jsonld.get('Object', {}).get('name'):
        titulo = jsonld['Object']['name']
    else:
        titulo = extrair_texto_primeiro(
            driver,
            'h1.typo-title-medium',
            'h1',
        )

    quartos_raw = None
    banheiros_raw = None
    area_raw = None
    vagas_raw = None

    try:
        amenidades = driver.find_elements(By.CSS_SELECTOR, '.text-secondary.typo-body-medium.font-regular')
        for el in amenidades:
            texto = el.text.lower()
            if 'quarto' in texto or 'dormit' in texto:
                quartos_raw = el.text
            elif 'banheiro' in texto or 'wc' in texto or 'suite' in texto:
                banheiros_raw = el.text
            elif 'vaga' in texto or 'garagem' in texto:
                vagas_raw = el.text
    except:
        pass

    fotos = []
    try:
        fotos_elem = driver.find_elements(
            By.CSS_SELECTOR,
            'img[src*="olx"]'
        )
        vistos = set()
        for f in fotos_elem:
            src = f.get_attribute('src')
            if src and src not in vistos and 'olx' in src:
                vistos.add(src)
                fotos.append(src)
    except:
        pass

    return {
        'fonte': FONTE,
        'external_id': external_id,
        'url': link,
        'titulo': titulo,
        'preco_raw': preco_raw,
        'tipo_anuncio_raw': TIPO_ANUNCIO,
        'categoria_raw': categoria,
        'endereco_raw': endereco_raw,
        'quartos_raw': quartos_raw,
        'banheiros_raw': banheiros_raw,
        'area_raw': area_raw,
        'condominio_raw': condominio_raw,
        'iptu_raw': iptu_raw,
        'vagas_raw': vagas_raw,
        'descricao_raw': descricao_raw,
        'data_coleta': date.today().strftime('%d/%m/%Y'),
        'fotos': fotos,
    }


def scraper_olx() -> str:
    links = coletar_links()
    if not links:
        print('Nenhum link novo encontrado.')
        return ''

    os.makedirs('artifacts', exist_ok=True)
    timestamp = date.today().strftime('%Y%m%d')
    output_file = f'artifacts/dados_crus_{timestamp}.jsonl'

    imoveis_existentes: set[str] = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for linha in f:
                if linha.strip():
                    try:
                        dado = json.loads(linha)
                        if dado.get('external_id'):
                            imoveis_existentes.add(dado['external_id'])
                    except:
                        continue

    with open(output_file, 'a', encoding='utf-8') as out:
        total = len(links)
        for i, link in enumerate(links, start=1):
            print(f'Processando {i}/{total}: {link}')

            anuncio = None
            for tentativa in range(1, MAX_TENTATIVAS + 1):
                driver = criar_driver()
                driver.set_page_load_timeout(30)
                try:
                    driver.get(url=link)
                except TimeoutException:
                    print(f'  Timeout ao carregar {link} (tentativa {tentativa}/{MAX_TENTATIVAS})')
                    driver.quit()
                    if tentativa == MAX_TENTATIVAS:
                        print(f'  Desistindo de {link} apos {MAX_TENTATIVAS} tentativas.')
                    continue

                try:
                    anuncio = extrair_anuncio(driver, link)
                except Exception as e:
                    print(f'  Erro ao extrair {link}: {e}')
                    anuncio = None
                finally:
                    driver.quit()

                if anuncio is not None:
                    break

            if not anuncio:
                continue

            if anuncio['external_id'] in imoveis_existentes:
                print(f'  Duplicata ignorada: {anuncio["external_id"]}')
                continue

            out.write(json.dumps(anuncio, ensure_ascii=False) + '\n')
            imoveis_existentes.add(anuncio['external_id'])
            print(f'  OK: {anuncio["titulo"]} - {anuncio["preco_raw"]}')

    print(f'Dados exportados para {output_file}')
    return output_file


if __name__ == '__main__':
    scraper_olx()
