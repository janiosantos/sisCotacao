# Regras Permanentes do Domínio Fiscal

1. Nunca inventar classificação ou tributação.
2. NCM não determina sozinho a tributação.
3. CFOP depende do contexto da operação.
4. CST/CSOSN é resultado de enquadramento e contexto.
5. ICMS, ICMS-ST, DIFAL e FCP devem possuir responsabilidades de cálculo separadas.
6. Regras fiscais devem possuir vigência.
7. Regras históricas não devem ser sobrescritas de forma destrutiva.
8. Toda regra relevante deve possuir fundamento legal.
9. O motor deve detectar ausência e conflito de regras.
10. Resultado fiscal de documento autorizado deve ser armazenado como snapshot.
11. Documento histórico não deve ser recalculado usando regra atual.
12. Alterações fiscais devem possuir testes de regressão.
13. Alíquotas, MVA, CEST, NCM, CFOP, CST, CSOSN e benefícios não devem ser hardcoded como regras permanentes.
14. Em caso de incerteza, bloquear a automação e retornar `FISCAL_REVIEW_REQUIRED`.
15. Frontend nunca decide tributação.
