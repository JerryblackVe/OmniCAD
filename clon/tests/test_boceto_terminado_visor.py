# -*- coding: utf-8 -*-
"""P-38 y B-109: lo que el visor dibuja de un boceto terminado (perfil celeste, construcción punteada) y la
proyección automática de una cara, que no se dibuja."""
from omnicad import api
from omnicad.restricciones.boceto import Boceto
from omnicad.ui.visor3d import polilineas_construccion, tris_perfil_terminado


def test_boceto_terminado_da_relleno_del_perfil_y_su_construccion():
    s = api.Sesion()
    for herramienta, args in (
            ("create_sketch", {"plane": "XY"}),
            ("draw_rectangle", {"x1": 0, "y1": 0, "x2": 20, "y2": 10}),
            ("draw_line", {"start_x": 0, "start_y": 0, "end_x": 20, "end_y": 10, "construction": True})):
        assert api.llamar(s, herramienta, args)["ok"]
    br = s.doc.estado_final.bocetos["op1"]
    assert len(tris_perfil_terminado(br)) == 1          # el rectángulo cerrado
    assert len(polilineas_construccion(br)) == 1        # la diagonal punteada
    assert len(tris_perfil_terminado(br, tope=0)) == 0  # sobre el tope no se rellena


def test_la_proyeccion_automatica_de_una_cara_no_se_dibuja_pero_la_propia_si():
    b = Boceto()
    caja = [("linea", None, (0, 0), (10, 0)), ("linea", None, (10, 0), (10, 5)),
            ("linea", None, (10, 5), (0, 5)), ("linea", None, (0, 5), (0, 0))]
    ids = b.agregar_proyeccion(caja, origen={"modo": "project", "refs": [], "auto": True})
    curvas, puntos = b.ocultos_por_proyeccion_auto()
    assert set(ids) <= curvas and puntos            # nada de la cara se dibuja
    propia = b.agregar_linea(b.agregar_punto(1, 1), b.agregar_punto(4, 4))
    assert propia not in b.ocultos_por_proyeccion_auto()[0]        # lo que dibuja la persona sí
    manual = Boceto()
    manual.agregar_proyeccion(caja, origen={"modo": "project", "refs": []})   # un Proyectar a mano
    assert manual.ocultos_por_proyeccion_auto() == (frozenset(), frozenset())
