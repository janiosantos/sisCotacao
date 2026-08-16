# Emissão fiscal via Tecnospeed/PlugNotas (NFC-e / NF-e B2B)

Fontes consultadas (ago/2026):
- [Primeiros Passos com o PlugNotas](https://atendimento.tecnospeed.com.br/hc/pt-br/articles/23715383551767)
- [Exemplo de payload de NF-e (exportação, mas mesma estrutura base)](https://atendimento.tecnospeed.com.br/hc/pt-br/articles/12446973447447)
- [Documentação Postman/PlugNotas](https://documenter.getpostman.com/view/3720339/2sB3WpSh1R)
- [Referência de rotas](https://docs.plugnotas.com.br/#tag/NFe/operation/addNFe)

## Pré-requisito: cadastro prévio na Tecnospeed (fora do sistema, uma vez)

**Nenhuma nota é emitida sem isso primeiro.** Antes de emitir qualquer
NFC-e ou NF-e, você precisa, na interface do PlugNotas
(ou via `services/tecnospeed.py::cadastrar_certificado` /
`cadastrar_empresa`):

1. Criar conta em https://conta.tecnospeed.com.br/ e pegar o token da
   Software House (aparece no avatar → "Exibir token").
2. Cadastrar o **certificado digital A1** (.pfx/.p12) do CNPJ emitente —
   `POST /certificado`.
3. Cadastrar a **empresa** (o CNPJ emitente) vinculada a esse
   certificado — `POST /empresa`, informando os módulos `nfe`/`nfce`
   ativos e se cada um roda em produção (`config.producao: true`) ou
   homologação (`false`) — **esse é o único lugar que define o
   ambiente**, não há URL separada de sandbox/produção para os envios.

Sem isso, qualquer emissão retorna erro de empresa/certificado não
encontrado.

## O que existe no sistema

- **Modo simulado (padrão)**: nenhuma chamada de rede é feita. A emissão
  fica "processando" (igual ao fluxo real, que é assíncrono) e vira
  "autorizado" na primeira consulta de status seguinte — dá pra testar
  Caixa → emitir → acompanhar status sem credenciais.
- **`documentos_fiscais`**: uma linha por tentativa de emissão (NFC-e
  modelo 65, NF-e modelo 55), ciclo de vida completo.
- **`clientes`** ganhou os campos de endereço estruturado que a NF-e B2B
  exige e a NFC-e não precisa: `numero`, `bairro`, `complemento` (os
  campos `ie`, `contribuinte` e `c_municipio`/código IBGE já existiam).
- **`services/tecnospeed.py`**: monta o payload real (ver estrutura
  abaixo), emite, consulta status, processa webhook.
- **Endpoints**:
  - `POST/GET /api/orcamentos/<id>/nfce` — NFC-e, balcão/consumidor.
  - `POST/GET /api/orcamentos/<id>/nfe` — NF-e B2B; exige que o
    orçamento tenha `cliente_id` apontando pra um cliente com CNPJ/CPF,
    IE e endereço completos.
  - `GET`/`PUT /api/tecnospeed/config` — token, ambiente, modo simulado.
  - `POST /api/webhooks/tecnospeed` — notificação assíncrona de status.
- **Caixa (ECF)**: emite NFC-e automaticamente após o recebimento.

## Contrato real da API (confirmado contra a documentação oficial)

| | Suposição inicial (errada) | Real (confirmado na doc) |
|---|---|---|
| Autenticação | `Authorization: Bearer <token>` | Header `x-api-key: <token>` |
| Ambiente | URL diferente por ambiente | Config da **empresa** cadastrada no PlugNotas (`config.producao`), mesma URL sempre |
| Resposta do envio | Autorizada na hora (chave/protocolo) | **Sempre assíncrona** — só devolve um `id`; autorização vem depois via `GET` ou webhook |
| Corpo do envio | Objeto único | `{"documento": [ {...} ]}` — array, permite lote |
| `quantidade`/`valorUnitario` do item | Número direto | Objeto `{comercial, tributavel}` |
| Forma de pagamento | `meioPagamento`/`valorPago` | `meio`/`valor` |
| **Resposta da consulta de status** | Objeto único, campo `chaveAcesso` | **Array** (mesmo consultando 1 nota), campo `chave` (não `chaveAcesso`), erro em `erro`, mensagem de sucesso em `mensagem` |
| Status possíveis | CONCLUIDO/REJEITADO/PROCESSANDO/CANCELADO | + `AGENDADO` (nota na fila, ainda nem começou a processar) |

O formato exato da consulta foi confirmado contra um exemplo real do artigo
oficial "Consultando uma Nota (Resumo NFe)":
```json
[{
  "id": "5cc8479cc2bb61002458112f", "status": "CONCLUIDO",
  "numero": "100537", "serie": "1",
  "chave": "41190408187168000160550010001005371000000008",
  "protocolo": "141190000292218", "mensagem": "Autorizado o uso da NF-e",
  "pdf": "https://.../nfe/{id}/pdf", "xml": "https://.../nfe/{id}/xml",
  "erro": null
}]
```
`services/tecnospeed.py::consultar_status` e `processar_webhook` já
foram ajustados pra esse formato exato (testado com resposta HTTP mockada
reproduzindo este JSON literal).

## O que AINDA precisa validar em homologação antes de produção

Mesmo com a estrutura corrigida contra a documentação oficial, **valide no
sandbox/homologação real antes de desligar o modo simulado**:

1. **URL e rota exatas** — `POST https://api.plugnotas.com.br/nfe` e
   `/nfce` confirmadas na doc. A rota de consulta (`GET /nfe/{id}`) foi
   inferida por convenção REST — o formato da RESPOSTA já foi validado
   contra um exemplo oficial (ver acima), mas o path exato da rota em si
   não apareceu com URL completa nos artigos consultados; confirme no
   Postman collection antes de ir para produção.
2. **NCM/CFOP/CST por item** vêm do snapshot fiscal gravado na
   finalização do orçamento (`orcamento_itens_fiscal`). Item sem esse
   snapshot **bloqueia a emissão de propósito** (não existe fallback
   "seguro" — enviar NCM/CFOP placeholder gera rejeição real da SEFAZ ou,
   pior, uma nota fiscalmente incorreta).
3. **Assinatura do webhook** — o endpoint `/api/webhooks/tecnospeed`
   ainda aceita qualquer POST sem validar origem. Adicione validação
   antes de produção.
4. **`natureza`, `finalidade`, `origem` fixos** — hoje o código usa
   `"natureza": "Venda"`, `"finalidade": 1` (normal) e `origem` do
   snapshot fiscal. Para devolução, complementar, ajuste, etc., será
   necessário parametrizar.
5. **Token de sandbox público**: `2da392a6-79d2-4304-a8b7-959572c7e44d` —
   único ambiente que não precisa de cadastro de empresa/certificado
   prévio (os retornos são mockados pela própria Tecnospeed, não vão pra
   SEFAZ de verdade). Bom para validar a estrutura do payload antes de
   partir para homologação real.

## Como configurar credenciais reais

```
PUT /api/tecnospeed/config
{
  "ambiente": "producao",
  "simulado": "0",
  "token": "SEU_TOKEN_DA_SOFTWARE_HOUSE"
}
```

Só desligue `simulado` depois de: (1) cadastrar certificado + empresa no
PlugNotas, e (2) validar os pontos da seção anterior em homologação.
