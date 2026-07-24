import csv
import json
import os
import re
from datetime import date
from typing import Optional

import yaml


def carregar_config(caminho: str = 'config.yaml') -> dict:
    with open(caminho, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)['filtros']


def parse_preco(valor: Optional[str]) -> Optional[float]:
    if not valor:
        return None
    v = valor.strip().lower()
    if 'a combinar' in v or 'não informado' in v or 'nao informado' in v \
            or 'grátis' in v or 'gratis' in v:
        return None

    numeros = re.sub(r'[^\d,.]', '', v)
    if not numeros:
        return None

    # Formato pt-BR: '.' e separador de milhar e ',' e decimal (ex: 1.200,00).
    if ',' in numeros:
        numeros = numeros.replace('.', '').replace(',', '.')
    else:
        # So pontos: se todos os grupos apos o primeiro tem 3 digitos, e milhar
        # (ex: 1.200 -> 1200, 1.200.000 -> 1200000).
        partes = numeros.split('.')
        if len(partes) > 1 and all(len(p) == 3 for p in partes[1:]):
            numeros = ''.join(partes)

    try:
        return float(numeros)
    except ValueError:
        return None


def parse_inteiro(valor: Optional[str]) -> Optional[int]:
    if not valor:
        return None
    numeros = re.search(r'(\d+)', valor)
    return int(numeros.group(1)) if numeros else None


def parse_area(valor: Optional[str]) -> Optional[float]:
    if not valor:
        return None
    numeros = re.search(r'([\d,.]+)', valor)
    if not numeros:
        return None
    num = numeros.group(1).replace(',', '.')
    try:
        return float(num)
    except ValueError:
        return None


def extrair_bairro_cidade(endereco_raw: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not endereco_raw:
        return None, None

    partes = re.split(r'[–\-—,|]', endereco_raw)
    partes = [p.strip() for p in partes if p.strip() and p.strip() not in ('PB',)]

    if len(partes) >= 3:
        bairro = partes[0]
        cidade = partes[1]
    elif len(partes) == 2:
        bairro = partes[0]
        cidade = partes[1]
    elif len(partes) == 1:
        bairro = partes[0]
        cidade = None
    else:
        bairro = None
        cidade = None

    return bairro, cidade


def aplicar_filtros(dados: dict, config: dict) -> bool:
    if config.get('remover_sem_preco', True) and dados.get('preco') is None:
        return False

    preco_max = config.get('preco_maximo')
    if preco_max and dados.get('preco') and dados['preco'] > preco_max:
        return False

    bairros = config.get('bairros_permitidos', [])
    if bairros and dados.get('bairro') and dados['bairro'] not in bairros:
        return False

    categorias = config.get('categorias_permitidas', [])
    if categorias and dados.get('categoria') and dados['categoria'] not in categorias:
        return False

    if config.get('remover_sem_bairro', False) and dados.get('bairro') is None:
        return False

    return True


def normalizar_anuncio(anuncio: dict) -> Optional[dict]:
    external_id = anuncio.get('external_id')
    if not external_id:
        return None

    bairro, cidade = extrair_bairro_cidade(anuncio.get('endereco_raw'))

    return {
        'external_id': external_id,
        'titulo': anuncio.get('titulo'),
        'preco': parse_preco(anuncio.get('preco_raw')),
        'tipo_anuncio': anuncio.get('tipo_anuncio_raw'),
        'categoria': anuncio.get('categoria_raw'),
        'cidade': cidade,
        'bairro': bairro,
        'quartos': parse_inteiro(anuncio.get('quartos_raw')),
        'banheiros': parse_inteiro(anuncio.get('banheiros_raw')),
        'area_m2': parse_area(anuncio.get('area_raw')),
        'condominio': parse_preco(anuncio.get('condominio_raw')),
        'iptu': parse_preco(anuncio.get('iptu_raw')),
        'vagas': parse_inteiro(anuncio.get('vagas_raw')),
        'url': anuncio.get('url'),
        'data_coleta': anuncio.get('data_coleta'),
        'descricao': anuncio.get('descricao_raw'),
        'fonte': anuncio.get('fonte'),
        'fotos': json.dumps(anuncio.get('fotos') or [], ensure_ascii=False),
    }


CABECALHO = [
    'external_id', 'titulo', 'preco', 'tipo_anuncio', 'categoria',
    'cidade', 'bairro', 'quartos', 'banheiros', 'area_m2',
    'condominio', 'iptu', 'vagas', 'url', 'data_coleta', 'descricao', 'fonte', 'fotos',
]


def normalizar_lista(anuncios: list[dict], config: Optional[dict] = None) -> list[dict]:
    """Normaliza e filtra uma lista de anuncios crus (em memoria)."""
    if config is None:
        config = carregar_config()

    normalizados = []
    for anuncio in anuncios:
        normalizado = normalizar_anuncio(anuncio)
        if not normalizado:
            continue
        if not aplicar_filtros(normalizado, config):
            continue
        normalizados.append(normalizado)
    return normalizados


def escrever_csv(normalizados: list[dict], arquivo_saida: str, incluir_cabecalho: bool = True) -> None:
    """Escreve/append uma lista de registros normalizados num CSV."""
    os.makedirs(os.path.dirname(arquivo_saida) or '.', exist_ok=True)
    modo = 'w' if incluir_cabecalho else 'a'
    with open(arquivo_saida, modo, newline='', encoding='utf-8') as csv_out:
        writer = csv.DictWriter(csv_out, fieldnames=CABECALHO, extrasaction='ignore')
        if incluir_cabecalho:
            writer.writeheader()
        for normalizado in normalizados:
            writer.writerow(normalizado)


def normalizar(arquivo_entrada: str, arquivo_saida: Optional[str] = None) -> str:
    config = carregar_config()

    if not arquivo_saida:
        timestamp = date.today().strftime('%Y%m%d')
        arquivo_saida = f'artifacts/dados_limpos_{timestamp}.csv'

    os.makedirs('artifacts', exist_ok=True)

    crus = []
    erro_count = 0
    with open(arquivo_entrada, 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                crus.append(json.loads(linha))
            except json.JSONDecodeError:
                erro_count += 1

    normalizados = normalizar_lista(crus, config)
    escrever_csv(normalizados, arquivo_saida)

    print(f'Normalizacao concluida:')
    print(f'  Registros normalizados: {len(normalizados)}')
    print(f'  Registros descartados:  {len(crus) - len(normalizados)}')
    print(f'  Linhas invalidas:       {erro_count}')
    print(f'Saida: {arquivo_saida}')

    return arquivo_saida


if __name__ == '__main__':
    import glob
    crus = sorted(glob.glob('artifacts/dados_crus_*.jsonl'))
    if not crus:
        print('Nenhum arquivo dados_crus_*.jsonl encontrado em artifacts/')
    else:
        normalizar(crus[-1])
