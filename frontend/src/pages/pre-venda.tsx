// pages/pre-venda.tsx — Pré-venda de orçamentos (React + Tailwind).

import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type Cliente,
  type CondicaoPagamento,
  type OrcamentoDetalhe,
  type OrcamentoItemPayload,
  type ProdutoResumo,
} from "../api/client";
import { fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { usuarioCorrente } from "./login";
import { Button } from "../ui/ui";
import { DataBox } from "../ui/data-box";
import { ModalCadastroCliente } from "./pre-venda/modal-cadastro-cliente";
import { ModalBuscaCliente } from "./pre-venda/modal-busca-cliente";
import { ModalDadosCliente } from "./pre-venda/modal-dados-cliente";
import { ModalAutorizar } from "./pre-venda/modal-autorizar";
import { ModalLocalizarOrcamento } from "./pre-venda/modal-localizar-orcamento";

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

export function parseBusca(v: string): { qtd: number; termo: string } {
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

function condicaoEhPrazo(condicao: CondicaoPagamento): boolean {
  const parcelas = condicao.parcelas || [];
  return parcelas.length >= 2 || (parcelas.length === 1 && Number(parcelas[0].dias || 0) > 0);
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
  // Aviso de crédito do cliente (trava de crédito da loja).
  const [avisoCredito, setAvisoCredito] = useState<{ texto: string; severidade: "warn" | "error" } | null>(null);
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
  const buscaRequestRef = useRef(0);

  const [linhaAtiva, setLinhaAtiva] = useState<number | null>(null);
  const [hora, setHora] = useState(() => new Date().toLocaleTimeString("pt-BR"));

  useEffect(() => {
    const t = setInterval(() => setHora(new Date().toLocaleTimeString("pt-BR")), 1000);
    return () => clearInterval(t);
  }, []);

  const c = useMemo(() => calculosPdv(linhas, descModo, desconto), [linhas, descModo, desconto]);
  const condicoesVisiveis = useMemo(
    () => clienteId === CLIENTE_PADRAO.id ? condicoes.filter((cd) => !condicaoEhPrazo(cd)) : condicoes,
    [clienteId, condicoes]
  );

  // O cliente padrão só pode operar à vista. Além de filtrar as opções,
  // corrige uma condição a prazo que tenha vindo de uma edição antiga.
  useEffect(() => {
    if (clienteId !== CLIENTE_PADRAO.id || !condicoes.length) return;
    if (!condicoesVisiveis.some((cd) => String(cd.id) === condicaoId)) {
      setCondicaoId(String(condicoesVisiveis[0]?.id || ""));
    }
  }, [clienteId, condicoes, condicoesVisiveis, condicaoId]);

  // Reavalia o aviso de crédito quando o total da venda muda.
  useEffect(() => {
    if (clienteId == null || clienteId === CLIENTE_PADRAO.id) return;
    const t = setTimeout(() => void carregarAvisoCredito(clienteId, cliente), 400);
    return () => clearTimeout(t);
  }, [c.total]);

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
    const requestId = ++buscaRequestRef.current;
    const { qtd, termo } = parseBusca(busca);
    if (!termo) {
      setSugestoes([]);
      setFocoLista(-1);
      setQtdDigitada(1);
      return;
    }
    setQtdDigitada(qtd);
    buscaTimer.current = setTimeout(() => {
      void api
        .listarProdutos({ q: termo, limit: 8, agrupado: 0 })
        .then((res) => {
          if (requestId !== buscaRequestRef.current) return;
          setSugestoes(res.items.map((i) => i as ProdutoResumo));
          setFocoLista(-1);
        })
        .catch(() => {
          if (requestId === buscaRequestRef.current) setSugestoes([]);
        });
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
    if (cli.id === CLIENTE_PADRAO.id) {
      const vista = condicoes.find((cd) => !condicaoEhPrazo(cd));
      setCondicaoId(vista ? String(vista.id) : "");
    }
    buscaRef.current?.focus();
    void carregarAvisoCredito(cli.id, cli.nome);
  };

  const carregarAvisoCredito = (id: number, nome: string) => {
    if (id === CLIENTE_PADRAO.id) {
      setAvisoCredito(null);
      return;
    }
    void api
      .situacaoCliente(id, c.total)
      .then((s) => {
        if (s.excede_limite) {
          setAvisoCredito({
            texto: `${nome}: venda de ${fmtMoney(c.total)} supera o limite disponível de ${fmtMoney(s.limite_disponivel)}.`,
            severidade: "warn",
          });
        } else if (s.excede_por_atraso) {
          setAvisoCredito({
            texto: `${nome}: cliente possui conta em atraso de ${fmtMoney(s.saldo_em_atraso)}.`,
            severidade: "error",
          });
        } else {
          setAvisoCredito(null);
        }
      })
      .catch(() => {});
  };

  const removerLinha = (i: number) => {
    setLinhas((arr) => arr.filter((_, j) => j !== i));
    setLinhaAtiva(null);
    buscaRef.current?.focus();
  };

  const ativarLinha = (i: number) => {
    if (i < 0 || i >= linhas.length) return;
    setLinhaAtiva(i);
    setTimeout(() => {
      qtdCentralRef.current?.focus();
      qtdCentralRef.current?.select();
    }, 0);
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
      await api.atualizarOrcamento(id, { status: "finalizado" });
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
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        const origem = e.target as HTMLElement | null;
        if (origem?.closest('[role="dialog"]')) return;
        e.preventDefault();
        buscaRef.current?.focus();
        buscaRef.current?.select();
        return;
      }
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
    <div className="flex min-h-[100dvh] flex-col">
      {/* ── Cabeçalho do sistema ─────────────────────────── */}
      <header className="flex flex-shrink-0 flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-gray-300 bg-[#e4e4e4] px-2 py-1.5 text-xs text-gray-800 sm:px-4 sm:text-sm">
        <div>
          <strong>Operador:</strong> <span className="hidden sm:inline">{usuarioCorrente()?.nome ?? "—"}</span>
          <span className="sm:hidden">{usuarioCorrente()?.nome?.split(" ")[0] ?? "—"}</span>
        </div>
        <div className="flex min-w-0 flex-1 items-center gap-1.5 sm:gap-2">
          <span>Cliente:</span>
          <button
            onClick={() => setModalBuscaCliente(true)}
            className="max-w-[40vw] truncate rounded border border-gray-400 bg-white px-2 py-0.5 text-sm font-medium text-gray-800 hover:bg-gray-100 sm:max-w-md"
            title="F6 — selecionar cliente"
          >
            {cliente}
          </button>
          <button
            onClick={() => setModalDadosCliente(true)}
            disabled={clienteId == null || clienteId === CLIENTE_PADRAO.id}
            className="rounded border border-gray-400 bg-white px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
            title="F9 — dados do cliente"
          >
            Dados
          </button>
        </div>
        <div className="hidden md:block">Vendedor: {usuarioCorrente()?.nome ?? "—"}</div>
        <div className="hidden md:block">Horário: {hora}</div>
      </header>

      {avisoCredito && (
        <div
          className={`flex flex-shrink-0 items-center justify-between gap-2 px-3 py-1.5 text-xs font-medium ${
            avisoCredito.severidade === "error" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"
          }`}
        >
          <span>{avisoCredito.texto}</span>
          <button onClick={() => setAvisoCredito(null)} className="rounded px-1 hover:bg-black/10" aria-label="Fechar aviso">
            ×
          </button>
        </div>
      )}

      {/* ── Área principal ────────────────────────────────── */}
      <main className="flex min-h-[480px] flex-1 flex-col gap-2 overflow-hidden bg-[#6a84a6] p-2 sm:gap-3 sm:p-4">
        {/* Painel de produto + busca */}
        <div className="relative flex-shrink-0 rounded-xl bg-white p-3 shadow-md">
          <span className="absolute left-4 top-2 text-sm font-bold text-gray-800">Produto</span>
          <div className="relative mx-auto mb-1 w-full max-w-2xl pt-5">
            <input
              ref={buscaRef}
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Código / nome (ex.: 3*Cabo) · ENTER adiciona"
              role="combobox"
              aria-label="Pesquisar produto"
              aria-autocomplete="list"
              aria-controls="pre-venda-sugestoes"
              aria-expanded={sugestoes.length > 0}
              aria-activedescendant={focoLista >= 0 ? `produto-sugestao-${sugestoes[focoLista]?.id}` : undefined}
              aria-keyshortcuts="Control+K"
              autoComplete="off"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-center text-lg text-gray-900 placeholder-gray-400 focus:border-orange-400 focus:outline-none"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  if (sugestoes.length > 0) {
                    adicionar(sugestoes[focoLista >= 0 ? focoLista : 0]);
                  } else if (!busca.trim()) {
                    descontoRef.current?.focus();
                    descontoRef.current?.select();
                  }
                } else if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setFocoLista((f) => (sugestoes.length ? (f + 1) % sugestoes.length : -1));
                } else if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setFocoLista((f) => (sugestoes.length ? (f - 1 + sugestoes.length) % sugestoes.length : -1));
                } else if (e.key === "Home" && sugestoes.length > 0) {
                  e.preventDefault();
                  setFocoLista(0);
                } else if (e.key === "End" && sugestoes.length > 0) {
                  e.preventDefault();
                  setFocoLista(sugestoes.length - 1);
                } else if (e.key === "Escape") {
                  setSugestoes([]);
                }
              }}
            />
            {sugestoes.length > 0 && (
              <div id="pre-venda-sugestoes" role="listbox" aria-label="Produtos encontrados" className="absolute z-20 mt-1 w-full rounded-lg border border-gray-300 bg-white shadow-lg">
                {sugestoes.map((p, i) => (
                  <button
                    key={p.id}
                    id={`produto-sugestao-${p.id}`}
                    role="option"
                    aria-selected={i === focoLista}
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
          <p className="mx-auto max-w-2xl text-center text-[11px] text-gray-500">
            Digite <b>quantidade*produto</b> para lançar várias unidades. Com a descrição vazia, Enter inicia o fluxo de desconto e pagamento.
            Use ↑ ↓, Home/End e Enter para escolher sem o mouse.
          </p>
          <h1 className="py-1 text-center text-2xl font-bold text-black">{linhaAtual?.nome || "Informe um produto para iniciar a venda"}</h1>
          {linhaAtual?.especificacao ? (
            <p className="text-center text-sm text-gray-500">{linhaAtual.especificacao}</p>
          ) : null}
        </div>

        {/* Grid responsivo: mobile empilha, desktop mantém 3 colunas */}
        <div className="grid min-h-0 flex-1 grid-cols-2 gap-2 md:grid-cols-12 md:gap-4">
          {/* Imagem do produto — oculta em telas pequenas */}
          <div className="hidden items-center justify-center overflow-hidden rounded-[2rem] bg-white p-4 shadow-md md:flex md:col-span-2">
            {linhaAtual?.imagem_url ? (
              <img src={linhaAtual.imagem_url} alt="" className="max-h-full max-w-full object-contain" />
            ) : (
              <div className="text-center text-sm text-gray-400">Sem imagem</div>
            )}
          </div>

          {/* Formulário de lançamento */}
          <div className="flex flex-col gap-2 md:col-span-3 md:gap-3">
            <DataBox label="Código" value={linhaAtual?.sku || "—"} />
            <div className="flex h-full flex-col justify-between rounded-xl bg-white p-3 shadow-md">
              <span className="text-sm font-bold text-gray-800">Quantidade</span>
              <input
                ref={qtdCentralRef}
                type="number"
                min={0}
                step="any"
                aria-label={linhaAtual ? `Quantidade de ${linhaAtual.nome}` : "Quantidade do item selecionado"}
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

          {/* Cupom fiscal (somente leitura) — ocupa o resto */}
          <div className="col-span-2 flex min-h-0 flex-col overflow-hidden rounded-[2rem] bg-white p-2 font-mono text-sm shadow-md md:col-span-7 md:p-4">
            <div className="grid grid-cols-[64px_1fr_52px_72px_76px_20px] gap-1 text-[10px] uppercase text-gray-500 sm:grid-cols-[80px_1fr_60px_84px_84px_24px] sm:text-[11px]">
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
                    role="group"
                    tabIndex={0}
                    aria-label={`Selecionar ${l.nome}, quantidade ${l.quantidade}`}
                    aria-current={linhaAtiva === i ? "true" : undefined}
                    onClick={() => ativarLinha(i)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        ativarLinha(i);
                      } else if (e.key === "Delete") {
                        e.preventDefault();
                        removerLinha(i);
                      } else if (e.key === "ArrowDown") {
                        e.preventDefault();
                        ativarLinha(Math.min(i + 1, linhas.length - 1));
                      } else if (e.key === "ArrowUp") {
                        e.preventDefault();
                        ativarLinha(Math.max(i - 1, 0));
                      }
                    }}
                    className={`grid cursor-pointer grid-cols-[64px_1fr_52px_72px_76px_20px] items-center gap-1 rounded border-b border-gray-100 py-1.5 outline-none focus-visible:ring-2 focus-visible:ring-orange-400 sm:grid-cols-[80px_1fr_60px_84px_84px_24px] ${linhaAtiva === i ? "bg-orange-100" : "hover:bg-orange-50"}`}
                  >
                    <span className="truncate text-xs">{l.sku || "#" + (i + 1)}</span>
                    <span className="truncate">{[l.nome, l.especificacao].filter(Boolean).join(" · ")}</span>
                    <span className="text-right text-xs">{l.quantidade}</span>
                    <span className="hidden text-right text-xs sm:block">{fmtMoney(l.preco_unitario)}</span>
                    <span className="text-right font-semibold">{fmtMoney(l.subtotal)}</span>
                    <button
                      type="button"
                      aria-label={`Remover ${l.nome}`}
                      title="Remover item (Delete)"
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
            className="w-20 rounded border border-gray-300 px-2 py-1 text-sm sm:w-24"
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
            className="w-40 rounded border border-gray-300 px-2 py-1 text-sm sm:w-44"
          >
            <option value="">Selecione</option>
            {condicoesVisiveis.map((cd) => (
              <option key={cd.id} value={cd.id}>
                {cd.nome}
              </option>
            ))}
          </select>
          <span className="font-semibold text-gray-600">Observação</span>
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
            aria-label="Observação do orçamento"
            placeholder="Observação (opcional)"
            className="min-w-40 flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
          />
        </div>

        {/* Totais */}
        <div className="grid flex-shrink-0 grid-cols-3 gap-2 sm:h-24 sm:gap-4">
          <div className="flex items-center justify-center rounded-xl bg-white p-1 shadow-md sm:p-4">
            <span className="truncate text-lg font-bold tracking-widest text-black sm:text-5xl">{editandoId ? "ALTERAÇÃO" : "VENDA"}</span>
          </div>
          <div>
            <DataBox label="Volumes" value={String(linhas.reduce((s, l) => s + l.quantidade, 0))} />
          </div>
          <div>
            <DataBox label="Total da Venda" value={fmtMoney(c.total)} largeValue valueColor="text-red-600" />
          </div>
        </div>
      </main>

      {/* ── Rodapé: atalhos + ações ───────────────────────── */}
      <footer className="safe-bottom flex flex-shrink-0 flex-wrap items-center gap-1.5 border-t border-gray-400 bg-[#f0f0f0] px-2 py-2 sm:gap-2 sm:px-4">
        <span className="hidden text-[11px] text-gray-500 lg:inline">Ctrl+K pesquisa · ↑↓ navega · Enter seleciona · Delete remove</span>
        <Button size="sm" variant="ghost" onClick={() => void acaoAtalho(5)} aria-keyshortcuts="F5" title="F5">
          Limpar
        </Button>
        <Button size="sm" variant="ghost" onClick={() => void acaoAtalho(6)} aria-keyshortcuts="F6" title="F6">
          Cliente
        </Button>
        <Button size="sm" variant="ghost" onClick={() => void acaoAtalho(7)} disabled={!linhas.length} aria-keyshortcuts="F7" title="F7" className="hidden sm:inline-flex">
          Impressora
        </Button>
        <Button size="sm" variant="ghost" onClick={() => void acaoAtalho(8)} aria-keyshortcuts="F8" title="F8">
          Localizar
        </Button>
        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <Button size="sm" variant="ghost" onClick={() => void acaoAtalho(2)} disabled={!linhas.length} aria-keyshortcuts="F2" title="F2" className="hidden sm:inline-flex">
            Visualizar
          </Button>
          <Button size="sm" variant="outline" onClick={() => void acaoAtalho(3)} disabled={!linhas.length || salvando} aria-keyshortcuts="F3" title="F3">
            Salvar
          </Button>
          <Button ref={salvarRef} variant="primary" onClick={() => void acaoAtalho(1)} disabled={!linhas.length || salvando} aria-keyshortcuts="F1" title="F1">
            Finalizar
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

