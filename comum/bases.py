"""Extrações do Winthor salvas por data: AAAA-MM-DD.xlsx, onde a data do nome é a data de corte."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path


def data_do_arquivo(caminho: Path) -> date:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", caminho.stem)
    if not m:
        raise ValueError(
            f"Não achei a data no nome de {caminho.name}. Renomeie como AAAA-MM-DD.xlsx (ex.: 2026-11-03.xlsx)."
        )
    return date(int(m[1]), int(m[2]), int(m[3]))


def listar_bases(pasta: Path | str) -> list[Path]:
    pasta = Path(pasta)
    arquivos = [p for p in pasta.glob("*.xlsx") if not p.name.startswith("~$")]
    return sorted(arquivos, key=data_do_arquivo)
