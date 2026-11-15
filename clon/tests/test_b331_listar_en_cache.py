# -*- coding: utf-8 -*-
"""B-331: `selectores.listar` mide las caras y aristas una vez por forma (antes, en cada find_faces y en cada id que se
resolvía, en el hilo de la ventana); un cuerpo cambiado, o movido en el lugar, se vuelve a medir."""
from OCP.gp import gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location

from omnicad import api
from omnicad.api import selectores as sl


def _llamar(s, nombre, **argumentos):
    r = api.llamar(s, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


def test_b331_listar_mide_una_vez_por_forma_y_vuelve_a_medir_si_cambia(monkeypatch):
    s = api.Sesion()
    _llamar(s, "create_box", length=40, width=30, height=20)
    _llamar(s, "fillet", edges="all", radius=1)                                   # el cuerpo ya modificado
    medidas, firma = [], sl.refs.firma_arista
    monkeypatch.setattr(sl.refs, "firma_arista", lambda e: medidas.append(1) or firma(e))
    ids = [e["id"] for e in _llamar(s, "find_edges")["edges"]]
    n = len(medidas)
    assert n == len(ids) > 12
    for i in ids[:10]:
        sl.resolver_id(s, i)
    _llamar(s, "find_edges")
    assert len(medidas) == n                                                       # sin volver a medir
    forma = s.cuerpo("Cuerpo1").forma
    largos = [e.firma["largo"] for e in sl.listar(forma, "arista")]
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(100, 0, 0))
    forma.Location(TopLoc_Location(t))                                            # movida en el lugar: mismo objeto
    movidas = sl.listar(forma, "arista")
    assert len(medidas) == 2 * n and [e.firma["largo"] for e in movidas] == largos
    _llamar(s, "create_box", length=5, width=5, height=5, x=-50)
    nuevo = sl.listar(s.cuerpo("Cuerpo2").forma, "arista")
    assert len(nuevo) == 12 and len(medidas) == 2 * n + 12                        # otra forma: se mide
