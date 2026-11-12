"""Avaliacao pequena de recuperacao; NAO mede qualidade da geracao do Gemini."""
import json
from pathlib import Path
from app.rag import Recuperador

ROOT = Path(__file__).resolve().parent
casos = [
    ('Como funciona a contagem de pessoas no distrito?', 'BS-01'),
    ('O que significa sem contato e pendente de confirmacao?', 'BS-02'),
    ('Como evitar duplicidade com varios enderecos?', 'BS-03'),
    ('Zero cadastros significa ausencia de perigo?', 'BS-04'),
    ('Quem toma a decisao de atendimento?', 'BS-05'),
    ('Posso enviar nomes contatos e enderecos individuais?', 'BS-06'),
    ('Receita culinaria de bolo chocolate', None),
    ('Programacao futebol campeonato brasileiro', None),
]
rag = Recuperador(ROOT / 'dados/base_conhecimento.json')
resultados = []
for pergunta, esperado in casos:
    encontrados = [r['id'] for r in rag.buscar(pergunta)]
    passou = esperado in encontrados if esperado else not encontrados
    resultados.append(dict(pergunta=pergunta, fonte_esperada=esperado,
                           fontes_recuperadas=encontrados, passou=passou))
positivos = [r for r in resultados if r['fonte_esperada']]
negativos = [r for r in resultados if not r['fonte_esperada']]
relatorio = {
    'tipo': 'Teste lexical local; exemplos pequenos e conhecidos, sem geracao real.',
    'hit_rate_top3': sum(r['passou'] for r in positivos) / len(positivos),
    'rejeicao_fora_de_base': sum(r['passou'] for r in negativos) / len(negativos),
    'casos': resultados,
    'limitacao': 'Nao representa acuracia da IA, seguranca operacional nem generalizacao.'
}
print(json.dumps(relatorio, ensure_ascii=False, indent=2))
