// pages/estoque.tsx — estoque (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type Deposito } from "../api/client";
import { PageHeader } from "../ui/ui";
import { Saldo } from "./estoque/saldo";
import { Depositos } from "./estoque/depositos";
import { Movimentos } from "./estoque/movimentos";
import { Lotes } from "./estoque/lotes";
import { Expedicao } from "./estoque/expedicao";
import { Inventario } from "./estoque/inventario";
import { Enderecos } from "./estoque/enderecos";

type Aba = "saldo" | "depositos" | "movimentos" | "lotes" | "expedicao" | "inventario" | "enderecos";

export default function Estoque() {
  const [aba, setAba] = useState<Aba>("saldo");
  const [depositos, setDepositos] = useState<Deposito[]>([]);

  const carregarDepositos = async () => {
    try {
      setDepositos(await api.listarDepositos());
    } catch {
      /* silêncio */
    }
  };

  useEffect(() => {
    void carregarDepositos();
  }, []);

  const TABS: { key: Aba; label: string }[] = [
    { key: "saldo", label: "Saldo" },
    { key: "depositos", label: "Depósitos" },
    { key: "movimentos", label: "Movimentos" },
    { key: "lotes", label: "Lotes" },
    { key: "expedicao", label: "Expedição" },
    { key: "inventario", label: "Inventário" },
  { key: "enderecos", label: "Endereços" },
  ];

  return (
    <div>
      <PageHeader title="Estoque" subtitle="Saldo, depósitos, movimentos e lotes." />
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
      {aba === "saldo" && <Saldo depositos={depositos} />}
      {aba === "depositos" && <Depositos depositos={depositos} onUpdate={carregarDepositos} />}
      {aba === "movimentos" && <Movimentos depositos={depositos} />}
      {aba === "lotes" && <Lotes depositos={depositos} />}
      {aba === "expedicao" && <Expedicao />}
      {aba === "inventario" && <Inventario depositos={depositos} />}
      {aba === "enderecos" && <Enderecos depositos={depositos} />}
    </div>
  );
}

