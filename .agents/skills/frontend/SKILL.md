# SKILL — Frontend

## Princípios

- Frontend apresenta estado e solicita ações ao backend.
- Não implementar regras tributárias.
- Não duplicar fórmulas fiscais.
- Não armazenar segredos.
- Validar UX, mas manter validação de negócio no backend.

## Fiscal

O frontend deve conseguir apresentar:

- situação fiscal;
- CFOP;
- CST/CSOSN;
- impostos;
- alertas;
- necessidade de revisão;
- justificativa do cálculo.

Quando o backend retornar `FISCAL_REVIEW_REQUIRED`, a interface deve impedir emissão automática e orientar o usuário.
