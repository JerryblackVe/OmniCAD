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
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def _manejador_log():
    """Adónde va el registro: a la consola si hay; en la app sin consola (OmniCAD.exe, sys.stderr = None) a
    omnicad.log en la carpeta de datos. Sin esto cada aviso imprimía «--- Logging error ---». El archivo se
    ENROULA (2 MB, una copia) en vez de pisarse: el registro de la sesión anterior sobrevive a un crasheo
    (B-21, incidente de la madrugada del 13/10 sin rastro)."""
    if sys.stderr is not None:
        return logging.StreamHandler()
    try:
        from omnicad import carpeta_datos
        carpeta = carpeta_datos()
        carpeta.mkdir(parents=True, exist_ok=True)
        return RotatingFileHandler(carpeta / "omnicad.log", mode="a", maxBytes=2_000_000, backupCount=1,
                                   encoding="utf-8", delay=True)
    except OSError:
        return logging.NullHandler()


def _abrir_issue(ruta):
    """Abre el navegador en la página de «nuevo issue» de GitHub con el informe ya cargado (sin rutas
    de la casa ni datos personales: se recortan a «~»). Nada se manda solo: la persona revisa y envía
    (pendiente 20 del PROJECT_LOG)."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    from omnicad import informes_error
    QDesktopServices.openUrl(QUrl(informes_error.url_issue(ruta.name, ruta.parent)))


def _avisar_error(ruta):
    """Cartel después de un error no capturado (pendiente 20): el detalle quedó en el informe y se puede
    abrir la carpeta de errores o reportarlo en GitHub."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QMessageBox

    caja = QMessageBox()
    caja.setIcon(QMessageBox.Icon.Critical)
    caja.setWindowTitle("OmniCAD tuvo un problema")
    caja.setText("Se produjo un error y el detalle quedó guardado en el informe de esta sesión:\n"
                 f"{ruta}")
    b_carpeta = caja.addButton("Abrir carpeta de errores", QMessageBox.ButtonRole.ActionRole)
    b_reporte = caja.addButton("Reportar problema", QMessageBox.ButtonRole.ActionRole)
    caja.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
    caja.exec()
    if caja.clickedButton() is b_carpeta:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta.parent)))
    elif caja.clickedButton() is b_reporte:
        _abrir_issue(ruta)


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
    if (sys.argv[1:] if argv is None else argv)[:1] == ["--tarea-aislada"]:
        from omnicad.nucleo import aislado      # hijo de `aislado.correr` en la app instalada (sin ventana ni Qt)
        return aislado.principal((sys.argv[2:] if argv is None else argv[1:]))
    ap = argparse.ArgumentParser(description="OmniCAD — CAD 3D paramétrico minimalista")
    ap.add_argument("proyecto", nargs="?", help="archivo .omnicad a abrir")
    ap.add_argument("--ejemplo", action="store_true", help="cargar el modelo de ejemplo")
    ap.add_argument("--prueba-humo", action="store_true", help="prueba automática de la interfaz completa")
    ap.add_argument("--puente", action="store_true",
                    help="permitir que agentes IA controlen esta sesión (MCP en vivo, solo 127.0.0.1)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", handlers=[_manejador_log()])
    logging.getLogger("omnicad").info("=== Arranque %s (pid %s) ===",
                                      time.strftime("%Y-%m-%d %H:%M:%S"), os.getpid())   # marca de sesión
    from omnicad import informes_error
    informes_error.instalar()          # informes/ de la carpeta de datos: un archivo por sesión (P20)
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
    from omnicad.ui import arranque
    arranque.poner_icono(app)

    if args.prueba_humo:
        from omnicad.prueba_humo import ejecutar
        return ejecutar()
    informes_error.instalar(avisar=_avisar_error)   # el cartel con «Abrir carpeta de errores», solo en la app

    portada = arranque.mostrar_portada(app)      # mientras se importa lo pesado (OCP, OpenGL…), como Fusion
    from omnicad.ui.ventana import VentanaPrincipal
    ventana = VentanaPrincipal()
    ventana.showMaximized()
    if portada:
        portada.finish(ventana)
    if args.puente and not ventana.encender_puente():
        logging.getLogger("omnicad").warning("No se pudo encender el puente para agentes IA.")
    if args.proyecto:
        ventana.abrir_ruta(args.proyecto, preguntar=not args.puente)   # con el puente, un diálogo modal lo bloquearía
    elif args.ejemplo:
        ventana.cargar_ejemplo()
    else:
        ventana.verificar_autoguardado_huerfano(solo_avisar=args.puente)    # con el puente, un diálogo modal lo bloquearía
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
