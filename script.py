import ast
import os
import sys
import logging
from pathlib import Path

import requests
import pandas as pd
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api-desafio-0lw6.onrender.com"
AUTH_ENDPOINT = f"{BASE_URL}/api/auth/bearer/"
DATA_ENDPOINT = f"{BASE_URL}/api/prova-paulista/"
PAGE_SIZE = 50
OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "prova_paulista.csv"


def carregar_credenciais() -> tuple[str, str]:
    load_dotenv()
    kid = os.getenv("KID")
    token = os.getenv("TOKEN")

    if not kid or not token:
        logger.error("Variáveis KID e/ou TOKEN não encontradas no arquivo .env.")
        sys.exit(1)

    return kid, token


def obter_bearer_token(kid: str, token: str) -> str:
    logger.info("Autenticando na API...")

    payload = {"token": token, "kid": kid}

    try:
        response = requests.post(AUTH_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        logger.error("Erro de autenticação (HTTP %s): %s", response.status_code, exc)
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        logger.error("Falha na conexão com a API: %s", exc)
        sys.exit(1)

    access_token: str = response.json().get("access", "")
    if not access_token:
        logger.error("Token JWT não retornado pela API.")
        sys.exit(1)

    logger.info("Autenticação bem-sucedida. Token obtido com sucesso.")
    return access_token


def buscar_pagina(bearer: str, page: int) -> dict:
    """Busca uma página específica de dados da API."""
    headers = {"Authorization": bearer}
    params = {"page": page, "page_size": PAGE_SIZE}

    try:
        response = requests.get(
            DATA_ENDPOINT, headers=headers, params=params, timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        logger.error(
            "Erro ao buscar página %d (HTTP %s): %s", page, response.status_code, exc
        )
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        logger.error("Falha na conexão ao buscar página %d: %s", page, exc)
        sys.exit(1)

    return response.json()


def consumir_todos_os_registros(bearer: str) -> list[list]:
    logger.info("Iniciando consumo de dados...")

    primeira_pagina = buscar_pagina(bearer, page=1)
    total = primeira_pagina.get("count", 0)
    registros = list(primeira_pagina.get("results", []))

    logger.info("Total de registros na API: %d", total)

    pagina_atual = 2
    while len(registros) < total:
        dados = buscar_pagina(bearer, page=pagina_atual)
        novos = dados.get("results", [])

        if not novos:
            break

        registros.extend(novos)
        logger.info(
            "Página %d processada – %d/%d registros coletados.",
            pagina_atual,
            len(registros),
            total,
        )

        if not dados.get("next"):
            break

        pagina_atual += 1

    logger.info("Consumo concluído. Total coletado: %d registros.", len(registros))
    return registros


def extrair_nome_escola(nome_bruto: str) -> str:
    if isinstance(nome_bruto, str) and " - " in nome_bruto:
        return nome_bruto.rsplit(" - ", 1)[0].strip()
    return nome_bruto


def extrair_notas(notas_raw) -> tuple:
    try:
        if isinstance(notas_raw, str):
            notas_raw = ast.literal_eval(notas_raw)
        notas = [round(float(n) * 100, 1) for n in notas_raw]
        n1 = notas[0] if len(notas) > 0 else None
        n2 = notas[1] if len(notas) > 1 else None
        n3 = notas[2] if len(notas) > 2 else None
        return n1, n2, n3
    except (ValueError, SyntaxError, TypeError):
        return None, None, None


def normalizar_registro(registro: list) -> dict:
    try:
        campo_id = registro[0] if len(registro) > 0 else None
        escola_bruta = registro[1] if len(registro) > 1 else None
        ano = registro[2] if len(registro) > 2 else None

        quarto = registro[3] if len(registro) > 3 else None
        if isinstance(quarto, list):
            nota_geral_raw = quarto[0] if len(quarto) > 0 else None
            notas_raw = quarto[1] if len(quarto) > 1 else None
        else:
            nota_geral_raw = quarto
            notas_raw = None

        n1, n2, n3 = extrair_notas(notas_raw)
        nota_geral = round(float(nota_geral_raw) * 100, 1) if nota_geral_raw is not None else None

        return {
            "id_escola": campo_id,
            "escola": extrair_nome_escola(escola_bruta),
            "ano": ano,
            "nota_geral": nota_geral,
            "nota_1": n1,
            "nota_2": n2,
            "nota_3": n3,
        }

    except (IndexError, TypeError) as exc:
        logger.warning("Registro malformado ignorado: %s | Erro: %s", registro, exc)
        return {}


def construir_dataframe(registros: list[list]) -> pd.DataFrame:
    logger.info("Construindo DataFrame...")

    dados_normalizados = [
        normalizado
        for r in registros
        if (normalizado := normalizar_registro(r))
    ]

    df = pd.DataFrame(dados_normalizados)

    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    for col in ["nota_geral", "nota_1", "nota_2", "nota_3"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("escola").reset_index(drop=True)

    logger.info(
        "DataFrame construído: %d linhas × %d colunas.", df.shape[0], df.shape[1]
    )
    return df


def exportar_csv(df: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, sep=";", encoding="utf-8-sig")
    logger.info("CSV exportado com sucesso: %s", OUTPUT_FILE.resolve())


def main() -> None:
    kid, token = carregar_credenciais()
    bearer = obter_bearer_token(kid, token)
    registros = consumir_todos_os_registros(bearer)

    if not registros:
        logger.warning("Nenhum registro retornado pela API. CSV não será gerado.")
        sys.exit(0)

    df = construir_dataframe(registros)
    exportar_csv(df)

    print("\n--- Prévia dos dados ---")
    print(df.head(10).to_string(index=False))
    print(f"\nTotal de registros: {len(df)}")


if __name__ == "__main__":
    main()
