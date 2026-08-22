# Regras de Negócio — Produtos e Variantes

O cadastro deve permitir criar o Produto Base sem variante quando o negócio aceitar venda simples e exigir variantes quando a unidade comercial for diferenciada. Cada variante possui SKU, atributos, preço, custo e estoque próprios.

Atributos como cor, voltagem, tamanho e bitola devem ficar em JSONB quando forem variáveis; NCM, CEST e origem ficam no Produto por padrão, com exceção controlada. Alterações de classificação que afetem documentos futuros devem versionar ou registrar vigência.

Uma variante usada em documento fiscal não pode ter sua descrição histórica alterada retroativamente. A tela pode mostrar o cadastro atual, mas o documento deve usar snapshot.
