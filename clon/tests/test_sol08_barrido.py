"""SOL-8: barrido con orientación alineada y superficie guía."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _anillo(**extra):
    """Un cilindro de radio 10 y un circulito de radio 1 barrido por su arista superior."""
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=10, name="Cil")
    llamar(s, "create_sketch", plane="XZ", name="Perfil")
    llamar(s, "draw_circle", radius=1, center_x=10, center_y=10, sketch="Perfil")
    r = api.llamar(s, "sweep", {"sketch": "Perfil", "path_edges": "%CIRCLE and >Z", "body": "Cil", "operation": "new_body",
                                **extra})
    return s, r


def test_alineada_con_el_eje_binormal_da_el_mismo_toro():
    s0, r0 = _anillo()
    assert r0["ok"], r0
    s1, r1 = _anillo(orientation="aligned", align_axis="Z")
    assert r1["ok"], r1
    v0 = geo.volumen(s0.doc.estado_final.cuerpos["op4.c1"].forma) if "op4.c1" in s0.doc.estado_final.cuerpos else None
    cuerpos0 = [c for c in s0.doc.estado_final.cuerpos.values() if c.nombre != "Cil"]
    cuerpos1 = [c for c in s1.doc.estado_final.cuerpos.values() if c.nombre != "Cil"]
    toro = 2 * math.pi * 10 * math.pi
    assert v0 is None or v0 > 0
    assert geo.volumen(cuerpos0[0].forma) == pytest.approx(toro, rel=1e-2)
    assert geo.volumen(cuerpos1[0].forma) == pytest.approx(toro, rel=1e-2)


def test_superficie_guia_en_una_ruta_apoyada_en_ella():
    s, r = _anillo(guide_surface="%CYLINDER")
    assert r["ok"], r
    nuevo = [c for c in s.doc.estado_final.cuerpos.values() if c.nombre != "Cil"]
    assert geo.volumen(nuevo[0].forma) == pytest.approx(2 * math.pi * 10 * math.pi, rel=1e-2)


def test_errores():
    s, _ = _anillo()
    for args in ({"orientation": "aligned"},                                       # sin eje
                 {"guide_surface": "%CYLINDER", "twist_angle": 10},                # con torsión
                 {"orientation": "aligned", "align_axis": "no existe"}):
        r = api.llamar(s, "sweep", {"sketch": "Perfil", "path_edges": "%CIRCLE and >Z", "body": "Cil", **args})
        assert not r["ok"], args


def _viga_y_ruta_recta(largo=40):
    """Una caja de 10 mm y una ruta recta en X de `largo` mm (boceto XY)."""
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Caja")
    llamar(s, "create_sketch", plane="XY", name="Ruta")
    llamar(s, "draw_line", start_x=0, start_y=0, end_x=largo, end_y=0, sketch="Ruta")
    return s


def test_barrido_de_un_cuerpo_por_una_ruta_recta_es_el_prisma_largo():
    s = _viga_y_ruta_recta()
    llamar(s, "sweep", sweep_bodies="Caja", path_sketch="Ruta", orientation="parallel", operation="new_body")
    nuevo = [c for c in s.doc.estado_final.cuerpos.values() if c.nombre != "Caja"][0]
    assert geo.es_valida(nuevo.forma)
    assert geo.volumen(nuevo.forma) == pytest.approx(10 * 10 * (10 + 40), rel=1e-3)
    assert geo.caja_envolvente(nuevo.forma)[1][0] == pytest.approx(5 + 40, abs=1e-3)
    assert geo.volumen(s.cuerpo("Caja").forma) == pytest.approx(1000)                  # el original no cambia


def test_barrido_de_un_cuerpo_perpendicular_en_un_arco_sigue_la_ruta():
    s = api.Sesion()
    llamar(s, "create_box", length=4, width=4, height=4, name="Taco")
    llamar(s, "create_sketch", plane="XY", name="Arco")
    llamar(s, "draw_arc", start_x=0, start_y=0, center_x=0, center_y=20, sweep_angle=90, sketch="Arco")
    r = api.llamar(s, "sweep", {"sweep_bodies": "Taco", "path_sketch": "Arco", "orientation": "perpendicular",
                                "operation": "new_body"})
    assert r["ok"], r
    nuevo = [c for c in s.doc.estado_final.cuerpos.values() if c.nombre != "Taco"][0]
    assert geo.es_valida(nuevo.forma)
    assert geo.volumen(nuevo.forma) == pytest.approx(4 * 4 * (4 + 10 * math.pi), rel=0.03)


def test_barrido_de_un_cuerpo_rechaza_perfil_y_torsion():
    s = _viga_y_ruta_recta()
    for extra in ({"sketch": "Ruta"}, {"twist_angle": 30}, {"taper_angle": 5}):
        r = api.llamar(s, "sweep", {"sweep_bodies": "Caja", "path_sketch": "Ruta", **extra})
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", extra


def test_ruta_encadenada_suma_las_aristas_tangentes():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY", name="Pista")
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=30, y2=10, sketch="Pista")
    llamar(s, "extrude", sketch="Pista", distance=5, operation="new_body")
    llamar(s, "fillet", edges="|Z", radius=3)                                     # esquinas redondeadas: borde tangente
    llamar(s, "create_sketch", plane="XZ", name="Perfil")
    llamar(s, "draw_circle", radius=0.5, center_x=15, center_y=5, sketch="Perfil")
    con = api.llamar(s, "sweep", {"sketch": "Perfil", "path_edges": "edges:%LINE and >Z and <Y", "operation": "new_body",
                                  "chain": True})
    assert con["ok"], con
    nuevo = list(s.doc.estado_final.cuerpos.values())[-1]
    perimetro = 2 * (24 + 4) + 2 * math.pi * 3                                    # la pista redondeada entera
    assert geo.volumen(nuevo.forma) == pytest.approx(perimetro * math.pi * 0.25, rel=0.02)


def test_cuerpo_chico_en_ruta_larga_falla_en_vez_de_dejar_cuentas_sueltas():
    s = api.Sesion()
    llamar(s, "create_box", length=2, width=2, height=2, name="Caja")
    llamar(s, "create_sketch", plane="XY", name="Ruta")
    llamar(s, "draw_line", start_x=0, start_y=0, end_x=1000, end_y=0, sketch="Ruta")
    r = api.llamar(s, "sweep", {"sweep_bodies": "Caja", "path_sketch": "Ruta", "orientation": "parallel",
                                "operation": "new_body"})
    assert not r["ok"] and "separadas" in r["mensaje"]


def test_cadena_con_curvas_de_boceto_avisa_que_no_las_encadena():
    s = _viga_y_ruta_recta()
    r = api.llamar(s, "sweep", {"sweep_bodies": "Caja", "path_sketch": "Ruta", "orientation": "parallel",
                                "operation": "new_body", "chain": True})
    assert r["ok"] and any("solo suma aristas de cuerpos" in a for a in r["avisos"]), r


def test_barrido_de_cuerpo_en_arco_se_acerca_al_volumen_exacto_y_la_via_por_caras_se_queda_corta():
    """Caja de 4 en un cuarto de arco de radio 20 (perpendicular): el volumen exacto es el sector (π/4·(22²−18²)·4 = 502,65)
    más las dos medias cajas de los extremos (2·32) = 566,65. Las copias unidas dan un 2 % de más (borde escalonado).
    La vía alternativa (MakePipe de cada cara + la caja inicial) da 535,6: `BRepOffsetAPI_MakePipe` devuelve un sólido
    nulo e inválido para las caras que contienen la tangente de la ruta, así que se pierde un tercio del barrido."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe
    from OCP.GC import GC_MakeArcOfCircle
    from OCP.gp import gp_Pnt

    from omnicad.nucleo import solidos_crear as sc
    caja = geo.caja(4, 4, 4, (-2, -2, -2))
    arco = GC_MakeArcOfCircle(gp_Pnt(0, 0, 0), gp_Pnt(20 * math.sin(math.pi / 4), 20 - 20 * math.cos(math.pi / 4), 0),
                              gp_Pnt(20, 20, 0)).Value()
    arista = BRepBuilderAPI_MakeEdge(arco).Edge()
    exacto = math.pi / 4 * (22 ** 2 - 18 ** 2) * 4 + 2 * 32
    copias = sc.barrer_cuerpo(caja, [arista], orientacion="perpendicular")
    assert geo.es_valida(copias) and geo.volumen(copias) == pytest.approx(exacto, rel=0.03)
    hilo = BRepBuilderAPI_MakeWire(arista).Wire()
    piezas = [caja]
    for cara in geo.caras(caja):
        pipe = BRepOffsetAPI_MakePipe(hilo, cara)
        pipe.Build()
        if geo.es_valida(pipe.Shape()) and geo.volumen(pipe.Shape()) > 1e-3:
            piezas.append(pipe.Shape())
    assert geo.volumen(geo.unir_todos(piezas)) < 0.96 * exacto               # la vía por caras no completa el barrido
