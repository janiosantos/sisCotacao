// pages/compras/lista-pedidos-compra.tsx — aba Pedidos de compra (receber com condição + preview de parcelas).
import { useEffect, useState } from "react";
import { api, type CondicaoPagamento, type ParcelaCalculada, type Pedido } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Card, Field, Loading, Modal, Select, StatCard } from "../../ui/ui";

export function ListaPedidosCompra() {
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [recebendo, setRecebendo] = useState<number | null>(null);
  const [modalReceber, setModalReceber] = useState<Pedido | null>(null);
  const [condId, setCondId] = useState("");
  const [condicoesLista, setCondicoesLista] = useState<CondicaoPagamento[]>([]);
  const [preview, setPreview] = useState<{ parcelas: ParcelaCalculada[]; total: number; n: number } | null>(null);

  const carregar = async () => {
    setCarregando(true);
    try {
      setPedidos(await api.listarPedidos());
    } catch {
      setPedidos([]);
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    void api.listarCondicoes().then(setCondicoesLista).catch(() => {});
  }, []);

  const abrirReceber = (p: Pedido) => {
    setModalReceber(p);
    setCondId("");
    setPreview(null);
  };

  const calcularPreview = async (condicaoId: string) => {
    setCondId(condicaoId);
    if (!condicaoId || !modalReceber) {
      setPreview(null);
      return;
    }
    try {
      const r = await api.previewLote({
        modo: "condicao",
        valor: modalReceber.total ?? 0,
        data_base: new Date().toISOString().slice(0, 10),
        condicao_pagamento_id: Number(condicaoId),
      });
      setPreview(r);
    } catch (e) {
      setPreview(null);
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const confirmarRecebimento = async () => {
    if (!modalReceber) return;
    setRecebendo(modalReceber.id);
    try {
      const r = await api.receberPedido(modalReceber.id, {
        condicao_pagamento_id: condId ? Number(condId) : undefined,
      });
      toast(
        r.parcelas && r.parcelas > 1
          ? `Pedido recebido — ${r.parcelas} contas a pagar geradas (estoque atualizado)`
          : "Pedido recebido — estoque e financeiro atualizados",
        "success"
      );
      setModalReceber(null);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setRecebendo(null);
    }
  };

  if (carregando) return <Loading />;

  const pendentes = pedidos.filter((p) => p.status !== "recebido").length;
  const totalAberto = pedidos.filter((p) => p.status !== "recebido").reduce((total, p) => total + (p.total ?? 0), 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatCard label="Pedidos em aberto" value={String(pendentes)} sub="aguardando recebimento" tone={pendentes ? "highlight" : "default"} />
        <StatCard label="Valor em aberto" value={fmtMoney(totalAberto)} sub="entrada ainda não recebida" tone={totalAberto ? "success" : "default"} />
        <StatCard label="Total de pedidos" value={String(pedidos.length)} sub="nesta consulta" />
      </div>
      <Card className="p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-gray-900">Pedidos de compra</h3>
        <p className="mt-1 text-xs text-gray-500">Receba o pedido uma única vez para atualizar estoque e contas a pagar.</p>
      </div>
      {pedidos.length === 0 ? (
        <div className="rounded-md border border-dashed border-gray-300 py-10 text-center text-sm text-gray-400">
          <p>Nenhum pedido de compra ainda.</p>
          <p className="mt-1">Os pedidos aparecem aqui após a aprovação de uma cotação.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {pedidos.map((p) => (
            <div key={p.id} className="rounded-md border border-gray-100 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <b className="text-sm">Pedido {p.numero}</b>
                  <span className="ml-2 text-xs text-gray-400">{p.fornecedor}</span>
                  <Badge tone={p.status === "recebido" ? "green" : "amber"}>
                    {p.status === "recebido" ? "Recebido" : "Enviado"}
                  </Badge>
                </div>
                <div className="text-sm font-semibold">{fmtMoney(p.total ?? 0)}</div>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <a
                  className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  target="_blank"
                  rel="noreferrer"
                  href={`/compras/pedidos/${p.id}/imprimir`}
                >
                  PDF
                </a>
                {p.status !== "recebido" ? (
                  <Button size="sm" variant="primary" onClick={() => void abrirReceber(p)} disabled={recebendo === p.id}>
                    {recebendo === p.id ? "Recebendo…" : "Receber"}
                  </Button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={modalReceber != null}
        onClose={() => setModalReceber(null)}
        title={modalReceber ? `Receber pedido ${modalReceber.numero}` : ""}
        footer={
          <>
            <Button onClick={() => setModalReceber(null)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void confirmarRecebimento()} disabled={recebendo === modalReceber?.id}>
              {recebendo === modalReceber?.id ? "Recebendo…" : "Confirmar recebimento"}
            </Button>
          </>
        }
      >
        {modalReceber ? (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              {modalReceber.fornecedor} · Total {fmtMoney(modalReceber.total ?? 0)}
            </p>
            <p className="text-sm text-gray-500">
              Confirma a entrada de estoque e a geração das <b>contas a pagar</b>. Escolha a condição de pagamento:
            </p>
            <Field label="Condição de pagamento (opcional — vazio = 1 conta em 30 dias)">
              <Select value={condId} onChange={(e) => void calcularPreview(e.target.value)}>
                <option value="">À vista / 30 dias</option>
                {condicoesLista.map((c) => (
                  <option key={c.id} value={c.id}>{c.nome}</option>
                ))}
              </Select>
            </Field>
            {preview ? (
              <div className="rounded-md bg-gray-50 p-3">
                <div className="mb-2 text-xs font-semibold text-gray-500">
                  {preview.n} parcela(s) · total {fmtMoney(preview.total)}
                </div>
                <div className="space-y-1">
                  {preview.parcelas.map((p, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">{i + 1}ª · venc. {fmtDate(p.vencimento)}</span>
                      <span className="font-medium">{fmtMoney(p.valor)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </Modal>
      </Card>
    </div>
  );
}
