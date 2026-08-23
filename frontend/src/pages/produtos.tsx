// pages/produtos.tsx — cadastro de produtos (famílias + produto pai + variações + imagens).

import { Fragment, useEffect, useRef, useState } from "react";
import {
  api,
  type Familia,
  type FamiliaAtributo,
  type FamiliaPayload,
  type Fornecedor,
  type FornecedorVariantePayload,
  type Grupo,
  type ItemListaCadastro,
  type Marca,
  type ProdutoCadastro,
  type Subgrupo,
  type ProdutoCadastroPayload,
  type ProdutoPreview,
  type UnidadeCompra,
  type PerfilFiscal,
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

const CA_RE = /(^|[^a-z0-9])(n\s?[º°]?\s?ca|ca|certificado|aprovacao)([^a-z0-9]|$)/i;

function normalize(str: string): string {
  return String(str || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function varianteLabel(v: VarianteLocal, atributos: FamiliaAtributo[], idx: number): string {
  return atributos.map((a) => v.valores[String(a.id)]).filter(Boolean).join(" · ") || `Variação ${idx + 1}`;
}

/** Reduz um texto a um trecho curto, só letras/números, maiúsculo — usado
 * para montar SKUs legíveis a partir do nome do produto e dos valores dos
 * atributos (ex.: "Cabo Flexível" + Cor=Azul + Bitola=2,5mm → CABOFL-AZUL-25MM). */
function slugify(str: string, maxLen: number): string {
  return normalize(str).replace(/[^a-z0-9]+/g, "").toUpperCase().slice(0, maxLen);
}

// Segmento de atributos do SKU estruturado ([GRUPO]-[SUBGRUPO]-[MARCA]-[ATRIBUTOS]).
// `template` = familia.sku_atributos (nomes na ordem que compõem o SKU); vazio/nulo = usa todos.
function gerarSkuAtributos(valores: Record<string, string>, atributos: FamiliaAtributo[], template?: string[] | null): string {
  let selecionados: FamiliaAtributo[];
  if (template && template.length) {
    selecionados = template
      .map((nome) => atributos.find((a) => a.nome.trim().toLowerCase() === nome.trim().toLowerCase()))
      .filter((a): a is FamiliaAtributo => !!a);
  } else {
    selecionados = atributos;
  }
  const partes = selecionados.map((a) => slugify(valores[String(a.id)] || "", 12)).filter(Boolean);
  return partes.join("-");
}

// Regras de validação de atributo "livre".

function validacaoLabel(v?: string): string {
  return v === "numero" ? "Somente números" : v === "alphanumerico" ? "Letras e números" : "Texto livre";
}

// Valida um valor digitado conforme o tipo/validação do atributo.
// Devolve "" se válido ou uma mensagem de erro.
function validarValorAtributo(tipo: string, validacao: string | undefined, valor: string): string {
  const v = valor.trim();
  if (!v) return "";
  if (tipo !== "livre") return "";
  if (validacao === "numero") {
    return /^\d+(?:[.,]\d{1,3})?$/.test(v) ? "" : "Informe apenas números (ex.: 2,5 ou 2500).";
  }
  if (validacao === "alphanumerico") {
    return /^[a-zA-Z0-9À-ÿ ]+$/.test(v) ? "" : "Use apenas letras e números (sem símbolos).";
  }
  return "";
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
  const [modalImportar, setModalImportar] = useState(false);

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
        <Button variant="outline" onClick={() => setModalImportar(true)}>
          Importar catálogo
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
      <ModalImportarCatalogo open={modalImportar} onClose={() => setModalImportar(false)} />
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
                  {f.atributos.length === 0 ? (
                    <div className="text-xs text-gray-400">Sem atributos.</div>
                  ) : (
                    <div className="mt-0.5 text-xs text-gray-500">
                      {f.atributos.map((a) => (
                        <span key={a.id} className="mr-2 inline-block">
                          <span className="font-medium text-gray-700">{a.nome}</span>
                          {a.tipo === "lista" && a.opcoes.length > 0 ? (
                            <span className="text-gray-400">: {a.opcoes.join(", ")}</span>
                          ) : a.tipo === "livre" ? (
                            <span className="text-blue-500"> ({validacaoLabel(a.validacao)})</span>
                          ) : null}
                        </span>
                      ))}
                    </div>
                  )}
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

function OpcoesEditor({ opcoes, onAdd, onRemove }: { opcoes: string[]; onAdd: (v: string) => void; onRemove: (v: string) => void }) {
  const [v, setV] = useState("");
  const adicionar = () => {
    const val = v.trim();
    if (!val) return;
    onAdd(val);
    setV("");
  };
  return (
    <div>
      {opcoes.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {opcoes.map((o) => (
            <span key={o} className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-700">
              {o}
              <button type="button" className="text-gray-400 hover:text-red-600" onClick={() => onRemove(o)}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Input className="flex-1" placeholder="Digite uma opção e Enter (ex.: azul)" value={v} onChange={(e) => setV(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); adicionar(); } }} />
        <Button size="sm" variant="ghost" onClick={adicionar}>
          Adicionar
        </Button>
      </div>
    </div>
  );
}

function ModalFamiliaForm({ familia, onClose, onSaved }: { familia: Familia | null; onClose: () => void; onSaved: () => void }) {
  const [nome, setNome] = useState(familia?.nome ?? "");
  const [descricao, setDescricao] = useState(familia?.descricao ?? "");
  const [ncm, setNcm] = useState(familia?.ncm_padrao ?? "");
  const [unidade, setUnidade] = useState(familia?.unidade_padrao ?? "UN");
  const [atributos, setAtributos] = useState<{ id: number | null; nome: string; tipo: "lista" | "livre"; opcoes: string[]; obrigatorio: boolean; validacao: string }[]>(() => {
    const a = (familia ? familia.atributos : []).map((x) => ({ id: x.id, nome: x.nome, tipo: x.tipo, opcoes: x.opcoes || [], obrigatorio: !!x.obrigatorio, validacao: x.validacao || "texto" }));
    return a.length ? a : [{ id: null, nome: "", tipo: "lista", opcoes: [], obrigatorio: false, validacao: "texto" }];
  });
  const [skuAtributos, setSkuAtributos] = useState<string[]>(() => (familia?.sku_atributos || []).map((s) => s.trim()).filter(Boolean));

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
        .map((a) => ({ id: a.id, nome: a.nome.trim(), tipo: a.tipo, opcoes: a.opcoes, obrigatorio: a.obrigatorio, validacao: a.validacao || "texto" }))
        .filter((a) => a.nome),
      sku_atributos: skuAtributos.map((s) => s.trim()).filter(Boolean),
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
          <div className="space-y-3">
            {atributos.map((a, i) => (
              <div key={i} className="rounded-md border border-gray-200 p-3">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-gray-800">{a.nome.trim() || `Atributo ${i + 1}`}</span>
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">{a.tipo === "lista" ? "Lista de opções" : "Valor livre"}</span>
                  {a.tipo === "livre" && <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-600">{validacaoLabel(a.validacao)}</span>}
                  <span className="flex-1" />
                  <button className="text-xs text-gray-400 hover:text-red-600" onClick={() => setAtributos((arr) => arr.filter((_, j) => j !== i))}>
                    × remover
                  </button>
                </div>
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-2">
                    <Input className="min-w-[200px] flex-1" placeholder="Nome do atributo (ex.: Cor)" value={a.nome} onChange={(e) => setAtributos((arr) => arr.map((x, j) => (j === i ? { ...x, nome: e.target.value } : x)))} />
                    <Select
                      className="w-44"
                      value={a.tipo}
                      onChange={(e) => setAtributos((arr) => arr.map((x, j) => (j === i ? { ...x, tipo: e.target.value as "lista" | "livre" } : x)))}
                    >
                      <option value="lista">Lista de opções</option>
                      <option value="livre">Valor livre</option>
                    </Select>
                  </div>
                  {a.tipo === "livre" ? (
                    <Select
                      className="w-64"
                      value={a.validacao || "texto"}
                      title="Validação do valor digitado no cadastro do produto"
                      onChange={(e) => setAtributos((arr) => arr.map((x, j) => (j === i ? { ...x, validacao: e.target.value } : x)))}
                    >
                      <option value="texto">Texto livre (qualquer valor)</option>
                      <option value="numero">Somente números (inteiro ou decimal)</option>
                      <option value="alphanumerico">Letras e números (sem símbolos)</option>
                    </Select>
                  ) : (
                    <OpcoesEditor
                      opcoes={a.opcoes}
                      onAdd={(v) => setAtributos((arr) => arr.map((x, j) => (j === i ? { ...x, opcoes: x.opcoes.includes(v) ? x.opcoes : [...x.opcoes, v] } : x)))}
                      onRemove={(v) => setAtributos((arr) => arr.map((x, j) => (j === i ? { ...x, opcoes: x.opcoes.filter((o) => o !== v) } : x)))}
                    />
                  )}
                  <label className="flex items-center gap-2 text-xs text-gray-600">
                    <input type="checkbox" checked={a.obrigatorio} onChange={(e) => setAtributos((arr) => arr.map((x, j) => (j === i ? { ...x, obrigatorio: e.target.checked } : x)))} />
                    Atributo obrigatório
                  </label>
                </div>
              </div>
            ))}
          </div>
          <Button size="sm" variant="ghost" className="mt-3" onClick={() => setAtributos((arr) => [...arr, { id: null, nome: "", tipo: "lista", opcoes: [], obrigatorio: false, validacao: "texto" }])}>
            + Adicionar atributo
          </Button>
        </Field>
        <Field
          label="Atributos que compõem o SKU"
          hint="Marque, na ordem, os atributos que entram no SKU (ex.: Bitola, Cor → ELE-CAB-SIL-25V-... ). Vazio = usa todos."
        >
          {atributos.filter((a) => a.nome.trim()).length === 0 ? (
            <p className="text-xs text-gray-400">Cadastre atributos acima para configurar o SKU.</p>
          ) : (
            <div className="space-y-1.5">
              {atributos
                .filter((a) => a.nome.trim())
                .map((a, i) => {
                  const nome = a.nome.trim();
                  const marcado = skuAtributos.includes(nome);
                  return (
                    <label key={i} className="flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={marcado}
                        onChange={(e) => {
                          const nome2 = nome;
                          setSkuAtributos((arr) => (e.target.checked ? [...arr.filter((x) => x !== nome2), nome2] : arr.filter((x) => x !== nome2)));
                        }}
                      />
                      <span className="flex-1">{nome}</span>
                      {marcado && (
                        <span className="flex items-center gap-1">
                          <button type="button" className="text-gray-400 hover:text-gray-700" title="Mover para cima" onClick={() => setSkuAtributos((arr) => { const j = arr.indexOf(nome); if (j <= 0) return arr; const c = [...arr]; [c[j - 1], c[j]] = [c[j], c[j - 1]]; return c; })}>
                            ↑
                          </button>
                          <button type="button" className="text-gray-400 hover:text-gray-700" title="Mover para baixo" onClick={() => setSkuAtributos((arr) => { const j = arr.indexOf(nome); if (j === -1 || j >= arr.length - 1) return arr; const c = [...arr]; [c[j], c[j + 1]] = [c[j + 1], c[j]]; return c; })}>
                            ↓
                          </button>
                          <span className="text-xs text-gray-400">pos {skuAtributos.indexOf(nome) + 1}</span>
                        </span>
                      )}
                    </label>
                  );
                })}
            </div>
          )}
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
// IMPORTAÇÃO DE CATÁLOGO (JSON exportado pelo scraper)
// ===================================================================

function ModalImportarCatalogo({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [importando, setImportando] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState<{ produtos: number; grupos: number; criados: number; atualizados: number } | null>(null);

  useEffect(() => {
    if (open) {
      setArquivo(null);
      setErro("");
      setResultado(null);
    }
  }, [open]);

  const importar = async () => {
    if (!arquivo) {
      toast("Selecione o arquivo JSON exportado pelo scraper", "error");
      return;
    }
    setImportando(true);
    setErro("");
    setResultado(null);
    try {
      const fd = new FormData();
      fd.append("file", arquivo);
      const res = await api.importarCatalogo(fd);
      setResultado(res);
      toast("Catálogo importado com sucesso", "success");
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setImportando(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Importar catálogo (scraper)"
      footer={
        <>
          <Button onClick={onClose}>Fechar</Button>
          <Button variant="primary" onClick={() => void importar()} disabled={importando || !arquivo}>
            {importando ? "Importando…" : "Importar arquivo"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <Field label="Arquivo JSON (output/catalogo.json)">
          <Input type="file" accept=".json,application/json" onChange={(e) => setArquivo(e.target.files?.[0] ?? null)} />
        </Field>
        <p className="text-xs text-gray-500">
          O scraper exporta o catálogo em JSON (100% local). A importação é idempotente: produtos já importados são
          atualizados, variantes sumidas são removidas e o histórico nunca é apagado.
        </p>
        {erro ? <p className="text-sm text-red-500">Erro: {erro}</p> : null}
        {resultado ? (
          <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm">
            <p>
              <strong>{resultado.grupos}</strong> produtos ({resultado.produtos} itens) ·{" "}
              <strong>{resultado.criados}</strong> criados · <strong>{resultado.atualizados}</strong> atualizados
            </p>
          </div>
        ) : null}
      </div>
    </Modal>
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

function ModalQuickAdd({
  tipo,
  grupoId,
  onClose,
  onSaved,
}: {
  tipo: "marca" | "grupo" | "subgrupo";
  grupoId: number | null;
  onClose: () => void;
  onSaved: (id: number, nome: string) => void;
}) {
  const [codigo, setCodigo] = useState("");
  const [nome, setNome] = useState("");
  const [salvando, setSalvando] = useState(false);

  const titulo = tipo === "marca" ? "Nova marca" : tipo === "grupo" ? "Novo grupo" : "Novo subgrupo";

  const salvar = async () => {
    const n = nome.trim();
    if (!n) {
      toast("Informe o nome", "error");
      return;
    }
    if (tipo === "subgrupo" && !grupoId) {
      toast("Selecione o grupo antes de criar o subgrupo.", "error");
      return;
    }
    setSalvando(true);
    try {
      if (tipo === "marca") {
        const m = await api.criarMarca(n);
        if (codigo.trim()) await api.atualizarCodigoMarca(m.id, codigo.trim());
        onSaved(m.id, m.nome);
      } else if (tipo === "grupo") {
        const g = await api.criarGrupo(codigo.trim() || n, n);
        onSaved(g.id, g.nome);
      } else {
        const s = await api.criarSubgrupo(grupoId!, codigo.trim() || n, n);
        onSaved(s.id, s.nome);
      }
      toast("Cadastrado com sucesso", "success");
      onClose();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={titulo}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" disabled={salvando} onClick={() => void salvar()}>
            Salvar
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-xs text-gray-500">
          O <strong>código</strong> entra no SKU estruturado (ex.: <code>ELE-CAB-SIL-25V</code>). Se vazio, usa o nome.
        </p>
        <Field label="Código (curto)">
          <Input placeholder={tipo === "marca" ? "Ex.: VOT" : tipo === "grupo" ? "Ex.: ELE" : "Ex.: CAB"} value={codigo} onChange={(e) => setCodigo(e.target.value.toUpperCase())} />
        </Field>
        <Field label="Nome *">
          <Input placeholder={tipo === "marca" ? "Ex.: Voltini" : tipo === "grupo" ? "Ex.: Elétrico" : "Ex.: Cabo Flexível"} value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </Field>
      </div>
    </Modal>
  );
}

export function ProdutoEditor() {
  const m = location.hash.match(/^#\/produtos\/(\d+)$/);
  const id = m ? Number(m[1]) : null;

  const [familias, setFamilias] = useState<Familia[]>([]);
  const [categoriasTree, setCategoriasTree] = useState<Record<string, string[]>>({});
  const [marcas, setMarcas] = useState<Marca[]>([]);
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [subgrupos, setSubgrupos] = useState<Subgrupo[]>([]);
  const [produto, setProduto] = useState<ProdutoCadastro | null>(null);
  const [form, setForm] = useState({ familia_id: "", marca: "", marca_id: "", external_id: "", nome: "", categoria: "", subcategoria: "", grupo_id: "", subgrupo_id: "", descricao: "", termos_busca: "" });
  const [atributos, setAtributos] = useState<FamiliaAtributo[]>([]);
  const [variantes, setVariantes] = useState<VarianteLocal[]>([]);
  const [tab, setTab] = useState<"gerais" | "atributos" | "variacoes" | "imagens" | "fiscal">("gerais");
  const [carregando, setCarregando] = useState(true);

  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [unidadesCompra, setUnidadesCompra] = useState<UnidadeCompra[]>([]);
  const [fornecedorRows, setFornecedorRows] = useState<FornecedorRow[]>([]);
  const fornecedorSeq = useRef(0);
  const [skuAvisos, setSkuAvisos] = useState<Record<number, string>>({});
  const [quickAdd, setQuickAdd] = useState<"marca" | "grupo" | "subgrupo" | null>(null);

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

      let marcas: Marca[] = [];
      try {
        marcas = await api.listarMarcas();
      } catch {
        marcas = [];
      }
      setMarcas(marcas);

      let grupos: Grupo[] = [];
      try {
        grupos = await api.listarGrupos();
      } catch {
        grupos = [];
      }
      setGrupos(grupos);

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
        marca_id: prod?.marca_id ? String(prod.marca_id) : "",
        external_id: prod?.external_id ?? "",
        nome: prod?.nome ?? "",
        categoria: prod?.categoria ?? "",
        subcategoria: prod?.subcategoria ?? "",
        grupo_id: prod?.grupo_id ? String(prod.grupo_id) : "",
        subgrupo_id: prod?.subgrupo_id ? String(prod.subgrupo_id) : "",
        descricao: prod?.descricao ?? "",
        termos_busca: prod?.termos_busca ?? "",
      });

      if (prod?.grupo_id) {
        try {
          setSubgrupos(await api.listarSubgrupos(prod.grupo_id));
        } catch {
          setSubgrupos([]);
        }
      } else {
        setSubgrupos([]);
      }

      const st = buildAtributosState(fs, familiaId, prod);
      setAtributos(st.atributos);
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
    setVariantes(st.variantes);
  };

  const trocarGrupo = (grupoId: string) => {
    setForm((f) => ({ ...f, grupo_id: grupoId, subgrupo_id: "" }));
    if (!grupoId) {
      setSubgrupos([]);
      return;
    }
    void (async () => {
      try {
        setSubgrupos(await api.listarSubgrupos(Number(grupoId)));
      } catch {
        setSubgrupos([]);
      }
    })();
  };

  const aoSalvarMarca = async (id: number, nome: string) => {
    setForm((f) => ({ ...f, marca: nome, marca_id: String(id) }));
    setMarcas(await api.listarMarcas().catch(() => []));
  };

  const aoSalvarGrupo = async (id: number, _nome: string) => {
    setGrupos(await api.listarGrupos().catch(() => []));
    setForm((f) => ({ ...f, grupo_id: String(id), subgrupo_id: "" }));
    setSubgrupos(await api.listarSubgrupos(id).catch(() => []));
  };

  const aoSalvarSubgrupo = async (id: number, _nome: string) => {
    if (form.grupo_id) setSubgrupos(await api.listarSubgrupos(Number(form.grupo_id)).catch(() => []));
    setForm((f) => ({ ...f, subgrupo_id: String(id) }));
  };

  // Cadastro individual de variações: cada variante carrega seus próprios
  // valores de atributo (subgrid na aba Variações).

  const adicionarVariante = () => {
    setVariantes((arr) => [
      ...arr,
      {
        sku: "",
        ean: "",
        preco: "",
        prom: "",
        peso: "",
        dimensoes: "",
        unidade_venda: "",
        embalagem: "",
        fator_conversao: "",
        localizacao: "",
        ncm: "",
        unidade_tributavel: "",
        valores: {},
      },
    ]);
  };

  const removerVariante = (idx: number) => {
    setVariantes((arr) => arr.filter((_, i) => i !== idx));
  };

  const atualizarValorVariante = (idx: number, attrId: number, value: string) => {
    setVariantes((arr) =>
      arr.map((v, i) => {
        if (i !== idx) return v;
        const novos = { ...v.valores };
        if (value.trim()) novos[String(attrId)] = value.trim();
        else delete novos[String(attrId)];
        return { ...v, valores: novos };
      })
    );
  };

  const atualizarVariante = (idx: number, field: keyof VarianteLocal, value: string) => {
    setVariantes((arr) => arr.map((v, i) => (i === idx ? { ...v, [field]: value } : v)));
    if (field === "sku") {
      setSkuAvisos((a) => ({ ...a, [idx]: "" }));
    }
  };

  const aplicarParaTodos = (field: keyof VarianteLocal) => {
    if (variantes.length < 2) return;
    const valorBase = variantes[0][field];
    setVariantes((arr) => arr.map((v) => ({ ...v, [field]: valorBase })));
    toast(`Valor da 1ª linha aplicado a todas as variações.`, "success");
  };

  const gerarSkus = async () => {
    if (!variantes.length) return;
    const nomeBase = (form.nome || form.marca || "").trim();
    const grupo = grupos.find((g) => String(g.id) === form.grupo_id);
    const subgrupo = subgrupos.find((s) => String(s.id) === form.subgrupo_id);
    const marcaCod =
      marcas.find((m) =>
        form.marca_id ? m.id === Number(form.marca_id) : m.nome === form.marca
      )?.codigo || "";
    const estruturado = !!(grupo?.codigo || subgrupo?.codigo || marcaCod);
    try {
      const res = await api.previewSkus({
        base: nomeBase || "SKU",
        produto_id: produto?.id ?? null,
        grupo_cod: grupo?.codigo || "",
        subgrupo_cod: subgrupo?.codigo || "",
        marca_cod: marcaCod,
        variantes: variantes.map((v) => {
          const familiaObj = familias.find((f) => String(f.id) === form.familia_id);
          const attrs = gerarSkuAtributos(v.valores, atributos, familiaObj?.sku_atributos);
          return {
            id: v.id ?? null,
            sku: attrs,
            attrs,
          };
        }),
      });
      const avisos: Record<number, string> = {};
      setVariantes((arr) =>
        arr.map((v, i) => {
          const r = res.skus[i];
          if (!r) return v;
          v = { ...v, sku: r.sku || v.sku };
          if (r.aviso) avisos[i] = r.aviso;
          return v;
        })
      );
      setSkuAvisos(avisos);
      const nAvisos = Object.keys(avisos).length;
      if (nAvisos)
        toast(
          `${nAvisos} SKU(s): vazio/duplicado/inválido ou emitido (mantido).`,
          "warn"
        );
      else if (estruturado)
        toast("SKUs estruturados gerados: [GRUPO]-[SUBGRUPO]-[MARCA]-[ATRIBUTOS].", "success");
      else
        toast("SKUs gerados a partir dos atributos.", "success");
    } catch {
      toast("Não foi possível gerar os SKUs.", "error");
    }
  };

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome base do produto", "error");
      return;
    }
    if (!variantes.length) {
      toast("Adicione ao menos uma variação", "error");
      setTab("variacoes");
      return;
    }
    // Validação por variante: atributos obrigatórios devem estar preenchidos
    // (aplicável apenas quando a família define atributos).
    const obr = atributos.filter((a) => a.obrigatorio);
    if (obr.length) {
      for (let i = 0; i < variantes.length; i++) {
        const faltando = obr.filter((a) => !(variantes[i].valores[String(a.id)] || "").trim());
        if (faltando.length) {
          toast(`Variação ${i + 1}: preencha os atributos obrigatórios: ${faltando.map((a) => a.nome).join(", ")}`, "error");
          setTab("variacoes");
          return;
        }
      }
    }
    const caAttrs = atributos.filter((a) => CA_RE.test(a.nome));
    if (caAttrs.length) {
      for (let i = 0; i < variantes.length; i++) {
        for (const a of caAttrs) {
          const v = variantes[i].valores[String(a.id)];
          if (v && !/^[\d.\s]+$/.test(String(v).trim())) {
            toast(`Variação ${i + 1}: o atributo "${a.nome}" deve ser um número de CA válido (ex.: 12345 ou 12.345).`, "error");
            setTab("variacoes");
            return;
          }
        }
      }
    }
    const familia_id = Number(form.familia_id) || null;
    const payload: ProdutoCadastroPayload = {
      familia_id,
      nome: form.nome.trim(),
      marca: form.marca.trim(),
      marca_id: form.marca_id ? Number(form.marca_id) : null,
      external_id: form.external_id.trim() || null,
      descricao: form.descricao.trim(),
      termos_busca: form.termos_busca.trim(),
      categoria: form.categoria.trim(),
      subcategoria: form.subcategoria.trim(),
      grupo_id: form.grupo_id ? Number(form.grupo_id) : null,
      subgrupo_id: form.subgrupo_id ? Number(form.subgrupo_id) : null,
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
      let bloqueadas = 0;
      let criadas = 0;
      let atributosFaltantes = 0;
      if (produto) {
        const res = await api.atualizarProdutoCadastro(produto.id, payload);
        desativadas = res.variantes?.desativadas || 0;
        bloqueadas = res.variantes?.bloqueadas || 0;
        criadas = res.variantes?.criadas || 0;
        atributosFaltantes = res.variantes?.atributos_faltantes || 0;
      } else {
        const res = await api.criarProdutoCadastro(payload);
        novoId = res.id;
      }
      if (atributosFaltantes) {
        toast(`Não foi possível salvar: ${atributosFaltantes} variação(ões) sem os atributos obrigatórios da família.`, "error");
        setTab("variacoes");
        return;
      }
      const avisos: string[] = [];
      if (desativadas) avisos.push(`${desativadas} variação(ões) removida(s) foram desativadas por possuírem estoque/preço/fornecedor (nenhum dado foi excluído)`);
      if (bloqueadas) avisos.push(`não foi possível remover ${bloqueadas} variação(ões): todo produto precisa de ao menos uma variação ativa`);
      if (criadas) avisos.push(`${criadas} variação(ões) padrão criada(s) automaticamente`);
      toast(avisos.length ? "Produto salvo. " + avisos.join("; ") : "Produto salvo", avisos.length ? "warn" : "success");
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
    ...(id ? [{ key: "fiscal" as const, label: "Perfil Fiscal" }] : []),
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
            <Field label="Família (opcional)">
              <div className="flex gap-2">
                <Select value={form.familia_id} onChange={(e) => trocarFamilia(Number(e.target.value) || null)} className="flex-1">
                  <option value="">— sem família —</option>
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
                <div className="flex gap-2">
                  <Input list="dlMarcas" placeholder="Ex.: Corfio" value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })} className="flex-1" />
                  <Button size="sm" variant="ghost" title="Cadastrar nova marca" onClick={() => setQuickAdd("marca")}>
                    +
                  </Button>
                </div>
                <datalist id="dlMarcas">
                  {marcas.map((m) => (
                    <option key={m.id} value={m.nome} />
                  ))}
                </datalist>
              </Field>
              <Field label="Código Fabricante">
                <Input placeholder="Ex.: B-66874" value={form.external_id} onChange={(e) => setForm({ ...form, external_id: e.target.value })} />
              </Field>
            </div>
            <Field label="Nome base do produto *">
              <Input placeholder="Ex.: Cabo Flexível 750V Antichama" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
              <div className="mt-1 text-xs text-gray-400" title="Padrão de nomenclatura de fábrica">
                {padraoText}
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
            <div className="grid grid-cols-2 gap-3">
              <Field label="Grupo (SKU)" hint="1º segmento do SKU estruturado">
                <div className="flex gap-2">
                  <Select value={form.grupo_id} onChange={(e) => trocarGrupo(e.target.value)} className="flex-1">
                    <option value="">—</option>
                    {grupos.map((g) => (
                      <option key={g.id} value={String(g.id)}>{g.codigo} · {g.nome}</option>
                    ))}
                  </Select>
                  <Button size="sm" variant="ghost" title="Cadastrar novo grupo" onClick={() => setQuickAdd("grupo")}>
                    +
                  </Button>
                </div>
              </Field>
              <Field label="Subgrupo (SKU)" hint="2º segmento do SKU estruturado">
                <div className="flex gap-2">
                  <Select value={form.subgrupo_id} onChange={(e) => setForm({ ...form, subgrupo_id: e.target.value })} className="flex-1" disabled={!form.grupo_id}>
                    <option value="">—</option>
                    {subgrupos.map((s) => (
                      <option key={s.id} value={String(s.id)}>{s.codigo} · {s.nome}</option>
                    ))}
                  </Select>
                  <Button size="sm" variant="ghost" title="Cadastrar novo subgrupo" disabled={!form.grupo_id} onClick={() => setQuickAdd("subgrupo")}>
                    +
                  </Button>
                </div>
              </Field>
            </div>
            <p className="text-xs text-gray-400">
              SKU estruturado: <code>[GRUPO]-[SUBGRUPO]-[MARCA]-[ATRIBUTOS]</code> (ex.: ELE-CAB-SIL-25V).
              Grupo e subgrupo têm código próprio; a marca e os atributos completam o SKU.
            </p>
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
          <p className="mb-3 text-sm text-gray-500">Atributos definidos pela família selecionada (referência). Os valores de cada atributo são informados em cada variação, na aba Variações.</p>
          {!form.familia_id ? (
            <p className="py-8 text-center text-sm text-gray-400">Sem família — este produto não possui atributos.</p>
          ) : atributos.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">Essa família não tem atributos. Edite a família para adicioná-los.</p>
          ) : (
            <div className="space-y-3">
              {atributos.map((a) => (
                <div key={a.id} className="rounded-lg border border-gray-200 bg-white p-3">
                  <div className="mb-1 text-sm font-medium text-gray-900">
                    {a.nome} {a.obrigatorio ? <span className="ml-1 rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-600">* obrigatório</span> : null}
                  </div>
                  <div className="text-xs text-gray-500">
                    {a.tipo === "lista" ? `Lista de opções: ${(a.opcoes || []).join(", ") || "—"}` : `Valor livre (${validacaoLabel(a.validacao)})`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "variacoes" && (
        <div>
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <Button variant="primary" onClick={adicionarVariante}>
              ＋ Adicionar variação
            </Button>
            {variantes.length > 0 && (
              <Button variant="secondary" onClick={() => void gerarSkus()}>
                Gerar SKUs
              </Button>
            )}
            {variantes.length > 0 && <span className="text-xs text-gray-500">{variantes.length} variação(ões)</span>}
            {!variantes.length && <span className="text-xs text-gray-500">Clique em "Adicionar variação" para cadastrar cada variação individualmente.</span>}
            {atributos.length > 0 && <span className="text-xs text-gray-400">Atributos da família: {atributos.map((a) => a.nome + (a.obrigatorio ? "*" : "")).join(" · ")}</span>}
          </div>

          {variantes.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {(
                      [
                        ["Variação", null],
                        ["SKU", null],
                        ["EAN", null],
                        ["Preço", "preco"],
                        ["Promo.", "prom"],
                        ["Peso", "peso"],
                        ["Dimensões", "dimensoes"],
                        ["Unid.", "unidade_venda"],
                        ["Emb.", "embalagem"],
                        ["Fator", "fator_conversao"],
                        ["Localização", "localizacao"],
                        ["NCM", "ncm"],
                        ["Unid. Trib.", "unidade_tributavel"],
                        ["", null],
                      ] as [string, keyof VarianteLocal | null][]
                    ).map(([h, field]) => (
                      <th key={h} className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                        <span className="inline-flex items-center gap-1">
                          {h}
                          {field && variantes.length > 1 && (
                            <button
                              type="button"
                              title="Copiar o valor da 1ª linha para todas as variações"
                              className="text-gray-400 hover:text-brand-600"
                              onClick={() => aplicarParaTodos(field)}
                            >
                              ↓⁝
                            </button>
                          )}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {variantes.map((v, idx) => (
                    <Fragment key={idx}>
                      <tr className="hover:bg-gray-50">
                        <td className="px-3 py-1.5 font-medium">{varianteLabel(v, atributos, idx)}</td>
                        <td className="px-3 py-1.5">
                          <CellInput value={String(v.sku)} onChange={(x) => atualizarVariante(idx, "sku", x)} placeholder="SKU" error={!!skuAvisos[idx]} title={skuAvisos[idx]} />
                        </td>
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
                          <button className="text-gray-400 hover:text-red-600" onClick={() => removerVariante(idx)}>
                            ×
                          </button>
                        </td>
                      </tr>
                      {atributos.length > 0 && (
                        <tr>
                          <td colSpan={14} className="bg-gray-50/60 px-3 py-2">
                            <div className="flex flex-wrap gap-3">
                              {atributos.map((a) => {
                                const val = v.valores[String(a.id)] || "";
                                const err = a.tipo === "livre" && val ? validarValorAtributo(a.tipo, a.validacao, val) : "";
                                return (
                                  <div key={a.id} className="min-w-[150px] flex-1">
                                    <label className="mb-0.5 block text-xs font-medium text-gray-600">
                                      {a.nome} {a.obrigatorio ? <span className="text-red-500">*</span> : null}
                                    </label>
                                    {a.tipo === "lista" ? (
                                      <select
                                        className="w-full rounded border border-gray-200 bg-white px-2 py-1 text-xs"
                                        value={val}
                                        onChange={(e) => atualizarValorVariante(idx, a.id, e.target.value)}
                                      >
                                        <option value="">—</option>
                                        {(a.opcoes || []).map((o) => (
                                          <option key={o} value={o}>{o}</option>
                                        ))}
                                      </select>
                                    ) : (
                                      <div>
                                        <input
                                          className="w-full rounded border border-gray-200 px-2 py-1 text-xs"
                                          inputMode={a.validacao === "numero" ? "decimal" : "text"}
                                          value={val}
                                          placeholder={a.validacao === "numero" ? "número" : a.validacao === "alphanumerico" ? "letras e números" : "texto"}
                                          onChange={(e) => atualizarValorVariante(idx, a.id, e.target.value)}
                                        />
                                        {err && <p className="mt-0.5 text-[10px] text-red-500">{err}</p>}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
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

      {tab === "fiscal" && (
        <div>
          {id ? <PerfilFiscalPanel variantes={variantes} /> : null}
        </div>
      )}

      <div className="mt-6 flex justify-end gap-2">
        <Button onClick={() => (location.hash = "#/produtos")}>Cancelar</Button>
        <Button variant="primary" onClick={() => void salvar()}>
          Salvar produto
        </Button>
      </div>

      {quickAdd && (
        <ModalQuickAdd
          tipo={quickAdd}
          grupoId={form.grupo_id ? Number(form.grupo_id) : null}
          onClose={() => setQuickAdd(null)}
          onSaved={quickAdd === "marca" ? aoSalvarMarca : quickAdd === "grupo" ? aoSalvarGrupo : aoSalvarSubgrupo}
        />
      )}
    </div>
  );
}

function num(x: string | number): string {
  return x !== "" && x != null ? String(x) : "";
}

function CellInput({ value, onChange, placeholder, type, error, title }: { value: string; onChange: (v: string) => void; placeholder?: string; type?: string; error?: boolean; title?: string }) {
  return (
    <input
      type={type || "text"}
      className={`w-24 rounded border px-2 py-1 text-xs focus:outline-none ${error ? "border-red-400 bg-red-50 focus:border-red-500" : "border-gray-200 focus:border-brand-500"}`}
      placeholder={placeholder}
      value={value}
      title={title}
      onChange={(e) => onChange(e.target.value)}
    />
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
  const variantes: VarianteLocal[] = [];
  if (produto && produto.familia_id === familiaId) {
    (produto.variantes || []).forEach((v) => {
      const vals: Record<string, string> = {};
      atributos.forEach((a) => {
        const val = v.atributos ? v.atributos[String(a.id)] : undefined;
        if (val) vals[String(a.id)] = val;
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
  return { atributos, variantes };
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

// ─── Perfil fiscal (classificação por variante) ─────────────────────────

function PerfilFiscalPanel({ variantes }: { variantes: VarianteLocal[] }) {
  const comId = variantes.filter((v) => v.id != null);
  const [varianteSel, setVarianteSel] = useState<number | null>(comId[0]?.id ?? null);
  const [perfil, setPerfil] = useState<PerfilFiscal | null>(null);
  const [ncmBusca, setNcmBusca] = useState("");
  const [ncmResultados, setNcmResultados] = useState<{ codigo: string; descricao: string }[]>([]);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (varianteSel == null) return;
    api.perfilFiscalObter(varianteSel).then(setPerfil).catch(() => toast("Erro ao ler perfil fiscal", "error"));
  }, [varianteSel]);

  const buscarNcm = async () => {
    if (!ncmBusca.trim()) return;
    try {
      setNcmResultados(await api.buscarNcm(ncmBusca.trim()));
    } catch (e) {
      toast("Erro na busca de NCM: " + (e as Error).message, "error");
    }
  };

  const salvar = async () => {
    if (varianteSel == null || !perfil) return;
    setSalvando(true);
    try {
      const salvo = await api.perfilFiscalSalvar(varianteSel, perfil);
      setPerfil(salvo);
      toast("Perfil fiscal salvo", "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  if (comId.length === 0) {
    return <p className="py-8 text-center text-sm text-gray-400">Salve o produto e crie variações para classificar o perfil fiscal.</p>;
  }

  const campo = "w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm";

  return (
    <div className="max-w-xl space-y-4">
      <div>
        <label className="text-xs uppercase text-gray-400">Variação</label>
        <select className={campo} value={varianteSel ?? ""} onChange={(e) => setVarianteSel(Number(e.target.value))}>
          {comId.map((v) => (
            <option key={v.id} value={v.id!}>
              {v.sku || `(sem SKU)`} {v.ean ? `· ${v.ean}` : ""}
            </option>
          ))}
        </select>
      </div>

      {!perfil ? (
        <p className="py-4 text-center text-sm text-gray-400">Carregando…</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs uppercase text-gray-400">NCM</label>
              <input className={campo} value={perfil.ncm} onChange={(e) => setPerfil({ ...perfil, ncm: e.target.value })} placeholder="ex.: 8544.42.00" />
            </div>
            <div>
              <label className="text-xs uppercase text-gray-400">CEST</label>
              <input className={campo} value={perfil.cest} onChange={(e) => setPerfil({ ...perfil, cest: e.target.value })} placeholder="opcional" />
              <p className="mt-1 text-[11px] text-gray-400">Fios/cabos uso construção (8544): <b>12.007.00</b> — Anexo VII Cap.12 item 7.0 (Conf. Consulta SEF/MG 105/2021).</p>
            </div>
            <div>
              <label className="text-xs uppercase text-gray-400">Origem da mercadoria</label>
              <select className={campo} value={perfil.origem} onChange={(e) => setPerfil({ ...perfil, origem: Number(e.target.value) })}>
                <option value={0}>0 — Nacional (exceto 3, 4, 5 e 8)</option>
                <option value={1}>1 — Estrangeira — importação direta</option>
                <option value={2}>2 — Estrangeira — adquirida no mercado interno</option>
                <option value={3}>3 — Nacional, conteúdo importação &gt; 40%</option>
                <option value={4}>4 — Nacional, processos produtivos básicos</option>
                <option value={5}>5 — Nacional, processo produtivo básico</option>
                <option value={8}>8 — Nacional, conteúdo importação ≤ 40%</option>
              </select>
              <p className="mt-1 text-[11px] text-gray-400">Vem das NFs de entrada dos fornecedores (não é consulta legal).</p>
            </div>
            <div>
              <label className="text-xs uppercase text-gray-400">Enquadramento ST (regime_st)</label>
              <input className={campo} value={perfil.regime_st} onChange={(e) => setPerfil({ ...perfil, regime_st: e.target.value })} placeholder="opcional" />
              <p className="mt-1 text-[11px] text-gray-400">Ex.: <code>substituido_ja_retido</code> quando a entrada reteve ICMS-MG.</p>
            </div>
          </div>

          <div className="rounded-md border border-gray-200 p-3">
            <p className="mb-2 text-xs uppercase text-gray-400">Buscar NCM versionado (fonte oficial)</p>
            <div className="flex gap-2">
              <input
                className={campo}
                value={ncmBusca}
                onChange={(e) => setNcmBusca(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void buscarNcm()}
                placeholder="código ou termo da descrição"
              />
              <Button onClick={() => void buscarNcm()}>Buscar</Button>
            </div>
            {ncmResultados.length > 0 && (
              <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-sm">
                {ncmResultados.map((n) => (
                  <li key={n.codigo}>
                    <button
                      type="button"
                      className="text-left hover:underline"
                      onClick={() =>
                        setPerfil((prev: PerfilFiscal | null) =>
                          prev ? { ...prev, ncm: n.codigo } : prev,
                        )
                      }
                    >
                      <span className="font-mono">{n.codigo}</span> — {n.descricao}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-[11px] text-gray-400">NCM não encontrado? Registre com fonte oficial via POST /api/fiscal/ncm — nunca inventar código.</p>
          </div>

          <div className="flex justify-end">
            <Button variant="primary" disabled={salvando} onClick={() => void salvar()}>
              {salvando ? "Salvando…" : "Salvar perfil fiscal"}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
