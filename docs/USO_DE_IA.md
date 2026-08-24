# Uso de IA

## Uso de IA no Nivel 2

- O Codex apoiou a implementacao das ferramentas deterministicas e do agente com function calling.
- As ferramentas `historico_cliente`, `operacoes_do_dia` e `perfil_canal` consultam a base tratada e realizam os calculos em Python/pandas, sem uso de LLM.
- O Gemini recebe essas ferramentas como opcoes e decide quais consultar conforme o contexto do cliente. O agente nao chama todas automaticamente e pode realizar mais de uma rodada de tool calling.
- O agente possui limites de rodadas e de chamadas para evitar loops. A resposta final e validada pelo modelo Pydantic `Parecer`.
- O resultado registra as ferramentas escolhidas, rodadas, tokens e latencia quando essas metricas sao retornadas pela API.
- O cache atual reutiliza, durante a execucao do processo, o resultado para o mesmo cliente e os mesmos parametros. Ele e mantido em memoria.
- A validacao manual confirmou a selecao dinamica de ferramentas em tres rodadas para o cliente `CLI-014`.

Este documento registra como ferramentas de IA foram utilizadas no desenvolvimento, conforme solicitado pelo desafio.

## Ferramentas utilizadas

- ChatGPT/Codex: leitura e organização do enunciado, planejamento da estrutura do repositório, apoio na implementação e revisão de código/documentação.
- Gemini (`gemini-3.6-flash`): geração de pareceres interpretativos a partir dos fatos calculados pela pipeline determinística. A chamada foi feita via API HTTP, com a chave carregada do `.env` local.

## Princípios adotados

- Cálculos, agregações, medianas, contagens e comparação com limites são realizados em Python/pandas.
- A LLM é usada para interpretação e redação do parecer, não para substituir regras numéricas.
- A resposta foi solicitada em JSON e validada com Pydantic; respostas malformadas são capturadas como falha de validação.
- Chaves e credenciais permanecem apenas em variáveis de ambiente locais.

## Revisão humana

Todo código sugerido por IA será revisado, executado e compreendido antes da entrega. Eventuais erros ou sugestões descartadas serão registrados aqui durante o desenvolvimento.

## Observações da execução

- O modelo inicialmente configurado (`gemini-2.5-flash-lite`) retornou indisponibilidade para novos usuários. A lista de modelos disponível para a chave indicou `gemini-3.6-flash`, que foi usado na execução real.
- O Prompt V1 retornou risco alto, enquanto o Prompt V2 retornou risco médio e apresentou uma justificativa mais cuidadosa sobre a diferença entre indício e prova. Isso reforça a decisão de usar instruções explícitas e registrar limitações no Prompt V2.
- A chamada Gemini possui até três tentativas, com espera progressiva para erros temporários, limites de requisição e respostas malformadas. Na última execução, o Prompt V1 precisou de duas tentativas e o Prompt V2 foi aceito na primeira.
