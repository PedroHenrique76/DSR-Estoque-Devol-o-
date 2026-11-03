-- =============================================================================
-- Extração por SKU para a análise de estoque (Winthor / Oracle)
-- RASCUNHO A VALIDAR: nomes de tabelas e colunas seguem o padrão do Winthor
-- (PCPRODUT, PCFORNEC, PCEST, PCMOV), mas filtros de operação, tipo de custo e a
-- origem da validade precisam ser conferidos na base da DSR antes do uso.
--
-- Objetivo: uma linha por produto com estoque e venda, no mesmo critério da planilha
-- por fornecedor ("Venda Mês" = média mensal dos últimos 3 meses), para que a soma
-- por fornecedor bata com a extração que o projeto já usa.
--
-- Binds:
--   :filial     código da filial do CD (ex.: '1')
--   :data_corte data da foto (ex.: TO_DATE('01/12/2026','DD/MM/YYYY'))
-- =============================================================================
WITH venda AS (
    SELECT m.codprod,
           SUM(m.qt)                              AS qt_3m,
           SUM(m.qt * m.punit)                    AS venda_3m,
           SUM(m.qt * (m.punit - m.custofin))     AS margem_3m,   -- conferir: CUSTOFIN x CUSTOREAL
           MAX(m.dtmov)                           AS dt_ult_venda
      FROM pcmov m
     WHERE m.codfilial = :filial
       AND m.codoper   = 'S'                      -- conferir: só saída por venda (excluir bonificação/transferência?)
       AND m.dtcancel  IS NULL
       AND m.dtmov    >= ADD_MONTHS(TRUNC(:data_corte), -3)
       AND m.dtmov    <  TRUNC(:data_corte)
     GROUP BY m.codprod
),
estoque AS (
    SELECT e.codprod,
           e.qtestger                                      AS qt_estoque,
           e.qtreserv                                      AS qt_reservada,
           e.qtbloqueada                                   AS qt_bloqueada,
           e.qtestger * NVL(e.custofin, 0)                 AS valor_estoque,  -- conferir: critério do "Valor Estoque" da planilha
           e.dtultent                                      AS dt_ult_entrada
      FROM pcest e
     WHERE e.codfilial = :filial
)
SELECT f.codfornec,
       f.fornecedor,
       p.codprod,
       p.descricao,
       p.embalagem,
       p.qtunitcx,
       NVL(es.qt_estoque, 0)                 AS qt_estoque,
       NVL(es.qt_reservada, 0)               AS qt_reservada,
       NVL(es.qt_bloqueada, 0)               AS qt_bloqueada,
       NVL(es.valor_estoque, 0)              AS valor_estoque,
       ROUND(NVL(v.qt_3m, 0) / 3, 2)         AS qt_venda_mes,
       ROUND(NVL(v.venda_3m, 0) / 3, 2)      AS venda_mes,
       ROUND(NVL(v.margem_3m, 0) / 3, 2)     AS margem_mes,
       es.dt_ult_entrada,
       v.dt_ult_venda
       -- validade: incluir a menor data de validade em estoque por produto.
       -- Origem a confirmar na DSR (lote / endereçamento WMS).
  FROM pcprodut p
  JOIN pcfornec f      ON f.codfornec = p.codfornec
  LEFT JOIN estoque es ON es.codprod  = p.codprod
  LEFT JOIN venda v    ON v.codprod   = p.codprod
 WHERE NVL(es.qt_estoque, 0) <> 0
    OR NVL(v.qt_3m, 0) <> 0
 ORDER BY f.fornecedor, venda_mes DESC;
