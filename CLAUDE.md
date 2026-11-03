# CLAUDE.md — estoque-dsr

Contexto para o Claude Code trabalhar neste projeto.

## O que é

Análise estratégica de estoque por fornecedor da DSR (distribuidora do Grupo São Roque, CD Bahia,
Feira de Santana). Lê a extração do Winthor por fornecedor (planilha "Export"), calcula indicadores,
compara com a foto do mês anterior, escreve achados e plano de ação, e gera painel HTML, relatório PDF
e planilha Excel. Nasceu de quatro análises feitas à mão (01/10, 16/10, 28/10 e 03/11/2026); o
histórico e as decisões de método estão em `docs/historico.md` — leia antes de mudar regras.

Responda e escreva textos em português do Brasil. O público dos relatórios é a gerência e a diretoria
de logística; texto direto, números no padrão brasileiro (R$ 1,5 mi, 14,3%, 63 dias).

## Comandos

```bash
pip install -r requirements.txt
python -m playwright install chromium     # só para PDF
python gerar.py                           # base mais recente
python gerar.py --todas --sem-pdf         # todas as datas, sem PDF
python -m pytest testes                   # conferência dos números
```

Rode os testes depois de qualquer mudança em `estoque/leitura.py` ou `estoque/indicadores.py`.
Os valores esperados em `testes/test_projeto.py` são os dos relatórios já entregues; só mude um
deles se a mudança de número for intencional e explicada.

## Mapa do código

- `estoque/leitura.py` — leitura da planilha. Trata linha "Total", coluna CODFORNEC (desde 03/11 vem uma
  linha de detalhe repetida da Flora, descartada), fornecedores duplicados, estoque negativo, e confere a
  soma com a linha Total. Ponto de entrada para trocar a planilha por consulta Oracle: `carregar_base`.
- `estoque/indicadores.py` — cobertura (DDE), cobertura a custo, margem %, GMROI, excesso sobre a
  cobertura-alvo, curva ABC, comparação, grupos de cadastros, objeto `Analise`.
- `estoque/achados.py` — regras que escrevem achados, destaque, plano e observações. Manual tem
  prioridade: `analises/AAAA-MM-DD.json` substitui as chaves presentes.
- `estoque/render.py` — monta painel/relatório a partir de `templates/` e gera PDF (Playwright) e Excel.
- `templates/painel.js` — um script só para os dois modos (`MODO = "painel" | "relatorio"`). No
  relatório, mapa vira matriz, simulador vira tabela de cenários, tabela completa vira os 30 maiores.
- `config.json` — área (9.000 m²), cobertura-alvo (45), custo de capital (1,2% a.m., premissa),
  limites, grupos de cadastros, nomes curtos.

## Regras de negócio que não devem ser quebradas

- Cobertura = estoque ÷ venda mensal × 30 (mesma fórmula da planilha do Winthor).
- Comparação padrão: foto de 25–40 dias antes (mesmo ponto do mês). Fechamento (dia 28) e início de
  mês não são comparáveis; em 28/10 o estoque subiu R$ 5,8 mi e voltou em 6 dias.
- Margem e estoque andam juntos: uma redução de cobertura obtida com desconto pode custar mais margem
  do que economiza em capital. O destaque automático faz essa conta.
- Efeito de margem por fornecedor é medido pela mudança de margem % × venda atual (efeito de taxa), não
  pela variação da margem em reais (que mistura volume).
- Análise por fornecedor aponta onde olhar; decisão de compra é no nível SKU.

## Visual

Painel com paleta e fontes próprias (Archivo, Public Sans, IBM Plex Mono embutidas de `fontes/`),
tema claro e escuro, funciona no celular (testado em 390 px sem rolagem lateral). O relatório PDF tem
8 páginas A4; ao adicionar seções, confira que continua sem página sobrando só com rodapé.

## Próximos passos combinados

1. **Em andamento: análise por SKU.** Roteiro, formato da extração e prioridades em
   `docs/proximo-passo-sku.md`; rascunho da consulta Winthor em `sql/extracao_sku.sql` (a validar).
   As extrações vão para `bases_sku/`. A soma por fornecedor tem de bater com a base por fornecedor.
2. Ler direto do Oracle do Winthor em vez da planilha (falta a consulta SQL que gera a exportação).
3. Custo por m² do CD com o custo mensal da operação e a ocupação por fornecedor (posições ou m²).
4. Explicar a queda de margem de 01/10 para 03/11 (preço, custo, desconto, mix).
