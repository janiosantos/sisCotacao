import React, { useRef } from "react";
import { Search } from "lucide-react";
import {
  FieldBox,
  LegacyModalShell,
  ModalFooterButtons,
  inputStyle,
  useLegacyForm,
} from "./legacy-kit";

/**
 * Ficha de Clientes, construída inteiramente sobre o legacy-kit:
 * - LegacyModalShell cuida da moldura (barra de título, sub-header, overlay).
 * - useLegacyForm cuida de tabIndex, Enter-como-Tab, foco automático,
 *   focus trap e dos atalhos Esc / Ctrl+F12.
 * Comparado à primeira versão, esta tela não reimplementa nada de chrome
 * ou de teclado — só declara campos e layout.
 */

const FIELD_ORDER = [
  "codigo",
  "nome",
  "fantasia",
  "tipoPessoa",
  "cpfCnpj",
  "cep",
  "endereco",
  "bairro",
  "cidade",
  "uf",
  "telefone",
  "celular",
  "email",
  "limiteCredito",
  "situacao",
  "confirmarBtn",
  "cancelarBtn",
] as const;

type FieldKey = (typeof FIELD_ORDER)[number];

export interface ClienteData {
  codigo: string;
  nome: string;
  fantasia: string;
  tipoPessoa: string;
  cpfCnpj: string;
  cep: string;
  endereco: string;
  bairro: string;
  cidade: string;
  uf: string;
  telefone: string;
  celular: string;
  email: string;
  limiteCredito: string;
  situacao: string;
}

const DEFAULT_CLIENTE: ClienteData = {
  codigo: "001176",
  nome: "CONSUMIDOR",
  fantasia: "",
  tipoPessoa: "Pessoa Física",
  cpfCnpj: "",
  cep: "",
  endereco: "",
  bairro: "",
  cidade: "",
  uf: "",
  telefone: "",
  celular: "",
  email: "",
  limiteCredito: "0,00",
  situacao: "1 Ativo",
};

interface FichaClientesProps {
  open: boolean;
  initialCodigo?: string;
  onClose: () => void;
  onConfirm: (cliente: ClienteData) => void;
}

export default function FichaClientes({
  open,
  initialCodigo,
  onClose,
  onConfirm,
}: FichaClientesProps) {
  const dataRef = useRef<ClienteData>({
    ...DEFAULT_CLIENTE,
    codigo: initialCodigo ?? DEFAULT_CLIENTE.codigo,
  });

  const handleConfirm = () => onConfirm(dataRef.current);

  const { registerRef, handleEnterAsTab } = useLegacyForm<FieldKey>({
    order: FIELD_ORDER,
    modal: true,
    open,
    onClose,
    onConfirm: handleConfirm,
  });

  const set = <K extends keyof ClienteData>(key: K, value: string) => {
    dataRef.current[key] = value;
  };

  return (
    <LegacyModalShell
      open={open}
      title="Ficha de Clientes"
      onClose={onClose}
      footer={
        <ModalFooterButtons
          onConfirm={handleConfirm}
          onCancel={onClose}
          confirmRef={registerRef("confirmarBtn")}
          cancelRef={registerRef("cancelarBtn")}
          confirmTabIndex={16}
          cancelTabIndex={17}
        />
      }
    >
      <div style={{ display: "flex", gap: 10 }}>
        <FieldBox label="Código" width={110}>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input
              ref={registerRef("codigo")}
              tabIndex={1}
              defaultValue={dataRef.current.codigo}
              onChange={(e) => set("codigo", e.target.value)}
              onKeyDown={handleEnterAsTab("codigo")}
              style={{ ...inputStyle, width: 62, background: "#bfe0ff" }}
            />
            <Search size={14} color="#555" />
          </div>
        </FieldBox>

        <FieldBox label="Tipo Pessoa" width={210}>
          <select
            ref={registerRef("tipoPessoa") as any}
            tabIndex={4}
            defaultValue={dataRef.current.tipoPessoa}
            onChange={(e) => set("tipoPessoa", e.target.value)}
            onKeyDown={handleEnterAsTab("tipoPessoa")}
            style={{ ...inputStyle, width: "100%" }}
          >
            <option>Pessoa Física</option>
            <option>Pessoa Jurídica</option>
          </select>
        </FieldBox>

        <FieldBox label="CPF/CNPJ" width={220} noBorderLeft>
          <input
            ref={registerRef("cpfCnpj")}
            tabIndex={5}
            defaultValue={dataRef.current.cpfCnpj}
            onChange={(e) => set("cpfCnpj", e.target.value)}
            onKeyDown={handleEnterAsTab("cpfCnpj")}
            style={{ ...inputStyle, width: "100%" }}
          />
        </FieldBox>
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <FieldBox label="Nome / Razão Social" width={330}>
          <input
            ref={registerRef("nome")}
            tabIndex={2}
            defaultValue={dataRef.current.nome}
            onChange={(e) => set("nome", e.target.value)}
            onKeyDown={handleEnterAsTab("nome")}
            style={{ ...inputStyle, width: "100%" }}
          />
        </FieldBox>
        <FieldBox label="Fantasia" width={210} noBorderLeft>
          <input
            ref={registerRef("fantasia")}
            tabIndex={3}
            defaultValue={dataRef.current.fantasia}
            onChange={(e) => set("fantasia", e.target.value)}
            onKeyDown={handleEnterAsTab("fantasia")}
            style={{ ...inputStyle, width: "100%" }}
          />
        </FieldBox>
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <FieldBox label="CEP" width={130}>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input
              ref={registerRef("cep")}
              tabIndex={6}
              defaultValue={dataRef.current.cep}
              onChange={(e) => set("cep", e.target.value)}
              onKeyDown={handleEnterAsTab("cep")}
              style={{ ...inputStyle, width: "100%" }}
            />
            <Search size={14} color="#555" />
          </div>
        </FieldBox>
        <FieldBox label="Endereço" width={410} noBorderLeft>
          <input
            ref={registerRef("endereco")}
            tabIndex={7}
            defaultValue={dataRef.current.endereco}
            onChange={(e) => set("endereco", e.target.value)}
            onKeyDown={handleEnterAsTab("endereco")}
            style={{ ...inputStyle, width: "100%" }}
          />
        </FieldBox>
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <FieldBox label="Bairro" width={280}>
          <input
            ref={registerRef("bairro")}
            tabIndex={8}
            defaultValue={dataRef.current.bairro}
            onChange={(e) => set("bairro", e.target.value)}
            onKeyDown={handleEnterAsTab("bairro")}
            style={{ ...inputStyle, width: "100%" }}
          />
        </FieldBox>
        <FieldBox label="Cidade" width={190} noBorderLeft>
          <input
            ref={registerRef("cidade")}
            tabIndex={9}
            defaultValue={dataRef.current.cidade}
            onChange={(e) => set("cidade", e.target.value)}
            onKeyDown={handleEnterAsTab("cidade")}
            style={{ ...inputStyle, width: "100%" }}
          />
        </FieldBox>
        <FieldBox label="UF" width={70} noBorderLeft>
          <input
            ref={registerRef("uf")}
            tabIndex={10}
            defaultValue={dataRef.current.uf}
            onChange={(e) => set("uf", e.target.value)}
            onKeyDown={handleEnterAsTab("uf")}
            style={{ ...inputStyle, width: "100%" }}
          />
        </FieldBox>
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <FieldBox label="Telefone" width={170}>
          <input
            ref={registerRef("telefone")}
            tabIndex={11}
            defaultValue={dataRef.current.telefone}
            onChange={(e) => set("telefone", e.target.value)}
            onKeyDown={handleEnterAsTab("telefone")}
            style={{ ...inputStyle, width: "100%" }}
          />
        </FieldBox>
        <FieldBox label="Celular" width={170} noBorderLeft>
          <input
            ref={registerRef("celular")}
            tabIndex={12}
            defaultValue={dataRef.current.celular}
            onChange={(e) => set("celular", e.target.value)}
            onKeyDown={handleEnterAsTab("celular")}
            style={{ ...inputStyle, width: "100%" }}
          />
        </FieldBox>
        <FieldBox label="E-mail" width={200} noBorderLeft>
          <input
            ref={registerRef("email")}
            tabIndex={13}
            defaultValue={dataRef.current.email}
            onChange={(e) => set("email", e.target.value)}
            onKeyDown={handleEnterAsTab("email")}
            style={{ ...inputStyle, width: "100%" }}
          />
        </FieldBox>
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <FieldBox label="Limite de Crédito" width={190}>
          <input
            ref={registerRef("limiteCredito")}
            tabIndex={14}
            defaultValue={dataRef.current.limiteCredito}
            onChange={(e) => set("limiteCredito", e.target.value)}
            onKeyDown={handleEnterAsTab("limiteCredito")}
            style={{ ...inputStyle, width: "100%", color: "#1b4dab" }}
          />
        </FieldBox>
        <FieldBox label="Situação" width={190} noBorderLeft>
          <select
            ref={registerRef("situacao") as any}
            tabIndex={15}
            defaultValue={dataRef.current.situacao}
            onChange={(e) => set("situacao", e.target.value)}
            onKeyDown={handleEnterAsTab("situacao")}
            style={{ ...inputStyle, width: "100%" }}
          >
            <option>1 Ativo</option>
            <option>2 Inativo</option>
            <option>3 Bloqueado</option>
          </select>
        </FieldBox>
      </div>
    </LegacyModalShell>
  );
}
