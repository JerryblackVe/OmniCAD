# -*- coding: utf-8 -*-
"""FL-16: la cadena tangente de muchas caras (las 164 paredes de «@tienda») o aristas hace un solo análisis del cuerpo
(antes uno por cara: 7 s) y da lo mismo que pedirla cara por cara."""
from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar as sm


def _cuerpo(*pasos):
    s = api.Sesion()
    for nombre, args in pasos:
        assert api.llamar(s, nombre, args)["ok"], nombre
    return next(iter(s.doc.estado_final.cuerpos.values())).forma


def _unicas(listas):
    salida = []
    for lista in listas:
        salida += [x for x in lista if not sm._contiene(salida, x)]
    return salida


def _contar(monkeypatch, nombre):
    llamadas, original = [], getattr(sm, nombre)
    monkeypatch.setattr(sm, nombre, lambda *a, **k: llamadas.append(1) or original(*a, **k))
    return llamadas


def test_texto_un_solo_analisis_y_la_misma_cadena(monkeypatch):
    forma = _cuerpo(("create_box", {"length": 100, "width": 100, "height": 3}),
                    ("create_sketch", {"plane": ">Z", "name": "T"}),
                    ("add_text", {"text": "@tienda", "x": -30, "y": -42, "height": 8}),
                    ("extrude", {"sketch": "T", "profile": "text", "distance": 3, "operation": "join"}))
    paredes = [c for c in geo.caras(forma) if 3.1 < geo.centro_masa(c, True)[2] < 5.9][::4]     # la referencia es lenta
    for coplanares in (True, False):
        esperado = _unicas(sm.caras_tangentes(forma, c, coplanares=coplanares) for c in paredes)
        llamadas = _contar(monkeypatch, "_analisis")
        cadena = sm.caras_en_cadena(forma, paredes, coplanares=coplanares)
        monkeypatch.undo()
        assert len(llamadas) == 1
        assert len(cadena) == len(esperado) and all(sm._contiene(cadena, c) for c in esperado)


def test_empalme_no_repite_la_cadena_de_una_arista_que_ya_entro(monkeypatch):
    forma = _cuerpo(("create_box", {"length": 30, "width": 20, "height": 10}),
                    ("fillet", {"body": "Cuerpo1", "edges": "|Z", "radius": 3}))
    aristas = sm._aristas(forma)
    esperado = _unicas(sm.aristas_cadena_tangente(forma, a) for a in aristas)
    llamadas = _contar(monkeypatch, "aristas_cadena_tangente")
    salida = sm._ampliar_tangentes(forma, aristas, True)
    assert len(salida) == len(esperado) and all(sm._contiene(salida, e) for e in esperado)
    assert len(llamadas) < len(aristas)
