# estoque-dsr — Gestão estratégica de estoque por fornecedor

Gera, a partir da extração do Winthor por fornecedor, a análise de estoque da DSR (CD Bahia):
indicadores, comparação com o mês anterior, achados escritos, plano de ação, painel HTML,
relatório PDF e planilha Excel. É a mesma construção feita à mão em out–nov/2026, agora em código.

## Instalação (uma vez)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium   # só para gerar o PDF
```

Python 3.10 ou mais novo.

## Uso no dia a dia

1. Exporte a planilha do Winthor (aba "Export", por fornecedor) e salve em `bases/` com a data da foto
   no nome: `bases/2026-12-01.xlsx`.
2. Rode:

```bash
python gerar.py
```

3. Pegue os arquivos em `saida/2026-12-01/`:

| Arquivo | Para quê |
|---|---|
| `Painel_Estoque_DSR_01-12-2026.html` | Painel interativo. Abre no navegador, funciona no celular e sem internet. É o arquivo para compartilhar por WhatsApp ou e-mail. |
| `Relatorio_Estoque_DSR_01-12-2026.pdf` | Relatório A4 com os mesmos indicadores; o mapa vira matriz, o simulador vira tabela de cenários e a tabela completa vira os 30 maiores. |
| `Indicadores_Estoque_DSR_01-12-2026.xlsx` | Abas Resumo (todas as fotos), Fornecedores (indicadores e variação) e Grupos (cadastros somados). |
| `analise_01-12-2026.json` | O texto usado no relatório, pronto para ser revisado (ver abaixo). |

Outras opções:

```bash
python gerar.py --base 2026-10-28          # gerar uma data antiga
python gerar.py --comparar 2026-10-16      # forçar a base de comparação
python gerar.py --todas                    # regerar todas as datas
python gerar.py --sem-pdf                  # sem PDF (não precisa do Playwright)
```

## Regra de comparação

Por padrão, a base atual é comparada com a base de **cerca de um mês antes (25 a 40 dias)**, para
comparar fotos do mesmo ponto do mês. Fotos de fechamento (dia 28) e de início de mês (dia 1º–3)
não são comparáveis entre si: em 28/10 o estoque subiu R$ 5,8 mi e voltou em 6 dias. Se não houver
base na janela, usa a anterior e o texto avisa que pode haver efeito de calendário.
**Recomendação: tirar a foto sempre no mesmo dia útil do início do mês.**

## Texto automático e revisão à mão

O código escreve os achados e o plano com as regras de `estoque/achados.py`:

- evolução do estoque, cobertura, GMROI e excesso contra a comparação;
- variação de margem, com os fornecedores que mais pesaram pela mudança de margem % e o teste "fora dos três maiores" (separa queda real de efeito de mix);
- maiores movimentos e avanços;
- grupos ou fornecedores A/B com **todas as fotos sem melhora** de cobertura (Flora, Bombril);
- compras sem giro (estoque subiu mais de R$ 100 mil com cobertura alta ou venda irrelevante);
- margens negativas, risco de ruptura (separando margem alta e baixa) e cauda parada;
- destaque com a conta de custo de capital contra margem;
- plano de ação em três prazos.

Para revisar o texto de uma data, copie `saida/<data>/analise_<data>.json` para
`analises/<AAAA-MM-DD>.json`, edite e rode de novo. Cada chave presente (`achados`, `destaque`,
`plano`, `observacoes`) substitui a automática; apague a chave para voltar ao automático. A chave
opcional `comparar_com` fixa a base de comparação daquela data. As análises de 28/10 e 03/11 já
estão revisadas em `analises/`, com o texto entregue na época.

## Parâmetros (`config.json`)

| Chave | Valor atual | O que muda |
|---|---|---|
| `area_m2` | 9000 | Indicadores por m² |
| `cobertura_alvo_dias` | 45 | Excesso, linhas do mapa, simulador, plano |
| `custo_capital_mensal` | 0,012 | Custo de carregar o estoque (premissa; troque pela taxa real) |
| `curva_abc` | 80% / 95% | Cortes da curva |
| `limites` | ver arquivo | Cobertura parada (180), ruptura (10), margem baixa (10%), aumento relevante (R$ 100 mil) |
| `grupos` | Flora, Selmi, Camil… | Fornecedores com mais de um cadastro, somados nas análises de grupo |
| `nomes_curtos` | lista | Como cada fornecedor aparece nos gráficos e textos |

## Estrutura

```
gerar.py               linha de comando
config.json            parâmetros
bases/                 extrações do Winthor (AAAA-MM-DD.xlsx)
analises/              textos revisados à mão por data
estoque/leitura.py     leitura e limpeza da planilha (linhas Total, CODFORNEC, duplicados, conferência com o Total)
estoque/indicadores.py cobertura, margem, GMROI, ABC, excesso, comparação, grupos
estoque/achados.py     regras que escrevem achados, destaque, plano e observações
estoque/render.py      painel HTML, relatório PDF, planilha Excel
estoque/formato.py     números no padrão brasileiro
templates/             HTML, CSS e JavaScript do painel e do relatório
fontes/                fontes embutidas (licença OFL, ver arquivos LICENSE)
testes/                conferência dos números das análises entregues
docs/historico.md      conclusões de cada foto e decisões de método
```

## Conferência

```bash
python -m pytest testes        # ou: python testes/test_projeto.py
```

Os testes conferem a soma com a linha Total de cada planilha, a remoção da linha duplicada da Flora
em 03/11 e os indicadores das quatro análises entregues.

## Definições

- Cobertura (DDE) = estoque ÷ venda mensal × 30 (venda a preço, como na planilha do Winthor).
- Cobertura a custo = estoque ÷ (venda − margem) × 30.
- Margem % = margem ÷ venda. GMROI = margem mensal × 12 ÷ estoque.
- Excesso = estoque acima de (venda diária × cobertura-alvo), só para fornecedores com venda.

## Limites conhecidos

- A análise é por fornecedor. Corte de compra e liquidação precisam do nível SKU, com validade e lead time.
- "Venda Mês" parece ser uma média de 3 meses (valores com frações de centavo); na virada do mês a janela muda.
- Próximo passo natural: trocar a planilha por consulta direta ao Oracle do Winthor. O ponto de entrada é
  `estoque/leitura.py: carregar_base`, que só precisa devolver as colunas FORNECEDOR, Venda Mês, Qtd SKU,
  Margem e Valor Estoque.
