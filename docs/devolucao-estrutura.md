# Análise de devolução — estrutura

Análise separada da de estoque, no mesmo repositório e com a mesma base técnica (leitura de extrações
do Winthor por data, indicadores em Python, painel HTML, relatório PDF, Excel, texto automático com
revisão à mão). As duas conversam em um ponto: mercadoria devolvida que volta avariada ou parada vira
estoque sem giro, e devolução ao fornecedor é a saída para parte desse estoque.

## Perguntas que a análise responde

1. **Quanto voltou e quanto custa?** Valor, peso, volume e NFs devolvidas; taxa sobre o faturado.
2. **Por quê?** Motivos em Pareto: avaria, transporte, desacordo comercial (preço, pedido em
   duplicidade, produto errado), cliente ausente/recusa, vencido/validade curta.
3. **Onde nasce?** Por rota e carregamento, motorista e veículo, cliente, vendedor (RCA),
   fornecedor e produto, filial.
4. **Para onde vai?** Reaproveitado ao estoque, avariado (perda), devolvido ao fornecedor
   (recuperado), ainda pendente.
5. **O processo funciona?** Tempo da chegada até a conferência e a baixa; pendências envelhecidas.
6. **Quanto se recupera do fornecedor?** Valor enviado, crédito recebido e crédito pendente por
   fornecedor, com prazo.

## Indicadores

| Bloco | Indicador | Definição |
|---|---|---|
| Volume | Valor devolvido | Soma do valor das NFs de devolução de cliente no período |
| | Taxa de devolução | Valor devolvido ÷ valor faturado no mesmo período e recorte |
| | Peso e volume devolvidos | Para o custo logístico do retorno |
| Motivo | Valor por motivo | Pareto; destaque para avaria, transporte e desacordo comercial |
| | Avaria + transporte | Soma das causas operacionais (responsabilidade da logística) |
| Origem | Taxa por rota, motorista, veículo | Cruza com romaneio e ZUQ; mínimo de faturamento para entrar no ranking |
| | Taxa por cliente e por RCA | Reincidência: clientes com devolução em 3 ou mais meses |
| | Taxa por fornecedor e produto | Liga com a análise de estoque |
| Destino | % reaproveitado | Voltou para estoque vendável |
| | % avariado | Perda; separa o que tem e o que não tem ressarcimento |
| | Perda líquida | Avariado − crédito recebido do fornecedor ou da transportadora |
| Processo | Tempo médio de entrada | Chegada da mercadoria até a conferência e a baixa |
| | Devoluções pendentes | NF de devolução lançada sem conferência ou baixa concluída; por faixa de idade (até 2 dias, 3 a 7, mais de 7) |
| Fornecedor | Devolvido a fornecedor | Valor enviado no período |
| | Crédito pendente | Enviado sem crédito; por fornecedor e idade |

Regras a fixar antes de construir (decisões, não código):
- Período padrão: mês corrente fechado ou mês até a data? Para comparação, usar o mesmo critério do
  estoque: mês contra mês no mesmo ponto.
- Lista oficial de motivos e o agrupamento em "operacional" (logística) e "comercial".
- Responsável por cada grupo de motivo, para o plano de ação ter dono.

## Extrações necessárias

Uma por período, salvas em `bases_devolucao/AAAA-MM-DD.xlsx` (passa a `bases/devolucao/` na reorganização do passo 1) (data de corte no nome).

**1. Itens devolvidos por cliente** (uma linha por item da NF de devolução)

| Coluna | |
|---|---|
| FILIAL, NUMNOTA_DEV, DT_ENTRADA, DT_CONFERENCIA, DT_BAIXA | Processo e pendência |
| NUMNOTA_ORIGEM, DT_FATURAMENTO | NF de venda que gerou a devolução |
| CODCLI, CLIENTE, CODUSUR (RCA) | |
| NUMCAR, CODMOTORISTA, MOTORISTA, PLACA | Carregamento da venda original |
| CODMOTIVO, MOTIVO | Tabela de motivos do Winthor |
| CODPROD, DESCRICAO, CODFORNEC, FORNECEDOR | Liga com estoque |
| QT, VALOR, PESO | |
| DESTINO | Reaproveitado / avaria / devolvido a fornecedor |

**2. Faturamento do período** no mesmo recorte (filial, rota, motorista, cliente, RCA, fornecedor),
para calcular as taxas. Sem ele, só há valores absolutos e o ranking favorece quem vende pouco.

**3. Devoluções a fornecedor** (uma linha por NF): FILIAL, NUMNOTA, DATA, CODFORNEC, FORNECEDOR,
VALOR, MOTIVO, DT_CREDITO, VALOR_CREDITO.

Rascunho da consulta 1: `sql/devolucao_clientes.sql` (validar tabelas e campos na base da DSR).

## Estrutura de código

```
dsr-estoque-devolucao/
├── CLAUDE.md
├── gerar.py                    # python gerar.py estoque | devolucao  [--base AAAA-MM-DD]
├── config.json                 # parâmetros do estoque (atual)
├── config_devolucao.json       # motivos, grupos de motivo, faixas de idade, mínimos de ranking
├── comum/                      # passo 1: extrair do pacote estoque o que é compartilhado
│   ├── formato.py              #   números no padrão brasileiro
│   ├── bases.py                #   data no nome do arquivo, conferência com a linha Total, avisos
│   ├── pagina.py               #   montagem do HTML (CSS, fontes, condicionais) e PDF
│   └── excel.py                #   escrita e formatação de planilhas
├── estoque/                    # análise atual (passa a importar de comum/)
├── devolucao/
│   ├── leitura.py              # itens devolvidos, faturamento, devoluções a fornecedor
│   ├── indicadores.py          # taxas, Pareto de motivos, origem, destino, aging, recuperação
│   ├── achados.py              # regras: motivo dominante, rota/motorista fora da curva,
│   │                           #   clientes reincidentes, pendências velhas, crédito parado
│   └── render.py               # dados para o painel e o relatório
├── templates/
│   ├── base.css                # identidade visual comum
│   ├── estoque.html / estoque.js
│   └── devolucao.html / devolucao.js
├── bases/
│   ├── estoque/                # (hoje em bases/; migra no passo 1)
│   ├── estoque_sku/
│   └── devolucao/
├── analises/
│   ├── estoque/
│   └── devolucao/
├── sql/
│   ├── extracao_sku.sql
│   └── devolucao_clientes.sql
├── testes/
└── saida/
    ├── estoque/AAAA-MM-DD/
    └── devolucao/AAAA-MM-DD/
```

## Painel de devolução (seções)

1. Indicadores do topo: valor devolvido, taxa sobre o faturado, % avaria + transporte, %
   reaproveitado, perda líquida, pendentes (quantidade e valor), cada um com variação contra o mês
   anterior.
2. O que os números dizem (achados automáticos com revisão à mão).
3. Pareto de motivos (barras horizontais, legível no celular).
4. Origem: ranking de rota, motorista e veículo por taxa, com o faturamento ao lado para não
   punir quem roda mais.
5. Clientes e RCAs reincidentes.
6. Destino da mercadoria e perda líquida.
7. Processo: tempo de entrada e pendências por idade.
8. Devolução a fornecedor e crédito pendente.
9. Plano de ação com dono por grupo de motivo.

No PDF, os mesmos blocos em versão estática, como no estoque.

## Ordem de construção

1. Extrair `comum/` do pacote `estoque` sem mudar nenhum número (os testes atuais garantem).
2. Validar a consulta de devolução de clientes e salvar a primeira extração.
3. `devolucao/leitura.py` com conferência (soma do valor devolvido contra o total da rotina do Winthor).
4. Indicadores e testes com a primeira base.
5. Painel e PDF.
6. Achados automáticos e plano.
7. Cruzamento com estoque: avaria parada no estoque por fornecedor e crédito pendente.
