// pages/orcamentos/modal-detalhe.tsx — detalhe do orçamento/pedido com ações por status.
import { type OrcamentoDetalhe } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { Badge, Button, Cell, Modal, StatCard, Table, TBody, THead } from "../../ui/ui";
import { DESCONTO_LABELS, STATUS_LABELS, descontoTone, statusTone } from "./tones";

export function ModalDetalhe({
  d,
  onClose,
  onAutorizar,
  onRejeitar,
  onReabrir,
  onExcluir,
}: {
  d: OrcamentoDetalhe;
  onClose: () => void;
  onAutorizar: () => void;
  onRejeitar: () => void;
  onReabrir: () => void;
  onExcluir: (id: number) => void;
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
            <Button variant="ghost" permission={{ recurso: "orcamentos", acao: "aprovar" }} onClick={onReabrir}>
              Reabrir para correção
            </Button>
          )}
          {d.status === "finalizado" && d.n_parcelas && d.n_parcelas > 1 ? (
            <>
              <a
                className="inline-flex items-center justify-center gap-1.5 rounded-md bg-brand-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700"
                target="_blank"
                rel="noreferrer"
                href={`/orcamentos/${d.id}/boleto`}
                title="Consultar e imprimir boletos das parcelas"
              >
                Boleto
              </a>
              <a
                className="inline-flex items-center justify-center gap-1.5 rounded-md border border-gray-300 px-3.5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                href="#/financeiro"
                title="Consultar contas a receber"
              >
                Contas a receber
              </a>
            </>
          ) : null}
          {pendenteDesconto && (
            <>
              <Button variant="ghost" permission={{ recurso: "orcamentos", acao: "aprovar" }} onClick={onRejeitar}>
                Rejeitar
              </Button>
              <Button variant="primary" permission={{ recurso: "orcamentos", acao: "aprovar" }} onClick={onAutorizar}>
                Autorizar desconto
              </Button>
            </>
          )}
          <Button variant="danger" permission={{ recurso: "orcamentos", acao: "excluir" }} onClick={() => onExcluir(d.id)}>
            Excluir
          </Button>
        </>
      }
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge tone={statusTone(d.status)}>{STATUS_LABELS[d.status] || d.status}</Badge>
        {d.desconto_status ? <Badge tone={descontoTone(d.desconto_status)}>{DESCONTO_LABELS[d.desconto_status] || d.desconto_status}</Badge> : null}
        {d.virou_pedido ? <Badge tone="blue">Pedido gerado</Badge> : null}
      </div>

      <p className="mb-4 text-sm text-gray-500">
        {d.cliente || "Sem cliente"}
        {d.contato ? " · " + d.contato : ""} · criado em {fmtDate(d.criado_em)}
        {d.virou_pedido ? " · virou pedido" : ""}
        {d.condicao_nome ? " · condição: " + d.condicao_nome : ""}
        {d.n_parcelas && d.n_parcelas > 1 ? ` · ${d.n_parcelas} parcela(s) a receber` : ""}
      </p>

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatCard label="Itens" value={String(d.itens.length)} sub="produtos no documento" />
        <StatCard label="Desconto" value={fmtMoney(d.desconto)} sub={d.desconto_status ? DESCONTO_LABELS[d.desconto_status] || d.desconto_status : "sem desconto"} />
        <StatCard label="Total" value={fmtMoney(d.total)} sub={d.n_parcelas && d.n_parcelas > 1 ? `${d.n_parcelas} parcelas` : "pagamento à vista"} tone="highlight" />
      </div>

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
