# SKILL — Deployment e Docker

## Princípios

Serviços devem possuir versões controladas.

Não usar `latest` em produção.

Separar claramente:

- desenvolvimento;
- homologação;
- produção.

## Docker

Alterações em:

- Dockerfile;
- compose;
- imagens;
- variáveis;
- volumes;
- rede;

devem ser avaliadas quanto ao impacto no banco e nas integrações.

## Banco

Migration deve ser executada de forma controlada antes da aplicação depender do novo schema.

## Fiscal

Homologação e produção devem ser explicitamente diferenciadas.

Nunca reutilizar acidentalmente credenciais, certificados ou endpoints de produção em homologação.
