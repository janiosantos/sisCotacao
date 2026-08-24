// pages/compras.tsx — fluxo de compra em tela única (React + Tailwind).

import { useEffect, useRef, useState } from "react";
import {
  api,
  type CotacaoComprasPayload,
  type CotacaoFornecedor,
  type Fornecedor,
  type Invite,
  type MatrizComparacao,
  type MatrizItem,
  type Pedido,
} from "../api/client";
import { fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Input, Loading, Select } from "../ui/ui";

const KEY_DRAFT = "compras_draft";
const KEY_COT = "compras_cotacao";
const KEY_PESOS = "compras_pesos_recomendado";

interface Pesos {
  preco: number;
  prazo: number;
  pagamento: number;
}

const PESOS_PADRAO: Pesos = { preco: 50, prazo: 30, pagamento: 20 };

function carregarPesos(): Pesos {
  try {
    const raw = sessionStorage.getItem(KEY_PESOS);
    if (!raw) return { ...PESOS_PADRAO };
    const p = JSON.parse(raw) as Partial<Pesos>;
    return {
      preco: p.preco ?? PESOS_PADRAO.preco,
      prazo: p.prazo ?? PESOS_PADRAO.prazo,
      pagamento: p.pagamento ?? PESOS_PADRAO.pagamento,
    };
  } catch {
    return { ...PESOS_PADRAO };
  }
}

function salvarPesos(p: Pesos): void {
  sessionStorage.setItem(KEY_PESOS, JSON.stringify(p));
}

function calcularRecomendados(
  itens: MatrizItem[],
  fornecedores: CotacaoFornecedor[],
  pesos: Pesos
): Map<number, number> {
  const diasPagto = new Map<number, number | null>();
  fornecedores.forEach((f) => diasPagto.set(f.fornecedor_id, f.condicao_pagamento_dias ?? null));

  const somaPesos = Math.max(1, pesos.preco + pesos.prazo + pesos.pagamento);
  const wPreco = pesos.preco / somaPesos;
  const wPrazo = pesos.prazo / somaPesos;
  const wPagto = pesos.pagamento / somaPesos;

  const resultado = new Map<number, number>();

  for (const item of itens) {
    const candidatos = Object.entries(item.precos).filter(([, pr]) => pr.disponivel && pr.preco_liquido > 0);
    if (candidatos.length === 0) continue;

    const maxPreco = Math.max(...candidatos.map(([, pr]) => pr.preco_liquido));
    const prazosValidos = candidatos.map(([, pr]) => pr.prazo).filter((p): p is number => p != null);
    const maxPrazo = prazosValidos.length ? Math.max(...prazosValidos) : 0;
    const diasValidos = candidatos.map(([fid]) => diasPagto.get(Number(fid))).filter((d): d is number => d != null);
    const maxDias = diasValidos.length ? Math.max(...diasValidos) : 0;

    let melhorFid: number | null = null;
    let melhorScore = -Infinity;

    for (const [fid, pr] of candidatos) {
      const normPreco = maxPreco > 0 ? pr.preco_liquido / maxPreco : 0;
      const normPrazo = maxPrazo > 0 ? (pr.prazo ?? maxPrazo) / maxPrazo : 0;
      const dias = diasPagto.get(Number(fid)) ?? 0;
      const normDias = maxDias > 0 ? dias / maxDias : 0;

      const score = wPreco * (1 - normPreco) + wPrazo * (1 - normPrazo) + wPagto * normDias;
      if (score > melhorScore) {
        melhorScore = score;
        melhorFid = Number(fid);
      }
    }
    if (melhorFid != null) resultado.set(item.cotacao_item_id, melhorFid);
  }

  return resultado;
}

interface ItemDraft {
  produto_id: number;
  quantidade: number;
  name?: string;
  category?: string;
}

interface FornecedorDraft {
  id: number | null;
  nome?: string;
  whatsapp?: string;
  email?: string;
}

interface Draft {
  apelido: string;
  comprador: string;
  data_limite: string;
  agrupar: boolean;
  itens: ItemDraft[];
  fornecedores: FornecedorDraft[];
}

interface CardBusca {
  group: boolean;
  id: number;
  name: string;
  sku: string;
  brand?: string;
  category?: string;
  price: number;
  price_min?: number;
  imagem_url?: string | null;
  variants?: { id: number }[];
}

function novoDraft(): Draft {
  return { apelido: "", comprador: "", data_limite: "", agrupar: false, itens: [], fornecedores: [] };
}

const ETAPAS = [
  { n: 1, nome: "Lista" },
  { n: 2, nome: "Cotando" },
  { n: 3, nome: "Comparando" },
  { n: 4, nome: "Pedido Gerado" },
];

export default function Compras() {
  const [etapa, setEtapa] = useState(1);
  const [cotacaoId, setCotacaoId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft>(novoDraft);
  const [logica, setLogica] = useState("fracionado");
  const [invites, setInvites] = useState<Invite[] | null>(null);
  const [iniciado, setIniciado] = useState(false);

  const salvar = (d: Draft, cot: number | null) => {
    sessionStorage.setItem(KEY_DRAFT, JSON.stringify(d || {}));
    if (cot) sessionStorage.setItem(KEY_COT, String(cot));
  };

  useEffect(() => {
    let d: Draft = novoDraft();
    try {
      d = (JSON.parse(sessionStorage.getItem(KEY_DRAFT) || "null") as Draft | null) || novoDraft();
    } catch {
      d = novoDraft();
    }
    const stored = sessionStorage.getItem(KEY_COT);
    if (stored) {
      const cot = Number(stored);
      setCotacaoId(cot);
      setDraft(novoDraft());
      void api
        .compararCotacao(cot)
        .then((m) => {
          const status = m.cotacao.status;
          setEtapa(status === "finalizada" ? 4 : 3);
        })
        .catch(() => {
          sessionStorage.removeItem(KEY_COT);
          setCotacaoId(null);
          setEtapa(1);
        })
        .finally(() => setIniciado(true));
    } else {
      setDraft(d);
      setEtapa(1);
      setIniciado(true);
    }
  }, []);

  const novaCompra = () => {
    sessionStorage.removeItem(KEY_COT);
    setCotacaoId(null);
    setDraft(novoDraft());
    setInvites(null);
    setLogica("fracionado");
    setEtapa(1);
    salvar(novoDraft(), null);
  };

  if (!iniciado) return <Loading />;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Comprar</h1>
          <p className="mt-1 text-sm text-gray-500">Monte a lista, cote com os fornecedores e gere o pedido em uma tela só.</p>
        </div>
        <Button variant="ghost" onClick={novaCompra}>
          ＋ Nova compra
        </Button>
      </div>

      <div className="mb-6 flex items-center">
        {ETAPAS.map((e, i) => (
          <div key={e.n} className="flex items-center">
            {i > 0 && <div className={`h-0.5 w-10 ${e.n <= etapa ? "bg-brand-600" : "bg-gray-200"}`} />}
            <div className="flex items-center gap-2">
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-full text-sm font-medium ${
                  e.n === etapa ? "bg-brand-600 text-white" : e.n < etapa ? "bg-brand-100 text-brand-700" : "bg-gray-100 text-gray-400"
                }`}
              >
                {e.n}
              </span>
              <span className={`text-sm ${e.n === etapa ? "font-medium text-gray-900" : "text-gray-400"}`}>{e.nome}</span>
            </div>
          </div>
        ))}
      </div>

      {invites !== null ? (
        <LinksPanel
          cotacaoId={cotacaoId}
          invites={invites}
          onVoltar={() => {
            setInvites(null);
            setEtapa(2);
          }}
          onComparar={() => {
            setInvites(null);
            setEtapa(3);
          }}
        />
      ) : etapa === 1 ? (
        <EtapaLista draft={draft} setDraft={setDraft} salvar={salvar} cotacaoId={cotacaoId} onProximo={() => setEtapa(2)} />
      ) : etapa === 2 ? (
        <EtapaCotando
          draft={draft}
          setDraft={setDraft}
          salvar={salvar}
          cotacaoId={cotacaoId}
          onDisparado={(id, inv) => {
            setCotacaoId(id);
            setInvites(inv);
          }}
        />
      ) : etapa === 3 ? (
        <EtapaComparando
          cotacaoId={cotacaoId}
          logica={logica}
          setLogica={setLogica}
          onGerado={() => setEtapa(4)}
        />
      ) : (
        <EtapaPedidos cotacaoId={cotacaoId} />
      )}
    </div>
  );
}

// ============================================================ ETAPA 1

function EtapaLista({
  draft,
  setDraft,
  salvar,
  cotacaoId,
  onProximo,
}: {
  draft: Draft;
  setDraft: (d: Draft) => void;
  salvar: (d: Draft, cot: number | null) => void;
  cotacaoId: number | null;
  onProximo: () => void;
}) {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [categorias, setCategorias] = useState<string[]>([]);
  const [resultados, setResultados] = useState<CardBusca[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    void api
      .listarCategorias()
      .then((cats) => setCategorias(Object.keys(cats).sort()))
      .catch(() => {});
  }, []);

  useEffect(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      void api
        .listarProdutos({ q: q.trim(), categoria: cat, limit: 12, agrupado: 1 })
        .then((r) => setResultados((r.items || []) as unknown as CardBusca[]))
        .catch(() => setResultados([]));
    }, 300);
    return () => clearTimeout(timer.current);
  }, [q, cat]);

  const adicionar = (p: CardBusca) => {
    const vid = p.group && p.variants && p.variants[0] ? p.variants[0].id : p.id;
    const exist = draft.itens.find((i) => i.produto_id === vid);
    const next = { ...draft, itens: [...draft.itens] };
    if (exist) {
      exist.quantidade += 1;
    } else {
      const categoria = p.category || "";
      if (draft.agrupar && draft.itens.length && categoria && (draft.itens[0].category || "") !== categoria) {
        toast("Grupo diferente: ative a opção de não misturar ou remova o item.", "error");
        return;
      }
      next.itens.push({ produto_id: vid, quantidade: 1, name: p.name, category: categoria });
    }
    setDraft(next);
    salvar(next, cotacaoId);
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-gray-900">Buscar produtos</h3>
        <div className="mb-3 flex gap-2">
          <Input placeholder="Nome, código, EAN ou grupo…" value={q} onChange={(e) => setQ(e.target.value)} />
          <Select value={cat} onChange={(e) => setCat(e.target.value)} className="w-44">
            <option value="">Todos os grupos</option>
            {categorias.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
        </div>
        <label className="mb-3 flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={draft.agrupar}
            onChange={(e) => {
              const next = { ...draft, agrupar: e.target.checked };
              setDraft(next);
              salvar(next, cotacaoId);
            }}
          />
          Não misturar grupos de produtos
        </label>
        <div className="space-y-2">
          {resultados.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-400">Digite para buscar</div>
          ) : (
            resultados.map((p) => {
              return (
                <div key={p.id} className="flex items-center gap-3 rounded-md border border-gray-100 p-2">
                  {p.imagem_url ? (
                    <img src={p.imagem_url} className="h-10 w-10 object-contain" alt="" onError={(e) => ((e.target as HTMLImageElement).style.visibility = "hidden")} />
                  ) : null}
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{p.name}</div>
                    <div className="truncate text-xs text-gray-400">
                      {p.sku}
                      {p.brand ? " · " + p.brand : ""}
                      {p.category ? " · " + p.category : ""}
                    </div>
                    <div className="text-sm font-semibold">{fmtMoney(p.group ? p.price_min : p.price)}</div>
                  </div>
                  <Button size="sm" variant="primary" onClick={() => adicionar(p)}>
                    Adicionar
                  </Button>
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-gray-900">
          Minha lista <Badge>{draft.itens.length}</Badge>
        </h3>
        <div className="mb-3">
          <Input placeholder="Apelido amigável (ex.: Parafusos Agosto)" value={draft.apelido} onChange={(e) => { const next = { ...draft, apelido: e.target.value }; setDraft(next); salvar(next, cotacaoId); }} />
        </div>
        <div className="mb-3 flex items-center gap-2">
          <Input type="date" value={draft.data_limite} onChange={(e) => { const next = { ...draft, data_limite: e.target.value }; setDraft(next); salvar(next, cotacaoId); }} className="w-48" />
          <span className="text-sm text-gray-500">Retorno até</span>
        </div>
        <div className="space-y-2">
          {draft.itens.length === 0 ? (
            <div className="py-8 text-center text-sm text-gray-400">
              Nenhum item na lista.
              <br />
              Use a busca ao lado e clique em "Adicionar".
            </div>
          ) : (
            draft.itens.map((it, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="flex-1 truncate text-sm">{it.name || "#" + it.produto_id}</span>
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={it.quantidade}
                  onChange={(e) => {
                    const next = { ...draft, itens: [...draft.itens] };
                    next.itens[idx] = { ...next.itens[idx], quantidade: Math.max(1, Number(e.target.value) || 1) };
                    setDraft(next);
                    salvar(next, cotacaoId);
                  }}
                  className="w-20 rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none"
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    const next = { ...draft, itens: draft.itens.filter((_, i) => i !== idx) };
                    setDraft(next);
                    salvar(next, cotacaoId);
                  }}
                >
                  ✕
                </Button>
              </div>
            ))
          )}
        </div>
        <div className="mt-4">
          <Button
            variant="primary"
            onClick={() => {
              if (!draft.itens.length) {
                toast("Adicione pelo menos 1 produto.", "error");
                return;
              }
              onProximo();
            }}
          >
            Continuar ➔ Cotação
          </Button>
        </div>
      </div>
    </div>
  );
}

// ============================================================ ETAPA 2

function EtapaCotando({
  draft,
  setDraft,
  salvar,
  cotacaoId,
  onDisparado,
}: {
  draft: Draft;
  setDraft: (d: Draft) => void;
  salvar: (d: Draft, cot: number | null) => void;
  cotacaoId: number | null;
  onDisparado: (id: number, invites: Invite[]) => void;
}) {
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [fxNome, setFxNome] = useState("");
  const [fxWhats, setFxWhats] = useState("");
  const [fxEmail, setFxEmail] = useState("");
  const [disparando, setDisparando] = useState(false);

  useEffect(() => {
    void api
      .listarFornecedores(true)
      .then(setFornecedores)
      .catch(() => {});
  }, []);

  const adicionarExpress = () => {
    if (!fxNome.trim()) {
      toast("Informe o nome do fornecedor.", "error");
      return;
    }
    const next = {
      ...draft,
      fornecedores: [...draft.fornecedores, { id: null, nome: fxNome.trim(), whatsapp: fxWhats.trim(), email: fxEmail.trim() }],
    };
    setDraft(next);
    salvar(next, cotacaoId);
    setFxNome("");
    setFxWhats("");
    setFxEmail("");
    toast("Fornecedor rápido adicionado à cotação.");
  };

  const disparar = async () => {
    if (!draft.fornecedores.length) {
      toast("Convide pelo menos 1 fornecedor.", "error");
      return;
    }
    setDisparando(true);
    const payload: CotacaoComprasPayload = {
      apelido: draft.apelido,
      comprador: draft.comprador || "Loja",
      data_limite: draft.data_limite,
      itens: draft.itens.map((i) => ({ produto_id: i.produto_id, quantidade: i.quantidade })),
      fornecedores: draft.fornecedores.map((f) =>
        f.id ? { fornecedor_id: f.id } : { nome: f.nome ?? "", whatsapp: f.whatsapp ?? "", email: f.email ?? "" }
      ),
    };
    try {
      const r = await api.criarCotacaoCompras(payload);
      sessionStorage.setItem(KEY_COT, String(r.id));
      const next = { ...draft, fornecedores: [] };
      setDraft(next);
      salvar(next, r.id);
      onDisparado(r.id, r.invites || []);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setDisparando(false);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold text-gray-900">Sua lista está pronta</h3>
        <p className="mb-3 text-sm text-gray-500">
          {draft.itens.length} itens {draft.apelido ? `· “${draft.apelido}”` : ""}
        </p>
        <div className="space-y-1">
          {draft.itens.map((it, i) => (
            <div key={i} className="flex justify-between text-sm">
              <span>{it.name || "#" + it.produto_id}</span>
              <b>{it.quantidade}</b>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-gray-900">Convide fornecedores</h3>
        <div className="space-y-1">
          {fornecedores.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-400">Nenhum fornecedor cadastrado.</p>
          ) : (
            fornecedores.map((f) => {
              const sel = draft.fornecedores.some((x) => x.id === f.id);
              return (
                <label key={f.id} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={sel}
                    onChange={(e) => {
                      let next: FornecedorDraft[];
                      if (e.target.checked) next = [...draft.fornecedores, { id: f.id }];
                      else next = draft.fornecedores.filter((x) => x.id !== f.id);
                      const d = { ...draft, fornecedores: next };
                      setDraft(d);
                      salvar(d, cotacaoId);
                    }}
                  />
                  <span className="flex-1">{f.nome}</span>
                  <small className="text-xs text-gray-400">{f.whatsapp || (f.email ? "e-mail" : "sem contato")}</small>
                </label>
              );
            })
          )}
        </div>

        <h4 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-gray-500">Cadastro rápido</h4>
        <div className="space-y-2">
          <Input placeholder="Nome do fornecedor" value={fxNome} onChange={(e) => setFxNome(e.target.value)} />
          <Input placeholder="WhatsApp (só números)" value={fxWhats} onChange={(e) => setFxWhats(e.target.value)} />
          <Input placeholder="E-mail (opcional)" value={fxEmail} onChange={(e) => setFxEmail(e.target.value)} />
          <Button onClick={adicionarExpress}>Adicionar</Button>
        </div>

        <div className="mt-4">
          <Button variant="primary" className="w-full" onClick={() => void disparar()} disabled={disparando}>
            {disparando ? "Enviando…" : "Disparar Cotação ➔"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function LinksPanel({ cotacaoId, invites, onVoltar, onComparar }: { cotacaoId: number | null; invites: Invite[]; onVoltar: () => void; onComparar: () => void }) {
  const [lembrando, setLembrando] = useState<number | null>(null);

  const lembrar = async (inv: Invite) => {
    if (!cotacaoId) return;
    setLembrando(inv.fornecedor_id);
    try {
      const r = await api.lembrarFornecedor(cotacaoId, inv.fornecedor_id);
      if (r.whatsapp_url) {
        window.open(r.whatsapp_url, "_blank", "noopener,noreferrer");
        toast("Lembrete aberto no WhatsApp");
      } else if (r.mailto_url) {
        window.location.href = r.mailto_url;
        toast("Lembrete aberto no e-mail");
      } else {
        void navigator.clipboard.writeText(r.link).then(() => toast("Sem contato — link copiado!"));
      }
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setLembrando(null);
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-900">Cotações disparadas! Envie para cada fornecedor</h3>
      <p className="mb-3 text-sm text-gray-500">Toque no WhatsApp (verde) para abrir a conversa pronta, ou copie o link. O botão "Lembrar" reenvia a mensagem para quem ainda não respondeu.</p>
      <div className="space-y-2">
        {invites.map((inv) => (
          <div key={inv.fornecedor_id} className="flex flex-wrap items-center gap-3 rounded-md border border-gray-100 p-2">
            <div className="flex-1">
              <b className="text-sm">{inv.nome}</b>
              <span className="ml-2 text-xs text-gray-400">{inv.status === "respondido" ? "✓ respondeu" : "pendente"}</span>
              {inv.data_limite_retorno ? <span className="ml-2 text-xs text-gray-400">retorno até {inv.data_limite_retorno}</span> : null}
            </div>
            <div className="flex gap-2">
              {inv.whatsapp_url ? (
                <a className="rounded-md bg-emerald-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-700" target="_blank" rel="noopener noreferrer" href={inv.whatsapp_url}>
                  WhatsApp
                </a>
              ) : null}
              {inv.mailto_url ? (
                <a className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50" href={inv.mailto_url}>
                  E-mail
                </a>
              ) : null}
              <Button size="sm" onClick={() => void navigator.clipboard.writeText(inv.link).then(() => toast("Link copiado!"))}>
                Copiar link
              </Button>
              {inv.status !== "respondido" ? (
                <Button size="sm" variant="secondary" onClick={() => void lembrar(inv)} disabled={lembrando === inv.fornecedor_id}>
                  {lembrando === inv.fornecedor_id ? "…" : "🔔 Lembrar"}
                </Button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex justify-between">
        <Button onClick={onVoltar}>← Editar lista</Button>
        <Button variant="primary" onClick={onComparar}>
          Ir para Comparação ➔
        </Button>
      </div>
    </div>
  );
}

// ============================================================ ETAPA 3

function EtapaComparando({
  cotacaoId,
  logica,
  setLogica,
  onGerado,
}: {
  cotacaoId: number | null;
  logica: string;
  setLogica: (l: string) => void;
  onGerado: () => void;
}) {
  const [m, setM] = useState<MatrizComparacao | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [pesos, setPesos] = useState<Pesos>(() => carregarPesos());
  const [gerando, setGerando] = useState(false);

  const carregar = async () => {
    if (!cotacaoId) return;
    setCarregando(true);
    setErro("");
    try {
      setM(await api.compararCotacao(cotacaoId));
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cotacaoId]);

  if (carregando) return <Loading />;
  if (erro) return <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">{erro}</div>;

  if (m) {
    const status = m.cotacao.status;
    if (status !== "analise" && status !== "finalizada" && !m.fornecedores.some((f) => f.status === "respondido")) {
      return (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
          <div className="mb-3 text-sm font-semibold text-gray-900">Cotação disparada — aguardando respostas</div>
          <p className="mb-4 text-sm text-gray-500">Quando os fornecedores responderem (ou você apertar o botão), a matriz aparece aqui.</p>
          <Button variant="primary" onClick={() => void carregar()}>
            Atualizar respostas
          </Button>
        </div>
      );
    }

    const fornecedores = m.fornecedores;
    const central = m.centralizado;
    const vencedorCentral = central ? central.fornecedor_id : null;
    const recomendados = logica === "recomendado" ? calcularRecomendados(m.itens, fornecedores, pesos) : new Map<number, number>();

    const importarIA = () => {
      const opts = {
        cotacaoId: cotacaoId!,
        fornecedores,
        titulo: m.cotacao.titulo || "Cotação " + m.cotacao.numero,
        onAplicado: () => void carregar(),
      };
      void import("./importia")
        .then((mod) => mod.abrir(opts))
        .catch(() => toast("Importador IA indisponível.", "error"));
    };

    const gerarPedidos = async () => {
      setGerando(true);
      try {
        const logicaEnvio = logica === "recomendado" ? "fracionado" : logica;
        await api.gerarPedidos(cotacaoId!, logicaEnvio);
        onGerado();
      } catch (e) {
        toast((e as Error).message, "error");
      } finally {
        setGerando(false);
      }
    };

    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-gray-900">Comparar propostas {m.cotacao.titulo ? `— “${m.cotacao.titulo}”` : ""}</h3>
          <div className="flex gap-2">
            {["fracionado", "centralizado", "recomendado"].map((l) => (
              <Button key={l} variant={logica === l ? "primary" : "secondary"} size="sm" onClick={() => setLogica(l)}>
                {l === "fracionado" ? "💰 Melhor preço por item" : l === "centralizado" ? "📦 Melhor preço por lote" : "⭐ Recomendado"}
              </Button>
            ))}
          </div>
        </div>

        {central ? (
          <p className="mb-2 text-sm text-gray-600">
            Opção de lote: <b>{central.nome}</b> — total {fmtMoney(central.total)}
          </p>
        ) : (
          <p className="mb-2 text-sm text-gray-400">Nenhum fornecedor precificou todos os itens para a opção de lote.</p>
        )}

        {logica === "recomendado" && (
          <div className="mb-3 flex flex-wrap items-center gap-4 rounded-md bg-gray-50 p-3 text-sm">
            <span className="font-medium text-gray-600">Priorizar:</span>
            {(["preco", "prazo", "pagamento"] as const).map((k) => (
              <label key={k} className="flex items-center gap-2">
                <span>{k === "preco" ? "💰 Preço" : k === "prazo" ? "🚚 Prazo" : "💳 Pagamento"}</span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={pesos[k]}
                  onChange={(e) => {
                    const next = { ...pesos, [k]: Number(e.target.value) };
                    setPesos(next);
                    salvarPesos(next);
                  }}
                />
                <b>{pesos[k]}%</b>
              </label>
            ))}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Produto</th>
                {fornecedores.map((f) => (
                  <th key={f.fornecedor_id} className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    {f.nome}
                    {f.status === "respondido" ? null : <span className="ml-1 text-gray-400">—</span>}
                    {f.condicao_pagamento ? <div className="mt-0.5 text-[11px] font-normal normal-case text-gray-400">{f.condicao_pagamento}</div> : null}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {m.itens.map((it) => (
                <tr key={it.cotacao_item_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5">
                    <b>{it.name}</b>
                    <small className="block text-xs text-gray-400">qtd {it.quantidade}</small>
                  </td>
                  {fornecedores.map((f) => {
                    const pr = it.precos[String(f.fornecedor_id)];
                    if (!pr)
                      return (
                        <td key={f.fornecedor_id} className="px-4 py-2.5 text-gray-400">
                          —
                        </td>
                      );
                    const recomendadoId = recomendados.get(it.cotacao_item_id) ?? null;
                    const ehVencedorPrincipal =
                      logica === "centralizado"
                        ? vencedorCentral === f.fornecedor_id && pr.disponivel && pr.preco_liquido > 0
                        : logica === "recomendado"
                          ? recomendadoId === f.fornecedor_id
                          : it.melhor_id === f.fornecedor_id;
                    const ehMelhorPreco = it.melhor_id === f.fornecedor_id;
                    const ehMenorPrazo = it.melhor_prazo_id === f.fornecedor_id && it.melhor_prazo_id !== it.melhor_id;
                    const motivoLabel =
                      pr.motivo_indisponibilidade === "em_falta_estoque"
                        ? "Em falta de estoque"
                        : pr.motivo_indisponibilidade === "nao_trabalha_linha"
                          ? "Não trabalha com a linha"
                          : pr.motivo_indisponibilidade === "descontinuado"
                            ? "Descontinuado"
                            : pr.motivo_indisponibilidade === "fora_regiao"
                              ? "Fora da região"
                              : pr.motivo_indisponibilidade === "outro"
                                ? "Indisponível"
                                : null;
                    const fator = pr.fator_conversao && pr.fator_conversao > 1 ? pr.fator_conversao : 1;
                    return (
                      <td key={f.fornecedor_id} className={`px-4 py-2.5 ${ehVencedorPrincipal ? "bg-brand-50" : ""}`}>
                        {!pr.disponivel ? (
                          <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                            {motivoLabel || "Indisponível"}
                          </span>
                        ) : (
                          <>
                            <b> {fmtMoney(pr.preco_liquido)}</b>
                            {logica === "recomendado" && ehVencedorPrincipal ? <span title="Recomendado">⭐</span> : null}
                            {logica !== "centralizado" && ehMelhorPreco ? <span title="Melhor preço">💰</span> : null}
                            {ehMenorPrazo ? <span title="Menor prazo de entrega">🚚</span> : null}
                          </>
                        )}
                        {pr.unidade_compra ? (
                          <small className="block text-xs text-gray-400">
                            {pr.unidade_compra}
                            {fator > 1 ? ` · ${fator}/emb · ${pr.qtd_embalagens ?? 0} emb.` : ""}
                            {pr.preco_embalagem != null && fator > 1 ? ` · ${fmtMoney(pr.preco_embalagem)}/emb` : ""}
                          </small>
                        ) : null}
                        {pr.marca_ofertada ? <small className="block text-xs text-gray-500">marca: {pr.marca_ofertada}</small> : null}
                        <small className="block text-xs text-gray-400">
                          {pr.desconto ? "desconto " + pr.desconto + "%" : ""}
                          {pr.prazo ? " · " + pr.prazo + "d" : ""}
                        </small>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-2 text-xs text-gray-400">
          💰 melhor preço · 🚚 menor prazo de entrega {logica === "recomendado" ? "· ⭐ recomendado (preço + prazo + pagamento)" : ""} · unidade/embalagem e marca vêm da proposta do representante
        </p>

        <div className="mt-4 flex flex-wrap justify-between gap-2">
          <div className="flex gap-2">
            <Button onClick={() => void carregar()}>↻ Atualizar respostas</Button>
            <Button onClick={importarIA}>⚡ Importar resposta IA</Button>
          </div>
          <Button variant="primary" onClick={() => void gerarPedidos()} disabled={gerando}>
            {gerando ? "Gerando…" : "Gerar Pedidos ➔"}
          </Button>
        </div>
      </div>
    );
  }

  return null;
}

// ============================================================ ETAPA 4

function EtapaPedidos({ cotacaoId }: { cotacaoId: number | null }) {
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    void api
      .listarPedidos()
      .then((p) => setPedidos(p.filter((x) => x.cotacao_id === cotacaoId)))
      .catch(() => setPedidos([]))
      .finally(() => setCarregando(false));
  }, [cotacaoId]);

  if (carregando) return <Loading />;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-900">Pedidos gerados — envie para os fornecedores</h3>
      <p className="mb-3 text-sm text-gray-500">Cada pedido consolida os itens vencedores por fornecedor.</p>
      {pedidos.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">Nenhum pedido ainda.</p>
      ) : (
        <div className="space-y-2">
          {pedidos.map((p) => (
            <div key={p.id} className="rounded-md border border-gray-100 p-3">
              <div className="flex items-center justify-between">
                <div>
                  <b className="text-sm">Pedido {p.numero}</b>
                  <span className="ml-2 text-xs text-gray-400">{p.fornecedor}</span>
                </div>
                <div className="text-sm font-semibold">{fmtMoney(p.total ?? 0)}</div>
              </div>
              {p.itens && p.itens.length > 0 ? (
                <div className="mt-2 space-y-0.5">
                  {p.itens.map((it) => (
                    <div key={it.id} className="flex items-center justify-between text-xs text-gray-500">
                      <span>
                        {it.name || "Item"} {it.unidade_compra ? `(${it.unidade_compra}${it.fator_conversao && it.fator_conversao > 1 ? `·${it.fator_conversao}` : ""})` : ""}
                      </span>
                      <span>
                        qtd {it.quantidade}
                        {it.unidade_compra ? ` ${it.unidade_compra}` : ""}
                        {it.fator_conversao && it.fator_conversao > 1 ? ` · ${Math.ceil(it.quantidade / it.fator_conversao)} emb.` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="mt-2 flex gap-2">
                <a className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50" target="_blank" rel="noreferrer" href={`/compras/pedidos/${p.id}/imprimir`}>
                  PDF
                </a>
                {p.whatsapp ? (
                  <a
                    className="rounded-md bg-emerald-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-700"
                    target="_blank"
                    rel="noopener noreferrer"
                    href={`https://wa.me/${p.whatsapp}?text=${encodeURIComponent(
                      "Olá " + p.fornecedor + ", segue nosso pedido de compras número " + p.numero + " referente à cotação aprovada. Aguardamos o faturamento e entrega!"
                    )}`}
                  >
                    WhatsApp
                  </a>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
