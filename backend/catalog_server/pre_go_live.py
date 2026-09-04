"""Inventario, preservacao e reset controlado para a entrada em operacao.

Esta rotina existe para a limpeza unica da base de testes que antecede o
go-live. Ela usa listas positivas de tabelas, nao usa CASCADE e recusa o reset
quando encontra uma tabela publica nova sem classificacao.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import sqlite3
import sys
import time
import unicodedata
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from werkzeug.security import check_password_hash

from catalog_server.db import system_conn


PROTECTED_TABLES = frozenset(
    {
        "alcada_compra",
        "beneficios_fiscais",
        "categorias",
        "centros_custo",
        "cest",
        "cest_version",
        "cfop",
        "comissao_politica",
        "condicao_parcelas",
        "condicoes_pagamento",
        "config_cobranca",
        "config_loja",
        "contabil_gatilho",
        "csosn",
        "cst_cofins",
        "cst_icms",
        "cst_pis",
        "depositos",
        "emitente",
        "endereco_posicao",
        "familia_atributos",
        "familias",
        "fiscal_engine_rule",
        "fiscal_engine_rule_condition",
        "fiscal_engine_rule_result",
        "fiscal_engine_rule_version",
        "fiscal_regra",
        "fiscal_regra_auditoria",
        "fiscal_regra_versao",
        "grupos",
        "ibpt",
        "impressao_config",
        "marcas",
        "ncm_version",
        "parceiro_politica",
        "payment_provider",
        "payment_provider_config",
        "perfis",
        "perfil_recurso",
        "plano_de_contas",
        "politica_descontos",
        "politica_fretes",
        "precificacao_configuracao",
        "rbac_audit_log",
        "recursos",
        "schema_migrations",
        "sistema_atualizacoes",
        "sistema_flags",
        "subcategorias",
        "subgrupos",
        "tabelas_preco",
        "tecnospeed_config",
        "tecnospeed_empresas",
        "unidades_compra",
        "usuario_override",
        "usuario_perfis",
        "usuarios",
        "xyz_config",
    }
)

RESET_TABLES = frozenset(
    {
        "_backup_categories",
        "_backup_crawler_state",
        "_backup_images",
        "_backup_product_attributes",
        "_backup_products",
        "abc_calculo",
        "abc_calculo_item",
        "adiantamentos",
        "alcada_aprovacao",
        "auditoria_evento",
        "cadastro_importacao",
        "caixa_movimento",
        "caixa_sessao",
        "cliente_apoio_comercial",
        "cliente_apoio_fiscal",
        "cliente_contatos",
        "cliente_enderecos",
        "cliente_interacao",
        "clientes",
        "comissao",
        "conta_anexo",
        "conta_bancaria",
        "conta_comprovante",
        "conta_pagar_rateio",
        "contas_pagar",
        "contas_receber",
        "contas_bancarias",
        "cotacao_fornecedores",
        "cotacao_itens",
        "cotacao_precos",
        "cotacoes",
        "credito_aprovacao",
        "credito_cliente",
        "credito_evento",
        "credito_reserva",
        "demanda_registro",
        "desconto_aprovacao_log",
        "devolucao_fornecedor",
        "devolucao_fornecedor_item",
        "devolucoes",
        "documentos_fiscais",
        "endereco_estoque",
        "endereco_movimento",
        "estoque_movimento",
        "estoque_parametro",
        "estoque_saldo",
        "expedicao",
        "expedicao_evento",
        "expedicao_itens",
        "extrato_bancario",
        "fiscal_config",
        "fiscal_config_historico",
        "fiscal_document_xml",
        "fiscal_snapshot",
        "fornecedor_desempenho",
        "fornecedor_contatos",
        "fornecedor_preco",
        "fornecedor_preferencial",
        "fornecedor_regra_financeira",
        "fornecedor_variantes",
        "fornecedores",
        "garantia",
        "ibpt_sugestoes",
        "idempotencia",
        "imagens_produto",
        "impressao_fila",
        "inventario_ciclo",
        "inventario_contagem",
        "inventario_itens",
        "inventarios",
        "lancamento_contabil",
        "login_rate_limit",
        "lotes",
        "movimento_bancario",
        "nfe_entrada",
        "nfe_entrada_item",
        "nfe_saida",
        "oportunidade",
        "orcamento_itens",
        "orcamento_itens_fiscal",
        "orcamento_pagamento",
        "orcamentos",
        "outbox",
        "paginas_fonte",
        "parceiro_bonus",
        "parceiro_indicacao",
        "parceiro_ponto",
        "parceiro_profissional",
        "pedido_itens",
        "pedidos_compra",
        "precificacao_competencia",
        "precificacao_revisoes",
        "preco_historico",
        "preco_regra",
        "product_fiscal_profile",
        "produto_diagnostico_variacao",
        "produto_fiscal_profile",
        "produto_identificador",
        "produto_relacao",
        "produtos_cadastro",
        "promocao_itens",
        "promocoes",
        "recebimento",
        "recebimento_divergencia",
        "recebimento_item",
        "recebimento_postagem",
        "rma",
        "scraper_sync",
        "solicitacao_compra",
        "solicitacao_itens",
        "tabela_preco_itens",
        "tolerancias_compra",
        "transportadora",
        "troca",
        "unidade_conversao",
        "vendedores",
        "webhook_log",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _public_tables(conn) -> list[str]:
    rows = conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    ).fetchall()
    return [str(row["tablename"]) for row in rows]


def _table_counts(conn, tables: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for table in tables:
        row = conn.execute(f'SELECT COUNT(*) AS total FROM "{table}"').fetchone()
        result[table] = int(row["total"])
    return result


def _schema_version(conn) -> int:
    row = conn.execute("SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations").fetchone()
    return int(row["version"])


def _access_readiness(conn) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT u.id,u.nome,u.login,u.ativo,"
        "COALESCE(string_agg(p.nome, ', ' ORDER BY p.nome),'') AS perfis "
        "FROM usuarios u "
        "LEFT JOIN usuario_perfis up ON up.usuario_id=u.id "
        "LEFT JOIN perfis p ON p.id=up.perfil_id "
        "GROUP BY u.id,u.nome,u.login,u.ativo ORDER BY u.id"
    ).fetchall()
    users = [
        {
            "id": int(row["id"]),
            "nome": str(row["nome"]),
            "login": str(row["login"]),
            "ativo": bool(row["ativo"]),
            "perfis": str(row["perfis"]),
        }
        for row in rows
    ]
    blockers: list[str] = []
    admin = conn.execute(
        "SELECT senha_hash FROM usuarios WHERE lower(login)='admin' AND ativo=1"
    ).fetchone()
    if admin:
        try:
            uses_test_password = check_password_hash(str(admin["senha_hash"]), "admin123")
        except (TypeError, ValueError):
            uses_test_password = True
        if uses_test_password:
            blockers.append(
                "O usuario admin ainda usa a senha de teste conhecida; altere-a antes do reset."
            )
    if not any(user["ativo"] and "Administrador" in user["perfis"] for user in users):
        blockers.append("Nao existe usuario Administrador ativo para o primeiro acesso.")
    return {"preserved_users": users, "blockers": blockers}


def _file_count_size(path: Path) -> tuple[int, int]:
    count = 0
    size = 0
    if not path.is_dir():
        return count, size
    for item in path.rglob("*"):
        if item.is_file():
            count += 1
            size += item.stat().st_size
    return count, size


def _gallery_verification(gallery_dir: Path) -> dict[str, Any] | None:
    marker = gallery_dir / "verified.json"
    if not marker.is_file():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    db_path = gallery_dir / "gallery.sqlite3"
    if not db_path.is_file() or data.get("database_sha256") != _sha256(db_path):
        return None
    return data


def inventory(images_dir: Path, gallery_dir: Path) -> dict[str, Any]:
    with system_conn() as conn:
        tables = _public_tables(conn)
        unknown = sorted(set(tables) - PROTECTED_TABLES - RESET_TABLES)
        counts = _table_counts(conn, tables)
        version = _schema_version(conn)
        access = _access_readiness(conn)
    source_count, source_bytes = _file_count_size(images_dir / "cadastro")
    proof = _gallery_verification(gallery_dir)
    return {
        "generated_at": _utc_now(),
        "schema_version": version,
        "unclassified_tables": unknown,
        "protected": {name: counts[name] for name in sorted(PROTECTED_TABLES & set(tables))},
        "reset": {name: counts[name] for name in sorted(RESET_TABLES & set(tables))},
        "reset_total_rows": sum(counts[name] for name in RESET_TABLES & set(tables)),
        "access_readiness": access,
        "product_images": {
            "source_dir": str(images_dir / "cadastro"),
            "source_files": source_count,
            "source_bytes": source_bytes,
            "gallery_verified": proof,
        },
    }


def _ascii_slug(value: str, *, fallback: str, limit: int) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return (value or fallback)[:limit].rstrip("-")


def _prefix(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9]", "", _ascii_slug(value, fallback="SEM", limit=64)).upper()
    return (clean[:3] or "SEM").ljust(3, "X")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalized_db_path(value: str) -> str:
    value = (value or "").replace("\\", "/").lstrip("/")
    marker = "images/"
    if marker in value.lower():
        pos = value.lower().rfind(marker)
        value = value[pos + len(marker) :]
    return value


def _load_product_metadata(conn) -> dict[int, dict[str, Any]]:
    rows = conn.execute(
        "SELECT p.id,p.nome,p.marca,COALESCE(c.nome,'') AS categoria,"
        "COALESCE(sc.nome,'') AS subcategoria "
        "FROM produtos_cadastro p "
        "LEFT JOIN categorias c ON c.id=p.categoria_id "
        "LEFT JOIN subcategorias sc ON sc.id=p.subcategoria_id"
    ).fetchall()
    return {int(row["id"]): dict(row) for row in rows}


def _load_image_references(conn) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    rows = [dict(row) for row in conn.execute(
        "SELECT id,produto_id,filename FROM imagens_produto ORDER BY id"
    ).fetchall()]
    by_path: dict[str, dict[str, Any]] = {}
    for row in rows:
        path = _normalized_db_path(str(row["filename"] or ""))
        current = by_path.get(path)
        if current is None or int(row["id"]) < int(current["id"]):
            by_path[path] = row
    return by_path, rows


def _open_gallery_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE images (
            id INTEGER PRIMARY KEY,
            source_path TEXT NOT NULL UNIQUE,
            relative_path TEXT NOT NULL UNIQUE,
            legacy_product_id INTEGER,
            legacy_image_id INTEGER,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            brand TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            bytes INTEGER NOT NULL,
            orphan INTEGER NOT NULL DEFAULT 0,
            search_text TEXT NOT NULL
        );
        CREATE TABLE missing_references (
            legacy_image_id INTEGER PRIMARY KEY,
            legacy_product_id INTEGER,
            filename TEXT NOT NULL
        );
        CREATE TABLE gallery_filters (
            kind TEXT NOT NULL,
            value TEXT NOT NULL,
            total INTEGER NOT NULL,
            PRIMARY KEY (kind, value)
        );
        CREATE VIRTUAL TABLE images_fts USING fts5(search_text, content='images', content_rowid='id');
        """
    )
    return conn


def _link_or_copy(source: Path, target: Path) -> str:
    try:
        os.link(source, target)
        return "hardlink"
    except OSError:
        shutil.copy2(source, target)
        return "copy"


def export_images(images_dir: Path, gallery_dir: Path) -> dict[str, Any]:
    source_root = (images_dir / "cadastro").resolve()
    if not source_root.is_dir():
        raise RuntimeError(f"Diretorio de imagens nao encontrado: {source_root}")
    gallery_dir.mkdir(parents=True, exist_ok=True)
    same_filesystem = source_root.stat().st_dev == gallery_dir.resolve().stat().st_dev
    free_bytes = shutil.disk_usage(gallery_dir).free
    if same_filesystem:
        required_bytes = 1024**3
    else:
        _, source_bytes = _file_count_size(source_root)
        required_bytes = source_bytes + 1024**3
    if free_bytes < required_bytes:
        raise RuntimeError(
            "Espaco insuficiente para exportar a galeria: "
            f"livre={free_bytes}, minimo={required_bytes}, "
            f"mesmo_filesystem={same_filesystem}"
        )
    for stale in gallery_dir.glob(".build-*"):
        if stale.is_dir():
            shutil.rmtree(stale)
    build = gallery_dir / f".build-{int(time.time())}-{os.getpid()}"
    media_build = build / "media"
    media_build.mkdir(parents=True)
    db_build = build / "gallery.sqlite3"

    with system_conn() as conn:
        products = _load_product_metadata(conn)
        references, all_references = _load_image_references(conn)

    files = sorted(path for path in source_root.rglob("*") if path.is_file())
    seen_db_paths: set[str] = set()
    hardlinks = 0
    copies = 0
    orphan_files = 0
    total_bytes = 0
    db = _open_gallery_db(db_build)
    try:
        for index, source in enumerate(files, start=1):
            source_relative = (Path("cadastro") / source.relative_to(source_root)).as_posix()
            reference = references.get(source_relative)
            if reference:
                seen_db_paths.add(source_relative)
            parts = source.relative_to(source_root).parts
            try:
                product_id = int(parts[0]) if parts else None
            except ValueError:
                product_id = None
            if reference and reference.get("produto_id") is not None:
                product_id = int(reference["produto_id"])
            product = products.get(product_id or -1, {})
            orphan = not bool(product)
            orphan_files += int(orphan or reference is None)
            product_name = str(product.get("nome") or f"produto-{product_id or 'sem-id'}")
            category = str(product.get("categoria") or "Sem categoria")
            subcategory = str(product.get("subcategoria") or "Sem subcategoria")
            brand = str(product.get("marca") or "Sem marca")
            digest = _sha256(source)
            image_id = int(reference["id"]) if reference else None
            suffix_id = (
                f"I{image_id:06d}"
                if image_id
                else f"F{digest[:10].upper()}_{index:06d}"
            )
            filename = (
                f"{_prefix(category)}_{_prefix(subcategory)}_"
                f"{_ascii_slug(product_name, fallback='produto', limit=84)}_"
                f"{_ascii_slug(brand, fallback='sem-marca', limit=32)}__"
                f"P{(product_id or 0):06d}_{suffix_id}{source.suffix.lower()}"
            )
            relative_target = Path(_prefix(category)) / _prefix(subcategory) / filename
            target = media_build / relative_target
            target.parent.mkdir(parents=True, exist_ok=True)
            method = _link_or_copy(source, target)
            hardlinks += int(method == "hardlink")
            copies += int(method == "copy")
            size = source.stat().st_size
            total_bytes += size
            search_text = " ".join((product_name, category, subcategory, brand, filename))
            db.execute(
                "INSERT INTO images (id,source_path,relative_path,legacy_product_id,legacy_image_id,"
                "product_name,category,subcategory,brand,sha256,bytes,orphan,search_text) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    index,
                    source_relative,
                    relative_target.as_posix(),
                    product_id,
                    image_id,
                    product_name,
                    category,
                    subcategory,
                    brand,
                    digest,
                    size,
                    int(orphan or reference is None),
                    search_text,
                ),
            )
            if index % 1000 == 0:
                db.commit()
            if index % 5000 == 0:
                print(f"export-images: {index}/{len(files)}", flush=True)

        for row in all_references:
            normalized = _normalized_db_path(str(row["filename"] or ""))
            if normalized not in seen_db_paths:
                db.execute(
                    "INSERT OR IGNORE INTO missing_references "
                    "(legacy_image_id,legacy_product_id,filename) VALUES (?,?,?)",
                    (int(row["id"]), int(row["produto_id"]), normalized),
                )
        db.execute("INSERT INTO images_fts(rowid,search_text) SELECT id,search_text FROM images")
        for kind, column in (("category", "category"), ("subcategory", "subcategory"), ("brand", "brand")):
            db.execute(
                f"INSERT INTO gallery_filters(kind,value,total) "
                f"SELECT ?,{column},COUNT(*) FROM images GROUP BY {column}",
                (kind,),
            )
        db.commit()
        missing = int(db.execute("SELECT COUNT(*) FROM missing_references").fetchone()[0])
    finally:
        db.close()

    db_hash = _sha256(db_build)
    result = {
        "generated_at": _utc_now(),
        "source_root": str(source_root),
        "source_files": len(files),
        "source_bytes": total_bytes,
        "exported_files": len(files),
        "hardlinks": hardlinks,
        "copies": copies,
        "same_filesystem": same_filesystem,
        "orphan_or_unlinked_files": orphan_files,
        "database_references": len(all_references),
        "missing_database_references": missing,
        "database_sha256": db_hash,
        "filename_pattern": "CAT_SUB_nome-base_marca__P000000_I000000.ext",
    }
    (build / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    old_media = gallery_dir / ".media-previous"
    if old_media.exists():
        shutil.rmtree(old_media)
    active_media = gallery_dir / "media"
    if active_media.exists():
        active_media.replace(old_media)
    media_build.replace(active_media)
    os.replace(db_build, gallery_dir / "gallery.sqlite3")
    os.replace(build / "manifest.json", gallery_dir / "manifest.json")
    (gallery_dir / "verified.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.rmtree(build, ignore_errors=True)
    shutil.rmtree(old_media, ignore_errors=True)
    return result


def verify_images(gallery_dir: Path, images_dir: Path | None = None) -> dict[str, Any]:
    db_path = gallery_dir / "gallery.sqlite3"
    media_dir = gallery_dir / "media"
    if not db_path.is_file() or not media_dir.is_dir():
        raise RuntimeError("Galeria nao exportada")
    checked = 0
    source_checked = 0
    total_bytes = 0
    errors: list[str] = []
    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT id,source_path,relative_path,sha256,bytes FROM images ORDER BY id"
        )
        for image_id, source_relative, relative, expected_hash, expected_bytes in rows:
            path = media_dir / relative
            if not path.is_file():
                errors.append(f"id={image_id}: arquivo ausente {relative}")
            elif path.stat().st_size != expected_bytes:
                errors.append(f"id={image_id}: tamanho divergente {relative}")
            elif _sha256(path) != expected_hash:
                errors.append(f"id={image_id}: checksum divergente {relative}")
            if images_dir is not None:
                source = (images_dir / source_relative).resolve()
                try:
                    source.relative_to(images_dir.resolve())
                except ValueError:
                    errors.append(f"id={image_id}: origem fora do diretorio permitido")
                else:
                    if not source.is_file():
                        errors.append(f"id={image_id}: origem ausente {source_relative}")
                    elif source.stat().st_size != expected_bytes:
                        errors.append(f"id={image_id}: tamanho da origem divergente")
                    elif not path.is_file() or not os.path.samestat(source.stat(), path.stat()):
                        if _sha256(source) != expected_hash:
                            errors.append(f"id={image_id}: checksum da origem divergente")
                    source_checked += 1
            checked += 1
            total_bytes += int(expected_bytes)
            if checked % 5000 == 0:
                print(f"verify-images: {checked}", flush=True)
    result = {
        "verified_at": _utc_now(),
        "checked_files": checked,
        "source_checked_files": source_checked,
        "checked_bytes": total_bytes,
        "errors": errors[:100],
        "error_count": len(errors),
        "database_sha256": _sha256(db_path),
    }
    if errors:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    marker = json.loads((gallery_dir / "manifest.json").read_text(encoding="utf-8"))
    marker["full_verification"] = result
    (gallery_dir / "verified.json").write_text(
        json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return marker


def _reset_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    proof = report["product_images"].get("gallery_verified") or {}
    return {
        "schema_version": report["schema_version"],
        "reset": report["reset"],
        "source_files": report["product_images"]["source_files"],
        "source_bytes": report["product_images"]["source_bytes"],
        "gallery_database_sha256": proof.get("database_sha256"),
        "gallery_exported_files": proof.get("exported_files"),
        "gallery_verified_files": (proof.get("full_verification") or {}).get("checked_files"),
    }


def dry_run(images_dir: Path, gallery_dir: Path) -> dict[str, Any]:
    report = inventory(images_dir, gallery_dir)
    if report["unclassified_tables"]:
        raise RuntimeError(f"Tabelas sem classificacao: {report['unclassified_tables']}")
    if report["access_readiness"]["blockers"]:
        raise RuntimeError(
            "Bloqueios de acesso para o go-live: "
            + " ".join(report["access_readiness"]["blockers"])
        )
    proof = report["product_images"].get("gallery_verified") or {}
    source_files = int(report["product_images"]["source_files"])
    if int(proof.get("exported_files", -1)) != source_files:
        raise RuntimeError("A galeria nao preserva todos os arquivos fisicos")
    if int((proof.get("full_verification") or {}).get("checked_files", -1)) != source_files:
        raise RuntimeError("A galeria ainda nao passou pela verificacao completa")
    if int((proof.get("full_verification") or {}).get("source_checked_files", -1)) != source_files:
        raise RuntimeError("As origens nao foram comparadas com o manifesto da galeria")
    snapshot = _reset_snapshot(report)
    token = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {"confirmation_token": token, "snapshot": snapshot, "inventory": report}


def _remove_operational_files(images_dir: Path) -> list[str]:
    removed: list[str] = []
    for name in ("cadastro", "comprovantes"):
        active = images_dir / name
        if not active.exists():
            active.mkdir(parents=True, exist_ok=True)
            continue
        quarantine = images_dir / f".{name}-pre-go-live-{int(time.time())}"
        active.replace(quarantine)
        active.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(quarantine)
        removed.append(name)
    return removed


def reset_database(images_dir: Path, gallery_dir: Path, confirmation: str) -> dict[str, Any]:
    planned = dry_run(images_dir, gallery_dir)
    if not confirmation or not hmac.compare_digest(confirmation, planned["confirmation_token"]):
        raise RuntimeError("Token de confirmacao ausente, invalido ou referente a outro snapshot")

    with system_conn() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('siscom-pre-go-live-reset'))")
        tables = _public_tables(conn)
        unknown = sorted(set(tables) - PROTECTED_TABLES - RESET_TABLES)
        if unknown:
            raise RuntimeError(f"Reset recusado; tabelas sem classificacao: {unknown}")
        present = sorted(RESET_TABLES & set(tables))
        quoted = ", ".join(f'"{table}"' for table in present)
        conn.execute(f"TRUNCATE TABLE {quoted} RESTART IDENTITY RESTRICT")
        # Regras vinculadas a fornecedores de teste nao podem sobreviver como
        # referencias silenciosamente invalidas. Regras genericas permanecem.
        conn.execute("DELETE FROM alcada_compra WHERE fornecedor_id IS NOT NULL")
        conn.execute(
            "INSERT INTO clientes "
            "(id,nome,tipo_pessoa,limite_credito,contribuinte,ie,c_municipio,ativo) "
            "VALUES (1,'CONSUMIDOR','f',0,'','','',1)"
        )
        conn.execute(
            "SELECT setval(pg_get_serial_sequence('clientes','id'),1,true)"
        )
        conn.execute(
            "UPDATE usuarios SET token_version=COALESCE(token_version,0)+1,"
            "atualizado_em=now()"
        )
        conn.execute(
            "INSERT INTO auditoria_evento "
            "(ator_login,acao,alvo_tipo,alvo_id,depois,motivo,correlation_id) "
            "VALUES (?,?,?,?,?::jsonb,?,?)",
            (
                "maintenance",
                "PRE_GO_LIVE_RESET",
                "sistema",
                "database",
                json.dumps(planned["snapshot"], ensure_ascii=False),
                "Limpeza controlada da base de testes antes da entrada em operacao",
                planned["confirmation_token"][:24],
            ),
        )

    removed_dirs = _remove_operational_files(images_dir)
    after = inventory(images_dir, gallery_dir)
    expected_residual = {"auditoria_evento": 1, "clientes": 1}
    unexpected = {
        name: total
        for name, total in after["reset"].items()
        if total != expected_residual.get(name, 0)
    }
    if unexpected:
        raise RuntimeError(f"Reset incompleto; contagens operacionais inesperadas: {unexpected}")
    return {
        "executed_at": _utc_now(),
        "confirmation_token": planned["confirmation_token"],
        "removed_image_directories": removed_dirs,
        "reset_total_rows_before": planned["inventory"]["reset_total_rows"],
        "audit_rows_after": after["reset"].get("auditoria_evento", 0),
        "protected": after["protected"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preparacao controlada do go-live SISCOM")
    parser.add_argument(
        "action", choices=("inventory", "export-images", "verify-images", "dry-run-reset", "reset")
    )
    parser.add_argument("--images-dir", default=os.getenv("IMAGES_DIR", "/app/images"))
    parser.add_argument("--gallery-dir", default=os.getenv("GALLERY_DATA_DIR", "/gallery"))
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args(argv)
    images_dir = Path(args.images_dir)
    gallery_dir = Path(args.gallery_dir)
    actions = {
        "inventory": lambda: inventory(images_dir, gallery_dir),
        "export-images": lambda: export_images(images_dir, gallery_dir),
        "verify-images": lambda: verify_images(gallery_dir, images_dir),
        "dry-run-reset": lambda: dry_run(images_dir, gallery_dir),
        "reset": lambda: reset_database(images_dir, gallery_dir, args.confirmation),
    }
    try:
        result = actions[args.action]()
    except Exception as exc:
        print(f"PRE_GO_LIVE_ERROR: {exc}", file=sys.stderr)
        return 1
    _json_dump(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
