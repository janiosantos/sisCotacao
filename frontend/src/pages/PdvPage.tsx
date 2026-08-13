// PdvPage.tsx — PDV (pré-venda) dentro do chrome legacy.
// Mantém a lógica vanilla do PDV (busca, carrinho, F1–F9) e adiciona a
// titlebar + sidebar de atalhos do padrão Protheus.

import { useEffect, useRef } from "react";
import { Sidebar, SubHeader, TitleBar, type SidebarAction } from "../legacy-kit";
import { pdvAtalho, pdvBuscaCliente, render as renderPdv, setOcultarCabecalho } from "./pdv";

export default function PdvPage() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setOcultarCabecalho(true);
    const el = ref.current;
    if (el) Promise.resolve(renderPdv(el)).catch(() => {});
  }, []);

  const actions: SidebarAction[] = [
    { icon: "▣", label: "Ficha de Clientes", shortcut: "Ctrl + F5", onAction: pdvBuscaCliente },
    { icon: "▣", label: "Imprimir", shortcut: "F1", onAction: () => void pdvAtalho(1) },
    { icon: "▣", label: "Visualizar", shortcut: "F2", onAction: () => void pdvAtalho(2) },
    { icon: "✓", label: "Finalizar", shortcut: "F3", onAction: () => void pdvAtalho(3) },
    { icon: "▣", label: "Salvar rascunho", shortcut: "F4", onAction: () => void pdvAtalho(4) },
    { icon: "▣", label: "Novo", shortcut: "F5", onAction: () => void pdvAtalho(5) },
    { icon: "▣", label: "Buscar cliente", shortcut: "F6", onAction: () => void pdvAtalho(6) },
    { icon: "▣", label: "Impressora", shortcut: "F7", onAction: () => void pdvAtalho(7) },
    { icon: "▣", label: "Lista orçamentos", shortcut: "F8", onAction: () => void pdvAtalho(8) },
    { icon: "⌕", label: "Foco busca", shortcut: "F9", onAction: () => void pdvAtalho(9) },
  ];

  return (
    <div className="lg-window">
      <TitleBar title="PDV — Pré-Venda" />
      <SubHeader
        title="PDV · Orçamentos"
        meta={
          <span>
            Controle <b>PENDENTE</b>
          </span>
        }
      />
      <div className="lg-body">
        <div className="lg-content" ref={ref} />
        <Sidebar brand="Sistema ERP" subBrand="GESTÃO COMERCIAL" actions={actions} />
      </div>
    </div>
  );
}
