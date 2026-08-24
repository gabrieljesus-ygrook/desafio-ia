# Decisões técnicas

## Estado inicial

O projeto começa com uma pipeline em Python, usando pandas para tratamento e regras determinísticas. A interpretação textual será isolada em uma camada de LLM com saída estruturada e validação.

## Qualidade dos dados

No Nível 1 foram encontrados 20 registros brutos, uma repetição de `OP-0007`, uma operação sem data (`OP-0017`) e uma operação em USD. A análise do esquema indicou que `id` é a chave única de cada registro. Por isso, a filtragem de duplicidade é feita exclusivamente por `id`, mantendo a primeira ocorrência e descartando ocorrências posteriores com a mesma chave, independentemente dos demais campos. A operação sem data foi preservada para não perder volume financeiro e excluída apenas de agrupamentos que dependem de data, e o USD foi convertido pela taxa fixa fornecida no arquivo.

Essa escolha evita contar duas vezes uma mesma operação. Em um cenário real, se registros com o mesmo `id` apresentassem campos divergentes, o ideal seria encaminhá-los para uma fila de inconsistências e investigar a origem, em vez de escolher silenciosamente uma versão.

Não foram encontrados campos ausentes, valores nulos ou valores não positivos.

## Separação entre regras e LLM

Operações matemáticas e decisões baseadas em limites ficarão no código. A LLM receberá fatos já calculados e será solicitada a explicar tipologias, sinais de alerta e justificativa.

## Regra 1

A validação compara o caso positivo de `CLI-A-1` em 2026-03-09, com três operações somando R$ 54.200,00, contra o caso parecido de `CLI-A-3`, que soma R$ 48.500,00 e fica abaixo do limite. A regra sinaliza somente o primeiro caso.

## Nível 2 — Parte A

A limpeza e as regras foram colocadas em `nivel_2/pipeline.py` para que o fluxo completo possa ser executado pelo `main`, sem depender de chamadas manuais de cada função. O ranking ordena primeiro pelo total de sinalizações e usa o volume total em BRL como desempate.

Na base maior, foram carregados 322 registros, reduzidos para 317 após a deduplicação por `id`. A Regra 1 sinalizou 16 operações e a Regra 2 sinalizou 21 operações. O resultado foi salvo em CSV com separador `;` e decimal `,` para abrir corretamente em planilhas configuradas para o padrão brasileiro.

## Nível 2 — Parte B

As ferramentas usam a mesma base tratada da Parte A e não fazem chamadas de LLM. O agente recebe as flags determinísticas e as declarações das três ferramentas, mas o modelo decide quais consultas são necessárias. O loop aceita múltiplas rodadas, registra as ferramentas chamadas e possui limites de rodadas e de chamadas para evitar ciclos.

No teste com `CLI-014`, o agente fez cinco chamadas em três rodadas: uma consulta de histórico, três consultas por data e uma consulta de perfil por canal. O parecer final foi validado com Pydantic e os tokens e a latência foram registrados.

## Itens ainda não implementados

O Nível 2 ainda precisa da execução em lote e do confronto entre regras e modelo. O Nível 3 será avaliado após a conclusão dos requisitos obrigatórios.
