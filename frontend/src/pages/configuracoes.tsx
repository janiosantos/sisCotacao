// pages/configuracoes.tsx — parâmetros do sistema.

import { PageHeader } from "../ui/ui";
import { Flags } from "./configuracoes/flags";
import { GatilhosContabeis } from "./configuracoes/gatilhos-contabeis";
import { Impressora } from "./configuracoes/impressora";
import { Loja } from "./configuracoes/loja";
import { IntegracoesPagamento } from "./configuracoes/integracoes-pagamento";

export default function Configuracoes() {
  return (
    <div>
      <PageHeader title="Configurações" subtitle="Parâmetros do sistema." />
      <div className="max-w-3xl space-y-8">
        <Flags />
        <GatilhosContabeis />
        <Impressora />
        <Loja />
        <IntegracoesPagamento />
      </div>
    </div>
  );
}
