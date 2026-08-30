// pages/pre-venda/modal-autorizar.tsx — autorização de desconto acima da alçada (gerente).
import { useState } from "react";
import { api } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

export function ModalAutorizar({
  id,
  descontoPct,
  limitePct,
  finalizar,
  onSalvarAntes,
  onClose,
  onAutorizado,
}: {
  id: number | null;
  descontoPct?: number;
  limitePct?: number;
  finalizar: boolean;
  onSalvarAntes?: () => Promise<{ id: number } | null>;
  onClose: () => void;
  onAutorizado: () => void;
}) {
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [autorizando, setAutorizando] = useState(false);

  const tentar = async () => {
    if (!login.trim() || !senha) {
      toast("Informe login e senha do gerente", "error");
      return;
    }
    setAutorizando(true);
    try {
      let alvoId = id;
      if (alvoId == null && onSalvarAntes) {
        const res = await onSalvarAntes();
        if (!res) {
          setAutorizando(false);
          return;
        }
        alvoId = res.id;
      }
      if (alvoId != null) {
        await api.autorizarDescontoOrcamento(alvoId, { login: login.trim(), senha });
        if (finalizar) {
          await api.atualizarOrcamento(alvoId, { status: "finalizado" });
        }
      }
      toast(finalizar ? "Desconto autorizado e venda finalizada" : "Desconto autorizado", "success");
      onClose();
      onAutorizado();
    } catch (e) {
      toast("Falha na autorização: " + (e as Error).message, "error");
      setAutorizando(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Autorizar desconto"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void tentar()} disabled={autorizando}>
            {autorizando ? "Autorizando…" : finalizar ? "Autorizar e finalizar" : "Autorizar desconto"}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-sm text-gray-500">
        {descontoPct != null && limitePct != null ? (
          <>
            O desconto aplicado (<b>{descontoPct.toFixed(1)}%</b>) está acima da alçada do
            vendedor (<b>{limitePct.toFixed(1)}%</b>). Informe as credenciais de um gerente
            para {finalizar ? "autorizar e finalizar" : "autorizar"}.
          </>
        ) : (
          `O desconto aplicado está acima da alçada do vendedor. Informe as credenciais do gerente para ${finalizar ? "autorizar e finalizar" : "autorizar"}.`
        )}
      </p>
      {id == null && (
        <p className="mb-3 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
          A pré-venda ainda não foi salva — ela será salva para registrar a autorização.
        </p>
      )}
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