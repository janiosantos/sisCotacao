A melhor abordagem, para o sistema que você está construindo, é não colocar toda a tributação nem no Produto Base nem toda na Variação. O correto é separar classificação fiscal do produto, parametrização tributária por contexto e valores calculados na operação.

Isso é coerente com a forma como sistemas fiscais/ERP estruturam o cadastro: NCM, CEST e origem aparecem como dados de cadastro do item, enquanto CST/CSOSN e demais regras podem depender do regime e da operação.

Minha recomendação para a Casa LM

Eu estruturaria em 4 camadas:

PRODUTO BASE
    │
    ├── Classificação fiscal
    │
    └── Características comuns
             │
             ▼
       VARIAÇÃO / SKU
             │
             ├── GTIN/EAN
             ├── atributos
             └── características específicas
             
             ↓
      REGRA TRIBUTÁRIA
             │
             ├── CST/CSOSN
             ├── CFOP
             ├── ICMS
             ├── PIS/COFINS
             └── ST etc.

             ↓
       ITEM DA NF-e/NFC-e
             │
             ├── quantidade
             ├── preço
             ├── base de cálculo
             ├── alíquota efetiva
             └── valores calculados
1. O que eu colocaria no Produto Base

São informações que normalmente identificam/classificam a mercadoria e são compartilhadas pelas variações.

Campo	Produto base?	Variação?
NCM	✅	normalmente não
CEST	✅	normalmente não
Origem da mercadoria	✅	pode haver exceção
Marca	✅	não
Categoria	✅	não
Unidade de medida	✅	depende do produto
Descrição base	✅	não
NBS	quando aplicável	—
Códigos fiscais complementares	avaliar	—

NCM é um ótimo exemplo de campo do Produto Base.

Imagine:

Produto:
Chuveiro Lorenzetti Acqua Storm

Variações:
127V 6800W
220V 7800W

Não faz sentido criar dois NCMs simplesmente porque existem duas voltagens, se ambas as variações possuem a mesma classificação fiscal.

2. O que eu colocaria na Variação

A Variação deve guardar aquilo que diferencia comercialmente uma unidade da outra.

Product
│
└── ProductVariant
      ├── SKU
      ├── GTIN/EAN
      ├── attributes JSONB
      ├── preço
      ├── custo
      └── estoque

Por exemplo:

{
  "voltagem": "220V",
  "potencia": "7800W",
  "cor": "branco"
}

E:

{
  "voltagem": "127V",
  "potencia": "6800W",
  "cor": "branco"
}

O GTIN/EAN, em particular, pode ser diferente para cada variação. A própria documentação da NF-e trata GTIN como identificação do produto/unidade comercial e possui validações específicas para ele.

3. E CST, CSOSN e CFOP?

Aqui está a parte mais importante.

Eu não colocaria simplesmente cst, csosn e cfop como campos fixos da Variação.

Porque tributação não é apenas uma propriedade do produto.

Ela depende do contexto da operação.

Por exemplo:

Produto
+
Regime tributário da empresa
+
UF origem
+
UF destino
+
tipo de cliente
+
finalidade
+
tipo de operação
+
ST
+
benefício fiscal
+
etc.

O mesmo produto pode ter tratamentos diferentes dependendo da operação.

Motores tributários modernos seguem justamente essa lógica: utilizam dados do produto como NCM/origem e dados da operação para determinar CFOP, CST/CSOSN e impostos.

4. Portanto, criaria uma entidade TaxRule

Algo como:

Product
   │
   └── TaxRule

ou, quando necessário:

ProductVariant
   │
   └── TaxRule

Mas eu começaria vinculando a regra ao Produto Base, permitindo override na Variação somente quando realmente necessário.

Conceitualmente:

Product
│
├── NCM
├── CEST
├── Origem
│
└── TaxRules
      │
      ├── operação interna
      ├── operação interestadual
      ├── regime tributário
      └── contexto fiscal
5. Exemplo prático

Imagine:

Produto

Cabo Flexível SIL

Classificação:

Grupo: Material Elétrico
Subgrupo: Cabos e Fios
Categoria: Cabo Flexível
Subcategoria: Cabo 750V
Marca: SIL
NCM: XXXXXXXX
CEST: XXXXXXX
Origem: 0

Variações:

ELE-CAB-SIL-15P-AZ
ELE-CAB-SIL-25P-AZ
ELE-CAB-SIL-25P-VD

Cada uma possui:

{
  "bitola": "2,5mm²",
  "cor": "Verde"
}

Mas todas podem compartilhar:

NCM
CEST
Origem

Enquanto a regra fiscal pode ser:

TaxRule
├── regime = SIMPLES_NACIONAL
├── operação = VENDA_INTERNA
├── finalidade = REVENDA
└── CSOSN = ...
6. E o IBPT?

Aqui eu faria uma separação ainda mais clara.

IBPT não deve ser tratado como uma característica permanente da variação.

O IBPT é uma tabela de carga tributária aproximada relacionada principalmente ao NCM/NBS e utilizada para a informação prevista na Lei 12.741/2012. O próprio IBPT orienta a integração da tabela ao cadastro do sistema e sua atualização periódica.

Portanto, eu criaria algo como:

IBPTTable

com:

id
ncm
ex
descricao
aliquota_nacional
aliquota_importados
aliquota_estadual
aliquota_municipal
vigencia_inicio
vigencia_fim
fonte
versao

E então:

Product
   │
   └── NCM
          │
          ▼
       IBPTTable

Assim você não precisa gravar a alíquota IBPT dentro de cada produto.

Quando atualizar a tabela IBPT, atualiza-se a tabela central.

Isso é especialmente importante porque as tabelas possuem vigência e precisam ser atualizadas; o próprio IBPT informa versões e períodos de vigência.

7. E tem um detalhe ainda mais importante: não misture regra com resultado

Eu dividiria assim:

Cadastro
Product
├── NCM
├── CEST
├── Origem
└── ...
Regra
TaxRule
├── regime
├── operação
├── CFOP
├── CST/CSOSN
├── alíquota
├── redução
├── ST
└── ...
Resultado da nota
InvoiceItem
├── quantidade
├── valor
├── CFOP aplicado
├── CST/CSOSN aplicado
├── base ICMS
├── alíquota ICMS
├── valor ICMS
├── base ST
├── valor ST
└── demais valores

Isso é fundamental.

Se amanhã uma regra fiscal mudar, você não deve alterar o histórico das notas já emitidas.

A NF-e deve conservar aquilo que efetivamente foi utilizado na operação.

8. Arquitetura que eu recomendaria

Para o seu projeto, eu chegaria a algo próximo disso:

┌─────────────────────────┐
│        PRODUCT          │
├─────────────────────────┤
│ id                      │
│ name                    │
│ brand_id                │
│ category_id             │
│ ncm                     │
│ cest                    │
│ origin                  │
│ unit_id                 │
│ description             │
└───────────┬─────────────┘
            │
            │ 1:N
            ▼
┌─────────────────────────┐
│     PRODUCT_VARIANT     │
├─────────────────────────┤
│ id                      │
│ product_id              │
│ sku                     │
│ gtin                    │
│ attributes JSONB        │
│ cost                    │
│ price                   │
│ stock                   │
└───────────┬─────────────┘
            │
            │ 0:N
            ▼
┌─────────────────────────┐
│       TAX_RULE          │
├─────────────────────────┤
│ id                      │
│ product_id              │
│ variant_id nullable     │
│ tax_regime              │
│ operation_type          │
│ destination_uf          │
│ cfop                    │
│ cst                     │
│ csosn                   │
│ icms_rate               │
│ ...                     │
└─────────────────────────┘

E separadamente:

┌─────────────────────────┐
│       IBPT_TABLE        │
├─────────────────────────┤
│ id                      │
│ ncm                     │
│ version                 │
│ valid_from              │
│ valid_until             │
│ federal_rate            │
│ state_rate              │
│ municipal_rate          │
└─────────────────────────┘
9. Quando a tributação deve ir para a Variação?

Existe uma exceção importante.

Se duas variações do mesmo Produto realmente possuírem tratamentos fiscais diferentes, você precisa permitir isso.

Por exemplo:

Product
└── Variants
    ├── Variante A
    └── Variante B

Regra padrão:

Product.tax_rule

Mas:

Variant B
   ↓
tax_rule_override

Assim você evita duplicação.

A lógica seria:

REGRA FISCAL DA VARIAÇÃO
        ↓
se existir override
        ↓
usa override

senão
        ↓
usa regra do produto

Isso é muito melhor do que obrigar cada variação a possuir uma cópia completa da tributação.

10. Resumo da decisão

Eu adotaria esta regra para o seu banco:

Informação	Onde colocar
Grupo	Classificação
Subgrupo	Classificação
Categoria	Classificação
Subcategoria	Classificação
Marca	Produto
Descrição	Produto
NCM	Produto
CEST	Produto
Origem	Produto, com possibilidade de exceção
SKU	Variação
GTIN/EAN	Variação
Atributos técnicos	Variação → JSONB
Custo	Variação
Preço	Variação
Estoque	Variação
IBPT	Tabela própria vinculada pelo NCM
CST	TaxRule
CSOSN	TaxRule
CFOP	TaxRule, conforme operação
ICMS	TaxRule + cálculo da operação
PIS/COFINS	TaxRule + cálculo da operação
Valores efetivamente calculados	Item da NF
Em uma frase:

Produto define o que é a mercadoria; Variação define qual unidade comercial específica é vendida; TaxRule define como aquela mercadoria deve ser tratada em determinado contexto fiscal; e o Item da NF registra o resultado efetivamente aplicado naquela operação.

Essa separação é a que eu usaria para a Casa LM, especialmente porque você pretende ter posteriormente NF-e/NFC-e e integração com SEFAZ-MG. Ela evita colocar regras tributárias rígidas demais no cadastro e deixa espaço para operações internas, interestaduais, Simples Nacional e futuras mudanças tributárias.

E há uma consequência importante para o prompt anterior: eu alteraria a arquitetura fiscal do prompt para introduzir TaxRule/FiscalProfile em vez de simplesmente colocar CST, CSOSN e CFOP diretamente em ProductVariant.