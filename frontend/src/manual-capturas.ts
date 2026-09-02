export type ManualCaptureKind = "Tela principal" | "Ação / subtela" | "Estado contextual";

export interface ManualCapture {
  src: string;
  title: string;
  alt: string;
  caption: string;
  kind: ManualCaptureKind;
}

const captura = (arquivo: string, title: string, caption: string, kind: ManualCaptureKind = "Ação / subtela"): ManualCapture => ({
  src: `/manual/capturas/${arquivo}.png`,
  title,
  alt: `Captura de tela: ${title}`,
  caption,
  kind,
});

export const MANUAL_CAPTURAS: Record<string, ManualCapture[]> = {
  dashboard: [captura("dashboard-desktop-dev", "Painel", "Indicadores e alertas da operação.", "Tela principal")],
  "pre-venda": [
    captura("pre-venda-desktop-dev", "Pré-venda / PDV", "Tela de venda preparada para operação com teclado.", "Tela principal"),
    captura("pre-venda-cliente-desktop-dev", "Busca de cliente no PDV", "Identificação do cliente antes de aplicar condição comercial."),
    captura("pre-venda-dados-desktop-dev", "PDV sem cliente selecionado", "Estado contextual com ações de cliente ainda desabilitadas.", "Estado contextual"),
  ],
  orcamentos: [
    captura("orcamentos-desktop-dev", "Orçamentos", "Lista de propostas, pedidos e ações permitidas.", "Tela principal"),
    captura("orcamentos-detalhes-desktop-dev", "Detalhe do orçamento", "Revisão de itens, status, desconto e condição."),
  ],
  caixa: [
    captura("caixa-desktop-dev", "Caixa", "Sessão de caixa e pedidos elegíveis para recebimento.", "Tela principal"),
    captura("caixa-acoes-desktop-dev", "Ações do caixa sem pedido", "Estado contextual sem pedido selecionado.", "Estado contextual"),
  ],
  posvenda: [
    captura("posvenda-desktop-dev", "Pós-venda", "Acompanhamento de relacionamento e ocorrências.", "Tela principal"),
    captura("posvenda-nova-interacao-desktop-dev", "Nova interação", "Registro de contato e próximo acompanhamento."),
    captura("posvenda-garantia-desktop-dev", "Garantia", "Abertura e acompanhamento de garantia."),
    captura("posvenda-devolucao-desktop-dev", "Devolução / troca", "Fluxo de devolução com motivo e itens."),
  ],
  catalogo: [captura("catalogo-desktop-dev", "Catálogo", "Consulta visual de produtos e preços.", "Tela principal")],
  produtos: [
    captura("produtos-desktop-dev", "Produtos", "Cadastro mestre e lista de produtos.", "Tela principal"),
    captura("produtos-novo-desktop-dev", "Novo produto", "Cadastro de dados gerais, variações e completude."),
    captura("produtos-etiquetas-desktop-dev", "Etiquetas", "Seleção e impressão de etiquetas."),
    captura("produtos-importar-lote-desktop-dev", "Importar lote", "Prévia e resultado da importação idempotente."),
    captura("produtos-familias-desktop-dev", "Famílias", "Organização de famílias e atributos."),
  ],
  clientes: [
    captura("clientes-desktop-dev", "Clientes", "Lista, busca e situação comercial.", "Tela principal"),
    captura("clientes-novo-desktop-dev", "Novo cliente", "Cadastro de dados pessoais e comerciais."),
    captura("clientes-editar-desktop-dev", "Editar cliente", "Abas de dados, endereços e apoio comercial."),
    captura("clientes-crediario-desktop-dev", "Crediário", "Consulta e gestão da análise de crédito."),
  ],
  parceiros: [
    captura("parceiros-desktop-dev", "Parceiros profissionais", "Rede de profissionais, indicações e fidelização.", "Tela principal"),
    captura("parceiros-novo-desktop-dev", "Novo parceiro", "Cadastro de profissional parceiro."),
  ],
  vendedores: [
    captura("vendedores-desktop-dev", "Vendedores", "Lista de vendedores e alçadas.", "Tela principal"),
    captura("vendedores-novo-desktop-dev", "Novo vendedor", "Cadastro de vendedor e comissão."),
  ],
  categorias: [captura("categorias-desktop-dev", "Categorias", "Árvore de classificação do catálogo.", "Tela principal")],
  unidades: [captura("unidades-desktop-dev", "Unidades", "Unidades de venda, compra e conversão.", "Tela principal")],
  compras: [
    captura("compras-desktop-dev", "Compras", "Pipeline de necessidade até recebimento.", "Tela principal"),
    captura("compras-sugestoes-desktop-dev", "Sugestões de compra", "Necessidades calculadas para reposição."),
    captura("compras-nova-cotacao-desktop-dev", "Nova cotação", "Montagem de cotação e seleção de fornecedores."),
    captura("compras-cotacoes-desktop-dev", "Cotações", "Acompanhamento das negociações abertas."),
    captura("compras-pedidos-desktop-dev", "Pedidos de compra", "Pedidos gerados e recebimento."),
  ],
  fornecedores: [
    captura("fornecedores-desktop-dev", "Fornecedores", "Busca, avaliação e dados comerciais.", "Tela principal"),
    captura("fornecedores-novo-desktop-dev", "Novo fornecedor", "Cadastro fiscal, contatos e prazo."),
    captura("fornecedores-editar-desktop-dev", "Editar fornecedor", "Manutenção de dados e contatos."),
  ],
  estoque: [
    captura("estoque-desktop-dev", "Estoque", "Saldo, movimentos e visão operacional.", "Tela principal"),
    captura("estoque-abc-desktop-dev", "Curva ABC", "Priorização de itens por valor e giro."),
    captura("estoque-inventario-desktop-dev", "Inventário", "Contagem e ajuste controlado."),
    captura("estoque-enderecos-desktop-dev", "Endereços", "Localização física por depósito."),
  ],
  qualidade: [captura("diagnostico-variacoes-desktop-dev", "Qualidade do catálogo", "Diagnóstico de variações incompletas.", "Tela principal")],
  financeiro: [
    captura("financeiro-desktop-dev", "Financeiro", "Contas a receber, pagar e cobranças.", "Tela principal"),
    captura("financeiro-entrada-desktop-dev", "Lançamento de entrada", "Registro de receita ou crédito."),
    captura("financeiro-saida-desktop-dev", "Lançamento de saída", "Registro de despesa ou débito."),
    captura("financeiro-receber-desktop-dev", "Contas a receber", "Títulos, parcelas e baixa financeira."),
    captura("financeiro-condicoes-desktop-dev", "Condições de pagamento", "Parcelas, vencimentos e percentuais."),
  ],
  precos: [
    captura("precos-desktop-dev", "Preços", "Tabelas, regras e revisões de preço.", "Tela principal"),
    captura("precos-nova-tabela-desktop-dev", "Nova tabela de preço", "Criação de tabela por canal ou público."),
    captura("precos-simulador-desktop-dev", "Simulador de preço", "Simulação de preço e margem."),
  ],
  historico: [captura("historico-desktop-dev", "Histórico de preços", "Evolução dos preços de compra e venda.", "Tela principal")],
  bancos: [
    captura("bancos-desktop-dev", "Bancos", "Contas bancárias, extrato e conciliação.", "Tela principal"),
    captura("bancos-nova-conta-desktop-dev", "Nova conta bancária", "Cadastro de conta corrente."),
  ],
  "plano-contas": [captura("plano-contas-desktop-dev", "Plano de contas", "Estrutura de receitas, custos e despesas.", "Tela principal")],
  fiscal: [
    captura("fiscal-desktop-dev", "Fiscal", "Configurações, documentos e consultas fiscais.", "Tela principal"),
    captura("fiscal-simulador-desktop-dev", "Simulador fiscal", "Resultado tributário contextual."),
    captura("fiscal-historico-desktop-dev", "Histórico fiscal", "Rastreabilidade de resultados e documentos."),
  ],
  relatorios: [captura("relatorios-desktop-dev", "Relatórios", "Indicadores para vendas, compras, estoque e financeiro.", "Tela principal")],
  usuarios: [captura("usuarios-desktop-dev", "Usuários", "Cadastro e situação dos acessos.", "Tela principal")],
  perfis: [captura("perfis-desktop-dev", "Perfis e permissões", "Matriz RBAC por recurso e ação.", "Tela principal")],
  configuracoes: [captura("configuracoes-desktop-dev", "Configurações", "Parâmetros operacionais e integrações.", "Tela principal")],
  atualizacoes: [captura("atualizacoes-desktop-dev", "Atualizações", "Notas e versões do sistema.", "Tela principal")],
  webhooks: [captura("webhooks-desktop-dev", "Webhooks", "Eventos recebidos e processamento de integrações.", "Tela principal")],
  cotacoes: [captura("cotacoes-desktop-dev", "Cotações de compra", "Tela legada de negociação com fornecedores.", "Tela principal")],
  solicitacoes: [captura("solicitacoes-desktop-dev", "Solicitações de compra", "Demandas internas antes da cotação.", "Tela principal")],
};

export function capturasDoManual(id: string): ManualCapture[] {
  return MANUAL_CAPTURAS[id] ?? [];
}
