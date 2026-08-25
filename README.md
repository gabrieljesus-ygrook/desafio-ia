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

Instale as dependências Python:

```bash
pip install -r requirements.txt
```

O Nível 1 usa Gemini e precisa de `GEMINI_API_KEY` no `.env` local. O Nível 2 foi executado com Qwen3 via Ollama:

```bash
ollama pull qwen3
```

Execute os passos do Nível 2 a partir da raiz do repositório:

```bash
python -m nivel_2.pipeline
python -m nivel_2.lote
python -m nivel_2.confronto
```

O lote local pode levar alguns minutos, dependendo do hardware. Nenhuma chave deve ser commitada; o arquivo `.env` está ignorado pelo Git.

## Escopo atual

Os resultados executados ficam commitados no notebook do Nível 1 e em `outputs/`, conforme exigido pelo desafio.

Na Parte A do Nível 2, a pipeline em `nivel_2/pipeline.py` reaplica a limpeza e as duas regras no dataset maior. O ranking organizado é salvo em `outputs/nivel_2_top10_clientes_organizado.csv`.

O lote processou os dez clientes do ranking com parecer estruturado, registrando tokens, latência e custo. Como o modelo foi executado localmente, o custo de API foi zero. No confronto final, regras e modelo concordaram em 9 de 10 clientes (90%). A divergência foi analisada em `outputs/nivel_2_confronto.md`.
