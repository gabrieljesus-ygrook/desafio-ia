from functools import lru_cache

import pandas as pd

from nivel_2.pipeline import aplicar_regras, carregar_dados, limpar_dados, normalizar_valores_brl


@lru_cache(maxsize=128)
def _base_tratada():
    """Prepara a base uma vez e reutiliza o resultado nas consultas."""
    df_bruto, taxa_usd_brl = carregar_dados()
    df_limpo = limpar_dados(df_bruto)
    df_normalizado = normalizar_valores_brl(df_limpo, taxa_usd_brl)
    return aplicar_regras(df_normalizado)


def _obter_cliente(cliente_id):
    df = _base_tratada()
    cliente = df[df["cliente_id"] == cliente_id].copy()
    if cliente.empty:
        raise ValueError(f"Cliente nao encontrado: {cliente_id}")
    return cliente


def historico_cliente(cliente_id):
    """Retorna os principais indicadores historicos de um cliente."""
    cliente = _obter_cliente(cliente_id)
    datas = cliente["data"].dropna()

    return {
        "cliente_id": cliente_id,
        "quantidade_operacoes": int(len(cliente)),
        "volume_total_brl": round(float(cliente["valor_brl"].sum()), 2),
        "media_valor_brl": round(float(cliente["valor_brl"].mean()), 2),
        "mediana_valor_brl": round(float(cliente["valor_brl"].median()), 2),
        "maior_operacao_brl": round(float(cliente["valor_brl"].max()), 2),
        "data_inicio": datas.min().strftime("%Y-%m-%d") if not datas.empty else None,
        "data_fim": datas.max().strftime("%Y-%m-%d") if not datas.empty else None,
        "sinalizacoes_regra_1": int(cliente["regra_1_fracionamento"].sum()),
        "sinalizacoes_regra_2": int(cliente["regra_2_valor_atipico"].sum()),
    }


def operacoes_do_dia(cliente_id, data):
    """Retorna as operacoes de um cliente em uma data especifica."""
    cliente = _obter_cliente(cliente_id)
    data_consulta = pd.to_datetime(data, errors="coerce")
    if pd.isna(data_consulta):
        raise ValueError(f"Data invalida: {data}")

    operacoes = cliente[cliente["data"] == data_consulta].copy()
    colunas = [
        "id",
        "data",
        "valor",
        "moeda",
        "valor_brl",
        "canal",
        "tipo",
        "contraparte",
        "observacao",
        "regra_1_fracionamento",
        "regra_2_valor_atipico",
    ]
    operacoes["data"] = operacoes["data"].dt.strftime("%Y-%m-%d")
    registros = operacoes[colunas].round({"valor_brl": 2}).to_dict(orient="records")

    return {
        "cliente_id": cliente_id,
        "data": data_consulta.strftime("%Y-%m-%d"),
        "quantidade_operacoes": int(len(operacoes)),
        "volume_total_brl": round(float(operacoes["valor_brl"].sum()), 2),
        "operacoes": registros,
    }


def perfil_canal(cliente_id):
    """Retorna quantidade, percentual e volume por canal do cliente."""
    cliente = _obter_cliente(cliente_id)
    total_operacoes = len(cliente)
    distribuicao = (
        cliente.groupby("canal", as_index=False)
        .agg(
            quantidade_operacoes=("id", "size"),
            volume_total_brl=("valor_brl", "sum"),
        )
        .sort_values("quantidade_operacoes", ascending=False)
    )
    distribuicao["percentual_operacoes"] = (
        distribuicao["quantidade_operacoes"] / total_operacoes * 100
    ).round(2)
    distribuicao["volume_total_brl"] = distribuicao["volume_total_brl"].round(2)

    return {
        "cliente_id": cliente_id,
        "quantidade_total_operacoes": int(total_operacoes),
        "distribuicao_por_canal": distribuicao.to_dict(orient="records"),
    }
