import json
import os
import time
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from nivel_2.pipeline import aplicar_regras, carregar_dados, limpar_dados, normalizar_valores_brl
from nivel_2.tools import historico_cliente, operacoes_do_dia, perfil_canal


class Parecer(BaseModel):
    """Formato final esperado do agente."""

    nivel_risco: str
    tipologia_suspeita: str
    red_flags: list[str]
    justificativa: str


TOOL_DECLARATIONS = [
    {
        "name": "historico_cliente",
        "description": "Consulta o resumo agregado das operacoes de um cliente.",
        "parameters": {
            "type": "object",
            "properties": {
                "cliente_id": {"type": "string", "description": "Identificador do cliente."}
            },
            "required": ["cliente_id"],
        },
    },
    {
        "name": "operacoes_do_dia",
        "description": "Consulta as operacoes de um cliente em uma data especifica.",
        "parameters": {
            "type": "object",
            "properties": {
                "cliente_id": {"type": "string", "description": "Identificador do cliente."},
                "data": {"type": "string", "description": "Data no formato YYYY-MM-DD."},
            },
            "required": ["cliente_id", "data"],
        },
    },
    {
        "name": "perfil_canal",
        "description": "Consulta a distribuicao de operacoes e volume por canal.",
        "parameters": {
            "type": "object",
            "properties": {
                "cliente_id": {"type": "string", "description": "Identificador do cliente."}
            },
            "required": ["cliente_id"],
        },
    },
]

TOOL_FUNCTIONS = {
    "historico_cliente": historico_cliente,
    "operacoes_do_dia": operacoes_do_dia,
    "perfil_canal": perfil_canal,
}


@lru_cache(maxsize=1)
def _base_para_contexto():
    """Carrega a base tratada usada para montar as flags iniciais."""
    df_bruto, taxa_usd_brl = carregar_dados()
    df_limpo = limpar_dados(df_bruto)
    df_normalizado = normalizar_valores_brl(df_limpo, taxa_usd_brl)
    return aplicar_regras(df_normalizado)


def _contexto_inicial(cliente_id):
    df = _base_para_contexto()
    cliente = df[df["cliente_id"] == cliente_id]
    if cliente.empty:
        raise ValueError(f"Cliente nao encontrado: {cliente_id}")

    return {
        "cliente_id": cliente_id,
        "quantidade_transacoes": int(len(cliente)),
        "volume_total_brl": round(float(cliente["valor_brl"].sum()), 2),
        "flags_deterministicas": {
            "fracionamento": bool(cliente["regra_1_fracionamento"].any()),
            "valor_atipico": bool(cliente["regra_2_valor_atipico"].any()),
        },
        "datas_com_sinalizacao": sorted(
            cliente.loc[
                cliente["regra_1_fracionamento"] | cliente["regra_2_valor_atipico"],
                "data",
            ]
            .dropna()
            .dt.strftime("%Y-%m-%d")
            .unique()
            .tolist()
        ),
    }


def _executar_tool(nome, argumentos):
    """Executa somente a ferramenta escolhida pelo modelo."""
    ferramenta = TOOL_FUNCTIONS.get(nome)
    if ferramenta is None:
        return {"erro": f"Ferramenta desconhecida: {nome}"}
    try:
        return ferramenta(**argumentos)
    except (TypeError, ValueError, KeyError) as erro:
        return {"erro": f"Falha ao executar {nome}: {erro}"}


def _validar_parecer(texto):
    try:
        payload = texto if isinstance(texto, dict) else json.loads(texto)
        return {"valido": True, "parecer": Parecer.model_validate(payload).model_dump(), "erro": None}
    except (json.JSONDecodeError, ValidationError, TypeError) as erro:
        return {"valido": False, "parecer": None, "erro": f"{type(erro).__name__}: {erro}"}


def _gerar_conteudo(api_key, model, contents):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": contents,
        "tools": [{"functionDeclarations": TOOL_DECLARATIONS}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": Parecer.model_json_schema(),
        },
    }
    inicio = time.perf_counter()
    resposta = requests.post(
        url,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    latencia_ms = round((time.perf_counter() - inicio) * 1000, 2)
    resposta.raise_for_status()
    return resposta.json(), latencia_ms


@lru_cache(maxsize=128)
def _analisar_cliente(cliente_id, max_rodadas=4, max_chamadas_tools=6):
    """Executa o agente e retorna parecer, rastreio de tools e metricas."""
    load_dotenv(Path(__file__).parents[1] / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY nao configurada no arquivo .env")

    contexto = _contexto_inicial(cliente_id)
    instrucao = (
        "Analise este cliente para triagem de PLD. Use as ferramentas somente quando "
        "precisar de detalhes adicionais; nao e necessario chamar todas. "
        "Os calculos determin deterministicos ja foram feitos em Python. "
        "No final, responda somente com um JSON contendo nivel_risco, "
        "tipologia_suspeita, red_flags e justificativa. Nao invente dados.\n\n"
        f"Contexto deterministico: {json.dumps(contexto, ensure_ascii=False)}"
    )
    contents = [{"role": "user", "parts": [{"text": instrucao}]}]
    ferramentas_chamadas = []
    tokens_entrada = 0
    tokens_saida = 0
    tokens_total = 0
    latencia_total_ms = 0.0
    ultimo_erro = None

    for rodada in range(1, max_rodadas + 1):
        resposta, latencia_ms = _gerar_conteudo(api_key, model, contents)
        latencia_total_ms += latencia_ms
        uso = resposta.get("usageMetadata", {})
        tokens_entrada += uso.get("promptTokenCount", 0) or 0
        tokens_saida += uso.get("candidatesTokenCount", 0) or 0
        tokens_total += uso.get("totalTokenCount", 0) or 0

        candidatos = resposta.get("candidates", [])
        if not candidatos:
            ultimo_erro = "API nao retornou candidatos"
            break
        conteudo_modelo = candidatos[0].get("content", {})
        partes = conteudo_modelo.get("parts", [])
        contents.append({"role": "model", "parts": partes})
        chamadas = [parte.get("functionCall") for parte in partes if parte.get("functionCall")]

        if not chamadas:
            textos = [parte.get("text", "") for parte in partes if parte.get("text")]
            resultado = _validar_parecer("".join(textos))
            if resultado["valido"]:
                resultado.update(
                    {
                        "cliente_id": cliente_id,
                        "modelo": model,
                        "rodadas": rodada,
                        "ferramentas_chamadas": ferramentas_chamadas,
                        "tokens_entrada": tokens_entrada,
                        "tokens_saida": tokens_saida,
                        "tokens_total": tokens_total,
                        "latencia_total_ms": round(latencia_total_ms, 2),
                    }
                )
                return resultado
            ultimo_erro = resultado["erro"]
            break

        if len(ferramentas_chamadas) + len(chamadas) > max_chamadas_tools:
            ultimo_erro = "Limite maximo de chamadas de ferramentas atingido"
            break

        for chamada in chamadas:
            nome = chamada.get("name")
            argumentos = chamada.get("args", {})
            resultado_tool = _executar_tool(nome, argumentos)
            ferramentas_chamadas.append({"nome": nome, "argumentos": argumentos})
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": nome,
                                "response": {"resultado": resultado_tool},
                            }
                        }
                    ],
                }
            )

    return {
        "valido": False,
        "parecer": None,
        "erro": ultimo_erro or "Agente encerrou sem parecer valido",
        "cliente_id": cliente_id,
        "modelo": model,
        "rodadas": max_rodadas,
        "ferramentas_chamadas": ferramentas_chamadas,
        "tokens_entrada": tokens_entrada,
        "tokens_saida": tokens_saida,
        "tokens_total": tokens_total,
        "latencia_total_ms": round(latencia_total_ms, 2),
    }


def analisar_cliente(cliente_id, max_rodadas=4, max_chamadas_tools=6):
    """Retorna o parecer do cliente, reutilizando resultados já calculados."""
    resultado = _analisar_cliente(cliente_id, max_rodadas, max_chamadas_tools)
    return deepcopy(resultado)


analisar_cliente.cache_clear = _analisar_cliente.cache_clear
analisar_cliente.cache_info = _analisar_cliente.cache_info
