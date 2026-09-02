import { useEffect, useState } from "react";
import { api, type Cliente, type ClienteCredito, type CreditoEvento } from "../../api/client";
import { fmtDate, fmtMoney } from "../../ui/format";
import { toast } from "../../ui/dom";
import { temPermissao } from "../../perm";
import { Badge, Button, Field, Input, Modal, Textarea } from "../../ui/ui";

const STATUS_LABEL: Record<string, string> = {
  nao_solicitado: "Não solicitado",
  em_analise: "Em análise",
  aprovado: "Aprovado",
  suspenso: "Suspenso",
  reprovado: "Reprovado",
  expirado: "Expirado",
  bloqueado: "Bloqueado",
};

function statusTone(status: string): "green" | "amber" | "red" | "blue" {
  if (status === "aprovado") return "green";
  if (status === "em_analise") return "amber";
  if (status === "nao_solicitado") return "blue";
  return "red";
}

export function ModalCredito({ cliente, onClose, onSaved }: { cliente: Cliente; onClose: () => void; onSaved: () => void }) {
  const [credito, setCredito] = useState<ClienteCredito | null>(null);
  const [eventos, setEventos] = useState<CreditoEvento[]>([]);
  const [motivo, setMotivo] = useState("");
  const [limite, setLimite] = useState("");
  const [prazo, setPrazo] = useState("30");
  const [inicio, setInicio] = useState(() => new Date().toISOString().slice(0, 10));
  const [fim, setFim] = useState(() => {
    const data = new Date();
    data.setFullYear(data.getFullYear() + 1);
    return data.toISOString().slice(0, 10);
  });
  const [carregando, setCarregando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const podeAprovar = temPermissao("credito", "aprovar");

  const carregar = async () => {
    try {
      const [situacao, historico] = await Promise.all([
        api.consultarCreditoCliente(cliente.id),
        api.historicoCreditoCliente(cliente.id),
      ]);
      setCredito(situacao);
      setEventos(historico.eventos);
      setLimite(String(situacao.limite_aprovado || ""));
      setPrazo(String(situacao.prazo_maximo_dias || 30));
    } catch (e) {
      toast("Erro ao carregar crediário: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, [cliente.id]);

  const executar = async (fn: () => Promise<unknown>) => {
    if (!motivo.trim()) {
      toast("Informe o motivo para manter a trilha de auditoria", "error");
      return;
    }
    setEnviando(true);
    try {
      await fn();
      toast("Crediário atualizado", "success");
      setMotivo("");
      await carregar();
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setEnviando(false);
    }
  };

  const solicitar = () => void executar(() => api.solicitarCreditoCliente(cliente.id, motivo));
  const aprovar = () => {
    const valor = Number(limite.replace(",", "."));
    if (!Number.isFinite(valor) || valor <= 0) {
      toast("Informe um limite aprovado maior que zero", "error");
      return;
    }
    void executar(() => api.aprovarCreditoCliente(cliente.id, {
      limite_aprovado: valor,
      prazo_maximo_dias: Number(prazo) || 0,
      vigencia_inicio: inicio,
      vigencia_fim: fim,
      motivo,
    }));
  };

  return (
    <Modal open onClose={onClose} title={`Crediário · ${cliente.nome}`} wide footer={<Button onClick={onClose}>Fechar</Button>}>
      {carregando || !credito ? <p className="py-8 text-center text-sm text-gray-500">Carregando situação...</p> : (
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3"><div className="text-xs text-gray-500">Situação</div><Badge tone={statusTone(credito.status)}>{STATUS_LABEL[credito.status] || credito.status}</Badge></div>
            <div className="rounded-lg border border-gray-200 p-3"><div className="text-xs text-gray-500">Limite aprovado</div><strong>{fmtMoney(credito.limite_aprovado)}</strong></div>
            <div className="rounded-lg border border-gray-200 p-3"><div className="text-xs text-gray-500">Disponível</div><strong>{fmtMoney(credito.limite_disponivel)}</strong></div>
            <div className="rounded-lg border border-gray-200 p-3"><div className="text-xs text-gray-500">Em atraso</div><strong className={credito.tem_atraso ? "text-red-600" : "text-emerald-600"}>{fmtMoney(credito.saldo_em_atraso)}</strong></div>
          </div>

          <div className="grid gap-3 rounded-lg border border-gray-200 p-4 sm:grid-cols-2">
            <Field label="Motivo / observação obrigatória"><Textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} placeholder="Ex.: documentos conferidos, análise de risco..." /></Field>
            {!podeAprovar ? (
              <div className="flex items-end"><Button variant="primary" onClick={solicitar} disabled={enviando}>Solicitar análise financeira</Button></div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Limite aprovado"><Input inputMode="decimal" value={limite} onChange={(e) => setLimite(e.target.value)} /></Field>
                <Field label="Prazo máximo (dias)"><Input type="number" min={0} value={prazo} onChange={(e) => setPrazo(e.target.value)} /></Field>
                <Field label="Início da vigência"><Input type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} /></Field>
                <Field label="Fim da vigência"><Input type="date" value={fim} onChange={(e) => setFim(e.target.value)} /></Field>
                <div className="flex flex-wrap gap-2 sm:col-span-2">
                  <Button variant="primary" onClick={aprovar} disabled={enviando}>Aprovar crediário</Button>
                  <Button variant="danger" onClick={() => void executar(() => api.bloquearCreditoCliente(cliente.id, motivo))} disabled={enviando}>Bloquear</Button>
                  <Button onClick={() => void executar(() => api.suspenderCreditoCliente(cliente.id, motivo))} disabled={enviando}>Suspender</Button>
                </div>
              </div>
            )}
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-gray-800">Histórico auditável</h3>
            {eventos.length === 0 ? <p className="text-sm text-gray-500">Nenhuma decisão registrada.</p> : (
              <div className="max-h-48 overflow-auto rounded-lg border border-gray-200">
                {eventos.map((evento) => <div key={evento.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 px-3 py-2 text-xs last:border-0"><span><strong>{STATUS_LABEL[evento.status_novo || ""] || evento.tipo_evento}</strong> · {evento.motivo || "sem motivo"}</span><span className="text-gray-500">{evento.usuario_nome || "usuário"} · {fmtDate(evento.criado_em)}</span></div>)}
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
