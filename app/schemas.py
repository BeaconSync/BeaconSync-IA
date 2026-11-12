from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

Quantidade = Annotated[int, Field(strict=True, ge=0, le=1_000_000)]


class Estrito(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Situacoes(Estrito):
    precisa_ajuda: Quantidade
    sem_contato: Quantidade
    pendente_confirmacao: Quantidade
    segura: Quantidade
    resgatada: Quantidade


class AnaliseEntrada(Estrito):
    alerta_id: str = Field(min_length=1, max_length=80)
    distrito_id: str = Field(min_length=1, max_length=80)
    distrito_nome: str = Field(min_length=1, max_length=100)
    atualizado_em: AwareDatetime
    situacoes: Situacoes
    pergunta: str = Field(default='Como interpretar a situacao e a contagem deste distrito?',
                          min_length=5, max_length=500)

    @field_validator('atualizado_em')
    @classmethod
    def nao_aceitar_futuro(cls, valor):
        from datetime import timedelta, timezone
        if valor > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError('atualizado_em nao pode estar no futuro')
        return valor


class Fonte(Estrito):
    id: str
    titulo: str
    origem: str
    trecho: str
    similaridade: float


class AnaliseSaida(Estrito):
    id_analise: str
    modo: Literal['demonstracao', 'gemini']
    status: Literal['DEMONSTRACAO', 'GERADO', 'SEM_BASE']
    modelo: str | None
    alerta_id: str
    distrito_id: str
    dados_atualizados_em: AwareDatetime
    gerado_em: AwareDatetime
    total_cadastrado: int
    total_acompanhamento: int
    boletim_dados: str
    analise: str
    fontes_recuperadas: list[Fonte]
    avisos: list[str]
