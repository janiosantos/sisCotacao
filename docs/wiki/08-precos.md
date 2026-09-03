# Preços e histórico

## Preços (`#/precos`)

**O que é?** Tabelas, regras, promoções e revisões. **Para que serve?** Formar
preço por público/canal e proteger margem. **Papel:** alimenta Catálogo, PDV e
Orçamento.

Crie a tabela, defina vigência, simule preço, confira margem mínima e aplique a
revisão com aprovação necessária. Valide novamente no PDV.

## Formação pelo método divisor

Na aba **Premissas**, o responsável informa faturamento mensal, despesas fixas e
variáveis, tributos, taxa média de cartão, atividade e cenário tributário. Esses
dados ficam salvos no ERP e podem ser revisados a cada período.

Na aba **Simulador**, selecione o produto e informe apenas os custos específicos
do item, como embalagem e frete. O sistema calcula:

```text
Custo de formação = custo líquido + embalagem + frete unitário
Divisor = 1 - (frete% + cartão% + impostos% + comissão% + despesa fixa% + margem%)
Preço sugerido = custo de formação / divisor
```

O **Preço mínimo** repete o cálculo sem margem, enquanto o preço sugerido
preserva a margem desejada. Para o cenário de reforma, IBS/CBS aparecem
separados e são adicionados ao preço sem tributos. O método é uma ferramenta de
gestão e deve ser conferido com a contabilidade e com o preço praticado pelo
mercado; não substitui o motor fiscal por produto e operação.

As tabelas novas usam **Markup divisor**. Tabelas antigas que tinham apenas
markup sobre custo são preservadas como **Markup custo (compatibilidade)** até
que o responsável altere explicitamente o método.

## Histórico de preços (`#/historico`)

**O que é?** Linha do tempo de preços de compra e venda. **Para que serve?**
Negociar fornecedor e entender margem. **Papel:** dá contexto para Compras,
Precificação e Relatórios. Compare unidades equivalentes.

## Atenções

Promoção vencida não deve ser aplicada. Alterar custo, fator ou unidade pode
alterar a comparação; registre uma nova revisão em vez de apagar histórico.

## Auditoria

Regra, tabela, promoção, vigência, revisão e autorização devem ser recuperáveis.

## Capturas

- [Preços](capturas/precos-desktop-dev.png) e [Histórico de preços](capturas/historico-desktop-dev.png).
- [Nova tabela](capturas/precos-nova-tabela-desktop-dev.png) e [Simulador](capturas/precos-simulador-desktop-dev.png).
