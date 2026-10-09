# -*- coding: utf-8 -*-
"""Entrada del ejecutable `omnicad-mcp` (servidor MCP) de la app instalada: lo que registra `omnicad setup`."""
import sys

from omnicad.servidor_mcp.principal import main

sys.exit(main())
