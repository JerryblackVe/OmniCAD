# -*- coding: utf-8 -*-
"""OmniCAD — CAD 3D paramétrico minimalista (re-implementación limpia, uso educativo)."""
import os
from pathlib import Path

VERSION = "0.1.0"
NOMBRE_APP = "OmniCAD"


def carpeta_datos():
    """%LOCALAPPDATA%/OmniCAD (o la carpeta personal): donde la app guarda lo suyo (autoguardado, temas…)."""
    return Path(os.environ.get("LOCALAPPDATA") or str(Path.home())) / NOMBRE_APP
