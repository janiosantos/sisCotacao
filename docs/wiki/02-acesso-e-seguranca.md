# Acesso, perfis e segurança

## O que é?

É o conjunto de telas que controla identidade, perfis, permissões e manutenção
do acesso ao ERP: `#/usuarios`, `#/perfis` e `#/atualizacoes`.

## Para que serve?

Permite criar usuários individuais, aplicar menor privilégio, revisar alçadas e
acompanhar a versão instalada.

## Qual é o papel no sistema?

Toda operação usa o usuário autenticado como autor. O frontend pode desabilitar
uma ação, mas somente o backend decide se ela será aceita.

## Passo a passo do administrador

1. Cadastre o usuário em **Usuários** sem compartilhar senha.
2. Associe o perfil mínimo em **Perfis e permissões**.
3. Conceda ações críticas somente a quem executa aquela responsabilidade.
4. Teste com uma conta de cada função e revise periodicamente.
5. Desative acessos desligados e consulte **Atualizações** após uma release.

## Segregação obrigatória

Vendedor registra venda, mas não aprova seu próprio desconto nem recebe seu
próprio pedido. Operador recebe pagamento à vista, mas não aprova crediário.
Financeiro aprova crédito, baixa títulos e aprova bônus conforme a política.

## Bloqueios e solução

- **Sem acesso:** solicite ao administrador o recurso/ação correta; não use conta
  de outra pessoa.
- **Sessão expirada:** entre novamente; não tente reutilizar token antigo.
- **Ação desabilitada:** confira o estado do documento e o perfil necessário.

## Auditoria

Alterações de usuário, senha, perfis, overrides, alçadas e status precisam ter
responsável e histórico.
