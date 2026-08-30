// pages/caixa/menu-acoes.tsx — menu de ações do pedido no caixa (devolver/editar/cancelar).
import { useEffect, useState } from "react";
import { type OrcamentoLista } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { Button, Modal } from "../../ui/ui";

export function MenuAcoes({
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