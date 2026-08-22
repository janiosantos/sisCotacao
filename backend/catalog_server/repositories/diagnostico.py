from __future__ import annotations

from catalog_server.db import system_conn


class DiagnosticoRepository:
    def resumo(self) -> list[dict]:
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT classificacao, COUNT(*) AS produtos, SUM(n_variantes) AS variantes "
                "FROM produto_diagnostico_variacao GROUP BY classificacao ORDER BY classificacao"
            ).fetchall()]

    def list(self, classificacao: str | None = None, revisado: bool | None = None, termo: str | None = None, limit: int = 100) -> list[dict]:
        sql = (
            "SELECT d.*, p.nome, p.marca, p.categoria_id "
            "FROM produto_diagnostico_variacao d "
            "JOIN produtos_cadastro p ON p.id = d.produto_id"
        )
        where: list[str] = []
        args: list = []
        if classificacao:
            where.append("d.classificacao = ?")
            args.append(classificacao)
        if revisado is not None:
            where.append("d.revisado = ?")
            args.append(int(revisado))
        if termo:
            where.append("(p.nome LIKE ? OR p.marca LIKE ? OR EXISTS (SELECT 1 FROM variantes vx WHERE vx.produto_id=p.id AND (vx.sku LIKE ? OR vx.ean LIKE ?)))")
            like = f"%{termo}%"
            args.extend([like, like, like, like])
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY d.n_variantes DESC, p.nome LIMIT ?"
        args.append(limit)
        with system_conn() as conn:
            return [dict(r) for r in conn.execute(sql, args).fetchall()]

    def detalhes(self, produto_id: int) -> dict:
        with system_conn() as conn:
            produto = conn.execute(
                "SELECT id, nome, marca, familia_id FROM produtos_cadastro WHERE id = ?", (produto_id,)
            ).fetchone()
            variantes = conn.execute(
                "SELECT v.id, v.sku, v.ean, v.preco, "
                "GROUP_CONCAT(fa.nome || '=' || va.valor, ' | ') AS atributos "
                "FROM variantes v LEFT JOIN variante_atributos va ON va.variante_id=v.id "
                "LEFT JOIN familia_atributos fa ON fa.id=va.atributo_id "
                "WHERE v.produto_id=? AND v.ativo=1 GROUP BY v.id ORDER BY v.id", (produto_id,)
            ).fetchall()
            return {"produto": dict(produto) if produto else None, "variantes": [dict(v) for v in variantes]}

    def marcar_revisado(self, produto_id: int, revisado: bool = True) -> bool:
        with system_conn() as conn:
            return conn.execute(
                "UPDATE produto_diagnostico_variacao SET revisado=?, atualizado_em=datetime('now') WHERE produto_id=?",
                (int(revisado), produto_id),
            ).rowcount > 0

    def consolidar_ofertas(self, produto_id: int, principal_id: int) -> dict:
        """Preserva a variante principal e desativa ofertas do mesmo EAN.

        Referências operacionais são migradas para a principal dentro de uma
        única transação; variantes antigas não são apagadas.
        """
        with system_conn() as conn:
            principal = conn.execute(
                "SELECT id, produto_id, ean FROM variantes WHERE id=? AND ativo=1", (principal_id,)
            ).fetchone()
            if not principal or principal["produto_id"] != produto_id or not principal["ean"]:
                raise ValueError("A variante principal deve pertencer ao produto e possuir EAN")
            duplicatas = conn.execute(
                "SELECT id FROM variantes WHERE produto_id=? AND ativo=1 AND id<>? AND ean=?",
                (produto_id, principal_id, principal["ean"]),
            ).fetchall()
            ids = [r["id"] for r in duplicatas]
            if not ids:
                raise ValueError("Nenhuma oferta duplicada com o mesmo EAN")

            for old_id in ids:
                # Tabelas com chave única: preserva a principal quando já existe.
                conn.execute("""
                    INSERT OR IGNORE INTO fornecedor_variantes
                        (variante_id, fornecedor_id, codigo_fornecedor, descricao_fornecedor, unidade_compra, fator_conversao)
                    SELECT ?, fornecedor_id, codigo_fornecedor, descricao_fornecedor, unidade_compra, fator_conversao
                    FROM fornecedor_variantes WHERE variante_id=?
                """, (principal_id, old_id))
                conn.execute("""
                    INSERT OR IGNORE INTO fornecedor_preco
                        (fornecedor_id, variante_id, preco, prazo_entrega, icms, ipi, moeda, data_validade, ativo)
                    SELECT fornecedor_id, ?, preco, prazo_entrega, icms, ipi, moeda, data_validade, ativo
                    FROM fornecedor_preco WHERE variante_id=?
                """, (principal_id, old_id))
                conn.execute("""
                    INSERT OR IGNORE INTO fornecedor_preferencial
                        (variante_id, fornecedor_id, ranking, ultimo_preco, ultimo_prazo)
                    SELECT ?, fornecedor_id, ranking, ultimo_preco, ultimo_prazo
                    FROM fornecedor_preferencial WHERE variante_id=?
                """, (principal_id, old_id))
                conn.execute("""
                    INSERT OR IGNORE INTO variante_atributos (variante_id, atributo_id, valor)
                    SELECT ?, atributo_id, valor FROM variante_atributos WHERE variante_id=?
                """, (principal_id, old_id))
                conn.execute(
                    "UPDATE imagens_produto SET variante_id=? WHERE variante_id=?",
                    (principal_id, old_id),
                )

                # Saldo: soma o saldo antigo na variante principal.
                conn.execute("""
                    INSERT INTO estoque_saldo (deposito_id, variante_id, quantidade, reserva, atualizado_em)
                    SELECT deposito_id, ?, quantidade, reserva, datetime('now')
                    FROM estoque_saldo WHERE variante_id=?
                    ON CONFLICT(deposito_id, variante_id) DO UPDATE SET
                      quantidade=estoque_saldo.quantidade + excluded.quantidade,
                      reserva=estoque_saldo.reserva + excluded.reserva,
                      atualizado_em=datetime('now')
                """, (principal_id, old_id))

                # Histórico e documentos continuam apontando para o produto real.
                for table in ("estoque_movimento", "lotes", "garantia", "solicitacao_itens", "expedicao_itens"):
                    conn.execute(f"UPDATE {table} SET variante_id=? WHERE variante_id=?", (principal_id, old_id))

                # Duplicatas de preço/promoção/fiscal não podem violar UNIQUE.
                for table in ("tabela_preco_itens", "promocao_itens", "fiscal_config"):
                    conn.execute(f"DELETE FROM {table} WHERE variante_id=? AND EXISTS (SELECT 1 FROM {table} p WHERE p.variante_id=?)", (old_id, principal_id))
                    conn.execute(f"UPDATE {table} SET variante_id=? WHERE variante_id=?", (principal_id, old_id))

                conn.execute("DELETE FROM fornecedor_variantes WHERE variante_id=?", (old_id,))
                conn.execute("DELETE FROM fornecedor_preco WHERE variante_id=?", (old_id,))
                conn.execute("DELETE FROM fornecedor_preferencial WHERE variante_id=?", (old_id,))
                conn.execute("DELETE FROM estoque_saldo WHERE variante_id=?", (old_id,))
                conn.execute("UPDATE variantes SET ativo=0 WHERE id=?", (old_id,))

            conn.execute(
                "UPDATE produto_diagnostico_variacao SET revisado=1, atualizado_em=datetime('now'),"
                " observacao=observacao || ' Ofertas consolidadas na variante ' || ? WHERE produto_id=?",
                (principal_id, produto_id),
            )
            return {"produto_id": produto_id, "principal_id": principal_id, "desativadas": len(ids)}


diagnostico_repo = DiagnosticoRepository()
