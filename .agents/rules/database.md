# Regras de Banco de Dados

1. Toda alteração de schema exige migration versionada.
2. Não alterar produção manualmente como procedimento normal.
3. Não utilizar FLOAT/REAL/DOUBLE para dinheiro ou tributos.
4. Utilizar NUMERIC/Decimal para valores monetários.
5. Preservar histórico fiscal e financeiro.
6. Usar foreign keys e constraints quando apropriado.
7. Evitar DELETE destrutivo de dados históricos.
8. Alterações incompatíveis devem seguir estratégia Expand → Migrate → Switch → Cleanup.
9. Migrations devem ser revisáveis e testadas.
10. Índices devem ser criados para consultas críticas sem duplicação desnecessária.
11. Dados fiscais devem permitir rastrear a regra e versão utilizada.
