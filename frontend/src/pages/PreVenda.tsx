// PreVenda.tsx — tela "Pré-Venda" (padrão Protheus), portada para React.
// Usa o legacy-kit: TitleBar/SubHeader/Sidebar prontos, useLegacyForm para
// Enter-como-Tab e useGlobalShortcuts para os atalhos (Ctrl+F5/F6, F8, etc.).

import { useState } from "react";
import {
  FieldBox,
  SubHeader,
  Sidebar,
  TitleBar,
  boxLabelStyle,
  boxStyle,
  ctrlDigit,
  ctrlFKey,
  ctrlLetter,
  fKey,
  inputStyle,
  useGlobalShortcuts,
  useLegacyForm,
  type SidebarAction,
} from "../legacy-kit";
import FichaClientes, { type ClienteData } from "./FichaClientes";
import ConsultarPreco from "./ConsultarPreco";

const FIELD_ORDER = [
  "vendedor",
  "cliente",
  "tipoNota",
  "entregaViaCarga",
  "tipoFrete",
  "operacaoPresencial",
  "produto",
  "desconto",
] as const;

type FieldKey = (typeof FIELD_ORDER)[number];

const ICO = {
  ficha: "▣",
  preco: "⌕",
  cancelar: "✕",
  pesquisar: "⌕",
  pagamento: "$",
  situacao: "↻",
  finalizar: "✓",
  entrega: "▸",
  opcoes: "＋",
};

export default function PreVenda() {
  const [lastAction, setLastAction] = useState("");
  const [fichaClientesOpen, setFichaClientesOpen] = useState(false);
  const [consultarPrecoOpen, setConsultarPrecoOpen] = useState(false);
  const [cliente, setCliente] = useState({ codigo: "001176", nome: "CONSUMIDOR" });

  const anyModalOpen = fichaClientesOpen || consultarPrecoOpen;

  const { registerRef, handleEnterAsTab, refs } = useLegacyForm<FieldKey>({
    order: FIELD_ORDER,
  });

  const handleFichaConfirm = (dados: ClienteData) => {
    setCliente({ codigo: dados.codigo, nome: dados.nome });
    setFichaClientesOpen(false);
    setTimeout(() => {
      const el = refs.current["cliente"];
      el?.focus();
      if (el instanceof HTMLInputElement) el.select();
    }, 0);
  };

  useGlobalShortcuts(
    [
      {
        match: ctrlFKey(5),
        label: "Ficha de Clientes (Ctrl+F5)",
        action: () => {
          setLastAction("Ficha de Clientes (Ctrl+F5)");
          setFichaClientesOpen(true);
        },
      },
      {
        match: ctrlFKey(6),
        label: "Consultar preço (Ctrl+F6)",
        action: () => {
          setLastAction("Consultar preço (Ctrl+F6)");
          setConsultarPrecoOpen(true);
        },
      },
      { match: ctrlDigit("8"), label: "Cancelar (Ctrl+8)", action: () => setLastAction("Cancelar (Ctrl+8)") },
      { match: ctrlLetter("q"), label: "Pesquisar (Ctrl+Q)", action: () => setLastAction("Pesquisar (Ctrl+Q)") },
      { match: fKey(8), label: "Pagamento (F8)", action: () => setLastAction("Pagamento (F8)") },
      { match: ctrlFKey(11), label: "Situação (Ctrl+F11)", action: () => setLastAction("Situação (Ctrl+F11)") },
      { match: ctrlFKey(12), label: "Finalizar (Ctrl+F12)", action: () => setLastAction("Finalizar (Ctrl+F12)") },
      { match: fKey(7), label: "Entrega (F7)", action: () => setLastAction("Entrega (F7)") },
      { match: ctrlFKey(7), label: "Mais Opções (Ctrl+F7)", action: () => setLastAction("Mais Opções (Ctrl+F7)") },
    ],
    !anyModalOpen
  );

  const actions: SidebarAction[] = [
    { icon: ICO.ficha, label: "Ficha de Clientes", shortcut: "Ctrl + F5", active: lastAction.startsWith("Ficha") },
    { icon: ICO.preco, label: "Consultar preço", shortcut: "Ctrl + F6", active: lastAction.startsWith("Consultar") },
    { icon: ICO.cancelar, label: "Cancelar", shortcut: "Ctrl + 8", active: lastAction.startsWith("Cancelar") },
    { icon: ICO.pesquisar, label: "Pesquisar", shortcut: "Ctrl + Q", active: lastAction.startsWith("Pesquisar") },
    { icon: ICO.pagamento, label: "Pagamento", shortcut: "F8", active: lastAction.startsWith("Pagamento") },
    { icon: ICO.situacao, label: "Situação", shortcut: "Ctrl + F11", active: lastAction.startsWith("Situação") },
    { icon: ICO.finalizar, label: "Finalizar", shortcut: "Ctrl + F12", active: lastAction.startsWith("Finalizar") },
    { icon: ICO.entrega, label: "Entrega", shortcut: "F7", active: lastAction.startsWith("Entrega") },
    { icon: ICO.opcoes, label: "Mais Opções", shortcut: "Ctrl + F7", active: lastAction.startsWith("Mais") },
  ];

  return (
    <>
      <div className="lg-window">
        <TitleBar title="Pré-Venda" />
        <SubHeader
          title="Pré-Venda"
          meta={
            <>
              <span style={{ fontSize: 13 }}>0000000000</span>
              <span style={{ fontSize: 12, opacity: 0.9 }}>Pedido</span>
              <span style={{ fontSize: 12 }}>U.N. 1</span>
              <span style={{ fontSize: 12 }}>Operador 000181</span>
              <span style={{ fontSize: 12 }}>Data 29/03/21</span>
              <span style={{ fontSize: 12 }}>
                Controle <b>PENDENTE</b>
              </span>
            </>
          }
        />

        <div className="lg-body">
          <div className="lg-content">
            <div style={{ display: "flex", gap: 8 }}>
              <FieldBox label="Vendedor" width={110}>
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <input
                    ref={registerRef("vendedor")}
                    tabIndex={1}
                    defaultValue="000181"
                    onKeyDown={handleEnterAsTab("vendedor")}
                    style={{ ...inputStyle, width: 62, background: "#bfe0ff" }}
                  />
                  <span style={{ color: "#555", fontSize: 14 }}>⌕</span>
                </div>
              </FieldBox>
              <FieldBox label="Descrição" width={455} noBorderLeft>
                <div style={{ fontSize: 13, paddingTop: 4 }}>VENDEDOR PADRÃO</div>
              </FieldBox>
            </div>

            <FieldBox label="Cliente" width={575}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <input
                    ref={registerRef("cliente")}
                    tabIndex={2}
                    value={cliente.codigo}
                    onChange={(e) => setCliente((c) => ({ ...c, codigo: e.target.value }))}
                    onKeyDown={handleEnterAsTab("cliente")}
                    style={{ ...inputStyle, width: 70 }}
                  />
                  <span style={{ color: "#555", fontSize: 14 }}>⌕</span>
                </div>
                <span style={{ fontSize: 13 }}>{cliente.nome}</span>
              </div>
            </FieldBox>

            <div style={boxLabelStyle}>Crédito Liberado</div>
            <div style={{ ...boxStyle, height: 34, marginBottom: 10 }} />

            <div style={{ display: "flex", gap: 26, marginBottom: 10, flexWrap: "wrap" }}>
              <div>
                <div style={boxLabelStyle}>Tipo Nota</div>
                <select
                  ref={registerRef("tipoNota")}
                  tabIndex={3}
                  defaultValue="Normal"
                  onKeyDown={handleEnterAsTab("tipoNota")}
                  style={{ ...inputStyle, width: 160 }}
                >
                  <option>Normal</option>
                  <option>Devolução</option>
                  <option>Bonificação</option>
                </select>
              </div>

              <div style={{ paddingTop: 20 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5 }}>
                  <input
                    ref={registerRef("entregaViaCarga")}
                    tabIndex={4}
                    type="checkbox"
                    onKeyDown={handleEnterAsTab("entregaViaCarga")}
                  />
                  Entrega via Carga
                </label>
              </div>

              <div>
                <div style={boxLabelStyle}>Tipo Frete</div>
                <select
                  ref={registerRef("tipoFrete")}
                  tabIndex={5}
                  defaultValue="F Sem Frete"
                  onKeyDown={handleEnterAsTab("tipoFrete")}
                  style={{ ...inputStyle, width: 180 }}
                >
                  <option>F Sem Frete</option>
                  <option>CIF</option>
                  <option>FOB</option>
                </select>
              </div>
            </div>

            <div style={{ display: "flex", gap: 26, marginBottom: 10, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <div style={boxLabelStyle}>Observação</div>
                <div style={{ ...boxStyle, height: 30 }} />
              </div>
              <div>
                <div style={boxLabelStyle}>Operação presencial</div>
                <select
                  ref={registerRef("operacaoPresencial")}
                  tabIndex={6}
                  defaultValue="1 Sim"
                  onKeyDown={handleEnterAsTab("operacaoPresencial")}
                  style={{ ...inputStyle, width: 180 }}
                >
                  <option>1 Sim</option>
                  <option>2 Não</option>
                </select>
              </div>
            </div>

            <div style={{ display: "flex", gap: 10, marginBottom: 4 }}>
              <div style={{ flex: 1 }}>
                <div style={boxLabelStyle}>Produto</div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <input
                    ref={registerRef("produto")}
                    tabIndex={7}
                    onKeyDown={handleEnterAsTab("produto")}
                    style={{ ...inputStyle, flex: 1 }}
                  />
                  <span style={{ color: "#555", fontSize: 16 }}>⌕</span>
                </div>
              </div>
              <div>
                <div style={boxLabelStyle}>Desconto</div>
                <input
                  ref={registerRef("desconto")}
                  tabIndex={8}
                  defaultValue="0,00%"
                  onKeyDown={handleEnterAsTab("desconto")}
                  style={{ ...inputStyle, width: 90, color: "#1b4dab" }}
                />
              </div>
            </div>

            <div style={boxLabelStyle}>Descrição</div>
            <div style={{ ...boxStyle, height: 28, paddingLeft: 6, color: "#666", fontSize: 12.5, marginBottom: 6 }}>
              Informe um produto para iniciar a venda
            </div>

            <div style={{ border: "1px solid #cfd3d8" }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "50px 60px 90px 1fr 100px 70px 45px 85px 90px",
                  fontSize: 11.5,
                  fontWeight: 600,
                  color: "#333",
                  borderBottom: "1px solid #cfd3d8",
                  padding: "4px 6px",
                }}
              >
                <span>Seq.</span>
                <span>Vend.</span>
                <span>Código</span>
                <span>Descrição</span>
                <span>Desc/Acrés.</span>
                <span>Quant.</span>
                <span>Uni.</span>
                <span>Pr. Unit.</span>
                <span>Pr. Total</span>
              </div>
              {Array.from({ length: 9 }).map((_, i) => (
                <div
                  key={i}
                  style={{ height: 22, background: i % 2 === 0 ? "#eaf2fb" : "#fff" }}
                />
              ))}
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: 40,
                marginTop: 10,
                fontSize: 12.5,
                flexWrap: "wrap",
              }}
            >
              <div>
                <div style={boxLabelStyle}>Quantidade</div>
                <div style={{ color: "#1b4dab", fontWeight: 700 }}>F4</div>
              </div>
              <div style={{ paddingBottom: 2 }}>X</div>
              <div>
                <div style={boxLabelStyle}>Preço Unitário</div>
              </div>
              <div style={{ paddingBottom: 2 }}>=</div>
              <div>
                <div style={boxLabelStyle}>Total Item</div>
              </div>
              <div style={{ flex: 1 }} />
              <div style={{ textAlign: "right" }}>
                <div style={boxLabelStyle}>Subtotal</div>
                <div style={{ fontSize: 15, fontWeight: 700 }}>0,00</div>
              </div>
            </div>
          </div>

          <Sidebar
            brand="Sistema ERP"
            subBrand="GESTÃO COMERCIAL"
            footerNote={lastAction ? `Último atalho: ${lastAction}` : undefined}
            actions={actions}
          />
        </div>
      </div>

      <FichaClientes
        open={fichaClientesOpen}
        initialCodigo={cliente.codigo}
        onClose={() => {
          setFichaClientesOpen(false);
          setTimeout(() => refs.current["cliente"]?.focus(), 0);
        }}
        onConfirm={handleFichaConfirm}
      />
      <ConsultarPreco open={consultarPrecoOpen} onClose={() => setConsultarPrecoOpen(false)} />
    </>
  );
}
