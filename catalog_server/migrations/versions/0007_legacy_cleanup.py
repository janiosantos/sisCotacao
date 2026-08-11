"""0007 — Reclassificação e higienização de produtos legados (v2 refinada).

Extrai códigos de fabricante do nome para `external_id`, cria famílias
(hydraulic included), reclassifica produtos órfãos e remove falsos positivos
da regra genérica `\bCabo\b` (que capturava "Cabo Madeira" de martelos).

Idempotente: verifica se a família "Acessórios para Ferramentas" existe.
"""
from __future__ import annotations

import re
import sqlite3

VERSION = 7
NAME = "Reclassificação e higienização de produtos legados (v2)"

NOVAS_FAMILIAS: list[dict] = [
    {
        "nome": "Acessórios para Ferramentas",
        "descricao": "Adaptadores, soquetes, mandris e acessórios",
        "atributos": [
            ("Tipo de Encaixe", "lista", '["1/4\\"", "3/8\\"", "1/2\\"", "Hexagonal", "SDS"]', 1),
            ("Tamanho", "livre", "[]", 2),
            ("Comprimento", "livre", "[]", 3),
            ("Material", "lista", '["Aço Carbono", "Aço Inox", "Cromo Vanádio"]', 4),
        ],
    },
    {
        "nome": "Fixação e Aperto",
        "descricao": "Abraçadeiras, braçadeiras, presilhas",
        "atributos": [
            ("Tipo", "lista", '["Abraçadeira", "Braçadeira", "Presilha", "Gancho"]', 1),
            ("Material", "lista", '["Aço Inox", "Aço Zincado", "Nylon", "Plástico"]', 2),
            ("Tamanho", "livre", "[]", 3),
            ("Diâmetro", "livre", "[]", 4),
        ],
    },
    {
        "nome": "Químicos e Adesivos",
        "descricao": "Adesivos, colas, selantes e sprays químicos",
        "atributos": [
            ("Tipo", "lista", '["Adesivo Instantâneo", "Silicone", "Spray", "Selante"]', 1),
            ("Marca", "livre", "[]", 2),
            ("Volume", "livre", "[]", 3),
        ],
    },
    {
        "nome": "Lubrificantes e Aerossóis",
        "descricao": "Lubrificantes, desengripantes, aerossóis",
        "atributos": [
            ("Tipo", "lista", '["Lubrificante", "Desengripante", "Aerossol", "Protetivo"]', 1),
            ("Volume", "livre", "[]", 2),
        ],
    },
    {
        "nome": "Instrumentos de Medição",
        "descricao": "Multímetros, alicates amperímetros, voltímetros",
        "atributos": [
            ("Tipo", "lista", '["Alicate Amperímetro", "Multímetro", "Voltímetro", "Megôhmetro"]', 1),
            ("Categoria de Segurança", "lista", '["CAT I", "CAT II", "CAT III", "CAT IV"]', 2),
            ("Faixa de Medição", "livre", "[]", 3),
        ],
    },
    {
        "nome": "Soquetes e Bocais",
        "descricao": "Bocais, soquetes, conectores para lâmpadas",
        "atributos": [
            ("Tipo de Bocal", "lista", '["E27", "E14", "E40", "GU10", "G4", "G9"]', 1),
            ("Cor", "lista", '["Branco", "Preto", "Marrom", "Bege"]', 2),
            ("Material", "lista", '["Termoplástico", "Porcelana", "Metal"]', 3),
        ],
    },
    {
        "nome": "Quadros e Caixas",
        "descricao": "Quadros de distribuição, caixas de passagem",
        "atributos": [
            ("Tipo", "lista", '["Sobrepor", "Embutir"]', 1),
            ("Capacidade", "livre", "[]", 2),
            ("Material", "lista", '["Plástico", "Metal", "PVC"]', 3),
        ],
    },
    {
        "nome": "Tubos e Conexões",
        "descricao": "Tubos, conexões, joelhos e flanges hidráulicas",
        "atributos": [
            ("Tipo", "lista", '["Tubo", "Joelho", "Conexão", "Flange", "Tê", "Luva", "Curva"]', 1),
            ("Material", "lista", '["PVC", "Cobre", "Aço Galvanizado", "PPR", "CPVC", "Ferro Fundido"]', 2),
            ("Diâmetro", "livre", "[]", 3),
        ],
    },
    {
        "nome": "Registros e Válvulas",
        "descricao": "Registros de água, válvulas de esfera, gaveta e retenção",
        "atributos": [
            ("Tipo", "lista", '["Registro de Esfera", "Registro de Gaveta", "Válvula de Retenção"]', 1),
            ("Material", "lista", '["PVC", "Metal", "Latão", "Aço Inox"]', 2),
            ("Diâmetro", "livre", "[]", 3),
        ],
    },
    {
        "nome": "Mangueiras",
        "descricao": "Mangueiras d'água, jardim e nível",
        "atributos": [
            ("Tipo", "lista", '["Mangueira Plástica", "Mangueira Trançada", "Mangueira de Jardim"]', 1),
            ("Diâmetro", "livre", "[]", 2),
            ("Comprimento", "livre", "[]", 3),
        ],
    },
]

PALAVRAS_PROIBIDAS = {
    "Antichama", "Branco", "Preto", "Vermelho", "Azul", "Verde", "Amarelo",
    "Cinza", "Marrom", "Bege", "Rosa", "Laranja", "Violeta", "Prata", "Dourado",
    "Flexivel", "Flexível", "Inox", "Zincado", "Fosfatizado",
    "Tigre", "Amanco", "Corfio", "SIL", "Vonder", "Gedore", "Tramontina",
    "Makita", "Bosch", "Rayco", "Famastil", "Minipa", "Foxlux", "Lorenzetti",
    "Black", "Decker", "Segurimax", "Ipec", "Mega", "Suprens", "Flexsil",
    "Rolo", "Avulso", "Metro", "Metros", "Lote", "Unidade", "Kit", "Pct",
    "Sobrepor", "Embutir", "Nenhum",
}

PADROES_NAO_CODIGO = re.compile(
    r"^\d+(ML|L|M|CM|MM|KG|G|MG|W|V|A|HZ|AH|MM2|MM²|POL|M2|M3|BAR|PSI)\b",
    re.IGNORECASE,
)

PADROES_CODIGO = [
    re.compile(r"\s+([A-Z0-9][A-Z0-9\-./]{4,40})$", re.IGNORECASE),
    re.compile(r"\s+Ref[.:]?\s+([A-Z0-9\-./]{3,30})$", re.IGNORECASE),
    re.compile(r"\s+(\d{5,15})$"),
    re.compile(r"\s+-\s+([A-Z0-9][A-Z0-9\-./]{3,30})$", re.IGNORECASE),
]

# Palavras que tornam "Cabo" = handle (ferramenta), não fio elétrico
TERMOS_CABO_FERRAMENTA = [
    "Martelo", "Marreta", "Machado", "Enxada", "Picareta", "Cavadeira",
    "Chave", "Alicate", "Serra", "Lima", "Ferramenta",
    "Cabo Madeira", "Cabo Fibra", "Cabo Emborrachado", "Cabo Tubular",
    "Cabo Antifaiscante", "Cabo de Madeira", "Cabo de Fibra",
]

CLASSIFICACAO = [
    # Hidráulica (mais específico primeiro)
    (r"(?i)\b(Joelho|Tubo|Conexão)\b.*(PVC|Soldável|Esgoto|Água|PPR|CPVC|Cobre|Galvanizado)", "Tubos e Conexões"),
    (r"(?i)\bRegistro\b.*(Água|Esfera|Gaveta|PVC|Metal)", "Registros e Válvulas"),
    (r"(?i)\bVálvula\b(?!.*(Máscara|Respiratória|PFF))", "Registros e Válvulas"),
    (r"(?i)\bMangueira\b(?!.*(Decorativa|Led|Luz|Natal))", "Mangueiras"),
    # Bocal/Soquete antes de Cabo (evita "Soquete Cabo" virar cabo)
    (r"(?i)\bBocal\b|\bSoquete\b(?!.*Impacto)", "Soquetes e Bocais"),
    # Cabo: só se NÃO for ferramenta
    (r"(?i)\bCabo\b", "Cabo Flexível"),
    # Quadro antes de Disjuntor (mais específico)
    (r"(?i)\bQuadro.*(Distribui[cç][ãa]o|Disjuntor)\b", "Quadros e Caixas"),
    # Disjuntor
    (r"(?i)\bDisjuntor\b|\bConector.*Disjuntor\b", "Material Elétrico"),
    # Instrumentos
    (r"(?i)\bMult[ií]metro\b|\bAmper[ií]metro\b|\bOsciloscópio\b", "Instrumentos de Medição"),
    # Ferramentas
    (r"(?i)\b(Martelo|Marreta|Machado|Enxada|Picareta|Cavadeira)\b", "Ferramentas"),
    (r"(?i)\bAlicate\b", "Ferramentas"),
    (r"(?i)\b(Chave|Serra|Lima|Broca|Fresa|Pastilha)\b", "Ferramentas"),
    (r"(?i)\bAdaptador.*(Soquete|Encaixe|Impacto)\b", "Acessórios para Ferramentas"),
    (r"(?i)\bSoquete.*Impacto\b", "Acessórios para Ferramentas"),
    # Fixação
    (r"(?i)\bAbraçadeira\b|\bBraçadeira\b|\bPresilha\b", "Fixação e Aperto"),
    # Químicos
    (r"(?i)\bAdesivo\b|\bCola\b|\bSuper\s+Bonder\b", "Químicos e Adesivos"),
    (r"(?i)\bAerosol\b|\bSpray\b|\bLubrificante\b|\bDesengripante\b", "Lubrificantes e Aerossóis"),
    # Iluminação
    (r"(?i)\bL[âa]mpada\b|\bBulbo\b|\bLED\b(?!.*Mangueira)", "Lâmpada"),
]

# Falsos positivos para limpeza pós-classificação
FALSOS_POSITIVOS = [
    ("Tubos e Conexões", r"(?i)\bLuva\b.*(Segurança|Malha|Pigmentada|Borracha|Látex|Antiderrapante)", "Ferramentas"),
    ("Tubos e Conexões", r"(?i)\b(Abraçadeira|Braçadeira|Presilha)\b", "Fixação e Aperto"),
    ("Registros e Válvulas", r"(?i)\b(Máscara|Respirador|Respiratória|PFF)\b", "Ferramentas"),
    ("Registros e Válvulas", r"(?i)\bMacaco\b.*(Hidropneumático|Hidráulico)\b", "Ferramentas"),
    ("Mangueiras", r"(?i)\bMangueira\b.*(Decorativa|Led|Luz|Natal|Luminosa)\b", "Material Elétrico"),
    ("Mangueiras", r"(?i)\b(Mangueira|Carretel)\b.*(Ar\s+Comprimido|Pneumática)\b", "Ferramentas"),
]


def _eh_cabo_ferramenta(nome: str) -> bool:
    """Retorna True se 'Cabo' no nome significa 'cabo de ferramenta' (handle)."""
    nome_lower = nome.lower()
    if "cabo" not in nome_lower:
        return False
    if any(termo.lower() in nome_lower for termo in ["martelo", "marreta", "machado", "enxada", "picareta", "cavadeira", "ancinho", "alavanca"]):
        return True
    for t in TERMOS_CABO_FERRAMENTA:
        if t.lower() in nome_lower:
            return True
    return False


def _extrair_codigo(nome: str) -> tuple[str, str | None]:
    original = nome.strip()
    for pat in PADROES_CODIGO:
        m = pat.search(original)
        if not m:
            continue
        cod = m.group(1).strip()
        nome_limpo = original[: m.start()].strip()
        if re.match(r"^\d+[xX]\d+", cod) or re.match(r"^\d+[.,]\d+", cod):
            continue
        if PADROES_NAO_CODIGO.match(cod):
            continue
        if cod.rstrip(".") in PALAVRAS_PROIBIDAS:
            continue
        if not re.search(r"\d", cod):
            continue
        if len(cod) >= 4:
            return nome_limpo, cod
    return original, None


def _limpar_nome(nome: str) -> str:
    n = nome.strip()
    subs = {r"\bEncx\b": "Encaixe", r"\bFLEX\b": "Flexível", r"\bAR\b": "Aço Inox", r"\bFIF\b": ""}
    for pat, repl in subs.items():
        n = re.sub(pat, repl, n)
    n = re.sub(r"\s+", " ", n).strip()
    n = re.sub(r"\s*-\s*-\s*", " - ", n)
    return n.strip(" -")


def guard(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM familias WHERE nome='Acessórios para Ferramentas'"
    ).fetchone()
    return row[0] > 0


def forward(conn: sqlite3.Connection) -> None:
    conn.execute("BEGIN")
    try:
        # ---- 1. Criar novas famílias ----
        familia_ids: dict[str, int] = {}
        for fam in NOVAS_FAMILIAS:
            conn.execute(
                "INSERT OR IGNORE INTO familias (nome, descricao, ativo) VALUES (?,?,1)",
                (fam["nome"], fam["descricao"]),
            )
            row = conn.execute("SELECT id FROM familias WHERE nome=?", (fam["nome"],)).fetchone()
            if row is None:
                raise RuntimeError(f"Falha ao criar família '{fam['nome']}'")
            familia_ids[fam["nome"]] = row[0]
            for attr_nome, attr_tipo, attr_opcoes, attr_ordem in fam["atributos"]:
                conn.execute(
                    "INSERT OR IGNORE INTO familia_atributos (familia_id, nome, tipo, opcoes, ordem, obrigatorio) VALUES (?,?,?,?,?,0)",
                    (familia_ids[fam["nome"]], attr_nome, attr_tipo, attr_opcoes, attr_ordem),
                )

        # ---- 2. Mapa completo de famílias ----
        todas = conn.execute("SELECT id, nome FROM familias").fetchall()
        id_familia = {r[1]: r[0] for r in todas}

        # ---- 3. Processar produtos em lote ----
        produtos = conn.execute(
            "SELECT id, nome, marca, external_id, familia_id FROM produtos_cadastro"
        ).fetchall()

        for prod in produtos:
            pid = prod[0]
            nome_original = prod[1]
            marca = prod[2] or ""
            fam_atual = prod[4]
            ext_atual = prod[3]
            ext_str = str(ext_atual or "")

            # 3a. Limpar nome e extrair código
            nome_limpo, codigo = _extrair_codigo(nome_original)
            nome_limpo = _limpar_nome(nome_limpo)
            nome_final = nome_limpo if nome_limpo != nome_original else nome_original

            # 3b. External ID
            ext_eh_medida = bool(PADROES_NAO_CODIGO.match(ext_str))
            ext_valido = ext_atual and not ext_eh_medida and re.search(r"\d", ext_str) and ext_str not in PALAVRAS_PROIBIDAS
            codigo_final = codigo if codigo else (ext_atual if ext_valido else None)

            # 3c. Classificação: pular se "Cabo" = ferramenta
            if "Cabo Flexível" in id_familia and _eh_cabo_ferramenta(nome_original):
                novafam = None
            else:
                novafam = None
                for padrao, fam_nome in CLASSIFICACAO:
                    if re.search(padrao, nome_original):
                        if fam_nome in id_familia:
                            novafam = id_familia[fam_nome]
                        break

            # Fallback para Importados
            if fam_atual == 32 and not novafam:
                if re.search(r"(?i)\bAbraçadeira\b", nome_original):
                    novafam = id_familia.get("Fixação e Aperto")
                elif re.search(r"(?i)\b(Alicate|Ferramenta|Martelo|Chave)\b", nome_original):
                    novafam = id_familia.get("Ferramentas")

            # 3d. Montar UPDATE
            updates: list[str] = []
            params: list = []

            if nome_final != nome_original:
                updates.append("nome=?")
                params.append(nome_final)

            if codigo_final and codigo_final != ext_str:
                updates.append("external_id=?")
                params.append(codigo_final)
            elif not ext_valido and ext_atual:
                updates.append("external_id=NULL")

            if novafam and fam_atual != novafam:
                updates.append("familia_id=?")
                params.append(novafam)

            if updates:
                params.append(pid)
                conn.execute(
                    f"UPDATE produtos_cadastro SET {', '.join(updates)}, atualizado_em=datetime('now') WHERE id=?",
                    params,
                )

        # ---- 4. Limpeza de falsos positivos pós-classificação ----
        for fam_origem, padrao_regex, fam_destino in FALSOS_POSITIVOS:
            oid = id_familia.get(fam_origem)
            did = id_familia.get(fam_destino)
            if not oid or not did:
                continue
            for r in conn.execute(
                "SELECT id, nome FROM produtos_cadastro WHERE ativo=1 AND familia_id=?",
                (oid,),
            ).fetchall():
                if re.search(padrao_regex, r[1]):
                    conn.execute(
                        "UPDATE produtos_cadastro SET familia_id=?, atualizado_em=datetime('now') WHERE id=?",
                        (did, r[0]),
                    )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def backward(conn: sqlite3.Connection) -> None:
    conn.execute("BEGIN")
    try:
        nomes = tuple(fam["nome"] for fam in NOVAS_FAMILIAS)
        placeholders = ",".join("?" * len(nomes))
        conn.execute(
            f"UPDATE produtos_cadastro SET familia_id=32, atualizado_em=datetime('now') "
            f"WHERE familia_id IN (SELECT id FROM familias WHERE nome IN ({placeholders}))",
            nomes,
        )
        conn.execute(
            f"DELETE FROM familia_atributos WHERE familia_id IN "
            f"(SELECT id FROM familias WHERE nome IN ({placeholders}))",
            nomes,
        )
        conn.execute(
            f"DELETE FROM familias WHERE nome IN ({placeholders})",
            nomes,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
