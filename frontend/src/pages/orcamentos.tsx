// pages/orcamentos.tsx — lista de orçamentos de venda salvos (PDV).
// Lifecycle orçamento→pedido (v2.18.0): transições controladas + alçada de desconto.

import { useEffect, useState } from "react";
import { api, type OrcamentoDetalhe, type OrcamentoLista } from "../api/client";
import { fmtDate, fmtMoney } from "../ui/format";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Field, Input, Loading, Modal, PageHeader, Select, Table, TBody, THead } from "../ui/ui";
import { ModalRecebimento } from "./recebimento";

const STATUS_LABELS: Record<string, string> = {
  rascunho: "Rascunho",
  ativo: "Ativo",
  em_analise: "Em análise",
  liberado: "Liberado",
  finalizado: "Finalizado",
  recebido: "Recebido",
  cancelado: "Cancelado",
  devolvido: "Devolvido",
};

const DESCONTO_LABELS: Record<string, string> = {
  ok: "Dentro da alçada",
  pendente: "Pendente",
  aprovado: "Aprovado",
  rejeitado: "Rejeitado",
};

function statusTone(status: string): "green" | "red" | "amber" | "gray" {
  if (status === "recebido") return "green";
  if (status === "finalizado") return "amber";
  if (status === "cancelado" || status === "devolvido") return "red";
  return "gray";
}

function descontoTone(s: string | undefined): "green" | "red" | "amber" | "gray" {
  if (s === "aprovado" || s === "ok") return "green";
  if (s === "rejeitado") return "red";
  if (s === "pendente") return "amber";
  return "gray";
}

export default function Orcamentos() {
  const [filtro, setFiltro] = useState("");
  const [lista, setLista] = useState<OrcamentoLista[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [detalhe, setDetalhe] = useState<OrcamentoDetalhe | null>(null);
  const [autorizarDe, setAutorizarDe] = useState<number | null>(null);
  const [rejeitarDe, setRejeitarDe] = useState<{ id: number; motivo: string } | null>(null);
  const [receberDe, setReceberDe] = useState<{ id: number; numero: string; total: number } | null>(null);
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

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Status">
          <Select value={filtro} onChange={(e) => setFiltro(e.target.value)} className="w-44">
            <option value="">Todos</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </Select>
        </Field>
        <span className="mb-2 text-sm text-gray-500">{lista.length} registro(s)</span>
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
                            className="rounded-md bg-brand-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
                            target="_blank"
                            rel="noreferrer"
                            href={`/orcamentos/${o.id}/boleto`}
                            title="Gerar / imprimir boleto das parcelas"
                          >
                            Boleto
                          </a>
                          <a
                            className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                            href="#/financeiro"
                            title="Ver contas a receber"
                          >
                            Contas
                          </a>
                        </>
                      ) : (
                        <Button size="sm" variant="primary" onClick={() => setReceberDe({ id: o.id, numero: o.numero, total: o.total })}>
                          Receber
                        </Button>
                      ))}
                    <a
                      className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                      target="_blank"
                      rel="noreferrer"
                      href={`/orcamentos/venda/${o.id}/imprimir`}
                      title="Imprimir / salvar PDF (com campo de assinatura)"
                    >
                      PDF
                    </a>
                    <Button size="sm" variant="ghost" onClick={() => void abrirDetalhe(o.id)} title="Detalhes">
                      ⚙
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
          onReceber={() => setReceberDe({ id: detalhe.id, numero: detalhe.numero, total: detalhe.total })}
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

      {receberDe && (
        <ModalRecebimento
          dados={receberDe}
          onClose={() => setReceberDe(null)}
          onRecebido={() => {
            setReceberDe(null);
            setDetalhe(null);
            void carregar();
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

function ModalDetalhe({
  d,
  onClose,
  onAutorizar,
  onRejeitar,
  onReabrir,
  onExcluir,
  onReceber,
}: {
  d: OrcamentoDetalhe;
  onClose: () => void;
  onAutorizar: () => void;
  onRejeitar: () => void;
  onReabrir: () => void;
  onExcluir: (id: number) => void;
  onReceber: () => void;
}) {
  const pendenteDesconto = d.desconto_status === "pendente";
  return (
    <Modal
      open
      onClose={onClose}
      title={`${d.numero} · ${STATUS_LABELS[d.status] || d.status}`}
      wide
      footer={
        <>
          <Button onClick={onClose}>Fechar</Button>
          {d.status === "finalizado" && (
            <Button variant="ghost" onClick={onReabrir}>
              Reabrir p/ correção
            </Button>
          )}
          {d.status === "finalizado" &&
            (d.n_parcelas && d.n_parcelas > 1 ? (
              <>
                <a
                  className="inline-flex items-center justify-center gap-1.5 rounded-md bg-brand-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700"
                  target="_blank"
                  rel="noreferrer"
                  href={`/orcamentos/${d.id}/boleto`}
                >
                  Boleto
                </a>
                <a
                  className="inline-flex items-center justify-center gap-1.5 rounded-md border border-gray-300 px-3.5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  href="#/financeiro"
                >
                  Contas a receber
                </a>
              </>
            ) : (
              <Button variant="primary" onClick={onReceber}>
                Receber
              </Button>
            ))}
          {pendenteDesconto && (
            <>
              <Button variant="ghost" onClick={onRejeitar}>
                Rejeitar
              </Button>
              <Button variant="primary" onClick={onAutorizar}>
                Autorizar desconto
              </Button>
            </>
          )}
          <Button variant="danger" onClick={() => onExcluir(d.id)}>
            Excluir
          </Button>
        </>
      }
    >
      <p className="mb-3 text-sm text-gray-500">
        {d.cliente || "Sem cliente"}
        {d.contato ? " · " + d.contato : ""} · criado em {fmtDate(d.criado_em)}
        {d.virou_pedido ? " · virou pedido" : ""}
        {d.condicao_nome ? " · condição: " + d.condicao_nome : ""}
        {d.n_parcelas && d.n_parcelas > 1 ? ` · ${d.n_parcelas} parcela(s) a receber` : ""}
      </p>

      {d.desconto_status ? (
        <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
          <Badge tone={descontoTone(d.desconto_status)}>{DESCONTO_LABELS[d.desconto_status] || d.desconto_status}</Badge>
          {d.desconto_status === "rejeitado" && d.desconto_rejeitado_motivo ? (
            <span className="text-xs text-red-600">Motivo: {d.desconto_rejeitado_motivo}</span>
          ) : null}
          {d.desconto_autorizado_nome ? (
            <span className="text-xs text-emerald-600">
              Autorizado por {d.desconto_autorizado_nome}
              {d.desconto_autorizado_em ? ` em ${fmtDate(d.desconto_autorizado_em)}` : ""}
            </span>
          ) : null}
        </div>
      ) : null}

      <Table>
        <THead cols={["Produto", "Qtd.", "Preço", "Desc. %", "Subtotal"]} />
        <TBody>
          {d.itens.map((i, idx) => (
            <tr key={idx} className="hover:bg-gray-50">
              <Cell>
                {i.nome}
                {i.sku ? <div className="font-mono text-xs text-gray-400">{i.sku}</div> : null}
              </Cell>
              <Cell>{i.quantidade}</Cell>
              <Cell>{fmtMoney(i.preco_unitario)}</Cell>
              <Cell>{i.desconto_percentual || 0}%</Cell>
              <Cell className="font-medium">{fmtMoney(i.subtotal || 0)}</Cell>
            </tr>
          ))}
        </TBody>
      </Table>

      <div className="mt-4 flex flex-wrap justify-end gap-4 text-sm">
        <div>
          Subtotal: <span className="font-medium">{fmtMoney(d.subtotal)}</span>
        </div>
        <div>
          Desconto: <span className="font-medium">{fmtMoney(d.desconto)}</span>
        </div>
        <div>
          Total: <span className="font-medium">{fmtMoney(d.total)}</span>
        </div>
      </div>
    </Modal>
  );
}

function ModalAutorizar({ id, onClose, onOk }: { id: number | null; onClose: () => void; onOk: () => void }) {
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [autorizando, setAutorizando] = useState(false);

  useEffect(() => {
    if (id) {
      setLogin("");
      setSenha("");
      setAutorizando(false);
    }
  }, [id]);

  const tentar = async () => {
    if (!id) return;
    if (!login.trim() || !senha) {
      toast("Informe login e senha do aprovador", "error");
      return;
    }
    setAutorizando(true);
    try {
      await api.autorizarDescontoOrcamento(id, { login: login.trim(), senha });
      toast("Desconto autorizado", "success");
      onOk();
    } catch (e) {
      toast("Falha na autorização: " + (e as Error).message, "error");
      setAutorizando(false);
    }
  };

  return (
    <Modal
      open={id !== null}
      onClose={onClose}
      title="Autorizar desconto"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void tentar()} disabled={autorizando}>
            {autorizando ? "Autorizando…" : "Autorizar"}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-gray-500">
        Informe as credenciais de um aprovador (com permissão e alçada suficiente — diferente do vendedor).
      </p>
      <div className="space-y-4">
        <Field label="Login do aprovador">
          <Input autoComplete="username" value={login} onChange={(e) => setLogin(e.target.value)} autoFocus />
        </Field>
        <Field label="Senha">
          <Input
            type="password"
            autoComplete="current-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void tentar();
            }}
          />
        </Field>
      </div>
    </Modal>
  );
}

function ModalRejeitar({ id, onClose, onOk }: { id: number; onClose: () => void; onOk: () => void }) {
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);

  const tentar = async () => {
    if (!motivo.trim()) {
      toast("Informe o motivo da rejeição", "error");
      return;
    }
    setEnviando(true);
    try {
      await api.rejeitarDescontoOrcamento(id, motivo.trim());
      toast("Desconto rejeitado", "success");
      onOk();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
      setEnviando(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Rejeitar desconto"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="danger" onClick={() => void tentar()} disabled={enviando}>
            {enviando ? "Rejeitando…" : "Rejeitar"}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-gray-500">Informe o motivo da rejeição do desconto.</p>
      <Field label="Motivo *">
        <Input value={motivo} onChange={(e) => setMotivo(e.target.value)} autoFocus />
      </Field>
    </Modal>
  );
}