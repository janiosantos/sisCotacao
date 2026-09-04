# PROBLEM

- **Severidade:** alta
- **Categoria:** segurança
- **Status:** encontrado - correção não aplicada
- **Arquivos afetados:** `AGENTS.md:224-229`

## Explicação para leigos

A documentação versionada informa endereço, usuário e uma senha de administrador de uma máquina. Quem obtiver acesso ao repositório ou ao seu histórico pode tentar usar essa credencial para assumir o host.

## Evidência e análise técnica

O bloco de ambiente DEV identifica o host e o usuário SSH e registra literalmente uma senha utilizada com `sudo`. O valor não é reproduzido neste relatório e deve ser tratado como `[REDACTED]`. Remover somente a linha atual não elimina o segredo dos commits anteriores.

## Impacto

Há risco de acesso remoto e elevação de privilégio no host, movimentação lateral para dados do ERP e comprometimento das chaves ou ambientes acessíveis a partir da máquina. O alcance depende da exposição de rede e de a senha ainda estar válida.

## Solução proposta

Rotacionar imediatamente a senha, remover qualquer instrução que a contenha e preferir SSH por chave com `sudo` controlado. Examinar o histórico e os clones/remotos autorizados; se o repositório tiver sido compartilhado, considerar reescrita coordenada do histórico e revogação de credenciais derivadas.

Uma pessoa deve validar posteriormente que a credencial antiga não autentica mais e revisar logs de acesso. Nenhuma tentativa de autenticação foi feita nesta auditoria.

## Diff/patch proposto - NÃO APLICADO

```diff
diff --git a/AGENTS.md b/AGENTS.md
@@
-**Ferramentas na VM**: ... sudo com senha `[REDACTED]`.
+**Ferramentas na VM**: ... Use autenticação SSH por chave e o procedimento
+operacional seguro fora do repositório para operações privilegiadas.
```
