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
        'batch_size': int(os.getenv('BACKEND_BATCH_SIZE', '20')),
    }


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
