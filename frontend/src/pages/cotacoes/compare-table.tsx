// pages/cotacoes/compare-table.tsx - módulo Cotações (CompareTable).

import { api, type CotacaoFornecedor, type ItemCotacao, type Preco, type Vencedor } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge } from "../../ui/ui";
import { statusLabel, statusTone, qtdEmbalagens } from "./helpers";

export function CompareTable({
  cotacaoId,
  itens,
  fornecedores,
  precoMap,
  vencedorMap,
  isFechada,
  onRegistrado,
}: {
  cotacaoId: number;
  itens: ItemCotacao[];
  fornecedores: CotacaoFornecedor[];
  precoMap: Record<string, Preco>;
  vencedorMap: Record<number, Vencedor>;
  isFechada: boolean;
  onRegistrado: () => void;
}) {
  if (itens.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
        <p>Sem itens</p>
        <p>Adicione produtos a esta cotação.</p>
      </div>
    );
  }
  if (fornecedores.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
        <p>Sem fornecedores convidados</p>
        <p>Adicione ao menos um fornecedor para lançar preços.</p>
      </div>
    );
  }

  const registrar = async (itemId: number, fornecedorId: number, raw: string) => {
    const val = parseFloat(raw.replace(",", "."));
    if (isNaN(val) || val < 0) {
      toast("Preço inválido", "error");
      return;
    }
    try {
      await api.registrarPreco(cotacaoId, { cotacao_item_id: itemId, fornecedor_id: fornecedorId, preco_unitario: val });
      toast("Preço registrado", "success");
      onRegistrado();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const remover = async (itemId: number) => {
    if (!window.confirm("Remover este item da cotação?")) return;
    await api.removerItem(cotacaoId, itemId);
    onRegistrado();
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="min-w-[220px] px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Produto</th>
            <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Qtd.</th>
            {fornecedores.map((f) => (
              <th key={f.fornecedor_id} className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                {f.nome}
                <div className="mt-1">
                  <Badge tone={statusTone(f.status)}>{statusLabel(f.status)}</Badge>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {itens.map((it) => {
            const rowPrecos = fornecedores
              .map((f) => precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`])
              .filter(Boolean);
            const best = rowPrecos.length ? Math.min(...rowPrecos.map((p) => p.preco_unitario)) : null;
            const vencedor = vencedorMap[it.cotacao_item_id];
            return (
              <tr key={it.cotacao_item_id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    {it.imagem_url ? (
                      <img src={it.imagem_url} alt="" className="h-8 w-8 object-contain" />
                    ) : (
                      <span className="w-8" />
                    )}
                    <div>
                      <div className="font-mono text-xs text-gray-500">{it.sku || "#" + it.produto_id}</div>
                      <div className="font-medium">{it.name}</div>
                    </div>
                    {!isFechada && (
                      <button
                        className="ml-auto rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-600"
                        title="Remover item"
                        onClick={() => void remover(it.cotacao_item_id)}
                      >
                        ×
                      </button>
                    )}
                  </div>
                </td>
                <td className="px-4 py-2.5">{it.quantidade}</td>
                {fornecedores.map((f) => {
                  const p = precoMap[`${it.cotacao_item_id}:${f.fornecedor_id}`];
                  const isBest = p != null && best !== null && p.preco_unitario === best;
                  const isWinner = vencedor && vencedor.fornecedor_id === f.fornecedor_id;
                  const delta =
                    p != null && best !== null && !isBest ? (((p.preco_unitario - best) / best) * 100).toFixed(1) : null;
                  const pack =
                    p && p.fator_conversao && p.fator_conversao > 1 && p.unidade_compra ? (
                      <span className="block text-[11px] text-gray-400">
                        {p.unidade_compra} · {p.fator_conversao} un · {qtdEmbalagens(it.quantidade, p.fator_conversao)} emb. ≈{" "}
                        {fmtMoney(p.preco_unitario * p.fator_conversao)}/emb.
                      </span>
                    ) : null;
                  return (
                    <td key={f.fornecedor_id} className={`px-4 py-2.5 ${isWinner || isBest ? "bg-brand-50" : ""}`}>
                      {isFechada ? (
                        <>
                          {p ? fmtMoney(p.preco_unitario) : "—"}
                          {pack}
                          {isWinner ? <span className="mt-1 inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">✓ vencedor</span> : null}
                        </>
                      ) : (
                        <>
                          <input
                            className="w-24 rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none"
                            inputMode="decimal"
                            defaultValue={p != null ? String(p.preco_unitario) : ""}
                            placeholder="R$"
                            onBlur={(e) => void registrar(it.cotacao_item_id, f.fornecedor_id, e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                            }}
                          />
                          {pack}
                          {isBest ? (
                            <span className="mt-1 inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">✓ melhor preço</span>
                          ) : null}
                          {delta ? <span className="ml-1 text-xs text-red-500">+{delta}%</span> : null}
                        </>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}


