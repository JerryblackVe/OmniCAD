# -*- coding: utf-8 -*-
"""
API única de OmniCAD: sin Qt y sin el paquete `mcp`. De acá salen las herramientas del servidor MCP, los
comandos de la CLI y la documentación generada.

    from omnicad import api
    s = api.Sesion()
    api.llamar(s, "create_parameter", {"name": "ancho", "expression": "60 mm"})
    → {"ok": True, "result": {...}, "avisos": []}

Cómo se agrega una herramienta: ver `registro.py`. Convención de imágenes: `Imagen` (también en `registro.py`).
"""
import importlib
import pkgutil

from .registro import Expr, Imagen, catalogo, herramienta, llamar
from .errores import ErrorAPI
from .sesion import Sesion
# Cada módulo `herramientas_*.py` registra sus herramientas al importarse: se cargan todos solos.
for _modulo in pkgutil.iter_modules(__path__):
    if _modulo.name.startswith("herramientas_"):
        importlib.import_module(f"{__name__}.{_modulo.name}")

__all__ = ["Sesion", "herramienta", "catalogo", "llamar", "ErrorAPI", "Imagen", "Expr"]
