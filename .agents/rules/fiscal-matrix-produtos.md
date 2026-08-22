# Regra de Matriz Fiscal

O Motor Fiscal recebe o SKU e o grupo de tributação, mas decide por contexto: natureza da operação, UF de origem, UF de destino, tipo de cliente, finalidade, regime tributário, data de vigência e indicadores de ST/DIFAL/benefício.

Modelar `naturezas_operacao`, `grupo_tributacao`, `matriz_fiscal_icms` e `matriz_fiscal_pis_cofins` com versão, vigência, prioridade, fonte e estado. Não codificar CFOP, CST/CSOSN ou alíquotas diretamente no frontend.

A matriz deve devolver códigos e parâmetros aplicáveis, além de avisos. Exemplos como CFOP 5102, 5405 ou 6102 são somente exemplos de contexto e devem ser confirmados pelo responsável fiscal antes de produção.
