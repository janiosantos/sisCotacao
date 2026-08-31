// pages/produtos/relacoes.tsx — relações entre produtos (MDM-005): equivalentes,
// substitutos, acessórios, complementares e componentes de kit.
import { useEffect, useState } from "react";
import { api, type ProdutoRelacionado } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Loading, Select } from "../../ui/ui";

const TIPO_LABEL: Record<string, string> = {
  equivalente: "Equivalente",
  substituto: "Substituto",
  acessorio: "Acessório",
  complementar: "Complementar",
  componente: "Componente de kit",
};

export function Relacoes({ produtoId }: { produtoId: number }) {
  const [rows, setRows] = useState<ProdutoRelacionado[] | null>(null);
  const [relacionadoId, setRelacionadoId] = useState("");
  const [tipo, setTipo] = useState("substituto");
  const [fator, setFator] = useState("1");
  const [prioridade, setPrioridade] = useState("1");
  const [salvando, setSalvando] = useState(false);

  const carregar = async () => {
    setRows(null);
    try {
      setRows((await api.listarRelacionados(produtoId)).relacionados);
    } catch (e) {
      toast("Erro ao carregar relações: " + (e as Error).message, "error");
      setRows([]);
    }
  };

  useEffect(() => {
    void carregar();
  }, [produtoId]);

  const salvar = async () => {
    const rid = Number(relacionadoId);
    if (!rid || rid === produtoId) {
      toast("Informe o ID do produto relacionado (diferente deste)", "error");
      return;
    }
    const f = Number(fator.replace(",", "."));
    if (!(f > 0)) {
      toast("Fator deve ser maior que zero", "error");
      return;
    }
    setSalvando(true);
    try {
      await api.salvarRelacao(produtoId, {
        relacionado_id: rid,
        tipo,
        fator: f,
        prioridade: Number(prioridade) || 1,
      });
      toast("Relação salva", "success");
      setRelacionadoId("");
      setFator("1");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (rid: number) => {
    try {
      await api.excluirRelacao(produtoId, rid);
      toast("Relação removida", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  if (rows === null) return <Loading message="Carregando relações…" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Relações comerciais entre produtos: equivalentes, substitutos (venda só substitui com confirmação),
        acessórios/complementares e componentes de kit. Alterar uma relação não muda documentos antigos.
      </p>

      {rows.length === 0 ? (
        <p className="rounded-md border border-dashed border-gray-300 bg-white py-6 text-center text-sm text-gray-400">
          Nenhuma relação cadastrada.
        </p>
      ) : (
        <div className="space-y-2">
          {rows.map((r) => (
            <div key={r.id} className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
              <span>
                <span className="font-medium">{TIPO_LABEL[r.tipo] || r.tipo}</span>
                {r.direcao === "alvo" ? <span className="ml-1 text-xs text-gray-400">(relacionado aponta p/ este)</span> : null}
                <span className="ml-2 font-mono text-gray-700">{r.outro_sku || "#" + r.outro_id}</span>
                <span className="ml-1">{r.outro_nome}</span>
                {r.fator !== 1 ? <span className="ml-2 text-xs text-gray-500">fator {r.fator}</span> : null}
                <span className="ml-2 text-xs text-gray-400">prio {r.prioridade}</span>
                {!r.aprovado ? <span className="ml-2 text-xs text-amber-600">não aprovado</span> : null}
              </span>
              <Button size="sm" variant="ghost" onClick={() => void excluir(r.id)}>
                ×
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-md border border-dashed border-gray-300 p-3">
        <div className="mb-2 text-xs font-semibold text-gray-500">Nova relação</div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Field label="Tipo">
            <Select value={tipo} onChange={(e) => setTipo(e.target.value)}>
              {Object.entries(TIPO_LABEL).map(([k, l]) => (
                <option key={k} value={k}>
                  {l}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Produto relacionado (ID)">
            <Input type="number" min={1} value={relacionadoId} onChange={(e) => setRelacionadoId(e.target.value)} placeholder="ex.: 12345" />
          </Field>
          <Field label="Fator (qtd por unidade)">
            <Input inputMode="decimal" value={fator} onChange={(e) => setFator(e.target.value)} />
          </Field>
          <Field label="Prioridade">
            <Input type="number" min={1} value={prioridade} onChange={(e) => setPrioridade(e.target.value)} />
          </Field>
          <div className="flex items-end">
            <Button size="sm" variant="primary" onClick={() => void salvar()} disabled={salvando}>
              {salvando ? "Salvando…" : "+ Salvar"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}