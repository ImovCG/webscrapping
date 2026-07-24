import unittest

from scraper_facebook import (
    eh_anuncio,
    extrair_post_id,
    inferir_categoria,
    extrair_por_regex,
    extrair_endereco,
)


class TestEhAnuncio(unittest.TestCase):
    def test_anuncio_casa(self):
        self.assertTrue(eh_anuncio('Alugo casa no Catolé, 2 quartos, R$ 800'))

    def test_anuncio_apartamento(self):
        self.assertTrue(eh_anuncio('Apartamento disponível para alugar na Prata'))

    def test_anuncio_kitnet(self):
        self.assertTrue(eh_anuncio('Kitnet mobiliada, aluguel 550 reais'))

    def test_procuro_casa_descartado(self):
        self.assertFalse(eh_anuncio('Procuro casa para alugar no Catingueira'))

    def test_alguem_tem_descartado(self):
        self.assertFalse(eh_anuncio('Alguém tem apartamento para alugar barato?'))

    def test_preciso_descartado(self):
        self.assertFalse(eh_anuncio('Preciso de um apartamento com 1 quarto urgente'))

    def test_sem_tipo_imovel_descartado(self):
        # Menciona aluguel/valor mas nenhum tipo de imovel -> nao e anuncio.
        self.assertFalse(eh_anuncio('Vendo moto R$ 5000, aceito troca'))

    def test_none_descartado(self):
        self.assertFalse(eh_anuncio(None))

    def test_vazio_descartado(self):
        self.assertFalse(eh_anuncio(''))


class TestExtrairPostId(unittest.TestCase):
    def test_posts(self):
        url = 'https://www.facebook.com/groups/504632767134665/posts/123456789/'
        self.assertEqual(extrair_post_id(url), '123456789')

    def test_permalink(self):
        url = 'https://www.facebook.com/groups/x/permalink/987654321/'
        self.assertEqual(extrair_post_id(url), '987654321')

    def test_story_fbid(self):
        url = 'https://www.facebook.com/story.php?story_fbid=555&id=1'
        self.assertEqual(extrair_post_id(url), '555')

    def test_multi_permalinks(self):
        url = 'https://www.facebook.com/groups/504632767134665/?multi_permalinks=42'
        self.assertEqual(extrair_post_id(url), '42')

    def test_sem_id(self):
        self.assertIsNone(extrair_post_id('https://www.facebook.com/groups/x/'))

    def test_none(self):
        self.assertIsNone(extrair_post_id(None))


class TestInferirCategoria(unittest.TestCase):
    def test_casa(self):
        self.assertEqual(inferir_categoria('Alugo casa grande'), 'casa')

    def test_apartamento(self):
        self.assertEqual(inferir_categoria('Apartamento novo'), 'apartamento')

    def test_apto(self):
        self.assertEqual(inferir_categoria('Apto 2 quartos'), 'apartamento')

    def test_kitnet(self):
        self.assertEqual(inferir_categoria('Kitnet mobiliada'), 'kitnet')

    def test_quitinete(self):
        self.assertEqual(inferir_categoria('Quitinete no centro'), 'kitnet')

    def test_sem_categoria(self):
        self.assertIsNone(inferir_categoria('Vendo carro'))


class TestExtrairPorRegex(unittest.TestCase):
    def test_preco(self):
        self.assertEqual(extrair_por_regex('Aluguel R$ 850 por mes', r'R\$\s?[\d.,]+'), 'R$ 850')

    def test_quartos(self):
        self.assertEqual(
            extrair_por_regex('Casa com 3 quartos', r'\d+\s*(?:quartos?|qto?s?|dormit\w*)'),
            '3 quartos',
        )

    def test_sem_match(self):
        self.assertIsNone(extrair_por_regex('sem numero aqui', r'R\$\s?[\d.,]+'))

    def test_none(self):
        self.assertIsNone(extrair_por_regex(None, r'R\$\s?[\d.,]+'))


class TestExtrairEndereco(unittest.TestCase):
    def test_bairro_conhecido(self):
        self.assertEqual(extrair_endereco('Alugo casa no Catolé perto do shopping'), 'Catolé')

    def test_bairro_case_insensitive(self):
        self.assertEqual(extrair_endereco('apartamento na prata'), 'Prata')

    def test_sem_bairro(self):
        self.assertIsNone(extrair_endereco('Alugo casa em lugar desconhecido'))

    def test_none(self):
        self.assertIsNone(extrair_endereco(None))


if __name__ == '__main__':
    unittest.main()
