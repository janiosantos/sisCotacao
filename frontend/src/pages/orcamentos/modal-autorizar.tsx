// pages/orcamentos/modal-autorizar.tsx — autorização de desconto acima da alçada (aprovador).
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

export function ModalAutorizar({ id, onClose, onOk }: { id: number | null; onClose: () => void; onOk: () => void }) {
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