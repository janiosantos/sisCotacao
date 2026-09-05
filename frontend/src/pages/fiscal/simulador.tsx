// pages/fiscal/simulador.tsx - módulo Fiscal (Simulador).
import { ResultadoFiscal } from "./resultado";

import { useEffect, useRef, useState } from "react";
import { api, type Cliente, type FiscalResultado, type ProdutoResumo } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Loading, Select } from "../../ui/ui";
import { ProductSearch } from "../../ui/product-search";

export function Simulador() {
  const [cliBusca, setCliBusca] = useState("");
  const [uf, setUf] = useState("");
  const [tipoCliente, setTipoCliente] = useState("");
  const [contribuinte, setContribuinte] = useState("");
  const [modelo, setModelo] = useState("");
  const [operacao, setOperacao] = useState("venda");
  const [data, setData] = useState(new Date().toISOString().slice(0, 10));
  const [qtd, setQtd] = useState("1");
  const [valor, setValor] = useState("100");
  const [desconto, setDesconto] = useState("0");

  const [sugCli, setSugCli] = useState<Cliente[]>([]);
  const [selecionada, setSelecionada] = useState<ProdutoResumo | null>(null);
  const [clienteId, setClienteId] = useState<number | null>(null);
  const [clienteNome, setClienteNome] = useState<string | null>(null);
  const [resultado, setResultado] = useState<FiscalResultado | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const timerC = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    clearTimeout(timerC.current);
    if (!cliBusca.trim()) {
      setSugCli([]);
      return;
    }
    timerC.current = setTimeout(() => {
      void api
        .buscarClientes(cliBusca.trim())
        .then(setSugCli)
        .catch(() => setSugCli([]));
    }, 200);
    return () => clearTimeout(timerC.current);
  }, [cliBusca]);

  const simular = async () => {
    if (!selecionada) {
      toast("Selecione um produto", "error");
      return;
    }
    const payload: Record<string, unknown> = {
      produto_id: selecionada.id,
      operacao,
      data: data || undefined,
      quantidade: parseFloat(qtd || "1"),
      valor_unitario: parseFloat(valor || "0"),
      desconto: parseFloat(desconto || "0"),
      uf_destino: uf.trim().toUpperCase() || undefined,
      tipo_cliente: tipoCliente || undefined,
      contribuinte: contribuinte || undefined,
      modelo_documento: modelo || undefined,
    };
    if (clienteId) payload.cliente_id = clienteId;
    setCarregando(true);
    setErro("");
    setResultado(null);
    try {
      const sim = await api.simularFiscal(payload);
      setResultado(sim.resultado);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Produto" className="min-w-[260px]">
          <ProductSearch
            selected={selecionada}
            onSelect={(produto) => {
              setSelecionada(produto);
              setResultado(null);
            }}
            onClear={() => {
              setSelecionada(null);
              setResultado(null);
            }}
          />
        </Field>
        <Field label="Cliente (opcional)" className="min-w-[200px]">
          <Input placeholder="Nome, CPF…" value={cliBusca} onChange={(e) => setCliBusca(e.target.value)} />
        </Field>
        <Field label="UF destino">
          <Input maxLength={2} value={uf} onChange={(e) => setUf(e.target.value)} className="w-20" />
        </Field>
        <Field label="Tipo cliente">
          <Select value={tipoCliente} onChange={(e) => setTipoCliente(e.target.value)} className="w-32">
            <option value="">—</option>
            <option value="PF">PF</option>
            <option value="PJ">PJ</option>
          </Select>
        </Field>
        <Field label="Contribuinte">
          <Select value={contribuinte} onChange={(e) => setContribuinte(e.target.value)} className="w-44">
            <option value="">—</option>
            <option value="contribuinte">Contribuinte</option>
            <option value="nao_contribuinte">Não contribuinte</option>
          </Select>
        </Field>
        <Field label="Modelo">
          <Select value={modelo} onChange={(e) => setModelo(e.target.value)} className="w-32">
            <option value="">—</option>
            <option value="55">NF-e 55</option>
            <option value="65">NFC-e 65</option>
          </Select>
        </Field>
        <Field label="Operação">
          <Select value={operacao} onChange={(e) => setOperacao(e.target.value)} className="w-32">
            <option value="venda">Venda</option>
            <option value="compra">Compra</option>
          </Select>
        </Field>
        <Field label="Data">
          <Input type="date" value={data} onChange={(e) => setData(e.target.value)} className="w-40" />
        </Field>
        <Field label="Qtd">
          <Input type="number" min={0} step="any" value={qtd} onChange={(e) => setQtd(e.target.value)} className="w-20" />
        </Field>
        <Field label="Valor unit.">
          <Input type="number" min={0} step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} className="w-24" />
        </Field>
        <Field label="Desconto">
          <Input type="number" min={0} step="0.01" value={desconto} onChange={(e) => setDesconto(e.target.value)} className="w-20" />
        </Field>
        <Button variant="primary" onClick={() => void simular()}>
          Simular
        </Button>
      </div>

      {sugCli.length > 0 ? (
        <div className="mb-3 divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
          {sugCli.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => {
                setClienteId(c.id);
                setClienteNome(c.nome);
                setSugCli([]);
              }}
              className="flex w-full items-center justify-between px-4 py-2 text-left text-sm hover:bg-gray-50"
            >
              <span className="font-medium">
                {c.nome}
                {c.doc ? <span className="ml-2 font-mono text-xs text-gray-400">{c.doc}</span> : null}
              </span>
            </button>
          ))}
        </div>
      ) : null}

      {selecionada ? (
        <p className="mb-2 text-sm text-gray-600">
          Produto: <span className="font-medium">{selecionada.name}</span>
          {selecionada.sku ? <span className="ml-2 font-mono text-xs text-gray-400">{selecionada.sku}</span> : null}
        </p>
      ) : null}
      {clienteNome ? <p className="mb-2 text-sm text-gray-600">Cliente: <span className="font-medium">{clienteNome}</span></p> : null}

      {carregando ? <Loading message="Calculando…" /> : null}
      {erro ? <div className="py-4 text-center text-sm text-gray-400">Erro: {erro}</div> : null}

      {resultado ? <ResultadoFiscal r={resultado} /> : null}
    </div>
  );
}


