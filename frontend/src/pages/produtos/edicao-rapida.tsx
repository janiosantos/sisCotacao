import { useEffect, useState } from "react";
import {
  api,
  type CategoriaTree,
  type Grupo,
  type ItemListaCadastro,
  type ProdutoEdicaoLote,
  type StatusCadastroProduto,
  type Subgrupo,
} from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Select } from "../../ui/ui";

const STATUS: { value: StatusCadastroProduto; label: string }[] = [
  { value: "rascunho", label: "Rascunho" },
  { value: "em_revisao", label: "Em revisao" },
  { value: "publicado", label: "Publicado" },
  { value: "bloqueado", label: "Bloqueado" },
];

const UNIDADES = ["UN", "CX", "MT", "M", "KG", "G", "LT", "L", "PC", "PCT", "RL", "JG"];

function produtoParaEdicao(item: ItemListaCadastro): ProdutoEdicaoLote {
  return {
    id: item.id,
    versao_edicao: item.versao_edicao || "",
    nome: item.nome || "",
    marca: item.marca || "",
    preco: Number(item.preco ?? 0),
    unidade_venda: item.unidade_venda || "UN",
    grupo_id: item.grupo_id ?? null,
    subgrupo_id: item.subgrupo_id ?? null,
    categoria_id: item.categoria_id ?? null,
    subcategoria_id: item.subcategoria_id ?? null,
    status_cadastro: item.status_cadastro || "publicado",
  };
}

export function EdicaoRapidaProdutos({
  items,
  grupos,
  subgrupos,
  categorias,
  onSaved,
  onDirtyChange,
}: {
  items: ItemListaCadastro[];
  grupos: Grupo[];
  subgrupos: Subgrupo[];
  categorias: CategoriaTree[];
  onSaved: () => void;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const [edicoes, setEdicoes] = useState<Record<number, ProdutoEdicaoLote>>({});
  const [selecionados, setSelecionados] = useState<Set<number>>(new Set());
  const [statusLote, setStatusLote] = useState<StatusCadastroProduto>("publicado");
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    setEdicoes({});
    setSelecionados(new Set());
    onDirtyChange(false);
  }, [items, onDirtyChange]);

  const editar = (item: ItemListaCadastro, mudancas: Partial<ProdutoEdicaoLote>) => {
    setEdicoes((atuais) => ({
      ...atuais,
      [item.id]: { ...(atuais[item.id] || produtoParaEdicao(item)), ...mudancas },
    }));
    setSelecionados((atuais) => new Set(atuais).add(item.id));
    onDirtyChange(true);
  };

  const alternarSelecao = (id: number, selecionado: boolean) => {
    setSelecionados((atuais) => {
      const novos = new Set(atuais);
      if (selecionado) novos.add(id);
      else novos.delete(id);
      return novos;
    });
  };

  const aplicarStatus = () => {
    if (!selecionados.size) {
      toast("Selecione ao menos um produto", "warn");
      return;
    }
    const porId = new Map(items.map((item) => [item.id, item]));
    setEdicoes((atuais) => {
      const novos = { ...atuais };
      for (const id of selecionados) {
        const item = porId.get(id);
        if (item) novos[id] = { ...(novos[id] || produtoParaEdicao(item)), status_cadastro: statusLote };
      }
      return novos;
    });
    onDirtyChange(true);
  };

  const descartar = () => {
    if (Object.keys(edicoes).length && !window.confirm("Descartar as alteracoes ainda nao salvas?")) return;
    setEdicoes({});
    setSelecionados(new Set());
    onDirtyChange(false);
  };

  const salvar = async () => {
    const alterados = Object.values(edicoes);
    if (!alterados.length) return;
    setSalvando(true);
    try {
      const resultado = await api.atualizarProdutosLote(alterados);
      toast(`${resultado.atualizados} produto(s) atualizado(s)`, "success");
      setEdicoes({});
      setSelecionados(new Set());
      onDirtyChange(false);
      onSaved();
    } catch (e) {
      toast("Nao foi possivel salvar o lote: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const todosSelecionados = items.length > 0 && items.every((item) => selecionados.has(item.id));
  const inputClass = "h-9 rounded-md border border-gray-300 bg-white px-2 text-sm text-gray-800 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100";

  return (
    <section aria-label="Edicao rapida de produtos" className="rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 bg-gray-50 px-3 py-2">
        <span className="text-sm font-semibold text-gray-800">Edicao rapida</span>
        <span className="text-xs text-gray-500">Edite com Tab e use o seletor para alterar o status de varias linhas.</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <label htmlFor="status-lote" className="text-xs font-medium text-gray-600">Status dos selecionados</label>
          <Select
            id="status-lote"
            value={statusLote}
            onChange={(e) => setStatusLote(e.target.value as StatusCadastroProduto)}
            className="w-36"
          >
            {STATUS.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}
          </Select>
          <Button size="sm" onClick={aplicarStatus}>Aplicar</Button>
          <Button size="sm" variant="ghost" disabled={!Object.keys(edicoes).length || salvando} onClick={descartar}>Descartar</Button>
          <Button size="sm" variant="primary" disabled={!Object.keys(edicoes).length || salvando} onClick={() => void salvar()}>
            {salvando ? "Salvando..." : `Salvar alteracoes (${Object.keys(edicoes).length})`}
          </Button>
        </div>
      </div>

      <div className="max-h-[65vh] overflow-auto">
        <table className="min-w-[1780px] border-separate border-spacing-0 text-left" aria-label="Grade editavel de produtos">
          <thead className="sticky top-0 z-20 bg-gray-100 text-xs uppercase tracking-wide text-gray-600">
            <tr>
              <th scope="col" className="sticky left-0 z-30 w-10 border-b border-r border-gray-200 bg-gray-100 px-3 py-2">
                <input
                  type="checkbox"
                  aria-label="Selecionar todos os produtos da pagina"
                  checked={todosSelecionados}
                  onChange={(e) => setSelecionados(e.target.checked ? new Set(items.map((item) => item.id)) : new Set())}
                  className="h-4 w-4 rounded border-gray-300"
                />
              </th>
              <th scope="col" className="sticky left-10 z-30 w-36 border-b border-r border-gray-200 bg-gray-100 px-3 py-2">Codigo</th>
              <th scope="col" className="w-72 border-b border-gray-200 px-3 py-2">Produto</th>
              <th scope="col" className="w-44 border-b border-gray-200 px-3 py-2">Marca</th>
              <th scope="col" className="w-28 border-b border-gray-200 px-3 py-2">Preco</th>
              <th scope="col" className="w-24 border-b border-gray-200 px-3 py-2">Unidade</th>
              <th scope="col" className="w-48 border-b border-gray-200 px-3 py-2">Grupo</th>
              <th scope="col" className="w-48 border-b border-gray-200 px-3 py-2">Subgrupo</th>
              <th scope="col" className="w-52 border-b border-gray-200 px-3 py-2">Categoria</th>
              <th scope="col" className="w-52 border-b border-gray-200 px-3 py-2">Subcategoria</th>
              <th scope="col" className="w-40 border-b border-gray-200 px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const linha = edicoes[item.id] || produtoParaEdicao(item);
              const subsDoGrupo = subgrupos.filter((sub) => !linha.grupo_id || sub.grupo_id === linha.grupo_id);
              const categoriasDaLinha = categorias.filter((categoria) => {
                if (categoria.id === linha.categoria_id) return true;
                if (linha.subgrupo_id) return categoria.subgrupo_id === linha.subgrupo_id;
                if (linha.grupo_id) return categoria.grupo_id === linha.grupo_id;
                return true;
              });
              const categoria = categorias.find((cat) => cat.id === linha.categoria_id);
              const alterado = Boolean(edicoes[item.id]);
              return (
                <tr key={item.id} className={alterado ? "bg-amber-50" : "hover:bg-gray-50"}>
                  <td className={`sticky left-0 z-10 border-b border-r border-gray-200 px-3 py-2 ${alterado ? "bg-amber-50" : "bg-white"}`}>
                    <input
                      type="checkbox"
                      aria-label={`Selecionar produto ${item.id}`}
                      checked={selecionados.has(item.id)}
                      onChange={(e) => alternarSelecao(item.id, e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                  </td>
                  <td className={`sticky left-10 z-10 border-b border-r border-gray-200 px-3 py-2 ${alterado ? "bg-amber-50" : "bg-white"}`}>
                    <button
                      className="block text-left font-mono text-xs font-semibold text-brand-700 hover:underline"
                      onClick={() => {
                        if (Object.keys(edicoes).length && !window.confirm("Ha alteracoes nao salvas. Descartar e abrir o produto?")) return;
                        location.hash = `#/produtos/${item.id}`;
                      }}
                    >
                      {item.sku || `ID ${item.id}`}
                    </button>
                    <span className="text-[11px] text-gray-500">ID {item.id}</span>
                  </td>
                  <td className="border-b border-gray-200 px-2 py-1.5">
                    <input aria-label={`Nome do produto ${item.id}`} value={linha.nome} onChange={(e) => editar(item, { nome: e.target.value })} className={`${inputClass} w-full`} />
                  </td>
                  <td className="border-b border-gray-200 px-2 py-1.5">
                    <input aria-label={`Marca do produto ${item.id}`} value={linha.marca} onChange={(e) => editar(item, { marca: e.target.value })} className={`${inputClass} w-full`} />
                  </td>
                  <td className="border-b border-gray-200 px-2 py-1.5">
                    <input aria-label={`Preco do produto ${item.id}`} type="number" min="0" step="0.01" value={linha.preco} onChange={(e) => editar(item, { preco: Number(e.target.value) })} className={`${inputClass} w-full text-right tabular-nums`} />
                  </td>
                  <td className="border-b border-gray-200 px-2 py-1.5">
                    <select aria-label={`Unidade do produto ${item.id}`} value={linha.unidade_venda} onChange={(e) => editar(item, { unidade_venda: e.target.value })} className={`${inputClass} w-full`}>
                      {UNIDADES.map((unidade) => <option key={unidade} value={unidade}>{unidade}</option>)}
                    </select>
                  </td>
                  <td className="border-b border-gray-200 px-2 py-1.5">
                    <select
                      aria-label={`Grupo do produto ${item.id}`}
                      value={linha.grupo_id ?? ""}
                      onChange={(e) => editar(item, { grupo_id: Number(e.target.value) || null, subgrupo_id: null, categoria_id: null, subcategoria_id: null })}
                      className={`${inputClass} w-full`}
                    >
                      <option value="">Sem grupo</option>
                      {grupos.map((grupo) => <option key={grupo.id} value={grupo.id}>{grupo.codigo} - {grupo.nome}</option>)}
                    </select>
                  </td>
                  <td className="border-b border-gray-200 px-2 py-1.5">
                    <select
                      aria-label={`Subgrupo do produto ${item.id}`}
                      value={linha.subgrupo_id ?? ""}
                      disabled={!linha.grupo_id}
                      onChange={(e) => editar(item, { subgrupo_id: Number(e.target.value) || null, categoria_id: null, subcategoria_id: null })}
                      className={`${inputClass} w-full disabled:bg-gray-100`}
                    >
                      <option value="">Sem subgrupo</option>
                      {subsDoGrupo.map((sub) => <option key={sub.id} value={sub.id}>{sub.codigo} - {sub.nome}</option>)}
                    </select>
                  </td>
                  <td className="border-b border-gray-200 px-2 py-1.5">
                    <select
                      aria-label={`Categoria do produto ${item.id}`}
                      value={linha.categoria_id ?? ""}
                      onChange={(e) => {
                        const categoriaId = Number(e.target.value) || null;
                        const novaCategoria = categorias.find((cat) => cat.id === categoriaId);
                        const novoSubgrupo = subgrupos.find((sub) => sub.id === novaCategoria?.subgrupo_id);
                        editar(item, {
                          categoria_id: categoriaId,
                          subcategoria_id: null,
                          subgrupo_id: novaCategoria?.subgrupo_id ?? linha.subgrupo_id,
                          grupo_id: novoSubgrupo?.grupo_id ?? linha.grupo_id,
                        });
                      }}
                      className={`${inputClass} w-full`}
                    >
                      <option value="">Sem categoria</option>
                      {categoriasDaLinha.map((cat) => <option key={cat.id} value={cat.id}>{cat.nome}</option>)}
                    </select>
                  </td>
                  <td className="border-b border-gray-200 px-2 py-1.5">
                    <select
                      aria-label={`Subcategoria do produto ${item.id}`}
                      value={linha.subcategoria_id ?? ""}
                      disabled={!linha.categoria_id}
                      onChange={(e) => editar(item, { subcategoria_id: Number(e.target.value) || null })}
                      className={`${inputClass} w-full disabled:bg-gray-100`}
                    >
                      <option value="">Sem subcategoria</option>
                      {(categoria?.subcategorias || []).map((sub) => <option key={sub.id} value={sub.id}>{sub.nome}</option>)}
                    </select>
                  </td>
                  <td className="border-b border-gray-200 px-2 py-1.5">
                    <select aria-label={`Status do produto ${item.id}`} value={linha.status_cadastro} onChange={(e) => editar(item, { status_cadastro: e.target.value as StatusCadastroProduto })} className={`${inputClass} w-full`}>
                      {STATUS.map((status) => <option key={status.value} value={status.value}>{status.label}</option>)}
                    </select>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="border-t border-gray-200 px-3 py-2 text-xs text-gray-500">
        {selecionados.size} selecionado(s) nesta pagina; {Object.keys(edicoes).length} linha(s) com alteracoes pendentes.
      </div>
    </section>
  );
}
