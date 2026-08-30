// pages/pre-venda/modal-cadastro-cliente.tsx — cadastro rápido de cliente no PDV.
import { useState } from "react";
import { api, type Cliente } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";

export function ModalCadastroCliente({
  prefill,
  onClose,
  onSaved,
}: {
  prefill: string;
  onClose: () => void;
  onSaved: (c: Cliente) => void;
}) {
  const [nome, setNome] = useState(prefill);
  const [doc, setDoc] = useState("");
  const [tel, setTel] = useState("");
  const [wpp, setWpp] = useState("");
  const [email, setEmail] = useState("");
  const [end, setEnd] = useState("");
  const [cid, setCid] = useState("");
  const [uf, setUf] = useState("");
  const [obs, setObs] = useState("");

  const salvar = async () => {
    if (!nome.trim()) {
      toast("Informe o nome", "error");
      return;
    }
    if (!doc.trim()) {
      toast("CPF obrigatório", "error");
      return;
    }
    try {
      const res = await api.criarCliente({
        nome: nome.trim(),
        doc: doc.trim(),
        tipo_pessoa: "f",
        telefone: tel.trim() || undefined,
        whatsapp: wpp.trim() || undefined,
        email: email.trim() || undefined,
        endereco: end.trim() || undefined,
        cidade: cid.trim() || undefined,
        uf: uf.trim().toUpperCase() || undefined,
        observacoes: obs.trim() || undefined,
      });
      toast("Cliente cadastrado", "success");
      onClose();
      onSaved({ id: res.id, nome: nome.trim(), doc: doc.trim(), tipo_pessoa: "f", email: "", telefone: "", whatsapp: wpp.trim(), endereco: "", cidade: cid.trim(), uf: uf.trim().toUpperCase(), cep: "", vendedor_id: null, vendedor_nome: null, limite_credito: 0, observacoes: "", ativo: true } as Cliente);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Cadastrar cliente"
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={() => void salvar()}>
            Salvar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Nome *">
          <Input value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </Field>
        <Field label="CPF *">
          <Input placeholder="000.000.000-00" value={doc} onChange={(e) => setDoc(e.target.value)} />
        </Field>
        <Field label="Telefone">
          <Input value={tel} onChange={(e) => setTel(e.target.value)} />
        </Field>
        <Field label="WhatsApp">
          <Input value={wpp} onChange={(e) => setWpp(e.target.value)} />
        </Field>
        <Field label="E-mail">
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label="Endereço" className="col-span-3">
            <Input value={end} onChange={(e) => setEnd(e.target.value)} />
          </Field>
          <Field label="Cidade" className="col-span-2">
            <Input value={cid} onChange={(e) => setCid(e.target.value)} />
          </Field>
          <Field label="UF">
            <Input maxLength={2} value={uf} onChange={(e) => setUf(e.target.value)} />
          </Field>
        </div>
        <Field label="Observações">
          <Input value={obs} onChange={(e) => setObs(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}