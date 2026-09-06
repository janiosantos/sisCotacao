// pages/categorias.tsx — árvore de categorias/subcategorias + produtos (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type CategoriaTree, type Grupo, type ProdutoSubcategoria, type Subgrupo } from "../api/client";
import { toast } from "../ui/dom";
import { Button, Cell, EmptyRow, Input, Loading, PageHeader, Select, Table, TBody, THead } from "../ui/ui";

const PROD_LIMITE = 60;

export default function Categorias() {
  const [categorias, setCategorias] = useState<CategoriaTree[]>([]);
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [subgrupos, setSubgrupos] = useState<Subgrupo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [catAtiva, setCatAtiva] = useState<number | null>(null);
  const [subAtiva, setSubAtiva] = useState<number | null>(null);
  const [rename, setRename] = useState("");
  const [catSubgrupo, setCatSubgrupo] = useState("");
  const [novaCat, setNovaCat] = useState("");
  const [novoGrupo, setNovoGrupo] = useState("");
  const [novoSubgrupo, setNovoSubgrupo] = useState("");
  const [novaSub, setNovaSub] = useState("");
  const [subEdits, setSubEdits] = useState<Record<number, string>>({});
  const [produtos, setProdutos] = useState<ProdutoSubcategoria[]>([]);
  const [prodTotal, setProdTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [selecionados, setSelecionados] = useState<Set<number>>(new Set());
  const [destCat, setDestCat] = useState("");
  const [destSub, setDestSub] = useState("");

  const carregar = async () => {
    try {
      const [tree, gruposCarregados] = await Promise.all([api.listarCategoriasTree(), api.listarGrupos()]);
      const subgruposCarregados = (
        await Promise.all(gruposCarregados.map((grupo) => api.listarSubgrupos(grupo.id)))
      ).flat();
      setCategorias(tree || []);
      setGrupos(gruposCarregados);
      setSubgrupos(subgruposCarregados);
    } catch {
      toast("Erro ao carregar categorias", "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const cat = categorias.find((c) => c.id === catAtiva);
  const sub = cat?.subcategorias.find((s) => s.id === subAtiva);

  useEffect(() => {
    if (cat) {
      setRename(cat.nome);
      setCatSubgrupo(cat.subgrupo_id ? String(cat.subgrupo_id) : "");
    }
  }, [cat?.id, cat?.nome, cat?.subgrupo_id]);

  const selecionarCat = (id: number) => {
    setExpanded((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
    setCatAtiva(id);
    setSubAtiva(null);
    setProdutos([]);
  };

  const selecionarSub = (id: number) => {
    setSubAtiva(id);
    setProdutos([]);
    setPagina(0);
    setSelecionados(new Set());
    void carregarProdutos(id, 0);
  };

  const carregarProdutos = async (subId: number, pg: number) => {
    try {
      const r = await api.listarProdutosSubcategoria(subId, pg * PROD_LIMITE, PROD_LIMITE);
      setProdutos(r.items);
      setProdTotal(r.total);
      setPagina(pg);
      setSelecionados(new Set());
    } catch (e) {
      toast("Erro ao carregar produtos: " + (e as Error).message, "error");
    }
  };

  const criarCategoria = async () => {
    if (!novaCat.trim() || !novoSubgrupo) {
      toast("Informe o nome, o grupo e o subgrupo da categoria", "error");
      return;
    }
    try {
      await api.criarCategoria(novaCat.trim(), Number(novoSubgrupo));
      setNovaCat("");
      toast("Categoria criada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const renomearCategoria = async () => {
    if (!cat || !rename.trim()) return;
    try {
      await api.atualizarCategoria(cat.id, rename.trim(), catSubgrupo ? Number(catSubgrupo) : null);
      toast("Categoria atualizada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const excluirCategoria = async () => {
    if (!cat || !window.confirm(`Excluir "${cat.nome}" e todas as subcategorias?`)) return;
    try {
      await api.excluirCategoria(cat.id);
      setCatAtiva(null);
      toast("Categoria excluída", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const addSub = async () => {
    if (!cat || !novaSub.trim()) return;
    try {
      await api.criarSubcategoria(cat.id, novaSub.trim());
      setNovaSub("");
      toast("Subcategoria adicionada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const salvarSub = async (id: number) => {
    const nome = (subEdits[id] ?? "").trim();
    if (!nome) return;
    try {
      await api.atualizarSubcategoria(id, nome);
      toast("Subcategoria renomeada", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const excluirSub = async (id: number) => {
    if (!window.confirm("Excluir esta subcategoria?")) return;
    try {
      await api.excluirSubcategoria(id);
      toast("Subcategoria excluída", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const moverSelecionados = async () => {
    if (!destCat && !destSub) {
      toast("Escolha a categoria de destino", "error");
      return;
    }
    if (!selecionados.size) {
      toast("Nenhum produto selecionado", "error");
      return;
    }
    try {
      const r = await api.reclassificarProdutos([...selecionados], destCat, destSub);
      toast(`${r.count} produto(s) movido(s)`, "success");
      setSelecionados(new Set());
      await carregar();
      if (subAtiva) await carregarProdutos(subAtiva, pagina);
    } catch (e) {
      toast("Erro ao mover: " + (e as Error).message, "error");
    }
  };

  const totalPaginas = Math.max(1, Math.ceil(prodTotal / PROD_LIMITE));

  return (
    <div>
      <PageHeader title="Categorias" subtitle="Navegue pela árvore e clique numa subcategoria para ver produtos." />

      {carregando ? (
        <Loading />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[260px_1fr]">
          {/* Árvore */}
          <div className="rounded-lg border border-gray-200 bg-white p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-500">{categorias.length} categorias</span>
            </div>
            <div className="mb-3 space-y-2 rounded-md border border-gray-200 bg-gray-50 p-2">
              <label className="block text-xs font-semibold text-gray-600" htmlFor="nova-categoria">Nova categoria</label>
              <Input id="nova-categoria" placeholder="Nome da categoria" value={novaCat} onChange={(e) => setNovaCat(e.target.value)} />
              <Select value={novoGrupo} onChange={(e) => { setNovoGrupo(e.target.value); setNovoSubgrupo(""); }} aria-label="Grupo da nova categoria">
                <option value="">Selecione o grupo</option>
                {grupos.map((grupo) => <option key={grupo.id} value={grupo.id}>{grupo.codigo} - {grupo.nome}</option>)}
              </Select>
              <Select value={novoSubgrupo} disabled={!novoGrupo} onChange={(e) => setNovoSubgrupo(e.target.value)} aria-label="Subgrupo da nova categoria">
                <option value="">Selecione o subgrupo</option>
                {subgrupos.filter((subgrupo) => subgrupo.grupo_id === Number(novoGrupo)).map((subgrupo) => (
                  <option key={subgrupo.id} value={subgrupo.id}>{subgrupo.codigo} - {subgrupo.nome}</option>
                ))}
              </Select>
              <Button size="sm" variant="primary" className="w-full" onClick={() => void criarCategoria()}>Criar categoria</Button>
            </div>
            <div className="space-y-1">
              {categorias.map((c) => {
                const aberta = expanded.has(c.id);
                const total = c.subcategorias.reduce((a, s) => a + s.product_count, 0);
                return (
                  <div key={c.id}>
                    <button
                      onClick={() => selecionarCat(c.id)}
                      className={`flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-sm ${
                        catAtiva === c.id && subAtiva == null ? "bg-brand-50 text-brand-700" : "text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      <span className="text-xs text-gray-400">{c.subcategorias.length ? (aberta ? "▾" : "▸") : ""}</span>
                      <span className="flex-1 text-left font-medium">{c.nome}</span>
                      <span className="text-xs text-gray-400">{total}</span>
                    </button>
                    <p className="ml-7 truncate text-[10px] text-gray-400">
                      {c.grupo_nome && c.subgrupo_nome ? `${c.grupo_nome} / ${c.subgrupo_nome}` : "Sem grupo/subgrupo vinculado"}
                    </p>
                    {aberta && (
                      <div className="ml-4 space-y-0.5">
                        {c.subcategorias.map((s) => (
                          <button
                            key={s.id}
                            onClick={() => selecionarSub(s.id)}
                            className={`flex w-full items-center justify-between rounded-md px-2 py-1 text-sm ${
                              subAtiva === s.id ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-100"
                            }`}
                          >
                            <span className="flex-1 text-left">{s.nome}</span>
                            <span className="text-xs opacity-70">{s.product_count}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Detalhe */}
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            {sub ? (
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{sub.nome}</h2>
                    <p className="text-sm text-gray-500">
                      {cat?.nome} · {prodTotal} produtos
                    </p>
                  </div>
                </div>

                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <label className="flex items-center gap-1.5 text-sm text-gray-600">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-gray-300"
                      checked={selecionados.size === produtos.length && produtos.length > 0}
                      onChange={(e) =>
                        setSelecionados(e.target.checked ? new Set(produtos.map((p) => p.id)) : new Set())
                      }
                    />
                    Selecionar tudo
                  </label>
                  <Select value={destCat} onChange={(e) => setDestCat(e.target.value)} className="w-44">
                    <option value="">Mover para categoria…</option>
                    {categorias.map((c) => (
                      <option key={c.id} value={c.nome}>
                        {c.nome}
                      </option>
                    ))}
                  </Select>
                  <Select value={destSub} onChange={(e) => setDestSub(e.target.value)} className="w-44">
                    <option value="">…subcategoria</option>
                    {categorias
                      .find((c) => c.nome === destCat)
                      ?.subcategorias.map((s) => (
                        <option key={s.id} value={s.nome}>
                          {s.nome}
                        </option>
                      ))}
                  </Select>
                  <Button size="sm" variant="primary" onClick={() => void moverSelecionados()}>
                    Mover selecionados
                  </Button>
                  {selecionados.size > 0 ? (
                    <span className="text-xs text-gray-500">{selecionados.size} selecionado(s)</span>
                  ) : null}
                </div>

                <Table>
                  <THead cols={[<input type="checkbox" className="h-4 w-4 rounded border-gray-300" readOnly checked={selecionados.size === produtos.length && produtos.length > 0} />, "Produto", "Marca", "Status", "External ID", "Menor preço"]} />
                  <TBody>
                    {produtos.length === 0 ? (
                      <EmptyRow colSpan={6} message="Nenhum produto nesta subcategoria." />
                    ) : (
                      produtos.map((p) => (
                        <tr key={p.id} className="hover:bg-gray-50">
                          <Cell>
                            <input
                              type="checkbox"
                              className="h-4 w-4 rounded border-gray-300"
                              checked={selecionados.has(p.id)}
                              onChange={(e) => {
                                const n = new Set(selecionados);
                                if (e.target.checked) n.add(p.id);
                                else n.delete(p.id);
                                setSelecionados(n);
                              }}
                            />
                          </Cell>
                          <Cell>{p.nome}</Cell>
                          <Cell className="text-xs">{p.marca || ""}</Cell>
                          <Cell className="text-xs">{p.status_cadastro === "em_revisao" ? "Em revisao" : p.status_cadastro || "Publicado"}</Cell>
                          <Cell className="text-xs text-gray-500">{p.external_id || ""}</Cell>
                          <Cell>{p.price_min != null ? `R$ ${p.price_min.toFixed(2)}` : "—"}</Cell>
                        </tr>
                      ))
                    )}
                  </TBody>
                </Table>

                <div className="mt-3 flex items-center justify-between text-sm">
                  <Button size="sm" disabled={pagina === 0} onClick={() => void carregarProdutos(sub.id, pagina - 1)}>
                    ← Anterior
                  </Button>
                  <span className="text-xs text-gray-500">
                    Página {pagina + 1} de {totalPaginas} · {prodTotal} produto(s)
                  </span>
                  <Button size="sm" disabled={pagina >= totalPaginas - 1} onClick={() => void carregarProdutos(sub.id, pagina + 1)}>
                    Próxima →
                  </Button>
                </div>
              </div>
            ) : cat ? (
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900">{cat.nome}</h2>
                  <span className="text-sm text-gray-500">
                    {cat.subcategorias.length} subcategorias · {cat.subcategorias.reduce((a, s) => a + s.product_count, 0)} produtos
                  </span>
                </div>
                <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-[minmax(180px,1fr)_minmax(220px,1fr)_auto_auto]">
                  <Input aria-label="Nome da categoria" value={rename} onChange={(e) => setRename(e.target.value)} />
                  <Select aria-label="Subgrupo da categoria" value={catSubgrupo} onChange={(e) => setCatSubgrupo(e.target.value)}>
                    <option value="">Sem grupo/subgrupo</option>
                    {grupos.map((grupo) => (
                      <optgroup key={grupo.id} label={`${grupo.codigo} - ${grupo.nome}`}>
                        {subgrupos.filter((subgrupo) => subgrupo.grupo_id === grupo.id).map((subgrupo) => (
                          <option key={subgrupo.id} value={subgrupo.id}>{subgrupo.codigo} - {subgrupo.nome}</option>
                        ))}
                      </optgroup>
                    ))}
                  </Select>
                  <Button size="sm" onClick={() => void renomearCategoria()}>
                    Salvar
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => void excluirCategoria()}>
                    Excluir categoria
                  </Button>
                </div>

                <div className="mb-2 text-sm font-semibold text-gray-700">Subcategorias</div>
                <div className="mb-3 flex gap-2">
                  <Input
                    placeholder="Nova subcategoria…"
                    value={novaSub}
                    onChange={(e) => setNovaSub(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && void addSub()}
                    className="max-w-xs"
                  />
                  <Button size="sm" variant="primary" onClick={() => void addSub()}>
                    Adicionar
                  </Button>
                </div>
                <div className="space-y-2">
                  {cat.subcategorias.map((s) => (
                    <div key={s.id} className="flex items-center gap-2">
                      <Input
                        value={subEdits[s.id] ?? s.nome}
                        onChange={(e) => setSubEdits({ ...subEdits, [s.id]: e.target.value })}
                        onKeyDown={(e) => e.key === "Enter" && void salvarSub(s.id)}
                        className="max-w-xs"
                      />
                      <span className="text-xs text-gray-500">{s.product_count} prods</span>
                      <Button size="sm" onClick={() => void salvarSub(s.id)}>
                        Salvar
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => void excluirSub(s.id)}>
                        ✕
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="py-16 text-center text-sm text-gray-400">
                Clique numa <b>categoria</b> para gerenciar, ou numa <b>subcategoria</b> para ver os produtos.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
