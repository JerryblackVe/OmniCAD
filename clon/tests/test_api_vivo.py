# -*- coding: utf-8 -*-
"""Herramientas en vivo (B-80, MCP-46 y MCP-50): capture_viewport, get_selection y select_entities. La ventana real
se prueba en test_vivo_ventana.py; acá los hooks son funciones falsas, como en las pruebas de select_bodies."""
import pytest

from omnicad import api
from omnicad.api.registro import Imagen

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 8


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, esperado="INVALID_ARGUMENTS", **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == esperado, r
    return r


class Ventana:
    """Lo que la ventana les da a las herramientas: una selección y una captura."""

    def __init__(self):
        self.seleccion, self.pedidos, self.capturas = [], [], []

    def capturar(self, ancho, alto):
        self.capturas.append((ancho, alto))
        return PNG, ancho or 800, alto or 600

    def leer(self):
        return list(self.seleccion)

    def elegir(self, refs, modo):
        self.pedidos.append((refs, modo))
        if modo == "add":
            self.seleccion += [r for r in refs if r not in self.seleccion]
        elif modo == "remove":
            self.seleccion = [r for r in self.seleccion if r not in refs]
        else:
            self.seleccion = list(refs)


@pytest.fixture
def vivo():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, name="Caja")
    v = Ventana()
    s.capturar_visor, s.leer_seleccion, s.seleccionar_entidades = v.capturar, v.leer, v.elegir
    return s, v


def test_sin_ventana_las_tres_fallan_con_app_not_running():
    s = api.Sesion()
    ok(s, "create_box", length=5, width=5, height=5)
    falla(s, "capture_viewport", esperado="APP_NOT_RUNNING")
    falla(s, "get_selection", esperado="APP_NOT_RUNNING")
    falla(s, "select_entities", kind="body", selector="Cuerpo1", esperado="APP_NOT_RUNNING")


def test_capturar_la_vista_real_devuelve_la_imagen_de_la_ventana(vivo):
    s, v = vivo
    r = ok(s, "capture_viewport")
    assert isinstance(r["image"], Imagen) and r["image"].png == PNG and (r["width"], r["height"]) == (800, 600)
    r = ok(s, "capture_viewport", width=320, height=200)
    assert (r["width"], r["height"]) == (320, 200) and v.capturas == [(None, None), (320, 200)]
    falla(s, "capture_viewport", width=320)                                  # los dos juntos o ninguno
    falla(s, "capture_viewport", width=8, height=200)
    falla(s, "capture_viewport", width=320, height=99999)
    assert len(v.capturas) == 2                                              # lo inválido no llegó a la ventana


def test_get_selection_describe_cada_elemento_con_su_referencia(vivo):
    s, v = vivo
    assert ok(s, "get_selection") == {"selection": [], "count": 0}
    v.seleccion = [{"tipo": "cuerpo", "cuerpo": "op1.c1"}, {"tipo": "perfil", "boceto": "op3", "firma": [1, 2],
                                                           "centroide": [0.0, 0.0]}]
    r = ok(s, "get_selection")
    assert r["count"] == 2
    assert r["selection"][0] == {"type": "cuerpo", "body": "op1.c1", "sketch": None, "ref": v.seleccion[0]}
    assert r["selection"][1]["type"] == "perfil" and r["selection"][1]["sketch"] == "op3"


def test_elegir_cuerpos_caras_aristas_y_perfiles(vivo):
    s, v = vivo
    r = ok(s, "select_entities", kind="body", selector="Caja")
    assert r["count"] == 1 and r["selection"][0]["body"] == "op1.c1" and v.pedidos[-1][1] == "replace"
    r = ok(s, "select_entities", kind="face", selector=">Z", body="Caja")
    (ref,) = [x["ref"] for x in r["selection"]]
    assert ref["tipo"] == "cara" and ref["cuerpo"] == "op1.c1" and r["count"] == 1
    r = ok(s, "select_entities", kind="edge", selector="|Z", body="Caja", mode="add")
    assert r["count"] == 5 and {x["type"] for x in r["selection"]} == {"cara", "arista"}
    ok(s, "select_entities", kind="edge", selector="|Z", body="Caja", mode="remove")
    assert ok(s, "get_selection")["count"] == 1                              # queda la cara
    ok(s, "create_sketch", plane="XY", name="Boceto")
    ok(s, "draw_rectangle", x1=0, y1=0, x2=10, y2=10)
    ok(s, "draw_circle", radius=2, center_x=30, center_y=0)
    r = ok(s, "select_entities", kind="profile", sketch="Boceto", profile="all")
    assert r["count"] == 2 and all(x["type"] == "perfil" for x in r["selection"])
    r = ok(s, "select_entities", kind="profile", sketch="Boceto", profile=1)
    assert r["count"] == 1 and r["selection"][0]["ref"]["firma"]
    ok(s, "select_entities", kind="body", selector=["Caja"], mode="replace")


def test_elegir_rechaza_lo_mal_pedido(vivo):
    s, v = vivo
    falla(s, "select_entities", kind="face")                                 # sin selector
    falla(s, "select_entities", kind="profile")                              # sin boceto
    falla(s, "select_entities", kind="body", selector="no_hay", esperado="BODY_NOT_FOUND")
    falla(s, "select_entities", kind="face", selector=">Q", body="Caja", esperado="INVALID_SELECTOR")
    falla(s, "select_entities", kind="profile", sketch="no_hay", esperado="SKETCH_NOT_FOUND")
    assert v.pedidos == []                                                   # nada llegó a la ventana
