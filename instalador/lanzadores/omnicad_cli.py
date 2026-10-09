# -*- coding: utf-8 -*-
"""Entrada del ejecutable `omnicad-cli` de la app instalada: lo mismo que el comando `omnicad` de `pip install -e .`."""
import sys

from omnicad.cli import main

sys.exit(main())
