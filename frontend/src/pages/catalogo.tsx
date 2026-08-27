// pages/catalogo.tsx — catálogo (filtros + grid) em cards planos (um produto por card).

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
import { fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Field, Input, Loading, Modal, Select } from "../ui/ui";

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
  return s.toLowerCase().replace(/(^|\s|\/|\()([a-zà-ÿ])/g, (_m, sep: string, c: string) => sep + c.toUpperCase());
}

// ---------------- página ----------------

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
      .catch((e) => toast("Erro ao carregar catálogo: " + (e as Error).message, "error"))
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
          <h1 className="text-2xl font-semibold text-gray-900">Catálogo</h1>
          <p className="mt-1 text-sm text-gray-500">Consulte produtos e selecione quantidades para montar uma cotação.</p>
        </div>

        <div className="mb-4 flex flex-wrap items-end gap-3">
          <Field label="Buscar" className="min-w-[240px] flex-1">
            <Input placeholder="Nome, código, marca…" value={busca} onChange={(e) => onSearch(e.target.value)} />
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
              <option value="abc">Curva ABC (A → C)</option>
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
              Página {page} de {paginas} · {total} produto(s)
            </span>
            <div className="flex gap-1">
              <Button size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                «
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
                  if (inicio > 2) botoes.push(<span key="e1">…</span>);
                }
                for (let p = inicio; p <= fim; p++)
                  botoes.push(
                    <Button key={p} size="sm" variant={p === page ? "primary" : "secondary"} onClick={() => setPage(p)}>
                      {p}
                    </Button>
                  );
                if (fim < paginas) {
                  if (fim < paginas - 1) botoes.push(<span key="e2">…</span>);
                  botoes.push(
                    <Button key={paginas} size="sm" onClick={() => setPage(paginas)}>
                      {paginas}
                    </Button>
                  );
                }
                return botoes;
              })()}
              <Button size="sm" disabled={page >= paginas} onClick={() => setPage((p) => p + 1)}>
                »
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

function ProductCard({
  prod,
  qty,
  onSetQty,
  onOpen,
}: {
  prod: ProdutoResumo;
  qty: number;
  onSetQty: (q: number) => void;
  onOpen: () => void;
}) {
  return (
    <article className={`overflow-hidden rounded-lg border bg-white shadow-sm ${qty > 0 ? "border-brand-500 ring-1 ring-brand-500" : "border-gray-200"}`}>
      <div className="flex h-40 cursor-pointer items-center justify-center bg-gray-50 p-3" onClick={onOpen}>
        {prod.imagem_url ? (
          <img src={prod.imagem_url} loading="lazy" alt="" className="max-h-full max-w-full object-contain" />
        ) : (
          <span className="font-mono text-xs text-gray-400">sem imagem</span>
        )}
      </div>
      <div className="p-3">
        <p className="font-mono text-xs text-gray-500">
          {prod.classe_abc ? <Badge tone="blue">{prod.classe_abc}</Badge> : null} {prod.sku || "#" + prod.id}
        </p>
        <p className="mt-1 line-clamp-2 text-sm font-medium text-gray-900">{prod.name}</p>
        {prod.spec ? <p className="mt-0.5 line-clamp-1 text-xs text-gray-500">{prod.spec}</p> : null}
        {prod.brand ? <p className="text-xs text-gray-400">{prod.brand}</p> : null}
        <div className="mt-2 flex items-center justify-between">
          <p className="text-base font-semibold text-gray-900">{fmtMoney(prod.price)}</p>
          {prod.package_label ? <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{prod.package_label}</span> : null}
        </div>
        {qty > 0 ? <p className="mt-1 text-xs text-brand-700">{qty} no carrinho</p> : null}
      </div>
      <div className="flex items-center justify-between border-t border-gray-100 px-3 py-2">
        <Button size="sm" variant="ghost" onClick={() => onSetQty(Math.max(0, qty - 1))}>
          –
        </Button>
        <input
          type="number"
          min={0}
          className="w-16 rounded-md border border-gray-300 px-2 py-1 text-center text-sm focus:border-brand-500 focus:outline-none"
          value={qty}
          onChange={(e) => onSetQty(Math.max(0, parseInt(e.target.value, 10) || 0))}
        />
        <Button size="sm" variant="ghost" onClick={() => onSetQty(qty + 1)}>
          +
        </Button>
      </div>
    </article>
  );
}

function ModalProduto({ produtoId, onClose }: { produtoId: number; onClose: () => void }) {
  const [p, setP] = useState<ProdutoResumo | null>(null);
  const [qty, setQty] = useState(1);
  const [imgs, setImgs] = useState<string[]>([]);
  const [main, setMain] = useState("");

  useEffect(() => {
    void api
      .detalharProduto(produtoId)
      .then((prod) => {
        setP(prod);
        const arr = (prod as ProdutoResumo & { image_urls?: string[] }).image_urls || [];
        setImgs(arr);
        setMain(arr.length ? arr[0] : "");
      })
      .catch(() => toast("Erro ao carregar produto", "error"));
  }, [produtoId]);

  const adicionar = () => {
    if (!p) return;
    const q = Math.max(1, qty || 1);
    Cart.addItem(p.id, q, {
      name: p.name || "",
      spec: [(p as ProdutoResumo & { color?: string }).color].filter(Boolean).join(", "),
      brand: p.brand || "",
      price: p.price || 0,
      imagem_url: main || "",
    });
    onClose();
    toast(`${q} item(ns) adicionado(s) à sua cotação`, "success");
  };

  return (
    <Modal open onClose={onClose} title="Produto" footer={
      <>
        <Button onClick={onClose}>Fechar</Button>
        <Button variant="primary" onClick={adicionar}>
          Adicionar à cotação
        </Button>
      </>
    }>
      {!p ? (
        <Loading />
      ) : (
        <div>
          {main ? <img src={main} alt="" className="mx-auto max-h-56 object-contain" /> : null}
          {imgs.length > 1 && (
            <div className="mt-2 flex gap-2">
              {imgs.map((u, i) => (
                <img
                  key={i}
                  src={u}
                  onClick={() => setMain(u)}
                  className={`h-12 w-12 cursor-pointer rounded border object-contain ${main === u ? "border-brand-500" : "border-gray-200"}`}
                  alt=""
                />
              ))}
            </div>
          )}
          <p className="mt-3 font-mono text-xs text-gray-500">{p.sku || "#" + p.id}</p>
          <h3 className="text-base font-semibold text-gray-900">{p.name}</h3>
          {p.brand ? <div className="text-sm text-gray-500">Marca: {p.brand}</div> : null}
          {(p as ProdutoResumo & { color?: string }).color ? (
            <div className="text-sm text-gray-500">Cor: {(p as ProdutoResumo & { color?: string }).color}</div>
          ) : null}
          <div className="mt-2 text-lg font-semibold text-gray-900">{fmtMoney(p.price)}</div>
          {p.pix_price ? <div className="text-sm font-semibold text-emerald-600">PIX: {fmtMoney(p.pix_price)}</div> : null}
          {p.installment ? <div className="text-sm text-gray-500">{p.installment}</div> : null}
          <div className="mt-4 flex items-center gap-2">
            <Input type="number" min={1} step={1} value={qty} onChange={(e) => setQty(parseInt(e.target.value, 10) || 1)} className="w-24" />
            <span className="text-sm text-gray-500">unidade(s)</span>
          </div>
        </div>
      )}
    </Modal>
  );
}

