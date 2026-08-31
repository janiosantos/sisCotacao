# Levantamento de lacunas do ERP Casa LM

**Data da auditoria:** 2026-08-31  
**Escopo:** backend Flask/PostgreSQL, frontend React/TypeScript/Vite/Tailwind, banco, fiscal, compras, estoque, financeiro, relatórios, UX/UI, integrações, testes e operação.  
**Objetivo:** identificar o que ainda precisa ser implementado ou complementado para uma loja de materiais elétricos, hidráulicos, ferragens e ferramentas operar com segurança e tomar decisões baseadas em dados.

## 1. Parecer executivo

O projeto possui uma fundação relevante: cadastro de produtos, categorias e marcas; busca e pré-venda; clientes, fornecedores e vendedores; preços e promoções; ciclo de cotação e pedido de compra; estoque por depósito, reservas, transferências, lotes e inventário; contas a pagar/receber, caixa, bancos e pagamentos; motor fiscal versionado; emissão estruturada via provedores; RBAC; outbox/webhooks; API pública; design system e melhorias de acessibilidade.

Ainda não deve ser considerado um ERP completo de varejo pronto para operação sem supervisão. As maiores lacunas estão no fechamento fiscal real, planejamento de reposição, inventário/valoração, recebimento de compras, devoluções financeiras/fiscais, relatórios gerenciais, integração operacional e testes ponta a ponta. A existência de um endpoint ou tela não significa que o processo tenha todas as etapas, permissões, auditoria, conciliação e tratamento de exceções exigidos no dia a dia.

### Classificação usada

- **P0:** bloqueia operação segura, conformidade ou decisões básicas; deve ser tratado antes de escalar o uso.
- **P1:** necessário para operação profissional recorrente e redução de perdas.
- **P2:** ganho importante de produtividade, gestão e integração.
- **P3:** evolução avançada após a base estar estável.
- **Existente:** já há implementação no código, mas pode haver complementos listados adiante.
- **Parcial:** há estrutura ou fluxo inicial, porém falta uma parte operacional relevante.
- **Ausente:** não foi identificado fluxo completo no repositório.

## 2. O que já existe e não deve ser refeito

| Área | Situação atual identificada |
|---|---|
| Catálogo | Produtos unificados, SKU, EAN, marca, grupo/subgrupo, família/atributos, imagens, unidades, busca e soft delete. |
| Venda | Pré-venda, orçamento/pedido, cliente, vendedor, tabela de preço, promoção, desconto com alçada, condição de pagamento, crédito, reserva e caixa. |
| Pós-venda | Acompanhamento, garantia, devolução/troca inicial. |
| Compras | Solicitação inicial, cotação, convite por fornecedor, portal de resposta, comparação, fornecedor preferencial, preço histórico inicial, tolerância e pedido de compra. |
| Estoque | Depósitos, saldos, limites mínimo/máximo, movimentos por fatos, transferência, reserva/liberação, lotes, expedição, inventário e reconciliação. |
| Financeiro | Caixa, contas a pagar/receber, parcelas, adiantamentos, anexos, centros de custo, bancos e conciliação manual inicial. |
| Cobrança | Adapters de boleto/PIX, provedores, webhooks assinados, logs, rechecagem e outbox. |
| Fiscal | Perfis e regras versionadas, snapshot, CFOP/CST/CSOSN/CEST/NCM/IBPT, emissão estruturada, NF-e/NFC-e inicial e integração Focus/TecnoSpeed. |
| Segurança | RBAC deny-by-default, overrides, auditoria RBAC, rate limit de login, revogação de tokens, limites de upload e proteção SSRF. |
| UI | Shell responsivo, componentes compartilhados, tabelas responsivas, foco/modal melhorados, navegação de pré-venda por teclado e base alinhada a Lightning Datatable/SLDS. |
| Integração | API pública de catálogo, CORS allowlist, imagens, portal do fornecedor, RQ/Redis, outbox e webhooks. |

Esses itens devem ser preservados e evoluídos mediante contratos, migrações versionadas e Expand/Migrate/Contract. Não é recomendável reescrever tudo para substituir o que já funciona.

## 3. Pendências P0

### P0.1 Fiscal real e prontidão de emissão

**Situação: parcial e bloqueadora.** Existem adapters e telas, mas a homologação com credenciais reais, validação completa do retorno, XSD, assinatura e contingência ainda não está fechada.

- Concluir homologação Focus NFe/SEFAZ para NF-e modelo 55 e NFC-e modelo 65, incluindo venda normal, venda para consumidor identificado, contribuinte, não contribuinte, interestadual, devolução, bonificação, transferência e entrada.
- Validar certificado A1, senha, cadeia, expiração, ambiente, série, numeração, CSC/QR Code e segregação por empresa/filial.
- Persistir e exibir o ciclo completo: pendente, enviado, autorizado, rejeitado, denegado, cancelado, inutilizado, contingência, transmitido em contingência e erro de consulta.
- Implementar consulta idempotente após timeout ou resposta ambígua antes de reenviar; não criar duplicidade fiscal por retry.
- Validar XML contra XSD oficial/provedor antes do envio e persistir request hash, referência, protocolo, chave, XML, DANFE/DANFCE e mensagens de rejeição.
- Implementar cancelamento, carta de correção quando aplicável, inutilização, consulta de situação e eventos de manifestação do destinatário para entradas.
- Completar NFC-e offline: fila local controlada, numeração, motivo, auditoria, relógio, transmissão posterior, tratamento de rejeição e reconciliação.
- Implementar entrada fiscal por XML: upload, leitura, conferência fornecedor/produto, vínculo por SKU/EAN/NCM, divergência, confirmação e geração de estoque/contas a pagar.
- Criar caixa de exceções fiscais com responsável, prazo, tentativa, mensagem amigável e ação de reprocessar.
- Alertar vencimento de certificado, CSC, token, credencial e competência de tabelas fiscais.
- Desativar qualquer regra estimada ou fallback em emissão real; quando faltar dado contextual, bloquear com `FISCAL_REVIEW_REQUIRED`.
- Validar a integração fiscal em staging com casos reais anonimizados e aprovar pelo responsável contábil/fiscal antes da produção.

### P0.2 Fechamento transacional de venda

**Situação: base endurecida, mas ainda precisa de prova operacional.** O código já possui transações, locks e idempotência em partes do fluxo; falta comprovar todos os caminhos e evitar lacunas entre venda, reserva, baixa, caixa, contas a receber e documento fiscal.

- Definir uma unidade de trabalho única para finalizar, cancelar, reabrir, devolver e faturar.
- Garantir atomicidade entre status do pedido, estoque físico/disponível, reserva, contas a receber, caixa, contabilidade e documento fiscal.
- Aplicar idempotency key por operação de negócio, não somente por webhook.
- Testar concorrência real de dois caixas vendendo o último saldo, duas pessoas recebendo o mesmo pagamento e duas emissões para o mesmo pedido.
- Implementar reconciliação de vendas: pedidos sem movimento, movimentos sem origem, títulos sem pedido, caixa sem recebimento e documento fiscal sem pedido.
- Proteger alteração de pedido após autorização, emissão fiscal, recebimento parcial ou baixa financeira.
- Definir estorno formal para cada efeito e impedir edição manual de eventos imutáveis.
- Criar fila de pendências e rotina de reconciliação para falhas depois do commit, sem depender de intervenção direta no banco.

### P0.3 Segurança de produção e recuperação

**Situação: hardening implementado, operação ainda pendente.**

- Publicar somente release aprovada, com imagem tagueada, backup, migration job, health check e smoke test.
- Validar TLS, renovação, cadeia do certificado, headers de segurança, cookies/token, CORS e webhook público no domínio definitivo.
- Criar backup automático do PostgreSQL, teste periódico de restauração e retenção definida.
- Definir RPO/RTO, procedimento de desastre, restauração de imagens e recuperação da outbox.
- Monitorar erros 5xx, latência, banco, fila RQ, Redis, espaço em disco, certificados, jobs mortos e webhooks não processados.
- Criar página operacional para jobs, outbox morta, falhas fiscais, integrações e rechecagens pendentes.
- Remover credenciais de teste, dados de demonstração, defaults inseguros e artefatos de desenvolvimento antes do uso real.

## 4. Compras e necessidades de reposição

### P1.1 Motor de necessidade de compra

**Situação: ausente como processo decisório.** Hoje há cadastro de limites e componentes de cotação, mas falta transformar dados do estoque em sugestão confiável de compra.

Implementar uma tela e uma API de planejamento por produto, depósito e fornecedor com:

- estoque físico;
- estoque reservado;
- estoque disponível;
- pedidos de venda abertos;
- pedidos de compra abertos;
- quantidade em trânsito;
- estoque mínimo e máximo;
- estoque de segurança;
- ponto de pedido;
- consumo médio diário/semanal/mensal;
- lead time real e variabilidade do fornecedor;
- dias de cobertura;
- lote mínimo, múltiplo, embalagem e unidade de compra;
- quantidade sugerida, data prevista de ruptura e data ideal do pedido;
- demanda sazonal, obras/projetos e compras sob encomenda;
- fornecedor preferencial e alternativas;
- justificativa legível para cada sugestão.

O cálculo deve separar disponível físico de disponível projetado. A sugestão não pode comprar novamente o que já está em pedido, reservado ou em trânsito. Deve suportar políticas configuráveis: ponto de pedido, máximo, lote a lote, compra sob demanda e revisão semanal/mensal.

### P1.2 Fluxo profissional de compras

- Completar a solicitação de compra com status, aprovação, prioridade, centro de custo, depósito destino, solicitante, justificativa e prazo.
- Permitir gerar cotação a partir da solicitação sem redigitar itens.
- Permitir consolidar solicitações compatíveis em uma cotação/pedido.
- Implementar aprovação por valor, fornecedor, margem, centro de custo e comprador.
- Controlar versões de cotação e prazo de validade de cada proposta.
- Comparar custo líquido completo: preço, desconto, IPI, ICMS, frete, condição, prazo, embalagem, quantidade mínima e marca.
- Registrar histórico de preço por fornecedor/produto/unidade e variação contra a última compra.
- Criar pedido de compra editável até aprovação e congelado após envio.
- Implementar envio por e-mail/WhatsApp via outbox, confirmação de leitura e reenvio auditado.
- Suportar pedido parcial, backorder, cancelamento de saldo, alteração aprovada e recebimento por item.
- Registrar previsão, atraso, entrega parcial e desempenho do fornecedor.
- Criar devolução ao fornecedor e vínculo com pedido, nota de entrada, lote e contas a pagar.
- Evitar que o portal do fornecedor seja a única fonte de negociação; importar resposta, anexos, XML e histórico.

### P1.3 Recebimento de compras

**Situação: parcial.** Há recebimento de pedido, mas falta um recebimento operacional completo.

- Conferência cega ou por pedido com código de barras/EAN e unidade de compra.
- Recebimento parcial por item, embalagem e conversão para unidade de estoque.
- Conferência de quantidade, preço, desconto, impostos, frete, lote, validade, número de série e marca.
- Divergência com tolerância configurável e aprovação do comprador.
- Geração automática de entrada de estoque, custo, conta a pagar e contabilização.
- Três vias: pedido de compra × recebimento físico × documento fiscal.
- Anexo de DANFE/XML/comprovantes e rastreabilidade de quem conferiu.
- Bloqueio de duplicidade por chave da NF e fornecedor.
- Conferência de qualidade, avaria, falta, sobra e quarentena.

## 5. Estoque e logística

### P1.4 Curva ABC/XYZ de verdade

**Situação: parcial.** O módulo `backend/catalog_server/abc.py` calcula uma classificação preventiva usando margem e giro estimados por linha. Isso é útil para bootstrap, mas não substitui uma ABC operacional baseada em histórico real.

Implementar:

- ABC por valor de consumo, receita, margem de contribuição, quantidade e frequência de venda.
- Período configurável e exclusão de vendas canceladas/devolvidas.
- Custo histórico do momento da venda, e não somente custo atual do cadastro.
- ABC por empresa, depósito, grupo, subgrupo, marca, fornecedor e família.
- Curva XYZ por variabilidade/intermitência da demanda.
- Matriz ABC-XYZ para definir frequência de contagem, nível de serviço e política de compra.
- Participação acumulada, corte configurável e tratamento de empate/itens sem venda.
- Comparação entre classificação anterior e atual, com data de cálculo e versão dos parâmetros.
- Drill-down até pedidos, movimentos e documentos que formaram o indicador.
- Separar visualmente “estimada” de “histórica”; não usar estimativa como fato de gestão depois que houver histórico.

### P1.5 Saldos, custos e valorização

- Definir método contábil oficial: custo médio móvel, custo específico ou outro aprovado pelo contador.
- Persistir custo por movimento/entrada para calcular CMV e margem histórica.
- Incluir frete, despesas acessórias, impostos recuperáveis/não recuperáveis e descontos no custo líquido conforme regra fiscal/contábil.
- Criar relatório de valorização por depósito, produto, lote e data de corte.
- Implementar revaloração com motivo, aprovação e lançamento contábil.
- Mostrar custo comprometido, custo em trânsito, custo reservado e custo disponível.
- Fechar períodos de estoque e impedir movimentos retroativos sem permissão especial.
- Criar rotina de reconciliação entre saldo derivado, fatos e estoque legado.
- Bloquear estoque negativo por regra configurável e permitir exceção somente com alçada auditada.

### P1.6 Inventário e contagem cíclica

**Situação: parcial.** Existe inventário e contagem, mas falta governança de inventário físico profissional.

- Planejar contagem cíclica por ABC/XYZ, depósito, endereço e data da última contagem.
- Congelar ou controlar movimentos durante a contagem.
- Permitir contagem cega, dupla contagem e reconciliação de divergência.
- Importar contagem por coletor, CSV/XLSX e código de barras.
- Aprovar ajuste por valor/percentual e exigir motivo.
- Fechar documento de inventário para impedir edição posterior.
- Relatar perdas, sobras, avarias e divergência por operador/depósito.
- Suportar endereço/bin, corredor, prateleira, gaveta e localização de picking.
- Imprimir lista, etiquetas e roteiro de contagem.

### P1.7 Lotes, séries, validade e rastreabilidade

- Parametrizar rastreabilidade por categoria: cabos e materiais normalmente por unidade/metragem; químicos, EPIs, colas e lubrificantes podem exigir lote/validade; ferramentas elétricas podem exigir série/garantia.
- Aplicar FEFO/FIFO quando a categoria exigir.
- Rastrear lote/série desde entrada até venda, devolução, garantia e recall.
- Alertar vencimento, quarentena, avaria e lote bloqueado.
- Permitir fracionamento de rolo/caixa com conversão auditada.
- Relacionar validade e número de série ao documento fiscal e ao cliente.

### P1.8 Armazém, separação e entrega

- Completar picking, conferência, packing e expedição com status e operador.
- Separar estoque disponível, reservado, em separação, em trânsito e entregue.
- Criar romaneio, retirada no balcão, entrega própria e transportadora.
- Calcular frete por região, peso, volume, valor e faixa de entrega.
- Integrar etiqueta, leitor de código de barras e impressão térmica.
- Controlar transferência em trânsito com confirmação no depósito destino.
- Registrar divergência de separação e entrega parcial.
- Implementar cancelamento de reserva por expiração e reserva para pedidos futuros.

## 6. Vendas, PDV e pós-venda

### P1.9 Pré-venda/PDV completo

O fluxo de teclado da pré-venda melhorou, mas ainda precisa ser fechado como operação de caixa:

- leitura por scanner e busca por EAN/SKU com baixa latência;
- aliases, códigos internos, fabricante, equivalentes e produtos substitutos;
- venda por metragem, peso, caixa, rolo, kit e conversão de unidade;
- seleção de depósito de retirada;
- orçamento, reserva, pedido, faturamento, retirada e entrega como estados distintos;
- múltiplas formas de pagamento na mesma venda;
- TEF/cartão, PIX, troco, sangria, suprimento, fechamento e conferência de caixa;
- cancelamento com alçada, estorno de pagamento e reversão de estoque;
- venda suspensa, retomada, troca de operador e múltiplos caixas/terminais;
- contingência operacional quando internet/provedor fiscal estiver indisponível;
- impressão NFC-e/DANFE, comprovante, orçamento e etiqueta;
- comissão calculada sobre base configurável, devoluções e recebimento;
- alerta de margem mínima, preço abaixo da tabela e desconto fora da alçada.

### P1.10 Devolução, troca, garantia e crédito

**Situação: parcial.** A tela registra devolução/troca, mas o processo precisa cobrir todos os efeitos.

- Vincular a devolução ao pedido, item, documento fiscal, lote/série e cliente.
- Validar prazo, motivo, condição do produto e política comercial.
- Gerar entrada de estoque, quarentena, descarte ou retorno ao fornecedor.
- Estornar parcela/conta a receber, gerar crédito de cliente ou diferença de troca.
- Emitir documento fiscal de devolução quando necessário.
- Registrar autorização de retorno/RMA e anexos.
- Criar fluxo de garantia com fornecedor, prazo, status, laudo e custo.
- Impedir devolução acima do vendido/devolvido e duplicidade de crédito.
- Relatar taxa de devolução por produto, fornecedor, vendedor e motivo.

### P2.11 Comercial e relacionamento

- CRM mínimo: oportunidades, orçamento perdido, motivo, follow-up, próxima ação e responsável.
- Histórico de compras, margem, inadimplência, preferências e obras/projetos do cliente.
- Orçamento por obra, centro de custo ou projeto com validade e versão.
- Tabela de preço por cliente/segmento, política de desconto e promoção por período/quantidade.
- Kits, combos, venda casada permitida e produtos complementares.
- Comissões por vendedor, produto, margem, recebimento e cancelamento.
- Comunicação transacional por e-mail/WhatsApp com opt-in, template e histórico.

## 7. Cadastro de produtos específico para o ramo

### P1.12 Dados comerciais e técnicos

- Modelo explícito Produto → unidade comercial → embalagem/conversão, sem depender apenas de JSON.
- Mais de um código de barras por produto/embalagem e validação de dígito/duplicidade.
- GTIN/EAN, código do fabricante, código do fornecedor e código interno.
- Unidade de estoque, venda, compra, tributável e conversões com vigência.
- Bitola, tensão, corrente, potência, comprimento, diâmetro, rosca, material, cor, acabamento, norma e compatibilidade.
- Marca, linha, modelo, garantia, origem, peso, dimensões e volume.
- Produtos equivalentes, substitutos, acessórios e compatibilidade entre itens.
- Kit/composição e desmonte para itens vendidos como conjunto.
- Controle de ativo, inativo, fora de linha, sob encomenda, venda bloqueada e compra bloqueada.
- Importação por planilha com prévia, deduplicação, validação, rollback e log por linha.
- Workflow de qualidade do cadastro: rascunho, revisão, publicado e bloqueado.
- Histórico de alteração de descrição, unidade, preço, custo, classificação e fiscal.

### P1.13 Preços e margem

- Margem real baseada no custo histórico e no custo líquido fiscal.
- Markup versus margem sem ambiguidade e validação de margem mínima.
- Preço por canal, cliente, região, quantidade, prazo e condição.
- Vigência, aprovação, revisão e rollback de preço.
- Simulação de preço com impostos, comissão, frete e custo financeiro.
- Importação e atualização em lote com prévia e auditoria.
- Histórico de preço de venda e motivo da alteração.

## 8. Relatórios, indicadores e BI

**Situação atual: insuficiente para administração.** Existem endpoints de vendas por período, aging, DRE resumido, margem de vendas e dashboard básico, mas não há uma central de relatórios com filtros, exportação, drill-down, histórico e visões por área.

### P0/P1.14 Painel executivo

- Receita bruta, receita líquida, pedidos, ticket médio, margem, CMV, lucro bruto e evolução.
- Vendas por dia, semana, mês, canal, vendedor, cliente, grupo, marca, depósito e forma de pagamento.
- Comparativo com período anterior, meta e orçamento.
- Contas a receber vencidas, a vencer, inadimplência e aging.
- Contas a pagar, compromissos futuros, saldo de caixa/bancos e fluxo projetado.
- Estoque total, estoque disponível, reservado, em trânsito, baixo, parado, excesso e ruptura.
- Alertas acionáveis com link para a lista que resolve o problema.

### P1.15 Relatórios de vendas e comercial

- Venda detalhada por pedido/item/documento fiscal.
- Ranking de produtos, marcas, grupos, clientes, vendedores e regiões.
- Curva de vendas e margem por período.
- Ticket médio, itens por pedido, desconto médio e margem após desconto.
- Orçamentos abertos, convertidos, perdidos, vencidos e taxa de conversão.
- Vendas canceladas, devolvidas, trocadas e motivos.
- Comissão apurada, pendente, paga e estornada.
- Clientes sem compra, recorrência, concentração e carteira ativa.

### P1.16 Relatórios de compras

- Necessidade de compra sugerida e justificativa por item.
- Compras por fornecedor, grupo, marca, comprador, período e depósito.
- Evolução de preço, custo líquido e variação contra última compra.
- Pedidos em aberto, atrasados, parciais, recebidos e cancelados.
- Lead time prometido versus realizado.
- Fill rate, índice de atendimento, ruptura causada por fornecedor e nível de serviço.
- Comparação de propostas, economia negociada e perda por indisponibilidade.
- Dependência e concentração de fornecedores.
- Devoluções, divergências de recebimento e notas pendentes.

### P1.17 Relatórios de estoque

- Saldo por depósito/endereço, disponível, reservado, bloqueado e em trânsito.
- Kardex com saldo anterior, entradas, saídas, ajustes, custo e documento origem.
- Valorização por método e data de corte.
- Curva ABC histórica e matriz ABC-XYZ.
- Giro, cobertura em dias, estoque médio e dias sem venda.
- Ruptura, excesso, estoque parado, obsolescência e validade próxima.
- Acuracidade de inventário e divergência por depósito/operador.
- Transferências pendentes e perdas/avarias.
- Produtos com estoque mas sem custo, preço, fornecedor, EAN ou classificação fiscal.

### P1.18 Financeiro, contábil e fiscal

- Fluxo de caixa realizado e projetado.
- DRE gerencial por período, centro de custo, grupo e filial.
- Plano de contas, lançamentos, partidas, saldo e período fechado.
- Conciliação bancária com importação OFX/CSV e matching sugerido.
- Contas a pagar/receber por vencimento, competência, caixa e origem.
- Inadimplência, cobrança, acordos, juros, multa, desconto e renegociação.
- Taxas de cartão/PIX/boleto e liquidação prevista versus realizada.
- Resultado por produto, canal, vendedor, cliente e depósito.
- Documentos fiscais autorizados, rejeitados, cancelados, contingentes e pendentes.
- Exportações e obrigações exigidas pelo contador, incluindo SPED quando aplicável ao regime.

### P1.19 Plataforma de relatórios

- Página `#/relatorios` com catálogo por perfil.
- Filtros por período, empresa, depósito, grupo, fornecedor, cliente e status.
- Presets salvos, favoritos, colunas configuráveis e drill-down.
- Exportação CSV/XLSX/PDF sem bloquear a requisição; geração grande via job.
- Relatório agendado por e-mail/arquivo e histórico de execuções.
- Snapshot de parâmetros e data de geração para auditoria.
- Permissão separada para visualizar, exportar e compartilhar dados sensíveis.
- Paginação/streaming para não carregar milhões de linhas no navegador.

## 9. Financeiro e contabilidade

### P1.20 Contas a pagar/receber e caixa

- Renegociação, prorrogação, desconto, juros, multa, abatimento e baixa parcial com histórico.
- Baixa agrupada com rateio por conta, centro de custo e forma de pagamento.
- Fluxo de aprovação para pagamentos e recebimentos acima de limite.
- Fechamento de caixa por operador/terminal com diferença e justificativa.
- Sangria, suprimento, transferência entre caixas e conciliação com adquirente.
- Taxas, antecipação e liquidação de cartão.
- Remessa/retorno bancário quando houver cobrança bancária real.
- PIX/boleto com expiração, cancelamento, segunda via, webhook e conciliação.
- Bloqueio de alterações retroativas após período financeiro fechado.

### P1.21 Contabilidade gerencial

- Plano de contas completo com natureza, hierarquia e vigência.
- Débito/crédito equilibrado, lote, origem e estorno.
- Regras de contabilização para venda, compra, estoque, impostos, frete, pagamento e devolução.
- Fechamento mensal e bloqueio de lançamento em período fechado.
- DRE por competência e caixa, margem de contribuição e ponto de equilíbrio.
- Orçamento versus realizado por centro de custo.
- Exportação para contabilidade e integração com escritório/serviço contábil.

## 10. Frontend, UX/UI e acessibilidade

### P1.22 Centralização dos fluxos

- Criar navegação clara por: Operação, Comercial, Compras, Estoque, Financeiro, Fiscal, Relatórios e Administração.
- Evitar telas legadas paralelas para compras/cotações/solicitações; manter compatibilidade, mas encaminhar para o fluxo único.
- Breadcrumb, título, estado, filtros ativos e ação primária consistentes.
- Mostrar contexto do depósito, empresa/filial, usuário e período atual.
- Formularios extensos em etapas ou abas com rascunho, validação inline e indicador de completude.
- Confirmar ações irreversíveis com impacto e motivo, não apenas `window.confirm`.

### P1.23 Tabelas de ERP

Aplicar em todas as tabelas o contrato já adotado como requisito do projeto, alinhado a [Salesforce Lightning Datatable](https://developer.salesforce.com/docs/platform/lwc/guide/data-table-a11y.html) e [SLDS](https://developer.salesforce.com/docs/platform/lightning-component-reference/guide/lightning-datatable.html?type=Example):

- cabeçalho semântico, foco visível, navegação por teclado e `aria` correto;
- ordenação, filtros por coluna, busca, paginação e total de registros;
- seleção de linha, ações em lote e confirmação de escopo;
- colunas fixas/configuráveis, densidade e persistência da preferência;
- menu de ação por linha e atalho documentado;
- loading/skeleton, empty state, erro recuperável e estado sem permissão;
- virtualização para listas extensas e renderização incremental;
- `data-label` apenas no modo mobile, sem destruir a semântica de tabela no desktop;
- exportação respeitando filtros, colunas e permissões;
- foco restaurado após modal, toast e atualização da lista.

### P1.24 Formulários e operação sem mouse

- Mapa de atalhos global sem conflitos com navegador/leitor.
- Enter, Tab, Shift+Tab, Escape e setas com comportamento documentado por tela.
- Foco inicial determinístico e foco devolvido ao campo de origem.
- Dialog com `role=dialog`, `aria-labelledby`, trap de foco e fechamento seguro.
- Não remountar modal/campo a cada tecla; preservar foco em autorização, busca e cadastro.
- Máscaras que não corrompem cursor, colagem ou leitores.
- Validação de campo e de regra de negócio com mensagem acionável.
- Proteção contra perda de alterações e rascunho local/servidor quando aplicável.
- Toast com texto, duração adequada e alternativa persistente para erros críticos.

### P1.25 Tipagem, dados e desempenho

- `strict: true` e eliminação gradual de `any`/casts sem validação.
- Contratos OpenAPI completos por blueprint, tipos gerados ou runtime schemas consistentes.
- Query/cache/invalidação padronizados; evitar fetch duplicado ao trocar abas.
- Estados de loading, erro, vazio e stale definidos para toda chamada.
- TanStack Query ou padrão equivalente para cache, retry e mutation.
- Virtualização de catálogo, estoque, compras e relatórios grandes.
- Code splitting por módulo e carregamento sob demanda.
- Testar em viewport de caixa, tablet de estoque e desktop administrativo.

### P1.26 Acessibilidade e localização

- Auditoria WCAG 2.2 AA com teclado, leitor de tela, contraste e zoom 200%.
- Formatação centralizada de moeda BRL, datas, hora, fuso, percentuais e números decimais.
- Mensagens sem mojibake e sem depender apenas de cor.
- Indicadores de status com texto e ícone/forma alternativa.
- Suporte a impressão e PDF legível em A4 e impressoras térmicas.
- Preparar idioma, timezone e moeda como configuração da empresa, mesmo que o primeiro uso seja Brasil/BRL.

## 11. API, arquitetura e qualidade

### P1.27 Contratos e domínio

- Manter controllers/Blueprints finos e mover regras para services/use cases.
- Padronizar DTO/schema de entrada e saída; não aceitar payload livre em endpoints críticos.
- Respostas paginadas com contrato comum, filtros validados e ordenação permitida por whitelist.
- Versionar API quando houver quebra; preservar compatibilidade durante Expand/Migrate/Contract.
- Padronizar erro `{code, message, details, correlation_id}`.
- Aplicar idempotência em criar pedido, recebimento, emissão fiscal, cobrança, devolução e importação.
- Adicionar correlation ID em logs e respostas.
- Revisar consultas N+1, índices, planos e limites de payload.
- Não retornar entidades internas ou segredos diretamente.

### P1.28 Concorrência e consistência

- Testes de isolamento e locks em saldo, reserva, caixa, títulos, pedido e emissão.
- Constraints e FKs para referências, quantidades, valores, status e unicidade por empresa.
- Imutabilidade de fatos de estoque, documentos autorizados, eventos fiscais e lançamentos fechados.
- Rotina de auditoria e reconciliação programada.
- Testes de retry, timeout, duplicidade, queda do worker e retomada após crash.

### P1.29 Testes

- E2E de login/RBAC, pré-venda, desconto, cliente, fechamento, pagamento, reabertura, devolução, compras, recebimento, estoque e fiscal.
- Contratos frontend/backend a partir do OpenAPI.
- Testes de migração banco vazio→head e incremental N→head.
- Testes de concorrência com PostgreSQL real.
- Testes de integração dos quatro provedores de pagamento com sandbox/mocks de contrato.
- Testes de webhook assinado, anti-replay, duplicidade e rechecagem.
- Testes de acessibilidade automatizados e roteiro manual de teclado.
- Smoke tests após release e testes de restauração de backup.
- Meta inicial: cobertura dos fluxos críticos, não somente aumento de percentual de linhas.

## 12. Integrações e operação de loja

### P1.30 Integrações essenciais

- TEF/adquirentes de cartão e conciliação de recebíveis.
- Bancos: OFX/CSV, boletos reais, remessa/retorno e conciliação.
- Provedor fiscal completo e ambiente de homologação/produção separado.
- Impressoras térmicas, etiquetas, balanças e leitores de código.
- Transportadoras, cálculo de frete, rastreio e comprovante de entrega.
- E-commerce e marketplaces com estoque, preço, pedido, cancelamento e devolução idempotentes.
- Fornecedor: e-mail/WhatsApp, XML de entrada, catálogos e atualização de preço.
- Contabilidade: exportação/importação de plano, lançamentos e documentos.
- CRM/WhatsApp com consentimento e histórico.

### P1.31 Multiempresa, filiais e governança

**Situação: não foi comprovado como requisito transversal no código atual.** Antes de crescer, decidir se o ERP será monoempresa ou multiempresa/multifilial.

- `empresa_id/filial_id` em dados de negócio e isolamento obrigatório por consulta.
- Depósito, caixa, série fiscal, certificado, preço, estoque e plano de contas por filial.
- Transferência entre filiais, venda entre estabelecimentos e regras fiscais correspondentes.
- Usuário, perfil e permissão por empresa/filial.
- Dashboard e relatórios consolidados ou segregados.
- Numeração e configurações independentes.

### P1.32 Administração de dados

- Importação inicial de produtos, clientes, fornecedores, saldos, preços e plano de contas.
- Deduplicação e reconciliação de EAN/SKU/documentos.
- Exportação completa e anonimização para suporte.
- Log de auditoria de dados sensíveis e consultas administrativas.
- Retenção, LGPD, consentimento, anonimização e atendimento de solicitação de dados.
- Rotinas de limpeza sem apagar documentos/fatos necessários à auditoria.

## 13. Backlog consolidado por ordem de execução

### Fase 0: tornar seguro para piloto

1. Fechar homologação fiscal e declarar explicitamente os cenários suportados.
2. Concluir reconciliação/atomicidade de venda, estoque, financeiro e fiscal.
3. Implementar backup testado, observabilidade, jobs e operação de release.
4. Corrigir dados mestres críticos: unidades, EAN, custo, fornecedor, NCM e preço.
5. Criar smoke/E2E dos fluxos de caixa e venda.

### Fase 1: operar compras e estoque com decisão

6. Implementar motor de necessidade de compra e tela de sugestões.
7. Implementar ABC histórica + XYZ + matriz de política.
8. Completar recebimento de compra, três vias, parcial, divergência e devolução.
9. Completar custo médio/valorização/CMV/margem histórica.
10. Completar inventário cíclico, endereçamento, coletor e aprovação.
11. Completar pedido de compra, aprovação, entrega e desempenho do fornecedor.
12. Criar central de relatórios de estoque, compras e vendas.

### Fase 2: profissionalizar operação comercial e financeira

13. Fechar PDV, múltiplos pagamentos, TEF, fechamento de caixa e contingência.
14. Completar devolução/troca/garantia com efeitos financeiros e fiscais.
15. Completar conciliação bancária, adquirentes, cobrança, renegociação e DRE.
16. Implementar comissões, CRM, obras/projetos e comunicação transacional.
17. Aplicar padrão de tabelas, teclado, filtros, exportação e acessibilidade em todos os módulos.

### Fase 3: escala e inteligência

18. Multiempresa/multifilial, se confirmado pelo negócio.
19. E-commerce/marketplaces e transportadoras.
20. Previsão de demanda, sazonalidade e otimização de estoque.
21. BI com metas, orçamento, alertas e relatórios agendados.
22. MDM/catálogo avançado, equivalência e recomendação de produtos.

## 14. Critério de prontidão para uso real

O ERP pode iniciar um piloto controlado somente quando os itens P0 estiverem aprovados e os P1 dos fluxos usados pela loja estiverem concluídos. A aprovação precisa considerar evidência, não apenas código:

- venda concorrente sem saldo não gera estoque negativo nem pedido duplicado;
- cancelamento/devolução estorna todos os efeitos corretamente;
- nota fiscal real é autorizada, consultada, armazenada e reprocessada sem duplicidade;
- compra sugerida explica o cálculo e não duplica pedidos em aberto;
- recebimento atualiza estoque, custo, título e contabilidade com conferência;
- inventário fecha divergência com aprovação e auditoria;
- administrador consegue enxergar receita, margem, CMV, estoque, giro, ruptura, compras, caixa e inadimplência;
- operador consegue concluir os fluxos principais com teclado e feedback claro;
- backup é restaurado com sucesso;
- release tem rollback de aplicação e banco documentado;
- staging passa os mesmos smoke tests que serão usados após a publicação.

## 15. Referências de mercado usadas

- O planejamento de reposição deve considerar ponto de pedido, estoque de segurança, políticas de ressuprimento, lead time, lote mínimo, múltiplos, oferta e demanda projetadas, conforme a documentação de planejamento de inventário do [Microsoft Dynamics 365 Business Central](https://learn.microsoft.com/en-gb/dynamics365/business-central/design-details-handling-reordering-policies) e de balanceamento de oferta e demanda [Microsoft Learn](https://learn.microsoft.com/en-us/dynamics365/business-central/design-details-balancing-demand-and-supply).
- Inventário profissional precisa suportar contagem física, múltiplos contadores, importação e postagem controlada; esse padrão aparece na documentação de [Inventory Counting do SAP Business One](https://help.sap.com/docs/SAP_BUSINESS_ONE/68a2e87fb29941b5bf959a184d9c6727/062b155358d8ff07e10000000a423f68.html).
- Valoração, custo e unidade de contagem precisam ser tratados como dados operacionais explícitos; ver [Item Master Data: Inventory Data Tab do SAP Business One](https://help.sap.com/docs/SAP_BUSINESS_ONE/68a2e87fb29941b5bf959a184d9c6727/451fa75c8ffb4a2fe10000000a11466f.html).
- O fiscal brasileiro exige ciclo de eventos e tratamento de contingência/cancelamento/carta de correção conforme os documentos técnicos oficiais do [Portal Nacional da NF-e](https://www.nfe.fazenda.gov.br/portal/).
- GTIN/EAN é base para identificação no varejo e deve ser modelado com regras de unicidade e embalagem; ver [GS1 Brasil](https://www.gs1br.org/conteudo/ebooks/Documents/180418_Amazon_GTIN.pdf).

## Conclusão

O maior risco não é ausência de telas isoladas; é operar com indicadores simplificados e fluxos que ainda não fecham o ciclo de negócio. A prioridade correta é: fiscal e consistência transacional, depois reposição/ABC/valoração, recebimento e relatórios, e somente então integrações avançadas e previsão. Esse sequenciamento reduz risco de comprar errado, vender sem margem, manter capital parado e tomar decisão financeira baseada em dados incompletos.
