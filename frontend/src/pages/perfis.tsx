// pages/perfis.tsx — gestão de perfis e permissões (RBAC, migração 0075).
// CRUD de perfis novos + matriz de ações por recurso.

import { useEffect, useMemo, useState } from "react";
import { api, type CatalogoPermissoes, type PerfilAcesso } from "../api/client";
import { toast } from "../ui/dom";
import { Badge, Button, Loading, PageHeader } from "../ui/ui";
import { ACOES_PERMISSAO, ROTULO_ACAO } from "../perm";
import { ModalPerfilForm } from "./perfis/modal-form";

export default function Perfis() {
  const [perfis, setPerfis] = useState<PerfilAcesso[] | null>(null);
  const [catalogo, setCatalogo] = useState<CatalogoPermissoes | null>(null);
  const [sel, setSel] = useState<number | null>(null);
  const [matriz, setMatriz] = useState<Record<string, string[]>>({});
  const [salvando, setSalvando] = useState(false);
  const [modalPerfil, setModalPerfil] = useState(false);
  const [editandoPerfil, setEditandoPerfil] = useState<PerfilAcesso | null>(null);

  const carregar = async () => {
    const p = await api.listarPerfis();
    setPerfis(p);
    if (sel == null) {
      const primeiro = p.find((x) => !x.superuser);
      if (primeiro) {
        setSel(primeiro.id);
        setMatriz(primeiro.permissoes);
      }
    } else {
      const atual = p.find((x) => x.id === sel);
      setMatriz(atual?.permissoes ?? {});
    }
  };

  useEffect(() => {
    void (async () => {
      try {
        const [p, c] = await Promise.all([api.listarPerfis(), api.catalogoPermissoes()]);
        setPerfis(p);
        setCatalogo(c);
        const primeiro = p.find((x) => !x.superuser);
        if (primeiro) {
          setSel(primeiro.id);
          setMatriz(primeiro.permissoes);
        }
      } catch (e) {
        toast("Erro ao carregar perfis: " + (e as Error).message, "error");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selecionar = (id: number) => {
    const p = perfis?.find((x) => x.id === id);
    setSel(id);
    setMatriz(p?.permissoes ?? {});
  };

  const alternar = (recurso: string, acao: string) => {
    setMatriz((prev) => {
      const atual = prev[recurso] ?? [];
      const tem = atual.includes(acao);
      const novo = tem ? atual.filter((a) => a !== acao) : [...atual, acao];
      const next = { ...prev };
      if (novo.length) next[recurso] = novo;
      else delete next[recurso];
      return next;
    });
  };

  const salvarMatriz = async () => {
    if (sel == null) return;
    setSalvando(true);
    try {
      await api.gravarPermissoesPerfil(sel, matriz);
      toast("Permissões do perfil salvas", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const abrirNovo = () => {
    setEditandoPerfil(null);
    setModalPerfil(true);
  };

  const abrirEditar = (p: PerfilAcesso) => {
    setEditandoPerfil(p);
    setModalPerfil(true);
  };

  const alternarAtivo = async (p: PerfilAcesso) => {
    try {
      await api.alternarAtivoPerfil(p.id, !p.ativo);
      toast(p.ativo ? "Perfil desativado" : "Perfil ativado", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const excluir = async (p: PerfilAcesso) => {
    if (!window.confirm(`Excluir o perfil "${p.nome}"?`)) return;
    try {
      await api.excluirPerfil(p.id);
      toast("Perfil excluído", "success");
      setSel(null);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const grupos = useMemo(() => {
    const out: { grupo: string; recursos: { codigo: string; nome: string }[] }[] = [];
    for (const r of catalogo?.recursos ?? []) {
      let g = out.find((x) => x.grupo === r.grupo);
      if (!g) {
        g = { grupo: r.grupo, recursos: [] };
        out.push(g);
      }
      g.recursos.push({ codigo: r.codigo, nome: r.nome });
    }
    return out;
  }, [catalogo]);

  if (!perfis || !catalogo) return <Loading />;

  const atual = perfis.find((p) => p.id === sel);

  return (
    <div>
      <PageHeader
        title="Perfis e permissões"
        subtitle="Matriz de ações por recurso. O Administrador é superuser (acesso total). Perfis podem ser criados/renomeados/excluídos."
        actions={
          <Button variant="primary" onClick={abrirNovo}>
            + Novo perfil
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        {perfis.map((p) => (
          <button
            key={p.id}
            onClick={() => selecionar(p.id)}
            className={`rounded-md border px-3 py-1.5 text-sm font-medium ${
              sel === p.id ? "border-brand-600 bg-brand-50 text-brand-700" : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            {p.nome}
            {p.superuser ? <Badge tone="blue">Superuser</Badge> : null}
            {!p.ativo ? <Badge tone="red">Inativo</Badge> : null}
          </button>
        ))}
      </div>

      {atual?.superuser ? (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">
          O perfil <strong>Administrador</strong> é superuser: ignora todas as checagens de permissão. Não utiliza matriz.
        </div>
      ) : atual ? (
        <div className="space-y-6">
          <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3">
            <div>
              <div className="text-sm font-semibold text-gray-800">{atual.nome}</div>
              <div className="text-xs text-gray-500">{atual.descricao || "Sem descrição"}</div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => abrirEditar(atual)}>
                Editar
              </Button>
              <Button size="sm" variant="ghost" onClick={() => alternarAtivo(atual)}>
                {atual.ativo ? "Desativar" : "Ativar"}
              </Button>
              <Button size="sm" variant="danger" onClick={() => excluir(atual)}>
                Excluir
              </Button>
            </div>
          </div>

          {grupos.map((g) => (
            <div key={g.grupo} className="overflow-hidden rounded-lg border border-gray-200 bg-white">
              <div className="border-b border-gray-100 bg-gray-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                {g.grupo}
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Recurso</th>
                      {ACOES_PERMISSAO.map((a) => (
                        <th key={a} className="px-2 py-2 text-center text-xs font-semibold uppercase tracking-wide text-gray-500">
                          {ROTULO_ACAO[a]}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {g.recursos.map((r) => (
                      <tr key={r.codigo} className="hover:bg-gray-50">
                        <td className="px-4 py-1.5 font-medium text-gray-800">{r.nome}</td>
                        {ACOES_PERMISSAO.map((a) => {
                          const tem = (matriz[r.codigo] ?? []).includes(a);
                          return (
                            <td key={a} className="px-2 py-1.5 text-center">
                              <input
                                type="checkbox"
                                checked={tem}
                                onChange={() => alternar(r.codigo, a)}
                                className="h-4 w-4 rounded border-gray-300"
                              />
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
          <div className="flex justify-end">
            <Button variant="primary" disabled={salvando} onClick={() => void salvarMatriz()}>
              {salvando ? "Salvando…" : "Salvar permissões"}
            </Button>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-16 text-center text-sm text-gray-400">
          Selecione um perfil ou crie um novo.
        </div>
      )}

      {modalPerfil && (
        <ModalPerfilForm
          perfil={editandoPerfil}
          onClose={() => setModalPerfil(false)}
          onSaved={carregar}
        />
      )}
    </div>
  );
}