"""Formatação das planilhas de indicadores: cabeçalho escuro, largura das colunas e formato numérico pelo nome."""
from __future__ import annotations


def formatar(xw, inteiros: tuple[str, ...] = ("Cobertura", "SKUs", "Fornecedores", "venda", "Sem")) -> None:
    """`inteiros`: trechos do nome de coluna que pedem formato sem casas (exceto colunas com "Venda")."""
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
            elif any(k in nome for k in inteiros) and "Venda" not in nome:
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
