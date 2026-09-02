# Plano complementar: crédito, recebimento e auditoria do ERP Casa LM

**Versão:** 1.0  
**Data:** 2026-09-01  
**Base:** `PLANO_MESTRE_IMPLEMENTACAO_ERP.md`, `AGENTS.md`, `CONTEXTO_SESSAO.md`, `RELATORIO_AUDITORIA_PLANO_MESTRE_ERP.md`, código atual e requisitos operacionais informados pelo usuário.  
**Objetivo:** auditar integralmente o trabalho já desenvolvido, corrigir as falhas confirmadas e implementar um fluxo de crédito/crediário auditável, segregado por responsabilidade e seguro para operação de loja de material elétrico, hidráulico, ferragens e ferramentas. Multi-tenancy fica fora do escopo desta fase.

## 1. Regra de execução

Este documento é um contrato de desenvolvimento. Nenhum agente deve marcar uma tarefa como concluída porque a tela abriu ou o endpoint respondeu. A entrega somente é aceita quando regra de negócio, persistência, contrato API, frontend, RBAC, auditoria, testes e operação estiverem coerentes.

### 1.1 Regras obrigatórias

1. Ler `AGENTS.md`, `CONTEXTO_SESSAO.md`, este plano, `PLANO_MESTRE_IMPLEMENTACAO_ERP.md` e os documentos de domínio antes de editar.
2. Executar `git status --short` e identificar alterações de outros agentes. Nunca apagar, resetar ou sobrescrever trabalho não compreendido.
3. Auditar o código existente antes de refatorar. O padrão adotado pelo OpenClaude não é presumido correto.
4. Regra de negócio deve existir no backend/service e ser testada por API. O frontend apenas orienta, filtra e fornece feedback.
5. Toda mudança de banco exige migração versionada com `VERSION`, `RISCO`, `NAME`, `MUDANCA`, `guard`, `forward` e `backward`.
6. Alterações incompatíveis devem seguir Expand -> Backfill -> Dual Write -> Trocar leitura -> Frontend -> Contract.
7. Toda operação crítica deve ter transação única, lock adequado, chave de idempotência e estorno ou compensação definido.
8. Dados financeiros, crédito aprovado, permissões e movimentos de estoque devem ter trilha de auditoria imutável.
9. O frontend não acessa tabelas, SQL ou modelos internos; somente contratos de API versionados.
10. Toda lista deve ter paginação, filtros, limites, loading, erro, estado vazio, foco e navegação por teclado.
11. Tabelas e navegação seguem o padrão definido no `AGENTS.md`, alinhado a Salesforce Lightning Datatable e SLDS.
12. Toda tarefa termina com evidência de testes, documentação, atualização de `CONTEXTO_SESSAO.md`, commit e push.
13. Não executar deploy, rebuild/restart de staging/produção ou migração nesses ambientes sem confirmação explícita do usuário.

### 1.2 Critério de aceite global

Uma tarefa só pode ser `Concluída` quando:

- a regra estiver descrita em documentação e implementada no backend;
- o contrato OpenAPI e os tipos TypeScript estiverem atualizados;
- o fluxo normal, negativo, concorrente e repetido estiver testado;
- a autorização for validada no servidor e refletida na UI;
- o histórico permitir identificar quem, quando, de onde e por que alterou o dado;
- a migração funcionar em banco vazio e incremental, quando aplicável;
- a UI funcionar com mouse, teclado, mobile e leitor de tela nos pontos afetados;
- logs não expuserem senha, token, cartão ou dados desnecessários de pessoa;
- rollback comportamental e estrutural estiver documentado;
- nenhuma publicação tiver sido feita sem autorização.

## 2. Resultado de negócio esperado

### 2.1 Regras comerciais definitivas

| Situação | Vendedor | Financeiro | Caixa | Resultado permitido |
|---|---:|---:|---:|---|
| Cliente padrão `CONSUMIDOR` | Monta venda | Não participa | Recebe | Somente à vista |
| Cliente identificado sem crédito aprovado | Monta venda à vista | Pode analisar crédito | Recebe | À vista; venda a prazo bloqueada |
| Cliente identificado com crédito aprovado ativo | Monta pedido | Mantém política | Recebe parcelas pagas | A prazo/boleto dentro do limite disponível |
| Cliente com crédito vencido, bloqueado ou expirado | Pode consultar motivo | Regulariza ou reanalisa | Não libera exceção | A prazo bloqueado |
| Aprovação, alteração ou bloqueio de crédito | Solicita | Executa | Não executa | Somente responsável financeiro autorizado |
| Recebimento de dinheiro, PIX ou cartão | Não executa | Pode consultar | Executa baixa | Somente usuário com permissão de recebimento |
| Exceção acima do limite | Solicita | Responsável com alçada aprova | Não aprova | Evento auditado e temporário |

O fato de o cliente possuir cadastro, limite preenchido ou histórico de compras não é, isoladamente, prova de crediário aprovado. O sistema deve distinguir `limite_cadastrado`, `limite_aprovado`, `status_credito`, `validade` e `exposicao_atual`.

### 2.2 Estados do crédito

```text
nao_solicitado -> em_analise -> aprovado -> suspenso -> aprovado
                              -> reprovado
aprovado -> expirado -> em_analise
aprovado -> bloqueado -> em_analise
```

Transições proibidas:

- vendedor aprovando, alterando ou reativando crédito;
- operador de caixa aprovando crédito ou alterando limite;
- aprovação sem responsável, data, validade, limite e justificativa;
- alteração de crédito sem versão anterior preservada;
- reativação automática após pagamento sem política explícita do financeiro;
- venda a prazo para crédito expirado, suspenso, bloqueado ou inexistente.

### 2.3 Cálculo de exposição

```text
exposicao = contas_receber_abertas
          + parcelas_vencidas
          + pedidos_a_prazo_nao_cancelados
          + reservas_de_credito
          - creditos_ou_adiantamentos_compensaveis

disponivel = limite_aprovado - exposicao
```

O cálculo deve ser feito no backend, dentro de transação compatível com a finalização. A tela pode antecipar o aviso, mas nunca liberar a operação com base apenas no valor exibido no navegador.

## 3. Auditoria integral antes da implementação

### AUD-001 - Inventário técnico e histórico de alterações

**Fazer:** mapear tudo que foi implementado pelo OpenClaude e pelos demais agentes.

**Como:**

- listar commits, branches e arquivos alterados por módulo;
- separar código novo, extração verbatim, correção funcional e alteração de contrato;
- mapear cada endpoint para blueprint, service, repository, tabela, frontend e teste;
- identificar código duplicado, compatibilidade legada, flags sem consumidor e endpoints sem OpenAPI;
- comparar documentação com comportamento real, sem confiar no changelog;
- registrar evidência em tabela `achado`, `severidade`, `arquivo/linha`, `risco`, `correção` e `teste`.

**Aceite:** nenhum módulo, job, template, workflow, migração ou integração fica fora do inventário.

### AUD-002 - Auditoria de regras no backend

**Fazer:** detectar regras implementadas somente na UI ou espalhadas em handlers.

**Verificar obrigatoriamente:** cliente padrão, condição de pagamento, crédito, desconto, recebimento, caixa, estoque, compras, contas a receber, boleto, fiscal, impressão e portal do fornecedor.

**Anti-padrões a procurar:**

- `disabled` ou filtro React usado como controle de segurança;
- `if` comercial no componente sem validação equivalente no service;
- endpoint genérico com `PATCH` livre de status;
- `or 1`, conversão silenciosa ou valor padrão que muda significado de `false`/`0`;
- uso de `request.json` sem validação de tipo e faixa;
- leitura para decisão de crédito sem lock ou rechecagem transacional;
- chamada a repository que abre outra conexão no meio de uma transação;
- `UPDATE`/`DELETE` em ledger financeiro ou de estoque consolidado;
- `except Exception` escondendo falha de postagem;
- montagem de URL com `$host`, hostname sem porta ou base fixa inadequada;
- página Flask existente sem rota no nginx/Vite;
- identificador de variante, produto, item de compra e item de estoque misturados.

**Aceite:** cada regra possui uma única fonte de verdade, um contrato de erro e teste de API.

### AUD-003 - Auditoria de dados reais e reconciliação

**Fazer:** verificar inconsistências existentes antes de corrigir a apresentação.

**Como:** executar consultas somente leitura para:

- compras/cotações com número `0051`, pedidos gerados, recebimentos e movimentos;
- produto do item, unidade, fator de conversão, depósito e saldo materializado;
- soma do ledger contra `estoque_saldo`;
- contas geradas por vendas a prazo e origem do documento;
- condições de pagamento do consumidor padrão;
- clientes com limite preenchido sem aprovação identificável;
- perfis com permissões de caixa, financeiro e crédito;
- URLs geradas com e sem porta em requisição direta e atrás de proxy.

**Aceite:** relatório distingue defeito de dado, defeito de regra, defeito de consulta e defeito somente visual. Nenhuma correção de dado é feita automaticamente nesta tarefa sem autorização específica.

## 4. Arquitetura alvo

### 4.1 Monólito modular antes de microsserviços

Manter um monólito Flask modular até existir volume ou equipe que justifique distribuição. Os bounded contexts devem ser delimitados mesmo permanecendo no mesmo processo:

```text
Produto/Unidade -> Estoque/Kardex -> Compras/Recebimento
Cliente/Crédito -> Vendas/Pré-venda -> Caixa/Contas a receber
Fiscal -> Documentos fiscais
Contábil -> Livro razão e integrações
Infra -> autenticação, RBAC, auditoria, outbox e observabilidade
```

Fluxo de dependência:

```text
PostgreSQL -> Repository -> Service/Use Case -> Blueprint/Schema -> Frontend
```

Controllers não calculam crédito, estoque ou parcelas. Repositories não decidem permissão ou fluxo de negócio. Componentes React não aprovam, recebem ou validam crédito como autoridade.

### 4.2 Escopo atual: monoempresa e monobanco

Multi-tenancy, `tenant_id`, database-per-tenant, schema-per-tenant e Row Level Security ficam **fora do escopo** deste plano. Não criar isolamento parcial ou campos sem consumidores reais.

O sistema deve continuar tratando corretamente os limites já existentes do negócio:

- usuário autenticado, perfil RBAC e autoria da operação;
- empresa/emitente atual, quando aplicável ao fiscal;
- filial, depósito, caixa e terminal quando já existirem no modelo;
- `correlation_id`, IP e timestamp para auditoria e rastreabilidade;
- jobs/outbox vinculados à origem operacional correta.

Uma futura adoção de multi-tenancy deverá começar por ADR próprio e novo plano de migração, antes de qualquer `tenant_id` ou RLS.

## 5. Blueprint de dados do crédito

### CRD-001 - Estrutura de aprovação

**Fazer:** criar uma fonte de verdade específica para crediário, preservando `clientes.limite_credito` durante a transição.

**Estrutura alvo recomendada:**

`credito_cliente`:

- `id`, `cliente_id`, `status`;
- `limite_aprovado`, `prazo_maximo_dias`, `condicoes_permitidas`;
- `vigencia_inicio`, `vigencia_fim`, `aprovado_por`, `aprovado_em`;
- `bloqueado_por`, `bloqueado_em`, `motivo_bloqueio`, `versao`;
- `created_at`, `updated_at`, `created_by`, `updated_by`;
- unicidade por cliente e lock por cliente na decisão.

`credito_evento` append-only:

- `id`, `credito_id`, `tipo_evento`, `status_anterior`, `status_novo`;
- `limite_anterior`, `limite_novo`, `motivo`, `documentos_ref`, `snapshot_json`;
- `usuario_id`, `ip`, `correlation_id`, `criado_em`.

`credito_reserva`:

- origem do pedido, valor, status, expiração, criação e liberação idempotentes;
- usada para evitar que pedidos simultâneos consumam o mesmo limite.

**Como:** migração Expand; backfill inicial idempotente não deve aprovar automaticamente todos os limites antigos. Registros antigos devem entrar como `em_analise` ou `aprovado` somente se houver decisão do negócio documentada. Durante a coexistência, escrever o campo legado e a estrutura nova com marca de origem.

**Aceite:** limite antigo não é interpretado como aprovação sem regra de compatibilidade explícita; repetir backfill não duplica; dados anteriores continuam consultáveis.

### CRD-002 - Permissões e segregação

**Fazer:** separar permissões de `financeiro`, `credito` e `caixa`.

**Como:**

- criar recurso `credito` no catálogo RBAC;
- permitir `credito.visualizar` para consulta conforme a política;
- permitir `credito.solicitar` ou `credito.cadastrar` ao vendedor, sem aprovação;
- permitir `credito.aprovar`, `credito.editar`, `credito.bloquear` e `credito.configurar` somente ao perfil financeiro responsável;
- permitir `caixa.receber` somente ao operador/caixa autorizado;
- retirar qualquer permissão de aprovação de crédito do operador de caixa;
- proteger atribuição de permissões pela regra atual de superusuário e último administrador.

Se a enumeração atual de ações não suportar `solicitar`, `aprovar`, `bloquear` e `receber` sem ambiguidade, criar ações versionadas em migração, mantendo compatibilidade temporária com ações antigas e mapeamento explícito por endpoint.

**Aceite:** chamada direta por vendedor, operador e usuário sem perfil retorna 403 estável; usuário financeiro autorizado consegue executar somente suas ações; toda decisão gera auditoria RBAC e de domínio.

### CRD-003 - Serviço de decisão

**Fazer:** criar service puro, testável sem Flask, para responder `consultar_credito`, `validar_venda_a_prazo`, `aprovar`, `bloquear`, `suspender`, `revisar` e `reservar_limite`.

**Como:** o service recebe contexto de cliente, pedido, data, usuário e política. Retorna decisão estruturada:

```json
{
  "permitido": false,
  "code": "crediario_nao_aprovado",
  "status": "em_analise",
  "limite_aprovado": 0,
  "exposicao": 0,
  "disponivel": 0,
  "motivos": []
}
```

Não retornar somente booleano. A decisão precisa ser explicável e armazenar a versão da política utilizada.

**Aceite:** a mesma entrada produz a mesma decisão; o service não importa React/Flask; cenários de validade, atraso, exposição, reserva, concorrência e cliente padrão estão cobertos.

## 6. Backlog por sprint

### Sprint 0 - Auditoria, decisões e baseline

**Prioridade:** P0. **Dependências:** nenhuma.

#### GOV-CRD-001 - Matriz de papéis e processos

Documentar venda balcão, pedido de vendedor, análise de crédito, aprovação, boleto, recebimento no caixa, compra, recebimento de mercadoria, impressão, compartilhamento e reconciliação. Cada linha deve conter ator, documento, estado, efeitos, permissão, exceção, estorno e evidência.

**Entrega:** `docs/erp/processos-credito-recebimento.md` e matriz de responsabilidades.

#### GOV-CRD-002 - Auditoria de código e dados

Executar `AUD-001`, `AUD-002` e `AUD-003`; criar relatório de achados com severidade P0-P3 e ligação para teste/correção. Validar todos os commits do OpenClaude por diff e comportamento, não por descrição.

#### GOV-CRD-003 - ADR de escopo operacional

Registrar a decisão de manter a aplicação em escopo monoempresa/monobanco nesta fase, incluindo limites operacionais de filial, depósito, caixa, terminal e autoria. Multi-tenancy permanece fora deste plano e qualquer evolução futura exigirá ADR e plano próprios.

**Saída da sprint:** baseline de testes, inventário, decisões aprovadas e lista de bloqueios. Nenhuma alteração destrutiva.

### Sprint 1 - Contexto operacional, auditoria e contratos

**Prioridade:** P0. **Dependência:** Sprint 0.

#### OPS-001 - Contexto operacional da requisição

Implementar contexto validado no backend, propagado para services, repositories, outbox, jobs e logs. Não confiar em identificadores de empresa, filial, depósito ou usuário enviados pelo payload quando a informação puder ser derivada da sessão ou do servidor. Adicionar `correlation_id` e `user_id` aos logs estruturados.

#### OPS-002 - Integridade do escopo monoempresa

Verificar chaves únicas, índices, foreign keys, relatórios e rotinas de manutenção para filial, depósito, caixa, terminal e autoria quando esses conceitos existirem no modelo. Criar testes contra acesso fora do escopo operacional permitido.

#### AUD-004 - Auditoria genérica

Padronizar `created_by`, `updated_by`, IP, trace e escopo operacional nas tabelas operacionais prioritárias. Criar audit log imutável para crédito, permissões, preço, estoque, caixa, financeiro e documentos fiscais. Correções financeiras devem ser estorno/compensação, não edição do fato.

#### API-CRD-001 - Contratos e erros

Atualizar OpenAPI e tipos TS para decisões de crédito, recebimento e estoque. Padronizar erro `{error, code, details, correlation_id}` e não retornar stack trace.

### Sprint 2 - Crediário e aprovação financeira

**Prioridade:** P0. **Dependência:** Sprint 1.

#### CRD-004 - Migração Expand e compatibilidade

Criar `credito_cliente`, `credito_evento` e `credito_reserva` com guard, índices, foreign keys e auditoria. Backfill idempotente em lotes. Não remover `clientes.limite_credito` nesta sprint.

#### CRD-005 - APIs de solicitação e decisão

Implementar:

- `GET /api/clientes/{id}/credito`;
- `POST /api/clientes/{id}/credito/solicitar`;
- `POST /api/clientes/{id}/credito/aprovar`;
- `POST /api/clientes/{id}/credito/bloquear`;
- `POST /api/clientes/{id}/credito/suspender`;
- `GET /api/clientes/{id}/credito/historico`;
- `GET /api/credito/pendentes`.

Validar payload estrito, permissão, cliente ativo, limite positivo, validade, prazo e motivo. Aprovação usa `SELECT FOR UPDATE` no crédito e registra evento antes do commit.

#### CRD-006 - Cadastro de cliente

Vendedor pode cadastrar/editar dados comerciais permitidos, mas não criar ou alterar limite aprovado. O endpoint deve comparar valor anterior e novo; campo inalterado não deve bloquear edição comum. Somente financeiro autorizado altera crédito, inclusive reduzindo para zero, suspendendo ou reativando.

#### CRD-007 - Tela financeira de crédito

Criar fila com filtros por status, validade, limite, exposição e atraso; detalhe com documentos, histórico e decisão. Aprovar exige confirmação, motivo e foco acessível. Não exibir ação de aprovar para caixa.

### Sprint 3 - Pré-venda, orçamento e cadeia de recebimento

**Prioridade:** P0. **Dependência:** Sprint 2.

#### VEN-CRD-001 - Consumidor padrão somente à vista

No frontend, ao selecionar `CONSUMIDOR`:

- selecionar automaticamente condição à vista;
- remover/desabilitar condições a prazo;
- limpar condição inválida já carregada;
- exibir motivo operacional próximo ao campo.

No backend, ao criar, editar ou finalizar orçamento, rejeitar condição a prazo para cliente padrão com `code=cliente_padrao_somente_avista`. A validação não pode depender do nome digitado; usa o `cliente_id` canônico.

#### VEN-CRD-002 - Cliente sem crediário aprovado

Na finalização com condição a prazo, chamar o serviço de crédito dentro da transação. Rejeitar cliente sem aprovação ativa, aprovação expirada, bloqueada, suspensa, limite insuficiente ou exposição vencida conforme política. Usar códigos distintos: `crediario_nao_aprovado`, `credito_expirado`, `credito_bloqueado`, `sem_credito`, `cliente_atraso`.

#### VEN-CRD-003 - Vendedor não recebe pedido

Remover `Receber` da lista e do detalhe de Orçamentos. Orçamentos deve encaminhar o usuário ao Caixa ou às contas a receber conforme o documento. Manter o endpoint legado apenas para compatibilidade, mas exigir no backend `caixa.receber` e usuário diferente do vendedor do pedido, salvo exceção de superusuário auditada.

#### VEN-CRD-004 - Caixa somente recebe

No Caixa, permitir dinheiro, PIX, cartão e demais formas configuradas somente com permissão de recebimento e sessão de caixa válida. O endpoint de baixa não pode aprovar crédito, alterar limite, alterar condição do pedido ou modificar documento fiscal já consolidado.

#### VEN-CRD-005 - Transação de finalização

Finalização deve bloquear pedido, crédito e saldo necessários, validar tudo, gerar contas/reserva/movimentos e publicar outbox no mesmo commit. Retry por `Idempotency-Key` não pode duplicar conta, reserva, caixa, estoque ou boleto. Falha em qualquer etapa faz rollback completo.

#### VEN-CRD-006 - Boleto e contas a receber

Boleto só pode nascer de venda a prazo válida e cliente com crédito aprovado. À vista não gera boleto. Emissão, cancelamento, baixa por webhook e reabertura precisam preservar o histórico e usar estorno/compensação.

### Sprint 4 - Estoque, compras e produto

**Prioridade:** P0/P1. **Dependência:** Sprint 1; integração com Sprint 3.

#### EST-CRD-001 - Diagnóstico da compra 0051

Identificar se `0051` é cotação ou pedido, localizar pedido gerado, recebimento, produto, item, depósito e movimentos. Não corrigir manualmente antes de saber se o problema é fluxo incompleto, unidade/fator, produto divergente ou apenas tela errada.

#### EST-CRD-002 - Recebimento de compra transacional

Garantir cadeia `pedido -> recebimento -> item recebido -> movimento de entrada -> saldo -> contas a pagar`. Usar produto correto do item, unidade base, fator de conversão, custo e depósito. Lock no pedido e idempotência impedem recebimento duplo. Postagem parcial deve atualizar status corretamente.

#### EST-CRD-003 - Aba Estoque do produto

A aba `Estoque` do cadastro deve exibir saldo físico, reservado, disponível, bloqueado, em trânsito, custo médio, depósito e situação. Os parâmetros de estoque ficam em seção própria na mesma aba. Não depender de dados carregados somente na aba Dados/Variações.

#### EST-CRD-004 - Reconciliador

Adicionar ação administrativa para comparar ledger, saldo materializado e saldo derivado por produto/depósito. Divergência gera relatório e evento, nunca correção silenciosa. Produto da compra 0051 deve ser localizável por nome, SKU, EAN e ID.

### Sprint 5 - Etiquetas, impressão e URLs

**Prioridade:** P0/P1. **Dependência:** Sprint 1.

#### UX-CRD-001 - Impressão de etiquetas

Validar o fluxo completo: botão -> URL -> proxy -> Flask -> consulta dos produtos -> template -> `window.print`. A rota `/etiquetas/` precisa estar explicitamente no nginx compartilhado entre dev/staging/prod e no proxy do Vite quando aplicável.

Requisitos:

- IDs validados no backend, sem `IN ()` para lista vazia;
- produto inexistente retorna aviso explícito, não folha vazia silenciosa;
- etiquetas exibem nome, SKU/EAN, preço, unidade e localização;
- botão de imprimir tem permissão e foco;
- teste HTTP autenticado e teste de renderização do template.

#### UX-CRD-002 - URL com porta

Padronizar construtor de URL usando `PUBLIC_BASE_URL` quando configurado; caso contrário, host/proto externo confiável incluindo porta. Nginx deve preservar `$http_host`/porta ao encaminhar e configurar `X-Forwarded-Host`, `X-Forwarded-Proto` e, se necessário, `X-Forwarded-Port`.

Testar:

- `http://localhost:8000/fornecedor/token`;
- `http://localhost:8080/fornecedor/token` atrás do nginx;
- domínio HTTPS com porta não padrão;
- proxy sem porta padrão;
- cabeçalho malicioso não confiável fora da lista de proxies.

Não aceitar host arbitrário para gerar link público sem política de proxy confiável.

#### UX-CRD-003 - Impressão de pedido e cupom

Separar impressão PDF/browser de impressão térmica. Cada uma deve ter rota, permissão, timeout, erro e evidência próprios. Falha de impressão não pode desfazer venda já confirmada; deve registrar pendência para reimpressão.

### Sprint 6 - Auditoria de todos os módulos e refatoração

**Prioridade:** P1. **Dependências:** Sprints 2 a 5.

Revisar, pelo mesmo checklist, `produtos`, `estoque`, `compras`, `recebimento`, `orçamentos`, `pré-venda`, `caixa`, `financeiro`, `fiscal`, `clientes`, `fornecedores`, `RBAC`, `webhooks`, `outbox`, jobs e relatórios.

Para cada achado, decidir uma destas ações: corrigir agora, criar dívida documentada, bloquear publicação ou aceitar formalmente o risco. Refatorar extrações verbatim que mantiveram acoplamento, duplicação ou regra errada. Não fazer refatoração cosmética junto com mudança de regra crítica sem teste independente.

### Sprint 7 - UX, teclado, observabilidade e E2E

**Prioridade:** P1. **Dependências:** Sprints 3 a 5.

#### UX-CRD-004 - Pré-venda

Manter o fluxo sem mouse: descrição -> produto -> quantidade -> desconto -> condição -> observação -> finalizar. Enter com descrição vazia segue o fluxo definido. Consumidor padrão deve anunciar que somente à vista está disponível. Foco nunca pode sair de login, desconto, crédito ou condição por re-render.

#### UX-CRD-005 - Orçamentos e Caixa

Orçamentos exibe próxima ação, nunca oferece receber ao vendedor. Caixa exibe somente ações de recebimento autorizadas. Ações críticas ficam em coluna/rodapé previsível, com `aria-label`, `aria-disabled`, atalhos documentados e confirmação contextual.

#### OBS-CRD-001 - Métricas de negócio

Medir bloqueios por crédito, aprovações, exceções, recebimentos, falhas de impressão, URLs geradas, divergências de estoque, deadlocks, retries e outbox morto. Logs estruturados devem conter escopo operacional quando aplicável, usuário, trace, módulo, duração e código de resultado, sem PII desnecessária.

#### E2E-CRD-001 - Fluxos críticos

Criar E2E com Postgres real para:

- consumidor padrão tentando condição a prazo;
- cliente sem crédito tentando boleto;
- cliente aprovado comprando dentro e fora do limite;
- vendedor tentando receber;
- caixa recebendo dinheiro/PIX/cartão;
- financeiro aprovando e bloqueando crédito;
- recebimento da compra e saldo do produto;
- impressão de etiquetas e URL com porta;
- retry concorrente de finalização, recebimento e webhook.

### Sprint 8 - Contract, piloto e publicação autorizada

**Prioridade:** P0/P1. **Dependências:** todas as anteriores.

Somente após evidência de uso real:

- trocar leituras legadas para `credito_cliente`;
- confirmar que frontend, relatórios, jobs e integrações não usam `clientes.limite_credito` como aprovação;
- remover compatibilidade apenas em release separada;
- criar manifesto com schema, backend, frontend, imagens, API, flags e rollback;
- validar banco vazio -> head e incremental -> head;
- backup antes de migration relevante;
- publicar staging somente com autorização explícita;
- executar smoke/E2E e observar métricas;
- produção somente após aceite operacional e fiscal/financeiro.

## 7. Matriz de testes obrigatória

### 7.1 Crédito e segregação

| Caso | Esperado |
|---|---|
| Consumidor + condição a prazo na API | 403 `cliente_padrao_somente_avista` |
| Consumidor + condição a prazo no frontend | Opção indisponível e foco preservado |
| Cliente identificado sem aprovação | 403 `crediario_nao_aprovado` |
| Crédito expirado/bloqueado | 403 com código específico |
| Crédito aprovado dentro do limite | Finaliza e gera contas a receber |
| Crédito aprovado acima do limite | 403 `sem_credito` |
| Vendedor aprova crédito | 403 e nenhum evento de aprovação |
| Operador altera limite | 403 e nenhum dado alterado |
| Financeiro aprova | 200, versão/histórico/auditoria gravados |
| Vendedor recebe pedido | 403, sem caixa, sem baixa, sem status recebido |
| Caixa recebe pedido | baixa idempotente e status correto |

### 7.2 Estoque e compras

| Caso | Esperado |
|---|---|
| Compra recebida uma vez | uma entrada, saldo e custo corretos |
| Mesmo recebimento repetido | resultado idempotente, sem segunda entrada |
| Recebimento parcial | saldo/status parcial coerentes |
| Item de produto divergente | rejeição antes do commit |
| Compra 0051 | cadeia identificada e saldo exibido na aba Estoque |
| Ledger divergente do materializado | alerta/reconciliação, sem correção silenciosa |

### 7.3 Impressão e URL

| Caso | Esperado |
|---|---|
| Etiquetas por ID válido | HTML renderizado com etiquetas |
| ID inexistente | erro orientativo ou resultado explicitamente vazio |
| Lista vazia/malformada | 400 estável, sem SQL inválido |
| `localhost:8000` | link preserva `:8000` |
| nginx com porta pública | link preserva porta externa |
| Host não confiável | não gera link arbitrário |
| impressão falha após venda | venda permanece; reimpressão possível |

## 8. Definition of Done por commit

Cada commit deve ser pequeno e ter uma finalidade:

1. `audit(...)`: apenas inventário/achados/testes de caracterização.
2. `migration(...)`: apenas schema e testes da migração.
3. `feat(...)`: service/API e contrato.
4. `fix(...)`: correção funcional com regressão reproduzida.
5. `ux(...)`: UI, foco, teclado e estados, sem mover regra para o frontend.
6. `test(...)`: cobertura complementar.
7. `docs(...)`: contexto, OpenAPI, manifesto e operação.

Antes de cada commit:

- `python -m py_compile` nos Python alterados;
- `npm run typecheck` em `frontend/`;
- testes backend focados e integração com PostgreSQL;
- `npm test -- --run` e `npm run build` quando frontend afetado;
- `git diff --check`;
- evidência do comando e resultado no contexto.

## 9. Rollback e riscos

### 9.1 Rollback comportamental

Flags podem desligar a nova decisão de crédito, UI nova, construtor de URL ou tela de estoque, mas não desfazem migração nem reabrem permissão de forma insegura. O fallback deve continuar negando crédito sem aprovação e recebimento sem permissão.

### 9.2 Rollback estrutural

- expand: manter novas tabelas sem impacto;
- dual write: parar escrita nova somente com monitor de divergência;
- troca de leitura: voltar à leitura legada mantendo o contrato API;
- contract: remover legado somente em release posterior e após busca em código, jobs, relatórios e integrações;
- migração destrutiva exige backup, plano de restauração e confirmação explícita.

### 9.3 Riscos que bloqueiam publicação

- não conseguir diferenciar limite antigo de aprovação;
- usuário de caixa com permissão de alterar crédito;
- vendedor conseguindo baixar pagamento por endpoint direto;
- acesso fora do escopo operacional em consulta, job ou relatório;
- contas/estoque duplicados após retry;
- compra recebida sem movimento ou movimento sem origem;
- etiqueta funcionando em Vite mas não no nginx de staging/prod;
- URL pública baseada em host manipulável;
- full suite não reproduzível ou migração incremental não testada.

## 10. Pendências de decisão do negócio

Estas decisões devem ser registradas antes da implementação correspondente:

1. Escopo operacional monoempresa/monobanco e futura evolução sem implementação de multi-tenancy nesta fase.
2. Quem é o responsável financeiro e qual perfil receberá as permissões de crédito.
3. Prazo de validade padrão da aprovação e periodicidade de revisão.
4. Política de atraso: bloqueio automático, tolerância e quem pode liberar exceção.
5. Se pedido a prazo reserva crédito imediatamente ou somente na finalização.
6. Se venda à vista para cliente identificado pode ser recebida no Caixa normalmente.
7. Layout físico da etiqueta, impressora e quantidade de etiquetas por item.
8. URL pública oficial e portas externas por ambiente.
9. Política de conversão de `clientes.limite_credito` legado para aprovação inicial.
10. Regras contábeis/fiscais do boleto e da baixa por PIX/cartão.

## 11. Ordem de execução resumida

```text
S0 Auditoria e decisões
  -> S1 Contexto operacional/auditoria/contratos
  -> S2 Crediário/RBAC/serviço de decisão
  -> S3 Pré-venda/orçamento/caixa/boleto
  -> S4 Compras/recebimento/estoque/produto
  -> S5 Etiquetas/impressão/URLs
  -> S6 Auditoria transversal/refatoração
  -> S7 UX/E2E/observabilidade
  -> S8 Contract/piloto/publicação autorizada
```

Nenhuma sprint posterior pode mascarar falha de uma sprint anterior. Em especial: não liberar UI de crédito antes da autoridade no backend; não usar saldo do produto para decidir compra antes da reconciliação; não remover o legado antes da fase Contract; e não publicar qualquer ambiente sem confirmação explícita do usuário.
