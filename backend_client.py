import csv
import json
import os
from datetime import datetime
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()


def carregar_config() -> dict:
    return {
        'url': os.getenv('BACKEND_URL', 'http://localhost:8080/api/imoveis/lote'),
        'token': os.getenv('BACKEND_TOKEN'),
        'timeout': int(os.getenv('BACKEND_TIMEOUT', '30')),
    }


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
    endereco = ', '.join(endereco_parts) if endereco_parts else None

    return {
        'externalId': linha.get('external_id'),
        'fonte': linha.get('fonte', 'olx'),
        'titulo': linha.get('titulo'),
        'preco': preco_float,
        'tipoAnuncio': linha.get('tipo_anuncio'),
        'categoria': linha.get('categoria') or None,
        'endereco': endereco,
        'bairro': linha.get('bairro') or None,
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


def enviar_lote(caminho_csv: str) -> dict:
    config = carregar_config()
    url = config['url']
    token = config['token']
    timeout = config['timeout']

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

    payload = {'imoveis': registros}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        print(f'Enviados {len(registros)} registros para {url}')
        print(f'Resposta: {resp.status_code}')
        return {'enviados': len(registros), 'falhas': 0, 'erro': None}
    except requests.RequestException as e:
        print(f'Erro ao enviar dados: {e}')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        falhou_path = f'artifacts/falhou_envio_{timestamp}.json'
        with open(falhou_path, 'w', encoding='utf-8') as f:
            json.dump({'payload': payload, 'erro': str(e)}, f, ensure_ascii=False, indent=2)
        print(f'Payload salvo em {falhou_path} para retentativa manual.')
        return {'enviados': 0, 'falhas': len(registros), 'erro': str(e)}


if __name__ == '__main__':
    import glob
    limpos = sorted(glob.glob('artifacts/dados_limpos_*.csv'))
    if not limpos:
        print('Nenhum arquivo dados_limpos_*.csv encontrado em artifacts/')
    else:
        enviar_lote(limpos[-1])
