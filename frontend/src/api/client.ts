// client.ts — cliente HTTP tipado para a API do catalog_server.

export type Metodo = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

// ------------------------------------------------------------------
// Catálogo
// ------------------------------------------------------------------

export interface ProdutoResumo {
  id: number;
  sku: string;
  name: string;
  spec?: string;
  brand?: string;
  price: number;
  pix_price?: number;
  installment?: string;
  imagem_url?: string;
  color?: string;
  package_label?: string;
  classe_abc?: string;
  unidade_venda?: string;
  embalagem_qtd?: number | null;
  ncm?: string;
}

export interface Atributo {
  id: number;
  label: string;
  options?: string[];
}

export interface Variante {
  id: number;
  name?: string;
  brand?: string;
  price: number;
  imagem_url?: string;
  sku?: string;
  attrs?: Record<string, unknown>;
  fornecedores?: string[];
}

export interface ProdutoGrupo {
  id: number;
  name: string;
  imagem_url?: string;
  price_min: number;
  price_max: number;
  package_label?: string;
  variant_count: number;
  variants: Variante[];
  attrs?: Atributo[];
  brands?: string[];
  group: boolean;
  classe_abc?: string;
}

export type CatalogoItem = ProdutoResumo | ProdutoGrupo;

export interface ListCatalogo {
  items: CatalogoItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface ResumoAbc {
  A: number;
  B: number;
  C: number;
  sem: number;
}

export type CategoriaMap = Record<string, string[]>;

// ------------------------------------------------------------------
// Fornecedores
// ------------------------------------------------------------------

export interface Fornecedor {
  id: number;
  nome: string;
  whatsapp: string | null;
  email: string | null;
  observacoes: string | null;
  razao_social: string | null;
  cnpj_cpf: string | null;
  representante: string | null;
  ativo: number | boolean;
}

export interface FornecedorPayload {
  nome: string;
  whatsapp?: string | null;
  email?: string | null;
  observacoes?: string | null;
}

// ------------------------------------------------------------------
// Clientes, vendedores, usuários e plano de contas (base do ERP)
// ------------------------------------------------------------------

export interface Vendedor {
  id: number;
  nome: string;
  comissao_pct: number;
  ativo: number | boolean;
}

export interface VendedorPayload {
  nome: string;
  comissao_pct?: number;
}

export interface Cliente {
  id: number;
  nome: string;
  tipo_pessoa: string;
  doc: string | null;
  email: string | null;
  telefone: string | null;
  whatsapp: string | null;
  endereco: string | null;
  cidade: string | null;
  uf: string | null;
  cep: string | null;
  vendedor_id: number | null;
  vendedor_nome: string | null;
  limite_credito: number;
  observacoes: string | null;
  ativo: number | boolean;
  contribuinte?: string;
  ie?: string;
}

export interface ClientePayload {
  nome: string;
  tipo_pessoa?: string;
  doc?: string | null;
  email?: string | null;
  telefone?: string | null;
  whatsapp?: string | null;
  endereco?: string | null;
  cidade?: string | null;
  uf?: string | null;
  cep?: string | null;
  vendedor_id?: number | null;
  limite_credito?: number;
  observacoes?: string | null;
  contribuinte?: string;
  ie?: string;
}

export interface ClienteEndereco {
  id: number;
  cliente_id: number;
  tipo: string;
  cep: string;
  logradouro: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  uf: string;
  criado_em: string;
}

export interface ClienteContato {
  id: number;
  cliente_id: number;
  nome: string;
  cargo: string;
  telefone: string;
  email: string;
  criado_em: string;
}

export interface ClienteApoioComercial {
  condicao_pagamento_id: number | null;
  tabela_preco_id: number | null;
  limite_credito: number;
  transportadora: string;
}

export interface ClienteApoioFiscal {
  cfop_padrao: string;
  cst_icms: string;
  cst_pis: string;
  cst_cofins: string;
  aliquota_icms: number;
  aliquota_pis: number;
  aliquota_cofins: number;
}

export interface Usuario {
  id: number;
  nome: string;
  login: string;
  perfil: string;
  ativo: number | boolean;
  desconto_limite_pct?: number;
  autoriza_desconto?: number | boolean;
  criado_em: string;
}

export interface UsuarioPayload {
  nome: string;
  login: string;
  senha?: string;
  perfil: string;
  desconto_limite_pct?: number;
  autoriza_desconto?: boolean;
}

export interface UsuarioAtual extends Usuario {
  autenticado: boolean;
}

export interface ContaPlano {
  id: number;
  codigo: string;
  nome: string;
  tipo: string;
  pai_id: number | null;
  ativo: number | boolean;
}

export interface ContaPlanoPayload {
  codigo: string;
  nome: string;
  tipo: "receita" | "despesa";
  pai_id?: number | null;
}

// ------------------------------------------------------------------
// Cotações
// ------------------------------------------------------------------

export interface CotacaoLista {
  id: number;
  numero: number | string;
  titulo: string | null;
  cliente: string | null;
  observacoes?: string | null;
  status: string;
  fechado_em: string | null;
  criado_em: string;
  data_limite_retorno?: string | null;
  n_itens: number;
  n_fornecedores: number;
  n_respostas: number;
}

export interface ItemCotacao {
  cotacao_item_id: number;
  produto_id: number;
  quantidade: number;
  sku: string;
  name: string;
  brand: string;
  category: string;
  subcategory: string;
  imagem_url: string | null;
  price: number;
}

export interface CotacaoFornecedor {
  fornecedor_id: number;
  status: string;
  nome: string;
  whatsapp: string | null;
  email: string | null;
  data_resposta?: string | null;
  condicao_pagamento?: string | null;
  condicao_pagamento_dias?: number | null;
}

export interface Preco {
  id: number;
  cotacao_item_id: number;
  fornecedor_id: number;
  preco_unitario: number;
  prazo_entrega_dias: number | null;
  observacao: string | null;
  registrado_em: string;
  validade_preco_em: string | null;
  status?: string;
  moeda?: string;
  desconto?: number;
  unidade_compra?: string | null;
  fator_conversao?: number | null;
}

export interface Vencedor {
  id: number;
  cotacao_id: number;
  cotacao_item_id: number;
  fornecedor_id: number;
  preco_unitario: number;
  quantidade: number;
}

export interface CotacaoDetalhe {
  cotacao: CotacaoLista;
  itens: ItemCotacao[];
  fornecedores: CotacaoFornecedor[];
  precos: Preco[];
  vencedores: Vencedor[];
}

// ------------------------------------------------------------------
// Compras / pedidos / convites
// ------------------------------------------------------------------

export interface Invite {
  fornecedor_id: number;
  nome: string;
  whatsapp: string | null;
  email: string | null;
  representante: string | null;
  status?: string;
  token: string;
  link: string;
  whatsapp_url: string;
  mailto_url: string;
}

export interface Pedido {
  id: number;
  numero: string;
  cotacao_id: number;
  fornecedor_id: number;
  fornecedor: string;
  fornecedor_nome?: string;
  whatsapp?: string | null;
  email?: string | null;
  status?: string;
  observacoes?: string | null;
  criado_em?: string;
  cotacao_numero?: number | string;
  cotacao_titulo?: string | null;
  n_itens?: number;
  total?: number;
  itens?: PedidoItem[];
}

export interface PedidoItem {
  id: number;
  cotacao_id: number;
  cotacao_item_id: number;
  fornecedor_id: number;
  preco_unitario: number;
  quantidade: number;
  produto_id?: number;
  name?: string;
  sku?: string;
  brand?: string;
  imagem_url?: string | null;
}

// Matriz de comparação (fluxo de compra em tela única).
export interface MatrizPreco {
  preco: number;
  desconto: number;
  prazo: number | null;
  preco_liquido: number;
  disponivel: boolean;
}

export interface MatrizItem {
  cotacao_item_id: number;
  produto_id: number;
  quantidade: number;
  name: string;
  sku: string;
  brand: string;
  imagem_url: string | null;
  precos: Record<string, MatrizPreco>;
  melhor_id: number | null;
  melhor_preco: number | null;
  melhor_prazo_id: number | null;
  melhor_prazo: number | null;
}

export interface MatrizCentral {
  fornecedor_id: number;
  nome: string;
  total: number;
  n_itens: number;
}

export interface MatrizComparacao {
  cotacao: CotacaoLista;
  logica: string;
  itens: MatrizItem[];
  fornecedores: CotacaoFornecedor[];
  centralizado: MatrizCentral | null;
}

// Payload de criação da cotação do fluxo de compra.
export interface CotacaoComprasItem {
  produto_id: number;
  quantidade: number;
}

export interface CotacaoComprasFornecedorVinculado {
  fornecedor_id: number;
}

export interface CotacaoComprasFornecedorExpress {
  nome: string;
  whatsapp?: string;
  email?: string;
}

export interface CotacaoComprasPayload {
  apelido: string;
  comprador: string;
  data_limite: string;
  itens: CotacaoComprasItem[];
  fornecedores: (CotacaoComprasFornecedorVinculado | CotacaoComprasFornecedorExpress)[];
}

// ------------------------------------------------------------------
// Histórico
// ------------------------------------------------------------------

export interface HistoricoPreco {
  fornecedor_id: number;
  fornecedor_nome: string;
  cotacao_id: number;
  cotacao_numero: number;
  preco_unitario: number;
  prazo_entrega_dias: number | null;
  registrado_em: string;
  validade_preco_em: string | null;
}

export interface ProdutoComHistorico {
  id: number;
  sku: string;
  name: string;
}

// ------------------------------------------------------------------
// IA importer
// ------------------------------------------------------------------

export interface IAItem {
  produto_fornecedor?: string;
  preco_extraido?: number | null;
}

export interface IACandidato {
  produto_catalogo_id: number | null;
  produto_catalogo_nome: string;
  score: number;
}

export interface IAMatchItem {
  produto_fornecedor?: string;
  preco_extraido?: number | null;
  candidatos?: IACandidato[];
}

export interface IAExtrairResult {
  items?: IAItem[];
}

export interface IAMatchResult {
  items?: IAMatchItem[];
}

export interface IASeedResult {
  enviados?: number;
  populados?: number;
  total_catalogo?: number;
  cap?: number;
  troncado?: boolean;
  colecao?: string | null;
}

export interface IAAplicarResult {
  aplicados?: number;
  ignorados?: { produto_fornecedor?: string; motivo?: string }[];
}

// ------------------------------------------------------------------
// Cadastro de produtos (ERP: famílias, produto pai, variações, imagens)
// ------------------------------------------------------------------

export interface ItemListaCadastro {
  id: number;
  nome: string;
  marca: string;
  familia_id: number | null;
  familia_nome: string | null;
  categoria: string;
  subcategoria: string;
  variant_count: number;
  price_min: number | null;
  price_max: number | null;
  imagem_url: string | null;
  classe_abc: string | null;
  em_linha: number;
  criado_em: string;
  atualizado_em: string | null;
}

export interface ListaCadastro {
  items: ItemListaCadastro[];
  total: number;
  offset: number;
  limit: number;
}

export interface FamiliaAtributo {
  id: number;
  nome: string;
  tipo: "lista" | "livre";
  opcoes: string[];
  obrigatorio: number | boolean;
}

export interface Familia {
  id: number;
  nome: string;
  descricao: string;
  ativo: number;
  criado_em: string;
  ncm_padrao?: string;
  unidade_padrao?: string;
  atributos: FamiliaAtributo[];
}

export interface FamiliaAtributoPayload {
  id?: number | null;
  nome: string;
  tipo: string;
  opcoes: string[];
  obrigatorio: boolean;
}

export interface FamiliaPayload {
  nome: string;
  descricao: string;
  ncm_padrao?: string;
  unidade_padrao?: string;
  atributos: FamiliaAtributoPayload[];
}

export interface ImagemProduto {
  id: number;
  produto_id: number;
  variante_id: number | null;
  url: string;
  url_origem?: string;
  ordem: number;
}

export interface VarianteCadastro {
  id: number;
  produto_id: number;
  sku: string;
  ean: string;
  preco: number;
  preco_promocional: number | null;
  old_price?: number | null;
  pix_price?: number | null;
  installment?: string;
  url?: string;
  marca?: string;
  observacao: string;
  ativo: number;
  criado_em: string;
  peso?: number | null;
  dimensoes?: string;
  unidade_venda?: string;
  embalagem?: number | null;
  fator_conversao?: number | null;
  localizacao?: string;
  ncm?: string;
  unidade_tributavel?: string;
  atributos: Record<string, string>;
  atributos_nomes?: Record<string, string>;
}

export interface FornecedorVariante {
  variante_id: number;
  fornecedor_id: number;
  codigo_fornecedor: string;
  descricao_fornecedor: string;
  unidade_compra: string;
  fator_conversao: number | null;
  fornecedor_nome: string;
  sku: string;
}

export interface ProdutoCadastro {
  id: number;
  familia_id: number;
  familia_nome: string;
  nome: string;
  marca: string;
  descricao: string;
  categoria: string;
  subcategoria: string;
  termos_busca: string;
  external_id: string | null;
  criado_em: string;
  atualizado_em: string | null;
  atributos: FamiliaAtributo[];
  variantes: VarianteCadastro[];
  imagens: ImagemProduto[];
  fornecedor_variantes: FornecedorVariante[];
  linha_produto?: string;
  classe_abc?: string | null;
  margem_lucro_estimada?: number | null;
  giro_esperado_mercado?: number | null;
  valor_agregado?: string | null;
  lucro_total_estimado?: number | null;
  em_linha?: number | null;
}

export interface VarianteCadastroPayload {
  id?: number | null;
  sku: string;
  ean: string;
  preco: number;
  preco_promocional: number | null;
  observacao: string;
  peso?: number | null;
  dimensoes?: string;
  unidade_venda?: string;
  embalagem?: number | null;
  fator_conversao?: number | null;
  localizacao?: string;
  ncm?: string;
  unidade_tributavel?: string;
  atributos: Record<string, unknown>;
}

export interface ProdutoCadastroPayload {
  familia_id: number;
  nome: string;
  marca: string;
  descricao: string;
  termos_busca: string;
  categoria: string;
  subcategoria: string;
  external_id?: string | null;
  variantes: VarianteCadastroPayload[];
}

export interface FornecedorVariantePayload {
  variante_id: number;
  codigo_fornecedor: string;
  descricao_fornecedor: string;
  unidade_compra: string;
  fator_conversao: number;
}

export interface ProdutoPreview {
  url: string;
  nome: string;
  sku: string;
  ean: string;
  marca: string;
  cor?: string;
  preco?: number | null;
  preco_de?: number | null;
  preco_pix?: number | null;
  parcelamento?: string;
  fotos: number;
  family_key?: string | null;
  familia_nome: string;
  base?: string;
  atributos?: { label: string; valor: string }[];
}

export interface CriarProdutoUrlResult {
  id: number;
  variante_id: number;
  nome: string;
  marca: string;
  familia: string;
  family_key?: string | null;
  imagens_baixadas: number;
  imagens_erros: number;
}

// ------------------------------------------------------------------
// transporte
// ------------------------------------------------------------------

async function request<T>(method: Metodo, path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = { method, headers: {} };
  let url = path;
  if (body !== undefined) {
    if (method === "GET") {
      const params = new URLSearchParams();
      for (const [k, v] of Object.entries(body as Record<string, unknown>)) {
        if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
      }
      const qs = params.toString();
      if (qs) url += "?" + qs;
    } else {
      opts.headers = { "Content-Type": "application/json" };
      opts.body = JSON.stringify(body);
    }
  }
  const res = await fetch(url, opts);
  if (!res.ok) {
    let detail = res.statusText;
    let code: string | undefined;
    try {
      const j = await res.json();
      detail = j.error || detail;
      code = j.code;
    } catch {
      /* resposta não-JSON */
    }
    const err = new Error(detail) as Error & { code?: string };
    if (code) err.code = code;
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

async function enviarArquivo<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(path, { method: "POST", body: formData });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.error || detail;
    } catch {
      /* resposta não-JSON */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

function qs(params: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  }
  return parts.length ? "?" + parts.join("&") : "";
}

// ------------------------------------------------------------------
// API pública
// ------------------------------------------------------------------

export const api = {
  // catálogo
  listarProdutos: (params: Record<string, unknown> = {}) =>
    request<ListCatalogo>("GET", "/api/produtos" + qs(params)),
  resumoAbc: (params: Record<string, unknown> = {}) =>
    request<ResumoAbc>("GET", "/api/produtos/abc-resumo" + qs(params)),
  detalharProduto: (id: number) => request<ProdutoResumo>("GET", `/api/produtos/${id}`),
  listarCategorias: () => request<CategoriaMap>("GET", "/api/categorias"),

  // fornecedores
  listarFornecedores: (somenteAtivos = false) =>
    request<Fornecedor[]>("GET", "/api/fornecedores" + qs({ somente_ativos: somenteAtivos })),
  criarFornecedor: (data: FornecedorPayload) => request<{ id: number }>("POST", "/api/fornecedores", data),
  atualizarFornecedor: (id: number, data: FornecedorPayload) =>
    request<{ ok: boolean }>("PUT", `/api/fornecedores/${id}`, data),
  alternarAtivoFornecedor: (id: number, ativo: boolean) =>
    request<{ ok: boolean }>("PATCH", `/api/fornecedores/${id}/ativo` + qs({ ativo })),

  // cotações
  listarCotacoes: (status: string) =>
    request<CotacaoLista[]>("GET", "/api/cotacoes" + qs({ status })),
  criarCotacao: (data: Record<string, unknown>) =>
    request<{ id: number; numero: number }>("POST", "/api/cotacoes", data),
  detalharCotacao: (id: number) => request<CotacaoDetalhe>("GET", `/api/cotacoes/${id}`),
  atualizarCotacao: (id: number, data: Record<string, unknown>) =>
    request<{ ok: boolean }>("PATCH", `/api/cotacoes/${id}`, data),
  convidarFornecedor: (cotacaoId: number, fornecedorId: number) =>
    request<{ ok: boolean }>("POST", `/api/cotacoes/${cotacaoId}/fornecedores/${fornecedorId}`),
  removerFornecedorDaCotacao: (cotacaoId: number, fornecedorId: number) =>
    request<{ ok: boolean }>("DELETE", `/api/cotacoes/${cotacaoId}/fornecedores/${fornecedorId}`),
  adicionarItem: (cotacaoId: number, data: Record<string, unknown>) =>
    request<{ ok: boolean }>("POST", `/api/cotacoes/${cotacaoId}/itens`, data),
  removerItem: (cotacaoId: number, itemId: number) =>
    request<{ ok: boolean }>("DELETE", `/api/cotacoes/${cotacaoId}/itens/${itemId}`),
  atualizarItem: (cotacaoId: number, itemId: number, data: Record<string, unknown>) =>
    request<{ ok: boolean }>("PATCH", `/api/cotacoes/${cotacaoId}/itens/${itemId}`, data),
  registrarPreco: (cotacaoId: number, data: Record<string, unknown>) =>
    request<{ ok: boolean }>("PUT", `/api/cotacoes/${cotacaoId}/precos`, data),
  fecharCotacao: (cotacaoId: number, escolhas: unknown[]) =>
    request<{ ok: boolean }>("POST", `/api/cotacoes/${cotacaoId}/fechar`, { escolhas }),
  reabrirCotacao: (cotacaoId: number) =>
    request<{ ok: boolean }>("POST", `/api/cotacoes/${cotacaoId}/reabrir`),

  // compras
  criarCotacaoCompras: (data: CotacaoComprasPayload) =>
    request<{ id: number; numero: string; invites: Invite[] }>("POST", "/api/compras/cotacoes", data),
  convitesCotacao: (id: number) => request<Invite[]>("GET", `/api/compras/cotacoes/${id}/invites`),
  compararCotacao: (id: number) => request<MatrizComparacao>("GET", `/api/compras/cotacoes/${id}/comparar`),
  gerarPedidos: (id: number, logica: string) =>
    request<{ pedidos: Pedido[] }>("POST", `/api/compras/cotacoes/${id}/pedidos`, { logica }),
  listarPedidos: () => request<Pedido[]>("GET", "/api/compras/pedidos"),
  receberPedido: (id: number, data: { deposito_id?: number }) => request<{ ok: boolean; total: number; itens: number }>("POST", `/api/compras/pedidos/${id}/receber`, data),
  detalharPedido: (id: number) => request<Pedido>("GET", `/api/compras/pedidos/${id}`),

  // histórico
  historicoPrecos: (produtoId: number) =>
    request<HistoricoPreco[]>("GET", "/api/historico-precos" + qs({ produto_id: produtoId })),
  produtosComHistorico: () => request<ProdutoComHistorico[]>("GET", "/api/historico-precos/produtos"),

  // importador IA
  iaHealth: () => request<{ ok: boolean }>("GET", "/api/ia/health"),
  iaSeed: (reset = false) => request<IASeedResult>("POST", "/api/ia/seed", { reset }),
  iaExtrairTexto: (texto: string) => request<IAExtrairResult>("POST", "/api/ia/extract", { text: texto }),
  iaExtrairPdf: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return enviarArquivo<IAExtrairResult>("/api/ia/extract/file", fd);
  },
  iaMatch: (items: unknown[], topK = 5, cotacaoId?: number) =>
    request<IAMatchResult>("POST", "/api/ia/match", { items, top_k: topK, cotacao_id: cotacaoId ?? null }),
  iaAplicar: (cotacaoId: number, data: Record<string, unknown>) =>
    request<IAAplicarResult>("POST", "/api/ia/apply", { cotacao_id: cotacaoId, ...data }),

  // cadastro de produtos (ERP)
  listarFamilias: () => request<Familia[]>("GET", "/api/familias"),
  criarFamilia: (payload: FamiliaPayload) => request<{ id: number }>("POST", "/api/familias", payload),
  atualizarFamilia: (id: number, payload: FamiliaPayload) =>
    request<{ ok: boolean }>("PUT", `/api/familias/${id}`, payload),
  excluirFamilia: (id: number) => request<{ ok: boolean }>("DELETE", `/api/familias/${id}`),
  listarProdutosCadastro: (params: Record<string, unknown> = {}) =>
    request<ListaCadastro>("GET", "/api/produtos-cadastro" + qs(params)),
  detalharProdutoCadastro: (id: number) =>
    request<ProdutoCadastro>("GET", `/api/produtos-cadastro/${id}`),
  criarProdutoCadastro: (payload: ProdutoCadastroPayload) =>
    request<{ id: number }>("POST", "/api/produtos-cadastro", payload),
  atualizarProdutoCadastro: (id: number, payload: ProdutoCadastroPayload) =>
    request<{ ok: boolean; variantes: { excluidas: number; desativadas: number } }>("PUT", `/api/produtos-cadastro/${id}`, payload),
  excluirProdutoCadastro: (id: number) =>
    request<{ ok: boolean; excluidas: number; desativadas: number }>("DELETE", `/api/produtos-cadastro/${id}`),
  parseUrlProduto: (url: string) =>
    request<ProdutoPreview>("POST", "/api/produtos-cadastro/parse-url", { url }),
  criarProdutoPorUrl: (url: string) =>
    request<CriarProdutoUrlResult>("POST", "/api/produtos-cadastro/from-url", { url }),
  enviarImagensProduto: (produtoId: number, formData: FormData) =>
    enviarArquivo<{ imagens: string[] }>(`/api/produtos-cadastro/${produtoId}/imagens`, formData),
  baixarImagensUrl: (produtoId: number, url: string) =>
    request<{ baixadas: string[]; total: number; erros: string[] }>(
      "POST",
      `/api/produtos-cadastro/${produtoId}/imagens-url`,
      { url }
    ),
  excluirImagem: (imagemId: number) =>
    request<{ ok: boolean }>("DELETE", `/api/imagens/${imagemId}`),
  definirCapaImagem: (produtoId: number, imagemId: number) =>
    request<{ ok: boolean }>("POST", `/api/produtos-cadastro/${produtoId}/imagens/capa`, {
      imagem_id: imagemId,
    }),
  salvarFornecedorVariantes: (
    produtoId: number,
    fornecedorId: number,
    itens: FornecedorVariantePayload[]
  ) =>
    request<{ ok: boolean; mapping: FornecedorVariante[] }>(
      "PUT",
      `/api/produtos-cadastro/${produtoId}/fornecedor-variantes`,
      { fornecedor_id: fornecedorId, itens }
    ),

  // Categorias
  request: <T>(method: Metodo, path: string, body?: unknown) =>
    request<T>(method, path, body),
  listarCategoriasTree: () => request<CategoriaTree[]>("GET", "/api/categorias-tree"),
  criarCategoria: (nome: string) => request<{ id: number }>("POST", "/api/categorias", { nome }),
  atualizarCategoria: (id: number, nome: string) => request("PUT", `/api/categorias/${id}`, { nome }),
  excluirCategoria: (id: number) => request("DELETE", `/api/categorias/${id}`),
  criarSubcategoria: (catId: number, nome: string) =>
    request<{ id: number }>("POST", `/api/categorias/${catId}/subcategorias`, { nome }),
  atualizarSubcategoria: (id: number, nome: string) => request("PUT", `/api/subcategorias/${id}`, { nome }),
  excluirSubcategoria: (id: number) => request("DELETE", `/api/subcategorias/${id}`),
  listarProdutosSubcategoria: (subId: number, offset = 0, limit = 60) =>
    request<ListaProdutosSubcategoria>("GET", `/api/subcategorias/${subId}/produtos` + qs({ offset, limit })),
  reclassificarProdutos: (produtoIds: number[], categoria: string, subcategoria: string) =>
    request<{ ok: boolean; count: number }>("POST", "/api/produtos/reclassificar", {
      produto_ids: produtoIds,
      categoria,
      subcategoria,
    }),

  // Unidades de compra
  listarUnidadesCompra: (apenasAtivas = false) =>
    request<UnidadeCompra[]>("GET", "/api/unidades-compra" + qs({ ativas: apenasAtivas })),
  criarUnidadeCompra: (sigla: string, descricao: string) =>
    request<{ id: number }>("POST", "/api/unidades-compra", { sigla, descricao }),
  atualizarUnidadeCompra: (id: number, sigla: string, descricao: string, ativo: boolean) =>
    request("PUT", `/api/unidades-compra/${id}`, { sigla, descricao, ativo }),
  excluirUnidadeCompra: (id: number) => request("DELETE", `/api/unidades-compra/${id}`),

  // base do ERP — clientes, vendedores, usuários e plano de contas
  listarClientes: (somenteAtivos = false, vendedorId?: number) =>
    request<Cliente[]>("GET", "/api/clientes" + qs({ somente_ativos: somenteAtivos, vendedor_id: vendedorId })),
  buscarClientes: (q: string) =>
    request<Cliente[]>("GET", "/api/clientes/buscar" + qs({ q })),
  detalharCliente: (id: number) => request<Cliente>("GET", `/api/clientes/${id}`),
  criarCliente: (data: ClientePayload) => request<{ id: number }>("POST", "/api/clientes", data),
  atualizarCliente: (id: number, data: ClientePayload) =>
    request<{ ok: boolean }>("PUT", `/api/clientes/${id}`, data),
  alternarAtivoCliente: (id: number, ativo: boolean) =>
    request<{ ok: boolean }>("PATCH", `/api/clientes/${id}/ativo` + qs({ ativo })),
  contextoCliente: () => request<{ vendedores: Vendedor[] }>("GET", "/api/clientes/contexto"),
  listarEnderecosCliente: (id: number) => request<ClienteEndereco[]>("GET", `/api/clientes/${id}/enderecos`),
  criarEnderecoCliente: (id: number, data: { tipo: string; cep?: string; logradouro?: string; numero?: string; complemento?: string; bairro?: string; cidade?: string; uf?: string }) =>
    request<{ id: number }>("POST", `/api/clientes/${id}/enderecos`, data),
  excluirEnderecoCliente: (enderecoId: number) => request<{ ok: boolean }>("DELETE", `/api/clientes/enderecos/${enderecoId}`),
  listarContatosCliente: (id: number) => request<ClienteContato[]>("GET", `/api/clientes/${id}/contatos`),
  criarContatoCliente: (id: number, data: { nome: string; cargo?: string; telefone?: string; email?: string }) =>
    request<{ id: number }>("POST", `/api/clientes/${id}/contatos`, data),
  excluirContatoCliente: (contatoId: number) => request<{ ok: boolean }>("DELETE", `/api/clientes/contatos/${contatoId}`),
  getApoioComercial: (id: number) => request<ClienteApoioComercial>("GET", `/api/clientes/${id}/apoio-comercial`),
  upsertApoioComercial: (id: number, data: Record<string, unknown>) =>
    request<{ ok: boolean }>("PUT", `/api/clientes/${id}/apoio-comercial`, data),
  getApoioFiscal: (id: number) => request<ClienteApoioFiscal>("GET", `/api/clientes/${id}/apoio-fiscal`),
  upsertApoioFiscal: (id: number, data: Record<string, unknown>) =>
    request<{ ok: boolean }>("PUT", `/api/clientes/${id}/apoio-fiscal`, data),
  listarVendedores: (somenteAtivos = false) =>
    request<Vendedor[]>("GET", "/api/vendedores" + qs({ somente_ativos: somenteAtivos })),
  detalharVendedor: (id: number) => request<Vendedor>("GET", `/api/vendedores/${id}`),
  criarVendedor: (data: VendedorPayload) => request<{ id: number }>("POST", "/api/vendedores", data),
  atualizarVendedor: (id: number, data: VendedorPayload) =>
    request<{ ok: boolean }>("PUT", `/api/vendedores/${id}`, data),
  alternarAtivoVendedor: (id: number, ativo: boolean) =>
    request<{ ok: boolean }>("PATCH", `/api/vendedores/${id}/ativo` + qs({ ativo })),
  listarUsuarios: (somenteAtivos = false) =>
    request<Usuario[]>("GET", "/api/usuarios" + qs({ somente_ativos: somenteAtivos })),
  criarUsuario: (data: UsuarioPayload) => request<{ id: number }>("POST", "/api/usuarios", data),
  atualizarUsuario: (id: number, data: UsuarioPayload) =>
    request<{ ok: boolean }>("PUT", `/api/usuarios/${id}`, data),
  alternarAtivoUsuario: (id: number, ativo: boolean) =>
    request<{ ok: boolean }>("PATCH", `/api/usuarios/${id}/ativo` + qs({ ativo })),
  usuarioAtual: () => request<UsuarioAtual>("GET", "/api/usuarios/atual"),
  usuariosVazio: () => request<{ vazio: boolean }>("GET", "/api/primeiro-usuario"),
  login: (login: string, senha: string) =>
    request<UsuarioAtual>("POST", "/api/login", { login, senha }),
  logout: () => request<{ ok: boolean }>("POST", "/api/logout"),
  listarPlanoContas: (tipo?: string, somenteAtivos = false) =>
    request<ContaPlano[]>("GET", "/api/plano-contas" + qs({ tipo, somente_ativos: somenteAtivos })),
  detalharContaPlano: (id: number) => request<ContaPlano>("GET", `/api/plano-contas/${id}`),
  criarContaPlano: (data: ContaPlanoPayload) => request<{ id: number }>("POST", "/api/plano-contas", data),
  atualizarContaPlano: (id: number, data: ContaPlanoPayload) =>
    request<{ ok: boolean }>("PUT", `/api/plano-contas/${id}`, data),
  alternarAtivoContaPlano: (id: number, ativo: boolean) =>
    request<{ ok: boolean }>("PATCH", `/api/plano-contas/${id}/ativo` + qs({ ativo })),

  // orçamentos de venda (PDV)
  listarOrcamentos: (status = "", somente_meus = false) =>
    request<OrcamentoLista[]>("GET", "/api/orcamentos" + qs({ status, somente_meus: somente_meus ? "1" : undefined })),
  criarOrcamento: (payload: OrcamentoPayload) =>
    request<{ id: number; numero: string }>("POST", "/api/orcamentos", payload),
  detalharOrcamento: (id: number) =>
    request<OrcamentoDetalhe>("GET", `/api/orcamentos/${id}`),
  atualizarOrcamento: (id: number, data: Record<string, unknown>) =>
    request<{ ok: boolean }>("PATCH", `/api/orcamentos/${id}`, data),
  substituirItensOrcamento: (id: number, itens: OrcamentoItemPayload[]) =>
    request<{ ok: boolean }>("PUT", `/api/orcamentos/${id}/itens`, { itens }),
  excluirOrcamento: (id: number) => request<{ ok: boolean }>("DELETE", `/api/orcamentos/${id}`),
  autorizarDescontoOrcamento: (id: number, creds: { login: string; senha: string }) =>
    request<{ ok: boolean; autorizado_por?: string; ja_autorizado?: boolean }>(
      "POST",
      `/api/orcamentos/${id}/autorizar-desconto`,
      creds
    ),

  // retaguarda de impressão (PDV → ESC/POS direto à impressora)
  imprimirOrcamento: (id: number) =>
    request<{ ok: boolean; job_id: number; numero: string }>("POST", `/api/impressao/orcamentos/${id}`),
  imprimirTeste: () => request<{ ok: boolean; job_id: number }>("POST", "/api/impressao/teste"),
  getConfigImpressao: () => request<ConfigImpressao>("GET", "/api/impressao/config"),
  setConfigImpressao: (cfg: Partial<ConfigImpressao>) =>
    request<ConfigImpressao>("PUT", "/api/impressao/config", cfg),
  filaImpressao: () => request<JobImpressao[]>("GET", "/api/impressao/fila"),

  // estoque
  listarDepositos: (somenteAtivos = false) =>
    request<Deposito[]>("GET", "/api/depositos" + qs({ somente_ativos: somenteAtivos })),
  detalharDeposito: (id: number) => request<Deposito>("GET", `/api/depositos/${id}`),
  criarDeposito: (nome: string) => request<{ id: number }>("POST", "/api/depositos", { nome }),
  atualizarDeposito: (id: number, nome: string) =>
    request<{ ok: boolean }>("PUT", `/api/depositos/${id}`, { nome }),
  alternarAtivoDeposito: (id: number, ativo: boolean) =>
    request<{ ok: boolean }>("PATCH", `/api/depositos/${id}/ativo` + qs({ ativo })),
  saldoEstoque: (params: Record<string, unknown> = {}) =>
    request<SaldoItem[]>("GET", "/api/estoque/saldo" + qs(params)),
  registrarMovimento: (data: MovimentoPayload) =>
    request<MovimentoResult>("POST", "/api/estoque/movimento", data),
  listarMovimentos: (params: Record<string, unknown> = {}) =>
    request<MovimentoItem[]>("GET", "/api/estoque/movimento" + qs(params)),
  transferirEstoque: (data: TransferenciaPayload) =>
    request<{ ok: boolean }>("POST", "/api/estoque/transferir", data),
  listarLotes: (params: Record<string, unknown> = {}) =>
    request<LoteItem[]>("GET", "/api/estoque/lotes" + qs(params)),
  detalharLote: (id: number) => request<LoteItem>("GET", `/api/estoque/lotes/${id}`),
  criarLote: (data: LotePayload) => request<{ id: number }>("POST", "/api/estoque/lotes", data),
  listarExpedicao: (params: Record<string, unknown> = {}) =>
    request<Expedicao[]>("GET", "/api/expedicao" + qs(params)),
  criarExpedicao: (data: { codigo: string; deposito_id: number; transportadora?: string; observacao?: string }) =>
    request<{ id: number }>("POST", "/api/expedicao", data),
  atualizarStatusExpedicao: (id: number, status: string) =>
    request<{ ok: boolean }>("POST", `/api/expedicao/${id}/status`, { status }),

  // preços
  listarTabelasPreco: (somenteAtivos = false) =>
    request<TabelaPreco[]>("GET", "/api/tabelas-preco" + qs({ somente_ativos: somenteAtivos })),
  detalharTabelaPreco: (id: number) => request<TabelaPreco>("GET", `/api/tabelas-preco/${id}`),
  criarTabelaPreco: (data: TabelaPrecoPayload) =>
    request<{ id: number }>("POST", "/api/tabelas-preco", data),
  atualizarTabelaPreco: (id: number, data: TabelaPrecoPayload) =>
    request<{ ok: boolean }>("PUT", `/api/tabelas-preco/${id}`, data),
  alternarAtivoTabelaPreco: (id: number, ativo: boolean) =>
    request<{ ok: boolean }>("PATCH", `/api/tabelas-preco/${id}/ativo` + qs({ ativo })),
  listarItensTabela: (id: number, q?: string) =>
    request<TabelaPrecoItem[]>("GET", `/api/tabelas-preco/${id}/itens` + qs({ q: q || "" })),
  upsertItemTabela: (id: number, data: TabelaPrecoItemPayload) =>
    request<{ ok: boolean }>("POST", `/api/tabelas-preco/${id}/itens`, data),
  deletarItemTabela: (id: number, varianteId: number) =>
    request<{ ok: boolean }>("DELETE", `/api/tabelas-preco/${id}/itens` + qs({ variante_id: varianteId })),
  gerarPrecosTabela: (id: number, data?: Record<string, unknown>) =>
    request<{ gerados: number }>("POST", `/api/tabelas-preco/${id}/gerar`, data || {}),
  calcularPreco: (varianteId: number, params: Record<string, unknown> = {}) =>
    request<CalculoPreco>("GET", `/api/precos/calcular/${varianteId}` + qs(params)),
  precoEfetivo: (varianteId: number, canal?: string) =>
    request<{ preco: number; origem: string; canal: string }>("GET", `/api/precos/efetivo/${varianteId}` + qs({ canal: canal || "" })),
  previaReajusteTabela: (id: number, data: Record<string, unknown> = {}) =>
    request<PreviaReajuste>("POST", `/api/tabelas-preco/${id}/previa`, data),
  reajustarTabela: (id: number, data: Record<string, unknown>) =>
    request<ReajusteResultado>("POST", `/api/tabelas-preco/${id}/reajustar`, data),
  listarHistoricoPrecos: (params: Record<string, unknown> = {}) =>
    request<HistoricoPrecoItem[]>("GET", "/api/precos/historico" + qs(params)),
  margemVendas: (params: Record<string, unknown> = {}) =>
    request<MargemVenda[]>("GET", "/api/relatorios/margem-vendas" + qs(params)),
  requestDashboard: () => request<DashboardData>("GET", "/api/dashboard"),
  // loja (PDV/estoque/compras/pós-venda)
  lojaConfig: () => request<{ bloquear_venda_sem_estoque: boolean }>("GET", "/api/loja/config"),
  setLojaConfig: (data: Record<string, unknown>) => request<{ bloquear_venda_sem_estoque: boolean }>("PUT", "/api/loja/config", data),
  lojaSaldo: (varianteId: number) => request<{ saldos: unknown[]; disponivel: number }>("GET", `/api/loja/saldo/${varianteId}`),
  listarInventarios: () => request<unknown[]>("GET", "/api/loja/inventarios"),
  criarInventario: (data: Record<string, unknown>) => request<{ id: number }>("POST", "/api/loja/inventarios", data),
  itensInventario: (id: number) => request<unknown[]>("GET", `/api/loja/inventarios/${id}/itens`),
  contarInventario: (invId: number, itemId: number, quantidade: number) =>
    request<{ ok: boolean }>("PATCH", `/api/loja/inventarios/${invId}/itens/${itemId}`, { quantidade_contada: quantidade }),
  finalizarInventario: (id: number) => request<{ ajustados: number; itens: number }>("POST", `/api/loja/inventarios/${id}/finalizar`),
  reposicaoSugerida: () => request<unknown[]>("GET", "/api/loja/reposicao"),
  listarDevolucoes: () => request<unknown[]>("GET", "/api/loja/devolucoes"),
  registrarDevolucao: (data: Record<string, unknown>) => request<{ id: number }>("POST", "/api/loja/devolucoes", data),
  alterarStatusDevolucao: (id: number, status: string) =>
    request<{ ok: boolean }>("PATCH", `/api/loja/devolucoes/${id}`, { status }),
  comissoes: (params: Record<string, unknown> = {}) => request<unknown[]>("GET", "/api/loja/comissoes" + qs(params)),
  listarPromocoes: (ativo?: boolean) =>
    request<Promocao[]>("GET", "/api/promocoes" + qs({ ativo: ativo !== undefined ? String(ativo) : "" })),
  detalharPromocao: (id: number) => request<Promocao>("GET", `/api/promocoes/${id}`),
  criarPromocao: (data: PromocaoPayload) => request<{ id: number }>("POST", "/api/promocoes", data),
  atualizarPromocao: (id: number, data: PromocaoPayload) =>
    request<{ ok: boolean }>("PUT", `/api/promocoes/${id}`, data),
  listarItensPromocao: (id: number, q?: string) =>
    request<PromocaoItem[]>("GET", `/api/promocoes/${id}/itens` + qs({ q: q || "" })),
  upsertItemPromocao: (id: number, data: PromocaoItemPayload) =>
    request<{ ok: boolean }>("POST", `/api/promocoes/${id}/itens`, data),
  aplicarPromocao: (id: number, varianteIds: number[]) =>
    request<{ aplicados: number }>("POST", `/api/promocoes/${id}/aplicar`, { variante_ids: varianteIds }),
  deletarItemPromocao: (id: number, varianteId: number) =>
    request<{ ok: boolean }>("DELETE", `/api/promocoes/${id}/itens` + qs({ variante_id: varianteId })),
  listarRevisoesPreco: (tabelaId?: number) =>
    request<RevisaoPreco[]>("GET", "/api/revisoes-preco" + qs({ tabela_id: tabelaId || "" })),
  criarRevisaoPreco: (data: { tabela_id: number; codigo: string; descricao?: string; data_validade?: string; cliente_id?: number }) =>
    request<{ id: number }>("POST", "/api/revisoes-preco", data),
  fecharRevisaoPreco: (id: number) => request<{ ok: boolean }>("POST", `/api/revisoes-preco/${id}/fechar`),
  listarItensTabelaMargem: (id: number, q?: string) =>
    request<TabelaPrecoItemMargem[]>("GET", `/api/tabelas-preco/${id}/itens-margem` + qs({ q: q || "" })),

  // financeiro
  saldoCaixa: () => request<{ saldo: number }>("GET", "/api/financeiro/caixa/saldo"),
  listarMovimentosCaixa: (params: Record<string, unknown> = {}) =>
    request<CaixaMovimento[]>("GET", "/api/financeiro/caixa/movimentos" + qs(params)),
  movimentarCaixa: (data: CaixaMovimentoPayload) =>
    request<{ id: number; saldo_anterior: number; saldo_posterior: number }>("POST", "/api/financeiro/caixa/movimento", data),
  listarReceber: (params: Record<string, unknown> = {}) =>
    request<ContaReceber[]>("GET", "/api/financeiro/receber" + qs(params)),
  criarReceber: (data: ContaPayload) => request<{ id: number }>("POST", "/api/financeiro/receber", data),
  receberConta: (id: number, data: { valor: number; data_recebimento?: string }) =>
    request<{ saldo_anterior: number; saldo_posterior: number; status: string }>("POST", `/api/financeiro/receber/${id}/receber`, data),
  listarPagar: (params: Record<string, unknown> = {}) =>
    request<ContaPagar[]>("GET", "/api/financeiro/pagar" + qs(params)),
  criarPagar: (data: ContaPayload) => request<{ id: number }>("POST", "/api/financeiro/pagar", data),
  pagarConta: (id: number, data: { valor: number; data_pagamento?: string }) =>
    request<{ saldo_anterior: number; saldo_posterior: number; status: string }>("POST", `/api/financeiro/pagar/${id}/pagar`, data),

  // fiscal
  listarCfop: (tipo?: string) =>
    request<CfopCode[]>("GET", "/api/fiscal/cfop" + qs({ tipo: tipo || "" })),
  listarCst: (tabela: string) =>
    request<CstCode[]>("GET", `/api/fiscal/cst/${tabela}`),
  listarFiscalConfig: (params: Record<string, unknown> = {}) =>
    request<FiscalConfigItem[]>("GET", "/api/fiscal/config" + qs(params)),
  getFiscalConfig: (varianteId: number) =>
    request<FiscalConfigItem>("GET", `/api/fiscal/config/${varianteId}`),
  upsertFiscalConfig: (varianteId: number, data: FiscalConfigPayload) =>
    request<{ ok: boolean }>("PUT", `/api/fiscal/config/${varianteId}`, data),
  gerarFiscalConfig: (cfop?: string, cst?: string) =>
    request<{ gerados: number }>("POST", "/api/fiscal/config/gerar", { cfop: cfop || "5.102", cst_icms: cst || "00" }),
  listarCest: (ncm?: string) =>
    request<CestItem[]>("GET", "/api/fiscal/cest" + qs({ ncm: ncm || "" })),
  listarCsosn: () => request<CsosnItem[]>("GET", "/api/fiscal/csosn"),
  listarBeneficiosFiscais: () => request<BeneficioFiscalItem[]>("GET", "/api/fiscal/beneficios"),
  listarHistoricoFiscal: (params: Record<string, unknown> = {}) =>
    request<HistoricoFiscalItem[]>("GET", "/api/fiscal/historico" + qs(params)),
  simularFiscal: (data: Record<string, unknown>) =>
    request<FiscalSimulacao>("POST", "/api/fiscal/simular", data),
  getEmitente: () => request<Emitente>("GET", "/api/emitente"),
  upsertEmitente: (data: Record<string, unknown>) => request<{ id: number }>("PUT", "/api/emitente", data),
  listarNfeSaida: (status?: string) =>
    request<NfeSaida[]>("GET", "/api/nfe-saida" + qs({ status: status || "" })),
  listarNfeEntrada: () => request<NfeEntrada[]>("GET", "/api/nfe-entrada"),
  relVendasPeriodo: (inicio: string, fim: string) =>
    request<RelVenda[]>("GET", "/api/relatorios/vendas-periodo" + qs({ inicio, fim })),
  relAgingReceber: () => request<RelAging[]>("GET", "/api/relatorios/aging-receber"),
  relAgingPagar: () => request<RelAging[]>("GET", "/api/relatorios/aging-pagar"),
  relDre: (inicio: string, fim: string) =>
    request<RelDre[]>("GET", "/api/relatorios/dre" + qs({ inicio, fim })),

  // bancos
  listarContasBancarias: (somenteAtivas = false) =>
    request<ContaBancaria[]>("GET", "/api/bancos/contas" + qs({ somente_ativos: somenteAtivas })),
  detalharContaBancaria: (id: number) => request<ContaBancaria>("GET", `/api/bancos/contas/${id}`),
  criarContaBancaria: (data: ContaBancariaPayload) =>
    request<{ id: number }>("POST", "/api/bancos/contas", data),
  atualizarContaBancaria: (id: number, data: ContaBancariaPayload) =>
    request<{ ok: boolean }>("PUT", `/api/bancos/contas/${id}`, data),
  alternarAtivoContaBancaria: (id: number, ativo: boolean) =>
    request<{ ok: boolean }>("PATCH", `/api/bancos/contas/${id}/ativo` + qs({ ativo })),
  listarMovimentosBancarios: (params: Record<string, unknown> = {}) =>
    request<MovimentoBancario[]>("GET", "/api/bancos/movimentos" + qs(params)),
  criarMovimentoBancario: (data: MovimentoBancarioPayload) =>
    request<{ id: number; saldo_atual: number }>("POST", "/api/bancos/movimentos", data),
  toggleConciliado: (movId: number) =>
    request<{ ok: boolean }>("POST", `/api/bancos/movimentos/${movId}/conciliar`),

  // condições de pagamento
  listarCondicoes: () => request<CondicaoPagamento[]>("GET", "/api/condicoes-pagamento"),
  getCondicao: (id: number) => request<CondicaoPagamento>("GET", `/api/condicoes-pagamento/${id}`),
  criarCondicao: (data: { nome: string; descricao?: string }) => request<{ id: number }>("POST", "/api/condicoes-pagamento", data),
  atualizarCondicao: (id: number, data: { nome: string; descricao?: string }) => request<{ ok: boolean }>("PUT", `/api/condicoes-pagamento/${id}`, data),
  salvarParcelas: (id: number, parcelas: { sequencia: number; dias: number; percentual: number }[]) =>
    request<{ ok: boolean }>("PUT", `/api/condicoes-pagamento/${id}/parcelas`, { parcelas }),
  listarCentrosCusto: () => request<CentroCusto[]>("GET", "/api/centros-custo"),
  criarCentroCusto: (data: { codigo: string; nome: string }) => request<{ id: number }>("POST", "/api/centros-custo", data),
  listarAdiantamentos: (tipo?: string) =>
    request<Adiantamento[]>("GET", "/api/adiantamentos" + qs({ tipo: tipo || "" })),
  criarAdiantamento: (data: { tipo: string; pessoa_nome: string; valor: number; data_adiantamento: string; pessoa_id?: number; observacao?: string }) =>
    request<{ id: number }>("POST", "/api/adiantamentos", data),
  baixarAdiantamento: (id: number, data: { valor: number; data_baixa: string }) =>
    request<{ saldo_anterior: number; saldo_posterior: number }>("POST", `/api/adiantamentos/${id}/baixar`, data),

  // pós-venda
  listarFornecedorPreco: (params: Record<string, unknown> = {}) =>
    request<FornecedorPrecoItem[]>("GET", "/api/fornecedor-preco" + qs(params)),
  upsertFornecedorPreco: (data: { fornecedor_id: number; variante_id: number; preco: number; prazo_entrega?: number; icms?: number; ipi?: number }) =>
    request<{ id: number }>("POST", "/api/fornecedor-preco", data),
  listarSolicitacoesCompra: (status?: string) =>
    request<SolicitacaoCompra[]>("GET", "/api/solicitacoes-compra" + qs({ status: status || "" })),
  criarSolicitacaoCompra: (data: { codigo: string; descricao?: string; observacao?: string }) =>
    request<{ id: number }>("POST", "/api/solicitacoes-compra", data),
  addItemSolicitacao: (id: number, data: { variante_id: number; quantidade: number; justificativa?: string }) =>
    request<{ id: number }>("POST", `/api/solicitacoes-compra/${id}/itens`, data),
  listarFornecedorPreferencial: (varianteId?: number) =>
    request<FornecedorPrefItem[]>("GET", "/api/fornecedor-preferencial" + qs({ variante_id: varianteId || "" })),
  upsertFornecedorPreferencial: (data: { variante_id: number; fornecedor_id: number; ranking?: number; ultimo_preco?: number; ultimo_prazo?: number }) =>
    request<{ id: number }>("POST", "/api/fornecedor-preferencial", data),
  getToleranciaCompra: (fornecedorId: number) =>
    request<ToleranciaCompra>("GET", "/api/tolerancias-compra" + qs({ fornecedor_id: fornecedorId })),
  upsertToleranciaCompra: (data: { fornecedor_id: number; tolerancia_preco_pct?: number; tolerancia_qtd_pct?: number; exige_aprovacao?: boolean }) =>
    request<{ id: number }>("POST", "/api/tolerancias-compra", data),
  listarIbpt: (params: Record<string, unknown> = {}) =>
    request<IbptItem[]>("GET", "/api/ibpt" + qs(params)),
  upsertIbpt: (data: { ncm: string; descricao?: string; aliquota_federal?: number; aliquota_estadual?: number; aliquota_municipal?: number }) =>
    request<{ id: number }>("POST", "/api/ibpt", data),
  listarSugestoesIbpt: (params: Record<string, unknown> = {}) =>
    request<SugestaoIbpt[]>("GET", "/api/ibpt/sugestoes" + qs(params)),
  gerarSugestoesIbpt: (data: Record<string, unknown> = {}) =>
    request<{ sugestoes: number; confianca_min: number; total_produtos: number }>("POST", "/api/ibpt/sugestoes/gerar", data),
  aplicarSugestoesIbpt: (data: Record<string, unknown> = {}) =>
    request<{ aplicadas: number }>("POST", "/api/ibpt/sugestoes/aplicar", data),
  revisarSugestaoIbpt: (id: number, status: "aplicada" | "rejeitada") =>
    request<{ ok: boolean }>("PATCH", `/api/ibpt/sugestoes/${id}`, { status }),
  listarPoliticaDescontos: () => request<DescontoRegra[]>("GET", "/api/politica-descontos"),
  criarPoliticaDesconto: (data: { nome: string; tipo: string; valor_maximo: number; valor_minimo?: number; perfil?: string }) =>
    request<{ id: number }>("POST", "/api/politica-descontos", data),
  listarPoliticaFretes: (uf?: string) =>
    request<FreteRegra[]>("GET", "/api/politica-fretes" + qs({ uf: uf || "" })),
  criarPoliticaFrete: (data: { nome: string; uf: string; valor_frete: number; valor_minimo_pedido?: number; tipo?: string }) =>
    request<{ id: number }>("POST", "/api/politica-fretes", data),
  listarInteracoes: (params: Record<string, unknown> = {}) =>
    request<ClienteInteracao[]>("GET", "/api/posvenda/interacoes" + qs(params)),
  resumoDiagnosticoVariacoes: () => request<DiagnosticoResumo[]>("GET", "/api/catalogo/diagnostico-variacoes/resumo"),
  listarDiagnosticoVariacoes: (params: Record<string, unknown> = {}) =>
    request<DiagnosticoVariacao[]>("GET", "/api/catalogo/diagnostico-variacoes" + qs(params)),
  detalhesDiagnosticoVariacao: (id: number) =>
    request<DiagnosticoDetalhe>("GET", `/api/catalogo/diagnostico-variacoes/${id}`),
  marcarDiagnosticoRevisado: (id: number, revisado = true) =>
    request<{ ok: boolean }>("PATCH", `/api/catalogo/diagnostico-variacoes/${id}/revisado`, { revisado }),
  consolidarOfertas: (produtoId: number, principalId: number) =>
    request<{ produto_id: number; principal_id: number; desativadas: number }>("POST", `/api/catalogo/diagnostico-variacoes/${produtoId}/consolidar`, { principal_id: principalId }),
  criarInteracao: (data: InteracaoPayload) =>
    request<{ id: number }>("POST", "/api/posvenda/interacoes", data),
  listarGarantias: (params: Record<string, unknown> = {}) =>
    request<Garantia[]>("GET", "/api/posvenda/garantias" + qs(params)),
  criarGarantia: (data: GarantiaPayload) =>
    request<{ id: number }>("POST", "/api/posvenda/garantias", data),
  atualizarStatusGarantia: (id: number, status: string) =>
    request<{ ok: boolean }>("PATCH", `/api/posvenda/garantias/${id}/status`, { status }),
};

export interface CategoriaTree {
  id: number;
  nome: string;
  ativo: boolean;
  subcategorias: { id: number; nome: string; ativo: boolean; product_count: number }[];
}

export interface UnidadeCompra {
  id: number;
  sigla: string;
  descricao: string;
  ativo: boolean;
}

// ------------------------------------------------------------------
// Orçamentos de venda (PDV)
// ------------------------------------------------------------------

export type OrcamentoStatus = "rascunho" | "ativo" | "fechado" | "cancelado";

export interface OrcamentoItemPayload {
  produto_id?: number | null;
  nome: string;
  sku?: string;
  marca?: string;
  especificacao?: string;
  quantidade: number;
  preco_unitario: number;
  desconto_percentual?: number;
  subtotal?: number;
}

export interface OrcamentoLista {
  id: number;
  numero: string;
  cliente: string;
  contato: string;
  status: OrcamentoStatus;
  desconto: number;
  subtotal: number;
  total: number;
  validade_dias: number;
  criado_em: string;
  observacoes: string;
  n_itens: number;
  usuario_id?: number | null;
  desconto_autorizado?: number | boolean;
  desconto_autorizado_por?: number | null;
  desconto_autorizado_em?: string | null;
  desconto_autorizado_nome?: string | null;
  condicao_pagamento_id?: number | null;
  cliente_id?: number | null;
  cliente_doc?: string | null;
  uf_destino?: string | null;
  tipo_cliente?: string | null;
  contribuinte?: string | null;
  ie?: string | null;
}

export interface OrcamentoDetalhe extends OrcamentoLista {
  itens: OrcamentoItemPayload[];
}

export interface ConfigImpressao {
  host: string;
  porta: number;
  papel_mm: number;
  auto_impressao: number;
  ativo: number;
}

export interface JobImpressao {
  id: number;
  tipo: string;
  referencia: string;
  status: string;
  erro: string | null;
  criado_em: string;
  processado_em: string | null;
}

export interface OrcamentoPayload {
  cliente: string;
  contato?: string;
  validade_dias?: number;
  observacoes?: string;
  desconto?: number;
  itens: OrcamentoItemPayload[];
  condicao_pagamento_id?: number;
  usuario_id?: number;
  cliente_id?: number;
}

export interface ProdutoSubcategoria {
  id: number;
  nome: string;
  marca: string | null;
  external_id: string | null;
  familia_id: number | null;
  price_min: number | null;
}

export interface ListaProdutosSubcategoria {
  items: ProdutoSubcategoria[];
  total: number;
  offset: number;
  limit: number;
}

export type DetalheCartItem = {
  id: number;
  name: string;
  price: number;
  imagem_url?: string;
  sku?: string;
  spec?: string;
  brand?: string;
  custom?: boolean;
  descricao?: string;
  produto_pai?: number;
  marca?: string;
  atributos?: Record<string, unknown>;
};

export interface CotacaoDraft {
  itens: Record<number, number>;
  detalhes: Record<number, DetalheCartItem>;
}

// ------------------------------------------------------------------
// Estoque
// ------------------------------------------------------------------

export interface Deposito {
  id: number;
  nome: string;
  ativo: number | boolean;
  criado_em: string;
}

export interface SaldoItem {
  id: number;
  deposito_id: number;
  variante_id: number;
  quantidade: number;
  reserva: number;
  atualizado_em: string;
  deposito_nome: string;
  sku: string;
  preco: number;
  produto_nome: string;
  marca: string;
  familia_id?: number | null;
  familia_nome?: string;
  unidade_venda?: string;
  embalagem?: number | null;
  fator_conversao?: number | null;
  ncm?: string;
  unidade_tributavel?: string;
  localizacao?: string;
  estoque_minimo?: number;
  estoque_maximo?: number;
  situacao?: string;
}

export interface MovimentoPayload {
  deposito_id: number;
  variante_id: number;
  tipo: "entrada" | "saida" | "ajuste" | "transferencia" | "inventario";
  quantidade: number;
  documento?: string;
  observacao?: string;
  lote_id?: number;
  usuario_id?: number;
}

export interface MovimentoResult {
  movimento_id: number;
  saldo_anterior: number;
  saldo_posterior: number;
}

export interface MovimentoItem {
  id: number;
  deposito_id: number;
  variante_id: number;
  tipo: string;
  quantidade: number;
  saldo_anterior: number;
  saldo_posterior: number;
  documento: string | null;
  observacao: string | null;
  lote_id: number | null;
  usuario_id: number | null;
  criado_em: string;
  deposito_nome: string;
  sku: string;
  produto_nome: string;
  marca: string;
}

export interface TransferenciaPayload {
  origem_id: number;
  destino_id: number;
  variante_id: number;
  quantidade: number;
  observacao?: string;
  usuario_id?: number;
}

export interface LoteItem {
  id: number;
  deposito_id: number;
  variante_id: number;
  codigo: string;
  data_fabricacao: string | null;
  data_validade: string | null;
  quantidade: number;
  criado_em: string;
  deposito_nome: string;
  sku: string;
  produto_nome: string;
  marca: string;
}

export interface LotePayload {
  deposito_id: number;
  variante_id: number;
  codigo: string;
  quantidade?: number;
  data_fabricacao?: string;
  data_validade?: string;
}

export interface Expedicao {
  id: number;
  codigo: string;
  deposito_id: number;
  deposito_nome: string;
  data_expedicao: string;
  status: string;
  transportadora: string;
  observacao: string;
  criado_em: string;
}

// ------------------------------------------------------------------
// Financeiro
// ------------------------------------------------------------------

export interface CaixaMovimento {
  id: number;
  tipo: string;
  descricao: string;
  valor: number;
  saldo_anterior: number;
  saldo_posterior: number;
  forma_pagamento: string;
  plano_conta_id: number | null;
  documento: string | null;
  orcamento_id: number | null;
  usuario_id: number | null;
  criado_em: string;
}

export interface CaixaMovimentoPayload {
  tipo: string;
  descricao: string;
  valor: number;
  forma_pagamento?: string;
  plano_conta_id?: number;
  documento?: string;
  orcamento_id?: number;
  usuario_id?: number;
}

export interface ContaReceber {
  id: number;
  cliente: string;
  cliente_id: number | null;
  descricao: string;
  valor: number;
  saldo: number;
  data_vencimento: string;
  data_emissao: string;
  data_recebimento: string | null;
  plano_conta_id: number | null;
  documento: string | null;
  observacao: string | null;
  status: string;
  criado_em: string;
}

export interface ContaPagar {
  id: number;
  fornecedor: string;
  fornecedor_id: number | null;
  descricao: string;
  valor: number;
  saldo: number;
  data_vencimento: string;
  data_emissao: string;
  data_pagamento: string | null;
  plano_conta_id: number | null;
  documento: string | null;
  observacao: string | null;
  status: string;
  criado_em: string;
}

export interface ContaPayload {
  cliente?: string;
  fornecedor?: string;
  valor: number;
  data_vencimento: string;
  cliente_id?: number;
  fornecedor_id?: number;
  descricao?: string;
  documento?: string;
  plano_conta_id?: number;
  observacao?: string;
}

// ------------------------------------------------------------------
// Preços
// ------------------------------------------------------------------

export interface TabelaPreco {
  id: number;
  nome: string;
  tipo: string;
  margem_padrao: number;
  markup: number;
  ativo: number | boolean;
  criado_em: string;
  atualizado_em: string | null;
}

export interface TabelaPrecoPayload {
  nome: string;
  tipo?: string;
  margem_padrao?: number;
  markup?: number;
}

export interface TabelaPrecoItem {
  id: number;
  tabela_id: number;
  variante_id: number;
  preco: number;
  margem: number | null;
  ativo: number | boolean;
  sku: string;
  preco_base: number;
  custo_unitario: number | null;
  produto_nome: string;
  marca: string;
}

export interface TabelaPrecoItemPayload {
  variante_id: number;
  preco: number;
  margem?: number;
}

export interface TabelaPrecoItemMargem {
  id: number;
  tabela_id: number;
  variante_id: number;
  preco: number;
  margem: number | null;
  ativo: number | boolean;
  sku: string;
  preco_base: number;
  custo_unitario: number | null;
  produto_nome: string;
  marca: string;
  margem_pct: number | null;
}

export interface RevisaoPreco {
  id: number;
  tabela_id: number;
  codigo: string;
  descricao: string;
  data_cadastro: string;
  data_validade: string | null;
  situacao: string;
  cliente_id: number | null;
  tabela_nome: string;
  cliente_nome: string | null;
  criado_em: string;
}

export interface Promocao {
  id: number;
  nome: string;
  tipo: string;
  valor: number;
  data_inicio: string | null;
  data_fim: string | null;
  ativo: number | boolean;
  criado_em: string;
}

export interface PromocaoPayload {
  nome: string;
  tipo: string;
  valor: number;
  data_inicio?: string;
  data_fim?: string;
  ativo?: number;
}

export interface PromocaoItem {
  id: number;
  promocao_id: number;
  variante_id: number;
  preco_promocional: number;
  sku: string;
  preco_base: number;
  produto_nome: string;
  marca: string;
}

export interface PromocaoItemPayload {
  variante_id: number;
  preco_promocional: number;
}

// ------------------------------------------------------------------
// Fiscal
// ------------------------------------------------------------------

export interface CfopCode {
  codigo: string;
  descricao: string;
  tipo: string;
}

export interface CstCode {
  codigo: string;
  descricao: string;
}

export interface FiscalConfigItem {
  id: number;
  variante_id: number;
  ncm: string;
  cfop: string | null;
  cst_icms: string | null;
  cst_pis: string | null;
  cst_cofins: string | null;
  aliquota_icms: number;
  aliquota_pis: number;
  aliquota_cofins: number;
  aliquota_ipi: number;
  origem: number;
  cest: string;
  csosn: string;
  aliquota_icms_st: number;
  mva: number;
  base_reducao: number;
  aliquota_interestadual: number;
  aliquota_fecp: number;
  credito_icms: number;
  beneficio_id: number | null;
  vigencia_inicio: string | null;
  vigencia_fim: string | null;
  sku: string;
  preco: number;
  produto_nome: string;
  marca: string;
  categoria: string | null;
}

export interface Emitente {
  id: number;
  razao_social: string;
  nome_fantasia: string;
  cnpj: string;
  ie: string;
  regime_tributario: string;
  cnae_principal: string;
  logradouro: string;
  numero: string;
  municipio: string;
  uf: string;
  token_focus: string;
  ambiente_focus: string;
  aliquota_icms: number;
  aliquota_pis: number;
  aliquota_cofins: number;
  serie_nfe: number;
  proximo_numero_nfe: number;
}

export interface NfeSaida {
  id: number;
  numero: number;
  serie: number;
  chave: string;
  status: string;
  cliente_nome: string;
  valor: number;
  criado_em: string;
}

export interface NfeEntrada {
  id: number;
  chave: string;
  numero: number;
  fornecedor_nome: string;
  valor: number;
  data_emissao: string;
  criado_em: string;
}

export interface RelVenda {
  dia: string;
  n_pedidos: number;
  total_vendas: number;
}

export interface RelAging {
  faixa: string;
  qtd: number;
  total: number;
}

export interface RelDre {
  tipo: string;
  valor: number;
}

export interface DiagnosticoResumo {
  classificacao: string;
  produtos: number;
  variantes: number;
}

export interface DiagnosticoVariacao {
  id: number;
  produto_id: number;
  classificacao: string;
  n_variantes: number;
  n_atributos: number;
  n_eans: number;
  observacao: string;
  revisado: number | boolean;
  nome: string;
  marca: string;
  categoria_id: number | null;
}

export interface DiagnosticoDetalhe {
  produto: { id: number; nome: string; marca: string; familia_id: number | null } | null;
  variantes: { id: number; sku: string; ean: string; preco: number; atributos: string | null }[];
}

export interface FornecedorPrefItem {
  id: number;
  variante_id: number;
  fornecedor_id: number;
  fornecedor_nome: string;
  ranking: number;
  ultimo_preco: number | null;
  ultimo_prazo: number | null;
  sku: string;
  produto_nome: string;
}

export interface ToleranciaCompra {
  id: number;
  fornecedor_id: number;
  tolerancia_preco_pct: number;
  tolerancia_qtd_pct: number;
  exige_aprovacao: number | boolean;
}

export interface IbptItem {
  id: number;
  ncm: string;
  descricao: string;
  aliquota_federal: number;
  aliquota_estadual: number;
  aliquota_municipal: number;
}

export interface SugestaoIbpt {
  id: number;
  variante_id: number;
  ncm: string;
  descricao: string;
  confianca: number;
  status: "pendente" | "aplicada" | "rejeitada";
  criado_em: string;
  aplicado_em: string | null;
  sku: string;
  produto_nome: string;
  marca: string;
}

export interface FiscalConfigPayload {
  ncm?: string;
  cfop?: string;
  cst_icms?: string;
  cst_pis?: string;
  cst_cofins?: string;
  aliquota_icms?: number;
  aliquota_pis?: number;
  aliquota_cofins?: number;
  aliquota_ipi?: number;
  origem?: number;
  cest?: string;
  csosn?: string;
  aliquota_icms_st?: number;
  mva?: number;
  base_reducao?: number;
  aliquota_interestadual?: number;
  aliquota_fecp?: number;
  credito_icms?: number;
  beneficio_id?: number | null;
  vigencia_inicio?: string | null;
  vigencia_fim?: string | null;
}

export interface CestItem {
  codigo: string;
  ncm_prefix: string;
  descricao: string;
  vigencia_inicio: string | null;
  vigencia_fim: string | null;
  ativo: number | boolean;
}

export interface CsosnItem {
  codigo: string;
  descricao: string;
}

export interface BeneficioFiscalItem {
  id: number;
  codigo: string;
  descricao: string;
  tipo: string;
  valor_default: number;
  vigencia_inicio: string | null;
  vigencia_fim: string | null;
  ativo: number | boolean;
}

export interface CalculoPrecoFiscal {
  regime: string;
  ncm: string;
  cest: string;
  csosn: string;
  aliquota_icms: number;
  icms_st: { aplica: boolean; aliquota: number; mva: number; base_reducao: number };
  difal: { aplica: boolean; uf_origem: string; uf_dest: string | null; aliquota_interestadual: number; aliquota_fecp: number };
  creditos: { icms: number; pis: number; cofins: number; ipi: number; total_pct: number };
  carga: { icms: number; pis: number; cofins: number; ipi: number; total_pct: number };
  beneficio: { codigo: string; descricao: string; tipo: string; valor: number } | null;
  vigencia: { config: boolean | null; inicio: string | null; fim: string | null };
  ibpt: { ncm: string; federal: number; estadual: number; municipal: number; vigente: boolean | null } | null;
}

export interface CalculoPreco {
  variante_id: number;
  canal: string | null;
  tabela_id: number | null;
  tabela_nome: string | null;
  custo_base: number | null;
  custo_liquido: number | null;
  regime: string | null;
  despesas_pct: { comissao: number; despesas: number; taxas: number; total: number };
  preco_minimo: number | null;
  preco_sugerido: number | null;
  margem_efetiva_pct: number | null;
  markup_efetivo_pct: number | null;
  observacao: string | null;
  fiscal: CalculoPrecoFiscal | null;
}

export interface ItemPreviaReajuste {
  variante_id: number;
  sku: string;
  produto_nome: string;
  marca: string;
  preco_atual: number;
  custo_base: number | null;
  custo_liquido: number | null;
  preco_minimo: number | null;
  preco_sugerido: number | null;
  margem_efetiva_pct: number | null;
  observacao: string | null;
}

export interface PreviaReajuste {
  tabela_id: number;
  margem: number;
  markup: number;
  total: number;
  confirmado?: boolean;
  itens: ItemPreviaReajuste[];
}

export interface ReajusteResultado {
  tabela_id: number;
  confirmado: boolean;
  aplicados: number;
  sem_custo: number;
  total: number;
}

export interface HistoricoPrecoItem {
  id: number;
  tabela_id: number;
  variante_id: number;
  preco_anterior: number;
  preco_novo: number;
  margem_pct: number | null;
  markup_pct: number | null;
  tipo: string;
  origem: string;
  usuario_id: number | null;
  criado_em: string;
  sku: string;
  produto_nome: string;
  marca: string;
  tabela_nome: string;
  usuario_nome: string | null;
}

export interface HistoricoFiscalItem {
  id: number;
  variante_id: number;
  tipo: string;
  ncm: string;
  cfop: string | null;
  cst_icms: string | null;
  cst_pis: string | null;
  cst_cofins: string | null;
  aliquota_icms: number;
  aliquota_pis: number;
  aliquota_cofins: number;
  aliquota_ipi: number;
  origem: number;
  cest: string;
  csosn: string;
  aliquota_icms_st: number;
  mva: number;
  base_reducao: number;
  aliquota_interestadual: number;
  aliquota_fecp: number;
  credito_icms: number;
  beneficio_id: number | null;
  vigencia_inicio: string | null;
  vigencia_fim: string | null;
  usuario_id: number | null;
  criado_em: string;
  sku: string;
  produto_nome: string;
  marca: string;
  usuario_nome: string | null;
}

export interface MargemVenda {
  variante_id: number;
  produto_nome: string;
  sku: string;
  n_itens: number;
  receita: number;
  custo: number;
  margem: number;
  margem_pct: number | null;
}

export interface DashboardData {
  resumo: {
    hoje: string;
    vendas_hoje: { n: number; total: number };
    vendas_mes: { n: number; total: number };
    receber_a_vencer: number;
    receber_vencidas: number;
    pagar_a_vencer: number;
    estoque_baixo: number;
    valor_estoque: number;
  };
  estoque_baixo: { variante_id: number; nome: string; sku: string; quantidade: number; estoque_minimo: number; deposito: string }[];
  top_vendas: { nome: string; sku: string; qtd: number; receita: number }[];
}

export interface ProblemaFiscal {
  tipo: "ERROR" | "WARNING" | "INFO";
  campo: string;
  mensagem: string;
}

export interface PassoDecisao {
  passo: string;
  detalhe: string;
}

export interface FiscalResultado {
  status: string;
  operacao: string;
  data: string;
  regime: string;
  ncm: string;
  cest: string;
  cfop: string;
  origem: number;
  cst_icms: string;
  csosn: string;
  cst_pis: string;
  cst_cofins: string;
  cst_ibs: string;
  cst_cbs: string;
  aliquota_icms: number;
  base_icms: number;
  valor_icms: number;
  modalidade_st: string;
  base_icms_st: number;
  aliquota_icms_st: number;
  valor_icms_st: number;
  aliquota_pis: number;
  valor_pis: number;
  aliquota_cofins: number;
  valor_cofins: number;
  aliquota_ibs: number;
  valor_ibs: number;
  aliquota_cbs: number;
  valor_cbs: number;
  memoria: Record<string, unknown>;
  memoria_produto: Record<string, unknown> | null;
  difal: { aplica: boolean; uf_origem: string; uf_destino: string | null };
  piscofins: Record<string, unknown>;
  ibs_cbs: Record<string, unknown>;
  decisao: PassoDecisao[];
  problemas: ProblemaFiscal[];
  status_validacao: string;
}

export interface FiscalSimulacao {
  resultado: FiscalResultado;
  status_validacao: string;
  problemas: ProblemaFiscal[];
}

// ------------------------------------------------------------------
// Bancos
// ------------------------------------------------------------------

export interface CondicaoPagamento {
  id: number;
  nome: string;
  descricao: string;
  ativo: number | boolean;
  parcelas?: CondicaoParcela[];
}

export interface CondicaoParcela {
  id: number;
  condicao_id: number;
  sequencia: number;
  dias: number;
  percentual: number;
}

export interface CentroCusto {
  id: number;
  codigo: string;
  nome: string;
  ativo: number | boolean;
  criado_em: string;
}

export interface Adiantamento {
  id: number;
  tipo: string;
  pessoa_id: number | null;
  pessoa_nome: string;
  valor: number;
  saldo: number;
  data_adiantamento: string;
  data_baixa: string | null;
  observacao: string;
  criado_em: string;
}

export interface ContaBancaria {
  id: number;
  nome: string;
  banco: string;
  agencia: string;
  conta: string;
  digito: string;
  saldo_inicial: number;
  saldo_atual: number;
  ativo: number | boolean;
  criado_em: string;
}

export interface ContaBancariaPayload {
  nome: string;
  banco?: string;
  agencia?: string;
  conta?: string;
  digito?: string;
  saldo_inicial?: number;
}

export interface MovimentoBancario {
  id: number;
  conta_id: number;
  tipo: string;
  valor: number;
  data_movimento: string;
  data_conciliacao: string | null;
  descricao: string;
  documento: string;
  categoria: string;
  plano_conta_id: number | null;
  conciliado: number | boolean;
  criado_em: string;
  conta_nome: string;
  banco: string;
}

export interface MovimentoBancarioPayload {
  conta_id: number;
  tipo: string;
  valor: number;
  data_movimento: string;
  descricao?: string;
  documento?: string;
  categoria?: string;
  plano_conta_id?: number;
}

// ------------------------------------------------------------------
// Pós-venda
// ------------------------------------------------------------------

export interface ClienteInteracao {
  id: number;
  cliente_id: number | null;
  cliente_nome: string;
  tipo: string;
  descricao: string;
  data_contato: string;
  data_proximo_contato: string | null;
  orcamento_id: number | null;
  usuario_id: number | null;
  criado_em: string;
}

export interface InteracaoPayload {
  cliente_id?: number;
  cliente_nome: string;
  tipo: string;
  descricao: string;
  data_contato: string;
  data_proximo_contato?: string;
  orcamento_id?: number;
  usuario_id?: number;
}

export interface Garantia {
  id: number;
  cliente_nome: string;
  cliente_id: number | null;
  orcamento_id: number | null;
  variante_id: number | null;
  produto_nome: string;
  data_venda: string | null;
  data_inicio: string;
  data_fim: string;
  dias: number;
  descricao: string;
  observacao: string;
  status: string;
  criado_em: string;
}

export interface FornecedorPrecoItem {
  id: number;
  fornecedor_id: number;
  variante_id: number;
  preco: number;
  prazo_entrega: number | null;
  icms: number;
  ipi: number;
  sku: string;
  produto_nome: string;
  fornecedor_nome: string;
}

export interface SolicitacaoCompra {
  id: number;
  codigo: string;
  descricao: string;
  status: string;
  data_solicitacao: string;
  data_aprovacao: string | null;
  usuario_nome: string | null;
  observacao: string;
  criado_em: string;
}

export interface DescontoRegra {
  id: number;
  nome: string;
  tipo: string;
  valor_maximo: number;
  valor_minimo: number;
  perfil: string;
  ativo: number | boolean;
  criado_em: string;
}

export interface FreteRegra {
  id: number;
  nome: string;
  uf: string;
  valor_minimo_pedido: number;
  valor_frete: number;
  tipo: string;
  ativo: number | boolean;
  criado_em: string;
}

export interface GarantiaPayload {
  cliente_nome: string;
  produto_nome: string;
  data_inicio: string;
  data_fim: string;
  dias?: number;
  cliente_id?: number;
  orcamento_id?: number;
  variante_id?: number;
  descricao?: string;
  observacao?: string;
  data_venda?: string;
}
