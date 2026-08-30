// pages/cotacoes/modal-add-fornecedor.tsx - módulo Cotações (ModalAddFornecedor).

import { useEffect, useState, useMemo } from "react";
import { api, type CotacaoFornecedor, type Fornecedor } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

export function ModalAddFornecedor({
  cotacaoId,
  jaConvidados,
  todosFornecedores,
  open,
  onClose,
  onSaved,
}: {
  cotacaoId: number;
  jaConvidados: CotacaoFornecedor[];
  todosFornecedores: Fornecedor[];
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nome, setNome] = useState("");
  const [whats, setWhats] = useState("");
  const [email, setEmail] = useState("");

  const jaIds = new Set(jaConvidados.map((f) => f.fornecedor_id));
  const disponiveis = useMemo(() => todosFornecedores.filter((f) => !jaIds.has(f.id)), [todosFornecedores, jaIds]);

  useEffect(() => {
    if (open) {
      setNome("");
      setWhats("");
      setEmail("");
    }
  }, [open]);

  const convidar = async (fid: number) => {
    try {
      await api.convidarFornecedor(cotacaoId, fid);
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const cadastrarConvidar = async () => {
    if (!nome.trim()) {
      toast("Informe o nome do fornecedor", "error");
      return;
    }
    try {
      const res = await api.criarFornecedor({
        nome: nome.trim(),
        whatsapp: whats.trim() || null,
        email: email.trim() || null,
      });
      await api.convidarFornecedor(cotacaoId, res.id);
      toast("Fornecedor cadastrado e convidado", "success");
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Convidar fornecedor"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          {disponiveis.length ? (
            <Button variant="primary" onClick={onClose}>
              Fechar
            </Button>
          ) : (
            <Button variant="primary" onClick={() => void cadastrarConvidar()}>
              Cadastrar e convidar
            </Button>
          )}
        </>
      }
    >
      {disponiveis.length ? (
        <div className="flex max-h-[260px] flex-col gap-1 overflow-y-auto">
          {disponiveis.map((f) => (
            <button
              key={f.id}
              onClick={() => void convidar(f.id)}
              className="rounded-md border border-gray-200 px-3 py-2 text-left text-sm hover:bg-gray-50"
            >
              {f.nome}
            </button>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            Nenhum fornecedor ativo disponível para convidar. Cadastre um novo abaixo — ele já será convidado para esta cotação:
          </p>
          <Field label="Nome *">
            <Input placeholder="Nome da empresa / contato" value={nome} onChange={(e) => setNome(e.target.value)} />
          </Field>
          <Field label="WhatsApp">
            <Input placeholder="55DDNÚMERO (só dígitos)" value={whats} onChange={(e) => setWhats(e.target.value)} />
          </Field>
          <Field label="E-mail">
            <Input value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
        </div>
      )}
    </Modal>
  );
}


