# Plano de Implementacao: Classificacao de Despesas, Competencia e Rateio na Precificacao

## 1. Objetivo

Implementar uma classificacao financeira confiavel para distinguir despesas fixas, despesas variaveis e custos diretamente apropriaveis, conectando o Plano de Contas, os lancamentos financeiros, as compras, os centros de custo, os relatorios e o motor de precificacao.

O sistema deve deixar de depender de nomes livres como `Aluguel`, `Cartao` ou `Frete` e passar a saber, de forma estruturada:

- qual e a natureza economica do lancamento;
- em qual competencia ele pertence;
- se deve ou nao participar do rateio de precificacao;
- qual produto, grupo, deposito, canal ou centro de resultado deve absorver o custo;
- se o custo ja foi informado diretamente no produto e nao pode ser incluido novamente no rateio;
- quem classificou, alterou, aprovou e utilizou essa informacao.

O escopo e monoempresa/monobanco. Multi-tenancy permanece fora deste plano.

## 2. Diagnostico atual

### 2.1 Plano de contas

O cadastro atual possui essencialmente:

- codigo;
- nome;
- tipo `receita` ou `despesa`;
- conta pai;
- ativo/inativo.

Nao existe um atributo semantico para distinguir:

- despesa fixa;
- despesa variavel;
- custo direto;
- custo de mercadoria vendida;
- despesa nao rateavel;
- despesa excluida da precificacao.

### 2.2 Contas a pagar

`contas_pagar` possui `plano_conta_id`, mas:

- o formulario de lancamento manual nao obriga a selecao da conta;
- os lancamentos de recebimento de compras nao herdam uma classificacao configurada;
- nao ha competencia financeira/gerencial explicita;
- nao ha flag de elegibilidade para rateio;
- nao ha garantia de que uma despesa paga ou em aberto seja classificada;
- nao ha mecanismo para tratar rateio parcial ou centros de custo.

### 2.3 Precificacao

A configuracao atual permite informar valores agregados de despesas fixas e variaveis. O motor calcula percentuais gerais, mas ainda nao consulta automaticamente as contas a pagar classificadas e aprovadas para compor o custo variavel ou fixo.

Consequentemente, a empresa pode classificar uma conta contabilmente, mas o dado ainda nao alimenta automaticamente a metodologia de precificacao.

## 3. Conceitos de negocio

### 3.1 Natureza de custo

Cada conta de despesa deve ter uma natureza principal:

| Natureza | Definicao | Exemplo |
|---|---|---|
| `fixa` | Nao varia diretamente com o volume vendido no curto prazo | aluguel, salarios administrativos, sistema, contador |
| `variavel` | Varia com venda, recebimento, entrega ou volume operacional | taxa de cartao, comissao, frete de venda |
| `custo_direto` | Pode ser associado diretamente a produto, compra ou servico | embalagem especifica, frete de compra apropriado |
| `cmv` | Custo da mercadoria vendida, apurado pelo estoque | custo medio/PEPS conforme politica definida |
| `nao_rateavel` | Despesa gerencial que nao deve formar preco automaticamente | multas, doacoes, perdas extraordinarias |
| `fora_precificacao` | Lancamento financeiro sem uso no calculo de preco | transferencias, adiantamentos, impostos recuperaveis |

Para evitar ambiguidade, `fixa` e `variavel` representam comportamento economico. `custo_direto`, `cmv`, `nao_rateavel` e `fora_precificacao` representam tratamento no rateio. O cadastro deve permitir uma combinacao valida, mas impedir combinacoes sem sentido.

### 3.2 Elegibilidade para precificacao

A natureza nao deve, sozinha, decidir o rateio. Cada conta deve possuir uma politica:

- `nao_incluir`: nunca participa do motor;
- `ratear_faturamento`: entra como percentual sobre receita;
- `ratear_unidades`: distribui por quantidade vendida;
- `ratear_custo_mercadoria`: distribui proporcionalmente ao custo dos produtos;
- `apropriar_direto`: deve ser associado a produto, grupo, pedido ou centro de custo;
- `revisao_manual`: exige aprovacao antes de entrar no calculo.

Padrao recomendado:

- despesas fixas: `ratear_faturamento`;
- despesas variaveis genericas: `ratear_faturamento`;
- frete de compra identificavel: `apropriar_direto` ou `ratear_custo_mercadoria`;
- CMV: tratado pelo estoque, nao somado como despesa a pagar;
- multas e despesas extraordinarias: `nao_incluir`;
- impostos: tratados pelo motor fiscal ou componente fiscal especifico, evitando duplicidade.

### 3.3 Competencia

O sistema deve separar:

- **data de emissao**: quando o documento foi emitido;
- **data de vencimento**: quando deveria ser pago;
- **data de pagamento**: quando saiu do caixa/banco;
- **competencia gerencial**: mes em que a despesa pertence economicamente;
- **periodo de apropriacao**: intervalo quando a despesa deve ser distribuida, como seguro anual.

Para precificacao, o padrao deve ser a competencia gerencial, e nao simplesmente a data de pagamento. Uma conta de aluguel paga em fevereiro, referente a janeiro, deve compor janeiro.

## 4. Modelo de dados alvo

As mudancas devem ser realizadas com migrations versionadas e estrategia Expand/Migrate/Contract.

### 4.1 Extensao de `plano_de_contas`

Adicionar:

- `natureza_custo`: `fixa`, `variavel`, `custo_direto`, `cmv`, `nao_rateavel`, `fora_precificacao`;
- `politica_rateio`: `nao_incluir`, `ratear_faturamento`, `ratear_unidades`, `ratear_custo_mercadoria`, `apropriar_direto`, `revisao_manual`;
- `exige_centro_custo`;
- `exige_competencia`;
- `permite_rateio`;
- `componente_variavel`: `frete`, `cartao`, `comissao`, `embalagem`, `outros` ou nulo;
- `limite_aprovacao` opcional;
- `observacao_padrao`;
- `atualizado_por`.

Restricoes:

- conta de `receita` nao pode possuir natureza de despesa;
- conta `cmv` nao deve ser usada para criacao manual de contas a pagar sem justificativa;
- conta `nao_rateavel` nao pode ser marcada como elegivel;
- conta inativa nao pode ser usada em novos lancamentos;
- alteracao da natureza nao apaga o historico anterior.

### 4.2 Extensao de `contas_pagar`

Adicionar:

- `plano_conta_id` validado;
- `competencia` no formato `YYYY-MM`;
- `data_competencia_inicio` e `data_competencia_fim` quando necessario;
- `natureza_custo_snapshot`;
- `politica_rateio_snapshot`;
- `elegivel_precificacao`;
- `componente_precificacao`;
- `centro_custo_id`;
- `centro_resultado_id` se o dominio ja estiver disponivel;
- `origem_classificacao`: `manual`, `herdada_compra`, `regra_fornecedor`, `regra_conta`, `importada`;
- `status_classificacao`: `pendente`, `classificada`, `aprovada`, `rejeitada`;
- `classificado_por`, `classificado_em`, `aprovado_por`, `aprovado_em`;
- `observacao_classificacao`.

O snapshot e necessario porque a natureza da conta pode mudar no futuro, mas um lancamento antigo deve continuar auditavel com a classificacao usada na epoca.

### 4.3 Rateios

Criar `conta_pagar_rateio` para casos em que uma conta seja dividida:

- `id`;
- `conta_pagar_id`;
- `centro_custo_id`;
- `produto_id`, `variante_id` ou grupo de produto, quando aplicavel;
- `percentual`;
- `valor`;
- `competencia`;
- `elegivel_precificacao`;
- `politica_rateio`;
- `criado_por` e timestamps.

A soma dos percentuais deve ser 100% quando o rateio estiver concluido. Enquanto estiver incompleto, o lancamento fica `revisao_manual` e nao alimenta a precificacao.

### 4.4 Regras de heranca

Criar estruturas para regras padrao, sem sobrescrever o snapshot historico:

#### `fornecedor_regra_financeira`

- fornecedor;
- plano de contas padrao;
- competencia padrao;
- centro de custo padrao;
- natureza/politica derivada da conta;
- prioridade;
- vigencia;
- ativo;
- usuario responsavel.

#### `categoria_compra_regra_financeira`

Permitir que uma categoria ou tipo de compra defina a conta padrao quando o fornecedor vender itens com tratamentos diferentes.

Precedencia:

1. classificacao explicita do documento;
2. regra especifica do item/categoria;
3. regra do fornecedor;
4. regra do tipo de operacao;
5. conta padrao configurada;
6. pendente de classificacao.

Nunca herdar silenciosamente uma conta quando houver mais de uma regra com a mesma prioridade.

## 5. Fluxos funcionais

### 5.1 Cadastro do plano de contas

Ao criar ou editar uma conta de despesa, o usuario autorizado deve informar:

- tipo;
- natureza economica;
- politica de rateio;
- elegibilidade para precificacao;
- componente variavel, se houver;
- necessidade de centro de custo;
- necessidade de competencia;
- conta pai.

A tela deve explicar o impacto. Exemplo: “Taxa de cartao — variavel — ratear por faturamento — componente cartao”.

Ao tentar desativar uma conta usada no historico, o sistema apenas impede novos usos; lancamentos existentes permanecem consultaveis.

### 5.2 Cadastro manual de contas a pagar

Para toda nova conta a pagar, o formulario deve exigir:

- fornecedor ou beneficiario;
- valor;
- data de emissao;
- vencimento;
- plano de contas;
- competencia;
- centro de custo, quando exigido;
- documento e observacao.

Depois da selecao do plano de contas, a tela deve mostrar a natureza e a politica herdada. O usuario nao deve conseguir editar livremente a natureza derivada; somente alterar a conta com permissao apropriada.

Se a conta for `apropriar_direto` ou `revisao_manual`, abrir a etapa de rateio antes de permitir aprovacao.

### 5.3 Recebimento de compras

No pedido/recebimento de compra, a classificacao deve ser definida antes da criacao das contas a pagar.

Fluxo:

1. pedido de compra possui fornecedor, itens, categoria e condicao;
2. sistema resolve a regra financeira;
3. comprador visualiza a conta sugerida e a origem;
4. Financeiro confirma ou corrige a classificacao;
5. recebimento grava snapshot da conta, competencia e centro de custo;
6. contas a pagar sao geradas com a classificacao herdada;
7. qualquer item sem regra fica pendente e impede a aprovacao financeira, mas nao necessariamente impede o recebimento fisico quando a politica operacional permitir;
8. o financeiro nao pode pagar uma conta pendente de classificacao quando a conta exigir classificacao.

Para uma compra de mercadoria, o tratamento deve distinguir:

- valor dos produtos: custo de estoque/CMV, nao despesa fixa;
- frete de compra: custo direto ou apropriacao ao estoque conforme politica;
- seguro e despesas acessorias: conta especifica e politica definida;
- juros/multa por atraso: nao ratear automaticamente no preco, salvo regra aprovada.

### 5.4 Importacao e conciliaçao bancaria

Lancamentos importados sem classificacao devem entrar como `pendente`.

O sistema pode sugerir classificacao por:

- fornecedor;
- descricao normalizada;
- documento;
- valor recorrente;
- conta bancaria;
- regra previamente aprovada.

A sugestao nao e gravacao definitiva. O usuario deve confirmar, e a regra so pode ser aprendida/criada por perfil autorizado.

## 6. Competencia e fechamento

### 6.1 Periodo aberto

Durante o periodo aberto, Financeiro pode classificar e corrigir lancamentos.

### 6.2 Fechamento da competencia

Ao fechar uma competencia:

- contas obrigatorias sem classificacao sao listadas;
- rateios incompletos bloqueiam o fechamento ou exigem justificativa de excecao;
- o sistema calcula despesas fixas e variaveis elegiveis;
- a configuracao de precificacao da competencia e congelada;
- e gerado snapshot para o motor de precificacao;
- o fechamento registra responsavel, data e totais.

### 6.3 Reabertura

Reabrir competencia exige permissao financeira superior e motivo. A reabertura cria um evento de auditoria e invalida os calculos de precificacao derivados, que deverao ser recalculados antes de novo lote.

## 7. Rateio para o motor de precificacao

### 7.1 Apuracao

Para cada competencia aprovada, calcular:

```text
fixas_elegiveis = soma de contas com natureza fixa
variaveis_elegiveis = soma de contas com natureza variavel
diretos_elegiveis = soma dos rateios de apropriacao direta
```

O valor deve considerar o criterio definido:

- realizado: contas emitidas/competentes no periodo;
- caixa: somente contas pagas, quando explicitamente escolhido;
- gerencial: competencia, independentemente do pagamento;
- planejado: orcamento aprovado.

O padrao recomendado para precificacao e gerencial por competencia.

### 7.2 Percentuais

```text
fixa_rateada_pct = fixas_elegiveis / faturamento_base * 100
variavel_rateada_pct = variaveis_elegiveis / faturamento_base * 100
```

O faturamento base deve ser identificado no snapshot: realizado, planejado ou media movel aprovada.

### 7.3 Evitar dupla contagem

Cada componente deve possuir uma origem:

- `conta_rateada`;
- `produto_politica`;
- `fiscal`;
- `estoque`;
- `fora_precificacao`.

Antes do calculo, o sistema deve comparar:

- contas com componente `cartao` versus `cartao_pct` informado na politica do produto;
- contas com componente `comissao` versus `comissao_pct`;
- frete rateado versus frete unitario/percentual;
- embalagem rateada versus embalagem unitaria;
- impostos financeiros versus motor fiscal.

Se o componente estiver em ambos os lados, o sistema deve bloquear ou exigir uma decisao explicita: excluir do rateio, excluir do produto ou usar modo hibrido com percentual residual.

### 7.4 Formula final

```text
custo_formacao = custo_liquido + embalagem_unitaria + frete_unitario

variaveis_item = frete_item% + cartao_item% + comissao_item%
                 + impostos_item% + outros_item%

variaveis_rateadas = despesas_variaveis_elegiveis / faturamento_base * 100

divisor = 1 - (
    variaveis_item + variaveis_rateadas +
    despesas_fixas_rateadas + margem_alvo
)

preco_sugerido = custo_formacao / divisor
```

O motor deve devolver a memoria discriminando cada parcela e sua origem. A regra atual de referencia de atividade continua disponivel quando nao houver competencia aprovada, mas deve aparecer como fallback explicito, nunca como valor silencioso.

## 8. APIs e contratos

Criar endpoints documentados no OpenAPI:

- `GET /api/plano-contas?tipo=despesa&natureza=variavel&rateavel=1`;
- `POST /api/plano-contas` com classificacao completa;
- `PUT /api/plano-contas/<id>` com validacao de impacto historico;
- `GET /api/plano-contas/<id>/uso`;
- `GET /api/financeiro/competencias`;
- `POST /api/financeiro/competencias`;
- `POST /api/financeiro/competencias/<id>/fechar`;
- `POST /api/financeiro/competencias/<id>/reabrir`;
- `GET /api/financeiro/classificacao/pendencias`;
- `POST /api/financeiro/contas-pagar/<id>/classificar`;
- `POST /api/financeiro/contas-pagar/<id>/rateio`;
- `GET /api/financeiro/contas-pagar/<id>/memoria-classificacao`;
- `GET/PUT /api/fornecedores/<id>/regra-financeira`;
- `GET /api/precos/competencias/<id>/apuracao`;
- `POST /api/precos/competencias/<id>/simular`.

Os endpoints devem:

- validar payloads no backend;
- verificar conta ativa e compatibilidade de natureza;
- resolver heranca no servidor;
- nunca aceitar do frontend uma classificacao derivada sem conferir a origem;
- retornar `code` estavel para erros de regra;
- usar idempotencia nas operacoes de fechamento e aplicacao;
- manter contrato retroativo para consumidores que ainda leem apenas `plano_conta_id`.

## 9. Interface e experiencia do usuario

### Plano de contas

Adicionar colunas e filtros:

```text
Codigo | Conta | Tipo | Natureza | Politica de rateio |
Componente | Centro obrigatorio | Competencia obrigatoria | Status
```

O formulario deve apresentar um painel de impacto com exemplos e alertas de combinacoes invalidas.

### Conta a pagar

Adicionar ao lancamento:

- select pesquisavel de conta contabil;
- badge de natureza;
- badge de elegibilidade;
- competencia editavel conforme permissao;
- centro de custo;
- origem da classificacao;
- link para ratear;
- alerta de pendencia.

Na listagem, permitir filtrar por natureza, elegibilidade, competencia e status de classificacao.

### Central de pendencias

Criar uma fila para:

- contas sem plano de contas;
- contas com competencia ausente;
- rateios incompletos;
- conflitos de heranca;
- possivel dupla contagem;
- despesas fora do periodo fechado;
- contas classificadas depois do fechamento.

Usar tabela acessivel e navegavel por teclado conforme o padrao Salesforce Lightning Datatable/SLDS adotado no projeto.

### Precificacao

Na tela de premissas, exibir:

- competencia utilizada;
- status da competencia;
- faturamento base;
- despesas fixas elegiveis;
- despesas variaveis elegiveis;
- itens excluidos e motivos;
- componentes ja informados por produto;
- percentual final usado no divisor;
- alertas de duplicidade.

## 10. RBAC e auditoria

Permissoes recomendadas:

- `plano_contas.visualizar`;
- `plano_contas.editar`;
- `financeiro.classificar`;
- `financeiro.ratear`;
- `financeiro.fechar_competencia`;
- `financeiro.reabrir_competencia`;
- `precos.visualizar_memoria`;
- `precos.aprovar_premissas`;
- `precos.aplicar_lote`.

Regras:

- operador de caixa nao classifica despesa nem fecha competencia;
- comprador pode sugerir classificacao de compra, mas Financeiro aprova;
- Financeiro pode classificar e aprovar conforme alçada;
- Administrador possui acesso tecnico, mas operacoes sensiveis devem permanecer auditadas;
- quem cria uma competencia ou lote nao deve ser o unico aprovador quando houver segregacao configurada.

Auditar:

- valor anterior e novo;
- classificacao anterior e nova;
- origem da heranca;
- motivo;
- usuario, data e IP;
- competencia;
- snapshot utilizado na precificacao;
- formula e versao do motor.

## 11. Migration e compatibilidade

### Etapa A - Expand

Adicionar colunas novas, tabelas de regra, competencia e rateio. Nenhuma coluna legada sera removida.

### Etapa B - Backfill

Classificar contas existentes por regras conservadoras:

- contas sem classificacao ficam `pendente`;
- somente contas com correspondencia inequívoca recebem backfill automatico;
- nenhum lancamento historico deve ser alterado sem snapshot/auditoria;
- executar em lotes e com relatorio de ambiguidades.

### Etapa C - Dual write

Novos lancamentos gravam `plano_conta_id` e a classificacao/snapshot. A leitura antiga continua funcionando.

### Etapa D - Adocao

Ativar obrigatoriedade por feature flag para novas contas a pagar e recebimentos de compras. Corrigir pendencias existentes.

### Etapa E - Precificacao integrada

Somente competencias fechadas e aprovadas alimentam o motor. A configuracao agregada atual permanece como fallback durante a transicao.

### Etapa F - Contract

Depois de validar todos os consumidores, decidir se campos ou regras antigas podem ser descontinuados. Nao executar `DROP` nesta implementacao inicial.

## 12. Backlog por sprint

### Sprint 0 - Regras e inventario

- aprovar dicionario de natureza e politica de rateio;
- definir criterio padrao de competencia;
- definir faturamento base;
- classificar contas modelo da empresa;
- mapear compras, contas a pagar, bancos, caixa, relatorios e precificacao;
- definir alçadas e excecoes.

**Saida:** ADR, matriz de classificacao, matriz de heranca e cenarios de aceite.

### Sprint 1 - Modelo financeiro

- migration de plano de contas;
- migration de contas a pagar e competencia;
- tabelas de rateio e regras de fornecedor;
- repositorios e validadores;
- backfill seguro e relatorio de ambiguidades.

**Saida:** banco preparado e retrocompativel.

### Sprint 2 - Lancamentos e compras

- tornar conta contabil obrigatoria quando aplicavel;
- adicionar competencia e centro de custo;
- resolver heranca no recebimento de compras;
- criar fila de pendencias;
- permitir classificacao/reclassificacao auditada;
- tratar compras de mercadoria, frete, servicos e despesas acessorias.

**Saida:** todo novo contas a pagar nasce classificado ou explicitamente pendente.

### Sprint 3 - Fechamento e rateio

- criar competencia aberta/fechada;
- calcular totais elegiveis;
- validar rateios em 100%;
- bloquear dupla contagem;
- criar aprovacao e reabertura;
- disponibilizar memoria de apuracao.

**Saida:** competencia financeira gerencial pronta para consumo.

### Sprint 4 - Integracao com precificacao

- adaptar configuracao de precificacao para consumir snapshot aprovado;
- incluir fixas e variaveis rateadas no divisor;
- preservar fallback por referencia de atividade;
- exibir origem e memoria;
- integrar politica individual de produto/variacao;
- criar simulacao comparativa antes/depois.

**Saida:** preco baseado em despesas classificadas, sem duplicidade.

### Sprint 5 - Frontend, relatorios e homologacao

- concluir telas de plano de contas, conta a pagar e pendencias;
- relatorios por natureza, competencia, centro e elegibilidade;
- relatorio de despesas nao classificadas;
- relatorio de impacto na margem;
- testes com catalogo e historico real anonimizado;
- ativacao gradual por feature flag.

**Saida:** processo operacional completo, auditavel e utilizavel pelo financeiro.

## 13. Testes obrigatorios

### Regras de classificacao

- conta de receita nao aceita natureza de despesa;
- conta inativa nao pode ser usada em novo lancamento;
- natureza e politica incompatíveis sao rejeitadas;
- alteracao da conta nao altera snapshot historico.

### Conta a pagar

- lancamento manual exige conta e competencia quando a regra determinar;
- fornecedor com regra valida herda classificacao;
- conflito de regras gera pendencia;
- conta sem regra fica pendente;
- rateio parcial nao entra na precificacao;
- rateio de 100% e aprovado corretamente.

### Compras

- produto de estoque vai para CMV/estoque, nao para despesa fixa;
- frete de compra segue politica configurada;
- conta a pagar de compra herda fornecedor/categoria;
- recebimento repetido nao gera duplicidade;
- pagamento de conta pendente segue bloqueio definido.

### Competencia

- competencia usa data economica, nao apenas pagamento;
- fechamento congela snapshot;
- reabertura exige permissao e motivo;
- lancamento posterior em competencia fechada gera pendencia ou exige reabertura.

### Precificacao

- despesas fixas elegiveis entram no divisor;
- despesas variaveis elegiveis entram somente quando o modo estiver ativo;
- componentes duplicados geram bloqueio/alerta;
- fallback de referencia de atividade e identificado;
- margem individual por produto prevalece conforme precedencia;
- memoria reproduz a planilha dentro da tolerancia de arredondamento.

### Operacao e seguranca

- RBAC impede classificacao/aprovacao indevida;
- fechamento e aplicacao sao idempotentes;
- dois usuarios nao fecham a mesma competencia simultaneamente;
- auditoria registra todas as alteracoes;
- API nao confia em natureza enviada pelo frontend;
- migration vazia e incremental passam no CI.

## 14. Criterios de aceite finais

O plano sera considerado concluido quando:

1. toda conta de despesa nova possuir natureza e politica de rateio validas;
2. toda conta a pagar obrigatoria tiver plano, competencia e centro de custo quando aplicavel;
3. recebimentos de compra herdarem classificacao com origem visivel;
4. existir fila de pendencias para excecoes;
5. competencias puderem ser fechadas, auditadas e reabertas sob alçada;
6. o motor usar apenas despesas elegiveis de competencia aprovada;
7. o sistema impedir dupla contagem com custos por produto;
8. a memoria mostrar cada componente usado no divisor;
9. relatorios financeiros e de precificacao reconciliarem com os lancamentos;
10. margem individual e lote consumirem a politica correta do produto/variacao;
11. rollback e compatibilidade legada forem testados;
12. nenhum deploy ou migration fora de DEV ocorrer sem confirmacao explicita.

## 15. Resultado esperado

Ao final, o Plano de Contas sera uma fonte semantica de classificacao, Contas a Pagar sera o registro financeiro completo e a Precificacao consumira somente dados aprovados, com competencia, origem, rateio e memoria explicavel.

Isso permite responder com seguranca:

- quanto a loja gastou com despesas fixas e variaveis;
- quais despesas realmente devem formar o preco;
- quais grupos/produtos absorveram cada custo;
- qual margem de contribuicao cada produto gera;
- por que determinado preco foi calculado;
- quem classificou, aprovou ou alterou a premissa.

