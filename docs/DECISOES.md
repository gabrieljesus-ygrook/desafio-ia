# Decisoes tecnicas

## 1. Separar calculo de interpretacao

Escolhi manter limpeza, conversao cambial, agregacoes, medianas e regras em Python/pandas. A alternativa seria deixar a LLM calcular os indicadores a partir dos registros, mas isso dificultaria a reproducao e abriria espaco para aritmetica inconsistente. A LLM recebe fatos calculados e interpreta risco, tipologia e justificativa.

Essa separacao nao elimina o risco de uma interpretacao ruim. Por isso, o parecer e validado por schema e os fatos usados na analise ficam rastreaveis.

## 2. Qualidade e chave de deduplicacao

O `id` foi tratado como chave unica porque o enunciado e a inspecao dos dados indicam que ele identifica o registro. A alternativa seria deduplicar pela combinacao de todos os campos, mas isso manteria duas versoes da mesma operacao quando algum campo divergisse. Em dados reais, nao escolheria silenciosamente a primeira versao: enviaria conflitos de mesmo `id` para uma fila de inconsistencias.

Datas invalidas sao preservadas no volume geral e excluidas apenas de regras que dependem de data. A taxa USD/BRL fornecida no arquivo e usada como referencia fixa. Em producao, eu versionaria a fonte da cotacao e a data de referencia.

## 3. Regras em escala e ranking

As regras do Nivel 1 foram extraidas para `nivel_2/pipeline.py` para evitar uma segunda implementacao. O ranking prioriza quantidade de sinalizacoes e usa volume em BRL como desempate. Essa ordenacao e simples e auditavel, mas nao representa um modelo estatistico de priorizacao. Com dados reais, eu validaria o ranking com casos revisados por especialistas e mediria falsos positivos e falsos negativos.

## 4. Tools e agente

As tres tools fazem consultas deterministicas sobre a base tratada. O modelo recebe as declaracoes, mas decide se precisa de historico, operacoes de um dia ou perfil de canal. Chamar todas sempre seria previsivel, porem deixaria de ser um agente e aumentaria latencia e custo.

O loop aceita varias rodadas, limita rodadas e chamadas e registra as ferramentas escolhidas. A alternativa seria usar um framework de agentes; escolhi a API HTTP direta para deixar visivel o protocolo de tool calling e reduzir dependencias. O custo e que o controle de mensagens, erros e compatibilidade com cada provedor fica sob responsabilidade do projeto.

## 5. Gemini e Qwen3/Ollama

O Gemini foi usado nas analises do Nivel 1 e nos primeiros testes do agente. O Qwen3 via Ollama foi escolhido para a execucao local e em lote porque elimina chave externa, custo de API e limite diario. Em troca, a inferencia local e mais lenta e a qualidade da selecao de tools pode variar conforme o hardware e o modelo baixado. A camada de comunicacao foi isolada para permitir trocar o provedor sem alterar as regras ou as tools.

## 6. Saida, cache e observabilidade

O parecer usa schema Pydantic com `nivel_risco`, `tipologia_suspeita`, `red_flags` e `justificativa`. Tokens, latencia, rodadas e tools chamadas sao registrados quando o provedor informa essas metricas. O cache atual e em memoria e evita repetir a mesma analise durante o processo; ele nao e persistente nem substitui uma trilha de auditoria.

## Limitacoes conhecidas

- Os limiares das regras sao fixos e nao foram calibrados com casos rotulados.
- A base e carregada em memoria e nao existe controle de concorrencia ou versionamento dos dados.
- O cache e perdido ao encerrar o processo.
- O Qwen3 local pode levar bastante tempo por cliente e pode produzir um parecer diferente do Gemini.
- O lote registra erros de API ou de inferencia, mas ainda nao possui retomada por checkpoint de cada cliente.
- O confronto automatico entre flags deterministicas e pareceres do modelo ainda nao foi implementado.
- Nao existem autenticacao, controle de acesso, armazenamento seguro de auditoria ou monitoramento de producao.

## O que faria com mais tempo

### Confronto entre regras e pareceres

Criaria `nivel_2/confronto.py` para juntar o ranking, as flags por cliente e os pareceres do lote. Calcularia com pandas uma tabela de concordancia, divergencia e clientes sem parecer. Validaria com casos positivos e negativos revisados manualmente, verificando se toda divergencia possui justificativa baseada nos fatos.

### Lote resiliente

Persistiria cada cliente assim que terminasse, com status, tentativa, erro e timestamp. O executor leria o arquivo existente e retomaria apenas clientes pendentes. Validaria interrompendo a execucao no meio e confirmando que a retomada nao duplica registros.

### Avaliacao dos modelos

Manteria Gemini e Qwen3 atras de uma interface comum e executaria ambos sobre os mesmos clientes. Compararia validade do schema, latencia, uso de tools, concordancia com as regras e revisao humana. Isso permitiria escolher o modelo por evidencias, nao apenas por custo.

### Dados reais e governanca

Substituiria a taxa fixa por uma fonte versionada, adicionaria testes de contrato do esquema, fila de inconsistencias e armazenamento de auditoria. Validaria reprocessamento idempotente, permissao de acesso e rastreabilidade da versao dos dados, regras e modelo usados em cada parecer.

### Nivel 3

Antes de escolher uma trilha, faria uma prova de conceito pequena e mensuravel. Para uma trilha de RAG, por exemplo, indexaria normas ou procedimentos versionados, recuperaria trechos com metadados e exigiria citacoes no parecer. Validaria a qualidade da recuperacao com perguntas conhecidas e revisao das fontes, sem misturar o calculo transacional com o contexto documental.
