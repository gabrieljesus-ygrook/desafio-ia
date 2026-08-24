import json
from pathlib import Path

import pandas as pd


CAMPOS_TEXTO = [
    "id",
    "cliente_id",
    "moeda",
    "canal",
    "tipo",
    "contraparte",
    "observacao",
]


def carregar_dados(caminho=None):
    """Ler o JSON do Nivel 2 e devolve as operacoes e a taxa do dolar."""
    caminho_padrao = Path(__file__).parents[1] / "dados" / "dados_nivel_2.json"
    caminho_arquivo = Path(caminho or caminho_padrao)
    conteudo = json.loads(caminho_arquivo.read_text(encoding="utf-8"))
    df_bruto = pd.DataFrame(conteudo["operacoes"])
    taxa_usd_brl = conteudo["taxa_cambio_usd_brl"]
    return df_bruto, taxa_usd_brl


def limpar_dados(df_bruto):
    """Ajusta os tipos basicos e remove repeticoes pela chave id."""
    df = df_bruto.copy()

    for coluna in CAMPOS_TEXTO:
        df[coluna] = df[coluna].fillna("").astype(str).str.strip()

    # O id e a chave unica; a primeira ocorrencia e mantida.
    df = df.drop_duplicates(subset="id", keep="first").reset_index(drop=True)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["data_ausente"] = df["data"].isna()
    return df


def normalizar_valores_brl(df_limpo, taxa_usd_brl):
    """Converte os valores para BRL usando a taxa do arquivo."""
    df = df_limpo.copy()
    multiplicadores = {"BRL": 1.0, "USD": taxa_usd_brl}
    df["multiplicador_moeda"] = df["moeda"].map(multiplicadores)

    if df["multiplicador_moeda"].isna().any():
        moedas_desconhecidas = sorted(
            df.loc[df["multiplicador_moeda"].isna(), "moeda"].unique()
        )
        raise ValueError(f"Moedas nao suportadas: {moedas_desconhecidas}")

    df["valor_brl"] = df["valor"] * df["multiplicador_moeda"]
    return df.drop(columns="multiplicador_moeda")


def aplicar_regra_1_fracionamento(df_normalizado):
    """Marca as operacoes que formam um grupo de fracionamento."""
    df = df_normalizado.copy()
    resumo_cliente_data = (
        df.dropna(subset=["data"])
        .groupby(["cliente_id", "data"])
        .agg(
            quantidade_operacoes=("id", "size"),
            soma_brl=("valor_brl", "sum"),
            maior_operacao_brl=("valor_brl", "max"),
        )
    )
    grupos_que_atendem_regra_1 = resumo_cliente_data[
        (resumo_cliente_data["quantidade_operacoes"] >= 3)
        & (resumo_cliente_data["soma_brl"] > 50000)
        & (resumo_cliente_data["maior_operacao_brl"] < 20000)
    ]
    chaves_cliente_data = pd.MultiIndex.from_frame(df[["cliente_id", "data"]])
    df["regra_1_fracionamento"] = chaves_cliente_data.isin(
        grupos_que_atendem_regra_1.index
    )
    return df


def aplicar_regra_2_valor_atipico(df_normalizado):
    """Marca operacoes acima de cinco vezes a mediana do cliente."""
    df = df_normalizado.copy()
    df["quantidade_transacao_cliente"] = df.groupby("cliente_id")["id"].transform("size")
    df["mediana_cliente_brl"] = df.groupby("cliente_id")["valor_brl"].transform("median")
    df["limite_atipico_brl"] = 5 * df["mediana_cliente_brl"]
    df["regra_2_valor_atipico"] = (
        (df["quantidade_transacao_cliente"] >= 4)
        & (df["valor_brl"] > df["limite_atipico_brl"])
    )
    return df


def aplicar_regras(df_normalizado):
    """Executa as duas regras e devolve o DataFrame com as flags."""
    df_com_regra_1 = aplicar_regra_1_fracionamento(df_normalizado)
    return aplicar_regra_2_valor_atipico(df_com_regra_1)


def gerar_ranking_clientes(df_com_regras, limite=10):
    """Ordena os clientes por sinalizacoes e volume total em BRL."""
    ranking = (
        df_com_regras.groupby("cliente_id", as_index=False)
        .agg(
            sinalizacoes_regra_1=("regra_1_fracionamento", "sum"),
            sinalizacoes_regra_2=("regra_2_valor_atipico", "sum"),
            volume_total_brl=("valor_brl", "sum"),
        )
    )
    ranking["total_sinalizacoes"] = (
        ranking["sinalizacoes_regra_1"] + ranking["sinalizacoes_regra_2"]
    )
    ranking = (
        ranking.sort_values(
            ["total_sinalizacoes", "volume_total_brl"],
            ascending=[False, False],
        )
        .head(limite)
        .reset_index(drop=True)
    )
    ranking = ranking[
        [
            "cliente_id",
            "sinalizacoes_regra_1",
            "sinalizacoes_regra_2",
            "total_sinalizacoes",
            "volume_total_brl",
        ]
    ]
    ranking.insert(0, "ranking", range(1, len(ranking) + 1))
    return ranking


def salvar_ranking(ranking, caminho_saida=None):
    """Salva o ranking em CSV e retorna o caminho usado."""
    caminho_padrao = Path(__file__).parents[1] / "outputs" / "nivel_2_top10_clientes_organizado.csv"
    caminho_arquivo = Path(caminho_saida or caminho_padrao)
    caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
    ranking.to_csv(
        caminho_arquivo,
        sep=";",
        decimal=",",
        float_format="%.2f",
        index=False,
        encoding="utf-8-sig",
    )
    return caminho_arquivo


def executar_parte_a(caminho_dados=None, caminho_saida=None):
    df_bruto, taxa_usd_brl = carregar_dados(caminho_dados)
    df_limpo = limpar_dados(df_bruto)
    df_normalizado = normalizar_valores_brl(df_limpo, taxa_usd_brl)
    df_com_regras = aplicar_regras(df_normalizado)
    ranking = gerar_ranking_clientes(df_com_regras)
    arquivo_saida = salvar_ranking(ranking, caminho_saida)
    return {
        "df_bruto": df_bruto,
        "df_com_regras": df_com_regras,
        "ranking": ranking,
        "arquivo_saida": arquivo_saida,
    }


def main():
    resultado = executar_parte_a()
    df_bruto = resultado["df_bruto"]
    df_com_regras = resultado["df_com_regras"]
    print(f"Registros brutos: {len(df_bruto)}")
    print(f"Registros após limpeza: {len(df_com_regras)}")
    print(f"Regra 1: {int(df_com_regras['regra_1_fracionamento'].sum())} operações")
    print(f"Regra 2: {int(df_com_regras['regra_2_valor_atipico'].sum())} operações")
    print(f"Ranking salvo em: {resultado['arquivo_saida']}")


if __name__ == "__main__":
    main()
