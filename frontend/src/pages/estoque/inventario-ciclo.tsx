// pages/estoque/inventario-ciclo.tsx — inventário cíclico (EST-006).
import { useEffect, useState } from "react";
import { api, type InventarioCiclo, type InventarioCicloDetalhe } from "../../api/client";
import { fmtDateTime } from "../../ui/format";
import { toast } from "../../ui/dom";
import { Badge, Button, Field, Input, Loading, Select } from "../../ui/ui";

function statusBadge(status: string) {
  const cor: Record<string, "green" | "amber" | "red" | "gray" | "blue"> = {
    planejado: "blue", em_andamento: "amber", aprovado: "blue",
    ajustado: "green", cancelado: "gray",
    pendente: "gray", conferido: "green", divergente: "red", ok: "green",
  };
  return <Badge tone={cor[status] ?? "gray"}>{status}</Badge>;
}

export function InventarioCiclo({ depositos }: { depositos: { id: number; nome: string }[] }) {
  const [ciclos, setCiclos] = useState<InventarioCiclo[] | null>(null);
  const [dep, setDep] = useState(depositos[0] ? String(depositos[0].id) : "");
  const [nome, setNome] = useState("");
  const [detalhe, setDetalhe] = useState<InventarioCicloDetalhe | null>(null);
  const [contagem, setContagem] = useState<Record<number, string>>({});
  const [obs, setObs] = useState<Record<number, string>>({});
  const [filtro, setFiltro] = useState("");

  const carregar = async () => {
    setCiclos(null);
    try {
      setCiclos((await api.listarCiclosInventario(dep ? Number(dep) : undefined)).ciclos);
    } catch (e) {
      toast("Erro ao carregar ciclos: " + (e as Error).message, "error");
      setCiclos([]);
    }
  };

  useEffect(() => {
    void carregar();
  }, [dep]);

  const abrir = async (id: number) => {
    try {
      setDetalhe((await api.detalheCicloInventario(id)).ciclo);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const criar = async () => {
    if (!dep || !nome.trim()) {
      toast("Depósito e nome são obrigatórios", "error");
      return;
    }
    try {
      const r = await api.criarCicloInventario({ deposito_id: Number(dep), nome: nome.trim() });
      toast(`Ciclo criado com ${r.ciclo.itens ?? ""} itens`, "success");
      setNome("");
      await carregar();
      await abrir(r.ciclo.id);
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const registrar = async (produtoId: number) => {
    if (!detalhe) return;
    const q = contagem[produtoId];
    if (q === undefined || q.trim() === "") {
      toast("Informe a quantidade contada", "error");
      return;
    }
    try {
      const r = await api.registrarContagem(detalhe.id, { produto_id: produtoId, quantidade_contada: Number(q), observacao: obs[produtoId] });
      toast(`Contagem: ${r.contagem.status}${r.contagem.diferenca ? ` (dif ${r.contagem.diferenca})` : ""}`, r.contagem.status === "divergente" ? "error" : "success");
      await abrir(detalhe.id);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const aprovar = async () => {
    if (!detalhe) return;
    try {
      const r = await api.aprovarCicloInventario(detalhe.id);
      toast(`Ciclo aprovado: ${r.resultado.ajustes} ajuste(s) aplicado(s)`, "success");
      await abrir(detalhe.id);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const cancelar = async (id: number) => {
    try {
      await api.cancelarCicloInventario(id);
      toast("Ciclo cancelado", "success");
      setDetalhe(null);
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const filtrados = ciclos?.filter((c) => !filtro || c.nome.toLowerCase().includes(filtro.toLowerCase())) ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Depósito">
          <Select value={dep} onChange={(e) => setDep(e.target.value)} className="w-48">
            {depositos.map((d) => (
              <option key={d.id} value={d.id}>{d.nome}</option>
            ))}
          </Select>
        </Field>
        <Field label="Buscar ciclo">
          <Input value={filtro} onChange={(e) => setFiltro(e.target.value)} placeholder="nome do ciclo…" />
        </Field>
        <Field label="Nome do novo ciclo">
          <Input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ciclo semanal…" />
        </Field>
        <Button variant="primary" onClick={() => void criar()}>+ Criar ciclo</Button>
      </div>

      {ciclos === null ? (
        <Loading />
      ) : (
        <div className="space-y-2">
          {filtrados.length === 0 && <p className="rounded-md border border-dashed border-gray-300 bg-white py-6 text-center text-sm text-gray-400">Nenhum ciclo.</p>}
          {filtrados.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
              <button className="text-left" onClick={() => void abrir(c.id)}>
                <span className="font-medium text-blue-700 hover:underline">{c.nome}</span>
                <span className="ml-2 text-xs text-gray-500">{c.deposito_nome} · {fmtDateTime(c.criado_em)}</span>
              </button>
              <span className="flex items-center gap-2">
                <span className="text-xs text-gray-500">{c.pendentes} pend · {c.conferidas} conf · {c.divergentes} div</span>
                {statusBadge(c.status)}
                {c.status !== "ajustado" && c.status !== "cancelado" && (
                  <Button size="sm" variant="ghost" onClick={() => void cancelar(c.id)}>Cancelar</Button>
                )}
              </span>
            </div>
          ))}
        </div>
      )}

      {detalhe && (
        <div className="rounded-md border border-gray-200 bg-white p-3">
          <div className="mb-2 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-gray-700">{detalhe.nome} · {detalhe.deposito_nome}</h4>
            <div className="flex items-center gap-2">
              {statusBadge(detalhe.status)}
              {detalhe.status === "em_andamento" && (
                <Button size="sm" variant="primary" onClick={() => void aprovar()}>Aprovar e ajustar</Button>
              )}
            </div>
          </div>
          <div className="divide-y divide-gray-100">
            {detalhe.contagens.map((g) => (
              <div key={g.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                <span className="w-48 truncate font-medium">{g.sku} — {g.produto_nome}</span>
                <span className="text-xs text-gray-500">esperado {g.saldo_esperado}</span>
                {g.quantidade_contada != null && (
                  <span className="text-xs text-gray-500">contado {g.quantidade_contada}</span>
                )}
                {g.diferenca != null && g.diferenca !== 0 && (
                  <span className={`text-xs font-semibold ${g.diferenca > 0 ? "text-red-600" : "text-emerald-700"}`}>
                    {g.diferenca > 0 ? "+" : ""}{g.diferenca}
                  </span>
                )}
                {statusBadge(g.status)}
                {g.status === "pendente" && (
                  <span className="flex items-center gap-1">
                    <Input className="w-24" inputMode="decimal" value={contagem[g.produto_id] ?? ""}
                      onChange={(e) => setContagem((s) => ({ ...s, [g.produto_id]: e.target.value }))}
                      placeholder="contado" aria-label={`quantidade contada de ${g.produto_nome}`} />
                    <Input className="w-40" value={obs[g.produto_id] ?? ""}
                      onChange={(e) => setObs((s) => ({ ...s, [g.produto_id]: e.target.value }))}
                      placeholder="observação" aria-label={`observação de ${g.produto_nome}`} />
                    <Button size="sm" variant="primary" onClick={() => void registrar(g.produto_id)}>Salvar</Button>
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}