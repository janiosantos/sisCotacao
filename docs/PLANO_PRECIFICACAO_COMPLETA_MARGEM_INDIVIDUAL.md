# Plano de Implementacao: Precificacao Completa, Rateio de Custos e Margem Individual

## 1. Objetivo

Completar a metodologia de precificacao baseada na planilha `docs/PLANILHA DE PRECIFICACAO.xlsx`, transformando-a em um processo confiavel para uma loja de materiais eletricos, hidraulicos, ferragens e ferramentas.

O resultado esperado e permitir que o responsavel:

- configure custos fixos e variaveis com origem e periodo de referencia;
- mantenha a formula da planilha reproduzivel e explicavel;
- defina uma margem-alvo individual por produto ou variacao;
- aplique precos em lote por filtros, sem obrigar todos os produtos a usarem a mesma margem;
- visualize custo, impostos, despesas, margem de contribuicao e preco final;
- revise e aprove alteracoes com trilha de auditoria;
- reverta um lote aplicado sem editar precos manualmente.

Este documento exclui multi-tenancy, conforme decisao registrada no projeto.

## 2. Diagnostico do estado atual

### 2.1 O que foi replicado

A implementacao atual reproduz a parte principal da planilha:

```text
Custo de formacao = custo liquido + embalagem unitaria + frete unitario

Divisor = 1 - (frete% + cartao% + impostos% + despesa fixa% + margem%)

Preco sugerido = custo de formacao / divisor
```

Tambem foram incorporados:

- percentuais calculados sobre o preco de venda, e nao sobre o custo;
- despesa fixa por referencia de atividade ou pela relacao despesa fixa/faturamento;
- simulacao separada do cenario de reforma tributaria IBS/CBS;
- preco minimo e preco sugerido;
- memoria de calculo e alertas para divisor invalido;
- preservacao de tabelas antigas que usavam markup sobre o custo;
- configuracao persistida das premissas de faturamento, despesas e tributos;
- uso do mesmo motor de calculo na simulacao e na geracao de precos da tabela.

### 2.2 Como os custos fixos funcionam atualmente

Existem dois modos:

1. **Referencia por atividade**: Comercio usa a referencia configurada para despesas fixas, atualmente 25% por padrao.
2. **Despesa fixa real**: `despesa_fixa_mensal / faturamento_mensal * 100`.

O percentual escolhido entra no divisor do produto. Quando o faturamento e zero, o sistema nao inventa um percentual real: retorna ausencia de percentual e alerta para configuracao.

Esse comportamento esta correto como primeira aproximacao da planilha, mas ainda precisa de:

- historico por competencia;
- aprovacao das premissas;
- separacao entre planejado, realizado e referencia;
- rateio por centro de resultado ou grupo de produto, quando a operacao exigir maior precisao;
- prevencao explicita de dupla contagem.

### 2.3 Como os custos variaveis funcionam atualmente

O sistema aceita custos variaveis ligados diretamente ao calculo do item, como:

- frete percentual ou unitario;
- taxa de cartao;
- comissao;
- impostos;
- embalagem e outros componentes unitarios.

A despesa variavel mensal e calculada e exibida como indicador de percentual real, mas **nao e adicionada automaticamente ao divisor do preco**. Isso evita uma dupla contagem silenciosa, mas deixa a metodologia incompleta para quem espera que a aba de despesas variaveis da planilha seja rateada sobre todos os produtos.

Hoje ainda nao existe:

- classificacao das despesas variaveis por componente;
- definicao de quais componentes ja estao contemplados por produto;
- escolha explicita entre custo variavel especifico e rateio variavel mensal;
- politica de custo por produto/variacao persistida para uso no lote;
- memoria historica da origem de cada percentual usado no preco.

### 2.4 Aplicacao em lote e margem individual

O lote atual usa uma margem ou markup comum da tabela. A margem gravada no item e resultado do calculo, nao uma politica individual de entrada.

Portanto, **a aplicacao em lote com margem individual por produto ainda nao esta implementada**.

O simulador permite testar parametros de um produto, mas esses parametros nao formam uma politica persistida que seja automaticamente consumida pelo reajuste em lote. A tela de geracao de precos tambem ainda trabalha com os campos globais antigos.

Conclusao: a metodologia esta parcialmente replicada; os requisitos de custos variaveis rateados e margem individual em lote ainda precisam ser desenvolvidos.

## 3. Decisoes de negocio obrigatorias

Antes da implementacao, o responsavel financeiro deve confirmar as decisoes abaixo. O sistema deve grava-las na configuracao e mostrar a origem no calculo.

### 3.1 Custo fixo

Suportar tres fontes, com uma unica selecionada por tabela/cenario:

- **Referencia de atividade**: percentual padrao para comercio;
- **Real da competencia**: despesa fixa realizada dividida pelo faturamento realizado;
- **Planejado da competencia**: despesa fixa orcada dividida pelo faturamento orcado.

Nao somar referencia e percentual real simultaneamente. Se houver rateio por centro de resultado, o percentual especifico substitui o percentual global para os produtos abrangidos.

### 3.2 Custo variavel

Suportar dois modos explicitos:

- **Especifico do produto**: usa frete, cartao, comissao, imposto e outros percentuais configurados para o produto/canal.
- **Rateado por faturamento**: calcula `despesa_variavel_mensal / faturamento_mensal * 100` e inclui esse percentual no divisor.

O modo rateado deve exigir uma classificacao das despesas para informar quais componentes estao incluidos. Se cartao e comissao ja forem informados individualmente, o sistema deve impedir ou alertar a inclusao desses mesmos componentes no percentual variavel rateado.

Formula no modo rateado:

```text
Variavel rateada% = despesa variavel elegivel / faturamento de referencia * 100

Divisor = 1 - (
    frete% + cartao% + comissao% + impostos% +
    outros variaveis% + variavel rateada% +
    despesa fixa% + margem alvo%
)
```

### 3.3 Margem individual

O termo **margem de participacao** deve ser registrado com nome de negocio claro para nao ser confundido com markup:

- `margem alvo sobre venda`: percentual desejado do preco de venda;
- `margem de contribuicao`: preco liquido menos todos os custos variaveis;
- `margem de contribuicao %`: margem de contribuicao dividida pelo preco liquido.

A margem individual deve ser uma politica de precificacao, nao apenas o resultado gravado no preco.

Precedencia recomendada:

1. override da variacao/produto na tabela de preco;
2. politica do produto ou familia;
3. politica do grupo/subgrupo;
4. margem padrao da tabela de preco;
5. margem padrao da configuracao geral.

O primeiro nivel encontrado vence. A memoria deve mostrar a fonte: `variacao`, `produto`, `familia`, `grupo`, `tabela` ou `configuracao`.

## 4. Blueprint tecnico alvo

### 4.1 Modelo de dados

Criar em migration versionada, sem remover os campos legados:

#### `precificacao_politica_produto`

- `id`;
- `produto_id` ou `variante_id`, com somente um alvo preenchido;
- `tabela_preco_id`, quando a politica for especifica de um canal/tabela;
- `margem_alvo_pct`;
- `frete_pct`;
- `cartao_pct`;
- `comissao_pct`;
- `outros_variaveis_pct`;
- `embalagem_unitaria`;
- `frete_unitario`;
- `modo_custo_variavel` (`especifico`, `rateado`, `hibrido`);
- `ativo`;
- `vigencia_inicio`, `vigencia_fim`;
- `observacao`;
- `versao`;
- `criado_por`, `atualizado_por`, timestamps.

Criar unicidade para impedir duas politicas ativas para o mesmo produto/variacao e tabela.

#### `precificacao_competencia`

Registrar as premissas por periodo:

- competencia;
- faturamento realizado e planejado;
- despesas fixas realizadas e planejadas;
- despesas variaveis por categoria;
- impostos por categoria;
- taxas de cartao e comissao;
- fonte do valor (`manual`, `importado`, `calculado`);
- status (`rascunho`, `aprovado`, `encerrado`);
- responsavel e aprovador.

#### `precificacao_lote` e `precificacao_lote_item`

Persistir o preview antes de alterar a tabela:

- filtros e parametros utilizados;
- snapshot da configuracao;
- versao da formula;
- usuario criador e aprovador;
- status (`preview`, `aprovado`, `aplicado`, `cancelado`, `revertido`);
- custo, percentuais, margem escolhida, divisor, preco atual e preco proposto por item;
- motivo de bloqueio ou alerta;
- preco anterior para rollback.

#### Campos de compatibilidade em `tabela_preco_itens`

Adicionar sem remover o legado:

- `margem_override_pct`;
- `margem_origem`;
- `politica_precificacao_id`;
- `lote_aplicacao_id`;
- `formula_versao`;
- `preco_calculado_em`.

### 4.2 Motor de calculo

O motor deve receber um objeto imutavel com:

- custo e componentes unitarios;
- impostos e despesas variaveis especificas;
- despesa variavel rateada elegivel;
- despesa fixa resolvida;
- margem alvo;
- cenario tributario;
- origem de cada percentual.

Ele deve devolver:

- custo de formacao;
- percentual total variavel;
- percentual fixo;
- margem alvo;
- divisor;
- preco minimo;
- preco sugerido;
- preco com reforma tributaria;
- margem de contribuicao em valor e percentual;
- margem efetiva sobre o preco final;
- memoria legivel;
- alertas e bloqueios.

Regras de seguranca do calculo:

- divisor menor ou igual a zero bloqueia aplicacao;
- percentuais fora do intervalo permitido bloqueiam salvamento;
- custo ausente ou negativo bloqueia calculo;
- arredondamento monetario somente no resultado final, mantendo maior precisao internamente;
- alteracao da formula exige nova `formula_versao`;
- nenhum preco deve ser alterado durante a previa.

### 4.3 APIs

Implementar contratos versionados e documentados:

- `GET /api/precos/produtos/<id>/politica`;
- `PUT /api/precos/produtos/<id>/politica`;
- `GET /api/precos/variantes/<id>/politica`;
- `POST /api/precos/lotes/previa`;
- `GET /api/precos/lotes/<id>` paginado;
- `POST /api/precos/lotes/<id>/aprovar`;
- `POST /api/precos/lotes/<id>/aplicar`;
- `POST /api/precos/lotes/<id>/reverter`;
- `GET /api/precos/lotes/<id>/memoria`;
- `GET /api/precos/competencias`;
- `POST /api/precos/competencias/<id>/aprovar`.

O endpoint de previa deve aceitar filtros como grupo, subgrupo, familia, marca, fornecedor, curva ABC, situacao de estoque, tabela, canal e faixa de custo. O backend resolve a margem de cada item; o frontend nao envia um preco confiavel para persistencia.

### 4.4 Aplicacao em lote

O lote deve seguir este fluxo atomico:

1. selecionar filtros e tabela;
2. carregar a configuracao e a competencia aprovada;
3. resolver a politica individual de cada produto/variacao;
4. gerar preview paginado;
5. permitir ajustes individuais somente na politica, nunca no preco final;
6. validar bloqueios e alertas;
7. enviar para aprovacao quando exigido;
8. aplicar todos os itens em uma transacao ou nao aplicar nenhum;
9. registrar preco anterior, novo preco e memoria;
10. permitir reversao do lote com lock e idempotencia.

Se o lote for muito grande, usar job assincrono, mas a aplicacao final deve continuar protegida por transacao e controle de concorrencia. O usuario deve ver o status do job e nao receber a falsa informacao de que todos os itens foram aplicados.

## 5. Redesign da interface

### 5.1 Tela de premissas

Organizar em blocos didaticos:

- faturamento e competencia;
- custos fixos: referencia, realizado ou planejado;
- custos variaveis: especificos, rateados e componentes incluidos;
- impostos e cenario tributario;
- regras de arredondamento;
- status da aprovacao.

Cada campo deve exibir formula curta, origem do valor, data da ultima atualizacao e impacto estimado no divisor.

### 5.2 Tela de politica do produto

Exibir:

- produto, variacao, SKU e unidade;
- custo atual e custo de formacao;
- politica herdada e override;
- margem padrao, margem individual e fonte;
- custos variaveis especificos;
- margem de contribuicao;
- simulacao por tabela/canal;
- historico e justificativa da ultima alteracao.

Permitir copiar politica para variacoes selecionadas somente com permissao de edicao e registrar a origem da copia.

### 5.3 Tela de precificacao em lote

Tabela desktop com alta densidade, acessivel e navegavel por teclado, seguindo o padrao adotado no projeto inspirado em Salesforce Lightning Datatable/SLDS:

- selecao por linha;
- foco visivel e `aria` correto;
- Enter edita a margem da linha;
- setas navegam entre celulas;
- Home/End navegam na linha;
- Ctrl/Cmd+Copia e preenchimento em selecao, com confirmacao;
- filtros persistentes;
- colunas fixas para SKU/produto;
- ordenacao por impacto, margem, custo e variacao de preco;
- paginação ou virtualizacao para grandes catalogos.

Colunas minimas:

```text
SKU | Produto/Variacao | Custo | Fixo% | Variavel% |
Margem alvo% | Origem | Divisor | Preco atual |
Preco sugerido | Delta% | Contribuicao | Situacao | Motivo
```

Estados obrigatorios:

- sem custo;
- divisor invalido;
- margem herdada;
- margem sobrescrita;
- variavel rateada incluida;
- possivel dupla contagem;
- preco abaixo do minimo;
- produto sem venda recente;
- alteracao pendente de aprovacao.

### 5.4 Resumo antes da aplicacao

Antes de aplicar, mostrar:

- quantidade de itens elegiveis;
- quantidade bloqueada;
- quantidade apenas com alerta;
- impacto estimado em faturamento e margem;
- maior aumento e maior reducao;
- produtos sem margem individual;
- origem dos custos usados;
- formula e versao;
- usuario que criara e usuario que aprovara.

## 6. Seguranca, auditoria e governanca

- manter regra de negocio no backend;
- aplicar RBAC separado para visualizar, editar, aprovar, aplicar, reverter e exportar;
- exigir aprovador diferente do criador para lotes acima de um limite configuravel;
- bloquear alteracao de premissa aprovada sem reabrir a competencia;
- auditar antes/depois, motivo, usuario, IP, formula, competencia e snapshot;
- proteger contra aplicacao duplicada com chave idempotente;
- usar lock por tabela/produto durante a aplicacao;
- impedir rollback parcial sem registrar excecao;
- nao apagar historico de precificacao;
- exportacoes devem mascarar dados desnecessarios e proteger celulas contra formula injection.

## 7. Estrategia de migration e compatibilidade

Seguir Expand/Migrate/Contract:

### Etapa A - Expand

Criar as tabelas de competencia, politica e lote. Manter `tabelas_preco.margem`, `markup` e precos atuais.

### Etapa B - Backfill

Criar politicas somente onde houver regra clara. Itens sem politica continuam usando a margem da tabela. O backfill deve ser idempotente e executado em lotes.

### Etapa C - Dual read/write

O motor grava origem e versao para novos lotes, mas conserva os campos legados. Comparar o resultado novo com o antigo e registrar divergencias.

### Etapa D - Troca de leitura

A tela passa a ler a politica e o lote, mantendo o contrato existente de consulta de preco.

### Etapa E - Adocao

Ativar por feature flag para uma tabela de preco ou grupo de produtos. Homologar produtos de cabo, lampada, parafuso, conexao e ferramentas.

### Etapa F - Contract

Somente depois de confirmados frontend, relatorios, jobs, integrações e rollback, decidir se campos antigos podem ser descontinuados. Nao fazer `DROP` nesta fase.

## 8. Backlog por sprint

### Sprint 0 - Fechamento das regras

- aprovar dicionario de custos fixos e variaveis;
- definir competencia e fonte oficial do faturamento;
- definir margem alvo versus margem de contribuicao;
- definir limites de aprovacao e segregacao;
- catalogar consumidores dos campos legados;
- escrever cenarios de referencia com valores da planilha.

**Saida:** ADR, dicionario de dados, matriz de precedencia e casos de aceite aprovados.

### Sprint 1 - Modelo e motor

- criar migration versionada;
- criar repositorios de politica e competencia;
- extrair classificacao de custos variaveis;
- incluir rateio opcional no motor;
- calcular margem de contribuicao;
- preservar o modo legado;
- criar testes unitarios de formula e arredondamento.

**Saida:** motor autoritativo com memoria completa e compatibilidade retroativa.

### Sprint 2 - Preview e lote backend

- criar endpoints de politica;
- criar previa paginada e filtros;
- persistir snapshot do lote;
- validar conflitos e divisor invalido;
- aplicar lote atomicamente;
- implementar aprovacao, idempotencia e rollback;
- atualizar OpenAPI e auditoria.

**Saida:** API capaz de simular, aprovar, aplicar e reverter sem depender da interface.

### Sprint 3 - Interface de politicas e lote

- remodelar Premissas;
- criar politica de produto/variacao;
- criar tabela de lote com edicao de margem individual;
- adicionar atalhos e foco conforme Salesforce/SLDS;
- criar resumo de impacto e confirmacao;
- refletir RBAC, loading, erro, empty state e progresso de job.

**Saida:** operador consegue selecionar produtos, ajustar margens individuais e revisar o impacto antes de aplicar.

### Sprint 4 - Relatorios e homologacao

- relatorio de margem por produto, grupo, subgrupo, fornecedor e vendedor;
- relatorio de custo variavel rateado e especifico;
- relatorio de produtos abaixo da margem alvo;
- relatorio de alteracoes de lote e rollback;
- testes com catalogo grande;
- homologacao de cenarios de varejo;
- ativacao gradual por feature flag.

**Saida:** processo operacional auditavel e pronto para uso assistido.

## 9. Criterios de aceite

### Formula da planilha

Com custo de formacao de `199,00`, frete de `1%`, cartao de `2,5%`, imposto de `3%`, despesa fixa de `25%` e margem de `15%`:

```text
Divisor = 1 - 0,01 - 0,025 - 0,03 - 0,25 - 0,15 = 0,535
Preco sugerido = 199 / 0,535 = 371,96
```

O ERP deve produzir o mesmo resultado dentro da tolerancia de arredondamento e exibir a memoria.

### Custos fixos

- referencia por atividade funciona;
- custo fixo real funciona quando faturamento e competencia existem;
- faturamento zero bloqueia o modo real;
- referencia e real nao sao somados;
- alteracao de competencia fica auditada.

### Custos variaveis

- modo especifico nao inclui rateio mensal;
- modo rateado inclui somente despesas elegiveis;
- dupla contagem de cartao/comissao gera alerta ou bloqueio;
- o percentual e exibido por origem;
- o resultado mostra margem de contribuicao.

### Margem individual e lote

- dois produtos da mesma tabela podem usar margens diferentes;
- uma variacao pode sobrescrever a politica do produto;
- item sem override herda a margem corretamente;
- preview nao altera preco;
- aplicacao altera todos os itens validos ou nenhum;
- falha/interrupcao permite retomar sem duplicar;
- rollback restaura o preco anterior do lote;
- usuario sem permissao nao consegue alterar, aprovar ou aplicar.

### Concorrencia e regressao

- dois lotes concorrentes nao sobrescrevem silenciosamente o mesmo item;
- produto alterado depois do preview exige nova previa;
- modo legado continua funcionando;
- relatorios e impressao continuam exibindo o preco efetivamente aplicado;
- migration vazia e migration incremental passam no CI.

## 10. Resultado esperado

Ao concluir este plano, a precificacao deixara de ser apenas um simulador baseado em parametros globais e passara a ser um processo de governanca de margem:

- custos fixos com fonte e competencia;
- custos variaveis especificos ou rateados, sem dupla contagem;
- margem individual por produto/variacao;
- aplicacao em lote com preview, aprovacao, auditoria e rollback;
- formula explicavel para o operador e para o financeiro;
- compatibilidade com precos legados durante a transicao.

