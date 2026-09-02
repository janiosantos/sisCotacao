# Cadastros comerciais: produtos, clientes e parceiros

## Produtos (`#/produtos`)

**O que é?** Cadastro mestre de produto, variações, SKU/EAN, unidade, estoque,
fornecedor, preço e fiscal. **Para que serve?** Evitar que vendas e compras
trabalhem com descrição, unidade ou identificação errada. **Papel:** fonte para
Catálogo, PDV, Compras, Estoque, Fiscal e Relatórios.

Cadastre dados gerais, variações, identificadores, fornecedores e parâmetros por
depósito. Revise completude e perfil fiscal antes de publicar. Etiquetas devem
ser geradas a partir do cadastro correto.

## Clientes (`#/clientes`)

**O que é?** Cadastro do comprador e histórico. **Para que serve?** Identificar
CPF/CNPJ, contatos, condições e situação de crédito. **Papel:** determina se a
venda a prazo pode ocorrer. Pesquise antes de criar e valide o documento.

Solicite crédito quando necessário; apenas o Financeiro aprova, bloqueia,
suspende ou revisa. Consumidor Padrão só compra à vista.

## Parceiros (`#/parceiros`)

**O que é?** Rede de profissionais que indicam e consomem produtos. **Para que
serve?** Controlar indicações, pontos e bônus. **Papel:** liga relacionamento à
venda sem permitir remuneração informal.

Cadastre o profissional, gere indicação, acompanhe conversão e extrato. Bônus
segue `pendente → aprovado → pago`; Financeiro aprova e paga conforme política.

## Vendedores (`#/vendedores`)

Mantém a autoria comercial e a alçada de desconto. Não concede crédito e não
permite recebimento do próprio pedido.

## Categorias (`#/categorias`) e Unidades (`#/unidades`)

Categorias organizam catálogo e relatórios. Unidades padronizam UN, CX, PCT, RL
e conversões. Não exclua uma unidade/categoria usada sem avaliar impactos.

## Auditoria

Alterações cadastrais, documentos, crédito, indicações, pontos e bônus devem ter
responsável, data e motivo quando aplicável.

## Capturas

- [Catálogo](capturas/catalogo-desktop-dev.png), [Produtos](capturas/produtos-desktop-dev.png), [Clientes](capturas/clientes-desktop-dev.png), [Parceiros](capturas/parceiros-desktop-dev.png), [Vendedores](capturas/vendedores-desktop-dev.png), [Categorias](capturas/categorias-desktop-dev.png) e [Unidades](capturas/unidades-desktop-dev.png).
- [Novo produto](capturas/produtos-novo-desktop-dev.png), [etiquetas](capturas/produtos-etiquetas-desktop-dev.png), [importação](capturas/produtos-importar-lote-desktop-dev.png), [novo cliente](capturas/clientes-novo-desktop-dev.png), [crediário](capturas/clientes-crediario-desktop-dev.png), [novo parceiro](capturas/parceiros-novo-desktop-dev.png) e [novo vendedor](capturas/vendedores-novo-desktop-dev.png).
