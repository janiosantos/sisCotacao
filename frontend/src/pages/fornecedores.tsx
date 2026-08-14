// pages/fornecedores.tsx — cadastro de fornecedores (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type Fornecedor, type FornecedorPayload } from "../api/client";
import { toast } from "../ui/dom";
import {
  Badge,
  Button,
  Cell,
  Field,
  Input,
  Loading,
  Modal,
  PageHeader,
  Table,
  TBody,
  THead,
  Textarea,
} from "../ui/ui";

interface Form {
  nome: string;
  whatsapp: string;
  email: string;
  observacoes: string;
}

export default function Fornecedores() {
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Fornecedor | null>(null);
  const [form, setForm] = useState<Form>({ nome: "", whatsapp: "", email: "", observacoes: "" });

  const carregar = async () => {
    try {
      setFornecedores(await api.listarFornecedores());
    } catch (e) {
      toast("Erro ao carregar fornecedores: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = (f?: Fornecedor) => {
    setEditando(f ?? null);
    setForm({
      nome: f?.nome ?? "",
      whatsapp: f?.whatsapp ?? "",
      email: f?.email ?? "",
      observacoes: f?.observacoes ?? "",
    });
    setModalOpen(true);
  };

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome do fornecedor", "error");
      return;
    }
    const payload: FornecedorPayload = {
      nome: form.nome.trim(),
      whatsapp: form.whatsapp.trim() || null,
      email: form.email.trim() || null,
      observacoes: form.observacoes.trim() || null,
    };
    try {
      if (editando) await api.atualizarFornecedor(editando.id, payload);
      else await api.criarFornecedor(payload);
      setModalOpen(false);
      toast("Fornecedor salvo", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alternar = async (f: Fornecedor) => {
    try {
      await api.alternarAtivoFornecedor(f.id, !f.ativo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <PageHeader
        title="Fornecedores"
        subtitle="Cadastro usado para convidar fornecedores nas cotações."
        actions={
          <Button variant="primary" onClick={() => abrir()}>
            + Novo fornecedor
          </Button>
        }
      />

      {carregando ? (
        <Loading message="Carregando fornecedores…" />
      ) : fornecedores.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhum fornecedor cadastrado.
        </div>
      ) : (
        <Table>
          <THead cols={["Nome", "WhatsApp", "E-mail", "Status", ""]} />
          <TBody>
            {fornecedores.map((f) => (
              <tr key={f.id} className="hover:bg-gray-50">
                <Cell>
                  <span className="font-medium">{f.nome}</span>
                </Cell>
                <Cell className="font-mono text-xs">{f.whatsapp || "—"}</Cell>
                <Cell className="text-xs">{f.email || "—"}</Cell>
                <Cell>
                  <Badge tone={f.ativo ? "green" : "red"}>{f.ativo ? "Ativo" : "Inativo"}</Badge>
                </Cell>
                <Cell>
                  <div className="flex justify-end gap-2">
                    <Button size="sm" onClick={() => abrir(f)}>
                      Editar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => alternar(f)}>
                      {f.ativo ? "Desativar" : "Ativar"}
                    </Button>
                  </div>
                </Cell>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editando ? "Editar fornecedor" : "Novo fornecedor"}
        footer={
          <>
            <Button onClick={() => setModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => void salvar()}>
              Salvar
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Nome *">
            <Input
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              autoFocus
            />
          </Field>
          <Field label="WhatsApp">
            <Input
              placeholder="55DDNÚMERO (só dígitos)"
              value={form.whatsapp}
              onChange={(e) => setForm({ ...form, whatsapp: e.target.value })}
            />
          </Field>
          <Field label="E-mail">
            <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </Field>
          <Field label="Observações">
            <Textarea
              value={form.observacoes}
              onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
            />
          </Field>
        </div>
      </Modal>
    </div>
  );
}
