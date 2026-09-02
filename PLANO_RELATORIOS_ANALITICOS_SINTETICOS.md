# Plano de Implementação: Relatórios Analíticos e Sintéticos

**Objetivo:** transformar o módulo de relatórios em uma solução operacional e gerencial para uma grande loja de material elétrico, hidráulico, ferragens e ferramentas.  
**Fora de escopo nesta versão:** multi-tenancy, contabilidade legal completa, emissão fiscal e domínio de obras/parceiros quando ainda não houver modelo aprovado.

## 1. Princípios obrigatórios

1. A regra de negócio e a segurança ficam no backend; o frontend apenas compõe filtros, exibe o contrato e solicita ações autorizadas.
2. Todo relatório terá tipo `sintetico` ou `analitico`, chave estável, versão de cálculo, fonte, data/hora, timezone, moeda, avisos e paginação.
3. O número do relatório precisa ser reconciliável com documentos e fatos de origem.
4. Datas de venda, compra, recebimento, pagamento e estoque serão definidas pelo evento de negócio correto, sem usar automaticamente `criado_em`.
5. Mudança de schema seguirá Expand/Migrate/Contract, com migration versionada, backfill idempotente e compatibilidade retroativa.
6. Exportar é uma operação privilegiada e auditável, não um `window.print()` escondido.
7. A tabela seguirá o padrão de acessibilidade já adotado no projeto, inspirado em Salesforce Lightning Datatable/SLDS: foco visível, navegação por teclado, cabeçalho semântico, ordenação anunciada e ações acessíveis.

## 2. Arquitetura alvo

```text
Frontend React
  -> filtros/colunas/estado da consulta
  -> GET dados paginados / POST exportação
API Flask + schemas
  -> RBAC, validação, limite, auditoria e contrato
Report Registry
  -> metadados, permissões, orientação, colunas, formatos
Query Services / Repositories
  -> fatos corretos, joins, agregações e drill-down
PostgreSQL
  -> índices, views/materializações quando comprovadas por EXPLAIN
Celery/Redis
  -> PDF/XLSX/CSV grandes, retenção e download autenticado
Templates de impressão
  -> shell do orçamento, A4 retrato/paisagem, cabeçalho/rodapé
```

### 2.1 Contrato de resposta

```json
{
  "report_key": "clientes.compras",
  "kind": "analitico",
  "calculation_version": "1.0",
  "generated_at": "2026-09-02T20:00:00-03:00",
  "timezone": "America/Sao_Paulo",
  "currency": "BRL",
  "orientation": "landscape",
  "filters": {"cliente_id": 45, "data_inicio": "2026-01-01", "data_fim": "2026-08-31"},
  "summary": {"total_rows": 28, "total_value": 12450.90},
  "columns": [],
  "rows": [],
  "pagination": {"limit": 100, "next_cursor": null},
  "warnings": []
}
```

## 3. Backlog priorizado

### P0 — fundação, segurança e saída utilizável

#### P0.1 Contrato e registry de relatórios

**Fazer:** substituir catálogo fixo por registry versionado com chave, nome, descrição, tipo, filtros, colunas, orientação, permissões e formatos.

**Como:** criar `catalog_server/reports/` com `registry.py`, `schemas.py`, `filters.py` e serviços por família. Manter adaptadores para endpoints legados durante a transição; não quebrar o contrato já consumido pelo frontend.

**Aceite:** cada relatório tem schema de entrada/saída; filtros inválidos retornam erro estruturado; período obrigatório ou default curto documentado; contrato publicado no OpenAPI; teste de contrato.

#### P0.2 Datas e fatos de negócio

**Fazer:** definir e documentar a data oficial de cada fato: venda finalizada/autorizada, recebimento de compra, pagamento, vencimento e saldo de estoque.

**Como:** mapear lifecycle atual e criar campos/eventos somente quando faltarem. Corrigir consultas legadas para lifecycle vigente sem remover compatibilidade. Criar testes de documento criado em um período e concluído em outro.

**Aceite:** o mesmo fato aparece no período correto; cancelamento/devolução não duplica receita; total do relatório concilia com documento de origem.

#### P0.3 RBAC e LGPD para relatórios

**Fazer:** separar `relatorios.visualizar`, `relatorios.imprimir`, `relatorios.exportar`, `relatorios.financeiro`, `relatorios.dados_pessoais` e `relatorios.configurar`.

**Como:** aplicar `exige_permissao()` no backend em toda rota, incluindo impressão e download; mascarar documentos/contatos; registrar auditoria com usuário, filtros, formato e quantidade.

**Aceite:** vendedor não acessa DRE/limite sem permissão; usuário sem exportar não consegue chamar a API diretamente; tentativa de IDOR é negada; exportação deixa registro auditável.

#### P0.4 Impressão HTML/PDF

**Fazer:** criar shell de relatório semelhante ao pedido de venda, com toolbar, cabeçalho, filtros, tabela paginada, totais e rodapé.

**Como:** criar `report_print.html` e endpoint de impressão por `report_key`; usar `@page` com orientação definida no registry; PDF deve ser gerado pelo mesmo HTML, sem duplicar regra de negócio.

**Aceite:** resumo imprime em retrato; extrato, DRE e ABC imprimem em paisagem; cabeçalho de tabela repete; filtros e período aparecem; documento não corta a última coluna; `window.print()` e salvar PDF funcionam.

#### P0.5 Exportação segura

**Fazer:** oferecer CSV e XLSX; PDF deve reutilizar a impressão; criar job assíncrono para volume alto.

**Como:** endpoint `POST /api/relatorios/{key}/exportacoes`, status e download autenticado; aplicar limite, expiração, encoding, locale, tipos numéricos e neutralização de fórmula CSV.

**Aceite:** pequeno volume responde rapidamente; grande volume vira job; arquivo contém filtros/parâmetros em aba ou cabeçalho; download expirado é negado; falha fica visível ao usuário.

### P1 — relatórios de operação e clientes

#### P1.1 Cadastro de cliente orientado a relacionamento

**Fazer:** adicionar data de nascimento e campos de comunicação permitida, preservando dados existentes.

**Como:** migration Expand com `data_nascimento`, `consentimento_contato`, `canal_preferencial` e `origem_cadastro` anuláveis; atualizar schema, API, formulário e validações; backfill somente quando houver fonte confiável. Não inferir data a partir de CPF/CNPJ.

**Aceite:** cadastro/edição valida data real e timezone; relatório diferencia “não informado”; campos sensíveis respeitam RBAC; migration fresca e incremental passam.

#### P1.2 Relatórios de clientes

**Fazer:** criar clientes por tipo, segmento, categoria, vendedor, cidade/UF, situação, aniversário, data de cadastro, última compra e inatividade.

**Como:** endpoints parametrizados com filtros combináveis, cursor pagination, ordenação whitelist e totais. Aniversário deve aceitar intervalo de datas e lidar com virada de ano. Exibir apenas idade se autorizada, sem exigir ano de nascimento.

**Aceite:** usuário consegue gerar “clientes pessoa jurídica do segmento profissional”; “aniversariantes de julho”; “sem compra há 90 dias”; “última compra entre datas”; tela, impressão e exportação retornam o mesmo conjunto.

#### P1.3 Compras do cliente

**Fazer:** extrato analítico e resumo sintético por cliente e por segmento.

**Como:** cruzar documento finalizado, itens, produto/variação, vendedor, condição, recebimentos, devoluções e margem disponível; permitir drill-down para o documento. Separar valor bruto, descontos, devoluções, líquido e saldo a receber.

**Aceite:** seleção de cliente mostra histórico por período, itens e total; total do extrato concilia com vendas; compras canceladas/devolvidas aparecem como ajuste; impressão paisagem e XLSX funcionam.

#### P1.4 Vendas analíticas e sintéticas

**Fazer:** período, comparação, produto, categoria, marca, vendedor, cliente, segmento, depósito, canal, condição e forma de pagamento.

**Como:** retornar nomes e IDs; incluir quantidade, pedidos, clientes, ticket, desconto, receita líquida, CMV, margem, devolução e participação; usar consulta paginada e agregação separada do detalhe.

**Aceite:** nenhum agrupamento mostra somente ID; 201ª linha é acessível; filtros são refletidos na impressão/exportação; margem não executa N+1.

#### P1.5 Compras e fornecedores

**Fazer:** relatório de pedidos, itens, fornecedores, preços, prazo prometido/realizado, recebimento parcial e divergência.

**Como:** definir eventos de pedido e recebimento; exibir unidade/fator de conversão, marca, quantidade solicitada/recebida, preço, frete e prazo; incluir ranking e concentração por fornecedor.

**Aceite:** comprador identifica atrasados, parcialmente recebidos e maior variação de preço; total recebido concilia com entrada de estoque e conta a pagar.

#### P1.6 Estoque e abastecimento

**Fazer:** saldo por depósito incluindo zero, kardex, ruptura, excesso, sem giro, cobertura, giro, estoque mínimo/máximo, ponto de pedido e sugestão de compra.

**Como:** começar com consulta correta e índices; depois implementar ABC por consumo/receita/margem e XYZ por variabilidade, com janela configurável e metodologia explícita. Não confundir saldo atual com saldo histórico.

**Aceite:** curva ABC informa período, métrica e corte; item sem saldo aparece; sugestão mostra fórmula, estoque atual, demanda, lead time e quantidade recomendada; kardex abre documento de origem.

### P2 — gestão avançada e escala

#### P2.1 Financeiro e DRE gerencial

**Fazer:** aging correto, contas a receber/pagar, fluxo de caixa, inadimplência, exposição de crédito e DRE gerencial.

**Como:** estabelecer regime gerencial, centros de custo, competência/caixa, títulos parciais e data de corte; conciliar lançamentos com pedidos, recebimentos e pagamentos; envolver revisão contábil antes de chamar de DRE fiscal.

**Aceite:** faixas de aging não se sobrepõem; títulos parciais aparecem; DRE demonstra composição; período anterior pode ser comparado; valores são auditáveis.

#### P2.2 Visões salvas e designer controlado

**Fazer:** permitir salvar filtros/colunas/ordenação por usuário e, depois, por perfil.

**Como:** somente sobre relatórios registrados, sem SQL livre; versionar a definição; aplicar permissões no momento da execução e não apenas no salvamento.

**Aceite:** visão salva continua válida após refresh; coluna proibida é removida; usuário não consegue criar consulta arbitrária no banco.

#### P2.3 Agendamento e distribuição

**Fazer:** agendar relatório para usuários autorizados por e-mail interno ou download seguro.

**Como:** job Celery/Redis, janela de execução, timezone, retry, retenção e auditoria; nunca enviar CPF/financeiro a destinatário sem permissão vigente.

**Aceite:** falha gera status e log; execução respeita filtros e timezone; revogação de permissão impede próxima distribuição.

#### P2.4 Performance, observabilidade e governança

**Fazer:** medir consultas, cachear apenas resultados seguros, adicionar índices comprovados, materializar agregados quando necessário e acompanhar uso.

**Como:** `EXPLAIN ANALYZE` com massa representativa; métricas de duração, linhas, erro e exportações; alertas para consultas lentas; retenção de artefatos.

**Aceite:** relatórios críticos têm SLO definido; consulta não degrada por N+1; volume alto não bloqueia workers HTTP; existe procedimento de troubleshooting.

#### P2.5 Parceiros, indicação e visão por obra

**Fazer:** somente após domínio aprovado, incluir parceiro/profissional, indicação, bonificação, margem de consumo e, se aplicável, obra/projeto/tarefa.

**Como:** modelar fatos de indicação e bonificação com status, aprovação, estorno e auditoria; separar comissão de desconto; projeto/obra deve ser dimensão explícita, não texto livre.

**Aceite:** bonificação só nasce de evento elegível; cancelamento estorna; margem usa fatos corretos; nenhum relatório financeiro depende de campo textual ambíguo.

## 4. Sprints sugeridas

### Sprint 0 — especificação e baseline

- congelar dicionário de métricas e datas;
- mapear consumidores dos endpoints atuais;
- criar massa de teste com vendas, devoluções, compras parciais, clientes e títulos;
- documentar contratos e cenários de reconciliação;
- medir consultas atuais.

**Saída:** matriz de métricas aprovada, casos de teste e inventário de compatibilidade.

### Sprint 1 — engine, RBAC e impressão/exportação

- registry e schemas;
- filtros seguros e paginação;
- permissões específicas;
- auditoria;
- shell HTML/PDF retrato/paisagem;
- CSV/XLSX e job assíncrono.

**Saída:** um relatório sintético e um analítico completos como referência vertical.

### Sprint 2 — clientes e histórico de compras

- migration de data de nascimento/comunicação;
- listagens por tipo/segmento/categoria/aniversário;
- última compra e inatividade;
- extrato de compras do cliente;
- impressão/exportação.

**Saída:** requisitos comerciais solicitados pelo usuário atendidos ponta a ponta.

### Sprint 3 — vendas e compras

- vendas por dimensões e margem;
- pedidos e recebimentos;
- ranking/variação de fornecedor;
- divergências e atrasos;
- drill-down para documento.

### Sprint 4 — estoque e abastecimento

- posição por depósito;
- kardex;
- ruptura/excesso/sem giro;
- ABC/XYZ;
- cobertura e sugestão de compra.

### Sprint 5 — financeiro e DRE gerencial

- aging com data de corte;
- contas a receber/pagar;
- fluxo projetado/realizado;
- DRE gerencial conciliada;
- campos sensíveis e exportação protegida.

### Sprint 6 — produto analítico e escala

- visões salvas;
- agendamentos;
- otimização por evidência;
- métricas e alertas;
- homologação operacional com compradores, caixa, estoque e financeiro.

## 5. APIs alvo

As rotas abaixo são uma proposta de contrato; a implementação deve preservar os endpoints existentes até a fase Contract:

```text
GET  /api/relatorios/catalogo
POST /api/relatorios/{report_key}/consulta
GET  /api/relatorios/{report_key}/imprimir
POST /api/relatorios/{report_key}/exportacoes
GET  /api/relatorios/exportacoes/{id}
GET  /api/relatorios/exportacoes/{id}/download
GET  /api/relatorios/clientes
GET  /api/relatorios/clientes/aniversariantes
GET  /api/relatorios/clientes/compras
GET  /api/relatorios/vendas
GET  /api/relatorios/compras
GET  /api/relatorios/estoque
GET  /api/relatorios/financeiro
```

Todos os endpoints devem validar parâmetros por schema, aplicar autorização no backend, limitar tamanho, usar ordenação por allowlist e devolver `request_id` para suporte.

## 6. Plano de testes

- **Unitários:** métricas, faixas de aging, ABC/XYZ, margem, datas de corte e virada de ano em aniversário.
- **Integração:** banco vazio→head, migration incremental, joins, lifecycle de venda/compra e autorização por perfil.
- **Contrato:** schema OpenAPI, filtros inválidos, paginação e compatibilidade de endpoints legados.
- **Segurança:** IDOR, exportação sem permissão, mascaramento, fórmula CSV e download expirado.
- **Frontend:** filtros por teclado, foco, ordenação anunciada, loading/skeleton, empty state, erro, tabela grande e modo impressão.
- **E2E:** cliente por segmento, aniversariante, extrato de compras, venda com devolução, compra parcial, ABC e exportação.
- **Performance:** massa representativa, `EXPLAIN ANALYZE`, limite de tempo para tela e job para arquivo grande.
- **Visual:** PDF retrato/paisagem, cabeçalhos repetidos, quebra de página, moeda, totais e rodapé.

## 7. Definition of Done

Um relatório só entra como concluído quando possui regra de negócio escrita e fonte identificada; schema, permissão, auditoria e OpenAPI; filtros, paginação e estados de tela; total conciliável e drill-down; tela, impressão e exportação autorizada; orientação validada; testes adequados; migration fresca e incremental quando aplicável; documentação wiki; e nenhuma publicação em staging/produção sem confirmação explícita.

## 8. Ordem recomendada de execução

1. Corrigir contrato, datas, status, reconciliação e permissões.
2. Entregar impressão/PDF/CSV/XLSX com uma vertical completa.
3. Adicionar data de nascimento e relatórios de clientes.
4. Entregar extrato de compras do cliente.
5. Completar vendas e compras analíticas.
6. Entregar estoque ABC/XYZ e abastecimento.
7. Completar financeiro/DRE.
8. Adicionar visões salvas, agendamentos, escala e parceiros.

Esse plano deve ser executado em releases incrementais, sem alterar banco, backend e frontend de forma incompatível em uma única tacada.
