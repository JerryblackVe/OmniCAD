"""H-82: «Al objeto» termina en la cara elegida y sus vecinas, como Extruir de Fusion."""
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _pieza(borde="chamfer", x2=9, arriba=False):
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=20, width=20, height=5, z=10, name="Tope")
    args = {"distance": 2} if borde == "chamfer" else {"radius": 2}
    _llamar(sesion, borde, edges="|Y and >X and " + (">Z" if arriba else "<Z"), **args)
    _llamar(sesion, "create_sketch", plane="XY", name="Perfil")
    _llamar(sesion, "draw_rectangle", x1=7, y1=-2, x2=x2, y2=2)
    return sesion


@pytest.mark.parametrize("borde,extra", [
    ("chamfer", 2),
    ("fillet", 4 * (2 - (math.sqrt(3) / 2 + math.pi / 3))),
])
@pytest.mark.parametrize("desfase", [0, 1])
def test_api_al_objeto_incluye_el_borde_adyacente(borde, extra, desfase):
    sesion = _pieza(borde)
    _llamar(sesion, "extrude", sketch="Perfil", extent="to_object", to="<Z", body="Tope",
            to_mode="adjacent", to_offset=desfase)
    forma = list(sesion.doc.estado_final.cuerpos.values())[-1].forma
    assert geo.es_valida(forma)
    assert geo.volumen_exacto(forma) == pytest.approx(80 + extra + 8 * desfase, abs=1e-5)
    assert np.allclose(geo.caja_envolvente(forma)[0], [7, -2, 0], atol=1e-6)
    altura = 11 if borde == "chamfer" else 12 - math.sqrt(3)
    assert np.allclose(geo.caja_envolvente(forma)[1], [9, 2, altura + desfase], atol=1e-6)
    assert sesion.doc.operaciones[-1].p["hasta_modo"] == "adyacentes"
    # El modo anterior sigue extendiendo el plano de la cara seleccionada.
    _llamar(sesion, "extrude", sketch="Perfil", extent="to_object", to="<Z", body="Tope")
    anterior = list(sesion.doc.estado_final.cuerpos.values())[-1].forma
    assert geo.es_valida(anterior)
    assert geo.volumen_exacto(anterior) == pytest.approx(80)


def test_adyacentes_no_usa_la_cara_opuesta_si_el_perfil_no_queda_cubierto():
    sesion = _pieza(x2=11)
    receta = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, "extrude", {"sketch": "Perfil", "extent": "to_object", "to": "<Z",
                                              "body": "Tope", "to_mode": "adjacent"})
    assert not respuesta["ok"]
    assert "adyacentes" in respuesta["mensaje"]
    assert sesion.doc.a_dict() == receta


@pytest.mark.parametrize("desfase", [0, 1])
@pytest.mark.parametrize("dos_lados", [False, True])
def test_adyacentes_hacia_abajo_y_en_el_lado_2(desfase, dos_lados):
    sesion = _pieza(arriba=True)
    args = ({"direction": "two_sides", "distance": 3, "side2_extent": "to_object", "side2_to": ">Z"}
            if dos_lados else {"extent": "to_object", "to": ">Z", "reverse": True})
    _llamar(sesion, "extrude", sketch="Perfil", start="offset", start_offset=20 if dos_lados else -20, body="Tope",
            to_mode="adjacent", to_offset=desfase, **args)
    forma = list(sesion.doc.estado_final.cuerpos.values())[-1].forma
    assert geo.es_valida(forma)
    assert geo.volumen_exacto(forma) == pytest.approx(42 + 8 * desfase + (24 if dos_lados else 0), abs=1e-5)
    assert np.allclose(geo.caja_envolvente(forma), [[7, -2, 14 - desfase], [9, 2, 23 if dos_lados else 20]], atol=1e-6)


@pytest.mark.parametrize("lado2", [False, True])
def test_panel_elige_adyacentes_y_recupera_la_opcion_al_editar(lado2):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos.solido import Extruir
    from omnicad.ui.visor3d import Visor3D

    app = QApplication.instance() or QApplication([])
    sesion = _pieza(arriba=lado2)
    args = ({"direction": "two_sides", "distance": 3, "side2_extent": "to_object", "side2_to": ">Z",
             "start": "offset", "start_offset": 20} if lado2 else {"extent": "to_object", "to": "<Z"})
    _llamar(sesion, "extrude", sketch="Perfil", body="Tope", **args)
    cmd, ctx, visor = Extruir(), ContextoComando(sesion.doc), Visor3D()
    panel = PanelComando(cmd, ctx, visor, cmd.desde_op(sesion.doc.operaciones[-1], ctx))
    try:
        panel.show()
        app.processEvents()
        combo = panel.widgets["hasta_modo"]
        assert combo.isVisible()
        assert combo.currentData() == "cara"
        assert combo.findData("adyacentes") >= 0
        combo.setFocus()
        QTest.keyClick(combo, Qt.Key_Down)
        assert panel.valores["hasta_modo"] == "adyacentes"
        op = cmd.construir(panel.valores, ctx)
        forma = op._forma(ctx.estado, ctx)
        assert geo.es_valida(forma)
        assert geo.volumen_exacto(forma) == pytest.approx(66 if lado2 else 82)
        assert cmd.desde_op(op, ctx)["hasta_modo"] == "adyacentes"
    finally:
        panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()
        app.processEvents()


def test_varios_perfiles_exigen_que_las_adyacentes_cubran_cada_uno():
    sesion = _pieza()
    _llamar(sesion, "draw_rectangle", x1=12, y1=-2, x2=13, y2=2)
    respuesta = api.llamar(sesion, "extrude", {"sketch": "Perfil", "profile": "all", "extent": "to_object",
                                              "to": "<Z", "body": "Tope", "to_mode": "adjacent"})
    assert not respuesta["ok"]
    assert "adyacentes" in respuesta["mensaje"]
