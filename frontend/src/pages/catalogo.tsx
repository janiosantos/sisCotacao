// pages/catalogo.tsx — catálogo (filtros + grid) e seleção de variações por matriz.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type Atributo,
  type CatalogoItem,
  type CategoriaMap,
  type ListCatalogo,
  type ProdutoGrupo,
  type ProdutoResumo,
  type ResumoAbc,
  type Variante,
  type DetalheCartItem,
} from "../api/client";
import * as Cart from "../cart";
import { fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Field, Input, Loading, Modal, Select } from "../ui/ui";

const PAGE = 60;

// ---------------- matriz 2D de variações (utilidade) ----------------

function naturalCompare(a: string | number, b: string | number): number {
  const re = /(\d+)|(\D+)/g;
  const aParts = String(a).match(re) || [];
  const bParts = String(b).match(re) || [];
  const n = Math.max(aParts.length, bParts.length);
  for (let i = 0; i < n; i++) {
    const pa = aParts[i];
    const pb = bParts[i];
    if (pa == null) return -1;
    if (pb == null) return 1;
    const na = /^\d+$/.test(pa);
    const nb = /^\d+$/.test(pb);
    if (na && nb) {
      const d = Number(pa) - Number(pb);
      if (d) return d;
    } else {
      const d = pa.localeCompare(pb, "pt");
      if (d) return d;
    }
  }
  return 0;
}

function orderedOptions(attr: Atributo, vset: Variante[]): (string | number)[] {
  const seen = new Set<string>();
  const vals: (string | number)[] = [];
  (attr.options || []).forEach((o) => {
    const key = String(o);
    if (!seen.has(key)) {
      seen.add(key);
      vals.push(o);
    }
  });
  vset.forEach((v) => {
    const val = v.attrs ? v.attrs[String(attr.id)] : undefined;
    if (val == null) return;
    const key = String(val);
    if (!seen.has(key)) {
      seen.add(key);
      vals.push(val as string | number);
    }
  });
  return vals.sort(naturalCompare);
}

interface MatrixCell {
  colValue: string | null;
  variant: Variante | null;
}

interface MatrixRow {
  value: string | number;
  tip: string;
  cells: MatrixCell[];
}

interface MatrixResult {
  rowAttr: Atributo | null;
  colAttr: Atributo | null;
  rows: MatrixRow[];
}

function buildVariationMatrix(variations: Variante[], meta: { attrs?: Atributo[] }): MatrixResult {
  let attrs = (meta && meta.attrs) || [];
  let vset = variations || [];
  const usable = attrs.filter((a) => vset.some((v) => v.attrs && v.attrs[String(a.id)] != null));
  const DIM = /bitola|di[âa]metro|tamanho|medida|capacidade|pot[eê]ncia|tens[aã]o|voltagem|corrente|amperagem|comprimento|volume|peso|quantidade|rolo|embalagem|mm|w\b|litros|kg|metro|pol/i;

  let row: Atributo | null = null;
  let col: Atributo | null = null;
  if (usable.length === 1) {
    row = usable[0];
  } else if (usable.length >= 2) {
    const dims = usable.filter((a) => DIM.test(a.label || ""));
    row = dims[0] || usable[0];
    col = usable.find((a) => a.id !== row!.id) || null;
  }

  if (!row && vset.length > 1) {
    const fallback: Atributo = {
      id: -1,
      label: "Variação / SKU",
      options: vset.map((v) => v.sku || `#${v.id}`),
    };
    attrs = [fallback];
    vset = vset.map((v) => ({
      ...v,
      attrs: { ...(v.attrs || {}), "-1": v.sku || `#${v.id}` },
    }));
    row = fallback;
  }

  if (!row) {
    return { rowAttr: null, colAttr: null, rows: [] };
  }

  const rowValues = orderedOptions(row, vset);
  const colValues = col ? orderedOptions(col, vset) : ["_"];

  const cellMap: Record<string, Record<string, Variante>> = {};
  vset.forEach((v) => {
    const rv = v.attrs ? v.attrs[String(row.id)] : undefined;
    if (rv == null) return;
    const cv = col ? String(v.attrs?.[String(col.id)] ?? "_") : "_";
    const keyR = String(rv);
    cellMap[keyR] = cellMap[keyR] || {};
    const prev = cellMap[keyR][cv];
    if (!prev || (v.price != null && (prev.price == null || v.price < prev.price))) {
      cellMap[keyR][cv] = v;
    }
  });

  const rows: MatrixRow[] = rowValues.map((value) => ({
    value,
    tip: tipValor(row!.label || "", value),
    cells: colValues.map((cv) => ({
      colValue: cv === "_" ? null : String(cv),
      variant: cellMap[String(value)] && cellMap[String(value)][cv] ? cellMap[String(value)][cv] : null,
    })),
  }));

  return { rowAttr: row, colAttr: col, rows };
}

function freeCellKey(parts: Array<[number, string]>): string {
  return parts.map(([id, v]) => `${id}=${encodeURIComponent(v)}`).join("&");
}

function freeCellAttrs(key: string): Record<number, string> {
  const out: Record<number, string> = {};
  String(key)
    .split("&")
    .forEach((part) => {
      const eq = part.indexOf("=");
      if (eq <= 0) return;
      out[Number(part.slice(0, eq))] = decodeURIComponent(part.slice(eq + 1));
    });
  return out;
}

function cartItemKey(descricao: string): number {
  let h = 2166136261;
  for (let i = 0; i < descricao.length; i++) {
    h = Math.imul(h ^ descricao.charCodeAt(i), 16777619);
  }
  if (!h) h = 1;
  return -(Math.abs(h >>> 0) || 1);
}

// ---------------- tooltips educativos ----------------

const ATTR_TIPS: Record<string, string> = {
  bitola: "Bitola = seção do condutor. Quanto maior, maior a corrente que o cabo suporta.",
  diametro: "Diâmetro da peça (mm ou polegadas).",
  tamanho: "Tamanho / medida da peça.",
  medida: "Medida do produto.",
  tensao: "Tensão de operação. Confira a instalação: 127V ou 220V.",
  voltagem: "Tensão de operação (127V ou 220V).",
  potencia: "Consumo elétrico em watts. Mais watts = mais potência/brilho.",
  "temperatura de cor": "Tom da luz: fria (trabalho), neutra (áreas gerais), quente (conforto).",
  cor: "Cor da peça. Escolha a desejada.",
  capacidade: "Capacidade que o produto comporta (volume/massa).",
  embalagem: "Forma de venda (rolo inteiro ou avulso, por exemplo).",
};
const TIPS_VALORES: Record<string, Record<string, string>> = {
  bitola: {
    "1,5": "Ideal para iluminação",
    "2,5": "Tomadas de uso geral",
    "4": "Chuveiros até 5.500W",
    "6": "Chuveiros elétricos potentes",
    "10": "Torneiras elétricas / centrais",
  },
  tensao: {
    "127v": "Padrão residencial (110–127V)",
    "110v": "Padrão residencial (110–127V)",
    "220v": "Comum no interior do país (200–240V)",
    "220": "Comum no interior (200–240V)",
  },
  potencia: {
    "9w": "Menor consumo — áreas de convivência",
    "12w": "Mais brilho — áreas de trabalho",
  },
};

function normTip(s: unknown): string {
  return String(s || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function tipValor(attrLabel: string, valor: unknown): string {
  const al = normTip(attrLabel);
  const vk = Object.keys(TIPS_VALORES).find((k) => al.includes(k));
  if (vk) {
    const v = normTip(valor);
    const t = Object.keys(TIPS_VALORES[vk]).find((k) => v.includes(k) || k.includes(v));
    if (t) return TIPS_VALORES[vk][t];
  }
  const g = Object.keys(ATTR_TIPS).find((k) => al.includes(k));
  return g ? ATTR_TIPS[g] : "Especifique a característica para montar o pedido.";
}

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
  const [items, setItems] = useState<CatalogoItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [agrupado, setAgrupado] = useState(true);
  const [carregando, setCarregando] = useState(true);
  const [abc, setAbc] = useState<ResumoAbc | null>(null);
  const [draft, setDraft] = useState<Cart.CartDraft>(() => Cart.load());
  const [modalProduto, setModalProduto] = useState<number | null>(null);
  const [modalVariante, setModalVariante] = useState<ProdutoGrupo | null>(null);

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
        agrupado: agrupado ? 1 : 0,
      })
      .then((res: ListCatalogo) => {
        if (!alive) return;
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((e) => toast("Erro ao carregar catálogo: " + (e as Error).message, "error"))
      .finally(() => {
        if (alive) setCarregando(false);
      });
    return () => {
      alive = false;
    };
  }, [filters, page, agrupado]);

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
          <Button onClick={() => setAgrupado((a) => !a)}>{agrupado ? "Ver todas as opções" : "Ver por produto"}</Button>
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
            {items.map((p) =>
              "group" in p && p.group ? (
                <GroupCard key={p.id} p={p as ProdutoGrupo} draft={draft} onOpen={() => setModalVariante(p as ProdutoGrupo)} />
              ) : (
                <ProductCard
                  key={p.id}
                  prod={p as ProdutoResumo}
                  qty={draft.itens[p.id] || 0}
                  onSetQty={(q) => setQty(p.id, q, detFromItem(p as ProdutoResumo))}
                  onOpen={() => setModalProduto(p.id)}
                />
              )
            )}
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
      {modalVariante != null && <ModalVariante p={modalVariante} onClose={() => setModalVariante(null)} />}
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

function GroupCard({ p, draft, onOpen }: { p: ProdutoGrupo; draft: Cart.CartDraft; onOpen: () => void }) {
  const naDraft = p.variants.reduce((s, v) => s + (draft.itens[v.id] || 0), 0);
  const pkgLabel = p.package_label || "";
  const priceLabel = p.price_min !== p.price_max ? `a partir de ${fmtMoney(p.price_min)}` : fmtMoney(p.price_min);
  return (
    <article className={`overflow-hidden rounded-lg border bg-white shadow-sm ${naDraft > 0 ? "border-brand-500 ring-1 ring-brand-500" : "border-gray-200"}`}>
      <div className="flex h-40 cursor-pointer items-center justify-center bg-gray-50 p-3" onClick={onOpen}>
        {p.imagem_url ? (
          <img src={p.imagem_url} loading="lazy" alt="" className="max-h-full max-w-full object-contain" />
        ) : (
          <span className="font-mono text-xs text-gray-400">sem imagem</span>
        )}
      </div>
      <div className="p-3">
        <p className="font-mono text-xs text-gray-500">
          {p.classe_abc ? <Badge tone="blue">{p.classe_abc}</Badge> : null}{" "}
          {pkgLabel ? <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{pkgLabel}</span> : null} {p.variant_count} variações
        </p>
        <p className="mt-1 line-clamp-2 text-sm font-medium text-gray-900">{p.name}</p>
        <p className="mt-2 text-base font-semibold text-gray-900">{priceLabel}</p>
      </div>
      <div className="border-t border-gray-100 p-3">
        <Button variant="primary" className="w-full" onClick={onOpen}>
          {naDraft > 0 ? `${naDraft} no carrinho · ` : ""}Escolher variação
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

function ModalVariante({ p, onClose }: { p: ProdutoGrupo; onClose: () => void }) {
  const variants = p.variants || [];
  const brands = p.brands && p.brands.length ? p.brands.slice() : [];
  const [selBrand, setSelBrand] = useState<string | null>(brands.length ? brands[0] : null);
  const [qtys, setQtys] = useState<Record<number, number>>({});
  const [freeQtys, setFreeQtys] = useState<Record<string, number>>({});
  const [addedRows, setAddedRows] = useState<string[]>([]);
  const [addedCols, setAddedCols] = useState<string[]>([]);
  const [addedQtys, setAddedQtys] = useState<Record<string, number>>({});

  const allById: Record<number, Variante> = {};
  variants.forEach((v) => {
    allById[v.id] = v;
  });
  const pkgLabel = p.package_label || "";

  const filtered = () => (selBrand ? variants.filter((v) => (v.brand || "") === selBrand) : variants);

  const m = useMemo(() => buildVariationMatrix(filtered(), { attrs: p.attrs || [] }), [selBrand]);

  function melhorPrecoUn(lista: Variante[]): number | null {
    const prices = lista.map((v) => v.price).filter((x) => x != null && x > 0);
    return prices.length ? Math.min(...prices) : null;
  }

  function fornecedorSugerido(): string | null {
    const pesos: Record<string, number> = {};
    Object.entries(qtys).forEach(([id, q]) => {
      if (!q) return;
      const v = allById[Number(id)];
      if (!v) return;
      (v.fornecedores || []).forEach((n) => {
        pesos[n] = (pesos[n] || 0) + q;
      });
    });
    const best = Object.entries(pesos).sort((a, b) => b[1] - a[1])[0];
    return best ? best[0] : null;
  }

  function subtotal(): number {
    return Object.entries(qtys).reduce((s, [id, q]) => {
      if (!q) return s;
      const v = allById[Number(id)];
      return v ? s + (v.price || 0) * q : s;
    }, 0);
  }

  function simKey(rowVal: string | number, colVal: string | number | null): string {
    const parts: Array<[number, string]> = [[m.rowAttr!.id, String(rowVal)]];
    if (m.colAttr && colVal != null) parts.push([m.colAttr.id, String(colVal)]);
    return freeCellKey(parts);
  }

  const allRowValues = () => [...m.rows.map((r) => String(r.value)), ...addedRows];
  const allColValues = () => {
    if (!m.colAttr) return [];
    const existing = m.rows.length ? m.rows[0].cells.map((c) => c.colValue).filter((v): v is string => v != null) : [];
    return [...existing, ...addedCols];
  };

  const adicionar = () => {
    const selecionadas = Object.entries(qtys).filter(([, q]) => q > 0);
    const livreSel = Object.entries(freeQtys).filter(([, q]) => q > 0);
    const addedSel = Object.entries(addedQtys).filter(([, q]) => q > 0);
    if (!selecionadas.length && !livreSel.length && !addedSel.length) {
      toast("Digite ao menos uma quantidade na matriz", "error");
      return;
    }
    let totalAdd = 0;
    selecionadas.forEach(([id, q]) => {
      const v = allById[Number(id)];
      if (!v) return;
      const specs: string[] = [];
      (p.attrs || []).forEach((a) => {
        const val = v.attrs ? v.attrs[String(a.id)] : undefined;
        if (val != null && String(val) !== "") specs.push(String(val));
      });
      Cart.addItem(v.id, q, {
        name: p.name || "",
        spec: specs.join(" · "),
        brand: v.brand || "",
        price: v.price || 0,
        imagem_url: v.imagem_url || p.imagem_url || "",
      });
      totalAdd += q;
    });
    const addCustom = (key: string, q: number) => {
      const attrs = freeCellAttrs(key);
      const specs: string[] = [];
      (p.attrs || []).forEach((a) => {
        const val = attrs[a.id];
        if (val != null && val !== "") specs.push(`${a.label}: ${val}`);
      });
      const descricao = specs.join(" · ") || p.name || "";
      Cart.addCustomItem(cartItemKey(key), q, {
        name: p.name || "",
        spec: specs.join(" · "),
        brand: selBrand || "",
        price: 0,
        imagem_url: p.imagem_url || "",
        custom: true,
        descricao,
        produto_pai: p.id,
        marca: selBrand || "",
        atributos: { ...attrs },
      });
      totalAdd += q;
    };
    livreSel.forEach(([key, q]) => addCustom(key, q));
    addedSel.forEach(([key, q]) => addCustom(key, q));
    onClose();
    toast(`${totalAdd} item(ns) adicionado(s) à sua cotação`, "success");
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={p.name}
      wide
      footer={
        <div className="flex w-full items-center justify-between gap-4">
          <div className="flex flex-wrap gap-4 text-sm">
            <span>
              Subtotal estimado <strong>{fmtMoney(subtotal())}</strong>
            </span>
            <span>Melhor preço / un <strong>{melhorPrecoUn(filtered()) != null ? `${fmtMoney(melhorPrecoUn(filtered()))} / un` : "—"}</strong></span>
            <span>Fornecedor sugerido <strong>{fornecedorSugerido() || "— (definir na cotação)"}</strong></span>
          </div>
          <Button variant="primary" onClick={adicionar}>
            Adicionar à cotação
          </Button>
        </div>
      }
    >
      <div className="mb-2 flex items-center gap-3">
        {p.imagem_url ? <img src={p.imagem_url} alt="" className="h-14 w-14 object-contain" /> : <span className="h-14 w-14" />}
        <div>
          <div className="text-sm text-gray-500">
            {pkgLabel ? <span className="mr-2 rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{pkgLabel}</span> : null}
            Preencha a quantidade desejada em cada célula. Vazio ou 0 = não selecionado.
          </div>
        </div>
      </div>

      {brands.length ? (
        <div className="mb-3 flex flex-wrap gap-1">
          {brands.map((b) => (
            <button
              key={b}
              onClick={() => setSelBrand(b)}
              className={`rounded-full border px-3 py-1 text-xs font-medium ${
                b === selBrand ? "border-brand-600 bg-brand-600 text-white" : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              {b}
            </button>
          ))}
        </div>
      ) : null}

      {!m.rowAttr ? (
        <div className="py-8 text-center text-sm text-gray-400">Sem variações para esta marca.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="border border-gray-200 bg-gray-50 px-3 py-2 text-left text-xs font-semibold text-gray-600">
                  {m.rowAttr.label || "Característica"} <span title={tipValor(m.rowAttr.label || "", "")}>?</span>
                </th>
                {m.colAttr ? (
                  <>
                    <th colSpan={allColValues().length} className="border border-gray-200 bg-gray-50 px-3 py-2 text-left text-xs font-semibold text-gray-600">
                      {m.colAttr.label} <span title={tipValor(m.colAttr.label, "")}>?</span>
                    </th>
                    <th className="border border-gray-200 bg-gray-50 px-3 py-2" />
                  </>
                ) : (
                  <th className="border border-gray-200 bg-gray-50 px-3 py-2 text-left text-xs font-semibold text-gray-600">Quantidade</th>
                )}
              </tr>
              {m.colAttr && (
                <tr>
                  <th className="border border-gray-200 bg-gray-50" />
                  {allColValues().map((cv) => (
                    <th key={cv} className="border border-gray-200 bg-gray-50 px-3 py-2 text-xs font-medium text-gray-600">
                      {cv}
                      {addedCols.includes(cv) && (
                        <button className="ml-1 text-gray-400 hover:text-red-600" onClick={() => setAddedCols((c) => c.filter((x) => x !== cv))}>
                          ×
                        </button>
                      )}
                    </th>
                  ))}
                  <th className="border border-gray-200 bg-gray-50 px-3 py-2">
                    <button
                      className="text-gray-500 hover:text-brand-600"
                      title={`Adicionar ${m.colAttr?.label || "coluna"}`}
                      onClick={() => {
                        const val = window.prompt(`Nova ${m.colAttr?.label || "coluna"}:`);
                        if (val && val.trim()) setAddedCols((c) => [...c, val.trim()]);
                      }}
                    >
                      +
                    </button>
                  </th>
                </tr>
              )}
            </thead>
            <tbody>
              {allRowValues().map((rv) => {
                const orig = m.rows.find((r) => String(r.value) === rv);
                const cells = m.colAttr
                  ? allColValues().map((cv) => {
                      const existing = orig?.cells.find((c) => c.colValue === cv);
                      if (existing?.variant)
                        return (
                          <td key={cv} className="border border-gray-200 px-3 py-2">
                            <QtyInput
                              value={qtys[existing.variant.id] || ""}
                              onChange={(v) => setQtys({ ...qtys, [existing.variant!.id]: v })}
                              price={existing.variant.price}
                            />
                          </td>
                        );
                      const key = simKey(rv, cv);
                      if (existing) return <td key={cv} className="border border-gray-200 px-3 py-2"><QtyInput value={freeQtys[key] || ""} onChange={(v) => setFreeQtys({ ...freeQtys, [key]: v })} /></td>;
                      return <td key={cv} className="border border-gray-200 px-3 py-2"><QtyInput value={addedQtys[key] || ""} onChange={(v) => setAddedQtys({ ...addedQtys, [key]: v })} /></td>;
                    })
                  : [<td key="q" className="border border-gray-200 px-3 py-2">{orig && orig.cells[0].variant ? <QtyInput value={qtys[orig.cells[0].variant.id] || ""} onChange={(v) => setQtys({ ...qtys, [orig.cells[0].variant!.id]: v })} price={orig.cells[0].variant.price} /> : <QtyInput value={freeQtys[simKey(rv, null)] || ""} onChange={(v) => setFreeQtys({ ...freeQtys, [simKey(rv, null)]: v })} />}</td>];
                return (
                  <tr key={rv}>
                    <td className="border border-gray-200 px-3 py-2">
                      <span className="font-medium">{rv}</span>
                      {addedRows.includes(rv) && (
                        <button className="ml-1 text-gray-400 hover:text-red-600" onClick={() => setAddedRows((r) => r.filter((x) => x !== rv))}>
                          ×
                        </button>
                      )}
                      {!addedRows.includes(rv) && tipValor(m.rowAttr!.label || "", rv) ? (
                        <span className="ml-1 text-gray-400" title={tipValor(m.rowAttr!.label || "", rv)}>
                          ?
                        </span>
                      ) : null}
                    </td>
                    {cells}
                    {m.colAttr && <td className="border border-gray-200 bg-gray-50" />}
                  </tr>
                );
              })}
              <tr>
                <td colSpan={m.colAttr ? allColValues().length + 2 : 2} className="border border-gray-200 px-3 py-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      const val = window.prompt(`Nova ${m.rowAttr?.label || "linha"}:`);
                      if (val && val.trim()) setAddedRows((r) => [...r, val.trim()]);
                    }}
                  >
                    + Adicionar nova {m.rowAttr?.label || "linha"}
                  </Button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}

function QtyInput({ value, onChange, price }: { value: string | number; onChange: (v: number) => void; price?: number }) {
  return (
    <div className="w-24">
      <input
        type="number"
        min={0}
        step={1}
        value={value}
        placeholder="0"
        inputMode="numeric"
        onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)}
        className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none"
      />
      <div className="mt-0.5 text-xs text-gray-500">{price != null ? fmtMoney(price) : "sob consulta"}</div>
    </div>
  );
}
