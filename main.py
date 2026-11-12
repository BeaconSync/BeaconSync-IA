import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from app import provider
from app.rag import Recuperador
from app.schemas import AnaliseEntrada, AnaliseSaida

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')


@asynccontextmanager
async def lifespan(app):
    if len(os.getenv('SERVICE_API_KEY', '')) < 32:
        raise RuntimeError('Execute python configurar.py ou configure SERVICE_API_KEY com pelo menos 32 caracteres.')
    modo = os.getenv('IA_MODO', 'demonstracao')
    if modo not in ('demonstracao', 'gemini'):
        raise RuntimeError('IA_MODO deve ser demonstracao ou gemini.')
    if modo == 'gemini' and (not os.getenv('GEMINI_API_KEY') or not os.getenv('GEMINI_MODEL')):
        raise RuntimeError('Modo gemini exige GEMINI_API_KEY e GEMINI_MODEL.')
    app.state.recuperador = Recuperador(ROOT / 'dados' / 'base_conhecimento.json')
    yield


app = FastAPI(title='BeaconSync IA', version='0.1.0', lifespan=lifespan,
              description='Prototipo academico: boletim deterministico + RAG lexical + Gemini opcional.')
api_key = APIKeyHeader(name='X-API-Key', auto_error=False)


def autenticar(chave: str | None = Security(api_key)):
    esperada = os.getenv('SERVICE_API_KEY', '')
    if not esperada or not chave or not secrets.compare_digest(chave.encode(), esperada.encode()):
        raise HTTPException(401, 'Chave de servico invalida ou ausente.')


@app.exception_handler(RequestValidationError)
async def validacao_sem_dados_pessoais(request, exc):
    # Nao replica valores fornecidos no corpo na resposta de validacao.
    erros = [{'loc': e['loc'], 'msg': e['msg'], 'type': e['type']} for e in exc.errors()]
    return JSONResponse(status_code=422, content={'detail': erros})


@app.get('/health')
def health():
    return {'status': 'ok', 'servico': 'beacon-sync-ia', 'modo': os.getenv('IA_MODO', 'demonstracao')}


@app.post('/ia/analisar-distrito', response_model=AnaliseSaida, dependencies=[Depends(autenticar)])
async def analisar(entrada: AnaliseEntrada):
    situacao = entrada.situacoes
    total = sum(situacao.model_dump().values())
    acompanhamento = situacao.precisa_ajuda + situacao.sem_contato + situacao.pendente_confirmacao
    boletim = (f'{entrada.distrito_nome}: {acompanhamento} pessoas em acompanhamento; '
               f'{situacao.precisa_ajuda} precisam de ajuda, {situacao.sem_contato} sem contato e '
               f'{situacao.pendente_confirmacao} com confirmacao pendente. '
               f'{situacao.segura} confirmadas seguras e {situacao.resgatada} resgatadas. '
               f'Total cadastrado neste recorte: {total}.')
    fontes = app.state.recuperador.buscar(entrada.pergunta)
    modo = os.getenv('IA_MODO', 'demonstracao')
    modelo = None
    avisos = ['Prototipo academico; a decisao operacional pertence ao agente autorizado.',
              'Contagens recebidas do backend; este servico nao verifica pessoas no banco.',
              'Fontes recuperadas nao garantem que toda afirmacao gerada esteja correta.']
    if (datetime.now(timezone.utc) - entrada.atualizado_em).total_seconds() > 900:
        avisos.append('Dados com mais de 15 minutos; consulte a atualizacao no backend. Limiar experimental.')
    if not fontes:
        status = 'SEM_BASE'
        analise = 'A base de conhecimento nao encontrou trechos para responder a essa pergunta.'
    elif modo == 'demonstracao':
        status = 'DEMONSTRACAO'
        analise = 'SIMULACAO SEM IA GENERATIVA. Trechos recuperados:\n' + '\n'.join(
            f"[{f['id']}] {f['trecho']}" for f in fontes)
    else:
        try:
            analise = await provider.gerar(entrada, fontes, os.getenv('GEMINI_API_KEY', ''),
                                         os.getenv('GEMINI_MODEL', ''))
        except provider.ProvedorErro as erro:
            raise HTTPException(erro.status, erro.mensagem) from None
        status, modelo = 'GERADO', os.getenv('GEMINI_MODEL')
    if modo == 'demonstracao':
        avisos.append('Modo demonstracao nao comprova o requisito de IA generativa.')
    return AnaliseSaida(id_analise=str(uuid4()), modo=modo, status=status, modelo=modelo,
                       alerta_id=entrada.alerta_id, distrito_id=entrada.distrito_id,
                       dados_atualizados_em=entrada.atualizado_em, gerado_em=datetime.now(timezone.utc),
                       total_cadastrado=total, total_acompanhamento=acompanhamento,
                       boletim_dados=boletim, analise=analise, fontes_recuperadas=fontes, avisos=avisos)
