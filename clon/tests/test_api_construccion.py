"""Construcción y referencias embebidas por la API pública, sin Qt."""
import math

import pytest
from PIL import Image

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs


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
