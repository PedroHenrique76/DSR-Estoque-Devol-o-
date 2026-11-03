"""Montagem das saídas: painel HTML interativo, relatório HTML/PDF e planilha de indicadores."""
from __future__ import annotations

import html
import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd

from comum import formato as f
from comum.excel import formatar
from comum.pagina import TEMPLATES, condicionais, documento, gerar_pdf, trocar  # noqa: F401  (gerar_pdf reexportado)
from .indicadores import Analise

def _n(v):
    """Número JSON-safe (NaN vira null)."""
    if v is None:
        return None
    v = float(v)
    return None if math.isnan(v) else round(v, 2)


# ----------------------------------------------------------------------------- dados para o script
def rotulos_mapa(a: Analise) -> list[str]:
    alvo = a.cfg["cobertura_alvo_dias"]
    pts = a.ativos[a.ativos.venda >= a.cfg["venda_minima_mapa"]]
    escolhidos: list[str] = []
    for df in [pts.nlargest(5, "estoque"), pts[pts.mpct < 0], pts[pts.dde > alvo * 3].nlargest(3, "estoque"),
               pts[pts.dde > alvo * 1.5].nlargest(4, "excesso")]:
        for x in df.forn:
            if x not in escolhidos:
                escolhidos.append(x)
    return escolhidos[:11]


def dados_script(a: Analise) -> dict:
    cfg = a.cfg
    rows = []
    for r in a.df.itertuples():
        rows.append({"f": r.forn, "n": r.curto, "v": _n(r.venda), "m": _n(r.margem), "s": int(r.sku),
                     "e": _n(r.estoque), "abc": r.abc,
                     "vc": _n(r.venda_c), "mc": _n(r.margem_c), "ec": _n(r.estoque_c)})
    foto = lambda s: {"rot": s["rotulo"], "v": s["venda"], "m": s["margem"], "e": s["estoque"], "x": s["excesso"]}
    tc = None
    if a.tot_comp:
        t = a.tot_comp
        tc = {"v": t["venda"], "m": t["margem"], "e": t["estoque"], "x": t["excesso"]}
    return {
        "rows": rows,
        "fotos": [foto(s) for s in a.serie],
        "atual": a.atual.rotulo, "comp": a.comp.rotulo if a.comp else None, "tc": tc,
        "rotulos_mapa": rotulos_mapa(a),
        "p": {"alvo": cfg["cobertura_alvo_dias"], "cc": cfg["custo_capital_mensal"], "area": cfg["area_m2"],
              "vmin_mapa": cfg["venda_minima_mapa"], "margem_baixa": cfg["limites"]["margem_baixa"]},
    }


# ----------------------------------------------------------------------------- blocos de texto
def _achados_html(itens: list[dict]) -> str:
    return "\n".join(f'      <li><span class="tag t-{i["classe"]}">{html.escape(i["tag"])}</span><p>{i["html"]}</p></li>'
                     for i in itens)


def _destaque_html(d: dict | None) -> str:
    if not d:
        return ""
    ps = "".join(f'<p class="small">{p}</p>' for p in d["paragrafos"])
    return f'<section>\n  <div class="callout">\n    <h3>{d["titulo"]}</h3>\n    {ps}\n  </div>\n</section>'


def _plano_html(fases: list[dict]) -> str:
    out = []
    for fase in fases:
        if not fase["itens"]:
            continue
        itens = "".join(f'<li><b>{i["titulo"]}</b><p class="small muted">{i["texto"]}</p></li>' for i in fase["itens"])
        out.append(f'    <div class="phase"><div><span class="eyebrow">{fase["prazo"]}</span><b>{fase["titulo"]}</b></div>'
                   f'<ol>{itens}</ol></div>')
    return "\n".join(out)


# ----------------------------------------------------------------------------- páginas
def montar_html(a: Analise, texto: dict, modo: str = "painel", embutir_fontes: bool = True) -> str:
    cfg, t = a.cfg, a.tot
    gerado = datetime.now().strftime("%d/%m/%Y %H:%M")
    origem = ("Texto revisado à mão: " + ", ".join(texto["revisado"]) + "." if texto.get("revisado")
              else "Texto gerado automaticamente a partir das regras em estoque/achados.py.")
    meta = [f"Base: {a.atual.arquivo.name}, {t['fornecedores']} fornecedores, {a.atual.rotulo_longo}"]
    if a.comp:
        gap = (a.atual.data - a.comp.data).days
        meta.append(f"Comparação: {a.comp.rotulo_longo}" + (" (mesmo ponto do mês)" if 25 <= gap <= 40 else f" ({gap} dias antes)"))
    meta.append("Valores em R$")
    if modo == "relatorio":
        meta.insert(0, "Relatório para PDF")
    rot = [s["rotulo"] for s in a.serie]
    evol_sub = f"Totais da {cfg['empresa']} em {f.lista(rot)}." + (f" O selo compara {a.atual.rotulo} com {a.comp.rotulo}." if a.comp else "")

    corpo = (TEMPLATES / "painel.html").read_text(encoding="utf-8")
    corpo = condicionais(corpo, {"evol": len(a.serie) >= 2, "comp": a.tem_comp,
                                  "painel": modo == "painel", "relatorio": modo == "relatorio"})
    trocas = {
        "EMPRESA": cfg["empresa"], "UNIDADE": cfg["unidade"],
        "META": "".join(f"<span>{html.escape(m)}</span>" for m in meta),
        "ACHADOS": _achados_html(texto["achados"]),
        "EVOL_SUB": evol_sub, "AREA": f.num(cfg["area_m2"]),
        "COMP": a.comp.rotulo if a.comp else "", "ATUAL": a.atual.rotulo,
        "VMIN": f.mil(cfg["venda_minima_mapa"]), "ALVO": str(cfg["cobertura_alvo_dias"]),
        "MEDIA": f.pct(t["mpct"]), "CC": f.pct(cfg["custo_capital_mensal"]),
        "MARGEM_BAIXA": f.pct(cfg["limites"]["margem_baixa"], 0),
        "DESTAQUE": _destaque_html(texto.get("destaque")),
        "PLANO": _plano_html(texto["plano"]),
        "OBS": "\n".join(f"    <li>{o}</li>" for o in texto["observacoes"]),
        "RODAPE": f"Gerado em {gerado} pelo projeto estoque-dsr. {origem}",
    }
    corpo = trocar(corpo, trocas)

    js = (TEMPLATES / "painel.js").read_text(encoding="utf-8")
    js = js.replace("__DADOS__", json.dumps(dados_script(a), ensure_ascii=False, separators=(",", ":")))
    js = js.replace("__MODO__", modo)

    css = (TEMPLATES / "painel.css").read_text(encoding="utf-8")
    css += "\n.rodape{margin-top:10px;font-size:.75rem}\n"
    if modo == "relatorio":
        css += "\n" + (TEMPLATES / "relatorio.css").read_text(encoding="utf-8")
    titulo = f"Estoque por Fornecedor {cfg['empresa']}" + (f" · {a.atual.rotulo_longo}" if modo == "relatorio" else "")
    return documento(titulo, css, corpo, js, modo, embutir_fontes)


# ----------------------------------------------------------------------------- planilha
def exportar_excel(a: Analise, destino: Path) -> None:
    cfg = a.cfg
    alvo = cfg["cobertura_alvo_dias"]
    df = a.df.copy()
    sufixo = f" {a.comp.rotulo}" if a.comp else ""
    cols = {
        "forn": "Fornecedor", "curto": "Nome curto", "grupo": "Grupo", "abc": "Curva",
        "venda": "Venda mês", "margem": "Margem R$", "mpct": "Margem %", "sku": "SKUs",
        "estoque": "Estoque", "dde": "Cobertura (dias)", "gmroi": "GMROI", "excesso": f"Excesso {alvo}d",
    }
    if a.comp:
        cols.update({"venda_c": f"Venda{sufixo}", "mpct_c": f"Margem %{sufixo}", "estoque_c": f"Estoque{sufixo}",
                     "dde_c": f"Cobertura{sufixo}", "d_estoque": "Δ estoque", "d_venda": "Δ venda", "novo": "Novo"})
    forn = df[list(cols)].rename(columns=cols)

    resumo = pd.DataFrame([{
        "Foto": s["rotulo"], "Data": s["data"], "Venda": s["venda"], "Margem R$": s["margem"], "Margem %": s["mpct"],
        "Estoque": s["estoque"], "Cobertura (dias)": s["dde"], "Cobertura a custo": s["dde_custo"], "GMROI": s["gmroi"],
        f"Excesso {alvo}d": s["excesso"], "Fornecedores": s["fornecedores"], "Com venda": s["ativos"],
        "Sem venda": s["sem_venda"], "Cobertura A": s["dde_A"], "Cobertura B": s["dde_B"], "Cobertura C": s["dde_C"],
    } for s in a.serie])

    grupos = a.grupos.pivot_table(index="grupo", columns="rotulo", values="dde", aggfunc="first")
    grupos = grupos[[s["rotulo"] for s in a.serie if s["rotulo"] in grupos.columns]].reset_index()
    grupos.columns = ["Grupo"] + [f"Cobertura {c}" for c in grupos.columns[1:]]

    with pd.ExcelWriter(destino, engine="openpyxl") as xw:
        resumo.to_excel(xw, sheet_name="Resumo", index=False)
        forn.to_excel(xw, sheet_name="Fornecedores", index=False)
        grupos.to_excel(xw, sheet_name="Grupos", index=False)
        formatar(xw)
