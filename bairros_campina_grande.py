import re
import unicodedata
from typing import Optional


BAIRROS_CAMPINA_GRANDE = {
    'Acácio Figueiredo',
    'Alto Branco',
    'Aluízio Campos',
    'Araxa',
    'Bairro das Cidades',
    'Bela Vista',
    'Bento Figueiredo',
    'Bodocongó',
    'Catolé',
    'Centenário',
    'Centro',
    'Conceição',
    'Cruzeiro',
    'Cuités',
    'Dinamérica',
    'Distrito Industrial',
    'Glória',
    'Itararé',
    'Jardim Continental',
    'Jardim Paulistano',
    'Jardim Quarenta',
    'Jardim Tavares',
    'Jeremias',
    'José Pinheiro',
    'Liberdade',
    'Louzeiro',
    'Malvinas',
    'Mirante',
    'Monte Castelo',
    'Monte Santo',
    'Nações',
    'Nova Brasília',
    'Novo Bodocongó',
    'Palmeira',
    'Palmeira Imperial',
    'Pedregal',
    'Portal Sudoeste',
    'Prata',
    'Presidente Médici',
    'Quarenta',
    'Ramadinha',
    'Rosa Mística',
    'Sandra Cavalcante',
    'Santa Cruz',
    'Santa Rosa',
    'Santo Antônio',
    'São José',
    'Serrotão',
    'Tambor',
    'Três Irmãs',
    'Universitário',
    'Velame',
    'Vila Cabral',
}


ALIASES_BAIRROS = {
    'acacio figueiredo': 'Acácio Figueiredo',
    'alto branco': 'Alto Branco',
    'aluizio campos': 'Aluízio Campos',
    'araxa': 'Araxa',
    'bairro das cidades': 'Bairro das Cidades',
    'cidades': 'Bairro das Cidades',
    'bela vista': 'Bela Vista',
    'bento figueiredo': 'Bento Figueiredo',
    'bodocongo': 'Bodocongó',
    'bodocongó': 'Bodocongó',
    'catole': 'Catolé',
    'catolé': 'Catolé',
    'centenario': 'Centenário',
    'centenário': 'Centenário',
    'centro': 'Centro',
    'conceicao': 'Conceição',
    'conceição': 'Conceição',
    'cruzeiro': 'Cruzeiro',
    'cuites': 'Cuités',
    'cuités': 'Cuités',
    'dinamerica': 'Dinamérica',
    'dinamérica': 'Dinamérica',
    'distrito industrial': 'Distrito Industrial',
    'gloria': 'Glória',
    'glória': 'Glória',
    'itarare': 'Itararé',
    'itararé': 'Itararé',
    'jardim continental': 'Jardim Continental',
    'jardim paulistano': 'Jardim Paulistano',
    'jardim quarenta': 'Jardim Quarenta',
    'jardim tavares': 'Jardim Tavares',
    'jeremias': 'Jeremias',
    'jose pinheiro': 'José Pinheiro',
    'josé pinheiro': 'José Pinheiro',
    'liberdade': 'Liberdade',
    'louzeiro': 'Louzeiro',
    'malvinas': 'Malvinas',
    'mirante': 'Mirante',
    'monte castelo': 'Monte Castelo',
    'monte santo': 'Monte Santo',
    'nacoes': 'Nações',
    'nações': 'Nações',
    'nova brasilia': 'Nova Brasília',
    'nova brasília': 'Nova Brasília',
    'novo bodocongo': 'Novo Bodocongó',
    'novo bodocongó': 'Novo Bodocongó',
    'palmeira': 'Palmeira',
    'palmeira imperial': 'Palmeira Imperial',
    'pedregal': 'Pedregal',
    'portal sudoeste': 'Portal Sudoeste',
    'prata': 'Prata',
    'presidente medici': 'Presidente Médici',
    'presidente médici': 'Presidente Médici',
    'quarenta': 'Quarenta',
    'ramadinha': 'Ramadinha',
    'rosa mistica': 'Rosa Mística',
    'rosa mística': 'Rosa Mística',
    'sandra cavalcante': 'Sandra Cavalcante',
    'santa cruz': 'Santa Cruz',
    'santa rosa': 'Santa Rosa',
    'santo antonio': 'Santo Antônio',
    'santo antônio': 'Santo Antônio',
    'sao jose': 'São José',
    'são josé': 'São José',
    'serrotao': 'Serrotão',
    'serrotão': 'Serrotão',
    'tambor': 'Tambor',
    'tres irmas': 'Três Irmãs',
    'três irmãs': 'Três Irmãs',
    'universitario': 'Universitário',
    'universitário': 'Universitário',
    'velame': 'Velame',
    'vila cabral': 'Vila Cabral',
}


def normalizar_texto(texto: Optional[str]) -> str:
    if not texto:
        return ''
    sem_acento = unicodedata.normalize('NFD', texto)
    sem_acento = ''.join(c for c in sem_acento if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', sem_acento).strip().lower()


def bairro_por_token(token: Optional[str]) -> Optional[str]:
    normalizado = normalizar_texto(token)
    return ALIASES_BAIRROS.get(normalizado)


def encontrar_bairro_no_texto(texto: Optional[str]) -> Optional[str]:
    normalizado = normalizar_texto(texto)
    if not normalizado:
        return None

    for alias, bairro in sorted(ALIASES_BAIRROS.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf'\b{re.escape(alias)}\b', normalizado):
            return bairro
    return None
