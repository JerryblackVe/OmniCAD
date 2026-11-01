"""BOC-53: «Cambiar por» (clic derecho en el símbolo y `replace_constraint`) rechaza la restricción nueva que no quita
ningún grado de libertad, igual que Agregar."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.restricciones.solver import restriccion_quita_grados  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402


def _tres_paralelas(b):
    ls = [b.agregar_linea((40, y), (70, y + 9)) for y in (30, 60, 90)]
    b.agregar_restriccion("paralela", [ls[0], ls[1]])
    b.agregar_restriccion("paralela", [ls[1], ls[2]])
    return ls


def test_quita_grados_dice_si_la_restriccion_baja_los_grados_de_libertad():
    b = Boceto()
    a, m, c = _tres_paralelas(b)
    igual = b.agregar_restriccion("igual", [a, c])
    sobra = b.agregar_restriccion("paralela", [a, c])               # la implican las otras dos
    assert restriccion_quita_grados(b, igual) and not restriccion_quita_grados(b, sobra)


@pytest.fixture
def lz():
    app = QApplication.instance() or QApplication([])
    lienzo = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar)
    lienzo.resize(800, 600)
    lienzo.show()
    lienzo.mensajes = []
    lienzo.mensaje.connect(lienzo.mensajes.append)
    yield lienzo
    lienzo.close()
    lienzo.deleteLater()
    app.processEvents()


def test_ventana_cambiar_por_algo_que_sobra_se_rechaza_con_su_mensaje_y_lo_util_pasa(lz):
    a, m, c = _tres_paralelas(lz.b)
    rid = lz.b.agregar_restriccion("igual", [a, c])
    lz.resolver()
    pasos = len(lz.historial)
    assert lz.reemplazar_restriccion(rid, "paralela") is False
    assert lz.b.restricciones[rid].tipo == "igual" and len(lz.historial) == pasos
    assert "no quita ningún grado de libertad" in lz.mensajes[-1] and "Paralela" in lz.mensajes[-1]
    assert lz.reemplazar_restriccion(rid, "colineal")                 # esa sí baja un grado más
    assert lz.b.restricciones[rid].tipo == "colineal" and lz.resultado.ok
    lz.deshacer()
    assert lz.b.restricciones[rid].tipo == "igual"


def _llamar(s, nombre, **a):
    return api.llamar(s, nombre, a)


def test_api_replace_constraint_rechaza_lo_que_sobra_y_deja_la_anterior():
    s = api.Sesion()
    assert _llamar(s, "create_sketch", name="S")["ok"]
    ids = [_llamar(s, "draw_line", sketch="S", start_x=40, start_y=y, end_x=70, end_y=y + 9)["result"]["entities"][0]["id"]
           for y in (30, 60, 90)]
    for par in ((0, 1), (1, 2)):
        assert _llamar(s, "add_constraint", sketch="S", type="parallel", entities=[ids[par[0]], ids[par[1]]])["ok"]
    rid = _llamar(s, "add_constraint", sketch="S", type="equal", entities=[ids[0], ids[2]])["result"]["constraint"]["id"]
    r = _llamar(s, "replace_constraint", sketch="S", constraint=rid, type="parallel")
    assert not r["ok"] and r["error_kind"] == "SKETCH_OVERCONSTRAINED" and "no quita ningún grado" in r["mensaje"]
    tipos = {x["id"]: x["type"] for x in _llamar(s, "get_sketch", sketch="S")["result"]["constraints"]}
    assert tipos[rid] == "equal"
    ok = _llamar(s, "replace_constraint", sketch="S", constraint=rid, type="collinear")
    assert ok["ok"] and ok["result"]["constraint"]["type"] == "collinear"
