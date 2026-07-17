"""
Scraper de feriados nacionais japoneses — Onion Payroll
=========================================================
Busca o CSV oficial do Gabinete do Governo do Japão (内閣府) e gera
docs/holidays.json no formato {"AAAA-MM": [dia1, dia2, ...]}.

Fonte oficial: https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv
Formato do CSV (desde 2019): Shift-JIS, CRLF, duas colunas —
  国民の祝日・休日月日,国民の祝日・休日名称
  2026/1/1,元日
  2026/1/12,成人の日
  ...

Roda semelhante ao scraper/scrape_mizuho.py do NetMikuji, mas sem
precisar de Selenium — o CSV é servido direto, sem JavaScript.

Uso: python scraper/scrape_holidays.py
Saída: docs/holidays.json
"""
import csv
import io
import json
import os
import sys
from datetime import date
from urllib.request import urlopen, Request

CSV_URL = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"
# Grava em dois lugares:
# - raiz do projeto: fonte "oficial", sobrevive a qualquer deploy.ps1
#   futuro (que apaga e reconstrói docs/ do zero a cada rodada)
# - docs/: efeito imediato no site publicado, sem esperar o próximo deploy
OUTPUT_PATHS = ["holidays.json", "docs/holidays.json"]

# Mantém só de N anos atrás até M anos à frente — evita gerar um JSON
# gigante com feriados de 1955 pra cá, que ninguém precisa.
ANOS_PASSADO = 1
ANOS_FUTURO = 3


def fetch_csv_rows() -> list[tuple[str, str]]:
    """Baixa e decodifica o CSV oficial (Shift-JIS), retorna linhas
    (data_str, nome) já sem o cabeçalho."""
    req = Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read()

    # O governo publica em Shift-JIS (às vezes reportado como MS932/CP932,
    # variante compatível). errors="replace" evita crash em caractere raro.
    text = raw.decode("cp932", errors="replace")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise ValueError("CSV vazio ou não foi possível ler as linhas")

    # Primeira linha é cabeçalho — descarta
    data_rows = rows[1:]
    resultado = []
    for row in data_rows:
        if len(row) < 2:
            continue
        data_str, nome = row[0].strip(), row[1].strip()
        if not data_str:
            continue
        resultado.append((data_str, nome))
    return resultado


def build_holidays_dict(rows: list[tuple[str, str]]) -> dict:
    """Converte as linhas (AAAA/M/D, nome) para {"AAAA-MM": [dias]},
    filtrando pela janela de anos relevante."""
    hoje = date.today()
    ano_min = hoje.year - ANOS_PASSADO
    ano_max = hoje.year + ANOS_FUTURO

    holidays: dict[str, list[int]] = {}
    for data_str, _nome in rows:
        try:
            partes = data_str.replace("-", "/").split("/")
            ano, mes, dia = int(partes[0]), int(partes[1]), int(partes[2])
        except (ValueError, IndexError):
            continue  # linha malformada — pula, não derruba o scraper inteiro

        if not (ano_min <= ano <= ano_max):
            continue

        month_key = f"{ano}-{mes:02d}"
        holidays.setdefault(month_key, [])
        if dia not in holidays[month_key]:
            holidays[month_key].append(dia)

    for month_key in holidays:
        holidays[month_key].sort()

    return dict(sorted(holidays.items()))


def main():
    print(f"Buscando {CSV_URL} ...")
    rows = fetch_csv_rows()
    print(f"{len(rows)} linhas lidas do CSV oficial")

    holidays = build_holidays_dict(rows)
    if not holidays:
        print("ERRO: nenhum feriado válido encontrado após o parse — abortando sem sobrescrever o arquivo.")
        sys.exit(1)

    total_dias = sum(len(v) for v in holidays.values())
    print(f"{total_dias} feriados em {len(holidays)} meses, de {min(holidays)} a {max(holidays)}")

    with open(OUTPUT_PATHS[0], "w", encoding="utf-8") as f:
        json.dump(holidays, f, ensure_ascii=False, indent=2)
    print(f"Salvo em {OUTPUT_PATHS[0]}")

    # docs/ pode não existir localmente antes do primeiro deploy.ps1 —
    # não falha o scraper por causa disso, só avisa.
    docs_dir = os.path.dirname(OUTPUT_PATHS[1])
    if os.path.isdir(docs_dir):
        with open(OUTPUT_PATHS[1], "w", encoding="utf-8") as f:
            json.dump(holidays, f, ensure_ascii=False, indent=2)
        print(f"Salvo em {OUTPUT_PATHS[1]}")
    else:
        print(f"Aviso: pasta '{docs_dir}' não existe ainda — pulado (normal antes do 1º deploy.ps1).")


if __name__ == "__main__":
    main()
