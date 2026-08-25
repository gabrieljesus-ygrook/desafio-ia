# Uso de IA

- **Codex/ChatGPT:** ajudou a interpretar o enunciado, estruturar o projeto, revisar o codigo e discutir trade-offs. Todo codigo foi revisado e executado localmente.
- **Gemini (`gemini-3.6-flash`):** usado nas analises do Nivel 1 e nos primeiros testes do agente via API.
- **Qwen3 (`qwen3:latest`) via Ollama:** usado na execucao local do agente e preparado para o processamento em lote, sem chave externa.

Um ponto corrigido durante o desenvolvimento foi a tentativa de manter imports com fallback para executar arquivos isoladamente. Isso escondia a forma correta de executar o projeto como pacote e foi removido; os comandos agora partem da raiz e usam `python -m nivel_2.lote`. Tambem foi identificado que o Gemini atingiu limite HTTP 429 durante o lote, motivando a validacao local com Ollama.

Os calculos permanecem em Python/pandas. A IA interpreta fatos ja calculados, escolhe tools quando necessario e produz o parecer estruturado; ela nao define os limiares nem faz as agregacoes.
