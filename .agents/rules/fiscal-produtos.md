# Regra Fiscal

Não concluir tributação apenas a partir do produto. Avaliar, no mínimo, regime tributário, UF de origem, UF de destino, tipo de cliente, finalidade, tipo de operação, benefício fiscal e eventual substituição tributária.

A resolução deve ser determinística e auditável. Para cada resultado, guardar a regra/versão usada, data de vigência, entradas relevantes, arredondamentos e avisos.

Quando houver conflito entre regra do Produto e override da Variação, aplicar o override somente se estiver ativo, vigente, compatível com o contexto e justificado. Em qualquer outro caso, usar a regra do Produto ou bloquear por falta de parametrização.

Códigos e alíquotas devem ser validados contra fontes mantidas pelo projeto e revisão fiscal. Não preencher valores fictícios em produção.
