# Dossiê de Validação Normativa — Cabos e Fios Elétricos (NCM 8544)

> Data da pesquisa: 2026-08-22 · Pesquisador: agente IA · Regime: Simples Nacional · Operação: venda interna MG→MG (revenda)

## Fontes consultadas

| # | Fonte | URL | Conteúdo usado |
|---|---|---|---|
| 1 | Consulta de Contribuinte nº 105/2021 — SEF/MG | https://www.legisweb.com.br/legislacao/?id=415741 | Enquadramento ST de fios/cabos 8544; exceção uso automotivo (art. 58-A); CEST e MVA das famílias |
| 2 | Protocolo ICMS 8/10 — CONFAZ | https://www.confaz.fazenda.gov.br/legislacao/protocolos/2010/pt008_10 | MVA ORIGINAL 36% p/ 8544 (altera Prot. 198/09 — materiais elétricos) |
| 3 | RICMS/MG 2023 — Anexo VII (Decreto 48.589/2023) | https://www.fazenda.mg.gov.br/empresas/legislacao_tributaria/ricms_2023_seco/anexovii2023_5.html | ⚠️ SEF/MG em manutenção no momento da consulta — confirmar numeração/MVA vigentes |

## Achados

### 1. Uso na construção (caso Casa LM — materiais elétricos)
- NCM **8544** (com 7605, 7614): fios/cabos p/ uso elétrico na construção, exceto uso automotivo
- CEST **12.007.00** (Capítulo 12 — Materiais Elétricos)
- Âmbito: interno MG + PR/RJ/RS/SC (Prot. 198/09), SP (Prot. 39/09), DF (Prot. 18/11)
- **MVA referências**: 40% (regime antigo, item 7.0) · **36% MVA original (Prot. ICMS 8/10)**

### 2. Exceção — uso exclusivamente automotivo (art. 58-A)
- Somente itens 72.0/73.0 Cap.1 (CEST **01.072.00**/**01.073.00**, NCM 8544.20.00/8544.30.00, **MVA 71,78%**)
- Cabos de uso GERAL na construção NÃO são automotivos → permanecem no Capítulo 12

### 3. Substituído já retido (venda interna pelo substituído)
- Revenda interna pelo substituído: **CFOP 5.405** + **CSOSN 500** (Simples) / CST 060 — sem novo destaque de ICMS próprio

## Status dos parâmetros

| Parâmetro | Estado |
|---|---|
| NCM 8544 sujeito a ST (construção, MG interno) | ✅ CONFIRMADO (fontes 1+2) |
| CEST 12.007.00 | ✅ CONFIRMADO (fonte 1) |
| CFOP 5405 / CSOSN 500 p/ substituído já retido | ✅ CONFIRMADO (fonte 1, §3) |
| Exceção automotivo (não-ST) | ✅ CONFIRMADO (fonte 1, art. 58-A) |
| MVA 36% original | 🟡 INFERIDO de Prot. 8/10 — **confirmar contra Anexo VII vigente do Decreto 48.589/2023** (SEF em manutenção) |
| Alíquota interna MG aplicável ao substituído | 🟡 A CONFIRMAR (depende da mercadoria/operação) |

## Regras derivadas (semeadas na migração 0071, estado PUBLISHED)

1. `MG interno · 8544 · revenda · substituído já retido` → **CFOP 5405 · CSOSN 500** · sem novo ICMS próprio
2. `MG interno · 8544 · uso automotivo (exceção)` → **CFOP 5102 · CSOSN 102** · sem ST (tributação no DAS)
