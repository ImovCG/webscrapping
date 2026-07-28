import csv
import json
import os
import re
import unicodedata
from datetime import datetime
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()


CAMPINA_GRANDE_CENTER = {'latitude': -7.2306, 'longitude': -35.8811}

BAIRRO_COORDS = {
    'centro': {'latitude': -7.2210, 'longitude': -35.8810},
    'universitario': {'latitude': -7.2190, 'longitude': -35.8945},
    'bodocongo': {'latitude': -7.2430, 'longitude': -35.9100},
    'novo-bodocongo': {'latitude': -7.2380, 'longitude': -35.9250},
    'tres-irmas': {'latitude': -7.2740, 'longitude': -35.9360},
    'tres-irmaos': {'latitude': -7.2740, 'longitude': -35.9360},
    'centenario': {'latitude': -7.2130, 'longitude': -35.8680},
    'catole': {'latitude': -7.2240, 'longitude': -35.8860},
    'itarare': {'latitude': -7.2360, 'longitude': -35.8800},
    'jardim-tavares': {'latitude': -7.2350, 'longitude': -35.8780},
    'alto-branco': {'latitude': -7.2080, 'longitude': -35.8850},
    'mirante': {'latitude': -7.2170, 'longitude': -35.9050},
    'nova-brasilia': {'latitude': -7.2280, 'longitude': -35.9000},
    'sao-jose': {'latitude': -7.2400, 'longitude': -35.8750},
    'prata': {'latitude': -7.2240, 'longitude': -35.8920},
    'liberdade': {'latitude': -7.2410, 'longitude': -35.8980},
    'cruzeiro': {'latitude': -7.2410, 'longitude': -35.9100},
    'malvinas': {'latitude': -7.2220, 'longitude': -35.9480},
    'serrotao': {'latitude': -7.2580, 'longitude': -35.9350},
    'tambor': {'latitude': -7.2440, 'longitude': -35.8950},
    'santa-rosa': {'latitude': -7.2300, 'longitude': -35.9070},
    'monte-santo': {'latitude': -7.2110, 'longitude': -35.9020},
    'jardim-paulistano': {'latitude': -7.2320, 'longitude': -35.8890},
    'vila-cabral': {'latitude': -7.2490, 'longitude': -35.9220},
    'bela-vista': {'latitude': -7.2190, 'longitude': -35.8700},
    'conceicao': {'latitude': -7.2140, 'longitude': -35.8740},
    'bento-figueiredo': {'latitude': -7.2290, 'longitude': -35.8660},
    'aluizio-campos': {'latitude': -7.2960, 'longitude': -35.9370},
    'jose-pinheiro': {'latitude': -7.2290, 'longitude': -35.8730},
    'sandra-cavalcante': {'latitude': -7.2460, 'longitude': -35.8840},
    'bairro-das-cidades': {'latitude': -7.2580, 'longitude': -35.8850},
    'dinamerica': {'latitude': -7.2300, 'longitude': -35.9170},
    'palmeira': {'latitude': -7.2120, 'longitude': -35.8930},
    'santo-antonio': {'latitude': -7.2250, 'longitude': -35.8720},
    'distrito-industrial': {'latitude': -7.2720, 'longitude': -35.9070},
    'jardim-quarenta': {'latitude': -7.2340, 'longitude': -35.8990},
    'nacoes': {'latitude': -7.2050, 'longitude': -35.8910},
    'velame': {'latitude': -7.2670, 'longitude': -35.8940},
    'quarenta': {'latitude': -7.2320, 'longitude': -35.8950},
    'santa-cruz': {'latitude': -7.2500, 'longitude': -35.8910},
}


def carregar_config() -> dict:
    return {
        'url': os.getenv('BACKEND_URL', 'http://localhost:8080/api/imoveis/lote'),
        'token': os.getenv('BACKEND_TOKEN'),
        'timeout': int(os.getenv('BACKEND_TIMEOUT', '30')),
        'batch_size': int(os.getenv('BACKEND_BATCH_SIZE', '20')),
    }


def slugify(texto: Optional[str]) -> str:
    if not texto:
        return ''
    normalized = unicodedata.normalize('NFKD', texto)
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii').lower()
    return re.sub(r'(^-|-$)', '', re.sub(r'[^a-z0-9]+', '-', ascii_text).strip('-'))


def coordenadas_bairro(bairro: Optional[str]) -> dict:
    if not bairro:
        return CAMPINA_GRANDE_CENTER
    return BAIRRO_COORDS.get(slugify(bairro), CAMPINA_GRANDE_CENTER)


def dividir_em_lotes(registros: list, tamanho: int) -> list:
    if tamanho <= 0:
        return [registros]
    return [registros[i:i + tamanho] for i in range(0, len(registros), tamanho)]


def url_individual(url_lote: str) -> str:
    if url_lote.endswith('/lote'):
        return url_lote[:-5]
    return url_lote.rstrip('/')


def salvar_falha(dados, erro: str) -> str:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    falhou_path = f'artifacts/falhou_envio_{timestamp}.json'
    with open(falhou_path, 'w', encoding='utf-8') as f:
        json.dump({'payload': dados, 'erro': erro}, f, ensure_ascii=False, indent=2)
    print(f'Payload salvo em {falhou_path} para retentativa manual.')
    return falhou_path


def parse_data_coleta(data_str: Optional[str]) -> Optional[str]:
    if not data_str:
        return None
    try:
        dt = datetime.strptime(data_str, '%d/%m/%Y')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return None


def parse_fotos(fotos_str: Optional[str]) -> list[str]:
    if not fotos_str:
        return []
    try:
        fotos = json.loads(fotos_str)
        return fotos if isinstance(fotos, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def csv_para_payload(linha: dict) -> dict:
    preco = linha.get('preco', '')
    preco_float = float(preco) if preco else None

    condominio = linha.get('condominio', '')
    condominio_float = float(condominio) if condominio else None

    iptu = linha.get('iptu', '')
    iptu_float = float(iptu) if iptu else None

    area = linha.get('area_m2', '')
    area_float = float(area) if area else None

    quartos = linha.get('quartos', '')
    quartos_int = int(quartos) if quartos else None

    banheiros = linha.get('banheiros', '')
    banheiros_int = int(banheiros) if banheiros else None

    vagas = linha.get('vagas', '')
    vagas_int = int(vagas) if vagas else None

    bairro = linha.get('bairro') or ''
    cidade = linha.get('cidade') or ''
    estado = linha.get('estado', 'PB')
    endereco_parts = [p for p in [bairro, cidade, estado] if p]
    endereco = linha.get('endereco') or (', '.join(endereco_parts) if endereco_parts else None)
    coordenadas = coordenadas_bairro(bairro)

    return {
        'externalId': linha.get('external_id'),
        'fonte': linha.get('fonte', 'olx'),
        'titulo': linha.get('titulo'),
        'preco': preco_float,
        'tipoAnuncio': linha.get('tipo_anuncio'),
        'categoria': linha.get('categoria') or None,
        'endereco': endereco,
        'bairro': linha.get('bairro') or None,
        'latitude': coordenadas['latitude'],
        'longitude': coordenadas['longitude'],
        'cidade': linha.get('cidade') or None,
        'estado': estado,
        'quartos': quartos_int,
        'banheiros': banheiros_int,
        'vagas': vagas_int,
        'areaM2': area_float,
        'condominio': condominio_float,
        'iptu': iptu_float,
        'descricao': linha.get('descricao') or None,
        'url': linha.get('url'),
        'dataColeta': parse_data_coleta(linha.get('data_coleta')),
        'fotos': parse_fotos(linha.get('fotos')),
    }


def enviar_um(imovel: dict, url: str, headers: dict, timeout: int) -> bool:
    try:
        resp = requests.post(url, json=imovel, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f'  Falha registro {imovel.get("externalId")}: {e}')
        return False


def enviar_lote(caminho_csv: str) -> dict:
    config = carregar_config()
    url = config['url']
    token = config['token']
    timeout = config['timeout']
    batch_size = config['batch_size']

    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    registros = []
    with open(caminho_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for linha in reader:
            registros.append(csv_para_payload(linha))

    if not registros:
        print('Nenhum registro para enviar.')
        return {'enviados': 0, 'falhas': 0, 'erro': None}

    url_um = url_individual(url)
    lotes = dividir_em_lotes(registros, batch_size)
    total = len(registros)
    enviados = 0
    falhas = 0
    erro = None

    for idx, lote in enumerate(lotes, start=1):
        payload = {'imoveis': lote}
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            enviados += len(lote)
            print(f'Lote {idx}/{len(lotes)}: {len(lote)} enviados ({enviados}/{total} no total)')
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 400:
                print(f'Lote {idx}/{len(lotes)} rejeitado (400 - validacao). Tentando individual...')
                lote_falhas = []
                for imovel in lote:
                    if enviar_um(imovel, url_um, headers, timeout):
                        enviados += 1
                    else:
                        lote_falhas.append(imovel)
                if lote_falhas:
                    salvar_falha(lote_falhas, f'validacao individual falhou para {len(lote_falhas)} registro(s)')
                    falhas += len(lote_falhas)
                    erro = 'validacao individual'
            else:
                print(f'Erro ao enviar lote {idx}/{len(lotes)}: {e}')
                salvar_falha(payload, str(e))
                falhas += len(lote)
                erro = str(e)
        except requests.RequestException as e:
            print(f'Erro ao enviar lote {idx}/{len(lotes)}: {e}')
            salvar_falha(payload, str(e))
            falhas += len(lote)
            erro = str(e)

    print(f'Envio concluido: {enviados} enviados, {falhas} falhas ({len(lotes)} lotes de ate {batch_size})')
    return {'enviados': enviados, 'falhas': falhas, 'erro': erro}


if __name__ == '__main__':
    import glob
    limpos = sorted(glob.glob('artifacts/dados_limpos_*.csv'))
    if not limpos:
        print('Nenhum arquivo dados_limpos_*.csv encontrado em artifacts/')
    else:
        enviar_lote(limpos[-1])
