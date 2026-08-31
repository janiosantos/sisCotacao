// pages/produtos.tsx — cadastro de produtos (famílias + produto pai + variações + imagens).

import { useEffect, useRef, useState } from "react";
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
  type UnidadeCompra,
  type SaldoItem,
  type CategoriaTree,
} from "../api/client";
import { fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Field, Input, Loading, Modal, PageHeader, Select } from "../ui/ui";
import { temPermissao } from "../perm";
import { ModalImportarUrl } from "./produtos/modal-importar-url";
import { ModalImportarCatalogo } from "./produtos/modal-importar-catalogo";
import { ModalEtiquetas } from "./produtos/modal-etiquetas";
import { Imagens } from "./produtos/imagens";
import { PerfilFiscalPanel } from "./produtos/perfil-fiscal-panel";
import { Conversoes } from "./produtos/conversoes";
import { Identificadores } from "./produtos/identificadores";
import { ModalImportarLote } from "./produtos/modal-importar-lote";
import { StatusCadastro } from "./produtos/status-cadastro";
import { Relacoes } from "./produtos/relacoes";
import { RegrasPreco } from "./produtos/regras-preco";

const PAGE = 60;

interface DadosOperacionais {
  sku: string;
  ean: string;
  preco: string;
  prom: string;
  peso: string;
  dimensoes: string;
  unidade_venda: string;
  embalagem: string;
  fator_conversao: string;
  localizacao: string;
  ncm: string;
  unidade_tributavel: string;
  bitola: string;
  tensao: string;
  potencia: string;
  comprimento: string;
  diametro: string;
  rosca: string;
  material: string;
  cor: string;
  norma: string;
  validade_dias: string;
  garantia_dias: string;
}

const DADOS_INICIAIS: DadosOperacionais = {
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
  bitola: "",
  tensao: "",
  potencia: "",
  comprimento: "",
  diametro: "",
  rosca: "",
  material: "",
  cor: "",
  norma: "",
  validade_dias: "",
  garantia_dias: "",
};

interface FornecedorRow {
  uid: string;
  fornecedor_id: string;
  codigo: string;
  unidade: string;
  fator: string | number;
}

interface ProdutoEditorForm {
  familia_id: string;
  marca: string;
  marca_id: string;
  external_id: string;
  nome: string;
  categoria: string;
  subcategoria: string;
  grupo_id: string;
  subgrupo_id: string;
  descricao: string;
  termos_busca: string;
}

const CA_RE = /(^|[^a-z0-9])(n\s?[º°]?\s?ca|ca|certificado|aprovacao)([^a-z0-9]|$)/i;

function normalize(str: string): string {
  return String(str || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
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
  const [modalImportarLote, setModalImportarLote] = useState(false);
  const [loteProduto, setLoteProduto] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

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
  }, [filters, page, refreshKey]);

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
    if (!window.confirm("Excluir este produto e as suas imagens?")) return;
    try {
      const res = await api.excluirProdutoCadastro(id);
      if (res.desativadas > 0) {
        toast(`Produto desativado (não excluído): possui estoque/preço/fornecedor e foi preservado.`, "warn");
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
        <Button variant="outline" onClick={() => setModalImportarLote(true)}>
          Importar lote
        </Button>
        <Button variant="outline" onClick={() => setModalUrl(true)}>
          Novo via URL
        </Button>
        {temPermissao("produtos", "cadastrar") ? (
          <Button variant="primary" onClick={() => (location.hash = "#/produtos/novo")}>
            Novo produto
          </Button>
        ) : null}
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
                  {p.classe_abc ? <Badge tone="blue">{p.classe_abc}</Badge> : null}
                </p>
                <p className="mt-1 line-clamp-2 text-sm font-medium text-gray-900">{p.nome}</p>
                {(() => {
                  const detalhe =
                    p.descricao && p.nome && p.descricao.toLowerCase().startsWith(p.nome.toLowerCase())
                      ? p.descricao.slice(p.nome.length).replace(/^[\s:·-]+/, "").trim()
                      : p.descricao || "";
                  return detalhe ? <p className="mt-0.5 line-clamp-2 text-xs text-gray-600">{detalhe}</p> : null;
                })()}
                {p.sku ? <p className="mt-0.5 font-mono text-[11px] text-gray-400">SKU: {p.sku}</p> : null}
                {p.marca ? <p className="text-xs text-gray-400">{p.marca}</p> : null}
                <p className="mt-2 text-sm font-semibold text-gray-900">{p.preco != null ? fmtMoney(p.preco) : p.price_min ? fmtMoney(p.price_min) : "sem preço"}</p>
              </div>
              <div className="flex gap-2 border-t border-gray-100 p-3">
                <Button variant="primary" size="sm" className="flex-1" onClick={() => (location.hash = `#/produtos/${p.id}`)}>
                  Editar
                </Button>
                <Button size="sm" variant="ghost" title="Baixar imagens em lote (irmãos)" onClick={() => setLoteProduto(p.id)}>
                  🖼️
                </Button>
                {temPermissao("produtos", "excluir") ? (
                  <Button variant="danger" size="sm" onClick={() => void excluir(p.id)}>
                    Excluir
                  </Button>
                ) : null}
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
      <ModalImportarLote open={modalImportarLote} onClose={() => setModalImportarLote(false)} />
      <ModalEtiquetas open={modalEtiquetas} onClose={() => setModalEtiquetas(false)} />
      {loteProduto != null && (
        <ModalImagensLote
          produtoId={loteProduto}
          onClose={() => setLoteProduto(null)}
          onAplicado={() => setRefreshKey((k) => k + 1)}
        />
      )}
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
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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

// ===================================================================
// INDICADOR DE COMPLETUDE (Dados Gerais)
// ===================================================================

function CompletudeDadosGerais({ form, dados }: { form: ProdutoEditorForm; dados: DadosOperacionais }) {
  const itens: { rotulo: string; preenchido: boolean; dica?: string }[] = [
    { rotulo: "Nome base do produto", preenchido: !!form.nome.trim() },
    { rotulo: "Marca", preenchido: !!form.marca.trim() },
    { rotulo: "Categoria", preenchido: !!form.categoria.trim(), dica: "Ex.: Fios e Cabos" },
    { rotulo: "Subcategoria", preenchido: !!form.subcategoria.trim(), dica: "Ex.: Cabo Flexível" },
    { rotulo: "Grupo (SKU)", preenchido: !!form.grupo_id, dica: "1º segmento do SKU estruturado" },
    { rotulo: "Subgrupo (SKU)", preenchido: !!form.subgrupo_id, dica: "2º segmento do SKU estruturado" },
    { rotulo: "Código fabricante", preenchido: !!form.external_id.trim(), dica: "Referência do fornecedor" },
    { rotulo: "Preço de venda > 0", preenchido: Number(dados.preco) > 0 },
  ];
  const preenchidos = itens.filter((i) => i.preenchido).length;
  const pct = Math.round((preenchidos / itens.length) * 100);
  const pendentes = itens.filter((i) => !i.preenchido);
  const concluido = preenchidos === itens.length;
  return (
    <div className={`rounded-lg border bg-white p-4 ${concluido ? "border-green-200" : "border-amber-200"}`}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Completude do cadastro</div>
        <Badge tone={concluido ? "green" : "amber"}>
          {preenchidos}/{itens.length}
        </Badge>
      </div>
      <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
        <div className={`h-full rounded-full ${concluido ? "bg-green-500" : "bg-amber-500"}`} style={{ width: `${pct}%` }} />
      </div>
      {pendentes.length === 0 ? (
        <p className="text-xs text-green-700">Cadastro completo — todos os dados gerais obrigatórios preenchidos.</p>
      ) : (
        <ul className="space-y-1">
          {pendentes.map((p) => (
            <li key={p.rotulo} className="flex items-start gap-1.5 text-xs text-gray-600">
              <span className="mt-0.5 text-amber-500">●</span>
              <span>
                <strong>{p.rotulo}</strong>
                {p.dica ? <span className="text-gray-400"> — {p.dica}</span> : null}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ===================================================================
// ESTOQUE POR DEPÓSITO + SITUAÇÃO (aba Variações)
// ===================================================================

function EstoqueDeposito({ produtoId }: { produtoId: number }) {
  const [saldos, setSaldos] = useState<SaldoItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let alive = true;
    setCarregando(true);
    setErro("");
    api
      .saldoEstoque({ produto_id: produtoId })
      .then((rows) => {
        if (alive) setSaldos(rows || []);
      })
      .catch((e) => {
        if (alive) setErro((e as Error).message);
      })
      .finally(() => {
        if (alive) setCarregando(false);
      });
    return () => {
      alive = false;
    };
  }, [produtoId]);

  const badgeSituacao = (sit?: string) =>
    sit === "ruptura" ? (
      <Badge tone="red">Ruptura</Badge>
    ) : sit === "excesso" ? (
      <Badge tone="amber">Excesso</Badge>
    ) : (
      <Badge tone="green">OK</Badge>
    );

  if (carregando) return <p className="text-xs text-gray-400">Carregando estoque…</p>;
  if (erro) return <p className="text-xs text-red-500">Erro ao carregar estoque: {erro}</p>;
  if (saldos.length === 0)
    return <p className="text-xs text-gray-400">Sem saldo registrado para este produto.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Depósito</th>
            <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Saldo</th>
            <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Situação</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {saldos.map((s, j) => (
            <tr key={j}>
              <td className="px-3 py-1.5 font-medium">{s.deposito_nome}</td>
              <td className="px-3 py-1.5">
                {s.quantidade}
                {s.reserva > 0 ? <span className="text-gray-400"> (reserva {s.reserva})</span> : null}
              </td>
              <td className="px-3 py-1.5">{badgeSituacao(s.situacao)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ProdutoEditor() {
  const m = location.hash.match(/^#\/produtos\/(\d+)$/);
  const id = m ? Number(m[1]) : null;

  const [familias, setFamilias] = useState<Familia[]>([]);
  const [categoriasTree, setCategoriasTree] = useState<CategoriaTree[]>([]);
  const [marcas, setMarcas] = useState<Marca[]>([]);
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [subgrupos, setSubgrupos] = useState<Subgrupo[]>([]);
  const [produto, setProduto] = useState<ProdutoCadastro | null>(null);
  const [form, setForm] = useState({ familia_id: "", marca: "", marca_id: "", external_id: "", nome: "", categoria: "", subcategoria: "", grupo_id: "", subgrupo_id: "", descricao: "", termos_busca: "" });
  const [atributos, setAtributos] = useState<FamiliaAtributo[]>([]);
  const [dados, setDados] = useState<DadosOperacionais>(DADOS_INICIAIS);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [tab, setTab] = useState<"gerais" | "atributos" | "dados" | "imagens" | "fiscal" | "conversoes" | "codigos" | "relacoes" | "precos">("gerais");
  const [carregando, setCarregando] = useState(true);

  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [unidadesCompra, setUnidadesCompra] = useState<UnidadeCompra[]>([]);
  const [fornecedorRows, setFornecedorRows] = useState<FornecedorRow[]>([]);
  const fornecedorSeq = useRef(0);
  const [quickAdd, setQuickAdd] = useState<"marca" | "grupo" | "subgrupo" | null>(null);

  useEffect(() => {
    void (async () => {
      // Restaura rascunho duplicado (novo produto)
      if (!id) {
        try {
          const rascunho = sessionStorage.getItem("dup_produto");
          if (rascunho) {
            const copia = JSON.parse(rascunho);
            setForm((f) => ({ ...f, ...copia }));
            sessionStorage.removeItem("dup_produto");
          }
        } catch {
          /* rascunho inválido — ignora */
        }
      }
      let fs: Familia[] = [];
      try {
        fs = await api.listarFamilias();
      } catch {
        fs = [];
      }
      setFamilias(fs);

      let tree: CategoriaTree[] = [];
      try {
        tree = await api.listarCategoriasTree();
      } catch {
        tree = [];
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
      setDados(st.dados);
      setValores(st.valores);

      if (prod) {
        const [f, u] = await Promise.all([api.listarFornecedores(true), api.listarUnidadesCompra(true)]).catch(() => [[], []] as [Fornecedor[], UnidadeCompra[]]);
        setFornecedores(f);
        setUnidadesCompra(u);
        const rows = seedFornecedorRows(prod, fornecedorSeq);
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
    setDados(st.dados);
    setValores(st.valores);
  };

  const trocarGrupo = (grupoId: string) => {
    setForm((f) => ({ ...f, grupo_id: grupoId, subgrupo_id: "", categoria: "", subcategoria: "" }));
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

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome base do produto", "error");
      return;
    }
    const obr = atributos.filter((a) => a.obrigatorio);
    const faltando = obr.filter((a) => !(valores[a.nome] || "").trim());
    if (faltando.length) {
      toast(`Preencha os atributos obrigatórios: ${faltando.map((a) => a.nome).join(", ")}`, "error");
      setTab("dados");
      return;
    }
    const caAttrs = atributos.filter((a) => CA_RE.test(a.nome));
    for (const a of caAttrs) {
      const v = valores[a.nome];
      if (v && !/^[\d.\s]+$/.test(String(v).trim())) {
        toast(`O atributo "${a.nome}" deve ser um número de CA válido (ex.: 12345 ou 12.345).`, "error");
        setTab("dados");
        return;
      }
    }
    const familia_id = Number(form.familia_id) || null;
    const payload: ProdutoCadastroPayload = {
      familia_id,
      nome: form.nome.trim(),
      marca: form.marca.trim(),
      marca_id: form.marca_id ? Number(form.marca_id) : null,
      external_id: form.external_id.trim() || null,
      descricao: form.descricao.trim() || descricaoSugerida,
      termos_busca: form.termos_busca.trim(),
      categoria: form.categoria.trim(),
      subcategoria: form.subcategoria.trim(),
      grupo_id: form.grupo_id ? Number(form.grupo_id) : null,
      subgrupo_id: form.subgrupo_id ? Number(form.subgrupo_id) : null,
      sku: dados.sku || "",
      ean: dados.ean || "",
      preco: dados.preco !== "" && dados.preco != null ? Number(dados.preco) : 0,
      preco_promocional: dados.prom !== "" ? Number(dados.prom) : null,
      peso: dados.peso !== "" ? Number(dados.peso) : null,
      dimensoes: dados.dimensoes || "",
      unidade_venda: dados.unidade_venda || "UN",
      embalagem: dados.embalagem !== "" ? Number(dados.embalagem) : null,
      fator_conversao: dados.fator_conversao !== "" ? Number(dados.fator_conversao) : null,
      localizacao: dados.localizacao || "",
      ncm: dados.ncm || "",
      unidade_tributavel: dados.unidade_tributavel || "",
      bitola: dados.bitola || "",
      tensao: dados.tensao || "",
      potencia: dados.potencia || "",
      comprimento: dados.comprimento || "",
      diametro: dados.diametro || "",
      rosca: dados.rosca || "",
      material: dados.material || "",
      cor: dados.cor || "",
      norma: dados.norma || "",
      validade_dias: dados.validade_dias !== "" ? Number(dados.validade_dias) : null,
      garantia_dias: dados.garantia_dias !== "" ? Number(dados.garantia_dias) : null,
      atributos: valores,
    };
    try {
      let novoId = produto ? produto.id : null;
      if (produto) {
        const res = await api.atualizarProdutoCadastro(produto.id, payload);
        const desativadas = res.desativadas || 0;
        const bloqueadas = res.bloqueadas || 0;
        const criadas = res.criadas || 0;
        const atributosFaltantes = res.atributos_faltantes || 0;
        if (atributosFaltantes) {
          toast(`Não foi possível salvar: ${atributosFaltantes} produto(s) sem os atributos obrigatórios da família.`, "error");
          setTab("dados");
          return;
        }
        const avisos: string[] = [];
        if (desativadas) avisos.push(`${desativadas} registro(s) desativado(s) por possuir estoque/preço/fornecedor (nenhum dado foi excluído)`);
        if (bloqueadas) avisos.push(`não foi possível remover ${bloqueadas} registro(s)`);
        if (criadas) avisos.push(`${criadas} registro(s) criado(s) automaticamente`);
        toast(avisos.length ? "Produto salvo. " + avisos.join("; ") : "Produto salvo", avisos.length ? "warn" : "success");
      } else {
        const res = await api.criarProdutoCadastro(payload);
        novoId = res.id;
        toast("Produto salvo", "success");
      }
      location.hash = `#/produtos/${novoId}`;
    } catch (e) {
      toast("Erro ao salvar: " + (e as Error).message, "error");
    }
  };

  const salvarFornecedor = async () => {
    if (!produto) return;
    const porFornecedor: Record<number, FornecedorVariantePayload[]> = {};
    for (const r of fornecedorRows) {
      const fornecedorId = Number(r.fornecedor_id);
      if (!fornecedorId) continue;
      const item: FornecedorVariantePayload = {
        produto_id: produto.id,
        codigo_fornecedor: r.codigo || "",
        descricao_fornecedor: "",
        unidade_compra: r.unidade || "",
        fator_conversao: r.fator !== "" && r.fator != null ? Number(r.fator) : 1,
      };
      (porFornecedor[fornecedorId] ||= []).push(item);
    }
    const envolver = new Set(Object.keys(porFornecedor).map(Number));
    for (const fv of produto.fornecedor_variantes || []) envolver.add(fv.fornecedor_id);
    const sucesso: string[] = [];
    const erros: string[] = [];
    for (const fid of envolver) {
      try {
        const itens = porFornecedor[fid] ? porFornecedor[fid]! : [];
        await api.salvarFornecedorVariantes(produto.id, fid, itens);
        sucesso.push(fornecedores.find((f) => f.id === fid)?.nome || "fornecedor " + fid);
      } catch (e) {
        erros.push((fornecedores.find((f) => f.id === fid)?.nome || String(fid)) + " (" + (e as Error).message + ")");
      }
    }
    if (!sucesso.length && !erros.length) {
      toast("Adicione ao menos uma linha e selecione o fornecedor.", "warn");
      return;
    }
    if (sucesso.length) toast(`Códigos salvos: ${sucesso.join(", ")}`, "success");
    if (erros.length) toast("Erro: " + erros.join("; "), "error");
  };

  // Categorias disponíveis conforme Grupo/Subgrupo selecionados:
// - subgrupo escolhido → categorias daquele subgrupo;
// - só grupo escolhido → categorias dos subgrupos do grupo;
// - nada → todas (mantém a atual se for customizada).
  const subgrupoIdsDoGrupo = new Set(subgrupos.map((s) => s.id));
  const categoriasFiltradas = categoriasTree.filter((c) => {
    if (form.subgrupo_id) return c.subgrupo_id === Number(form.subgrupo_id);
    if (form.grupo_id) return c.subgrupo_id != null && subgrupoIdsDoGrupo.has(c.subgrupo_id);
    return true;
  });
  const catAtual = categoriasTree.find((c) => c.nome === form.categoria);
  const subcategorias = catAtual ? catAtual.subcategorias.map((s) => s.nome) : [];
  const duplicar = () => {
    // Copia o cadastro como novo rascunho (mantém atributos/dados p/ edição)
    const copia = { ...form, id: undefined };
    sessionStorage.setItem("dup_produto", JSON.stringify(copia));
    location.hash = "#/produtos/novo";
    toast("Copiado como rascunho — revise antes de salvar", "success");
  };
  const padraoText = normalize(form.categoria).includes("epi")
    ? "Padrão EPI: Item + Material/Tamanho + Nº CA + Marca."
    : normalize(form.categoria).includes("cabo") || normalize(form.categoria).includes("fio")
      ? "Padrão de cabos: Item + Bitola (mm²) + Tensão + Norma/Marca."
      : "Padrão: Item + Características (bitola, tensão, CA) + Marca.";

  // Descrição padronizada: Nome + [valores dos atributos na ordem da família] + " - Marca".
  // É usada diretamente na busca (características embutidas) e como rótulo no PDV.
  const descricaoSugerida = [
    form.nome.trim(),
    ...atributos.map((a) => (valores[a.nome] || "").trim()).filter(Boolean),
    form.marca.trim() ? `- ${form.marca.trim()}` : "",
  ].filter(Boolean).join(" ");

  const sugerirSku = () => {
    const partes = [form.nome, ...atributos.map((a) => (valores[a.nome] || "").trim()), form.marca].filter((v) => v && v.trim());
    const sku = normalize(partes.join(" ")).replace(/[^a-z0-9]+/g, "-").replace(/(^-+|-+$)/g, "").slice(0, 40).toUpperCase();
    setDados((d) => ({ ...d, sku: sku || d.sku }));
    toast(sku ? `SKU sugerido: ${sku}` : "Preencha nome/atributos/marca para sugerir o SKU.", sku ? "success" : "warn");
  };

  const TABS: { key: typeof tab; label: string }[] = [
    { key: "gerais", label: "Dados Gerais" },
    { key: "atributos", label: "Atributos da Família" },
    { key: "dados", label: "Dados e Variação" },
    { key: "imagens", label: "Mídia e Anexos" },
    ...(id ? [{ key: "fiscal" as const, label: "Perfil Fiscal" }] : []),
    ...(id ? [{ key: "conversoes" as const, label: "Conversões" }] : []),
    ...(id ? [{ key: "codigos" as const, label: "Códigos" }] : []),
    ...(id ? [{ key: "relacoes" as const, label: "Relações" }] : []),
    ...(id ? [{ key: "precos" as const, label: "Regras de preço" }] : []),
  ];

  return (
    <div>
      <PageHeader
        title={produto ? "Editar produto" : "Novo produto"}
        subtitle="Cadastre o produto uma vez; as variações são geradas pelas combinações dos atributos."
        actions={
          <div className="flex gap-2">
            {produto && id ? <StatusCadastro produtoId={id} inicial={produto.status_cadastro} /> : null}
            {produto && (
              <Button variant="ghost" onClick={duplicar}>⧉ Duplicar</Button>
            )}
            <Button variant="ghost" onClick={() => (location.hash = "#/produtos")}>
              ← Voltar
            </Button>
          </div>
        }
      />

      <div className="mb-4 flex gap-2 overflow-x-auto border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${
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
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Categoria" hint={form.grupo_id ? "Filtrada pelo grupo/subgrupo" : ""}>
                <Select
                  value={form.categoria}
                  onChange={(e) => setForm({ ...form, categoria: e.target.value, subcategoria: "" })}
                  className="flex-1"
                >
                  <option value="">— selecione —</option>
                  {categoriasFiltradas.map((c) => (
                    <option key={c.id} value={c.nome}>
                      {c.nome}
                    </option>
                  ))}
                  {form.categoria && !categoriasFiltradas.some((c) => c.nome === form.categoria) ? (
                    <option value={form.categoria}>{form.categoria}</option>
                  ) : null}
                </Select>
              </Field>
              <Field label="Subcategoria">
                <Select
                  value={form.subcategoria}
                  onChange={(e) => setForm({ ...form, subcategoria: e.target.value })}
                  className="flex-1"
                  disabled={!form.categoria}
                >
                  <option value="">— selecione —</option>
                  {subcategorias.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
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
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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
            <Field label="Descrição padrão / PDV (opcional)">
              <Input placeholder="Ex.: Cabo Flexível 2,5mm² Verde 750V - SIL" value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
              <div className="mt-1 flex items-center gap-2 rounded-md bg-gray-50 px-2 py-1.5 text-xs text-gray-600">
                <span className="font-medium text-gray-700">Sugestão:</span>
                <span className="flex-1 truncate">{descricaoSugerida || "— preencha nome, atributos e marca —"}</span>
                <Button size="sm" variant="ghost" disabled={!descricaoSugerida} onClick={() => setForm({ ...form, descricao: descricaoSugerida })}>
                  usar como descrição
                </Button>
              </div>
              <p className="mt-1 text-xs text-gray-400">A descrição padronizada (nome + características + marca) é usada diretamente na busca e como rótulo no PDV.</p>
            </Field>
            <Field label="Termos de busca / sinônimos">
              <Input placeholder="Ex.: cabo, fio, 750V, antichama, barramento…" value={form.termos_busca} onChange={(e) => setForm({ ...form, termos_busca: e.target.value })} />
              <p className="mt-1 text-xs text-gray-400">Palavras-chave e variações do nome usado pelo mercado, para facilitar a busca (ex.: "fio" além de "cabo").</p>
            </Field>
          </div>
          <aside className="space-y-4">
            <CompletudeDadosGerais form={form} dados={dados} />
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Curva ABC · Gestão de Linha</div>
              {produto ? <AbcRecap p={produto} /> : <p className="text-sm text-gray-400">Salve o produto para ver os indicadores de gestão.</p>}
            </div>
          </aside>
        </div>
      )}

      {tab === "atributos" && (
        <div>
          <p className="mb-3 text-sm text-gray-500">Atributos definidos pela família selecionada (referência). Os valores de cada atributo são informados na aba Dados e Variação.</p>
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

      {tab === "dados" && (
        <div>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-gray-900">Dados operacionais do produto</h4>
              <p className="text-xs text-gray-500">Este produto é uma unidade única (antiga variação). Preencha os campos operacionais e, se houver família, os valores dos atributos.</p>
            </div>
            <Button size="sm" variant="ghost" onClick={sugerirSku} title="Gera um SKU a partir de nome + atributos + marca">
              ✨ Sugerir SKU
            </Button>
          </div>

          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">SKU</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">EAN</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Preço</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Promo.</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Peso</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Dimensões</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Unid.</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Emb.</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Fator</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Localização</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">NCM</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Unid. Trib.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr className="hover:bg-gray-50">
                  <td className="px-3 py-1.5"><CellInput value={dados.sku} onChange={(x) => setDados((d) => ({ ...d, sku: x }))} placeholder="SKU" /></td>
                  <td className="px-3 py-1.5"><CellInput value={dados.ean} onChange={(x) => setDados((d) => ({ ...d, ean: x }))} placeholder="EAN" /></td>
                  <td className="px-3 py-1.5"><CellInput type="number" value={dados.preco} onChange={(x) => setDados((d) => ({ ...d, preco: x }))} placeholder="R$" /></td>
                  <td className="px-3 py-1.5"><CellInput type="number" value={dados.prom} onChange={(x) => setDados((d) => ({ ...d, prom: x }))} placeholder="Promo" /></td>
                  <td className="px-3 py-1.5"><CellInput type="number" value={dados.peso} onChange={(x) => setDados((d) => ({ ...d, peso: x }))} placeholder="kg" /></td>
                  <td className="px-3 py-1.5"><CellInput value={dados.dimensoes} onChange={(x) => setDados((d) => ({ ...d, dimensoes: x }))} placeholder="CxLxA" /></td>
                  <td className="px-3 py-1.5"><CellInput value={dados.unidade_venda} onChange={(x) => setDados((d) => ({ ...d, unidade_venda: x }))} placeholder="UN" /></td>
                  <td className="px-3 py-1.5"><CellInput type="number" value={dados.embalagem} onChange={(x) => setDados((d) => ({ ...d, embalagem: x }))} placeholder="unid/cx" /></td>
                  <td className="px-3 py-1.5"><CellInput type="number" value={dados.fator_conversao} onChange={(x) => setDados((d) => ({ ...d, fator_conversao: x }))} placeholder="cx →" /></td>
                  <td className="px-3 py-1.5"><CellInput value={dados.localizacao} onChange={(x) => setDados((d) => ({ ...d, localizacao: x }))} placeholder="Endereço" /></td>
                  <td className="px-3 py-1.5"><CellInput value={dados.ncm} onChange={(x) => setDados((d) => ({ ...d, ncm: x }))} placeholder="NCM" /></td>
                  <td className="px-3 py-1.5"><CellInput value={dados.unidade_tributavel} onChange={(x) => setDados((d) => ({ ...d, unidade_tributavel: x }))} placeholder="UN" /></td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
            <h4 className="mb-1 text-sm font-semibold text-gray-900">Atributos técnicos do ramo</h4>
            <p className="mb-3 text-xs text-gray-500">
              Campos estruturais para filtro, tributação e integração (MDM-004). Não substituem a descrição comercial.
            </p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              <Field label="Bitola / tamanho">
                <Input value={dados.bitola} onChange={(e) => setDados((d) => ({ ...d, bitola: e.target.value }))} placeholder="2,5mm²" />
              </Field>
              <Field label="Tensão">
                <Input value={dados.tensao} onChange={(e) => setDados((d) => ({ ...d, tensao: e.target.value }))} placeholder="220V" />
              </Field>
              <Field label="Potência">
                <Input value={dados.potencia} onChange={(e) => setDados((d) => ({ ...d, potencia: e.target.value }))} placeholder="10W" />
              </Field>
              <Field label="Comprimento">
                <Input value={dados.comprimento} onChange={(e) => setDados((d) => ({ ...d, comprimento: e.target.value }))} placeholder="100m" />
              </Field>
              <Field label="Diâmetro (Ø)">
                <Input value={dados.diametro} onChange={(e) => setDados((d) => ({ ...d, diametro: e.target.value }))} placeholder="1/2" />
              </Field>
              <Field label="Rosca">
                <Input value={dados.rosca} onChange={(e) => setDados((d) => ({ ...d, rosca: e.target.value }))} placeholder="M8 / 1/4" />
              </Field>
              <Field label="Material">
                <Input value={dados.material} onChange={(e) => setDados((d) => ({ ...d, material: e.target.value }))} placeholder="Cobre / Aço" />
              </Field>
              <Field label="Cor">
                <Input value={dados.cor} onChange={(e) => setDados((d) => ({ ...d, cor: e.target.value }))} placeholder="Azul" />
              </Field>
              <Field label="Norma">
                <Input value={dados.norma} onChange={(e) => setDados((d) => ({ ...d, norma: e.target.value }))} placeholder="NBR 6880" />
              </Field>
              <Field label="Validade (dias)">
                <Input type="number" min={0} value={dados.validade_dias} onChange={(e) => setDados((d) => ({ ...d, validade_dias: e.target.value }))} placeholder="—" />
              </Field>
              <Field label="Garantia (dias)">
                <Input type="number" min={0} value={dados.garantia_dias} onChange={(e) => setDados((d) => ({ ...d, garantia_dias: e.target.value }))} placeholder="—" />
              </Field>
            </div>
          </div>

          {atributos.length > 0 && (
            <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
              <h4 className="mb-1 text-sm font-semibold text-gray-900">Valores dos atributos da família</h4>
              <p className="mb-3 text-xs text-gray-500">Preencha o valor de cada atributo do produto. Obrigatórios são marcados com *.</p>
              <div className="flex flex-wrap gap-3">
                {atributos.map((a) => {
                  const val = valores[a.nome] || "";
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
                          onChange={(e) => setValores((v) => ({ ...v, [a.nome]: e.target.value }))}
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
                            onChange={(e) => setValores((v) => ({ ...v, [a.nome]: e.target.value }))}
                          />
                          {err && <p className="mt-0.5 text-[10px] text-red-500">{err}</p>}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {produto ? (
            <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
              <h4 className="mb-2 text-sm font-semibold text-gray-900">Estoque por depósito</h4>
              <p className="mb-3 text-xs text-gray-400">
                Saldo e situação por depósito (ok/ruptura/excesso) calculados a partir dos estoque mínimo e máximo.
              </p>
              <EstoqueDeposito produtoId={produto.id} />
            </div>
          ) : null}

          {produto ? (
            <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
              <h4 className="mb-2 text-sm font-semibold text-gray-900">Códigos por fornecedor</h4>
              <p className="mb-3 text-xs text-gray-400">
                Informe para este produto o fornecedor, o código usado por ele, a unidade de compra e o fator de conversão (ex.: embalagem com 10 unidades → fator 10).
              </p>
              <FornecedorGrid
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
            <p className="mt-4 text-sm text-gray-400">Salve o produto para cadastrar os códigos dos fornecedores.</p>
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
          {id ? <PerfilFiscalPanel produto={produto} /> : null}
        </div>
      )}

      {tab === "conversoes" && (
        <div>
          {id ? <Conversoes produtoId={id} /> : <p className="py-8 text-center text-sm text-gray-400">Salve o produto para configurar conversões.</p>}
        </div>
      )}

      {tab === "codigos" && (
        <div>
          {id ? <Identificadores produtoId={id} /> : <p className="py-8 text-center text-sm text-gray-400">Salve o produto para cadastrar códigos.</p>}
        </div>
      )}

      {tab === "relacoes" && (
        <div>
          {id ? <Relacoes produtoId={id} /> : <p className="py-8 text-center text-sm text-gray-400">Salve o produto para cadastrar relações.</p>}
        </div>
      )}

      {tab === "precos" && (
        <div>
          {id ? <RegrasPreco produtoId={id} /> : <p className="py-8 text-center text-sm text-gray-400">Salve o produto para configurar regras de preço.</p>}
        </div>
      )}

      <div className="mt-6 flex justify-end gap-2">
        <Button onClick={() => (location.hash = "#/produtos")}>Cancelar</Button>
        {temPermissao("produtos", "cadastrar") || temPermissao("produtos", "editar") ? (
          <Button variant="primary" onClick={() => void salvar()}>
            Salvar produto
          </Button>
        ) : null}
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
  fornecedores,
  unidadesCompra,
  rows,
  setRows,
  seq,
}: {
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

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
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
      <Button size="sm" className="mt-2" onClick={() => setRows([...rows, { uid: "fvr" + ++seq.current, fornecedor_id: "", codigo: "", unidade: "", fator: "" }])}>
        + Adicionar linha
      </Button>
    </div>
  );
}


// ---------------- helpers de estado (fora do componente) ----------------

function buildAtributosState(familias: Familia[], familiaId: number | null, produto: ProdutoCadastro | null) {
  let atributos: FamiliaAtributo[] = familias.find((x) => x.id === familiaId)?.atributos || [];
  if (produto && produto.atributos && produto.familia_id === familiaId) atributos = produto.atributos;
  let dados: DadosOperacionais = { ...DADOS_INICIAIS };
  let valores: Record<string, string> = {};
  if (produto) {
    dados = {
      sku: produto.sku ?? "",
      ean: produto.ean ?? "",
      preco: produto.preco?.toString() ?? "",
      prom: produto.preco_promocional?.toString() ?? "",
      peso: produto.peso?.toString() ?? "",
      dimensoes: produto.dimensoes ?? "",
      unidade_venda: produto.unidade_venda ?? "UN",
      embalagem: produto.embalagem?.toString() ?? "",
      fator_conversao: produto.fator_conversao?.toString() ?? "",
      localizacao: produto.localizacao ?? "",
      ncm: produto.ncm ?? "",
      unidade_tributavel: produto.unidade_tributavel ?? "",
      bitola: produto.bitola ?? "",
      tensao: produto.tensao ?? "",
      potencia: produto.potencia ?? "",
      comprimento: produto.comprimento ?? "",
      diametro: produto.diametro ?? "",
      rosca: produto.rosca ?? "",
      material: produto.material ?? "",
      cor: produto.cor ?? "",
      norma: produto.norma ?? "",
      validade_dias: produto.validade_dias?.toString() ?? "",
      garantia_dias: produto.garantia_dias?.toString() ?? "",
    };
    valores = produto.atributos_valores ?? {};
  }
  return { atributos, dados, valores };
}

function seedFornecedorRows(produto: ProdutoCadastro, seq: React.MutableRefObject<number>): FornecedorRow[] {
  const rows: FornecedorRow[] = [];
  for (const r of produto.fornecedor_variantes || []) {
    rows.push({
      uid: "fvr" + ++seq.current,
      fornecedor_id: String(r.fornecedor_id),
      codigo: r.codigo_fornecedor || "",
      unidade: r.unidade_compra || "",
      fator: r.fator_conversao ?? "",
    });
  }
  if (!rows.length) {
    rows.push({ uid: "fvr" + ++seq.current, fornecedor_id: "", codigo: "", unidade: "", fator: "" });
  }
  return rows;
}

// ===================================================================
// Imagens em lote (fornecedor)
// ===================================================================

const SITES_IMAGENS: { id: string; nome: string; url: (t: string) => string }[] = [
  { id: "casadoeletricista", nome: "Casa do Eletricista", url: (t) => `https://www.casadoeletricistasc.com.br/procura?procura=${t}` },
  { id: "casadosparafusos", nome: "Casa dos Parafusos", url: (t) => `https://www.casadosparafusos.com/busca?busca=${t}` },
  { id: "anhanguera", nome: "Anhanguera Ferramentas", url: (t) => `https://www.anhangueraferramentas.com.br/busca?q=${t}` },
];

interface IrmaoItem {
  id: number;
  nome: string;
  marca: string;
  sku: string;
  descricao: string;
  atributos: Record<string, string>;
}

function ModalImagensLote({ produtoId, onClose, onAplicado }: { produtoId: number; onClose: () => void; onAplicado?: () => void }) {
  const [irmaos, setIrmaos] = useState<IrmaoItem[]>([]);
  const [sel, setSel] = useState<Set<number>>(new Set());
  const [carregandoIrmaos, setCarregandoIrmaos] = useState(true);
  const [site, setSite] = useState(SITES_IMAGENS[0].id);
  const [termo, setTermo] = useState("");
  const [itens, setItens] = useState<{ url: string; name: string; thumb?: string }[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [prodUrl, setProdUrl] = useState("");
  const [preview, setPreview] = useState<{ url: string; md5?: string; largura?: number | null; altura?: number | null }[]>([]);
  const [imgsSel, setImgsSel] = useState<Set<string>>(new Set());
  const [favUrl, setFavUrl] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [aplicando, setAplicando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const ir = await api.listarIrmaos(produtoId);
        setIrmaos(ir);
        setSel(new Set(ir.map((x) => x.id)));
        const base = ir[0]?.nome || "";
        const cor = ir[0]?.atributos["Cor"] || "";
        const fabricante = ir[0]?.marca || "";
        setTermo([base.split(" ").slice(0, 2).join(" "), cor, fabricante].filter(Boolean).join(" ").replace(/\s+/g, "+"));
      } catch {
        setErro("Não foi possível carregar os irmãos.");
      } finally {
        setCarregandoIrmaos(false);
      }
    })();
  }, [produtoId]);

  const urlBusca = () => {
    const t = encodeURIComponent((termo || "").trim().replace(/\s+/g, "+"));
    return SITES_IMAGENS.find((s) => s.id === site)?.url(t) || "";
  };

  const buscar = async () => {
    setBuscando(true);
    setErro("");
    try {
      const res = await api.buscarImagensFornecedor(urlBusca());
      setItens(res.itens || []);
    } catch (e) {
      setErro("Falha na busca: " + (e as Error).message);
    } finally {
      setBuscando(false);
    }
  };

  const carregarPreview = async (url: string) => {
    setProdUrl(url);
    setPreviewLoading(true);
    setErro("");
    try {
      const res = await api.previewImagensFornecedor(url);
      setPreview(res.imagens || []);
      setImgsSel(new Set((res.imagens || []).map((i) => i.url)));
      setFavUrl((res.imagens || [])[0]?.url || "");
    } catch (e) {
      setErro("Falha no preview: " + (e as Error).message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const aplicar = async () => {
    const ids = [...sel];
    const urls = [...imgsSel];
    if (!ids.length) return toast("Nenhum produto do lote selecionado", "error");
    if (!urls.length) return toast("Nenhuma imagem selecionada", "error");
    setAplicando(true);
    setErro("");
    try {
      const res = await api.aplicarImagensLote(ids, urls, favUrl || undefined);
      const dedup = (res as { deduplicadas?: number }).deduplicadas || 0;
      if (res.aplicadas === 0 && res.erros.length === 0) {
        toast(dedup ? `Nenhuma imagem nova aplicada — ${dedup} já existiam nos produtos (dedup).` : "Nenhuma imagem foi aplicada.", "warn");
      } else {
        const extra = dedup ? ` (${dedup} já existiam)` : "";
        toast(`${res.aplicadas} imagem(ns) aplicada(s) a ${ids.length} produto(s)${extra}`, res.erros.length ? "warn" : "success");
      }
      if (res.erros.length) setErro(res.erros.slice(0, 3).join(" | "));
      onAplicado?.();
    } catch (e) {
      setErro("Erro ao aplicar: " + (e as Error).message);
    } finally {
      setAplicando(false);
    }
  };

  return (
    <Modal open onClose={onClose} title="Imagens em lote" footer={
      <>
        <Button onClick={onClose}>Fechar</Button>
        <Button variant="primary" onClick={() => void aplicar()} disabled={aplicando}>
          {aplicando ? "Aplicando…" : `Aplicar imagens aos ${sel.size} produto(s)`}
        </Button>
      </>
    }>
      {erro ? <p className="mb-2 rounded bg-red-50 p-2 text-xs text-red-700">{erro}</p> : null}

      <div className="mb-3">
        <h4 className="mb-1 text-sm font-semibold text-gray-900">Lote (irmãos)</h4>
        {carregandoIrmaos ? (
          <Loading />
        ) : irmaos.length === 0 ? (
          <p className="text-sm text-gray-400">Nenhum irmão encontrado (mesmo nome + marca + cor).</p>
        ) : (
          <div className="max-h-40 overflow-y-auto rounded border border-gray-200">
            {irmaos.map((x) => {
              const bitola = x.atributos["Bitola / Tamanho"] || x.atributos["Bitola"] || "";
              return (
                <label key={x.id} className="flex items-center gap-2 border-b border-gray-100 px-2 py-1 text-sm">
                  <input
                    type="checkbox"
                    checked={sel.has(x.id)}
                    onChange={(e) => {
                      const n = new Set(sel);
                      if (e.target.checked) n.add(x.id);
                      else n.delete(x.id);
                      setSel(n);
                    }}
                  />
                  <span className="flex-1 truncate">{x.nome}</span>
                  <span className="text-xs text-gray-500">{bitola || x.sku}</span>
                </label>
              );
            })}
          </div>
        )}
      </div>

      <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Fornecedor</label>
          <Select value={site} onChange={(e) => setSite(e.target.value)} className="w-full">
            {SITES_IMAGENS.map((s) => (
              <option key={s.id} value={s.id}>{s.nome}</option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Termo da busca</label>
          <Input value={termo} onChange={(e) => setTermo(e.target.value)} />
        </div>
      </div>
      <div className="mb-3 flex gap-2">
        <Input className="flex-1" readOnly value={urlBusca()} />
        <Button variant="primary" onClick={() => void buscar()} disabled={buscando || !termo.trim()}>
          {buscando ? "Buscando…" : "Buscar"}
        </Button>
      </div>

      {itens.length > 0 && (
        <div className="mb-3 max-h-44 overflow-y-auto rounded border border-gray-200">
          {itens.map((it) => (
            <button
              key={it.url}
              onClick={() => void carregarPreview(it.url)}
              className={`flex w-full items-center gap-2 border-b border-gray-100 px-2 py-1.5 text-left text-sm hover:bg-gray-50 ${prodUrl === it.url ? "bg-orange-50" : ""}`}
            >
              {it.thumb ? <img src={it.thumb} alt="" className="h-8 w-8 rounded object-contain" /> : <span className="h-8 w-8" />}
              <span className="flex-1 truncate">{it.name}</span>
            </button>
          ))}
        </div>
      )}

      {previewLoading ? (
        <Loading />
      ) : preview.length > 0 ? (
        <div>
          <h4 className="mb-1 text-sm font-semibold text-gray-900">Imagens do produto (marque as que quer)</h4>
          <div className="grid max-h-56 grid-cols-4 gap-2 overflow-y-auto">
            {preview.map((p) => (
              <label key={p.md5 || p.url} className="relative cursor-pointer rounded border p-1">
                <input
                  type="checkbox"
                  className="absolute left-1 top-1"
                  checked={imgsSel.has(p.url)}
                  onChange={(e) => {
                    const n = new Set(imgsSel);
                    if (e.target.checked) n.add(p.url);
                    else n.delete(p.url);
                    setImgsSel(n);
                  }}
                />
                <button
                  type="button"
                  className={`absolute right-1 top-1 rounded px-1 text-sm shadow ${favUrl === p.url ? "bg-amber-400 text-white" : "bg-white text-gray-400 hover:text-amber-500"}`}
                  title="Marcar como foto favorita (capa)"
                  onClick={(e) => {
                    e.preventDefault();
                    setFavUrl(favUrl === p.url ? "" : p.url);
                  }}
                >
                  ★
                </button>
                <img src={p.url} loading="lazy" alt="" className="h-20 w-full object-contain" />
              </label>
            ))}
          </div>
          <p className="mt-1 text-xs text-gray-400">Marque as fotos que quer usar e clique na ★ da foto favorita (será a capa).</p>
        </div>
      ) : null}
    </Modal>
  );
}
