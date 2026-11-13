"""RS-X3: las curvas y los puntos del boceto se pegan desde una imagen guardada. Cada cambio que altera lo que se ve tiene
que rearmarla: después de cada uno, lo pintado con la imagen guardada es idéntico a lo pintado desde cero."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui.editor_boceto import Lienzo  # noqa: E402


def _lienzo():
    QApplication.instance() or QApplication([])
    b = Boceto()
    a, c = b.agregar_punto(0, 0), b.agregar_punto(30, 10)
    linea = b.agregar_linea(a, c)
    circulo = b.agregar_circulo(b.agregar_punto(-20, 5), 8)
    constr = b.agregar_linea(b.agregar_punto(-30, -20), b.agregar_punto(30, -20), construccion=True)
    lz = Lienzo(b, TablaParametros().evaluar, plano=g.Plano("XY"))
    lz.resize(600, 400)
    lz.encuadrar()
    lz.set_herramienta("seleccionar")
    return lz, {"linea": linea, "circulo": circulo, "constr": constr, "punto": c, "inicio": a}


def _de_cero(lz):
    lz._capa_clave = None
    return lz.grab().toImage()


def _cambios(lz, ids):
    def mover():
        lz.b.puntos[ids["punto"]].x += 7                 # sin resolver: la geometría cambia igual
    def fijo():
        lz.b.agregar_restriccion("fijo", [ids["inicio"]])
        lz.resolver()
    def tema():
        lz._oscuro = lambda: True
    return {
        "geometría": mover,
        "selección": lambda: lz.seleccion.append(ids["linea"]),
        "hover": lambda: setattr(lz, "_sobre", ids["circulo"]),
        "determinadas y fijos": fijo,
        "tema": tema,
        "capas: construcción": lambda: lz.mostrar.__setitem__("construccion", False),
        "capas: puntos": lambda: lz.mostrar.__setitem__("puntos", False),
        "cámara (zoom)": lambda: setattr(lz, "escala", lz.escala * 1.5),
        "cámara (desplazar)": lambda: lz.centro.__setitem__(0, lz.centro[0] + 10),
        "resaltado parcial": lambda: setattr(lz, "_brillantes", {ids["linea"]}),
    }


@pytest.mark.parametrize("cambio", list(_cambios(*_lienzo())))
def test_rsx3_cada_cambio_rearma_la_imagen_de_las_curvas(cambio):
    lz, ids = _lienzo()
    lz.resolver()
    antes = lz.grab().toImage()
    guardada = lz._capa_img
    assert lz.grab().toImage() == antes and lz._capa_img is guardada        # sin cambios se pega la misma imagen
    _cambios(lz, ids)[cambio]()
    con_cache = lz.grab().toImage()
    assert con_cache != antes, "el cambio no se ve: la prueba no prueba nada"
    assert con_cache == _de_cero(lz)
    lz.close()
