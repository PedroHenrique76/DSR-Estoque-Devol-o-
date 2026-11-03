# Próximo passo — análise por SKU

## Por quê

A análise por fornecedor diz **onde** está o problema; a decisão de compra, trava e liquidação é
por produto. Dentro de um fornecedor com 120 dias de cobertura costuma haver itens de giro bom e
itens parados que puxam a média. Sem o nível SKU, travar a compra de um fornecedor inteiro pode
gerar ruptura nos itens que giram.

## Fornecedores prioritários (base 03/11/2026)

| Fornecedor | Por que | Pergunta a responder |
|---|---|---|
| Flora (4 cadastros) | 4 fotos sem melhora, 125 dias, R$ 5,2 mi | Quais SKUs concentram o excesso e quais estão sendo comprados mesmo parados? |
| Bombril | 4 fotos sem melhora (69 → 96 dias), venda caindo | O estoque é de itens que perderam venda ou de compras recentes? |
| L'Oréal | Maior excesso individual (R$ 3,0 mi), melhorou no mês | O que sobrou acima de 45 dias tem validade curta? |
| Colgate | R$ 2,6 mi de excesso, margem caiu 1,2 ponto | Queda de margem é de poucos SKUs ou geral? |
| Unilever | Margem caiu para 11,9% | Quais SKUs perderam margem (preço, custo, ação)? |

## Extração necessária

Uma planilha ou consulta por foto, salva em `bases_sku/AAAA-MM-DD.xlsx`, com uma linha por produto:

| Coluna | Observação |
|---|---|
| CODFORNEC, FORNECEDOR | Mesmo nome da extração por fornecedor, para cruzar |
| CODPROD, DESCRICAO, EMBALAGEM | |
| QT_ESTOQUE, VALOR_ESTOQUE | Mesmo critério de valor da planilha atual |
| QT_RESERVADA, QT_BLOQUEADA | Separar estoque disponível de bloqueado |
| QT_VENDA_MES, VENDA_MES, MARGEM_MES | Média mensal de 3 meses, como "Venda Mês" |
| DT_ULT_ENTRADA, DT_ULT_VENDA | Identifica compra recente sem giro e item parado |
| VALIDADE_MIN | Menor validade em estoque (se o WMS tiver) |

Rascunho da consulta: `sql/extracao_sku.sql` (validar operações, custo e origem da validade).

**Conferência obrigatória:** a soma de `VALOR_ESTOQUE` e `VENDA_MES` por fornecedor tem de bater com a
extração por fornecedor da mesma data. Se não bater, o critério da consulta está diferente.

## O que construir

1. `estoque/leitura_sku.py`: leitura de `bases_sku/`, com a conferência contra a base por fornecedor.
2. Indicadores por SKU: cobertura, margem %, GMROI, excesso, curva ABC dentro do fornecedor, dias desde a última venda e a última entrada, risco de validade (cobertura maior que os dias até o vencimento).
3. Classificação de ação por SKU: **travar compra** (cobertura alta e entrada recente), **liquidar** (parado ou risco de validade), **repor** (cobertura baixa e margem boa), **rever preço** (margem abaixo de 10%).
4. Página de detalhe por fornecedor no painel e no PDF (Flora, Bombril, L'Oréal, Colgate, Unilever).
5. Lista exportável de SKUs para travar no Winthor, para o comprador agir sem redigitar.
