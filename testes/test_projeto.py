"""Testes de conferência. Rode com:  python -m pytest testes   (ou  python testes/test_projeto.py)

Os valores esperados são os das análises entregues em out–nov/2026. Se uma mudança no
código alterar algum deles, o teste avisa antes de o relatório sair com número diferente.
"""
import json
import sys
import tempfile
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from estoque.indicadores import analisar  # noqa: E402
from estoque.leitura import carregar_todas  # noqa: E402

CFG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
BASES = carregar_todas(RAIZ / "bases")


def test_soma_bate_com_linha_total():
    for b in BASES:
        assert not any("difere da linha Total" in a for a in b.avisos), (b.rotulo, b.avisos)


def test_flora_nao_duplica_em_03_11():
    b = next(b for b in BASES if b.data == date(2026, 11, 3))
    flora = b.df[b.df.forn == "FLORA PRODUTOS DE HIGIENE E LIMPEZA LTDA"]
    assert len(flora) == 1
    assert round(flora.estoque.iloc[0]) == 4_160_034


def test_indicadores_conhecidos():
    esperado = {  # data: (estoque, cobertura, margem %, excesso 45d)
        date(2026, 10, 1): (72_134_933, 68.2, 0.1493, 25.38e6),
        date(2026, 10, 16): (70_630_372, 65.2, 0.1596, 22.54e6),
        date(2026, 10, 28): (76_380_541, 70.0, 0.1554, 28.13e6),
        date(2026, 11, 3): (70_623_071, 63.3, 0.1431, 21.67e6),
    }
    for d, (e, dde, m, x) in esperado.items():
        a = analisar(BASES, CFG, d)
        assert round(a.tot["estoque"]) == e
        assert abs(a.tot["dde"] - dde) < 0.05
        assert abs(a.tot["mpct"] - m) < 0.0005
        assert abs(a.tot["excesso"] - x) < 0.01e6


def test_comparacao_mesmo_ponto_do_mes():
    a = analisar(BASES, CFG, date(2026, 11, 3))
    assert a.comp.data == date(2026, 10, 1)
    a = analisar(BASES, CFG, date(2026, 10, 1))
    assert a.comp is None


def test_geracao_sem_pdf():
    import gerar
    with tempfile.TemporaryDirectory() as tmp:
        assert gerar.main(["--base", "2026-11-03", "--sem-pdf", "--saida", tmp]) == 0
        pasta = Path(tmp) / "2026-11-03"
        nomes = {p.name for p in pasta.iterdir()}
        assert "Painel_Estoque_DSR_03-11-2026.html" in nomes
        assert "Indicadores_Estoque_DSR_03-11-2026.xlsx" in nomes


if __name__ == "__main__":
    falhas = 0
    for nome, fn in list(globals().items()):
        if nome.startswith("test_"):
            try:
                fn()
                print("ok   ", nome)
            except AssertionError as e:
                falhas += 1
                print("FALHA", nome, e)
    sys.exit(1 if falhas else 0)
