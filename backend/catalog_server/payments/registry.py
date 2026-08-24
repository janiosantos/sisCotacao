"""Seleção do provedor de pagamento por prioridade de custo (migração 0083).

O operador configura a prioridade (custo) de cada provedor por operação
(boleto/pix) e ambiente (sandbox/producao). A troca de provedor é apenas
reordenar prioridades — sem mudança de código.
"""
from __future__ import annotations

from catalog_server.payments.repo import payment_provider_repo


class ProviderIndisponivel(Exception):
    pass


def instanciar(provider_codigo: str, operacao: str, ambiente: str):
    """Instancia o provider (fase 1: Asaas/Mercado Pago)."""
    from catalog_server.payments.asaas import AsaasProvider
    from catalog_server.payments.mercadopago import MercadoPagoProvider

    cfg = payment_provider_repo.get_config(provider_codigo, operacao, ambiente)
    if cfg is None:
        raise ProviderIndisponivel(
            f"Sem configuração ativa para {provider_codigo} · {operacao} · {ambiente}"
        )
    if provider_codigo == "asaas":
        return AsaasProvider(cfg)
    if provider_codigo == "mercadopago":
        return MercadoPagoProvider(cfg)
    if provider_codigo == "efipay":
        from catalog_server.payments.efipay import EfiPayProvider

        return EfiPayProvider(cfg)
    if provider_codigo == "sicoob":
        from catalog_server.payments.sicoob import SicoobProvider

        return SicoobProvider(cfg)
    raise ProviderIndisponivel(f"Provedor não implementado: {provider_codigo}")


def escolher(operacao: str, ambiente: str):
    """Provedor ativo de menor prioridade (custo) para operação/ambiente."""
    cfg = payment_provider_repo.escolher(operacao, ambiente)
    if cfg is None:
        raise ProviderIndisponivel(
            f"Sem provedor ativo para {operacao} · {ambiente}. Configure em Integrações de pagamento."
        )
    return instanciar(cfg["provider_codigo"], operacao, ambiente)


def instanciar_por_conta(conta: dict):
    """Instancia o provider usado na conta (provider_id + tipo_cobranca)."""
    if not conta.get("provider_id"):
        raise ProviderIndisponivel("Conta sem cobrança emitida")
    from catalog_server.payments.repo import payment_provider_repo

    cfg = payment_provider_repo.get_config(
        _codigo_por_id(conta["provider_id"]),
        conta.get("tipo_cobranca") or "boleto",
        "sandbox",
    )
    if cfg is None:
        raise ProviderIndisponivel("Configuração do provedor não encontrada")
    return instanciar(cfg["provider_codigo"], cfg["operacao"], cfg["ambiente"])


def _codigo_por_id(provider_id: int) -> str:
    from catalog_server.payments.repo import payment_provider_repo

    for p in payment_provider_repo.list_providers():
        if int(p["id"]) == int(provider_id):
            return p["codigo"]
    raise ProviderIndisponivel(f"Provedor {provider_id} não encontrado")