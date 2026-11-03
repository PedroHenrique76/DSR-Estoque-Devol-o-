"""Formatação de números no padrão brasileiro, igual à usada no painel."""
from __future__ import annotations

import math


def _br(v: float, casas: int = 0) -> str:
    s = f"{v:,.{casas}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    if s.startswith("-"):
        s = "−" + s[1:]
        if s.strip("−0,") == "":      # evita "−0,0"
            s = s[1:]
    return s


def num(v: float, casas: int = 0) -> str:
    return _br(v, casas)


def mi(v: float) -> str:
    return f"R$ {_br(v / 1e6, 1)} mi"


def mil(v: float) -> str:
    if abs(v) >= 1e6:
        return mi(v)
    return f"R$ {_br(round(v / 1000), 0)} mil"


def reais(v: float) -> str:
    """Valor em reais: mil ou mi conforme o tamanho; abaixo de R$ 1 mil, em reais."""
    if abs(v) < 1000:
        return f"R$ {_br(v, 0)}"
    if abs(v) < 10_000:
        return f"R$ {_br(v / 1000, 1)} mil"
    return mil(v)


def sinal(v: float, f=mil) -> str:
    s = "+" if v > 0 else "−" if v < 0 else ""
    return s + f(abs(v))


def pct(v: float, casas: int = 1) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    return f"{_br(v * 100, casas)}%"


def pp(v: float) -> str:
    """Variação em pontos percentuais (v em fração: 0.006 -> 0,6 p.p.)."""
    s = "+" if v > 0 else "−" if v < 0 else ""
    return f"{s}{_br(abs(v) * 100, 1)} p.p."


def dias(v: float) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    return f"{_br(round(v), 0)} dias"


def d(v: float) -> str:
    """Dias sem a palavra, para sequências como 96 → 125."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    return _br(round(v), 0)


def gmroi(v: float) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    return _br(v, 2)


def lista(itens: list[str], conj: str = "e") -> str:
    itens = [i for i in itens if i]
    if not itens:
        return ""
    if len(itens) == 1:
        return itens[0]
    return ", ".join(itens[:-1]) + f" {conj} " + itens[-1]
