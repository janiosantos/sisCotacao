# Auditoria de prontidão para grande varejo e rede de profissionais

**Data:** 2026-09-02  
**Escopo:** código atual do backend Flask/PostgreSQL, frontend React/TypeScript, migrations, rotas, serviços, telas, testes, documentação e banco de desenvolvimento em execução.  
**Objetivo:** verificar o que foi realmente implementado, identificar implementações parciais ou inconsistentes e definir o que falta para uma grande loja de materiais elétricos, hidráulicos, ferragens e ferramentas operar com compras, estoque, margem, rede de profissionais, fidelização e bonificação por indicação.

**Fora do escopo:** multi-tenancy. O diagnóstico considera uma operação monoempresa, com possibilidade futura de filiais e depósitos.

## 1. Parecer executivo

O projeto possui uma fundação ampla e valiosa: catálogo com dezenas de milhares de produtos, busca, pré-venda, clientes, fornecedores, preços, promoções, compras, estoque por depósito, contas financeiras, caixa, RBAC, fiscal, outbox, webhooks, transporte, pós-venda e uma base de relatórios.

Entretanto, a aplicação ainda não deve ser considerada um ERP pronto para uma grande operação. O principal problema não é a falta de telas isoladas, mas a existência de fluxos que terminam antes dos efeitos financeiros, fiscais e gerenciais; além disso, algumas entregas declaradas como concluídas funcionam somente no caminho feliz ou estão desalinhadas com o banco e com a regra de negócio.

O maior gap estratégico é a rede de profissionais. Não foi encontrada entidade, migration, serviço, endpoint ou tela para parceiro, programa de fidelidade, pontos, cashback, indicação, carteira de bonificação, regras de elegibilidade ou liquidação. O segmento `profissional` existente é apenas um atributo de cliente e não representa um programa de relacionamento.

### Classificação

| Classificação | Significado |
|---|---|
| **Existente** | Há fluxo funcional e evidência de teste, mas ainda pode haver evolução normal. |
| **Parcial** | Há código ou tela, porém faltam etapas, regras, integrações, governança ou escala. |
| **Risco crítico** | O comportamento atual pode gerar perda financeira, estoque incorreto, fraude, baixa indevida ou quebra operacional. |
| **Ausente** | Não foi localizada implementação de domínio utilizável. |

## 2. Evidências e estado do ambiente

- Foram confrontados `CONTEXTO_SESSAO.md`, `AGENTS.md`, migrations até `0143`, blueprints, serviços, repositórios, páginas React, cliente de API, testes e relatórios anteriores.
- O repositório está limpo em `main`, alinhado ao remoto, com as últimas mudanças de documentação e crediário no histórico.
- O banco PostgreSQL de desenvolvimento em execução está no schema **142**, não no 104 descrito em trechos antigos da documentação.
- A migration `0143_crediario_aprovacao.py` existe no código, mas ainda não está aplicada no banco atual. As tabelas `credito_aprovacao`, `credito_evento` e `credito_reserva` não existem no banco em execução.
- O frontend passa `npm run typecheck`.
- Os testes backend não foram executados nesta auditoria porque o ambiente local não possui `TEST_PG_URL` configurada e o container backend não possui `pytest` instalado. A coleta de testes local foi interrompida pela configuração obrigatória do PostgreSQL de teste.
- Não existe suíte E2E padronizada com Playwright/Cypress; há scripts manuais com Puppeteer que não equivalem a uma matriz automatizada de regressão.

## 3. Matriz de implementação por domínio

| Domínio | Estado real | Conclusão da auditoria |
|---|---|---|
| Catálogo de produtos | Parcialmente existente | A base é grande, mas faltam governança de dados, ciclo de vida comercial, qualidade de atributos e controles específicos de elétrica/hidráulica. |
| Busca e pré-venda | Parcialmente existente | O teclado e a navegação evoluíram, mas faltam operação de caixa completa, contingência, TEF, suspensão de venda e garantia de margem. |
| Clientes e crediário | Parcial no código; indisponível no banco atual | O serviço tem boa separação inicial, mas a migration 143 não está aplicada e faltam política de crédito, documentos e revisão financeira completa. |
| Compras e cotações | Parcial | A cadeia existe, mas há autoria manipulável, recebimento financeiro simplificado, baixa governança de propostas e planejamento ainda pouco confiável. |
| Estoque e reposição | Parcial com riscos | Há ledger, depósitos, lotes, inventário, ABC/XYZ e motor de reposição, mas os cálculos ainda misturam depósitos e perdem contexto histórico. |
| Financeiro e caixa | Parcial com riscos críticos | Existem contas, caixa, cobrança e provedores, mas conciliação, parcelas de fornecedores, estornos e fechamento contábil ainda não são confiáveis em todos os caminhos. |
| Fiscal | Parcial | Adapters e snapshots existem, mas homologação real, contingência, eventos fiscais, entrada fiscal integrada e operação de produção ainda não estão encerradas. |
| Pós-venda | Parcial | RMA, troca e garantia iniciais existem, porém efeitos fiscais, financeiros, estoque de quarentena e reversão completa ainda faltam. |
| Comissão de vendedores | Parcial e duplicada | Existem dois modelos de comissão com bases e vínculos diferentes, sem uma fonte única de verdade. |
| Relatórios e BI | Parcial | O dashboard é inicial; existem erros semânticos/SQL e não há visão de contribuição, parceiros, fidelidade, coortes ou rentabilidade por cliente/projeto. |
| RBAC e auditoria | Parcial | RBAC centralizado foi criado, mas vários endpoints aceitam ator no payload e permitem autoria falsa ou auditoria incorreta. |
| Parceiros profissionais | Ausente | Não há módulo de cadastro, vínculo, indicação, portal, regras ou liquidação. |
| Fidelização | Ausente | Não há ledger de pontos/cashback, campanhas, níveis, expiração ou reversão. |
| Bonificação por indicação | Ausente | Não há atribuição de origem, aprovação, antifraude, contas a pagar ou extrato do parceiro. |
| Margem para consumo profissional | Ausente como domínio | Há precificação genérica, mas não há rentabilidade líquida por parceiro, obra, consumo, canal ou campanha. |

## 4. Riscos críticos encontrados

### 4.1 Banco e crediário não estão sincronizados

**Estado:** risco crítico.

O código de `backend/catalog_server/services/credito.py` consulta as novas tabelas da migration 143, mas o banco de desenvolvimento está no 142 e não possui essas tabelas. A funcionalidade pode retornar erro de banco em endpoints de crédito, mesmo que o código e os testes específicos existam.

**Correção necessária:** aplicar a migration somente em ambiente autorizado, validar banco vazio e incremental, executar testes de integração e atualizar a documentação para refletir schema 142/143 real. Não basta liberar a tela.

### 4.2 Recebimento de compra cria contas a pagar incorretas

**Arquivo:** `backend/catalog_server/services/recebimento.py`, função `finalizar`.

O serviço recebe `condicao_pagamento_id`, porém grava uma única conta a pagar com vencimento fixo de 30 dias. Em recebimento parcial, cada postagem pode criar um novo título sem uma chave de origem que represente o saldo total do pedido, gerando duplicidade ou parcelas incorretas. A consequência é divergência de fluxo de caixa, vencimentos e conciliação com o fornecedor.

Além disso, uma exceção contábil é capturada e ignorada. O estoque e o financeiro podem ser confirmados com `contabil_ok=False`, sem fila de reparo transacional e sem bloqueio ou pendência operacional clara.

**Correção necessária:** gerar parcelas pela condição aprovada, distribuir somente o valor efetivamente recebido, manter vínculo por pedido/recebimento/item, tornar a postagem idempotente em estoque, contas a pagar e contabilidade e criar fila de reconciliação para falha contábil.

### 4.3 Conferência de três vias perde linhas repetidas

**Arquivo:** `backend/catalog_server/services/tres_vias.py`, função `conferir`.

Pedido e nota são transformados em dicionários indexados por `produto_id`. Se o mesmo produto aparecer em duas linhas com unidades, lotes, marcas ou condições diferentes, uma linha sobrescreve a outra. A conferência passa a comparar uma representação que não existe fisicamente no documento.

A rotina também percorre os itens da NF, mas não garante que todas as linhas pedidas tenham sido avaliadas. Isso deixa lacunas de falta ou backorder.

**Correção necessária:** usar `pedido_item_id`/linha fiscal como chave, comparar listas normalizadas e emitir divergência explícita para linha ausente, extra, duplicada, unidade incompatível, lote divergente e preço divergente.

### 4.4 Conciliação bancária pode baixar conta a receber ao conciliar conta a pagar

**Arquivo:** `backend/catalog_server/services/conciliacao.py`, funções `sugerir_matching` e `aprovar`.

As sugestões combinam contas a receber e a pagar sem informar o tipo da conta no matching. Na aprovação, a busca tenta localizar nas duas tabelas, mas o `UPDATE` executado é sempre em `contas_receber`. Um pagamento de fornecedor pode ser marcado como recebido, ou o extrato pode ser conciliado sem baixa correta.

**Correção necessária:** persistir `origem_tipo`, `origem_id` e direção do movimento; usar lock na conta; validar valor, sinal, status e duplicidade; atualizar a tabela correta e impedir que uma mesma conta seja conciliada duas vezes.

### 4.5 Retry de pagamento pendente pode marcar venda como recebida

**Arquivo:** `backend/catalog_server/services/pagamento_venda.py`, função `registrar`.

Quando uma forma pendente, como PIX ou cartão, é reenviada com a mesma chave de idempotência, o valor existente entra na soma, mas o registro existente não incrementa `pendentes`. Um retry do mesmo pagamento pode, portanto, fechar a soma e alterar o pedido para `recebido` antes da confirmação externa.

A função `confirmar` também não trava o pedido antes de ler e confirmar pendências. Duas confirmações concorrentes podem lançar duas entradas de caixa para o mesmo pagamento.

**Correção necessária:** calcular o estado a partir dos registros persistidos, tratar retry como resposta idempotente sem mudar estado, bloquear o pedido e os pagamentos pendentes, usar chave de confirmação própria e garantir unicidade do lançamento no caixa.

### 4.6 Autoria ainda pode ser falsificada em compras e estoque

**Arquivos:** `backend/catalog_server/blueprints/api_compras_avancado.py`, `api_estoque.py`, `api_financeiro.py`, `api_posvenda.py`.

Vários endpoints aceitam `usuario_id`, `operador_id`, `aprovador_id` ou `vendedor_id` enviados no JSON. Isso contradiz a regra de que o ator deve ser derivado do Bearer. O RBAC pode autorizar a rota, mas o histórico e os efeitos podem ser gravados em nome de outra pessoa.

**Correção necessária:** remover IDs de ator do contrato público; derivar sempre de `usuario_id_requisicao()`; permitir outro aprovador somente por uma operação de delegação autorizada e auditada; validar que solicitante e aprovador sejam pessoas distintas.

### 4.7 ABC histórica está funcionalmente incorreta

**Arquivo:** `backend/catalog_server/services/abc_historica.py`.

- O critério `consumo` aparece na interface, mas não existe como métrica na consulta; `_valor` retorna zero para esse critério.
- `deposito_id` é salvo no cabeçalho, porém não filtra vendas nem custos por depósito.
- O resultado contém somente produtos com venda; itens em estoque sem venda não entram na classificação operacional.
- A aplicação grava `classe_abc` e `ordem_abc` diretamente no produto, tornando uma classificação por depósito aparentemente global e sobrescrevendo classificações anteriores.
- Somente `finalizado` é considerado; a regra de negócio precisa definir se vendas `recebido` também representam consumo realizado.
- A tela exibe no máximo 50 itens, não mostra claramente a versão aplicada e não permite escolher depósito.

**Correção necessária:** criar universo produto × depósito, calcular consumo por saída efetiva e custo histórico, preencher meses sem venda com zero, versionar classificação por depósito e separar resultado calculado de classe operacional aplicada.

### 4.8 Motor de reposição mistura contexto de depósitos e tem custo de escala alto

**Arquivo:** `backend/catalog_server/services/motor_reposicao.py`.

- Compras em trânsito são somadas globalmente por produto, sem depósito destino e sem dedução precisa de recebimento parcial.
- Demanda aberta também é global e não respeita depósito.
- A média mensal considera somente meses com venda e não preenche meses zerados, superestimando demanda intermitente.
- Ao consolidar vendas sem saldo, o produto é atribuído ao primeiro depósito encontrado.
- Há consultas por produto para saldo, produto, fornecedor e demanda, gerando padrão N+1 para um catálogo grande.
- A conversão de embalagem/unidade é declarada como requisito, mas a recomendação usa principalmente lote mínimo/múltiplo e não fecha a conversão comercial completa.

**Correção necessária:** calcular por depósito destino, linha de pedido e unidade base; tratar recebimento parcial; fazer séries temporais com zeros; usar consultas agregadas; incluir sazonalidade, variabilidade, lead time real e cobertura.

### 4.9 Precificação não protege a margem

**Arquivos:** `backend/catalog_server/services/pricing_engine.py` e `preco_regra.py`.

O motor calcula preço por margem/markup e sinaliza `abaixo_da_margem_minima`, mas não bloqueia a venda nem exige alçada quando uma regra comercial leva o preço abaixo do piso. A validação das regras não garante faixa de margem, ordem de vigência, exclusividade entre preço fixo e desconto, existência de referências e tratamento monetário completo.

O preço efetivo não considera parceiro, campanha de indicação, benefício de fidelidade, custo de aquisição em trânsito, frete, custo financeiro, taxa de pagamento e comissão por linha. O fallback de tabela ou preço base pode retornar preço sem custo e sem sinalização suficiente para decisão comercial.

**Correção necessária:** centralizar o cálculo de preço líquido e margem de contribuição; registrar componentes e versão; bloquear ou submeter a alçada quando abaixo do piso; aplicar benefícios na ordem definida e impedir que comissão, pontos e indicação consumam a margem mínima.

### 4.10 Relatórios atuais não sustentam decisão de uma grande loja

**Arquivo:** `backend/catalog_server/services/relatorios.py`.

- O agrupamento `grupo` usa `p.categoria_id` sem o join correspondente, podendo falhar em SQL.
- O agrupamento `deposito` usa `o.uf_destino`, que não representa necessariamente o depósito de saída.
- `canal` usa `modelo_documento`, que é documento fiscal, não canal comercial.
- O CMV é calculado globalmente, não necessariamente na mesma granularidade do agrupamento da receita.
- O aging ignora o período solicitado e não trata todos os status, como `parcial` em alguns indicadores.
- A DRE inicial considera essencialmente receita e CMV, sem despesas operacionais, impostos, devoluções, taxas, comissões, custo financeiro e centros de custo.
- O estoque exclui quantidade zero, limita a 500 linhas e não oferece paginação ou visão completa de itens sem saldo/ruptura.
- Compras usam valor bruto do pedido e não custo efetivamente recebido, frete, impostos, descontos e devoluções.

**Arquivo frontend:** `frontend/src/pages/relatorios.tsx`.

A tela não oferece filtros de período/deposito/filial/canal, exportação, drill-down, estado de erro distinguível de vazio, carregamento por relatório ou relatórios de parceiro/fidelidade/margem. Para uma grande operação, o gestor precisa de consultas assíncronas, filtros persistentes e exportação auditável.

## 5. Auditoria funcional por módulo

### 5.1 Cadastro e catálogo

**Existente:** produtos unificados, SKU, EAN, marca, categoria, subgrupo, imagens, unidades, busca, identificadores e relações.

**Parcial ou faltante:**

- Governança de cadastro com aprovação, histórico de alteração, responsável e publicação comercial.
- Detecção de duplicidade por EAN, fabricante, código do fornecedor, descrição normalizada e atributos técnicos.
- Regras específicas para cabo, tubo, conexão, fita, tinta, ferramenta elétrica, EPI, abrasivo, química e itens vendidos por metragem, peso, caixa, kit e rolo.
- Ficha técnica comparável para tensão, corrente, bitola, seção, material, rosca, diâmetro, comprimento, pressão, vazão, IP, potência, voltagem, norma e compatibilidade.
- Produto substituto e equivalente comercial com aprovação, mantendo a diferença técnica e de margem.
- Controle de produto ativo, inativo, obsoleto, sob encomenda, bloqueado para venda e sem compra.
- Importação de catálogo com validação, prévia, rollback, relatório de erros e atualização incremental.

### 5.2 Pré-venda e PDV

**Existente:** orçamento/pedido, navegação por teclado, desconto com alçada, condição de pagamento, cliente padrão, reserva e recebimento separado.

**Parcial ou faltante:**

- Busca instantânea por scanner, EAN, SKU, código do fabricante, código de fornecedor, apelido e tokens de descrição.
- Venda fracionada com conversão inequívoca entre unidade comercial e unidade de estoque.
- Venda por projeto/obra, centro de custo do cliente e consumo acumulado.
- Venda suspensa, retomada, troca de terminal, troca de operador, autorização de cancelamento e fechamento de caixa por terminal.
- Integração TEF ou fluxo homologado para cartão, PIX com confirmação e contingência.
- Impressão de pedido, DANFE/NFC-e, etiqueta e comprovante com URL/porta corretamente configuradas.
- Modo offline controlado para perda de internet, com fila, numeração e reconciliação fiscal.
- Política que impeça vendedor de receber, impeça operador de aprovar crediário e mantenha o financeiro segregado.

### 5.3 Compras e recebimento

**Existente:** solicitação, cotação, portal de fornecedor, comparação, fornecedor preferencial, alçada de compra, pedido, recebimento, conferência, três vias e devolução ao fornecedor.

**Parcial ou faltante:**

- Orçamento de compra com custo posto, prazo, frete, impostos, bonificação do fornecedor, quantidade mínima, múltiplo e condição real.
- Aprovação por valor, comprador, centro de custo, margem projetada, fornecedor e exceção.
- Consolidação segura de necessidades sem perder depósito, obra, solicitante ou prioridade.
- Pedido de compra com alteração versionada, backorder, cancelamento parcial, saldo a receber e previsão revisada.
- Recebimento por linha, unidade, embalagem, lote, validade, série, avaria e quarentena.
- Integração NF-e/XML → vínculo → três vias → estoque/custo/contas a pagar/contábil em fluxo único.
- Títulos a pagar parcelados conforme condição, com abatimentos, devoluções, descontos financeiros e retenções quando aplicável.
- Desempenho de fornecedor com fill rate, atraso, divergência, qualidade, preço líquido e índice de devolução.

### 5.4 Estoque e logística

**Existente:** saldo por depósito, fatos de estoque, custo médio, reserva, transferência, lotes, endereçamento, inventário, ABC/XYZ, expedição e transporte.

**Parcial ou faltante:**

- Saldo confiável por depósito, endereço, lote, série, unidade base e unidade de venda.
- Custo médio móvel ou método oficial definido pelo contador, com custo histórico e data de corte.
- Picking, packing, conferência e entrega vinculados ao pedido e ao operador.
- Inventário cíclico por ABC/XYZ, contagem cega, dupla contagem e aprovação de divergência.
- Reposição com cobertura, sazonalidade, demanda aberta, trânsito por destino, lead time variável e alternativas de fornecedor.
- Tratamento para estoque negativo, bloqueado, quarentena, avariado, consignado, reservado e em separação.
- Relatórios de ruptura, excesso, obsolescência, giro, cobertura, perdas e capital parado.

### 5.5 Financeiro, fiscal e contábil

**Existente:** caixa, contas a receber/pagar, parcelas iniciais, cobrança, provedores, webhooks, bancos, conciliação manual, plano de contas e gatilhos.

**Parcial ou faltante:**

- Crediário aplicado no banco, com dossiê de documentos, análise, política de limite, prazo, condições permitidas, revisão periódica, exposição consolidada e grupo econômico.
- Contas a receber por parcela com juros, multa, desconto, renegociação, baixa parcial, estorno e conciliação por título.
- Contas a pagar por condição de compra, recebimento parcial, devolução, abatimento e título original.
- Conciliação por tipo e direção, com importação OFX/CSV/API, matching explicável e aprovação segregada.
- DRE gerencial por regime definido, centro de custo, depósito, canal, vendedor, parceiro e obra.
- Fiscal real homologado com certificado, séries, CSC, contingência, cancelamento, inutilização, carta de correção, eventos e entrada fiscal.
- Contabilização obrigatória ou fila de exceção; exceções não podem desaparecer em `except Exception`.

### 5.6 Pós-venda

**Existente:** RMA, troca, crédito de cliente, garantia e interação CRM inicial.

**Parcial ou faltante:**

- Devolução por item e documento fiscal, respeitando quantidade já devolvida e condição do produto.
- Estorno fiscal, financeiro, estoque e comissão como eventos independentes e auditáveis.
- Quarentena, laudo, descarte, conserto, retorno ao estoque e retorno ao fornecedor.
- Garantia com série/lote, prazo, fornecedor responsável, custo, SLA, anexos e decisão.
- Métrica de devolução por produto, fornecedor, vendedor, parceiro, lote e motivo.

## 6. Rede de profissionais, fidelização e indicação: capacidades ausentes

### 6.1 Cadastro e governança do parceiro

Criar um módulo próprio, sem reutilizar apenas `clientes.segmento='profissional'`.

- Cadastro do parceiro: pessoa física/jurídica, CPF/CNPJ, nome comercial, contatos, endereço, cidade/UF, especialidades, registro profissional quando aplicável, regiões atendidas e tipos de obra.
- Vínculo com cliente comprador, empresa, equipe, obra e responsáveis autorizados.
- Status: convidado, em análise, aprovado, ativo, suspenso, bloqueado e encerrado.
- KYC operacional: documentos, aceite de regulamento, consentimento LGPD, dados bancários/Pix, responsável pela aprovação e revisão periódica.
- Classificação: eletricista, instalador hidráulico, encanador, técnico, engenheiro, arquiteto, construtora, empreiteiro, manutenção, revenda parceira e influenciador técnico.
- Segmentação por volume, margem, recorrência, especialidade, região e potencial.
- Histórico de aprovação, alteração cadastral, suspensão e motivo.

### 6.2 Atribuição de indicação

Implementar atribuição como evento imutável, não como campo livre na venda.

- Código, link, QR Code ou convite exclusivo do parceiro.
- Registro do primeiro contato, origem da indicação, cliente indicado, data, operador e consentimento do cliente.
- Regras de atribuição: primeiro toque, último toque ou parceiro explicitamente informado no balcão.
- Janela de atribuição configurável e bloqueio de troca retroativa sem aprovação.
- Proteção contra autoindicação, duplicidade de CPF/CNPJ, indicação circular, vendas canceladas e múltiplos parceiros para o mesmo evento.
- Atribuição por cliente, pedido, item ou obra, conforme o programa; a política deve deixar essa escolha explícita.

### 6.3 Fidelidade

Implementar um ledger de pontos/cashback com lançamentos, e não um saldo editável.

- Programa, versão, regras de acúmulo, resgate, expiração, mínimo de resgate e limites.
- Pontos por valor pago, categoria, marca, margem, recorrência, campanha ou ação de relacionamento.
- Cashback como passivo controlado, com data de liberação após pagamento e período de devolução.
- Bloqueio de pontos para venda pendente, inadimplente, cancelada ou devolvida.
- Reversão automática de pontos/cashback em estorno, devolução, cancelamento ou fraude.
- Carteira do cliente e do parceiro separadas, com extrato, saldo disponível, pendente, expirado e estornado.
- Níveis do programa com benefícios, vigência, critérios e downgrade controlado.
- Resgate em desconto, crédito, produto, frete ou benefício autorizado, sempre com limite de margem.

### 6.4 Bonificação por indicação

Separar bonificação de vendedor e de parceiro. A bonificação não deve ser paga no momento da indicação.

- Política versionada por campanha, categoria, margem mínima, canal, região, parceiro, cliente novo/recorrente e período.
- Base de cálculo configurável: venda líquida, margem de contribuição, itens elegíveis ou primeira compra.
- Estados: elegível, pendente de carência, aprovado, bloqueado, provisionado, a pagar, pago, revertido e expirado.
- Carência após pagamento confirmado e fim da janela de devolução.
- Provisão contábil e conta a pagar do parceiro apenas após elegibilidade.
- Lote de pagamento com aprovação financeira, comprovante, conciliação e reversão.
- Extrato detalhado do parceiro, com pedido, item, base, percentual, valor, status e motivo de bloqueio.
- Regras de teto, mínimo de saque, retenções e documentação fiscal conforme orientação contábil.
- Auditoria de qualquer alteração de parceiro, política, atribuição, aprovação ou pagamento.

### 6.5 Portal e relacionamento

- Portal ou área autenticada do parceiro com catálogo elegível, preços/benefícios, indicações, pedidos atribuídos, extrato e status de bonificação.
- Compartilhamento de orçamento com consentimento e proteção de dados do cliente.
- Solicitação de orçamento técnico, lista de materiais, recorrência e compra rápida.
- Comunicação de campanhas, produtos complementares, treinamentos e alertas de ruptura.
- CRM de parceria com contatos, visitas, leads, obras, oportunidades, atividades e próxima ação.
- Controle de acesso para que o parceiro veja somente seus dados, indicações e pedidos permitidos.

## 7. Compras de consumo e margem profissional

O sistema atual possui produto, custo, preço e comissão genéricos, mas não modela a rentabilidade real de compras recorrentes de profissionais e obras. Para tornar essa operação decisória, implementar:

- Entidade de obra/projeto/contrato com cliente, parceiro responsável, endereço, vigência, orçamento, centro de custo e status.
- Lista técnica de materiais por obra, com quantidade prevista, consumida, reservada, comprada e saldo.
- Requisição de consumo vinculada a obra, profissional, equipe ou veículo.
- Histórico de consumo por cliente e parceiro, com recorrência, frequência, ticket, categorias e margem.
- Preço negociado por obra/contrato, tabela de preço por parceiro e vigência aprovada.
- Custo posto por item: aquisição, frete, impostos, despesas acessórias, bonificação de fornecedor, quebra, conversão e custo financeiro.
- Margem bruta, margem de contribuição e margem líquida, separando custo de mercadoria, imposto, taxa de pagamento, frete, comissão, pontos, cashback, bonificação e desconto.
- Piso de margem por categoria, marca, canal, cliente, parceiro e obra.
- Alçada para venda abaixo do piso, com motivo obrigatório e aprovação diferente do vendedor.
- Simulador de mix: permitir desconto em itens de baixa margem compensado por itens de alta margem, desde que a margem total do pedido permaneça aprovada.
- Regras para material bonificado, amostra, brinde, corte, sobra, perda e consumo interno sem contaminar receita de venda.
- Relatórios de rentabilidade por parceiro, obra, cliente, categoria, marca, vendedor, campanha e período.

### Indicadores obrigatórios

- Receita bruta, receita líquida e margem de contribuição por pedido e por item.
- CMV histórico e custo posto.
- Desconto concedido e desconto aprovado.
- Comissão de vendedor, bonificação de parceiro, pontos e cashback provisionados.
- Custo de frete, taxa de pagamento e custo financeiro.
- Lucro de primeira compra e recompra.
- Ticket, frequência, recência, margem acumulada e lifetime value por parceiro/cliente.
- Ruptura e venda perdida de itens de consumo recorrente.
- Conversão de orçamento indicado em pedido pago.
- ROI da campanha e custo por cliente/parceiro ativado.

## 8. Arquitetura recomendada para as próximas implementações

### Backend

- Manter `PostgreSQL → repository → service/use case → schema/contrato → blueprint`.
- Criar módulos de domínio separados: `partner`, `referral`, `loyalty`, `reward_settlement`, `profitability` e `project_consumption`.
- Não adicionar campos de parceiro em `orcamentos` como solução definitiva; usar vínculos de atribuição e eventos versionados.
- Usar `Decimal`/NUMERIC para dinheiro e percentuais monetários; evitar `float` em regra financeira.
- Criar ledger append-only para pontos, cashback, comissão e bonificação, com origem, reversão e idempotência.
- Criar política de margem como serviço único, consumido por pré-venda, promoção, tabela, parceiro, fidelidade e relatório.
- Derivar ator do Bearer em todos os casos; IDs de usuário no payload devem ser removidos ou tratados somente como referência não autoritativa.
- Aplicar locks na entidade financeira e na reserva de crédito antes de calcular disponibilidade.
- Toda postagem operacional deve fechar estoque, financeiro, contábil e auditoria na mesma unidade transacional ou produzir uma pendência explícita e reprocessável.
- Usar migrations Expand/Migrate/Contract para qualquer alteração em pedido, cliente, comissão, preço ou financeiro.

### Frontend

- Criar telas separadas para cadastro de parceiro, regras do programa, indicações, carteira, aprovação financeira e liquidação.
- Manter tabelas densas com padrão Salesforce Lightning Datatable/SLDS: navegação por setas, Enter para edição/ação, foco visível, `aria-sort`, seleção por teclado, cabeçalho fixo, coluna de ações acessível e `data-label` no mobile.
- Usar filtros persistentes, paginação server-side, busca com debounce, carregamento incremental e exportação assíncrona.
- Exibir margem e impacto de cada benefício no carrinho, nunca esconder pontos, cashback, comissão ou bonificação do operador.
- Diferenciar claramente pendente, aprovado, bloqueado, provisionado, pago, estornado e expirado.
- Para telas financeiras, mostrar trilha de auditoria, responsável, motivo e origem do valor.
- Implementar estados de loading, erro, vazio, sem permissão e dado desatualizado de forma distinta.

## 9. Backlog priorizado e critérios de aceite

### Onda 0 — baseline e correções bloqueadoras

- Aplicar e validar migration 143 em DEV, banco vazio e incremental.
- Corrigir divergência de schema na documentação e no readiness.
- Corrigir retry/lock de pagamentos.
- Corrigir recebimento parcial, condição de pagamento, duplicidade de contas a pagar e falha contábil.
- Corrigir tipo de conta na conciliação bancária.
- Remover autoria de usuário enviada pelo cliente nos endpoints críticos.
- Critério de aceite: dois requests concorrentes não duplicam caixa, estoque, título ou bonificação; cada evento tem ator Bearer e correlation id.

### Onda 1 — integridade de estoque e compras

- Corrigir conferência por linha e três vias.
- Refatorar motor de reposição por depósito, unidade, trânsito e demanda.
- Refatorar ABC histórica por depósito e custo histórico.
- Completar recebimento fiscal e financeiro.
- Critério de aceite: compra parcial, nota com sobra/falta, produto repetido e recebimento em depósitos diferentes produzem saldo, título e auditoria corretos.

### Onda 2 — margem e rentabilidade

- Criar motor único de margem de contribuição.
- Definir piso e alçadas por categoria, canal, parceiro e obra.
- Unificar comissão de vendedor e eliminar o relatório legado conflitante.
- Criar custo posto e histórico de preço/margem.
- Critério de aceite: nenhum desconto, comissão, ponto ou benefício aprovado permite margem abaixo do piso sem alçada e motivo.

### Onda 3 — cadastro e programa de parceiros

- Criar migration e domínio de parceiros, vínculos, status, documentos e consentimentos.
- Criar cadastro, aprovação, suspensão, segmentação e histórico.
- Criar atribuição de indicação e código/link/QR.
- Critério de aceite: uma indicação é imutável, auditável, não duplicada e somente atribui venda dentro da política vigente.

### Onda 4 — fidelização e benefícios

- Criar programas, campanhas, níveis e regras versionadas.
- Criar ledger de pontos/cashback, expiração e reversão.
- Integrar cálculo ao pedido e ao pagamento, não somente à tela.
- Critério de aceite: venda pendente não libera benefício; devolução reverte exatamente o lançamento original; retry não duplica saldo.

### Onda 5 — bonificação e liquidação

- Criar elegibilidade, carência, provisão, aprovação, conta a pagar, lote e comprovante.
- Criar extrato do parceiro e reconciliação.
- Criar antifraude e bloqueios por duplicidade, autoindicação e devolução.
- Critério de aceite: financeiro consegue explicar e liquidar cada centavo por pedido, item, parceiro e política versionada.

### Onda 6 — obras, consumo e portal

- Criar obra/projeto, lista técnica, requisição e consumo.
- Criar portal do parceiro com escopo de dados restrito.
- Criar campanhas e comunicação baseada em ruptura, recompra e margem.
- Critério de aceite: uma obra mostra previsto, comprado, recebido, consumido, saldo e margem, sem misturar estoque de outros depósitos.

### Onda 7 — BI, escala e operação

- Criar data mart ou consultas materializadas para vendas, estoque, compras, margem, parceiros e fidelidade.
- Adicionar filtros, drill-down, exportação, agendamento e snapshots.
- Adicionar E2E dos fluxos críticos, teste de concorrência e testes de migration.
- Critério de aceite: relatórios não bloqueiam o PDV, têm data de atualização, filtros explícitos e reconciliam com os ledgers operacionais.

## 10. Gate de prontidão para grande operação

A aplicação só deve ser considerada pronta para uma grande loja quando todos os itens abaixo forem demonstrados em staging:

- Schema atualizado e migration 143 validada.
- Venda concorrente do último estoque sem saldo negativo indevido.
- Pagamento pendente, retry, confirmação, estorno e troco sem duplicidade.
- Crediário aprovado pelo financeiro, condição limitada, reserva concorrente e bloqueio por atraso.
- Compra parcial com parcelas corretas, devolução e conciliação.
- NF-e/NFC-e homologadas com certificado, contingência e eventos principais.
- ABC/XYZ e reposição reconciliadas por depósito.
- Margem por item e pedido contendo todos os custos e benefícios.
- Parceiro indicado, pontos/cashback, devolução, bonificação e pagamento auditados de ponta a ponta.
- Inventário, expedição, entrega, devolução e garantia testados.
- RBAC revisado por matriz de segregação de funções.
- Backup restaurado em simulação, outbox reprocessada e monitoramento funcionando.
- E2E automatizado dos fluxos de caixa, compras, estoque, financeiro, fiscal e parceiros.

## 11. Conclusão

O projeto não precisa ser reescrito. A estratégia correta é corrigir primeiro os efeitos financeiros/estoque e o drift de migration, depois consolidar custo e margem, e somente então construir o programa de parceiros sobre eventos e ledgers auditáveis. A rede de profissionais deve ser tratada como um novo domínio comercial e financeiro, não como um simples campo de cliente ou percentual de comissão.

Até a conclusão das Ondas 0 e 1, o ERP pode continuar sendo usado como base de cadastro e operação assistida, mas não deve ser escalado para decisões automáticas de compra, pagamentos, crédito, bonificação ou rentabilidade sem reconciliação manual.
