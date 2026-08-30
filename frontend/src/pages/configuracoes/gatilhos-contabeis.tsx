// pages/configuracoes/gatilhos-contabeis.tsx - módulo Configurações (GatilhosContabeis).

import { useEffect, useState } from "react";
import { api, type ContabilGatilho, type ContaPlano } from "../../api/client";
import { toast } from "../../ui/dom";
import { Badge, Button, Field, Select } from "../../ui/ui";

export function GatilhosContabeis() {
  const [gatilhos, setGatilhos] = useState<ContabilGatilho[] | null>(null);
  const [contas, setContas] = useState<ContaPlano[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [g, c] = await Promise.all([api.listarGatilhosContabil(), api.listarPlanoContas()]);
        setGatilhos(g.gatilhos);
        setContas(c);
      } catch (e) {
        toast("Erro ao carregar gatilhos contábeis: " + (e as Error).message, "error");
      } finally {
        setCarregando(false);
      }
    })();
  }, []);

  const atualizar = (eventoTipo: string, patch: Partial<ContabilGatilho>) => {
    setGatilhos((prev) => prev?.map((g) => (g.evento_tipo === eventoTipo ? { ...g, ...patch } : g)) ?? null);
  };

  const salvar = async (g: ContabilGatilho) => {
    setSalvando(g.evento_tipo);
    try {
      const salvo = await api.configurarGatilhoContabil(g.evento_tipo, {
        ativo: !!g.ativo,
        debito_conta_id: g.debito_conta_id,
        credito_conta_id: g.credito_conta_id,
        descricao: g.descricao,
      });
      setGatilhos((prev) => prev?.map((x) => (x.evento_tipo === g.evento_tipo ? { ...x, ...salvo } : x)) ?? null);
      toast(`Gatilho "${g.evento_tipo}" salvo`, "success");
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(null);
    }
  };

  const rotuloEvento: Record<string, string> = {
    venda_autorizada: "Venda autorizada",
    compra: "Compra",
    ajuste: "Ajuste de estoque",
  };

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="mb-1 text-base font-semibold text-gray-900">Gatilhos contábeis</h2>
      <p className="mb-4 text-sm text-gray-500">
        Conecta eventos de negócio ao lançamento contábil (débito/crédito) com idempotência por evento. Padrão: inativo — ative após definir as contas.
      </p>
      {carregando ? (
        <p className="py-6 text-center text-sm text-gray-400">Carregando…</p>
      ) : !gatilhos || gatilhos.length === 0 ? (
        <p className="py-6 text-center text-sm text-gray-400">Nenhum gatilho configurado.</p>
      ) : (
        <div className="space-y-4">
          {gatilhos.map((g) => (
            <div key={g.evento_tipo} className="rounded-md border border-gray-100 p-3">
              <div className="mb-2 flex items-center gap-2">
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-800">
                  <input
                    type="checkbox"
                    checked={!!g.ativo}
                    onChange={(e) => atualizar(g.evento_tipo, { ativo: e.target.checked })}
                  />
                  {rotuloEvento[g.evento_tipo] || g.evento_tipo}
                </label>
                <Badge tone={g.ativo ? "green" : "gray"}>{g.ativo ? "Ativo" : "Inativo"}</Badge>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="Conta de débito">
                  <Select value={String(g.debito_conta_id ?? "")} onChange={(e) => atualizar(g.evento_tipo, { debito_conta_id: e.target.value ? Number(e.target.value) : null })}>
                    <option value="">—</option>
                    {contas.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.codigo} · {c.nome}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Conta de crédito">
                  <Select value={String(g.credito_conta_id ?? "")} onChange={(e) => atualizar(g.evento_tipo, { credito_conta_id: e.target.value ? Number(e.target.value) : null })}>
                    <option value="">—</option>
                    {contas.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.codigo} · {c.nome}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
              <div className="mt-3 flex justify-end">
                <Button size="sm" variant="primary" disabled={salvando === g.evento_tipo} onClick={() => void salvar(g)}>
                  {salvando === g.evento_tipo ? "Salvando…" : "Salvar"}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}


