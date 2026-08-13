// pages/usuarios.tsx — gestão de usuários (React + Tailwind).

import { useEffect, useState } from "react";
import { api, type Usuario, type UsuarioPayload } from "../api/client";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Field, Input, Loading, Modal, PageHeader, Select, Table, TBody, THead } from "../ui/ui";

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Usuario | null>(null);
  const [form, setForm] = useState({ nome: "", login: "", senha: "", perfil: "vendedor", desconto_limite_pct: "0", autoriza_desconto: false });

  const carregar = async () => {
    try {
      setUsuarios(await api.listarUsuarios());
    } catch (e) {
      toast("Erro ao carregar usuários: " + (e as Error).message, "error");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrir = (u: Usuario | null) => {
    setEditando(u);
    setForm({
      nome: u?.nome ?? "",
      login: u?.login ?? "",
      senha: "",
      perfil: u?.perfil ?? "vendedor",
      desconto_limite_pct: String(u?.desconto_limite_pct ?? 0),
      autoriza_desconto: !!u?.autoriza_desconto,
    });
    setModalOpen(true);
  };

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome do usuário", "error");
      return;
    }
    if (!editando && form.senha.length < 4) {
      toast("Informe uma senha com pelo menos 4 caracteres", "error");
      return;
    }
    const payload: UsuarioPayload = {
      nome: form.nome.trim(),
      login: editando ? editando.login : form.login.trim(),
      senha: form.senha.length ? form.senha : undefined,
      perfil: form.perfil,
      desconto_limite_pct: Number(form.desconto_limite_pct) || 0,
      autoriza_desconto: form.autoriza_desconto,
    };
    try {
      if (editando) await api.atualizarUsuario(editando.id, payload);
      else await api.criarUsuario(payload);
      setModalOpen(false);
      toast("Usuário salvo", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const alternar = async (u: Usuario) => {
    try {
      await api.alternarAtivoUsuario(u.id, !u.ativo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <div>
      <PageHeader
        title="Usuários"
        subtitle="Contas de acesso ao sistema, com perfil de permissão."
        actions={
          <Button variant="primary" onClick={() => abrir(null)}>
            + Novo usuário
          </Button>
        }
      />
      {carregando ? (
        <Loading />
      ) : usuarios.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Nenhum usuário cadastrado.
        </div>
      ) : (
        <Table>
          <THead cols={["Nome", "Login", "Perfil", "Limite desc.", "Autoriza", "Status", ""]} />
          <TBody>
            {usuarios.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <Cell className="font-medium">{u.nome}</Cell>
                <Cell className="font-mono text-xs">{u.login}</Cell>
                <Cell>
                  <Badge tone={u.perfil === "admin" ? "blue" : "gray"}>{u.perfil}</Badge>
                </Cell>
                <Cell>{u.perfil === "admin" ? "—" : `${Number(u.desconto_limite_pct || 0)}%`}</Cell>
                <Cell>{u.autoriza_desconto ? "Sim" : "—"}</Cell>
                <Cell>
                  <Badge tone={u.ativo ? "green" : "red"}>{u.ativo ? "Ativo" : "Inativo"}</Badge>
                </Cell>
                <Cell>
                  <div className="flex justify-end gap-2">
                    <Button size="sm" onClick={() => abrir(u)}>
                      Editar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => alternar(u)}>
                      {u.ativo ? "Desativar" : "Ativar"}
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
        title={editando ? "Editar usuário" : "Novo usuário"}
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
            <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus />
          </Field>
          <Field label="Login *">
            <Input
              value={form.login}
              disabled={!!editando}
              onChange={(e) => setForm({ ...form, login: e.target.value })}
            />
          </Field>
          <Field label={editando ? "Senha (deixe em branco para manter)" : "Senha *"}>
            <Input
              type="password"
              autoComplete="new-password"
              value={form.senha}
              onChange={(e) => setForm({ ...form, senha: e.target.value })}
            />
          </Field>
          <Field label="Perfil">
            <Select value={form.perfil} onChange={(e) => setForm({ ...form, perfil: e.target.value })}>
              <option value="vendedor">Vendedor</option>
              <option value="admin">Admin</option>
            </Select>
          </Field>
          <Field label="Limite de desconto (%)">
            <Input
              type="number"
              min={0}
              step="0.5"
              value={form.desconto_limite_pct}
              onChange={(e) => setForm({ ...form, desconto_limite_pct: e.target.value })}
            />
          </Field>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300"
              checked={form.autoriza_desconto}
              onChange={(e) => setForm({ ...form, autoriza_desconto: e.target.checked })}
            />
            Pode autorizar desconto acima da alçada (gerente)
          </label>
        </div>
      </Modal>
    </div>
  );
}
