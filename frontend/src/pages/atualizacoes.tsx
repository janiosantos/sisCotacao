// pages/atualizacoes.tsx — painel de controle de atualização e versionamento.

import { Fragment, useEffect, useState } from "react";
import {
  api,
  type AtualizacaoLog,
  type NivelRisco,
  type ReleaseManifesto,
  type SistemaStatus,
} from "../api/client";
import { toast } from "../ui/dom";
import { Button, PageHeader } from "../ui/ui";
import { ListaNotas } from "./atualizacoes/lista-notas";

const RISCOS: { nivel: NivelRisco; label: string }[] = [
  { nivel: "critica", label: "Críticas" },
  { nivel: "rotina", label: "Rotina" },
  { nivel: "melhoria", label: "Melhorias" },
  { nivel: "todos", label: "Tudo" },
];

function riscoCor(risco: string): string {
  switch (risco) {
    case "critica":
      return "bg-red-100 text-red-700";
    case "rotina":
      return "bg-amber-100 text-amber-700";
    case "melhoria":
      return "bg-blue-100 text-blue-700";
    case "release":
      return "bg-emerald-100 text-emerald-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
}

function componenteCor(nome: string): string {
  switch (nome) {
    case "backend":
      return "bg-indigo-100 text-indigo-700";
    case "frontend":
      return "bg-purple-100 text-purple-700";
    case "schema":
      return "bg-teal-100 text-teal-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
}


export default function Atualizacoes() {
  const [st, setSt] = useState<SistemaStatus | null>(null);
  const [log, setLog] = useState<AtualizacaoLog[]>([]);
  const [pendentesRelease, setPendentesRelease] = useState<ReleaseManifesto[]>(
    [],
  );
  const [aplicando, setAplicando] = useState<NivelRisco | null>(null);
  const [expandidos, setExpandidos] = useState<Set<number>>(new Set());

  const alternarExpansao = (id: number) => {
    setExpandidos((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const carregar = () => {
    api
      .sistemaStatus()
      .then(setSt)
      .catch(() => toast("Não foi possível ler o status do sistema", "error"));
    api
      .sistemaUpdatesLog()
      .then((r) => setLog(r.log))
      .catch(() => {});
    api
      .releasesPendentes()
      .then((r) => setPendentesRelease(r.pendentes))
      .catch(() => {});
  };

  useEffect(() => {
    carregar();
  }, []);

  const aplicar = async (nivel: NivelRisco) => {
    setAplicando(nivel);
    try {
      const res = await api.aplicarAtualizacoes(nivel);
      if (res.ok) {
        toast(`Atualizações (${nivel}) aplicadas`, "success");
        setSt(res);
        carregar();
      } else {
        toast("Falha: " + (res.error || "erro desconhecido"), "error");
      }
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setAplicando(null);
    }
  };

  const pendentes = st ? st.pending.length : 0;

  return (
    <div>
      <PageHeader
        title="Atualizações"
        subtitle="Controle de atualização e versionamento do sistema."
      />
      <div className="max-w-4xl space-y-6">
        <section className="rounded-lg border border-gray-200 bg-white p-5">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-xs uppercase text-gray-400">App</p>
              <p className="font-mono text-lg">{st?.app_version ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs uppercase text-gray-400">Schema</p>
              <p className="font-mono text-lg">
                {st ? `${st.schema_version} / ${st.schema_max}` : "—"}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase text-gray-400">Migrações</p>
              <p className="font-mono text-lg">
                {st ? `${st.applied}/${st.total_migrations}` : "—"}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase text-gray-400">Estado</p>
              <p
                className={`text-lg font-semibold ${
                  st?.atualizado ? "text-emerald-600" : "text-amber-600"
                }`}
              >
                {st ? (st.atualizado ? "Atualizado" : "Pendente") : "—"}
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-base font-semibold">Aplicar por nível de risco</h2>
          <p className="mb-4 text-sm text-gray-500">
            Críticas sempre são aplicadas antes (não é possível pular a ordem de migração).
          </p>
          <div className="flex flex-wrap gap-2">
            {RISCOS.map((r) => (
              <Button
                key={r.nivel}
                variant={r.nivel === "todos" ? "primary" : "ghost"}
                onClick={() => void aplicar(r.nivel)}
                disabled={aplicando !== null || pendentes === 0}
              >
                {aplicando === r.nivel ? "Aplicando…" : `Aplicar ${r.label}`}
              </Button>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-base font-semibold">Rascunhos pendentes ({pendentesRelease.length})</h2>
          <p className="mb-3 text-sm text-gray-500">
            Releases implementadas em dev e ainda não publicadas. A publicação acontece
            autorizando o deploy no GitHub (Actions → Deploy produção → Run workflow).
          </p>
          {pendentesRelease.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-400">
              Nenhum rascunho — tudo que foi implementado já está em produção.
            </p>
          ) : (
            <div className="space-y-3">
              {pendentesRelease.map((m) => (
                <div key={m.versao} className="rounded-md border border-gray-200 p-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold">{m.versao}</span>
                    {(m.componentes ?? []).map((c) => (
                      <span
                        key={c}
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${componenteCor(c)}`}
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                  <div className="mt-2 space-y-1 text-xs text-gray-600">
                    <ListaNotas titulo="Recursos" cor="text-emerald-700" itens={m.recursos} />
                    <ListaNotas titulo="Melhorias" cor="text-blue-700" itens={m.melhorias} />
                    <ListaNotas titulo="Correções" cor="text-red-700" itens={m.correcoes} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-base font-semibold">Migrações pendentes ({pendentes})</h2>
          {!st ? (
            <p className="py-6 text-center text-sm text-gray-400">Carregando…</p>
          ) : pendentes === 0 ? (
            <p className="py-6 text-center text-sm text-gray-400">
              Nenhuma migração pendente.
            </p>
          ) : (
            <div className="space-y-3">
              {st.pending.map((p) => (
                <div key={p.version} className="rounded-md border border-gray-200 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono font-semibold">{p.version}</span>
                    <span className="font-mono text-sm text-gray-700">{p.name}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riscoCor(p.risco)}`}>
                      {p.risco}
                    </span>
                  </div>
                  {p.mudanca ? (
                    <div className="mt-2 space-y-1 text-xs text-gray-600">
                      <ListaNotas titulo="O que" cor="text-gray-800" itens={p.mudanca.o_que} />
                      <ListaNotas titulo="Porque" cor="text-blue-700" itens={p.mudanca.porque} />
                      <ListaNotas titulo="Novidades" cor="text-emerald-700" itens={p.mudanca.novidades} />
                    </div>
                  ) : (
                    <p className="mt-2 text-xs font-medium text-red-600">
                      ⚠ Sem descrição MUDANCA — o apply será bloqueado até documentar.
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-base font-semibold">Histórico de atualizações</h2>
          {log.length === 0 ? (
            <p className="py-6 text-center text-sm text-gray-400">
              Nenhuma atualização registrada ainda.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400">
                  <th className="py-2">Quando</th>
                  <th>Versão</th>
                  <th>Tipo</th>
                  <th>Schema</th>
                  <th>Origem</th>
                  <th>Usuário</th>
                  <th>Erro</th>
                </tr>
              </thead>
              <tbody>
                {log.map((l) => (
                  <Fragment key={l.id}>
                    <tr className="border-t border-gray-100">
                      <td className="py-2">
                        {l.origem !== "release" && (l.detalhes?.migracoes?.length ?? 0) > 0 ? (
                          <button
                            type="button"
                            className="mr-1 text-brand-600 hover:underline"
                            onClick={() => alternarExpansao(l.id)}
                          >
                            {expandidos.has(l.id) ? "▾" : "▸"}
                          </button>
                        ) : null}
                        {new Date(l.executado_em).toLocaleString("pt-BR")}
                      </td>
                      <td className="font-mono">
                        {l.versao_release ?? l.versao_app}
                      </td>
                      <td>
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${riscoCor(l.nivel)}`}
                        >
                          {l.nivel}
                        </span>
                      </td>
                      <td className="font-mono">
                        {l.origem === "release"
                          ? "—"
                          : `${l.schema_antes} → ${l.schema_depois}`}
                      </td>
                      <td>{l.origem}</td>
                      <td>{l.usuario ?? "—"}</td>
                      <td
                        className="max-w-[12rem] truncate text-red-600"
                        title={l.erro ?? ""}
                      >
                        {l.erro ? l.erro : "—"}
                      </td>
                    </tr>
                    {l.origem === "release" && (
                      <tr className="border-t border-gray-50 bg-gray-50/60">
                        <td colSpan={7}>
                          <div className="space-y-1 py-2 text-xs text-gray-600">
                            {(l.componentes ?? []).length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {(l.componentes ?? []).map((c) => (
                                  <span
                                    key={c}
                                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${componenteCor(c)}`}
                                  >
                                    {c}
                                  </span>
                                ))}
                              </div>
                            )}
                            <ListaNotas titulo="Recursos" cor="text-emerald-700" itens={l.recursos} />
                            <ListaNotas titulo="Melhorias" cor="text-blue-700" itens={l.melhorias} />
                            <ListaNotas titulo="Correções" cor="text-red-700" itens={l.correcoes} />
                          </div>
                        </td>
                      </tr>
                    )}
                    {l.origem !== "release" &&
                      expandidos.has(l.id) &&
                      (l.detalhes?.migracoes?.map((mig, idx) => (
                        <tr key={`${l.id}-mig-${idx}`} className="border-t border-gray-50 bg-gray-50/60">
                          <td colSpan={7}>
                            <div className="space-y-1 py-2 text-xs text-gray-600">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-mono font-semibold text-gray-800">
                                  {mig.nome ?? ""}
                                </span>
                                {mig.risco ? (
                                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riscoCor(mig.risco)}`}>
                                    {mig.risco}
                                  </span>
                                ) : null}
                              </div>
                              <ListaNotas titulo="O que" cor="text-gray-800" itens={mig.o_que} />
                              <ListaNotas titulo="Porque" cor="text-blue-700" itens={mig.porque} />
                              <ListaNotas titulo="Novidades" cor="text-emerald-700" itens={mig.novidades} />
                            </div>
                          </td>
                        </tr>
                      )) ||
                        null)}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}
