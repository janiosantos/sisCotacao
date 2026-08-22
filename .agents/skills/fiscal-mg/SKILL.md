# SKILL — Fiscal Minas Gerais (ERP Varejista)

> Escopo: domínio fiscal de ERP para varejo de materiais elétricos, hidráulicos, ferramentas, ferragens e materiais de construção, inicialmente em Minas Gerais.
>
> Esta skill define arquitetura e comportamento do software. Não substitui legislação vigente nem orientação tributária profissional. Parametrizações definitivas devem ser validadas em fonte oficial vigente.

## 1. Princípio central

O motor fiscal NÃO pode ser modelado como `NCM -> imposto`.

O resultado deve ser determinado por:

```text
Produto + classificação fiscal + regime + estabelecimento + UF origem/destino
+ operação + finalidade + destinatário + consumidor final + contribuinte
+ data da operação + legislação vigente + exceções
-> Resultado Fiscal
```

Toda regra fiscal deve ser versionada, explicável e auditável.

---

## 2. Hierarquia de fontes

Priorizar:

1. legislação federal aplicável;
2. CONFAZ;
3. Receita Federal;
4. Portal Nacional da NF-e;
5. SEF/MG;
6. RICMS/MG e anexos;
7. atos normativos e notas técnicas vigentes;
8. fontes secundárias apenas como apoio.

### Fontes oficiais principais

**RICMS/MG — Decreto nº 48.589/2023:**
https://www.fazenda.mg.gov.br/empresas/legislacao_tributaria/ricms_2023_seco/sumario2023seco.html

**Anexo VII — Substituição Tributária:**
https://www.fazenda.mg.gov.br/empresas/legislacao_tributaria/ricms_2023_seco/anexovii2023_1.html

**SEF/MG — cálculo/consulta de ST:**
https://www.fazenda.mg.gov.br/empresas/substituicao_tributaria/stminasgerais.html

**Anexo V — documentos fiscais:**
https://www.fazenda.mg.gov.br/empresas/legislacao_tributaria/ricms2023/anexov2023.pdf

**Portal Nacional NF-e — manuais:**
https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=ndIjl+iEFdE%3D

**CONFAZ:**
https://www.confaz.fazenda.gov.br/

**Leis estaduais MG:**
https://www.fazenda.mg.gov.br/empresas/legislacao_tributaria/leis/

Registrar sempre: norma, artigo/anexo/item, vigência, data da consulta, fonte e URL.

---

## 3. Proibição de legislação hardcoded

Nunca tratar como constantes permanentes:

- alíquotas;
- MVA/PMPF;
- NCM/CEST;
- CFOP;
- CST/CSOSN;
- benefícios;
- redução de base;
- diferimento;
- isenção;
- FCP;
- DIFAL;
- regras de ST.

Toda regra deve possuir, no mínimo:

```text
id
codigo
versao
status
vigencia_inicio
vigencia_fim
prioridade
fundamento_legal
fonte_oficial
observacoes
```

A data usada para selecionar a regra é a **data da operação**, não a data atual.

---

## 4. Produto e classificação fiscal

Separar cadastro comercial de perfil fiscal.

```text
Product
ProductFiscalProfile
NCM
NCMVersion
CEST
CESTVersion
FiscalProductClassification
```

### NCM

NCM é atributo fiscal do produto, mas não determina sozinho ST, CFOP, CST, CSOSN ou alíquota.

Permitir vigência/versionamento quando necessário.

### CEST

CEST deve ser associado ao enquadramento fiscal aplicável. Não preencher CEST apenas porque o NCM aparece em uma tabela: validar descrição, mercadoria e item legal.

### Origem

Manter origem da mercadoria como atributo independente. Não inferir origem pelo NCM.

### Categorias comerciais relevantes

Preparar o catálogo para:

- material elétrico;
- material hidráulico;
- tubos e conexões;
- registros e válvulas;
- ferramentas;
- acessórios de ferramentas;
- ferragens;
- parafusos/fixação;
- iluminação/lâmpadas;
- chuveiros/torneiras;
- mangueiras;
- químicos/adesivos;
- lubrificantes/aerossóis;
- soquetes/bocais;
- quadros/caixas;
- materiais de construção.

A categoria comercial não substitui a classificação fiscal oficial.

---

## 5. ICMS-ST

A existência de NCM compatível não basta para concluir que há ST.

O motor deve verificar:

1. NCM;
2. CEST, quando aplicável;
3. descrição/enquadramento;
4. capítulo/item do Anexo VII;
5. âmbito de aplicação;
6. UF origem;
7. UF destino;
8. operação;
9. finalidade;
10. destinatário;
11. responsabilidade tributária;
12. exceções;
13. vigência.

### Estrutura conceitual

```text
STRule
  id
  version
  ncm
  cest
  commodity_scope
  origin_uf
  destination_uf
  operation_type
  taxpayer_role
  application_scope
  calculation_method
  mva
  pmpf
  internal_rate
  validity
  legal_reference
```

### Base de cálculo

O motor deve suportar os métodos previstos na legislação vigente, inclusive preço fixado, PMPF, valor da operação acrescido dos componentes legais e MVA e hipóteses específicas de entrada.

Não implementar uma única fórmula universal de ST.

### MVA

Manter separadamente:

```text
mva_original
mva_adjusted
origin_rate
internal_rate
valid_from
valid_to
```

MVA ajustada somente quando a regra vigente determinar.

### ICMS próprio x ST

Sempre separar:

```text
icms_proprio
icms_st_base
icms_st
```

Nunca misturar os valores.

### Mercadoria já retida

Para hipóteses internas em que o contribuinte atua como substituído, o motor deve considerar a regra aplicável. O Anexo VII prevê, em hipóteses específicas, CST 060 ou CSOSN 500 para saída sem destaque.

Isso não autoriza aplicar 060/500 a qualquer mercadoria apenas por categoria.

### Exceções

Modelar inaplicabilidade da ST como regras explícitas e versionadas. Não usar uma flag simples `is_st = true` como fonte suficiente.

---

## 6. DIFAL

Separar:

```text
DIFAL_ENTRADA
DIFAL_SAIDA
```

### Entrada

Avaliar separadamente:

- uso/consumo;
- ativo imobilizado;
- revenda;
- mercadoria sujeita a ST;
- regime tributário;
- contribuinte;
- UF origem/destino.

### Base por dentro

Quando a legislação aplicável determinar cálculo por dentro, o motor deve receber explicitamente:

```text
valor_operacao
icms_origem
aliquota_interna
aliquota_interestadual
base_destino
difal
```

Fórmula conceitual:

```text
valor_sem_icms_origem = valor_operacao - icms_origem
base_destino = valor_sem_icms_origem / (1 - aliquota_interna)
difal = (base_destino * aliquota_interna) - icms_origem
```

A fórmula não deve ser aplicada a todos os cenários sem identificar a regra jurídica.

### Saída para consumidor final não contribuinte

Avaliar:

- UF destino;
- consumidor final;
- contribuinte ICMS;
- alíquota interestadual;
- origem;
- DIFAL;
- FCP/FCP-ST quando aplicável;
- responsabilidade pelo recolhimento;
- legislação vigente.

Não usar uma única regra percentual para todos os estados.

---

## 7. CFOP

CFOP é consequência do contexto da operação, não propriedade permanente do produto.

Famílias:

```text
1.xxx entradas internas
2.xxx entradas interestaduais
3.xxx entradas do exterior
5.xxx saídas internas
6.xxx saídas interestaduais
7.xxx saídas para exterior
```

O resolver deve considerar:

```text
direction
origin_uf
destination_uf
operation_type
purpose
customer_type
taxpayer_status
final_consumer
stock_origin
return_type
transfer
```

### Exemplos de candidatos

```text
5.102 venda de mercadoria adquirida/recebida de terceiros
5.405 venda de mercadoria sujeita a ST na condição de substituído
2.102 compra para comercialização
2.556 compra de material para uso/consumo
6.108 venda de mercadoria adquirida/recebida de terceiros destinada a não contribuinte
```

Esses códigos são **exemplos de cenários**, não regras universais. Validar descrição e contexto antes de selecionar.

---

## 8. CST e CSOSN

### Regime Normal

Suportar, entre outros, conforme enquadramento:

```text
00 tributada integralmente
10 tributada com ST
20 redução de base
60 ICMS cobrado anteriormente por ST
```

### Simples Nacional

Suportar CSOSN completo. Exemplos relevantes:

```text
102 tributada pelo Simples sem permissão de crédito
500 ICMS cobrado anteriormente por ST/antecipação
900 outros
```

Não limitar o motor a esses exemplos.

Nunca implementar:

```text
NCM -> CSOSN
```

Implementar:

```text
contexto + produto + regime + regra -> CST/CSOSN
```

---

## 9. Matriz de cenários

A matriz é baseline de engenharia, não tabela legal.

| Cenário | Regime | CFOP candidato | CST/CSOSN candidato | Resultado |
|---|---|---|---|---|
| Venda interna normal | Simples | 5.102 | 102 | segregação/tributação do DAS |
| Venda interna normal | Normal | 5.102 | 00 | ICMS próprio |
| Venda interna ST já retida | Simples | 5.405 | 500 | sem novo ICMS próprio, conforme regra |
| Venda interna ST já retida | Normal | 5.405 | 60 | sem novo ICMS próprio, conforme regra |
| Compra interestadual revenda | qualquer | 2.102 | conforme regra | crédito/DIFAL/ST conforme contexto |
| Compra interestadual uso/consumo | qualquer | 2.556 | conforme regra | DIFAL quando aplicável |
| Compra interestadual ativo | qualquer | conforme operação | conforme regra | DIFAL/crédito conforme regra |
| Venda interestadual contribuinte | conforme regime | 6.xxx | conforme regra | ICMS interestadual |
| Venda interestadual não contribuinte | conforme regime | 6.xxx | conforme regra | ICMS + DIFAL/FCP quando aplicável |
| Devolução | qualquer | conforme documento | conforme documento | espelho/contexto original |
| Transferência | qualquer | conforme operação | conforme regra | regras específicas |
| Complemento | qualquer | conforme finalidade | conforme regra | complemento fiscal |

Nunca codificar esta tabela como `switch` fixo.

---

## 10. FiscalContext

Criar objeto equivalente a:

```text
FiscalContext {
  company_id
  establishment_id
  tax_regime
  ie
  uf_origin
  uf_destination
  operation_type
  operation_date
  customer_type
  customer_taxpayer_status
  final_consumer
  merchandise_purpose
  stock_origin
  document_model
  document_series
  product_id
  ncm
  cest
  merchandise_origin
  quantity
  unit_price
  discount
  freight
  insurance
  other_expenses
  ipi
  original_document_id
}
```

Adicionar campos quando a regra exigir.

---

## 11. FiscalResult

```text
FiscalResult {
  status
  cfop
  cst
  csosn
  icms_base
  icms_rate
  icms_value
  icms_st_base
  icms_st_rate
  icms_st_value
  difal_base
  difal_rate
  difal_value
  fcp_base
  fcp_rate
  fcp_value
  rule_id
  rule_version
  legal_reference
  source_url
  matched_conditions[]
  warnings[]
  errors[]
}
```

### Status

```text
CALCULATED
RULE_NOT_FOUND
FISCAL_REVIEW_REQUIRED
FISCAL_RULE_CONFLICT
INVALID_PRODUCT_FISCAL_DATA
INVALID_OPERATION_CONTEXT
LEGISLATION_OUTDATED
CALCULATION_ERROR
```

Nunca retornar imposto zero silenciosamente por falta de regra.

---

## 12. Prioridade e conflitos

Usar prioridade determinística. Exemplo de engenharia:

```text
1000 regra específica por item legal
900  regra específica por CEST
800  NCM + contexto
700  categoria fiscal
500  regra geral
```

Os números são convenção de software, não prioridade jurídica.

Conflito entre regras de mesma prioridade:

```text
FISCAL_RULE_CONFLICT
```

Não escolher arbitrariamente.

---

## 13. Vigência

Toda regra:

```text
valid_from
valid_to
```

O cálculo usa `operation_date`.

Exemplo:

```text
Regra A: 01/01/2026 -> 30/06/2026
Regra B: 01/07/2026 -> NULL
```

Operação em 15/06 usa A mesmo que o sistema rode em agosto.

---

## 14. Snapshot fiscal

Após autorização, persistir o resultado efetivamente utilizado:

```text
FiscalSnapshot {
  document_id
  product_id
  rule_id
  rule_version
  operation_date
  calculation_date
  cfop
  cst
  csosn
  bases
  rates
  values
  legal_reference
  source_url
  calculation_inputs
  calculation_outputs
}
```

Documento histórico não pode depender da regra atual para continuar sendo interpretável.

---

## 15. Precisão e arredondamento

Usar `Decimal` no backend e `NUMERIC` no PostgreSQL.

Nunca usar `float/double` para dinheiro ou tributos.

Definir explicitamente:

- casas decimais;
- arredondamento;
- truncamento quando exigido;
- cálculo por item;
- totalização.

Toda fórmula crítica precisa de testes de precisão.

---

## 16. NF-e e NFC-e

Documentos:

```text
NF-e  = modelo 55
NFC-e = modelo 65
```

Não usar regra simplista `varejo = sempre NFC-e`. A seleção depende da operação, destinatário e legislação estadual vigente.

### MOC

A integração deve acompanhar o MOC vigente da NF-e/NFC-e e seus anexos de:

- leiaute;
- regras de validação;
- DANFE;
- contingência.

### Arquitetura

Separar:

```text
FiscalEngine
 -> XMLBuilder
 -> XMLValidator
 -> XMLSigner
 -> SEFAZAdapter
 -> Authorization
 -> Storage
```

SOAP/XML, certificados e particularidades do webservice não devem ficar dentro do domínio fiscal.

### NF-e

Suportar arquitetura para:

- emissão;
- assinatura;
- validação;
- transmissão;
- autorização;
- rejeição;
- cancelamento;
- inutilização;
- eventos;
- consulta;
- armazenamento XML/protocolo.

### NFC-e/MG

Considerar:

- modelo 65;
- XML;
- autorização;
- numeração por estabelecimento/série;
- contingência;
- QR Code/DANFE NFC-e;
- requisitos estaduais;
- credenciamento/autorização aplicável;
- CSC quando aplicável;
- MOC vigente.

O Anexo V do RICMS/MG disciplina características e autorização da NFC-e e remete ao MOC e ao Ajuste SINIEF 19/16.

---

## 17. Fluxo de emissão

```text
Pedido/Venda
 -> validação comercial
 -> FiscalContext
 -> FiscalEngine
 -> FiscalResult
 -> validação fiscal
 -> XML
 -> schema validation
 -> assinatura
 -> SEFAZ
 -> autorização/rejeição
 -> persistência
 -> snapshot fiscal
 -> DANFE/NFC-e
```

Status de documento e status de cálculo fiscal são coisas diferentes.

---

## 18. Devoluções

Não tratar devolução como venda negativa.

Avaliar:

```text
documento_original
produto_original
tributação_original
quantidade
motivo
tipo_devolução
regime
UF
```

Para ST, avaliar retenção, restituição, reembolso, complementação e regras do Anexo VII aplicáveis.

---

## 19. Transferências

Usar operação própria:

```text
TRANSFER
```

Não classificar automaticamente como venda. Aplicar regras vigentes de transferências e créditos.

---

## 20. Fiscal x estoque x financeiro

Separar:

```text
StockMovement
FiscalDocument
FiscalItem
FiscalSnapshot
FinancialEntry
```

Movimento de estoque não é sinônimo de operação fiscal; operação fiscal não deve ser representada apenas por lançamento financeiro.

---

## 21. Atualização fiscal

Processo obrigatório:

```text
Fonte oficial
 -> coleta
 -> identificar alteração
 -> nova versão
 -> validação
 -> testes
 -> homologação
 -> publicação
```

Estados:

```text
DRAFT
VALIDATED
PUBLISHED
SUPERSEDED
REVOKED
```

Nunca sobrescrever regra histórica publicada.

---

## 22. Auditoria

Registrar:

```text
quem
quando
o que
versão anterior
versão nova
fundamento
fonte
motivo
```

O ERP deve responder:

> Por que esta operação recebeu esta tributação?

A resposta deve indicar regra, versão, condições e fundamento.

---

## 23. Testes fiscais obrigatórios

Criar golden tests para:

### Simples

- venda interna tributada;
- venda interna ST;
- compra interestadual;
- uso/consumo;
- ativo;
- venda interestadual;
- devolução.

### Regime normal

- venda interna;
- venda ST;
- compra com crédito;
- compra sem crédito;
- uso/consumo;
- ativo;
- venda interestadual;
- consumidor final não contribuinte;
- devolução.

### ST

- aplicável;
- não aplicável;
- MVA original;
- MVA ajustada quando aplicável;
- PMPF;
- exceção;
- devolução;
- restituição/complementação quando aplicável.

### Motor

- regra inexistente;
- conflito;
- regra vencida;
- regra futura;
- classificação inválida;
- arredondamento;
- snapshot.

---

## 24. Checklist para nova regra

```text
[ ] fonte oficial
[ ] norma
[ ] artigo/anexo/item
[ ] vigência
[ ] condições
[ ] exceções
[ ] prioridade
[ ] fórmula
[ ] arredondamento
[ ] teste unitário
[ ] golden test
[ ] regressão
[ ] migration, se necessária
[ ] auditoria
[ ] resultado explicável
[ ] homologação
```

---

## 25. Proibições

O agente NÃO deve:

1. inventar NCM;
2. inventar CEST;
3. assumir ST pelo nome da categoria;
4. assumir CFOP pelo produto;
5. assumir CST/CSOSN pelo produto;
6. usar alíquota fixa para todo o ERP;
7. recalcular documento histórico com regra atual;
8. esconder ausência de regra retornando zero;
9. resolver conflito arbitrariamente;
10. colocar tributação no frontend;
11. alterar regra publicada sem nova versão;
12. usar fonte secundária como única autoridade;
13. implementar legislação nova sem testes;
14. misturar preço e tributação;
15. misturar ICMS próprio e ST;
16. tratar DIFAL como uma fórmula universal.

---

## 26. Regra de segurança operacional

Quando houver dúvida fiscal relevante:

```text
FISCAL_REVIEW_REQUIRED
```

O retorno deve informar:

- produto;
- NCM;
- CEST;
- operação;
- UF;
- regra candidata;
- motivo da dúvida;
- fonte consultada.

É preferível bloquear a emissão automática do que emitir documento com tributação arbitrária.

---

## 27. Validações normativas que devem ser revistas antes de codificar

Não congelar sem consulta à legislação vigente:

- obrigatoriedade de NF-e/NFC-e por cenário;
- DeSTDA;
- EFD ICMS/IPI e dispensas;
- DAPI;
- sublimites e efeitos do Simples;
- DIFAL de entrada/saída;
- cálculo por dentro;
- FCP;
- ST por NCM/CEST;
- MVA/PMPF;
- responsabilidade pelo recolhimento;
- devoluções;
- transferências;
- alterações por leis, convênios, ajustes, decretos e notas técnicas.

Uma regra encontrada em artigo, exemplo ou operação específica nunca deve ser generalizada para todo o ERP sem validação.
