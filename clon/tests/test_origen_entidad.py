# -*- coding: utf-8 -*-
"""«De dónde viene esta cara»: `timeline.origen.origen_de` y la herramienta `get_entity_origin`, con volúmenes y áreas
conocidos (caja 40×30×20, agujero Ø8, empalme R2…)."""
import pytest

from omnicad import api
from omnicad.nucleo import referencias as refs
from omnicad.timeline.origen import origen_de
from omnicad.ui import temas


def llamar(s, herramienta, **a):
    r = api.llamar(s, herramienta, a)
    assert r["ok"], r
    return r["result"]


def origenes(s, tipo="cara", cuerpo=None):
    """{(geometría, medida redondeada): [(creó, [modificaron]), …]} de todas las caras o aristas de un cuerpo."""
    c = s.doc.estado_final.cuerpos[cuerpo or next(iter(s.doc.estado_final.cuerpos))]
    salida = {}
    for sub in refs.subformas(c.forma, tipo):
        ref = refs.referencia(c.id, sub, c.forma)
        o = origen_de(s.doc, ref)
        f = ref["firma"]
        clave = (f["geom"], round(f.get("area", f.get("largo", 0.0)), 1))
        salida.setdefault(clave, []).append((o["creo"], o["modificaron"]) if o else None)
    return salida


@pytest.fixture
def caja_agujero_empalme():
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=30, height=20)
    llamar(s, "create_hole", face=">Z", diameter=8, depth=10)
    llamar(s, "fillet", edges="|Z", radius=2)
    return s


def test_tapa_creada_por_la_caja_y_modificada_por_agujero_y_empalme(caja_agujero_empalme):
    o = origenes(caja_agujero_empalme)
    assert o[("plano", 1146.3)] == [("op1", ["op2", "op3"])]          # la tapa: 1200 − π·16 − 4 empalmes
    assert o[("plano", 1196.6)] == [("op1", ["op3"])]                  # la base: solo recortada por el empalme


def test_caras_del_agujero_y_del_empalme_son_de_su_paso(caja_agujero_empalme):
    o = origenes(caja_agujero_empalme)
    assert o[("cilindro", 251.3)] == [("op2", [])]                     # pared del agujero: 2π·4·10
    assert o[("plano", 50.3)] == [("op2", [])]                         # fondo del agujero: π·16
    assert o[("cilindro", 62.8)] == [("op3", [])] * 4                  # los cuatro empalmes: ¼·2π·2·20


def test_arista_tangente_del_empalme_la_creo_el_empalme(caja_agujero_empalme):
    r = llamar(caja_agujero_empalme, "get_entity_origin", entity="edges:nearest:[-18,-15,10]")
    assert r["type"] == "edge" and r["created_by"]["id"] == "op3" and r["modified_by"] == []


def test_suprimir_el_agujero_lo_saca_de_las_modificaciones(caja_agujero_empalme):
    s = caja_agujero_empalme
    s.doc.suprimir("op2", True)
    o = origenes(s)
    # el empalme depende de las aristas del agujero y falla (SC3): queda la caja sin tocar, sin cilindros ni modificaciones
    assert o == {("plano", 600.0): [("op1", [])] * 2, ("plano", 800.0): [("op1", [])] * 2, ("plano", 1200.0): [("op1", [])] * 2}


def test_extrusion_corte_y_union():
    s = api.Sesion()
    b = llamar(s, "create_sketch", plane="XY")["sketch"]["id"]
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=40, y2=20)
    llamar(s, "extrude", sketch=b, profile=0, distance=10)                        # op2: placa 40×20×10
    b = llamar(s, "create_sketch", plane=">Z")["sketch"]["id"]
    llamar(s, "draw_circle", center_x=20, center_y=10, radius=4)
    llamar(s, "extrude", sketch=b, profile=0, distance=5, operation="cut")        # op4: pocket Ø8
    b = llamar(s, "create_sketch", plane=">Z")["sketch"]["id"]
    llamar(s, "draw_rectangle", x1=2, y1=2, x2=8, y2=8)
    llamar(s, "extrude", sketch=b, profile=0, distance=6, operation="join")       # op6: tarugo 6×6×6
    o = origenes(s)
    assert o[("plano", 713.7)] == [("op2", ["op4", "op6"])]                        # la tapa: 800 − 50,3 − 36
    assert o[("cilindro", 125.7)] == [("op4", [])] and o[("plano", 50.3)] == [("op4", [])]
    assert o[("plano", 36.0)] == [("op6", [])] * 5                                 # el tarugo: 4 lados y su tapa
    assert o[("plano", 800.0)] == [("op2", [])]


def test_revolucion_chaflan_vaciado_y_mover_cara():
    s = api.Sesion()
    b = llamar(s, "create_sketch", plane="XZ")["sketch"]["id"]
    llamar(s, "draw_rectangle", x1=5, y1=0, x2=15, y2=20)
    llamar(s, "revolve", sketch=b, profile=0, axis="Z")
    assert all(v == ("op2", []) for lista in origenes(s).values() for v in lista)      # todo viene de la revolución

    s = api.Sesion()
    llamar(s, "create_box", length=40, width=30, height=20)
    llamar(s, "chamfer", edges=">Z and |X", distance=2)
    o = origenes(s)
    assert o[("plano", 113.1)] == [("op2", [])] * 2                                # los dos chaflanes: √8·20 + ...
    assert o[("plano", 1200.0)] == [("op1", [])]                                   # la base no se tocó

    s = api.Sesion()
    llamar(s, "create_box", length=40, width=30, height=20)
    llamar(s, "shell", body="op1.c1", faces=">Z", thickness=2)
    o = origenes(s)
    assert o[("plano", 936.0)] == [("op2", [])]                                    # el piso interior es del vaciado
    assert o[("plano", 1200.0)] == [("op1", [])] and o[("plano", 800.0)] == [("op1", [])] * 2

    s = api.Sesion()
    llamar(s, "create_box", length=40, width=30, height=20)
    llamar(s, "move_faces", faces=">Z", distance=5, direction="Z")
    o = origenes(s)
    assert sorted(o[("plano", 1200.0)]) == [("op1", []), ("op2", [])]              # la tapa movida nace en el paso Mover
    assert o[("plano", 1000.0)] == [("op1", ["op2"])] * 2                          # las laterales crecieron


def test_patron_de_agujeros_cada_copia_es_del_patron():
    s = api.Sesion()
    llamar(s, "create_box", length=60, width=30, height=10)
    llamar(s, "create_hole", face=">Z", diameter=4, depth=5, points=[[-20, 0]])
    llamar(s, "rectangular_pattern", features=["op2"], x_count=3, x_spacing=20)
    o = origenes(s)
    assert sorted(o[("cilindro", 62.8)]) == [("op2", []), ("op3", []), ("op3", [])]    # el original y dos copias
    assert o[("plano", 1762.3)] == [("op1", ["op2", "op3"])]


def test_combinar_corta_y_une_cuerpos():
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=30, height=20)
    llamar(s, "create_cylinder", height=40, radius=5, z=-10)
    llamar(s, "boolean_operation", target="op1.c1", tools=["op2.c1"], operation="cut")
    o = origenes(s)
    assert o[("cilindro", 628.3)] == [("op3", [])]                                 # la pared del corte entra con el paso Combinar
    assert o[("plano", 1121.5)] == [("op1", ["op3"])] * 2


def test_cuerpo_y_referencias_sin_origen():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10)
    assert origen_de(s.doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"}) == {"creo": "op1", "modificaron": [], "cuerpo": "op1.c1"}
    assert origen_de(s.doc, {"tipo": "cuerpo", "cuerpo": "nada"}) is None
    assert origen_de(s.doc, {"tipo": "plano", "id": "XY"}) is None
    assert origen_de(s.doc, {"tipo": "cara", "cuerpo": "op1.c1", "firma": {"geom": "plano"}}) is None   # firma incompleta: no explota


def test_herramienta_get_entity_origin(caja_agujero_empalme):
    s = caja_agujero_empalme
    r = llamar(s, "get_entity_origin", entity=">Z")
    assert r["known"] and r["type"] == "face" and r["body"]["id"] == "op1.c1"
    assert r["created_by"] == {"id": "op1", "name": "Caja1", "type": "primitiva"}
    assert [p["id"] for p in r["modified_by"]] == ["op2", "op3"]
    cil = llamar(s, "find_faces", selector="%CYLINDER and nearest:[0,0,15]")["faces"][0]["id"]      # pared del agujero
    assert llamar(s, "get_entity_origin", entity=cil)["created_by"]["id"] == "op2"
    malo = api.llamar(s, "get_entity_origin", {"entity": "%PLANE"})                  # varias caras: pide una sola
    assert not malo["ok"] and malo["error_kind"] == "AMBIGUOUS_REFERENCE"


@pytest.mark.parametrize("clave", list(temas.INCLUIDOS))
def test_amarillo_con_texto_legible_en_todos_los_temas(clave):
    """El texto oscuro sobre el amarillo se lee, y el amarillo (o su borde) se despega del fondo del tema."""
    colores = temas.INCLUIDOS[clave]["colores"]
    for marca in ("creo", "modifico"):
        assert temas.razon_contraste(temas.ORIGEN["texto"], temas.ORIGEN[marca]) >= temas.MIN_CONTRASTE
        # sobre un fondo claro el amarillo casi no se despega: lo marca el borde ámbar; sobre uno oscuro, el relleno
        visible = max(temas.razon_contraste(temas.ORIGEN[marca], colores["panel"]),
                      temas.razon_contraste(temas.ORIGEN["borde"], colores["panel"]))
        assert visible >= 3.0, (clave, marca)
