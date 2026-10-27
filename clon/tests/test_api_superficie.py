"""Superficies por MCP/CLI: áreas, referencias persistentes, errores atómicos y deshacer."""
import inspect
import json
import math

import pytest

from omnicad import api
from omnicad.api import herramientas_superficie as hs
from omnicad.nucleo import geometria as geo


TIPOS = {
    "create_surface_extrude": "sup_extruir", "create_surface_revolve": "sup_revolucion",
    "create_surface_sweep": "sup_barrido", "create_surface_loft": "sup_solevacion",
    "offset_surface": "sup_desfase", "fillet_surface": "sup_empalme", "create_patch": "parche",
    "create_ruled_surface": "reglada", "extend_surface": "extender_sup", "trim_surface": "recortar_sup",
    "untrim_surface": "destrimar", "stitch_surfaces": "coser", "unstitch_surfaces": "descoser",
    "reverse_surface_normal": "invertir_normal",
}


def llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    resultado = respuesta["result"]
    if nombre in TIPOS:
        assert resultado["feature"]["type"] == TIPOS[nombre]
        assert sesion.doc.operaciones[-1].TIPO == TIPOS[nombre]
    return resultado


def creado(sesion, nombre, **args):
    return llamar(sesion, nombre, **args)["bodies_created"][0]["id"]


def linea(sesion, nombre="Perfil", inicio=(0, 0), fin=(20, 0), plano="XY"):
    llamar(sesion, "create_sketch", name=nombre, plane=plano)
    llamar(sesion, "draw_line", sketch=nombre, start_x=inicio[0], start_y=inicio[1], end_x=fin[0], end_y=fin[1])
    curvas = sesion.doc.estado_final.bocetos[sesion.paso(nombre).id].boceto.curvas
    return {"sketch": nombre, "curve": next(iter(curvas))}


def parche(sesion, nombre="Contorno", x1=0, x2=10, plano="XY"):
    llamar(sesion, "create_sketch", name=nombre, plane=plano)
    llamar(sesion, "draw_rectangle", sketch=nombre, x1=x1, y1=0, x2=x2, y2=10)
    return creado(sesion, "create_patch", boundary={"sketch": nombre, "profile": 0})


def area(sesion, cid, esperada, tolerancia=1e-5):
    forma = sesion.cuerpo(cid).forma
    assert geo.es_valida(forma)
    assert geo.area(forma) == pytest.approx(esperada, rel=tolerancia)
    return forma


def test_catalogo_y_documentacion_completa():
    catalogo = {h["nombre"]: h for h in api.catalogo("solido")}
    for nombre in TIPOS:
        h = catalogo[nombre]
        assert h["modifica"]
        parametros = set(inspect.signature(getattr(hs, nombre)).parameters) - {"sesion"}
        assert set(h["esquema"]["properties"]) == parametros
        assert all(p.get("description") for p in h["esquema"]["properties"].values())


def test_extrusion_abierta_simetrica_y_deshacer():
    s = api.Sesion()
    perfil = linea(s)
    antes = json.dumps(s.doc.a_dict(), sort_keys=True)
    pila = len(s.doc._deshacer)
    cid = creado(s, "create_surface_extrude", profiles=perfil, distance=5, symmetric=True)
    forma = area(s, cid, 100)
    assert [p[2] for p in geo.caja_envolvente(forma)] == pytest.approx([-2.5, 2.5])
    assert llamar(s, "get_scene_info")["bodies"][0]["type"] == "surface"
    assert len(s.doc._deshacer) == pila + 1
    llamar(s, "undo")
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes


def test_extrusion_perfil_y_conicidad_con_expresion():
    s = api.Sesion()
    llamar(s, "create_parameter", name="altura", expression="5 mm")
    llamar(s, "create_sketch", name="Rectángulo")
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=20, y2=10)
    cid = creado(s, "create_surface_extrude", profiles={"sketch": "Rectángulo", "profile": "largest"},
                 direction="Z", distance="altura", taper_angle=5)
    t = 5 * math.tan(math.radians(5))
    area(s, cid, (60 + 4 * t) * 5 / math.cos(math.radians(5)))


def test_revolucion_segmento_alrededor_de_z():
    s = api.Sesion()
    perfil = linea(s, inicio=(5, 0), fin=(5, 10), plano="XZ")
    cid = creado(s, "create_surface_revolve", profiles=perfil, axis="Z", angle=180)
    area(s, cid, 50 * math.pi)


@pytest.mark.parametrize("orientacion,giro", [("perpendicular", 90), ("parallel", 0)])
def test_barrido_orientacion_y_torsion(orientacion, giro):
    s = api.Sesion()
    perfil = linea(s, inicio=(-5, 0), fin=(5, 0))
    ruta = linea(s, nombre="Ruta", inicio=(0, 0), fin=(0, 100), plano="XZ")
    cid = creado(s, "create_surface_sweep", profiles=perfil, path=ruta, orientation=orientacion, twist_angle=giro)
    k = math.radians(giro) / 100
    esperada = 1000 if not giro else 100 * (5 * math.sqrt(1 + (5 * k) ** 2) + math.asinh(5 * k) / k)
    # El barrido con torsión aproxima el helicoide con B-splines (misma tolerancia que test_superficies).
    area(s, cid, esperada, tolerancia=1e-4)


def test_barrido_hasta_una_fraccion_de_la_ruta():
    s = api.Sesion()
    perfil = linea(s, inicio=(-5, 0), fin=(5, 0))
    ruta = linea(s, nombre="Ruta", inicio=(0, 0), fin=(0, 100), plano="XZ")
    cid = creado(s, "create_surface_sweep", profiles=perfil, path=ruta, path_distance=0.4)
    area(s, cid, 400)
    paso = s.doc.operacion(s.doc.operaciones[-1].id)
    assert paso.p["distancia"] == "0.4"
    malo = api.llamar(s, "create_surface_sweep", {"profiles": perfil, "path": ruta, "path_distance": 2})
    assert not malo["ok"]
    # una receta anterior, sin el parámetro, barre toda la ruta
    from omnicad.timeline.ops_superficie import OpSupBarrido
    viejo = {k: v for k, v in paso.p.items() if k != "distancia"}
    s.doc.reemplazar(paso.id, OpSupBarrido(paso.id, paso.nombre, False, **viejo))
    area(s, cid, 1000)


def test_solevacion_abierta_reglada():
    s = api.Sesion()
    perfiles = [linea(s, nombre=f"Sección{i}", inicio=(x, y), fin=(x, y + 10))
                for i, (x, y) in enumerate([(0, 0), (4, 0)])]
    cid = creado(s, "create_surface_loft", profiles=perfiles, ruled=True)
    area(s, cid, 40)


def test_solevacion_cerrada_reglada():
    s = api.Sesion()
    llamar(s, "create_construction_plane", plane="XZ", offset=-3, name="Desfasado")
    perfiles = [linea(s, nombre="Primera", inicio=(0, 0), fin=(0, 10), plano="XZ"),
                linea(s, nombre="Segunda", inicio=(4, 0), fin=(4, 10), plano="XZ"),
                linea(s, nombre="Tercera", inicio=(0, 0), fin=(0, 10), plano="Desfasado")]
    cid = creado(s, "create_surface_loft", profiles=perfiles, ruled=True, closed=True)
    area(s, cid, 120)


def test_solevacion_de_perfiles_cerrados():
    s = api.Sesion()
    llamar(s, "create_construction_plane", offset=10, name="Superior")
    for nombre, plano in [("Abajo", "XY"), ("Arriba", "Superior")]:
        llamar(s, "create_sketch", name=nombre, plane=plano)
        llamar(s, "draw_circle", radius=5, sketch=nombre)
    cid = creado(s, "create_surface_loft", profiles=[{"sketch": nombre, "profile": 0} for nombre in ["Abajo", "Arriba"]])
    area(s, cid, 100 * math.pi)


def test_selector_con_prefijo_respeta_body_y_cuerpo_como_perfil():
    s = api.Sesion()
    base = parche(s)
    otra = creado(s, "offset_surface", faces=base, distance=20)
    cid = creado(s, "create_surface_extrude", profiles="edges:all", body=base, distance=5)
    area(s, cid, 200)
    cid = creado(s, "create_surface_extrude", profiles={"body": otra}, distance=5)
    area(s, cid, 200)


def test_parche_con_ids_de_aristas_y_desfase_de_cara():
    s = api.Sesion()
    base = parche(s)
    aristas = llamar(s, "find_edges", body=base)["edges"]
    copia = creado(s, "create_patch", boundary=[a["id"] for a in aristas])
    area(s, copia, 100)
    cara = llamar(s, "find_faces", body=copia)["faces"][0]["id"]
    cid = creado(s, "offset_surface", faces=cara, distance=2, offset_type="rounded")
    forma = area(s, cid, 100)
    assert geo.caja_envolvente(forma)[0][2] == pytest.approx(2)


@pytest.mark.parametrize("tipo", ["sharp", "rounded"])
def test_desfase_cuerpo_por_nombre(tipo):
    s = api.Sesion()
    base = parche(s)
    cid = creado(s, "offset_surface", faces=s.nombre_cuerpo(s.cuerpo(base)), distance=-2, offset_type=tipo)
    area(s, cid, 100)


@pytest.mark.parametrize("tipo,direccion,angulo", [("normal", None, 45), ("tangent", None, 0), ("direction", "Z", 0)])
def test_reglada_opciones(tipo, direccion, angulo):
    s = api.Sesion()
    base = parche(s)
    cid = creado(s, "create_ruled_surface", edges="<Y", body=base, distance=5,
                 surface_type=tipo, direction=direccion, angle=angulo)
    area(s, cid, 50)


def dos_superficies(s):
    base = parche(s)
    pared = parche(s, nombre="Pared", plano="XZ")
    return base, pared


def test_coser_y_descoser_conservan_area_y_un_solo_cuerpo():
    s = api.Sesion()
    base, pared = dos_superficies(s)
    llamar(s, "stitch_surfaces", bodies=[base, pared], tolerance="0.001 mm")
    assert len(s.doc.estado_final.cuerpos) == 1
    forma = area(s, base, 200)
    assert len(geo.caras(forma)) == 2
    r = llamar(s, "unstitch_surfaces", bodies=base)
    assert len(r["bodies_created"]) == 2 and r["bodies_removed"] == [base]
    for cuerpo in r["bodies_created"]:
        area(s, cuerpo["id"], 100)
    llamar(s, "undo")
    assert len(s.doc.estado_final.cuerpos) == 1
    area(s, base, 200)


@pytest.mark.parametrize("tolerancia", ["0", "-1"])
def test_coser_rechaza_tolerancia_cero_o_negativa(tolerancia):
    """SUP-8: una tolerancia ≤ 0 no cose nada y antes pasaba en silencio."""
    s = api.Sesion()
    base, pared = dos_superficies(s)
    antes = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, "stitch_surfaces", {"bodies": [base, pared], "tolerance": tolerancia})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes


def test_coser_rechaza_una_expresion_que_da_cero():
    """El núcleo también valida la tolerancia ya evaluada (expresión o panel)."""
    s = api.Sesion()
    base, pared = dos_superficies(s)
    r = api.llamar(s, "stitch_surfaces", {"bodies": [base, pared], "tolerance": "0 mm"})
    assert not r["ok"] and "tolerancia de costura" in r["mensaje"], r


def test_dividir_un_cuerpo_de_superficie():
    """SUP-2: dividir un tubo de superficie da dos cuerpos de superficie, no un error."""
    s = api.Sesion()
    llamar(s, "create_sketch", name="Circulo")
    llamar(s, "draw_circle", sketch="Circulo", radius=10)
    tubo = creado(s, "create_surface_extrude", profiles={"sketch": "Circulo", "profile": 0}, distance=20)
    llamar(s, "create_construction_plane", plane="XY", offset=10, name="Mitad")
    r = llamar(s, "split_body", body=tubo, tool="Mitad")
    assert len(r["bodies_created"]) == 1
    for cid in [tubo] + [b["id"] for b in r["bodies_created"]]:
        assert s.cuerpo(cid).tipo == "superficie"
        area(s, cid, 200 * math.pi)


@pytest.mark.parametrize("tipo,esperada", [("fillet", 160 + 10 * math.pi), ("chamfer", 160 + 20 * math.sqrt(2))])
def test_empalme_y_chaflan_superficie(tipo, esperada):
    s = api.Sesion()
    base, pared = dos_superficies(s)
    llamar(s, "stitch_surfaces", bodies=[base, pared])
    llamar(s, "fillet_surface", edges="nearest:[5,0,0]", body=base, size=2, fillet_type=tipo)
    area(s, base, esperada)


@pytest.mark.parametrize("tipo,caras", [("natural", 1), ("tangent", 2), ("perpendicular", 2)])
def test_extender_opciones(tipo, caras):
    s = api.Sesion()
    base = parche(s)
    llamar(s, "extend_surface", edges=">X", body=base, distance=5, extension_type=tipo)
    forma = area(s, base, 150)
    assert len(geo.caras(forma)) == caras


def test_recortar_por_plano_y_por_cuerpo():
    s = api.Sesion()
    base = parche(s, x1=-5, x2=5)
    llamar(s, "trim_surface", surface=base, tool="YZ", remove_point=[3, 5, 0])
    area(s, base, 50)
    s = api.Sesion()
    base = parche(s)
    ruta = linea(s, nombre="Corte", inicio=(0, 3), fin=(10, 3))
    corte = creado(s, "create_surface_extrude", profiles=ruta, distance=10, symmetric=True)
    llamar(s, "trim_surface", surface=base, tool=corte, remove_point=[5, 1, 0])
    area(s, base, 70)


def test_destrimar_cilindro_recupera_limites_naturales():
    s = api.Sesion()
    perfil = linea(s, inicio=(5, 0), fin=(5, 10), plano="XZ")
    cid = creado(s, "create_surface_revolve", profiles=perfil, axis="Z", angle=120)
    llamar(s, "untrim_surface", faces="all", body=cid, boundaries="outer")
    area(s, cid, 100 * math.pi)


def test_invertir_normal_conserva_area_y_cambia_orientacion():
    s = api.Sesion()
    base = parche(s)
    normal = geo.plano_de_cara(geo.caras(s.cuerpo(base).forma)[0]).normal.copy()
    llamar(s, "reverse_surface_normal", bodies=base)
    forma = area(s, base, 100)
    assert geo.plano_de_cara(geo.caras(forma)[0]).normal == pytest.approx(-normal)


@pytest.mark.parametrize("nombre,args,kind", [
    ("create_surface_extrude", {"profiles": []}, "INVALID_ARGUMENTS"),
    ("create_surface_revolve", {"profiles": {"sketch": "Nada", "curve": 1}, "axis": "Z"}, "SKETCH_NOT_FOUND"),
    ("create_surface_sweep", {"profiles": [], "path": []}, "INVALID_ARGUMENTS"),
    ("create_surface_loft", {"profiles": []}, "INVALID_ARGUMENTS"),
    ("offset_surface", {"faces": "Nada"}, "BODY_NOT_FOUND"),
    ("fillet_surface", {"edges": "all", "size": -1}, "INVALID_ARGUMENTS"),
    ("create_patch", {"boundary": []}, "INVALID_ARGUMENTS"),
    ("create_ruled_surface", {"edges": "all", "surface_type": "direction"}, "INVALID_ARGUMENTS"),
    ("extend_surface", {"edges": []}, "INVALID_ARGUMENTS"),
    ("trim_surface", {"surface": "Nada", "tool": "YZ", "remove_point": [1, 2]}, "INVALID_ARGUMENTS"),
    ("untrim_surface", {"faces": []}, "INVALID_ARGUMENTS"),
    ("stitch_surfaces", {"bodies": []}, "INVALID_ARGUMENTS"),
    ("unstitch_surfaces", {"bodies": "Nada"}, "BODY_NOT_FOUND"),
    ("reverse_surface_normal", {"bodies": []}, "INVALID_ARGUMENTS"),
])
def test_error_por_herramienta_no_modifica_documento(nombre, args, kind):
    s = api.Sesion()
    antes = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes
    assert not s.doc._deshacer


def test_error_del_kernel_revierte_transaccion():
    s = api.Sesion()
    perfil = linea(s)
    antes = json.dumps(s.doc.a_dict(), sort_keys=True)
    pila = len(s.doc._deshacer)
    r = api.llamar(s, "create_patch", {"boundary": perfil})
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED", r
    assert "no es cerrado" in r["mensaje"]
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes
    assert len(s.doc._deshacer) == pila


def _curva_de(sesion, nombre):
    curvas = sesion.doc.estado_final.bocetos[sesion.paso(nombre).id].boceto.curvas
    return {"sketch": nombre, "curve": next(iter(curvas))}


def test_superficies_degeneradas_avisan_y_no_crean_el_paso():
    """SUP-6: un resultado sin área o inválido no puede pasar como correcto."""
    s = api.Sesion()
    llamar(s, "create_sketch", name="Circulo")
    llamar(s, "draw_circle", sketch="Circulo", radius=5)
    circulo = _curva_de(s, "Circulo")
    recta = linea(s, nombre="Recta", inicio=(5, 0), fin=(5, 10), plano="XZ")
    casos = [
        ("create_surface_sweep", {"profiles": circulo, "path": circulo}),
        ("create_surface_revolve", {"profiles": recta, "axis": "Z", "angle": "1e-6 deg"}),
        ("create_surface_extrude", {"profiles": recta, "distance": "1e-6 mm"}),
    ]
    for nombre, args in casos:
        antes = json.dumps(s.doc.a_dict(), sort_keys=True)
        r = api.llamar(s, nombre, args)
        assert not r["ok"], (nombre, r)
        assert r["error_kind"] == "OPERATION_FAILED", (nombre, r)
        assert "degenerada" in r["mensaje"], (nombre, r)
        assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes
