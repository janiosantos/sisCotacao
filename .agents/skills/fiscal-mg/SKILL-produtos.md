---
name: fiscal-mg
description: Orientar regras e integrações fiscais brasileiras com foco em Minas Gerais, incluindo contextos de NF-e/NFC-e e SEFAZ-MG. Usar quando a tarefa envolver UF MG, operações internas, validação de documentos ou legislação estadual.
---

# Fiscal MG

## Procedimento

1. Identificar o tipo de documento, ambiente, operação e participantes.
2. Separar regra nacional, regra estadual e parametrização da empresa.
3. Consultar fontes oficiais e registrar URL, data de acesso e vigência.
4. Modelar exceções sem duplicar a regra padrão.
5. Exigir homologação antes de produção.

Tratar qualquer código ou alíquota não confirmado como `A CONFIRMAR`. O agente deve pedir validação do responsável fiscal antes de concluir uma implementação que altere o documento fiscal.
