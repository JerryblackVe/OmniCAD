"""Construcción y referencias embebidas por la API pública, sin Qt."""
import math

import numpy as np
import pytest
from PIL import Image

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPlano
from omnicad.timeline.ops_construir import OpEje, OpSCU


def llamar(sesion, nombre, **args):
    resultado = api.llamar(sesion, nombre, args)
    assert resultado["ok"], resultado
    return resultado["result"]


def test_catalogo_y_parametros_documentados():
    nombres = {"create_construction_axis", "create_construction_point", "create_ucs", "insert_fastener", "insert_canvas",
               "create_base_feature", "split_face", "split_body", "silhouette_split", "replace_face", "remove_bodies",
               "delete_faces"}
    herramientas = {h["nombre"]: h for h in api.catalogo() if h["nombre"] in nombres}
    assert len(herramientas) == 12
    for nombre, herramienta in herramientas.items():
        assert herramienta["modifica"]
        grupo = "boceto" if nombre in {"create_construction_axis", "create_construction_point", "create_ucs"} else "solido"
        assert herramienta["grupo"] == grupo
        assert all(p.get("description") for p in herramienta["esquema"]["properties"].values())


def boceto_linea(s):
    bid = llamar(s, "create_sketch")["sketch"]["id"]
    llamar(s, "draw_line", sketch=bid, start_x=2, start_y=3, end_x=12, end_y=3)
    br = s.doc.estado_final.bocetos[bid]
    curva = next(iter(br.boceto.curvas))
    punto = next(iter(br.boceto.puntos))
    return {"sketch": bid, "curve": curva}, {"sketch": bid, "point": punto}


@pytest.mark.parametrize("tipo", ["cilindro", "perpendicular_cara", "dos_planos", "dos_puntos", "arista"])
def test_ejes_cada_variante(tipo):
    s = api.Sesion()
    curva, punto = boceto_linea(s)
    cid = llamar(s, "create_cylinder", radius=5, height=10, x=3, y=4)["bodies_created"][0]["id"]
    referencias = {"cilindro": ["%CYLINDER"], "perpendicular_cara": ["XY", punto],
                   "dos_planos": ["XY", "XZ"], "dos_puntos": ["O", punto], "arista": [curva]}
    origenes = {"cilindro": [3, 4, 5], "perpendicular_cara": [2, 3, 0], "dos_planos": [0, 0, 0],
                "dos_puntos": [0, 0, 0], "arista": [2, 3, 0]}
    direcciones = {"cilindro": [0, 0, 1], "perpendicular_cara": [0, 0, 1], "dos_planos": [1, 0, 0],
                   "dos_puntos": [2 / math.sqrt(13), 3 / math.sqrt(13), 0], "arista": [1, 0, 0]}
    r = llamar(s, "create_construction_axis", type=tipo, references=referencias[tipo], body=cid)
    assert r["axis"]["type"] == "eje"
    assert r["origin"] == pytest.approx(origenes[tipo])
    assert r["direction"] == pytest.approx(direcciones[tipo])
    assert geo.es_valida(s.cuerpo(cid).forma)


@pytest.mark.parametrize("tipo", ["vertice", "dos_aristas", "tres_planos", "centro", "arista_plano", "ruta"])
def test_puntos_cada_variante(tipo):
    s = api.Sesion()
    curva, punto = boceto_linea(s)
    cid = llamar(s, "create_sphere", radius=2, x=3, y=4, z=5)["bodies_created"][0]["id"]
    referencias = {"vertice": [punto], "dos_aristas": ["X", "Y"], "tres_planos": ["XY", "XZ", "YZ"],
                   "centro": ["%SPHERE"], "arista_plano": ["Z", "XY"], "ruta": [curva]}
    posiciones = {"vertice": [2, 3, 0], "dos_aristas": [0, 0, 0], "tres_planos": [0, 0, 0],
                  "centro": [3, 4, 5], "arista_plano": [0, 0, 0], "ruta": [7, 3, 0]}
    r = llamar(s, "create_construction_point", type=tipo, references=referencias[tipo], body=cid, position=0.5)
    assert r["point"]["type"] == "punto"
    assert r["position"] == pytest.approx(posiciones[tipo])
    assert geo.es_valida(s.cuerpo(cid).forma)


def test_vertice_real_y_dos_aristas_en_interseccion():
    s = api.Sesion()
    cid = llamar(s, "create_box", length=10, width=10, height=10, anchor="corner")["bodies_created"][0]["id"]
    forma = s.cuerpo(cid).forma
    vertice = refs.subformas(forma, "vertice")[0]
    referencia = refs.referencia(cid, vertice, forma)
    r = llamar(s, "create_construction_point", type="vertice", references=[referencia])
    assert r["position"] == pytest.approx(refs.punto_de_vertice(vertice))
    r = llamar(s, "create_construction_point", type="dos_aristas",
               references=["edges:|X and <Y and <Z", "edges:|Y and <X and <Z"], body=cid)
    assert r["position"] == pytest.approx([0, 0, 0])
    assert geo.es_valida(forma)


def test_punto_de_construccion_acepta_el_formato_body_vertex():
    s = api.Sesion()
    cid = llamar(s, "create_box", length=10, width=10, height=10, anchor="corner")["bodies_created"][0]["id"]
    vertice = refs.subformas(s.cuerpo(cid).forma, "vertice")[0]
    r = llamar(s, "create_construction_point", type="vertice", references=[{"body": cid, "vertex": 1}])
    assert r["position"] == pytest.approx(refs.punto_de_vertice(vertice))


def test_scu_origen_ejes_y_planos():
    s = api.Sesion()
    _, punto = boceto_linea(s)
    r = llamar(s, "create_ucs", origin=punto, x_axis="Y", y_axis="Z", dx=1, dy=2, dz=3, rz=90)
    assert r["ucs"]["type"] == "scu"
    assert r["origin"] == pytest.approx([5, 4, 2])
    assert r["axes"]["x"]["direction"] == pytest.approx([0, 0, 1])
    assert r["axes"]["y"]["direction"] == pytest.approx([0, -1, 0])
    assert r["axes"]["z"]["direction"] == pytest.approx([1, 0, 0])
    for pid in r["planes"].values():
        assert s.doc.estado_final.planos[pid].origen == pytest.approx([5, 4, 2])


@pytest.mark.parametrize("posicion,zmin,zmax", [("%CYLINDER", -6, 20), ("edges:%CIRCLE and >Z", -10, 16)])
def test_fijacion_m6_respeta_agujero_y_no_modifica_placa(posicion, zmin, zmax):
    s = api.Sesion()
    cid = llamar(s, "create_box", length=30, width=30, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_hole", body=cid, face=">Z", points=[[2, 3, 10]], diameter=6.6, through_all=True)
    volumen = geo.volumen(s.cuerpo(cid).forma)
    r = llamar(s, "insert_fastener", positions=[posicion], body=cid, standard="ISO 4762", size="M6", length=20,
               similar=False)
    assert r["feature"]["type"] == "fijacion"
    assert len(r["bodies_created"]) == 1
    assert len(s.doc.estado_final.cuerpos) == 2
    tornillo = s.cuerpo(r["bodies_created"][0]["id"]).forma
    assert geo.es_valida(tornillo) and geo.volumen(tornillo) > 0
    minimo, maximo = geo.caja_envolvente(tornillo)
    assert minimo == pytest.approx([-3, -2, zmin], abs=1e-5)
    assert maximo == pytest.approx([7, 8, zmax], abs=1e-5)
    assert geo.volumen(s.cuerpo(cid).forma) == pytest.approx(volumen)
    assert geo.es_valida(s.cuerpo(cid).forma)


def test_lienzo_embebido_se_guarda_y_reabre(tmp_path):
    s = api.Sesion()
    ruta = tmp_path / "imagen.png"
    Image.new("RGB", (8, 4), "white").save(ruta)
    r = llamar(s, "insert_canvas", path=str(ruta), plane="XZ", width=40, dx=3, dy=4, angle=30, opacity=25, flip=True)
    fid = r["feature"]["id"]
    assert r["feature"]["type"] == "lienzo"
    assert r["width"] == 40 and r["height"] == 20
    lienzo = s.doc.estado_final.lienzos[fid]
    assert lienzo["opacidad"] == 0.25 and lienzo["voltear"]
    assert lienzo["dx"] == 3 and lienzo["dy"] == 4 and lienzo["angulo"] == 30
    proyecto = tmp_path / "lienzo.omnicad"
    llamar(s, "save_document", path=str(proyecto))
    ruta.unlink()
    nueva = api.Sesion()
    llamar(nueva, "open_document", path=str(proyecto))
    assert nueva.doc.operacion(fid).p["imagen"] == s.doc.operacion(fid).p["imagen"]
    assert nueva.doc.estado_final.lienzos[fid]["ancho"] == 40
    assert nueva.doc.estado_final.lienzos[fid]["alto"] == 20


def test_operacion_base_congela_cuerpos_tras_recalcular():
    s = api.Sesion()
    r = llamar(s, "create_box", length=10, width=10, height=10)
    cid, fid = r["bodies_created"][0]["id"], r["feature"]["id"]
    base = llamar(s, "create_base_feature", bodies="Cuerpo1")
    assert base["feature"]["type"] == "operacion_base"
    llamar(s, "edit_feature", feature=fid, params={"ancho": "20 mm"})
    s.doc.recalcular()
    forma = s.cuerpo(cid).forma
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(1000)
    assert len(s.doc.estado_final.cuerpos) == 1


@pytest.mark.parametrize("nombre,args", [
    ("create_construction_axis", {"type": "dos_planos", "references": ["XY"]}),
    ("create_construction_point", {"type": "vertice", "references": ["Z"]}),
    ("create_ucs", {"origin": "XY"}),
    ("insert_fastener", {"positions": []}),
    ("create_base_feature", {"bodies": []}),
])
def test_errores_atomicos(nombre, args):
    s = api.Sesion()
    antes = s.doc.a_dict()
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert s.doc.a_dict() == antes


def test_lienzo_rechaza_imagen_corrupta_y_grande(tmp_path):
    s = api.Sesion()
    ruta = tmp_path / "rota.png"
    ruta.write_bytes(b"No es una imagen")
    for grande in (False, True):
        if grande:
            with ruta.open("wb") as archivo:
                archivo.truncate(32 * 1024 * 1024 + 1)
        antes = s.doc.a_dict()
        r = api.llamar(s, "insert_canvas", {"path": str(ruta)})
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
        assert s.doc.a_dict() == antes


def test_fijacion_en_eje_volteado():
    s = api.Sesion()
    r = llamar(s, "insert_fastener", positions=["X"], size="M6", standard="ISO 4762", length=20, flip=True)
    assert len(r["bodies_created"]) == 1
    forma = s.cuerpo(r["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma) and geo.volumen(forma) > 0
    minimo, maximo = geo.caja_envolvente(forma)
    assert minimo == pytest.approx([-6, -5, -5], abs=1e-5)
    assert maximo == pytest.approx([20, 5, 5], abs=1e-5)


# ---------------------------------------------------------------- CON-2 a CON-8, B-130 y B-131
def caja(s, **k):
    return llamar(s, "create_box", length=20, width=20, height=10, **k)["bodies_created"][0]["id"]


def falla(s, nombre, kind, **args):
    antes = s.doc.a_dict()
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == kind, r
    assert s.doc.a_dict() == antes
    return r


@pytest.mark.parametrize("nombre,args,causa", [
    ("create_construction_axis", {"type": "dos_planos", "references": ["XY", ">Z"]}, "paralelos"),
    ("create_construction_point", {"type": "tres_planos", "references": ["XY", ">Z", "YZ"]}, "no se cortan"),
    ("create_construction_plane", {"type": "tangent", "references": [">Z"]}, "cilíndrica"),
    ("create_construction_plane", {"type": "two_edges", "references": ["edges:|X and >Z and >Y", "edges:|Y and <Z and <X"]}, "se cruzan"),
])
def test_b130_lo_que_no_se_calcula_dice_la_causa(nombre, args, causa):
    s = api.Sesion()
    caja(s)
    r = falla(s, nombre, "OPERATION_FAILED", **args)
    assert causa in r["mensaje"] and "No existe 'op" not in r["mensaje"]


@pytest.mark.parametrize("nombre,args", [
    ("create_construction_plane", {"type": "two_edges", "references": ["S", "X"]}),
    ("create_construction_point", {"type": "arista_plano", "references": ["S", "XY"]}),
    ("create_construction_axis", {"type": "arista", "references": ["S"]}),
])
def test_b131_una_spline_donde_va_una_linea_es_un_error_de_argumentos(nombre, args):
    s = api.Sesion()
    bid = llamar(s, "create_sketch")["sketch"]["id"]
    llamar(s, "draw_spline", sketch=bid, points=[[0, 0], [5, 5], [10, 0]])
    curva = next(iter(s.doc.estado_final.bocetos[bid].boceto.curvas))
    args = dict(args, references=[{"sketch": bid, "curve": curva} if r == "S" else r for r in args["references"]])
    assert "Esa referencia no sirve" in falla(s, nombre, "INVALID_ARGUMENTS", **args)["mensaje"]


def test_receta_vieja_da_el_mismo_plano_eje_y_punto():
    """Una receta guardada antes (sin las claves nuevas): mismos números, escritos a mano."""
    s = api.Sesion()
    caja(s)
    cuerpo = "op1.c1"
    forma = s.cuerpo(cuerpo).forma
    cara = next(c for c in refs.subformas(forma, "cara") if refs.firma_cara(c).get("normal") == pytest.approx((0, 0, 1)))
    vertice = next(c for c in refs.subformas(forma, "vertice") if refs.punto_de_vertice(c) == pytest.approx((-10, -10, 10)))
    rcara, rvert = refs.referencia(cuerpo, cara, forma), refs.referencia(cuerpo, vertice, forma)
    doc = s.doc
    doc.agregar(OpPlano(doc.nuevo_id(), "A", tipo="desfase", base="XY", distancia="7 mm"))
    doc.agregar(OpPlano(doc.nuevo_id(), "B", tipo="perpendicular", refs=[rcara, rvert], desfase="2 mm"))
    doc.agregar(OpEje(doc.nuevo_id(), "C", tipo="perpendicular_cara", refs=[rcara, rvert]))
    doc.agregar(OpSCU(doc.nuevo_id(), "D", origen=rvert, eje_x={"tipo": "eje", "id": "Y"}, eje_y={"tipo": "eje", "id": "Z"}, dx="1 mm"))
    receta = doc.a_dict()
    nuevas = set(OpPlano.PARAMS) - {"tipo", "base", "marco", "distancia", "refs", "angulo", "posicion", "desfase"}
    nuevas |= set(OpEje.PARAMS) - {"tipo", "refs"}
    nuevas |= {"eje_z"}
    for o in receta["operaciones"]:
        if o["tipo"] in ("plano", "eje", "scu"):
            for k in nuevas:
                o["params"].pop(k, None)
    e = Documento.desde_dict(receta).estado_final
    assert e.planos["op2"].origen == pytest.approx((0, 0, 7)) and e.planos["op2"].normal == pytest.approx((0, 0, 1))
    pl = e.planos["op3"]
    assert abs(float((pl.origen - np.array((-10, -10, 10))) @ pl.normal)) == pytest.approx(2)
    assert abs(float(pl.normal[2])) < 1e-12
    assert e.ejes["op4"][0] == pytest.approx((-10, -10, 10)) and e.ejes["op4"][1] == pytest.approx((0, 0, 1))
    assert e.puntos["op5_o"][0] == pytest.approx((-10, -9, 10))
    assert e.ejes["op5_x"][1] == pytest.approx((0, 1, 0)) and e.ejes["op5_y"][1] == pytest.approx((0, 0, 1))


def test_desfase_al_objeto_sigue_al_punto():
    s = api.Sesion()
    curva, punto = boceto_linea(s)
    bid = curva["sketch"]
    llamar(s, "edit_feature", feature=bid, params={"desplazamiento": "4"})
    r = llamar(s, "create_construction_plane", plane="XY", extent="to_object", object=punto)
    assert r["origin"] == pytest.approx((0, 0, 4))
    llamar(s, "edit_feature", feature=bid, params={"desplazamiento": "9"})
    assert s.doc.estado_final.planos[r["plane"]["id"]].origen == pytest.approx((0, 0, 9))
    falla(s, "create_construction_plane", "INVALID_ARGUMENTS", plane="XY", extent="to_object")
    falla(s, "create_construction_plane", "INVALID_ARGUMENTS", plane="XY", extent="absolute")


@pytest.mark.parametrize("args,z", [
    ({"plane": "XY", "offset": 5, "extra_offset": 2}, 7),
    ({"type": "three_points", "references": [[-10, -10, 10], [10, -10, 10], [10, 10, 10]], "extra_offset": 3}, 13),
    ({"type": "two_edges", "references": ["edges:|X and >Z and >Y", "edges:|X and >Z and <Y"], "extra_offset": 1}, 9),
])
def test_desfase_extra_corre_el_plano_y_queda_en_el_paso(args, z):
    s = api.Sesion()
    caja(s)
    r = llamar(s, "create_construction_plane", **args)
    assert abs(r["origin"][2]) == pytest.approx(z)
    assert float(s.doc.operacion(r["plane"]["id"]).p["desfase"]) == args["extra_offset"]


def test_desfase_extra_no_va_en_medio_ni_perpendicular():
    s = api.Sesion()
    caja(s)
    for args in ({"type": "middle", "references": ["XY", ">Z"]}, {"type": "perpendicular", "references": [">Z"]}):
        falla(s, "create_construction_plane", "INVALID_ARGUMENTS", extra_offset=2, **args)


def test_redimensionar_y_tipo_de_extension():
    s = api.Sesion()
    caja(s)
    tres = {"type": "three_points", "references": [[-10, -10, 10], [10, -10, 10], [10, 10, 10]]}
    d = llamar(s, "create_construction_plane", **tres)["display"]
    assert d["redimensionar"] == "predeterminado" and d["limites"][2] - d["limites"][0] > 20
    assert llamar(s, "create_construction_plane", resize="extended", **tres)["display"]["redimensionar"] == "extendido"
    d = llamar(s, "create_construction_plane", size=50, **tres)["display"]
    assert d["limites"][2] - d["limites"][0] == pytest.approx(50) and d["limites"][3] - d["limites"][1] == pytest.approx(50)
    d = llamar(s, "create_construction_axis", type="arista", references=["edges:|Z and >X and >Y"], size=40)["display"]
    assert d["limites"][1] - d["limites"][0] == pytest.approx(40)
    d = llamar(s, "create_construction_axis", type="dos_planos", references=["XZ", "YZ"], size_type="to_object", size_object=[10, 10, 10])["display"]
    assert abs(d["limites"][1] - d["limites"][0]) == pytest.approx(10)      # del punto del eje hasta el objeto, sin margen
    falla(s, "create_construction_plane", "INVALID_ARGUMENTS", size_type="to_object", **tres)


def test_plano_perpendicular_cara_plana_u_v_y_lugar():
    s = api.Sesion()
    caja(s)
    u = llamar(s, "create_construction_plane", type="perpendicular", references=[">Z"], location=[3, 4, 10])
    v = llamar(s, "create_construction_plane", type="perpendicular", references=[">Z"], location=[3, 4, 10], direction="V", distance=2)
    nu, nv = np.array(u["normal"]), np.array(v["normal"])
    assert nu @ nv == pytest.approx(0) and nu[2] == pytest.approx(0) and nv[2] == pytest.approx(0)
    assert float((np.array((3, 4, 10)) - np.array(u["origin"])) @ nu) == pytest.approx(0, abs=1e-9)
    assert float((np.array(v["origin"]) - np.array((3, 4, 10))) @ nv) == pytest.approx(2)


def test_plano_perpendicular_sin_lugar_va_al_centro_y_acepta_plano_de_construccion():
    s = api.Sesion()
    caja(s)
    r = llamar(s, "create_construction_plane", type="perpendicular", references=[">Z"])
    assert float((np.array((0, 0, 10)) - np.array(r["origin"])) @ np.array(r["normal"])) == pytest.approx(0, abs=1e-9)
    r = llamar(s, "create_construction_plane", type="perpendicular", references=["XY"], location=[5, 6, 0])
    assert r["normal"][2] == pytest.approx(0) and float((np.array((5, 6, 0)) - np.array(r["origin"])) @ np.array(r["normal"])) == pytest.approx(0, abs=1e-9)


def test_plano_perpendicular_cara_curva_sigue_la_normal_en_el_lugar():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=30)
    lugar = [10 * math.cos(1.0), 10 * math.sin(1.0), 12]
    r = llamar(s, "create_construction_plane", type="perpendicular", references=["%CYLINDER"], location=lugar)
    o, n = np.array(r["origin"]), np.array(r["normal"])
    assert o == pytest.approx(lugar, abs=1e-4)
    assert float(n @ np.array((math.cos(1.0), math.sin(1.0), 0))) == pytest.approx(0, abs=1e-4)     # contiene la normal de la cara


def test_plano_perpendicular_objeto_de_referencia():
    s = api.Sesion()
    caja(s)
    r = llamar(s, "create_construction_plane", type="perpendicular", references=[">Z", "YZ"])            # plano: pasa por el corte
    assert r["normal"] == pytest.approx((1, 0, 0)) or r["normal"] == pytest.approx((-1, 0, 0))
    assert r["origin"][0] == pytest.approx(0)
    r = llamar(s, "create_construction_plane", type="perpendicular", references=[">Z", [10, 10, 10]])    # punto: pasa por él
    assert float((np.array((10, 10, 10)) - np.array(r["origin"])) @ np.array(r["normal"])) == pytest.approx(0, abs=1e-9)
    llamar(s, "create_cylinder", radius=3, height=30, x=40)
    falla(s, "create_construction_plane", "OPERATION_FAILED", type="perpendicular", references=["%CYLINDER", "YZ"], body="Cuerpo2")


def test_eje_perpendicular_lugar_tocado():
    s = api.Sesion()
    caja(s)
    r = llamar(s, "create_construction_axis", type="perpendicular_cara", references=[">Z"], location=[3, 4, 10])
    assert r["origin"] == pytest.approx((3, 4, 10)) and r["direction"] == pytest.approx((0, 0, 1))
    r = llamar(s, "create_construction_axis", type="perpendicular_cara", references=[">Z"])
    assert r["origin"] == pytest.approx((0, 0, 10))


def _cadena(s):
    bid = llamar(s, "create_sketch")["sketch"]["id"]
    llamar(s, "draw_line", sketch=bid, start_x=0, start_y=0, end_x=20, end_y=0)
    llamar(s, "draw_line", sketch=bid, start_x=20, start_y=0, end_x=40, end_y=0)
    llamar(s, "draw_line", sketch=bid, start_x=40, start_y=0, end_x=40, end_y=30)
    return [{"sketch": bid, "curve": c} for c in s.doc.estado_final.bocetos[bid].boceto.curvas], bid


def test_plano_en_ruta_tipos_de_distancia():
    s = api.Sesion()
    curvas, bid = _cadena(s)
    uno = curvas[0]
    assert llamar(s, "create_construction_plane", type="path", references=[uno], position=0.25)["origin"] == pytest.approx((10, 0, 0))
    assert llamar(s, "create_construction_plane", type="path", references=[uno], extent="absolute", distance=30)["origin"] == pytest.approx((30, 0, 0))
    r = llamar(s, "create_construction_plane", type="path", references=[uno], extent="to_object", object="O", extra_offset=3, tangent_chain=False)
    assert r["origin"] == pytest.approx((3, 0, 0)) and r["normal"] == pytest.approx((1, 0, 0))
    assert llamar(s, "create_construction_plane", type="path", references=[uno], position=0.25, tangent_chain=False)["origin"] == pytest.approx((5, 0, 0))
    r = llamar(s, "create_construction_plane", type="path", references=curvas[:3], extent="absolute", distance=50, tangent_chain=False)
    assert r["origin"] == pytest.approx((40, 10, 0)) and r["normal"] == pytest.approx((0, 1, 0))
    r = llamar(s, "create_construction_plane", type="path", references=curvas[:3], extent="absolute", distance=80, tangent_chain=False)
    assert r["origin"] == pytest.approx((40, 40, 0))                     # pasó del final: sigue por la normal del último tramo


def test_extra_offset_cuenta_en_una_ruta_que_es_un_eje():
    r = llamar(api.Sesion(), "create_construction_plane", type="path", references=["Z"], distance=5, extra_offset=3)
    assert r["origin"][2] == pytest.approx(8)


def test_object_sin_al_objeto_no_se_ignora_callado():
    r = api.llamar(api.Sesion(), "create_construction_plane", {"type": "offset", "base": "XY", "offset": 5, "object": [1, 2, 3]})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r


@pytest.mark.parametrize("datos", [{"modo": "en_arista"}, {"modo": "lugar_plano"}, {"modo": "lugar_plano", "uv": "x"},
                                   {"modo": "lugar_plano", "uv": [1]}, {"modo": "tangencial"}, {"modo": "otro"}])
def test_punto_de_forzado_mal_formado_es_error_de_argumentos(datos):
    ref = {"tipo": "forzado", "base": {"tipo": "plano", "id": "XY"}, **datos}
    r = api.llamar(api.Sesion(), "create_construction_point", {"type": "vertice", "references": [ref]})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r


def test_plano_en_ruta_sobre_un_eje():
    s = api.Sesion()
    r = llamar(s, "create_construction_plane", type="path", references=["X"], distance=12)
    assert r["origin"] == pytest.approx((12, 0, 0)) and r["normal"] == pytest.approx((1, 0, 0))
    caja(s)
    r = llamar(s, "create_construction_plane", type="path", references=["Y"], object=[10, 10, 10], distance=-2)
    assert r["origin"] == pytest.approx((0, 8, 0))


def test_cadena_tangente_en_aristas_de_un_cuerpo():
    s = api.Sesion()
    cid = caja(s)
    llamar(s, "fillet", body=cid, edges="edges:|Z and >X and >Y", radius=3)
    r = llamar(s, "create_construction_plane", type="path", references=["edges:|X and >Z and >Y"], extent="absolute", distance=0, body=cid)
    d = api.llamar(s, "create_construction_plane", {"type": "path", "references": ["edges:|X and >Z and >Y"], "position": 1.0, "body": cid})
    assert d["ok"]
    largo_recta = 17.0
    assert s.doc.operacion(d["result"]["plane"]["id"]).p["cadena_tangente"] is True
    extremos = {tuple(np.round(x, 3)) for x in (r["origin"], d["result"]["origin"])}
    assert len(extremos) == 2 and max(abs(a - b) for a, b in zip(r["origin"], d["result"]["origin"], strict=True)) > largo_recta


def test_punto_en_ruta_fisico_y_cadena():
    s = api.Sesion()
    curvas, _ = _cadena(s)
    assert llamar(s, "create_construction_point", type="ruta", references=[curvas[0]], extent="physical", distance=25)["position"] == pytest.approx((25, 0, 0))
    assert llamar(s, "create_construction_point", type="ruta", references=[curvas[0]], position=0.75)["position"] == pytest.approx((30, 0, 0))
    assert llamar(s, "create_construction_point", type="ruta", references=[curvas[0]], position=0.75, tangent_chain=False)["position"] == pytest.approx((15, 0, 0))


def _snap(s, entidad, kind, **k):
    return next(p for p in llamar(s, "find_snap_points", entity=entidad, **k)["snap_points"] if p["kind"] == kind)


def test_puntos_de_forzado_cara_arista_y_lugar():
    s = api.Sesion()
    caja(s)
    c = _snap(s, ">Z", "centro_cara")
    assert c["position"] == pytest.approx((0, 0, 10))
    assert llamar(s, "create_construction_point", type="vertice", references=[c["ref"]])["position"] == pytest.approx((0, 0, 10))
    a = _snap(s, "edges:|X and >Z and >Y", "centro_arista")
    assert a["position"] == pytest.approx((0, 10, 10))
    assert llamar(s, "create_construction_point", type="vertice", references=[a["ref"]])["position"] == pytest.approx((0, 10, 10))
    e = _snap(s, "edges:|X and >Z and >Y", "en_arista", location=[-5, 10, 10])
    assert e["position"] == pytest.approx((-5, 10, 10), abs=1e-5)
    lugar = _snap(s, ">Z", "lugar_cara", location=[3, 4, 10])
    assert lugar["position"] == pytest.approx((3, 4, 10))
    assert llamar(s, "create_construction_axis", type="dos_puntos", references=[c["ref"], lugar["ref"]])["direction"] == pytest.approx((0.6, 0.8, 0))
    assert llamar(s, "create_construction_plane", type="three_points", references=[c["ref"], a["ref"], lugar["ref"]])["normal"][2] ** 2 == pytest.approx(1)
    assert llamar(s, "create_construction_axis", type="perpendicular_cara", references=[">Z", lugar["ref"]])["origin"] == pytest.approx((3, 4, 10))
    assert llamar(s, "create_ucs", origin=c["ref"])["origin"] == pytest.approx((0, 0, 10))


def test_puntos_tangenciales_de_caras_curvas():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=30)
    puntos = [p["position"] for p in llamar(s, "find_snap_points", entity="%CYLINDER")["snap_points"] if p["kind"] == "tangencial"]
    assert sorted(map(tuple, np.round(puntos, 6).tolist())) == sorted(
        [(10, 0, 15), (-10, 0, 15), (0, 10, 15), (0, -10, 15)])
    s = api.Sesion()
    llamar(s, "create_sphere", radius=5)
    puntos = [p["position"] for p in llamar(s, "find_snap_points", entity="%SPHERE")["snap_points"] if p["kind"] == "tangencial"]
    assert len(puntos) == 6 and all(np.linalg.norm(p) == pytest.approx(5) for p in puntos)
    assert (0, 0, 5) in [tuple(np.round(p, 6) + 0.0) for p in puntos]


def test_punto_de_forzado_sigue_a_la_cara_al_cambiar_una_medida():
    s = api.Sesion()
    llamar(s, "create_parameter", name="alto", expression="10 mm")
    op = llamar(s, "create_box", length=20, width=20, height="alto")["feature"]["id"]
    c = _snap(s, ">Z", "centro_cara")["ref"]
    p = llamar(s, "create_construction_point", type="vertice", references=[c])["point"]["id"]
    assert op in s.doc.operacion(p).dependencias()
    llamar(s, "set_parameter", name="alto", expression="25 mm")
    assert s.doc.estado_final.puntos[p][0] == pytest.approx((0, 0, 25))


def test_scu_alineacion_de_z_y_x():
    s = api.Sesion()
    caja(s)
    r = llamar(s, "create_ucs", origin="O", z_axis="X")
    assert r["axes"]["z"]["direction"] == pytest.approx((1, 0, 0))
    r = llamar(s, "create_ucs", origin="O", z_axis=">Z", x_axis="Y")
    assert r["axes"]["z"]["direction"] == pytest.approx((0, 0, 1)) and r["axes"]["x"]["direction"] == pytest.approx((0, 1, 0))
    assert r["axes"]["y"]["direction"] == pytest.approx((-1, 0, 0))
    r = llamar(s, "create_ucs", origin="O")
    assert r["axes"]["x"]["direction"] == pytest.approx((1, 0, 0)) and r["axes"]["z"]["direction"] == pytest.approx((0, 0, 1))


def test_nombres_de_planos_en_visibilidad_de_objetos():
    s = api.Sesion()
    r = llamar(s, "set_object_visibility")["visibility"]
    assert r["nombres_planos_construccion"] is True and r["nombres_planos_origen"] is True
    r = llamar(s, "set_object_visibility", types=["nombres_planos_origen"], visible=False)["visibility"]
    assert r["nombres_planos_origen"] is False and r["planos_origen"] is True
