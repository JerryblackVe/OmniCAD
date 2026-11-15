"""H-115: el Grosor de tangencia llega del panel y de la API al sólido paramétrico."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _caja():
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=20, width=20, height=20, name="Caja")
    return sesion


def _volumen(sesion):
    forma = sesion.cuerpo("Caja").forma
    assert geo.es_valida(forma)
    assert len(geo.solidos(forma)) == 1
    return geo.volumen(forma)


def test_peso_neutro_conserva_el_circulo_y_otro_peso_cambia_el_volumen():
    sesion = _caja()
    argumentos = dict(edges="nearest:[10,10,10]", radius=2, tangent_chain=False)
    _llamar(sesion, "fillet", **argumentos)
    circular = _volumen(sesion)
    assert circular == pytest.approx(8000 - (4 - math.pi) * 20, abs=1e-4)
    _llamar(sesion, "undo")
    _llamar(sesion, "fillet", **argumentos, tangency_weight=1)
    assert _volumen(sesion) == pytest.approx(circular, abs=1e-6)
    _llamar(sesion, "undo")
    _llamar(sesion, "fillet", **argumentos, tangency_weight=math.sqrt(2))
    # Peso central 1: Bézier cuadrática x=r(1-t)², y=rt²; área quitada = r²/6.
    assert _volumen(sesion) == pytest.approx(8000 - 4 * 20 / 6, abs=1e-3)
    assert abs(_volumen(sesion) - circular) > 1
    _llamar(sesion, "undo")
    _llamar(sesion, "fillet", **argumentos, tangency_weight=0.5)
    assert _volumen(sesion) < circular


def test_receta_sin_peso_conserva_el_empalme_anterior():
    sesion = _caja()
    _llamar(sesion, "fillet", edges="|Z", radius=2)
    anterior = _volumen(sesion)
    receta = _llamar(sesion, "get_recipe")["recipe"]
    receta["operaciones"][-1]["params"].pop("peso_tangencia", None)
    copia = api.Sesion()
    _llamar(copia, "apply_recipe", recipe=receta)
    assert _volumen(copia) == pytest.approx(anterior, abs=1e-6)


def test_peso_en_asimetrico_y_en_varios_conjuntos():
    sesion = _caja()
    _llamar(sesion, "fillet", edges="nearest:[10,10,10]", radius=2, radius2=4, radius_type="asymmetric",
            tangency_weight=math.sqrt(2), sets=[{"edges": "nearest:[-10,-10,10]", "radius": 3}])
    assert _volumen(sesion) == pytest.approx(8000 - (2 * 4 + 3 * 3) * 20 / 6, abs=1e-3)


@pytest.mark.parametrize("argumentos", [
    {"radius_type": "variable", "end_radius": 3},
    {"radius_type": "chord", "chord_length": 2},
    {"corner_type": "setback", "setback": 3},
    {"faces_a": ">Z", "edges": None},
    {"type": "full_round", "center_face": ">Z", "side_faces": ["<Y", ">Y"]},
])
def test_las_variantes_sin_soporte_no_ignoran_el_peso(argumentos):
    sesion = _caja()
    antes = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, "fillet", dict(edges="nearest:[10,10,10]", radius=2,
                                                tangency_weight=2) | argumentos)
    assert not respuesta["ok"], respuesta
    assert "tangencia" in respuesta["mensaje"].lower(), respuesta
    assert sesion.doc.a_dict() == antes


@pytest.mark.parametrize("peso", [0, -1, float("nan"), float("inf")])
def test_el_nucleo_rechaza_pesos_no_positivos_o_no_finitos(peso):
    from omnicad.nucleo import solidos_modificar as sm
    with pytest.raises(geo.ErrorGeometria, match="tangencia"):
        sm.empalme(geo.caja(20, 20, 20), [{"aristas": [], "radio": 2}], peso_tangencia=peso)


@pytest.mark.parametrize("continuidad", ["g1", "g2"])
def test_el_peso_parametrico_recalcula_y_se_conserva_en_la_receta(continuidad):
    sesion = _caja()
    _llamar(sesion, "create_parameter", name="peso", expression=1, kind="scalar")
    _llamar(sesion, "fillet", edges="nearest:[10,10,10]", radius=2, continuity=continuidad,
            tangent_chain=False, tangency_weight="peso")
    neutro = _volumen(sesion)
    _llamar(sesion, "set_parameter", name="peso", expression=2)
    pesado = _volumen(sesion)
    assert abs(pesado - neutro) > 1
    assert sesion.doc.operaciones[-1].p["peso_tangencia"] == "peso"
    receta = _llamar(sesion, "get_recipe")["recipe"]
    copia = api.Sesion()
    _llamar(copia, "apply_recipe", recipe=receta)
    assert _volumen(copia) == pytest.approx(pesado, abs=1e-4)
    _llamar(sesion, "set_parameter", name="peso", expression=1)
    assert _volumen(sesion) == pytest.approx(neutro, abs=1e-4)


@pytest.mark.parametrize("peso", [0, -1, "2 mm"])
def test_peso_invalido_no_modifica_el_documento(peso):
    sesion = _caja()
    antes = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, "fillet", dict(edges="nearest:[10,10,10]", radius=2, tangency_weight=peso))
    assert not respuesta["ok"], respuesta
    assert "tangencia" in respuesta["mensaje"].lower(), respuesta
    assert sesion.doc.a_dict() == antes
    assert _volumen(sesion) == pytest.approx(8000)


def test_teclear_peso_en_el_panel_aceptar_y_reabrir():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from omnicad.api import selectores
    from omnicad.ui.comando import ContextoComando, PanelComando, hit_desde_ref
    from omnicad.ui.comandos.modificar import Empalme
    from omnicad.ui.visor3d import Visor3D

    app = QApplication.instance() or QApplication([])
    sesion = _caja()
    cuerpo, arista = selectores.elegir_uno(sesion, "nearest:[10,10,10]", "arista")
    hit = hit_desde_ref(selectores.referencia(cuerpo, arista), sesion.doc.estado_final)
    visor = Visor3D()
    visor.set_modelo(sesion.doc.estado_final)
    panel = PanelComando(Empalme(), ContextoComando(sesion.doc), visor,
                         {"aristas": [hit], "radio": "2 mm", "cadena_tangente": False})
    panel.show()
    previas = []
    panel.previa.connect(previas.append)
    editor = None
    try:
        assert "peso_tangencia" in panel.widgets
        campo = panel.widgets["peso_tangencia"]
        assert campo.isVisible() and campo.text() == "1"
        panel._calcular_previa()
        neutro = geo.volumen(next(iter(previas[-1].cuerpos.values())).forma)
        for texto in ("0", "-1", "2 mm"):
            campo.setFocus()
            QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
            QTest.keyClicks(campo, texto)
            panel._calcular_previa()
            assert not panel._previa_ok
        QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClicks(campo, "2")
        panel._calcular_previa()
        assert panel._previa_ok, panel.mensaje.text()
        panel.confirmar = lambda op: sesion.doc.agregar(op).estado == "ok"
        panel.aceptar()
        assert len(sesion.doc.operaciones) == 2
        assert abs(_volumen(sesion) - neutro) > 1
        op = sesion.doc.operaciones[-1]
        editor = PanelComando(Empalme(), ContextoComando(sesion.doc, op=op), visor)
        assert editor.widgets["peso_tangencia"].text() == "2"
    finally:
        if editor is not None:
            editor.cancelar()
            editor.deleteLater()
        if not panel.cerrando:
            panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()
        app.processEvents()
