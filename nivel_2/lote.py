import json
import os
import time
from pathlib import Path

import pandas as pd

from nivel_2.agente import analisar_cliente
from nivel_2.pipeline import executar_parte_a


RAIZ_PROJETO = Path(__file__).parents[1]
ARQUIVO_PARECERES = RAIZ_PROJETO / "outputs" / "nivel_2_pareceres_lote.jsonl"
ARQUIVO_METRICAS = RAIZ_PROJETO / "outputs" / "nivel_2_metricas_lote.csv"
ARQUIVO_RESUMO = RAIZ_PROJETO / "outputs" / "nivel_2_resumo_lote.json"


def obter_clientes_alvo(limite=10):
    """Retorna os clientes mais sinalizados pela mesma regra da Parte A."""
    ranking = executar_parte_a()["ranking"]
    return ranking.head(limite)["cliente_id"].tolist()


def calcular_custo(tokens_entrada, tokens_saida):
    """Estima o custo em USD usando precos configurados no ambiente."""
    if os.getenv("LLM_PROVIDER", "ollama").lower() == "ollama":
        return 0.0
    preco_entrada = float(os.getenv("GEMINI_INPUT_COST_PER_MILLION_USD", "0.75"))
    preco_saida = float(os.getenv("GEMINI_OUTPUT_COST_PER_MILLION_USD", "3.75"))
    return round(
        (tokens_entrada / 1_000_000) * preco_entrada
        + (tokens_saida / 1_000_000) * preco_saida,
        8,
    )


def executar_lote(clientes=None):
    """Executa o agente para cada cliente e devolve pareceres e metricas."""
    clientes = clientes or obter_clientes_alvo()
    analisar_cliente.cache_clear()
    pareceres = []
    metricas = []

    intervalo_segundos = float(os.getenv("LOTE_INTERVALO_SEGUNDOS", "5"))
    for indice, cliente_id in enumerate(clientes):
        print(f"Processando {indice + 1}/{len(clientes)}: {cliente_id}", flush=True)
        try:
            resultado = analisar_cliente(cliente_id)
        except Exception as erro:
            resultado = {
                "valido": False,
                "parecer": None,
                "erro": f"{type(erro).__name__}: {erro}",
                "cliente_id": cliente_id,
                "modelo": os.getenv("OLLAMA_MODEL", "qwen3:latest"),
                "rodadas": 0,
                "ferramentas_chamadas": [],
                "tokens_entrada": 0,
                "tokens_saida": 0,
                "tokens_total": 0,
                "latencia_total_ms": 0,
            }

        status = "ok" if resultado.get("valido") else f"erro: {resultado.get('erro')}"
        print(f"Concluido {cliente_id}: {status}", flush=True)

        pareceres.append(resultado)
        parecer = resultado.get("parecer") or {}
        tokens_entrada = resultado.get("tokens_entrada", 0)
        tokens_saida = resultado.get("tokens_saida", 0)
        metricas.append(
            {
                "cliente_id": cliente_id,
                "valido": resultado.get("valido", False),
                "nivel_risco": parecer.get("nivel_risco"),
                "rodadas": resultado.get("rodadas", 0),
                "quantidade_tools": len(resultado.get("ferramentas_chamadas", [])),
                "tokens_entrada": tokens_entrada,
                "tokens_saida": tokens_saida,
                "tokens_total": resultado.get("tokens_total", 0),
                "latencia_total_ms": resultado.get("latencia_total_ms", 0),
                "custo_estimado_usd": calcular_custo(tokens_entrada, tokens_saida),
                "erro": resultado.get("erro"),
            }
        )
        if indice < len(clientes) - 1 and intervalo_segundos > 0:
            time.sleep(intervalo_segundos)

    return pareceres, pd.DataFrame(metricas)


def analisar_metricas(df_metricas):
    """Calcula os totais operacionais do lote com pandas."""
    return {
        "clientes_processados": int(len(df_metricas)),
        "clientes_validos": int(df_metricas["valido"].sum()),
        "clientes_com_erro": int((~df_metricas["valido"]).sum()),
        "tokens_entrada_total": int(df_metricas["tokens_entrada"].sum()),
        "tokens_saida_total": int(df_metricas["tokens_saida"].sum()),
        "tokens_total": int(df_metricas["tokens_total"].sum()),
        "latencia_total_ms": round(float(df_metricas["latencia_total_ms"].sum()), 2),
        "latencia_media_ms": round(float(df_metricas["latencia_total_ms"].mean()), 2),
        "custo_estimado_total_usd": round(float(df_metricas["custo_estimado_usd"].sum()), 8),
        "distribuicao_nivel_risco": df_metricas["nivel_risco"].value_counts(dropna=False).to_dict(),
    }


def salvar_resultados(pareceres, df_metricas, caminho_pareceres=None, caminho_metricas=None):
    """Salva um registro JSON por cliente e as metricas tabulares do lote."""
    arquivo_pareceres = Path(caminho_pareceres or ARQUIVO_PARECERES)
    arquivo_metricas = Path(caminho_metricas or ARQUIVO_METRICAS)
    arquivo_pareceres.parent.mkdir(parents=True, exist_ok=True)

    with arquivo_pareceres.open("w", encoding="utf-8") as arquivo:
        for parecer in pareceres:
            arquivo.write(json.dumps(parecer, ensure_ascii=False) + "\n")

    df_metricas.to_csv(
        arquivo_metricas,
        sep=";",
        decimal=",",
        index=False,
        encoding="utf-8-sig",
    )
    return arquivo_pareceres, arquivo_metricas


def main():
    pareceres, df_metricas = executar_lote()
    arquivos = salvar_resultados(pareceres, df_metricas)
    resumo = analisar_metricas(df_metricas)
    ARQUIVO_RESUMO.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Pareceres salvos em: {arquivos[0]}")
    print(f"Metricas salvas em: {arquivos[1]}")
    print(f"Resumo salvo em: {ARQUIVO_RESUMO}")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
