import unittest

from normalizador import (
    parse_preco,
    parse_inteiro,
    parse_area,
    extrair_bairro_cidade,
    aplicar_filtros,
    normalizar_anuncio,
)


class TestParsePreco(unittest.TestCase):
    def test_preco_simples(self):
        self.assertEqual(parse_preco('R$ 1.200'), 1200.0)

    def test_preco_com_centavos(self):
        self.assertEqual(parse_preco('R$ 1.200,50'), 1200.50)

    def test_preco_grande(self):
        self.assertEqual(parse_preco('R$ 3.500'), 3500.0)

    def test_preco_sem_prefixo(self):
        self.assertEqual(parse_preco('1370'), 1370.0)

    def test_preco_apenas_numero_com_virgula(self):
        self.assertEqual(parse_preco('1.370'), 1370.0)

    def test_preco_apenas_virgula_decimal(self):
        self.assertEqual(parse_preco('350,50'), 350.50)

    def test_preco_a_combinar(self):
        self.assertIsNone(parse_preco('A combinar'))

    def test_preco_nao_informado(self):
        self.assertIsNone(parse_preco('Não informado'))

    def test_preco_nao_informado_sem_acento(self):
        self.assertIsNone(parse_preco('Nao informado'))

    def test_preco_gratis(self):
        self.assertIsNone(parse_preco('Grátis'))

    def test_preco_none(self):
        self.assertIsNone(parse_preco(None))

    def test_preco_vazio(self):
        self.assertIsNone(parse_preco(''))

    def test_preco_lixo(self):
        self.assertIsNone(parse_preco('abc'))

    def test_preco_zero(self):
        self.assertEqual(parse_preco('R$ 0'), 0.0)


class TestParseInteiro(unittest.TestCase):
    def test_quartos(self):
        self.assertEqual(parse_inteiro('2 quartos'), 2)

    def test_banheiros(self):
        self.assertEqual(parse_inteiro('1 banheiro'), 1)

    def test_com_bullet(self):
        self.assertEqual(parse_inteiro('• 3 quartos'), 3)

    def test_apenas_numero(self):
        self.assertEqual(parse_inteiro('5'), 5)

    def test_none(self):
        self.assertIsNone(parse_inteiro(None))

    def test_vazio(self):
        self.assertIsNone(parse_inteiro(''))

    def test_sem_numero(self):
        self.assertIsNone(parse_inteiro('sem informacao'))

    def test_zero(self):
        self.assertEqual(parse_inteiro('0 vagas'), 0)


class TestParseArea(unittest.TestCase):
    def test_area_com_m2(self):
        self.assertEqual(parse_area('50 m²'), 50.0)

    def test_area_apenas_numero(self):
        self.assertEqual(parse_area('50'), 50.0)

    def test_area_decimal_virgula(self):
        self.assertEqual(parse_area('50,5'), 50.5)

    def test_area_decimal_ponto(self):
        self.assertEqual(parse_area('50.5'), 50.5)

    def test_area_com_texto(self):
        self.assertEqual(parse_area('Área 80 m²'), 80.0)

    def test_none(self):
        self.assertIsNone(parse_area(None))

    def test_vazio(self):
        self.assertIsNone(parse_area(''))

    def test_sem_numero(self):
        self.assertIsNone(parse_area('metro quadrado'))

    def test_lixo_com_numero_no_meio(self):
        self.assertEqual(parse_area('xx12yy'), 12.0)


class TestExtrairBairroCidade(unittest.TestCase):
    def test_endereco_completo_bairro_cidade_estado(self):
        bairro, cidade = extrair_bairro_cidade('Centro, Campina Grande, PB')
        self.assertEqual(bairro, 'Centro')
        self.assertEqual(cidade, 'Campina Grande')

    def test_endereco_bairro_cidade(self):
        bairro, cidade = extrair_bairro_cidade('Centro, Campina Grande')
        self.assertEqual(bairro, 'Centro')
        self.assertEqual(cidade, 'Campina Grande')

    def test_endereco_so_bairro(self):
        bairro, cidade = extrair_bairro_cidade('Centro')
        self.assertEqual(bairro, 'Centro')
        self.assertIsNone(cidade)

    def test_endereco_com_traco(self):
        bairro, cidade = extrair_bairro_cidade('Centro - Campina Grande')
        self.assertEqual(bairro, 'Centro')
        self.assertEqual(cidade, 'Campina Grande')

    def test_endereco_com_traco_longo(self):
        bairro, cidade = extrair_bairro_cidade('Centro — Campina Grande — PB')
        self.assertEqual(bairro, 'Centro')
        self.assertEqual(cidade, 'Campina Grande')

    def test_endereco_com_pipe(self):
        bairro, cidade = extrair_bairro_cidade('Centro|Campina Grande|PB')
        self.assertEqual(bairro, 'Centro')
        self.assertEqual(cidade, 'Campina Grande')

    def test_endereco_cidade_estado_sem_bairro(self):
        bairro, cidade = extrair_bairro_cidade('Campina Grande, PB')
        self.assertEqual(bairro, 'Campina Grande')
        self.assertIsNone(cidade)

    def test_endereco_none(self):
        bairro, cidade = extrair_bairro_cidade(None)
        self.assertIsNone(bairro)
        self.assertIsNone(cidade)

    def test_endereco_vazio(self):
        bairro, cidade = extrair_bairro_cidade('')
        self.assertIsNone(bairro)
        self.assertIsNone(cidade)


class TestAplicarFiltros(unittest.TestCase):
    def setUp(self):
        self.config_padrao = {
            'preco_maximo': 1500,
            'bairros_permitidos': [],
            'categorias_permitidas': [],
            'remover_sem_preco': True,
            'remover_sem_bairro': False,
        }

    def test_aceita_dentro_do_preco(self):
        dados = {'preco': 1200.0, 'bairro': 'Centro', 'categoria': 'apartamento'}
        self.assertTrue(aplicar_filtros(dados, self.config_padrao))

    def test_rejeita_acima_do_preco(self):
        dados = {'preco': 2000.0, 'bairro': 'Centro', 'categoria': None}
        self.assertFalse(aplicar_filtros(dados, self.config_padrao))

    def test_rejeita_sem_preco(self):
        dados = {'preco': None, 'bairro': 'Centro', 'categoria': None}
        self.assertFalse(aplicar_filtros(dados, self.config_padrao))

    def test_aceita_sem_preco_se_filtro_desligado(self):
        config = {**self.config_padrao, 'remover_sem_preco': False}
        dados = {'preco': None, 'bairro': 'Centro', 'categoria': None}
        self.assertTrue(aplicar_filtros(dados, config))

    def test_aceita_no_limite_do_preco(self):
        dados = {'preco': 1500.0, 'bairro': 'Centro', 'categoria': None}
        self.assertTrue(aplicar_filtros(dados, self.config_padrao))

    def test_rejeita_bairro_nao_permitido(self):
        config = {**self.config_padrao, 'bairros_permitidos': ['Centro', 'Bodocongo']}
        dados = {'preco': 1200.0, 'bairro': 'Malvinas', 'categoria': None}
        self.assertFalse(aplicar_filtros(dados, config))

    def test_aceita_bairro_permitido(self):
        config = {**self.config_padrao, 'bairros_permitidos': ['Centro', 'Bodocongo']}
        dados = {'preco': 1200.0, 'bairro': 'Centro', 'categoria': None}
        self.assertTrue(aplicar_filtros(dados, config))

    def test_rejeita_categoria_nao_permitida(self):
        config = {**self.config_padrao, 'categorias_permitidas': ['apartamento']}
        dados = {'preco': 1200.0, 'bairro': 'Centro', 'categoria': 'casa'}
        self.assertFalse(aplicar_filtros(dados, config))

    def test_aceita_categoria_permitida(self):
        config = {**self.config_padrao, 'categorias_permitidas': ['apartamento']}
        dados = {'preco': 1200.0, 'bairro': 'Centro', 'categoria': 'apartamento'}
        self.assertTrue(aplicar_filtros(dados, config))

    def test_rejeita_sem_bairro_se_filtro_ligado(self):
        config = {**self.config_padrao, 'remover_sem_bairro': True}
        dados = {'preco': 1200.0, 'bairro': None, 'categoria': None}
        self.assertFalse(aplicar_filtros(dados, config))

    def test_aceita_sem_bairro_se_filtro_desligado(self):
        dados = {'preco': 1200.0, 'bairro': None, 'categoria': None}
        self.assertTrue(aplicar_filtros(dados, self.config_padrao))

    def test_sem_limite_de_preco(self):
        config = {**self.config_padrao, 'preco_maximo': None}
        dados = {'preco': 999999.0, 'bairro': 'Centro', 'categoria': None}
        self.assertTrue(aplicar_filtros(dados, config))


class TestNormalizarAnuncio(unittest.TestCase):
    def test_normalizacao_completa(self):
        anuncio = {
            'external_id': '1234567890',
            'titulo': 'Apto 2 quartos - Centro',
            'preco_raw': 'R$ 1.370',
            'tipo_anuncio_raw': 'aluguel',
            'categoria_raw': None,
            'endereco_raw': 'Centro, Campina Grande, PB',
            'quartos_raw': '2 quartos',
            'banheiros_raw': '1 banheiro',
            'area_raw': '50 m²',
            'condominio_raw': 'R$ 300',
            'iptu_raw': None,
            'vagas_raw': '1 vaga',
            'url': 'https://pb.olx.com.br/teste',
            'data_coleta': '06/07/2026',
            'descricao_raw': 'Apartamento bem localizado',
            'fonte': 'olx',
            'fotos': ['https://img.olx.com.br/foto1.jpg'],
        }

        resultado = normalizar_anuncio(anuncio)

        self.assertEqual(resultado['external_id'], '1234567890')
        self.assertEqual(resultado['titulo'], 'Apto 2 quartos - Centro')
        self.assertEqual(resultado['preco'], 1370.0)
        self.assertEqual(resultado['tipo_anuncio'], 'aluguel')
        self.assertIsNone(resultado['categoria'])
        self.assertEqual(resultado['cidade'], 'Campina Grande')
        self.assertEqual(resultado['bairro'], 'Centro')
        self.assertEqual(resultado['quartos'], 2)
        self.assertEqual(resultado['banheiros'], 1)
        self.assertEqual(resultado['area_m2'], 50.0)
        self.assertEqual(resultado['condominio'], 300.0)
        self.assertIsNone(resultado['iptu'])
        self.assertEqual(resultado['vagas'], 1)
        self.assertEqual(resultado['url'], 'https://pb.olx.com.br/teste')
        self.assertEqual(resultado['data_coleta'], '06/07/2026')
        self.assertEqual(resultado['descricao'], 'Apartamento bem localizado')
        self.assertEqual(resultado['fonte'], 'olx')

    def test_normalizacao_sem_external_id(self):
        anuncio = {'titulo': 'Sem id', 'preco_raw': 'R$ 500'}
        self.assertIsNone(normalizar_anuncio(anuncio))

    def test_normalizacao_external_id_vazio(self):
        anuncio = {'external_id': '', 'titulo': 'Teste'}
        self.assertIsNone(normalizar_anuncio(anuncio))

    def test_normalizacao_campos_invalidos(self):
        anuncio = {
            'external_id': '123',
            'titulo': 'Teste',
            'preco_raw': 'a combinar',
            'endereco_raw': 'Bairro, Cidade, PB',
            'quartos_raw': 'sem info',
            'banheiros_raw': None,
            'area_raw': '',
            'condominio_raw': 'nao informado',
            'iptu_raw': 'grátis',
            'vagas_raw': '',
            'fotos': [],
        }

        resultado = normalizar_anuncio(anuncio)

        self.assertIsNone(resultado['preco'])
        self.assertIsNone(resultado['quartos'])
        self.assertIsNone(resultado['banheiros'])
        self.assertIsNone(resultado['area_m2'])
        self.assertIsNone(resultado['condominio'])
        self.assertIsNone(resultado['iptu'])
        self.assertIsNone(resultado['vagas'])

    def test_normalizacao_fotos_serializadas_como_json(self):
        anuncio = {
            'external_id': '123',
            'titulo': 'Teste',
            'fotos': ['https://a.jpg', 'https://b.jpg'],
        }
        import json
        resultado = normalizar_anuncio(anuncio)
        fotos = json.loads(resultado['fotos'])
        self.assertEqual(fotos, ['https://a.jpg', 'https://b.jpg'])

    def test_normalizacao_sem_fotos(self):
        anuncio = {'external_id': '123', 'titulo': 'Teste'}
        import json
        resultado = normalizar_anuncio(anuncio)
        self.assertEqual(json.loads(resultado['fotos']), [])

    def test_normalizacao_fotos_none(self):
        anuncio = {'external_id': '123', 'titulo': 'Teste', 'fotos': None}
        import json
        resultado = normalizar_anuncio(anuncio)
        self.assertEqual(json.loads(resultado['fotos']), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
