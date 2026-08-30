// pages/caixa.tsx — Caixa (ECF): recebimento de vendas de balcão.
// Layout de PDV (frente de caixa). O pedido é selecionado via "Localizar
// pedido (F8)" — mesmo padrão do modal de localização da pré-venda.

import { useEffect, useState } from "react";
import { api, type OrcamentoDetalhe, type OrcamentoLista } from "../api/client";
import { fmtDate, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { usuarioCorrente } from "./login";
import { Button } from "../ui/ui";
import { DataBox } from "../ui/data-box";
import { STATUS_LABELS } from "./caixa/labels";
import { ModalLocalizarPedido } from "./caixa/modal-localizar-pedido";
import { ModalMovimentoCaixa } from "./caixa/modal-movimento-caixa";
import { MenuAcoes } from "./caixa/menu-acoes";
import { ModalEditarStatus } from "./caixa/modal-editar-status";
import { ModalPedidoCaixa } from "./caixa/modal-pedido-caixa";
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

