# -*- coding: utf-8 -*-
"""Portón de AG-7 (docs/auditorias/porton_auditoria.md, punto 1): matriz de combinaciones de CONSTRUIR.

Cada plano, eje, punto y SCU se arma sobre una caja de alto paramétrico (también uno sobre el resultado de otro) y se
comprueba con números contra la geometría esperada en cada estado: recién creado, con la cota cambiada, deshacer,
rehacer y guardar y reabrir. Una referencia perdida no se reasigna callada (B-252): ese caso vive en
test_api_construccion.py."""
import numpy as np
import pytest

from omnicad import api

H0, H1 = 10.0, 25.0
R2 = 2 ** -0.5


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


# nombre → (herramienta, argumentos, qué es, esperado(h)): un plano es (punto suyo, normal); un eje, (punto, dirección)
CASOS = {
    "desfase": ("create_construction_plane", dict(plane=">Z", offset=5), "plano", lambda h: ((0, 0, h + 5), (0, 0, 1))),
    "angulo": ("create_construction_plane", dict(type="angle", references=["edges:>Z and >X"], angle=30), "plano",
               lambda h: ((20, 0, h), (0.5, 0, 3 ** 0.5 / 2))),
    "medio": ("create_construction_plane", dict(type="middle", references=[">Z", "<Z"]), "plano",
              lambda h: ((0, 0, h / 2), (0, 0, 1))),
    "dos_aristas": ("create_construction_plane", dict(type="two_edges", references=["edges:>Z and >X", "edges:<Z and <X"]),
                    "plano", lambda h: ((20, 0, h), (-h, 0, 20))),
    "tres_puntos": ("create_construction_plane", dict(type="three_points", references=[[20, 0, H0], [20, 20, H0], [0, 0, 0]]),
                    "plano", lambda h: ((20, 0, h), (-h, 0, 20))),
    "perpendicular": ("create_construction_plane", dict(type="perpendicular", references=[">X", [20, 20, H0]]), "plano",
                      lambda h: ((20, 20, h), (0, 1, 0))),
    "ruta": ("create_construction_plane", dict(type="path", references=["edges:>X and >Y"], position=0.5), "plano",
             lambda h: ((20, 20, h / 2), (0, 0, 1))),
    "tangente": ("create_construction_plane", dict(type="tangent", references=["faces:%CYLINDER"], body="Cuerpo2"), "plano",
                 lambda h: ((50, 0, 0), (1, 0, 0))),
    "eje_dos_planos": ("create_construction_axis", dict(type="dos_planos", references=[">Z", ">X"]), "eje",
                       lambda h: ((20, 0, h), (0, 1, 0))),
    "eje_dos_puntos": ("create_construction_axis", dict(type="dos_puntos", references=[[20, 0, H0], [0, 20, H0]]), "eje",
                       lambda h: ((20, 0, h), (-R2, R2, 0))),
    "eje_arista": ("create_construction_axis", dict(type="arista", references=["edges:>X and >Y"]), "eje",
                   lambda h: ((20, 20, 0), (0, 0, 1))),
    "eje_perpendicular": ("create_construction_axis", dict(type="perpendicular_cara", references=[">Z"], location=[5, 5, H0]),
                          "eje", lambda h: ((5, 5, h), (0, 0, 1))),
    "eje_cilindro": ("create_construction_axis", dict(type="cilindro", references=["faces:%CYLINDER"], body="Cuerpo2"), "eje",
                     lambda h: ((40, 0, 0), (0, 0, 1))),
    "punto_vertice": ("create_construction_point", dict(type="vertice", references=[[20, 20, H0]]), "punto",
                      lambda h: (20, 20, h)),
    "punto_tres_planos": ("create_construction_point", dict(type="tres_planos", references=[">Z", ">X", ">Y"]), "punto",
                          lambda h: (20, 20, h)),
    "punto_dos_aristas": ("create_construction_point", dict(type="dos_aristas", references=["edges:>Z and >X", "edges:>X and >Y"]),
                          "punto", lambda h: (20, 20, h)),
    "punto_ruta": ("create_construction_point", dict(type="ruta", references=["edges:>X and >Y"], position=0.25), "punto",
                   lambda h: (20, 20, h / 4)),
    "punto_centro": ("create_construction_point", dict(type="centro", references=["edges:%CIRCLE and >Z"], body="Cuerpo2"),
                     "punto", lambda h: (40, 0, 5)),
}


def _armar():
    s = api.Sesion()
    llamar(s, "create_parameter", name="alto", expression=f"{H0} mm")
    llamar(s, "create_box", length=20, width=20, height="alto", anchor="corner")
    llamar(s, "create_cylinder", radius=10, height=5, x=40, y=0)
    return s


def _mide(s, que, i):
    e = s.doc.estado_final
    if que == "plano":
        return e.planos[i].origen, e.planos[i].normal
    if que == "eje":
        return e.ejes[i][0], e.ejes[i][1]
    return e.puntos[i][0], None


def _comprobar(s, que, i, esperado, h):
    p, d = _mide(s, que, i)
    if que == "punto":
        assert np.allclose(p, esperado(h), atol=1e-6)
        return
    q, n = (np.asarray(v, float) for v in esperado(h))
    n /= np.linalg.norm(n)
    assert abs(abs(float(np.dot(d, n))) - 1) < 1e-6            # misma normal o dirección
    lejos = (q - p) @ n if que == "plano" else np.linalg.norm(np.cross(q - p, n))
    assert abs(lejos) < 1e-6                                   # el punto esperado está en el plano o el eje


@pytest.mark.parametrize("caso", CASOS)
def test_construir_sigue_a_la_cota_deshacer_y_reabrir(caso, tmp_path):
    herramienta, args, que, esperado = CASOS[caso]
    s = _armar()
    r = llamar(s, herramienta, **{"body": "Cuerpo1", **args})
    i = next(v["id"] for v in r.values() if isinstance(v, dict) and "id" in v)
    _comprobar(s, que, i, esperado, H0)
    llamar(s, "set_parameter", name="alto", expression=f"{H1} mm")
    _comprobar(s, que, i, esperado, H1)
    llamar(s, "undo")
    _comprobar(s, que, i, esperado, H0)
    llamar(s, "redo")
    _comprobar(s, que, i, esperado, H1)
    ruta = tmp_path / "m.omnicad"
    llamar(s, "save_document", path=str(ruta))
    otra = api.Sesion()
    llamar(otra, "open_document", path=str(ruta))
    _comprobar(otra, que, i, esperado, H1)


def test_construir_encadenada_y_scu_siguen_a_la_cota():
    """El resultado de una herramienta de CONSTRUIR alimenta a otra (plano → eje → punto) y la SCU se apoya en un vértice."""
    s = _armar()
    pid = llamar(s, "create_construction_plane", plane=">Z", offset=5, body="Cuerpo1")["plane"]["id"]
    eid = llamar(s, "create_construction_axis", type="dos_planos", references=[pid, "YZ"])["axis"]["id"]
    qid = llamar(s, "create_construction_point", type="arista_plano", references=[eid, "XZ"])["point"]["id"]
    u = llamar(s, "create_ucs", origin=[20, 20, H0], rz=90, body="Cuerpo1")
    for h in (H0, H1):
        llamar(s, "set_parameter", name="alto", expression=f"{h} mm")
        e = s.doc.estado_final
        assert np.allclose(e.puntos[qid][0], (0, 0, h + 5), atol=1e-6)
        assert np.allclose(e.puntos[f"{u['ucs']['id']}_o"][0], (20, 20, h), atol=1e-6)
        m = np.array([e.ejes[f"{u['ucs']['id']}_{k}"][1] for k in "xyz"])
        assert np.allclose(m @ m.T, np.eye(3), atol=1e-9) and np.linalg.det(m) == pytest.approx(1)
