"""B-502: la barra «Posición» no se pisa con el ViewCube ni con el navegador a ningún tamaño de ventana."""
import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFrame

from omnicad.ui import superposiciones as sup
from omnicad.ui import visor3d as vis
from omnicad.ui.arrastre_componente import BarraPosicion


@pytest.mark.parametrize("ancho,alto", [(1024, 640), (800, 520), (700, 480), (520, 420)])
def test_barra_posicion_no_pisa(ancho, alto):
    app = QApplication.instance() or QApplication([])
    area = sup.AreaVisor(vis.Visor3D())
    nav = QFrame(area)
    nav.setFixedSize(300, 186)
    area.anclar_arriba_izq(nav)
    area.barra_posicion = barra = BarraPosicion(None, area)
    area.resize(ancho, alto)
    area.show()
    nav.show()
    barra.show()
    area.reubicar()
    app.processEvents()
    assert area.rect().contains(barra.geometry())
    assert not barra.geometry().intersects(area.viewcube.geometry())
    assert not barra.geometry().intersects(nav.geometry())
    area.close()


def test_barra_posicion_sigue_al_navegador_si_cambia_de_alto():
    QApplication.instance() or QApplication([])
    area = sup.AreaVisor(vis.Visor3D())
    nav = QFrame(area)
    nav.setFixedSize(300, 186)
    area.anclar_arriba_izq(nav)
    area.barra_posicion = barra = BarraPosicion(None, area)
    area.resize(800, 520)
    area.show()
    nav.show()
    barra.show()
    area.reubicar()
    nav.setFixedHeight(300)                  # el árbol del navegador se expande
    QTest.qWait(50)
    assert not barra.geometry().intersects(nav.geometry())
    area.close()
