"""Cálculo dos indicadores por fornecedor, totais, comparação entre fotos e listas de risco.

Definições (as mesmas usadas desde a primeira análise):
  Cobertura (DDE)  = estoque ÷ venda mensal × 30           (venda a preço, como na planilha)
  Cobertura a custo = estoque ÷ (venda − margem) × 30
  Margem %          = margem ÷ venda
  GMROI             = margem mensal × 12 ÷ estoque
  Excesso           = max(0, estoque − venda diária × cobertura-alvo), só para quem vendeu
  Curva ABC         = venda acumulada até 80% (A), até 95% (B), restante (C)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np
import pandas as pd

from .leitura import Base


# ----------------------------------------------------------------------------- nomes
def nome_curto(nome: str, cfg: dict) -> str:
    n = nome.upper().strip()
    for padrao, curto in cfg.get("nomes_curtos", []):
        if n.startswith(padrao.upper()):
            return curto
    s = re.sub(r"\s+(LTDA|S/A|S\.A\.?|SA|S A|LT|ME|EPP)\b.*$", "", n)
    s = re.sub(r" IND\.? E COM.*$", "", s)
    s = re.sub(r" (INDUSTRIA|INDUSTRIAL|INDUSTRIAS|DISTRIBUIDORA|COMERCIAL)\b.*$", "", s)
    return (s or n)[:26].strip()


def grupo_de(nome: str, cfg: dict) -> str | None:
    n = nome.upper()
    for grupo, prefixos in cfg.get("grupos", {}).items():
        if grupo.startswith("_"):
            continue
        if any(n.startswith(p.upper()) for p in prefixos):
            return grupo
    return None


# ----------------------------------------------------------------------------- por fornecedor
def calcular(base: Base, cfg: dict) -> pd.DataFrame:
    df = base.df.copy()
    alvo = cfg["cobertura_alvo_dias"]
    a, b = cfg["curva_abc"]
    df["mpct"] = np.where(df.venda > 0, df.margem / df.venda.where(df.venda > 0), np.nan)
    df["dde"] = np.where(df.venda > 0, df.estoque / df.venda.where(df.venda > 0) * 30, np.nan)
    df["gmroi"] = np.where(df.estoque > 0, df.margem * 12 / df.estoque.where(df.estoque > 0), np.nan)
    df["excesso"] = np.where(df.venda > 0, (df.estoque - df.venda / 30 * alvo).clip(lower=0), 0.0)
    df = df.sort_values(["venda", "estoque"], ascending=False).reset_index(drop=True)
    acum = df.venda.cumsum() / max(df.venda.sum(), 1)
    antes = acum.shift(fill_value=0)
    df["abc"] = np.where(antes < a, "A", np.where(antes < b, "B", "C"))
    df["curto"] = df.forn.map(lambda x: nome_curto(x, cfg))
    df["grupo"] = df.forn.map(lambda x: grupo_de(x, cfg))
    return df


def totais(df: pd.DataFrame, cfg: dict) -> dict:
    V, M, E = df.venda.sum(), df.margem.sum(), df.estoque.sum()
    ativos = df[df.venda > 0]
    lim = cfg["limites"]
    t = {
        "venda": V, "margem": M, "estoque": E, "sku": df.sku.sum(),
        "mpct": M / V if V else np.nan,
        "dde": E / V * 30 if V else np.nan,
        "dde_custo": E / (V - M) * 30 if V - M else np.nan,
        "gmroi": M * 12 / E if E else np.nan,
        "excesso": ativos.excesso.sum(),
        "fornecedores": len(df), "ativos": len(ativos),
        "sem_venda": int((df.venda <= 0).sum()),
        "sem_venda_sku": float(df[df.venda <= 0].sku.sum()),
        "sem_venda_estoque": float(df[df.venda <= 0].estoque.sum()),
        "parados_n": int((ativos.dde > lim["cobertura_parada_dias"]).sum()),
        "parados_estoque": float(ativos[ativos.dde > lim["cobertura_parada_dias"]].estoque.sum()),
    }
    for c in "ABC":
        x = df[df.abc == c]
        t[f"dde_{c}"] = x.estoque.sum() / x.venda.sum() * 30 if x.venda.sum() else np.nan
        t[f"estoque_{c}"] = x.estoque.sum()
    return t


# ----------------------------------------------------------------------------- comparação
def escolher_comparacao(bases: list[Base], atual: Base, cfg: dict) -> Base | None:
    anteriores = [b for b in bases if b.data < atual.data]
    if not anteriores:
        return None
    modo = cfg.get("comparacao", {}).get("modo", "mesmo_ponto_do_mes")
    if modo == "mesmo_ponto_do_mes":
        lo, hi = cfg["comparacao"].get("janela_dias", [25, 40])
        janela = [b for b in anteriores if lo <= (atual.data - b.data).days <= hi]
        if janela:
            return min(janela, key=lambda b: abs((atual.data - b.data).days - 30))
    return anteriores[-1]


def comparar(atual: pd.DataFrame, comp: pd.DataFrame | None) -> pd.DataFrame:
    df = atual.copy()
    if comp is None:
        for c in ["venda_c", "margem_c", "estoque_c", "dde_c", "mpct_c"]:
            df[c] = np.nan
        df["novo"] = False
    else:
        c = comp.set_index("forn")[["venda", "margem", "estoque", "dde", "mpct"]].add_suffix("_c")
        df = df.join(c, on="forn")
        df["novo"] = df.estoque_c.isna()
    df["d_estoque"] = df.estoque - df.estoque_c.fillna(0)
    df["d_venda"] = df.venda - df.venda_c.fillna(0)
    df["d_margem"] = df.margem - df.margem_c.fillna(0)
    df["d_mpct"] = df.mpct - df.mpct_c
    if comp is None:
        df[["d_estoque", "d_venda", "d_margem"]] = np.nan
    return df


def serie_grupos(historico: list[tuple[Base, pd.DataFrame]], cfg: dict) -> pd.DataFrame:
    """Uma linha por grupo × foto, com estoque, venda e cobertura somados."""
    linhas = []
    for base, df in historico:
        g = df[df.grupo.notna()].groupby("grupo").agg(venda=("venda", "sum"), estoque=("estoque", "sum"),
                                                      margem=("margem", "sum"), excesso=("excesso", "sum"),
                                                      cadastros=("forn", "count"))
        for nome, r in g.iterrows():
            linhas.append({"grupo": nome, "data": base.data, "rotulo": base.rotulo, **r.to_dict(),
                           "dde": r.estoque / r.venda * 30 if r.venda else np.nan})
    return pd.DataFrame(linhas)


# ----------------------------------------------------------------------------- pacote completo
@dataclass
class Analise:
    cfg: dict
    atual: Base
    comp: Base | None
    historico: list[Base]                 # todas as bases até a atual, em ordem
    df: pd.DataFrame                      # fornecedores da base atual + colunas da comparação
    tot: dict
    tot_comp: dict | None
    serie: list[dict]                     # totais de cada foto do histórico
    grupos: pd.DataFrame                  # série por grupo de cadastros
    por_foto: dict = field(default_factory=dict)   # data -> DataFrame calculado
    saiu: list[str] = field(default_factory=list)  # fornecedores da comparação ausentes na atual

    @property
    def tem_comp(self) -> bool:
        return self.comp is not None

    @property
    def ativos(self) -> pd.DataFrame:
        return self.df[self.df.venda > 0]

    def fornecedor(self, prefixo: str) -> pd.Series | None:
        x = self.df[self.df.forn.str.upper().str.startswith(prefixo.upper())]
        return x.iloc[0] if len(x) else None


def analisar(bases: list[Base], cfg: dict, data_atual=None, data_comp=None) -> Analise:
    if not bases:
        raise ValueError("Nenhuma base encontrada na pasta bases/.")
    bases = sorted(bases, key=lambda b: b.data)
    if data_atual:
        atual = next((b for b in bases if b.data == data_atual), None)
        if atual is None:
            raise ValueError(f"Não há base de {data_atual:%d/%m/%Y} em bases/.")
    else:
        atual = bases[-1]
    if data_comp:
        comp = next((b for b in bases if b.data == data_comp), None)
        if comp is None:
            raise ValueError(f"Não há base de {data_comp:%d/%m/%Y} para comparar.")
    else:
        comp = escolher_comparacao(bases, atual, cfg)

    historico = [b for b in bases if b.data <= atual.data]
    por_foto = {b.data: calcular(b, cfg) for b in historico}
    if comp and comp.data not in por_foto:
        por_foto[comp.data] = calcular(comp, cfg)
    df_atual = por_foto[atual.data]
    df_comp = por_foto[comp.data] if comp else None
    df = comparar(df_atual, df_comp)
    serie = [{"data": b.data, "rotulo": b.rotulo, **totais(por_foto[b.data], cfg)} for b in historico]
    grupos = serie_grupos([(b, por_foto[b.data]) for b in historico], cfg)
    saiu = sorted(set(df_comp.forn) - set(df_atual.forn)) if df_comp is not None else []
    return Analise(cfg=cfg, atual=atual, comp=comp, historico=historico, df=df,
                   tot=totais(df_atual, cfg), tot_comp=totais(df_comp, cfg) if df_comp is not None else None,
                   serie=serie, grupos=grupos, por_foto=por_foto, saiu=saiu)
