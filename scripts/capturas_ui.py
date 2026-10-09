# -*- coding: utf-8 -*-
"""
Genera capturas de pantalla de OmniCAD en evidencias/capturas/ para compararlas con las
capturas de Fusion 360 que pasó el usuario: ventana principal, elegir plano para el boceto,
boceto dentro de la vista 3D (pestaña BOCETO + paleta), menús de la cinta y de la barra de
navegación, preferencias y vistas múltiples.
Usa preferencias en un .ini temporal (no toca la configuración real del usuario).
"""
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))

from PySide6.QtCore import QPoint, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QSurfaceFormat  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402


def _menu_del_grupo(v, pestana, titulo):
    fila = v.cinta.pila.widget(pestana)
    for b in fila.findChildren(QToolButton):
        if b.text().startswith(titulo) and b.menu():
            return b, b.menu()
    raise KeyError(titulo)


def _capturar_menu(boton, menu, ruta, submenu=None):
    menu.popup(boton.mapToGlobal(QPoint(0, boton.height())))
    QTest.qWait(250)
    if submenu is None:
        menu.grab().save(str(ruta))
    else:
        accion = next(a for a in menu.actions() if a.text() == submenu)
        menu.setActiveAction(accion)
        accion.menu().popup(menu.mapToGlobal(menu.actionGeometry(accion).topRight()))
        QTest.qWait(250)
        accion.menu().grab().save(str(ruta))
        accion.menu().hide()
    menu.hide()


def main():
    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)
    _app = QApplication([])  # mantiene viva la app
    from omnicad.ejemplo import crear_documento_ejemplo
    from omnicad.ui.preferencias import DialogoPreferencias, Preferencias
    from omnicad.ui.ventana import VentanaPrincipal

    destino = RAIZ / "evidencias" / "capturas"
    destino.mkdir(parents=True, exist_ok=True)
    temporal = Path(tempfile.mkdtemp(prefix="omnicad_capturas_"))
    prefs = Preferencias(QSettings(str(temporal / "prefs.ini"), QSettings.IniFormat))
    v = VentanaPrincipal(crear_documento_ejemplo(), prefs=prefs)
    v.resize(1900, 1000)
    v.show()
    QTest.qWait(600)
    v._guardar_en(str(temporal / "Placa con aro.omnicad"))       # para que el panel de datos tenga una tarjeta
    v.visor.encuadrar()
    QTest.qWait(300)
    v.grab().save(str(destino / "ventana_principal.png"))
    for pestana, titulo, archivo in ((0, "CREAR", "menu_crear.png"), (0, "MODIFICAR", "menu_modificar.png")):
        _capturar_menu(*_menu_del_grupo(v, pestana, titulo), destino / archivo)
    boton_archivo = next(b for b in v.findChildren(QToolButton) if b.menu() is v.menu_archivo)
    _capturar_menu(boton_archivo, v.menu_archivo, destino / "menu_archivo.png")
    barra = v.barra_nav
    boton_vis = next(b for b in barra.findChildren(QToolButton) if b.menu() is barra.menus["visualizacion"])
    _capturar_menu(boton_vis, barra.menus["visualizacion"], destino / "menu_visualizacion.png")
    _capturar_menu(boton_vis, barra.menus["visualizacion"], destino / "menu_estilo_visual.png", "Estilo visual")
    boton_rej = next(b for b in barra.findChildren(QToolButton) if b.menu() is barra.menus["rejilla"])
    _capturar_menu(boton_rej, barra.menus["rejilla"], destino / "menu_rejilla.png")

    dlg = DialogoPreferencias(prefs, v)
    dlg.show()
    QTest.qWait(300)
    dlg.grab().save(str(destino / "preferencias.png"))
    dlg.reject()

    # Crear boceto: elegir el plano en la vista 3D
    v.crear_boceto()
    L = v.visor._tam_planos()
    q = v.visor.proyectar((L * 0.75, L * 0.9, 0))
    QTest.mouseMove(v.visor, q.toPoint())
    QTest.qWait(200)
    v.grab().save(str(destino / "boceto_elegir_plano.png"))
    hit = v.visor.elegir(q)
    v._plano_elegido(hit if hit and hit["plano"] is not None else
                     {"ref": "XY", "plano": __import__("omnicad.nucleo.geometria", fromlist=["x"]).Plano("XY"),
                      "marco": None})
    QTest.qWait(300)
    lz = v.modo_boceto.lienzo
    lz.ajustar_grilla = True
    for herramienta, pts in (("rectangulo", [(-30, -20), (30, 20)]), ("circulo", [(0, 0), (8, 0)]),
                             ("poligono_inscrito", [(-60, 0), (-48, 0)])):
        v.modo_boceto.herramienta(herramienta)
        for u, w in pts:
            QTest.mouseMove(lz, lz.a_px(u, w).toPoint())
            QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(u, w).toPoint())
    v.modo_boceto.herramienta("cota")
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(0, -20).toPoint())
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(0, -30).toPoint())
    if lz.entrada is not None:
        lz.entrada.campos[0].setText("ancho")
        QTest.keyClick(lz.entrada.campos[0], Qt.Key_Return)
    v.modo_boceto.herramienta("linea")
    QTest.mouseMove(lz, lz.a_px(45, 10).toPoint())
    QTest.qWait(300)
    v.grab().save(str(destino / "boceto_en_3d.png"))
    for titulo, archivo in (("CREAR", "menu_boceto_crear.png"), ("RESTRICCIONES", "menu_restricciones.png")):
        _capturar_menu(*_menu_del_grupo(v, v.cinta.pila.currentIndex(), titulo), destino / archivo)
    v.modo_boceto.terminar()
    QTest.qWait(200)

    v.visor.vista("iso")
    v.cambiar_vista("vistas_multiples", True)
    QTest.qWait(400)
    v.grab().save(str(destino / "vistas_multiples.png"))
    v.cambiar_vista("vistas_multiples", False)
    v.doc.modificado = False
    v.close()
    print("Capturas en", destino)


if __name__ == "__main__":
    main()
