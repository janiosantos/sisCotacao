import React, { useState } from "react";
import {
  Search,
  Users,
  XCircle,
  SearchCheck,
  Banknote,
  RefreshCw,
  CheckCircle2,
  Truck,
  Plus,
} from "lucide-react";
import {
  FieldBox,
  TitleBar,
  SubHeader,
  Sidebar,
  useLegacyForm,
  useGlobalShortcuts,
  ctrlFKey,
  ctrlDigit,
  fKey,
  ctrlLetter,
  inputStyle,
  boxLabelStyle,
  boxStyle,
  legacyFont,
  windowShadow,
} from "./legacy-kit";
import FichaClientes, { ClienteData } from "./FichaClientes";
import ConsultarPreco from "./ConsultarPreco";

/**
 * Réplica da tela "Pré-Venda", agora construída sobre o legacy-kit:
 * - TitleBar / SubHeader / Sidebar vêm prontos do kit.
 * - useLegacyForm cuida de tabIndex e Enter-como-Tab dos campos principais.
 * - useGlobalShortcuts declara os atalhos como dados (em vez de um switch
 *   manual), e cada atalho pode abrir uma tela modal diferente construída
 *   com o mesmo kit (Ficha de Clientes, Consultar Preço).
 *
 * Adicionar uma nova tela acionada por atalho = importar o componente,
 * criar um `useState` para abri-lo e adicionar UMA linha na lista de
 * `shortcuts` abaixo. Nenhum código de chrome ou de teclado é duplicado.
 */

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

export default function PreVenda() {
  const [lastAction, setLastAction] = useState("");
  const [fichaClientesOpen, setFichaClientesOpen] = useState(false);
  const [consultarPrecoOpen, setConsultarPrecoOpen] = useState(false);
  const [cliente, setCliente] = useState({
    codigo: "001176",
    nome: "CONSUMIDOR",
  });

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

  const closeFicha = () => {
    setFichaClientesOpen(false);
    setTimeout(() => refs.current["cliente"]?.focus(), 0);
  };

  const closeConsultarPreco = () => setConsultarPrecoOpen(false);

  // Atalhos declarados como dados — cada linha nova aqui é uma tela nova
  // integrada, sem tocar em nada além desta lista.
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
      {
        match: ctrlDigit("8"),
        label: "Cancelar (Ctrl+8)",
        action: () => setLastAction("Cancelar (Ctrl+8)"),
      },
      {
        match: ctrlLetter("q"),
        label: "Pesquisar (Ctrl+Q)",
        action: () => setLastAction("Pesquisar (Ctrl+Q)"),
      },
      {
        match: fKey(8),
        label: "Pagamento (F8)",
        action: () => setLastAction("Pagamento (F8)"),
      },
      {
        match: ctrlFKey(11),
        label: "Situação (Ctrl+F11)",
        action: () => setLastAction("Situação (Ctrl+F11)"),
      },
      {
        match: ctrlFKey(12),
        label: "Finalizar (Ctrl+F12)",
        action: () => setLastAction("Finalizar (Ctrl+F12)"),
      },
      {
        match: fKey(7),
        label: "Entrega (F7)",
        action: () => setLastAction("Entrega (F7)"),
      },
      {
        match: ctrlFKey(7),
        label: "Mais Opções (Ctrl+F7)",
        action: () => setLastAction("Mais Opções (Ctrl+F7)"),
      },
    ],
    !anyModalOpen // suspenso enquanto qualquer modal do kit estiver aberto
  );

  return (
    <div
      style={{
        fontFamily: legacyFont,
        background: "#4a4a4a",
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        padding: 20,
      }}
    >
      <div
        style={{
          width: 1000,
          border: "1px solid #999",
          boxShadow: windowShadow,
          background: "#fff",
        }}
      >
        <TitleBar title="Pré-Venda" />
        <SubHeader
          title="Pré-Venda"
          meta={
            <>
              <span style={{ fontSize: 15 }}>0000000000</span>
              <span style={{ fontSize: 12.5, opacity: 0.9, marginLeft: -8 }}>
                Pedido
              </span>
              <span style={{ marginLeft: 24, fontSize: 12.5 }}>U.N. 1</span>
              <span style={{ fontSize: 12.5 }}>Operador 000181</span>
              <span style={{ fontSize: 12.5 }}>Data 29/03/21</span>
              <span style={{ fontSize: 12.5 }}>
                Controle <b>PENDENTE</b>
              </span>
            </>
          }
        />

        <div style={{ display: "flex" }}>
          {/* Main content */}
          <div style={{ flex: 1, padding: 12 }}>
            <div style={{ display: "flex", gap: 10 }}>
              <FieldBox label="Vendedor" width={110}>
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <input
                    ref={registerRef("vendedor")}
                    tabIndex={1}
                    defaultValue="000181"
                    onKeyDown={handleEnterAsTab("vendedor")}
                    style={{ ...inputStyle, width: 62, background: "#bfe0ff" }}
                  />
                  <Search size={14} color="#555" />
                </div>
              </FieldBox>

              <FieldBox label="Descrição" width={455} noBorderLeft>
                <div style={{ fontSize: 13, paddingTop: 4 }}>
                  VENDEDOR PADRÃO
                </div>
              </FieldBox>
            </div>

            <FieldBox label="Cliente" width={575}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <input
                    ref={registerRef("cliente")}
                    tabIndex={2}
                    value={cliente.codigo}
                    onChange={(e) =>
                      setCliente((c) => ({ ...c, codigo: e.target.value }))
                    }
                    onKeyDown={handleEnterAsTab("cliente")}
                    style={{ ...inputStyle, width: 70 }}
                  />
                  <Search size={14} color="#555" />
                </div>
                <span style={{ fontSize: 13 }}>{cliente.nome}</span>
              </div>
            </FieldBox>

            <div style={boxLabelStyle}>Crédito Liberado</div>
            <div style={{ ...boxStyle, height: 34, marginBottom: 10 }} />

            <div style={{ display: "flex", gap: 26, marginBottom: 10 }}>
              <div>
                <div style={boxLabelStyle}>Tipo Nota</div>
                <select
                  ref={registerRef("tipoNota") as any}
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
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 12.5,
                  }}
                >
                  <input
                    ref={registerRef("entregaViaCarga") as any}
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
                  ref={registerRef("tipoFrete") as any}
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

            <div style={{ display: "flex", gap: 26, marginBottom: 10 }}>
              <div style={{ flex: 1 }}>
                <div style={boxLabelStyle}>Observação</div>
                <div style={{ ...boxStyle, height: 30 }} />
              </div>
              <div>
                <div style={boxLabelStyle}>Operação presencial</div>
                <select
                  ref={registerRef("operacaoPresencial") as any}
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
                  <Search size={16} color="#555" />
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
            <div
              style={{
                ...boxStyle,
                height: 28,
                display: "flex",
                alignItems: "center",
                paddingLeft: 6,
                color: "#666",
                fontSize: 12.5,
                marginBottom: 6,
              }}
            >
              Informe um produto para iniciar a venda
            </div>

            <div style={{ border: "1px solid #cfd3d8" }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "50px 60px 90px 1fr 100px 70px 45px 85px 90px",
                  fontSize: 11.5,
                  fontWeight: 600,
                  color: "#333",
                  background: "#fff",
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
                  style={{
                    height: 22,
                    background: i % 2 === 0 ? "#eaf2fb" : "#fff",
                  }}
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
            actions={[
              {
                icon: <Users size={18} />,
                label: "Ficha de Clientes",
                shortcut: "Ctrl + F5",
                active: lastAction.startsWith("Ficha"),
              },
              {
                icon: <SearchCheck size={18} />,
                label: "Consultar preço",
                shortcut: "Ctrl + F6",
                active: lastAction.startsWith("Consultar"),
              },
              {
                icon: <XCircle size={18} />,
                label: "Cancelar",
                shortcut: "Ctrl + 8",
                active: lastAction.startsWith("Cancelar"),
              },
              {
                icon: <Search size={18} />,
                label: "Pesquisar",
                shortcut: "Ctrl + Q",
                active: lastAction.startsWith("Pesquisar"),
              },
              {
                icon: <Banknote size={18} />,
                label: "Pagamento",
                shortcut: "F8",
                active: lastAction.startsWith("Pagamento"),
              },
              {
                icon: <RefreshCw size={18} />,
                label: "Situação",
                shortcut: "Ctrl + F11",
                active: lastAction.startsWith("Situação"),
              },
              {
                icon: <CheckCircle2 size={18} />,
                label: "Finalizar",
                shortcut: "Ctrl + F12",
                active: lastAction.startsWith("Finalizar"),
              },
              {
                icon: <Truck size={18} />,
                label: "Entrega",
                shortcut: "F7",
                active: lastAction.startsWith("Entrega"),
              },
              {
                icon: <Plus size={18} />,
                label: "Mais Opções",
                shortcut: "Ctrl + F7",
                active: lastAction.startsWith("Mais"),
              },
            ]}
          />
        </div>
      </div>

      <FichaClientes
        open={fichaClientesOpen}
        initialCodigo={cliente.codigo}
        onClose={closeFicha}
        onConfirm={handleFichaConfirm}
      />

      <ConsultarPreco open={consultarPrecoOpen} onClose={closeConsultarPreco} />
    </div>
  );
}
