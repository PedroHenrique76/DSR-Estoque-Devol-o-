"""Montagem das páginas HTML (painel e relatório) e geração do PDF, comum às análises."""
from __future__ import annotations

import base64
import html
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATES = RAIZ / "templates"
FONTES = RAIZ / "fontes"

_FACES = [("Archivo", "archivo", [500, 700, 800]),
          ("Public Sans", "public-sans", [400, 500, 600, 700]),
          ("IBM Plex Mono", "ibm-plex-mono", [400, 500])]


def condicionais(txt: str, flags: dict[str, bool]) -> str:
    """Mantém ou remove os trechos <!--SE:nome-->…<!--FIM:nome--> do template."""
    for nome, ligado in flags.items():
        padrao = re.compile(rf"<!--SE:{nome}-->(.*?)<!--FIM:{nome}-->", re.S)
        txt = padrao.sub(lambda m: m.group(1) if ligado else "", txt)
    return txt


def trocar(txt: str, trocas: dict[str, str]) -> str:
    for k, v in trocas.items():
        txt = txt.replace("{{" + k + "}}", v)
    return txt


def fontes_css() -> str:
    css = []
    for fam, arq, pesos in _FACES:
        for w in pesos:
            p = FONTES / f"{arq}-latin-{w}-normal.woff2"
            if p.exists():
                b64 = base64.b64encode(p.read_bytes()).decode()
                css.append(f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};font-display:swap;"
                           f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "\n".join(css)


def documento(titulo: str, css: str, corpo: str, js: str, modo: str, embutir_fontes: bool = True) -> str:
    """Esqueleto da página. No relatório o tema é sempre claro."""
    fontes = fontes_css() if embutir_fontes else ""
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
