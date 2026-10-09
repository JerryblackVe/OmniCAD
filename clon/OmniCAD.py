# -*- coding: utf-8 -*-
"""
OmniCAD — punto de entrada.

    python OmniCAD.py                    abre la aplicación
    python OmniCAD.py proyecto.omnicad    abre un proyecto
    python OmniCAD.py --ejemplo          abre con el modelo de ejemplo cargado
    python OmniCAD.py --prueba-humo      prueba automática de la interfaz completa (sale con 0 si pasa)
    python OmniCAD.py --puente           enciende el puente para agentes IA (MCP en vivo) en esta sesión
"""
import argparse
import logging
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def _verificar_dependencias():
    """Avisa si falta algún paquete. Solo los BUSCA (find_spec), sin importarlos: scipy, p. ej., se carga recién al
    usar una malla o el solver de bocetos (arranque rápido)."""
    from importlib.util import find_spec
    faltan = [paquete for modulo, paquete in (("PySide6", "PySide6"), ("OpenGL", "PyOpenGL"), ("OCP", "cadquery-ocp"),
                                               ("numpy", "numpy"), ("scipy", "scipy"))
              if find_spec(modulo) is None]
    if faltan:
        sys.exit("Faltan dependencias: " + ", ".join(faltan) +
                 "\nInstalalas con:  python -m pip install -r requirements.txt")


def main(argv=None):
    ap = argparse.ArgumentParser(description="OmniCAD — CAD 3D paramétrico minimalista")
    ap.add_argument("proyecto", nargs="?", help="archivo .omnicad a abrir")
    ap.add_argument("--ejemplo", action="store_true", help="cargar el modelo de ejemplo")
    ap.add_argument("--prueba-humo", action="store_true", help="prueba automática de la interfaz completa")
    ap.add_argument("--puente", action="store_true",
                    help="permitir que agentes IA controlen esta sesión (MCP en vivo, solo 127.0.0.1)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    _verificar_dependencias()

    import omnicad.ui  # noqa: F401 — en Linux elige la plataforma de Qt y la de OpenGL ANTES de crear la aplicación
    from PySide6.QtCore import QLibraryInfo, QTranslator
    from PySide6.QtGui import QSurfaceFormat
    from PySide6.QtWidgets import QApplication

    formato = QSurfaceFormat()
    formato.setDepthBufferSize(24)
    formato.setStencilBufferSize(8)      # sombra en el suelo sin manchas dobles
    formato.setSamples(4)                # el anti-aliasing se prende y apaga en vivo (Efectos)
    QSurfaceFormat.setDefaultFormat(formato)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("OmniCAD")
    traductor = QTranslator(app)            # botones estándar de Qt en español (Guardar, Cancelar, …)
    if traductor.load("qtbase_es", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(traductor)

    if args.prueba_humo:
        from omnicad.prueba_humo import ejecutar
        return ejecutar()

    from omnicad.ui.ventana import VentanaPrincipal
    ventana = VentanaPrincipal()
    ventana.showMaximized()
    if args.puente and not ventana.encender_puente():
        logging.getLogger("omnicad").warning("No se pudo encender el puente para agentes IA.")
    if args.proyecto:
        ventana.abrir_ruta(args.proyecto)
    elif args.ejemplo:
        ventana.cargar_ejemplo()
    else:
        ventana.verificar_autoguardado_huerfano()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
