-- =============================================================================
-- Itens devolvidos por clientes (Winthor / Oracle)
-- RASCUNHO A VALIDAR na base da DSR. Segue o padrão do Winthor:
--   PCNFENT  notas de entrada (devolução de cliente)
--   PCMOV    itens movimentados (CODOPER 'ED' = entrada por devolução)
--   PCESTCOM estorno de comissão, onde fica o motivo da devolução (CODDEVOL)
--   PCTABDEV tabela de motivos de devolução
--   PCNFSAID nota de venda de origem (NUMCAR = carregamento)
--   PCCARREG carregamento (motorista, veículo)
-- Conferir: TIPODESCARGA usado pela DSR para devolução de cliente, onde o destino
-- (reaproveitado/avaria) é registrado, e as datas de conferência e baixa no WMS.
--
-- Binds: :filial, :dt_ini, :dt_fim
-- =============================================================================
SELECT e.codfilial                       AS filial,
       e.numnota                         AS numnota_dev,
       e.dtent                           AS dt_entrada,
       -- dt_conferencia / dt_baixa: origem a confirmar (WMS)
       s.numnota                         AS numnota_origem,
       s.dtsaida                         AS dt_faturamento,
       e.codcli,
       c.cliente,
       s.codusur,
       s.numcar,
       cg.codmotorista,
       mt.nome                           AS motorista,
       v.placa,
       ec.coddevol                       AS codmotivo,
       td.motivo,
       m.codprod,
       p.descricao,
       p.codfornec,
       f.fornecedor,
       m.qt,
       m.qt * m.punit                    AS valor,
       m.qt * NVL(p.pesobruto, 0)        AS peso
       -- destino: reaproveitado / avaria / devolvido a fornecedor (a confirmar)
  FROM pcnfent  e
  JOIN pcmov    m  ON m.numtransent = e.numtransent
                  AND m.codoper     = 'ED'
  LEFT JOIN pcestcom ec ON ec.numtransent = e.numtransent
  LEFT JOIN pctabdev td ON td.coddevol    = ec.coddevol
  LEFT JOIN pcnfsaid s  ON s.numtransvenda = ec.numtransvenda
  LEFT JOIN pccarreg cg ON cg.numcar       = s.numcar
  LEFT JOIN pcempr   mt ON mt.matricula    = cg.codmotorista
  LEFT JOIN pcveicul v  ON v.codveiculo    = cg.codveiculo
  LEFT JOIN pcclient c  ON c.codcli        = e.codcli
  JOIN pcprodut p  ON p.codprod   = m.codprod
  JOIN pcfornec f  ON f.codfornec = p.codfornec
 WHERE e.codfilial = :filial
   AND e.tipodescarga IN ('6', '8')        -- conferir: tipos de devolução de cliente na DSR
   AND e.dtent BETWEEN :dt_ini AND :dt_fim
   AND m.dtcancel IS NULL
 ORDER BY e.dtent, e.numnota;
