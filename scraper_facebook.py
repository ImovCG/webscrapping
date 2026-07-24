import csv
import json
import os
import re
import time
from datetime import date
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scraper_olx import criar_driver, CATEGORIAS_CONHECIDAS

# =============================================================================
# CONFIGURACAO
# =============================================================================
GROUP_ID = os.getenv('FB_GROUP_ID', '504632767134665')
BASE_URL = f'https://www.facebook.com/groups/{GROUP_ID}?locale=pt_BR'
FONTE = 'facebook'
TIPO_ANUNCIO = 'aluguel'
COOKIES_PATH = os.getenv('FB_COOKIES_PATH', 'artifacts/fb_cookies.json')
MAX_SCROLLS = int(os.getenv('FB_MAX_SCROLLS', '15'))
SCROLL_PAUSA = float(os.getenv('FB_SCROLL_PAUSA', '3'))
SCROLLS_SEM_NOVO_MAX = 3
WAIT_TIMEOUT = 15

# Termos que caracterizam um imovel (requisito duro para ser anuncio).
# Reusa as categorias conhecidas da OLX + alguns termos comuns em texto livre.
TIPOS_IMOVEL = set(CATEGORIAS_CONHECIDAS) | {
    'quarto', 'quartos', 'apto', 'apt', 'ap', 'flat', 'quitinete', 'quarto e sala',
}

# Sinais de que o post e uma BUSCA (procura), nao um anuncio.
PADROES_PROCURO = [
    'procuro', 'procura-se', 'estou procurando', 'to procurando', 'tô procurando',
    'preciso de', 'preciso alugar', 'alguem tem', 'alguém tem', 'quem tem',
    'quem tiver', 'alguma casa para alugar', 'alguma casa pra alugar',
    'algum apartamento para alugar', 'algum apartamento pra alugar',
    'alguem sabe', 'alguém sabe', 'ando procurando',
]

# Sinais de oferta (aumentam a confianca, nao obrigatorios).
PADROES_OFERTA = [
    'alugo', 'aluga-se', 'aluga se', 'aluga-se', 'disponivel', 'disponível',
    'para alugar', 'pra alugar', 'r$', 'aluguel:', 'valor:', 'oportunidade',
]

# Bairros conhecidos de Campina Grande (best-effort para extrair endereco).
BAIRROS_CG = [
    'Catolé', 'Catole', 'Bodocongó', 'Bodocongo', 'Centenário', 'Centenario',
    'Liberdade', 'Prata', 'Centro', 'Palmeira', 'Malvinas', 'Cruzeiro',
    'Jardim Paulistano', 'Jardim Quarenta', 'Itararé', 'Itarare', 'Mirante',
    'Alto Branco', 'Sandra Cavalcante', 'Tambor', 'Universitário', 'Universitario',
    'Ligeiro', 'Santo Antônio', 'Santo Antonio', 'José Pinheiro', 'Jose Pinheiro',
    'Monte Santo', 'Bela Vista', 'Dinamérica', 'Dinamerica', 'Acácio Figueiredo',
    'Acacio Figueiredo', 'Catingueira', 'Novo Bodocongó', 'Novo Bodocongo',
    'Pedregal', 'Presidente Médici', 'Presidente Medici', 'Distrito Industrial',
]


# =============================================================================
# AUTENTICACAO
# =============================================================================
def carregar_cookies(driver: webdriver.Chrome) -> None:
    with open(COOKIES_PATH, 'r', encoding='utf-8') as f:
        cookies = json.load(f)

    driver.get('https://www.facebook.com/')
    for cookie in cookies:
        # add_cookie nao aceita alguns campos que o get_cookies retorna.
        cookie.pop('sameSite', None)
        if 'expiry' in cookie and cookie['expiry'] is not None:
            cookie['expiry'] = int(cookie['expiry'])
        try:
            driver.add_cookie(cookie)
        except WebDriverException:
            continue


def esta_logado(driver: webdriver.Chrome) -> bool:
    """Detecta se a sessao caiu na tela/modal de login."""
    try:
        if driver.find_elements(By.CSS_SELECTOR, 'input[name="pass"], input[type="password"]'):
            return False
    except WebDriverException:
        pass
    return True


def criar_driver_autenticado() -> Optional[webdriver.Chrome]:
    if not os.path.exists(COOKIES_PATH):
        print(f'Arquivo de cookies nao encontrado em {COOKIES_PATH}. '
              f'Rode salvar_cookies.py primeiro. Pulando Facebook.')
        return None

    driver = criar_driver()
    carregar_cookies(driver)

    driver.set_page_load_timeout(60)
    try:
        driver.get(BASE_URL)
    except TimeoutException:
        print('Timeout ao carregar o grupo. Pulando Facebook.')
        driver.quit()
        return None

    if not esta_logado(driver):
        print('Sessao do Facebook invalida/expirada (caiu na tela de login). '
              'Regenere os cookies com salvar_cookies.py. Pulando Facebook.')
        driver.quit()
        return None

    return driver


# =============================================================================
# CLASSIFICACAO / EXTRACAO DE TEXTO LIVRE
# =============================================================================
def eh_anuncio(texto: Optional[str]) -> bool:
    """True somente se o post oferece um imovel (casa/apto/kitnet/...).

    Requisito duro: precisa mencionar um tipo de imovel E nao ser uma busca.
    """
    if not texto:
        return False
    t = texto.lower()

    tem_imovel = any(re.search(rf'\b{re.escape(tipo)}\b', t) for tipo in TIPOS_IMOVEL)
    if not tem_imovel:
        return False

    if any(padrao in t for padrao in PADROES_PROCURO):
        return False

    return True


def inferir_categoria(texto: Optional[str]) -> Optional[str]:
    if not texto:
        return None
    t = texto.lower()
    mapeamento = {
        'kitnete': 'kitnet', 'quitinete': 'kitnet', 'kitnet': 'kitnet',
        'apartamento': 'apartamento', 'apto': 'apartamento', 'flat': 'apartamento',
        'casa': 'casa', 'studio': 'studio', 'loft': 'loft', 'quarto': 'quarto',
    }
    for termo, categoria in mapeamento.items():
        if re.search(rf'\b{re.escape(termo)}\b', t):
            return categoria
    return None


def extrair_por_regex(texto: Optional[str], padrao: str) -> Optional[str]:
    if not texto:
        return None
    match = re.search(padrao, texto, re.IGNORECASE)
    return match.group(0).strip() if match else None


def extrair_endereco(texto: Optional[str]) -> Optional[str]:
    if not texto:
        return None
    for bairro in BAIRROS_CG:
        if re.search(rf'\b{re.escape(bairro)}\b', texto, re.IGNORECASE):
            return bairro
    return None


def extrair_post_id(permalink: Optional[str]) -> Optional[str]:
    if not permalink:
        return None
    for padrao in (
        r'/posts/(\d+)',
        r'/permalink/(\d+)',
        r'multi_permalinks=(\d+)',
        r'story_fbid=(\d+)',
        r'/groups/\d+/(\d+)',
    ):
        match = re.search(padrao, permalink)
        if match:
            return match.group(1)
    return None


# =============================================================================
# EXTRACAO DO DOM
# =============================================================================
def expandir_ver_mais(article) -> None:
    try:
        botoes = article.find_elements(
            By.XPATH,
            './/div[@role="button"][contains(text(), "Ver mais") or contains(text(), "See more")]',
        )
        for botao in botoes:
            try:
                botao.click()
                time.sleep(0.3)
            except WebDriverException:
                continue
    except WebDriverException:
        pass


def extrair_permalink(article) -> Optional[str]:
    try:
        for a in article.find_elements(By.CSS_SELECTOR, 'a[href]'):
            href = a.get_attribute('href') or ''
            if any(p in href for p in ('/posts/', '/permalink/', 'story_fbid', 'multi_permalinks')):
                return href.split('?')[0] if '/posts/' in href or '/permalink/' in href else href
    except WebDriverException:
        pass
    return None


def extrair_autor(article) -> Optional[str]:
    for seletor in ('h2 a', 'h3 a', 'h2 strong', 'strong a'):
        try:
            el = article.find_element(By.CSS_SELECTOR, seletor)
            texto = (el.text or '').strip()
            if texto:
                return texto
        except WebDriverException:
            continue
    return None


def extrair_texto(article) -> Optional[str]:
    for seletor in (
        'div[data-ad-comet-preview="message"]',
        'div[data-ad-preview="message"]',
        'div[data-testid="post_message"]',
    ):
        try:
            el = article.find_element(By.CSS_SELECTOR, seletor)
            texto = (el.text or '').strip()
            if texto:
                return texto
        except WebDriverException:
            continue

    # Fallback: maior bloco dir="auto" do article.
    try:
        blocos = article.find_elements(By.CSS_SELECTOR, 'div[dir="auto"]')
        textos = [(b.text or '').strip() for b in blocos]
        textos = [t for t in textos if t]
        if textos:
            return max(textos, key=len)
    except WebDriverException:
        pass
    return None


def montar_anuncio(article) -> Optional[dict]:
    expandir_ver_mais(article)

    texto = extrair_texto(article)
    if not eh_anuncio(texto):
        return None

    permalink = extrair_permalink(article)
    external_id = extrair_post_id(permalink)
    if not external_id:
        return None

    titulo = texto.split('\n', 1)[0][:120] if texto else None

    return {
        'fonte': FONTE,
        'external_id': external_id,
        'url': permalink,
        'autor': extrair_autor(article),
        'titulo': titulo,
        'preco_raw': extrair_por_regex(texto, r'R\$\s?[\d.,]+'),
        'tipo_anuncio_raw': TIPO_ANUNCIO,
        'categoria_raw': inferir_categoria(texto),
        'endereco_raw': extrair_endereco(texto),
        'quartos_raw': extrair_por_regex(texto, r'\d+\s*(?:quartos?|qto?s?|dormit\w*)'),
        'banheiros_raw': extrair_por_regex(texto, r'\d+\s*(?:banheiros?|wc|su[ií]tes?)'),
        'area_raw': extrair_por_regex(texto, r'\d+[.,]?\d*\s*m[²2]'),
        'condominio_raw': extrair_por_regex(texto, r'condom[ií]nio[:\s]*R?\$?\s?[\d.,]+'),
        'iptu_raw': extrair_por_regex(texto, r'iptu[:\s]*R?\$?\s?[\d.,]+'),
        'vagas_raw': extrair_por_regex(texto, r'\d+\s*(?:vagas?|garagens?)'),
        'descricao_raw': texto,
        'data_coleta': date.today().strftime('%d/%m/%Y'),
        # Fotos do FB nao sao coletadas: URLs do scontent sao longas (estouram a
        # coluna do backend) e expiram. O frontend usa uma imagem ilustrativa.
        'fotos': [],
    }


# =============================================================================
# COLETA
# =============================================================================
def coletar_posts(driver: webdriver.Chrome, ja_coletados: set[str]) -> list[dict]:
    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="article"]'))
        )
    except TimeoutException:
        print('Nenhum post carregou no feed do grupo.')
        return []

    anuncios: list[dict] = []
    vistos_execucao: set[str] = set()
    scrolls_sem_novo = 0

    for scroll in range(1, MAX_SCROLLS + 1):
        articles = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
        novos_neste_scroll = 0

        for article in articles:
            try:
                anuncio = montar_anuncio(article)
            except WebDriverException:
                continue
            if not anuncio:
                continue

            ext_id = anuncio['external_id']
            if ext_id in vistos_execucao or ext_id in ja_coletados:
                continue

            vistos_execucao.add(ext_id)
            anuncios.append(anuncio)
            novos_neste_scroll += 1
            print(f'  Anuncio: {anuncio["titulo"]} - {anuncio["preco_raw"]}')

        print(f'Scroll {scroll}/{MAX_SCROLLS}: {novos_neste_scroll} anuncios novos '
              f'({len(anuncios)} no total).')

        if novos_neste_scroll == 0:
            scrolls_sem_novo += 1
            if scrolls_sem_novo >= SCROLLS_SEM_NOVO_MAX:
                print('Sem posts novos por varios scrolls. Encerrando.')
                break
        else:
            scrolls_sem_novo = 0

        driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
        time.sleep(SCROLL_PAUSA)

    return anuncios


def scraper_facebook(flush_callback=None, batch_size: int = 20) -> str:
    os.makedirs('artifacts', exist_ok=True)

    timestamp = date.today().strftime('%Y%m%d')
    output_file = f'artifacts/dados_crus_{timestamp}.jsonl'
    coletados_csv = 'artifacts/fb_posts_coletados.csv'

    ja_coletados: set[str] = set()
    if os.path.exists(coletados_csv):
        with open(coletados_csv, 'r', encoding='utf-8') as f:
            for linha in csv.reader(f):
                if linha:
                    ja_coletados.add(linha[0])

    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for linha in f:
                if linha.strip():
                    try:
                        dado = json.loads(linha)
                        if dado.get('fonte') == FONTE and dado.get('external_id'):
                            ja_coletados.add(dado['external_id'])
                    except json.JSONDecodeError:
                        continue

    driver = criar_driver_autenticado()
    if driver is None:
        return ''

    try:
        anuncios = coletar_posts(driver, ja_coletados)
    finally:
        driver.quit()

    if not anuncios:
        print('Nenhum anuncio novo coletado no Facebook.')
        return ''

    buffer: list[dict] = []
    with open(output_file, 'a', encoding='utf-8') as out, \
            open(coletados_csv, 'a', newline='', encoding='utf-8') as csv_out:
        writer = csv.writer(csv_out)
        for anuncio in anuncios:
            out.write(json.dumps(anuncio, ensure_ascii=False) + '\n')
            writer.writerow([anuncio['external_id']])

            if flush_callback is not None:
                buffer.append(anuncio)
                if len(buffer) >= batch_size:
                    out.flush()
                    csv_out.flush()
                    flush_callback(buffer)
                    buffer = []

    if flush_callback is not None and buffer:
        flush_callback(buffer)

    print(f'Coletados {len(anuncios)} anuncios do Facebook em {output_file}')
    return output_file


if __name__ == '__main__':
    scraper_facebook()
