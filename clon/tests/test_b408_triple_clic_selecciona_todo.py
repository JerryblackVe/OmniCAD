"""B-408: triple clic y reemplazo del valor en los paneles reales, sin mover el cursor."""
import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import referencias as refs
from omnicad.nucleo.referencias import subformas
from omnicad.ui.campo_expresion import CampoExpresion
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture(params=[("chaflan_3d", "distancia", "1 mm", "4"),
                       ("extruir", "distancia", "0 mm", "10"),
                       ("empalme_3d", "radio", "18.34 mm", "4")])
def campo_panel(request, tmp_path):
    app = QApplication.instance() or QApplication([])
    sesion = api.Sesion()

    def llamar(nombre, **argumentos):
        salida = api.llamar(sesion, nombre, argumentos)
        assert salida["ok"], salida
        return salida["result"]

    llamar("create_box", length=100, width=60, height=40)
    comando, clave, texto, reemplazo = request.param
    if comando == "extruir":
        llamar("sketch_from_spec", entities=[{"type": "rectangle", "corner1": [120, 0], "corner2": [140, 20]}])
        boceto = sesion.doc.operaciones[-1].id
        perfil = sesion.doc.estado_final.bocetos[boceto].perfiles[0]
        from omnicad.timeline.operaciones import OpExtrusion
        ref = {"tipo": "perfil", "boceto": boceto, **OpExtrusion.referencia_perfil(perfil)}
    else:
        arista = llamar("find_edges", selector="|Z")["edges"][0]
        forma = sesion.cuerpo(arista["body"]).forma
        indice = int(arista["id"].rsplit("/E", 1)[1]) - 1
        ref = {"tipo": "arista", "cuerpo": arista["body"], "firma": refs.firma_arista(subformas(forma, "arista")[indice])}
    ventana = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    ventana.resize(1280, 900)
    ventana.show()
    panel = ventana.ejecutar_comando(CATALOGO[comando]())
    try:
        panel._elegida(hit_desde_ref(ref, panel.ctx.estado))
        panel.set_valor(clave, texto)
        app.processEvents()
        campo = panel.widgets[clave]
        assert isinstance(campo, CampoExpresion) and campo.isVisible()
        yield ventana, panel, campo, clave, texto, reemplazo
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        ventana.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()


def _punto(campo):
    # Sobre la unidad, no en el espacio vacío ni sobre el botón fx.
    return QPoint(5 + campo.fontMetrics().horizontalAdvance(campo.text()[:-1]), campo.height() // 2)


@pytest.mark.parametrize("ya_enfocado", [False, True], ids=["desde_visor", "enfocado"])
def test_triple_clic_selecciona_todo_y_teclear_reemplaza(campo_panel, ya_enfocado):
    con_doble = True      # un triple clic real es doble clic + un tercer clic: tres QTest.mouseClick sueltos no generan el doble clic
    ventana, panel, campo, clave, texto, reemplazo = campo_panel
    if ya_enfocado:
        QTest.keyClick(ventana.visor, Qt.Key_Tab)
        campo.setFocus(Qt.TabFocusReason)
    else:
        ventana.visor.setFocus()
    punto = _punto(campo)
    QTest.mouseClick(campo, Qt.LeftButton, pos=punto)
    if con_doble:
        QTest.mouseDClick(campo, Qt.LeftButton, pos=punto)
        QTest.mouseRelease(campo, Qt.LeftButton, pos=punto)
        assert campo.selectedText() == "mm"       # doble clic sigue seleccionando una palabra
    else:
        QTest.mouseClick(campo, Qt.LeftButton, pos=punto)
    QTest.mouseClick(campo, Qt.LeftButton, pos=punto)
    assert campo.selectedText() == texto
    QTest.keyClicks(campo, reemplazo)
    QTest.keyClick(campo, Qt.Key_Tab)
    QApplication.processEvents()
    assert campo.text() == reemplazo
    assert panel.valores[clave] == reemplazo and clave not in panel.invalidos


def test_triple_clic_con_pausas_de_100_ms_entre_los_eventos(campo_panel):
    """Un triple clic humano tiene pausas entre los clics (el temporizador de triple clic de Qt dura el intervalo de doble clic)."""
    ventana, panel, campo, clave, texto, reemplazo = campo_panel
    ventana.visor.setFocus()
    punto = _punto(campo)
    QTest.mouseClick(campo, Qt.LeftButton, pos=punto)
    QTest.qWait(100)
    QTest.mouseDClick(campo, Qt.LeftButton, pos=punto)
    QTest.qWait(100)
    QTest.mouseClick(campo, Qt.LeftButton, pos=punto)
    assert campo.selectedText() == texto
