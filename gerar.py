"""Gera a análise de estoque por fornecedor a partir das extrações do Winthor.

Uso:
  python gerar.py                       # base mais recente em bases/, comparação automática
  python gerar.py --base 2026-10-28     # uma data específica
  python gerar.py --comparar 2026-10-16 # força a base de comparação
  python gerar.py --todas               # gera todas as datas da pasta bases/
  python gerar.py --sem-pdf             # só HTML e Excel (não precisa do Playwright)

Saídas em saida/AAAA-MM-DD/:
  Painel_Estoque_<empresa>_<data>.html      painel interativo (celular e computador)
  Relatorio_Estoque_<empresa>_<data>.pdf    relatório A4 para compartilhar
  Indicadores_Estoque_<empresa>_<data>.xlsx indicadores por fornecedor, resumo das fotos e grupos
  analise_<data>.json                       texto usado (achados, destaque, plano) para revisar à mão
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from estoque import achados
from estoque.indicadores import analisar
from estoque.leitura import carregar_todas
from estoque.render import exportar_excel, gerar_pdf, montar_html

RAIZ = Path(__file__).resolve().parent


def _data(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def gerar_uma(bases, cfg, data_atual: date | None, data_comp: date | None, pdf: bool, saida: Path) -> Path:
    # uma análise revisada à mão pode fixar a base de comparação usada na época
    if data_comp is None and data_atual is not None:
        arq = RAIZ / "analises" / f"{data_atual:%Y-%m-%d}.json"
        if arq.exists():
            data_comp = _data(json.loads(arq.read_text(encoding="utf-8")).get("comparar_com"))
    a = analisar(bases, cfg, data_atual, data_comp)
    texto = achados.montar(a, RAIZ / "analises")
    rot = a.atual.data.strftime("%d-%m-%Y")
    emp = cfg["empresa"]
    pasta = saida / f"{a.atual.data:%Y-%m-%d}"
    pasta.mkdir(parents=True, exist_ok=True)

    painel = pasta / f"Painel_Estoque_{emp}_{rot}.html"
    painel.write_text(montar_html(a, texto, "painel"), encoding="utf-8")
    relatorio_html = pasta / f"relatorio_{rot}.html"
    relatorio_html.write_text(montar_html(a, texto, "relatorio"), encoding="utf-8")
    exportar_excel(a, pasta / f"Indicadores_Estoque_{emp}_{rot}.xlsx")
    (pasta / f"analise_{rot}.json").write_text(
        json.dumps({k: texto[k] for k in ["achados", "destaque", "plano"]}, ensure_ascii=False, indent=2), encoding="utf-8")
    if pdf:
        gerar_pdf(relatorio_html, pasta / f"Relatorio_Estoque_{emp}_{rot}.pdf",
                  f"{emp} · {cfg['unidade']} · Estoque, giro e margem por fornecedor · base {a.atual.rotulo_longo}")

    t = a.tot
    comp = f" vs {a.comp.rotulo}" if a.comp else ""
    print(f"[{a.atual.rotulo_longo}{comp}] estoque {t['estoque']/1e6:.1f} mi · cobertura {t['dde']:.0f} dias · "
          f"margem {t['mpct']*100:.1f}% · excesso {t['excesso']/1e6:.1f} mi"
          + (f" · texto revisado: {', '.join(texto['revisado'])}" if texto["revisado"] else " · texto automático"))
    for aviso in a.atual.avisos:
        print("  aviso:", aviso)
    print("  saída:", pasta)
    return pasta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Análise estratégica de estoque por fornecedor (Winthor).")
    ap.add_argument("--base", help="data da base atual (AAAA-MM-DD). Padrão: a mais recente.")
    ap.add_argument("--comparar", help="data da base de comparação (AAAA-MM-DD). Padrão: mesmo ponto do mês anterior.")
    ap.add_argument("--todas", action="store_true", help="gera todas as datas da pasta bases/.")
    ap.add_argument("--sem-pdf", action="store_true", help="não gera o PDF (dispensa o Playwright).")
    ap.add_argument("--bases", default=str(RAIZ / "bases"), help="pasta das extrações.")
    ap.add_argument("--saida", default=str(RAIZ / "saida"), help="pasta de saída.")
    args = ap.parse_args(argv)

    cfg = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    bases = carregar_todas(args.bases)
    if not bases:
        print("Nenhuma base .xlsx em", args.bases, file=sys.stderr)
        return 1
    datas = [b.data for b in bases] if args.todas else [_data(args.base) or bases[-1].data]
    for d in datas:
        gerar_uma(bases, cfg, d, _data(args.comparar), not args.sem_pdf, Path(args.saida))
    return 0


if __name__ == "__main__":
    sys.exit(main())
