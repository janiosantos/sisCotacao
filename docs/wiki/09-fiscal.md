# Fiscal

## Fiscal (`#/fiscal`)

**O que é?** Configuração, simulação, emissão e histórico fiscal. **Para que
serve?** Emitir documentos conforme contexto tributário e legislação vigente.
**Papel:** transforma produto + operação + contexto em resultado explicável.

1. Configure Emitente e integração no ambiente apropriado.
2. Revise perfil fiscal do produto, CFOP, CST/CSOSN, CEST e alíquotas.
3. Simule a operação com contexto correto.
4. Emita ou trate rejeição/contingência pelo fluxo indicado.
5. Consulte histórico, resultado e versão da regra.

As abas de CFOP, CST, CEST, IBPT, sugestões, NF-e e histórico apoiam esse fluxo.
Não deduza imposto apenas pelo NCM. Em dúvida, bloqueie para revisão fiscal.

## Quem pode usar?

Fiscal e Administrador configuram; emissão depende da ação RBAC específica. A
operação comercial não deve editar regra tributária durante o atendimento.

## Auditoria

O sistema deve preservar contexto, snapshot, regra, versão, retorno do provedor,
rejeição, contingência e responsável.
