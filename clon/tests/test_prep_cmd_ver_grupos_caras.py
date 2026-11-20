# -*- coding: utf-8 -*-
"""PREP: test del comando ver_grupos_caras - muestra grupos de caras de malla."""
from omnicad import api


def ok(r):
    assert r["ok"], r
    return r["result"]


def test_ver_grupos_caras_basic():
    """Caso normal: ver grupos de caras de una malla con groups generados."""
    s = api.Sesion()
    r = api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})
    assert r["ok"]
    b = r["result"]["bodies_created"][0]["id"]
    r = api.llamar(s, "tessellate", {"bodies": [b], "keep_original": False})
    assert r["ok"]
    m = r["result"]["bodies_created"][0]["id"]
    r = api.llamar(s, "generate_face_groups", {"bodies": [m], "angle": 30})
    assert r["ok"]
    r = ok(api.llamar(s, "get_viewport_image", {"bodies": [m], "mesh_face_groups": True}))
    assert "image" in r
    assert r["image"] is not None


def test_ver_grupos_caras_borde_sin_grupos_explicitos():
    """Borde: malla con un solo group (sin generate_face_groups explícito)."""
    s = api.Sesion()
    r = api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})
    assert r["ok"]
    b = r["result"]["bodies_created"][0]["id"]
    r = api.llamar(s, "tessellate", {"bodies": [b], "keep_original": False})
    assert r["ok"]
    m = r["result"]["bodies_created"][0]["id"]
    r = ok(api.llamar(s, "get_viewport_image", {"bodies": [m], "mesh_face_groups": True}))
    assert "image" in r
    assert r["image"] is not None