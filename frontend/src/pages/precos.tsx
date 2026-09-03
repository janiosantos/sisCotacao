// pages/precos.tsx — preços (React + Tailwind).

import { useState } from "react";
import { PageHeader } from "../ui/ui";
import { Tabelas } from "./precos/tabelas";
import { Revisoes } from "./precos/revisoes";
import { Promocoes } from "./precos/promocoes";
import { Simulador } from "./precos/simulador";
import { Historico } from "./precos/historico";
import { ConfiguracaoPrecificacao } from "./precos/configuracao";

type Aba = "tabelas" | "promocoes" | "revisoes" | "simulador" | "historico" | "configuracao";


export default function Precos() {
  const [aba, setAba] = useState<Aba>("tabelas");

  const TABS: { key: Aba; label: string }[] = [
    { key: "tabelas", label: "Tabelas" },
    { key: "promocoes", label: "Promoções" },
    { key: "revisoes", label: "Revisões" },
    { key: "simulador", label: "Simulador" },
    { key: "historico", label: "Histórico" },
    { key: "configuracao", label: "Premissas" },
  ];

  return (
    <div>
      <PageHeader title="Preços" subtitle="Tabelas de preço e promoções." />
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
      {aba === "tabelas" && <Tabelas />}
      {aba === "promocoes" && <Promocoes />}
      {aba === "revisoes" && <Revisoes />}
      {aba === "simulador" && <Simulador />}
      {aba === "historico" && <Historico />}
      {aba === "configuracao" && <ConfiguracaoPrecificacao />}
    </div>
  );
}

// ──────────────────────────────────────────────────────────
//  Tabelas de Preço
