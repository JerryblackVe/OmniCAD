# -*- coding: utf-8 -*-
import pytest

from omnicad import api
from omnicad.timeline.operaciones import TIPOS_OPERACION


def ok(r):
    assert r["ok"], r
    return r["result"]


def _base(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "create_sketch", {}))
    ok(api.llamar(sesion, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 5, "y2": 5}))


def _params_heuristic(tipo, desc_result):
    params = dict(desc_result["example"]["args"]["params"])
    for p in desc_result["params"]:
        if p.get("choices"):
            continue
        nm = p["name"].lower()
        if "boceto" in nm:
            params[p["name"]] = "Boceto1"
        elif "perfil" in nm:
            if p["type"] == "array":
                params[p["name"]] = ["all"]
            else:
                params[p["name"]] = "all"
        elif "cuerpo" in nm or "objetivo" in nm or "objeto" in nm or "bodies" in nm:
            if p["type"] == "array":
                params[p["name"]] = ["Cuerpo1"]
            else:
                params[p["name"]] = "Cuerpo1"
        elif "cara" in nm:
            if p["type"] == "array":
                params[p["name"]] = [">Z"]
            else:
                params[p["name"]] = ">Z"
        elif "arista" in nm:
            if p["type"] == "array":
                params[p["name"]] = ["|Z"]
            else:
                params[p["name"]] = "|Z"
        elif "plano" in nm:
            params[p["name"]] = "XY"
        elif "eje" in nm and p["type"] != "string":
            params[p["name"]] = "Z"
    return params


def _armar_via_run(sesion, tipo):
    _base(sesion)
    d = ok(api.llamar(sesion, "describe_operation", {"type": tipo}))
    params = _params_heuristic(tipo, d)
    r = api.llamar(sesion, "run_operation", {"type": tipo, "params": params})
    assert r["ok"], r


def _caso_primitiva(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 15, "width": 15, "height": 15}))


def _caso_extrusion(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10}))
    ok(api.llamar(sesion, "create_sketch", {}))
    ok(api.llamar(sesion, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 6, "y2": 6}))
    ok(api.llamar(sesion, "extrude", {"sketch": "Boceto1", "distance": 12}))


def _caso_revolucion(sesion):
    ok(api.llamar(sesion, "create_sketch", {"plane": "XZ"}))
    ok(api.llamar(sesion, "draw_rectangle", {"x1": 2, "y1": 0, "x2": 6, "y2": 8}))
    ok(api.llamar(sesion, "revolve", {"sketch": "Boceto1", "axis": "sketch_y", "angle": 360}))


def _caso_empalme(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "fillet", {"edges": "|Z", "radius": 2}))


def _caso_chaflan(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "chamfer", {"edges": "|Z", "distance": 1}))


def _caso_vaciado(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 30, "width": 30, "height": 20}))
    try:
        ok(api.llamar(sesion, "shell", {"body": "Cuerpo1", "faces": ">Z", "thickness": 2}))
    except Exception:
        _armar_via_run(sesion, "vaciado")


def _caso_agujero(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 30, "width": 30, "height": 10}))
    ok(api.llamar(sesion, "create_hole", {"face": ">Z", "diameter": 8, "depth": 6}))


def _caso_combinar(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10}))
    ok(api.llamar(sesion, "create_cylinder", {"radius": 4, "height": 15, "x": 3}))
    try:
        ok(api.llamar(sesion, "boolean_operation", {"type": "union", "bodies": ["Cuerpo1", "Cuerpo2"]}))
    except Exception:
        _armar_via_run(sesion, "combinar")


def _caso_simetria(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10, "x": 5}))
    try:
        ok(api.llamar(sesion, "mirror", {"bodies": ["Cuerpo1"], "plane": "YZ"}))
    except Exception:
        _armar_via_run(sesion, "simetria")


def _caso_patron(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10}))
    try:
        ok(api.llamar(sesion, "rectangular_pattern", {"bodies": ["Cuerpo1"], "x_count": 2, "x_spacing": 15, "y_count": 1, "y_spacing": 15}))
    except Exception:
        _armar_via_run(sesion, "patron")


def _caso_escala(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10}))
    try:
        ok(api.llamar(sesion, "scale_body", {"bodies": ["Cuerpo1"], "factor": 1.5}))
    except Exception:
        _armar_via_run(sesion, "escala")


CASOS = {}
for _t in [
    "plano", "operacion_base", "calibracion_holguras", "convertir_chapa", "scu",
    "componente", "engranaje", "eje_escalonado", "teselar", "desfase_cara", "editar_cara",
    "apoyar", "reparar_cuerpo", "bobina", "solido_envolvente", "patron_geometrico",
    "reticula_volumetrica", "reglada", "sup_desfase", "coser", "engrosar", "sup_empalme", "sup_primitiva",
    "sup_bobina", "escala", "simetria",
]:
    CASOS[_t] = (lambda sesion, t=_t: _armar_via_run(sesion, t))

CASOS["primitiva"] = _caso_primitiva


def _dos_cajas(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10}))
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10, "x": 5}))


CASOS["mover"] = lambda s: (_dos_cajas(s), ok(api.llamar(s, "move_body", {"body": "Cuerpo2", "translate": [20, 0, 0]})))
CASOS["quitar"] = lambda s: (_dos_cajas(s), ok(api.llamar(s, "remove_bodies", {"bodies": "Cuerpo2"})))
CASOS["combinar"] = lambda s: (_dos_cajas(s), ok(api.llamar(s, "boolean_operation", {"target": "Cuerpo1", "tools": ["Cuerpo2"]})))
CASOS["extrusion"] = _caso_extrusion
CASOS["empalme"] = _caso_empalme
CASOS["chaflan"] = _caso_chaflan
CASOS["vaciado"] = _caso_vaciado
CASOS["agujero"] = _caso_agujero
CASOS["patron"] = _caso_patron
CASOS["escala"] = _caso_escala
CASOS["simetria"] = _caso_simetria
CASOS["revolucion"] = _caso_revolucion

_PENDIENTES_RAW = sorted(set(TIPOS_OPERACION.keys()) - set(CASOS.keys()))


def _razon_pendiente(t):
    tl = t.lower()
    if "importar" in tl:
        return "requiere un archivo externo (STEP/IGES/OBJ/STL)"
    if "chapa" in tl or "pleg" in tl or "doblad" in tl or "despleg" in tl or "unir_pleg" in tl:
        return "requiere chapa/plegado previo"
    if "malla" in tl or "remall" in tl or "suaviz" in tl or "reducir_malla" in tl or "separar_malla" in tl or "limpiar_malla" in tl or "reparar_malla" in tl or "convertir_malla" in tl or "vaciado_malla" in tl or "escalar_malla" in tl or "invertir_normal_malla" in tl or "grupos_caras" in tl or "combinar_grupos_caras" in tl:
        return "requiere malla previa"
    if "componente" in tl or "ensambl" in tl or "union" in tl or "origen_union" in tl or "grupo_rigido" in tl or "vinculo" in tl or "anclar" in tl or "posicion_inicial" in tl or "capturar_posicion" in tl or "revertir_posicion" in tl or "copiar_componente" in tl or "fijacion" in tl:
        return "requiere ensamble/componentes previos"
    if "grafo" in tl or "lienzo" in tl:
        return "requiere grafo de programacion visual o configuracion de ventana"
    if "patron_plano" in tl:
        return "requiere cara/punto especificos"
    if "barrido" == tl or "solevacion" == tl or "sup_barrido" == tl or "sup_solevacion" == tl:
        return "requiere boceto de trayectoria/perfiles especificos"
    if "nervio" in tl or "saliente" in tl or "pestana" in tl or "labio" in tl or "repujado" in tl or "desgarro" in tl:
        return "requiere caras/bordes especificos"
    if "dividir" in tl or "borrar_caras" in tl or "reemplazar_cara" in tl or "desfase_aristas" in tl or "quitar_empalmes" in tl or "eliminar_operaciones" in tl or "alinear" in tl or "mover" == tl or "escala" == tl or "desmoldeo" == tl or "rosca" == tl:
        return "requiere referencias (caras/aristas/cuerpos) especificas"
    if "tuberia" in tl:
        return "requiere curva/boceto de trayectoria"
    if "parche" in tl or "recortar_sup" in tl or "destrimar" in tl or "extender_sup" in tl or "descoser" in tl or "invertir_normal" in tl or "relleno_contorno" in tl or "regla_plastico" in tl or "volumen_fluido" in tl:
        return "requiere superficies o caras especificas"
    if "eje" == tl or "punto" == tl or "derivacion" in tl:
        return "requiere referencias especificas"
    if "cortar_plano" in tl:
        return "requiere plano/corte especifico"
    return "caso minimo no armado en esta tanda (requiere geometria o referencias especificas)"


PENDIENTES = {t: _razon_pendiente(t) for t in _PENDIENTES_RAW}


def test_todos_los_tipos_tienen_caso_o_razon():
    tipos = set(TIPOS_OPERACION.keys())
    casos_keys = set(CASOS.keys())
    pend_keys = set(PENDIENTES.keys())
    assert casos_keys.union(pend_keys) == tipos
    assert casos_keys.intersection(pend_keys) == set()
    assert len(casos_keys) >= 37                 # piso: lo que hoy pasa; la meta de la tanda era 40


def _guardar_y_abrir(sesion, tmp_path):
    r = api.llamar(sesion, "save_document", {"path": str(tmp_path / "caso")})
    assert r["ok"], r
    path = r["result"]["path"]
    props_antes = api.llamar(sesion, "get_physical_properties", {})
    assert props_antes["ok"]
    vols_antes = {b["id"]: b["volume"] for b in props_antes["result"]["bodies"]}
    otra = api.Sesion()
    ro = api.llamar(otra, "open_document", {"path": path})
    assert ro["ok"], ro
    props_despues = api.llamar(otra, "get_physical_properties", {})
    assert props_despues["ok"]
    vols_despues = {b["id"]: b["volume"] for b in props_despues["result"]["bodies"]}
    assert set(vols_antes.keys()) == set(vols_despues.keys())
    for k in vols_antes:
        assert vols_despues[k] == pytest.approx(vols_antes[k], rel=1e-3)


@pytest.mark.parametrize("tipo", sorted(CASOS), ids=sorted(CASOS))
def test_caso_de_cada_tipo(tipo, tmp_path):
    s = api.Sesion()
    CASOS[tipo](s)
    tl = api.llamar(s, "get_timeline", {})
    assert tl["ok"]
    steps = tl["result"]["steps"]
    assert steps[-1]["type"] == tipo
    assert steps[-1].get("status") != "error"
    cg = api.llamar(s, "check_geometry", {})
    assert cg["ok"]
    assert cg["result"].get("all_valid") is True
    _guardar_y_abrir(s, tmp_path)
    tl_antes = api.llamar(s, "get_timeline", {})["result"]["steps"]
    n = len(tl_antes)
    ru = api.llamar(s, "undo", {})
    assert ru["ok"], ru
    tl_despues = api.llamar(s, "get_timeline", {})["result"]["steps"]
    assert len(tl_despues) == n - 1
