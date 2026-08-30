// pages/catalogo.tsx â€” catÃ¡logo (filtros + grid) em cards planos (um produto por card).

import { useEffect, useRef, useState } from "react";
import {
  api,
  type CategoriaMap,
  type ListCatalogo,
  type ProdutoResumo,
  type ResumoAbc,
  type DetalheCartItem,
} from "../api/client";
import * as Cart from "../cart";
import { toast } from "../ui/dom";
import { Button, Field, Input, Loading, Select } from "../ui/ui";
import { ProductCard } from "./catalogo/product-card";
import { ModalProduto } from "./catalogo/modal-produto";

const PAGE = 60;

function detFromItem(p: ProdutoResumo): Partial<DetalheCartItem> {
  return {
    name: p.name || "",
    spec: p.spec || "",
    brand: p.brand || "",
    price: p.price || 0,
    imagem_url: p.imagem_url || "",
  };
}

function titleCase(s: string): string {
  if (!s) return s;
  return s.toLowerCase().replace(/(^|\s|\/|\()([a-zÃ -Ã¿])/g, (_m, sep: string, c: string) => sep + c.toUpperCase());
}

// ---------------- pÃ¡gina ----------------

export default function Catalogo() {
  const [categorias, setCategorias] = useState<CategoriaMap>({});
  const [filters, setFilters] = useState({ categoria: "", subcategoria: "", q: "", classe: "", ordenar: "" });
  const [busca, setBusca] = useState("");
  const [items, setItems] = useState<ProdutoResumo[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [carregando, setCarregando] = useState(true);
  const [abc, setAbc] = useState<ResumoAbc | null>(null);
  const [draft, setDraft] = useState<Cart.CartDraft>(() => Cart.load());
  const [modalProduto, setModalProduto] = useState<number | null>(null);

  const sidebarRef = useRef<HTMLDivElement>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    void api
      .listarCategorias()
      .then(setCategorias)
      .catch(() => setCategorias({}));
  }, []);

  useEffect(() => {
    if (sidebarRef.current) Cart.mountSidebar(sidebarRef.current);
  }, []);

  useEffect(() => {
    const onUpdate = () => setDraft(Cart.load());
    document.addEventListener("cart:updated", onUpdate);
    return () => document.removeEventListener("cart:updated", onUpdate);
  }, []);

  useEffect(() => {
    let alive = true;
    setCarregando(true);
    api
      .listarProdutos({
        categoria: filters.categoria,
        subcategoria: filters.subcategoria,
        q: filters.q,
        classe: filters.classe,
        ordenar: filters.ordenar,
        offset: (page - 1) * PAGE,
        limit: PAGE,
      })
      .then((res: ListCatalogo) => {
        if (!alive) return;
        setItems(res.items as ProdutoResumo[]);
        setTotal(res.total);
      })
      .catch((e) => toast("Erro ao carregar catÃ¡logo: " + (e as Error).message, "error"))
      .finally(() => {
        if (alive) setCarregando(false);
      });
    return () => {
      alive = false;
    };
  }, [filters, page]);

  useEffect(() => {
    let alive = true;
    api
      .resumoAbc({ categoria: filters.categoria, subcategoria: filters.subcategoria, q: filters.q })
      .then((r) => {
        if (alive) setAbc(r);
      })
      .catch(() => {
        if (alive) setAbc(null);
      });
    return () => {
      alive = false;
    };
  }, [filters.categoria, filters.subcategoria, filters.q]);

  const onSearch = (v: string) => {
    setBusca(v);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      const q = v.trim();
      if (q.length > 0 && q.length < 3) {
        setFilters((f) => (f.q === "" ? f : { ...f, q: "" }));
      } else {
        setFilters((f) => ({ ...f, q }));
        setPage(1);
      }
    }, 300);
  };

  const setQty = (id: number, qty: number, det?: Partial<DetalheCartItem>) => {
    Cart.setQty(id, qty, det || {});
  };

  const limpar = () => {
    setFilters({ categoria: "", subcategoria: "", q: "", classe: "", ordenar: "" });
    setBusca("");
    setPage(1);
  };

  const paginas = Math.max(1, Math.ceil(total / PAGE));

  const subcategorias = filters.categoria
    ? categorias[filters.categoria] || []
    : [...new Set(Object.values(categorias).flat())];

  return (
    <div className="flex gap-6">
      <div className="min-w-0 flex-1">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-900">CatÃ¡logo</h1>
          <p className="mt-1 text-sm text-gray-500">Consulte produtos e selecione quantidades para montar uma cotaÃ§Ã£o.</p>
        </div>

        <div className="mb-4 flex flex-wrap items-end gap-3">
          <Field label="Buscar" className="min-w-[240px] flex-1">
            <Input placeholder="Nome, cÃ³digo, marcaâ€¦" value={busca} onChange={(e) => onSearch(e.target.value)} />
          </Field>
          <Field label="Categoria">
            <Select
              value={filters.categoria}
              onChange={(e) => setFilters((f) => ({ ...f, categoria: e.target.value, subcategoria: "" }))}
              className="w-40"
            >
              <option value="">Todas</option>
              {Object.keys(categorias)
                .sort()
                .map((cat) => (
                  <option key={cat} value={cat}>
                    {titleCase(cat)}
                  </option>
                ))}
            </Select>
          </Field>
          <Field label="Subcategoria">
            <Select value={filters.subcategoria} onChange={(e) => setFilters((f) => ({ ...f, subcategoria: e.target.value }))} className="w-44">
              <option value="">Todas</option>
              {subcategorias.slice().sort().map((s) => (
                <option key={s} value={s}>
                  {titleCase(s)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Curva ABC">
            <Select value={filters.classe} onChange={(e) => setFilters((f) => ({ ...f, classe: e.target.value }))} className="w-40">
              <option value="">Todas as classes</option>
              <option value="A">Classe A</option>
              <option value="B">Classe B</option>
              <option value="C">Classe C</option>
            </Select>
          </Field>
          <Field label="Ordenar por">
            <Select value={filters.ordenar} onChange={(e) => setFilters((f) => ({ ...f, ordenar: e.target.value }))} className="w-44">
              <option value="">Nome</option>
              <option value="abc">Curva ABC (A â†’ C)</option>
            </Select>
          </Field>
          <Button onClick={limpar}>Limpar filtros</Button>
          <span className="mb-2 text-sm text-gray-500">{total} produto(s)</span>
        </div>

        {abc && (
          <div className="mb-4 flex flex-wrap gap-2">
            {(["A", "B", "C"] as const).map((classe) => {
              const n = abc[classe];
              const tot = abc.A + abc.B + abc.C + abc.sem;
              const pct = tot ? Math.round((n / tot) * 100) : 0;
              return (
                <button
                  key={classe}
                  onClick={() => setFilters((f) => ({ ...f, classe: f.classe === classe ? "" : classe }))}
                  className={`rounded-full border px-3 py-1 text-xs font-medium ${
                    filters.classe === classe
                      ? "border-brand-600 bg-brand-600 text-white"
                      : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  Classe {classe}: <strong>{n}</strong> ({pct}%)
                </button>
              );
            })}
            {abc.sem > 0 && (
              <button
                onClick={() => setFilters((f) => ({ ...f, classe: "" }))}
                className={`rounded-full border px-3 py-1 text-xs font-medium ${
                  filters.classe === "" ? "border-brand-600 bg-brand-600 text-white" : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
                }`}
              >
                sem classe: <strong>{abc.sem}</strong> ({abc.A + abc.B + abc.C + abc.sem ? Math.round((abc.sem / (abc.A + abc.B + abc.C + abc.sem)) * 100) : 0}%)
              </button>
            )}
          </div>
        )}

        {carregando ? (
          <Loading />
        ) : items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
            <p>Nada encontrado</p>
            <p>Tente outro termo de busca ou categoria.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((p) => (
              <ProductCard
                key={p.id}
                prod={p}
                qty={draft.itens[p.id] || 0}
                onSetQty={(q) => setQty(p.id, q, detFromItem(p))}
                onOpen={() => setModalProduto(p.id)}
              />
            ))}
          </div>
        )}

        {paginas > 1 && (
          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-gray-500">
              PÃ¡gina {page} de {paginas} Â· {total} produto(s)
            </span>
            <div className="flex gap-1">
              <Button size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Â«
              </Button>
              {(() => {
                const inicio = Math.max(1, page - 3);
                const fim = Math.min(paginas, page + 3);
                const botoes = [];
                if (inicio > 1) {
                  botoes.push(
                    <Button key={1} size="sm" onClick={() => setPage(1)}>
                      1
                    </Button>
                  );
                  if (inicio > 2) botoes.push(<span key="e1">â€¦</span>);
                }
                for (let p = inicio; p <= fim; p++)
                  botoes.push(
                    <Button key={p} size="sm" variant={p === page ? "primary" : "secondary"} onClick={() => setPage(p)}>
                      {p}
                    </Button>
                  );
                if (fim < paginas) {
                  if (fim < paginas - 1) botoes.push(<span key="e2">â€¦</span>);
                  botoes.push(
                    <Button key={paginas} size="sm" onClick={() => setPage(paginas)}>
                      {paginas}
                    </Button>
                  );
                }
                return botoes;
              })()}
              <Button size="sm" disabled={page >= paginas} onClick={() => setPage((p) => p + 1)}>
                Â»
              </Button>
            </div>
          </div>
        )}
      </div>

      <div ref={sidebarRef} className="w-72 flex-none" />

      {modalProduto != null && <ModalProduto produtoId={modalProduto} onClose={() => setModalProduto(null)} />}
    </div>
  );
}

