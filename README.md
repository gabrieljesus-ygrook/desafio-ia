# Desafio Técnico — Estágio em Engenharia de Inteligência Artificial

Solução para o desafio de triagem de operações financeiras, separando cálculos determinísticos de interpretação por modelo de linguagem.

## Status

- Nível 1: Parte A e Parte B implementadas e executadas.
- Nível 2: não iniciado.
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
