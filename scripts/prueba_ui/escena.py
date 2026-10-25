# -*- coding: utf-8 -*-
"""Escena de prueba para la ventana: bocetos separados en el espacio (para que el clic no se confunda) y cuerpos."""
from omnicad import api
from omnicad.nucleo import geometria as geo


def construir():
    s = api.Sesion()

    def L(nombre, **a):
        r = api.llamar(s, nombre, a)
        assert r["ok"], (nombre, a, r)
        return r["result"]

    L("create_sketch", name="Rect", plane="XY"); L("draw_rectangle", sketch="Rect", x1=0, y1=0, x2=20, y2=10)
    L("create_sketch", name="Lin", plane="XY"); L("draw_line", sketch="Lin", start_x=0, start_y=-30, end_x=20, end_y=-30)
    L("create_sketch", name="Circ", plane="XY"); L("draw_circle", sketch="Circ", center_x=60, center_y=0, radius=5)
    L("create_sketch", name="Perf", plane="XY"); L("draw_circle", sketch="Perf", center_x=0, center_y=60, radius=2)
    L("create_sketch", name="Ruta", plane="YZ"); L("draw_line", sketch="Ruta", start_x=60, start_y=0, end_x=60, end_y=30)
    L("create_sketch", name="RevL", plane="XZ"); L("draw_line", sketch="RevL", start_x=30, start_y=0, end_x=30, end_y=20)
    L("create_construction_plane", plane="XY", offset=20, name="PL")
    L("create_construction_plane", plane="XY", offset=10, name="PM")
    L("create_sketch", name="Circ2", plane="PL"); L("draw_circle", sketch="Circ2", center_x=60, center_y=0, radius=8)
    ids = {}
    ids["tubo"] = L("create_surface_extrude", profiles={"sketch": "Circ", "profile": 0}, distance=20)["bodies_created"][0]["id"]
    ids["caja"] = L("create_box", length=30, width=30, height=20, x=-100)["bodies_created"][0]["id"]
    ids["cil"] = L("create_cylinder", height=30, radius=10, x=-160)["bodies_created"][0]["id"]
    b = L("create_box", length=20, width=20, height=10, x=100)["bodies_created"][0]["id"]
    L("unstitch_surfaces", bodies=b)
    caras = [c.id for c in s.doc.estado_final.cuerpos.values() if c.id.startswith(b.split(".")[0]) or c.op_id == s.doc.operaciones[-1].id]
    L("stitch_surfaces", bodies=caras[:5])
    ids["quilt"], ids["tapa"] = caras[0], caras[5]
    # --- para Sólido: caja hueca con un boceto que la cruza (nervio / red), y un boceto de ruta en 3D
    L("create_sketch", name="NerL", plane="PM"); L("draw_line", sketch="NerL", start_x=181, start_y=0, end_x=219, end_y=0)
    hb = L("create_box", length=40, width=40, height=30, x=200)["bodies_created"][0]["id"]
    L("shell", body=hb, faces=">Z", thickness=2)
    ids["hueca"] = hb
    L("create_sketch", name="Rep", plane="PL"); L("draw_circle", sketch="Rep", center_x=-100, center_y=0, radius=4)
    # comprobaciones de la escena
    est = s.doc.estado_final
    assert est.cuerpos[ids["quilt"]].tipo == "superficie" and est.cuerpos[ids["tubo"]].tipo == "superficie"
    pts = geo.polilinea_arista(next(iter(est.bocetos[s.paso("Ruta").id].boceto.curvas.values())) if False else
                               __import__("omnicad.ui.comando", fromlist=["hit_desde_ref"]).hit_desde_ref(
                                   {"tipo": "curva_boceto", "boceto": s.paso("Ruta").id,
                                    "curva": next(iter(est.bocetos[s.paso("Ruta").id].boceto.curvas))}, est)["forma"])
    ids["ruta_extremos"] = [tuple(round(float(x), 2) for x in pts[0]), tuple(round(float(x), 2) for x in pts[-1])]
    return s, ids
