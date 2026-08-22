# Regras de Negócio — Fiscal

A resolução fiscal combina cadastro, variante, empresa, regime, operação, origem/destino, cliente, finalidade, data e benefícios. A saída é congelada no FiscalItem quando o documento avança para envio/autorização.

IBPTTable, quando usada, deve ser central e versionada por vigência; não gravar alíquota estimada como propriedade fixa da variante. Falta de regra deve gerar pendência ou bloqueio, não zero silencioso.
