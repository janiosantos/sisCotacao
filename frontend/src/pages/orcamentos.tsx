// pages/orcamentos.tsx — lista de orçamentos de venda salvos (PDV).
// Lifecycle orçamento→pedido (v2.18.0): transições controladas + alçada de desconto.

import { useEffect, useState } from "react";
import { api, type OrcamentoDetalhe, type OrcamentoLista } from "../api/client";
import { fmtDate, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Field, Loading, Modal, PageHeader, Select, StatCard, Table, TBody, THead } from "../ui/ui";
import { STATUS_LABELS, DESCONTO_LABELS, statusTone, descontoTone } from "./orcamentos/tones";
import { ModalDetalhe } from "./orcamentos/modal-detalhe";
import { ModalAutorizar } from "./orcamentos/modal-autorizar";
import { ModalRejeitar } from "./orcamentos/modal-rejeitar";

export default function Orcamentos() {
  const [filtro, setFiltro] = useState("");
  const [lista, setLista] = useState<OrcamentoLista[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [detalhe, setDetalhe] = useState<OrcamentoDetalhe | null>(null);
  const [autorizarDe, setAutorizarDe] = useState<number | null>(null);
  const [rejeitarDe, setRejeitarDe] = useState<{ id: number; motivo: string } | null>(null);
  const [pendentes, setPendentes] = useState<(OrcamentoLista & { desconto_pct?: number; limite_aprovador?: number })[]>([]);
  const [showFila, setShowFila] = useState(false);

  const carregar = async () => {
    setCarregando(true);
    try {
      setLista(await api.listarOrcamentos(filtro));
    } catch (e) {
      toast("Erro ao carregar orçamentos: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtro]);

  const emAberto = lista.filter((o) => ["rascunho", "ativo", "em_analise", "liberado"].includes(o.status)).length;
  const finalizados = lista.filter((o) => o.status === "finalizado").length;
  const totalEmAberto = lista.filter((o) => o.status !== "cancelado").reduce((total, o) => total + (o.total || 0), 0);

  const abrirDetalhe = async (id: number) => {
    try {
      setDetalhe(await api.detalharOrcamento(id));
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const excluir = async (id: number) => {
    if (!window.confirm("Excluir este orçamento?")) return;
    try {
      await api.excluirOrcamento(id);
      setDetalhe(null);
      toast("Orçamento excluído", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const reabrir = async (id: number) => {
    try {
      await api.reabrirOrcamento(id);
      toast("Pedido reaberto para correção — desconto reavaliado", "success");
      setDetalhe(null);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const carregarFila = async () => {
    try {
      setPendentes(await api.pendentesAprovacao());
      setShowFila(true);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <PageHeader
        title="Orçamentos · Pedidos"
        subtitle="Orçamentos de venda montados no PDV (orçamento = proposta; finalizado = pedido)."
        actions={
          <>
            <Button variant="outline" onClick={() => void carregarFila()}>
              Fila de aprovação
            </Button>
            <a
              href="#/pre-venda"
              className="inline-flex items-center justify-center gap-1.5 rounded-md bg-brand-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700"
            >
              + Nova pré-venda
            </a>
          </>
        }
      />

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatCard label="Em andamento" value={String(emAberto)} sub="propostas que ainda exigem ação" tone={emAberto ? "highlight" : "default"} />
        <StatCard label="Pedidos finalizados" value={String(finalizados)} sub="nesta consulta" tone={finalizados ? "success" : "default"} />
        <StatCard label="Valor dos registros" value={fmtMoney(totalEmAberto)} sub={filtro ? "considerando o filtro atual" : "considerando todos os status"} />
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Status">
          <Select aria-label="Filtrar orçamentos por status" value={filtro} onChange={(e) => setFiltro(e.target.value)} className="w-44">
            <option value="">Todos</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </Select>
        </Field>
        <span className="mb-2 text-sm text-gray-500">{lista.length} registro(s) nesta consulta</span>
      </div>

      {carregando ? (
        <Loading />
      ) : lista.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          <p>Nenhum orçamento ainda</p>
          <p>
            Monte uma pré-venda no <a className="text-brand-600 hover:underline" href="#/pre-venda">PDV</a>.
          </p>
        </div>
      ) : (
        <Table>
          <THead cols={["Nº", "Cliente", "Status", "Desconto", "Itens", "Total", "Criada em", ""]} />
          <TBody>
            {lista.map((o) => (
              <tr key={o.id} className="cursor-pointer hover:bg-gray-50" onClick={() => void abrirDetalhe(o.id)}>
                <Cell className="font-mono">{o.numero}</Cell>
                <Cell>{o.cliente || "—"}</Cell>
                <Cell>
                  <Badge tone={statusTone(o.status)}>{STATUS_LABELS[o.status] || o.status}</Badge>
                </Cell>
                <Cell>
                  {o.desconto_status ? (
                    <Badge tone={descontoTone(o.desconto_status)}>{DESCONTO_LABELS[o.desconto_status] || o.desconto_status}</Badge>
                  ) : o.desconto_autorizado ? (
                    <Badge tone="green">Autorizado</Badge>
                  ) : (
                    "—"
                  )}
                </Cell>
                <Cell>{o.n_itens}</Cell>
                <Cell className="font-medium">{fmtMoney(o.total)}</Cell>
                <Cell className="text-xs">{fmtDate(o.criado_em)}</Cell>
                <Cell>
                  <div className="flex justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                    {o.status === "finalizado" &&
                      (o.n_parcelas && o.n_parcelas > 1 ? (
                        <>
                          <a
                            aria-label={`Abrir boleto do pedido ${o.numero}`}
                            className="rounded-md bg-brand-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
                            target="_blank"
                            rel="noreferrer"
                            href={`/orcamentos/${o.id}/boleto`}
                            title="Gerar / imprimir boleto das parcelas"
                          >
                            Boleto
                          </a>
                          <a
                            aria-label={`Abrir contas a receber do pedido ${o.numero}`}
                            className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                            href="#/financeiro"
                            title="Ver contas a receber"
                          >
                            Contas
                          </a>
                        </>
                      ) : null)}
                    <a
                      aria-label={`Imprimir PDF do orçamento ${o.numero}`}
                      className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                      target="_blank"
                      rel="noreferrer"
                      href={`/orcamentos/venda/${o.id}/imprimir`}
                      title="Imprimir / salvar PDF (com campo de assinatura)"
                    >
                      PDF
                    </a>
                    <Button size="sm" variant="ghost" onClick={() => void abrirDetalhe(o.id)} title="Abrir detalhes" aria-label={`Abrir detalhes do orçamento ${o.numero}`}>
                      Detalhes
                    </Button>
                  </div>
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      {detalhe && (
        <ModalDetalhe
          d={detalhe}
          onClose={() => setDetalhe(null)}
          onAutorizar={() => setAutorizarDe(detalhe.id)}
          onRejeitar={() => setRejeitarDe({ id: detalhe.id, motivo: "" })}
          onReabrir={() => void reabrir(detalhe.id)}
          onExcluir={excluir}
        />
      )}

      <ModalAutorizar
        id={autorizarDe}
        onClose={() => setAutorizarDe(null)}
        onOk={async () => {
          setAutorizarDe(null);
          await abrirDetalhe(detalhe?.id ?? (autorizarDe as number));
          await carregar();
        }}
      />

      {rejeitarDe && (
        <ModalRejeitar
          id={rejeitarDe.id}
          onClose={() => setRejeitarDe(null)}
          onOk={async () => {
            setRejeitarDe(null);
            await abrirDetalhe(detalhe?.id ?? (rejeitarDe.id as number));
            await carregar();
          }}
        />
      )}

      {showFila && (
        <Modal
          open
          onClose={() => setShowFila(false)}
          title="Fila de aprovação (desconto)"
          wide
          footer={<Button onClick={() => setShowFila(false)}>Fechar</Button>}
        >
          {pendentes.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">Nenhum desconto pendente para sua alçada.</p>
          ) : (
            <Table>
              <THead cols={["Nº", "Cliente", "Desconto", "Sua alçada", "Total", ""]} />
              <TBody>
                {pendentes.map((p) => (
                  <tr key={p.id}>
                    <Cell className="font-mono">{p.numero}</Cell>
                    <Cell>{p.cliente || "—"}</Cell>
                    <Cell>{p.desconto_pct != null ? `${p.desconto_pct.toFixed(1)}%` : "—"}</Cell>
                    <Cell>{p.limite_aprovador != null ? `${p.limite_aprovador.toFixed(1)}%` : "—"}</Cell>
                    <Cell className="font-medium">{fmtMoney(p.total)}</Cell>
                    <Cell>
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="primary" onClick={() => setAutorizarDe(p.id)}>
                          Autorizar
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setRejeitarDe({ id: p.id, motivo: "" })}>
                          Rejeitar
                        </Button>
                      </div>
                    </Cell>
                  </tr>
                ))}
              </TBody>
            </Table>
          )}
        </Modal>
      )}
    </div>
  );
}

