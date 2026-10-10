# -*- coding: utf-8 -*-
"""Valores de lista cerrada (OPCIONES) de las operaciones, enteros y distancias mínimas (PROJECT_LOG L219 y L175):
un valor inválido da un error claro con el campo y los valores válidos, y describe_operation los lista."""
import json
import math
import re

import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.gp import gp_Pnt

from omnicad import api
from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import superficies as sf
from omnicad.timeline.operaciones import TIPOS_OPERACION, ErrorOperacion, operacion_desde_dict

CON_OPCIONES = sorted(t for t, c in TIPOS_OPERACION.items() if c.OPCIONES)


def _op(tipo, /, **params):
    return operacion_desde_dict({"tipo": tipo, "id": "op99", "params": params})


def _foto(sesion):
    doc = sesion.doc
    return json.dumps(doc.a_dict(), sort_keys=True), [(r.estado, r.mensaje) for r in doc.resultados]


def _fallo(r):
    assert not r["ok"], r
    return r


def _ok(r):
    assert r["ok"], r
    return r["result"]


def _arista(a, b):
    return BRepBuilderAPI_MakeEdge(gp_Pnt(*map(float, a)), gp_Pnt(*map(float, b))).Edge()


# ---------------------------------------------------------------- una sola fuente: OPCIONES
def test_hay_opciones_en_las_familias_de_operaciones():
    for tipo in ("primitiva", "extrusion", "bobina", "union", "teselar", "patron", "pestana", "plano", "eje", "punto",
                 "fijacion", "empalme", "parche", "combinar"):
        assert TIPOS_OPERACION[tipo].OPCIONES, tipo


@pytest.mark.parametrize("tipo", sorted(TIPOS_OPERACION))
def test_opciones_coherentes_con_params_y_describe(tipo):
    clase = TIPOS_OPERACION[tipo]
    for clave, validos in clase.OPCIONES.items():
        assert clave in clase.PARAMS, clave
        assert clase.PARAMS[clave] in list(validos), (clave, clase.PARAMS[clave])
    _op(tipo).validar_opciones()                     # los valores por defecto siempre valen
    d = _ok(api.llamar(api.Sesion(), "describe_operation", {"type": tipo}))
    for p in d["params"]:
        if p["name"] in clase.OPCIONES:
            assert p["choices"] == list(clase.OPCIONES[p["name"]])
        else:
            assert "choices" not in p, p
    json.dumps(d)


def test_describe_operation_lista_los_valores_de_teselar_y_union():
    s = api.Sesion()
    tes = {p["name"]: p for p in _ok(api.llamar(s, "describe_operation", {"type": "teselar"}))["params"]}
    assert tes["refinamiento"]["choices"] == ["bajo", "medio", "alto"]
    uni = {p["name"]: p for p in _ok(api.llamar(s, "describe_operation", {"type": "union"}))["params"]}
    assert uni["tipo"]["choices"] == ["rigida", "revolucion", "deslizante", "cilindrica", "pasador_ranura", "planar",
                                      "bola"]
    assert uni["eje_giro"]["choices"] == ["X", "Y", "Z"] and "choices" not in uni["origen1"]


@pytest.mark.parametrize("tipo", CON_OPCIONES)
def test_valor_invalido_nombra_el_campo_y_los_validos(tipo):
    clase = TIPOS_OPERACION[tipo]
    for clave, validos in clase.OPCIONES.items():
        with pytest.raises(ErrorOperacion) as e:
            _op(tipo, **{clave: "xyz"}).validar_opciones()
        texto = str(e.value)
        assert f"«{clave}»" in texto and "'xyz'" in texto, texto
        assert all(str(v) in texto for v in validos if v), texto
    for clave in clase.OPCIONES:
        op = _op(tipo, **{clave: None})
        if clase.PARAMS.get(clave) is None:
            op.validar_opciones()    # campo opcional: None vale
        else:
            with pytest.raises(ErrorOperacion, match=f"«{clave}»"):
                op.validar_opciones()


def test_patron_n2_sin_direccion_2_y_suprimir_mal_formado():
    s = api.Sesion()
    _ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10}))
    (cid,) = s.doc.estado_final.cuerpos
    base = {"cuerpos": [cid], "dir1": {"tipo": "eje", "id": "X"}, "d1": "30 mm", "n1": 3}
    res = _ok(api.llamar(s, "run_operation", {"type": "patron", "params": dict(base, n2=0)}))   # n2 sin dir2: no cuenta
    assert res["status"] == "ok" and len(res["new_bodies"]) == 2
    for sup in (["op99.c1"], [None]):
        r = _fallo(api.llamar(s, "run_operation", {"type": "patron", "params": dict(base, suprimir=sup)}))
        assert "«suprimir»" in r["mensaje"] and "invalid literal" not in r["mensaje"], r


# ---------------------------------------------------------------- por la API: error claro, documento intacto
@pytest.mark.parametrize("tipo, clave, validos", [
    ("primitiva", "forma", "caja, cilindro, esfera, toroide"),
    ("bobina", "tipo", "rev_altura, rev_paso, altura_paso"),
    ("union", "tipo", "rigida, revolucion, deslizante, cilindrica, pasador_ranura, planar, bola"),
])
def test_run_operation_con_enum_invalido(tipo, clave, validos):
    s = api.Sesion()
    _ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10}))
    antes = _foto(s)
    r = _fallo(api.llamar(s, "run_operation", {"type": tipo, "params": {clave: "xyz"}}))
    assert r["error_kind"] == "OPERATION_FAILED"
    assert f"«{clave}»" in r["mensaje"] and validos in r["mensaje"] and "inesperado" not in r["mensaje"], r
    assert _foto(s) == antes


# ---------------------------------------------------------------- bobina: revoluciones y paso
def test_bobina_con_revoluciones_o_paso_cero():
    revoluciones = "Las revoluciones de la bobina tienen que ser mayores"
    paso = "El paso de la bobina tiene que ser mayor"
    for datos, mensaje in (({"revoluciones": 0, "altura": 30}, revoluciones),
                           ({"revoluciones": 0, "paso": 6}, revoluciones),
                           ({"altura": 30, "paso": 0}, paso), ({"revoluciones": 5, "paso": -1}, paso)):
        with pytest.raises(geo.ErrorGeometria, match=mensaje):
            sc.bobina((0, 0, 0), (0, 0, 1), diametro=20, tamano_seccion=3, **datos)
    s = api.Sesion()
    for params in ({"revoluciones": "0"}, {"tipo": "altura_paso", "paso": "0 mm"}):
        r = _fallo(api.llamar(s, "run_operation", {"type": "bobina", "params": params}))
        assert "mayor que cero" in r["mensaje"] or "mayores que cero" in r["mensaje"], r
        assert "division" not in r["mensaje"] and "inesperado" not in r["mensaje"], r


# ---------------------------------------------------------------- enteros
def test_entero_del_patron():
    op = _op("patron", n1="abc", n2=2.5, n="4", d1=3.0)
    with pytest.raises(ErrorOperacion, match=r"«n1» tiene que ser un número entero \(al menos 1\): llegó el texto "
                                             r"'abc'"):
        op.entero("n1")
    with pytest.raises(ErrorOperacion, match="«n2» tiene que ser un número entero"):
        op.entero("n2")
    assert op.entero("n") == 4 and op.entero("d1") == 3
    with pytest.raises(ErrorOperacion, match="al menos 1"):
        _op("patron", n1=0).entero("n1")
    with pytest.raises(ErrorOperacion, match="número entero"):
        _op("patron", n1=True).entero("n1")


def test_patron_con_cantidad_de_texto():
    s = api.Sesion()
    _ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10}))
    (cid,) = s.doc.estado_final.cuerpos
    base = {"cuerpos": [cid], "dir1": {"tipo": "eje", "id": "X"}, "d1": "30 mm"}
    r = _fallo(api.llamar(s, "run_operation", {"type": "patron", "params": dict(base, n1="abc")}))
    assert "«n1» tiene que ser un número entero" in r["mensaje"] and "invalid literal" not in r["mensaje"], r
    res = _ok(api.llamar(s, "run_operation", {"type": "patron", "params": dict(base, n1="3")}))
    assert res["status"] == "ok" and len(res["new_bodies"]) == 2
    x0 = geo.caja_envolvente(s.doc.estado_final.cuerpos[cid].forma)[0][0]
    nuevos = [s.doc.estado_final.cuerpos[c].forma for c in res["new_bodies"]]
    assert all(geo.es_valida(f) for f in nuevos)
    assert sorted(round(geo.caja_envolvente(f)[0][0] - x0, 6) for f in nuevos) == [15, 30]   # extensión de 30 mm


# ---------------------------------------------------------------- distancias mínimas de extrusión
def _cara():
    return next(c for c in geo.caras(geo.caja(10, 10, 10)) if abs(geo.plano_de_cara(c).normal[2] - 1) < 1e-9)


def test_extrusion_de_un_diezmillonesimo_de_mm():
    with pytest.raises(geo.ErrorGeometria, match=r"La distancia de extrusión tiene que ser de al menos 0\.000001 mm"):
        geo.extruir([_cara()], (0, 0, 1), 1e-7)
    with pytest.raises(geo.ErrorGeometria, match=r"al menos 0\.000001 mm; recibió 0 mm"):
        geo.extruir([_cara()], (0, 0, 1), 0)
    with pytest.raises(geo.ErrorGeometria, match=r"al menos 0\.000001 mm"):
        sc.extruir_avanzado([_cara()], (0, 0, 1), distancia1=1e-7, conicidad1=5)
    with pytest.raises(geo.ErrorGeometria, match=r"La distancia del lado 2 tiene que ser de al menos 0\.000001 mm"):
        sc.extruir_avanzado([_cara()], (0, 0, 1), direccion="dos_lados", distancia1=5, distancia2=1e-7, conicidad1=5)
    with pytest.raises(geo.ErrorGeometria, match=r"La profundidad del repujado tiene que ser de al menos 0\.000001 mm"):
        sc.repujado(geo.caja(10, 10, 10), [_cara()], _cara(), 1e-7)
    with pytest.raises(geo.ErrorGeometria, match=r"al menos 0\.000001 mm"):
        sf.extruir_superficie([_arista((0, 0, 0), (10, 0, 0))], (0, 0, 1), -1e-7)
    borde = geo.extruir([_cara()], (0, 0, 1), 1e-6)                 # el mínimo sí se construye
    assert geo.es_valida(borde) and geo.volumen(borde) == pytest.approx(100 * 1e-6, rel=1e-6)


def test_extrusion_minima_por_la_api():
    s = api.Sesion()
    sid = _ok(api.llamar(s, "sketch_from_spec", {"plane": "XY", "name": "S1", "entities": [
        {"type": "rectangle", "origin": [-10, -10], "width": 20, "height": 20, "id": "rc"}]}))["sketch"]["id"]
    antes = _foto(s)
    r = _fallo(api.llamar(s, "extrude", {"sketch": sid, "distance": "0.0000001 mm"}))
    assert r["error_kind"] == "OPERATION_FAILED" and "al menos 0.000001 mm" in r["mensaje"], r
    assert "BRepSweep" not in r["mensaje"] and _foto(s) == antes


def test_extrusion_minima_nombra_el_campo_y_el_valor_escrito():
    """Lado 2, simétrica y «Al objeto»: el mensaje dice el campo que se escribió y su valor, no el largo del prisma
    (antes: «La distancia de extrusión… recibió 2e-07 mm» con 1e-7 en la simétrica «mitad»)."""
    from omnicad.timeline.operaciones import OpExtrusion
    s = api.Sesion()
    _ok(api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 20}))
    (cid,) = s.doc.estado_final.cuerpos
    sid = _ok(api.llamar(s, "sketch_from_spec", {"plane": "XY", "name": "S1", "entities": [
        {"type": "rectangle", "origin": [-10, -10], "width": 20, "height": 20, "id": "rc"}]}))["sketch"]["id"]
    perfiles = [dict(OpExtrusion.referencia_perfil(p), tipo="perfil", boceto=sid)
                for p in s.doc.estado_final.bocetos[sid].perfiles]
    base = {"boceto": sid, "perfiles": perfiles, "operacion": "nuevo"}
    lado2 = r"La distancia del lado 2 tiene que ser de al menos 0\.000001 mm; recibió 1e-07 mm"
    total = r"La distancia total de la extrusión simétrica tiene que ser de al menos 0\.000002 mm; recibió 1\.5e-06 mm"
    casos = [({"direccion": "dos_lados", "distancia": "5 mm", "distancia2": "0.0000001 mm"}, lado2),
             ({"direccion": "dos_lados", "distancia": "5 mm", "distancia2": "0.0000001 mm", "conicidad": "5 deg"},
              lado2),
             ({"direccion": "dos_lados", "extension": "objeto", "hasta": {"tipo": "cuerpo", "cuerpo": cid},
               "distancia2": "0.0000001 mm"}, lado2),
             ({"direccion": "simetrica", "medida": "mitad", "distancia": "0.0000001 mm"},
              r"La distancia de extrusión tiene que ser de al menos 0\.000001 mm; recibió 1e-07 mm"),
             ({"direccion": "simetrica", "medida": "total", "distancia": "0.0000015 mm"}, total),
             ({"direccion": "simetrica", "medida": "total", "distancia": "0.0000015 mm", "conicidad": "5 deg"}, total)]
    antes = _foto(s)
    for params, mensaje in casos:
        r = _fallo(api.llamar(s, "run_operation", {"type": "extrusion", "params": dict(base, **params)}))
        assert r["error_kind"] == "OPERATION_FAILED" and re.search(mensaje, r["mensaje"]), (params, r)
        assert _foto(s) == antes
    for medida, distancia in (("mitad", "0.000001 mm"), ("total", "0.000002 mm")):  # el mínimo sí se construye
        res = _ok(api.llamar(s, "run_operation", {"type": "extrusion", "params": dict(
            base, direccion="simetrica", medida=medida, distancia=distancia)}))
        forma = s.doc.estado_final.cuerpos[res["new_bodies"][0]].forma
        assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(400 * 2e-6, rel=1e-6)   # 20 × 20 × 2e-6
        _ok(api.llamar(s, "undo"))


# ---------------------------------------------------------------- extrusión de superficie de una recta con conicidad
def test_sup_extruir_recta_sola_con_conicidad():
    t5 = math.tan(math.radians(5))
    recta_z = [_arista((0, 0, 0), (0, 0, 30))]
    s = sf.extruir_superficie(recta_z, (0, -1, 0), 10, conicidad=5)       # antes: «Error inesperado:» en blanco
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(s)
    assert geo.es_valida(s) and geo.area(s) == pytest.approx(300 / math.cos(math.radians(5)), rel=1e-6)
    assert (x0, x1, y0, y1) == pytest.approx((0, 10 * t5, -10, 0), abs=1e-6)     # a la derecha del recorrido
    (x0, _, _), (x1, _, _) = geo.caja_envolvente(sf.extruir_superficie(recta_z, (0, -1, 0), 10, conicidad=-5))
    assert (x0, x1) == pytest.approx((-10 * t5, 0), abs=1e-6)
    sim = sf.extruir_superficie(recta_z, (0, -1, 0), 10, simetrica=True, conicidad=5)
    (x0, y0, _), (x1, y1, _) = geo.caja_envolvente(sim)
    assert geo.area(sim) == pytest.approx(300 / math.cos(math.radians(5)), rel=1e-6)
    assert (x0, x1, y0, y1) == pytest.approx((-5 * t5, 5 * t5, -5, 5), abs=1e-6)
    # Donde MakeDraft sí resuelve, el resultado no cambia: recta +X hacia +Z se inclina hacia −Y.
    (_, y0, _), (_, y1, _) = geo.caja_envolvente(sf.extruir_superficie([_arista((0, 0, 0), (10, 0, 0))], (0, 0, 1),
                                                                          10, conicidad=5))
    assert (y0, y1) == pytest.approx((-10 * t5, 0), abs=1e-6)


def test_sup_extruir_con_conicidad_que_occ_no_resuelve(monkeypatch):
    class Falla:
        def __init__(self, *a):
            raise RuntimeError("")                              # como gp_VectorWithNullMagnitude: sin texto

    monkeypatch.setattr(sf, "BRepOffsetAPI_MakeDraft", Falla)
    recta = sf.extruir_superficie([_arista((0, 0, 0), (10, 0, 0))], (0, 0, 1), 10, conicidad=5)
    assert geo.es_valida(recta) and geo.caja_envolvente(recta)[0][1] == pytest.approx(-10 * math.tan(math.radians(5)))
    ele = [_arista((0, 0, 0), (10, 0, 0)), _arista((10, 0, 0), (10, 10, 0))]
    with pytest.raises(geo.ErrorGeometria, match="probá con conicidad 0"):
        sf.extruir_superficie(ele, (0, 0, 1), 10, conicidad=5)


def test_sup_extruir_por_la_api_con_una_recta():
    s = api.Sesion()
    sid = _ok(api.llamar(s, "sketch_from_spec", {"plane": "XZ", "name": "S2", "entities": [
        {"type": "line", "start": [0, 0], "end": [0, 30], "id": "l1"}]}))["sketch"]["id"]
    boceto = s.doc.estado_final.bocetos[sid].boceto
    curvas = [{"tipo": "curva_boceto", "boceto": sid, "curva": c} for c in boceto.curvas]
    res = _ok(api.llamar(s, "run_operation", {"type": "sup_extruir", "params": {"curvas": curvas,
                                                                                "conicidad": "5 deg"}}))
    assert res["status"] == "ok" and len(res["new_bodies"]) == 1
    forma = s.doc.estado_final.cuerpos[res["new_bodies"][0]].forma
    assert geo.area(forma) == pytest.approx(300 / math.cos(math.radians(5)), rel=1e-6)


# ---------------------------------------------------------------- compatibilidad
def test_el_ejemplo_recalcula_sin_errores():
    doc = crear_documento_ejemplo()
    assert all(r.estado != "error" for r in doc.resultados), [(r.estado, r.mensaje) for r in doc.resultados]
    for op in doc.operaciones:
        op.validar_opciones()
