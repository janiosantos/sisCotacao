// pages/produtos.tsx — cadastro de produtos (famílias + produto pai + variações + imagens).

import { useEffect, useRef, useState } from "react";
import {
  api,
  type Familia,
  type FamiliaAtributo,
  type FamiliaPayload,
  type Fornecedor,
  type FornecedorVariantePayload,
  type ItemListaCadastro,
  type ProdutoCadastro,
  type ProdutoCadastroPayload,
  type ProdutoPreview,
  type UnidadeCompra,
} from "../api/client";
import { fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Field, Input, Loading, Modal, PageHeader, Select, Textarea } from "../ui/ui";

const PAGE = 60;

interface VarianteLocal {
  id?: number;
  sku: string;
  ean: string;
  preco: string | number;
  prom: string | number;
  peso: string | number;
  dimensoes: string;
  unidade_venda: string;
  embalagem: string | number;
  fator_conversao: string | number;
  localizacao: string;
  ncm: string;
  unidade_tributavel: string;
  valores: Record<string, string>;
}

interface FornecedorRow {
  uid: string;
  fornecedor_id: string;
  codigo: string;
  unidade: string;
  fator: string | number;
  variante_idx: number;
}

const PADRAO_ATTRS = [
  "bitola", "tensao", "tensão", "capacidade", "potencia", "potência",
  "vazao", "vazão", "diametro", "diâmetro", "material", "cor",
  "espessura", "comprimento", "tamanho", "medida", "rolo", "voltagem",
];
const CA_RE = /(^|[^a-z0-9])(n\s?[º°]?\s?ca|ca|certificado|aprovacao)([^a-z0-9]|$)/i;

function normalize(str: string): string {
  return String(str || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function ehAttrPadrao(nome: string): boolean {
  const n = normalize(nome);
  if (CA_RE.test(nome)) return true;
  return PADRAO_ATTRS.some((k) => n.includes(k));
}

function cartesiano(arrays: string[][]): string[][] {
  return arrays.reduce((acc, cur) => acc.flatMap((a) => cur.map((c) => [...a, c])), [[]] as string[][]);
}

function varianteLabel(v: VarianteLocal, atributos: FamiliaAtributo[], idx: number): string {
  return atributos.map((a) => v.valores[String(a.id)]).filter(Boolean).join(" · ") || `Variação ${idx + 1}`;
}

// ===================================================================
// LISTA
// ===================================================================

export default function Produtos() {
  const [familias, setFamilias] = useState<Familia[]>([]);
  const [categoriasTree, setCategoriasTree] = useState<Record<string, string[]>>({});
  const [filters, setFilters] = useState({ q: "", categoria: "", subcategoria: "" });
  const [busca, setBusca] = useState("");
  const [items, setItems] = useState<ItemListaCadastro[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [carregando, setCarregando] = useState(true);
  const [modalFamilias, setModalFamilias] = useState(false);
  const [modalUrl, setModalUrl] = useState(false);
  const [modalEtiquetas, setModalEtiquetas] = useState(false);

  const searchTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const carregarFamilias = async () => {
    try {
      setFamilias(await api.listarFamilias());
    } catch {
      setFamilias([]);
    }
  };

  useEffect(() => {
    void carregarFamilias();
    void api
      .listarCategorias()
      .then(setCategoriasTree)
      .catch(() => setCategoriasTree({}));
  }, []);

  useEffect(() => {
    let alive = true;
    setCarregando(true);
    api
      .listarProdutosCadastro({
        q: filters.q,
        categoria: filters.categoria || undefined,
        subcategoria: filters.subcategoria || undefined,
        offset: (page - 1) * PAGE,
        limit: PAGE,
      })
      .then((res) => {
        if (!alive) return;
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((e) => toast("Erro ao carregar produtos: " + (e as Error).message, "error"))
      .finally(() => {
        if (alive) setCarregando(false);
      });
    return () => {
      alive = false;
    };
  }, [filters, page]);

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

  const excluir = async (id: number) => {
    if (!window.confirm("Excluir este produto e todas as suas variações e imagens?")) return;
    try {
      const res = await api.excluirProdutoCadastro(id);
      if (res.desativadas > 0) {
        toast(`Produto desativado (não excluído): ${res.desativadas} variação(ões) possuem estoque/preço/fornecedor e foram preservadas.`, "warn");
      } else {
        toast("Produto excluído", "success");
      }
      setPage(1);
      // força recarga
      setFilters((f) => ({ ...f }));
    } catch (e) {
      toast("Erro ao excluir: " + (e as Error).message, "error");
    }
  };

  const subcategorias = filters.categoria ? categoriasTree[filters.categoria] || [] : [];

  return (
    <div>
      <PageHeader title="Produtos" subtitle="Cadastre produtos por família e geração de variações (modelo TOTVS)." />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Buscar" className="min-w-[240px] flex-1">
          <Input placeholder="Nome, marca, código…" value={busca} onChange={(e) => onSearch(e.target.value)} />
        </Field>
        <Field label="Categoria">
          <Select value={filters.categoria} onChange={(e) => setFilters((f) => ({ ...f, categoria: e.target.value, subcategoria: "" }))} className="w-44">
            <option value="">Todas</option>
            {Object.keys(categoriasTree)
              .sort()
              .map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
          </Select>
        </Field>
        <Field label="Subcategoria">
          <Select value={filters.subcategoria} onChange={(e) => setFilters((f) => ({ ...f, subcategoria: e.target.value }))} className="w-44">
            <option value="">Todas</option>
            {subcategorias.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
        </Field>
        <Button variant="outline" onClick={() => setModalFamilias(true)}>
          Famílias
        </Button>
        <Button variant="outline" onClick={() => setModalEtiquetas(true)}>
          Etiquetas
        </Button>
        <Button variant="outline" onClick={() => setModalUrl(true)}>
          Novo via URL
        </Button>
        <Button variant="primary" onClick={() => (location.hash = "#/produtos/novo")}>
          Novo produto
        </Button>
        <span className="mb-2 text-sm text-gray-500">{total} produto(s)</span>
      </div>

      {carregando ? (
        <Loading />
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          {filters.q ? (
            <>
              <p>Nenhum produto encontrado para a busca.</p>
              <p>Confira os termos digitados ou busque por SKU/EAN.</p>
            </>
          ) : (
            <>
              <p>Nenhum produto cadastrado</p>
              <p>Clique em "Novo produto" para começar.</p>
            </>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((p) => (
            <article key={p.id} className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
              <div className="flex h-40 items-center justify-center bg-gray-50 p-3">
                {p.imagem_url ? <img src={p.imagem_url} loading="lazy" alt="" className="max-h-full max-w-full object-contain" /> : <span className="font-mono text-xs text-gray-400">sem imagem</span>}
              </div>
              <div className="p-3">
                <p className="text-xs text-gray-500">
                  <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-600">
                    {p.categoria || p.familia_nome || "Sem categoria"}
                    {p.subcategoria ? ` / ${p.subcategoria}` : ""}
                  </span>{" "}
                  {p.variant_count} variações {p.classe_abc ? <Badge tone="blue">{p.classe_abc}</Badge> : null}
                </p>
                <p className="mt-1 line-clamp-2 text-sm font-medium text-gray-900">{p.nome}</p>
                {p.marca ? <p className="text-xs text-gray-400">{p.marca}</p> : null}
                <p className="mt-2 text-sm font-semibold text-gray-900">{p.price_min ? `a partir de ${fmtMoney(p.price_min)}` : "sem preço"}</p>
              </div>
              <div className="flex gap-2 border-t border-gray-100 p-3">
                <Button variant="primary" size="sm" className="flex-1" onClick={() => (location.hash = `#/produtos/${p.id}`)}>
                  Editar
                </Button>
                <Button variant="danger" size="sm" onClick={() => void excluir(p.id)}>
                  Excluir
                </Button>
              </div>
            </article>
          ))}
        </div>
      )}

      {total > PAGE && (
        <div className="mt-6 flex items-center gap-1">
          <Button size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            «
          </Button>
          <span className="px-2 text-sm text-gray-500">
            Página {page} de {Math.ceil(total / PAGE)}
          </span>
          <Button size="sm" disabled={page >= Math.ceil(total / PAGE)} onClick={() => setPage((p) => p + 1)}>
            »
          </Button>
        </div>
      )}

      <ModalFamilias familias={familias} open={modalFamilias} onClose={() => setModalFamilias(false)} onChanged={carregarFamilias} />
      <ModalImportarUrl open={modalUrl} onClose={() => setModalUrl(false)} />
      <ModalEtiquetas open={modalEtiquetas} onClose={() => setModalEtiquetas(false)} />
    </div>
  );
}

// ===================================================================
// FAMÍLIAS
// ===================================================================

function ModalFamilias({
  familias,
  open,
  onClose,
  onChanged,
}: {
  familias: Familia[];
  open: boolean;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [formDe, setFormDe] = useState<Familia | null | undefined>(undefined);

  return (
    <>
      <Modal
        open={open && formDe === undefined}
        onClose={onClose}
        title="Famílias"
        footer={
          <>
            <Button onClick={onClose}>Fechar</Button>
            <Button variant="primary" onClick={() => setFormDe(null)}>
              Nova família
            </Button>
          </>
        }
      >
        {familias.length === 0 ? (
          <p className="py-6 text-center text-sm text-gray-400">Nenhuma família cadastrada ainda.</p>
        ) : (
          <div className="space-y-2">
            {familias.map((f) => (
              <div key={f.id} className="flex items-center gap-2 rounded-md border border-gray-100 p-2">
                <div className="flex-1">
                  <strong className="text-sm">{f.nome}</strong>
                  <div className="text-xs text-gray-400">
                    {f.atributos.length} atributo(s): {f.atributos.map((a) => a.nome).join(", ")}
                  </div>
                </div>
                <Button size="sm" onClick={() => setFormDe(f)}>
                  Editar
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  onClick={async () => {
                    if (!window.confirm(`Excluir a família "${f.nome}"?`)) return;
                    try {
                      await api.excluirFamilia(f.id);
                      toast("Família excluída", "success");
                      onChanged();
                    } catch (e) {
                      toast("Erro: " + (e as Error).message, "error");
                    }
                  }}
                >
                  Excluir
                </Button>
              </div>
            ))}
          </div>
        )}
      </Modal>

      {formDe !== undefined && (
        <ModalFamiliaForm
          familia={formDe}
          onClose={() => setFormDe(undefined)}
          onSaved={() => {
            setFormDe(undefined);
            onChanged();
          }}
        />
      )}
    </>
  );
}

function ModalFamiliaForm({ familia, onClose, onSaved }: { familia: Familia | null; onClose: () => void; onSaved: () => void }) {
  const [nome, setNome] = useState(familia?.nome ?? "");
  const [descricao, setDescricao] = useState(familia?.descricao ?? "");
  const [ncm, setNcm] = useState(familia?.ncm_padrao ?? "");
  const [unidade, setUnidade] = useState(familia?.unidade_padrao ?? "UN");
  const [atributos, setAtributos] = useState<{ id: number | null; nome: string; tipo: "lista" | "livre"; opcoes: string[]; obrigatorio: boolean }[]>(() => {
    const a = (familia ? familia.atributos : []).map((x) => ({ id: x.id, nome: x.nome, tipo: x.tipo, opcoes: x.opcoes || [], obrigatorio: !!x.obrigatorio }));
    return a.length ? a : [{ id: null, nome: "", tipo: "lista", opcoes: [], obrigatorio: false }];
  });

  const salvar = async () => {
    if (!nome.trim()) {
      toast("Informe o nome da família", "error");
      return;
    }
    const payload: FamiliaPayload = {
      nome: nome.trim(),
      descricao: descricao.trim(),
      ncm_padrao: ncm.trim(),
      unidade_padrao: unidade.trim() || "UN",
      atributos: atributos
        .map((a) => ({ id: a.id, nome: a.nome.trim(), tipo: a.tipo, opcoes: a.opcoes, obrigatorio: a.obrigatorio }))
        .filter((a) => a.nome),
    };
    try {
      if (familia) await api.atualizarFamilia(familia.id, payload);
      else await api.criarFamilia(payload);
      toast("Família salva", "success");
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={familia ? "Editar família" : "Nova família"}
      wide
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void salvar()}>
            Salvar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Nome da família *">
          <Input placeholder="Ex.: Cabo Flexível, Parafuso, Cola" value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </Field>
        <Field label="Descrição (opcional)">
          <Input value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="NCM padrão">
            <Input maxLength={8} placeholder="Ex.: 8536.69.90" value={ncm} onChange={(e) => setNcm(e.target.value)} />
          </Field>
          <Field label="Unidade padrão">
            <Input placeholder="UN, PC, MT, RL…" value={unidade} onChange={(e) => setUnidade(e.target.value)} />
          </Field>
        </div>
        <Field label="Atributos (características das variações)">
          <div className="space-y-2">
            {atributos.map((a, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input className="flex-1" placeholder="Nome do atributo (ex.: Cor)" value={a.nome} onChange={(e) => setAtributos((arr) => arr.map((x, j) => (j === i ? { ...x, nome: e.target.value } : x)))} />
                <Select
                  className="w-40"
                  value={a.tipo}
                  onChange={(e) => setAtributos((arr) => arr.map((x, j) => (j === i ? { ...x, tipo: e.target.value as "lista" | "livre" } : x)))}
                >
                  <option value="lista">Lista de opções</option>
                  <option value="livre">Valor livre</option>
                </Select>
                <Input className="flex-1" placeholder="azul, vermelho, preto (separado por vírgula)" value={a.opcoes.join(", ")} onChange={(e) => setAtributos((arr) => arr.map((x, j) => (j === i ? { ...x, opcoes: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) } : x)))} />
                <label className="flex items-center gap-1 whitespace-nowrap text-xs text-gray-600">
                  <input type="checkbox" checked={a.obrigatorio} onChange={(e) => setAtributos((arr) => arr.map((x, j) => (j === i ? { ...x, obrigatorio: e.target.checked } : x)))} />
                  Obrig.
                </label>
                <button className="text-gray-400 hover:text-red-600" onClick={() => setAtributos((arr) => arr.filter((_, j) => j !== i))}>
                  ×
                </button>
              </div>
            ))}
          </div>
          <Button size="sm" variant="ghost" className="mt-2" onClick={() => setAtributos((arr) => [...arr, { id: null, nome: "", tipo: "lista", opcoes: [], obrigatorio: false }])}>
            + Adicionar atributo
          </Button>
        </Field>
      </div>
    </Modal>
  );
}

// ===================================================================
// IMPORTAR POR URL
// ===================================================================

function ModalImportarUrl({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [url, setUrl] = useState("");
  const [parsed, setParsed] = useState<ProdutoPreview | null>(null);
  const [analisando, setAnalisando] = useState(false);
  const [cadastrando, setCadastrando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (open) {
      setUrl("");
      setParsed(null);
      setErro("");
    }
  }, [open]);

  const analisar = async () => {
    if (!url.trim()) {
      toast("Informe a URL do produto", "error");
      return;
    }
    setAnalisando(true);
    setErro("");
    setParsed(null);
    try {
      setParsed(await api.parseUrlProduto(url.trim()));
      toast("Produto identificado", "success");
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setAnalisando(false);
    }
  };

  const cadastrar = async () => {
    if (!parsed) return;
    setCadastrando(true);
    try {
      const res = await api.criarProdutoPorUrl(parsed.url);
      onClose();
      toast(`Produto cadastrado (${res.imagens_baixadas} foto(s) baixada(s))`, "success");
      if (res.imagens_erros) toast(`${res.imagens_erros} foto(s) não puderam ser baixadas`, "error");
      location.hash = `#/produtos/${res.id}`;
    } catch (e) {
      toast("Erro ao cadastrar: " + (e as Error).message, "error");
      setCadastrando(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Cadastrar a partir de URL"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button onClick={() => void analisar()} disabled={analisando}>
            {analisando ? "Analisando…" : "Analisar URL"}
          </Button>
          {parsed && (
            <Button variant="primary" onClick={() => void cadastrar()} disabled={cadastrando}>
              {cadastrando ? "Cadastrando…" : "Cadastrar produto"}
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-3">
        <Field label="URL do produto">
          <Input placeholder="https://www.casadoeletricistasc.com.br/..." value={url} onChange={(e) => setUrl(e.target.value)} />
        </Field>
        <p className="text-xs text-gray-500">O sistema lê a página e cria automaticamente a família, os atributos e baixa as fotos. Você confere o resultado antes de confirmar.</p>
        {erro ? <p className="text-sm text-gray-400">Erro: {erro}</p> : null}
        {parsed && (
          <div className="rounded-lg border border-gray-200 p-3 text-sm">
            <PreviewRow k="Produto" v={parsed.nome} />
            <PreviewRow k="Marca" v={parsed.marca} />
            <PreviewRow k="SKU / EAN" v={[parsed.sku, parsed.ean].filter(Boolean).join(" / ")} />
            <PreviewRow k="Família" v={parsed.familia_nome} />
            <PreviewRow k="Preço" v={parsed.preco != null ? fmtMoney(parsed.preco) : "—"} />
            <PreviewRow k="À vista (PIX)" v={parsed.preco_pix != null ? fmtMoney(parsed.preco_pix) : "—"} />
            <PreviewRow k="De" v={parsed.preco_de != null ? fmtMoney(parsed.preco_de) : "—"} />
            <PreviewRow k="Parcelamento" v={parsed.parcelamento} />
            <PreviewRow k="Fotos" v={String(parsed.fotos)} />
            {(parsed.atributos || []).length > 0 && (
              <div className="flex gap-2 border-t border-gray-100 py-2">
                <span className="w-36 text-gray-500">Atributos</span>
                <span>{parsed.atributos?.map((a) => `${a.label}: ${a.valor}`).join(" · ")}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

function PreviewRow({ k, v }: { k: string; v?: string | null }) {
  if (!v) return null;
  return (
    <div className="flex gap-2 border-b border-gray-100 py-1.5">
      <span className="w-36 text-gray-500">{k}</span>
      <span className="font-medium">{v}</span>
    </div>
  );
}

// ===================================================================
// ETIQUETAS
// ===================================================================

function ModalEtiquetas({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [ids, setIds] = useState("");
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Etiquetas de preço"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button
            variant="primary"
            onClick={() => {
              const texto = ids.trim();
              if (!texto) {
                toast("Informe ao menos um ID", "error");
                return;
              }
              const idList = texto.split(",").map((s) => s.trim()).filter(Boolean).join(",");
              window.open(`/etiquetas/imprimir?ids=${idList}`, "_blank");
            }}
          >
            Gerar etiquetas
          </Button>
        </>
      }
    >
      <p className="mb-3 text-sm text-gray-500">Informe os IDs das variantes (separados por vírgula) para gerar a folha de etiquetas.</p>
      <Field label="IDs das variantes">
        <Textarea rows={3} placeholder="Ex.: 1, 2, 3, 10" value={ids} onChange={(e) => setIds(e.target.value)} />
      </Field>
    </Modal>
  );
}

// ===================================================================
// EDITOR DE PRODUTO
// ===================================================================

export function ProdutoEditor() {
  const m = location.hash.match(/^#\/produtos\/(\d+)$/);
  const id = m ? Number(m[1]) : null;

  const [familias, setFamilias] = useState<Familia[]>([]);
  const [categoriasTree, setCategoriasTree] = useState<Record<string, string[]>>({});
  const [produto, setProduto] = useState<ProdutoCadastro | null>(null);
  const [form, setForm] = useState({ familia_id: "", marca: "", external_id: "", nome: "", categoria: "", subcategoria: "", descricao: "", termos_busca: "" });
  const [atributos, setAtributos] = useState<FamiliaAtributo[]>([]);
  const [valores, setValores] = useState<Record<number, Set<string>>>({});
  const [variantes, setVariantes] = useState<VarianteLocal[]>([]);
  const [tab, setTab] = useState<"gerais" | "atributos" | "variacoes" | "imagens">("gerais");
  const [carregando, setCarregando] = useState(true);

  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [unidadesCompra, setUnidadesCompra] = useState<UnidadeCompra[]>([]);
  const [fornecedorRows, setFornecedorRows] = useState<FornecedorRow[]>([]);
  const fornecedorSeq = useRef(0);

  useEffect(() => {
    void (async () => {
      let fs: Familia[] = [];
      try {
        fs = await api.listarFamilias();
      } catch {
        fs = [];
      }
      setFamilias(fs);

      let tree: Record<string, string[]> = {};
      try {
        tree = await api.listarCategorias();
      } catch {
        tree = {};
      }
      setCategoriasTree(tree);

      let prod: ProdutoCadastro | null = null;
      if (id) {
        try {
          prod = await api.detalharProdutoCadastro(id);
        } catch {
          toast("Erro ao carregar produto", "error");
          location.hash = "#/produtos";
          return;
        }
      }
      setProduto(prod);

      const familiaId = prod ? prod.familia_id : fs[0] ? fs[0].id : null;
      setForm({
        familia_id: String(familiaId ?? ""),
        marca: prod?.marca ?? "",
        external_id: prod?.external_id ?? "",
        nome: prod?.nome ?? "",
        categoria: prod?.categoria ?? "",
        subcategoria: prod?.subcategoria ?? "",
        descricao: prod?.descricao ?? "",
        termos_busca: prod?.termos_busca ?? "",
      });

      const st = buildAtributosState(fs, familiaId, prod);
      setAtributos(st.atributos);
      setValores(st.valores);
      setVariantes(st.variantes);

      if (prod) {
        const [f, u] = await Promise.all([api.listarFornecedores(true), api.listarUnidadesCompra(true)]).catch(() => [[], []] as [Fornecedor[], UnidadeCompra[]]);
        setFornecedores(f);
        setUnidadesCompra(u);
        const rows = seedFornecedorRows(prod, st.variantes, fornecedorSeq);
        setFornecedorRows(rows);
      }

      setCarregando(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (carregando) return <Loading />;

  const trocarFamilia = (familiaId: number | null) => {
    setForm((f) => ({ ...f, familia_id: String(familiaId ?? "") }));
    const st = buildAtributosState(familias, familiaId, null);
    setAtributos(st.atributos);
    setValores(st.valores);
    setVariantes(st.variantes);
  };

  const montarNomePadrao = () => {
    const base = form.nome.trim();
    const specs = atributos.filter((a) => ehAttrPadrao(a.nome)).map((a) => [...(valores[a.id] || [])].join("/")).filter(Boolean);
    const montado = [base, ...specs, form.marca.trim()].filter(Boolean).join(" ");
    if (!montado) {
      toast("Informe o nome base ou selecione valores de atributos para montar.", "error");
    } else {
      setForm((f) => ({ ...f, nome: montado }));
      toast("Nome montado pelo padrão da família. Ajuste se necessário.", "success");
    }
  };

  const toggleValor = (attrId: number, val: string, on: boolean) => {
    setValores((prev) => {
      const set = new Set(prev[attrId] || []);
      if (on) set.add(val);
      else set.delete(val);
      return { ...prev, [attrId]: set };
    });
  };

  const addValor = (attrId: number, val: string) => {
    const v = val.trim();
    if (!v) return;
    setValores((prev) => {
      const set = new Set(prev[attrId] || []);
      set.add(v);
      return { ...prev, [attrId]: set };
    });
  };

  const gerarVariacoes = () => {
    const keys = atributos.map((a) => a.id);
    const vazios = atributos.filter((a) => !valores[a.id] || valores[a.id].size === 0);
    if (vazios.length) {
      toast(`Selecione ao menos um valor para: ${vazios.map((a) => a.nome).join(", ")}`, "error");
      return;
    }
    const arrays = keys.map((k) => [...(valores[k] || [])]);
    const combos = cartesiano(arrays);
    const existentes: Record<string, VarianteLocal> = {};
    variantes.forEach((v) => {
      existentes[JSON.stringify(v.valores)] = v;
    });
    const next = combos.map((vals) => {
      const attr: Record<string, string> = {};
      keys.forEach((k, j) => {
        attr[String(k)] = vals[j];
      });
      const prev = existentes[JSON.stringify(attr)];
      return {
        id: prev ? prev.id : undefined,
        sku: prev ? prev.sku : "",
        ean: prev ? prev.ean : "",
        preco: prev ? prev.preco : "",
        prom: prev ? prev.prom : "",
        peso: prev ? prev.peso : "",
        dimensoes: prev ? prev.dimensoes : "",
        unidade_venda: prev ? prev.unidade_venda : "",
        embalagem: prev ? prev.embalagem : "",
        fator_conversao: prev ? prev.fator_conversao : "",
        localizacao: prev ? prev.localizacao : "",
        ncm: prev ? prev.ncm : "",
        unidade_tributavel: prev ? prev.unidade_tributavel : "",
        valores: attr,
      };
    });
    setVariantes(next);
    toast(`${next.length} variação(ões) gerada(s)`, "success");
  };

  const atualizarVariante = (idx: number, field: keyof VarianteLocal, value: string) => {
    setVariantes((arr) => arr.map((v, i) => (i === idx ? { ...v, [field]: value } : v)));
  };

  const salvar = async () => {
    const familia_id = Number(form.familia_id);
    if (!familia_id) {
      toast("Selecione a família", "error");
      return;
    }
    if (!form.nome.trim()) {
      toast("Informe o nome base do produto", "error");
      return;
    }
    const semsValor = atributos.filter((a) => a.obrigatorio && (!valores[a.id] || valores[a.id].size === 0));
    if (semsValor.length) {
      toast("Preencha os atributos obrigatórios: " + semsValor.map((a) => a.nome).join(", "), "error");
      setTab("atributos");
      return;
    }
    const caAttrs = atributos.filter((a) => CA_RE.test(a.nome));
    for (const a of caAttrs) {
      for (const v of valores[a.id] || []) {
        if (!/^[\d.\s]+$/.test(String(v).trim())) {
          toast(`O atributo "${a.nome}" deve ser um número de CA válido (ex.: 12345 ou 12.345).`, "error");
          setTab("atributos");
          return;
        }
      }
    }
    const payload: ProdutoCadastroPayload = {
      familia_id,
      nome: form.nome.trim(),
      marca: form.marca.trim(),
      external_id: form.external_id.trim() || null,
      descricao: form.descricao.trim(),
      termos_busca: form.termos_busca.trim(),
      categoria: form.categoria.trim(),
      subcategoria: form.subcategoria.trim(),
      variantes: variantes.map((v) => ({
        id: v.id,
        sku: v.sku || "",
        ean: v.ean || "",
        preco: v.preco !== "" && v.preco != null ? Number(v.preco) : 0,
        preco_promocional: v.prom !== "" && v.prom != null ? Number(v.prom) : null,
        observacao: "",
        peso: v.peso !== "" && v.peso != null ? Number(v.peso) : null,
        dimensoes: v.dimensoes || "",
        unidade_venda: v.unidade_venda || "UN",
        embalagem: v.embalagem !== "" && v.embalagem != null ? Number(v.embalagem) : null,
        fator_conversao: v.fator_conversao !== "" && v.fator_conversao != null ? Number(v.fator_conversao) : null,
        localizacao: v.localizacao || "",
        ncm: v.ncm || "",
        unidade_tributavel: v.unidade_tributavel || "",
        atributos: v.valores,
      })),
    };
    try {
      let novoId = produto ? produto.id : null;
      let desativadas = 0;
      if (produto) {
        const res = await api.atualizarProdutoCadastro(produto.id, payload);
        desativadas = res.variantes?.desativadas || 0;
      } else {
        const res = await api.criarProdutoCadastro(payload);
        novoId = res.id;
      }
      toast(
        desativadas
          ? `Produto salvo. ${desativadas} variação(ões) removida(s) foram desativadas por possuírem estoque/preço/fornecedor — nenhum dado foi excluído.`
          : "Produto salvo",
        desativadas ? "warn" : "success"
      );
      location.hash = `#/produtos/${novoId}`;
    } catch (e) {
      toast("Erro ao salvar: " + (e as Error).message, "error");
    }
  };

  const salvarFornecedor = async () => {
    if (!produto) return;
    const porFornecedor: Record<number, Map<number, FornecedorVariantePayload>> = {};
    const semId: VarianteLocal[] = [];
    for (const r of fornecedorRows) {
      const fornecedorId = Number(r.fornecedor_id);
      if (!fornecedorId) continue;
      const v = variantes[r.variante_idx];
      if (!v) continue;
      if (v.id == null || v.id === 0) {
        if (!semId.includes(v)) semId.push(v);
        continue;
      }
      (porFornecedor[fornecedorId] ||= new Map()).set(v.id, {
        variante_id: v.id,
        codigo_fornecedor: r.codigo || "",
        descricao_fornecedor: "",
        unidade_compra: r.unidade || "",
        fator_conversao: r.fator !== "" && r.fator != null ? Number(r.fator) : 1,
      });
    }
    const envolver = new Set(Object.keys(porFornecedor).map(Number));
    for (const fv of produto.fornecedor_variantes || []) envolver.add(fv.fornecedor_id);
    const sucesso: string[] = [];
    const erros: string[] = [];
    for (const fid of envolver) {
      try {
        const itens = porFornecedor[fid] ? Array.from(porFornecedor[fid]!.values()) : [];
        await api.salvarFornecedorVariantes(produto.id, fid, itens);
        sucesso.push(fornecedores.find((f) => f.id === fid)?.nome || "fornecedor " + fid);
      } catch (e) {
        erros.push((fornecedores.find((f) => f.id === fid)?.nome || String(fid)) + " (" + (e as Error).message + ")");
      }
    }
    if (!sucesso.length && !erros.length && !semId.length) {
      toast("Adicione ao menos uma linha e selecione o fornecedor.", "warn");
      return;
    }
    if (sucesso.length) toast(`Códigos salvos: ${sucesso.join(", ")}`, "success");
    if (semId.length) toast("As variações recém-geradas só vinculam após salvar o produto (Salvar produto).", "warn");
    if (erros.length) toast("Erro: " + erros.join("; "), "error");
  };

  const subcategorias = categoriasTree[form.categoria] || [];
  const padraoText = normalize(form.categoria).includes("epi")
    ? "Padrão EPI: Item + Material/Tamanho + Nº CA + Marca."
    : normalize(form.categoria).includes("cabo") || normalize(form.categoria).includes("fio")
      ? "Padrão de cabos: Item + Bitola (mm²) + Tensão + Norma/Marca."
      : "Padrão: Item + Características (bitola, tensão, CA) + Marca.";

  const TABS: { key: typeof tab; label: string }[] = [
    { key: "gerais", label: "Dados Gerais" },
    { key: "atributos", label: "Atributos da Família" },
    { key: "variacoes", label: "Matriz de Variações" },
    { key: "imagens", label: "Mídia e Anexos" },
  ];

  return (
    <div>
      <PageHeader
        title={produto ? "Editar produto" : "Novo produto"}
        subtitle="Cadastre o produto uma vez; as variações são geradas pelas combinações dos atributos."
        actions={
          <Button variant="ghost" onClick={() => (location.hash = "#/produtos")}>
            ← Voltar
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              tab === t.key ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "gerais" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <Field label="Família *">
              <div className="flex gap-2">
                <Select value={form.familia_id} onChange={(e) => trocarFamilia(Number(e.target.value) || null)} className="flex-1">
                  {familias.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.nome}
                    </option>
                  ))}
                </Select>
              </div>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Marca">
                <Input placeholder="Ex.: Corfio" value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })} />
              </Field>
              <Field label="Código Fabricante">
                <Input placeholder="Ex.: B-66874" value={form.external_id} onChange={(e) => setForm({ ...form, external_id: e.target.value })} />
              </Field>
            </div>
            <Field label="Nome base do produto *">
              <Input placeholder="Ex.: Cabo Flexível 750V Antichama" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="text-xs text-gray-400" title="Padrão de nomenclatura de fábrica">
                  {padraoText}
                </span>
                <Button size="sm" variant="ghost" onClick={montarNomePadrao}>
                  Montar pelo padrão
                </Button>
              </div>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Categoria (opcional)">
                <Input list="dlCategorias" placeholder="Fios e Cabos" value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} />
                <datalist id="dlCategorias">
                  {[...new Set(Object.entries(categoriasTree).flatMap(([c, s]) => [c, ...(s || [])]))].map((c) => (
                    <option key={c} value={c} />
                  ))}
                </datalist>
              </Field>
              <Field label="Subcategoria (opcional)">
                <Input list="dlSubcategorias" placeholder="Cabo Flexível" value={form.subcategoria} onChange={(e) => setForm({ ...form, subcategoria: e.target.value })} />
                <datalist id="dlSubcategorias">
                  {subcategorias.map((s) => (
                    <option key={s} value={s} />
                  ))}
                </datalist>
              </Field>
            </div>
            <Field label="Descrição (opcional)">
              <Input value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
            </Field>
            <Field label="Termos de busca / sinônimos">
              <Input placeholder="Ex.: cabo, fio, 750V, antichama, barramento…" value={form.termos_busca} onChange={(e) => setForm({ ...form, termos_busca: e.target.value })} />
              <p className="mt-1 text-xs text-gray-400">Palavras-chave e variações do nome usado pelo mercado, para facilitar a busca (ex.: "fio" além de "cabo").</p>
            </Field>
          </div>
          <aside className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Curva ABC · Gestão de Linha</div>
            {produto ? <AbcRecap p={produto} /> : <p className="text-sm text-gray-400">Salve o produto para ver os indicadores de gestão.</p>}
          </aside>
        </div>
      )}

      {tab === "atributos" && (
        <div>
          <p className="mb-3 text-sm text-gray-500">Combine os valores dos atributos da família selecionada. Os marcados ficam ativos na aba de variações.</p>
          {atributos.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">Essa família não tem atributos. Edite a família para adicioná-los.</p>
          ) : (
            <div className="space-y-3">
              {atributos.map((a) => {
                const set = valores[a.id] || new Set<string>();
                const opts = a.tipo === "lista" ? [...a.opcoes] : [];
                const custom = [...set].filter((v) => !opts.includes(v));
                const display = [...opts, ...custom];
                return (
                  <div key={a.id} className="rounded-lg border border-gray-200 bg-white p-3">
                    <div className="mb-2 text-sm font-medium text-gray-900">
                      {a.nome} {a.obrigatorio ? <span className="ml-1 rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-600">* obrigatório</span> : null}
                    </div>
                    {display.length > 0 && (
                      <div className="mb-2 flex flex-wrap gap-2">
                        {display.map((v) => (
                          <label key={v} className={`flex cursor-pointer items-center gap-1 rounded-full border px-3 py-1 text-sm ${set.has(v) ? "border-brand-600 bg-brand-50 text-brand-700" : "border-gray-200 text-gray-600"}`}>
                            <input type="checkbox" checked={set.has(v)} onChange={(e) => toggleValor(a.id, v, e.target.checked)} className="hidden" />
                            {set.has(v) ? "✓ " : ""}
                            {v}
                          </label>
                        ))}
                      </div>
                    )}
                    <AttrAddInput onAdd={(v) => addValor(a.id, v)} />
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {tab === "variacoes" && (
        <div>
          <div className="mb-3 flex items-center gap-3">
            <Button variant="primary" onClick={gerarVariacoes}>
              Gerar Variações
            </Button>
            {variantes.length > 0 && <span className="text-xs text-gray-500">{variantes.length} variação(ões) · atributos: {atributos.map((a) => a.nome).join(" · ")}</span>}
            {!variantes.length && atributos.length > 0 && <span className="text-xs text-gray-500">Selecione os valores dos atributos e clique em "Gerar Variações".</span>}
          </div>

          {variantes.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {["Variação", "SKU", "EAN", "Preço", "Promo.", "Peso", "Dimensões", "Unid.", "Emb.", "Fator", "Localização", "NCM", "Unid. Trib.", ""].map((h) => (
                      <th key={h} className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {variantes.map((v, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-3 py-1.5 font-medium">{varianteLabel(v, atributos, idx)}</td>
                      <td className="px-3 py-1.5"><CellInput value={String(v.sku)} onChange={(x) => atualizarVariante(idx, "sku", x)} placeholder="SKU" /></td>
                      <td className="px-3 py-1.5"><CellInput value={String(v.ean)} onChange={(x) => atualizarVariante(idx, "ean", x)} placeholder="EAN" /></td>
                      <td className="px-3 py-1.5"><CellInput type="number" value={num(v.preco)} onChange={(x) => atualizarVariante(idx, "preco", x)} placeholder="R$" /></td>
                      <td className="px-3 py-1.5"><CellInput type="number" value={num(v.prom)} onChange={(x) => atualizarVariante(idx, "prom", x)} placeholder="Promo" /></td>
                      <td className="px-3 py-1.5"><CellInput type="number" value={num(v.peso)} onChange={(x) => atualizarVariante(idx, "peso", x)} placeholder="kg" /></td>
                      <td className="px-3 py-1.5"><CellInput value={String(v.dimensoes)} onChange={(x) => atualizarVariante(idx, "dimensoes", x)} placeholder="CxLxA" /></td>
                      <td className="px-3 py-1.5"><CellInput value={String(v.unidade_venda)} onChange={(x) => atualizarVariante(idx, "unidade_venda", x)} placeholder="UN" /></td>
                      <td className="px-3 py-1.5"><CellInput type="number" value={num(v.embalagem)} onChange={(x) => atualizarVariante(idx, "embalagem", x)} placeholder="unid/cx" /></td>
                      <td className="px-3 py-1.5"><CellInput type="number" value={num(v.fator_conversao)} onChange={(x) => atualizarVariante(idx, "fator_conversao", x)} placeholder="cx →" /></td>
                      <td className="px-3 py-1.5"><CellInput value={String(v.localizacao)} onChange={(x) => atualizarVariante(idx, "localizacao", x)} placeholder="Endereço" /></td>
                      <td className="px-3 py-1.5"><CellInput value={String(v.ncm)} onChange={(x) => atualizarVariante(idx, "ncm", x)} placeholder="NCM" /></td>
                      <td className="px-3 py-1.5"><CellInput value={String(v.unidade_tributavel)} onChange={(x) => atualizarVariante(idx, "unidade_tributavel", x)} placeholder="UN" /></td>
                      <td className="px-3 py-1.5">
                        <button className="text-gray-400 hover:text-red-600" onClick={() => setVariantes((arr) => arr.filter((_, i) => i !== idx))}>
                          ×
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {produto ? (
            <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
              <h4 className="mb-2 text-sm font-semibold text-gray-900">Códigos por fornecedor</h4>
              <p className="mb-3 text-xs text-gray-400">
                Informe para cada variação o fornecedor, o código usado por ele, a unidade de compra e o fator de conversão (ex.: embalagem com 10 unidades → fator 10).
              </p>
              <FornecedorGrid
                variantes={variantes}
                atributos={atributos}
                fornecedores={fornecedores}
                unidadesCompra={unidadesCompra}
                rows={fornecedorRows}
                setRows={setFornecedorRows}
                seq={fornecedorSeq}
              />
              <div className="mt-3 flex justify-end">
                <Button variant="primary" size="sm" onClick={() => void salvarFornecedor()}>
                  Salvar códigos
                </Button>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-gray-400">Salve o produto para cadastrar os códigos dos fornecedores por variação.</p>
          )}
        </div>
      )}

      {tab === "imagens" && (
        <div>
          {produto ? <Imagens produto={produto} setProduto={setProduto} /> : <p className="py-8 text-center text-sm text-gray-400">Salve o produto para poder adicionar imagens.</p>}
        </div>
      )}

      <div className="mt-6 flex justify-end gap-2">
        <Button onClick={() => (location.hash = "#/produtos")}>Cancelar</Button>
        <Button variant="primary" onClick={() => void salvar()}>
          Salvar produto
        </Button>
      </div>
    </div>
  );
}

function num(x: string | number): string {
  return x !== "" && x != null ? String(x) : "";
}

function CellInput({ value, onChange, placeholder, type }: { value: string; onChange: (v: string) => void; placeholder?: string; type?: string }) {
  return (
    <input
      type={type || "text"}
      className="w-24 rounded border border-gray-200 px-2 py-1 text-xs focus:border-brand-500 focus:outline-none"
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function AttrAddInput({ onAdd }: { onAdd: (v: string) => void }) {
  const [v, setV] = useState("");
  return (
    <div className="flex gap-2">
      <Input
        className="flex-1"
        placeholder="Adicionar valor…"
        value={v}
        onChange={(e) => setV(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            if (v.trim()) {
              onAdd(v.trim());
              setV("");
            }
          }
        }}
      />
      <Button
        size="sm"
        variant="ghost"
        onClick={() => {
          if (v.trim()) {
            onAdd(v.trim());
            setV("");
          }
        }}
      >
        Adicionar
      </Button>
    </div>
  );
}

function AbcRecap({ p }: { p: ProdutoCadastro }) {
  const classe = p.classe_abc || "—";
  return (
    <div className="flex flex-wrap gap-2">
      <Badge tone={classe === "A" ? "blue" : classe === "B" ? "amber" : "gray"}>Classe: {classe}</Badge>
      {p.em_linha != null && <Badge tone={p.em_linha ? "green" : "red"}>{p.em_linha ? "No rolar" : "Fora do rolar"}</Badge>}
      {p.linha_produto && <Badge>Linha: {p.linha_produto}</Badge>}
      {p.margem_lucro_estimada != null && <Badge>Margem: {(p.margem_lucro_estimada * 100).toFixed(0)}%</Badge>}
      {p.giro_esperado_mercado != null && <Badge>Giro: {p.giro_esperado_mercado.toFixed(2)}</Badge>}
      {p.valor_agregado && <Badge>Valor: {p.valor_agregado}</Badge>}
      {p.lucro_total_estimado != null && <Badge tone="green">Lucro est.: {fmtMoney(p.lucro_total_estimado)}</Badge>}
    </div>
  );
}

function FornecedorGrid({
  variantes,
  atributos,
  fornecedores,
  unidadesCompra,
  rows,
  setRows,
  seq,
}: {
  variantes: VarianteLocal[];
  atributos: FamiliaAtributo[];
  fornecedores: Fornecedor[];
  unidadesCompra: UnidadeCompra[];
  rows: FornecedorRow[];
  setRows: (r: FornecedorRow[]) => void;
  seq: React.MutableRefObject<number>;
}) {
  const atualizar = (uid: string, patch: Partial<FornecedorRow>) => {
    setRows(rows.map((r) => (r.uid === uid ? { ...r, ...patch } : r)));
  };

  if (fornecedores.length === 0) return <p className="text-sm text-gray-400">Nenhum fornecedor ativo cadastrado.</p>;
  if (!variantes.length) return <p className="text-sm text-gray-400">Gere as variações primeiro para associar os códigos.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Variação</th>
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Fornecedor</th>
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Código do fornecedor</th>
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Unid. compra</th>
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Fator conv.</th>
            <th className="w-9" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((r) => (
            <tr key={r.uid}>
              <td className="px-3 py-1.5">
                <Select value={String(r.variante_idx)} onChange={(e) => atualizar(r.uid, { variante_idx: Number(e.target.value) })} className="py-1 text-xs">
                  {variantes.map((v, i) => (
                    <option key={i} value={i}>
                      {varianteLabel(v, atributos, i)}
                      {v.sku ? " · " + v.sku : ""}
                    </option>
                  ))}
                </Select>
              </td>
              <td className="px-3 py-1.5">
                <Select value={r.fornecedor_id} onChange={(e) => atualizar(r.uid, { fornecedor_id: e.target.value })} className="py-1 text-xs">
                  <option value="">—</option>
                  {fornecedores.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.nome}
                    </option>
                  ))}
                </Select>
              </td>
              <td className="px-3 py-1.5">
                <Input className="py-1 text-xs" placeholder="Código do fornecedor" value={r.codigo} onChange={(e) => atualizar(r.uid, { codigo: e.target.value })} />
              </td>
              <td className="px-3 py-1.5">
                <Select value={r.unidade} onChange={(e) => atualizar(r.uid, { unidade: e.target.value })} className="py-1 text-xs">
                  <option value="">—</option>
                  {unidadesCompra.map((u) => (
                    <option key={u.sigla} value={u.sigla}>
                      {u.sigla}
                      {u.descricao ? " — " + u.descricao : ""}
                    </option>
                  ))}
                  {r.unidade && !unidadesCompra.some((u) => u.sigla === r.unidade) ? (
                    <option value={r.unidade}>{r.unidade} (não cadastrada)</option>
                  ) : null}
                </Select>
              </td>
              <td className="px-3 py-1.5">
                <Input type="number" min={0} step="0.01" className="w-24 py-1 text-xs" placeholder="1" value={r.fator !== "" && r.fator != null ? String(r.fator) : ""} onChange={(e) => atualizar(r.uid, { fator: e.target.value })} />
              </td>
              <td className="px-3 py-1.5">
                <button className="text-gray-400 hover:text-red-600" onClick={() => setRows(rows.filter((x) => x.uid !== r.uid))}>
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Button size="sm" className="mt-2" onClick={() => setRows([...rows, { uid: "fvr" + ++seq.current, variante_idx: 0, fornecedor_id: "", codigo: "", unidade: "", fator: "" }])}>
        + Adicionar linha
      </Button>
    </div>
  );
}

function Imagens({ produto, setProduto }: { produto: ProdutoCadastro; setProduto: (p: ProdutoCadastro) => void }) {
  const [url, setUrl] = useState("");
  const [baixando, setBaixando] = useState(false);
  const uploadRef = useRef<HTMLInputElement>(null);

  const refresh = async () => {
    try {
      setProduto(await api.detalharProdutoCadastro(produto.id));
    } catch {
      /* silêncio */
    }
  };

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || !files.length) return;
    const count = files.length;
    const fd = new FormData();
    for (let i = 0; i < files.length; i++) fd.append("files", files[i]);
    try {
      await api.enviarImagensProduto(produto.id, fd);
      await refresh();
      toast(`${count} imagem(ns) enviada(s)`, "success");
    } catch (e) {
      toast("Erro no upload: " + (e as Error).message, "error");
    }
    e.target.value = "";
  };

  const baixarUrl = async () => {
    if (!url.trim()) {
      toast("Informe a URL", "error");
      return;
    }
    setBaixando(true);
    try {
      const res = await api.baixarImagensUrl(produto.id, url.trim());
      await refresh();
      toast(`${res.total} imagem(ns) baixada(s)`, "success");
      if (res.erros && res.erros.length) toast(`Erros: ${res.erros.slice(0, 3).join(" | ")}`, "error");
    } catch (e) {
      toast("Erro ao baixar: " + (e as Error).message, "error");
    } finally {
      setBaixando(false);
    }
  };

  const imgs = produto.imagens || [];

  return (
    <div>
      <div className="mb-3 flex gap-2">
        <label className="inline-flex cursor-pointer items-center justify-center rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
          Enviar arquivos
          <input ref={uploadRef} type="file" accept="image/*" multiple hidden onChange={onUpload} />
        </label>
        <Input className="flex-1" placeholder="URL da página do produto ou imagem direta" value={url} onChange={(e) => setUrl(e.target.value)} />
        <Button variant="primary" onClick={() => void baixarUrl()} disabled={baixando}>
          {baixando ? "Baixando…" : "Baixar da internet"}
        </Button>
      </div>

      {imgs.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">Nenhuma imagem. Envie arquivos ou informe a URL de uma página do produto.</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {imgs.map((im, i) => (
            <div key={im.id} className="relative rounded-lg border border-gray-200 bg-white p-2">
              <img src={im.url} loading="lazy" alt="" className="h-24 w-full object-contain" />
              {i === 0 ? <span className="absolute left-1 top-1 rounded bg-brand-600 px-1.5 py-0.5 text-[10px] font-medium text-white">Capa</span> : null}
              {i > 0 && (
                <button
                  className="absolute right-1 top-1 rounded bg-white px-1 text-gray-500 shadow hover:text-amber-500"
                  title="Definir como imagem de capa"
                  onClick={async () => {
                    try {
                      await api.definirCapaImagem(produto.id, im.id);
                      await refresh();
                      toast("Imagem de capa atualizada", "success");
                    } catch (e) {
                      toast("Erro ao definir capa: " + (e as Error).message, "error");
                    }
                  }}
                >
                  ★
                </button>
              )}
              <button
                className="absolute bottom-1 right-1 rounded bg-white px-1 text-gray-500 shadow hover:text-red-600"
                title="Excluir imagem"
                onClick={async () => {
                  try {
                    await api.excluirImagem(im.id);
                    await refresh();
                  } catch (e) {
                    toast("Erro ao excluir imagem: " + (e as Error).message, "error");
                  }
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------- helpers de estado (fora do componente) ----------------

function buildAtributosState(familias: Familia[], familiaId: number | null, produto: ProdutoCadastro | null) {
  let atributos: FamiliaAtributo[] = familias.find((x) => x.id === familiaId)?.atributos || [];
  if (produto && produto.atributos && produto.familia_id === familiaId) atributos = produto.atributos;
  const valores: Record<number, Set<string>> = {};
  atributos.forEach((a) => {
    valores[a.id] = new Set();
  });
  const variantes: VarianteLocal[] = [];
  if (produto && produto.familia_id === familiaId) {
    (produto.variantes || []).forEach((v) => {
      const vals: Record<string, string> = {};
      atributos.forEach((a) => {
        const val = v.atributos ? v.atributos[String(a.id)] : undefined;
        if (val) {
          valores[a.id].add(val);
          vals[String(a.id)] = val;
        }
      });
      variantes.push({
        id: v.id,
        sku: v.sku || "",
        ean: v.ean || "",
        preco: v.preco || "",
        prom: v.preco_promocional || "",
        peso: v.peso || "",
        dimensoes: v.dimensoes || "",
        unidade_venda: v.unidade_venda || "",
        embalagem: v.embalagem || "",
        fator_conversao: v.fator_conversao || "",
        localizacao: v.localizacao || "",
        ncm: v.ncm || "",
        unidade_tributavel: v.unidade_tributavel || "",
        valores: vals,
      });
    });
  }
  return { atributos, valores, variantes };
}

function seedFornecedorRows(produto: ProdutoCadastro, variantes: VarianteLocal[], seq: React.MutableRefObject<number>): FornecedorRow[] {
  const rows: FornecedorRow[] = [];
  const idxPorId: Record<number, number> = {};
  variantes.forEach((v, i) => {
    if (v.id != null) idxPorId[v.id] = i;
  });
  for (const r of produto.fornecedor_variantes || []) {
    rows.push({
      uid: "fvr" + ++seq.current,
      variante_idx: r.variante_id in idxPorId ? idxPorId[r.variante_id] : 0,
      fornecedor_id: String(r.fornecedor_id),
      codigo: r.codigo_fornecedor || "",
      unidade: r.unidade_compra || "",
      fator: r.fator_conversao ?? "",
    });
  }
  if (!rows.length && variantes.length) {
    rows.push({ uid: "fvr" + ++seq.current, variante_idx: 0, fornecedor_id: "", codigo: "", unidade: "", fator: "" });
  }
  return rows;
}
