# Auditoria visual e plano de evolução UI/UX

> **Base da análise:** capturas autenticadas das telas principais, modais,
> abas e formulários do DEV em 02/09/2026. A auditoria avalia operação de uma
> grande loja de material elétrico, hidráulico, ferragens e ferramentas.

## Diagnóstico atual

O sistema já possui uma base visual consistente: shell compartilhado, navegação
por grupos, cores semânticas, tabelas adaptáveis para mobile, modais com rodapé
de ação e uma Pré-venda orientada a teclado. O modal de busca de cliente, por
exemplo, comunica `↑/↓`, `Enter` e `Esc` de forma direta ([captura](capturas/pre-venda-cliente-desktop-dev.png)).

Os principais pontos de fricção observados são:

- A barra lateral reúne muitas rotas no mesmo nível; depois de Compras e
  Financeiro ela exige bastante varredura visual. Favoritos, recentes e busca
  global devem reduzir esse custo sem remover o acesso direto.
- Tabelas de Clientes e Fornecedores exibem muitos campos e ações por linha
  ([Clientes](capturas/clientes-desktop-dev.png), [Fornecedores](capturas/fornecedores-desktop-dev.png)).
  Em uma grande base, faltam visão salva, filtros combináveis, escolha de
  colunas, paginação explícita, seleção em massa e uma ação contextual única.
- Compras mistura a montagem da necessidade, os filtros e a lista de itens na
  mesma altura ([captura](capturas/compras-sugestoes-desktop-dev.png)). O
  operador precisa de um resumo persistente da necessidade selecionada antes
  de gerar a solicitação.
- Estoque e Fiscal têm muitas abas horizontais ([ABC](capturas/estoque-abc-desktop-dev.png),
  [simulador fiscal](capturas/fiscal-simulador-desktop-dev.png)). Em telas
  menores, deve existir uma navegação de seção com overflow controlado e
  indicação clara da próxima ação.
- Formulários longos, como crediário e cadastro de produto, precisam separar
  melhor dados obrigatórios, política, aprovação, e histórico ([crediário](capturas/clientes-crediario-desktop-dev.png),
  [novo produto](capturas/produtos-novo-desktop-dev.png)).
- Foi observado um bloqueio funcional em [Relatórios](capturas/relatorios-desktop-dev.png):
  o administrador recebeu “Sem acesso”. Deve ser investigado no mapeamento
  RBAC/API antes de qualquer remodelação visual.

## P0 — correções antes de treinamento

1. Corrigir o acesso de administrador a Relatórios e criar teste de contrato que valide a permissão efetiva da rota e do endpoint.
2. Padronizar estados de carregamento com limite observável: skeleton no primeiro carregamento, mensagem de erro com `Tentar novamente` e estado vazio explicando a próxima ação. O editor de produto deve evitar uma tela aparentemente parada durante chamadas assíncronas.
3. Garantir que toda ação crítica tenha grupo explícito de ação primária, secundária e destrutiva. `Salvar`, `Finalizar`, `Receber`, `Aprovar` e `Excluir` não devem competir visualmente no mesmo rodapé.

## P1 — remodelação operacional recomendada

### Shell e navegação

- Manter a identidade atual, mas transformar a lateral em grupos recolhíveis com busca de módulo, favoritos e “recentes”.
- Adicionar breadcrumb e contexto no topo: empresa, depósito, período e documento selecionado. Isso reduz erros de operação em Estoque, Compras e Financeiro.
- Reservar a faixa superior para busca global, ajuda, notificações de aprovação e tarefas pendentes; o avatar não deve competir com ações do processo.

### Tabelas no padrão Lightning/SLDS

- Usar cabeçalho sticky, ordenação visível, filtros por coluna, densidade confortável/compacta e visão salva por usuário.
- Aplicar navegação por teclado com célula ativa, roving `tabindex`, `aria-sort`, seleção por `Space`, ações da linha no último campo e menu contextual com `Enter`/`Esc`. Não depender apenas de cor para status.
- Em grandes listas, usar paginação server-side ou cursor, seleção em massa e virtualização somente quando a medição justificar.
- Mostrar primeiro os campos que respondem à decisão: saldo disponível e cobertura no Estoque; custo, margem e prazo em Compras; limite disponível e atraso em Clientes; vencimento e saldo em Financeiro.

### Formulários, modais e aprovação

- Preferir drawer lateral para edição rápida e página dedicada para cadastro extenso. Usar modal apenas para confirmação, busca contextual ou decisão curta.
- Organizar formulários em seções “Obrigatório”, “Comercial”, “Fiscal”, “Logística” e “Auditoria”, com progresso de completude e erros junto ao campo.
- Manter rodapé sticky com ação primária à direita, cancelar ao lado e ação destrutiva isolada. Preservar o foco ao abrir/fechar e alertar sobre alterações não salvas.
- No Crediário, separar claramente análise, decisão, vigência, limite, prazo e histórico imutável; a ação de aprovação deve exibir o perfil responsável e o motivo obrigatório.

### Pré-venda, Compras e Estoque

- Pré-venda deve manter o caminho sem mouse: produto → quantidade → desconto → condição → observação → finalizar. Um painel lateral fixo pode exibir cliente, crédito, vendedor, itens, estoque e total sem retirar o foco da busca.
- Compras deve adotar um stepper persistente “Necessidade → Cotação → Análise → Pedido → Recebimento”, com resumo fixo dos itens e exceções de unidade, embalagem, prazo e fornecedor.
- Estoque deve abrir por “exceções primeiro”: ruptura, disponível negativo, divergência de inventário, lote próximo do vencimento e itens sem endereço. ABC, reposição e movimentos devem herdar depósito e período do contexto.

### Dashboard, Financeiro e Fiscal

- Dashboard deve priorizar alertas acionáveis em vez de apenas cards: ruptura, compras pendentes, aprovação de desconto/crediário, títulos vencidos, divergências e documentos fiscais rejeitados.
- Financeiro deve separar visualmente “consultar” de “baixar/alterar” e manter filtros de tipo, vencimento, origem e status no topo ([receber](capturas/financeiro-receber-desktop-dev.png)).
- Fiscal deve mostrar contexto da simulação, versão da regra, resultado, advertências e próxima ação; configuração e emissão devem ter permissões e cores de risco distintas.

## P2 — acabamento e produtividade

- Criar atalhos de comando com `Ctrl+/`, busca global e paleta de ações, sem substituir os atalhos explícitos do PDV.
- Oferecer skeleton, empty state orientado e toast com correlação do erro; mensagens técnicas devem ficar em “Detalhes” para o usuário autorizado.
- Aplicar contraste WCAG, foco visível, tamanho mínimo de alvo e suporte a redução de movimento em todas as telas.
- No mobile, manter bottom-sheet, tabs roláveis e cards, mas fixar a ação primária no rodapé quando o formulário exigir rolagem.

## Decisão de remodelação

Não recomendo trocar toda a identidade visual agora. A base atual deve ser
preservada e evoluída em três incrementos: **P0 de confiabilidade e estados**,
**P1 de navegação/tabelas/formulários orientados a processo** e **P2 de
produtividade e acessibilidade**. Essa abordagem reduz risco de treinamento e
permite medir tempo de atendimento, erros de recebimento, conversão de orçamento
e tempo de reposição antes/depois.

