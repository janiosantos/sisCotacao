// pages/usuarios.tsx — gestão de usuários (React + Tailwind).
// RBAC: múltiplos perfis + overrides por tela (conceder/negar ações).

import { useEffect, useState } from "react";
import { api, type CatalogoPermissoes, type PerfilAcesso, type Usuario, type UsuarioPayload } from "../api/client";
import { toast } from "../ui/dom";
import { Badge, Button, Cell, Field, Input, Loading, Modal, PageHeader, Table, TBody, THead } from "../ui/ui";
import { ACOES_PERMISSAO, ROTULO_ACAO } from "../perm";

type OverridesLocal = Record<string, { conceder: string[]; negar: string[] }>;

function normalizarOverrides(u?: Usuario | null): OverridesLocal {
  const raw = (u?.overrides ?? {}) as Record<string, string[] | { conceder: string[]; negar: string[] }>;
  const out: OverridesLocal = {};
  for (const [recurso, val] of Object.entries(raw)) {
    if (Array.isArray(val)) out[recurso] = { conceder: val, negar: [] };
    else out[recurso] = { conceder: val?.conceder ?? [], negar: val?.negar ?? [] };
  }
  return out;
}

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [perfis, setPerfis] = useState<PerfilAcesso[]>([]);
  const [catalogo, setCatalogo] = useState<CatalogoPermissoes | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState<Usuario | null>(null);
  const [form, setForm] = useState({ nome: "", login: "", senha: "", desconto_limite_pct: "0", autoriza_desconto: false });
  const [perfilIds, setPerfilIds] = useState<number[]>([]);
  const [overrides, setOverrides] = useState<OverridesLocal>({});

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
    setForm({
      nome: u?.nome ?? "",
      login: u?.login ?? "",
      senha: "",
      desconto_limite_pct: String(u?.desconto_limite_pct ?? 0),
      autoriza_desconto: !!u?.autoriza_desconto,
    });
    setPerfilIds(u?.perfil_ids ?? []);
    setOverrides(normalizarOverrides(u));
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
    const conceder: Record<string, string[]> = {};
    const negar: Record<string, string[]> = {};
    for (const [recurso, o] of Object.entries(overrides)) {
      if (o.conceder.length) conceder[recurso] = o.conceder;
      if (o.negar.length) negar[recurso] = o.negar;
    }
    const payload: UsuarioPayload = {
      nome: form.nome.trim(),
      login: editando ? editando.login : form.login.trim(),
      senha: form.senha.length ? form.senha : undefined,
      desconto_limite_pct: Number(form.desconto_limite_pct) || 0,
      autoriza_desconto: form.autoriza_desconto,
      perfil_ids: perfilIds,
      conceder,
      negar,
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

  const alternarPerfil = (id: number) => {
    setPerfilIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const alternarOverride = (recurso: string, acao: string, tipo: "conceder" | "negar") => {
    setOverrides((prev) => {
      const atual = prev[recurso] ?? { conceder: [], negar: [] };
      const lista = atual[tipo];
      const tem = lista.includes(acao);
      const nova = tem ? lista.filter((a) => a !== acao) : [...lista, acao];
      const next = { ...prev, [recurso]: { ...atual, [tipo]: nova } };
      const o = next[recurso];
      if (!o.conceder.length && !o.negar.length) delete next[recurso];
      return next;
    });
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

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editando ? "Editar usuário" : "Novo usuário"}
        wide
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
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Nome *">
              <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus />
            </Field>
            <Field label="Login *">
              <Input value={form.login} disabled={!!editando} onChange={(e) => setForm({ ...form, login: e.target.value })} />
            </Field>
          </div>
          <Field label={editando ? "Senha (deixe em branco para manter)" : "Senha *"}>
            <Input type="password" autoComplete="new-password" value={form.senha} onChange={(e) => setForm({ ...form, senha: e.target.value })} />
          </Field>

          <Field label="Perfis de acesso (pode marcar mais de um)">
            <div className="flex flex-wrap gap-2">
              {perfis.map((p) => (
                <label
                  key={p.id}
                  className={`inline-flex cursor-pointer items-center gap-2 rounded-md border px-3 py-1.5 text-sm ${
                    perfilIds.includes(p.id) ? "border-brand-600 bg-brand-50 text-brand-700" : "border-gray-200 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  <input type="checkbox" checked={perfilIds.includes(p.id)} onChange={() => alternarPerfil(p.id)} className="h-4 w-4" />
                  {p.nome}
                </label>
              ))}
            </div>
          </Field>

          {catalogo ? (
            <Field label="Acesso personalizado por tela (conceder extra / negar ação)">
              <div className="max-h-80 space-y-3 overflow-y-auto rounded-md border border-gray-100 p-3">
                {catalogo.recursos.map((r) => (
                  <div key={r.codigo} className="border-b border-gray-100 pb-2 last:border-0">
                    <div className="mb-1 text-xs font-medium text-gray-600">
                      {r.nome} <span className="font-mono text-gray-400">({r.codigo})</span>
                    </div>
                    <div className="grid grid-cols-[auto_1fr_1fr] gap-x-3 gap-y-1">
                      {ACOES_PERMISSAO.map((a) => {
                        const o = overrides[r.codigo] ?? { conceder: [], negar: [] };
                        return (
                          <div key={a} className="contents">
                            <span className="py-0.5 text-xs text-gray-500">{ROTULO_ACAO[a]}</span>
                            <label className="inline-flex items-center gap-1 text-xs text-green-700">
                              <input type="checkbox" checked={o.conceder.includes(a)} onChange={() => alternarOverride(r.codigo, a, "conceder")} className="h-3.5 w-3.5" />
                              Conceder
                            </label>
                            <label className="inline-flex items-center gap-1 text-xs text-red-700">
                              <input type="checkbox" checked={o.negar.includes(a)} onChange={() => alternarOverride(r.codigo, a, "negar")} className="h-3.5 w-3.5" />
                              Negar
                            </label>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </Field>
          ) : null}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Alçada de desconto (%) — concede sem aprovação até este %">
              <Input type="number" min={0} step="0.5" value={form.desconto_limite_pct} onChange={(e) => setForm({ ...form, desconto_limite_pct: e.target.value })} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" className="h-4 w-4 rounded border-gray-300" checked={form.autoriza_desconto} onChange={(e) => setForm({ ...form, autoriza_desconto: e.target.checked })} />
              Pode autorizar desconto acima da alçada (aprovador de outros pedidos)
            </label>
          </div>
        </div>
      </Modal>
    </div>
  );
}