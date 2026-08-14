// pages/recebimentos.tsx — Caixa (ECF): recebimento de vendas de balcão.
// Tela orientada a teclado: ↑/↓ navegam, ENTER abre, M abre o menu de ações.

import { useEffect, useRef, useState } from "react";
import { api, type OrcamentoDetalhe, type OrcamentoLista } from "../api/client";
import { fmtDate, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Field, Input, Loading, Modal, PageHeader, Select, Table, TBody, THead } from "../ui/ui";
import { FORMAS_PAGAMENTO } from "./recebimento";

function parseNum(v: string): number {
  const n = parseFloat(String(v || "").replace(",", "."));
  return isNaN(n) ? 0 : n;
}

function fmtNum2(n: number): string {
  return n.toFixed(2).replace(".", ",");
}

const STATUS_LABELS: Record<string, string> = {
  rascunho: "Rascunho",
  ativo: "Ativo",
  em_analise: "Em análise",
  liberado: "Liberado",
  faturado: "Faturado",
  recebido: "Recebido",
  cancelado: "Cancelado",
};

export default function Recebimentos() {
  const [pedidos, setPedidos] = useState<OrcamentoLista[]>([]);
  const [focoId, setFocoId] = useState<number | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [saldo, setSaldo] = useState(0);
  const [modalPedido, setModalPedido] = useState<OrcamentoDetalhe | null>(null);
  const [menuAberto, setMenuAberto] = useState(false);
  const [editarDe, setEditarDe] = useState<OrcamentoLista | null>(null);

  const focoIdRef = useRef<number | null>(null);
  const rowRefs = useRef<Record<number, HTMLTableRowElement | null>>({});

  const carregar = async (silent = false) => {
    if (!silent) setCarregando(true);
    try {
      const [p, s] = await Promise.all([api.listarOrcamentos("faturado"), api.saldoCaixa()]);
      setPedidos(p);
      setSaldo(s.saldo);
      const atual = focoIdRef.current;
      if (atual != null && p.some((o) => o.id === atual)) {
        setFocoId(atual);
      } else {
        const primeiro = p[0]?.id ?? null;
        setFocoId(primeiro);
        focoIdRef.current = primeiro;
      }
    } catch {
      /* silêncio no auto-refresh */
    } finally {
      if (!silent) setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  // Auto-refresh: atualiza a fila sem mexer no pedido em foco.
  useEffect(() => {
    const t = setInterval(() => void carregar(true), 5000);
    return () => clearInterval(t);
  }, []);

  const mover = (delta: number) => {
    const idx = pedidos.findIndex((o) => o.id === focoId);
    const alvo = Math.min(pedidos.length - 1, Math.max(0, (idx < 0 ? 0 : idx) + delta));
    const id = pedidos[alvo]?.id ?? null;
    setFocoId(id);
    focoIdRef.current = id;
    rowRefs.current[id]?.scrollIntoView({ block: "nearest" });
  };

  const abrirPedido = async (id: number | null) => {
    if (id == null) return;
    try {
      setModalPedido(await api.detalharOrcamento(id));
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  // Teclado global da tela (lista).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (modalPedido || menuAberto || editarDe) return;
      const k = e.key.toLowerCase();
      if (e.key === "ArrowDown") {
        e.preventDefault();
        mover(1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        mover(-1);
      } else if (e.key === "Enter") {
        e.preventDefault();
        void abrirPedido(focoId);
      } else if (k === "m") {
        e.preventDefault();
        setMenuAberto(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focoId, pedidos, modalPedido, menuAberto, editarDe]);

  const focado = pedidos.find((o) => o.id === focoId) ?? null;
  const totalPendente = pedidos.reduce((s, o) => s + o.total, 0);

  return (
    <div>
      <PageHeader title="Caixa (ECF)" subtitle="Vendas de balcão finalizadas aguardando recebimento — navegue pelo teclado." />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="rounded-lg border border-gray-200 bg-white px-5 py-3">
          <div className="text-xs font-medium uppercase text-gray-500">Saldo do caixa</div>
          <div className="text-2xl font-semibold text-gray-900">{fmtMoney(saldo)}</div>
        </div>
        <div className="rounded-lg border border-orange-200 bg-orange-50 px-5 py-3">
          <div className="text-xs font-medium uppercase text-orange-700">Pendente</div>
          <div className="text-2xl font-semibold text-orange-600">{fmtMoney(totalPendente)}</div>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2 rounded-md bg-gray-100 px-3 py-2 text-xs text-gray-600">
          <span><kbd className="rounded bg-white px-1.5 py-0.5 shadow-sm">↑</kbd> <kbd className="rounded bg-white px-1.5 py-0.5 shadow-sm">↓</kbd> navegar</span>
          <span><kbd className="rounded bg-white px-1.5 py-0.5 shadow-sm">ENTER</kbd> abrir</span>
          <span><kbd className="rounded bg-white px-1.5 py-0.5 shadow-sm">M</kbd> menu</span>
          <span className="text-gray-400">· auto-atualiza a cada 5s</span>
        </div>
      </div>

      {carregando ? (
        <Loading />
      ) : pedidos.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhuma venda aguardando recebimento.
        </div>
      ) : (
        <Table>
          <THead cols={["Nº", "Cliente", "Total", "Vendedor", "Itens", ""]} />
          <TBody>
            {pedidos.map((o) => {
              const ativo = o.id === focoId;
              return (
                <tr
                  key={o.id}
                  ref={(el) => {
                    rowRefs.current[o.id] = el;
                  }}
                  onClick={() => {
                    setFocoId(o.id);
                    focoIdRef.current = o.id;
                    void abrirPedido(o.id);
                  }}
                  className={`cursor-pointer ${ativo ? "bg-orange-100" : o.id % 2 === 0 ? "bg-white" : "bg-gray-50"}`}
                >
                  <Cell className="font-mono font-semibold">{o.numero}</Cell>
                  <Cell>{o.cliente || "—"}</Cell>
                  <Cell className="font-semibold text-orange-600">{fmtMoney(o.total)}</Cell>
                  <Cell>{o.usuario_nome || "—"}</Cell>
                  <Cell>{o.n_itens}</Cell>
                  <Cell>
                    <div className="flex justify-end">
                      <Button size="sm" variant="primary" onClick={(e) => { e.stopPropagation(); void abrirPedido(o.id); }}>
                        Receber
                      </Button>
                    </div>
                  </Cell>
                </tr>
              );
            })}
          </TBody>
        </Table>
      )}

      {focado && menuAberto && (
        <MenuAcoes
          pedido={focado}
          onClose={() => setMenuAberto(false)}
          onDevolver={async () => {
            setMenuAberto(false);
            if (!window.confirm(`Devolver a venda ${focado.numero}? O estoque será revertido.`)) return;
            try {
              const r = await api.devolverOrcamento(focado.id);
              toast(`Venda devolvida (${r.itens_devolvidos} item(ns) estornados)`, "success");
              void carregar(true);
            } catch (e) {
              toast("Erro: " + (e as Error).message, "error");
            }
          }}
          onEditar={() => {
            setMenuAberto(false);
            setEditarDe(focado);
          }}
          onCancelar={async () => {
            setMenuAberto(false);
            if (!window.confirm(`Cancelar a venda ${focado.numero}?`)) return;
            try {
              await api.cancelarOrcamento(focado.id);
              toast("Venda cancelada", "success");
              void carregar(true);
            } catch (e) {
              toast("Erro: " + (e as Error).message, "error");
            }
          }}
        />
      )}

      {modalPedido && (
        <ModalPedidoCaixa
          d={modalPedido}
          onVoltar={() => setModalPedido(null)}
          onRecebido={() => {
            setModalPedido(null);
            void carregar(true);
          }}
        />
      )}

      {editarDe && (
        <ModalEditarStatus
          d={editarDe}
          onClose={() => setEditarDe(null)}
          onSalvo={() => {
            setEditarDe(null);
            void carregar(true);
          }}
        />
      )}
    </div>
  );
}

function MenuAcoes({
  pedido,
  onClose,
  onDevolver,
  onEditar,
  onCancelar,
}: {
  pedido: OrcamentoLista;
  onClose: () => void;
  onDevolver: () => void;
  onEditar: () => void;
  onCancelar: () => void;
}) {
  const opcoes = [
    { label: "DEVOLVER", fn: onDevolver, tone: "text-amber-700" },
    { label: "EDITAR", fn: onEditar, tone: "text-gray-900" },
    { label: "CANCELAR", fn: onCancelar, tone: "text-red-600" },
  ];
  const [sel, setSel] = useState(0);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSel((s) => (s + 1) % opcoes.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSel((s) => (s - 1 + opcoes.length) % opcoes.length);
      } else if (e.key === "Enter") {
        e.preventDefault();
        opcoes[sel].fn();
      } else if (e.key === "Escape" || e.key.toLowerCase() === "m") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sel]);

  return (
    <Modal open onClose={onClose} title={`Ações — ${pedido.numero}`} footer={<Button onClick={onClose}>Fechar (ESC)</Button>}>
      <p className="mb-3 text-sm text-gray-500">
        {pedido.cliente || "—"} · {fmtMoney(pedido.total)}
      </p>
      <div className="space-y-1">
        {opcoes.map((o, i) => (
          <button
            key={o.label}
            onClick={o.fn}
            onMouseEnter={() => setSel(i)}
            className={`block w-full rounded-md px-3 py-2.5 text-left text-sm font-semibold ${o.tone} ${i === sel ? "bg-orange-100" : "hover:bg-gray-50"}`}
          >
            {i === sel ? "▸ " : ""}
            {o.label}
          </button>
        ))}
      </div>
    </Modal>
  );
}

function ModalEditarStatus({
  d,
  onClose,
  onSalvo,
}: {
  d: OrcamentoLista;
  onClose: () => void;
  onSalvo: () => void;
}) {
  const [status, setStatus] = useState<string>(d.status);

  const salvar = async () => {
    try {
      await api.atualizarOrcamento(d.id, { status });
      toast("Status atualizado", "success");
      onSalvo();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={`Editar status — ${d.numero}`}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void salvar()}>
            Salvar
          </Button>
        </>
      }
    >
      <Field label="Status">
        <Select value={status} onChange={(e) => setStatus(e.target.value)}>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </Select>
      </Field>
    </Modal>
  );
}

function ModalPedidoCaixa({
  d,
  onVoltar,
  onRecebido,
}: {
  d: OrcamentoDetalhe;
  onVoltar: () => void;
  onRecebido: () => void;
}) {
  const total = d.total;
  const [forma, setForma] = useState("dinheiro");
  const [valor, setValor] = useState("");
  const [pagamentos, setPagamentos] = useState<{ forma: string; valor: number }[]>([]);
  const [enviando, setEnviando] = useState(false);
  const valorRef = useRef<HTMLInputElement>(null);

  const pago = pagamentos.reduce((s, p) => s + p.valor, 0);
  const falta = Math.max(0, total - pago);
  const troco = Math.max(0, pago - total);

  const adicionar = () => {
    const v = parseNum(valor);
    if (v <= 0) return;
    setPagamentos((arr) => [...arr, { forma, valor: v }]);
    setValor("");
    valorRef.current?.focus();
  };

  const remover = (i: number) => setPagamentos((arr) => arr.filter((_, j) => j !== i));

  const confirmar = async () => {
    if (pagamentos.length === 0) {
      toast("Adicione ao menos um pagamento", "error");
      return;
    }
    setEnviando(true);
    try {
      const res = await api.receberOrcamento(d.id, {
        pagamentos: pagamentos.map((p) => ({ forma_pagamento: p.forma, valor: p.valor })),
      });
      if (res.recebido) toast(res.troco > 0 ? `Recebido · troco ${fmtMoney(res.troco)}` : "Recebimento registrado", "success");
      else toast(`Recebimento parcial de ${fmtMoney(res.valor_recebido)}`, "success");
      onRecebido();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
      setEnviando(false);
    }
  };

  return (
    <Modal
      open
      onClose={onVoltar}
      title={`Pedido ${d.numero}`}
      wide
      footer={
        <>
          <Button variant="ghost" onClick={onVoltar}>
            ← Voltar para Caixa (ECF)
          </Button>
          <Button variant="primary" onClick={() => void confirmar()} disabled={enviando || pagamentos.length === 0}>
            {enviando ? "Registrando…" : "Confirmar recebimento"}
          </Button>
        </>
      }
    >
      <p className="mb-3 text-sm text-gray-500">
        {d.cliente || "Sem cliente"}
        {d.contato ? " · " + d.contato : ""} · Vendedor: {d.usuario_nome || "—"} · {fmtDate(d.criado_em)}
      </p>

      <Table>
        <THead cols={["Produto", "Qtd.", "Preço", "Subtotal"]} />
        <TBody>
          {d.itens.map((i, idx) => (
            <tr key={idx}>
              <Cell>
                {i.nome}
                {i.sku ? <div className="font-mono text-xs text-gray-400">{i.sku}</div> : null}
              </Cell>
              <Cell>{i.quantidade}</Cell>
              <Cell>{fmtMoney(i.preco_unitario)}</Cell>
              <Cell className="font-medium">{fmtMoney(i.subtotal || 0)}</Cell>
            </tr>
          ))}
        </TBody>
      </Table>

      <div className="mt-4 flex flex-wrap justify-end gap-4 text-sm">
        <div>
          Subtotal: <strong>{fmtMoney(d.subtotal)}</strong>
        </div>
        <div>
          Desconto: <strong>{fmtMoney(d.desconto)}</strong>
        </div>
        <div>
          Total: <strong className="text-orange-600">{fmtMoney(d.total)}</strong>
        </div>
      </div>

      <div className="mt-5 rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-900">Recebimento</h4>
          <div className="text-sm">
            Pago: <strong className="text-emerald-600">{fmtMoney(pago)}</strong> ·{" "}
            Falta: <strong className={falta > 0.01 ? "text-amber-600" : "text-emerald-600"}>{fmtMoney(falta)}</strong>
            {troco > 0 ? ` · Troco: ${fmtMoney(troco)}` : ""}
          </div>
        </div>

        <div className="mb-3 flex flex-wrap gap-1.5">
          {FORMAS_PAGAMENTO.map((f) => (
            <button
              key={f.valor}
              onClick={() => setForma(f.valor)}
              className={`rounded-full border px-3 py-1 text-xs font-medium ${
                forma === f.valor ? "border-orange-500 bg-orange-500 text-white" : "border-gray-300 bg-white text-gray-700 hover:bg-gray-100"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          <Input
            ref={valorRef}
            inputMode="decimal"
            placeholder={fmtMoney(falta)}
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                adicionar();
              }
            }}
            className="w-40"
          />
          <Button onClick={adicionar}>Adicionar</Button>
          <Button size="sm" variant="ghost" onClick={() => { setValor(fmtNum2(falta)); }}>
            Restante
          </Button>
        </div>

        {pagamentos.length > 0 && (
          <div className="mt-3 space-y-1">
            {pagamentos.map((p, i) => (
              <div key={i} className="flex items-center gap-2 rounded-md bg-white px-3 py-1.5 text-sm">
                <Badge tone="gray">{FORMAS_PAGAMENTO.find((f) => f.valor === p.forma)?.label || p.forma}</Badge>
                <span className="flex-1 font-medium">{fmtMoney(p.valor)}</span>
                <button className="text-gray-400 hover:text-red-600" onClick={() => remover(i)}>
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}
