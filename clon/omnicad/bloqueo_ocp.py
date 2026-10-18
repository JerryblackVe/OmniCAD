# -*- coding: utf-8 -*-
"""Guardia de pruebas: un import accidental del otro kernel debe fallar."""
import importlib.abc
import os
import sys


class _Bloqueo(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "OCP" or fullname.startswith("OCP."):
            raise ImportError(f"Import prohibido por OMNICAD_BLOQUEAR_OCP: {fullname}")
        return None


def activar():
    if os.environ.get("OMNICAD_BLOQUEAR_OCP") != "1":
        return
    if any(n == "OCP" or n.startswith("OCP.") for n in sys.modules):
        raise RuntimeError("OCP ya estaba importado antes de activar su bloqueo.")
    if not any(isinstance(f, _Bloqueo) for f in sys.meta_path):
        sys.meta_path.insert(0, _Bloqueo())
