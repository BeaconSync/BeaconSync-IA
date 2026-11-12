import copy
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app import provider
from app.schemas import AnaliseEntrada
from main import app

ROOT = Path(__file__).resolve().parents[1]
KEY = 'teste-local-chave-com-mais-de-32-caracteres'


def exemplo():
    dado = json.loads((ROOT / 'exemplos/distrito.json').read_text(encoding='utf-8'))
    dado['atualizado_em'] = datetime.now(timezone.utc).isoformat()
    return dado


class APITests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'SERVICE_API_KEY': KEY, 'IA_MODO': 'demonstracao'})
        self.env.start()
        self.client = TestClient(app).__enter__()
        self.headers = {'X-API-Key': KEY}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()

    def post(self, data=None):
        return self.client.post('/ia/analisar-distrito', json=data or exemplo(), headers=self.headers)

    def test_health_nao_revela_chave(self):
        r = self.client.get('/health')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(KEY, r.text)

    def test_exige_autenticacao(self):
        for headers in ({}, {'X-API-Key': 'incorreta'}):
            self.assertEqual(self.client.post('/ia/analisar-distrito', json=exemplo(), headers=headers).status_code, 401)

    def test_contagem_e_demonstracao_explicita(self):
        r = self.post()
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body['total_acompanhamento'], 18)
        self.assertEqual(body['total_cadastrado'], 24)
        self.assertEqual(body['status'], 'DEMONSTRACAO')
        self.assertIsNone(body['modelo'])
        self.assertIn('BS-01', [f['id'] for f in body['fontes_recuperadas']])

    def test_dados_invalidos(self):
        for value in (-1, 1.5, True, '10', 1_000_001):
            with self.subTest(value=value):
                data = exemplo()
                data['situacoes']['precisa_ajuda'] = value
                self.assertEqual(self.post(data).status_code, 422)

    def test_campo_pessoal_extra_rejeitado_sem_refletir_valor(self):
        data = exemplo()
        data['cpf'] = 'VALOR-PESSOAL-NAO-REFLETIR'
        response = self.post(data)
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(data['cpf'], response.text)

    def test_data_exige_fuso_e_rejeita_futuro(self):
        for value in ('2026-11-12T12:00:00', (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()):
            data = exemplo()
            data['atualizado_em'] = value
            self.assertEqual(self.post(data).status_code, 422)

    def test_sem_base_nao_chama_provedor(self):
        data = exemplo()
        data['pergunta'] = 'Receita culinaria de bolo chocolate'
        with patch('main.provider.gerar', new_callable=AsyncMock) as generate:
            result = self.post(data).json()
            self.assertEqual(result['status'], 'SEM_BASE')
            generate.assert_not_awaited()

    def test_aviso_dados_antigos(self):
        data = exemplo()
        data['atualizado_em'] = (datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
        self.assertTrue(any('15 minutos' in a for a in self.post(data).json()['avisos']))

    def test_fluxo_gemini_com_provedor_simulado(self):
        with patch.dict(os.environ, {'IA_MODO': 'gemini', 'GEMINI_API_KEY': 'fake', 'GEMINI_MODEL': 'modelo-teste'}):
            with patch('main.provider.gerar', new_callable=AsyncMock, return_value='Explicacao [BS-01]') as generate:
                body = self.post().json()
                self.assertEqual(body['status'], 'GERADO')
                self.assertEqual(body['modelo'], 'modelo-teste')
                generate.assert_awaited_once()

    def test_falha_provedor_nao_vira_sucesso_falso(self):
        with patch.dict(os.environ, {'IA_MODO': 'gemini'}):
            with patch('main.provider.gerar', new_callable=AsyncMock,
                       side_effect=provider.ProvedorErro(503, 'Cota indisponivel')):
                self.assertEqual(self.post().status_code, 503)

    def test_swagger_expoe_autenticacao(self):
        schema = self.client.get('/openapi.json').json()
        self.assertEqual(schema['components']['securitySchemes']['APIKeyHeader']['name'], 'X-API-Key')


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def call(self, handler):
        original = httpx.AsyncClient
        client = original(transport=httpx.MockTransport(handler))
        with patch('app.provider.httpx.AsyncClient', return_value=client):
            return await provider.gerar(AnaliseEntrada(**exemplo()), [], 'chave-fake', 'modelo-teste')

    async def test_formato_rest_e_resposta(self):
        def handler(request):
            self.assertTrue(str(request.url).endswith('/modelo-teste:generateContent'))
            self.assertEqual(request.headers['x-goog-api-key'], 'chave-fake')
            self.assertIn('systemInstruction', json.loads(request.content))
            return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {
                'parts': [{'text': 'interno', 'thought': True}, {'text': 'Resposta [BS-01]'}]}}]})
        self.assertEqual(await self.call(handler), 'Resposta [BS-01]')

    async def test_erros_http_sem_expor_corpo(self):
        for code, expected in [(429, 503), (401, 503), (404, 503), (500, 502)]:
            with self.subTest(code=code), self.assertRaises(provider.ProvedorErro) as ctx:
                await self.call(lambda req: httpx.Response(code, text='segredo-provedor'))
            self.assertEqual(ctx.exception.status, expected)
            self.assertNotIn('segredo-provedor', ctx.exception.mensagem)

    async def test_timeout(self):
        def handler(request):
            raise httpx.ReadTimeout('timeout', request=request)
        with self.assertRaises(provider.ProvedorErro) as ctx:
            await self.call(handler)
        self.assertEqual(ctx.exception.status, 504)

    async def test_resposta_vazia_ou_truncada(self):
        for body in ({}, {'candidates': [{'finishReason': 'MAX_TOKENS'}]}):
            with self.assertRaises(provider.ProvedorErro) as ctx:
                await self.call(lambda req: httpx.Response(200, json=body))
            self.assertEqual(ctx.exception.status, 502)


if __name__ == '__main__':
    unittest.main()
