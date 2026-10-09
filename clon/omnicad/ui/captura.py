# -*- coding: utf-8 -*-
"""
Captura de la ventana REAL de OmniCAD, para verificar la interfaz sin mirar la pantalla.

    python -m omnicad.ui.captura salida.png [--ejemplo | --proyecto ruta.omnicad] [--tamano 1600x900]

Abre la ventana principal con el mismo formato OpenGL que `OmniCAD.py`, espera a que el visor dibuje,
encuadra el modelo, guarda la ventana entera en `salida.png` y sale. Las preferencias van a un .ini temporal:
no se toca la configuración del usuario ni su lista de proyectos recientes. El proyecto se abre sin los
diálogos de recuperación de autoguardado, para que nada quede esperando una respuesta.

Códigos de salida: 0 ok · 1 otra falla · 2 uso · 3 no hay pantalla u OpenGL.
La herramienta `app_screenshot` (api/herramientas_dev.py) la llama en un subproceso.
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

ESPERA_DIBUJO_MS = 800      # tiempo para que el visor pinte la primera imagen
ESPERA_ENCUADRE_MS = 300    # tiempo para que el encuadre se aplique antes de capturar
OK, FALLA, USO, SIN_PANTALLA = 0, 1, 2, 3


class SinPantalla(Exception):
    """No hay escritorio ni OpenGL: la ventana no se puede abrir (código 3)."""


def _tamano(texto):
    partes = texto.lower().split("x")
    if len(partes) != 2 or not all(p.isdigit() for p in partes):
        raise argparse.ArgumentTypeError(f"tiene que ser ANCHOxALTO (p. ej. 1600x900), no '{texto}'")
    return int(partes[0]), int(partes[1])


def _capturar(salida, ejemplo, ruta_proyecto, ancho, alto):
    from PySide6.QtCore import QLibraryInfo, QSettings, QSize, Qt, QTranslator
    from PySide6.QtGui import QSurfaceFormat
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    formato = QSurfaceFormat()          # el mismo formato que OmniCAD.py: el visor depende de él
    formato.setDepthBufferSize(24)
    formato.setStencilBufferSize(8)
    formato.setSamples(4)
    QSurfaceFormat.setDefaultFormat(formato)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("OmniCAD")
    traductor = QTranslator(app)        # botones estándar de Qt en español, como en la app
    if traductor.load("qtbase_es", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(traductor)
    if app.primaryScreen() is None:
        raise SinPantalla("no hay pantalla disponible")

    from ..ejemplo import crear_documento_ejemplo
    from ..io_archivos.proyecto import abrir as abrir_proyecto
    from .preferencias import Preferencias
    from .ventana import VentanaPrincipal

    temporal = Path(tempfile.mkdtemp(prefix="omnicad_captura_"))
    try:
        prefs = Preferencias(QSettings(str(temporal / "prefs.ini"), QSettings.IniFormat))
        try:
            ventana = VentanaPrincipal(crear_documento_ejemplo() if ejemplo else None, prefs=prefs)
        except Exception as e:  # driver sin OpenGL o sin contexto: la app no puede dibujar
            raise SinPantalla(f"no se pudo crear la ventana con OpenGL ({e})") from e
        if ruta_proyecto:
            doc = abrir_proyecto(ruta_proyecto)
            doc.ruta, doc.nombre, doc.modificado = str(ruta_proyecto), Path(ruta_proyecto).stem, False
            ventana.set_documento(doc)
        ventana.resize(ancho, alto)
        ventana.show()
        QTest.qWait(ESPERA_DIBUJO_MS)
        ventana.visor.encuadrar()
        QTest.qWait(ESPERA_ENCUADRE_MS)
        imagen = ventana.grab().toImage()
        if imagen.size() != QSize(ancho, alto):   # si la pantalla no alcanza, se escala al tamaño pedido
            imagen = imagen.scaled(ancho, alto, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        if not imagen.save(str(salida), "PNG"):
            raise OSError(f"no se pudo escribir {salida}")
        ventana.doc.modificado = False      # para cerrar sin preguntar por cambios
        ventana.close()
        return OK
    finally:
        shutil.rmtree(temporal, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m omnicad.ui.captura",
                                 description="Captura la ventana real de OmniCAD a un PNG.")
    ap.add_argument("salida", metavar="salida.png", help="PNG donde guardar la captura")
    origen = ap.add_mutually_exclusive_group()
    origen.add_argument("--ejemplo", action="store_true", help="abrir el modelo de ejemplo")
    origen.add_argument("--proyecto", metavar="ruta.omnicad", help="abrir este proyecto")
    ap.add_argument("--tamano", type=_tamano, default=(1600, 900), metavar="ANCHOxALTO",
                    help="tamaño de la captura en píxeles (defecto 1600x900)")
    args = ap.parse_args(argv)
    ancho, alto = args.tamano
    ruta_proyecto = Path(args.proyecto).resolve() if args.proyecto else None
    if ruta_proyecto is not None and not ruta_proyecto.is_file():
        ap.error(f"no existe el proyecto: {args.proyecto}")
    try:
        return _capturar(Path(args.salida).resolve(), args.ejemplo, ruta_proyecto, ancho, alto)
    except SinPantalla as e:
        print(f"captura: {e}", file=sys.stderr)
        return SIN_PANTALLA
    except Exception as e:  # noqa: BLE001 — la falla sale como mensaje claro, no como rastro
        print(f"captura: {type(e).__name__}: {e}", file=sys.stderr)
        return FALLA


if __name__ == "__main__":
    sys.exit(main())
