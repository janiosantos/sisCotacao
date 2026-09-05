export interface ManualQuickEntry {
  id: string;
  title: string;
  route: string;
  group: string;
  keywords: string;
  what: string;
  purpose: string;
  role: string;
  access: string;
  prerequisites: string;
  steps: string[];
  shortcuts?: string;
  cautions: string;
  audit: string;
}

export const MANUAL_ENTRIES: ManualQuickEntry[] = [
  {
    id: "dashboard", title: "Painel", route: "#/dashboard", group: "Operação", keywords: "indicadores vendas estoque financeiro",
    what: "Visão resumida da operação da loja.", purpose: "Acompanhar vendas, estoque, recebimentos e alertas que exigem ação.", role: "É o ponto de entrada para priorizar o trabalho do dia; não substitui os relatórios analíticos.", access: "Todos os perfis com acesso ao Painel.", prerequisites: "Usuário autenticado e dados lançados no período.",
    steps: ["Confira os cards de vendas, estoque e financeiro.", "Abra o módulo indicado no alerta para investigar a causa.", "Use os filtros de período quando disponíveis.", "Registre a ação no módulo de origem, não em planilhas paralelas."],
    shortcuts: "Ctrl+/ abre o manual; use Ajuda no topo para pesquisar outro módulo.", cautions: "Indicadores dependem dos lançamentos confirmados; um rascunho não representa venda efetiva.", audit: "A consulta não altera dados; as ações são auditadas nos documentos de origem."
  },
  {
    id: "pre-venda", title: "Pré-venda / PDV", route: "#/pre-venda", group: "Operação", keywords: "pdv venda teclado desconto cliente pagamento",
    what: "Tela de montagem e finalização de uma venda ou orçamento.", purpose: "Registrar itens rapidamente, identificar o cliente e concluir a venda conforme a condição permitida.", role: "Conecta cliente, preço, estoque, crédito, caixa, contas a receber e fiscal.", access: "Vendedor e Operador conforme o RBAC; recebimento fica no Caixa.", prerequisites: "Produtos ativos, preço válido e, para venda a prazo, cliente identificado com crediário aprovado.",
    steps: ["Selecione o cliente ou mantenha Consumidor Padrão para venda à vista.", "Bipe qualquer código ativo do produto ou digite nome, SKU, EAN, código interno, do fabricante, fornecedor ou embalagem; informe quantidade no formato 2*produto.", "O código exato adiciona o item e devolve o foco à pesquisa para a próxima leitura.", "Revise preço, desconto e disponibilidade.", "Escolha a condição permitida; cliente padrão só aceita À vista.", "Use Enter para seguir Desconto → Condição → Observação → Finalizar.", "Finalize e encaminhe o pedido ao Caixa quando houver pagamento."],
    shortcuts: "Ctrl+K pesquisa; leitor+Enter adiciona e prepara a próxima leitura; F1 finalizar; F2 visualizar; F3 salvar; F5 limpar; F6 cliente; F7 imprimir; F8 localizar orçamento.", cautions: "A tela não mantém cliente, indicador ou pedido em cache. Ao sair com alterações, escolha continuar, descartar ou salvar o rascunho. Crédito só é avaliado para cliente identificado em condição a prazo. Se um código estiver vinculado a mais de um produto, escolha o item na lista.", audit: "Venda, desconto, autorização, estoque e recebimento ficam vinculados ao usuário autenticado."
  },
  {
    id: "orcamentos", title: "Orçamentos", route: "#/orcamentos", group: "Operação", keywords: "proposta pedido desconto aprovação boleto",
    what: "Lista de propostas e pedidos de venda com ciclo controlado.", purpose: "Acompanhar rascunhos, aprovações, conversões, reaberturas e documentos financeiros.", role: "É a ponte entre negociação comercial, estoque, crédito, caixa e fiscal.", access: "Vendas para operação; aprovadores e financeiro para ações específicas.", prerequisites: "Cliente/produtos cadastrados; desconto e condição definidos.",
    steps: ["Filtre o status do documento.", "Abra o detalhe para revisar itens, cliente e condição.", "Autorize ou rejeite desconto quando a alçada exigir.", "Converta somente após resolver bloqueios de crédito, estoque e fiscal.", "Use Boleto/Contas apenas nas vendas a prazo elegíveis.", "Para venda à vista, encaminhe o pedido ao Caixa; o pagamento não é recebido aqui.", "Use PDF para emissão ou reimpressão do documento."],
    shortcuts: "Tab percorre ações; Escape fecha detalhes e modais.", cautions: "Pedido finalizado é congelado; reabertura é controlada e boleto emitido impede alteração. Orçamentos nunca recebe dinheiro, PIX, cartão ou qualquer outra forma de pagamento.", audit: "Status, desconto, aprovador, conversão, contas e documentos fiscais são rastreáveis."
  },
  {
    id: "caixa", title: "Caixa", route: "#/caixa", group: "Operação", keywords: "receber pagamento pix dinheiro cartão sangria abertura",
    what: "Controle da sessão de caixa e recebimento de pedidos à vista.", purpose: "Abrir, movimentar, conferir e fechar o caixa com segregação de funções.", role: "Conclui financeiramente a venda à vista; não aprova crediário nem substitui o Financeiro.", access: "Operador/Caixa para receber; responsável autorizado para aprovação e fechamento.", prerequisites: "Sessão aberta e pedido finalizado elegível para recebimento.",
    steps: ["Abra a sessão informando o saldo inicial.", "Localize o pedido finalizado.", "Confirme a forma e o valor recebido; registre troco quando aplicável.", "Lance suprimentos ou sangrias com justificativa.", "Confira o resumo e solicite fechamento/aprovação conforme o perfil."],
    shortcuts: "Use Enter no pedido selecionado; Escape fecha o menu de ações.", cautions: "Vendedor não recebe o próprio pedido; divergências exigem conferência e autorização.", audit: "Cada movimento possui usuário, horário, origem e chave de idempotência."
  },
  {
    id: "posvenda", title: "Pós-venda", route: "#/posvenda", group: "Operação", keywords: "devolução garantia interação cliente",
    what: "Acompanhamento de relacionamento, garantias e devoluções.", purpose: "Resolver ocorrências após a venda e preservar o histórico do cliente.", role: "Fecha o ciclo comercial e alimenta atendimento, estoque, financeiro e qualidade.", access: "Vendas/Pós-venda; ações financeiras dependem do RBAC.", prerequisites: "Venda ou cliente identificado.",
    steps: ["Localize o cliente ou documento.", "Registre interação com próxima ação quando necessário.", "Abra garantia ou devolução e informe motivo e itens.", "Aguarde validações de estoque/financeiro antes de concluir.", "Acompanhe o status até a resolução."], cautions: "Não ajuste estoque ou contas por fora do fluxo de devolução.", audit: "Interações, garantias e devoluções mantêm responsável e histórico."
  },
  {
    id: "catalogo", title: "Catálogo", route: "#/catalogo", group: "Comercial", keywords: "buscar produto carrinho preço",
    what: "Consulta visual de produtos disponíveis para venda.", purpose: "Encontrar produtos por nome, SKU ou marca e montar uma cotação rapidamente.", role: "Apresenta o catálogo comercial sem substituir o cadastro mestre.", access: "Usuários comerciais com visualização.", prerequisites: "Produtos ativos e preços publicados.",
    steps: ["Pesquise por nome, SKU ou marca.", "Abra o produto para conferir variação e preço.", "Informe quantidade e adicione ao carrinho.", "Revise o carrinho e envie para uma cotação."], cautions: "Preço e saldo devem ser confirmados no fluxo de venda antes de prometer ao cliente.", audit: "A consulta não altera cadastro; a cotação criada terá autor e itens."
  },
  {
    id: "produtos", title: "Produtos", route: "#/produtos", group: "Comercial", keywords: "cadastro sku ean ncm estoque variante etiqueta",
    what: "Cadastro mestre de produtos, variações e identificadores.", purpose: "Manter dados comerciais, estoque, fornecedores, preços e perfil fiscal confiáveis.", role: "É a fonte do produto usada por vendas, compras, estoque, fiscal e relatórios.", access: "Cadastro autorizado; exclusão e fiscal são ações restritas.", prerequisites: "Categoria, unidade e dados fiscais quando aplicável.",
    steps: ["Crie ou localize o produto.", "Preencha os dados gerais e abra a aba Códigos para cadastrar EAN/GTIN, código interno, do fabricante, fornecedor ou embalagem.", "Configure estoque por depósito, fornecedores, conversões e preços.", "Revise completude e perfil fiscal.", "Salve e teste cada código ativo em uma busca de produto; o mesmo leitor funciona em pré-venda, compras, estoque, inventário, fiscal, preços, etiquetas, promoções, devolução e histórico."], cautions: "Não reutilize SKU/EAN; códigos duplicados exigem seleção manual e alterações fiscais exigem revisão responsável.", audit: "Alterações cadastrais, importações, etiquetas e status de cadastro ficam registradas."
  },
  {
    id: "clientes", title: "Clientes", route: "#/clientes", group: "Comercial", keywords: "cpf cnpj crédito crediário cadastro",
    what: "Cadastro e histórico comercial do comprador.", purpose: "Identificar clientes, consultar crédito e manter dados para venda e relacionamento.", role: "Determina condição comercial, crédito, cobrança e documentos emitidos.", access: "Vendas para cadastro básico; Financeiro para aprovar/revisar crédito.", prerequisites: "Documento válido e dados de contato mínimos.",
    steps: ["Pesquise antes de criar para evitar duplicidade.", "Cadastre CPF/CNPJ e contatos; confira os dígitos.", "Consulte a situação de crédito.", "Solicite crédito quando necessário; aguarde análise do Financeiro.", "Use histórico e interações para acompanhamento."], cautions: "Nunca conceda crédito pelo PDV; Consumidor Padrão só compra à vista.", audit: "Documento, alterações, interações e eventos de crédito têm histórico."
  },
  {
    id: "parceiros", title: "Parceiros profissionais", route: "#/parceiros", group: "Comercial", keywords: "profissional indicação pontos bônus fidelidade",
    what: "Gestão da rede de profissionais que indicam e consomem na loja.", purpose: "Cadastrar parceiros, acompanhar indicações, pontos e bônus aprováveis.", role: "Conecta relacionamento profissional à venda, fidelização e remuneração controlada.", access: "Comercial cadastra/consulta; Financeiro aprova e paga bônus.", prerequisites: "Política vigente e parceiro ativo.",
    steps: ["Cadastre o profissional e mantenha o status atualizado.", "Gere uma indicação para cliente ou orçamento.", "Acompanhe conversão e pontos no extrato.", "Revise bônus pendentes; Financeiro aprova e paga conforme política."], cautions: "Bônus não é pagamento automático; toda aprovação exige segregação e política vigente.", audit: "Ledger de pontos é somente acréscimo; indicação e bônus possuem estados e responsáveis."
  },
  {
    id: "vendedores", title: "Vendedores", route: "#/vendedores", group: "Comercial", keywords: "vendedor comissão alçada",
    what: "Cadastro dos vendedores e parâmetros de atuação comercial.", purpose: "Vincular vendas, alçadas de desconto e indicadores ao responsável correto.", role: "Identifica autoria comercial, mas não concede crédito nem recebe o próprio pedido.", access: "Administração/Cadastro autorizado.", prerequisites: "Usuário correspondente quando houver operação no PDV.",
    steps: ["Crie ou localize o vendedor.", "Informe nome, contato e situação.", "Defina a alçada de desconto conforme política.", "Mantenha ativo somente quem pode vender."], cautions: "A alçada não substitui autorização de Financeiro.", audit: "Alterações de vendedor e vínculos comerciais são rastreáveis."
  },
  {
    id: "categorias", title: "Categorias", route: "#/categorias", group: "Comercial", keywords: "categoria árvore classificação",
    what: "Árvore de classificação do catálogo.", purpose: "Organizar produtos, filtros, relatórios e regras comerciais.", role: "A classificação alimenta navegação, análise e organização do estoque.", access: "Cadastro autorizado.", prerequisites: "Definição da árvore comercial da empresa.",
    steps: ["Crie a categoria principal.", "Adicione subcategorias quando necessário.", "Revise produtos vinculados antes de excluir ou reclassificar.", "Use a árvore para localizar itens."], cautions: "Evite categorias duplicadas e mudanças sem avaliar relatórios históricos.", audit: "Criação, alteração, exclusão e reclassificação ficam vinculadas ao usuário."
  },
  {
    id: "unidades", title: "Unidades", route: "#/unidades", group: "Comercial", keywords: "unidade compra caixa pacote conversão",
    what: "Cadastro das unidades usadas na compra e venda.", purpose: "Padronizar UN, CX, PCT, RL e conversões entre embalagem e unidade.", role: "Evita divergência entre quantidade solicitada, recebida, estoque e preço.", access: "Cadastro autorizado.", prerequisites: "Convenção de unidades da operação.",
    steps: ["Cadastre sigla e descrição.", "Ative a unidade necessária.", "Associe a fornecedores e conversões do produto.", "Confira o fator antes de cotar ou receber."], cautions: "Unidade em uso não pode ser excluída; alterar fator impacta compras futuras.", audit: "Ativação e alterações cadastrais são registradas."
  },
  {
    id: "compras", title: "Compras", route: "#/compras", group: "Compras", keywords: "cotação fornecedor pedido receber necessidade",
    what: "Pipeline de Solicitação → Cotação → Análise → Pedido → Recebimento.", purpose: "Comprar com comparação de fornecedores, rastreabilidade e entrada correta no estoque.", role: "Liga demanda, negociação, contas a pagar e estoque.", access: "Compras; recebimento conforme segregação definida.", prerequisites: "Produtos, fornecedores e depósito de destino.",
    steps: ["Adicione itens ou use uma necessidade de reposição.", "Convide fornecedores e acompanhe respostas.", "Compare preço, unidade, prazo, marca e disponibilidade.", "Gere o pedido vencedor.", "Receba conferindo quantidades e documento; confirme o depósito."], cautions: "Não receba duas vezes; divergência de linha deve ser tratada antes da confirmação.", audit: "Convites, propostas, escolha, pedido, NF, estoque e contas a pagar são vinculados."
  },
  {
    id: "fornecedores", title: "Fornecedores", route: "#/fornecedores", group: "Compras", keywords: "cnpj contato prazo avaliação fornecedor",
    what: "Cadastro e avaliação dos fornecedores.", purpose: "Manter dados para cotação, pedido, entrega e pagamento.", role: "Fornece a contraparte da compra e seus parâmetros comerciais.", access: "Compras/Cadastro autorizado.", prerequisites: "CNPJ/CPF válido, contatos e condição de pagamento quando conhecida.",
    steps: ["Pesquise antes de cadastrar.", "Informe dados fiscais, endereço e contatos.", "Defina categoria, prazo médio e avaliação.", "Associe produtos quando aplicável.", "Mantenha inativo quem não deve receber convites."], cautions: "Confira o fornecedor e a unidade de compra antes de enviar pedidos.", audit: "Cadastro, contatos, status e avaliações são rastreáveis."
  },
  {
    id: "estoque", title: "Estoque", route: "#/estoque", group: "Compras", keywords: "saldo movimento inventário abc reposição depósito expedição",
    what: "Controle físico e analítico do estoque por depósito.", purpose: "Consultar saldo, movimentações, inventário, curva ABC e necessidades de compra.", role: "É a fonte operacional para disponibilidade, reposição, compras e margem.", access: "Estoque para movimentos; gestão para análises e ajustes autorizados.", prerequisites: "Depósitos e produtos configurados.",
    steps: ["Selecione o depósito e consulte o saldo.", "Use Movimentos/Kardex para rastrear entradas e saídas.", "Execute inventário com contagem e justificativa.", "Analise ABC e necessidade de reposição.", "Use Expedição para separar e acompanhar pedidos."], cautions: "Não corrija saldo diretamente; use fato de estoque auditável.", audit: "Cada entrada, saída, ajuste e inventário mantém origem, usuário e data."
  },
  {
    id: "qualidade", title: "Qualidade do catálogo", route: "#/diagnostico-variacoes", group: "Compras", keywords: "diagnóstico variação qualidade cadastro",
    what: "Painel de inconsistências do cadastro de variações.", purpose: "Encontrar atributos faltantes, duplicidades e dados que impedem venda ou compra.", role: "Previne falhas no catálogo, fiscal, estoque e integrações.", access: "Cadastro e qualidade.", prerequisites: "Produtos/variações importados ou cadastrados.",
    steps: ["Execute a análise.", "Filtre o tipo de problema.", "Abra o detalhe da variação.", "Corrija no cadastro mestre e rode novamente."], cautions: "Não marque como resolvido sem corrigir a origem.", audit: "Correções acontecem no cadastro e preservam usuário/data."
  },
  {
    id: "financeiro", title: "Financeiro", route: "#/financeiro", group: "Financeiro", keywords: "contas receber pagar boleto pix cobrança baixa",
    what: "Central de contas a receber, contas a pagar e cobranças.", purpose: "Controlar vencimentos, baixas, boletos, PIX, comprovantes e inadimplência.", role: "Autoriza crédito, acompanha liquidez e mantém a verdade financeira da venda/compra.", access: "Financeiro; caixa apenas para recebimentos à vista.", prerequisites: "Documentos finalizados e plano de contas configurado.",
    steps: ["Filtre contas por tipo, status e vencimento.", "Abra o título e confira origem e parcelas.", "Emita cobrança pelo provedor configurado quando aplicável.", "Confirme baixa somente após liquidação comprovada.", "Anexe comprovante e trate exceções."], cautions: "Não marque como pago por retorno inválido; conciliação deve respeitar receber/pagar.", audit: "Títulos, parcelas, cobranças, baixas, comprovantes e atores ficam registrados."
  },
  {
    id: "precos", title: "Preços", route: "#/precos", group: "Financeiro", keywords: "tabela preço promoção margem revisão",
    what: "Gestão de tabelas, regras, promoções e revisões de preço.", purpose: "Formar preço por público/canal preservando margem e histórico.", role: "Alimenta Catálogo, PDV, orçamento e decisões comerciais.", access: "Comercial/gestão de preços.", prerequisites: "Produtos, custos e tabelas cadastrados.",
    steps: ["Crie ou selecione uma tabela.", "Defina regras e vigência.", "Simule o preço e confira margem mínima.", "Aplique promoção ou revisão com aprovação.", "Valide no Catálogo/PDV."], cautions: "Sinalização de margem não autoriza venda fora da política; trate bloqueios no backend.", audit: "Regras, versões, vigências e autorizações ficam no histórico."
  },
  {
    id: "historico", title: "Histórico de preços", route: "#/historico", group: "Financeiro", keywords: "preço compra fornecedor evolução",
    what: "Consulta histórica de preços praticados e comprados.", purpose: "Comparar evolução, negociar com fornecedores e entender impacto na margem.", role: "Dá contexto para compras, precificação e relatórios.", access: "Compras e gestão com visualização.", prerequisites: "Compras/cotações registradas.",
    steps: ["Selecione produto ou fornecedor.", "Filtre período.", "Compare preço unitário, unidade e condição.", "Use o resultado na próxima cotação ou revisão."], cautions: "Compare unidades equivalentes e considere frete/impostos quando disponíveis.", audit: "É consulta; origem permanece no documento de compra."
  },
  {
    id: "bancos", title: "Bancos e conciliação", route: "#/bancos", group: "Financeiro", keywords: "conta bancária extrato conciliação",
    what: "Cadastro de contas bancárias, importação de extrato e conciliação.", purpose: "Conferir o que ocorreu no banco contra títulos a receber/pagar.", role: "Fecha o ciclo financeiro e reduz divergências de caixa/banco.", access: "Financeiro.", prerequisites: "Conta bancária e extrato disponível.",
    steps: ["Cadastre a conta bancária.", "Importe ou consulte o extrato.", "Selecione o título do mesmo tipo e valor.", "Concilie e confira o responsável.", "Investigue sobras e diferenças antes de ajustar."], cautions: "Não concilie receber com pagar; divergências não devem ser forçadas.", audit: "Match, tipo, valor, extrato e usuário ficam registrados."
  },
  {
    id: "plano-contas", title: "Plano de contas", route: "#/plano-contas", group: "Financeiro", keywords: "contábil receita despesa centro conta",
    what: "Estrutura de contas para classificar receitas, custos e despesas.", purpose: "Padronizar lançamentos e relatórios gerenciais.", role: "É a linguagem comum entre financeiro, contábil e relatórios.", access: "Financeiro/Administrador.", prerequisites: "Definição contábil da empresa.",
    steps: ["Crie contas por hierarquia.", "Defina natureza e situação.", "Associe gatilhos/eventos quando aplicável.", "Valide em um relatório antes de ativar."], cautions: "Não exclua conta usada em históricos; desative e crie substituta.", audit: "Alterações do plano e vínculos são rastreáveis."
  },
  {
    id: "fiscal", title: "Fiscal", route: "#/fiscal", group: "Fiscal", keywords: "nfe nfce cfop cst ibpt emitente",
    what: "Configuração, simulação, emissão e acompanhamento fiscal.", purpose: "Emitir documentos conforme contexto tributário e legislação vigente.", role: "Garante que venda/compra tenha resultado fiscal explicável e auditável.", access: "Fiscal/Administrador; emissão conforme RBAC.", prerequisites: "Emitente, certificados, regras e perfil fiscal revisados.",
    steps: ["Configure emitente e integrações em ambiente adequado.", "Revise CFOP/CST/CSOSN/CEST e perfil do produto.", "Simule o resultado com contexto correto.", "Emita ou trate contingência conforme o fluxo.", "Acompanhe histórico e rejeições."], cautions: "NCM não determina imposto sozinho; em dúvida, bloqueie para revisão fiscal.", audit: "Snapshot, regra, versão, retorno do provedor e responsável são preservados."
  },
  {
    id: "relatorios", title: "Relatórios", route: "#/relatorios", group: "Gestão", keywords: "vendas estoque compras dre abc margem",
    what: "Consultas gerenciais consolidadas do ERP.", purpose: "Tomar decisões sobre vendas, compras, estoque, margem e financeiro.", role: "Transforma fatos registrados nos módulos em indicadores comparáveis.", access: "Conforme permissão de relatório e sensibilidade do dado.", prerequisites: "Dados lançados e filtros de período/deposito revisados.",
    steps: ["Escolha o relatório adequado à pergunta.", "Defina período, depósito, categoria ou fornecedor.", "Confira totais e critérios.", "Exporte/compartilhe somente dados autorizados.", "Registre a decisão no processo correspondente."], cautions: "Relatório não corrige base; divergências devem ser investigadas na origem.", audit: "Parâmetros da consulta e origem dos dados devem ser preservados quando exportados."
  },
  {
    id: "usuarios", title: "Usuários", route: "#/usuarios", group: "Administração", keywords: "usuário login acesso perfil senha",
    what: "Cadastro de pessoas que acessam o ERP.", purpose: "Controlar identidade, situação e vínculo de acesso.", role: "É a base da autenticação e autoria de todas as operações.", access: "Administrador.", prerequisites: "Política de acesso e perfil definido.",
    steps: ["Crie o usuário com identificação única.", "Associe os perfis mínimos necessários.", "Defina alçada comercial quando aplicável.", "Desative imediatamente acessos que não devem operar.", "Revise permissões periodicamente."], cautions: "Nunca compartilhe login; admin não deve ser usado por toda a equipe.", audit: "Criação, alteração, ativação, troca de senha e perfis são auditáveis."
  },
  {
    id: "perfis", title: "Perfis e permissões", route: "#/perfis", group: "Administração", keywords: "rbac permissão visualizar aprovar financeiro",
    what: "Matriz RBAC de recursos e ações.", purpose: "Aplicar menor privilégio e segregação de funções.", role: "Define quem pode consultar, cadastrar, editar, aprovar, receber e configurar.", access: "Administrador/superusuário.", prerequisites: "Catálogo de recursos e política de segregação.",
    steps: ["Revise o perfil antes de alterar.", "Conceda somente ações necessárias.", "Use overrides com justificativa e prazo quando possível.", "Teste com usuário de cada função.", "Revise a auditoria das alterações."], cautions: "Botão desabilitado não é segurança; o backend deve negar a ação sem permissão.", audit: "Alterações de perfis, vínculos e negações devem ter responsável."
  },
  {
    id: "configuracoes", title: "Configurações", route: "#/configuracoes", group: "Administração", keywords: "loja impressora integração flags contábil",
    what: "Parâmetros operacionais, integrações, impressora e feature flags.", purpose: "Adequar o ERP às regras e equipamentos da loja.", role: "Controla comportamento transversal; alterações devem ser planejadas.", access: "Administrador e responsáveis por cada configuração.", prerequisites: "Definição da operação e backup quando necessário.",
    steps: ["Abra a aba correta.", "Leia o impacto antes de alterar.", "Salve e valide em DEV/staging quando a mudança for relevante.", "Teste o fluxo afetado.", "Registre a decisão e mantenha rollback."], cautions: "Não coloque segredos ou certificados em texto; deploy e migração exigem confirmação.", audit: "Flags e configurações devem registrar valor efetivo e responsável."
  },
  {
    id: "atualizacoes", title: "Atualizações", route: "#/atualizacoes", group: "Administração", keywords: "release notas versão mudança",
    what: "Notas e informações das versões publicadas.", purpose: "Entender mudanças, correções e impactos operacionais.", role: "Ajuda a alinhar treinamento, suporte e validação pós-release.", access: "Todos com visualização; publicação restrita.", prerequisites: "Release com manifesto e notas.",
    steps: ["Leia a versão e o resumo.", "Confira mudanças que afetam seu módulo.", "Siga os procedimentos de validação.", "Reporte comportamento diferente com versão e contexto."], cautions: "Não execute publicação por esta tela sem fluxo autorizado.", audit: "Versão, notas e publicação devem permanecer imutáveis após release."
  },
  {
    id: "webhooks", title: "Webhooks", route: "#/webhooks", group: "Administração", keywords: "pagamento retorno integração evento",
    what: "Monitoramento de eventos recebidos de provedores.", purpose: "Investigar retornos de PIX, boleto e integrações sem duplicar baixa.", role: "Conecta sistemas externos ao financeiro com idempotência e retry.", access: "Financeiro/Administrador.", prerequisites: "Integração configurada e segredo mantido fora da UI.",
    steps: ["Consulte o evento e o status.", "Verifique origem, data e tentativa.", "Abra o título relacionado.", "Reprocesse somente pelo mecanismo autorizado.", "Acione suporte quando o provedor divergir."], cautions: "Não marque pagamento manualmente só porque chegou um evento sem validação.", audit: "Payload sanitizado, processamento, retry e resultado ficam registrados."
  },
  {
    id: "cotacoes", title: "Cotações de compra", route: "#/cotacoes", group: "Compras", keywords: "cotação proposta fornecedor comparação convite",
    what: "Etapa de negociação do pipeline de compras.", purpose: "Continuar uma cotação legada, convidar fornecedores e comparar propostas.", role: "É compatível com o módulo Compras e não deve criar uma cadeia paralela.", access: "Compras.", prerequisites: "Cotação aberta e itens definidos.",
    steps: ["Abra a cotação ou entre pelo módulo Compras.", "Confira itens e fornecedores convidados.", "Compare respostas por unidade, fator, preço e prazo.", "Feche a cotação e gere o pedido vencedor."], cautions: "Prefira Compras para novos fluxos; não duplique cotação para a mesma necessidade.", audit: "Convites, respostas, escolha e pedidos preservam a origem."
  },
  {
    id: "solicitacoes", title: "Solicitações de compra", route: "#/solicitacoes", group: "Compras", keywords: "solicitação necessidade aprovação compra",
    what: "Pedido interno de compra originado por uma necessidade operacional.", purpose: "Formalizar o que precisa ser comprado antes de cotar.", role: "Inicia a demanda e dá rastreabilidade ao motivo da compra.", access: "Solicitante e aprovador conforme RBAC.", prerequisites: "Produto, quantidade e justificativa.",
    steps: ["Crie a solicitação com itens e prioridade.", "Envie para aprovação quando a política exigir.", "Acompanhe o status.", "Abra a solicitação no Compras para gerar a cotação."], cautions: "Não transforme uma solicitação recusada diretamente em pedido.", audit: "Solicitante, aprovador, motivo, itens e transições ficam registrados."
  },
];

export function buscarManual(term: string): ManualQuickEntry[] {
  const normalized = term.trim().toLocaleLowerCase("pt-BR");
  if (!normalized) return MANUAL_ENTRIES;
  return MANUAL_ENTRIES.filter((entry) =>
    [entry.title, entry.group, entry.keywords, entry.what, entry.purpose].join(" ").toLocaleLowerCase("pt-BR").includes(normalized),
  );
}
