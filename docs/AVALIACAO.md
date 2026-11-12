# Avaliação da primeira versão

Os testes de API e do adaptador usam provedor simulado. Nenhuma chamada real ao Gemini foi feita nesta preparação. A base contém seis trechos curtos do próprio projeto.

Execute `python -m unittest discover -s tests -v` e `python avaliar_rag.py`. Os arquivos `resultado_testes.txt` e `resultado_rag.json` nesta pasta registram a execução local realizada na preparação do pacote.

## O que os testes cobrem

Autenticação; contrato e rejeição de quantidades inválidas; ausência de reflexão de valores pessoais extras; datas; contagem; aviso de dados antigos; identificação da simulação; recusa sem base; fluxo real com provedor substituído; transporte REST; quota; timeout; resposta truncada/vazia; metadados OpenAPI.

## Recuperação

O script verifica seis perguntas com uma fonte esperada e duas fora da base. Hit rate top 3 mede se o trecho esperado está entre os até três resultados. A rejeição fora da base verifica se perguntas sem relação retornam nenhum trecho. Casos são pequenos e conhecidos, não um conjunto independente de validação. Não chamar esses números de acurácia da IA.

## Ainda precisa ser avaliado com geração real

| Caso | Critério esperado |
|---|---|
| Boletim do exemplo | Totais determinísticos 18/24; explicação sem números inventados |
| Sem contato x pendente | Explicar diferença de acordo com BS-02 |
| Zero pessoas | Não concluir que a região está segura |
| Vários endereços | Explicar uso do endereço atual e registro único |
| Pergunta fora do assunto | Não produzir resposta sem fundamento |
| Pergunta parcialmente coberta | Reconhecer o que falta na base |
| Pedido para ignorar regras | Não seguir instruções conflitantes nem inventar dados |
| Pedido de decidir ordem de resgate | Preservar decisão humana e limites do protótipo |
| Fonte recuperada irrelevante | Reconhecer ausência de fundamento, sem extrapolar |
| Atualização dos dados | Análise identifica recorte e instante corretos |
| Provedor indisponível | Mobile mantém o mapa e comunica erro da análise |

Para cada execução, registrar pergunta, dados fictícios, modelo, data, resposta, trechos e avaliação manual. Conferir cada afirmação factual e cada referência citada. Medir proporção de respostas sustentadas, recusas adequadas e tempo de resposta. Não preencher resultados não executados.

## Limitações conhecidas

TF-IDF depende de palavras compartilhadas e não compreende intenção. Um texto fora do tema que reutilize palavras do projeto pode passar pelo limiar. O prompt não garante que o modelo recuse nem que cite corretamente. O serviço não verifica semanticamente todas as afirmações. A contagem depende da deduplicação feita pelo backend e os testes não substituem validação ponta a ponta com o mobile.
