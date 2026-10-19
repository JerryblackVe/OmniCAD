# -*- coding: utf-8 -*-
"""Revisión con el tipo nativo: por ahora solo `es_estanca` (las demás funciones de revisión, sin soporte)."""
from ..geometria import ErrorGeometria


def es_estanca(forma):
    """Un cuerpo del kernel es un sólido cerrado o una lámina: estanco si todos son sólidos con volumen (como
    OpenCascade, mira la topología, no la validez geométrica)."""
    from .. import malla as ml
    if isinstance(forma, ml.Malla):
        return forma.es_cerrada()
    if forma is None or forma.IsNull():
        raise ErrorGeometria("No hay forma para revisar: el cuerpo está vacío.")
    if forma.tipo != "cuerpo":
        return False
    from .geometria import volumen
    solidos = forma.subformas("solido")
    return bool(solidos) and all(volumen(s) > 0 for s in solidos)
