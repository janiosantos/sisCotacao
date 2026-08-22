# Regra de Produtos e Variantes

`Product` representa a mercadoria conceitual e mantém classificação compartilhada. `ProductVariant` representa a unidade comercial vendável. O SKU deve ser único no escopo definido pela empresa; GTIN/EAN deve ser validado e pode variar por SKU.

Usar JSONB para atributos técnicos variáveis, com catálogo de atributos, tipos, unidades e regras de validação. Atributos que participem de preço, estoque, tributação, contabilidade, busca crítica ou integração devem possuir representação estruturada ou projeção indexada.

Não permitir apagar produtos ou variantes utilizados em vendas, movimentos de estoque ou documentos fiscais; usar inativação e preservar referências históricas.
