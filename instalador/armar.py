# -*- coding: utf-8 -*-
"""
Arma el instalador de OmniCAD para el sistema donde corre (ver instalador/README.md):

  Windows   PyInstaller → instalador/dist/OmniCAD/  →  Inno Setup → instalador/dist/OmniCAD-<versión>-windows-instalador.exe
  Linux     PyInstaller → instalador/dist/OmniCAD/  →  appimagetool → instalador/dist/OmniCAD-<versión>-x86_64.AppImage

    python instalador/armar.py                 todo
    python instalador/armar.py --sin-pyinstaller   reusa la carpeta ya congelada (solo vuelve a empaquetar)

Se corre con el Python del venv del proyecto (el que tiene PyInstaller): `clon/.venv/Scripts/python.exe` en Windows,
`clon/.venv/bin/python` en Linux. GitHub Actions corre lo mismo en cada versión (.github/workflows/instaladores.yml).
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent
sys.path.insert(0, str(REPO / "clon"))
from omnicad import RECURSOS, VERSION  # noqa: E402

DIST, BUILD = AQUI / "dist", AQUI / "build"
# Imágenes del asistente de Inno Setup: (ancho, alto) al 100 %, 150 % y 200 % de escala.
GRANDE = {"100": (164, 314), "150": (246, 471), "200": (328, 628)}
CHICA = {"100": (55, 55), "150": (83, 83), "200": (110, 110)}
RECORTE_PORTADA = 0.68          # centro horizontal del recorte vertical de la portada (el auto, sin cortar textos)


def _correr(argv, **kw):
    print("»", " ".join(str(a) for a in argv), flush=True)
    subprocess.run([str(a) for a in argv], check=True, **kw)


def congelar():
    _correr([sys.executable, "-m", "PyInstaller", AQUI / "omnicad.spec", "--noconfirm",
             "--distpath", DIST, "--workpath", BUILD])


def imagenes_asistente():
    """BMP del asistente: un recorte vertical de la portada (izquierda del asistente) y el ícono (arriba a la derecha)."""
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
    QGuiApplication.instance() or QGuiApplication(["armar"])
    carpeta = BUILD / "asistente"
    carpeta.mkdir(parents=True, exist_ok=True)
    portada = QImage(str(RECURSOS / "portada.jpg"))
    icono = QImage(str(RECURSOS / "omnicad_512.png"))
    for escala, (ancho, alto) in GRANDE.items():
        ancho_recorte = round(portada.height() * ancho / alto)
        x = min(max(0, round(portada.width() * RECORTE_PORTADA - ancho_recorte / 2)), portada.width() - ancho_recorte)
        img = portada.copy(QRect(x, 0, ancho_recorte, portada.height())).scaled(
            ancho, alto, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        img.convertToFormat(QImage.Format_RGB888).save(str(carpeta / f"grande_{escala}.bmp"))
    for escala, (ancho, alto) in CHICA.items():
        img = QImage(ancho, alto, QImage.Format_RGB888)
        img.fill(QColor("white"))                   # la cabecera del asistente es blanca
        p = QPainter(img)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(QRect(0, 0, ancho, alto), icono)
        p.end()
        img.save(str(carpeta / f"chica_{escala}.bmp"))
    return carpeta


def _iscc():
    candidatos = [os.environ.get("ISCC"), shutil.which("ISCC"), shutil.which("iscc"),
                  Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
                  Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
                  Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe"]
    for c in candidatos:
        if c and Path(c).is_file():
            return Path(c)
    sys.exit("No encuentro Inno Setup 6 (ISCC.exe). Instalalo (winget install JRSoftware.InnoSetup) o poné su ruta en ISCC.")


def instalador_windows():
    imagenes_asistente()
    _correr([_iscc(), f"/DVersion={VERSION}", AQUI / "windows" / "omnicad.iss"])
    return DIST / f"OmniCAD-{VERSION}-windows-instalador.exe"


def appimage_linux():
    _correr(["bash", AQUI / "linux" / "armar_appimage.sh", VERSION])
    return DIST / f"OmniCAD-{VERSION}-x86_64.AppImage"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Arma el instalador de OmniCAD para este sistema.")
    ap.add_argument("--sin-pyinstaller", action="store_true", help="reusar instalador/dist/OmniCAD (no volver a congelar)")
    args = ap.parse_args(argv)
    if not args.sin_pyinstaller:
        congelar()
    if not (DIST / "OmniCAD").is_dir():
        sys.exit(f"Falta la carpeta congelada {DIST / 'OmniCAD'}: corré sin --sin-pyinstaller.")
    if sys.platform == "win32":
        salida = instalador_windows()
    elif sys.platform.startswith("linux"):
        salida = appimage_linux()
    else:
        sys.exit("Por ahora hay instalador para Windows y Linux.")
    print(f"Listo: {salida} ({salida.stat().st_size / 2**20:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
