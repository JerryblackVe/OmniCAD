# -*- coding: utf-8 -*-
"""La lista de claves de comandos que usa la API (sin Qt) tiene que ser la del catálogo de la ventana."""
import importlib.util
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_claves_comandos_al_dia():
    ruta = Path(__file__).resolve().parents[2] / "scripts" / "claves_comandos.py"
    espec = importlib.util.spec_from_file_location("claves_comandos_script", ruta)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    actual = modulo.DESTINO.read_text(encoding="utf-8")
    assert actual == modulo.contenido(), "Falta regenerar: clon/.venv/Scripts/python.exe scripts/claves_comandos.py"
