import unittest

import scraper_olx as s


class TestUrlValida(unittest.TestCase):
    def test_http_valido(self):
        self.assertTrue(s._url_valida('https://olx-pt.staticaflexibleusercontent.com/img.jpg'))

    def test_data_uri_rejeitado(self):
        self.assertFalse(s._url_valida('data:image/svg+xml;base64,abc'))

    def test_vazio(self):
        self.assertFalse(s._url_valida(''))
        self.assertFalse(s._url_valida(None))

    def test_protocolo_invalido(self):
        self.assertFalse(s._url_valida('ftp://x/img.jpg'))

    def test_blacklist_logo(self):
        self.assertFalse(s._url_valida('https://olx.com.br/logo.svg'))

    def test_blacklist_avatar(self):
        self.assertFalse(s._url_valida('https://olx.com.br/avatar/user-42.png'))


class TestPrimeiroSrcset(unittest.TestCase):
    def test_unico(self):
        self.assertEqual(
            s._primeiro_url_srcset('https://a/img.jpg 1x'),
            'https://a/img.jpg',
        )

    def test_multiplos(self):
        srcset = 'https://a/img.jpg 1x, https://a/img@2x.jpg 2x'
        self.assertEqual(s._primeiro_url_srcset(srcset), 'https://a/img.jpg')

    def test_data_primeiro_pula(self):
        srcset = 'data:image/svg+xml,abc, https://a/real.jpg 2x'
        self.assertEqual(s._primeiro_url_srcset(srcset), 'https://a/real.jpg')

    def test_vazio(self):
        self.assertIsNone(s._primeiro_url_srcset(None))
        self.assertIsNone(s._primeiro_url_srcset(''))

    def test_tudo_invalido(self):
        self.assertIsNone(s._primeiro_url_srcset('data:image/svg+xml,x, data:image/svg+xml,y'))


class TestMaxFotos(unittest.TestCase):
    def test_constante_existe(self):
        self.assertEqual(s.MAX_FOTOS, 12)


if __name__ == '__main__':
    unittest.main(verbosity=2)