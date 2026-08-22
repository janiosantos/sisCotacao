# Regras de Negócio — Estoque

O estoque físico resulta de movimentos confirmados. Reserva reduz disponível, mas não físico; cancelamento de reserva devolve disponibilidade; saída reduz físico e disponível; entrada aumenta físico e disponível conforme status. Transferência gera saída de um depósito e entrada em outro com correlação.

Ajustes exigem motivo, usuário, aprovação quando acima do limite e referência a inventário. Devoluções devem apontar para a operação de origem quando possível. Lote, validade e série são obrigatórios somente para categorias parametrizadas.
