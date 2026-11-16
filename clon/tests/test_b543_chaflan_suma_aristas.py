"""B-543: en Chaflán, con la previa a la vista (que se come las aristas de la cadena tangente), un clic sobre otra arista
la suma: se elige sobre el cuerpo original, como Fusion con la previa a la vista."""
import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


@pytest.fixture
def chaflan(tmp_path):
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    cid = api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 20})["result"]["bodies_created"][0]["id"]
    assert api.llamar(s, "fillet", {"body": cid, "edges": "|Z", "radius": 3})["ok"]   # el borde de arriba: una cadena tangente
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        v.resize(1280, 800)
        v.show()
        v.visor.vista("iso")
        p = v.ejecutar_comando(CATALOGO["chaflan_3d"]())
        QTest.qWait(200)
        yield v.visor, p, geo.caja_envolvente(s.doc.estado_final.cuerpos[cid].forma)
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def _clic(visor, p, punto, demora=-1):
    q = visor.proyectar(punto)
    QTest.mouseClick(visor, Qt.LeftButton, Qt.NoModifier, QPoint(int(q.x()), int(q.y())), demora)
    for _ in range(80):                       # la previa puede ir a un proceso aparte
        QTest.qWait(50)
        if not p._t_previa.isActive() and not p.mensaje.text().startswith("Calculando"):
            break


def test_con_la_previa_a_la_vista_un_clic_suma_otra_arista(chaflan):
    visor, p, ((x0, y0, _z0), (x1, y1, z1)) = chaflan
    _clic(visor, p, ((x0 + x1) / 2, y0, z1))
    assert len(p.valores["aristas"]) == 1 and p._previa_ok
    _clic(visor, p, (x1, (y0 + y1) / 2, z1))  # la previa ya chaflanó esta arista (cadena tangente)
    assert len(p.valores["aristas"]) == 2
    # otro clic sobre la misma la quita, como Fusion: lejos del medio (ahí está el asa de la distancia) y con la demora
    # de una persona (si no, es un doble clic)
    _clic(visor, p, (x1, y0 + (y1 - y0) * 0.3, z1), QApplication.doubleClickInterval() + 50)
    assert len(p.valores["aristas"]) == 1
