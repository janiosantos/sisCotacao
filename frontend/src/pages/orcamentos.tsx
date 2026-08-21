// pages/orcamentos.tsx — lista de orçamentos de venda salvos (PDV).

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
  faturado: "Faturado",
  recebido: "Recebido",
  cancelado: "Cancelado",
};

function statusTone(status: string): "green" | "red" | "amber" | "gray" {
  if (status === "recebido") return "green";
  if (status === "faturado") return "amber";
  if (status === "cancelado") return "red";
  return "gray";
}

export default function Orcamentos() {
  const [filtro, setFiltro] = useState("");
  const [lista, setLista] = useState<OrcamentoLista[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [detalhe, setDetalhe] = useState<OrcamentoDetalhe | null>(null);
  const [autorizarDe, setAutorizarDe] = useState<number | null>(null);
  const [receberDe, setReceberDe] = useState<{ id: number; numero: string; total: number } | null>(null);

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

  const mudarStatus = async (id: number, status: string) => {
    try {
      await api.atualizarOrcamento(id, { status });
      toast("Status atualizado", "success");
      setDetalhe(null);
      await carregar();
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

  return (
    <div>
      <PageHeader
        title="Orçamentos - Mod Teste"
        subtitle="Orçamentos de venda montados no PDV."
        actions={
          <a
            href="#/pdv"
            className="inline-flex items-center justify-center gap-1.5 rounded-md bg-brand-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700"
          >
            + Novo orçamento
          </a>
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
        <span className="mb-2 text-sm text-gray-500">{lista.length} orçamento(s)</span>
      </div>

      {carregando ? (
        <Loading />
      ) : lista.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          <p>Nenhum orçamento ainda</p>
          <p>
            Monte um orçamento de venda no <a className="text-brand-600 hover:underline" href="#/pdv">PDV</a>.
          </p>
        </div>
      ) : (
        <Table>
          <THead cols={["Nº", "Cliente", "Contato", "Status", "Desconto", "Itens", "Total", "Criada em", ""]} />
          <TBody>
            {lista.map((o) => (
              <tr key={o.id} className="cursor-pointer hover:bg-gray-50" onClick={() => void abrirDetalhe(o.id)}>
                <Cell className="font-mono">{o.numero}</Cell>
                <Cell>{o.cliente || "—"}</Cell>
                <Cell>{o.contato || "—"}</Cell>
                <Cell>
                  <Badge tone={statusTone(o.status)}>{STATUS_LABELS[o.status] || o.status}</Badge>
                </Cell>
                <Cell>
                  {o.desconto_autorizado ? <Badge tone="green">Autorizado</Badge> : "—"}
                </Cell>
                <Cell>{o.n_itens}</Cell>
                <Cell className="font-medium">{fmtMoney(o.total)}</Cell>
                <Cell className="text-xs">{fmtDate(o.criado_em)}</Cell>
                <Cell>
                  <div className="flex justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                    {o.status === "faturado" && (
                      <Button size="sm" variant="primary" onClick={() => setReceberDe({ id: o.id, numero: o.numero, total: o.total })}>
                        Receber
                      </Button>
                    )}
                    <a
                      className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                      target="_blank"
                      rel="noreferrer"
                      href={`/orcamentos/venda/${o.id}/imprimir`}
                      title="Imprimir / salvar PDF"
                    >
                      PDF
                    </a>
                    <Button size="sm" variant="ghost" onClick={() => void abrirDetalhe(o.id)} title="Alterar status">
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
          onMudarStatus={mudarStatus}
          onAutorizar={() => setAutorizarDe(detalhe.id)}
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
        }}
      />

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
    </div>
  );
}

function ModalDetalhe({
  d,
  onClose,
  onMudarStatus,
  onAutorizar,
  onExcluir,
  onReceber,
}: {
  d: OrcamentoDetalhe;
  onClose: () => void;
  onMudarStatus: (id: number, status: string) => void;
  onAutorizar: () => void;
  onExcluir: (id: number) => void;
  onReceber: () => void;
}) {
  return (
    <Modal
      open
      onClose={onClose}
      title={d.numero}
      wide
      footer={
        <>
          <a
            className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3.5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            target="_blank"
            rel="noreferrer"
            href={`/orcamentos/venda/${d.id}/imprimir`}
          >
            PDF
          </a>
          <Button variant="primary" onClick={() => window.open(`/orcamentos/venda/${d.id}/imprimir`, "_blank")}>
            Imprimir
          </Button>
          {d.status === "faturado" && (
            <Button variant="primary" onClick={onReceber}>
              Receber
            </Button>
          )}
          <Button onClick={onClose}>Fechar</Button>
          <Button variant="danger" onClick={() => onExcluir(d.id)}>
            Excluir
          </Button>
        </>
      }
    >
      <p className="mb-3 text-sm text-gray-500">
        {d.cliente || "Sem cliente"}
        {d.contato ? " · " + d.contato : ""} · criado em {fmtDate(d.criado_em)}
      </p>
      <div className="mb-4">
        <Field label="Status">
          <Select value={d.status} onChange={(e) => onMudarStatus(d.id, e.target.value)} className="w-48">
            {Object.entries(STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </Select>
        </Field>
      </div>

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

      {d.desconto_autorizado ? (
        <p className="mt-3 text-sm text-emerald-600">
          ✓ Desconto autorizado{d.desconto_autorizado_nome ? ` por ${d.desconto_autorizado_nome}` : ""}
          {d.desconto_autorizado_em ? ` em ${fmtDate(d.desconto_autorizado_em)}` : ""}.
        </p>
      ) : (
        <Button variant="ghost" className="mt-3" onClick={onAutorizar}>
          Autorizar desconto (gerente)
        </Button>
      )}
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
      toast("Informe login e senha do gerente", "error");
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
        Informe as credenciais do gerente (admin ou usuário com permissão) para autorizar o desconto deste orçamento.
      </p>
      <div className="space-y-4">
        <Field label="Login do gerente">
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
