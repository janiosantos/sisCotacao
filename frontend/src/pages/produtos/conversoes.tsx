// pages/produtos/conversoes.tsx — conversões de unidade por produto/embalagem (MDM-002).
import { useEffect, useState } from "react";
import { api, type ConversaoUnidade } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Loading } from "../../ui/ui";

export function Conversoes({ produtoId }: { produtoId: number }) {
  const [rows, setRows] = useState<ConversaoUnidade[] | null>(null);
  const [origem, setOrigem] = useState("");
  const [destino, setDestino] = useState("");
  const [fator, setFator] = useState("");
  const [base, setBase] = useState("UN");
  const [salvando, setSalvando] = useState(false);
  const [testQtd, setTestQtd] = useState("1");
  const [testDe, setTestDe] = useState("");
  const [testPara, setTestPara] = useState("");
  const [testResult, setTestResult] = useState<string | null>(null);

  const carregar = async () => {
    setRows(null);
    try {
      setRows((await api.listarConversoes(produtoId)).conversoes);
    } catch (e) {
      toast("Erro ao carregar conversões: " + (e as Error).message, "error");
      setRows([]);
    }
  };

  useEffect(() => {
    void carregar();
  }, [produtoId]);

  const salvar = async () => {
    if (!origem.trim() || !destino.trim() || !base.trim()) {
      toast("Informe unidade de origem, destino e unidade base", "error");
      return;
    }
    const f = Number(fator.replace(",", "."));
    if (!(f > 0)) {
      toast("Fator deve ser maior que zero", "error");
      return;
    }
    setSalvando(true);
    try {
      await api.salvarConversao(produtoId, {
        unidade_origem: origem.trim().toUpperCase(),
        unidade_destino: destino.trim().toUpperCase(),
        fator: f,
        unidade_base: base.trim().toUpperCase(),
      });
      toast("Conversão salva", "success");
      setOrigem("");
      setDestino("");
      setFator("");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (o: string) => {
    try {
      await api.excluirConversao(produtoId, o);
      toast("Conversão removida", "success");
      await carregar();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  const testar = async () => {
    if (!testDe.trim() || !testPara.trim()) {
      toast("Informe as unidades de origem e destino do teste", "error");
      return;
    }
    try {
      const r = await api.converterUnidade(produtoId, Number(testQtd) || 1, testDe.trim(), testPara.trim());
      setTestResult(`${r.resultado} ${testPara.trim().toUpperCase()} (fator ${r.fator} · base ${r.unidade_base})`);
    } catch (e) {
      setTestResult(null);
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  if (rows === null) return <Loading message="Carregando conversões…" />;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Define como as embalagens se convertem para a unidade base (ex.: <b>1 CX = 12 UN</b>). O fator informa
        quantas unidades de <b>destino</b> equivalem a 1 unidade de <b>origem</b>.
      </p>

      {rows.length === 0 ? (
        <p className="rounded-md border border-dashed border-gray-300 bg-white py-6 text-center text-sm text-gray-400">
          Nenhuma conversão configurada.
        </p>
      ) : (
        <div className="space-y-2">
          {rows.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-sm">
              <span>
                <b className="font-mono">{c.unidade_origem}</b> = <b className="font-mono">{c.fator}</b>{" "}
                <span className="font-mono">{c.unidade_destino}</span>
                <span className="ml-2 text-xs text-gray-400">base {c.unidade_base} · v{c.versao}</span>
              </span>
              <Button size="sm" variant="ghost" onClick={() => void excluir(c.unidade_origem)}>
                ×
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-md border border-dashed border-gray-300 p-3">
        <div className="mb-2 text-xs font-semibold text-gray-500">Nova conversão</div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Field label="Origem">
            <Input placeholder="CX" maxLength={10} value={origem} onChange={(e) => setOrigem(e.target.value)} />
          </Field>
          <Field label="Destino">
            <Input placeholder="UN" maxLength={10} value={destino} onChange={(e) => setDestino(e.target.value)} />
          </Field>
          <Field label="Fator">
            <Input placeholder="12" inputMode="decimal" value={fator} onChange={(e) => setFator(e.target.value)} />
          </Field>
          <Field label="Unidade base">
            <Input placeholder="UN" maxLength={10} value={base} onChange={(e) => setBase(e.target.value.toUpperCase())} />
          </Field>
        </div>
        <div className="mt-3">
          <Button size="sm" variant="primary" onClick={() => void salvar()} disabled={salvando}>
            {salvando ? "Salvando…" : "+ Salvar conversão"}
          </Button>
        </div>
      </div>

      <div className="rounded-md border border-gray-200 bg-white p-3">
        <div className="mb-2 text-xs font-semibold text-gray-500">Testar conversão</div>
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Qtd">
            <Input className="w-20" inputMode="decimal" value={testQtd} onChange={(e) => setTestQtd(e.target.value)} />
          </Field>
          <Field label="De">
            <Input className="w-20" maxLength={10} value={testDe} onChange={(e) => setTestDe(e.target.value.toUpperCase())} />
          </Field>
          <Field label="Para">
            <Input className="w-20" maxLength={10} value={testPara} onChange={(e) => setTestPara(e.target.value.toUpperCase())} />
          </Field>
          <Button size="sm" onClick={() => void testar()}>Converter</Button>
        </div>
        {testResult ? <p className="mt-2 text-sm font-medium text-emerald-700">{testResult}</p> : null}
      </div>
    </div>
  );
}