Estruturar um ERP do zero no Brasil que emita documentos fiscais (NFe modelo 55 e NFCe modelo 65) é um dos maiores desafios de engenharia de software devido à complexidade tributária. O segredo para um sistema escalável, que não vai quebrar quando o contador pedir uma alteração, é a separação de responsabilidades.

O produto não deve "saber" qual é a sua alíquota de ICMS. O imposto é calculado por um "Motor Fiscal" baseado no contexto da venda.

Aqui está a arquitetura estrutural do banco de dados e as regras de negócio divididas por domínios (módulos).

1. Domínio de Catálogo (Produtos e Variantes)
Além das informações comerciais e JSONB, o cadastro precisa dos ganchos fiscais essenciais que a SEFAZ exige.

Tabelas Principais:

produtos (Pai): id, nome_base, ncm (Nomenclatura Comum do Mercosul - Obrigatório), cest (Código Especificador da Substituição Tributária), origem_mercadoria (0-Nacional, 1-Estrangeira, etc. - afeta o CST).

skus (Filho/Variante): id, produto_id, codigo_sku, ean (Código de barras GTIN - exigido na NFe), preco_venda, atributos (JSONB).

Regra de Negócio (Catálogo):
A SEFAZ exige que produtos com EAN (código de barras) válido sejam informados no XML da nota no grupo <cEAN>. Se o material de construção não tiver EAN (ex: areia a granel, prego pesado na hora), o sistema deve preencher essa tag com a string "SEM GTIN".

2. Domínio de Estoque (Kardex)
O maior erro em sistemas iniciantes é apenas ter uma coluna quantidade_atual e fazer um UPDATE. Em um ERP contábil, o estoque é um Livro Razão (Ledger).

Tabelas Principais:

estoque_locais: id, nome (ex: Loja Matriz, Depósito, Pátio).

estoque_saldos: sku_id, local_id, quantidade_fisica, quantidade_reservada.

estoque_movimentos (O Kardex): id, sku_id, local_id, tipo (ENTRADA, SAIDA), quantidade, custo_medio_unitario, documento_origem_tipo (ex: VENDA, AJUSTE, COMPRA), documento_origem_id (ex: ID da NFe).

Regras de Negócio (Estoque):

Imutabilidade: A tabela estoque_movimentos é append-only (só recebe INSERTS, nunca UPDATES). Se houver um erro, faz-se um movimento de estorno.

Reserva: Quando um pedido é feito no PDV mas o cliente vai retirar no depósito, a quantidade_reservada aumenta. O saldo físico só cai quando o cliente retira a mercadoria. Saldo Disponível = Físico - Reservado.

Custo Médio: A cada entrada de mercadoria por nota fiscal de compra, o custo médio do produto deve ser recalculado. A contabilidade usa isso para calcular o lucro (CMV - Custo da Mercadoria Vendida).

3. Domínio Tributário (O Motor Fiscal)
Esta é a parte mais crítica. Em vez de amarrar impostos ao produto, você cria uma "Matriz Tributária".

Tabelas Principais:

naturezas_operacao: id, descricao (ex: Venda Interna, Venda Interestadual, Devolução).

grupo_tributacao: id, nome (ex: "Materiais com ICMS Normal", "Materiais com Substituição Tributária ST"). Você amarra o produto a este grupo.

matriz_fiscal_icms: A tabela de regras cruzadas.

Campos: grupo_tributacao_id, uf_origem, uf_destino, natureza_operacao_id, tipo_cliente (B2B/B2C).

Retornos Fiscais: cfop (ex: 5102, 5405, 6102), cst_csosn (ex: 102, 500, 00, 60), aliquota_icms, aliquota_reducao_base.

matriz_fiscal_pis_cofins: Regras para os impostos federais (CST PIS/COFINS e alíquotas).

Regra de Negócio (Tributos):
Quando o PDV ou a API for gerar a nota, o sistema pergunta ao Motor Fiscal:
"Estou vendendo um SKU do grupo 'Substituição Tributária', de MG para MG, para Consumidor Final B2C. Qual a tributação?"
O motor responde com as alíquotas zero e o CFOP 5405 (Venda de mercadoria sujeita a ST). Se for para outro estado (BA), a regra devolve o CFOP 6102 com diferencial de alíquota (DIFAL).

4. Domínio de Vendas e Faturamento (PDV / Notas Fiscais)
O pedido de venda e a nota fiscal são entidades diferentes. Um pedido pode gerar uma nota, ser cancelado, ou gerar um cupom fiscal.

Tabelas Principais:

pedidos: id, cliente_id, total_produtos, total_descontos, total_frete, status (PENDENTE, FATURADO, CANCELADO).

pedidos_itens: pedido_id, sku_id, quantidade, preco_unitario.

notas_fiscais (NF-e / NFC-e):

Campos: id, pedido_id, modelo (55 para NFe, 65 para NFCe), numero, serie, chave_acesso (44 dígitos), status_sefaz (Autorizado, Rejeitado, Cancelado), xml_enviado, xml_retorno, recibo.

notas_fiscais_itens: Esta tabela é um "retrato" exato dos itens no momento da emissão, incluindo os impostos calculados para cada item (Valor ICMS, Valor ST, etc.). Isso é necessário porque os impostos podem mudar no futuro, mas a nota fiscal emitida é imutável.

Regras de Negócio (Emissão):

Idempotência: A comunicação com a SEFAZ deve ser protegida. Se o sistema enviar o XML e a internet cair antes da SEFAZ responder, o sistema deve ser capaz de consultar a Chave de Acesso para ver se autorizou, antes de tentar enviar de novo (evitando duplicidade).

Contingência Offline (NFC-e): Para o PDV de material de construção, se a SEFAZ estiver fora do ar, o sistema deve permitir gerar o Cupom Fiscal (modelo 65) em contingência offline (imprimindo na hora) e enviar o XML para a SEFAZ assim que a internet voltar (prazo legal de até 24h).

Transações ACID: Ao faturar um pedido, o sistema deve, numa única transação de banco de dados (BEGIN ... COMMIT):

Mudar status do pedido.

Gravar o movimento no Kardex (saída de estoque).

Gravar o contas a receber (financeiro).
Se qualquer uma dessas falhar (ex: faltou estoque), dá ROLLBACK em tudo.



Ferramenta usada para Desenvolvedor (FastAPI/Python)
Não vamos construir o gerador de XML e o comunicador SOAP com os web services da SEFAZ do zero. É uma perda de tempo gigantesca (são centenas de regras de validação, schemas XSD e assinaturas digitais com certificado A1).

Vamos Integra o ERP com uma API fiscal (SaaS):
Use serviços como Focus NFe documentacao em https://doc.focusnfe.com.br/. O sistema no FastAPI apenas monta um JSON simplificado com os dados da venda e os impostos que seu motor calculou, envia para essas APIs, e eles devolvem o PDF (DANFE) e o XML autorizado. Isso poupará tempo de desenvolvimento.