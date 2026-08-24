// pages/caixa.tsx — Caixa (ECF): recebimento de vendas de balcão.
// Layout de PDV (frente de caixa). O pedido é selecionado via "Localizar
// pedido (F8)" — mesmo padrão do modal de localização da pré-venda.

import { useEffect, useRef, useState } from "react";
import { api, type DocumentoFiscal, type OrcamentoDetalhe, type OrcamentoLista } from "../api/client";
import { fmtDate, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { usuarioCorrente } from "./login";
import { Badge, Button, Field, Input, Modal, Select } from "../ui/ui";
import { SearchModal } from "../ui/search-modal";

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
  finalizado: "Finalizado",
  recebido: "Recebido",
  cancelado: "Cancelado",
  devolvido: "Devolvido",
};

// Ordem/atalhos das formas de pagamento no caixa (ECF).
const FORMAS_CAIXA: { valor: string; label: string; tecla: string }[] = [
  { valor: "dinheiro", label: "Dinheiro", tecla: "F1" },
  { valor: "pix", label: "PIX", tecla: "F2" },
  { valor: "cartao_credito", label: "Cartão crédito", tecla: "F3" },
  { valor: "cartao_debito", label: "Cartão débito", tecla: "F4" },
  { valor: "cheque", label: "Cheque", tecla: "F5" },
  { valor: "convenio", label: "Convênio", tecla: "F6" },
  { valor: "boleto", label: "Boleto", tecla: "F7" },
];

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
    <div className="flex h-full min-w-0 flex-col justify-between rounded-xl bg-white p-2 shadow-md sm:p-3">
      <span className="truncate text-xs font-bold text-gray-800 sm:text-sm">{label}</span>
      <div className={`mt-1 min-w-0 truncate text-right font-bold ${largeValue ? "text-2xl sm:text-4xl" : "text-lg sm:text-2xl"} ${valueColor}`}>{value ?? ""}</div>
    </div>
  );
}

export default function Caixa() {
  const [selecionado, setSelecionado] = useState<OrcamentoDetalhe | null>(null);
  const [modalLocalizar, setModalLocalizar] = useState(false);
  const [modalRecebimento, setModalRecebimento] = useState<OrcamentoDetalhe | null>(null);
  const [menuAberto, setMenuAberto] = useState(false);
  const [editarDe, setEditarDe] = useState<OrcamentoLista | null>(null);
  const [modalMovimento, setModalMovimento] = useState<"sangria" | "suprimento" | null>(null);

  const [hora, setHora] = useState(() => new Date().toLocaleTimeString("pt-BR"));

  useEffect(() => {
    const t = setInterval(() => setHora(new Date().toLocaleTimeString("pt-BR")), 1000);
    return () => clearInterval(t);
  }, []);

  const selecionarPedido = async (id: number) => {
    try {
      setSelecionado(await api.detalharOrcamento(id));
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const receber = () => {
    if (selecionado) setModalRecebimento(selecionado);
  };

  // Teclado global da tela: ENTER/F3 recebe (padrão), F8 localiza, M ações, S/R sangria/reforço.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (modalLocalizar || modalRecebimento || menuAberto || editarDe || modalMovimento) return;
      const k = e.key.toLowerCase();
      if (e.key === "F8") {
        e.preventDefault();
        setModalLocalizar(true);
      } else if (e.key === "F3" || e.key === "Enter") {
        e.preventDefault();
        receber();
      } else if (k === "m") {
        e.preventDefault();
        if (selecionado) setMenuAberto(true);
      } else if (k === "s") {
        e.preventDefault();
        setModalMovimento("sangria");
      } else if (k === "r") {
        e.preventDefault();
        setModalMovimento("suprimento");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modalLocalizar, modalRecebimento, menuAberto, editarDe, modalMovimento, selecionado]);

  return (
    <div className="flex min-h-[560px] flex-col">
      {/* ── Cabeçalho do sistema ─────────────────────────── */}
      <header className="flex flex-shrink-0 flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-gray-300 bg-[#e4e4e4] px-2 py-1.5 text-xs text-gray-800 sm:px-4 sm:text-sm">
        <div>
          <strong>Operador:</strong> <span className="hidden sm:inline">{usuarioCorrente()?.nome ?? "—"}</span>
          <span className="sm:hidden">{usuarioCorrente()?.nome?.split(" ")[0] ?? "—"}</span>
        </div>
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <span>Pedido:</span>
          <span className="max-w-[45vw] truncate rounded border border-gray-400 bg-white px-2 py-0.5 text-sm font-medium text-gray-800 sm:max-w-md">
            {selecionado ? `${selecionado.numero} · ${selecionado.cliente || "—"}` : "Nenhum pedido selecionado"}
          </span>
          <span className="hidden text-[10px] text-gray-500 sm:inline">F8 localizar</span>
        </div>
        <div className="hidden md:block">Vendedor: {selecionado?.usuario_nome ?? "—"}</div>
        <div className="hidden md:block">Horário: {hora}</div>
      </header>

      {/* ── Área principal ────────────────────────────────── */}
      <main className="flex min-h-[480px] flex-1 flex-col gap-2 overflow-hidden bg-[#6a84a6] p-2 sm:gap-3 sm:p-4">
        {/* Painel de seleção do pedido */}
        <div className="flex flex-shrink-0 flex-wrap items-center justify-between gap-2 rounded-xl bg-white p-3 shadow-md">
          <div className="min-w-0">
            <span className="text-sm font-bold text-gray-800">Pedido</span>
            <div className="mt-0.5 text-xs text-gray-500">
              Selecione uma venda finalizada para receber o pagamento.
            </div>
          </div>
          <Button variant="outline" onClick={() => setModalLocalizar(true)}>
            Localizar (F8)
          </Button>
        </div>

        {/* Grid responsivo: mobile empilha, desktop mantém 3 colunas */}
        <div className="grid min-h-0 flex-1 grid-cols-2 gap-2 md:grid-cols-12 md:gap-4">
          {/* Resumo do pedido selecionado */}
          <div className="flex flex-col gap-2 md:col-span-3 md:gap-3">
            <DataBox label="Nº Pedido" value={selecionado?.numero || "—"} />
            <DataBox label="Cliente" value={selecionado?.cliente || "—"} />
            <DataBox label="Vendedor" value={selecionado?.usuario_nome || "—"} />
            <DataBox label="Itens" value={String(selecionado?.n_itens ?? 0)} />
          </div>

          {/* Dados do pedido */}
          <div className="flex flex-col gap-2 md:col-span-3 md:gap-3">
            <DataBox label="Data" value={selecionado ? fmtDate(selecionado.criado_em) : "—"} />
            <DataBox label="Subtotal" value={fmtMoney(selecionado?.subtotal ?? 0)} />
            <DataBox label="Desconto" value={fmtMoney(selecionado?.desconto ?? 0)} />
            <DataBox label="Status" value={selecionado ? STATUS_LABELS[selecionado.status] ?? selecionado.status : "—"} />
          </div>

          {/* Cupom fiscal (somente leitura) — ocupa o resto */}
          <div className="col-span-2 flex min-h-0 flex-col overflow-hidden rounded-[2.5rem] bg-white p-2 font-mono text-sm shadow-md md:col-span-6 md:p-4">
            <div className="grid grid-cols-[1fr_52px_68px_72px] gap-1 text-[10px] uppercase text-gray-500 sm:grid-cols-[1fr_60px_84px_84px] sm:text-[11px]">
              <span>Descrição</span>
              <span className="text-right">Qtde</span>
              <span className="text-right">Vl.Unit</span>
              <span className="text-right">Vl.Item</span>
            </div>
            <div className="my-2 border-b-2 border-dashed border-gray-300" />
            <div className="min-h-0 flex-1 overflow-auto">
              {!selecionado ? (
                <p className="py-8 text-center text-gray-400">Selecione um pedido para visualizar os itens</p>
              ) : selecionado.itens.length === 0 ? (
                <p className="py-8 text-center text-gray-400">Nenhum item</p>
              ) : (
                selecionado.itens.map((it, i) => (
                  <div
                    key={i}
                    className="grid grid-cols-[1fr_52px_68px_72px] items-center gap-1 border-b border-gray-100 py-1.5 sm:grid-cols-[1fr_60px_84px_84px]"
                  >
                    <span className="truncate">{it.nome}</span>
                    <span className="text-right text-xs">{it.quantidade}</span>
                    <span className="text-right text-xs">{fmtMoney(it.preco_unitario)}</span>
                    <span className="text-right font-semibold">{fmtMoney(it.subtotal || 0)}</span>
                  </div>
                ))
              )}
            </div>
            <div className="mt-2 border-t-2 border-dashed border-gray-300 pt-2">
              <div className="flex justify-between text-xs text-gray-500">
                <span>Subtotal</span>
                <span>{fmtMoney(selecionado?.subtotal ?? 0)}</span>
              </div>
              {selecionado && selecionado.desconto > 0 && (
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Desconto</span>
                  <span>{fmtMoney(selecionado.desconto)}</span>
                </div>
              )}
              <div className="flex justify-between text-base font-bold">
                <span>TOTAL</span>
                <span>{fmtMoney(selecionado?.total ?? 0)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Totais */}
        <div className="grid flex-shrink-0 grid-cols-3 gap-2 sm:h-24 sm:gap-4">
          <div className="flex items-center justify-center rounded-xl bg-white p-1 shadow-md sm:p-4">
            <span className="truncate text-lg font-bold tracking-widest text-black sm:text-5xl">{selecionado ? selecionado.numero : "CAIXA"}</span>
          </div>
          <div>
            <DataBox label="Itens" value={String(selecionado?.n_itens ?? 0)} />
          </div>
          <div>
            <DataBox label="Total a Receber" value={fmtMoney(selecionado?.total ?? 0)} largeValue valueColor="text-red-600" />
          </div>
        </div>
      </main>

      {/* ── Rodapé: atalhos + ações ───────────────────────── */}
      <footer className="safe-bottom flex flex-shrink-0 flex-wrap items-center gap-1.5 border-t border-gray-400 bg-[#f0f0f0] px-2 py-2 sm:gap-2 sm:px-4">
        <Button size="sm" variant="ghost" onClick={() => setModalLocalizar(true)}>
          Localizar
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setMenuAberto(true)} disabled={!selecionado}>
          Ações
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setModalMovimento("sangria")}>
          Sangria
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setModalMovimento("suprimento")} className="hidden sm:inline-flex">
          Reforço
        </Button>
        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <Button variant="primary" onClick={receber} disabled={!selecionado}>
            Receber (F3)
          </Button>
        </div>
      </footer>

      {modalLocalizar && (
        <ModalLocalizarPedido
          onClose={() => setModalLocalizar(false)}
          onSelecionar={(id) => {
            setModalLocalizar(false);
            void selecionarPedido(id);
          }}
        />
      )}

      {selecionado && menuAberto && (
        <MenuAcoes
          pedido={selecionado}
          onClose={() => setMenuAberto(false)}
          onDevolver={async () => {
            setMenuAberto(false);
            if (!window.confirm(`Devolver a venda ${selecionado.numero}? O estoque será revertido.`)) return;
            try {
              const r = await api.devolverOrcamento(selecionado.id);
              toast(`Venda devolvida (${r.itens_devolvidos} item(ns) estornados)`, "success");
              setSelecionado(null);
            } catch (e) {
              toast("Erro: " + (e as Error).message, "error");
            }
          }}
          onEditar={() => {
            setMenuAberto(false);
            setEditarDe(selecionado);
          }}
          onCancelar={async () => {
            setMenuAberto(false);
            if (!window.confirm(`Cancelar a venda ${selecionado.numero}?`)) return;
            try {
              await api.cancelarOrcamento(selecionado.id);
              toast("Venda cancelada", "success");
              setSelecionado(null);
            } catch (e) {
              toast("Erro: " + (e as Error).message, "error");
            }
          }}
        />
      )}

      {modalRecebimento && (
        <ModalPedidoCaixa
          d={modalRecebimento}
          onSair={() => {
            setModalRecebimento(null);
            setSelecionado(null);
          }}
        />
      )}

      {editarDe && (
        <ModalEditarStatus
          d={editarDe}
          onClose={() => setEditarDe(null)}
          onSalvo={() => {
            setEditarDe(null);
            setSelecionado(null);
          }}
        />
      )}

      {modalMovimento && (
        <ModalMovimentoCaixa
          tipo={modalMovimento}
          onClose={() => setModalMovimento(null)}
          onSalvo={() => setModalMovimento(null)}
        />
      )}
    </div>
  );
}

function ModalLocalizarPedido({ onClose, onSelecionar }: { onClose: () => void; onSelecionar: (id: number) => void }) {
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [rows, setRows] = useState<OrcamentoLista[]>([]);

  const buscar = () => {
    void api
      .listarOrcamentosFiltro({
        status: "finalizado",
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
      title="Localizar pedido (finalizado)"
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

function ModalMovimentoCaixa({
  tipo,
  onClose,
  onSalvo,
}: {
  tipo: "sangria" | "suprimento";
  onClose: () => void;
  onSalvo: () => void;
}) {
  const [valor, setValor] = useState("");
  const [descricao, setDescricao] = useState("");
  const [enviando, setEnviando] = useState(false);
  const titulo = tipo === "sangria" ? "Sangria (retirada do caixa)" : "Reforço (suprimento de caixa)";

  const confirmar = async () => {
    const v = parseNum(valor);
    if (v <= 0) {
      toast("Informe um valor maior que zero", "error");
      return;
    }
    setEnviando(true);
    try {
      const res = await api.movimentarCaixa({
        tipo,
        descricao: descricao.trim() || (tipo === "sangria" ? "Sangria" : "Reforço"),
        valor: v,
        forma_pagamento: "dinheiro",
      });
      toast(`${titulo} registrada · novo saldo ${fmtMoney(res.saldo_posterior)}`, "success");
      onSalvo();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
      setEnviando(false);
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
          <Button variant="primary" onClick={() => void confirmar()} disabled={enviando}>
            {enviando ? "Registrando…" : "Confirmar"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Valor">
          <Input
            inputMode="decimal"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void confirmar();
            }}
            autoFocus
          />
        </Field>
        <Field label="Descrição (opcional)">
          <Input value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder={tipo === "sangria" ? "ex.: depósito no banco" : "ex.: troco inicial"} />
        </Field>
      </div>
    </Modal>
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

type EtapaRecebimento = "recebimento" | "emitindo" | "aguardando" | "autorizada" | "erro";

function ModalPedidoCaixa({ d, onSair }: { d: OrcamentoDetalhe; onSair: () => void }) {
  const total = d.total;
  const [etapa, setEtapa] = useState<EtapaRecebimento>("recebimento");
  const [forma, setForma] = useState("dinheiro");
  const [valor, setValor] = useState("");
  const [bandeira, setBandeira] = useState("");
  const [codigoAutorizacao, setCodigoAutorizacao] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [doc, setDoc] = useState<DocumentoFiscal | { status: "nao_emitido" } | null>(null);
  const [erroMsg, setErroMsg] = useState("");
  const [imprimindo, setImprimindo] = useState(false);
  const valorRef = useRef<HTMLInputElement>(null);
  const bandeiraRef = useRef<HTMLInputElement>(null);
  const codigoRef = useRef<HTMLInputElement>(null);
  const imprimirRef = useRef<HTMLButtonElement>(null);
  const retryRef = useRef<HTMLButtonElement>(null);
  const confirmarRef = useRef<HTMLButtonElement>(null);

  const valorNum = parseNum(valor);
  const troco = forma === "dinheiro" ? Math.max(0, valorNum - total) : 0;
  const ehCartao = forma === "cartao_credito" || forma === "cartao_debito";

  const mudarForma = (f: string) => {
    setForma(f);
    // Dinheiro: operador digita o recebido. Demais formas: valor exato (total).
    setValor(f === "dinheiro" ? "" : fmtNum2(total));
    valorRef.current?.focus();
    valorRef.current?.select();
  };

  const emitirNfceAuto = async () => {
    setErroMsg("");
    setEtapa("emitindo");
    try {
      const res = await api.emitirNfce(d.id);
      setDoc(res);
      if (res.status === "autorizado") {
        setEtapa("autorizada");
      } else if (res.status === "rejeitado" || res.status === "erro") {
        setErroMsg(res.motivo || "Falha na emissão da NFC-e");
        setEtapa("erro");
      } else {
        setEtapa("aguardando");
      }
    } catch (e) {
      setErroMsg((e as Error).message);
      setEtapa("erro");
    }
  };

  const confirmar = async () => {
    if (valorNum <= 0) {
      toast("Informe o valor recebido", "error");
      return;
    }
    setEnviando(true);
    try {
      const res = await api.receberOrcamento(d.id, {
        forma_pagamento: forma,
        valor_recebido: valorNum,
        bandeira: ehCartao ? bandeira.trim() || undefined : undefined,
        codigo_autorizacao: ehCartao ? codigoAutorizacao.trim() || undefined : undefined,
      });
      setEnviando(false);
      if (res.recebido) toast(res.troco > 0 ? `Recebido · troco ${fmtMoney(res.troco)}` : "Recebimento registrado", "success");
      else toast(`Recebimento parcial de ${fmtMoney(res.valor_recebido)}`, "success");
      // Emissão da NFC-e é automática após concluir o recebimento.
      void emitirNfceAuto();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
      setEnviando(false);
    }
  };

  const imprimir = async () => {
    if (imprimindo) return;
    setImprimindo(true);
    try {
      await api.imprimirOrcamento(d.id);
      toast("Cupom enviado à impressora", "success");
      onSair();
    } catch (e) {
      toast("Impressão falhou: " + (e as Error).message, "error");
      setImprimindo(false);
      setTimeout(() => imprimirRef.current?.focus(), 0);
    }
  };

  // Polling do status enquanto a NFC-e fica "processando" (emissão assíncrona).
  useEffect(() => {
    if (etapa !== "aguardando") return;
    const t = setInterval(() => {
      void api
        .statusNfce(d.id)
        .then((res) => {
          setDoc(res);
          if (res.status === "autorizado") setEtapa("autorizada");
          else if (res.status === "rejeitado" || res.status === "erro") {
            setErroMsg(res.motivo || "Falha na emissão da NFC-e");
            setEtapa("erro");
          }
        })
        .catch(() => {});
    }, 3000);
    return () => clearInterval(t);
  }, [etapa, d.id]);

  // Foco no botão de impressão / nova tentativa conforme a etapa.
  useEffect(() => {
    if (etapa === "autorizada") imprimirRef.current?.focus();
    else if (etapa === "erro") retryRef.current?.focus();
  }, [etapa]);

  // Atalhos da etapa de recebimento: F1..F7 trocam a forma, F9 preenche com o
  // total, Ctrl+Enter confirma.
  useEffect(() => {
    if (etapa !== "recebimento") return;
    const onKey = (e: KeyboardEvent) => {
      const idx = FORMAS_CAIXA.findIndex((f) => f.tecla === e.key.toUpperCase());
      if (idx >= 0) {
        e.preventDefault();
        mudarForma(FORMAS_CAIXA[idx].valor);
        return;
      }
      if (e.key === "F9") {
        e.preventDefault();
        setValor(fmtNum2(total));
        valorRef.current?.focus();
        valorRef.current?.select();
        return;
      }
      if (e.key === "Enter" && e.ctrlKey) {
        e.preventDefault();
        void confirmar();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etapa, forma, valorNum, bandeira, codigoAutorizacao, total]);

  const titulo = etapa === "recebimento" ? `Recebimento — Pedido ${d.numero}` : `NFC-e — Pedido ${d.numero}`;

  return (
    <Modal
      open
      onClose={onSair}
      title={titulo}
      wide
      footer={
        etapa === "autorizada" ? (
          <>
            <Button variant="ghost" onClick={onSair}>
              ← Voltar para o Caixa <kbd className="ml-1 rounded bg-white px-1 text-[10px] shadow-sm">ESC</kbd>
            </Button>
            <Button ref={imprimirRef} variant="primary" onClick={() => void imprimir()} disabled={imprimindo}>
              {imprimindo ? "Imprimindo…" : "Imprimir"}
              <kbd className="ml-2 rounded bg-white/20 px-1 text-[10px]">ENTER</kbd>
            </Button>
          </>
        ) : etapa === "erro" ? (
          <>
            <Button variant="ghost" onClick={onSair}>
              ← Voltar <kbd className="ml-1 rounded bg-white px-1 text-[10px] shadow-sm">ESC</kbd>
            </Button>
            <Button ref={retryRef} variant="primary" onClick={() => void emitirNfceAuto()}>
              Tentar novamente <kbd className="ml-2 rounded bg-white/20 px-1 text-[10px]">ENTER</kbd>
            </Button>
          </>
        ) : etapa === "recebimento" ? (
          <>
            <Button variant="ghost" onClick={onSair}>
              ← Voltar para o Caixa <kbd className="ml-1 rounded bg-white px-1 text-[10px] shadow-sm">ESC</kbd>
            </Button>
            <Button ref={confirmarRef} variant="primary" onClick={() => void confirmar()} disabled={enviando}>
              {enviando ? "Registrando…" : "Confirmar recebimento"}
              <kbd className="ml-2 rounded bg-white/20 px-1 text-[10px]">Ctrl+Enter</kbd>
            </Button>
          </>
        ) : (
          <Button variant="ghost" onClick={onSair}>
            ← Voltar <kbd className="ml-1 rounded bg-white px-1 text-[10px] shadow-sm">ESC</kbd>
          </Button>
        )
      }
    >
      {etapa === "recebimento" && (
        <>
          <p className="mb-3 text-sm text-gray-500">
            {d.cliente || "Sem cliente"} · Vendedor: {d.usuario_nome || "—"} · {fmtDate(d.criado_em)}
          </p>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-xl bg-orange-50 p-4 text-center">
              <div className="text-xs font-medium uppercase text-orange-700">Valor a Receber</div>
              <div className="mt-1 text-3xl font-bold text-orange-600">{fmtMoney(total)}</div>
            </div>

            <div className="rounded-xl bg-white p-4 text-center ring-1 ring-gray-200">
              <div className="text-xs font-medium uppercase text-gray-500">Valor Recebido</div>
              <input
                ref={valorRef}
                inputMode="decimal"
                value={valor}
                onChange={(e) => setValor(e.target.value)}
                autoFocus
                placeholder="0,00"
                className="mt-1 w-full bg-transparent text-center text-3xl font-bold text-black outline-none"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    if (ehCartao) {
                      bandeiraRef.current?.focus();
                    } else {
                      // Dinheiro: não finaliza ainda — mostra o troco e move o
                      // foco para "Confirmar recebimento"; um 2º ENTER finaliza.
                      confirmarRef.current?.focus();
                    }
                  }
                }}
              />
            </div>

            <div className="rounded-xl bg-white p-4 text-center ring-1 ring-gray-200">
              <div className="text-xs font-medium uppercase text-gray-500">Troco</div>
              <div className="mt-1 text-3xl font-bold text-emerald-600">{fmtMoney(troco)}</div>
            </div>
          </div>

          <div className="mt-4">
            <label className="mb-1 block text-xs font-semibold text-gray-600">Forma de pagamento</label>
            <div className="flex flex-wrap gap-1.5">
              {FORMAS_CAIXA.map((f) => (
                <button
                  key={f.valor}
                  onClick={() => mudarForma(f.valor)}
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${
                    forma === f.valor ? "border-orange-500 bg-orange-500 text-white" : "border-gray-300 bg-white text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  {f.label}
                  <kbd className={`rounded px-1 text-[10px] ${forma === f.valor ? "bg-white/25" : "bg-gray-100 text-gray-400"}`}>
                    {f.tecla}
                  </kbd>
                </button>
              ))}
              <button
                onClick={() => {
                  setValor(fmtNum2(total));
                  valorRef.current?.focus();
                  valorRef.current?.select();
                }}
                className="flex items-center gap-1.5 rounded-full border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
              >
                Total <kbd className="rounded bg-gray-100 px-1 text-[10px] text-gray-400">F9</kbd>
              </button>
            </div>
          </div>

          {ehCartao && (
            <div className="mt-4 grid grid-cols-2 gap-3">
              <Field label="Bandeira do cartão">
                <Input
                  ref={bandeiraRef}
                  value={bandeira}
                  onChange={(e) => setBandeira(e.target.value)}
                  placeholder="VISA / MASTER / ELO…"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      codigoRef.current?.focus();
                    }
                  }}
                />
              </Field>
              <Field label="Código de autorização">
                <Input
                  ref={codigoRef}
                  value={codigoAutorizacao}
                  onChange={(e) => setCodigoAutorizacao(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void confirmar();
                    }
                  }}
                />
              </Field>
            </div>
          )}
        </>
      )}

      {(etapa === "emitindo" || etapa === "aguardando") && (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <div className="h-9 w-9 animate-spin rounded-full border-4 border-gray-200 border-t-orange-500" />
          <p className="mt-4 text-lg font-bold text-gray-700">
            {etapa === "emitindo" ? "Emitindo NFC-e…" : "Aguardando NFC-e…"}
          </p>
          <p className="mt-1 text-xs text-gray-500">Aguarde a autorização da SEFAZ.</p>
        </div>
      )}

      {etapa === "autorizada" && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Badge tone="green">NFC-e autorizada</Badge>
          </div>
          {doc && "chave_acesso" in doc && doc.chave_acesso && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
              <div className="mb-1 text-xs font-medium uppercase text-gray-500">Chave de acesso</div>
              <div className="break-all font-mono text-xs">{doc.chave_acesso}</div>
              {doc.protocolo && <div className="mt-2 text-xs text-gray-500">Protocolo: {doc.protocolo}</div>}
            </div>
          )}
          <p className="text-sm text-gray-600">
            Pressione <b>ENTER</b> para imprimir o cupom ou <b>ESC</b> para voltar ao caixa.
          </p>
        </div>
      )}

      {etapa === "erro" && (
        <div className="space-y-3">
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{erroMsg || "Falha na emissão da NFC-e."}</p>
          <p className="text-sm text-gray-600">
            Pressione <b>ENTER</b> para tentar novamente ou <b>ESC</b> para voltar ao caixa.
          </p>
        </div>
      )}
    </Modal>
  );
}
