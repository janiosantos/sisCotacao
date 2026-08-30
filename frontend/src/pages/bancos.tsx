// pages/bancos.tsx — contas bancárias e extrato (React + Tailwind).

import { useState } from "react";
import { PageHeader } from "../ui/ui";
import { Contas } from "./bancos/contas";
import { Extrato } from "./bancos/extrato";

type Aba = "contas" | "extrato";

export default function Bancos() {
  const [aba, setAba] = useState<Aba>("contas");

  return (
    <div>
      <PageHeader title="Bancos" subtitle="Contas bancárias, extrato e conciliação." />
      <div className="mb-5 flex gap-2 border-b border-gray-200">
        {(["contas", "extrato"] as Aba[]).map((a) => (
          <button
            key={a}
            onClick={() => setAba(a)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              aba === a ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {a === "contas" ? "Contas" : "Extrato"}
          </button>
        ))}
      </div>
      {aba === "contas" ? <Contas /> : <Extrato />}
    </div>
  );
}

