---
name: product-catalog
description: Modelar cadastro de produtos, variantes/SKUs, atributos JSONB, classificação, preços, custos e inativação histórica em ERP. Usar em qualquer evolução do catálogo.
---

# Product Catalog

Modelar Produto Base separado de Variant. Definir unicidade, ciclo de vida, unidades, marcas, categorias, atributos e validações. Guardar classificação fiscal compartilhada no Produto, admitindo exceção controlada na Variante.

Para cada atributo JSONB, definir chave, tipo, unidade, domínio permitido, obrigatoriedade por categoria e estratégia de indexação. Criar testes de SKU, GTIN, alterações, inativação, importação e compatibilidade com documentos históricos.
