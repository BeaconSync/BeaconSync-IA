# Contrato proposto v0.1 — alinhar antes de integrar

Não representa endpoints existentes em Java/.NET. O serviço Python recebe um recorte pronto; nenhuma URL de backend é chamada por ele nesta versão.

## Requisição

`POST /ia/analisar-distrito`

Headers: `Content-Type: application/json`, `X-API-Key: <segredo de servidor>`.

Corpo: `exemplos/distrito.json`. Todos os campos são obrigatórios, exceto `pergunta` (possui pergunta padrão). Campos adicionais são rejeitados. Quantidades devem ser inteiros entre 0 e 1.000.000; não aceita negativos, booleanos, texto ou frações.

| Campo | Significado |
|---|---|
| `alerta_id` | ID estável do alerta que define o recorte |
| `distrito_id` | ID usado também pelo backend e pelo GeoJSON |
| `distrito_nome` | Nome público da região, sem dados de pessoas |
| `atualizado_em` | ISO 8601 com fuso; instante dos dados, não da geração |
| `situacoes.precisa_ajuda` | Pessoas que precisam de ajuda |
| `situacoes.sem_contato` | Responsável informou que não conseguiu contato |
| `situacoes.pendente_confirmacao` | Nenhuma confirmação recebida |
| `situacoes.segura` | Seguras por confirmação, fora da categoria resgatada |
| `situacoes.resgatada` | Resgate concluído; não contar novamente em segura |
| `pergunta` | Pergunta de 5 a 500 caracteres, sem dados pessoais |

O backend deve agrupar pessoas únicas pelo endereço atual, dentro do alerta, e atribuir uma única situação. Se seus enums atuais diferirem, um adaptador deve convertê-los; não mudar banco ou enums sem alinhamento. Resgates em andamento são outra dimensão e não entram como sexta situação no contrato inicial.

`total_acompanhamento = precisa_ajuda + sem_contato + pendente_confirmacao`.

`total_cadastrado = soma das cinco situações`.

## Resposta

`200`: inclui `id_analise`, `modo`, `status`, `modelo`, IDs do recorte, timestamps, totais, `boletim_dados`, `analise`, `fontes_recuperadas` e `avisos`.

- `DEMONSTRACAO`: resposta determinística, sem IA generativa.
- `GERADO`: explicação recebida do modelo; conferir qualidade.
- `SEM_BASE`: não houve recuperação acima do limiar; modelo não é chamado.
- Similaridade das fontes é uma medida lexical, não confiança da IA nem probabilidade de correção.

| Erro | Significado |
|---|---|
| 401 | Chave do serviço ausente/incorreta |
| 422 | Entrada inválida |
| 502 | Erro externo ou resposta vazia/incompleta/bloqueada |
| 503 | Falha de conexão, cota ou configuração do provedor |
| 504 | Timeout do provedor |

## Decisões pendentes para a equipe

1. Quem mantém o endpoint do mapa e agrega as cinco situações: Java ou .NET?
2. Qual município/GeoJSON e IDs oficiais serão usados? A IA não faz geocodificação.
3. Quais são as faixas finais de cores? Não confundir ausência de dados com zero.
4. Como o backend autentica usuários, autoriza órgão/área e resolve conflitos entre responsáveis?
5. Como serão detectadas alterações para atualizar mapa e análise? Exibir timestamps; evitar análise antiga sobre mapa novo.

O mobile deve manter mapa e análise independentes. Em falha da IA, mostrar mensagem na área de análise e preservar as contagens. Não reutilizar uma análise de outro alerta ou distrito. Não embutir `SERVICE_API_KEY` no aplicativo.
