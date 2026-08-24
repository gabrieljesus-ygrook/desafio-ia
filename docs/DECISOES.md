# Decisões técnicas

## Estado inicial

O projeto começa com uma pipeline em Python, usando pandas para tratamento e regras determinísticas. A interpretação textual será isolada em uma camada de LLM com saída estruturada e validação.

## Qualidade dos dados

Os datasets serão analisados antes da aplicação das regras. Duplicidades, datas ausentes, moedas diferentes e demais inconsistências serão documentadas com evidências no notebook e tratadas de maneira explícita.

## Separação entre regras e LLM

Operações matemáticas e decisões baseadas em limites ficarão no código. A LLM receberá fatos já calculados e será solicitada a explicar tipologias, sinais de alerta e justificativa.

## Itens ainda não implementados

Os Níveis 1 e 2 ainda estão em desenvolvimento. O Nível 3 será avaliado somente após a conclusão dos requisitos obrigatórios.

