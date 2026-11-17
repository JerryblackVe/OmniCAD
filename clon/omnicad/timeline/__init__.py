# -*- coding: utf-8 -*-
"""Timeline paramétrico: parámetros, operaciones (features) y documento."""
import sys

# B-590: operaciones primero; si no, importar un ops_*.py suelto cierra un ciclo con operaciones.py.
# B-624: salvo que venga del grafo (`grafo` solo necesita `parametros`, y no debe cargar OpenCascade).
if "omnicad.grafo" not in sys.modules:
    from . import operaciones  # noqa: F401
