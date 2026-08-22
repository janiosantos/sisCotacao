# Workflow: Migration

1. Escrever o modelo alvo e as invariantes.
2. Avaliar volume, dependências e compatibilidade.
3. Criar migration versionada e backfill seguro.
4. Testar em cópia anonimizada.
5. Medir tempo, locks, falhas e rollback.
6. Executar em janela aprovada.
7. Validar contagens, constraints e amostras.
8. Atualizar documentação e plano de suporte.

Nunca apagar o snapshot fiscal de InvoiceItem para corrigir a regra atual.
