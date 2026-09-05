// pages/historico.tsx — histórico de preços (React + Tailwind).

import { useState } from "react";
import type { ProdutoResumo } from "../api/client";
import { ProductSearch } from "../ui/product-search";
import { PageHeader } from "../ui/ui";
import { Detalhe } from "./historico/detalhe";

export default function Historico() {
  const [produto, setProduto] = useState<ProdutoResumo | null>(null);
  const [produtoId, setProdutoId] = useState<number | null>(null);

  return (
    <div>
      <PageHeader
        title="Histórico de preços"
        subtitle="Evolução de preço por fornecedor ao longo do tempo, com base nas cotações lançadas."
      />
      <div>
        <ProductSearch
          className="mb-4 max-w-xl"
          selected={produto}
          onSelect={(item) => {
            setProduto(item);
            setProdutoId(item.id);
          }}
          onClear={() => {
            setProduto(null);
            setProdutoId(null);
          }}
        />
        {produtoId != null ? <Detalhe produtoId={produtoId} /> : (
          <div className="rounded-lg border border-dashed border-gray-300 bg-white py-12 text-center text-sm text-gray-400">
            Selecione um produto para consultar sua evolução de preços.
          </div>
        )}
      </div>
    </div>
  );
}
