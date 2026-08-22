# Regra Operacional — GTIN e SEM GTIN

| Situação | Valor transmitido | Ação |
|---|---|---|
| GTIN válido e aplicável | GTIN do SKU | Validar formato e manter no snapshot |
| Produto sem GTIN | `SEM GTIN` | Não gerar identificador fictício |
| GTIN inválido ou conflitante | Bloqueio ou revisão | Corrigir cadastro antes de emissão, conforme regra do documento |

A decisão de aceitar `SEM GTIN` deve ser compatível com o layout, o ambiente e o integrador utilizado. Guardar a justificativa e a validação realizada.
