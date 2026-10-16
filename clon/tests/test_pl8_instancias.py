# -*- coding: utf-8 -*-
"""PL8 + F17 + RH17 (instancias / copias ligeras, `ligeras` en la operación y `lightweight` en la API): las copias de un
patrón o de Mover/copiar comparten la geometría
del original (la misma forma con otra ubicación), cada una tiene su posición, editar la original cambia todas y se
guarda en el .omnicad sin romper los archivos viejos."""
import json

import numpy as np
import pytest

from omnicad import api
from omnicad.io_archivos import proyecto
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


def _ok(r):
    assert r["ok"], r
    return r["result"]


def _caja(s, **medidas):
    return _ok(api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, **medidas}))["bodies_created"][0]["id"]


def _formas(s):
    return [c.forma for c in s.doc.estado_final.cuerpos.values()]


def _centro(forma):
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(forma)
    return np.array([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])


@pytest.fixture
def con_patron():
    s = api.Sesion()
    cid = _caja(s)
    _ok(api.llamar(s, "rectangular_pattern", {"bodies": [cid], "x_count": 3, "x_spacing": 20, "y_count": 2,
                                              "y_spacing": 20, "lightweight": True}))
    return s


# ---------------------------------------------------------------- el núcleo
def test_instanciar_comparte_la_geometria_y_cambia_la_ubicacion():
    caja = geo.caja(10, 10, 10, (0, 0, 0))
    m = np.identity(4)
    m[:3, 3] = (50, 0, 0)
    copia = sc.instanciar(caja, m)
    assert copia.IsPartner(caja) and not copia.IsSame(caja)               # mismo TShape, otra ubicación
    assert geo.volumen(copia) == pytest.approx(geo.volumen(caja)) and geo.es_valida(copia)
    assert _centro(copia) == pytest.approx(_centro(caja) + (50, 0, 0))
    real = sc.aplicar(caja, m)
    assert not real.IsPartner(caja)                                       # la copia de verdad duplica la geometría


def test_las_aristas_los_vertices_y_las_caras_de_una_instancia_estan_en_su_lugar():
    from omnicad.nucleo import referencias as refs
    caja = geo.caja(10, 10, 10, (0, 0, 0))
    m = np.identity(4)
    m[:3, 3] = (50, 0, 0)
    copia = sc.instanciar(caja, m)
    desde = np.array([50.0, 0.0, 0.0])
    for e0, e1 in zip(refs.subformas(caja, "arista"), refs.subformas(copia, "arista"), strict=True):
        assert np.asarray(geo.polilinea_arista(e1)) == pytest.approx(np.asarray(geo.polilinea_arista(e0)) + desde)
    for v0, v1 in zip(refs.subformas(caja, "vertice"), refs.subformas(copia, "vertice"), strict=True):
        assert np.asarray(refs.punto_de_vertice(v1)) == pytest.approx(np.asarray(refs.punto_de_vertice(v0)) + desde)
    caras0, caras1 = refs.subformas(caja, "cara"), refs.subformas(copia, "cara")
    assert len(caras1) == 6
    for c0, c1 in zip(caras0, caras1, strict=True):
        assert _centro(c1) == pytest.approx(_centro(c0) + desde)


def test_una_simetria_o_una_escala_no_se_pueden_instanciar_y_caen_en_copia_de_verdad():
    caja = geo.caja(10, 10, 10, (5, 0, 0))
    espejo = np.diag([-1.0, 1.0, 1.0, 1.0])
    copia = sc.instanciar(caja, espejo)
    assert not copia.IsPartner(caja) and geo.volumen(copia) == pytest.approx(1000)
    assert _centro(copia) == pytest.approx([-5, 5, 5], abs=1e-6) or _centro(copia)[0] < 0
    grande = sc.instanciar(caja, np.diag([2.0, 2.0, 2.0, 1.0]))
    assert not grande.IsPartner(caja) and geo.volumen(grande) == pytest.approx(8000)


# ---------------------------------------------------------------- patrones
def test_el_patron_con_instancias_comparte_la_geometria_y_cada_copia_tiene_su_lugar(con_patron):
    s = con_patron
    formas = _formas(s)
    assert len(formas) == 6 and all(f.IsPartner(formas[0]) for f in formas)
    centros = sorted(tuple(np.round(_centro(f), 3)) for f in formas)
    assert centros == sorted((x, y, 5.0) for x in (0.0, 20.0, 40.0) for y in (0.0, 20.0))     # la caja nace centrada en XY
    assert all(geo.volumen(f) == pytest.approx(1000) for f in formas)


def test_sin_instancias_siguen_siendo_copias_de_verdad():
    s = api.Sesion()
    cid = _caja(s)
    _ok(api.llamar(s, "rectangular_pattern", {"bodies": [cid], "x_count": 3, "x_spacing": 20}))
    formas = _formas(s)
    assert len(formas) == 3 and not any(f.IsPartner(formas[0]) for f in formas[1:])


def test_editar_la_original_cambia_todas_las_copias(con_patron):
    s = con_patron
    assert all(geo.volumen(f) == pytest.approx(1000) for f in _formas(s))
    _ok(api.llamar(s, "edit_feature", {"feature": s.doc.operaciones[0].id, "params": {"alto": "30 mm"}}))
    formas = _formas(s)
    assert len(formas) == 6 and all(geo.volumen(f) == pytest.approx(3000) for f in formas)
    assert all(f.IsPartner(formas[0]) for f in formas)                    # y siguen compartiendo la geometría nueva


def test_realizar_las_instancias_las_vuelve_copias_de_verdad(con_patron):
    s = con_patron
    paso = s.doc.operaciones[-1]
    r = _ok(api.llamar(s, "realize_copies", {"feature": paso.id}))
    assert r["feature"]["id"] == paso.id and r["realized"] == 5
    formas = _formas(s)
    assert len(formas) == 6 and not any(f.IsPartner(formas[0]) for f in formas[1:])
    assert all(geo.volumen(f) == pytest.approx(1000) for f in formas)
    again = api.llamar(s, "realize_copies", {"feature": paso.id})
    assert again["ok"] is False and again["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "realize_copies", {"feature": s.doc.operaciones[0].id})["ok"] is False


def test_combinar_no_usa_instancias_y_une_de_verdad():
    s = api.Sesion()
    cid = _caja(s)
    _ok(api.llamar(s, "rectangular_pattern", {"bodies": [cid], "x_count": 3, "x_spacing": 8, "combine": True,
                                              "lightweight": True}))
    (unica,) = _formas(s)
    assert geo.es_valida(unica) and geo.volumen(unica) == pytest.approx(10 * 10 * 10 + 8 * 10 * 10 * 2)


def test_circular_puntos_y_ruta_tambien_instancian():
    s = api.Sesion()
    cid = _caja(s, x=30)
    _ok(api.llamar(s, "circular_pattern", {"bodies": [cid], "count": 4, "lightweight": True}))
    formas = _formas(s)
    assert len(formas) == 4 and all(f.IsPartner(formas[0]) for f in formas)
    s = api.Sesion()
    cid = _caja(s)
    _ok(api.llamar(s, "point_pattern", {"bodies": [cid], "points": [[20, 0, 0], [40, 10, 0]], "lightweight": True}))
    formas = _formas(s)
    assert len(formas) == 3 and all(f.IsPartner(formas[0]) for f in formas)


def test_multitransformacion_instancia_lo_rigido_y_copia_de_verdad_las_simetrias():
    s = api.Sesion()
    cid = _caja(s, x=20)
    _ok(api.llamar(s, "multi_transform", {"bodies": [cid], "lightweight": True,
                                          "transforms": [{"type": "rectangular", "axis": "x", "count": 2, "spacing": 30},
                                                         {"type": "mirror", "plane": "YZ"}]}))
    formas = _formas(s)
    assert len(formas) == 4 and all(geo.volumen(f) == pytest.approx(1000) and geo.es_valida(f) for f in formas)
    assert sum(1 for f in formas[1:] if f.IsPartner(formas[0])) >= 1       # lo rígido comparte, el espejo no


# ---------------------------------------------------------------- Mover / copiar
def test_mover_copiar_puede_dejar_una_copia_ligera():
    s = api.Sesion()
    cid = _caja(s)
    _ok(api.llamar(s, "move_body", {"body": cid, "translate": [30, 0, 0], "copy": True, "lightweight": True}))
    a, b = _formas(s)
    assert a.IsPartner(b) and _centro(b) == pytest.approx(_centro(a) + (30, 0, 0))
    s2 = api.Sesion()
    cid = _caja(s2)
    _ok(api.llamar(s2, "move_body", {"body": cid, "translate": [30, 0, 0], "copy": True}))
    a, b = _formas(s2)
    assert not a.IsPartner(b)
    mover = api.llamar(s2, "move_body", {"body": cid, "translate": [1, 0, 0], "lightweight": True})   # sin copy: no tiene sentido
    assert mover["ok"] is False and mover["error_kind"] == "INVALID_ARGUMENTS"


# ---------------------------------------------------------------- lo que tiene que seguir andando con formas ubicadas
def test_exportar_teselar_y_operar_con_instancias(con_patron, tmp_path):
    s = con_patron
    original, copia = _formas(s)[0], _formas(s)[-1]
    v0, v1 = geo.teselar(original, 0.1, 0.3)[0], geo.teselar(copia, 0.1, 0.3)[0]
    assert len(v0) == len(v1) and not np.allclose(np.asarray(v0).mean(axis=0), np.asarray(v1).mean(axis=0))
    ruta = tmp_path / "instancias.stl"
    exp = _ok(api.llamar(s, "export", {"path": str(ruta), "overwrite": True}))
    assert exp["format"] == "stl" and ruta.stat().st_size > 6 * 12 * 50
    ids = [c.id for c in s.doc.estado_final.cuerpos.values()]
    hueco = _ok(api.llamar(s, "create_cylinder", {"radius": 2, "height": 30, "x": 45, "y": 25}))["bodies_created"][0]["id"]
    r = _ok(api.llamar(s, "boolean_operation", {"target": ids[-1], "tools": [hueco], "operation": "cut"}))
    modificado = next(c for c in s.doc.estado_final.cuerpos.values() if c.id == ids[-1])
    assert geo.volumen(modificado.forma) < 1000 and r is not None
    assert all(geo.volumen(c.forma) == pytest.approx(1000) for c in s.doc.estado_final.cuerpos.values()
               if c.id in ids[:-1])                                         # las demás copias siguen intactas
    ancho = _ok(api.llamar(s, "fillet", {"edges": ">Z", "radius": 1, "body": ids[0]}))
    assert ancho["bodies_modified"][0]["volume"] < 1000


def test_un_step_con_instancias_vuelve_con_cada_copia_en_su_lugar(tmp_path):
    s = api.Sesion()
    cid = _caja(s)
    _ok(api.llamar(s, "rectangular_pattern", {"bodies": [cid], "x_count": 3, "x_spacing": 20, "lightweight": True}))
    ruta = tmp_path / "instancias.step"
    _ok(api.llamar(s, "export", {"path": str(ruta), "overwrite": True}))
    otra = api.Sesion()
    _ok(api.llamar(otra, "insert_file", {"path": str(ruta)}))
    formas = _formas(otra)
    assert len(formas) == 3 and all(geo.volumen(f) == pytest.approx(1000) for f in formas)
    assert sorted(round(float(_centro(f)[0])) for f in formas) == [0, 20, 40]


# ---------------------------------------------------------------- archivos
def test_el_proyecto_guarda_el_parametro_y_los_archivos_viejos_abren_igual(con_patron, tmp_path):
    s = con_patron
    receta = s.doc.a_dict()
    patron = next(o for o in receta["operaciones"] if o["tipo"] == "patron")
    assert patron["params"]["ligeras"] is True
    ruta = tmp_path / "pieza.omnicad"
    proyecto.guardar(s.doc, ruta)
    abierto = proyecto.abrir(ruta)
    formas = [c.forma for c in abierto.estado_final.cuerpos.values()]
    assert len(formas) == 6 and all(f.IsPartner(formas[0]) for f in formas)
    del patron["params"]["ligeras"]                                      # un archivo anterior: no trae el parámetro
    viejo = api.Sesion(__import__("omnicad.timeline.documento", fromlist=["Documento"]).Documento.desde_dict(json.loads(
        json.dumps(receta))))
    formas = [c.forma for c in viejo.doc.estado_final.cuerpos.values()]
    assert len(formas) == 6 and not any(f.IsPartner(formas[0]) for f in formas[1:])
    assert all(geo.volumen(f) == pytest.approx(1000) for f in formas)


# ---------------------------------------------------------------- la interfaz
def test_el_dialogo_del_patron_tiene_la_casilla_de_instancias():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.comando import Casilla, ContextoComando, hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10 mm", largo="10 mm", alto="10 mm"))
    cmd = CATALOGO["patron_rectangular_3d"]()
    ctx = ContextoComando(doc)
    campos = {c.clave: c for c in cmd.campos(ctx)}
    assert isinstance(campos["ligeras"], Casilla) and campos["ligeras"].defecto is False
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(cuerpos=[hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)],
             dir1=[hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)], ligeras=True)
    op = cmd.construir(v, ctx)
    assert op.p["ligeras"] is True and doc.agregar(op).estado in ("ok", "aviso")
    formas = [c.forma for c in doc.estado_final.cuerpos.values()]
    assert len(formas) == 3 and all(f.IsPartner(formas[0]) for f in formas)
    assert cmd.desde_op(op, ContextoComando(doc, op=op))["ligeras"] is True


# ---------------------------------------------------------------- revisión ponytail (upgrades3)
def test_con_combine_lightweight_se_ignora_avisa_y_realize_copies_no_miente():
    s = api.Sesion()
    cid = _caja(s)
    r = api.llamar(s, "rectangular_pattern", {"bodies": [cid], "x_count": 3, "x_spacing": 8, "combine": True,
                                              "lightweight": True})
    assert r["ok"] and any("combine" in a for a in r["avisos"])
    paso = r["result"]["feature"]["id"]
    assert s.doc.operaciones[-1].p["ligeras"] is False
    falla = api.llamar(s, "realize_copies", {"feature": paso})                    # antes: ok con realized=1
    assert falla["ok"] is False and falla["error_kind"] == "INVALID_ARGUMENTS"


def test_realize_copies_de_un_mover_sin_copia_falla():
    s = api.Sesion()
    cid = _caja(s)
    paso = _ok(api.llamar(s, "move_body", {"body": [cid], "translate": [5, 0, 0]}))["feature"]["id"]
    _ok(api.llamar(s, "edit_feature", {"feature": paso, "params": {"ligera": True}}))
    falla = api.llamar(s, "realize_copies", {"feature": paso})
    assert falla["ok"] is False and falla["error_kind"] == "INVALID_ARGUMENTS"


def test_la_multitransformacion_avisa_que_la_simetria_no_queda_ligera():
    s = api.Sesion()
    cid = _caja(s, x=20)
    r = api.llamar(s, "multi_transform", {"bodies": [cid], "lightweight": True,
                                          "transforms": [{"type": "mirror", "plane": "YZ"}]})
    assert r["ok"] and any("simetría" in a for a in r["avisos"])


def test_el_dialogo_no_guarda_ligeras_con_la_casilla_oculta_por_unir():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10 mm", largo="10 mm", alto="10 mm"))
    cmd = CATALOGO["patron_rectangular_3d"]()
    ctx = ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    v.update(cuerpos=[hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)],
             dir1=[hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)], ligeras=True, combinar=True)
    assert cmd.construir(v, ctx).p["ligeras"] is False
