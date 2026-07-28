import unittest
from unittest.mock import patch, MagicMock

import requests

import backend_client as bc


def _resp(status_code: int) -> MagicMock:
    r = MagicMock(spec=requests.Response)
    r.status_code = status_code
    r.raise_for_status = MagicMock()
    if status_code >= 400:
        err = requests.HTTPError(response=r)
        r.raise_for_status.side_effect = err
    return r


class TestUrlIndividual(unittest.TestCase):
    def test_strip_lote(self):
        self.assertEqual(
            bc.url_individual('http://localhost:8080/api/imoveis/lote'),
            'http://localhost:8080/api/imoveis',
        )

    def test_sem_lote(self):
        self.assertEqual(
            bc.url_individual('http://localhost:8080/api/imoveis'),
            'http://localhost:8080/api/imoveis',
        )


class TestParseFotos(unittest.TestCase):
    def test_none(self):
        self.assertEqual(bc.parse_fotos(None), [])

    def test_vazio(self):
        self.assertEqual(bc.parse_fotos(''), [])

    def test_json_valido(self):
        self.assertEqual(
            bc.parse_fotos('["https://a.jpg", "https://b.jpg"]'),
            ['https://a.jpg', 'https://b.jpg'],
        )

    def test_json_invalido(self):
        self.assertEqual(bc.parse_fotos('nao eh json'), [])

    def test_nao_lista(self):
        self.assertEqual(bc.parse_fotos('{"k": "v"}'), [])


class TestCsvParaPayloadFotos(unittest.TestCase):
    def test_fotos_serializadas(self):
        linha = {'fotos': '["https://a.jpg", "https://b.jpg"]'}
        payload = bc.csv_para_payload(linha)
        self.assertEqual(payload['fotos'], ['https://a.jpg', 'https://b.jpg'])

    def test_fotos_vazias(self):
        payload = bc.csv_para_payload({'fotos': '[]'})
        self.assertEqual(payload['fotos'], [])

    def test_fotos_ausentes(self):
        payload = bc.csv_para_payload({})
        self.assertEqual(payload['fotos'], [])

    def test_coordenadas_por_bairro(self):
        payload = bc.csv_para_payload({'bairro': 'Três Irmãs'})
        self.assertEqual(payload['latitude'], -7.2740)
        self.assertEqual(payload['longitude'], -35.9360)

    def test_coordenadas_fallback_centro(self):
        payload = bc.csv_para_payload({})
        self.assertEqual(payload['latitude'], bc.CAMPINA_GRANDE_CENTER['latitude'])
        self.assertEqual(payload['longitude'], bc.CAMPINA_GRANDE_CENTER['longitude'])


class TestEnviarUm(unittest.TestCase):
    @patch('backend_client.requests.post')
    def test_ok(self, mock_post):
        mock_post.return_value = _resp(201)
        self.assertTrue(bc.enviar_um({'externalId': '1'}, 'http://x', {}, 10))
        mock_post.assert_called_once()

    @patch('backend_client.requests.post')
    def test_falha_400(self, mock_post):
        mock_post.return_value = _resp(400)
        self.assertFalse(bc.enviar_um({'externalId': '1'}, 'http://x', {}, 10))


class TestEnviarLote(unittest.TestCase):
    csv_path = 'artifacts/_test_lote.csv'

    def setUp(self):
        import csv, os
        os.makedirs('artifacts', exist_ok=True)
        cab = ['external_id', 'titulo', 'preco', 'tipo_anuncio', 'categoria',
               'cidade', 'bairro', 'quartos', 'banheiros', 'area_m2',
               'condominio', 'iptu', 'vagas', 'url', 'data_coleta',
               'descricao', 'fonte', 'fotos']
        rows = [
            {'external_id': '1', 'titulo': 'A', 'preco': '100', 'tipo_anuncio': 'aluguel',
             'categoria': '', 'cidade': 'CG', 'bairro': 'Centro', 'quartos': '', 'banheiros': '',
             'area_m2': '', 'condominio': '', 'iptu': '', 'vagas': '',
             'url': 'http://x/1', 'data_coleta': '13/07/2026', 'descricao': '', 'fonte': 'olx',
             'fotos': '[]'},
        ]
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cab)
            w.writeheader()
            w.writerows(rows)

    def tearDown(self):
        import os
        for fn in os.listdir('artifacts'):
            if fn.startswith('falhou_envio_'):
                os.remove(f'artifacts/{fn}')
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    @patch('backend_client.requests.post')
    def test_lote_ok(self, mock_post):
        mock_post.return_value = _resp(201)
        r = bc.enviar_lote(self.csv_path)
        self.assertEqual(r['enviados'], 1)
        self.assertEqual(r['falhas'], 0)
        self.assertIsNone(r['erro'])
        mock_post.assert_called_once()

    @patch('backend_client.requests.post')
    def test_lote_400_falla_individual(self, mock_post):
        lote_resp = _resp(400)
        indiv_ok = _resp(201)
        mock_post.side_effect = [lote_resp, indiv_ok]
        r = bc.enviar_lote(self.csv_path)
        self.assertEqual(r['enviados'], 1)
        self.assertEqual(r['falhas'], 0)
        self.assertEqual(mock_post.call_count, 2)

    @patch('backend_client.requests.post')
    def test_lote_400_e_individual_falha(self, mock_post):
        lote_resp = _resp(400)
        indiv_resp = _resp(400)
        mock_post.side_effect = [lote_resp, indiv_resp]
        r = bc.enviar_lote(self.csv_path)
        self.assertEqual(r['enviados'], 0)
        self.assertEqual(r['falhas'], 1)
        self.assertEqual(r['erro'], 'validacao individual')

    @patch('backend_client.requests.post')
    def test_erro_rede(self, mock_post):
        mock_post.side_effect = requests.ConnectionError('boom')
        r = bc.enviar_lote(self.csv_path)
        self.assertEqual(r['enviados'], 0)
        self.assertEqual(r['falhas'], 1)
        self.assertIn('boom', r['erro'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
