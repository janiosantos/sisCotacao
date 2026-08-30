// pages/pre-venda/modal-dados-cliente.tsx — dados + limite de crédito do cliente no PDV.
import { useEffect, useState } from "react";
import { api, type Cliente, type ClienteSituacao } from "../../api/client";
import { fmtMoney } from "../../ui/format";
import { Button, Modal } from "../../ui/ui";
import { LinhaInfo } from "./linha-info";

export function ModalDadosCliente({ clienteId, onClose }: { clienteId: number; onClose: () => void }) {
  const [cli, setCli] = useState<Cliente | null>(null);
  const [situacao, setSituacao] = useState<ClienteSituacao | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    let alive = true;
    setCarregando(true);
    void Promise.all([api.detalharCliente(clienteId), api.situacaoCliente(clienteId)])
      .then(([c, s]) => {
        if (!alive) return;
        setCli(c);
        setSituacao(s);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setCarregando(false);
      });
    return () => {
      alive = false;
    };
  }, [clienteId]);

  return (
    <Modal
      open
      onClose={onClose}
      title={cli?.nome ?? "Dados do cliente"}
      footer={<Button onClick={onClose}>Fechar</Button>}
    >
      {carregando ? (
        <p className="py-6 text-center text-sm text-gray-400">Carregando…</p>
      ) : (
        <div className="space-y-3 text-sm">
          <LinhaInfo label="Endereço" valor={[cli?.endereco, cli?.cidade, cli?.uf].filter(Boolean).join(" — ")} />
          <LinhaInfo label="Telefone" valor={cli?.telefone || cli?.whatsapp} />
          <LinhaInfo label="E-mail" valor={cli?.email} />
          <div className="my-2 border-t border-gray-200" />
          <LinhaInfo label="Limite" valor={fmtMoney(situacao?.limite_credito ?? 0)} />
          <LinhaInfo label="Limite utilizado" valor={fmtMoney(situacao?.limite_utilizado ?? 0)} />
          <LinhaInfo label="Limite disponível" valor={fmtMoney(situacao?.limite_disponivel ?? 0)} />
          {situacao?.tem_atraso && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-red-700">
              <strong>Conta em aberto (em atraso):</strong> {fmtMoney(situacao.saldo_em_atraso)}
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}