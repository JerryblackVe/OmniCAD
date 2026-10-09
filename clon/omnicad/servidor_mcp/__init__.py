# -*- coding: utf-8 -*-
"""
Servidor MCP de OmniCAD (stdio y HTTP local). Las herramientas salen solas de `omnicad.api.catalogo()`.

    python -m omnicad.servidor_mcp [--modo auto|vivo|sin_ventana] [--doc ruta.omnicad] [--toolsets a,b] [--dev]
                                  [--http --port 27190]

El paquete no se llama `omnicad/mcp` porque chocaría con el paquete `mcp` del SDK.
"""
from .principal import main
from .servidor import ServidorOmniCAD, crear_servidor

__all__ = ["main", "crear_servidor", "ServidorOmniCAD"]
