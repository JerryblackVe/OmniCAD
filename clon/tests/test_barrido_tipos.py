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


def _caso_eje(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "create_construction_axis", {"type": "dos_planos", "references": ["XY", "XZ"]}))


def _caso_punto(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "create_construction_point", {"type": "tres_planos", "references": ["XY", "XZ", "YZ"]}))


def _caso_sup_extruir(sesion):
    ok(api.llamar(sesion, "create_sketch", {}))
    ok(api.llamar(sesion, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 5, "y2": 5}))
    ok(api.llamar(sesion, "create_surface_extrude", {"profiles": {"sketch": "Boceto1", "profile": "all"}, "distance": "5 mm"}))


def _caso_sup_revolucion(sesion):
    ok(api.llamar(sesion, "create_sketch", {"plane": "XZ"}))
    ok(api.llamar(sesion, "draw_rectangle", {"x1": 2, "y1": 0, "x2": 6, "y2": 8}))
    ok(api.llamar(sesion, "create_surface_revolve", {"profiles": {"sketch": "Boceto1", "profile": "all"}, "axis": "Z", "angle": "360 deg"}))


def _caso_sup_tuberia(sesion):
    ok(api.llamar(sesion, "create_sketch", {"plane": "XZ"}))
    ok(api.llamar(sesion, "draw_line", {"start_x": 0, "start_y": 0, "end_x": 10, "end_y": 0}))
    ok(api.llamar(sesion, "create_surface_pipe", {"path": {"sketch": "Boceto1", "curve": 3}}))


def _caso_recortar_sup(sesion):
    ok(api.llamar(sesion, "create_surface_box", {"length": 10, "width": 10, "height": 10}))
    ok(api.llamar(sesion, "trim_surface", {"surface": "Cuerpo1", "tool": "XY", "remove_point": [0, 0, 0]}))


def _caso_invertir_normal(sesion):
    ok(api.llamar(sesion, "create_surface_box", {"length": 10, "width": 10, "height": 10}))
    ok(api.llamar(sesion, "reverse_surface_normal", {"bodies": "Cuerpo1"}))


def _caso_pestana(sesion):
    ok(api.llamar(sesion, "create_sketch", {}))
    ok(api.llamar(sesion, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 20, "y2": 20}))
    ok(api.llamar(sesion, "create_base_flange", {"sketch": "Boceto1", "profile": "all"}))


def _caso_patron_plano(sesion):
    ok(api.llamar(sesion, "create_sketch", {}))
    ok(api.llamar(sesion, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 20, "y2": 20}))
    ok(api.llamar(sesion, "create_base_flange", {"sketch": "Boceto1", "profile": "all"}))
    ok(api.llamar(sesion, "create_flat_pattern", {"face": ">Z"}))


def _caso_sup_solevacion(sesion):
    ok(api.llamar(sesion, "create_sketch", {}))
    ok(api.llamar(sesion, "draw_circle", {"center_x": 0, "center_y": 0, "radius": 5}))
    ok(api.llamar(sesion, "create_sketch", {"plane": "XZ"}))
    ok(api.llamar(sesion, "draw_circle", {"center_x": 0, "center_y": 0, "radius": 3}))
    ok(api.llamar(sesion, "create_surface_loft", {"profiles": [{"sketch": "Boceto1", "profile": "all"}, {"sketch": "Boceto2", "profile": "all"}]}))


def _caso_multitransformar(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10}))
    ok(api.llamar(sesion, "multi_transform", {"bodies": "Cuerpo1", "transforms": [{"type": "rectangular", "axis": "x", "count": 2, "spacing": 15}]}))


def _caso_desmoldeo(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "draft", {"faces": ">X", "angle": 5, "neutral": "XY"}))


def _caso_dividir_cara(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "split_face", {"faces": ">Z", "tool": "XZ"}))


def _caso_desfase_aristas(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "offset_edges", {"edges": ">Z", "distance": "2 mm"}))


def _caso_parche(sesion):
    ok(api.llamar(sesion, "create_surface_box", {"length": 10, "width": 10, "height": 10}))
    ok(api.llamar(sesion, "create_patch", {"boundary": ">Z"}))


def _caso_relleno_contorno(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "create_boundary_fill", {"tools": ["Cuerpo1", "XY"]}))


def _caso_volumen_fluido(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "create_fluid_volume", {"bodies": "Cuerpo1", "volume_type": "external"}))


def _caso_regla_plastico(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "create_component", {"bodies": ["Cuerpo1"], "name": "Comp1"}))
    ok(api.llamar(sesion, "assign_plastic_rule", {"component": "Comp1"}))


def _caso_repujado(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "create_sketch", {}))
    ok(api.llamar(sesion, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 5, "y2": 5}))
    ok(api.llamar(sesion, "create_emboss", {"sketch": "Boceto1", "faces": ">Z", "depth": 2}))


def _caso_apoyo(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 40, "width": 20, "height": 10, "anchor": "corner"}))
    ok(api.llamar(sesion, "shell", {"body": "Cuerpo1", "faces": ">Z", "thickness": 2}))
    ok(api.llamar(sesion, "create_sketch", {"plane": "XY"}))
    ok(api.llamar(sesion, "draw_rectangle", {"x1": 10, "y1": 6, "x2": 20, "y2": 16}))
    ok(api.llamar(sesion, "create_rest", {"sketch": "Boceto1", "body": "Cuerpo1"}))
    # caja 40x20x10 vaciada a 2 mm (3392) más el apoyo de 10x10 que llena el hueco hasta la tapa (8 mm): 4192
    assert ok(api.llamar(sesion, "get_physical_properties", {}))["total"]["volume"] == pytest.approx(4192, abs=1)


def _caso_empalme(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "fillet", {"edges": "|Z", "radius": 2}))


def _caso_chaflan(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 20, "width": 20, "height": 10}))
    ok(api.llamar(sesion, "chamfer", {"edges": "|Z", "distance": 1}))


def _caso_vaciado(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 30, "width": 30, "height": 20}))
    ok(api.llamar(sesion, "shell", {"body": "Cuerpo1", "faces": ">Z", "thickness": 2}))


def _caso_agujero(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 30, "width": 30, "height": 10}))
    ok(api.llamar(sesion, "create_hole", {"face": ">Z", "diameter": 8, "depth": 6}))


def _caso_simetria(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10, "x": 5}))
    ok(api.llamar(sesion, "mirror", {"bodies": ["Cuerpo1"], "plane": "YZ"}))


def _caso_patron(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10}))
    ok(api.llamar(sesion, "rectangular_pattern", {"bodies": ["Cuerpo1"], "x_count": 2, "x_spacing": 15, "y_count": 1, "y_spacing": 15}))


def _caso_escala(sesion):
    ok(api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10}))
    ok(api.llamar(sesion, "scale_body", {"bodies": ["Cuerpo1"], "factor": 1.5}))


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
CASOS["eje"] = _caso_eje
CASOS["punto"] = _caso_punto
CASOS["sup_extruir"] = _caso_sup_extruir
CASOS["sup_revolucion"] = _caso_sup_revolucion
CASOS["sup_tuberia"] = _caso_sup_tuberia
CASOS["recortar_sup"] = _caso_recortar_sup
CASOS["invertir_normal"] = _caso_invertir_normal
CASOS["pestana"] = _caso_pestana
CASOS["patron_plano"] = _caso_patron_plano
CASOS["sup_solevacion"] = _caso_sup_solevacion
CASOS["multitransformar"] = _caso_multitransformar
CASOS["desmoldeo"] = _caso_desmoldeo
CASOS["dividir_cara"] = _caso_dividir_cara
CASOS["desfase_aristas"] = _caso_desfase_aristas
CASOS["parche"] = _caso_parche
CASOS["relleno_contorno"] = _caso_relleno_contorno
CASOS["volumen_fluido"] = _caso_volumen_fluido
CASOS["regla_plastico"] = _caso_regla_plastico
CASOS["repujado"] = _caso_repujado
CASOS["apoyo"] = _caso_apoyo

_PENDIENTES_RAW = sorted(set(TIPOS_OPERACION.keys()) - set(CASOS.keys()))


def _razon_pendiente(t):
    tl = t.lower()
    if "importar" in tl:
        return "requiere un archivo externo (STEP/IGES/OBJ/STL)"
    if "chapa" in tl or "pleg" in tl or "doblad" in tl or "despleg" in tl or "unir_pleg" in tl:
        return "requiere chapa/plegado previo"
    if "malla" in tl or "remall" in tl or "suaviz" in tl or "reducir_malla" in tl or "separar_malla" in tl or "limpiar_malla" in tl or "reparar_malla" in tl or "convertir_malla" in tl or "vaciado_malla" in tl or "escalar_malla" in tl or "invertir_normal_malla" in tl or "grupos_caras" in tl or "grupo_caras" in tl:
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
    if "derivacion" in tl:
        return "requiere otro archivo .omnicad como origen: el paso lo relee al recalcular"
    if "cortar_plano" in tl:
        return "requiere plano/corte especifico"
    if t == "boceto":
        return "crea un boceto vacío: no es geometría 3D verificable con check_geometry"
    if t == "division_silueta":
        return "requiere una cara con silueta para dividir"
    if t == "grampa":
        return "requiere marcos (puntos, normales y brazos) del boceto y dos cuerpos"
    if t == "insertar_diseno":
        return "requiere un archivo .omnicad externo"
    if t == "red":
        return "requiere curvas abiertas dibujadas sobre un cuerpo"
    return "caso minimo no armado en esta tanda (requiere geometria o referencias especificas)"


PENDIENTES = {t: _razon_pendiente(t) for t in _PENDIENTES_RAW}


def test_todos_los_tipos_tienen_caso_o_razon():
    tipos = set(TIPOS_OPERACION.keys())
    casos_keys = set(CASOS.keys())
    pend_keys = set(PENDIENTES.keys())
    assert casos_keys.union(pend_keys) == tipos
    assert casos_keys.intersection(pend_keys) == set()
    assert len(casos_keys) >= 57                 # piso: 37 + 20 nuevos (H-37)


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
