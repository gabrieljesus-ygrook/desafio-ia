# Desafio Técnico — Estágio em Engenharia de Inteligência Artificial

Solução para o desafio de triagem de operações financeiras, separando cálculos determinísticos de interpretação por modelo de linguagem.

## Status

- Nível 1: Parte A e Parte B implementadas e executadas.
- Nível 2: Parte A implementada e executada.
- Nível 2: Parte B implementada e testada com Gemini e Qwen3 via Ollama.
- Nível 2: execução em lote e confronto implementados e executados.
- Nível 3: ainda não iniciado.

## Estrutura

- `dados/`: datasets fornecidos no desafio.
- `nivel_1/`: notebook de limpeza, regras, validação e análise com LLM.
- `nivel_2/`: regras em escala, ferramentas, agente e confronto.
- `nivel_3/`: trilha opcional, caso seja implementada.
- `outputs/`: resultados gerados pelas execuções.
- `docs/`: decisões técnicas e registro do uso de IA.

## Como executar

Instale as dependências:

```bash
pip install -r requirements.txt
```

Nenhuma chave de API deve ser commitada. Copie `.env.example` para `.env` e preencha apenas localmente.

## Escopo atual

Os resultados executados ficam commitados no notebook do Nível 1 e em `outputs/`, conforme exigido pelo desafio.

Na Parte A do Nível 2, a pipeline em `nivel_2/pipeline.py` reaplica a limpeza e as duas regras no dataset maior. O ranking organizado é salvo em `outputs/nivel_2_top10_clientes_organizado.csv`.
