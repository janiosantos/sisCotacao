// pages/plano_contas/modal-form.tsx — criação/edição de conta do plano de contas.
import { useEffect, useState } from "react";
import { api, type ContaPlano, type ContaPlanoPayload } from "../../api/client";
import { toast } from "../../ui/dom";
import { Button, Field, Input, Modal, Select } from "../../ui/ui";

export function ModalContaForm({
  conta,
  onClose,
  onSaved,
}: {
  conta: ContaPlano | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    codigo: "", nome: "", tipo: "receita" as "receita" | "despesa",
    natureza_custo: "fora_precificacao", politica_rateio: "nao_incluir",
    exige_centro_custo: false, exige_competencia: false, permite_rateio: false,
    componente_variavel: "",
  });

  useEffect(() => {
    setForm({
      codigo: conta?.codigo ?? "", nome: conta?.nome ?? "",
      tipo: (conta?.tipo ?? "receita") as "receita" | "despesa",
      natureza_custo: conta?.natureza_custo ?? "fora_precificacao",
      politica_rateio: conta?.politica_rateio ?? "nao_incluir",
      exige_centro_custo: Boolean(conta?.exige_centro_custo),
      exige_competencia: Boolean(conta?.exige_competencia),
      permite_rateio: Boolean(conta?.permite_rateio),
      componente_variavel: conta?.componente_variavel ?? "",
    });
  }, [conta]);

  const salvar = async () => {
    if (!form.codigo.trim() || !form.nome.trim()) {
      toast("Informe código e nome da conta", "error");
      return;
    }
    const payload: ContaPlanoPayload = {
      codigo: form.codigo.trim(), nome: form.nome.trim(), tipo: form.tipo,
      natureza_custo: form.tipo === "despesa" ? form.natureza_custo : "fora_precificacao",
      politica_rateio: form.tipo === "despesa" ? form.politica_rateio : "nao_incluir",
      exige_centro_custo: form.exige_centro_custo,
      exige_competencia: form.exige_competencia,
      permite_rateio: form.tipo === "despesa" && form.politica_rateio !== "nao_incluir" && form.permite_rateio,
      componente_variavel: form.tipo === "despesa" ? form.componente_variavel || null : null,
    };
    try {
      if (conta) await api.atualizarContaPlano(conta.id, payload);
      else await api.criarContaPlano(payload);
      onClose();
      toast("Conta salva", "success");
      onSaved();
    } catch (e) {
      toast("Erro: " + (e as Error).message, "error");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={conta ? "Editar conta" : "Nova conta"}
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
        <Field label="Código *">
          <Input placeholder="Ex.: 1.01" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} autoFocus />
        </Field>
        <Field label="Nome *">
          <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
        </Field>
        <Field label="Tipo">
          <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value as "receita" | "despesa" })}>
            <option value="receita">Receita</option>
            <option value="despesa">Despesa</option>
          </Select>
        </Field>
        {form.tipo === "despesa" ? (
          <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50/60 p-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Classificação gerencial</h3>
              <p className="mt-1 text-xs leading-5 text-slate-600">Define se esta conta alimenta custos fixos, variáveis ou fica fora da precificação.</p>
            </div>
            <Field label="Natureza do custo">
              <Select value={form.natureza_custo} onChange={(e) => setForm({ ...form, natureza_custo: e.target.value })}>
                <option value="fixa">Despesa fixa</option>
                <option value="variavel">Despesa variável</option>
                <option value="custo_direto">Custo direto</option>
                <option value="cmv">CMV / estoque</option>
                <option value="nao_rateavel">Não rateável</option>
                <option value="fora_precificacao">Fora da precificação</option>
              </Select>
            </Field>
            <Field label="Política de rateio">
              <Select value={form.politica_rateio} onChange={(e) => setForm({ ...form, politica_rateio: e.target.value })}>
                <option value="nao_incluir">Não incluir</option>
                <option value="ratear_faturamento">Ratear por faturamento</option>
                <option value="ratear_unidades">Ratear por unidades</option>
                <option value="ratear_custo_mercadoria">Ratear pelo custo da mercadoria</option>
                <option value="apropriar_direto">Apropriar diretamente</option>
                <option value="revisao_manual">Revisão manual</option>
              </Select>
            </Field>
            <Field label="Componente variável (opcional)">
              <Select value={form.componente_variavel} onChange={(e) => setForm({ ...form, componente_variavel: e.target.value })}>
                <option value="">Nenhum</option>
                <option value="frete">Frete</option>
                <option value="cartao">Cartão</option>
                <option value="comissao">Comissão</option>
                <option value="embalagem">Embalagem</option>
                <option value="outros">Outros</option>
              </Select>
            </Field>
            <div className="grid gap-2 sm:grid-cols-2">
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={form.permite_rateio} onChange={(e) => setForm({ ...form, permite_rateio: e.target.checked })} />
                Elegível para precificação
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={form.exige_competencia} onChange={(e) => setForm({ ...form, exige_competencia: e.target.checked })} />
                Exige competência
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={form.exige_centro_custo} onChange={(e) => setForm({ ...form, exige_centro_custo: e.target.checked })} />
                Exige centro de custo
              </label>
            </div>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
