# Regra de Segurança

Aplicar menor privilégio e segregação entre consulta, manutenção de cadastro, publicação de regra e emissão fiscal. Proteger dados pessoais e credenciais de integração.

Nunca registrar em logs certificados digitais, chaves privadas, tokens, XML completo sem necessidade ou dados pessoais em excesso. Criptografar segredos em repouso e em trânsito, validar webhooks, limitar tentativas e manter trilha de auditoria.

Revisar dependências, controlar acesso a ambientes, usar dados anonimizados em testes e bloquear deploy se houver vulnerabilidade crítica ou segredo versionado.
