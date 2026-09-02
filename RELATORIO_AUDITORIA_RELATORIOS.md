# Auditoria do Módulo de Relatórios

**Data:** 2026-09-02  
**Escopo:** backend Flask/SQLAlchemy/SQL, frontend React/TypeScript e impressão  
**Status:** levantamento técnico concluído; nenhuma alteração funcional foi publicada

## 1. Parecer executivo

O módulo atual atende somente a uma primeira camada de acompanhamento operacional. Ele possui um dashboard com indicadores planos e algumas agregações, mas ainda não é um módulo de BI/relatórios de um ERP de varejo. Não há separação efetiva entre relatório sintético e analítico, não há mecanismo de impressão/exportação, não há consulta de clientes por perfil/aniversário, e o histórico de compras de um cliente não está disponível como relatório próprio.

O maior risco não é apenas visual. Parte dos números pode induzir decisão incorreta porque as consultas misturam datas de criação com datas de conclusão, usam status legados, calculam estoque/contas sem uma data de corte consistente e não oferecem a composição que permite auditar o total até o documento de origem.

### Classificação geral

| Área | Situação atual | Classificação |
|---|---|---|
| Dashboard executivo | 10 KPIs planos, sem tendência, drill-down ou filtros visíveis | P1 |
| Vendas | Agregação simples limitada a 200 linhas e dimensões com IDs | P0/P1 |
| Compras | Totais e prazo médio, sem análise de fornecedor, item, recebimento ou preço | P1 |
| Estoque | Posição atual limitada a 500 linhas; sem ABC, giro, cobertura ou ruptura | P0/P1 |
| Financeiro/DRE | Cards resumidos; DRE incompleta e aging inconsistente | P0 |
| Clientes | Sem relatórios parametrizados; sem data de nascimento no modelo | P0 |
| Compras por cliente | Não existe relatório/histórico analítico dedicado | P0 |
| Impressão | Existem páginas de documentos, mas não de relatórios | P0 |
| Exportação | Não há PDF, CSV, XLSX nem processamento assíncrono | P0 |
| Segurança/LGPD | Falta granularidade específica para visualizar, imprimir e exportar | P0 |

## 2. Inventário do que existe

### 2.1 Backend

`backend/catalog_server/blueprints/api_relatorios.py` expõe:

- `GET /api/relatorios/central`
- `GET /api/relatorios/dashboard`
- `GET /api/relatorios/vendas`
- `GET /api/relatorios/compras`
- `GET /api/relatorios/estoque`
- `GET /api/relatorios/financeiro`
- endpoints legados para vendas por período, aging, DRE e margem.

`backend/catalog_server/services/relatorios.py` concentra consultas e cálculos em poucos métodos grandes. `backend/catalog_server/repositories/relatorios.py` mantém consultas legadas em paralelo. O catálogo contém apenas cinco famílias e não descreve tipo, colunas, filtros, permissões, orientação ou formatos de saída.

Não existe:

- registry de relatórios com contrato estável e versão de cálculo;
- DTO/schema de filtros e resultados por relatório;
- endpoint de impressão HTML;
- endpoint de exportação PDF/CSV/XLSX;
- fila de geração, histórico, artefato ou download de exportação;
- relatório de clientes por tipo, segmento, aniversário ou data da última compra;
- relatório de compras detalhadas por cliente;
- relatório ABC/XYZ, giro, cobertura, ruptura ou previsão de compras;
- relatório sintético/analítico de compras, vendas e financeiro com drill-down;
- snapshot/as-of para números financeiros e de estoque historicamente reproduzíveis.

### 2.2 Frontend

`frontend/src/pages/relatorios.tsx` possui cinco abas: Dashboard, Vendas, Compras, Estoque e Financeiro/DRE. A implementação atual apresenta cards e tabelas simples:

- Dashboard sem filtros de período visíveis, comparação com período anterior ou links para a origem do número;
- Vendas somente com agrupamento e quatro colunas, sem período, paginação, composição ou exportação;
- Compras com cinco cards, sem lista de pedidos/itens/fornecedores;
- Estoque com tabela atual limitada, sem filtros de situação, categoria, depósito, ABC ou paginação;
- Financeiro com três cards, sem DRE detalhada, aging navegável ou contas a pagar;
- nenhuma ação de `Imprimir`, `Exportar PDF`, `Exportar CSV/XLSX`, salvar visão ou compartilhar consulta.

O layout de `backend/catalog_server/templates/orcamento_print.html` é uma boa referência interna: toolbar de impressão, cabeçalho empresarial, período/identificação, painéis, tabela com cabeçalho repetível, totais, observações, assinaturas e rodapé. O padrão deve ser reutilizado como shell, mas relatórios extensos precisam de uma variante paisagem.

### 2.3 Modelo de dados

O cadastro de clientes já possui `tipo_pessoa`, `segmento`, `categoria`, documentos, contatos e limite de crédito. Porém, não foi encontrado campo de data de nascimento em migrations, modelos, repositório ou tela. Também faltam atributos para governar comunicação de aniversário, como consentimento/canal autorizado, origem e data de cadastro formal.

O relatório de compras por cliente precisa cruzar cliente, orçamento/pedido finalizado, itens, produto/variação, preço, desconto, condição, pagamentos, devoluções e custo na data da venda. Hoje a agregação de vendas por cliente retorna uma chave, não um extrato comercial auditável.

## 3. Falhas técnicas e de negócio

### 3.1 Correção dos números

1. O período padrão começa em `1900-01-01` e termina na data atual. Isso pode retornar todo o histórico quando a tela não envia filtros e torna caro o primeiro carregamento.
2. Não há validação consistente de `data_inicio <= data_fim`, limite máximo, timezone da loja ou data de corte.
3. Vendas usam `orcamentos.criado_em`, embora o evento de negócio relevante seja finalização/autorização/faturamento. Um orçamento criado em um mês e finalizado em outro pode cair no período errado.
4. Receita, desconto, impostos, frete, taxas, devoluções e cancelamentos não possuem uma regra única documentada. O total por linha não é necessariamente conciliável com o total do documento.
5. CMV/margem não estão congelados no fato da venda. `margem_vendas` chama cálculo de custo por linha, gerando N+1 e risco de usar o custo atual em vez do custo histórico.
6. Dashboard calcula caixa pelo último `saldo_posterior` global, não por período, caixa, operador, depósito ou filial.
7. Inadimplência e estoque são posições correntes misturadas com vendas do período. Falta o conceito explícito de “posição em” uma data.
8. Aging inclui apenas status `aberto`, podendo omitir títulos parciais. As faixas também se sobrepõem no dia corrente e não definem claramente 1-30, 31-60, 61-90 e acima de 90.
9. DRE contém somente receita/CMV e despesas pagas; não é uma DRE gerencial completa nem necessariamente coincide com o regime contábil adotado.
10. Consultas legadas ainda consideram `fechado`, enquanto o lifecycle novo trabalha com `finalizado/recebido/cancelado/devolvido`. Isso permite divergência entre telas e relatórios.
11. Compras considera `parcialmente_recebido` como recebido e não mede pedido, recebimento, divergência, prazo prometido, atraso ou atendimento do fornecedor.
12. Estoque ignora quantidade zero, justamente onde surgem rupturas. O valor atual não é um valor histórico e não há saldo por depósito na consulta analítica.

### 3.2 Performance e escalabilidade

- Vendas limita 200 linhas sem informar que há mais dados e sem paginação determinística.
- Estoque limita 500 linhas sem paginação, cursor ou total distinto de produtos.
- Não há ordenação controlada, índices documentados ou evidência de `EXPLAIN` para as principais consultas.
- O cálculo de margem executa custo por linha, um padrão N+1.
- Não existe pré-agregação para períodos longos, cache por filtro ou job assíncrono para arquivos grandes.
- Exportações, quando forem adicionadas, não podem ser geradas dentro do request HTTP para grandes volumes.

### 3.3 Segurança, autorização e LGPD

O gate RBAC geral existe, mas o catálogo de relatórios não diferencia claramente visualizar, imprimir, exportar, ver dados financeiros, ver dados pessoais/crédito e administrar relatórios/agendamentos. CPF/CNPJ, telefone, limite de crédito, títulos e histórico de compras devem ser mascarados ou negados conforme perfil. Toda exportação precisa registrar usuário, relatório, filtros, período, quantidade e formato. CSV deve neutralizar fórmulas iniciadas por `=`, `+`, `-` ou `@`.

## 4. Relatórios necessários

### 4.1 Catálogo sintético

Relatórios sintéticos respondem “como está o negócio?” e devem trazer KPIs, totais, variação contra período anterior, alertas e links para o analítico.

1. **Resumo executivo:** faturamento, pedidos, ticket médio, margem bruta, CMV, devoluções, recebimentos, inadimplência, estoque e compras em aberto.
2. **Vendas por período:** dia/semana/mês, comparação, metas, quantidade, receita líquida, margem, ticket e cancelamentos.
3. **Compras e abastecimento:** pedidos em aberto, recebidos, atrasados, valor comprado, cobertura e necessidade de compra.
4. **Posição de estoque:** valor a custo e venda, itens em ruptura, estoque baixo, excesso, sem giro e cobertura média.
5. **Financeiro:** contas a receber, contas a pagar, vencidos, a vencer, fluxo de caixa projetado e realizado.
6. **DRE gerencial:** receita líquida, CMV, margem bruta, despesas operacionais, resultado e percentuais.
7. **Carteira de clientes:** clientes ativos, novos, sem compra, aniversariantes, concentração de receita e crédito utilizado.

### 4.2 Catálogo analítico

Relatórios analíticos respondem “quais documentos e fatos formam esse número?”. Todos precisam de filtros, ordenação, paginação, subtotal, total geral e drill-down.

#### Clientes e relacionamento

- clientes por tipo de pessoa, segmento, categoria, vendedor, cidade/UF e situação;
- clientes por data de cadastro e origem;
- aniversariantes por dia, mês e intervalo, com idade opcional, canal autorizado e vendedor responsável;
- clientes sem compra há X dias, primeira/última compra e frequência média;
- clientes ativos/inativos, reativação e risco de concentração;
- clientes com limite, crédito utilizado, disponível, títulos vencidos e bloqueios;
- clientes por faixa de faturamento, margem e ticket médio;
- extrato de compras por cliente: documento, data da venda, vendedor, itens, quantidade, preço, desconto, impostos, total, pagamentos, devoluções, margem e status;
- ranking de produtos comprados por cliente e clientes que compraram determinado produto;
- compras por segmento/categoria e análise de recorrência;
- desempenho de profissionais/parceiros, indicações, bonificações e consumo com margem, quando o domínio de parceiros estiver ativo.

#### Vendas

- vendas por produto/variação, categoria, marca, vendedor, cliente, segmento, canal, condição e depósito;
- itens vendidos, receita bruta/líquida, desconto, custo, margem em valor e percentual;
- ticket médio, itens por pedido, clientes compradores e frequência;
- orçamento → pedido → recebimento: conversão, tempo médio e motivos de perda;
- devoluções, cancelamentos, descontos por usuário e vendas abaixo da margem mínima;
- vendas à vista, crediário, boleto, PIX, cartão e contas em aberto;
- detalhamento conciliável com o documento de origem.

#### Compras

- compras por fornecedor, produto, categoria, marca e comprador;
- preço médio, menor/maior preço e variação por fornecedor/período;
- pedidos em aberto, atrasados, parcialmente recebidos e recebidos;
- prazo prometido x realizado, lead time, OTIF e divergência de quantidade;
- compras por depósito, unidade de compra, embalagem e fator de conversão;
- curva de dependência de fornecedor, concentração e oportunidade de negociação;
- sugestão de compra por estoque mínimo, máximo, ponto de pedido, cobertura, venda média e lead time.

#### Estoque

- saldo por depósito/produto/variação/lote, incluindo saldo zero;
- movimentações e kardex com documento de origem, usuário, motivo e saldo antes/depois;
- curva ABC por valor de consumo, faturamento, margem e quantidade;
- curva XYZ por variabilidade/demanda, com matriz ABC-XYZ;
- giro, cobertura em dias, estoque mínimo/máximo e ponto de pedido;
- ruptura, excesso, itens sem giro, estoque negativo e divergência de inventário;
- aging de estoque por entrada/lote e validade, se aplicável;
- custo médio, última compra, custo na venda e valorização por depósito.

#### Financeiro e fiscal gerencial

- contas a receber por cliente, vencimento, vendedor e condição;
- aging por faixas não sobrepostas, com títulos parciais e data de corte;
- contas a pagar por fornecedor, vencimento, centro de custo e status;
- fluxo de caixa realizado/projetado por caixa, conta e forma de pagamento;
- inadimplência, recuperação, prazo médio de recebimento e exposição de crédito;
- DRE gerencial detalhada com receitas, devoluções, CMV, despesas, impostos, fretes, comissões e resultado;
- conciliação entre pedido, recebimento, conta, pagamento e documento fiscal;
- divergências fiscais/documentos rejeitados, sempre respeitando o motor fiscal e sem inferir imposto apenas por NCM.

## 5. Impressão e exportação

### 5.1 Requisito visual

O relatório impresso deve seguir o shell de `orcamento_print.html`: toolbar com voltar/fechar, imprimir e exportar; cabeçalho com empresa, filial/depósito, nome, período, filtros e data/hora; indicação de sintético/analítico; tabela com cabeçalho repetido; subtotais; total geral; observações; fonte; versão do cálculo; rodapé com página, usuário e confidencialidade; e impressão sem depender de scroll horizontal.

### 5.2 Orientação

| Orientação | Uso recomendado |
|---|---|
| Retrato | Resumo executivo, clientes básicos, aniversariantes, aging curto e listas com até 6 colunas |
| Paisagem | Vendas por item, extrato do cliente, compras por fornecedor, ABC/XYZ, DRE detalhada e kardex |
| Paisagem legal/A3 opcional | Matrizes extensas e comparações de fornecedores, somente quando o parque de impressão suportar |

A orientação deve ser definida pelo relatório e permitir troca manual quando possível. O backend deve devolver metadado `orientation`, e o template deve aplicar `@page { size: A4 landscape; }` ou retrato. O PDF precisa repetir cabeçalhos, controlar quebras, alinhar valores monetários e não cortar a última coluna.

### 5.3 Formatos

- **PDF:** documento paginado e pronto para impressão, usando o mesmo template HTML validado.
- **CSV:** UTF-8, separador configurável e proteção contra formula injection.
- **XLSX:** abas de resumo, dados, parâmetros e legenda; filtros nativos, congelamento da primeira linha e tipos numéricos reais.
- **HTML:** visualização compartilhável apenas quando autorizada, com filtros aplicados e validade do link.

Arquivos grandes devem ser gerados por job Celery/Redis, com status `queued/running/completed/failed/expired`, download autenticado e retenção configurável. PDF pequeno pode ser síncrono, mas deve possuir o mesmo contrato de dados.

## 6. Benchmark de mercado

A referência oficial do TOTVS RM Reports descreve relatórios em listas, agrupamentos, resumos, gráficos, matrizes e códigos de barras, com uso desktop/web e exportação para PDF, Excel, Word, HTML e imagem. Isso indica que o módulo precisa de um catálogo parametrizado e múltiplos formatos, e não apenas cards fixos: [TOTVS RM Reports](https://tdn.totvs.com/display/public/LRM/RM%2BReports).

O material oficial do CRM Fidelidade da TOTVS contempla filtros de perfil, relatórios de compras por período, extrato do cliente, campanhas/pontos, impressão e seleção de aniversariantes por período. Esses são os padrões mínimos para o eixo de clientes e relacionamento: [Manual de CRM Fidelidade TOTVS](https://tdn.totvs.com/display/LRMS/Manual%2Bde%2BCRM%2BFidelidade%2B5681).

Também existe referência oficial para relatório de clientes por data da última compra, com filtros e impressão, exatamente uma das lacunas identificadas: [Clientes por data de compra/venda](https://centraldeatendimento.totvs.com/hc/pt-br/articles/360045941253-VA-VAR-Relat%C3%B3rio-de-Clientes-por-data-de-compra-venda).

O posicionamento do TOTVS Analytics reforça histórico de KPIs, dashboards gerenciais customizáveis e acompanhamento de finanças, compras e estoque: [TOTVS Analytics](https://produtos.totvs.com/ficha-tecnica/tudo-sobre-o-totvs-analytics/).

Não foi possível identificar, nas fontes públicas consultadas, um produto ERP claramente denominado “MRV” que pudesse ser usado como benchmark direto. Se a intenção for uma visão inspirada em construção/obra, a referência aplicável é tratar projeto/obra/tarefa como dimensão opcional de compras e custos, como nas documentações TOTVS de pedidos e cronograma: [Geração de pedidos por projeto/tarefa](https://tdn.totvs.com/pages/viewpage.action?pageId=421385492) e [Cronograma de custos e compras](https://tdn.totvs.com/display/LRM/Cronograma).

## 7. Conclusão da auditoria

O módulo precisa ser tratado como uma frente de produto, não como uma extensão de `relatorios.tsx`. A entrega deve começar por contrato, correção dos fatos e segurança; depois criar o mecanismo de impressão/exportação; em seguida liberar clientes/compras por cliente; e só então ampliar ABC, DRE, recomendações e designer de relatórios.

Nenhum relatório deve ser considerado pronto apenas porque exibe dados. Ele só estará pronto quando o operador conseguir filtrar, entender a origem, imprimir/exportar, reconciliar com o documento e obter a mesma resposta em tela e arquivo.
