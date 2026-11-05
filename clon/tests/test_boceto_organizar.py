# -*- coding: utf-8 -*-
"""Organización del boceto: categorías, grupos, visible / bloqueado / en perfiles, aislar y eliminar."""
import numpy as np
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo.perfiles import detectar_boceto
from omnicad.restricciones import objetos as ob
from omnicad.restricciones.boceto import Boceto, ErrorBoceto

PLANO = geo.Plano("XY")


def _escena():
    """Rectángulo suelto, un «SVG» (objeto importado), un círculo hecho objeto y un texto."""
    b = Boceto()
    sueltas = b.agregar_rectangulo((0, 0), (40, 20))
    svg = ob.crear(b, b.agregar_rectangulo((60, 0), (80, 20)), "logo.svg")
    b.objetos[svg]["tipo_origen"] = "SVG"
    circulo = ob.crear(b, [b.agregar_circulo((100, 10), 5)], "Disco")
    tid = b.agregar_texto((0, 40), "HOLA", altura=10)
    texto = next(i for i, o in b.objetos.items() if o.get("texto_automatico") == tid)
    return b, sueltas, svg, circulo, texto, tid


def test_categorias_salen_del_dato_y_un_grupo_no_cambia_la_de_sus_miembros():
    b, sueltas, svg, circulo, texto, _tid = _escena()
    u = ob.unidades(b)
    assert u == {"geometrias": [circulo], "textos": [texto], "vectores": [svg], "grupos": []}
    assert ob.geometria_suelta(b) == sueltas
    assert ob.nombre_curva(b, sueltas[0]) == f"Línea {sueltas[0]}"
    grupo = ob.crear(b, [svg, texto], "Composición1")
    u = ob.unidades(b)
    assert u["grupos"] == [grupo] and u["vectores"] == [svg] and u["textos"] == [texto]


def test_participar_en_perfiles_es_independiente_de_ver_y_bloquear():
    b, _s, svg, circulo, _t, _tid = _escena()
    areas = lambda: sorted(round(p.area, 6) for p in detectar_boceto(b, PLANO) if p.area > 50)  # noqa: E731
    todas = areas()
    assert round(np.pi * 25, 6) in todas
    b.objetos[circulo]["visible"] = False
    b.objetos[circulo]["bloqueado"] = True
    assert areas() == todas                         # oculto y bloqueado siguen formando perfiles
    b.objetos[circulo]["perfiles"] = False
    assert round(np.pi * 25, 6) not in areas()
    assert b.objetos[circulo]["visible"] is False and b.objetos[circulo]["bloqueado"] is True
    grupo = ob.crear(b, [svg], "G")
    b.objetos[grupo]["perfiles"] = False            # lo hereda el contenido
    assert 400.0 not in areas()


def test_aislar_y_restaurar_vuelven_exactamente_a_la_visibilidad_anterior():
    b, sueltas, svg, circulo, texto, _tid = _escena()
    b.objetos[circulo]["visible"] = False           # ya estaba oculto: tiene que seguir oculto
    ob.aislar(b, [texto])
    assert ob.aislamiento_activo(b)
    assert not b.objetos[svg]["visible"] and b.objetos[texto]["visible"]
    assert not set(sueltas) & ob.curvas_visibles(b)  # la geometría suelta también se va
    ob.restaurar_aislamiento(b)
    assert b.objetos[svg]["visible"] and not b.objetos[circulo]["visible"]
    assert set(sueltas) <= ob.curvas_visibles(b) and not ob.aislamiento_activo(b)
    grupo = ob.crear(b, [svg, texto], "G")
    ob.aislar(b, [texto])                           # dentro de un grupo: el grupo queda, el hermano se oculta
    assert b.objetos[grupo]["visible"] and not b.objetos[svg]["visible"]
    b2 = Boceto.desde_dict(b.a_dict())              # persiste: se restaura también tras reabrir
    ob.restaurar_aislamiento(b2)
    assert b2.objetos[svg]["visible"] and not b2.objetos[circulo]["visible"]
    with pytest.raises(ErrorBoceto):
        ob.aislar(b, [99999])


def test_mover_a_grupo_conserva_la_posicion_en_pantalla():
    b, _s, svg, circulo, texto, _tid = _escena()
    grupo = ob.crear(b, [svg, texto], "G")
    ob.transformar(b, [grupo], ob.afin(5, 3, 30, sx=2, sy=2))
    antes = ob.caja(b, [circulo])
    ob.mover_a_grupo(b, [circulo], grupo)
    assert circulo in b.objetos[grupo]["entidades"]
    assert ob.caja(b, [circulo]) == pytest.approx(antes)
    caja_svg = ob.caja(b, [svg])
    ob.mover_a_grupo(b, [svg], None)                 # sacar a la raíz
    assert svg in ob.raices(b) and ob.caja(b, [svg]) == pytest.approx(caja_svg)
    with pytest.raises(ErrorBoceto, match="dentro de sí mismo"):
        ob.mover_a_grupo(b, [grupo], grupo)
    otro = ob.crear(b, [svg], "Otro")
    ob.mover_a_grupo(b, [otro], grupo)
    with pytest.raises(ErrorBoceto, match="dentro de sí mismo"):
        ob.mover_a_grupo(b, [grupo], otro)
    ob.mover_a_grupo(b, [circulo, texto, otro], None)
    assert grupo not in b.objetos                    # el grupo vacío desaparece


def test_no_se_saca_una_pieza_interna_de_un_svg():
    b = Boceto()
    hoja = ob.crear(b, b.agregar_rectangulo((0, 0), (5, 5)), "forma")
    raiz = ob.crear(b, [hoja], "logo.svg")
    b.objetos[raiz]["tipo_origen"] = "SVG"
    with pytest.raises(ErrorBoceto, match="parte de un SVG"):
        ob.mover_a_grupo(b, [hoja], None)


def test_eliminar_contenedor_o_contenido():
    b, _s, svg, circulo, texto, tid = _escena()
    grupo = ob.crear(b, [svg, circulo], "G")
    ob.eliminar(b, [grupo], contenido=False)
    assert grupo not in b.objetos and {svg, circulo} <= set(ob.raices(b))
    curvas_svg = ob.curvas(b, [svg])
    with pytest.raises(ErrorBoceto, match="grupo personalizado"):
        ob.eliminar(b, [svg], contenido=False)
    ob.eliminar(b, [svg, texto])
    assert svg not in b.objetos and texto not in b.objetos and tid not in b.curvas
    assert not set(curvas_svg) & set(b.curvas)
    b.objetos[circulo]["bloqueado"] = True
    with pytest.raises(ErrorBoceto, match="Desbloque"):
        ob.eliminar(b, [circulo])


def test_eliminar_con_contenido_frena_si_un_hijo_del_grupo_esta_bloqueado():
    b, _s, svg, circulo, _texto, _tid = _escena()
    grupo = ob.crear(b, [svg, circulo], "G")
    b.objetos[circulo]["bloqueado"] = True
    with pytest.raises(ErrorBoceto, match="bloqueado dentro"):
        ob.eliminar(b, [grupo])
    assert {grupo, svg, circulo} <= set(b.objetos)         # no se borró nada


def test_texto_convertido_sigue_en_textos():
    b = Boceto()
    tid = b.agregar_texto((0, 0), "AB", altura=10)
    b.desglosar_texto(tid)
    assert len(ob.unidades(b)["textos"]) == 1 and not ob.unidades(b)["geometrias"]


def test_proyecto_viejo_sin_las_claves_nuevas_no_cambia():
    b, *_ = _escena()
    d = b.a_dict()
    for o in d["objetos"]:
        assert "perfiles" not in o and "aislado" not in o
    b2 = Boceto.desde_dict(d)
    assert sorted(p.area for p in detectar_boceto(b2, PLANO)) == pytest.approx(
        sorted(p.area for p in detectar_boceto(b, PLANO)))


# ------------------------------------------------------------------ API, MCP y CLI (la misma lógica)
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="20mm" height="10mm" viewBox="0 0 20 10">'
       '<rect x="0" y="0" width="8" height="8"/><circle cx="15" cy="5" r="3"/></svg>')


def _llamar(s, nombre, **args):
    from omnicad import api
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def sesion(tmp_path):
    from omnicad import api
    s = api.Sesion()
    ruta = tmp_path / "logo.svg"
    ruta.write_text(SVG, encoding="utf-8")
    sk = _llamar(s, "insert_svg", path=str(ruta), plane="XY")["sketch"]["id"]
    _llamar(s, "draw_rectangle", x1=-40, y1=0, x2=-20, y2=10, sketch=sk)
    _llamar(s, "draw_circle", radius=4, center_x=-60, sketch=sk)
    _llamar(s, "add_text", text="HOLA", x=0, y=30, height=8, sketch=sk)
    return s, sk


def _ids(s, sk):
    org = _llamar(s, "get_sketch_organization", sketch=sk)
    return {c: [o["id"] for o in v["objects"]] for c, v in org["categories"].items()}, org


def _perfiles(s, sk):
    return len(s.doc.estado_final.bocetos[sk].perfiles)


def test_api_organizacion_flags_aislar_grupo_y_eliminar(sesion):
    s, sk = sesion
    ids, org = _ids(s, sk)
    assert len(ids["vectores"]) == 1 and len(ids["textos"]) == 1 and ids["grupos"] == []
    geo_cat = org["categories"]["geometrias"]
    assert geo_cat["count"] == 5 and {c["type"] for c in geo_cat["curves"]} == {"linea", "circulo"}
    svg, texto = ids["vectores"][0], ids["textos"][0]
    total = _perfiles(s, sk)
    _llamar(s, "set_vector_object", object=svg, in_profiles=False, visible=False)
    assert _perfiles(s, sk) < total
    info = next(o for o in _llamar(s, "get_vector_objects", sketch=sk)["objects"] if o["id"] == svg)
    assert info["in_profiles"] is False and info["visible"] is False and info["locked"] is False
    _llamar(s, "undo")
    assert _perfiles(s, sk) == total                  # un solo paso de deshacer para los dos cambios
    grupo = _llamar(s, "group_vector_objects", objects=[svg, texto], name="Composición1", sketch=sk)["object_id"]
    ids, _ = _ids(s, sk)
    assert ids["grupos"] == [grupo] and ids["vectores"] == [svg] and ids["textos"] == [texto]
    caja = _llamar(s, "get_vector_objects", sketch=sk)
    antes = next(o for o in caja["objects"] if o["id"] == texto)
    _llamar(s, "transform_vector_objects", objects=[texto], dx=5, sketch=sk)   # miembro de un grupo
    despues = next(o for o in _llamar(s, "get_vector_objects", sketch=sk)["objects"] if o["id"] == texto)
    assert despues["position"][0] == pytest.approx(antes["position"][0] + 5)
    _llamar(s, "isolate_vector_objects", objects=[texto], sketch=sk)
    b = s.doc.estado_final.bocetos[sk].boceto
    assert not b.objetos[svg]["visible"] and _llamar(s, "get_sketch_organization", sketch=sk)["isolation_active"]
    _llamar(s, "isolate_vector_objects", sketch=sk)
    assert s.doc.estado_final.bocetos[sk].boceto.objetos[svg]["visible"]
    _llamar(s, "move_vector_objects_to_group", objects=[texto], sketch=sk)
    _llamar(s, "delete_vector_objects", objects=[grupo], keep_contents=True, sketch=sk)
    ids, _ = _ids(s, sk)
    assert ids["grupos"] == [] and ids["vectores"] == [svg] and ids["textos"] == [texto]
    _llamar(s, "delete_vector_objects", objects=[svg], sketch=sk)
    assert _llamar(s, "get_sketch_organization", sketch=sk)["categories"]["vectores"]["count"] == 0
    _llamar(s, "undo")
    assert _llamar(s, "get_sketch_organization", sketch=sk)["categories"]["vectores"]["count"] == 1


def test_api_reflejar_y_errores(sesion):
    from omnicad import api
    s, sk = sesion
    ids, _ = _ids(s, sk)
    svg = ids["vectores"][0]
    antes = next(o for o in _llamar(s, "get_vector_objects", sketch=sk)["objects"] if o["id"] == svg)
    _llamar(s, "transform_vector_objects", objects=[svg], scale_x=-1, scale_y=1, sketch=sk)
    despues = next(o for o in _llamar(s, "get_vector_objects", sketch=sk)["objects"] if o["id"] == svg)
    assert despues["position"] == pytest.approx(antes["position"]) and despues["width"] == pytest.approx(antes["width"])
    assert _perfiles(s, sk) >= 3                      # reflejado sigue formando sus perfiles
    interna = next(i for i in s.doc.estado_final.bocetos[sk].boceto.objetos[svg]["entidades"]
                   if i in s.doc.estado_final.bocetos[sk].boceto.objetos)
    for nombre, args, kind in (
            ("transform_vector_objects", {"objects": [interna], "dx": 1}, "INVALID_ARGUMENTS"),
            ("move_vector_objects_to_group", {"objects": [interna]}, None),
            ("isolate_vector_objects", {"objects": [123456]}, "ENTITY_NOT_FOUND"),
            ("delete_vector_objects", {"objects": [svg], "keep_contents": True}, None),
            ("set_vector_object", {"object": svg, "name": "  "}, "INVALID_ARGUMENTS")):
        r = api.llamar(s, nombre, {**args, "sketch": sk})
        assert not r["ok"] and r["mensaje"], (nombre, r)
        if kind:
            assert r["error_kind"] == kind, r


def test_cli_misma_logica_y_persistencia(tmp_path, capsys):
    import json

    from omnicad.cli import main
    ruta, svg = tmp_path / "p.omnicad", tmp_path / "logo.svg"
    svg.write_text(SVG, encoding="utf-8")
    assert main(["new", str(ruta)]) == 0
    assert main(["call", "insert_svg", "--doc", str(ruta), f"path={svg}", "plane=XY"]) == 0
    capsys.readouterr()
    assert main(["call", "get_sketch_organization", "--doc", str(ruta), "--json"]) == 0
    org = json.loads(capsys.readouterr().out)
    oid = org["result"]["categories"]["vectores"]["objects"][0]["id"]
    assert main(["call", "set_vector_object", "--doc", str(ruta), "--args",
                 json.dumps({"object": oid, "in_profiles": False, "locked": True, "name": "Logo"})]) == 0
    capsys.readouterr()
    assert main(["call", "get_sketch_organization", "--doc", str(ruta), "--json"]) == 0
    fila = json.loads(capsys.readouterr().out)["result"]["categories"]["vectores"]["objects"][0]
    assert (fila["name"], fila["in_profiles"], fila["locked"], fila["visible"]) == ("Logo", False, True, True)


def test_vaciar_un_grupo_anidado_lo_quita_tambien_de_su_padre():
    """Revisión: sacar el único objeto de G2 (dentro de G1) fallaba con «contiene un elemento inexistente»."""
    b = Boceto()
    a = ob.crear(b, [b.agregar_circulo((0, 0), 3)], "A")
    c = ob.crear(b, [b.agregar_circulo((9, 0), 3)], "C")
    g2 = ob.crear(b, [a], "G2")
    g1 = ob.crear(b, [g2, c], "G1")
    ob.mover_a_grupo(b, [a], None)
    assert g2 not in b.objetos and b.objetos[g1]["entidades"] == [c] and a in ob.raices(b)


def test_borrar_lo_aislado_deja_restaurar_el_resto():
    """Revisión: el resto quedaba oculto para siempre y «Restaurar aislamiento» se apagaba."""
    b = Boceto()
    a = ob.crear(b, [b.agregar_circulo((0, 0), 3)], "A")
    c = ob.crear(b, [b.agregar_circulo((9, 0), 3)], "C")
    ob.aislar(b, [a])
    ob.eliminar(b, [a])
    assert ob.aislamiento_activo(b)
    ob.restaurar_aislamiento(b)
    assert b.objetos[c]["visible"] and not ob.aislamiento_activo(b)
