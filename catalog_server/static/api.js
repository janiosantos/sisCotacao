// api.js — wrapper fino sobre fetch para a API do sistema.
const Api = (() => {
  async function request(method, path, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const j = await res.json();
        detail = j.error || detail;
      } catch (e) {}
      throw new Error(detail);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  return {
    // catálogo
    listarProdutos: (params = {}) => request("GET", "/api/produtos" + qs(params)),
    detalharProduto: (id) => request("GET", `/api/produtos/${id}`),
    listarCategorias: () => request("GET", "/api/categorias"),

    // fornecedores
    listarFornecedores: (somenteAtivos = false) =>
      request("GET", "/api/fornecedores" + qs({ somente_ativos: somenteAtivos })),
    criarFornecedor: (data) => request("POST", "/api/fornecedores", data),
    atualizarFornecedor: (id, data) => request("PUT", `/api/fornecedores/${id}`, data),
    alternarAtivoFornecedor: (id, ativo) =>
      request("PATCH", `/api/fornecedores/${id}/ativo` + qs({ ativo })),

    // cotações
    listarCotacoes: (status) => request("GET", "/api/cotacoes" + qs({ status })),
    criarCotacao: (data) => request("POST", "/api/cotacoes", data),
    detalharCotacao: (id) => request("GET", `/api/cotacoes/${id}`),
    atualizarCotacao: (id, data) => request("PATCH", `/api/cotacoes/${id}`, data),
    convidarFornecedor: (cotacaoId, fornecedorId) =>
      request("POST", `/api/cotacoes/${cotacaoId}/fornecedores/${fornecedorId}`),
    removerFornecedorDaCotacao: (cotacaoId, fornecedorId) =>
      request("DELETE", `/api/cotacoes/${cotacaoId}/fornecedores/${fornecedorId}`),
    adicionarItem: (cotacaoId, data) => request("POST", `/api/cotacoes/${cotacaoId}/itens`, data),
    removerItem: (cotacaoId, itemId) => request("DELETE", `/api/cotacoes/${cotacaoId}/itens/${itemId}`),
    registrarPreco: (cotacaoId, data) => request("PUT", `/api/cotacoes/${cotacaoId}/precos`, data),
    fecharCotacao: (cotacaoId, escolhas) =>
      request("POST", `/api/cotacoes/${cotacaoId}/fechar`, { escolhas }),
    reabrirCotacao: (cotacaoId) => request("POST", `/api/cotacoes/${cotacaoId}/reabrir`),

    criarCotacaoCompras: (data) => request("POST", "/api/compras/cotacoes", data),
    convitesCotacao: (id) => request("GET", `/api/compras/cotacoes/${id}/invites`),
    compararCotacao: (id) => request("GET", `/api/compras/cotacoes/${id}/comparar`),
    gerarPedidos: (id, logica) =>
      request("POST", `/api/compras/cotacoes/${id}/pedidos`, { logica }),
    listarPedidos: () => request("GET", "/api/compras/pedidos"),
    detalharPedido: (id) => request("GET", `/api/compras/pedidos/${id}`),

    // histórico
    historicoPrecos: (produtoId) => request("GET", "/api/historico-precos" + qs({ produto_id: produtoId })),
    produtosComHistorico: () => request("GET", "/api/historico-precos/produtos"),

    // cadastro de produtos
    listarFamilias: (incluirInativas = false) =>
      request("GET", "/api/familias" + qs({ incluir_inativas: incluirInativas })),
    criarFamilia: (data) => request("POST", "/api/familias", data),
    atualizarFamilia: (id, data) => request("PUT", `/api/familias/${id}`, data),
    excluirFamilia: (id) => request("DELETE", `/api/familias/${id}`),
    listarProdutosCadastro: (params = {}) => request("GET", "/api/produtos-cadastro" + qs(params)),
    detalharProdutoCadastro: (id) => request("GET", `/api/produtos-cadastro/${id}`),
    criarProdutoCadastro: (data) => request("POST", "/api/produtos-cadastro", data),
    atualizarProdutoCadastro: (id, data) => request("PUT", `/api/produtos-cadastro/${id}`, data),
    excluirProdutoCadastro: (id) => request("DELETE", `/api/produtos-cadastro/${id}`),
    parseUrlProduto: (url) => request("POST", "/api/produtos-cadastro/parse-url", { url }),
    criarProdutoPorUrl: (url) => request("POST", "/api/produtos-cadastro/from-url", { url }),
    baixarImagensUrl: (id, url) => request("POST", `/api/produtos-cadastro/${id}/imagens-url`, { url }),
    excluirImagem: (id) => request("DELETE", `/api/imagens/${id}`),
    definirCapaImagem: (id, imagemId) =>
      request("POST", `/api/produtos-cadastro/${id}/imagens/capa`, { imagem_id: imagemId }),
    salvarFornecedorVariantes: (id, fornecedorId, itens) =>
      request("PUT", `/api/produtos-cadastro/${id}/fornecedor-variantes`, { fornecedor_id: fornecedorId, itens }),
    enviarImagensProduto: (id, formData) => {
      return fetch(`/api/produtos-cadastro/${id}/imagens`, { method: "POST", body: formData })
        .then(async (res) => {
          if (!res.ok) {
            let detail = res.statusText;
            try { const j = await res.json(); detail = j.error || detail; } catch (e) {}
            throw new Error(detail);
          }
          return res.json();
        });
    },
  };

  function qs(params) {
    const parts = [];
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null || v === "") continue;
      parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
    }
    return parts.length ? "?" + parts.join("&") : "";
  }
})();
