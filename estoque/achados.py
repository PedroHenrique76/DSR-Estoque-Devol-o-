"""Escrita automática da análise: achados, destaque e plano de ação.

As regras abaixo reproduzem o raciocínio usado nas análises manuais de out–nov/2026.
Se existir analises/AAAA-MM-DD.json, cada chave presente nele (achados, destaque,
plano, observacoes) substitui a versão automática. Assim dá para revisar o texto à mão
sem mexer no código, e o automático continua cobrindo o que não foi revisado.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from comum import formato as f
from .indicadores import Analise


def _ok(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def _seq(vals) -> str:
    return " → ".join(f.d(v) for v in vals)


def _cob(r) -> str:
    """'92 → 64 dias' usando a cobertura da comparação e a atual."""
    if r.get("novo", False) or not _ok(r.get("dde_c")):
        return f"novo, {f.dias(r['dde'])}"
    return f"{f.d(r['dde_c'])} → {f.dias(r['dde'])}"


_MINUSCULAS = {"DE", "DA", "DO", "DAS", "DOS", "E", "LA", "LOS"}
_SIGLAS = {"ASA", "ERS", "JBS", "CRS", "CNA", "SA", "ME", "CD", "H&L", "B", "S", "LR", "IVL"}


def _palavra(w: str) -> str:
    nucleo = w.strip(".()/")
    if nucleo in _SIGLAS or "." in nucleo.strip(".") or (nucleo.isalpha() and not re.search(r"[AEIOUÁÉÍÓÚÂÊÔÃÕ]", nucleo)):
        return w
    return "'".join(p[:1].upper() + p[1:].lower() for p in w.split("'")) if w[:1] != "(" else "(" + _palavra(w[1:])


def _nome(r) -> str:
    """Nome curto para texto corrido: 'BEBIDAS GRASSI DO BRASIL' -> 'Bebidas Grassi do Brasil'.
    Siglas (CRS, JBS, J.G.S.M) ficam em maiúsculas."""
    s = r["curto"]
    if not s.isupper():
        return s
    out = [w.lower() if i and w in _MINUSCULAS else _palavra(w) for i, w in enumerate(s.split())]
    out[0] = out[0][:1].upper() + out[0][1:]
    return " ".join(out)


def efeito_taxa_margem(a: Analise) -> pd.DataFrame:
    """Quanto da variação de margem vem da mudança de margem % de cada fornecedor (sobre a venda atual)."""
    df = a.df[a.df.venda_c.notna() & (a.df.venda > 0) & (a.df.venda_c > 0)].copy()
    df["efeito"] = (df.mpct - df.mpct_c) * df.venda
    return df


def _verbo(n: int, sing: str, plur: str) -> str:
    return sing if n == 1 else plur


# ============================================================================= achados
def _evolucao(a: Analise) -> dict | None:
    if not a.tem_comp:
        t = a.tot
        return {"classe": "info", "tag": "foto inicial", "html":
                f"<b>Primeira foto da série.</b> Estoque de {f.mi(t['estoque'])} para uma venda de {f.mi(t['venda'])} "
                f"no mês: {f.dias(t['dde'])} de cobertura, GMROI {f.gmroi(t['gmroi'])} e {f.mi(t['excesso'])} acima de "
                f"{a.cfg['cobertura_alvo_dias']} dias."}
    t, c = a.tot, a.tot_comp
    gap = (a.atual.data - a.comp.data).days
    mesmo_ponto = 25 <= gap <= 40
    dE, dV = t["estoque"] - c["estoque"], t["venda"] / c["venda"] - 1
    melhor = dE <= 0 and t["dde"] <= c["dde"]
    ddes = [s["dde"] for s in a.serie]
    extremo = ""
    if len(ddes) >= 3:
        if t["dde"] <= min(ddes) + 1e-9:
            extremo = f", a melhor das {len(ddes)} fotos"
        elif t["dde"] >= max(ddes) - 1e-9:
            extremo = f", a pior das {len(ddes)} fotos"
    ref = f"De {a.comp.rotulo} para {a.atual.rotulo}" + (" (mesmo ponto do mês)" if mesmo_ponto else "")
    if melhor:
        cab = f"O estoque caiu {f.mil(-dE)} enquanto a venda {'subiu' if dV >= 0 else 'caiu'} {f.pct(abs(dV))}."
    else:
        cab = f"O estoque subiu {f.mil(dE)} para uma venda que {'subiu' if dV >= 0 else 'caiu'} {f.pct(abs(dV))}."
    txt = (f"<b>{cab}</b> {ref}, o estoque foi de {f.mi(c['estoque'])} para {f.mi(t['estoque'])}. "
           f"A cobertura foi de {f.d(c['dde'])} para {f.dias(t['dde'])}{extremo}, o GMROI de {f.gmroi(c['gmroi'])} "
           f"para {f.gmroi(t['gmroi'])} e o capital acima de {a.cfg['cobertura_alvo_dias']} dias de "
           f"{f.mi(c['excesso'])} para {f.mi(t['excesso'])}.")
    if not mesmo_ponto:
        txt += (f" Atenção: as fotos têm {gap} dias de diferença e podem estar em pontos diferentes do mês; "
                "parte da variação pode ser calendário de compra.")
    return {"classe": "good" if melhor else "crit", "tag": "mês contra mês" if mesmo_ponto else "evolução", "html": txt}


def _margem(a: Analise) -> dict | None:
    if not a.tem_comp:
        return None
    t, c = a.tot, a.tot_comp
    dpp = t["mpct"] - c["mpct"]
    if abs(dpp) < 0.002:
        return {"classe": "info", "tag": "margem", "html":
                f"<b>Margem estável em {f.pct(t['mpct'])}</b> (era {f.pct(c['mpct'])} em {a.comp.rotulo})."}
    mps = [s["mpct"] for s in a.serie]
    extremo = ""
    if len(mps) >= 3:
        if t["mpct"] <= min(mps) + 1e-12:
            extremo = f", a mais baixa das {len(mps)} fotos"
        elif t["mpct"] >= max(mps) - 1e-12:
            extremo = f", a mais alta das {len(mps)} fotos"
    dV, dM = t["venda"] - c["venda"], t["margem"] - c["margem"]
    df = efeito_taxa_margem(a)
    lado = df.nsmallest(3, "efeito") if dpp < 0 else df.nlargest(3, "efeito")
    nomes = [f"{_nome(r)} ({f.pct(r['mpct_c'])} → {f.pct(r['mpct'])})" for _, r in lado.iterrows()]
    # a variação se repete fora dos três maiores? (separa efeito de mix)
    top3 = set(a.df.nlargest(3, "venda").forn)
    fora = a.df[~a.df.forn.isin(top3)]
    fora_c = a.por_foto[a.comp.data]
    fora_c = fora_c[~fora_c.forn.isin(top3)]
    m_fora, m_fora_c = fora.margem.sum() / fora.venda.sum(), fora_c.margem.sum() / fora_c.venda.sum()
    caiu = dpp < 0
    txt = (f"<b>A margem {'caiu' if caiu else 'subiu'} de {f.pct(c['mpct'])} para {f.pct(t['mpct'])}{extremo}.</b> "
           f"A venda {'subiu' if dV >= 0 else 'caiu'} {f.mil(abs(dV))} e a margem bruta em reais variou {f.sinal(dM)}. "
           f"A mudança de margem % pesou mais em {f.lista(nomes)}. ")
    if (m_fora - m_fora_c) * dpp > 0 and abs(m_fora - m_fora_c) >= 0.002:
        txt += (f"Fora dos três maiores fornecedores a margem também {'caiu' if caiu else 'subiu'} "
                f"({f.pct(m_fora_c)} → {f.pct(m_fora)}), então não é só mix. ")
    if caiu:
        txt += "Antes da próxima foto, separar o que foi preço de venda, custo de compra, desconto de escoamento e mix."
    else:
        txt += "Confirmar se é ganho recorrente (preço, custo) ou pontual (verba, bonificação lançada) antes de contar com ele."
    return {"classe": "crit" if caiu and abs(dpp) >= 0.004 else "warn" if caiu else "good", "tag": "margem", "html": txt}


def _movimentos(a: Analise) -> dict | None:
    if not a.tem_comp:
        return None
    df = a.df
    up, dn = df[df.d_estoque > 0], df[df.d_estoque < 0]
    big = df.reindex(df.d_estoque.abs().sort_values(ascending=False).index).head(3)
    partes = [f"{_nome(r)} ({f.sinal(r['d_estoque'])}, {_cob(r)})" for _, r in big.iterrows()]
    return {"classe": "info", "tag": "movimentos", "html":
            f"<b>Os maiores movimentos de estoque:</b> {f.lista(partes)}. No total, {len(up)} fornecedores aumentaram "
            f"estoque ({f.sinal(up.d_estoque.sum())}) e {len(dn)} reduziram ({f.sinal(dn.d_estoque.sum())})."}


def entidades_persistentes(a: Analise, minimo_fotos: int = 3) -> list[dict]:
    """Grupos de cadastros e fornecedores A/B cuja cobertura não melhorou em nenhuma foto da série."""
    alvo = a.cfg["cobertura_alvo_dias"]
    out = []
    if len(a.historico) < minimo_fotos:
        return out
    # grupos
    for nome, g in a.grupos.groupby("grupo"):
        g = g.sort_values("data")
        if len(g) < minimo_fotos or g.cadastros.iloc[-1] < 2:
            continue
        seq = g.dde.tolist()
        if all(seq[i] >= seq[i - 1] - 2 for i in range(1, len(seq))) and seq[-1] > alvo * 1.5:
            ult = g.iloc[-1]
            out.append({"nome": nome, "seq": seq, "estoque": ult.estoque, "excesso": ult.excesso,
                        "gmroi": ult.margem * 12 / ult.estoque if ult.estoque else np.nan,
                        "cadastros": int(ult.cadastros), "membros": a.df[a.df.grupo == nome].forn.tolist()})
    # fornecedores individuais relevantes
    agrupados = set(a.df[a.df.grupo.notna()].forn)
    for _, r in a.df[(a.df.abc.isin(["A", "B"])) & ~a.df.forn.isin(agrupados)].iterrows():
        seq = []
        for b in a.historico:
            x = a.por_foto[b.data]
            x = x[x.forn == r.forn]
            if len(x) and _ok(x.dde.iloc[0]):
                seq.append(float(x.dde.iloc[0]))
        if len(seq) >= minimo_fotos and all(seq[i] >= seq[i - 1] - 2 for i in range(1, len(seq))) \
                and seq[-1] > alvo * 1.5 and r.excesso >= 300_000:
            out.append({"nome": _nome(r), "seq": seq, "estoque": r.estoque, "excesso": r.excesso,
                        "gmroi": r.gmroi, "cadastros": 1, "membros": [r.forn]})
    return sorted(out, key=lambda e: -e["excesso"])


def _rank_excesso(a: Analise, ent: dict) -> int:
    outros = a.ativos[~a.ativos.forn.isin(ent["membros"])].excesso.tolist()
    return 1 + sum(1 for x in outros if x > ent["excesso"])


def _persistentes(a: Analise) -> list[dict]:
    res = []
    for e in entidades_persistentes(a)[:2]:
        cad = f"Os {e['cadastros']} cadastros somam" if e["cadastros"] > 1 else "Soma"
        res.append({"classe": "crit", "tag": e["nome"], "html":
                    f"<b>{len(e['seq'])} fotos seguidas sem melhora ({_seq(e['seq'])} dias).</b> {cad} "
                    f"{f.mi(e['estoque'])} de estoque, {f.mil(e['excesso'])} acima de {a.cfg['cobertura_alvo_dias']} dias "
                    f"({'o maior' if _rank_excesso(a, e) == 1 else 'o ' + str(_rank_excesso(a, e)) + 'º maior'} excesso da base) e GMROI {f.gmroi(e['gmroi'])}. "
                    "Sem trava de compra, o número não muda."})
    return res


def compras_sem_giro(a: Analise) -> pd.DataFrame:
    if not a.tem_comp:
        return a.df.iloc[0:0]
    lim, alvo = a.cfg["limites"], a.cfg["cobertura_alvo_dias"]
    persist = {m for e in entidades_persistentes(a) for m in e["membros"]}
    df = a.df[~a.df.forn.isin(persist)]
    cond = (df.d_estoque >= lim["aumento_relevante"]) & ((df.dde > alvo * 1.5) | (df.venda <= 0) | (df.estoque > df.venda * 12))
    return df[cond].sort_values("d_estoque", ascending=False)


def _compras(a: Analise) -> dict | None:
    sg = compras_sem_giro(a)
    if sg.empty:
        return None
    partes = []
    for _, r in sg.head(6).iterrows():
        if r.venda > 0 and r.estoque > r.venda * 12:
            partes.append(f"{_nome(r)} ({f.mil(r['estoque'])} em estoque para {f.reais(r['venda'])} de venda por mês)")
        else:
            partes.append(f"{_nome(r)} ({f.sinal(r['d_estoque'])}, {_cob(r)})")
    txt = f"<b>Entraram compras sem giro que as justifique.</b> {f.lista(partes)}."
    # estoque subiu enquanto a venda caiu
    q = a.df[(a.df.venda_c > 200_000) & (a.df.d_venda / a.df.venda_c < -0.15) & (a.df.d_estoque > 0)]
    for _, r in q.head(2).iterrows():
        txt += (f" {_nome(r)} está com {f.dias(r['dde'])} porque a venda caiu {f.pct(-r['d_venda'] / r['venda_c'], 0)} "
                "e o estoque não acompanhou.")
    return {"classe": "warn", "tag": "compras", "html": txt}


def _avancos(a: Analise) -> dict | None:
    if not a.tem_comp:
        return None
    df = a.df[(a.df.d_estoque < 0) & (a.df.estoque_c >= 300_000) & ((a.df.dde_c - a.df.dde) >= 15)]
    df = df.sort_values("d_estoque").head(6)
    if df.empty:
        return None
    partes = [f"{_nome(r)} ({_cob(r)}, {f.sinal(r['d_estoque'])})" for _, r in df.iterrows()]
    return {"classe": "good", "tag": "avanços", "html": f"<b>O que melhorou.</b> {f.lista(partes)}."}


def margens_negativas(a: Analise) -> pd.DataFrame:
    return a.df[(a.df.venda >= a.cfg["limites"]["venda_minima_ruptura"]) & (a.df.mpct < 0)].sort_values("estoque", ascending=False)


def _negativas(a: Analise) -> dict | None:
    neg = margens_negativas(a)
    if neg.empty:
        return None
    partes = [f"{_nome(r)} ({f.pct(r['mpct'])}, {f.mil(r['estoque'])} em estoque)" for _, r in neg.iterrows()]
    return {"classe": "warn", "tag": "margem negativa", "html":
            f"<b>{len(neg)} fornecedor(es) vendendo abaixo do custo:</b> {f.lista(partes)}. "
            "Só faz sentido com acordo da indústria ou consignação."}


def rupturas(a: Analise) -> pd.DataFrame:
    lim = a.cfg["limites"]
    return a.ativos[(a.ativos.dde < lim["cobertura_ruptura_dias"]) & (a.ativos.venda >= lim["venda_minima_ruptura"])]


def _ruptura(a: Analise) -> dict | None:
    r = rupturas(a)
    if r.empty:
        return None
    lim = a.cfg["limites"]["margem_baixa"]
    alta, baixa = r[r.mpct >= lim], r[r.mpct < lim]
    txt = ""
    if len(baixa):
        txt += (f"{f.lista([f'{_nome(x)} ({f.dias(x.dde)})' for _, x in baixa.iterrows()])} {_verbo(len(baixa), 'está', 'estão')} com menos de "
                f"{a.cfg['limites']['cobertura_ruptura_dias']} dias de cobertura, mas com margem abaixo de {f.pct(lim, 0)}, "
                "então a falta pesa pouco. ")
    if len(alta):
        txt += (f"{f.lista([f'{_nome(x)} ({f.dias(x.dde)}, margem {f.pct(x.mpct)})' for _, x in alta.iterrows()])} "
                f"{_verbo(len(alta), 'merece', 'merecem')} reposição, com teto de cobertura.")
    return {"classe": "info", "tag": "ruptura", "html": txt.strip()}


def _cauda(a: Analise) -> dict | None:
    t, c = a.tot, a.tot_comp
    partes = []
    if c:
        partes.append(f"A curva C foi de {f.d(c['dde_C'])} para {f.dias(t['dde_C'])}.")
        partes.append(f"Fornecedores sem venda: {c['sem_venda']} → {t['sem_venda']}, com {f.num(t['sem_venda_sku'])} SKUs "
                      f"e {f.mil(t['sem_venda_estoque'])} em estoque.")
        if a.saiu:
            partes.append(f"{len(a.saiu)} fornecedor(es) saíram da base desde {a.comp.rotulo}; se foi inativação, a limpeza está andando.")
        partes.append(f"Acima de {a.cfg['limites']['cobertura_parada_dias']} dias: {t['parados_n']} fornecedores com "
                      f"{f.mi(t['parados_estoque'])} (eram {c['parados_n']} e {f.mi(c['parados_estoque'])}).")
    else:
        partes.append(f"{t['sem_venda']} fornecedores sem venda, com {f.num(t['sem_venda_sku'])} SKUs e "
                      f"{f.mil(t['sem_venda_estoque'])} em estoque. {t['parados_n']} acima de "
                      f"{a.cfg['limites']['cobertura_parada_dias']} dias somam {f.mi(t['parados_estoque'])}.")
    return {"classe": "info", "tag": "cauda", "html": " ".join(partes)}


def achados_automaticos(a: Analise) -> list[dict]:
    regras = [_evolucao, _margem, _movimentos, _avancos]
    itens = [x for x in (r(a) for r in regras) if x]
    itens += _persistentes(a)
    itens += [x for x in (r(a) for r in [_compras, _negativas, _ruptura, _cauda]) if x]
    return itens


# ============================================================================= destaque
def destaque_automatico(a: Analise) -> dict | None:
    if not a.tem_comp:
        return None
    t, c, cc = a.tot, a.tot_comp, a.cfg["custo_capital_mensal"]
    dE, dpp = t["estoque"] - c["estoque"], t["mpct"] - c["mpct"]
    v01 = t["venda"] * 0.001
    if dE <= 0 and dpp < -0.002:
        return {"titulo": "O estoque está melhorando; a margem, não", "paragrafos": [
            f"A DSR vendeu {f.mil(t['venda'] - c['venda'])} a mais com {f.mil(-dE)} a menos de estoque. Mas a margem caiu "
            f"{f.pp(dpp).lstrip('−')}, e o GMROI foi só de {f.gmroi(c['gmroi'])} para {f.gmroi(t['gmroi'])}. Se o estoque saiu com "
            "desconto, a melhora de cobertura foi paga com margem.",
            f"A conta de referência: cada 0,1 ponto de margem sobre a venda atual vale cerca de {f.mil(v01)} por mês. "
            f"A queda desde {a.comp.rotulo} equivale a uns {f.mil(-dpp * t['venda'])} por mês, contra "
            f"{f.mil(-dE * cc)} mensais economizados ao carregar menos estoque (a {f.pct(cc)} a.m.)."]}
    if dE > 0:
        meses = (t["dde"] - c["dde"]) / 30
        return {"titulo": "Quanto custa o estoque a mais", "paragrafos": [
            f"O estoque subiu {f.mil(dE)} desde {a.comp.rotulo}. A {f.pct(cc)} a.m., isso custa cerca de "
            f"{f.mil(dE * cc)} por mês para carregar.",
            (f"Se foi compra de oportunidade, ela só se paga com desconto acima de ~{f.pct(max(meses, 0) * cc)} sobre a compra "
             f"(a cobertura subiu {f.d(t['dde'] - c['dde'])} dias). Sem condição comercial, a DSR financiou a meta da indústria.")
            if meses > 0 else
            "A cobertura não subiu porque a venda cresceu junto; vale confirmar se o volume novo tem giro."]}
    return {"titulo": "A regra de compra decide o próximo mês", "paragrafos": [
        "A cobertura melhorou sem perda de margem. Para manter, o pedido que deixa o fornecedor acima da cobertura-alvo "
        "precisa de aprovação; sem isso, cada fechamento de mês volta a encher o estoque."]}


# ============================================================================= plano
def plano_automatico(a: Analise) -> list[dict]:
    alvo, lim = a.cfg["cobertura_alvo_dias"], a.cfg["limites"]
    curto = []
    if a.tem_comp and a.tot["mpct"] - a.tot_comp["mpct"] <= -0.003:
        df = efeito_taxa_margem(a).nsmallest(3, "efeito")
        curto.append({"titulo": f"Explicar a queda de margem de {f.lista([_nome(r) for _, r in df.iterrows()])}.",
                      "texto": f"Separar preço de venda, custo de compra, desconto de escoamento e mix. Só pela queda de "
                               f"margem %, os três custam {f.mil(-df.efeito.sum())} por mês em relação a {a.comp.rotulo}."})
    for e in entidades_persistentes(a)[:2]:
        curto.append({"titulo": f"Travar {e['nome']} com um responsável nomeado.",
                      "texto": f"{len(e['seq'])} fotos sem melhora: {_seq(e['seq'])} dias. Bloquear a sugestão de compra "
                               f"no Winthor{' para os ' + str(e['cadastros']) + ' cadastros' if e['cadastros'] > 1 else ''} "
                               "e conferir na próxima foto que nenhum pedido entrou."})
    sg = compras_sem_giro(a)
    if len(sg):
        curto.append({"titulo": "Explicar as compras sem giro.",
                      "texto": f"{f.lista([_nome(r) for _, r in sg.head(6).iterrows()])}. Quem aprovou, com qual previsão "
                               "de venda, e se há direito de troca."})
    neg = margens_negativas(a)
    if len(neg):
        curto.append({"titulo": "Tratar as margens negativas.",
                      "texto": f"{f.lista([f'{_nome(r)} ({f.pct(r.mpct)})' for _, r in neg.iterrows()])}. "
                               "Vender abaixo do custo só com acordo da indústria."})
    rp = rupturas(a)
    rp = rp[rp.mpct >= lim["margem_baixa"]]
    if len(rp):
        curto.append({"titulo": f"Repor {f.lista([_nome(r) for _, r in rp.iterrows()])} com teto de cobertura.",
                      "texto": "Margem acima de 10% e menos de "
                               f"{lim['cobertura_ruptura_dias']} dias de cobertura. Repor até a cobertura-alvo, não por lote."})
    if a.tem_comp and not (25 <= (a.atual.data - a.comp.data).days <= 40):
        curto.append({"titulo": "Tirar a próxima foto no mesmo ponto do mês.",
                      "texto": "A comparação limpa é sempre entre fotos do mesmo dia útil do mês."})

    baixa = a.ativos[(a.ativos.mpct < lim["margem_baixa"]) & (a.ativos.venda >= lim["venda_minima_ruptura"])].sort_values("mpct")
    medio = [
        {"titulo": "Aprovação obrigatória acima da cobertura-alvo.",
         "texto": f"Nenhum pedido que deixe o fornecedor acima do alvo sai sem aprovação de quem responde pelo estoque, "
                  f"incluindo compras de fechamento. Ponto de partida: curva A {alvo - 10}–{alvo} dias, B {alvo}–{alvo + 15}, "
                  "C sob demanda, ajustado pelo lead time de cada indústria."},
        {"titulo": "Teto de cobertura para reposição.",
         "texto": "A sugestão de compra deve mirar a cobertura-alvo, não um lote arbitrário."},
    ]
    if a.tem_comp and a.tot["mpct"] < a.tot_comp["mpct"]:
        medio.append({"titulo": "Piso de margem para ações de escoamento.",
                      "texto": "Desconto para girar estoque passa por aprovação, com a conta do desconto contra o custo de carregar."})
    if len(baixa):
        medio.append({"titulo": f"Revisar margem dos fornecedores abaixo de {f.pct(lim['margem_baixa'], 0)}.",
                      "texto": f"{f.mi(baixa.estoque.sum())} em estoque ({f.pct(baixa.estoque.sum() / a.tot['estoque'])} do total). "
                               f"Os piores: {f.lista([f'{_nome(r)} ({f.pct(r.mpct)})' for _, r in baixa.head(7).iterrows()])}."})

    parados = a.ativos[a.ativos.dde > lim["cobertura_parada_dias"]].sort_values("estoque", ascending=False)
    longo = []
    if len(parados):
        longo.append({"titulo": "Liquidar a cauda parada.",
                      "texto": f"{len(parados)} fornecedores acima de {lim['cobertura_parada_dias']} dias somam "
                               f"{f.mi(parados.estoque.sum())}: {f.lista([_nome(r) for _, r in parados.head(7).iterrows()] + ['outros'])}."})
    t = a.tot
    longo.append({"titulo": "Inativar o que não vende.",
                  "texto": f"{t['sem_venda']} fornecedores e {f.num(t['sem_venda_sku'])} SKUs sem venda, com "
                           f"{f.mil(t['sem_venda_estoque'])} em estoque: inativar cadastro e liberar endereços de picking."})
    longo.append({"titulo": "Medir o custo por m² do CD.",
                  "texto": "Com o custo mensal da operação e a ocupação por fornecedor (posições ou m²), calcular quanto da "
                           "margem o CD consome e quais fornecedores pagam o espaço que ocupam."})
    return [
        {"prazo": "Até a próxima foto", "titulo": "Explicar e travar", "itens": curto},
        {"prazo": "30–60 dias", "titulo": "Regra de compra", "itens": medio},
        {"prazo": "60–90 dias", "titulo": "Limpar e medir", "itens": longo},
    ]


# ============================================================================= observações
def observacoes(a: Analise) -> list[str]:
    t, alvo = a.tot, a.cfg["cobertura_alvo_dias"]
    obs = [
        f"Cobertura (DDE) = estoque ÷ venda mensal × 30, como na planilha. Usa venda a preço; com estoque a custo, os dias "
        f"reais são maiores (~{f.d(t['dde_custo'])} no total).",
        f"GMROI = margem mensal × 12 ÷ estoque. Margem % = margem ÷ venda. Curva ABC: "
        f"{f.pct(a.cfg['curva_abc'][0], 0)} / {f.pct(a.cfg['curva_abc'][1], 0)} da venda acumulada. "
        f"Excesso = estoque acima de {alvo} dias de venda.",
    ]
    if a.tem_comp:
        obs.append(f"Comparações por fornecedor e indicadores do topo usam {a.comp.rotulo_longo}. "
                   "As demais fotos aparecem na evolução.")
    for aviso in a.atual.avisos:
        obs.append("Base atual: " + aviso)
    obs.append(f"Valores por m² usam a área total de {f.num(a.cfg['area_m2'])} m². A área útil de armazenagem é menor.")
    obs.append("A análise é por fornecedor. Decisões de corte e compra precisam do nível SKU, com validade e lead time.")
    return obs


# ============================================================================= montagem
def montar(a: Analise, pasta_analises: Path | str) -> dict:
    texto = {
        "achados": achados_automaticos(a),
        "destaque": destaque_automatico(a),
        "plano": plano_automatico(a),
        "observacoes": observacoes(a),
        "revisado": [],
    }
    arq = Path(pasta_analises) / f"{a.atual.data:%Y-%m-%d}.json"
    if arq.exists():
        manual = json.loads(arq.read_text(encoding="utf-8"))
        for k in ["achados", "destaque", "plano", "observacoes"]:
            if k in manual:
                texto[k] = manual[k]
                texto["revisado"].append(k)
    return texto
