"""RAG lexical: TF-IDF e cosseno, sem treino supervisionado ou embeddings externos."""
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

STOPWORDS = set('a o os as de da do das dos e em no na nos nas um uma para por com '
                'que qual quais como este esta deste desta esse essa se ao ou meu minha '
                'sobre tem ser sao foi mais'.split())


def tokens(texto: str) -> list[str]:
    normal = unicodedata.normalize('NFKD', texto.lower())
    normal = ''.join(c for c in normal if not unicodedata.combining(c))
    return [t for t in re.findall(r'[a-z0-9]+', normal) if len(t) > 2 and t not in STOPWORDS]


class Recuperador:
    def __init__(self, arquivo: Path):
        self.documentos = json.loads(arquivo.read_text(encoding='utf-8'))
        contagens = [Counter(tokens(d['titulo'] + ' ' + d['texto'])) for d in self.documentos]
        vocabulario = set().union(*(set(c) for c in contagens))
        self.idf = {t: math.log((1 + len(contagens)) / (1 + sum(t in c for c in contagens))) + 1
                    for t in vocabulario}
        self.vetores = [self.vetor(c) for c in contagens]

    def vetor(self, contagem):
        v = {t: (1 + math.log(n)) * self.idf[t] for t, n in contagem.items() if t in self.idf}
        norma = math.sqrt(sum(x*x for x in v.values())) or 1
        return {t: x / norma for t, x in v.items()}

    def buscar(self, pergunta: str, limite: int = 3):
        consulta = self.vetor(Counter(tokens(pergunta)))
        resultados = []
        for doc, vetor in zip(self.documentos, self.vetores):
            score = sum(valor * vetor.get(t, 0) for t, valor in consulta.items())
            if score >= 0.12:
                resultados.append({'id': doc['id'], 'titulo': doc['titulo'], 'origem': doc['origem'],
                                   'trecho': doc['texto'], 'similaridade': round(score, 4)})
        return sorted(resultados, key=lambda d: (-d['similaridade'], d['id']))[:limite]
