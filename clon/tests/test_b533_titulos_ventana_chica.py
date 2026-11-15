"""B-533: a 800×520 ningún nombre de grupo de la cinta queda partido al medio («INSP…AR»): o entero, o solo «▾» con el
nombre en el tooltip. Con la ventana grande no cambia nada (B-495)."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.ui.cinta import PESTANAS
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal

TODAS = [n for n, _ in PESTANAS] + ["BOCETO"]


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(crear_documento_ejemplo(), prefs=Preferencias(
        QSettings(str(tmp_path / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    QTest.qWaitForWindowExposed(v)
    app.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _titulos(v, pestana):
    if pestana == "BOCETO":
        v.cinta.mostrar_contextual("BOCETO")
    else:
        next(b for b in v.cinta.pestanas if b.toolTip() == pestana).click()
    QApplication.processEvents()
    QTest.qWait(30)
    pagina = v.cinta.pila.currentWidget()
    return [t for t in pagina.findChildren(QToolButton, "titulo_grupo") if t.isVisible() and t.property("titulo_completo")]


@pytest.mark.parametrize("ancho, alto", [(800, 520), (1100, 700), (1400, 800), (1783, 900), (1920, 900)])
@pytest.mark.parametrize("pestana", TODAS)
def test_ningun_titulo_de_grupo_queda_partido(ventana, pestana, ancho, alto):
    ventana.resize(ancho, alto)
    QTest.qWait(30)
    titulos = _titulos(ventana, pestana)
    assert titulos
    for t in titulos:
        completo = t.property("titulo_completo")
        assert t.text() in (completo, "▾") and "…" not in t.text(), (pestana, ancho, t.text(), completo)
        assert t.toolTip() == completo.replace(" ▾", "")                    # el nombre entero, al pasar el ratón
        if t.text() == completo:                                            # entero: entra en su botón
            assert t.width() >= t.fontMetrics().horizontalAdvance(completo), (pestana, ancho, completo)


@pytest.mark.parametrize("pestana", ["SÓLIDO", "BOCETO"])
def test_a_1920_todos_los_titulos_van_enteros(ventana, pestana):
    ventana.resize(1920, 900)
    QTest.qWait(30)
    assert all(t.text() == t.property("titulo_completo") for t in _titulos(ventana, pestana))


@pytest.mark.parametrize("ancho, alto", [(800, 520), (1100, 700), (1280, 800), (1920, 900)])
@pytest.mark.parametrize("con_boceto", [False, True])
def test_b535_ninguna_pestana_queda_cortada(ventana, ancho, alto, con_boceto):
    """B-535: con 800 px entran enteros los siete nombres (y BOCETO): se achica el relleno, no el nombre."""
    ventana.resize(ancho, alto)
    if con_boceto:
        ventana.cinta.mostrar_contextual("BOCETO")
    QTest.qWait(50)
    visibles = [b for b in ventana.cinta.pestanas + list(ventana.cinta.contextuales.values()) if b.isVisible()]
    assert len(visibles) == (8 if con_boceto else 7)
    for b in visibles:
        assert b.text() == b.toolTip() and "…" not in b.text(), (ancho, b.text())
        assert b.width() >= b.fontMetrics().horizontalAdvance(b.text()), (ancho, b.text(), b.width())


def test_b535_si_ni_con_el_relleno_chico_entran_recorta_el_final_y_guarda_el_nombre_en_el_tooltip(ventana):
    ventana.resize(300, 520)                       # más angosto que cualquier mínimo: la ventana se queda en su mínimo
    QTest.qWait(50)
    cinta = ventana.cinta
    sobra = sum(b.ancho_entero() for b in cinta.pestanas) - (cinta.pila.width() - 6 * 6)
    for b in cinta.pestanas:
        assert b.text().startswith(b.toolTip()[:4]) and (b.text() == b.toolTip() or b.text().endswith("…")), b.text()
        assert (b.text() == b.toolTip()) == (sobra <= 0)
