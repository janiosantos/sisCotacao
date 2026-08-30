// pages/usuarios/modal-form.tsx — formulário de usuário (perfis + overrides de ações).
import { useEffect, useState } from "react";
import { api, type CatalogoPermissoes, type PerfilAcesso, type Usuario, type UsuarioPayload } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal } from "../../ui/ui";
import { ACOES_PERMISSAO, ROTULO_ACAO } from "../../perm";

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

export function ModalUsuarioForm({
  usuario,
  perfis,
  catalogo,
  onClose,
  onSaved,
}: {
  usuario: Usuario | null;
  perfis: PerfilAcesso[];
  catalogo: CatalogoPermissoes | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({ nome: "", login: "", senha: "", desconto_limite_pct: "0", autoriza_desconto: false });
  const [perfilIds, setPerfilIds] = useState<number[]>([]);
  const [overrides, setOverrides] = useState<OverridesLocal>({});

  useEffect(() => {
    setForm({
      nome: usuario?.nome ?? "",
      login: usuario?.login ?? "",
      senha: "",
      desconto_limite_pct: String(usuario?.desconto_limite_pct ?? 0),
      autoriza_desconto: !!usuario?.autoriza_desconto,
    });
    setPerfilIds(usuario?.perfil_ids ?? []);
    setOverrides(normalizarOverrides(usuario));
  }, [usuario]);

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast("Informe o nome do usuário", "error");
      return;
    }
    if (!usuario && form.senha.length < 4) {
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
      login: usuario ? usuario.login : form.login.trim(),
      senha: form.senha.length ? form.senha : undefined,
      desconto_limite_pct: Number(form.desconto_limite_pct) || 0,
      autoriza_desconto: form.autoriza_desconto,
      perfil_ids: perfilIds,
      conceder,
      negar,
    };
    try {
      if (usuario) await api.atualizarUsuario(usuario.id, payload);
      else await api.criarUsuario(payload);
      onClose();
      toast("Usuário salvo", "success");
      onSaved();
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

  return (
    <Modal
      open
      onClose={onClose}
      title={usuario ? "Editar usuário" : "Novo usuário"}
      wide
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
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Nome *">
            <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} autoFocus />
          </Field>
          <Field label="Login *">
            <Input value={form.login} disabled={!!usuario} onChange={(e) => setForm({ ...form, login: e.target.value })} />
          </Field>
        </div>
        <Field label={usuario ? "Senha (deixe em branco para manter)" : "Senha *"}>
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
  );
}