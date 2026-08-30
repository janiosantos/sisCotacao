// pages/cotacoes/summary.tsx - módulo Cotações (Summary).

import { type CotacaoFornecedor, type ItemCotacao, type Vencedor } from "../../api/client";
import { fmtMoney } from "../../ui/format";

export function Summary({ itens, vencedores, fornecedores }: { itens: ItemCotacao[]; vencedores: Vencedor[]; fornecedores: CotacaoFornecedor[] }) {
  const fornecedorNome: Record<number, string> = {};
  for (const f of fornecedores) fornecedorNome[f.fornecedor_id] = f.nome;
  let total = 0;
  const porFornecedor: Record<number, number> = {};
  for (const v of vencedores) {
    total += v.preco_unitario * v.quantidade;
    porFornecedor[v.fornecedor_id] = (porFornecedor[v.fornecedor_id] || 0) + v.preco_unitario * v.quantidade;
  }
  return (
    <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="text-xs font-medium uppercase tracking-wide text-gray-500">Total do pedido</div>
        <div className="mt-1 text-xl font-semibold text-gray-900">{fmtMoney(total)}</div>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="text-xs font-medium uppercase tracking-wide text-gray-500">Itens fechados</div>
        <div className="mt-1 text-xl font-semibold text-gray-900">
          {vencedores.length} / {itens.length}
        </div>
      </div>
      {Object.entries(porFornecedor).map(([fid, val]) => (
        <div key={fid} className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-gray-500">{fornecedorNome[Number(fid)] || "—"}</div>
          <div className="mt-1 text-xl font-semibold text-gray-900">{fmtMoney(val)}</div>
        </div>
      ))}
    </div>
  );
}


