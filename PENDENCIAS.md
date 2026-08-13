# Pendências do Módulo Fiscal

Lista de tarefas pendentes registradas durante o desenvolvimento. Cada item
deve ser validado com a legislação antes de uso em produção.

## Pendências fiscais (validar com a legislação)

- [ ] **Refinamento do ICMS-ST por convênio/MOC** — base de cálculo de ST,
      redução de base, ICMS retido anteriormente (CST 60 / CSOSN 500),
      ST interestadual e MVA ajustada por convênio. Hoje o motor usa base
      simplificada (`base × (1+MVA) × (1−redução)`).
- [ ] **Validação das regras SIMULADAS** da matriz `fiscal_regra` (CFOP,
      CST/CSOSN, PIS/COFINS) — substituir `fonte = SIMULADO` por regras
      confirmadas com a legislação.
- [ ] **IBS/CBS (Reforma Tributária 2026)** — alíquotas 0,1% (IBS) / 0,9%
      (CBS) são **NECESSITA VALIDAÇÃO**; o cálculo ainda não foi
      implementado (parâmetros já existem no emitente).
- [~] **Cobertura de NCM do catálogo** — 88% coberto (categoria→NCM, sugestão IA);
      restante (~12%) são categorias mistas (EPI, Movimentação de carga, Promoção,
      Limpeza, sem-categoria) que exigem revisão por produto/subcategoria.
- [ ] **Composição de regras (operação × produto)** — implementada (dimensão
      em `fiscal_regra`); registrar auditoria das regras de produto aplicadas
      no snapshot fiscal da venda (fase de snapshot).
- [ ] **Emissão NF-e/NFC-e + SEFAZ** — fases 8/9 (geração XML, assinatura,
      validação XSD, comunicação).
- [ ] **PIS/COFINS** — tabela de semântica de CST (quais destacam) marcada
      como NECESSITA VALIDAÇÃO; produtos monofásicos/alíquota zero/isenção a
      validar por NCM.

## Pendências de emissão (FASE 9 — NF-e/NFC-e)

- [ ] **Homologação SEFAZ** — o XML gerado (`nfe_gerador`) é base estrutural;
      falta **validação XSD**, **assinatura digital** (certificado A1/A3) e
      ciclo de homologação SEFAZ/Focus antes de produção.
- [~] **Código IBGE do município** — `emitente` preenchido (NETFIBRAX —
      Teófilo Otoni/MG, IBGE 3168606); `clientes.c_municipio` disponível; falta
      aplicar IBGE nos clientes antigos (lookup por cidade).
- [~] **Dados do destinatário** — orçamento vincula `cliente_id` e contexto
      (doc, UF, tipo, contribuinte, IE) no PDV; falta endereço/cidade do
      destinatário no XML (dependente de P-5/IBGE).
- [ ] **Chave de acesso** — `aamm` da chave usa `0000` (simplificação); usar a
      data de emissão real.
- [ ] **IBS/CBS no layout** — valores calculados no FiscalResult, mas fora do
      XML até o layout da transição ser definido pela ABNT.
- [ ] **CST/CSOSN por item no XML** — gerador usa CSOSN102/ICMS00 simplificado;
      cobrir CST 10/40/60, CSOSN 101/500, ST, PIS/COFINS por CST completo.
