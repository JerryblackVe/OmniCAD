# -*- coding: utf-8 -*-
"""
Catálogo de comandos con diálogo al estilo Fusion (ver `ui/comando.py`).

`CATALOGO`: clave de acción → clase de comando (la ventana crea una QAction por cada uno).
`POR_TIPO`: tipo de operación del timeline → clase de comando que la edita (doble clic en el timeline).
"""
CATALOGO = {}
POR_TIPO = {}


def registrar(*clases):
    for c in clases:
        CATALOGO[c.CLAVE] = c
        if c.CLASE_OP is not None:
            POR_TIPO.setdefault(c.CLASE_OP.TIPO, c)
    return clases


from . import chapa, construir, crear, ensamblar, fijacion, insertar, inspeccionar, malla, modificar, solido, superficie  # noqa: E402,F401  (cada módulo se registra al importarse)
from . import asas_extra  # noqa: E402,F401  (engancha asas en la vista a comandos ya registrados)


def comando_para(op):
    """Clase de comando que edita esa operación. Si varios comandos crean el mismo tipo de operación
    (planos, ejes, puntos, patrones), manda la VARIANTE: (parámetro, valor) que distingue a cada uno."""
    clase = construir.POR_TIPO_CONSTRUCCION.get((op.TIPO, op.p.get("tipo", "desfase")))
    if clase is not None:
        return clase
    for c in CATALOGO.values():
        variante = getattr(c, "VARIANTE", None)
        if c.CLASE_OP is not None and c.CLASE_OP.TIPO == op.TIPO and variante and op.p.get(variante[0]) == variante[1]:
            return c
    return POR_TIPO.get(op.TIPO)
