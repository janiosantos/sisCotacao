# Auditoria do Plano Mestre de Implementacao ERP

Data: 2026-09-01
Escopo: revisao estatica dos commits ate `5cfc970`, execucao dos testes frontend e leitura dos fluxos backend recentes.

## Conclusao executiva

O trabalho implementou grande parte do esqueleto funcional das ondas 0 a 14, com migracoes ate a 0142, services, blueprints, telas e testes de caminho feliz. Entretanto, o estado documentado como concluido nao atende integralmente os criterios de aceite do `PLANO_MESTRE_IMPLEMENTACAO_ERP.md`.

Os maiores riscos para uma loja em operacao sao:

1. Curva ABC historica incorreta no criterio padrao e sem isolamento por deposito.
2. Recebimento de compras com conta a pagar simplificada, sem respeitar condicao de pagamento e com possibilidade de duplicidade financeira em recebimentos parciais.
3. Conciliacao bancaria que sempre atualiza `contas_receber`, inclusive quando o matching e uma conta a pagar.
4. APIs de compras/recebimento aceitando o ator pelo JSON, permitindo falsificar autoria e quebrando segregacao/auditoria.
5. Motor de reposicao usando transito, demanda e vendas globais para cada deposito.
6. Contrato OpenAPI e validacao de payload incompletos, apesar do plano exigir ambos para endpoints criticos.

Sem corrigir os itens P0, o ERP nao deve ser usado para fechamento financeiro, reposicao automatica ou recebimento fiscal em producao.

## Status por epico

| Epico | Estado | Evidencia da auditoria |
|---|---|---|
| GOV-001..004 | Parcial | Existem processos, dicionario, maquinas e flags, mas nao ha prova de cobertura de todos os estados, eventos, rollback e contratos de cada rota nova. |
| MDM-001 | Nao atendido | Nao existe contexto autenticado de empresa/filial nem isolamento por escopo; o modelo documentado em `docs/erp/database` nao esta aplicado ao schema operacional. |
| MDM-002..005 | Parcial | Conversoes, identificadores, atributos e relacoes existem, mas recebimento, venda, fiscal e compras ainda nao usam a mesma unidade base de forma uniforme. |
| MDM-006 | Parcial | Importacao de produto possui pre-validacao, mas carga administrativa so cobre clientes/fornecedores e nao entrega staging/rollback para todos os dados do plano. |
| MDM-007 | Parcial | Regras de preco existem, mas a auditoria e o bloqueio de margem minima precisam ser comprovados em todos os canais. |
| EST-001..008 | Parcial | Saldo, fatos, custo, parametros, inventario, enderecos e lotes existem; faltam enforcement uniforme de deposito/endereco/lote e testes de concorrencia por fluxo. |
| COM-001..012 | Parcial com bloqueios | ABC, XYZ, demanda, reposicao, fornecedor e ciclo de compras existem, mas ha bugs de escopo, unidade, aprovacao, idempotencia e convite. |
| REC-001..006 | Parcial com bloqueios | XML, tres vias, conferencia, postagem e devolucao existem; a integracao XML -> recebimento -> financeiro/fiscal ainda nao e um pipeline completo. |
| VEN-001..006 | Parcial | Unidade, pagamentos, caixa, entrega, credito e cobranca existem; ha falhas de troco/idempotencia e faltam fechamento operacional completo e regras contabeis. |
| VEN-007 | Externo/manual | TEF/adquirencia permanece explicitamente manual no piloto. |
| POS-001..005 | Parcial | RMA, troca, garantia, CRM e comissao possuem services basicos, mas efeitos financeiros/fiscais, autorizacao e UI ainda nao fecham o processo de mercado. |
| FIS-001..006 | Nao liberado | Homologacao real, certificado, matriz aprovada, eventos fiscais e obrigacoes dependem de contador/provedor e ainda nao possuem evidencias. |
| BI-001..007 | Parcial com bugs | Relatorios basicos existem, porem sem filtros combinaveis, exportacao, drill-down, snapshots/materialized views, labels confiaveis e DRE completa. |
| UX-001..007 | Parcial | Shell, tabela, modal e paginacao evoluiram; faltam estados de erro, filtros globais, virtualizacao, telas recentes e E2E dos fluxos criticos. |
| ARC-001..007 | Parcial | Services e locks pontuais existem; schemas, contrato OpenAPI, idempotencia transversal e matriz E2E ainda nao atendem ao aceite. |
| INT-001..006 | Parcial | Banco, cobranca, impressao, comunicacao, transporte e outbox existem; marketplace/e-commerce nao foi implementado. |
| ADM-001..005 | Parcial | Backup, LGPD, carga, deduplicacao, readiness e auditoria existem, mas carga completa, restore automatizado, alertas e merge seguro precisam de endurecimento. |
| PIL-001..004 | Documento apenas | Ha checklist, mas nao ha evidencia de execucao do dia de loja, aprovacao fiscal/financeira ou gate de producao. |

## Achados criticos

### P0-01 - ABC padrao calcula consumo como zero e aplica globalmente

Em `backend/catalog_server/services/abc_historica.py`, `CRITERIOS` inclui `consumo`, mas a consulta de `_metricas()` nao retorna a coluna `consumo`. `_valor()` devolve zero para todos os itens quando a tela usa o criterio padrao `consumo`. O resultado classifica tudo como C e total zero.

O argumento `deposito_id` tambem nao chega a `_metricas()`. O calculo e global, embora a API aceite deposito. `aplicar()` grava a classe em `produtos_cadastro`, portanto aplicar uma versao de um deposito sobrescreve a classe global de outro deposito.

A mesma rotina considera somente vendas `finalizado`, exclui `recebido`, nao inclui itens sem qualquer venda e calcula `sem_venda` apenas dentro do conjunto ja retornado pela consulta.

Referencia: `backend/catalog_server/services/abc_historica.py:16-168`.

Correcao: definir explicitamente consumo (quantidade x custo historico ou regra aprovada), filtrar movimentos/vendas por deposito, incluir universo de produtos sem venda e persistir resultado por produto/depósito ou manter classe global somente quando o calculo for global.

### P0-02 - Recebimento gera financeiro incorreto

`finalizar()` cria sempre uma conta a pagar unica para 30 dias e ignora `condicao_pagamento_id`. Em recebimentos parciais, cada postagem cria outro titulo para o valor parcial sem chave de origem/parcelamento que garanta a conciliacao com a obrigacao original.

O erro contabil e capturado por `except Exception` e a entrada de estoque/conta continua, deixando uma postagem parcialmente contabilizada e apenas `contabil_ok=False`.

Referencia: `backend/catalog_server/services/recebimento.py:107-216`.

Correcao: criar parcelas a partir da condicao real, usar origem/idempotencia por recebimento e parcela, controlar saldo restante do pedido, e abortar a transacao quando a contabilizacao obrigatoria falhar ou criar estado explicito de pendencia com fila auditada.

### P0-03 - Conciliacao bancaria baixa a tabela errada

`conciliacao.sugerir_matching()` junta contas a receber e a pagar sem transportar o tipo da conta. `aprovar()` localiza a conta em qualquer tabela, mas executa sempre `UPDATE contas_receber`. Um matching de conta a pagar nao e baixado corretamente; se os IDs coincidirem, pode baixar o titulo errado.

Referencia: `backend/catalog_server/services/conciliacao.py:50-107`.

Correcao: persistir `matching_tipo`/origem, filtrar por direcao bancaria, valor, documento e vencimento, bloquear movimento e titulo com `FOR UPDATE`, e atualizar a tabela correta em uma transacao idempotente. Adicionar teste para receber e pagar com o mesmo ID numerico.

### P0-04 - Ator de compras e recebimento pode ser falsificado

Em varios endpoints o backend usa IDs recebidos no corpo em vez do usuario do Bearer: solicitante, transicoes, cotacao, vencedor, aprovador, operador, usuario da postagem, scanner, aprovacao de tres vias e devolucao.

Referencias principais: `backend/catalog_server/blueprints/api_compras_avancado.py:53-209` e `:252-472`.

Impacto: autoria, segregacao de funcoes e auditoria podem ser falsificadas; o cliente pode se apresentar como outro aprovador. O gate RBAC nao corrige esse problema porque a permissao e checada para o token, mas o efeito grava outro ator.

Correcao: remover IDs de ator do contrato de escrita ou ignorar o valor recebido; usar `usuario_id_requisicao()` em todos os comandos e aceitar um ator diferente somente em fluxo administrativo explicitamente autorizado, com motivo e regra de segregacao.

## Achados altos e medios

### P1-01 - Motor de reposicao mistura depositos e recebimentos parciais

`_transito()` e `_demanda_aberta()` recebem apenas produto, portanto o mesmo transito/demanda e aplicado a cada deposito. O transito soma a quantidade total do pedido, sem descontar o que ja foi recebido. A lista de candidatos atribui toda a venda recente ao primeiro deposito existente.

Referencia: `backend/catalog_server/services/motor_reposicao.py:32-80` e `:101-225`.

Efeito: sugestao de compra menor ou maior que a necessidade real, especialmente em multi-deposito e recebimento parcial.

### P1-02 - Media de demanda superestima produtos com meses sem venda

`_demanda_mensal()` faz `AVG` apenas dos meses que possuem venda, em vez de gerar os seis meses do periodo e preencher ausencias com zero. Tambem considera apenas `finalizado`.

Referencia: `backend/catalog_server/services/motor_reposicao.py:65-80`.

### P1-03 - Idempotencia central nao respeita escopo no banco

A tabela `idempotencia` declara `chave` como chave primaria, mas o servico consulta por `(chave, escopo)` e insere com `ON CONFLICT (chave)`. A mesma chave usada em escopos diferentes colide e a segunda operacao pode retornar como nova sem persistir seu resultado. Alem disso, `executar()` chama `ctx.__exit__(None, None, None)` sempre, inclusive quando ocorre excecao, impedindo o contexto de receber a informacao correta do erro.

Referencias: `backend/catalog_server/services/infra.py:12-49` e `backend/migrations/versions/0141_infra_idempotencia_auditoria_conciliacao.py:31-40`.

### P1-04 - Relatorio de vendas possui agrupamentos quebrados ou semanticamente errados

`_AGRUPAMENTOS` usa `p.categoria_id` sem juntar `produtos_cadastro p`, usa `oi.marca` sem verificar snapshot em todos os registros, usa UF como deposito e modelo de documento como canal. Os agrupamentos `grupo`, e potencialmente `marca`, podem falhar em runtime ou mostrar dados incorretos.

Referencia: `backend/catalog_server/services/relatorios.py:88-123`.

### P1-05 - XML de entrada nao fecha o pipeline de recebimento

`nfe_entrada.confirmar()` apenas muda o status e devolve linhas para o chamador. Nao existe vinculo persistido com `recebimento`, pedido, conta a pagar ou snapshot fiscal. O item pode ser confirmado fiscalmente sem ser postado ou comparado a um recebimento concreto.

Referencia: `backend/catalog_server/services/nfe_entrada.py:165-182`.

### P1-06 - Linhas repetidas do mesmo produto sao colapsadas

`tres_vias.conferir()` cria dicionario por `produto_id`, e `_pedido_linhas()` tambem e convertido para dicionario. Se um pedido tiver duas linhas do mesmo produto com preco, unidade ou fornecedor diferentes, uma linha sobrescreve a outra. `recebimento.conferir_item()` soma recebimentos globais por produto, nao por `pedido_item_id`.

Referencias: `backend/catalog_server/services/tres_vias.py:16-25` e `:31-90`; `backend/catalog_server/services/recebimento.py:59-105`.

### P1-07 - Idempotencia e concorrencia do pedido/cotacao nao estao fechadas

`gerar_pedido()` nao recebe chave idempotente nem bloqueia cotacao; chamadas concorrentes podem criar pedidos duplicados. `gerar_cotacao()` faz consulta e insercao separadas sem lock/constraint unica. Alem disso, a funcao informa fornecedores preferenciais, mas nao cria convites/propostas; o convite real ainda depende de outra etapa.

Referencias: `backend/catalog_server/services/pedido_compra.py:23-72` e `backend/catalog_server/services/cotacao_necessidade.py:8-66`.

### P1-08 - Pagamento tem bug de retry e troco

Em `registrar()`, quando uma linha idempotente ja existe, ela ainda entra na soma, mas nao incrementa corretamente os pendentes. Um retry de pagamento PIX/cartao pode fazer a venda parecer paga enquanto o registro continua pendente. Para dinheiro, o caminho confirmado pode marcar a venda como recebida sem lancar o troco; o troco so e tratado em `confirmar()`.

Referencia: `backend/catalog_server/services/pagamento_venda.py:14-83`.

### P1-09 - Merge de duplicados nao cobre referencias e pode quebrar unicidade

`operacao.merge()` atualiza uma lista fixa de tabelas, nao valida que os IDs sao entidades distintas, nao cria marcador de entidade mesclada e nao cobre todas as referencias adicionadas pelas migracoes recentes (pedidos, recebimentos, RMA, comissoes, fiscal e outros). Nao ha lock do primario/duplicado nem plano para conflitos de SKU/EAN.

Referencia: `backend/catalog_server/services/operacao.py:95-147`.

### P1-10 - Relatorios nao atingem o aceite de decisao

Estoque limita a 500 linhas, mas nao retorna pagina/has_more; ruptura exclui saldos zero; vendas nao tem filtros combinaveis, labels ou drill-down; financeiro mistura fluxo de caixa com DRE por competencia, usa aging sempre na data atual e nao possui despesas, impostos, centros e contas; dashboard usa o ultimo saldo de caixa global sem contexto.

Referencias: `backend/catalog_server/services/relatorios.py:27-83`, `:93-185` e `:193-218`.

### P1-11 - OpenAPI nao acompanha os endpoints implementados

O arquivo `backend/openapi.json` documenta apenas uma pequena parte das rotas recentes. Nao ha contrato completo de compras avancadas, recebimento, ABC/XYZ, reposicao, POS, infraestrutura e relatorios novos. Isso viola GOV-002/ARC-002 e deixa frontend e integracoes sem contrato versionado.

### P1-12 - Validacao de payload nao foi aplicada aos comandos criticos

Os blueprints de compras, recebimento, POS e infraestrutura fazem `float()`/`int()` direto e aceitam dicionarios livres. A camada `validacao.py` foi aplicada em poucos pontos, nao existe schema de entrada/saida uniforme e erros de tipo podem virar 500.

## Frontend e UX

1. `frontend/src/pages/relatorios.tsx` trata erro como loading infinito em Compras, Estoque e Financeiro; em Vendas converte erro em lista vazia. Nao existem filtros de periodo, paginacao, exportacao, drill-down ou aviso de dados parciais.
2. `frontend/src/pages/estoque/abc.tsx` nao permite selecionar deposito, mostra somente 50 itens, nao confirma a aplicacao global e nao exibe claramente se a versao esta aplicada ou e apenas simulacao.
3. `frontend/src/pages/compras/necessidades.tsx` cria solicitacao e depois insere itens um por um. Falha no item N deixa documento parcial, sem rollback; o codigo baseado em `Date.now()` pode colidir. O fragmento retornado no `map` nao possui `key`, gerando warning React.
4. A inicializacao de `dep` em Necessidades ocorre antes de depositos carregarem; se a lista chega assincronamente, o estado permanece vazio e o calculo pode rodar para todos os depositos.
5. A tabela padrao evoluiu com ordenacao e paginacao, mas o aceite Lightning/SLDS ainda nao esta comprovado para selecao, roving tabindex, colunas configuraveis, filtros por coluna, virtualizacao e acao em lote.
6. Nao existe E2E automatizado real para o roteiro completo de login/RBAC, pre-venda, desconto, pagamento, compra, recebimento, devolucao e fiscal; os scripts `e2e_*.mjs` nao substituem uma suite reprodutivel integrada ao pipeline.

## Itens externos ou ainda nao demonstrados

- Matriz fiscal assinada por contador e cenarios reais de NF-e/NFC-e.
- Certificado A1/A3, CSC, credenciais separadas e testes Focus/SEFAZ em homologacao.
- Contingencia NFC-e com fila, numeracao e transmissao posterior.
- Marketplace/e-commerce (INT-004) nao encontrado como fluxo implementado.
- TEF/adquirencia continua manual, conforme decisao do piloto.
- Restauracao de backup medida em ambiente isolado, alertas de monitoramento e RPO/RTO demonstrados.
- Massa anonimizada realista e execucao documentada do dia de loja.
- Deploy/staging: nenhum foi executado nesta auditoria, conforme regra do `AGENTS.md`.

## Verificacao executada

- Frontend: `npm run typecheck` passou.
- Frontend: `npm test -- --run` passou com 39 testes.
- Backend: a execucao direcionada contra PostgreSQL foi iniciada, mas interrompida por lentidao operacional antes do resultado final; portanto nao e correto declarar a suite backend verde nesta auditoria.
- Nenhuma migracao, restart, rebuild ou deploy em staging/producao foi executado.

## Ordem recomendada de correcao

1. Corrigir recebimento financeiro, conciliacao bancaria e identidade do ator; adicionar testes negativos e concorrentes.
2. Corrigir ABC, reposicao e escopo por deposito/unidade.
3. Fechar idempotencia central, pedido/cotacao/pagamento e pipeline XML -> recebimento.
4. Corrigir agrupamentos e contratos OpenAPI/validacao de todos os endpoints novos.
5. Implementar transacao bulk para necessidade -> solicitacao e estados de erro da UI.
6. Completar DRE/BI, filtros/paginacao/exportacao e E2E dos fluxos P0.
7. Somente depois executar homologacao fiscal/financeira, piloto e gate de publicacao.
