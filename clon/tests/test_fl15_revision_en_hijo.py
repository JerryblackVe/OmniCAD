# -*- coding: utf-8 -*-
"""FL-15: ya en el proceso aparte, un barrido vaciado (caras B-spline y su desfase, ~600 polos) se revisa ahí mismo
en vez de abrir otro proceso por paso (editar su perfil tardaba 11-25 s); una rosca modelada sigue aislada, y si el
análisis falla ahí, va al proceso aparte como siempre."""
from omnicad import api
from omnicad.nucleo import aislado
from omnicad.nucleo import revision as rev


def _llamar(s, nombre, **argumentos):
    r = api.llamar(s, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


def _forma(s):
    return next(iter(s.doc.estado_final.cuerpos.values())).forma


def test_fl15_barrido_vaciado_se_revisa_en_el_hijo_y_la_rosca_no(monkeypatch):
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XY", name="perfil")
    _llamar(s, "draw_circle", radius=5)
    _llamar(s, "create_sketch", plane="XZ", name="ruta")
    _llamar(s, "draw_spline", points=[[0, 0], [30, 10], [60, 0], [90, 10]])
    _llamar(s, "sweep", sketch="perfil", path_sketch="ruta")
    tapa = [f["id"] for f in _llamar(s, "find_faces")["faces"] if f["type"] == "plane"][0]
    _llamar(s, "shell", body="Cuerpo1", faces=[tapa], thickness=1)                   # el cuerpo ya modificado
    vaciado = _forma(s)
    r = api.Sesion()
    _llamar(r, "create_cylinder", radius=3, height=8)
    cara = [f["id"] for f in _llamar(r, "find_faces")["faces"] if f["type"] == "cylinder"][0]
    _llamar(r, "create_thread", faces=[cara], modeled=True)
    pedidos = []
    monkeypatch.setattr(aislado, "EN_HIJO", True)
    monkeypatch.setattr(aislado, "correr", lambda tarea, forma, *a, **k: pedidos.append(forma) or (0, [], True))
    assert rev._autointersecciones_seguras(vaciado, 1, 5.0)[0] == 0 and pedidos == []     # sin otro proceso
    assert rev._autointersecciones_seguras(_forma(r), 1, 5.0)[0] == 0 and len(pedidos) == 1   # la rosca, aislada

    def falla(*a):
        raise RuntimeError("caída simulada")
    monkeypatch.setattr(rev, "_autointersecciones", falla)
    assert rev._autointersecciones_seguras(vaciado, 1, 5.0)[0] == 0 and pedidos[-1] is vaciado   # cae al aparte
