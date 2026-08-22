# Schema de Negócio — ERP de Produtos

## Catálogo

`produtos(id, empresa_id, nome_base, ncm, cest, origem_mercadoria, grupo_tributacao_id, status, created_at, updated_at)`; `skus(id, produto_id, codigo_sku, ean, preco_venda, custo_atual, atributos_jsonb, status)`; `atributos_definicoes(id, categoria_id, chave, tipo, unidade, obrigatorio, valores_permitidos)`.

## Estoque

`estoque_locais(id, empresa_id, nome, tipo, status)`; `estoque_saldos(sku_id, local_id, quantidade_fisica, quantidade_reservada, quantidade_bloqueada, quantidade_transito, version)`; `estoque_movimentos(id, sku_id, local_id, tipo, quantidade, custo_unitario, documento_origem_tipo, documento_origem_id, movimento_estorno_id, idempotency_key, occurred_at)`.

## Fiscal e vendas

`naturezas_operacao`; `grupo_tributacao`; `matriz_fiscal_icms`; `matriz_fiscal_pis_cofins`; `pedidos`; `pedidos_itens`; `notas_fiscais`; `notas_fiscais_itens`; `fiscal_events`; `outbox_events`.

## Contábil e financeiro

`contas_contabeis`; `regras_contabilizacao`; `lancamentos`; `lancamentos_itens`; `contas_receber`; `titulos_receber`; `periodos_contabeis`.

## Constraints essenciais

Usar FK para referências, CHECK para quantidades e valores, UNIQUE por empresa para SKU e referência fiscal, índice por idempotency key, índice por vigência e contexto fiscal, e proteção contra alteração de movimento, item fiscal autorizado e lançamento de período fechado.
