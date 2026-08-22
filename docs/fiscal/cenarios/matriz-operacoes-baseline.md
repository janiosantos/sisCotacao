# Matriz de Cenários Fiscais — Baseline de Engenharia

> Referência de engenharia. Não é tabela legal e não deve ser convertida diretamente em código sem validação da regra vigente.

| ID | Operação | Origem | Destino | Regime | Destinatário | Finalidade | Tratamento |
|---|---|---|---|---|---|---|---|
| SALE-IN-SN | Venda interna | MG | MG | Simples | consumidor | revenda | CFOP + CSOSN + segregação |
| SALE-IN-NORMAL | Venda interna | MG | MG | Normal | contribuinte/consumidor | revenda | CFOP + CST + ICMS |
| SALE-IN-ST-SN | Venda interna ST | MG | MG | Simples | consumidor | revenda | CFOP + CSOSN 500 quando aplicável |
| SALE-IN-ST-NORMAL | Venda interna ST | MG | MG | Normal | consumidor | revenda | CFOP + CST 060 quando aplicável |
| PURCHASE-INTERSTATE | Compra interestadual | outra UF | MG | qualquer | estabelecimento | revenda | crédito/DIFAL/ST conforme contexto |
| PURCHASE-CONSUMPTION | Compra uso/consumo | outra UF | MG | qualquer | estabelecimento | uso/consumo | DIFAL quando aplicável |
| PURCHASE-ASSET | Compra ativo | outra UF | MG | qualquer | estabelecimento | ativo | DIFAL/crédito conforme regra |
| SALE-INTERSTATE | Venda interestadual | MG | outra UF | conforme regime | contribuinte | revenda | ICMS interestadual |
| SALE-INTERSTATE-NON-TAXPAYER | Venda interestadual | MG | outra UF | conforme regime | não contribuinte | consumidor final | ICMS + DIFAL/FCP quando aplicável |
| RETURN-SALE | Devolução | conforme origem | conforme origem | qualquer | origem | devolução | documento original/contexto |
| TRANSFER | Transferência | MG | MG/outra UF | qualquer | próprio | estoque | regras específicas |
| COMPLEMENT | Complemento | conforme operação | conforme operação | qualquer | conforme | ajuste | complemento fiscal |

Fluxo:

```text
FiscalContext -> RuleResolution -> FiscalResult -> DocumentPayload
```

A matriz nunca deve selecionar diretamente uma alíquota.
