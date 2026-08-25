import json
import unicodedata
from pathlib import Path

import pandas as pd


RAIZ_PROJETO = Path(__file__).parents[1]
ARQUIVO_RANKING = RAIZ_PROJETO / "outputs" / "nivel_2_top10_clientes_organizado.csv"
ARQUIVO_PARECERES = RAIZ_PROJETO / "outputs" / "nivel_2_pareceres_lote.jsonl"
ARQUIVO_CONFRONTO = RAIZ_PROJETO / "outputs" / "nivel_2_confronto.csv"
ARQUIVO_RESUMO = RAIZ_PROJETO / "outputs" / "nivel_2_confronto_resumo.json"
ARQUIVO_RELATORIO = RAIZ_PROJETO / "outputs" / "nivel_2_confronto.md"

ORDEM_RISCO = {"baixo": 1, "medio": 2, "alto": 3}


def normalizar_nivel_risco(nivel_risco):
    """Padroniza variacoes de escrita retornadas pelo modelo."""
    texto = unicodedata.normalize("NFKD", str(nivel_risco).strip().lower())
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    equivalencias = {"baixo": "baixo", "medio": "medio", "moderado": "medio", "alto": "alto"}
    return equivalencias.get(texto, "desconhecido")


def classificar_risco_regras(sinalizacoes_regra_1, sinalizacoes_regra_2):
    """Classifica o risco pela quantidade de regras independentes presentes."""
    regras_ativas = int(sinalizacoes_regra_1 > 0) + int(sinalizacoes_regra_2 > 0)
    if regras_ativas == 2:
        return "alto"
    if regras_ativas == 1:
        return "medio"
    return "baixo"


def carregar_pareceres(caminho=None):
    """Carrega o JSONL do lote e extrai os campos usados no confronto."""
    arquivo = Path(caminho or ARQUIVO_PARECERES)
    registros = []
    with arquivo.open(encoding="utf-8") as conteudo:
        for linha in conteudo:
            if not linha.strip():
                continue
            resultado = json.loads(linha)
            parecer = resultado.get("parecer") or {}
            registros.append(
                {
                    "cliente_id": resultado["cliente_id"],
                    "nivel_risco_modelo_original": parecer.get("nivel_risco"),
                    "nivel_risco_modelo": normalizar_nivel_risco(parecer.get("nivel_risco")),
                    "tipologia_suspeita": parecer.get("tipologia_suspeita"),
                    "justificativa_modelo": parecer.get("justificativa"),
                    "quantidade_tools": len(resultado.get("ferramentas_chamadas", [])),
                }
            )
    return pd.DataFrame(registros)


def avaliar_divergencia(linha):
    """Indica qual leitura esta mais sustentada pelos dados disponiveis."""
    if linha["concorda"]:
        return "concordancia"

    risco_regras = ORDEM_RISCO.get(linha["nivel_risco_regras"], 0)
    risco_modelo = ORDEM_RISCO.get(linha["nivel_risco_modelo"], 0)
    regras_ativas = int(linha["sinalizacoes_regra_1"] > 0) + int(
        linha["sinalizacoes_regra_2"] > 0
    )

    if risco_modelo > risco_regras and regras_ativas == 1:
        return "regra_mais_consistente"
    if risco_modelo < risco_regras:
        return "regra_mais_consistente"
    return "revisao_humana"


def explicar_divergencia(linha):
    """Produz uma explicacao auditavel sem pedir novo julgamento a LLM."""
    if linha["concorda"]:
        return "O agente e o criterio deterministico atribuiram o mesmo nivel de risco."

    if linha["avaliacao_divergencia"] == "regra_mais_consistente":
        return (
            "O parecer elevou o risco sem apresentar uma segunda tipologia ou evidencia "
            "independente. Como apenas uma regra esta ativa, o nivel medio e mais "
            "coerente com o criterio definido. A ausencia de chamadas de tools nao e, "
            "por si so, um erro: o agente deve consulta-las apenas quando necessario."
        )

    return (
        "A divergencia possui elementos que nao podem ser resolvidos apenas pela "
        "contagem de regras e deve ser revisada por um analista."
    )


def montar_confronto(caminho_ranking=None, caminho_pareceres=None):
    """Combina regras e pareceres e calcula concordancia por cliente."""
    ranking = pd.read_csv(
        caminho_ranking or ARQUIVO_RANKING,
        sep=";",
        decimal=",",
        encoding="utf-8-sig",
    )
    pareceres = carregar_pareceres(caminho_pareceres)
    confronto = ranking.merge(pareceres, on="cliente_id", how="left", validate="one_to_one")
    confronto["nivel_risco_regras"] = confronto.apply(
        lambda linha: classificar_risco_regras(
            linha["sinalizacoes_regra_1"], linha["sinalizacoes_regra_2"]
        ),
        axis=1,
    )
    confronto["concorda"] = confronto["nivel_risco_regras"] == confronto["nivel_risco_modelo"]
    confronto["avaliacao_divergencia"] = confronto.apply(avaliar_divergencia, axis=1)
    confronto["analise_divergencia"] = confronto.apply(explicar_divergencia, axis=1)
    return confronto


def resumir_confronto(confronto):
    """Calcula a taxa de concordancia e resume as divergencias."""
    total = len(confronto)
    concordancias = int(confronto["concorda"].sum())
    divergencias = confronto.loc[
        ~confronto["concorda"],
        [
            "cliente_id",
            "nivel_risco_regras",
            "nivel_risco_modelo",
            "avaliacao_divergencia",
            "analise_divergencia",
        ],
    ].to_dict(orient="records")
    return {
        "criterio": {
            "alto": "cliente sinalizado pelas duas regras",
            "medio": "cliente sinalizado por apenas uma regra",
            "baixo": "cliente sem sinalizacao pelas regras",
        },
        "clientes_comparados": total,
        "concordancias": concordancias,
        "divergencias": total - concordancias,
        "taxa_concordancia_percentual": round(concordancias / total * 100, 2) if total else 0,
        "detalhes_divergencias": divergencias,
    }


def salvar_resultados(confronto, resumo):
    """Salva a tabela, o resumo e a leitura humana das divergencias."""
    ARQUIVO_CONFRONTO.parent.mkdir(parents=True, exist_ok=True)
    confronto.to_csv(
        ARQUIVO_CONFRONTO,
        sep=";",
        decimal=",",
        index=False,
        encoding="utf-8-sig",
    )
    ARQUIVO_RESUMO.write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    linhas = [
        "# Confronto entre regras e modelo",
        "",
        f"Taxa de concordancia: {resumo['taxa_concordancia_percentual']:.2f}% "
        f"({resumo['concordancias']} de {resumo['clientes_comparados']} clientes).",
        "",
        "## Divergencias",
        "",
    ]
    if not resumo["detalhes_divergencias"]:
        linhas.append("Nao foram encontradas divergencias.")
    for divergencia in resumo["detalhes_divergencias"]:
        linhas.extend(
            [
                f"### {divergencia['cliente_id']}",
                "",
                f"- Regras: {divergencia['nivel_risco_regras']}",
                f"- Modelo: {divergencia['nivel_risco_modelo']}",
                f"- Avaliacao: {divergencia['avaliacao_divergencia']}",
                f"- Analise: {divergencia['analise_divergencia']}",
                "",
            ]
        )
    ARQUIVO_RELATORIO.write_text("\n".join(linhas), encoding="utf-8")


def executar_confronto():
    confronto = montar_confronto()
    resumo = resumir_confronto(confronto)
    salvar_resultados(confronto, resumo)
    return confronto, resumo


def main():
    _, resumo = executar_confronto()
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    print(f"Confronto salvo em: {ARQUIVO_CONFRONTO}")
    print(f"Relatorio salvo em: {ARQUIVO_RELATORIO}")


if __name__ == "__main__":
    main()
