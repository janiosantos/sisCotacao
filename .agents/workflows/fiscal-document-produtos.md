# Workflow: Documento Fiscal

1. Criar rascunho comercial.
2. Resolver TaxRule pela operação e vigência.
3. Criar snapshot dos itens e valores.
4. Validar consistência fiscal e numeração.
5. Gerar XML e transmitir com idempotência.
6. Persistir protocolo e resposta.
7. Atualizar estado para autorizado, rejeitado ou contingência.
8. Gerar eventos contábeis após o ponto definido pela política da empresa.
9. Preservar XML, histórico e auditoria.
