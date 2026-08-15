// pages/pdv.tsx — PDV de orçamentos (React + Tailwind).

import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type Cliente,
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
import { ModalRecebimento } from "./recebimento";

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

export default function Pdv() {
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

  const [contato, setContato] = useState("");
  const [validade, setValidade] = useState(String(VALIDADE_PADRAO));
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
    { id: number; descontoPct?: number; limitePct?: number } | null
  >(null);
  const [modalRecebimento, setModalRecebimento] = useState<{ id: number; numero: string; total: number } | null>(null);
  const [modalLocalizar, setModalLocalizar] = useState(false);

  const buscaRef = useRef<HTMLInputElement>(null);
  const contatoRef = useRef<HTMLInputElement>(null);
  const validadeRef = useRef<HTMLInputElement>(null);
  const descontoRef = useRef<HTMLInputElement>(null);
  const condRef = useRef<HTMLSelectElement>(null);
  const obsRef = useRef<HTMLInputElement>(null);
  const salvarRef = useRef<HTMLButtonElement>(null);
  const qtdCentralRef = useRef<HTMLInputElement>(null);
  const buscaTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const [linhaAtiva, setLinhaAtiva] = useState<number | null>(null);
  const recebimentoPendenteRef = useRef<{ id: number; numero: string; total: number } | null>(null);
  const [hora, setHora] = useState(() => new Date().toLocaleTimeString("pt-BR"));

  useEffect(() => {
    const t = setInterval(() => setHora(new Date().toLocaleTimeString("pt-BR")), 1000);
    return () => clearInterval(t);
  }, []);

  const c = useMemo(() => calculosPdv(linhas, descModo, desconto), [linhas, descModo, desconto]);

  useEffect(() => {
    void api.listarCondicoes().then(setCondicoes).catch(() => {});
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
    if (!contato && cli.whatsapp) setContato(cli.whatsapp);
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

  const finalizarOrcamento = async (id: number, numero: string, total: number): Promise<boolean> => {
    try {
      await api.atualizarOrcamento(id, { status: "faturado" });
      setModalRecebimento({ id, numero, total });
      return true;
    } catch (e) {
      const err = e as Error & { code?: string; details?: Record<string, unknown> };
      if (err.code === "desconto_exige_autorizacao") {
        setModalAutorizar({
          id,
          descontoPct: err.details?.desconto_pct as number | undefined,
          limitePct: err.details?.limite_pct as number | undefined,
        });
        recebimentoPendenteRef.current = { id, numero, total };
        return false;
      }
      toast("Erro ao finalizar: " + err.message, "error");
      return false;
    }
  };

  const salvar = async (finalizado = false, imprimir = true): Promise<{ id: number; numero: string } | null> => {
    if (!linhas.length) {
      toast("Adicione ao menos um item", "error");
      return null;
    }
    const itens: OrcamentoItemPayload[] = linhas.map((l) => ({
      produto_id: l.produto_id,
      nome: l.nome,
      sku: l.sku,
      marca: l.marca,
      especificacao: l.especificacao,
      quantidade: l.quantidade,
      preco_unitario: l.preco_unitario,
      desconto_percentual: l.desconto_percentual,
    }));
    setSalvando(true);
    try {
      const condId = parseInt(condicaoId, 10) || undefined;
      let res: { id: number; numero: string };
      if (editandoId != null) {
        const patch: Record<string, unknown> = {
          cliente: cliente.trim(),
          contato: contato.trim(),
          validade_dias: parseInt(validade, 10) || VALIDADE_PADRAO,
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
          contato: contato.trim(),
          validade_dias: parseInt(validade, 10) || VALIDADE_PADRAO,
          observacoes: obs.trim(),
          desconto: c.descontoGeral,
          itens,
          condicao_pagamento_id: condId,
          cliente_id: clienteId ?? undefined,
        });
      }
      sessionStorage.setItem("pdv_cliente", cliente.trim());
      sessionStorage.setItem("pdv_cliente_id", clienteId != null ? String(clienteId) : String(CLIENTE_PADRAO.id));

      if (finalizado) {
        const ok = await finalizarOrcamento(res.id, res.numero, c.total);
        toast(ok ? `${res.numero} finalizado` : `${res.numero} salvo — finalização requer autorização de desconto`, ok ? "success" : "error");
      } else {
        toast(editandoId == null ? `${res.numero} salvo` : `${res.numero} atualizado`, "success");
      }

      if (imprimir) {
        void api.imprimirOrcamento(res.id).catch(() => toast("Orçamento salvo, mas a impressão falhou", "error"));
      }

      setEditandoId(null);
      setEditandoNumero("");
      setLinhas([]);
      setDesconto("");
      setObs("");
      buscaRef.current?.focus();
      return res;
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
      return null;
    } finally {
      setSalvando(false);
    }
  };

  const visualizarImprimir = async () => {
    if (!linhas.length) {
      toast("Adicione itens antes de visualizar", "error");
      return;
    }
    const res = await salvar(false, false);
    if (res) window.open(`/orcamentos/venda/${res.id}/imprimir`, "_blank");
  };

  const limpar = () => {
    if (linhas.length && !window.confirm("Limpar todos os itens?")) return;
    setLinhas([]);
    setLinhaAtiva(null);
    setDesconto("");
    setObs("");
    setEditandoId(null);
    setEditandoNumero("");
    buscaRef.current?.focus();
  };

  const acaoAtalho = async (f: number) => {
    switch (f) {
      case 1:
        if (linhas.length) await salvar(false, false);
        break;
      case 2:
        await visualizarImprimir();
        break;
      case 3:
        if (linhas.length) await salvar(true, false);
        else toast("Adicione ao menos um item", "error");
        break;
      case 5:
        limpar();
        break;
      case 6:
        setModalBuscaCliente(true);
        break;
      case 7:
        if (linhas.length) await salvar(false, true);
        else toast("Adicione itens antes de imprimir", "error");
        break;
      case 8:
        setModalLocalizar(true);
        break;
    }
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const m = e.key?.toUpperCase().match(/^F([1-9])$/);
      if (!m) return;
      e.preventDefault();
      e.stopPropagation();
      void acaoAtalho(Number(m[1]));
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linhas, cliente, clienteId, contato, validade, obs, desconto, descModo, condicaoId, editandoId]);

  const onDescontoChange = (raw: string) => {
    let v = raw;
    if (/%/.test(v)) {
      setDescModo("pct");
      v = v.replace(/%/g, "").trim();
    }
    setDesconto(v);
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
    setContato(d.contato || "");
    setValidade(String(d.validade_dias || VALIDADE_PADRAO));
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
            {clienteId != null ? `${clienteId} · ${cliente}` : cliente}
          </button>
          <span className="text-[10px] text-gray-500">F6</span>
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
                      <span className={`block text-xs ${i === focoLista ? "text-orange-100" : "text-gray-400"}`}>{[p.sku, p.brand, p.unidade_venda].filter(Boolean).join(" · ")}</span>
                    </span>
                    <span className="font-semibold">{fmtMoney(p.price)}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <h1 className="py-1 text-center text-2xl font-bold text-black">{linhaAtual?.nome || "Informe um produto para iniciar a venda"}</h1>
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
                    <span className="truncate">{l.nome}</span>
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

        {/* Lançamento (contato / validade / desconto / condição / obs) */}
        <div className="flex flex-shrink-0 flex-wrap items-center gap-2 rounded-xl bg-white/90 px-3 py-2 text-xs">
          <span className="font-semibold text-gray-600">Contato</span>
          <input
            ref={contatoRef}
            value={contato}
            onChange={(e) => setContato(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                validadeRef.current?.focus();
              }
            }}
            className="w-40 rounded border border-gray-300 px-2 py-1 text-sm"
            placeholder="WhatsApp / e-mail"
          />
          <span className="font-semibold text-gray-600">Validade</span>
          <input
            ref={validadeRef}
            type="number"
            min={1}
            value={validade}
            onChange={(e) => setValidade(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                buscaRef.current?.focus();
              }
            }}
            className="w-20 rounded border border-gray-300 px-2 py-1 text-sm"
          />
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
            Finalizar (F3)
          </Button>
          <Button ref={salvarRef} variant="primary" onClick={() => void acaoAtalho(1)} disabled={!linhas.length || salvando}>
            Salvar orçamento (F1)
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
      {modalAutorizar !== null && (
        <ModalAutorizar
          id={modalAutorizar.id}
          descontoPct={modalAutorizar.descontoPct}
          limitePct={modalAutorizar.limitePct}
          onClose={() => setModalAutorizar(null)}
          onAutorizado={() => {
            const pend = recebimentoPendenteRef.current;
            recebimentoPendenteRef.current = null;
            if (pend) setModalRecebimento(pend);
          }}
        />
      )}
      {modalRecebimento !== null && (
        <ModalRecebimento
          dados={modalRecebimento}
          onClose={() => setModalRecebimento(null)}
          onRecebido={() => setModalRecebimento(null)}
          imprimir
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

function ModalAutorizar({
  id,
  descontoPct,
  limitePct,
  onClose,
  onAutorizado,
}: {
  id: number;
  descontoPct?: number;
  limitePct?: number;
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
      await api.autorizarDescontoOrcamento(id, { login: login.trim(), senha });
      await api.atualizarOrcamento(id, { status: "faturado" });
      toast("Desconto autorizado e venda finalizada", "success");
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
            {autorizando ? "Autorizando…" : "Autorizar e finalizar"}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-gray-500">
        {descontoPct != null && limitePct != null ? (
          <>
            O desconto aplicado (<b>{descontoPct.toFixed(1)}%</b>) está acima da alçada do
            vendedor (<b>{limitePct.toFixed(1)}%</b>). Informe as credenciais de um gerente
            para autorizar e finalizar.
          </>
        ) : (
          "O desconto aplicado está acima da alçada do vendedor. Informe as credenciais do gerente para autorizar e finalizar."
        )}
      </p>
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
