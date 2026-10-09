# -*- mode: python ; coding: utf-8 -*-
"""
Receta de PyInstaller: congela OmniCAD (Python, Qt, OpenCascade…) en UNA carpeta con tres programas:

  OmniCAD(.exe)       la app, sin consola
  omnicad-cli(.exe)   la CLI para agentes y scripts (no «omnicad»: Windows no distingue mayúsculas y pisaría OmniCAD.exe)
  omnicad-mcp(.exe)   el servidor MCP (lo registra `omnicad setup`)

Se arma desde la raíz del repo con el Python del venv (ver instalador/README.md):

    clon/.venv/Scripts/python.exe -m PyInstaller instalador/omnicad.spec --distpath instalador/dist --workpath instalador/build

Después el instalador de Windows (Inno Setup, `windows/omnicad.iss`) o el AppImage de Linux (`linux/armar_appimage.sh`)
empaquetan esa carpeta.
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

REPO = Path(SPECPATH).resolve().parent
CLON = REPO / "clon"
sys.path.insert(0, str(CLON))
from omnicad import RECURSOS, VERSION  # noqa: E402

WINDOWS = sys.platform == "win32"
ICONO = str(RECURSOS / ("omnicad.ico" if WINDOWS else "omnicad_256.png"))

# `omnicad.api` y `omnicad.cli` descubren sus módulos con pkgutil (herramientas_*, cmd_*): PyInstaller no los ve solo.
OCULTOS = collect_submodules("omnicad")
DATOS = collect_data_files("omnicad") + [
    (str(REPO / ".claude" / "skills" / "omnicad"), "skill_omnicad"),      # la copia `omnicad setup` (cmd_setup._origen_skill)
]
# Nada de esto lo usa OmniCAD; vtkmodules viene con cadquery-ocp (OCP solo necesita algunas DLL, que PyInstaller sigue solo).
EXCLUIR = ["tkinter", "vtkmodules", "vtk", "matplotlib", "IPython", "pytest", "ruff", "PyInstaller"]


def _analisis(script):
    return Analysis([str(script)], pathex=[str(CLON)], hiddenimports=OCULTOS, datas=DATOS, excludes=EXCLUIR,
                    noarchive=False)


def _programa(analisis, nombre, consola):
    return EXE(PYZ(analisis.pure), analisis.scripts, [], exclude_binaries=True, name=nombre, console=consola,
               icon=ICONO, upx=False)


app = _analisis(CLON / "OmniCAD.py")
cli = _analisis(REPO / "instalador" / "lanzadores" / "omnicad_cli.py")
mcp = _analisis(REPO / "instalador" / "lanzadores" / "omnicad_mcp.py")

coll = COLLECT(
    _programa(app, "OmniCAD", consola=False), app.binaries, app.datas,
    _programa(cli, "omnicad-cli", consola=True), cli.binaries, cli.datas,
    _programa(mcp, "omnicad-mcp", consola=True), mcp.binaries, mcp.datas,
    name="OmniCAD", upx=False,
)
print(f"OmniCAD {VERSION}: carpeta lista en {Path(DISTPATH) / 'OmniCAD'}")
