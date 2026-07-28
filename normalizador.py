import csv
import html
import json
import os
import re
import unicodedata
from datetime import date
from typing import Optional

import yaml

from bairros_campina_grande import bairro_por_token, encontrar_bairro_no_texto


CIDADES_BLOQUEADAS_PADRAO = [
    'Bananeiras',
    'Guarabira',
    'João Pessoa',
    'Patos',
    'Lagoa Seca',
    'Esperança',
    'Solânea',
]

TERMOS_BLOQUEADOS_PADRAO = [
    'moto',
    'start 160',
    'honda',
    'yamaha',
]


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


def normalizar_texto(valor: Optional[str]) -> str:
    if not valor:
        return ''
    texto = unicodedata.normalize('NFD', valor)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', texto).strip().lower()


def texto_anuncio(dados: dict) -> str:
    campos = [
        dados.get('titulo'),
        dados.get('descricao'),
        dados.get('categoria'),
        dados.get('endereco'),
        dados.get('bairro'),
        dados.get('cidade'),
    ]
    return ' '.join(c for c in campos if c)


def contem_termo(texto: str, termos: list[str]) -> bool:
    texto_norm = normalizar_texto(texto)
    for termo in termos:
        termo_norm = normalizar_texto(termo)
        if termo_norm and re.search(rf'\b{re.escape(termo_norm)}\b', texto_norm):
            return True
    return False


def cidade_bloqueada_no_texto(texto: Optional[str], cidades_bloqueadas: Optional[list[str]] = None) -> Optional[str]:
    cidades = cidades_bloqueadas or CIDADES_BLOQUEADAS_PADRAO
    texto_norm = normalizar_texto(texto)
    if not texto_norm:
        return None
    for cidade in cidades:
        cidade_norm = normalizar_texto(cidade)
        if re.search(rf'\b{re.escape(cidade_norm)}\b', texto_norm):
            return cidade
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


def limpar_descricao(valor: Optional[str]) -> Optional[str]:
    if not valor:
        return None

    texto = html.unescape(valor)
    texto = re.sub(r'<\s*br\s*/?\s*>', '\n', texto, flags=re.I)
    texto = re.sub(r'</\s*(p|div|li|ul|ol)\s*>', '\n\n', texto, flags=re.I)
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = texto.replace('\r\n', '\n').replace('\r', '\n').replace('\xa0', ' ')
    texto = re.sub(r'[ \t]+', ' ', texto)
    texto = re.sub(r'(?m)^[ \t]*\?[ \t]+', '', texto)
    texto = '\n'.join(linha.strip() for linha in texto.split('\n'))
    texto = re.sub(r'\n{3,}', '\n\n', texto).strip()

    return texto or None


def extrair_cep(texto: Optional[str]) -> Optional[str]:
    if not texto:
        return None
    match = re.search(r'\b(\d{5})-?(\d{3})\b', texto)
    return ''.join(match.groups()) if match else None


def extrair_endereco(
    endereco_raw: Optional[str],
    titulo: Optional[str] = None,
    descricao: Optional[str] = None,
) -> dict:
    texto_completo = f'{endereco_raw or ""} {titulo or ""} {descricao or ""}'
    cidade_bloqueada = cidade_bloqueada_no_texto(texto_completo)
    cep = extrair_cep(endereco_raw)
    estado = 'PB' if endereco_raw and re.search(r'\bPB\b|para[ií]ba', endereco_raw, re.I) else 'PB'

    if not endereco_raw:
        bairro = encontrar_bairro_no_texto(f'{titulo or ""} {descricao or ""}')
        cidade = None if cidade_bloqueada else ('Campina Grande' if bairro else None)
        endereco = ', '.join(p for p in [bairro, cidade, estado] if p) if bairro else None
        return {
            'endereco': endereco,
            'bairro': bairro,
            'cidade': cidade,
            'estado': estado,
            'cep': cep,
            'cidade_bloqueada': cidade_bloqueada,
        }

    partes = re.split(r'[–\-—,|]', endereco_raw)
    partes = [p.strip() for p in partes if p.strip()]

    bairro = None
    cidade = None
    tokens_endereco = []

    for parte in partes:
        if re.fullmatch(r'\d{5}-?\d{3}', parte):
            continue
        if re.fullmatch(r'PB', parte, re.I) or re.fullmatch(r'para[ií]ba', parte, re.I):
            continue
        if re.fullmatch(r'campina grande', parte, re.I):
            cidade = 'Campina Grande'
            continue

        bairro_detectado = bairro_por_token(parte)
        if bairro_detectado:
            bairro = bairro or bairro_detectado
            tokens_endereco.append(bairro_detectado)
            continue

        tokens_endereco.append(parte)

    if not bairro:
        bairro = encontrar_bairro_no_texto(f'{endereco_raw} {titulo or ""} {descricao or ""}')

    if not cidade and not cidade_bloqueada and (bairro or re.search(r'campina grande', endereco_raw, re.I)):
        cidade = 'Campina Grande'

    endereco_partes = []
    if bairro:
        endereco_partes.append(bairro)
    elif tokens_endereco:
        candidato = tokens_endereco[0]
        if not re.fullmatch(r'campina grande', candidato, re.I):
            endereco_partes.append(candidato)

    if cidade:
        endereco_partes.append(cidade)
    if estado:
        endereco_partes.append(estado)

    endereco = ', '.join(dict.fromkeys(endereco_partes)) if endereco_partes else None

    return {
        'endereco': endereco,
        'bairro': bairro,
        'cidade': cidade,
        'estado': estado,
        'cep': cep,
        'cidade_bloqueada': cidade_bloqueada,
    }


def extrair_bairro_cidade(endereco_raw: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    endereco = extrair_endereco(endereco_raw)
    return endereco['bairro'], endereco['cidade']


def aplicar_filtros(dados: dict, config: dict) -> bool:
    if config.get('remover_sem_preco', True) and dados.get('preco') is None:
        return False

    preco_max = config.get('preco_maximo')
    if preco_max and dados.get('preco') and dados['preco'] > preco_max:
        return False

    texto = texto_anuncio(dados)

    cidades_bloqueadas = config.get('cidades_bloqueadas') or CIDADES_BLOQUEADAS_PADRAO
    if dados.get('cidade_bloqueada') or cidade_bloqueada_no_texto(texto, cidades_bloqueadas):
        return False

    termos_bloqueados = config.get('termos_bloqueados') or TERMOS_BLOQUEADOS_PADRAO
    texto_bloqueio_categoria = ' '.join(c for c in [dados.get('titulo'), dados.get('categoria')] if c)
    if contem_termo(texto_bloqueio_categoria, termos_bloqueados):
        return False

    cidades_permitidas = config.get('cidades_permitidas', [])
    if cidades_permitidas:
        cidade = dados.get('cidade')
        if not cidade or normalizar_texto(cidade) not in {normalizar_texto(c) for c in cidades_permitidas}:
            return False

    if config.get('exigir_cidade_permitida', False) and dados.get('cidade') != 'Campina Grande':
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

    descricao = limpar_descricao(anuncio.get('descricao_raw'))
    endereco = extrair_endereco(
        anuncio.get('endereco_raw'),
        titulo=anuncio.get('titulo'),
        descricao=descricao,
    )

    return {
        'external_id': external_id,
        'titulo': anuncio.get('titulo'),
        'preco': parse_preco(anuncio.get('preco_raw')),
        'tipo_anuncio': anuncio.get('tipo_anuncio_raw'),
        'categoria': anuncio.get('categoria_raw'),
        'endereco': endereco['endereco'],
        'cidade': endereco['cidade'],
        'bairro': endereco['bairro'],
        'estado': endereco['estado'],
        'cep': endereco['cep'],
        'cidade_bloqueada': endereco.get('cidade_bloqueada'),
        'quartos': parse_inteiro(anuncio.get('quartos_raw')),
        'banheiros': parse_inteiro(anuncio.get('banheiros_raw')),
        'area_m2': parse_area(anuncio.get('area_raw')),
        'condominio': parse_preco(anuncio.get('condominio_raw')),
        'iptu': parse_preco(anuncio.get('iptu_raw')),
        'vagas': parse_inteiro(anuncio.get('vagas_raw')),
        'url': anuncio.get('url'),
        'data_coleta': anuncio.get('data_coleta'),
        'descricao': descricao,
        'fonte': anuncio.get('fonte'),
        'fotos': json.dumps(anuncio.get('fotos') or [], ensure_ascii=False),
    }


CABECALHO = [
    'external_id', 'titulo', 'preco', 'tipo_anuncio', 'categoria',
    'endereco', 'cidade', 'bairro', 'estado', 'cep',
    'quartos', 'banheiros', 'area_m2',
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
