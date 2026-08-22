# Regra de EAN/GTIN

Quando o SKU possuir GTIN/EAN válido e aplicável, o emissor deve enviar esse identificador no item fiscal. Quando o produto não possuir GTIN, o sistema deve usar `SEM GTIN` conforme contrato do documento e do integrador, sem criar um código falso.

Guardar o valor original informado, status de validação, fonte e data de validação. Não aceitar o mesmo GTIN para SKUs incompatíveis dentro do escopo definido pela empresa.
