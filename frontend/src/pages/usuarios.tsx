// pages/usuarios.tsx — gestão de usuários (React + Tailwind).
// RBAC: múltiplos perfis + overrides por tela (conceder/negar ações).

import { useEffect, useState } from "react";
import { api, type CatalogoPermissoes, type PerfilAcesso, type Usuario } from "../api/client";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Loading, PageHeader, Table, TBody, THead } from "../ui/ui";
import { ModalUsuarioForm } from "./usuarios/modal-form";

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [perfis, setPerfis] = useState<PerfilAcesso[]>([]);
  const [catalogo, setCatalogo] = useState<CatalogoPermissoes | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Usuario | null>(null);

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
    void (async () => {
      await Promise.all([carregar(), carregarContexto()]);
    })();
  }, []);

  const carregarContexto = async () => {
    try {
      const [p, c] = await Promise.all([api.listarPerfis(), api.catalogoPermissoes()]);
      setPerfis(p.filter((x) => !x.superuser));
      setCatalogo(c);
    } catch {
      setPerfis([]);
      setCatalogo(null);
    }
  };

  const abrir = (u: Usuario | null) => {
    setEditando(u);
    setModalOpen(true);
  };

  const alternar = async (u: Usuario) => {
    try {
      await api.alternarAtivoUsuario(u.id, !u.ativo);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const ehAdmin = (u: Usuario) => (u.perfil_ids ?? []).some((pid) => perfis.find((p) => p.id === pid)?.nome === "Administrador");

  return (
    <div>
      <PageHeader
        title="Usuários"
        subtitle="Contas de acesso com perfis de permissão (RBAC). Um usuário pode ter mais de um perfil e overrides por tela."
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
          <THead cols={["Nome", "Login", "Perfis", "Limite desc.", "Autoriza", "Status", ""]} />
          <TBody>
            {usuarios.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <Cell className="font-medium">{u.nome}</Cell>
                <Cell className="font-mono text-xs">{u.login}</Cell>
                <Cell>
                  <div className="flex flex-wrap gap-1">
                    {(u.perfil_ids ?? []).map((pid) => {
                      const p = perfis.find((x) => x.id === pid);
                      return (
                        <Badge key={pid} tone={p?.nome === "Administrador" ? "blue" : "gray"}>
                          {p?.nome ?? `#${pid}`}
                        </Badge>
                      );
                    })}
                    {!u.perfil_ids?.length ? <span className="text-xs text-gray-400">—</span> : null}
                  </div>
                </Cell>
                <Cell>{ehAdmin(u) ? "—" : `${Number(u.desconto_limite_pct || 0)}%`}</Cell>
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

      {modalOpen && (
        <ModalUsuarioForm
          usuario={editando}
          perfis={perfis}
          catalogo={catalogo}
          onClose={() => setModalOpen(false)}
          onSaved={carregar}
        />
      )}
    </div>
  );
}