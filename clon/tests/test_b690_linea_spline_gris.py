"""B-690: como Fusion, Perpendicular y Tangente entre una línea y una spline de ajuste sin punto en común están
apagadas (P-169): el boceto, la ventana, «Cambiar a» y la API las rechazan con «No disponible: …». Las ya guardadas
siguen y una línea encadenada a la spline puede ser tangente."""
import os

import pytest

from omnicad import api
from omnicad.restricciones import Boceto, ErrorBoceto

SPLINE = [(0, 0), (20, 10), (40, -5), (60, 5)]


def _escena():
    b = Boceto()
    return b, b.agregar_spline(SPLINE), b.agregar_linea((-30, 20), (-20, 40))


@pytest.mark.parametrize("tipo", ["perpendicular", "tangente"])
def test_sin_punto_en_comun_no_esta_disponible(tipo):
    b, s, l = _escena()
    with pytest.raises(ErrorBoceto, match=r"^No disponible: .*\(B-690\)"):
        b.exigir_disponible(tipo, [l, s])


def test_encadenada_a_la_spline_sigue_tangente():
    b = Boceto()
    s = b.agregar_spline(SPLINE)
    l = b.agregar_linea((60, 5), (80, 5))
    b.agregar_restriccion("coincidente", [b.curvas[l].puntos()[0], b.curvas[s].puntos()[-1]])
    b.exigir_disponible("tangente", [l, s])                 # no lanza


def test_la_guardada_sigue_se_copia_y_cambiar_a_no_la_ofrece():
    b, s, l = _escena()
    b2 = Boceto.desde_dict(b.a_dict())          # un proyecto viejo que ya la tenía
    from omnicad.restricciones.boceto_entidades import Restriccion
    b2.restricciones[99] = Restriccion(99, "tangente", [l, s])
    b3 = Boceto.desde_dict(b2.a_dict())
    assert [r.tipo for r in b3.restricciones.values()] == ["tangente"]
    assert "perpendicular" not in b3.tipos_compatibles(99)
    copia = Boceto()
    copia.pegar_de(b3, list(b3.curvas))                     # copiar y pegar repite la guardada sin rechazarla
    assert [r.tipo for r in copia.restricciones.values()] == ["tangente"]


def test_la_ventana_avisa_y_no_la_agrega():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui import editor_boceto
    b, s, l = _escena()
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    avisos = []
    lz.mensaje.connect(avisos.append)
    assert not lz.aplicar_restriccion("perpendicular", [l, s])
    assert not b.restricciones and any(a.startswith("No disponible:") for a in avisos)


def test_la_api_la_rechaza_con_el_motivo():
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"name": "B"})["ok"]
    sp = api.llamar(s, "draw_spline", {"points": [list(p) for p in SPLINE]})["result"]["entities"][0]["id"]
    ln = api.llamar(s, "draw_line", {"start_x": -30, "start_y": 20, "end_x": -20, "end_y": 40})["result"]["entities"][0]["id"]
    r = api.llamar(s, "add_constraint", {"sketch": "B", "type": "perpendicular", "entities": [ln, sp]})
    assert not r["ok"] and "No disponible:" in str(r) and "B-690" in str(r)
