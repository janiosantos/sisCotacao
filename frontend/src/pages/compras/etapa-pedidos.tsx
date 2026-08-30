// pages/compras/etapa-pedidos.tsx — pedidos gerados a partir da comparação (Etapa 4).
import { useEffect, useState } from "react";
import { api, type Pedido } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { Loading } from "../../ui/ui";

export function EtapaPedidos({ cotacaoId }: { cotacaoId: number | null }) {
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    void api
      .listarPedidos()
      .then((p) => setPedidos(p.filter((x) => x.cotacao_id === cotacaoId)))
      .catch(() => setPedidos([]))
      .finally(() => setCarregando(false));
  }, [cotacaoId]);

  if (carregando) return <Loading />;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-900">Pedidos gerados — envie para os fornecedores</h3>
      <p className="mb-3 text-sm text-gray-500">Cada pedido consolida os itens vencedores por fornecedor.</p>
      {pedidos.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">Nenhum pedido ainda.</p>
      ) : (
        <div className="space-y-2">
          {pedidos.map((p) => (
            <div key={p.id} className="rounded-md border border-gray-100 p-3">
              <div className="flex items-center justify-between">
                <div>
                  <b className="text-sm">Pedido {p.numero}</b>
                  <span className="ml-2 text-xs text-gray-400">{p.fornecedor}</span>
                </div>
                <div className="text-sm font-semibold">{fmtMoney(p.total ?? 0)}</div>
              </div>
              {p.itens && p.itens.length > 0 ? (
                <div className="mt-2 space-y-0.5">
                  {p.itens.map((it) => (
                    <div key={it.id} className="flex items-center justify-between text-xs text-gray-500">
                      <span>
                        {it.name || "Item"} {it.unidade_compra ? `(${it.unidade_compra}${it.fator_conversao && it.fator_conversao > 1 ? `·${it.fator_conversao}` : ""})` : ""}
                      </span>
                      <span>
                        qtd {it.quantidade}
                        {it.unidade_compra ? ` ${it.unidade_compra}` : ""}
                        {it.fator_conversao && it.fator_conversao > 1 ? ` · ${Math.ceil(it.quantidade / it.fator_conversao)} emb.` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="mt-2 flex gap-2">
                <a className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50" target="_blank" rel="noreferrer" href={`/compras/pedidos/${p.id}/imprimir`}>
                  PDF
                </a>
                {p.whatsapp ? (
                  <a
                    className="rounded-md bg-emerald-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-700"
                    target="_blank"
                    rel="noopener noreferrer"
                    href={`https://wa.me/${p.whatsapp}?text=${encodeURIComponent(
                      "Olá " + p.fornecedor + ", segue nosso pedido de compras número " + p.numero + " referente à cotação aprovada. Aguardamos o faturamento e entrega!"
                    )}`}
                  >
                    WhatsApp
                  </a>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}