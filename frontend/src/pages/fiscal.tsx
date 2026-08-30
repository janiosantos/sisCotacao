// pages/fiscal.tsx — fiscal (React + Tailwind).

import { useState } from "react";
import { PageHeader } from "../ui/ui";
import { Cfop } from "./fiscal/cfop";
import { Cst } from "./fiscal/cst";
import { Cest } from "./fiscal/cest";
import { Config } from "./fiscal/config";
import { EmitenteTab } from "./fiscal/emitente-tab";
import { Nfe } from "./fiscal/nfe";
import { Ibpt } from "./fiscal/ibpt";
import { HistoricoFiscal } from "./fiscal/historico";
import { Simulador } from "./fiscal/simulador";
import { Sugestoes } from "./fiscal/sugestoes";

type Aba = "cfop" | "cst" | "cest" | "config" | "emitente" | "nfe" | "ibpt" | "sugestoes" | "simulador" | "historico";

export default function Fiscal() {
  const [aba, setAba] = useState<Aba>("cfop");

  const TABS: { key: Aba; label: string }[] = [
    { key: "cfop", label: "CFOP" },
    { key: "cst", label: "CST" },
    { key: "cest", label: "CEST" },
    { key: "config", label: "Config. Fiscal" },
    { key: "emitente", label: "Emitente" },
    { key: "nfe", label: "NF-e" },
    { key: "ibpt", label: "IBPT" },
    { key: "sugestoes", label: "Sugestões NCM" },
    { key: "simulador", label: "Simulador" },
    { key: "historico", label: "Histórico" },
  ];

  return (
    <div>
      <PageHeader title="Fiscal" subtitle="CFOP, CST e configuração tributária por produto." />
      <div className="mb-5 flex gap-2 overflow-x-auto border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setAba(t.key)}
            className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${
              aba === t.key ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {aba === "cfop" && <Cfop />}
      {aba === "cst" && <Cst />}
      {aba === "cest" && <Cest />}
      {aba === "config" && <Config />}
      {aba === "emitente" && <EmitenteTab />}
      {aba === "nfe" && <Nfe />}
      {aba === "ibpt" && <Ibpt />}
      {aba === "sugestoes" && <Sugestoes />}
      {aba === "simulador" && <Simulador />}
      {aba === "historico" && <HistoricoFiscal />}
    </div>
  );
}

