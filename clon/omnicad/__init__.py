# -*- coding: utf-8 -*-
"""OmniCAD — CAD 3D paramétrico minimalista (re-implementación limpia, uso educativo)."""
import os
from pathlib import Path

VERSION = "0.1.2"
NOMBRE_APP = "OmniCAD"
RECURSOS = Path(__file__).resolve().parent / "recursos"     # ícono (.ico y .png) y portada de la pantalla de carga


def carpeta_datos():
    """Donde la app guarda lo suyo (autoguardado, temas, puente.json…): %LOCALAPPDATA%/OmniCAD en Windows y
    ~/.local/share/OmniCAD en Linux y macOS (la misma regla que el complemento de Fusion, `OmniCADPuente.py`)."""
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".local" / "share") / NOMBRE_APP
