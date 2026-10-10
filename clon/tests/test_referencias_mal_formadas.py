# -*- coding: utf-8 -*-
"""Parámetros mal formados en un paso del timeline (prueba de uso del 2026-10-09, PROJECT_LOG «Hallazgos»):
una referencia que es texto, [None] o un dict sin sus claves, o una lista que llega como texto o None, tiene
que dar un error que nombre el campo (INVALID_ARGUMENTS), nunca «Error inesperado». Y los campos de cuerpos
aceptan las dos formas: el id («op1.c1») o la referencia {"tipo": "cuerpo", "cuerpo": "op1.c1"}."""
import json

import pytest

from omnicad import api
from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.nucleo import geometria as geo
from omnicad.timeline import entidades as ent
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import ErrorOperacion, EstadoModelo, operacion_desde_dict


def _ref(cid):
    return {"tipo": "cuerpo", "cuerpo": cid}


@pytest.fixture
def s():
    """Dos cajas de 20 mm: op1.c1 en el origen y op2.c1 corrida 30 mm en X (no se tocan)."""
    sesion = api.Sesion(Documento())
    for params in ({"forma": "caja"}, {"forma": "caja", "x": "30 mm"}):
        assert api.llamar(sesion, "run_operation", {"type": "primitiva", "params": params})["ok"]
    return sesion


def _correr(s, tipo, params):
    return api.llamar(s, "run_operation", {"type": tipo, "params": params})


def _ok(r):
    assert r["ok"], r
    assert r["result"]["status"] in ("ok", "aviso"), r
    return r["result"]


def _receta(s):
    return json.dumps(s.doc.a_dict(), sort_keys=True)


# ---------------------------------------------------------------- valores malos → campo nombrado
MALOS = [
    ("chaflan", {"aristas": "basura"}, "aristas"),
    ("chaflan", {"aristas": [None]}, "aristas[0]"),
    ("chaflan", {"aristas": ["op1.c1"]}, "aristas[0]"),
    ("chaflan", {"aristas": [{"tipo": "cara"}]}, "aristas[0]"),
    ("empalme", {"aristas": [{"tipo": "arista", "cuerpo": "op1.c1"}]}, "aristas[0]"),
    ("mover", {"cuerpos": ["op1.c1"], "pivote": "origen"}, "pivote"),
    ("mover", {"cuerpos": ["op1.c1"], "pivote": {"tipo": "cuerpo", "id": "op1.c1"}}, "pivote"),
    ("escala", {"cuerpos": ["op1.c1"], "punto": [None]}, "punto"),
    ("simetria", {"cuerpos": ["op1.c1"], "plano": {"tipo": "plano"}}, "plano"),
    ("combinar", {"objetivo": [None], "herramientas": ["op2.c1"]}, "objetivo"),
    ("combinar", {"objetivo": "op1.c1", "herramientas": [None]}, "herramientas[0]"),
    ("coser", {"cuerpos": None}, "cuerpos"),
    ("descoser", {"cuerpos": None}, "cuerpos"),
    ("coser", {"cuerpos": [{"tipo": "cara", "cuerpo": "op1.c1", "firma": {"geom": "plano"}}]}, "cuerpos[0]"),
    ("quitar", {"cuerpos": [{"cuerpo": "op1.c1"}]}, "cuerpos[0]"),
    ("extrusion", {"boceto": ["x"], "perfiles": [{"firma": []}]}, "boceto"),
    ("convertir_chapa", {"cara": "basura"}, "cara"),
    ("convertir_chapa", {"ajustes": "basura"}, "ajustes"),
    ("plano", {"refs": ["basura"]}, "refs[0]"),
    ("plano", {"base": {"tipo": "plano", "id": "XY"}}, "base"),
]


# Referencias con «tipo», «cuerpo» y «firma.geom», pero sin las claves que lee nucleo/referencias._distancia
# (revisión del 2026-10-10: daban «Error inesperado: 'medio'» / 'centro' / 'punto').
ARISTA_SIN_MEDIO = {"tipo": "arista", "cuerpo": "op1.c1", "firma": {"geom": "linea"}}
CARA_SIN_CENTRO = {"tipo": "cara", "cuerpo": "op1.c1", "firma": {"geom": "plano"}}
CARA_CENTRO_TEXTO = {"tipo": "cara", "cuerpo": "op1.c1", "firma": {"geom": "plano", "centro": "x", "area": 1}}
CARA_NORMAL_MALA = {"tipo": "cara", "cuerpo": "op1.c1",
                    "firma": {"geom": "plano", "centro": [0, 0, 20], "area": 400, "normal": [0, 1]}}
VERT_SIN_PUNTO = {"tipo": "vertice", "cuerpo": "op1.c1", "firma": {"geom": "punto"}}
MALOS += [
    ("chaflan", {"aristas": [ARISTA_SIN_MEDIO]}, "aristas[0]"),
    ("empalme", {"aristas": [ARISTA_SIN_MEDIO]}, "aristas[0]"),
    ("desfase_cara", {"caras": [CARA_SIN_CENTRO]}, "caras[0]"),
    ("vaciado", {"caras": [CARA_SIN_CENTRO]}, "caras[0]"),
    ("borrar_caras", {"caras": [CARA_CENTRO_TEXTO]}, "caras[0]"),
    ("borrar_caras", {"caras": [CARA_NORMAL_MALA]}, "caras[0]"),
    ("mover", {"cuerpos": ["op1.c1"], "pivote": VERT_SIN_PUNTO}, "pivote"),
    ("plano", {"tipo": "tres_puntos", "refs": [VERT_SIN_PUNTO]}, "refs[0]"),
]
# Revisión r3 del 2026-10-10: un boceto vacío que no es texto ([] o {}) y una referencia de cuerpo bien formada en
# un campo de caras o aristas (daban «Error inesperado: unhashable type» y un TypeError de OCP).
MALOS += [
    ("extrusion", {"boceto": [], "perfiles": [{"firma": [1]}]}, "boceto"),
    ("extrusion", {"boceto": {}, "perfiles": [{"firma": [1]}]}, "boceto"),
    ("revolucion", {"boceto": [], "perfiles": [{"firma": [1]}]}, "boceto"),
    ("chaflan", {"aristas": [_ref("op1.c1")]}, "aristas[0]"),
    ("empalme", {"aristas": [_ref("op1.c1")]}, "aristas[0]"),
    ("desfase_cara", {"caras": [_ref("op1.c1")]}, "caras[0]"),
    ("vaciado", {"caras": [_ref("op1.c1")]}, "caras[0]"),
    ("borrar_caras", {"caras": [_ref("op1.c1")]}, "caras[0]"),
    ("desmoldeo", {"plano": {"tipo": "plano", "id": "XY"}, "caras": [_ref("op1.c1")]}, "caras[0]"),
    ("destrimar", {"caras": [_ref("op1.c1")]}, "caras[0]"),
    ("extender_sup", {"aristas": [_ref("op1.c1")]}, "aristas[0]"),
    ("sup_empalme", {"aristas": [_ref("op1.c1")]}, "aristas[0]"),
    # datos guardados en la receta (no son referencias, pero daban el mismo «Error inesperado»)
    ("insertar_malla", {"datos": "basura"}, "datos"),
    ("operacion_base", {"cuerpos": [None]}, "cuerpos[0]"),
    ("operacion_base", {"cuerpos": [_ref("op1.c1")]}, "cuerpos[0]"),
]


@pytest.mark.parametrize("tipo, params, campo", MALOS)
def test_parametro_mal_formado_nombra_el_campo(s, tipo, params, campo):
    antes = _receta(s)
    r = _correr(s, tipo, params)
    assert not r["ok"], r
    assert r["error_kind"] == "INVALID_ARGUMENTS", r
    assert f"«{campo}»" in r["mensaje"], r["mensaje"]
    assert "inesperado" not in r["mensaje"].lower(), r["mensaje"]
    assert _receta(s) == antes


@pytest.mark.parametrize("tipo, params, campo", [
    ("extrusion", {"perfiles": [{"firma": [[1, 2]], "centroide": "x"}]}, "perfiles[0]"),
    ("extrusion", {"perfiles": [{"firma": [1, 2, 3, 4], "centroide": "x"}]}, "perfiles[0]"),
    ("sup_extruir", {"curvas": [{"tipo": "perfil", "firma": [[1]]}]}, "curvas[0]"),
])
def test_perfil_con_firma_mal_formada_nombra_el_campo(s, tipo, params, campo):
    """Con un boceto real (un rectángulo): la firma de un perfil son ids de curva (enteros) y el centroide [u, v]."""
    assert api.llamar(s, "create_sketch", {"plane": "XY"})["ok"]
    assert api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 5, "y2": 5})["ok"]
    boceto = [o.id for o in s.doc.operaciones if o.TIPO == "boceto"][0]
    params = json.loads(json.dumps(params))
    if tipo == "extrusion":
        params["boceto"] = boceto
    else:
        params["curvas"][0]["boceto"] = boceto
    antes = _receta(s)
    r = _correr(s, tipo, params)
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert f"«{campo}»" in r["mensaje"] and "inesperado" not in r["mensaje"].lower(), r["mensaje"]
    assert _receta(s) == antes


def test_las_referencias_reales_pasan_la_validacion(s):
    """Las referencias que arma el programa (con y sin «rel») a caras, aristas y vértices de una caja y un
    cilindro pasan la validación: la revisión de la firma no rechaza nada bien formado."""
    from omnicad.nucleo import referencias as refs
    _ok(_correr(s, "primitiva", {"forma": "cilindro", "x": "80 mm"}))
    n = 0
    for cid, cuerpo in s.doc.estado_final.cuerpos.items():
        for tipo in ("cara", "arista", "vertice"):
            for sub in refs.subformas(cuerpo.forma, tipo):
                ent.validar(refs.referencia(cid, sub, cuerpo.forma))
                ent.validar(json.loads(json.dumps(refs.referencia(cid, sub))))
                n += 1
    assert n == 2 * (6 + 12 + 8) + 3 + 3 + 2, n


def test_el_mensaje_dice_que_llego_y_que_se_esperaba(s):
    r = _correr(s, "mover", {"cuerpos": ["op1.c1"], "pivote": "origen"})
    assert "'origen'" in r["mensaje"], r["mensaje"]
    assert '{"tipo": "punto", "id": "O"}' in r["mensaje"], r["mensaje"]


@pytest.mark.parametrize("tipo, params", [
    ("simetria", {"cuerpos": ["op1.c1"], "plano": {"tipo": "eje", "id": "Z"}}),
    ("mover", {"cuerpos": ["op1.c1"], "tipo": "rotacion", "eje": {"tipo": "punto", "id": "O"}}),
])
def test_referencia_de_otro_tipo_no_es_error_inesperado(s, tipo, params):
    """Bien formada pero del tipo equivocado (un eje donde va un plano): error de la operación, no «inesperado»."""
    antes = _receta(s)
    r = _correr(s, tipo, params)
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED", r
    assert "inesperado" not in r["mensaje"].lower() and "Se esperaba" in r["mensaje"], r["mensaje"]
    assert _receta(s) == antes


def test_previsualizar_tambien_nombra_el_campo(s):
    """Camino de los diálogos de la UI: la vista previa propaga el error con el campo."""
    op = operacion_desde_dict({"tipo": "mover", "id": "op9", "params": {"cuerpos": ["op1.c1"], "pivote": "origen"}})
    with pytest.raises(ErrorOperacion, match="«pivote»"):
        s.doc.previsualizar(op)
    assert op.p["pivote"] == "origen"            # el paso no se toca


# ---------------------------------------------------------------- campos de cuerpos: id o referencia
def test_mover_con_referencia_de_cuerpo(s):
    x0 = geo.caja_envolvente(s.doc.estado_final.cuerpos["op1.c1"].forma)[0][0]
    _ok(_correr(s, "mover", {"cuerpos": [_ref("op1.c1")], "dx": "10 mm"}))
    forma = s.doc.estado_final.cuerpos["op1.c1"].forma
    assert geo.caja_envolvente(forma)[0][0] == pytest.approx(x0 + 10, abs=1e-3)
    assert geo.volumen(forma) == pytest.approx(8000, rel=1e-6) and geo.es_valida(forma)


def test_quitar_con_referencia_de_cuerpo(s):
    _ok(_correr(s, "quitar", {"cuerpos": [_ref("op1.c1")]}))
    assert list(s.doc.estado_final.cuerpos) == ["op2.c1"]


def test_descoser_y_coser_con_referencias(s):
    caras = _ok(_correr(s, "descoser", {"cuerpos": [_ref("op1.c1")]}))["new_bodies"]
    cuerpos = s.doc.estado_final.cuerpos
    assert len(caras) == 6 and "op1.c1" not in cuerpos
    assert all(cuerpos[c].tipo == "superficie" for c in caras)
    _ok(_correr(s, "coser", {"cuerpos": [_ref(c) for c in caras]}))
    cuerpos = s.doc.estado_final.cuerpos
    cosido = cuerpos[caras[0]]
    assert cosido.tipo == "solido" and not any(c in cuerpos for c in caras[1:])
    assert abs(geo.volumen(cosido.forma)) == pytest.approx(8000, rel=1e-6) and geo.es_valida(cosido.forma)


def test_vaciado_de_cuerpo_entero_por_referencia(s):
    _ok(_correr(s, "vaciado", {"cuerpos": [_ref("op1.c1")]}))
    forma = s.doc.estado_final.cuerpos["op1.c1"].forma
    assert geo.volumen(forma) == pytest.approx(20 ** 3 - 18 ** 3, rel=1e-6) and geo.es_valida(forma)


def test_combinar_con_referencias(s):
    _ok(_correr(s, "combinar", {"objetivo": _ref("op1.c1"), "herramientas": [_ref("op2.c1")]}))
    cuerpos = s.doc.estado_final.cuerpos
    assert list(cuerpos) == ["op1.c1"]
    assert geo.volumen(cuerpos["op1.c1"].forma) == pytest.approx(16000, rel=1e-6)


def test_combinar_objetivo_que_tambien_es_herramienta_por_referencia(s):
    r = _correr(s, "combinar", {"objetivo": "op1.c1", "herramientas": [_ref("op1.c1")]})
    assert not r["ok"] and "no puede ser también herramienta" in r["mensaje"], r


def test_teselar_sin_mantener_por_referencia(s):
    nuevos = _ok(_correr(s, "teselar", {"cuerpos": [_ref("op1.c1")], "mantener": False}))["new_bodies"]
    cuerpos = s.doc.estado_final.cuerpos
    assert "op1.c1" not in cuerpos and len(nuevos) == 1 and cuerpos[nuevos[0]].tipo == "malla"


# ---------------------------------------------------------------- dependencias
@pytest.mark.parametrize("tipo, params", [
    ("mover", {"pivote": "basura"}), ("extrusion", {"boceto": ["x"]}), ("chaflan", {"aristas": "basura"}),
    ("combinar", {"objetivo": [None], "herramientas": "op1.c1"}), ("plano", {"base": {"tipo": "plano"}}),
    ("coser", {"cuerpos": 5}), ("primitiva", {"objetivo": [None]}), ("extrusion", {"objetivos": [None, 3]}),
])
def test_dependencias_no_lanzan_con_valores_malos(tipo, params):
    op = operacion_desde_dict({"tipo": tipo, "id": "op9", "params": params})
    assert None not in op.dependencias()


def test_dependencias_con_referencia_de_cuerpo():
    op = operacion_desde_dict({"tipo": "coser", "id": "op9", "params": {"cuerpos": [_ref("op3.c2"), "op4.c1"]}})
    assert op.dependencias() == {"op3", "op4"}
    op = operacion_desde_dict({"tipo": "combinar", "id": "op9",
                               "params": {"objetivo": _ref("op1.c1"), "herramientas": [_ref("op2.c1")]}})
    assert op.dependencias() == {"op1", "op2"}


def test_no_se_elimina_un_paso_usado_por_referencia(s):
    _ok(_correr(s, "mover", {"cuerpos": [_ref("op1.c1")], "dx": "5 mm"}))
    r = api.llamar(s, "delete_feature", {"feature": "op1"})
    assert not r["ok"] and r["error_kind"] == "FEATURE_IN_USE", r


# ---------------------------------------------------------------- camino directo (UI) y recetas reales
@pytest.mark.parametrize("ref", ["basura", None, [None], {"tipo": "cara"}, {"tipo": "xyz"}, {"cuerpo": "op1.c1"},
                                 {"tipo": "arista", "cuerpo": "op1.c1", "firma": {"medio": [0, 0, 0]}},
                                 ARISTA_SIN_MEDIO, VERT_SIN_PUNTO, CARA_NORMAL_MALA,
                                 {"tipo": "perfil", "boceto": "op1", "firma": [[1]]},
                                 {"tipo": "perfil", "boceto": "op1", "firma": [1], "centroide": [0]}])
def test_resolver_directo_lanza_error_de_referencia(ref):
    """Camino de la UI: ErrorReferencia (la subclase de forma, antes de buscar el cuerpo o el boceto)."""
    with pytest.raises(ent.ReferenciaMalFormada):
        ent.resolver(ref, EstadoModelo())


def test_el_ejemplo_pasa_la_revision_y_recalcula_sin_errores():
    doc = crear_documento_ejemplo()
    for op in doc.operaciones:
        op.revisar_parametros()
    assert all(r.estado in ("ok", "aviso") for r in doc.resultados), [(r.estado, r.mensaje) for r in doc.resultados]
