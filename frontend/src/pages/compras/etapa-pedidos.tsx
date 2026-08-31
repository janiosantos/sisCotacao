// pages/compras/etapa-pedidos.tsx — pedidos gerados a partir da comparação (Etapa 4).
import { useEffect, useState } from "react";
import { api, type Pedido } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { Badge, Button, Card, Loading, StatCard } from "../../ui/ui";

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

  const total = pedidos.reduce((sum, pedido) => sum + (pedido.total ?? 0), 0);
  const enviados = pedidos.filter((pedido) => pedido.status !== "recebido").length;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatCard label="Pedidos gerados" value={String(pedidos.length)} sub="um por fornecedor vencedor" tone="success" />
        <StatCard label="Aguardando envio" value={String(enviados)} sub="compartilhe PDF ou WhatsApp" tone={enviados ? "highlight" : "default"} />
        <StatCard label="Valor total" value={fmtMoney(total)} sub="soma desta cotação" />
      </div>
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-gray-900">Pedidos gerados</h3>
        <p className="mb-3 mt-1 text-sm text-gray-500">Cada pedido consolida os itens vencedores por fornecedor. Envie o documento e acompanhe o recebimento na aba de pedidos.</p>
      {pedidos.length === 0 ? (
        <div className="rounded-md border border-dashed border-gray-300 py-10 text-center text-sm text-gray-400">
          <p>Nenhum pedido foi gerado.</p>
          <p className="mt-1">Volte à comparação e selecione uma proposta com preço informado.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {pedidos.map((p) => (
            <div key={p.id} className="rounded-md border border-gray-100 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <b className="text-sm">Pedido {p.numero}</b>
                  <span className="ml-2 text-xs text-gray-400">{p.fornecedor}</span>
                  <Badge tone={p.status === "recebido" ? "green" : "amber"}>{p.status === "recebido" ? "Recebido" : "Aguardando envio"}</Badge>
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
                <Button size="sm" onClick={() => window.open(`/compras/pedidos/${p.id}/imprimir`, "_blank", "noopener,noreferrer")}>Abrir PDF</Button>
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
      </Card>
    </div>
  );
}
