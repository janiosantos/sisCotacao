# Manual do Sistema ERP Comercial

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Acesso ao Sistema](#2-acesso-ao-sistema)
3. [Módulo Vendas](#3-módulo-vendas)
   - 3.1. Catálogo de Produtos
   - 3.2. PDV (Ponto de Venda)
   - 3.3. Orçamentos
   - 3.4. Cotações de Venda
4. [Módulo Compras](#4-módulo-compras)
   - 4.1. Cotações de Compra
   - 4.2. Pedidos de Compra
   - 4.3. Recebimento de Mercadorias
   - 4.4. Solicitações de Compra
5. [Módulo Cadastros](#5-módulo-cadastros)
   - 5.1. Clientes
   - 5.2. Fornecedores
   - 5.3. Produtos
   - 5.4. Vendedores
   - 5.5. Categorias
6. [Módulo Estoque](#6-módulo-estoque)
   - 6.1. Saldo de Estoque
   - 6.2. Movimentações
   - 6.3. Depósitos
   - 6.4. Lotes
   - 6.5. Expedição
7. [Módulo Financeiro](#7-módulo-financeiro)
   - 7.1. Caixa
   - 7.2. Contas a Receber
   - 7.3. Contas a Pagar
   - 7.4. Condições de Pagamento
   - 7.5. Centros de Custo
   - 7.6. Adiantamentos
8. [Módulo Preços](#8-módulo-preços)
   - 8.1. Tabelas de Preço
   - 8.2. Promoções
   - 8.3. Revisões de Preço
9. [Módulo Fiscal](#9-módulo-fiscal)
   - 9.1. CFOP
   - 9.2. CST
   - 9.3. Configuração Fiscal por Produto
   - 9.4. Emitente
   - 9.5. NF-e
   - 9.6. IBPT
10. [Módulo Bancos](#10-módulo-bancos)
    - 10.1. Contas Bancárias
    - 10.2. Extrato
    - 10.3. Conciliação
11. [Módulo Pós-Venda](#11-módulo-pós-venda)
    - 11.1. Acompanhamento de Clientes
    - 11.2. Garantia
12. [Módulo Administrativo](#12-módulo-administrativo)
    - 12.1. Usuários
    - 12.2. Plano de Contas
    - 12.3. Histórico de Preços
    - 12.4. Relatórios
13. [Atalhos de Teclado PDV](#13-atalhos-de-teclado-pdv)
14. [Dicas e Boas Práticas](#14-dicas-e-boas-práticas)

---

## 1. Visão Geral

O ERP Comercial é um sistema completo para gestão de lojas de material de construção. Ele cobre todo o ciclo: **comprar → estocar → vender → receber → pagar → emitir NF-e**.

### Fluxo Principal

```
Fornecedor → Compra → Estoque → Venda (PDV) → Cliente
                              ↓
                        Financeiro (Receber/Pagar)
                              ↓
                           Fiscal (NF-e)
```

### Acesso

- **Frontend (recomendado):** http://localhost:5173
- **Backend (API):** http://localhost:8000
- **Login padrão:** admin / admin123

---

## 2. Acesso ao Sistema

### 2.1. Primeiro Acesso

1. Abra o navegador em http://localhost:5173
2. Na tela de login, informe:
   - **Usuário:** admin
   - **Senha:** admin123
3. Clique em **Entrar**

### 2.2. Navegação

O menu principal está no topo da tela, organizado em grupos:

| Grupo | Módulos |
|-------|---------|
| **Vendas** | Catálogo, PDV, Orçamentos, Cotações, Compras |
| **Cadastros** | Clientes, Fornecedores, Produtos, Vendedores, Categorias |
| **Financeiro** | Financeiro, Preços, Bancos, Plano de Contas |
| **Logística** | Estoque, Fiscal |
| **Admin** | Pós-venda, Solic. Compra, Hist. Preços, Usuários |

Clique no nome do grupo para abrir o submenu e selecione o módulo desejado.

---

## 3. Módulo Vendas

### 3.1. Catálogo de Produtos

**Localização:** Menu Vendas > Catálogo

Tela principal de consulta e venda rápida de produtos.

**Funcionalidades:**
- Busca de produtos por nome, SKU ou marca
- Visualização em cards com foto, preço e parcelamento
- Seleção de variações (cor, tamanho)
- Carrinho lateral para montar pedido
- Matriz de variação por grupo de produto

**Como usar:**
1. Digite o nome do produto no campo de busca
2. Os resultados aparecem automaticamente
3. Clique em **+** para adicionar ao carrinho
4. Ajuste a quantidade no carrinho
5. Clique no carrinho para criar uma cotação

### 3.2. PDV (Ponto de Venda)

**Localização:** Menu Vendas > PDV

Tela de criação rápida de orçamentos de venda, projetada para uso com teclado.

**Campos principais:**
- **Cliente:** digite o nome. Após 3 caracteres, busca automática. Use **F6** para busca avançada por CPF/endereço
- **Contato:** WhatsApp ou e-mail do cliente
- **Validade:** dias de validade do orçamento
- **Busca de Produto:** digite o nome. Use o formato `N*produto` para definir quantidade (ex.: `3*Cabo Flex`)
- **Desconto:** valor em R$ de desconto global
- **Condição de pagamento:** selecione à vista, 30 dias, parcelado, etc.
- **Observações:** texto livre

**Botões de ação:**
- **F1** — Imprimir cupom (salva + imprime)
- **F2** — Visualizar pedido em tela (prévia)
- **F3** — Finalizar pedido (salva como Faturado)
- **F4** — Salvar rascunho (sem imprimir)
- **F5** — Novo / Limpar
- **F6** — Buscar cliente (modal avançado)
- **F7** — Configurar impressora
- **F8** — Ver orçamentos salvos
- **F9** — Foco no campo de busca

**Fluxo completo de venda:**
1. Informe o cliente (busca automática ou digite nome)
2. Tecle **ENTER** para avançar ao campo de busca
3. Digite o produto (ex.: `2*Cabo`) e tecle **ENTER**
4. O produto é adicionado com a quantidade especificada
5. Repita para cada item
6. Ajuste desconto se necessário
7. Pressione **F3** para finalizar a venda
   - Automaticamente: baixa o estoque, gera conta a receber

### 3.3. Orçamentos

**Localização:** Menu Vendas > Orçamentos

Lista e gerencia todos os orçamentos de venda.

**Status dos orçamentos:**
| Status | Significado |
|--------|-------------|
| Rascunho | Em criação, não finalizado |
| Ativo | Em negociação com o cliente |
| Em análise | Aguardando aprovação |
| Liberado | Aprovado para faturamento |
| Faturado | Venda concluída |

**Ações:**
- Clique em um orçamento para ver detalhes
- Altere o status conforme o fluxo de aprovação
- Imprima o cupom fiscal

### 3.4. Cotações de Venda

**Localização:** Menu Vendas > Cotações

Gerencia cotações enviadas a fornecedores para cotação de preços.

**Fluxo:** Criar cotação → Convidar fornecedores → Aguardar respostas → Comparar preços → Gerar pedido

**Unidade de compra × unidade de venda:** o catálogo trabalha sempre em unidades (ex.: ABRAÇADEIRA vendida avulsa). Quando um fornecedor só vende a embalagem (ex.: CX 50 un), cadastre isso em **Cadastros > Produtos** (aba Fornecedores): informe a *Unid. compra* e o *Fator conv.* (ex. `50`). Na comparação de preços e na impressão da cotação, o sistema passa a exibir a embalagem do fornecedor e o total de embalagens que a quantidade comprada representa (ex.: 100 un → 2 CX), mantendo os preços por unidade.

> **Unidades predefinidas:** a *Unid. compra* não é texto livre — escolhe-se uma das opções cadastradas em **Cadastros > Unidades** (sigla + descrição, ex.: `CX` = Caixa, `PCT` = Pacote, `RL` = Rolo). Gerencie (criar, renomear, ativar/inativar, excluir) pela mesma tela. Uma unidade em uso em códigos de fornecedor não pode ser excluída.

---

## 4. Módulo Compras

### 4.1. Cotações de Compra

**Localização:** Menu Vendas > Compras

Fluxo completo de cotação de compra em tela única.

**Etapas:**
1. **Lista de itens:** adicione produtos para cotar
2. **Disparo:** envie convites aos fornecedores (link, WhatsApp, e-mail)
3. **Comparação:** veja a matriz de preços e selecione o melhor
4. **Pedidos:** gere pedidos de compra automaticamente

### 4.2. Pedidos de Compra

Gerados automaticamente ao fechar uma cotação. Cada fornecedor vencedor recebe um pedido.

### 4.3. Recebimento de Mercadorias

**Localização:** Ações no pedido de compra

Ao receber a mercadoria do fornecedor:
1. Acesse o pedido em **Compras > Pedidos**
2. Clique em **Receber**
3. Confirme o depósito de destino
4. O sistema automaticamente:
   - Registra **entrada no estoque**
   - Gera **conta a pagar** com vencimento em 30 dias

### 4.4. Solicitações de Compra

**Localização:** Menu Admin > Solic. Compra

Solicitações internas de compra com fluxo de aprovação.

1. Clique em **Nova solicitação**
2. Informe código e descrição
3. Adicione os itens desejados
4. A solicitação fica pendente para aprovação

---

## 5. Módulo Cadastros

### 5.1. Clientes

**Localização:** Menu Cadastros > Clientes

Cadastro completo de clientes com 5 abas:

| Aba | Campos |
|-----|--------|
| **Dados** | Nome, CPF/CNPJ, e-mail, WhatsApp, vendedor, limite de crédito |
| **Endereços** | Endereços de cobrança, entrega e faturamento |
| **Contatos** | Nome, cargo, telefone, e-mail dos contatos |
| **Apoio Comercial** | Tabela de preço, condição de pagamento, transportadora |
| **Apoio Fiscal** | CFOP padrão, CST ICMS/PIS/COFINS, alíquotas |

**Como cadastrar:**
1. Clique em **+ Novo cliente**
2. Preencha os dados na aba **Dados**
3. Navegue pelas abas para completar endereços e contatos
4. Na aba **Apoio Comercial**, vincule a tabela de preço
5. Clique em **Salvar**

### 5.2. Fornecedores

**Localização:** Menu Cadastros > Fornecedores

Cadastro de fornecedores com dados fiscais e comerciais.

- Razão social, CNPJ, IE
- Dados de contato (telefone, WhatsApp, e-mail)
- Endereço completo
- Tabela de preço de compra (por produto)

### 5.3. Produtos

**Localização:** Menu Cadastros > Produtos

Gerencia o cadastro de produtos do sistema (independente do catálogo importado).

- Criação de famílias e atributos
- Cadastro de variações (SKU, EAN, preço)
- Upload de imagens
- Importação por URL de fornecedor

### 5.4. Vendedores

**Localização:** Menu Cadastros > Vendedores

Cadastro de vendedores com percentual de comissão.

### 5.5. Categorias

**Localização:** Menu Cadastros > Categorias

Organização hierárquica de categorias e subcategorias de produtos.

---

## 6. Módulo Estoque

### 6.1. Saldo de Estoque

**Localização:** Menu Logística > Estoque > Aba Saldo

Consulta o saldo atual de todos os produtos por depósito.

**Colunas:**
- Produto, SKU, Depósito
- Quantidade atual
- Preço de venda
- **Situação:** 🟢 OK / 🟡 Ruptura (abaixo do mínimo) / 🔴 Excesso (acima do máximo)

**Como configurar limites:**
Na tela de saldo, clique em **Editar limites** para definir:
- **Estoque mínimo:** dispara alerta quando o saldo estiver abaixo
- **Estoque máximo:** dispara alerta quando o saldo estiver acima

### 6.2. Movimentações

**Localização:** Menu Logística > Estoque > Aba Movimentos

Registra movimentações manuais de estoque.

**Tipos de movimento:**
| Tipo | Descrição |
|------|-----------|
| Entrada | Aumenta o saldo (compra, devolução, ajuste) |
| Saída | Diminui o saldo (venda, perda, consumo) |
| Ajuste | Define o saldo para um valor específico |

**Importante:** Ao faturar uma venda no PDV, a saída de estoque é **automática**. Use este módulo apenas para ajustes manuais.

### 6.3. Depósitos

**Localização:** Menu Logística > Estoque > Aba Depósitos

Cadastro de depósitos/almoxarifados.

**Tipos de depósito:**
- **Próprio:** instalações da empresa
- **Terceiros:** armazém de parceiro logístico
- **Virtual:** estoque lógico (consignação, mostruário)

**Campos:**
- Nome, tipo, endereço
- Localizações (rua, prateleira, nível, vão) — até 8 por depósito

### 6.4. Lotes

**Localização:** Menu Logística > Estoque > Aba Lotes

Controle de lotes com data de fabricação e validade.

### 6.5. Expedição

**Localização:** Menu Logística > Estoque > Aba Expedição

Gerenciamento de romaneios de expedição.

**Fluxo:**
1. Crie uma expedição informando código e depósito
2. Adicione os itens a serem expedidos
3. Atualize o status conforme o progresso:
   - Pendente → Separando → Conferido → Carregado → Finalizado

---

## 7. Módulo Financeiro

### 7.1. Caixa

**Localização:** Menu Financeiro > Financeiro > Aba Caixa

Registro de movimentações de caixa diário.

**Ações:**
- **+ Entrada:** registrar recebimento em dinheiro
- **- Saída:** registrar pagamento em dinheiro
- **Suprimento:** aumentar o caixa com recursos externos
- **Sangria:** retirar valor do caixa para depósito bancário

**Formas de pagamento:** Dinheiro, Pix, Crédito, Débito, Boleto, Cheque, Outro

**Saldo:** calculado automaticamente com base nos movimentos.

### 7.2. Contas a Receber

**Localização:** Menu Financeiro > Financeiro > Aba Receber

Títulos a receber de clientes.

**Criação manual:**
1. Clique em **Nova conta a receber**
2. Informe cliente, valor, vencimento e descrição
3. O título fica em aberto para recebimento

**Criação automática:** Ao **faturar** uma venda no PDV, o sistema gera automaticamente uma conta a receber com vencimento em 30 dias.

**Recebimento:**
1. Clique em **Receber** na linha do título
2. Informe valor e data de recebimento
3. O status muda para Pago (ou Parcial, se valor menor)

### 7.3. Contas a Pagar

**Localização:** Menu Financeiro > Financeiro > Aba Pagar

Títulos a pagar para fornecedores.

**Criação manual:**
1. Clique em **Nova conta a pagar**
2. Informe fornecedor, valor, vencimento

**Criação automática:**
- Ao **receber mercadoria** de um pedido de compra
- O sistema gera a conta a pagar com vencimento em 30 dias

**Pagamento:**
1. Clique em **Pagar** na linha do título
2. Informe valor e data de pagamento

### 7.4. Condições de Pagamento

**Localização:** Menu Financeiro > Financeiro > Aba Condições

Cadastro de condições de pagamento (parcelamento).

**Exemplos cadastrados:**
| Condição | Parcelas |
|----------|----------|
| À vista | 1x em 0 dias (100%) |
| 30 dias | 1x em 30 dias (100%) |
| 30/60 dias | 2x (50% em 30d + 50% em 60d) |
| 30/60/90 dias | 3x (33,33% cada) |

**Como criar:**
1. Clique em **Nova condição**
2. Informe nome e descrição
3. No campo **Parcelas**, digite no formato: `sequência:dias,percentual`
   - Ex.: `1:30,50` (parcela 1, vence em 30 dias, 50% do valor)
4. Clique em **Salvar**

### 7.5. Centros de Custo

**Localização:** Menu Financeiro > Financeiro > Aba Centros Custo

Classificação de custos para rateio financeiro.

**Centros padrão:** Administrativo, Comercial, Financeiro, Logística, Produção, TI.

### 7.6. Adiantamentos

**Localização:** Menu Financeiro > Financeiro > Aba Adiantamentos

Registro de adiantamentos recebidos de clientes ou pagos a fornecedores.

---

## 8. Módulo Preços

### 8.1. Tabelas de Preço

**Localização:** Menu Financeiro > Preços > Aba Tabelas

Gerencia listas de preço (varejo, atacado, contrato).

**Ações:**
- **Criar tabela:** defina nome, tipo, margem padrão e markup
- **Ver itens:** consulte todos os produtos com seus preços na tabela
- **Gerar preços:** gere automaticamente os preços com base no custo + margem ou markup

**Cálculo de Margem:** `Margem % = (Preço de Venda - Custo) / Preço de Venda × 100`

### 8.2. Promoções

**Localização:** Menu Financeiro > Preços > Aba Promoções

Campanhas promocionais.

**Tipos:**
- **Percentual:** desconto percentual sobre o preço base
- **Valor fixo:** preço promocional definido manualmente

**Como aplicar:**
1. Crie a promoção definindo nome, tipo e valor
2. Clique em **Aplicar** e informe os IDs das variantes
3. O sistema calcula o preço promocional

### 8.3. Revisões de Preço

**Localização:** Menu Financeiro > Preços > Aba Revisões

Controle de versão das tabelas de preço.

**Fluxo:**
1. Crie uma revisão vinculada a uma tabela
2. A revisão fica em situação **Aberta** para edição
3. Quando os preços estiverem definidos, **Feche** a revisão
4. Revisões fechadas não podem ser alteradas (congelamento)

---

## 9. Módulo Fiscal

### 9.1. CFOP

**Localização:** Menu Logística > Fiscal > Aba CFOP

Consulta a tabela de CFOP (Código Fiscal de Operações e Prestações).

**Filtros:** Todos, Entrada, Saída, Mesma UF, Outra UF.

**Exemplos:**
| Código | Descrição |
|--------|-----------|
| 5.102 | Venda de mercadoria adquirida |
| 1.102 | Compra para industrialização |
| 5.405 | Venda ao consumidor final |

### 9.2. CST

**Localização:** Menu Logística > Fiscal > Aba CST

Consulta códigos CST para ICMS, PIS e COFINS.

**Tabelas:** ICMS (00 a 90), PIS (01 a 99), COFINS (01 a 99).

### 9.3. Configuração Fiscal por Produto

**Localização:** Menu Logística > Fiscal > Aba Config. Fiscal

Define a tributação de cada variante.

**Campos:**
- NCM (código de 8 dígitos)
- CFOP padrão
- CST ICMS, PIS, COFINS
- Alíquotas (ICMS, PIS, COFINS, IPI)

**Gerar configuração padrão:**
Clique em **Gerar config padrão** para atribuir CFOP 5.102 e CST 00 com alíquotas padrão (ICMS 18%, PIS 1,65%, COFINS 7,6%) para todas as variantes.

### 9.4. Emitente

**Localização:** Menu Logística > Fiscal > Aba Emitente

Cadastro da empresa emitente para emissão de NF-e.

**Campos obrigatórios:**
- Razão Social
- CNPJ
- Inscrição Estadual
- Regime Tributário (Simples Nacional, Lucro Presumido, Lucro Real)
- Token Focus NFe (para emissão integrada)
- Alíquota ICMS padrão

### 9.5. NF-e

**Localização:** Menu Logística > Fiscal > Aba NF-e

Consulta de NF-e emitidas (saída) e recebidas (entrada).

**Abas internas:**
- **Saída:** lista notas fiscais de venda emitidas
- **Entrada:** lista notas fiscais de compra recebidas

### 9.6. IBPT

**Localização:** Menu Logística > Fiscal > Aba IBPT

Tabela de carga tributária por NCM (Imposto sobre Produtos Industrializados).

**Importação em lote:**
1. Obtenha o arquivo CSV da FEBRACON no formato: `ncm;descricao;nacional;estadual;municipal`
2. Na aba IBPT, clique em **Importar CSV**
3. Selecione o arquivo e confirme

---

## 10. Módulo Bancos

### 10.1. Contas Bancárias

**Localização:** Menu Financeiro > Bancos > Aba Contas

Cadastro de contas correntes da empresa.

**Campos:** Nome, código do banco (ex.: 341 para Itaú), agência, conta, dígito, saldo inicial.

### 10.2. Extrato

**Localização:** Menu Financeiro > Bancos > Aba Extrato

Movimentação financeira das contas bancárias.

**Ações:**
- **Novo movimento:** registre créditos, débitos e transferências
- **Filtrar:** selecione a conta desejada

### 10.3. Conciliação

Na tela de extrato, cada movimento tem um botão **Conciliar/Desconciliar** para controle de conciliação bancária.

---

## 11. Módulo Pós-Venda

### 11.1. Acompanhamento de Clientes

**Localização:** Menu Admin > Pós-venda > Aba Acompanhamento

Registro de interações com clientes (pós-venda, follow-up).

**Tipos de interação:** Ligação, Visita, E-mail, WhatsApp, Follow-up, Outro.

**Como registrar:**
1. Clique em **Nova interação**
2. Informe cliente, tipo, data e descrição
3. Opcionalmente, defina **Próximo contato** para agendar follow-up

### 11.2. Garantia

**Localização:** Menu Admin > Pós-venda > Aba Garantia

Registro de termos de garantia por produto/cliente.

**Status:** Ativa, Vencida, Acionada, Cancelada.

---

## 12. Módulo Administrativo

### 12.1. Usuários

**Localização:** Menu Admin > Usuários

Gerencia os usuários do sistema.

**Perfis:** Admin, Supervisor, Vendedor, Financeiro, Fiscal.

**Ações:** Criar, editar, ativar/desativar, alterar senha.

### 12.2. Plano de Contas

**Localização:** Menu Financeiro > Plano de contas

Estrutura hierárquica de contas contábeis (Receitas e Despesas).

**Contas de Receita:** Vendas, serviços, receitas financeiras.
**Contas de Despesa:** CMV, pessoal, administrativo, vendas, financeiro, tributário.

### 12.3. Histórico de Preços

**Localização:** Menu Admin > Hist. preços

Consulta o histórico de preços de produtos por fornecedor (cotações passadas).

### 12.4. Relatórios

**Endpoints de relatório:**
- **Vendas por período:** total de vendas agregado por dia
- **Aging Receber:** faixas de vencimento de contas a receber
- **Aging Pagar:** faixas de vencimento de contas a pagar
- **DRE:** Demonstração de Resultado resumida (receitas vs despesas)

Os relatórios estão disponíveis via API e podem ser acessados pelo menu **Admin > Relatórios**.

---

## 13. Atalhos de Teclado PDV

A tela de PDV foi projetada para uso sem mouse. Os atalhos são:

| Tecla | Função |
|-------|--------|
| **ENTER** | Avança para o próximo campo |
| **F1** | Imprimir cupom (salva e imprime) |
| **F2** | Visualizar pedido na tela |
| **F3** | Finalizar pedido (faturar) |
| **F4** | Salvar rascunho |
| **F5** | Novo / Limpar orçamento |
| **F6** | Buscar cliente (modal avançado) |
| **F7** | Configurar impressora |
| **F8** | Ver orçamentos salvos |
| **F9** | Foco no campo de busca de produto |
| **↑/↓** | Navegar nas sugestões de busca |
| **ESC** | Fechar sugestões / Fechar modal |

**Formato de busca:** `N*produto` adiciona o produto com quantidade N. Ex.: `3*Cabo Flex`

---

## 14. Dicas e Boas Práticas

### Para o dia a dia

1. **Use o PDV sempre que possível** — ele integra venda, estoque e financeiro automaticamente
2. **Cadastre clientes completos** — CPF, endereço e contatos agilizam a emissão de NF-e
3. **Mantenha o estoque mínimo configurado** — evita rupturas
4. **Feche o caixa diariamente** — registre sangrias/suprimentos para manter o saldo correto

### Fluxos automáticos

| Ação | O que acontece |
|------|----------------|
| Faturar venda no PDV | ✅ Baixa estoque + gera conta a receber |
| Receber mercadoria | ✅ Entrada no estoque + gera conta a pagar |
| Finalizar cotação | ✅ Gera pedidos de compra |
| Fechar revisão de preço | ✅ Preços congelados (não podem ser alterados) |

### Erros comuns

| Erro | Causa | Solução |
|------|-------|---------|
| "Variante não encontrada" | ID inválido no movimento de estoque | Verifique se o ID existe no catálogo |
| "Status inválido" | Usou "fechado" em vez de "faturado" | Use o menu de orçamentos para alterar status |
| "FOREIGN KEY" | Referência a registro inexistente | Cadastre o registro antes de referenciá-lo |

### Desenvolvimento

**Rodar os testes de regressão** (banco SQLite temporário, não toca no `server.db`):

```bash
.venv\Scripts\python.exe -m pytest tests\ -q
```

**Backup do banco antes de mudanças de schema** (cópia timestampada de `server.db`, `server_cache.db` e `crawler.db` em `backups/`):

```bash
.venv\Scripts\python.exe scripts\backup_db.py
.venv\Scripts\python.exe scripts\backup_db.py --incluir-cache   # inclui o cache de 8,6 GB
```

**Baseline de qualidade dos dados** (contagens + métricas em JSON):

```bash
.venv\Scripts\python.exe scripts\baseline.py
```

**Rollback:** para desfazer uma migração de schema, restaure o backup:

```bash
Copy-Item backups\server_YYYY-MM-DD_HHMMSS.db catalog_server\data\server.db
```

### PostgreSQL (em migração)

O serviço `db` do `docker-compose.yml` sobe um PostgreSQL 16 com a URL
`postgresql+psycopg://catalog:catalog@db:5432/catalog`. A variável
`DATABASE_URL` no backend controla o destino: **vazia = SQLite** (padrão,
produção atual); preenchida = PostgreSQL.

O sistema já roda sobre o Postgres: `db.system_conn()` usa a camada de
compatibilidade `catalog_server/pgsql.py` quando `DATABASE_URL` está
configurada, traduzindo o SQL dos repositórios (escritos para SQLite) para o
dialeto Postgres na hora da execução (`?`→`%s`, `datetime('now')`→`to_char`,
`INSERT OR IGNORE`→`ON CONFLICT DO NOTHING`, `LIKE ... COLLATE NOCASE`→`ILIKE`,
`GROUP_CONCAT`→`string_agg`, etc.). As migrações SQLite não rodam no PG: o
schema é aplicado pelos scripts de migração.

```bash
docker compose up -d db
# rodar o backend sobre o Postgres:
$env:DATABASE_URL = "postgresql+psycopg://catalog:catalog@localhost:5432/catalog"
.venv\Scripts\python.exe -m catalog_server.app
```

**Migrar os dados do SQLite para o Postgres** (schema + dados + conferência):

```bash
.venv\Scripts\python.exe scripts\backup_db.py                      # backup pré-migração
$env:DATABASE_URL = "postgresql+psycopg://catalog:catalog@localhost:5432/catalog"
.venv\Scripts\python.exe scripts\schema_postgres.py                # gera scripts/postgres_schema.sql
.venv\Scripts\python.exe scripts\migrar_postgres.py --apply-schema # DROP SCHEMA + schema + import + conferência
```

O `server_cache.db` (cache de páginas-fonte) **não** é migrado — fica fora da
estrutura de produção. A tabela `produtos_fts` (índice FTS5 de busca) também
não vem da migração: no Postgres ela é criada automaticamente no primeiro
`ensure_fts()` (startup do servidor) usando `tsvector` + `pg_trgm` — coluna
`fts` gerada com `to_tsvector('simple', f_unaccent(...))` (remover acentos) e
função `fts5_to_tsquery()` que converte a query FTS5 (`parafuso* AND 5x50*`)
para tsquery de prefixo. O `rebuild()` roda no startup para popular o índice.

O script imprime a conferência linha a linha (contagens origem → destino) e
falha (`exit 1`) se houver divergência. Após o import, as FKs são validadas
pelo Postgres (todas `convalidated`) e as sequences são ajustadas com
`setval` para o maior id de cada tabela.

**Validar a camada Postgres com a suíte de testes** (35 testes rodam também
contra o PG; cada teste zera as tabelas e replica os seeds das migrações):

```bash
# SQLite (padrão):
.venv\Scripts\python.exe -m pytest tests\ -q
# PostgreSQL:
$env:TEST_PG_URL = "postgresql+psycopg://catalog:catalog@localhost:5432/catalog_test"
.venv\Scripts\python.exe -m pytest tests\ -q
```

### Suporte

Para dúvidas ou problemas, entre em contato com o suporte técnico.

---

*Documentação gerada em 09/08/2026*
