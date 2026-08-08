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
}

export type CatalogoItem = ProdutoResumo | ProdutoGrupo;

export interface ListCatalogo {
  items: CatalogoItem[];
  total: number;
  offset: number;
  limit: number;
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
  familia_id: number;
  familia_nome: string;
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
  if (body !== undefined) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
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
  iaMatch: (items: unknown[], topK = 5) =>
    request<IAMatchResult>("POST", "/api/ia/match", { items, top_k: topK }),
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
    request<{ ok: boolean }>("PUT", `/api/produtos-cadastro/${id}`, payload),
  excluirProdutoCadastro: (id: number) =>
    request<{ ok: boolean }>("DELETE", `/api/produtos-cadastro/${id}`),
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
};

export type DetalheCartItem = {
  id: number;
  name: string;
  price: number;
  imagem_url?: string;
  sku?: string;
  spec?: string;
  brand?: string;
};

export interface CotacaoDraft {
  itens: Record<number, number>;
  detalhes: Record<number, DetalheCartItem>;
}