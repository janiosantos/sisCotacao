"""API do painel (Dashboard)."""
from __future__ import annotations

from flask import Blueprint, jsonify

from catalog_server.repositories import dashboard

api_dashboard_bp = Blueprint("api_dashboard", __name__)


@api_dashboard_bp.get("/api/dashboard")
def resumo_dashboard():
    return jsonify({
        "resumo": dashboard.resumo(),
        "estoque_baixo": dashboard.estoque_baixo_lista(),
        "top_vendas": dashboard.top_vendas(),
    })
