# Plano mestre de implementação do ERP Casa LM

**Versão do plano:** 1.0  
**Data:** 2026-08-31  
**Base:** `RELATORIO_LACUNAS_ERP.md`, `AGENTS.md`, `CONTEXTO_SESSAO.md`, `DESENVOLVIMENTO.md` e estado atual do código.  
**Objetivo:** transformar as lacunas levantadas em um backlog prescritivo, com ordem de execução, blueprint de dados/API/UI, critérios de aceite, testes e gates de publicação.

## 1. Regra de execução

Este documento é o contrato de desenvolvimento das próximas fases. O agente que executar uma tarefa deve seguir a especificação da tarefa, os documentos de domínio e o `AGENTS.md`. Não é permitido substituir uma entrega por uma aproximação silenciosa, inventar regra fiscal/comercial ou marcar uma tarefa como pronta apenas porque o endpoint responde.

### 1.1 Condições obrigatórias para qualquer tarefa

1. Ler `AGENTS.md`, `CONTEXTO_SESSAO.md`, este plano e os documentos do domínio antes de editar.
2. Executar `git status --short`, mapear consumidores e preservar alterações de outros agentes.
3. Identificar impacto em PostgreSQL, backend, contrato API, frontend, jobs, relatórios, integrações e imagens.
4. Se houver alteração de banco, usar migração versionada com `VERSION`, `RISCO`, `NAME`, `MUDANCA`, `guard`, `forward` e `backward`.
5. Usar Expand/Migrate/Contract em qualquer alteração incompatível; nunca fazer banco, backend e frontend incompatíveis em uma única tacada.
6. Manter o frontend dependente somente da API, nunca de tabela ou coluna do PostgreSQL.
7. Aplicar autorização no backend; esconder botão no frontend é apenas melhoria de UX.
8. Toda operação que altere mais de uma entidade deve usar uma transação única, locks adequados, idempotência e estorno definido.
9. Toda lista deve ter paginação, filtros, estados de carregamento/erro/vazio e limite de volume.
10. Toda tarefa deve terminar com testes, documentação da evidência, atualização do contexto, commit e push.
11. Deploy, restart, rebuild, migration em staging/produção ou exclusão de dados só podem ocorrer depois de confirmação explícita do usuário.

### 1.2 Regra de aceite

Uma tarefa somente passa para `Concluída` quando todos os itens abaixo estiverem verdadeiros:

- código implementado em camadas corretas;
- contrato OpenAPI e tipos frontend atualizados;
- migração testada em banco vazio e incremental, quando aplicável;
- testes unitários, integração e regressão do fluxo;
- UI validada em desktop, tablet e mobile quando houver UI;
- teclado, foco, acessibilidade e estados de erro validados;
- RBAC e auditoria validados;
- logs sem segredo e com correlation ID;
- rollback comportamental e estrutural documentado;
- staging validado somente após autorização de publicação;
- `CONTEXTO_SESSAO.md` atualizado com status real.

## 2. Status e dependências

### 2.1 Legenda

- **P0:** bloqueia conformidade, integridade ou operação segura.
- **P1:** necessário para operar profissionalmente e decidir compras/estoque/financeiro.
- **P2:** produtividade, integração e inteligência comercial.
- **P3:** escala e otimização avançada.
- **BASE:** já existe, deve ser preservado e complementado.
- **A FAZER:** ainda não há fluxo completo.
- **EXTERNO:** depende de contador, provedor, banco, adquirente, certificado ou decisão do negócio.

### 2.2 Grafo de dependências

```text
S0 Contratos e regras
 ├─ S1 Dados mestres e contexto de empresa
 │   ├─ S2 Estoque, custo e inventário
 │   │   └─ S4 Necessidade de compra e ABC
 │   └─ S3 Compras e recebimento
 ├─ S5 Venda, caixa e pagamentos
 │   └─ S6 Devolução, garantia e pós-venda
 ├─ S7 Fiscal real
 ├─ S8 Relatórios e indicadores
 └─ S9 UX, acessibilidade, E2E e operação
       └─ S10 Integrações e piloto controlado
```

Não iniciar S4 sem S2, pois a sugestão de compra dependeria de saldo e custo incorretos. Não iniciar S8 como relatório final antes de S2, S3 e S5, pois os indicadores seriam incompletos. Não liberar S7 para produção sem os artefatos externos e aprovação fiscal.

## 3. Sprint 0 — governança, contratos e critérios

**Prioridade:** P0  
**Objetivo:** preparar o terreno para que as sprints seguintes não criem dados incompatíveis.

### GOV-001 — Matriz de processos e responsáveis

**Fazer:** documentar os processos reais da loja: venda balcão, orçamento de obra, reserva, retirada, entrega, compra para reposição, compra para cliente, recebimento, devolução, garantia, caixa e fechamento.

**Como:** criar uma matriz com processo, ator, documento de origem, estado, efeitos em estoque/financeiro/fiscal, permissão, exceções e responsável pelo aceite. Marcar explicitamente o que é decisão do negócio.

**Entrega:** `docs/erp/processos-operacionais.md` e matriz de responsáveis.

**Aceite:** cada fluxo possui início, fim, estados, cancelamento, estorno, ator e evidência esperada; nenhum agente precisa inferir regra ausente.

### GOV-002 — Dicionário de dados e contratos

**Fazer:** padronizar nomes, unidades, status, datas, dinheiro, percentuais, identificadores, códigos de erro e paginação.

**Como:** criar `docs/erp/contracts/dicionario-dados.md`, schemas JSON/OpenAPI e tipos TypeScript. Definir `id`, `empresa_id`, `filial_id`, `deposito_id`, `criado_em`, `atualizado_em`, `versao` e `correlation_id` onde aplicável.

**Aceite:** novas APIs não retornam campos internos sem decisão; erros seguem `{error, code, details, correlation_id}`; filtros e limites são validados no backend.

### GOV-003 — Catálogo de estados e transições

**Fazer:** centralizar máquinas de estado para pedido de venda, compra, recebimento, estoque, fiscal, financeiro, devolução e garantia.

**Como:** cada transição terá `from`, `to`, comando, permissão, pré-condições, efeitos, evento, idempotência e estorno. Proibir `PATCH` livre de status em documentos críticos.

**Aceite:** transição inválida retorna erro estável; cada transição gera auditoria e teste.

### GOV-004 — Feature flags e plano de rollout

**Fazer:** criar flags para motor de compras, ABC real, custo histórico, entrada fiscal e novo recebimento.

**Como:** flag comportamental não desfaz migração; configurar por ambiente e registrar autor/data. Definir fallback compatível durante Expand/Migrate/Contract.

**Aceite:** desligar a flag reverte comportamento sem perda estrutural; ambiente antigo continua funcionando durante o período de coexistência.

## 4. Sprint 1 — dados mestres, empresa e produto

**Prioridade:** P0/P1  
**Objetivo:** garantir que produto, unidade, embalagem, fornecedor, empresa e filial tenham dados confiáveis.

### MDM-001 — Contexto de empresa/filial

**Fazer:** decidir e implementar o escopo monoempresa ou multiempresa/multifilial.

**Como:** se multiempresa for aprovado, criar `empresas`, `filiais` e contexto autenticado; adicionar `empresa_id`/`filial_id` aos dados de negócio via Expand, backfill e dual read/write. Se monoempresa continuar, registrar a decisão e deixar o modelo preparado sem simular isolamento.

**Aceite:** nenhum usuário consulta ou altera dados fora do escopo; relatórios consolidado/filtrado funcionam; séries fiscais, caixas, depósitos, certificados e preços respeitam filial.

### MDM-002 — Unidade e conversão comercial

**Fazer:** modelar unidade de estoque, venda, compra, tributável, embalagem e conversão.

**Como:** criar tabela de conversões versionadas por produto/embalagem, com fator positivo, arredondamento, unidade base e validade. Preservar `unidade_venda` atual durante a migração.

**Aceite:** `1 CX = N UN`, `1 RL = N M` e fracionamento são calculados sem perda; estoque usa unidade base; pedido/compra/fiscal exibem a unidade correta; conversão fica auditada.

### MDM-003 — Códigos e identificação

**Fazer:** suportar múltiplos EAN/GTIN, código interno, fabricante, fornecedor e embalagem.

**Como:** criar cadastro de identificadores com tipo, valor normalizado, produto, embalagem, origem e ativo. Validar GTIN quando aplicável, unicidade por contexto e busca exata antes da busca textual.

**Aceite:** scanner encontra produto por qualquer código ativo; duplicidade é bloqueada; código inativo não vende; produto sem GTIN pode usar código interno sem inventar GTIN.

### MDM-004 — Atributos técnicos do ramo

**Fazer:** complementar atributos de cabos, tubos, conexões, ferragens, ferramentas e químicos.

**Como:** manter atributos flexíveis em JSONB, mas promover para colunas relacionais os campos usados em filtro, tributação, cálculo ou integração: bitola, tensão, potência, comprimento, diâmetro, rosca, material, cor, norma, validade e garantia.

**Aceite:** filtros por atributos são indexáveis; produto não perde histórico; obrigatoriedade varia por família; a descrição comercial é gerada sem substituir os dados estruturais.

### MDM-005 — Equivalentes, substitutos e kits

**Fazer:** permitir equivalência comercial, substituição, acessórios e composição/desmonte.

**Como:** criar relações tipadas com vigência, fator, prioridade, aprovação e motivo. Kits devem ter composição versionada e movimento auditável.

**Aceite:** busca mostra substitutos e complementares; venda só substitui com confirmação; kit baixa componentes corretos; alterações não mudam documentos antigos.

### MDM-006 — Qualidade e importação de cadastro

**Fazer:** criar workflow de cadastro `rascunho → revisão → publicado → bloqueado` e importação em lote segura.

**Como:** upload em job, prévia por linha, validação, deduplicação por SKU/EAN/nome+marca, relatório de erros e commit idempotente. Não gravar parcialmente sem indicar o resultado.

**Aceite:** importação pode ser simulada; erros são corrigíveis; reprocessar o mesmo arquivo não duplica; cada linha possui auditoria.

### MDM-007 — Preço e margem

**Fazer:** completar preço por cliente, segmento, quantidade, canal, região, condição e vigência.

**Como:** manter tabelas/revisões existentes e adicionar prioridade de regra, data/hora de vigência, aprovação, margem mínima, comissão, custo financeiro e custo fiscal. O motor devolve preço aplicado e explicação.

**Aceite:** o mesmo item em contextos diferentes mostra a regra aplicada; preço abaixo da margem exige alçada; rollback de revisão é possível; margem usa custo definido pelo módulo de custos.

## 5. Sprint 2 — estoque, custo e inventário

**Prioridade:** P0/P1  
**Objetivo:** transformar estoque em saldo confiável, auditável e valorizado.

### EST-001 — Modelo de disponibilidade

**Fazer:** separar físico, reservado, bloqueado, disponível, em separação e em trânsito.

**Como:** definir fórmula única no service de estoque e expô-la em todas as APIs. Persistir somente fatos e saldos derivados necessários, com reconciliação.

**Aceite:** disponível não fica negativo sem exceção autorizada; reserva reduz disponível, não físico; transferência altera origem/destino corretamente; dashboard e venda usam a mesma fórmula.

### EST-002 — Fatos e idempotência

**Fazer:** completar o ledger imutável de movimentos.

**Como:** todo fato terá produto, depósito, quantidade, unidade base, custo, tipo, documento origem, usuário, horário, idempotency key e estorno. Não editar movimento; corrigir com estorno e novo fato.

**Aceite:** retry não duplica; movimento sem origem é rejeitado; estorno mantém cadeia; reconciliação identifica divergências.

### EST-003 — Custo médio e custo histórico

**Fazer:** definir método oficial com contador e implementar custo por entrada e saída.

**Como:** persistir custo unitário do movimento; calcular custo médio por depósito conforme política aprovada; incluir frete, descontos e impostos conforme regra fiscal/contábil. Não usar custo atual para margem histórica.

**Aceite:** entrada altera custo conforme método; saída usa custo do momento; período fechado bloqueia alteração; margem e CMV reproduzem o custo registrado.

### EST-004 — Valorização e revaloração

**Fazer:** criar valorização por data de corte, depósito, produto, lote e grupo.

**Como:** consulta de saldo e ledger com custo histórico; revaloração como documento aprovado e lançamento contábil, nunca update direto.

**Aceite:** relatório de estoque bate com saldo; revaloração é auditada; diferença entre físico e contábil é explicável.

### EST-005 — Limites, ponto de pedido e segurança

**Fazer:** substituir a visão simplificada de mínimo/máximo por parâmetros de planejamento.

**Como:** criar parâmetros por produto/depósito: política, mínimo, máximo, ponto de pedido, estoque de segurança, lead time, lote mínimo, máximo, múltiplo, calendário e fonte do valor.

**Aceite:** parâmetros podem ser manuais ou calculados; alteração registra autor e motivo; cálculo não mistura unidades nem depósitos.

### EST-006 — Inventário cíclico

**Fazer:** completar contagem física por ciclo e ABC/XYZ.

**Como:** documento de inventário com depósito/endereço, lista congelada, contador, contagem cega/dupla, divergência, aprovação e postagem. Importar CSV/XLSX/coletor de forma idempotente.

**Aceite:** item contado não pode ser editado após fechamento; ajuste exige motivo/alçada; movimentação durante contagem é controlada; relatório mostra acuracidade e perdas.

### EST-007 — Endereçamento e operação de armazém

**Fazer:** criar corredor, módulo, prateleira, gaveta, picking e localização alternativa.

**Como:** tabela de endereços por depósito, prioridade de picking, capacidade e ativo. Movimentação/contagem/separação usam endereço opcional ou obrigatório por depósito.

**Aceite:** operador encontra localização; transferências preservam endereço; inventário pode ser roteirizado por endereço.

### EST-008 — Lote, validade e série

**Fazer:** completar rastreabilidade parametrizada por família.

**Como:** cadastro de lote/série com entrada, validade, custo, status, fornecedor e documento; vínculos de saída, devolução e garantia; FEFO/FIFO conforme regra.

**Aceite:** item controlado não entra ou sai sem rastreio; lote vencido/bloqueado não é vendido; recall lista clientes e documentos afetados.

## 6. Sprint 3 — ABC, demanda e necessidade de compra

**Prioridade:** P1  
**Objetivo:** gerar sugestões de compra explicáveis e úteis para o comprador.

### COM-001 — ABC histórica

**Fazer:** substituir a dependência operacional da ABC estimada por cálculo histórico.

**Como:** criar job/API de cálculo por período, empresa, depósito e critério: valor de consumo, receita, margem, quantidade e frequência. Excluir cancelamentos/devoluções conforme regra; salvar versão, parâmetros, total, acumulado e classificação.

**Aceite:** classe é reproduzível; usuário vê fórmula/período; custo da margem é histórico; item sem venda aparece separado; ABC estimada fica identificada como bootstrap.

### COM-002 — XYZ e matriz de política

**Fazer:** classificar variabilidade/intermitência da demanda e cruzar ABC×XYZ.

**Como:** usar histórico mensal/semanal mínimo configurável, calcular média, desvio, coeficiente de variação e intermitência. Mapear matriz para política de estoque, contagem e serviço.

**Aceite:** item com alta margem e demanda irregular não recebe política automática indevida; parâmetros e limiares são configuráveis e auditados.

### COM-003 — Base de demanda

**Fazer:** consolidar demanda real e projetada.

**Como:** considerar vendas confirmadas, pedidos abertos, reservas, devoluções, sazonalidade, obras/projetos e consumo manual. Separar demanda atendida de demanda perdida por ruptura.

**Aceite:** demanda pode ser auditada até os documentos; pedido cancelado não permanece como demanda; venda parcial e ruptura ficam identificadas.

### COM-004 — Motor de reposição

**Fazer:** calcular necessidade por produto/depósito.

**Como:** fórmula base:

```text
disponível_projetado = físico - reservado - bloqueado
                    + compras_confirmadas_em_trânsito
                    - demanda_aberta

necessidade = máximo(0,
  estoque_alvo + demanda_durante_lead_time - disponível_projetado)
```

Aplicar estoque de segurança, ponto de pedido, lote mínimo, múltiplo, embalagem, pedido em aberto, prazo e política. O resultado deve trazer todos os componentes do cálculo.

**Aceite:** não sugere compra duplicada; mostra data provável de ruptura, quantidade, fornecedor e justificativa; arredondamento respeita unidade de compra; compra sob encomenda não vira estoque automático.

### COM-005 — Fornecedor e lead time

**Fazer:** medir desempenho real do fornecedor.

**Como:** registrar datas prometida, enviada, recebida e aceita; calcular lead time médio, desvio, fill rate, preço líquido, indisponibilidade e atraso. Permitir override manual com motivo.

**Aceite:** sugestão usa lead time real quando houver amostra mínima; pouca amostra aparece como baixa confiança; comprador pode comparar fornecedor preferencial e alternativa.

### COM-006 — Tela de sugestões de compra

**Fazer:** criar `#/compras/necessidades`.

**Como:** tabela com filtros depósito/ABC/XYZ/fornecedor/prioridade/ruptura, colunas selecionáveis, detalhe do cálculo, seleção em lote, ajuste com justificativa e ação “gerar solicitação/cotação”.

**Aceite:** seleção não perde filtros; ação em lote respeita RBAC; cada linha explica o motivo; teclado e tabela seguem o contrato Lightning/SLDS do projeto.

## 7. Sprint 4 — solicitação, cotação e pedido de compra

**Prioridade:** P1  
**Objetivo:** fechar o ciclo de compras sem redigitação e com aprovação.

### COM-007 — Solicitação de compra

**Fazer:** completar status, prioridade, origem, centro de custo, depósito, solicitante, aprovação e prazo.

**Como:** máquina `rascunho → enviada → aprovada → cotando → convertida → cancelada`; itens têm unidade, necessidade, justificativa e origem de sugestão.

**Aceite:** solicitação aprovada não pode ser editada sem nova versão; cotação nasce vinculada; cancelamento deixa auditoria.

### COM-008 — Cotação a partir de necessidade

**Fazer:** gerar cotação a partir de solicitações e sugestões.

**Como:** comando idempotente consolida itens compatíveis, preserva depósito/destino, convida fornecedores conforme preferência e permite split quando fornecedores diferentes vencem.

**Aceite:** não duplica item; origem é rastreável; alterações têm versão; comprador vê itens sem proposta.

### COM-009 — Comparação de propostas

**Fazer:** tornar comparação baseada em custo total e serviço.

**Como:** normalizar preço por unidade base, desconto, impostos, frete, embalagem, prazo, condição, marca e disponibilidade. Mostrar preço bruto/líquido e custo efetivo.

**Aceite:** comparação não escolhe automaticamente somente pelo menor preço; usuário consegue justificar vencedor; total é recalculável.

### COM-010 — Aprovação de compra

**Fazer:** criar alçada por valor, grupo, fornecedor, centro de custo e margem.

**Como:** regras configuráveis, segregação solicitante/aprovador, aprovação/rejeição com motivo, versão e validade. Backend bloqueia envio/recebimento sem aprovação quando exigido.

**Aceite:** usuário sem alçada não aprova; alteração relevante invalida aprovação; auditoria registra antes/depois.

### COM-011 — Pedido de compra

**Fazer:** completar pedido editável/congelado, envio, confirmação, parcial, backorder e cancelamento.

**Como:** máquina `rascunho → aprovado → enviado → confirmado → parcialmente_recebido → recebido → cancelado`; gerar PDF, e-mail/WhatsApp via outbox e confirmação do fornecedor.

**Aceite:** pedido enviado é imutável salvo alterações autorizadas; saldo cancelado não pode ser recebido; pedido parcial mantém saldo aberto.

### COM-012 — Histórico e fornecedor

**Fazer:** exibir preço, prazo e desempenho por produto/fornecedor.

**Como:** fatos originados de pedidos/recebimentos; evitar campos manuais duplicados; permitir análise por período e unidade.

**Aceite:** comprador consegue decidir com histórico confiável; dado importado tem origem e data.

## 8. Sprint 5 — recebimento, nota de entrada e custo

**Prioridade:** P0/P1  
**Objetivo:** impedir que entrada física, fiscal, estoque e contas fiquem divergentes.

### REC-001 — Documento de recebimento

**Fazer:** criar recebimento separado do pedido, com conferência parcial.

**Como:** cabeçalho fornecedor, depósito, operador, data, pedido, documento fiscal e status; itens pedido, recebido, aceito, recusado, avariado e pendente.

**Aceite:** dois recebimentos do mesmo pedido são permitidos sem ultrapassar saldo; retry não duplica; pedido atualiza status corretamente.

### REC-002 — Conferência por código/unidade

**Fazer:** receber por scanner, embalagem, conversão e contagem cega.

**Como:** resolver identificador para produto/embalagem, converter para unidade base e mostrar divergência de quantidade/preço/unidade.

**Aceite:** caixa/rolo não gera quantidade errada; produto desconhecido vai para exceção; operador consegue concluir sem mouse.

### REC-003 — Três vias

**Fazer:** comparar pedido, recebimento e NF/XML.

**Como:** normalizar linhas, tolerâncias por fornecedor, aprovação de divergência e estados `aguardando_conferência`, `divergente`, `aprovado`, `rejeitado`.

**Aceite:** diferença de preço/quantidade/fiscal fica visível; tolerância não esconde divergência; só aprovação gera efeitos definitivos.

### REC-004 — Entrada fiscal XML

**Fazer:** importar XML, vincular produtos e criar prévia.

**Como:** validar assinatura/formato, chave única, fornecedor, itens, NCM/CFOP/CST, impostos, lote e total; usar matching por código fornecedor/EAN/descrição com confirmação humana.

**Aceite:** XML duplicado é rejeitado; item sem vínculo não entra silenciosamente; fiscal pode corrigir vínculo antes da confirmação.

### REC-005 — Postagem de recebimento

**Fazer:** em uma transação, postar estoque, custo, conta a pagar, fiscal snapshot e contabilidade.

**Como:** service de recebimento com lock no pedido/saldo, idempotency key e outbox somente para integração externa. Erro desfaz tudo localmente.

**Aceite:** não existe estoque sem origem, título sem recebimento ou custo sem documento; reprocessamento é seguro.

### REC-006 — Devolução ao fornecedor

**Fazer:** criar devolução vinculada ao recebimento/NF/lote.

**Como:** validar quantidade disponível, motivo, estado, documento fiscal e efeitos: saída de estoque, crédito/estorno a pagar, evento fiscal e auditoria.

**Aceite:** não devolve mais que o recebido; lote/série é rastreado; conta a pagar fica correta.

## 9. Sprint 6 — venda, PDV, caixa e pagamentos

**Prioridade:** P0/P1  
**Objetivo:** fechar o ciclo de balcão e venda a prazo.

### VEN-001 — Unidade de venda e produto alternativo

**Fazer:** permitir venda por UN, CX, RL, M, KG, kit e fracionado.

**Como:** preço e estoque usam unidade base; tela mostra conversão e quantidade resultante; fiscal recebe unidade tributável correta.

**Aceite:** venda fracionada não cria saldo decimal inválido; total e documento fiscal batem; operador confirma conversão quando ambígua.

### VEN-002 — Pré-venda/PDV de alta velocidade

**Fazer:** otimizar busca por scanner, EAN, SKU, código fornecedor, termo e atributos.

**Como:** endpoint de busca rápida com debounce, ranking, limite e cache; teclado com contrato documentado: descrição vazia + Enter segue desconto → condição → observação → finalizar.

**Aceite:** busca não rouba foco; modal de autorização preserva login; tabela/lista opera sem mouse; produto indisponível explica saldo/reserva.

### VEN-003 — Pagamentos múltiplos

**Fazer:** aceitar dinheiro, PIX, débito, crédito, boleto, transferência e combinação.

**Como:** entidade de parcelas/pagamentos por pedido com valor, forma, taxa, provedor, status, idempotência e estorno. Cartão/PIX aguardam confirmação quando necessário.

**Aceite:** soma dos pagamentos fecha o total; troco só em dinheiro; pagamento pendente não marca venda como paga; retry não duplica.

### VEN-004 — Caixa e terminal

**Fazer:** implementar abertura, suprimento, sangria, venda, recebimento, fechamento e diferença por operador/terminal.

**Como:** sessão de caixa com lock, saldo inicial, movimentos, saldo esperado, contado, diferença, justificativa e aprovação.

**Aceite:** dois operadores não usam sessão indevida; fechamento bloqueia novos movimentos; relatório reconcilia caixa e contas.

### VEN-005 — Estados de venda e unidade de trabalho

**Fazer:** separar orçamento, pedido, reserva, faturamento, retirada e entrega.

**Como:** service transacional com locks e comandos; outbox após commit; cada transição tem evento e estorno.

**Aceite:** venda concorrente do último item é serializada; cancelamento reverte reserva/estoque/financeiro; emissão não duplica documento.

### VEN-006 — Crédito, parcelas e cobrança

**Fazer:** completar limite, atraso, renegociação e parcelamento.

**Como:** cliente identificado, política de crédito, parcelas, juros/multa/desconto, contas a receber e cobrança vinculadas. Consumidor padrão segue regra comercial definida, sem bypass fiscal.

**Aceite:** bloqueios são explicáveis; parcela vencida é recalculada com política; reabrir ou devolver estorna títulos corretamente.

### VEN-007 — TEF e adquirência

**Fazer:** integrar adquirente/TEF ou definir escopo manual inicial.

**Como:** adapter por provedor, estados de autorização/captura/estorno, conciliação e outbox. Nunca marcar cartão como recebido só por clique local.

**Aceite:** transação aprovada, negada, timeout e estornada são tratados; taxas e liquidação aparecem no financeiro.

## 10. Sprint 7 — devoluções, trocas, garantias e comercial

**Prioridade:** P1/P2  
**Objetivo:** fechar o pós-venda e aumentar controle comercial.

### POS-001 — RMA/devolução

**Fazer:** criar autorização de retorno vinculada à venda/documento/item.

**Como:** estados `solicitada → autorizada → recebida → analisada → concluída/rejeitada`; validar prazo, motivo, quantidade, série/lote e condição.

**Aceite:** devolução acima do vendido é bloqueada; todos os efeitos têm origem; usuário vê o saldo de crédito/estorno.

### POS-002 — Troca e crédito

**Fazer:** tratar troca por outro produto, diferença, crédito de cliente ou estorno.

**Como:** transação única com entrada do item original, saída do substituto, ajuste financeiro e documento fiscal quando aplicável.

**Aceite:** diferença positiva/negativa é calculada; não há crédito duplicado; preço/custo histórico ficam preservados.

### POS-003 — Garantia

**Fazer:** completar garantia com fornecedor, laudo e prazo.

**Como:** RMA fornecedor, anexos, número de série, custos, responsabilidade, status e SLA.

**Aceite:** operador acompanha pendência; retorno ao estoque/quarentena é rastreado; relatório de defeitos por fornecedor/produto existe.

### POS-004 — CRM e orçamento de obra

**Fazer:** registrar oportunidade, obra/projeto, follow-up, orçamento perdido e próxima ação.

**Como:** entidades vinculadas ao cliente e vendedor; lembretes via outbox; métricas de conversão e margem.

**Aceite:** carteira do vendedor é filtrável; orçamento perdido exige motivo; follow-up vencido gera alerta.

### POS-005 — Comissões

**Fazer:** calcular comissão por venda, margem, recebimento, devolução e cancelamento.

**Como:** política versionada; base e percentual congelados no evento; estorno gera reversão, não edição retroativa.

**Aceite:** relatório apura e explica comissão; usuário não altera cálculo sem alçada.

## 11. Sprint 8 — fiscal real e compliance

**Prioridade:** P0 e EXTERNO  
**Objetivo:** sair do modo estrutural/sandbox somente depois de validação fiscal formal.

### FIS-001 — Matriz fiscal aprovada

**Fazer:** validar cenários com contador/responsável fiscal.

**Como:** para cada operação, documentar produto, origem, UF, destinatário, regime, CFOP, CST/CSOSN, PIS/COFINS, ICMS/ST, CEST, benefício e vigência. NCM nunca decide imposto sozinho.

**Aceite:** matriz baseline assinada/aprovada; casos ambíguos retornam `FISCAL_REVIEW_REQUIRED`.

### FIS-002 — Emissão NF-e/NFC-e

**Fazer:** fechar emissão, consulta, autorização, rejeição, denegação, cancelamento e inutilização.

**Como:** adapter Focus/TecnoSpeed isolado do domínio; request hash, referência idempotente, XML/XSD, protocolo, chave, PDF e eventos persistidos.

**Aceite:** cenários golden autorizam em homologação; timeout consulta antes de reenviar; rejeição é explicável; retry não duplica.

### FIS-003 — Certificados e credenciais

**Fazer:** configurar A1/A3/CSC/token por ambiente e filial.

**Como:** segredo somente em secret manager/env; teste de validade e alerta de expiração; nunca retornar segredo ao frontend/log.

**Aceite:** produção não sobe sem configuração explícita; staging e produção não compartilham credencial de operação.

### FIS-004 — Contingência NFC-e

**Fazer:** implementar contingência offline controlada.

**Como:** habilitação por flag/permissão, série/numeração, motivo, fila, assinatura, transmissão posterior, rejeição e reconciliação.

**Aceite:** contingência não é habilitada por erro genérico; documentos transmitidos posteriormente preservam vínculo e ordem; prazos legais são validados externamente.

### FIS-005 — Eventos e manifestação

**Fazer:** adicionar cancelamento, CC-e, inutilização e manifestação de entrada quando aplicável.

**Como:** comandos por documento autorizado, validação de prazo, certificado, evento único e auditoria.

**Aceite:** evento inválido é bloqueado antes do envio; situação do documento reflete retorno real.

### FIS-006 — Entrada por XML e obrigações

**Fazer:** integrar NF de entrada, XML, estoque, contas, custo e exportação contábil/fiscal.

**Como:** pipeline parse → matching → conferência → aprovação → postagem; armazenar XML e eventos; definir exportações exigidas pelo regime.

**Aceite:** NF recebida é rastreável até estoque/custo/conta; duplicidade e divergência têm tratamento; contador valida arquivos gerados.

## 12. Sprint 9 — relatórios e indicadores

**Prioridade:** P0/P1  
**Objetivo:** criar uma central de decisão para administrativo, compras, estoque e vendas.

### BI-001 — Camada de consultas analíticas

**Fazer:** separar consultas operacionais de agregações pesadas.

**Como:** criar views/materialized views ou tabelas de fatos conforme volume; jobs incrementais, índice por período/empresa/depósito e snapshot de cálculo.

**Aceite:** relatório grande não bloqueia transação operacional; resultado é reproduzível; tempo e volume monitorados.

### BI-002 — Dashboard executivo

**Fazer:** construir painel com receita líquida, margem, CMV, ticket, caixa, inadimplência, estoque e compras.

**Como:** cards acionáveis, comparação de período/meta, filtros globais e alertas com link para resolução.

**Aceite:** números batem com relatórios detalhados; usuário consegue explicar cada KPI até a origem.

### BI-003 — Relatórios de vendas

**Fazer:** implementar vendas por produto, grupo, marca, vendedor, cliente, depósito, canal, forma e período.

**Como:** incluir pedidos cancelados/devolvidos separadamente; receita bruta/líquida, desconto, custo histórico, margem e comissão.

**Aceite:** filtros combináveis; exportação respeita filtro; drill-down abre documento autorizado.

### BI-004 — Relatórios de compras

**Fazer:** implementar necessidade, pedidos, atrasos, preço, economia, fill rate, lead time e dependência.

**Como:** fatos de cotação/pedido/recebimento; medir prometido versus realizado; exibir baixa confiança quando amostra insuficiente.

**Aceite:** comprador identifica o que comprar, de quem, quanto, quando e por quê.

### BI-005 — Relatórios de estoque

**Fazer:** implementar saldo, kardex, valorização, giro, cobertura, ruptura, excesso, parado, validade e ABC/XYZ.

**Como:** filtros por depósito/endereço/grupo/marca/fornecedor; custo e período de corte; vínculos para movimentos.

**Aceite:** saldo do relatório bate com estoque; ABC histórica é distinguida da estimada; produto problemático abre ação corretiva.

### BI-006 — Financeiro e contábil

**Fazer:** implementar fluxo de caixa, aging, DRE, orçamento versus realizado, conciliação e rentabilidade.

**Como:** separar competência/caixa, títulos abertos/pagos, taxas, juros, centros e contas; período fechado não muda.

**Aceite:** contador valida DRE e exportação; diferenças são explicáveis por origem.

### BI-007 — Central de relatórios

**Fazer:** criar `#/relatorios` com catálogo, favoritos, presets, colunas, exportações e agendamento.

**Como:** cada relatório declara schema, filtros, RBAC, limite, formato e job assíncrono. Exportação sensível exige permissão própria.

**Aceite:** usuário administrativo não vê relatório fiscal/financeiro sem permissão; exportações grandes aparecem na fila e podem ser baixadas depois.

## 13. Sprint 10 — frontend, UX e acessibilidade

**Prioridade:** P1  
**Objetivo:** aplicar o padrão de ERP cloud em todos os módulos, sem quebrar o teclado do PDV.

### UX-001 — Navegação e contexto

**Fazer:** reorganizar shell em Operação, Comercial, Compras, Estoque, Financeiro, Fiscal, Relatórios e Administração.

**Como:** breadcrumb, título, contexto de filial/depósito/período, ação primária, filtros ativos e estado da tela.

**Aceite:** usuário sabe onde está e qual contexto está usando; rotas antigas redirecionam sem duplicar fluxo.

### UX-002 — Tabela padrão

**Fazer:** criar um componente único para tabelas de ERP.

**Como:** aplicar cabeçalho semântico, ordenação, filtro por coluna, seleção, ações em lote, ações por linha, colunas configuráveis, densidade, paginação, virtualização, `aria`, foco e mobile cards. Seguir [Lightning Datatable Accessibility](https://developer.salesforce.com/docs/platform/lwc/guide/data-table-a11y.html) e [SLDS](https://developer.salesforce.com/docs/platform/lightning-component-reference/guide/lightning-datatable.html?type=Example).

**Aceite:** tabela funciona com teclado; seleção/ordenação não perde foco; exportação usa filtros; desktop/mobile foram verificados.

### UX-003 — Formulários e modais

**Fazer:** padronizar labels, validação, mensagens, foco, dirty state e confirmação.

**Como:** `Field` associado, `aria-describedby`, foco inicial, trap, Escape, restauração, erro por campo, resumo de erro e confirmação contextual.

**Aceite:** modal de desconto mantém foco; cadastro de cliente não perde foco; ação irreversível informa impacto e permissão.

### UX-004 — Atalhos e PDV sem mouse

**Fazer:** documentar e testar mapa de teclado por tela.

**Como:** evitar handlers globais invasivos; usar roving tabindex/arrow navigation onde aplicável; Enter, Tab, Shift+Tab, Escape e setas têm comportamento estável.

**Aceite:** roteiro de caixa conclui venda só com teclado; foco não é roubado por render; leitor de tela não recebe atalhos inesperados.

### UX-005 — Estados, feedback e erros

**Fazer:** completar loading, skeleton, empty, stale, erro, retry, disabled e sucesso.

**Como:** usar `ApiError`, códigos de negócio e mensagens sem detalhes internos. Ações em andamento desabilitam apenas o necessário e suportam retry seguro.

**Aceite:** falha fiscal/financeira explica próxima ação; não há tela vazia ambígua; cor não é único indicador.

### UX-006 — Desempenho e volume

**Fazer:** virtualizar catálogo, estoque, compras e relatórios; reduzir fetch/re-render.

**Como:** paginação server-side, cache/invalidação, code splitting, TanStack Query ou padrão equivalente e medição com dados reais.

**Aceite:** nenhum módulo carrega milhares de linhas inicialmente; métricas de tempo inicial e interação ficam registradas.

### UX-007 — Acessibilidade e localização

**Fazer:** validar WCAG 2.2 AA, contraste, zoom, leitor de tela, BRL, data/fuso e impressão.

**Como:** auditoria automatizada + roteiro manual; usar tokens de design e formatadores centrais.

**Aceite:** principais fluxos passam teclado/contraste/zoom 200%; PDF A4 e térmico permanecem legíveis.

## 14. Sprint 11 — API, arquitetura, concorrência e qualidade

**Prioridade:** P0/P1  
**Objetivo:** impedir regressões estruturais durante a implementação dos módulos.

### ARC-001 — Services/use cases

**Fazer:** manter Blueprint fino e extrair regras de venda, recebimento, compra, estoque, fiscal e financeiro.

**Como:** controller valida transporte; schema valida payload; service aplica regra/transação; repository consulta/escreve; adapter integra externo.

**Aceite:** teste de regra não depende de Flask; operações multi-entidade têm um ponto transacional; nenhum endpoint crítico faz SQL e regra fiscal misturados.

### ARC-002 — Schemas e contratos

**Fazer:** validar entrada/saída de endpoints críticos.

**Como:** Pydantic/Marshmallow ou camada existente, com enum/status, limites, decimal, datas, ids e campos desconhecidos rejeitados quando seguro.

**Aceite:** payload inválido retorna 400 com erro de campo; OpenAPI descreve request/response; tipos frontend não usam `any` para o contrato.

### ARC-003 — Idempotência transversal

**Fazer:** aplicar chave idempotente a criação de pedido, recebimento, emissão, cobrança, devolução, importação e jobs.

**Como:** chave por operação e escopo; tabela/constraint; guardar resultado; retry retorna o resultado anterior sem repetir efeito.

**Aceite:** teste de duas requisições simultâneas produz um único efeito; chave reutilizada com payload diferente é rejeitada.

### ARC-004 — Locks e concorrência

**Fazer:** testar saldo, reserva, caixa, título, pedido e emissão em PostgreSQL real.

**Como:** `FOR UPDATE`, `SKIP LOCKED`, advisory lock ou versionamento conforme caso; transação curta; timeout observado.

**Aceite:** cenários de último saldo, recebimento duplicado e emissão simultânea passam; deadlock tem estratégia de retry limitada.

### ARC-005 — Reconciliação

**Fazer:** criar jobs/relatórios de divergência.

**Como:** regras: pedido sem movimento, movimento sem origem, reserva órfã, conta sem documento, documento sem pedido, webhook pendente, outbox morta e saldo inconsistente.

**Aceite:** divergência aparece com severidade, origem, data e ação; correção é comando auditado, não SQL manual.

### ARC-006 — Auditoria e observabilidade

**Fazer:** ampliar auditoria além de RBAC.

**Como:** evento de negócio com ator Bearer, ação, alvo, antes/depois mascarado, motivo, IP, correlation ID e timestamp. Logs estruturados sem segredo/PII desnecessária.

**Aceite:** gestor rastreia alteração de preço, estoque, alçada, fiscal e financeiro; suporte encontra uma requisição pelo correlation ID.

### ARC-007 — Testes

**Fazer:** criar matriz automatizada de testes backend/frontend/E2E.

**Como:** backend com PostgreSQL real; frontend Vitest; E2E para login/RBAC, pré-venda, desconto, cliente, venda, pagamento, compra, recebimento, inventário, devolução e fiscal; contrato OpenAPI.

**Aceite:** pipeline falha em regressão; migrations vazio→head e incremental→head passam; teste não usa produção nem segredo real.

## 15. Sprint 12 — integrações operacionais

**Prioridade:** P1/P2  
**Objetivo:** integrar os pontos que tornam a operação de loja prática.

### INT-001 — Bancos e conciliação

**Fazer:** importar OFX/CSV, sugerir matching e conciliar movimentos.

**Como:** normalizar data/valor/documento, matching por tolerância, aprovação, rejeição, duplicidade e auditoria.

**Aceite:** extrato não cria baixa automática sem regra; conciliação manual fica rastreável; saldo bancário bate com movimentos.

### INT-002 — Cobrança e adquirentes

**Fazer:** completar boleto/PIX, expiração, cancelamento, segunda via, taxas e liquidação.

**Como:** preservar adapters atuais, adicionar status canônico e reconciliação por webhook/consulta; outbox para externo.

**Aceite:** cada cobrança possui provider, ambiente, referência, status e idempotência; falha não perde título.

### INT-003 — Impressão e periféricos

**Fazer:** validar impressora térmica, etiquetas, leitor e balança.

**Como:** abstrair driver, fila de impressão, teste, reimpressão autorizada e fallback PDF. Balança deve ter unidade e origem.

**Aceite:** impressão falha sem perder venda; fila mostra pendência; reimpressão é auditada.

### INT-004 — E-commerce/marketplaces

**Fazer:** sincronizar catálogo, preço, estoque, pedido, cancelamento e devolução.

**Como:** adapters, mapeamento de produto, outbox, webhook, idempotência, limite e reconciliação periódica.

**Aceite:** estoque não fica negativo por corrida; pedido externo não duplica; erro aparece para operador.

### INT-005 — Transporte e entrega

**Fazer:** integrar cálculo, etiqueta, rastreio e comprovante.

**Como:** pedido de expedição com transportadora, eventos e SLA; não misturar status logístico com fiscal/financeiro.

**Aceite:** operador identifica o que separar, entregar e rastrear; entrega parcial é possível.

### INT-006 — Fornecedor e comunicação

**Fazer:** e-mail/WhatsApp de cotação/pedido, confirmação e histórico.

**Como:** templates versionados, opt-in quando necessário, outbox, retry, dead-letter e visualização do último envio.

**Aceite:** envio externo não bloqueia compra; retry não manda duplicado indevido; falha possui ação.

## 16. Sprint 13 — administração, LGPD e migração de dados

**Prioridade:** P1/P2  
**Objetivo:** preparar implantação e governança do dado.

### ADM-001 — Carga inicial

**Fazer:** importar produtos, clientes, fornecedores, preços, saldos e plano de contas.

**Como:** ferramenta de staging, validação, mapeamento, prévia, backup, lote, relatório e rollback lógico. Nunca importar diretamente em produção sem aprovação.

**Aceite:** contagem origem/destino bate; rejeições são listadas; importação repetida é idempotente.

### ADM-002 — Deduplicação

**Fazer:** identificar duplicidade de SKU/EAN/CPF/CNPJ/fornecedor/cliente.

**Como:** relatório de candidatos, merge assistido, preservação de histórico e redirecionamento de referências.

**Aceite:** nenhum merge destrói documento; usuário confirma conflitos; operação gera auditoria.

### ADM-003 — LGPD e dados sensíveis

**Fazer:** limitar coleta, exposição, exportação e retenção de PII/financeiro.

**Como:** classificação de campos, mascaramento, logs mínimos, consentimento de comunicação, exportação controlada e anonimização quando juridicamente possível.

**Aceite:** relatório/exportação respeita permissão; logs não expõem documento completo/segredo sem necessidade.

### ADM-004 — Backup, restauração e continuidade

**Fazer:** automatizar backup PostgreSQL, imagens, configurações e outbox.

**Como:** retenção, criptografia, teste de restauração, RPO/RTO, procedimento e evidência; banco e arquivos devem ser consistentes.

**Aceite:** restauração em ambiente isolado funciona; tempo medido; não depende de acesso manual a produção.

### ADM-005 — Monitoramento operacional

**Fazer:** painel/alertas de API, banco, Redis, RQ, outbox, webhook, fiscal, disco, certificado e jobs.

**Como:** métricas, logs, health/readiness, dead-letter, alarmes e runbook.

**Aceite:** falha crítica gera alerta; operador identifica impacto, causa provável e procedimento.

## 17. Sprint 14 — piloto e certificação interna

**Prioridade:** P0/P1  
**Objetivo:** provar que o ERP suporta um dia real de operação antes da escala.

### PIL-001 — Massa de teste realista

**Fazer:** criar base anonimizada representativa: cabos, tubos, conexões, ferragens, ferramentas, químicos, kits, unidades e lotes.

**Como:** copiar estrutura sem PII/segredos; incluir preços, custos, fornecedores, saldos, pedidos e históricos variados.

**Aceite:** dados cobrem ruptura, excesso, fracionamento, lote, devolução, atraso e venda a prazo.

### PIL-002 — Roteiro de dia de loja

**Fazer:** executar abertura, compra, recebimento, venda, desconto, pagamento, entrega, devolução, fechamento e relatórios.

**Como:** roteiro por papel: administrador, comprador, estoquista, vendedor, caixa e fiscal. Registrar tempo, erro e retrabalho.

**Aceite:** todos os papéis concluem tarefas; pendências são classificadas sem “contorno manual”.

### PIL-003 — Homologação fiscal/financeira

**Fazer:** validar com contador, provedor fiscal, banco e adquirente.

**Como:** anexar evidências de XML, protocolos, títulos, liquidação, eventos e relatórios.

**Aceite:** responsável externo aprova cenários; pendências fiscais/financeiras têm decisão registrada.

### PIL-004 — Gate de produção

**Fazer:** preparar release, manifesto, backup, migration job, smoke, rollback e janela.

**Como:** validar em staging primeiro; somente depois pedir confirmação explícita para produção.

**Aceite:** checklist P0 completo, sem falha aberta crítica, usuário autoriza publicação e evidências estão anexadas.

## 18. Backlog de relatórios por área

Este catálogo é obrigatório para a entrega da central de relatórios. Cada relatório deve reutilizar a camada analítica e declarar filtros, origem, fórmula, permissão, exportação e drill-down.

### Administrativo

- ADM-R01 Receita líquida, CMV, margem bruta, lucro e ticket médio.
- ADM-R02 DRE por competência e caixa.
- ADM-R03 Fluxo de caixa realizado e projetado.
- ADM-R04 Contas a pagar/receber, aging e inadimplência.
- ADM-R05 Resultado por filial, depósito, grupo, canal e vendedor.
- ADM-R06 Orçado versus realizado por centro de custo.
- ADM-R07 Auditoria de alterações críticas.

### Compras

- COM-R01 Necessidades de compra priorizadas.
- COM-R02 Ruptura prevista e cobertura.
- COM-R03 Pedidos abertos, atrasados, parciais e cancelados.
- COM-R04 Preço histórico e variação por fornecedor.
- COM-R05 Comparação de cotações e economia.
- COM-R06 Lead time, fill rate e qualidade do fornecedor.
- COM-R07 Compras por grupo, marca, depósito e comprador.
- COM-R08 Dependência/concentração de fornecedores.

### Estoque

- EST-R01 Saldos físico, reservado, disponível, bloqueado e trânsito.
- EST-R02 Kardex e cadeia de estorno.
- EST-R03 Valorização por data de corte.
- EST-R04 ABC por valor, receita, margem, quantidade e frequência.
- EST-R05 XYZ e matriz ABC×XYZ.
- EST-R06 Giro, cobertura e estoque médio.
- EST-R07 Ruptura, excesso, parado e obsolescência.
- EST-R08 Validade, lotes e séries.
- EST-R09 Acuracidade de inventário e perdas.
- EST-R10 Produtos sem custo, preço, fornecedor, EAN ou fiscal.

### Vendas e pós-venda

- VEN-R01 Vendas por período, produto, grupo, marca, cliente e vendedor.
- VEN-R02 Orçamentos abertos, ganhos, perdidos e conversão.
- VEN-R03 Desconto médio e vendas abaixo da margem.
- VEN-R04 Comissão apurada, paga e estornada.
- VEN-R05 Cancelamentos, devoluções, trocas e motivos.
- VEN-R06 Garantias, SLA e defeitos por fornecedor.
- VEN-R07 Clientes ativos, inativos, recorrência e concentração.

### Fiscal e financeiro

- FIS-R01 Documentos por status fiscal.
- FIS-R02 Rejeições, reprocessamentos e contingência.
- FIS-R03 Compras sem XML/entrada confirmada.
- FIN-R01 Caixa por operador/terminal e diferenças.
- FIN-R02 Conciliação bancária.
- FIN-R03 Taxas e liquidações de adquirentes.
- FIN-R04 Renegociações, juros, descontos e acordos.

## 19. Checklist de implementação por agente

Antes de começar:

- [ ] identificar o ID da tarefa e sprint;
- [ ] ler documentos de domínio aplicáveis;
- [ ] localizar tabelas, rotas, services, telas, jobs e testes existentes;
- [ ] definir se é nova funcionalidade, correção ou migração;
- [ ] registrar decisão de negócio ausente como bloqueio, sem inventar.

Durante:

- [ ] implementar banco com Expand/Migrate/Contract;
- [ ] implementar service transacional;
- [ ] implementar repository sem N+1 e com filtros seguros;
- [ ] atualizar API/OpenAPI/erro/tipos;
- [ ] implementar UI com RBAC, estados e teclado;
- [ ] adicionar auditoria, idempotência e métricas;
- [ ] cobrir concorrência, retry, duplicidade e rollback.

Antes de concluir:

- [ ] `python -m py_compile` nos arquivos Python alterados;
- [ ] `uv run pytest -q` com `TEST_PG_URL` correto;
- [ ] `npm test -- --run`, `npm run typecheck` e `npm run build`;
- [ ] teste de migração vazio→head e incremental;
- [ ] `git diff --check`;
- [ ] revisão de segurança, RBAC, segredos, PII e SQL;
- [ ] validação visual desktop/tablet/mobile;
- [ ] atualização de OpenAPI e documentação;
- [ ] atualização de `CONTEXTO_SESSAO.md`;
- [ ] commit/push;
- [ ] nenhum deploy sem autorização explícita.

## 20. Decisões que exigem usuário ou responsável externo

Estas decisões não podem ser inventadas pelo agente:

- regime tributário, matriz fiscal e cenários de ICMS/ST/PIS/COFINS;
- método contábil de estoque e composição do custo;
- uso monoempresa ou multiempresa/multifilial;
- adquirente/TEF, bancos e regras de conciliação;
- política de troca, devolução, garantia e crédito;
- níveis de serviço, estoque de segurança e política de compra;
- regras de comissão, margem mínima e aprovação;
- integração com marketplaces, transportadoras e contabilidade;
- prazos legais de contingência/cancelamento/eventos fiscais;
- dados reais, certificados, tokens e janela de publicação.

Quando uma dessas decisões estiver ausente, criar uma tarefa `DECISAO-*`, documentar opções e bloquear somente a parte dependente. Não criar um default silencioso que possa produzir dado fiscal, financeiro ou de estoque incorreto.

## 21. Ordem final recomendada

1. GOV-001 a GOV-004.
2. MDM-001 a MDM-007.
3. EST-001 a EST-008.
4. COM-001 a COM-006.
5. COM-007 a COM-012.
6. REC-001 a REC-006.
7. VEN-001 a VEN-007.
8. FIS-001 a FIS-006, em paralelo somente com as tarefas não dependentes de autorização fiscal.
9. BI-001 a BI-007.
10. POS-001 a POS-005.
11. UX-001 a UX-007 e ARC-001 a ARC-007.
12. INT-001 a INT-006 e ADM-001 a ADM-005.
13. PIL-001 a PIL-004.

O ERP só deve ser classificado como pronto para uso real depois que os gates P0 forem aceitos e os P1 correspondentes aos fluxos utilizados pela loja tiverem evidência operacional. A publicação continua sendo uma decisão separada e exige confirmação explícita do usuário.
