"""B-444: Editar unión recuerda su presentación y las pestañas responden al primer clic."""
import pytest
from PySide6.QtCore import QElapsedTimer, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(tmp_path, app):
    sesion = api.Sesion()
    cuerpos = []
    for nombre, x in (("Base", 0), ("Pieza", 100)):
        r = api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 20, "x": x})
        assert r["ok"], r
        cuerpos.append(r["result"]["bodies_created"][0]["id"])
        r = api.llamar(sesion, "create_component", {"bodies": cuerpos[-1:], "name": nombre,
                                                    "grounded": nombre == "Base"})
        assert r["ok"], r
    v = VentanaPrincipal(sesion.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    app.processEvents()
    yield v, sesion, cuerpos
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _editar(ventana, conforme=False, movimiento="revolute"):
    v, sesion, (base, pieza) = ventana
    if conforme:
        nombre, args = "create_as_built_joint", {"origin": ">Z", "body": pieza, "component2": "Base"}
    else:
        nombre, args = "create_joint", {"origin1": "<Z", "body1": pieza, "origin2": ">Z", "body2": base,
                                        "joint_type": "revolute"}
    r = api.llamar(sesion, nombre, dict(args, joint_type=movimiento))
    assert r["ok"], r
    union = r["result"]["joint"]["id"]
    v.editar_operacion(union)
    QTest.qWait(30)
    assert v.panel is not None
    return union, v.panel


def _esperar(condicion, tope_ms=10000):
    """Espera a que `condicion()` sea cierta (no un tiempo fijo): con la VPS cargada el cierre tarda más de 30 ms."""
    reloj = QElapsedTimer()
    reloj.start()
    while not condicion() and reloj.elapsed() < tope_ms:
        QTest.qWait(10)


def _esperar_pie_asentado(panel, tope_ms=5000):
    """B-444: la barra se compara cuando el panel ya asentó su pie (ni el temporizador del pie ni la reubicación
    pendientes y sin altura fija), no tras un tiempo fijo: con la VPS cargada el asentado tarda más de 250 ms."""
    reloj = QElapsedTimer()
    reloj.start()
    while (panel._t_pie.isActive() or panel._t_reubicar.isActive() or panel._t_previa.isActive()
           or panel._y_fijo is not None) and reloj.elapsed() < tope_ms:
        QTest.qWait(10)
    assert panel._y_fijo is None and not panel._t_pie.isActive(), "el pie del panel no se asentó"


def _clic_pestana(panel, indice):
    barra = panel.barra_pestanas
    posicion = barra.mapToGlobal(barra.tabRect(indice).center())
    ventana = panel.window()
    QTest.mousePress(ventana.windowHandle(), Qt.LeftButton, pos=ventana.mapFromGlobal(posicion))
    QTest.qWait(40)
    QTest.mouseRelease(ventana.windowHandle(), Qt.LeftButton, pos=ventana.mapFromGlobal(posicion))
    QTest.qWait(30)


@pytest.mark.parametrize("conforme", [False, True])
@pytest.mark.parametrize("aceptar", [False, True])
def test_reabrir_recuerda_la_pestana_al_aceptar_o_cancelar(ventana, conforme, aceptar):
    v, sesion, _ = ventana
    union, panel = _editar(ventana, conforme)
    receta = sesion.doc.a_dict()
    _clic_pestana(panel, 1)
    assert panel.widgets["tipo"].isVisible()
    if aceptar:
        _esperar(panel.boton_ok.isEnabled)     # Aceptar queda gris mientras se calcula la previa: se espera a que se habilite
        assert panel.boton_ok.isEnabled()
    QTest.mouseClick(panel.boton_ok if aceptar else panel.boton_cancelar, Qt.LeftButton)
    _esperar(lambda: v.panel is None)      # el cierre puede tardar con la VPS cargada: se espera el cierre real
    assert v.panel is None
    v.editar_operacion(union)
    QTest.qWait(30)
    assert v.panel.barra_pestanas.currentIndex() == 1
    assert v.panel.widgets["tipo"].isVisible()
    assert sesion.doc.a_dict() == receta


@pytest.mark.parametrize("conforme", [False, True])
def test_editar_una_union_sin_tocar_nada_deja_aceptar_encendido(ventana, conforme):
    """B-444: los límites opcionales vacíos (Límite mínimo, máximo, reposo) no apagan Aceptar (B-468 lo apagaba)."""
    _, panel = _editar(ventana, conforme)
    assert not panel.invalidos - {"minimo", "maximo", "reposo_giro"}
    assert panel.boton_ok.isEnabled()


def test_reabrir_recuerda_cada_seccion_y_mas_opciones(ventana):
    v, _, _ = ventana
    union, panel = _editar(ventana)
    for titulo in ("Componente 1", "Alineación"):
        QTest.mouseClick(panel.plegables[titulo].boton, Qt.LeftButton)
        QTest.qWait(10)
    if not panel.seccion.abierta:
        QTest.mouseClick(panel.seccion.boton, Qt.LeftButton)
        QTest.qWait(10)
    esperado = {titulo: s.abierta for titulo, s in panel.plegables.items()}
    assert esperado == {"Componente 1": False, "Componente 2": True, "Alineación": False}
    assert panel.seccion.abierta
    QTest.mouseClick(panel.boton_cancelar, Qt.LeftButton)
    QTest.qWait(10)
    v.editar_operacion(union)
    QTest.qWait(30)
    assert {titulo: s.abierta for titulo, s in v.panel.plegables.items()} == esperado
    assert v.panel.seccion.abierta
    for seccion in v.panel.plegables.values():
        if not seccion.abierta:
            QTest.mouseClick(seccion.boton, Qt.LeftButton)
            QTest.qWait(10)
    QTest.mouseClick(v.panel.boton_cancelar, Qt.LeftButton)
    QTest.qWait(10)
    v.editar_operacion(union)
    QTest.qWait(30)
    assert all(s.abierta for s in v.panel.plegables.values())
    assert v.panel.widgets["origen1"].isVisible() and v.panel.widgets["angulo"].isVisible()


@pytest.mark.parametrize("conforme", [False, True])
def test_una_union_nueva_empieza_por_los_origenes(ventana, conforme):
    v, _, _ = ventana
    _, panel = _editar(ventana, conforme)
    clase = type(panel.comando)
    _clic_pestana(panel, 1)
    QTest.mouseClick(panel.boton_cancelar, Qt.LeftButton)
    QTest.qWait(10)
    nuevo = v.ejecutar_comando(clase())
    QTest.qWait(30)
    assert nuevo.barra_pestanas.currentIndex() == 0
    assert nuevo.widgets["origen1"].isVisible()


@pytest.mark.parametrize("conforme", [False, True])
@pytest.mark.parametrize("tamano", [(1280, 800), (900, 700), (800, 520)])
@pytest.mark.parametrize("movimiento", ["revolute", "ball"])
def test_un_clic_cambia_la_pestana_sin_mover_la_barra(ventana, conforme, tamano, movimiento):
    v, _, _ = ventana
    v.resize(*tamano)
    _, panel = _editar(ventana, conforme, movimiento)
    for seccion in panel.plegables.values():
        QTest.mouseClick(seccion.boton, Qt.LeftButton)
        QTest.qWait(10)
    for indice in (1, 0, 1):
        barra = panel.barra_pestanas
        _esperar_pie_asentado(panel)
        posicion = barra.mapToGlobal(barra.rect().topLeft())
        _clic_pestana(panel, indice)
        _esperar_pie_asentado(panel)
        assert barra.currentIndex() == indice
        assert panel.widgets["tipo"].isVisible() == bool(indice)
        assert panel.pagina_principal.isVisible() != bool(indice)
        assert barra.mapToGlobal(barra.rect().topLeft()) == posicion, "La pestaña se mueve durante el clic"
