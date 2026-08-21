// pages/pre-venda.tsx — Pré-venda de orçamentos (React + Tailwind).

import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type Cliente,
  type ClienteSituacao,
  type CondicaoPagamento,
  type OrcamentoDetalhe,
  type OrcamentoItemPayload,
  type OrcamentoLista,
  type ProdutoResumo,
} from "../api/client";
import { fmtDate, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { usuarioCorrente } from "./login";
import { Button, Field, Input, Modal } from "../ui/ui";
import { SearchModal } from "../ui/search-modal";

interface LinhaPdv {
  produto_id: number | null;
  sku: string;
  nome: string;
  marca: string;
  especificacao: string;
  unidade: string;
  ncm: string;
  imagem_url: string;
  quantidade: number;
  preco_unitario: number;
  desconto_percentual: number;
  desconto_modo: "pct" | "valor";
  subtotal: number;
}

const VALIDADE_PADRAO = 7;
const CLIENTE_PADRAO = { id: 1, nome: "CONSUMIDOR" };

function parseNum(v: string): number {
  const n = parseFloat(String(v || "").replace(",", "."));
  return isNaN(n) ? 0 : n;
}

function parseBusca(v: string): { qtd: number; termo: string } {
  const m = v.trim().match(/^(\d+(?:[.,]\d+)?)\s*\*+\s*([\s\S]*)$/);
  if (!m) return { qtd: 1, termo: v.trim() };
  const n = parseFloat(m[1].replace(",", "."));
  return { qtd: n > 0 ? n : 1, termo: m[2].trim() };
}

function calculosPdv(linhas: LinhaPdv[], vDescModo: "pct" | "valor", vDesconto: string) {
  const base = linhas.reduce((s, l) => s + l.preco_unitario * l.quantidade, 0);
  const subtotal = linhas.reduce((s, l) => s + l.subtotal, 0);
  const descontoGeral = vDescModo === "pct" ? subtotal * (parseNum(vDesconto) / 100) : parseNum(vDesconto);
  const descontoItens = Math.max(0, base - subtotal);
  const descontoTotal = Math.max(0, descontoItens + descontoGeral);
  const pct = base > 0 ? (descontoTotal / base) * 100 : 0;
  return { base, subtotal, descontoItens, descontoGeral, descontoTotal, pct, total: Math.max(0, subtotal - descontoGeral) };
}

function DataBox({
  label,
  value,
  largeValue = false,
  valueColor = "text-black",
}: {
  label: string;
  value?: string;
  largeValue?: boolean;
  valueColor?: string;
}) {
  return (
    <div className="flex h-full flex-col justify-between rounded-xl bg-white p-3 shadow-md">
      <span className="text-sm font-bold text-gray-800">{label}</span>
      <div className={`mt-2 text-right font-bold ${largeValue ? "text-4xl" : "text-2xl"} ${valueColor}`}>{value ?? ""}</div>
    </div>
  );
}

export default function PreVenda() {
  const [linhas, setLinhas] = useState<LinhaPdv[]>([]);
  const [busca, setBusca] = useState("");
  const [sugestoes, setSugestoes] = useState<ProdutoResumo[]>([]);
  const [focoLista, setFocoLista] = useState(-1);
  const [qtdDigitada, setQtdDigitada] = useState(1);

  const [cliente, setCliente] = useState(() => sessionStorage.getItem("pdv_cliente") || CLIENTE_PADRAO.nome);
  const [clienteId, setClienteId] = useState<number | null>(() => {
    const saved = sessionStorage.getItem("pdv_cliente_id");
    return saved ? Number(saved) : CLIENTE_PADRAO.id;
  });

  const [obs, setObs] = useState("");
  const [desconto, setDesconto] = useState("");
  const [descModo, setDescModo] = useState<"pct" | "valor">("valor");
  const [condicoes, setCondicoes] = useState<CondicaoPagamento[]>([]);
  const [condicaoId, setCondicaoId] = useState("");

  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [editandoNumero, setEditandoNumero] = useState("");
  const [salvando, setSalvando] = useState(false);

  const [modalCadCliente, setModalCadCliente] = useState<string | null>(null);
  const [modalBuscaCliente, setModalBuscaCliente] = useState(false);
  const [modalAutorizar, setModalAutorizar] = useState<
    { id: number | null; descontoPct?: number; limitePct?: number; modo: "autorizar" | "finalizar" } | null
  >(null);
  const [modalDadosCliente, setModalDadosCliente] = useState(false);
  const [modalLocalizar, setModalLocalizar] = useState(false);
  // Desconto acima da alçada já autorizado por um gerente (nesta composição).
  // Qualquer alteração de itens/desconto expira essa autorização.
  const [descontoAutorizado, setDescontoAutorizado] = useState(false);

  const buscaRef = useRef<HTMLInputElement>(null);
  const descontoRef = useRef<HTMLInputElement>(null);
  const condRef = useRef<HTMLSelectElement>(null);
  const obsRef = useRef<HTMLInputElement>(null);
  const salvarRef = useRef<HTMLButtonElement>(null);
  const qtdCentralRef = useRef<HTMLInputElement>(null);
  const buscaTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const [linhaAtiva, setLinhaAtiva] = useState<number | null>(null);
  const [hora, setHora] = useState(() => new Date().toLocaleTimeString("pt-BR"));

  useEffect(() => {
    const t = setInterval(() => setHora(new Date().toLocaleTimeString("pt-BR")), 1000);
    return () => clearInterval(t);
  }, []);

  const c = useMemo(() => calculosPdv(linhas, descModo, desconto), [linhas, descModo, desconto]);

  // Limite de alçada do vendedor atual (temporariamente se aplica a todos,
  // inclusive admin, até existirem grupos/permissões).
  const usuario = usuarioCorrente();
  const limiteAlcadaPct = usuario ? (usuario.desconto_limite_pct ?? 0) : 0;

  // Qualquer alteração no pedido (itens/quantidade/cliente/desconto/condição…)
  // expira a autorização de desconto anterior — reavalia do zero.
  useEffect(() => {
    setDescontoAutorizado(false);
  }, [linhas, cliente, clienteId, obs, desconto, descModo, condicaoId]);

  useEffect(() => {
    void api
      .listarCondicoes()
      .then((cds) => {
        setCondicoes(cds);
        // Condição padrão: "À Vista" (ou a primeira disponível).
        setCondicaoId((cur) => {
          if (cur) return cur;
          const vista = cds.find((cd) => /vista/i.test(cd.nome)) ?? cds[0];
          return vista ? String(vista.id) : "";
        });
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    buscaRef.current?.focus();
  }, []);

  useEffect(() => {
    clearTimeout(buscaTimer.current);
    const { qtd, termo } = parseBusca(busca);
    if (!termo) {
      setSugestoes([]);
      setFocoLista(-1);
      return;
    }
    setQtdDigitada(qtd);
    buscaTimer.current = setTimeout(() => {
      void api
        .listarProdutos({ q: termo, limit: 8, agrupado: 0 })
        .then((res) => {
          setSugestoes(res.items.map((i) => i as ProdutoResumo));
          setFocoLista(-1);
        })
        .catch(() => setSugestoes([]));
    }, 180);
    return () => clearTimeout(buscaTimer.current);
  }, [busca]);

  const adicionar = (p: ProdutoResumo) => {
    const qtd = qtdDigitada;
    let atualizado = false;
    const next = linhas.map((l) => {
      if (l.produto_id != null && l.produto_id === p.id) {
        atualizado = true;
        return { ...l, quantidade: l.quantidade + qtd, subtotal: l.preco_unitario * (l.quantidade + qtd) };
      }
      return l;
    });
    if (!atualizado) {
      next.push({
        produto_id: p.id,
        sku: p.sku || "",
        nome: p.name || "",
        marca: p.brand || "",
        especificacao: p.spec || "",
        unidade: p.unidade_venda || "",
        ncm: p.ncm || "",
        imagem_url: p.imagem_url || "",
        quantidade: qtd,
        preco_unitario: p.price || 0,
        desconto_percentual: 0,
        desconto_modo: "pct",
        subtotal: (p.price || 0) * qtd,
      });
    }
    const alvo = atualizado ? next.findIndex((l) => l.produto_id != null && l.produto_id === p.id) : next.length - 1;
    setLinhas(next);
    setQtdDigitada(1);
    setLinhaAtiva(alvo);
    setSugestoes([]);
    setFocoLista(-1);
    setBusca("");
    setTimeout(() => {
      const el = qtdCentralRef.current;
      el?.focus();
      el?.select();
    }, 0);
    void api
      .precoEfetivo(p.id)
      .then((ef) => {
        if (ef && ef.preco > 0) {
          setLinhas((arr) =>
            arr.map((l) =>
              l.produto_id === p.id && l.preco_unitario !== ef.preco
                ? { ...l, preco_unitario: ef.preco, subtotal: ef.preco * l.quantidade * (1 - l.desconto_percentual / 100) }
                : l
            )
          );
        }
      })
      .catch(() => {});
  };

  const selecionarCliente = (cli: Cliente) => {
    setCliente(cli.nome);
    setClienteId(cli.id);
    sessionStorage.setItem("pdv_cliente", cli.nome);
    sessionStorage.setItem("pdv_cliente_id", String(cli.id));
    buscaRef.current?.focus();
  };

  const removerLinha = (i: number) => {
    setLinhas((arr) => arr.filter((_, j) => j !== i));
    setLinhaAtiva(null);
    buscaRef.current?.focus();
  };

  const onQtyChange = (i: number, raw: string) => {
    setLinhas((arr) =>
      arr.map((l, j) => {
        if (j !== i) return l;
        const qtd = Math.max(0, parseNum(raw));
        return { ...l, quantidade: qtd, subtotal: l.preco_unitario * qtd * (1 - l.desconto_percentual / 100) };
      })
    );
  };

  const buildItens = (): OrcamentoItemPayload[] =>
    linhas.map((l) => ({
      produto_id: l.produto_id,
      nome: l.nome,
      sku: l.sku,
      marca: l.marca,
      especificacao: l.especificacao,
      quantidade: l.quantidade,
      preco_unitario: l.preco_unitario,
      desconto_percentual: l.desconto_percentual,
    }));

  // Persiste (cria/atualiza) o rascunho atual — sem limpar a tela nem avisar.
  // Compartilha a chamada em voo para não criar orçamento duplicado quando o
  // auto-save e uma ação manual (finalizar/salvar) disparam juntos.
  const persistirInFlightRef = useRef<Promise<{ id: number; numero: string } | null> | null>(null);

  const persistir = async (): Promise<{ id: number; numero: string } | null> => {
    if (persistirInFlightRef.current) return persistirInFlightRef.current;
    if (!linhas.length) return null;
    const p = (async () => {
      const itens = buildItens();
      const condId = parseInt(condicaoId, 10) || undefined;
      let res: { id: number; numero: string };
      if (editandoId != null) {
        const patch: Record<string, unknown> = {
          cliente: cliente.trim(),
          observacoes: obs.trim(),
          desconto: c.descontoGeral,
        };
        if (condId !== undefined) patch.condicao_pagamento_id = condId;
        await api.atualizarOrcamento(editandoId, patch);
        await api.substituirItensOrcamento(editandoId, itens);
        res = { id: editandoId, numero: editandoNumero };
      } else {
        res = await api.criarOrcamento({
          cliente: cliente.trim(),
          validade_dias: VALIDADE_PADRAO,
          observacoes: obs.trim(),
          desconto: c.descontoGeral,
          itens,
          condicao_pagamento_id: condId,
          cliente_id: clienteId ?? undefined,
        });
        setEditandoId(res.id);
        setEditandoNumero(res.numero);
      }
      sessionStorage.setItem("pdv_cliente", cliente.trim());
      sessionStorage.setItem("pdv_cliente_id", clienteId != null ? String(clienteId) : String(CLIENTE_PADRAO.id));
      return res;
    })();
    persistirInFlightRef.current = p;
    try {
      return await p;
    } finally {
      persistirInFlightRef.current = null;
    }
  };

  const limparTela = () => {
    setEditandoId(null);
    setEditandoNumero("");
    setLinhas([]);
    setLinhaAtiva(null);
    setDesconto("");
    setDescModo("valor");
    setObs("");
    // Nova pré-venda começa no cliente padrão (CONSUMIDOR).
    setCliente(CLIENTE_PADRAO.nome);
    setClienteId(CLIENTE_PADRAO.id);
    sessionStorage.setItem("pdv_cliente", CLIENTE_PADRAO.nome);
    sessionStorage.setItem("pdv_cliente_id", String(CLIENTE_PADRAO.id));
    buscaRef.current?.focus();
  };

  const finalizarOrcamento = async (id: number): Promise<boolean> => {
    // Gate local: desconto acima da alçada e ainda não autorizado → abre o
    // modal de autorização ANTES de chamar o backend (sem o 403 confuso).
    if (c.descontoTotal > 0.01 && c.pct > limiteAlcadaPct + 1e-6 && !descontoAutorizado) {
      setModalAutorizar({ id, descontoPct: c.pct, limitePct: limiteAlcadaPct, modo: "finalizar" });
      return false;
    }
    try {
      await api.atualizarOrcamento(id, { status: "faturado" });
      return true;
    } catch (e) {
      const err = e as Error & { code?: string; details?: Record<string, unknown> };
      if (err.code === "desconto_exige_autorizacao") {
        // Fallback: o backend rejeitou (ex.: autorização expirada após edição).
        setModalAutorizar({
          id,
          descontoPct: err.details?.desconto_pct as number | undefined,
          limitePct: err.details?.limite_pct as number | undefined,
          modo: "finalizar",
        });
        return false;
      }
      toast("Erro ao finalizar: " + err.message, "error");
      return false;
    }
  };

  // Finaliza (fatura → caixa). Ação principal (F1).
  const finalizar = async (): Promise<void> => {
    if (!linhas.length) {
      toast("Adicione ao menos um item", "error");
      return;
    }
    setSalvando(true);
    try {
      const res = await persistir();
      if (!res) return;
      const ok = await finalizarOrcamento(res.id);
      if (!ok) {
        // Finalização bloqueada: mantém os dados e passa a editar o rascunho
        // criado (para não duplicar) enquanto o modal de autorização está aberto.
        setEditandoId(res.id);
        setEditandoNumero(res.numero);
        return;
      }
      toast(`${res.numero} finalizado`, "success");
      limparTela();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  // Salva explicitamente o rascunho e limpa a tela (F3).
  const salvar = async (): Promise<void> => {
    if (!linhas.length) {
      toast("Adicione ao menos um item", "error");
      return;
    }
    // Autorização por senha exigida apenas ao salvar/finalizar, se o desconto
    // estiver acima da alçada do vendedor e ainda não tiver sido autorizado.
    if (c.descontoTotal > 0.01 && c.pct > limiteAlcadaPct + 1e-6 && !descontoAutorizado) {
      setModalAutorizar({ id: null, descontoPct: c.pct, limitePct: limiteAlcadaPct, modo: "autorizar" });
      return;
    }
    setSalvando(true);
    try {
      const res = await persistir();
      if (!res) return;
      toast(`${res.numero} salvo`, "success");
      limparTela();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const visualizarImprimir = async () => {
    if (!linhas.length) {
      toast("Adicione itens antes de visualizar", "error");
      return;
    }
    const res = await persistir();
    if (res) window.open(`/orcamentos/venda/${res.id}/imprimir`, "_blank");
  };

  const imprimirTermica = async () => {
    if (!linhas.length) {
      toast("Adicione itens antes de imprimir", "error");
      return;
    }
    setSalvando(true);
    try {
      const res = await persistir();
      if (!res) return;
      void api.imprimirOrcamento(res.id).catch(() => toast("Orçamento salvo, mas a impressão falhou", "error"));
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const limpar = () => {
    if (linhas.length && !window.confirm("Descartar o pedido atual e limpar a tela?")) return;
    if (editandoId != null) {
      void api.excluirOrcamento(editandoId).catch(() => {});
    }
    limparTela();
  };

  // ── Auto-save: persistir o rascunho a cada mudança (debounce) ──
  const persistirRef = useRef(persistir);
  persistirRef.current = persistir;
  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    if (linhas.length === 0) return;
    clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = setTimeout(() => {
      void persistirRef.current().catch(() => {});
    }, 500);
    return () => clearTimeout(autoSaveTimer.current);
  }, [linhas, cliente, clienteId, obs, desconto, descModo, condicaoId]);

  // ── Ao sair da tela: salvar (manter) ou descartar (excluir) o pedido ──
  const editandoIdRef = useRef<number | null>(null);
  const linhasRef = useRef<LinhaPdv[]>([]);
  useEffect(() => {
    editandoIdRef.current = editandoId;
    linhasRef.current = linhas;
  }, [editandoId, linhas]);

  useEffect(() => {
    const temPedido = () => linhasRef.current.length > 0;
    const aoSair = () => {
      if (!temPedido()) return;
      const manter = window.confirm(
        "Há um pedido em andamento.\n\nClique em OK para SALVAR (manter o rascunho) ou em Cancelar para DESCARTAR (excluir) o pedido."
      );
      if (!manter && editandoIdRef.current != null) {
        void api.excluirOrcamento(editandoIdRef.current).catch(() => {});
      }
    };
    const onHash = () => {
      if (location.hash !== "#/pre-venda") aoSair();
    };
    const onUnload = (e: BeforeUnloadEvent) => {
      if (temPedido()) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("hashchange", onHash);
    window.addEventListener("beforeunload", onUnload);
    return () => {
      window.removeEventListener("hashchange", onHash);
      window.removeEventListener("beforeunload", onUnload);
    };
  }, []);

  const acaoAtalho = async (f: number) => {
    switch (f) {
      case 1:
        await finalizar();
        break;
      case 2:
        await visualizarImprimir();
        break;
      case 3:
        await salvar();
        break;
      case 5:
        limpar();
        break;
      case 6:
        setModalBuscaCliente(true);
        break;
      case 7:
        await imprimirTermica();
        break;
      case 8:
        setModalLocalizar(true);
        break;
      case 9:
        if (clienteId != null && clienteId !== CLIENTE_PADRAO.id) setModalDadosCliente(true);
        break;
    }
  };

  const acaoAtalhoRef = useRef(acaoAtalho);
  acaoAtalhoRef.current = acaoAtalho;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const m = e.key?.toUpperCase().match(/^F([1-9])$/);
      if (!m) return;
      e.preventDefault();
      e.stopPropagation();
      void acaoAtalhoRef.current(Number(m[1]));
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const onDescontoChange = (raw: string) => {
    let v = raw;
    let modo: "pct" | "valor" = descModo;
    if (/%/.test(v)) {
      modo = "pct";
      v = v.replace(/%/g, "").trim();
    }
    setDescModo(modo);
    setDesconto(v);
    // A autorização por senha NÃO é solicitada durante a digitação: ela é
    // pedida apenas ao Salvar ou Finalizar (ver salvar/finalizarOrcamento).
  };

  const carregarParaEdicao = async (id: number) => {
    let d: OrcamentoDetalhe;
    try {
      d = await api.detalharOrcamento(id);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
      return;
    }
    setCliente(d.cliente || "");
    setClienteId(d.cliente_id ?? null);
    setObs(d.observacoes || "");
    setDesconto(String(d.desconto || ""));
    setDescModo("valor");
    setLinhas(
      (d.itens || []).map((it) => ({
        produto_id: it.produto_id ?? null,
        sku: it.sku || "",
        nome: it.nome || "",
        marca: it.marca || "",
        especificacao: it.especificacao || "",
        unidade: "",
        ncm: "",
        imagem_url: "",
        quantidade: it.quantidade,
        preco_unitario: it.preco_unitario,
        desconto_percentual: it.desconto_percentual || 0,
        desconto_modo: "pct",
        subtotal: it.subtotal ?? it.preco_unitario * it.quantidade,
      }))
    );
    setLinhaAtiva(null);
    setEditandoId(id);
    setEditandoNumero(d.numero || "");
    if (d.condicao_pagamento_id != null) setCondicaoId(String(d.condicao_pagamento_id));
    setModalLocalizar(false);
    buscaRef.current?.focus();
  };

  const linhaAtual = linhaAtiva != null ? linhas[linhaAtiva] : undefined;

  return (
    <div className="flex min-h-[560px] flex-col">
      {/* ── Cabeçalho do sistema ─────────────────────────── */}
      <header className="flex flex-shrink-0 items-center justify-between gap-3 border-b border-gray-300 bg-[#e4e4e4] px-4 py-1.5 text-sm text-gray-800">
        <div>
          <strong>Operador:</strong> {usuarioCorrente()?.nome ?? "—"}
        </div>
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <span>Cliente:</span>
          <button
            onClick={() => setModalBuscaCliente(true)}
            className="max-w-md truncate rounded border border-gray-400 bg-white px-2 py-0.5 text-sm font-medium text-gray-800 hover:bg-gray-100"
            title="F6 — selecionar cliente"
          >
            {cliente}
          </button>
          <span className="text-[10px] text-gray-500">F6</span>
          <button
            onClick={() => setModalDadosCliente(true)}
            disabled={clienteId == null || clienteId === CLIENTE_PADRAO.id}
            className="rounded border border-gray-400 bg-white px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
            title="F9 — dados do cliente"
          >
            Dados do cliente <span className="text-[10px] text-gray-400">F9</span>
          </button>
        </div>
        <div>Vendedor: {usuarioCorrente()?.nome ?? "—"}</div>
        <div>Horário: {hora}</div>
      </header>

      {/* ── Área principal ────────────────────────────────── */}
      <main className="flex min-h-[480px] flex-1 flex-col gap-3 overflow-hidden bg-[#6a84a6] p-4">
        {/* Painel de produto + busca */}
        <div className="relative flex-shrink-0 rounded-xl bg-white p-3 shadow-md">
          <span className="absolute left-4 top-2 text-sm font-bold text-gray-800">Produto</span>
          <div className="relative mx-auto mb-1 w-full max-w-2xl pt-5">
            <input
              ref={buscaRef}
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Código / nome (ex.: 3*Cabo) · ENTER adiciona"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-center text-lg text-gray-900 placeholder-gray-400 focus:border-orange-400 focus:outline-none"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  if (sugestoes.length > 0) adicionar(sugestoes[focoLista >= 0 ? focoLista : 0]);
                  else descontoRef.current?.focus();
                } else if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setFocoLista((f) => (sugestoes.length ? (f + 1) % sugestoes.length : -1));
                } else if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setFocoLista((f) => (sugestoes.length ? (f - 1 + sugestoes.length) % sugestoes.length : -1));
                } else if (e.key === "Escape") {
                  setSugestoes([]);
                }
              }}
            />
            {sugestoes.length > 0 && (
              <div className="absolute z-20 mt-1 w-full rounded-lg border border-gray-300 bg-white shadow-lg">
                {sugestoes.map((p, i) => (
                  <button
                    key={p.id}
                    className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm ${i === focoLista ? "bg-orange-500 text-white" : "hover:bg-orange-50"}`}
                    onMouseEnter={() => setFocoLista(i)}
                    onClick={() => adicionar(p)}
                  >
                    <span>
                      {qtdDigitada > 1 ? <span className={`mr-1 rounded px-1.5 text-xs font-semibold ${i === focoLista ? "bg-orange-600 text-white" : "bg-orange-100 text-orange-700"}`}>{qtdDigitada}x</span> : null}
                      <span className="font-medium">{p.name}</span>
                      <span className={`block text-xs ${i === focoLista ? "text-orange-100" : "text-gray-400"}`}>{[p.sku, p.spec, p.brand, p.unidade_venda].filter(Boolean).join(" · ")}</span>
                    </span>
                    <span className="font-semibold">{fmtMoney(p.price)}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <h1 className="py-1 text-center text-2xl font-bold text-black">{linhaAtual?.nome || "Informe um produto para iniciar a venda"}</h1>
          {linhaAtual?.especificacao ? (
            <p className="text-center text-sm text-gray-500">{linhaAtual.especificacao}</p>
          ) : null}
        </div>

        {/* Três colunas */}
        <div className="flex min-h-0 flex-1 gap-4">
          {/* Imagem do produto */}
          <div className="flex w-3/12 items-center justify-center overflow-hidden rounded-[2rem] bg-white p-4 shadow-md">
            {linhaAtual?.imagem_url ? (
              <img src={linhaAtual.imagem_url} alt="" className="max-h-full max-w-full object-contain" />
            ) : (
              <div className="text-center text-sm text-gray-400">Sem imagem</div>
            )}
          </div>

          {/* Formulário de lançamento */}
          <div className="flex w-3/12 flex-col gap-3">
            <DataBox label="Código" value={linhaAtual?.sku || "—"} />
            <div className="flex h-full flex-col justify-between rounded-xl bg-white p-3 shadow-md">
              <span className="text-sm font-bold text-gray-800">Quantidade</span>
              <input
                ref={qtdCentralRef}
                type="number"
                min={0}
                step="any"
                value={linhaAtual ? String(linhaAtual.quantidade) : ""}
                placeholder="0"
                onChange={(e) => {
                  if (linhaAtiva != null) onQtyChange(linhaAtiva, e.target.value);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    buscaRef.current?.focus();
                  }
                }}
                className="mt-2 w-full bg-transparent text-right text-2xl font-bold text-black outline-none"
              />
            </div>
            <DataBox label="Valor Unitário" value={fmtMoney(linhaAtual?.preco_unitario ?? 0)} />
            <DataBox label="Valor Total" value={fmtMoney(linhaAtual?.subtotal ?? 0)} />
          </div>

          {/* Cupom fiscal (somente leitura) */}
          <div className="flex w-6/12 min-h-0 flex-col overflow-hidden rounded-[2.5rem] bg-white p-4 font-mono text-sm shadow-md">
            <div className="grid grid-cols-[80px_1fr_60px_84px_84px_24px] gap-1 text-[11px] uppercase text-gray-500">
              <span>Código</span>
              <span>Descrição</span>
              <span className="text-right">Qtde</span>
              <span className="text-right">Vl.Unit</span>
              <span className="text-right">Vl.Item</span>
              <span />
            </div>
            <div className="my-2 border-b-2 border-dashed border-gray-300" />
            <div className="min-h-0 flex-1 overflow-auto">
              {linhas.length === 0 ? (
                <p className="py-8 text-center text-gray-400">Nenhum item</p>
              ) : (
                linhas.map((l, i) => (
                  <div
                    key={i}
                    onClick={() => setLinhaAtiva(i)}
                    className={`grid cursor-pointer grid-cols-[80px_1fr_60px_84px_84px_24px] items-center gap-1 border-b border-gray-100 py-1.5 ${linhaAtiva === i ? "bg-orange-100" : ""}`}
                  >
                    <span className="truncate text-xs">{l.sku || "#" + (i + 1)}</span>
                    <span className="truncate">{[l.nome, l.especificacao].filter(Boolean).join(" · ")}</span>
                    <span className="text-right text-xs">{l.quantidade}</span>
                    <span className="text-right text-xs">{fmtMoney(l.preco_unitario)}</span>
                    <span className="text-right font-semibold">{fmtMoney(l.subtotal)}</span>
                    <button
                      className="text-gray-400 hover:text-red-600"
                      onClick={(e) => {
                        e.stopPropagation();
                        removerLinha(i);
                      }}
                    >
                      ×
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Lançamento (desconto / condição / obs) */}
        <div className="flex flex-shrink-0 flex-wrap items-center gap-2 rounded-xl bg-white/90 px-3 py-2 text-xs">
          <span className="ml-2 font-semibold text-gray-600">Desconto {descModo === "pct" ? "%" : "R$"}</span>
          <input
            ref={descontoRef}
            inputMode="decimal"
            placeholder="0,00"
            value={desconto}
            onChange={(e) => onDescontoChange(e.target.value)}
            onKeyDown={(e) => {
              const k = e.key.toLowerCase();
              if (k === "p") {
                e.preventDefault();
                setDescModo("pct");
              } else if (k === "r") {
                e.preventDefault();
                setDescModo("valor");
              } else if (e.key === "Enter") {
                e.preventDefault();
                condRef.current?.focus();
              }
            }}
            className="w-24 rounded border border-gray-300 px-2 py-1 text-sm"
          />
          <span className="font-semibold text-gray-600">Condição</span>
          <select
            ref={condRef}
            value={condicaoId}
            onChange={(e) => setCondicaoId(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                obsRef.current?.focus();
              }
            }}
            className="w-44 rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="">Selecione</option>
            {condicoes.map((cd) => (
              <option key={cd.id} value={cd.id}>
                {cd.nome}
              </option>
            ))}
          </select>
          <span className="font-semibold text-gray-600">Obs</span>
          <input
            ref={obsRef}
            value={obs}
            onChange={(e) => setObs(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                salvarRef.current?.focus();
              }
            }}
            className="min-w-40 flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </div>

        {/* Totais */}
        <div className="flex h-24 flex-shrink-0 gap-4">
          <div className="flex w-4/12 items-center justify-center rounded-xl bg-white shadow-md">
            <span className="text-5xl font-bold tracking-widest text-black">{editandoId ? "ALTERAÇÃO" : "VENDA"}</span>
          </div>
          <div className="w-2/12">
            <DataBox label="Volumes" value={String(linhas.reduce((s, l) => s + l.quantidade, 0))} />
          </div>
          <div className="w-6/12">
            <DataBox label="Total da Venda" value={fmtMoney(c.total)} largeValue valueColor="text-red-600" />
          </div>
        </div>
      </main>

      {/* ── Rodapé: atalhos + ações ───────────────────────── */}
      <footer className="flex flex-shrink-0 flex-wrap items-center gap-2 border-t border-gray-400 bg-[#f0f0f0] px-4 py-2">
        <Button size="sm" variant="ghost" onClick={() => void acaoAtalho(5)}>
          Limpar (F5)
        </Button>
        <Button size="sm" variant="ghost" onClick={() => void acaoAtalho(6)}>
          Cliente (F6)
        </Button>
        <Button size="sm" variant="ghost" onClick={() => void acaoAtalho(7)} disabled={!linhas.length}>
          Enviar p/ Impressora Térmica (F7)
        </Button>
        <Button size="sm" variant="ghost" onClick={() => void acaoAtalho(8)}>
          Localizar orçamento (F8)
        </Button>
        <div className="ml-auto flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={() => void acaoAtalho(2)} disabled={!linhas.length}>
            Visualizar (F2)
          </Button>
          <Button size="sm" variant="outline" onClick={() => void acaoAtalho(3)} disabled={!linhas.length || salvando}>
            Salvar (F3)
          </Button>
          <Button ref={salvarRef} variant="primary" onClick={() => void acaoAtalho(1)} disabled={!linhas.length || salvando}>
            Finalizar (F1)
          </Button>
        </div>
      </footer>

      {modalCadCliente !== null && (
        <ModalCadastroCliente prefill={modalCadCliente} onClose={() => setModalCadCliente(null)} onSaved={selecionarCliente} />
      )}
      {modalBuscaCliente && (
        <ModalBuscaCliente
          onClose={() => setModalBuscaCliente(false)}
          onSaved={selecionarCliente}
          onNovoCliente={() => {
            setModalBuscaCliente(false);
            setModalCadCliente("");
          }}
        />
      )}
      {modalLocalizar && (
        <ModalLocalizarOrcamento onClose={() => setModalLocalizar(false)} onSelecionar={(id) => void carregarParaEdicao(id)} />
      )}
      {modalDadosCliente && clienteId != null && (
        <ModalDadosCliente clienteId={clienteId} onClose={() => setModalDadosCliente(false)} />
      )}
      {modalAutorizar !== null && (
        <ModalAutorizar
          id={modalAutorizar.id}
          descontoPct={modalAutorizar.descontoPct}
          limitePct={modalAutorizar.limitePct}
          finalizar={modalAutorizar.modo === "finalizar"}
          onSalvarAntes={() => persistir()}
          onClose={() => setModalAutorizar(null)}
          onAutorizado={() => {
            setDescontoAutorizado(true);
            limparTela();
          }}
        />
      )}
    </div>
  );
}

function ModalCadastroCliente({
  prefill,
  onClose,
  onSaved,
}: {
  prefill: string;
  onClose: () => void;
  onSaved: (c: Cliente) => void;
}) {
  const [nome, setNome] = useState(prefill);
  const [doc, setDoc] = useState("");
  const [tel, setTel] = useState("");
  const [wpp, setWpp] = useState("");
  const [email, setEmail] = useState("");
  const [end, setEnd] = useState("");
  const [cid, setCid] = useState("");
  const [uf, setUf] = useState("");
  const [obs, setObs] = useState("");

  const salvar = async () => {
    if (!nome.trim()) {
      toast("Informe o nome", "error");
      return;
    }
    if (!doc.trim()) {
      toast("CPF obrigatório", "error");
      return;
    }
    try {
      const res = await api.criarCliente({
        nome: nome.trim(),
        doc: doc.trim(),
        tipo_pessoa: "f",
        telefone: tel.trim() || undefined,
        whatsapp: wpp.trim() || undefined,
        email: email.trim() || undefined,
        endereco: end.trim() || undefined,
        cidade: cid.trim() || undefined,
        uf: uf.trim().toUpperCase() || undefined,
        observacoes: obs.trim() || undefined,
      });
      toast("Cliente cadastrado", "success");
      onClose();
      onSaved({ id: res.id, nome: nome.trim(), doc: doc.trim(), tipo_pessoa: "f", email: "", telefone: "", whatsapp: wpp.trim(), endereco: "", cidade: cid.trim(), uf: uf.trim().toUpperCase(), cep: "", vendedor_id: null, vendedor_nome: null, limite_credito: 0, observacoes: "", ativo: true } as Cliente);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Cadastrar cliente"
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
        <Field label="Nome *">
          <Input value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </Field>
        <Field label="CPF *">
          <Input placeholder="000.000.000-00" value={doc} onChange={(e) => setDoc(e.target.value)} />
        </Field>
        <Field label="Telefone">
          <Input value={tel} onChange={(e) => setTel(e.target.value)} />
        </Field>
        <Field label="WhatsApp">
          <Input value={wpp} onChange={(e) => setWpp(e.target.value)} />
        </Field>
        <Field label="E-mail">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <div className="grid grid-cols-3 gap-3">
          <Field label="Endereço" className="col-span-3">
            <Input value={end} onChange={(e) => setEnd(e.target.value)} />
          </Field>
          <Field label="Cidade" className="col-span-2">
            <Input value={cid} onChange={(e) => setCid(e.target.value)} />
          </Field>
          <Field label="UF">
            <Input maxLength={2} value={uf} onChange={(e) => setUf(e.target.value)} />
          </Field>
        </div>
        <Field label="Observações">
          <Input value={obs} onChange={(e) => setObs(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}

function ModalBuscaCliente({
  onClose,
  onSaved,
  onNovoCliente,
}: {
  onClose: () => void;
  onSaved: (c: Cliente) => void;
  onNovoCliente: () => void;
}) {
  const [clientes, setClientes] = useState<Cliente[]>([]);

  useEffect(() => {
    void api.listarClientes(true).then(setClientes).catch(() => setClientes([]));
  }, []);

  return (
    <SearchModal
      open
      title="Buscar cliente"
      columns={[
        { key: "id", label: "Código", align: "right", render: (c) => String(c.id).padStart(6, "0") },
        { key: "nome", label: "Nome", render: (c) => c.nome },
        { key: "doc", label: "CPF/CNPJ", render: (c) => c.doc || "—" },
        { key: "cidade", label: "Cidade", render: (c) => [c.cidade, c.uf].filter(Boolean).join(" - ") || "—" },
      ]}
      data={clientes}
      searchText={(c) => [c.nome, c.doc, c.cidade, c.telefone, c.whatsapp, String(c.id)].join(" ")}
      extra={
        <div className="mt-3 flex justify-end">
          <button onClick={onNovoCliente} className="rounded-md bg-[#6a84a6] px-3 py-1.5 text-sm font-bold text-white hover:bg-[#587291]">
            + Novo cliente
          </button>
        </div>
      }
      onClose={onClose}
      onSelect={(c) => {
        onSaved(c);
        onClose();
      }}
    />
  );
}

function LinhaInfo({ label, valor }: { label: string; valor?: string | null }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-xs font-medium uppercase text-gray-500">{label}</span>
      <span className="text-right font-medium text-gray-800">{valor || "—"}</span>
    </div>
  );
}

function ModalDadosCliente({ clienteId, onClose }: { clienteId: number; onClose: () => void }) {
  const [cli, setCli] = useState<Cliente | null>(null);
  const [situacao, setSituacao] = useState<ClienteSituacao | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    let alive = true;
    setCarregando(true);
    void Promise.all([api.detalharCliente(clienteId), api.situacaoCliente(clienteId)])
      .then(([c, s]) => {
        if (!alive) return;
        setCli(c);
        setSituacao(s);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setCarregando(false);
      });
    return () => {
      alive = false;
    };
  }, [clienteId]);

  return (
    <Modal
      open
      onClose={onClose}
      title={cli?.nome ?? "Dados do cliente"}
      footer={<Button onClick={onClose}>Fechar</Button>}
    >
      {carregando ? (
        <p className="py-6 text-center text-sm text-gray-400">Carregando…</p>
      ) : (
        <div className="space-y-3 text-sm">
          <LinhaInfo label="Endereço" valor={[cli?.endereco, cli?.cidade, cli?.uf].filter(Boolean).join(" — ")} />
          <LinhaInfo label="Telefone" valor={cli?.telefone || cli?.whatsapp} />
          <LinhaInfo label="E-mail" valor={cli?.email} />
          <div className="my-2 border-t border-gray-200" />
          <LinhaInfo label="Limite" valor={fmtMoney(situacao?.limite_credito ?? 0)} />
          <LinhaInfo label="Limite utilizado" valor={fmtMoney(situacao?.limite_utilizado ?? 0)} />
          <LinhaInfo label="Limite disponível" valor={fmtMoney(situacao?.limite_disponivel ?? 0)} />
          {situacao?.tem_atraso && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-red-700">
              <strong>Conta em aberto (em atraso):</strong> {fmtMoney(situacao.saldo_em_atraso)}
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

function ModalAutorizar({
  id,
  descontoPct,
  limitePct,
  finalizar,
  onSalvarAntes,
  onClose,
  onAutorizado,
}: {
  id: number | null;
  descontoPct?: number;
  limitePct?: number;
  finalizar: boolean;
  onSalvarAntes?: () => Promise<{ id: number } | null>;
  onClose: () => void;
  onAutorizado: () => void;
}) {
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [autorizando, setAutorizando] = useState(false);

  const tentar = async () => {
    if (!login.trim() || !senha) {
      toast("Informe login e senha do gerente", "error");
      return;
    }
    setAutorizando(true);
    try {
      let alvoId = id;
      if (alvoId == null && onSalvarAntes) {
        const res = await onSalvarAntes();
        if (!res) {
          setAutorizando(false);
          return;
        }
        alvoId = res.id;
      }
      if (alvoId != null) {
        await api.autorizarDescontoOrcamento(alvoId, { login: login.trim(), senha });
        if (finalizar) {
          await api.atualizarOrcamento(alvoId, { status: "faturado" });
        }
      }
      toast(finalizar ? "Desconto autorizado e venda finalizada" : "Desconto autorizado", "success");
      onClose();
      onAutorizado();
    } catch (e) {
      toast("Falha na autorização: " + (e as Error).message, "error");
      setAutorizando(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Autorizar desconto"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void tentar()} disabled={autorizando}>
            {autorizando ? "Autorizando…" : finalizar ? "Autorizar e finalizar" : "Autorizar desconto"}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-gray-500">
        {descontoPct != null && limitePct != null ? (
          <>
            O desconto aplicado (<b>{descontoPct.toFixed(1)}%</b>) está acima da alçada do
            vendedor (<b>{limitePct.toFixed(1)}%</b>). Informe as credenciais de um gerente
            para {finalizar ? "autorizar e finalizar" : "autorizar"}.
          </>
        ) : (
          `O desconto aplicado está acima da alçada do vendedor. Informe as credenciais do gerente para ${finalizar ? "autorizar e finalizar" : "autorizar"}.`
        )}
      </p>
      {id == null && (
        <p className="mb-3 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
          A pré-venda ainda não foi salva — ela será salva para registrar a autorização.
        </p>
      )}
      <div className="space-y-4">
        <Field label="Login do gerente">
          <Input autoComplete="username" value={login} onChange={(e) => setLogin(e.target.value)} autoFocus />
        </Field>
        <Field label="Senha">
          <Input
            type="password"
            autoComplete="current-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void tentar();
            }}
          />
        </Field>
      </div>
    </Modal>
  );
}

function ModalLocalizarOrcamento({ onClose, onSelecionar }: { onClose: () => void; onSelecionar: (id: number) => void }) {
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [rows, setRows] = useState<OrcamentoLista[]>([]);

  const buscar = () => {
    void api
      .listarOrcamentosFiltro({
        status: "rascunho",
        somente_meus: true,
        data_inicio: dataInicio || undefined,
        data_fim: dataFim || undefined,
      })
      .then(setRows)
      .catch(() => setRows([]));
  };

  useEffect(() => {
    buscar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataInicio, dataFim]);

  return (
    <SearchModal
      open
      title="Localizar orçamento (rascunho)"
      columns={[
        { key: "numero", label: "Nº", render: (o) => o.numero },
        { key: "cliente", label: "Cliente", render: (o) => o.cliente || "—" },
        { key: "total", label: "Total", align: "right", render: (o) => fmtMoney(o.total) },
        { key: "n_itens", label: "Itens", align: "center", render: (o) => o.n_itens },
        { key: "criado_em", label: "Criado em", render: (o) => fmtDate(o.criado_em) },
      ]}
      data={rows}
      searchText={(o) => [o.numero, o.cliente].join(" ")}
      extra={
        <div className="mt-3 flex items-center gap-2 text-sm">
          <span className="font-bold text-gray-800">Filtrar por data:</span>
          <input
            type="date"
            value={dataInicio}
            onChange={(e) => setDataInicio(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1"
          />
          <span>até</span>
          <input
            type="date"
            value={dataFim}
            onChange={(e) => setDataFim(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1"
          />
        </div>
      }
      onClose={onClose}
      onSelect={(o) => onSelecionar(o.id)}
    />
  );
}
