# -*- coding: utf-8 -*-
"""Objetos de diseño: exactitud, firmas, jerarquía, persistencia y transacciones CAD."""
import json
import math

import numpy as np
import pytest

from omnicad import api
from omnicad.io_archivos.boceto_archivos import boceto_desde_primitivas
from omnicad.io_archivos.svg import leer_svg
from omnicad.nucleo import geometria as geo
from omnicad.nucleo.perfiles import detectar_boceto, sin_huecos
from omnicad.restricciones import Boceto, ErrorBoceto, resolver
from omnicad.restricciones import objetos as ob


def svg(tmp_path, contenido):
    ruta = tmp_path / "logo.svg"
    ruta.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" '
                    'viewBox="0 0 100 100">' + contenido + '</svg>', encoding="utf-8")
    return ruta


def rectangulo(b, x=10, y=10, ancho=20, alto=10):
    return ob.crear(b, b.agregar_rectangulo((x, y), (x + ancho, y + alto)), "Rectángulo")


def test_svg_se_conserva_como_un_objeto_sin_incognitas_internas(tmp_path):
    ruta = svg(tmp_path, '<g id="marca"><rect x="10" y="20" width="20" height="10"/> '
                        '<g id="detalle"><circle cx="15" cy="25" r="2"/></g></g>')
    b = boceto_desde_primitivas(leer_svg(ruta))
    assert len(b.curvas) == 5 and len(ob.raices(b)) == 1
    assert {"logo", "marca", "detalle"} <= {o["nombre"] for o in b.objetos.values()}
    assert resolver(b).gdl == 0
    origen = json.dumps(b.a_dict()["puntos"], sort_keys=True)
    oid = ob.raices(b)[0]
    ob.transformar(b, [oid], ob.afin(35, -18, 27, 2, 0.7, (20, 75)))
    assert json.dumps(b.a_dict()["puntos"], sort_keys=True) == origen
    perfiles = detectar_boceto(b, geo.Plano("XY"))
    assert len(perfiles) == 2
    assert all(geo.es_valida(p.cara) for p in perfiles)
    assert sum(p.area for p in perfiles) == pytest.approx(200 * 1.4, rel=1e-8)


def test_circulo_deformado_es_conica_exacta_no_polilinea():
    b = Boceto()
    cid = b.agregar_circulo((0, 0), 5)
    oid = ob.crear(b, [cid])
    ob.transformar(b, [oid], ob.afin(10, 20, 31, 3, 0.5))
    p = b.primitivas(cid)[0]
    assert p[0] == "elipse" and sorted(p[3:5]) == [2.5, 15.0]
    perfiles = detectar_boceto(b, geo.Plano("XY"))
    assert perfiles[0].area == pytest.approx(math.pi * 25 * 1.5, rel=1e-10)
    assert geo.es_valida(perfiles[0].cara)
    # Extremos exactos de la elipse girada, no su polígono de control.
    a = math.radians(31)
    ex = math.hypot(15 * math.cos(a), 2.5 * math.sin(a))
    ey = math.hypot(15 * math.sin(a), 2.5 * math.cos(a))
    assert ob.caja(b, [oid]) == pytest.approx((10 - ex, 20 - ey, 10 + ex, 20 + ey), abs=1e-8)


def test_jerarquia_desagrupar_y_pivote_no_cambian_geometria():
    b = Boceto()
    a, c = rectangulo(b), rectangulo(b, 50)
    grupo = ob.crear(b, [a, c], "Marca")
    ob.transformar(b, [grupo], ob.afin(12, 7, 33, 2, 0.8))
    antes = b.geometria()
    ob.poner_pivote(b, grupo, (12, 17))
    assert ob.pivote(b, grupo) == pytest.approx((12, 17))
    assert b.geometria() == antes
    assert ob.desagrupar(b, grupo) == [a, c]
    for p, q in zip(antes, b.geometria(), strict=True):
        assert np.asarray(p[2:]) == pytest.approx(np.asarray(q[2:]))
    assert ob.raices(b) == [a, c]


def test_objetos_serializan_y_las_recetas_anteriores_no_cambian():
    b = Boceto()
    oid = rectangulo(b)
    ob.transformar(b, [oid], ob.afin(7, 4, 15, 2, 3))
    copia = Boceto.desde_dict(json.loads(json.dumps(b.a_dict())))
    assert copia.a_dict() == b.a_dict()
    assert ob.caja(copia, [oid]) == pytest.approx(ob.caja(b, [oid]))
    viejo = Boceto()
    viejo.agregar_circulo((3, 4), 7)
    d = viejo.a_dict()
    assert "objetos" not in d
    assert Boceto.desde_dict(d).a_dict() == d


def test_objeto_bloqueado_o_matriz_hostil_no_dejan_cambios():
    b = Boceto()
    oid = rectangulo(b)
    antes = b.a_dict()
    with pytest.raises(ErrorBoceto):
        ob.transformar(b, [oid], ob.afin(1e9, 0))
    assert b.a_dict() == antes
    b.objetos[oid]["bloqueado"] = True
    with pytest.raises(ErrorBoceto, match="bloqueado"):
        ob.transformar(b, [oid], ob.afin(10, 0))
    for mala in ([[1, 0, 0], [0, 0, 0], [0, 0, 1]], [[1, 0, 0], [0, 1, 0], [0, 1, 1]]):
        d = b.a_dict()
        d["objetos"][0]["matriz"] = mala
        with pytest.raises(ErrorBoceto):
            Boceto.desde_dict(d)


def ok(s, tool, **args):
    r = api.llamar(s, tool, args)
    assert r["ok"], r
    return r["result"]


def test_api_transformacion_parametrica_extruye_y_sobrevive_guardar_undo(tmp_path):
    s = api.Sesion()
    ruta = svg(tmp_path, '<path fill-rule="evenodd" d="M10 10H30V30H10Z M15 15H25V25H15Z"/>')
    r = ok(s, "insert_svg", path=str(ruta), plane="XY")
    oid = r["object_ids"][0]
    assert ok(s, "get_vector_objects")["roots"] == [oid]
    ok(s, "extrude", sketch=r["sketch"]["id"], profile=f"object:{oid}", distance=5)
    cuerpo = next(iter(s.doc.estado_final.cuerpos.values()))
    assert geo.volumen(cuerpo.forma) == pytest.approx(1500)
    assert geo.es_valida(cuerpo.forma)
    ok(s, "create_parameter", name="desplazar", expression="20 mm")
    ok(s, "transform_vector_objects", objects=[oid], dx="desplazar", angle=90, scale_x=2, pivot=[0, 0])
    original = s.doc.a_dict()
    formas = list(s.doc.estado_final.cuerpos.values())
    assert geo.volumen(formas[0].forma) == pytest.approx(6000)
    caja_antes = geo.caja_envolvente(formas[0].forma)
    ok(s, "set_parameter", name="desplazar", expression="45 mm")
    caja_despues = geo.caja_envolvente(next(iter(s.doc.estado_final.cuerpos.values())).forma)
    assert caja_despues[0][0] - caja_antes[0][0] == pytest.approx(25)
    ok(s, "undo")
    assert s.doc.a_dict() == original
    ok(s, "redo")
    archivo = tmp_path / "objetos.omnicad"
    ok(s, "save_document", path=str(archivo))
    t = api.Sesion()
    ok(t, "open_document", path=str(archivo))
    assert ok(t, "get_vector_objects")["roots"] == [oid]
    assert geo.volumen(next(iter(t.doc.estado_final.cuerpos.values())).forma) == pytest.approx(6000)


def test_api_agrupar_alinear_distribuir_duplicar_y_bloqueo():
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY")
    ids = []
    for x, y in ((10, 10), (50, 25), (100, 50)):
        r = ok(s, "draw_circle", center_x=x, center_y=y, radius=3)
        ids.append(ok(s, "create_vector_object", entities=[r["entities"][0]["id"]])["object_id"])
    ok(s, "align_vector_objects", objects=ids, mode="bottom")
    objs = ok(s, "get_vector_objects")["objects"]
    assert all(o["position"][1] == pytest.approx(7) for o in objs)
    ok(s, "align_vector_objects", objects=ids, mode="distribute_horizontal", gap=4)
    objs = sorted(ok(s, "get_vector_objects")["objects"], key=lambda o: o["position"][0])
    assert [o["position"][0] for o in objs] == pytest.approx([7, 17, 27])
    grupo = ok(s, "group_vector_objects", objects=ids)["object_id"]
    copia = ok(s, "duplicate_vector_objects", objects=[grupo], dx=100)["object_ids"][0]
    assert len(ok(s, "get_vector_objects")["roots"]) == 2
    ok(s, "set_vector_object", object=copia, locked=True)
    antes = s.doc.a_dict()
    fallo = api.llamar(s, "transform_vector_objects", {"objects": [copia], "dx": 12})
    assert not fallo["ok"] and "bloqueado" in fallo["mensaje"]
    assert s.doc.a_dict() == antes
    assert ok(s, "ungroup_vector_object", object=grupo)["object_ids"] == ids


@pytest.mark.parametrize("regla,interior,area", [("evenodd", "M15 15H25V25H15Z", 300),
                                                  ("nonzero", "M15 15H25V25H15Z", 400),
                                                  ("nonzero", "M15 15V25H25V15Z", 300)])
def test_reglas_de_relleno_svg_exactas_y_agujeros(tmp_path, regla, interior, area):
    s = api.Sesion()
    ruta = svg(tmp_path, f'<path fill-rule="{regla}" d="M10 10H30V30H10Z {interior}"/>')
    oid = ok(s, "insert_svg", path=str(ruta), plane="XZ")["object_ids"][0]
    utiles = ok(s, "get_vector_regions", objects=[oid])["profiles"]
    assert sum(p["area"] for p in utiles) == pytest.approx(area)
    ok(s, "extrude", sketch=ok(s, "get_vector_objects")["sketch"], profile=f"object:{oid}", distance=3)
    assert sum(geo.volumen(c.forma) for c in s.doc.estado_final.cuerpos.values()) == pytest.approx(area * 3)


def test_arcos_svg_son_exactos_y_conservan_agujeros_al_reflejar(tmp_path):
    s = api.Sesion()
    ruta = svg(tmp_path, '<path d="M30 50 A20 20 0 1 1 70 50 A20 20 0 1 1 30 50 Z '
                        'M40 50 A10 10 0 1 0 60 50 A10 10 0 1 0 40 50 Z"/>')
    r = ok(s, "insert_svg", path=str(ruta), plane="XY")
    oid = r["object_ids"][0]
    br = s.doc.estado_final.bocetos[r["sketch"]["id"]]
    assert all(p[0] == "arco" for p in br.boceto.geometria())
    for escala in (1, -1):
        if escala == -1:
            ok(s, "transform_vector_objects", objects=[oid], angle=37, scale_x=-1, scale_y=1)
        utiles = ok(s, "get_vector_regions", objects=[oid])["profiles"]
        assert sum(p["area"] for p in utiles) == pytest.approx(300 * math.pi, rel=1e-9)


def test_viewbox_respeta_ambas_dimensiones_y_preserve_aspect_ratio(tmp_path):
    ruta = tmp_path / "aspecto.svg"
    for aspecto, ancho, alto in (("none", 80, 20), ("xMidYMid meet", 20, 20)):
        ruta.write_text(f'<svg width="80mm" height="20mm" viewBox="0 0 10 10" preserveAspectRatio="{aspecto}">'
                        '<rect width="10" height="10"/></svg>', encoding="utf-8")
        b = boceto_desde_primitivas(leer_svg(ruta))
        x0, y0, x1, y1 = ob.caja(b, ob.raices(b))
        assert (x1 - x0, y1 - y0) == pytest.approx((ancho, alto))


@pytest.mark.parametrize("contenido", ["HOLA", "ZAI FEST"])
def test_texto_editable_transformado_convertido_separado_y_extruido(contenido):
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY")
    t = ok(s, "add_text", text=contenido, font="Arial", height=10)["entities"][0]["id"]
    oid = ok(s, "get_vector_objects")["roots"][0]
    ok(s, "transform_vector_objects", objects=[oid], dx=20, dy=30, angle=23, scale_x=1.5)
    ok(s, "edit_text", entity=t, font="Times New Roman", height=12)
    assert ok(s, "get_vector_objects")["objects"][0]["editable_text"] == [t]
    perfiles = ok(s, "get_vector_regions", objects=[oid])["profiles"]
    area = sum(p["area"] for p in perfiles)
    ok(s, "explode_text", entity=t)
    assert ok(s, "get_vector_objects")["roots"] == [oid]
    convertidos = ok(s, "get_vector_regions", objects=[oid])["profiles"]
    assert sum(p["area"] for p in convertidos) == pytest.approx(area, rel=1e-8)
    hijos = ok(s, "separate_vector_regions", object=oid)["object_ids"]
    assert len(hijos) == len(contenido.replace(" ", ""))
    for i in hijos:
        ok(s, "extrude", sketch=ok(s, "get_vector_objects")["sketch"], profile=f"object:{i}", distance=2)
    assert sum(geo.volumen(c.forma) for c in s.doc.estado_final.cuerpos.values()) == pytest.approx(area * 2, rel=2e-5)
    assert all(geo.es_valida(c.forma) for c in s.doc.estado_final.cuerpos.values())


def test_duplicar_texto_no_edita_el_contenido_del_original():
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY")
    t = ok(s, "add_text", text="HOLA", font="Arial", height=10)["entities"][0]["id"]
    oid = ok(s, "get_vector_objects")["roots"][0]
    nuevo = ok(s, "duplicate_vector_objects", objects=[oid])["object_ids"][0]
    copia = next(o for o in ok(s, "get_vector_objects")["objects"] if o["id"] == nuevo)["editable_text"][0]
    ok(s, "edit_text", entity=copia, text="ZAI FEST")
    textos = {e["id"]: e["text"] for e in ok(s, "get_sketch")["entities"]}
    assert textos[t] == "HOLA" and textos[copia] == "ZAI FEST"


def test_desagrupar_una_forma_no_rompe_el_contorno_ni_el_relleno(tmp_path):
    """Desagrupar un elemento del SVG no puede separar sus curvas: se perderían el contorno cerrado y la regla de relleno."""
    ruta = svg(tmp_path, '<path fill-rule="evenodd" d="M10 10H30V30H10Z M15 15H25V25H15Z"/>')
    b = boceto_desde_primitivas(leer_svg(ruta))
    ob.desagrupar(b, ob.raices(b)[0])          # el path queda como raíz
    forma = next(o["id"] for o in b.objetos.values() if o.get("regla_relleno"))
    assert ob.desagrupar(b, forma) == [forma]   # una hoja no se separa
    perfiles = detectar_boceto(b, geo.Plano("XY"))
    assert len(perfiles) == 2
    assert sum(p.area for p in sin_huecos(perfiles, b)) == pytest.approx(300, rel=1e-6)


def test_desagrupar_un_grupo_parametrico_conserva_sus_formulas():
    s = api.Sesion()
    ok(s, "create_sketch", plane="XY")
    ids = []
    for x in (10, 40):
        c = ok(s, "draw_circle", center_x=x, radius=3)["entities"][0]["id"]
        ids.append(ok(s, "create_vector_object", entities=[c])["object_id"])
    grupo = ok(s, "group_vector_objects", objects=ids)["object_id"]
    ok(s, "create_parameter", name="separar", expression="10 mm")
    ok(s, "transform_vector_objects", objects=[grupo], dx="separar")
    ok(s, "ungroup_vector_object", object=grupo)
    ok(s, "set_parameter", name="separar", expression="30 mm")
    xs = sorted(o["position"][0] for o in ok(s, "get_vector_objects")["objects"])
    assert xs == pytest.approx([37, 67])


def test_offset_booleana_y_validacion_de_objetos(tmp_path):
    s = api.Sesion()
    ruta = svg(tmp_path, '<path fill-rule="evenodd" d="M10 10H30V30H10Z M15 15H25V25H15Z"/>')
    oid = ok(s, "insert_svg", path=str(ruta), plane="XY")["object_ids"][0]
    assert ok(s, "validate_vector_objects", objects=[oid])["valid"]
    desfase = ok(s, "offset_vector_objects", objects=[oid], distance=1, corners="sharp")["object_id"]
    assert sum(p["area"] for p in ok(s, "get_vector_regions", objects=[desfase])["profiles"]) == pytest.approx(22**2 - 8**2)
    copia = ok(s, "duplicate_vector_objects", objects=[oid], dx=8)["object_ids"][0]
    unido = ok(s, "combine_vector_objects", objects=[oid, copia])["object_id"]
    assert ok(s, "validate_vector_objects", objects=[unido])["valid"]
    assert len(ok(s, "get_vector_regions", objects=[unido])["profiles"]) >= 1


def test_validar_abiertos_duplicados_y_autointersecciones(tmp_path):
    for contenido, campo in (('<path d="M10 10H30V30"/>', "open_curves"),
                              ('<path d="M10 10L30 30L10 30L30 10Z"/>', "intersections"),
                              ('<path d="M10 10H30V30H10Z M10 10H30V30H10Z"/>', "duplicate_curves")):
        s = api.Sesion()
        oid = ok(s, "insert_svg", path=str(svg(tmp_path, contenido)), plane="XY")["object_ids"][0]
        r = ok(s, "validate_vector_objects", objects=[oid])
        assert not r["valid"] and r[campo], r


def test_simplificar_es_opcional_acotado_y_no_toca_otro_objeto(tmp_path):
    s = api.Sesion()
    ruta = svg(tmp_path, '<path d="M10 10H20H30V30H10Z"/><path d="M50 50H60H70V70H50Z"/>')
    oid = ok(s, "insert_svg", path=str(ruta), plane="XY")["object_ids"][0]
    b = next(iter(s.doc.estado_final.bocetos.values())).boceto
    fuentes = [o for o in b.objetos.values() if "regla_relleno" in o]
    antes = {i: b.curvas[i].a_dict() for i in fuentes[1]["entidades"]}
    r = ok(s, "simplify_vector_object", object=fuentes[0]["id"], tolerance=0.01)
    assert r["removed"] == 1 and r["after"] == 4 and r["measured_deviation_mm"] <= 0.01
    actual = next(iter(s.doc.estado_final.bocetos.values())).boceto
    assert {i: actual.curvas[i].a_dict() for i in antes} == antes
    assert sum(p["area"] for p in ok(s, "get_vector_regions", objects=[oid])["profiles"]) == pytest.approx(800)


def test_formato_nuevo_impide_que_un_lector_viejo_ignore_las_matrices(tmp_path, monkeypatch):
    from omnicad.io_archivos import proyecto
    s = api.Sesion()
    oid = ok(s, "insert_svg", path=str(svg(tmp_path, '<rect width="20" height="10"/>')), plane="XY")["object_ids"][0]
    ok(s, "transform_vector_objects", objects=[oid], dx=50)
    ruta = tmp_path / "nuevo.omnicad"
    ok(s, "save_document", path=str(ruta))
    monkeypatch.setattr(proyecto, "VERSION_FORMATO", 1)
    with pytest.raises(proyecto.ErrorProyecto, match="más nueva"):
        proyecto.abrir(ruta)


def test_dxf_como_objeto_unico_con_capas_y_perfiles_estables(tmp_path):
    from omnicad.io_archivos.dxf import escribir_dxf
    ruta = tmp_path / "pieza.dxf"
    escribir_dxf(ruta, [("polilinea", [(10, 10), (30, 10), (30, 30), (10, 30)], True)])
    s = api.Sesion()
    r = ok(s, "insert_dxf", path=str(ruta), plane="XY")
    oid = r["object_ids"][0]
    b = s.doc.estado_final.bocetos[r["sketch"]["id"]].boceto
    ids = set(b.curvas)
    assert len(ob.raices(b)) == 1 and resolver(b).gdl == 0
    assert b.objetos[oid]["tipo_origen"] == "DXF"
    ok(s, "transform_vector_objects", objects=[oid], dx=5, scale_x=2)
    ok(s, "extrude", sketch=r["sketch"]["id"], profile=f"object:{oid}", distance=3)
    cuerpo = next(iter(s.doc.estado_final.cuerpos.values()))
    assert geo.volumen(cuerpo.forma) == pytest.approx(4800) and geo.es_valida(cuerpo.forma)
    assert set(s.doc.estado_final.bocetos[r["sketch"]["id"]].boceto.curvas) == ids


def test_dxf_con_texto_conserva_la_jerarquia_y_el_texto_editable(tmp_path):
    from omnicad.io_archivos.dxf import escribir_dxf, leer_dxf
    ruta = tmp_path / "letras.dxf"
    escribir_dxf(ruta, [("letras", ("texto", (0, 0), 10, "OB8")),
                       ("contorno", ("circulo", (30, 30), 5))])
    b = boceto_desde_primitivas(leer_dxf(ruta))
    assert len(ob.raices(b)) == 1
    tid = next(c.id for c in b.curvas.values() if c.tipo == "texto")
    assert b.curvas[tid].texto == "OB8" and ob.indice(b)[tid][0] == ob.raices(b)[0]
    ob.transformar(b, ob.raices(b), ob.afin(10, 20, 35, 2, 2))
    assert detectar_boceto(b, geo.Plano("XY"))


def test_restablecer_transformacion_por_api_conserva_ids_y_extrusion(tmp_path):
    s = api.Sesion()
    oid = ok(s, "insert_svg", path=str(svg(tmp_path, '<rect width="20" height="10"/>')), plane="XY")["object_ids"][0]
    antes = ok(s, "get_vector_objects")["objects"][-1]
    ok(s, "extrude", sketch=ok(s, "get_vector_objects")["sketch"], profile=f"object:{oid}", distance=2)
    ok(s, "transform_vector_objects", objects=[oid], dx=40, angle=30, scale_x=2)
    ok(s, "set_vector_object", object=oid, reset_transform=True)
    actual = next(o for o in ok(s, "get_vector_objects")["objects"] if o["id"] == oid)
    assert actual["curves"] == antes["curves"] and actual["width"] == pytest.approx(20)
    cuerpo = next(iter(s.doc.estado_final.cuerpos.values()))
    assert geo.volumen(cuerpo.forma) == pytest.approx(400) and geo.es_valida(cuerpo.forma)


def test_limites_rapidos_coinciden_con_el_kernel_exacto():
    """Árbitro independiente de las fórmulas de UI: las cajas del B-rep sin malla."""
    from omnicad.nucleo.perfiles import aristas_boceto
    rng = np.random.default_rng(1974)
    prims = []
    for i in range(100):
        centro = tuple(rng.uniform(-1e5, 1e5, 2))
        prims.extend([("circulo", i, centro, float(rng.uniform(0.01, 100))),
                      ("elipse", i, centro, 80., 3., float(rng.uniform(-math.pi, math.pi))),
                      ("spline", i, tuple(map(tuple, rng.uniform(-100, 100, (4, 2)) + centro)),
                       (0., 0., 0., 0., 1., 1., 1., 1.), 3, None)])
    prims.append(("spline", 101, ((0., 0.), (10., 0.), (20., 0.), (30., 0.)),
                  (0., 0., 0., 0., 1., 1., 1., 1.), 3, None))
    for prim in prims:
        arista = aristas_boceto([prim], geo.Plano("XY"))[0][1]
        assert geo.es_valida(arista)
        a, b = geo.caja_envolvente(arista)
        assert ob.limites_primitiva(prim) == pytest.approx((a[0], a[1], b[0], b[1]), abs=2e-6)


@pytest.mark.parametrize("forma", ["anillo", "casi_coincidentes"])
def test_transformar_no_reintersecta_ni_cambia_topologia_de_un_objeto(forma, monkeypatch):
    from omnicad.nucleo import perfiles as pf
    b = Boceto()
    if forma == "anillo":
        cids = [b.agregar_circulo((0, 0), r) for r in (10, 9.99985)]
    else:
        cids = b.agregar_rectangulo((0, 0), (10, 10)) + b.agregar_rectangulo((.00015, .00015), (10.00015, 10.00015))
    oid = ob.crear(b, cids)
    pl = geo.Plano("XY")
    originales = detectar_boceto(b, pl)
    llamadas = []
    detectar = pf._detectar
    def contar(*args, **kwargs):
        llamadas.append(True)
        return detectar(*args, **kwargs)
    monkeypatch.setattr(pf, "_detectar", contar)
    ob.transformar(b, [oid], ob.afin(-88.914, 1.567, sx=.529, sy=.529))
    nuevos = detectar_boceto(b, pl)
    assert llamadas == [], "Una matriz del recurso no debe volver a intersectar sus curvas locales."
    assert len(nuevos) == len(originales)
    assert sorted(p.area for p in nuevos) == pytest.approx(sorted(p.area * .529 ** 2 for p in originales), rel=1e-7, abs=1e-9)
    assert all(geo.es_valida(p.cara) for p in nuevos)
