// pages/posvenda.tsx — pós-venda (React + Tailwind).

import { useState } from "react";
import { PageHeader } from "../ui/ui";
import { Acompanhamento } from "./posvenda/acompanhamento";
import { Garantia } from "./posvenda/garantia";
import { Devolucao } from "./posvenda/devolucao";

type Aba = "acompanhamento" | "garantia" | "devolucao";

export default function PosVenda() {
  const [aba, setAba] = useState<Aba>("acompanhamento");

  return (
    <div>
      <PageHeader title="Pós-venda" subtitle="Acompanhamento de clientes e garantia." />
      <div className="mb-5 flex gap-2 border-b border-gray-200">
        {(["acompanhamento", "garantia", "devolucao"] as Aba[]).map((a) => (
          <button
            key={a}
            onClick={() => setAba(a)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              aba === a ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {a === "acompanhamento" ? "Acompanhamento" : a === "garantia" ? "Garantia" : "Devolução / Troca"}
          </button>
        ))}
      </div>
      {aba === "acompanhamento" ? <Acompanhamento /> : aba === "garantia" ? <Garantia /> : <Devolucao />}
    </div>
  );
}
