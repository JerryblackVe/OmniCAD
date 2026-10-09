# -*- coding: utf-8 -*-
"""Elementos de los menús de la cinta (compartidos por cinta.py y cinta_boceto.py)."""

SEP = "-"


def _i(texto, clave=None, atajo="", ico=None):
    """Ítem de menú: con `clave` usa la acción real de la ventana; sin clave queda grisado."""
    return ("item", texto, clave, atajo, ico)


def _sub(texto, items):
    return ("sub", texto, items)
