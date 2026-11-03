"""Montagem das saídas: painel HTML interativo, relatório HTML/PDF e planilha de indicadores."""
from __future__ import annotations

import base64
import html
import json
import math
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import formato as f
from .indicadores import Analise

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATES = RAIZ / "templates"
FONTES = RAIZ / "fontes"

_FACES = [("Archivo", "archivo", [500, 700, 800]),
          ("Public Sans", "public-sans", [400, 500, 600, 700]),
          ("IBM Plex Mono", "ibm-plex-mono", [400, 500])]


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


def _condicionais(txt: str, flags: dict[str, bool]) -> str:
    for nome, ligado in flags.items():
        padrao = re.compile(rf"<!--SE:{nome}-->(.*?)<!--FIM:{nome}-->", re.S)
        txt = padrao.sub(lambda m: m.group(1) if ligado else "", txt)
    return txt


def _fontes_css() -> str:
    css = []
    for fam, arq, pesos in _FACES:
        for w in pesos:
            p = FONTES / f"{arq}-latin-{w}-normal.woff2"
            if p.exists():
                b64 = base64.b64encode(p.read_bytes()).decode()
                css.append(f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};font-display:swap;"
                           f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "\n".join(css)


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
    corpo = _condicionais(corpo, {"evol": len(a.serie) >= 2, "comp": a.tem_comp,
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
    for k, v in trocas.items():
        corpo = corpo.replace("{{" + k + "}}", v)

    js = (TEMPLATES / "painel.js").read_text(encoding="utf-8")
    js = js.replace("__DADOS__", json.dumps(dados_script(a), ensure_ascii=False, separators=(",", ":")))
    js = js.replace("__MODO__", modo)

    css = (TEMPLATES / "painel.css").read_text(encoding="utf-8")
    css += "\n.rodape{margin-top:10px;font-size:.75rem}\n"
    if modo == "relatorio":
        css += "\n" + (TEMPLATES / "relatorio.css").read_text(encoding="utf-8")
    fontes = _fontes_css() if embutir_fontes else ""
    titulo = f"Estoque por Fornecedor {cfg['empresa']}" + (f" · {a.atual.rotulo_longo}" if modo == "relatorio" else "")
    tema = ' data-theme="light"' if modo == "relatorio" else ""
    return (f'<!DOCTYPE html>\n<html lang="pt-BR"{tema}>\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{titulo}</title>\n'
            f"<style>\n*,*::before,*::after{{box-sizing:border-box}}\n:root{{color-scheme:light}}\n"
            f"html{{-webkit-text-size-adjust:100%}}\nbody{{margin:0}}\nimg{{max-width:100%}}\n[hidden]{{display:none!important}}\n"
            f"{fontes}\n{css}\n</style>\n</head>\n<body>\n{corpo}\n<script>\n{js}\n</script>\n</body>\n</html>\n")


def gerar_pdf(html_relatorio: Path, pdf: Path, rodape: str) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError("Para gerar o PDF instale o Playwright: pip install playwright && "
                           "python -m playwright install chromium") from e
    pe = ('<div style="width:100%;font-family:Helvetica,Arial,sans-serif;font-size:7.5px;color:#7a8291;padding:0 12mm;'
          f'display:flex;justify-content:space-between"><span>{html.escape(rodape)}</span>'
          '<span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>')
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pg = nav.new_page()
        erros: list[str] = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.emulate_media(media="print", color_scheme="light")
        pg.goto(html_relatorio.resolve().as_uri())
        pg.wait_for_timeout(800)
        if erros:
            raise RuntimeError("Erro de script no relatório: " + "; ".join(erros))
        pg.pdf(path=str(pdf), format="A4", print_background=True, display_header_footer=True,
               header_template="<div></div>", footer_template=pe,
               margin={"top": "13mm", "bottom": "15mm", "left": "12mm", "right": "12mm"})
        nav.close()


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
        _formatar(xw)


def _formatar(xw) -> None:
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    cab = PatternFill("solid", fgColor="1F2A37")
    for ws in xw.book.worksheets:
        ws.freeze_panes = "B2"
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = cab
        for i, col in enumerate(ws.iter_cols(min_row=1, max_row=ws.max_row), start=1):
            nome = str(col[0].value or "")
            larg = max(len(nome), *(len(str(c.value)) for c in col[1:50] if c.value is not None), 8)
            ws.column_dimensions[get_column_letter(i)].width = min(larg + 2, 48)
            if "%" in nome:
                fmt = "0.0%"
            elif any(k in nome for k in ["Cobertura", "SKUs", "Fornecedores", "venda", "Sem"]) and "Venda" not in nome:
                fmt = "0"
            elif "GMROI" in nome:
                fmt = "0.00"
            elif nome in ("Data",):
                fmt = "dd/mm/yyyy"
            else:
                fmt = "#,##0"
            for c in col[1:]:
                if isinstance(c.value, (int, float)):
                    c.number_format = fmt
