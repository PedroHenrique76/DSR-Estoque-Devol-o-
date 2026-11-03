# Histórico das análises — out–nov/2026

Conclusões de cada foto e decisões de método, para quem for continuar a série.

## Série

| Foto | Estoque | Venda mês | Cobertura | Margem | GMROI | Excesso > 45 dias |
|---|---|---|---|---|---|---|
| 01/10 | R$ 72,1 mi | R$ 31,7 mi | 68 dias | 14,9% | 0,79 | R$ 25,4 mi |
| 16/10 | R$ 70,6 mi | R$ 32,5 mi | 65 dias | 16,0% | 0,88 | R$ 22,5 mi |
| 28/10 | R$ 76,4 mi | R$ 32,8 mi | 70 dias | 15,5% | 0,80 | R$ 28,1 mi |
| 03/11 | R$ 70,6 mi | R$ 33,5 mi | 63 dias | 14,3% | 0,81 | R$ 21,7 mi |

## 01/10 — primeira foto

- R$ 72,1 mi para 68 dias de venda (~80 dias a custo). GMROI 0,79.
- O excesso está nos grandes: a curva A tem 70% do excesso. L'Oréal (92 dias, 17,7% do estoque para 13,0% da venda), Colgate e Flora somavam 49% do capital acima de 45 dias.
- Cauda: 137 fornecedores da curva C com 5% da venda e 22% dos SKUs; 70 fornecedores sem venda. Ganho operacional (endereços, cadastro), não financeiro.
- 8 fornecedores com mais de um cadastro (Flora com 4). Daí a configuração de `grupos`.
- Pendências abertas: Cervejaria Petrópolis (margem zero, 249 dias), saldos negativos (Jacobs, Vanisul).

## 16/10 — melhora concentrada

- Estoque −R$ 1,5 mi com venda +2,4%. Mas L'Oréal e Colgate sozinhas reduziram R$ 3,9 mi; 37 fornecedores aumentaram (+R$ 4,7 mi).
- Flora piorou (96 → 109 dias). Siena e Haleon entraram com mais de 500 dias de cobertura.
- Margem subiu para 16,0%, 96% disso em Unilever e Colgate. Hipótese levantada: verba ou bonificação pontual.

## 28/10 — fechamento de mês

- Estoque +R$ 5,8 mi em 12 dias; Unilever e L'Oréal explicaram 94% da alta.
- Margem caiu para 15,5%: a alta de 16/10 era em parte pontual.
- Flora pela terceira foto piorando (123 dias). Compras sem giro: Arrozeira Pelotas, Angelo Auricchio, Bela Vista, Perfumes Dana (de 5 para 103 dias após recomendação de reposição, origem do "teto de cobertura para reposição").
- Decisão de método: 16/10 é meio de mês e 28/10 é fechamento. Comparar as duas mistura calendário com gestão. Recomendado fixar a data de extração.

## 03/11 — primeira comparação mês contra mês

- Mesma posição do mês que 01/10: estoque −R$ 1,5 mi com venda +5,5%; cobertura 63 dias, a melhor da série.
- O volume do fechamento de 28/10 saiu em 6 dias (Unilever 59 → 50, L'Oréal 81 → 64): a piora de 28/10 era calendário.
- Margem 14,3%, a mais baixa da série. Venda +R$ 1,7 mi no mês com margem em reais estável (+R$ 50 mil). A queda aparece também fora dos três maiores, então não é só mix. Conta: −0,6 ponto de margem ≈ R$ 210 mil/mês, contra ~R$ 18 mil/mês de economia por carregar menos estoque.
- Flora na quarta foto sem melhora (125 dias). Bombril também sem melhora em nenhuma foto (69 → 96 dias), identificado pela regra automática.
- A base passou a vir com a coluna CODFORNEC e uma linha de detalhe repetida da Flora; a leitura descarta linhas de detalhe.

## Decisões de método

1. Comparar sempre fotos do mesmo ponto do mês (regra padrão do projeto).
2. Margem e estoque juntos: reduzir cobertura com desconto pode custar mais margem do que economiza em capital.
3. Cobertura-alvo inicial de 45 dias (A 35–45, B 45–60, C sob demanda), a ajustar pelo lead time de cada indústria.
4. Custo de capital de 1,2% a.m. é premissa; trocar pela taxa real.
5. Análise por fornecedor indica onde olhar; a decisão de compra é no nível SKU.
