// pages/perfis/modal-form.tsx — criação/edição de perfil (nome + descrição).
import { useEffect, useState } from "react";
import { api, type PerfilAcesso } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

export function ModalPerfilForm({
  perfil,
  onClose,
  onSaved,
}: {
  perfil: PerfilAcesso | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [formPerfil, setFormPerfil] = useState({ nome: "", descricao: "" });

  useEffect(() => {
    setFormPerfil({ nome: perfil?.nome ?? "", descricao: perfil?.descricao ?? "" });
  }, [perfil]);

  const salvarPerfil = async () => {
    if (!formPerfil.nome.trim()) {
      toast("Informe o nome do perfil", "error");
      return;
    }
    try {
      if (perfil) {
        await api.atualizarPerfil(perfil.id, { nome: formPerfil.nome.trim(), descricao: formPerfil.descricao.trim() });
        toast("Perfil atualizado", "success");
      } else {
        await api.criarPerfil({ nome: formPerfil.nome.trim(), descricao: formPerfil.descricao.trim() });
        toast("Perfil criado", "success");
      }
      onClose();
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={perfil ? "Editar perfil" : "Novo perfil"}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void salvarPerfil()}>
            Salvar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Nome *">
          <Input value={formPerfil.nome} onChange={(e) => setFormPerfil({ ...formPerfil, nome: e.target.value })} autoFocus />
        </Field>
        <Field label="Descrição">
          <Input value={formPerfil.descricao} onChange={(e) => setFormPerfil({ ...formPerfil, descricao: e.target.value })} />
        </Field>
      </div>
    </Modal>
  );
}