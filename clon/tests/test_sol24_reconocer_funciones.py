"""SOL-24: reconocer funciones (Find Features) en un cuerpo sin historial y rehacerlas en el timeline."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import reconocer_funciones as rf

LOCALES = ("hole", "fillet", "chamfer")


def _tipos(r):
    return sorted(f["type"] for f in r["features"])


def _bloque():
    return geo.caja(40, 40, 20, (-20, -20, 0))


def _agujerear(forma, *centros, radio=2):
    for x, y in centros:
        forma = geo.booleano(forma, geo.cilindro(radio, 30, (x, y, -5)), "cortar")
    return forma


def test_agujero_pasante_y_ciego():
    pasante = _agujerear(_bloque(), (0, 0), radio=4)
    (h,) = rf.reconocer_funciones(pasante, LOCALES)["features"]
    assert h["type"] == "hole" and h["through"] and h["diameter"] == pytest.approx(8) and h["depth"] == pytest.approx(20)
    ciego = geo.booleano(_bloque(), geo.cilindro(3, 10, (0, 0, 10)), "cortar")
    (h,) = rf.reconocer_funciones(ciego, LOCALES)["features"]
    assert h["type"] == "hole" and not h["through"] and h["depth"] == pytest.approx(10)
    assert len(h["faces"]) == 2 and h["entry_point"] == pytest.approx([0, 0, 20])     # pared + fondo; entra por arriba


def test_avellanado_une_dos_agujeros_coaxiales():
    pieza = geo.booleano(_agujerear(_bloque(), (0, 0), radio=3), geo.cilindro(6, 6, (0, 0, 14)), "cortar")
    r = rf.reconocer_funciones(pieza, LOCALES)
    assert _tipos(r) == ["hole", "hole"]
    assert all("counterbore_with" in f for f in r["features"])
    ancho = next(f for f in r["features"] if f["diameter"] == pytest.approx(12))
    assert not ancho["through"] and len(ancho["faces"]) == 2                     # el escalón es su fondo


def test_empalme_y_chaflan_y_cuerpo_liso():
    assert rf.reconocer_funciones(_bloque(), LOCALES)["features"] == []           # una caja lisa no tiene funciones locales
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 20, "name": "Caja"})
    api.llamar(s, "fillet", {"edges": "|Z", "radius": 4})
    r = api.llamar(s, "find_features", {"types": list(LOCALES)})["result"]
    assert r["summary"] == {"hole": 0, "fillet": 4, "chamfer": 0}
    assert all(f["radius"] == pytest.approx(4) and f["convex"] for f in r["features"] if f["type"] == "fillet")
    t = api.Sesion()
    api.llamar(t, "create_box", {"length": 40, "width": 40, "height": 20, "name": "Caja"})
    api.llamar(t, "chamfer", {"edges": ">Z", "distance": 2})
    r = api.llamar(t, "find_features", {"types": list(LOCALES)})["result"]
    assert r["summary"]["chamfer"] == 4 and r["summary"]["fillet"] == 0
    f = r["features"][0]
    assert f["angle"] == pytest.approx(45, abs=1) and f["width"] == pytest.approx(2.828, rel=1e-2)
    assert f["distance"] == pytest.approx(2, rel=1e-6)


def test_un_cilindro_macizo_no_es_un_agujero_pero_es_extrusion_y_revolucion():
    r = rf.reconocer_funciones(geo.cilindro(10, 10))
    assert _tipos(r) == ["extrude", "revolve"]
    ext, rev = sorted(r["features"], key=lambda f: f["type"])
    assert ext["distance"] == pytest.approx(10) and ext["profile_area"] == pytest.approx(math.pi * 100)
    assert abs(ext["direction"][2]) == pytest.approx(1) and rev["angle"] == pytest.approx(360)


def test_extrusion_con_agujeros_pasantes_y_no_con_uno_ciego():
    pieza = _agujerear(_bloque(), (0, 0), radio=4)
    (ext,) = [f for f in rf.reconocer_funciones(pieza)["features"] if f["type"] == "extrude"]
    assert ext["distance"] == pytest.approx(20)
    assert ext["profile_area"] * ext["distance"] == pytest.approx(geo.volumen(pieza), rel=1e-6)
    ciego = geo.booleano(_bloque(), geo.cilindro(3, 10, (0, 0, 10)), "cortar")
    assert "extrude" not in _tipos(rf.reconocer_funciones(ciego))                 # el fondo del agujero corta el prisma


def test_revolucion_parcial_mide_el_angulo():
    cuarto = geo.booleano(geo.cilindro(10, 10), geo.caja(20, 20, 20, (0, 0, -5)), "intersecar")
    (rev,) = [f for f in rf.reconocer_funciones(cuarto)["features"] if f["type"] == "revolve"]
    assert rev["angle"] == pytest.approx(90) and len(rev["faces"]) == 2
    tres_cuartos = geo.booleano(geo.cilindro(10, 10), geo.caja(20, 20, 20, (0, 0, -5)), "cortar")
    (rev,) = [f for f in rf.reconocer_funciones(tres_cuartos)["features"] if f["type"] == "revolve"]
    assert rev["angle"] == pytest.approx(270)
    assert "revolve" not in _tipos(rf.reconocer_funciones(_bloque()))


def test_patrones_y_simetria_de_agujeros():
    fila = rf.reconocer_funciones(_agujerear(_bloque(), (-10, 5), (0, 5), (10, 5)), ("rectangular_pattern",))
    (p,) = fila["features"]
    assert p["count"] == 3 and p["directions"][0]["step"] == pytest.approx(10) and len(p["faces"]) == 3
    rejilla = rf.reconocer_funciones(_agujerear(_bloque(), (-10, -10), (10, -10), (-10, 10), (10, 10)),
                                     ("rectangular_pattern", "circular_pattern"))
    (p,) = rejilla["features"]
    assert p["type"] == "rectangular_pattern" and [d["count"] for d in p["directions"]] == [2, 2]
    assert all(d["step"] == pytest.approx(20) for d in p["directions"])
    brida = geo.cilindro(30, 10)
    for k in range(6):
        a = 2 * math.pi * k / 6
        brida = geo.booleano(brida, geo.cilindro(3, 30, (20 * math.cos(a), 20 * math.sin(a), -5)), "cortar")
    (p,) = rf.reconocer_funciones(brida, ("circular_pattern",))["features"]
    assert p["count"] == 6 and p["angle_step"] == pytest.approx(60) and p["axis_point"][:2] == pytest.approx([0, 0])
    par = rf.reconocer_funciones(_agujerear(_bloque(), (-12, 3), (12, 3)), ("mirror", "rectangular_pattern"))
    (p,) = par["features"]
    assert p["type"] == "mirror" and p["plane_normal"] == pytest.approx([1, 0, 0]) and p["count"] == 2
    distintos = _agujerear(_agujerear(_bloque(), (-12, 3)), (12, 3), radio=3)
    assert rf.reconocer_funciones(distintos, ("mirror",))["features"] == []        # dos agujeros distintos no se reflejan


def test_herramienta_pide_un_solido_y_valida_tipos():
    s = api.Sesion()
    assert not api.llamar(s, "find_features", {})["ok"]
    api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})
    assert not api.llamar(s, "find_features", {"types": ["sweep"]})["ok"]
    solo = api.llamar(s, "find_features", {"types": ["hole"]})["result"]
    assert solo["features"] == []
    todo = api.llamar(s, "find_features", {})["result"]
    assert todo["summary"]["extrude"] == 1 and set(todo["summary"]) == set(rf.TIPOS)
    (ext,) = todo["features"]
    assert all(i.endswith(("/F1", "/F2", "/F3", "/F4", "/F5", "/F6")) for i in ext["faces"])
    assert not api.llamar(s, "rebuild_features", {"max_features": 0})["ok"]


# ---------------------------------------------------------------- rehacer en el timeline
def _importada(tmp_path):
    """Una pieza con empalmes, chaflanes, un agujero ciego y uno abocardado, exportada a STEP e importada (sin historial)."""
    s = api.Sesion()
    for nombre, args in [("create_box", {"length": 40, "width": 40, "height": 20, "name": "Caja"}),
                         ("fillet", {"edges": "|Z", "radius": 4}), ("chamfer", {"edges": "<Z", "distance": 1.5}),
                         ("create_hole", {"face": ">Z", "points": [[8, 8]], "diameter": 6, "depth": 8}),
                         ("create_hole", {"face": ">Z", "points": [[-8, -8]], "diameter": 5, "through_all": True,
                                          "hole_type": "counterbore", "counterbore_diameter": 10,
                                          "counterbore_depth": 4})]:
        assert api.llamar(s, nombre, args)["ok"]
    ruta = tmp_path / "pieza.step"
    assert api.llamar(s, "export", {"path": str(ruta)})["ok"]
    t = api.Sesion()
    assert api.llamar(t, "insert_file", {"path": str(ruta)})["ok"]
    return t


def _cuerpo(s):
    (c,) = s.doc.estado_final.cuerpos.values()
    return c


def test_rehace_agujeros_empalmes_y_chaflanes_de_una_pieza_importada(tmp_path):
    s = _importada(tmp_path)
    antes = _cuerpo(s).forma
    v0, bb0 = geo.volumen(antes), geo.caja_envolvente(antes)
    pasos0 = len(s.doc.operaciones)
    r = api.llamar(s, "rebuild_features", {})
    assert r["ok"], r
    r = r["result"]
    assert r["not_rebuilt"] == [], r["not_rebuilt"]
    assert r["summary"] == {"hole": 2, "fillet": 4, "chamfer": 1}                # el chaflán da la vuelta a los empalmes
    abocardado = next(f for f in r["rebuilt"] if f.get("counterbore_diameter"))
    assert abocardado["diameter"] == pytest.approx(5) and abocardado["counterbore_depth"] == pytest.approx(4)
    assert abocardado["through"]
    tipos = [o.TIPO for o in s.doc.operaciones[pasos0:]]
    assert tipos.count("borrar_caras") == 7 and tipos.count("agujero") == 2
    assert tipos.count("empalme") == 4 and tipos.count("chaflan") == 1
    despues = _cuerpo(s).forma
    assert geo.es_valida(despues) and geo.volumen(despues) == pytest.approx(v0, rel=1e-6)
    for a, b in zip(geo.caja_envolvente(despues), bb0, strict=True):
        assert a == pytest.approx(b, abs=1e-6)
    assert all(r.estado != "error" for r in s.doc.resultados)
    # los pasos nuevos son paramétricos: el radio del empalme se edita como cualquier otro
    empalme = next(o for o in s.doc.operaciones if o.TIPO == "empalme")
    assert api.llamar(s, "edit_feature", {"feature": empalme.id, "params": {"radio": "2 mm"}})["ok"]
    assert geo.volumen(_cuerpo(s).forma) > v0
    # todo el rehacer es UN paso de deshacer
    assert api.llamar(s, "undo", {})["ok"] and api.llamar(s, "undo", {})["ok"]
    assert len(s.doc.operaciones) == pasos0
    assert geo.volumen(_cuerpo(s).forma) == pytest.approx(v0, rel=1e-9)


def test_lo_que_no_se_puede_rehacer_queda_listado_y_el_documento_igual():
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 20, "name": "Caja"})["ok"]
    assert api.llamar(s, "create_cylinder", {"height": 6, "radius": 3, "z": 7, "operation": "cut",
                                             "target": "Caja"})["ok"]          # un hueco cerrado adentro del bloque
    pasos0 = len(s.doc.operaciones)
    v0 = geo.volumen(_cuerpo(s).forma)
    r = api.llamar(s, "rebuild_features", {"types": ["hole"]})["result"]
    assert r["rebuilt"] == [] and len(r["not_rebuilt"]) == 1 and r["not_rebuilt"][0]["reason"]
    assert len(s.doc.operaciones) == pasos0 and geo.volumen(_cuerpo(s).forma) == pytest.approx(v0, rel=1e-9)


def test_dialogo_lista_lo_encontrado_y_rehace():
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.comando import ContextoComando, ErrorComando, hit_desde_ref
    from omnicad.ui.comandos.inspeccionar import ReconocerFunciones
    QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="20"))
    cmd, ctx = ReconocerFunciones(), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    assert "Elegí" in cmd._resultado(v, ctx)
    v["cuerpo"] = [hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)]
    assert "Extrusión: 1 (" in cmd._resultado(v, ctx)                 # una caja es un prisma en cualquier dirección
    v.update(extrusion=False, revolucion=False)
    assert "No se encontró" in cmd._resultado(v, ctx)
    cmd.aplicar(v, ctx)                                            # sin «Rehacer», Aceptar no toca el documento
    assert len(doc.operaciones) == 1
    v["rehacer"] = True
    with pytest.raises(ErrorComando):
        cmd.aplicar(dict(v, agujeros=False, empalmes=False, chaflanes=False), ctx)
    s = api.Sesion(doc)
    api.llamar(s, "fillet", {"edges": "|Z", "radius": 3})
    v["cuerpo"] = [hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)]
    assert "Empalmes: 4 (R3)" in cmd._resultado(v, ctx)
    cmd.aplicar(v, ctx)
    assert [o.TIPO for o in doc.operaciones].count("empalme") == 5
    v.update(agujeros=False, empalmes=False, chaflanes=False, simetria=False, patron_circular=False,
             patron_rectangular=False)
    assert "Marcá" in cmd._resultado(v, ctx)


def test_rehacer_un_prisma_como_boceto_y_extrusion():
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 40, "width": 20, "height": 5, "name": "Placa"})
    api.llamar(s, "create_hole", {"face": ">Z", "diameter": 4, "through_all": True, "points": [[0, 0]]})
    api.llamar(s, "create_hole", {"face": ">Z", "diameter": 3, "through_all": True, "points": [[10, 0]]})
    antes = geo.volumen(s.cuerpo("Placa").forma)
    r = api.llamar(s, "rebuild_features", {"types": ["extrude"]})
    assert r["ok"], r
    assert [f["type"] for f in r["result"]["rebuilt"]] == ["extrude"] and not r["result"]["not_rebuilt"]
    cuerpos = list(s.doc.estado_final.cuerpos.values())
    assert [c.nombre for c in cuerpos] == ["Placa"]
    assert geo.es_valida(cuerpos[0].forma) and geo.volumen(cuerpos[0].forma) == pytest.approx(antes, rel=1e-6)
    pasos = [p["type"] for p in api.llamar(s, "get_timeline")["result"]["steps"]]
    assert pasos[-2:] == ["boceto", "extrusion"] or "extrusion" in pasos
    api.llamar(s, "undo")                                                       # un solo paso de deshacer
    assert geo.volumen(s.cuerpo("Placa").forma) == pytest.approx(antes, rel=1e-6)
    sin_prisma = api.Sesion()
    api.llamar(sin_prisma, "create_box", {"length": 40, "width": 20, "height": 5, "name": "Caja"})
    api.llamar(sin_prisma, "fillet", {"edges": ">Z", "radius": 1})
    r = api.llamar(sin_prisma, "rebuild_features", {"types": ["extrude"]})
    assert r["ok"] and not r["result"]["rebuilt"]                               # un cuerpo con empalmes no es un prisma
