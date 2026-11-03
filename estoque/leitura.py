"""Leitura das extrações do Winthor (planilha "Export" por fornecedor).

Cada base fica em bases/AAAA-MM-DD.xlsx. A data do nome do arquivo é a data da foto.
A leitura aceita as duas versões da extração vistas até agora:
  - sem a coluna CODFORNEC (até 28/10/2026);
  - com CODFORNEC, onde a linha do fornecedor vem marcada como "Total" e pode haver
    linhas de detalhe repetindo o mesmo fornecedor (caso da Flora em 03/11/2026).
    As linhas de detalhe são descartadas para não contar o fornecedor em dobro.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from comum.bases import data_do_arquivo, listar_bases  # noqa: F401  (reexportadas)

COLUNAS = {
    "FORNECEDOR": "forn",
    "Venda Mês": "venda",
    "Qtd SKU": "sku",
    "Margem": "margem",
    "Valor Estoque": "estoque",
    "DDE": "dde_planilha",
}
LINHAS_IGNORADAS = {"Total", "Nenhum filtro aplicado"}


@dataclass
class Base:
    data: date
    arquivo: Path
    df: pd.DataFrame                      # uma linha por fornecedor
    total_planilha: dict                  # linha "Total" da planilha, para conferência
    avisos: list[str] = field(default_factory=list)

    @property
    def rotulo(self) -> str:
        return self.data.strftime("%d/%m")

    @property
    def rotulo_longo(self) -> str:
        return self.data.strftime("%d/%m/%Y")


def carregar_base(caminho: Path | str) -> Base:
    caminho = Path(caminho)
    bruto = pd.read_excel(caminho, sheet_name=0)
    avisos: list[str] = []

    faltando = [c for c in COLUNAS if c not in bruto.columns]
    if faltando:
        raise ValueError(f"{caminho.name}: colunas ausentes {faltando}. Colunas lidas: {list(bruto.columns)}")

    if "CODFORNEC" in bruto.columns:
        cod = bruto["CODFORNEC"].astype(str).str.strip()
        detalhe = bruto[(cod != "Total") & bruto["FORNECEDOR"].notna() & ~bruto["FORNECEDOR"].isin(LINHAS_IGNORADAS)]
        if len(detalhe):
            nomes = ", ".join(sorted(detalhe["FORNECEDOR"].astype(str).unique()))
            avisos.append(f"{len(detalhe)} linha(s) de detalhe por código descartada(s) para não duplicar: {nomes}.")
        bruto = bruto[(cod == "Total") | bruto["FORNECEDOR"].isin(LINHAS_IGNORADAS)]

    linha_total = bruto[bruto["FORNECEDOR"] == "Total"]
    total = {}
    if len(linha_total):
        t = linha_total.iloc[0]
        total = {"venda": float(t["Venda Mês"]), "margem": float(t["Margem"]),
                 "estoque": float(t["Valor Estoque"]), "sku": float(t["Qtd SKU"])}

    df = bruto[bruto["FORNECEDOR"].notna() & ~bruto["FORNECEDOR"].isin(LINHAS_IGNORADAS)]
    df = df[list(COLUNAS)].rename(columns=COLUNAS).copy()
    df["forn"] = df["forn"].astype(str).str.strip()
    for c in ["venda", "sku", "margem", "estoque"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    dup = df[df["forn"].duplicated(keep=False)]
    if len(dup):
        avisos.append(f"Fornecedores repetidos somados: {', '.join(sorted(dup['forn'].unique()))}.")
        df = df.groupby("forn", as_index=False).agg({"venda": "sum", "sku": "sum", "margem": "sum",
                                                      "estoque": "sum", "dde_planilha": "first"})

    neg = df[df["estoque"] < 0]
    if len(neg):
        avisos.append("Estoque negativo no cadastro: " + ", ".join(f"{r.forn} ({r.estoque:,.0f})" for r in neg.itertuples()) + ".")

    if total:
        for k in ["venda", "estoque"]:
            soma = df[k].sum()
            if abs(soma - total[k]) > max(1.0, abs(total[k]) * 1e-6):
                avisos.append(f"Soma de {k} ({soma:,.0f}) difere da linha Total da planilha ({total[k]:,.0f}).")

    return Base(data=data_do_arquivo(caminho), arquivo=caminho, df=df.reset_index(drop=True),
                total_planilha=total, avisos=avisos)


def carregar_todas(pasta: Path | str) -> list[Base]:
    return [carregar_base(p) for p in listar_bases(pasta)]
