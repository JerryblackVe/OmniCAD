# -*- coding: utf-8 -*-
"""Hallazgos de la prueba de tortura del 2026-10-17 (docs/informe_tortura_2026-10-17.md), uno por bug (T-01 … T-18):
cuelgues del kernel que ahora se cortan por tiempo, referencias que se perdían, vaciados imposibles, topes de rango,
avisos que faltaban y mensajes que culpaban a lo que no era."""
import json
import time
import zipfile

import numpy as np
import pytest

from omnicad import api
from omnicad.io_archivos import dxf, proyecto
from omnicad.nucleo import aislado
from omnicad.nucleo import dibujo as nd
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as rf
from omnicad.nucleo import revision as rv
from omnicad.nucleo import solidos_modificar as sm
from omnicad.restricciones import boceto as bc
from omnicad.timeline import parametros as pa
from omnicad.timeline.documento import Documento


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(s, nombre, **args):
    return ok(api.llamar(s, nombre, args))


def falla(s, nombre, kind=None, **args):
    receta = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and (kind is None or r["error_kind"] == kind), r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == receta          # atómica: el documento no cambió
    return r


def _solevado():
    """Rectángulo 24 × 24 en z = 0 solevado a un círculo de radio 7 en z = 30: cinco caras B-spline."""
    s = api.Sesion()
    llamar(s, "sketch_from_spec", name="A", plane="XY",
           entities=[{"type": "rectangle", "id": "R", "center": [0, 0], "width": 24, "height": 24}])
    llamar(s, "create_construction_plane", plane="XY", offset=30, name="P2")
    llamar(s, "sketch_from_spec", name="B", plane="P2",
           entities=[{"type": "circle", "id": "C", "center": [0, 0], "radius": 7}])
    llamar(s, "loft", sketches=["A", "B"])
    return s


def _forma(s):
    return next(iter(s.doc.estado_final.cuerpos.values())).forma


def _se_agoto(*_a, **_k):
    raise aislado.TiempoAgotado("pasó de 10 s y se cortó")


def test_t12_reached_distingue_un_residuo_submilimetrico_de_un_destino_imposible():
    """Un extremo acotado queda en x=10 sin estar fijado: residuo determinista, sin simular el solver."""
    s = api.Sesion()
    r = llamar(s, "sketch_from_spec", entities=[
        {"type": "line", "id": "L", "start": [0, 0], "end": [10, 0]}],
        constraints=[{"type": "fix", "entities": ["L.start"]}, {"type": "horizontal", "entities": ["L"]}],
        dimensions=[{"type": "distance", "entities": ["L"], "value": 10}])
    punto = r["handles"]["L.end"]
    for delta, esperado in ((0.0005, True), (0.002, False)):
        r = llamar(s, "move_sketch_point", point=punto, x=10 + delta, y=0)
        assert r["reached"] is esperado
        assert r["point"]["x"] == pytest.approx(10, abs=1e-4)


# ---------------------------------------------------------------- T-01 · autointersecciones sin congelar la app
def test_t01_las_formas_libres_se_revisan_en_un_proceso_aparte():
    s = _solevado()
    cuerpo = llamar(s, "check_geometry")["bodies"][0]
    assert cuerpo["self_intersections"] == 0 and cuerpo["issues"] == []          # el hijo corrió y no halló nada


def test_t01_sin_tiempo_las_autointersecciones_quedan_omitidas_con_aviso():
    informe = rv.revisar(_forma(_solevado()), hasta=time.monotonic() - 1)
    assert informe["autointersecciones"] is None and informe["autointersecciones_completo"] is False
    assert [p["tipo"] for p in informe["problemas"]] == ["autointerseccion_omitida"] and informe["avisos"] == 1


def test_t01_check_geometry_cuenta_el_aviso_si_el_hijo_se_cuelga(monkeypatch):
    monkeypatch.setattr(aislado, "correr", _se_agoto)
    cuerpo = llamar(_solevado(), "check_geometry")["bodies"][0]
    assert cuerpo["self_intersections"] is None and cuerpo["warnings"] == 1
    assert [(i["kind"], i["severity"]) for i in cuerpo["issues"]] == [("self_intersection_skipped", "warning")]


def test_t01_el_hijo_se_mata_al_pasar_el_tope():
    forma = _forma(_solevado())
    with pytest.raises(aislado.TiempoAgotado, match=r"pasó de 0,05 s y se cortó"):
        aislado.correr("autointersecciones", forma, 0.05, limite=5)         # python tarda más en arrancar
    with pytest.raises(ValueError, match="desconocida"):
        aislado.correr("nada", forma, 1)


def test_t01_las_formas_analiticas_no_pagan_el_proceso_aparte(monkeypatch):
    monkeypatch.setattr(aislado, "correr", _se_agoto)                       # si se usara, el resultado sería None
    assert rv.revisar(geo.caja(10, 20, 30))["autointersecciones"] == 0


@pytest.mark.parametrize("programa", ["OmniCAD.exe", "omnicad-cli.exe", "omnicad-mcp.exe"])
def test_t01_empaquetado_lanza_la_app_desde_cualquiera_de_los_tres_programas(monkeypatch, tmp_path, programa):
    monkeypatch.setattr(aislado.sys, "frozen", True, raising=False)
    monkeypatch.setattr(aislado.sys, "platform", "win32")
    monkeypatch.setattr(aislado.sys, "executable", str(tmp_path / programa))
    assert aislado._comando("autointersecciones", tmp_path) == [
        str(tmp_path / "OmniCAD.exe"), "--tarea-aislada", "autointersecciones", str(tmp_path)]


# ---------------------------------------------------------------- T-02 · líneas ocultas exactas con tope de tiempo
def test_t02_la_proyeccion_exacta_de_una_forma_libre_corre_aparte_y_da_lo_mismo():
    forma, marco, info = _forma(_solevado()), nd.marco_orientacion("frontal"), {}
    aparte = nd.proyectar(forma, marco, info=info)
    assert info == {"metodo": "exacto"}
    directo = nd._hlr(forma, marco, "exacto", 0.05)
    assert {c: len(v) for c, v in aparte.items() if c in ("visibles", "silueta")} == \
        {c: len(directo[c]) for c in ("visibles", "silueta")}
    assert all(isinstance(p, np.ndarray) for ls in aparte.values() for p in ls)


def test_t02_si_el_exacto_no_termina_sigue_el_rapido_o_falla_si_se_pidio_exacto(monkeypatch):
    monkeypatch.setattr(aislado, "correr", _se_agoto)
    forma, marco, info = _forma(_solevado()), nd.marco_orientacion("frontal"), {}
    assert nd.proyectar(forma, marco, info=info)["visibles"] and info["metodo"] == "rapido" and "10 s" in info["motivo"]
    with pytest.raises(geo.ErrorGeometria, match="no terminó"):
        nd.proyectar(forma, marco, respaldo=False)


def test_t02_export_hidden_line_svg_avisa_el_respaldo_y_pide_exacto_a_pedido(tmp_path, monkeypatch):
    s = _solevado()
    monkeypatch.setattr(aislado, "correr", _se_agoto)
    r = api.llamar(s, "export_hidden_line_svg", {"path": str(tmp_path / "a.svg"), "view": "front"})
    assert r["ok"] and r["result"]["method"] == "fast" and any("rápido" in a for a in r["avisos"])
    r = api.llamar(s, "export_hidden_line_svg", {"path": str(tmp_path / "b.svg"), "method": "exact"})
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED" and not (tmp_path / "b.svg").exists()
    r = api.llamar(s, "export_hidden_line_svg", {"path": str(tmp_path / "c.svg"), "method": "fast"})
    assert r["ok"] and r["result"]["method"] == "fast" and not r["avisos"]


# ---------------------------------------------------------------- T-05 · unión del contacto coplanar
def test_t05_unir_por_api_elimina_el_contacto_coplanar():
    s = api.Sesion()
    llamar(s, "create_sphere", radius=10)
    llamar(s, "tessellate", bodies="Cuerpo1", refinement="low", keep_original=False)
    cuerpo = next(c for c in s.doc.estado_final.cuerpos.values() if c.tipo == "malla")
    area, volumen = cuerpo.forma.area(), cuerpo.forma.volumen()
    llamar(s, "plane_cut_mesh", bodies=cuerpo.id, plane="XY", kind="split_body")
    a, b = list(s.doc.estado_final.cuerpos)
    r = api.llamar(s, "combine_meshes", {"target": a, "tools": b, "operation": "join"})
    ok(r)
    assert not r["avisos"]
    m = next(iter(s.doc.estado_final.cuerpos.values())).forma
    assert m.es_cerrada() and m.area() == pytest.approx(area, rel=1e-7)
    assert m.volumen() == pytest.approx(volumen, rel=1e-7)


# ---------------------------------------------------------------- T-03 · referencias que sobreviven a cambios grandes
def _caja_redondeada():
    """Placa de 120 × 90 × 50 con las cuatro esquinas redondeadas por `sketch_fillet` (radio = ancho / 20)."""
    s = api.Sesion()
    llamar(s, "create_parameter", name="ancho", expression="120 mm")
    llamar(s, "create_parameter", name="radio_esq", expression="ancho / 20")
    llamar(s, "sketch_from_spec", name="P", plane="XY", entities=[
        {"type": "rectangle", "id": "R", "center": [0, 0], "width": 120, "height": 90},
        {"type": "line", "id": "ax", "start": [0, -80], "end": [0, 80], "construction": True},
        {"type": "line", "id": "ay", "start": [-90, 0], "end": [90, 0], "construction": True}],
        dimensions=[{"type": "horizontal", "entities": ["R.bottom"], "value": "ancho"},
                    {"type": "vertical", "entities": ["R.right"], "value": 90}],
        constraints=[{"type": "fix", "entities": ["ax", "ay"]},
                     {"type": "symmetry", "entities": ["R.c1", "R.c2", "ax"]},
                     {"type": "symmetry", "entities": ["R.c1", "R.c4", "ay"]}])
    for a, b in ((5, 6), (6, 7), (7, 8), (8, 5)):
        llamar(s, "sketch_fillet", sketch="P", entity1=a, entity2=b, radius="radio_esq")
    llamar(s, "extrude", sketch="P", profile=0, distance=50)
    return s


def _caja_con_tapa():
    s = _caja_redondeada()
    llamar(s, "shell", body="Cuerpo1", faces=">Z", thickness=4)
    llamar(s, "chamfer", edges=">Z", distance=1)
    return s


def test_t03_el_chaflan_del_borde_tras_un_vaciado_sobrevive_a_un_cambio_de_cota_del_29_por_ciento():
    """Con `ancho` de 155 en adelante el chaflán perdía la arista (la firma geométrica no distinguía el lazo interior
    del exterior); la posición de la arista entre las del cuerpo (misma topología) la reconoce."""
    s = _caja_con_tapa()
    for ancho in (150, 155, 160, 120):
        llamar(s, "set_parameter", name="ancho", expression=f"{ancho} mm")


def test_t03_el_agujero_sobre_la_cara_de_un_boss_sigue_a_la_cara_cuando_el_boss_se_achica():
    s = api.Sesion()
    llamar(s, "create_parameter", name="alto_boss", expression="46.5 mm")
    llamar(s, "sketch_from_spec", name="P", plane="XY",
           entities=[{"type": "rectangle", "id": "R", "center": [0, 0], "width": 120, "height": 90}])
    llamar(s, "extrude", sketch="P", profile=0, distance=50)
    llamar(s, "shell", body="Cuerpo1", faces=">Z", thickness=4)
    llamar(s, "create_cylinder", height="alto_boss", radius=5, x=48, y=33, z=3.5, operation="join", target="Cuerpo1")
    llamar(s, "rectangular_pattern", features=["Cilindro1"], x_count=2, x_spacing=-96, y_count=2, y_spacing=-66)
    llamar(s, "create_hole", diameter=3, face="nearest:[48,33,50]", depth=8, body="Cuerpo1")
    for alto in (40, 30, 20, 10, 46.5):
        llamar(s, "set_parameter", name="alto_boss", expression=f"{alto} mm")


def test_t03_la_referencia_guarda_la_posicion_solo_si_conoce_el_cuerpo():
    forma = geo.caja(10, 20, 30)
    cara = rf.subformas(forma, "cara")[3]
    con_forma = rf.referencia("c", cara, forma)
    assert con_forma["indice"] == 3 and con_forma["de"] == 6
    assert "indice" not in rf.referencia("c", cara, caja=geo.caja_envolvente(forma))      # los .omnicad viejos igual
    assert rf.resolver(forma, con_forma).IsSame(cara)
    mapa = rf.mapa_de_subformas(forma, "cara")                        # el visor arma el mapa una vez y lo reparte
    assert rf.referencia("c", cara, caja=geo.caja_envolvente(forma), mapa=mapa) == con_forma


# ---------------------------------------------------------------- T-04 / T-13 · vaciados que el kernel no podía
def _extremos(forma):
    """Caras planas de arriba (z = 30) y de abajo (z = 0) del solevado."""
    planas = [c for c in geo.caras(forma) if rf.firma_cara(c)["geom"] == "plano"]
    return [c for c in planas if round(rf.firma_cara(c)["centro"][2]) in (0, 30)]


def test_t04_el_vaciado_de_un_solevado_de_caras_bspline_ya_no_falla():
    forma = _forma(_solevado())
    volumen = geo.volumen_exacto(forma)
    for quitar, espesor in (([], 1.0), (_extremos(forma), 1.2), (_extremos(forma)[:1], 0.2)):
        hueco = sm.vaciado(forma, quitar, espesor_interior=espesor)
        assert geo.es_valida(hueco) and 0 < geo.volumen_exacto(hueco) < volumen, (quitar, espesor)
    pared = sm.vaciado(forma, [], espesor_interior=1.0)
    assert geo.volumen_exacto(pared) == pytest.approx(2592.8, rel=1e-3)           # 10.324,4 − 7.731,6 del desfase


def test_t04_shell_exterior_de_la_herramienta_sobre_el_solevado():
    s = _solevado()
    llamar(s, "shell", body="Cuerpo1", faces=[">Z", "<Z"], thickness=1.2, direction="outside")
    forma = _forma(s)
    assert geo.es_valida(forma) and rv.es_estanca(forma) and len(geo.solidos(forma)) == 1
    assert geo.volumen_exacto(forma) == pytest.approx(2680.5633, rel=0.01)


@pytest.mark.parametrize("abertura,casquetes,z_min,z_max", [
    ("ambas", 803.3921 + 238.2443, 0.0, 30.0),
    ("inferior", 803.3921, 0.0, 31.2),
    ("superior", 238.2443, -1.2, 30.0),
])
def test_t04_vaciado_exterior_bspline_valido_y_estanco(abertura, casquetes, z_min, z_max):
    forma = _forma(_solevado())
    extremos = sorted(_extremos(forma), key=lambda c: geo.centro_masa(c, True)[2])
    quitar = extremos if abertura == "ambas" else [extremos[0 if abertura == "inferior" else 1]]
    r = sm.vaciado(forma, quitar, espesor_interior=0, espesor_exterior=1.2, direccion="exterior")
    assert geo.es_valida(r) and rv.es_estanca(r) and len(geo.solidos(r)) == 1
    # Referencia en mm³: desfase cerrado (14.046,6429) menos cuerpo (10.324,4432)
    # y casquetes recortados en las aberturas (803,3921 abajo; 238,2443 arriba).
    # A·t corresponde al desfase CERRADO: deja de ser una cota al quitar las tapas.
    esperado = 14046.6429 - geo.volumen_exacto(forma) - casquetes
    assert geo.volumen_exacto(r) == pytest.approx(esperado, rel=0.01)
    a, b = geo.caja_envolvente(r)
    assert a == pytest.approx((-13.2, -13.2, z_min), abs=1e-3)
    assert b == pytest.approx((13.2, 13.2, z_max), abs=1e-3)
    informe = rv.revisar(r)
    assert informe["autointersecciones_completo"] and informe["autointersecciones"] == 0
    assert informe["problemas"] == []
    assert geo.es_valida(forma) and geo.volumen_exacto(forma) == pytest.approx(10324.4432, rel=1e-7)


def test_t04_shell_de_la_herramienta_sobre_el_solevado():
    s = _solevado()
    antes = geo.volumen_exacto(_forma(s))
    llamar(s, "shell", body="Cuerpo1", faces=[">Z", "<Z"], thickness=1.2)
    despues = _forma(s)
    assert geo.es_valida(despues) and 0 < geo.volumen_exacto(despues) < antes / 2


def test_t13_vaciar_despues_de_un_chaflan_en_el_borde_dice_que_el_chaflan_va_despues():
    """El kernel no puede desfasar un chaflán más angosto que el espesor; antes el mensaje culpaba a «cortes o agujeros
    que cruzan la cara quitada» y la causa era el chaflán."""
    s = _caja_redondeada()
    llamar(s, "chamfer", edges=">Z", distance=1.5)
    r = falla(s, "shell", "OPERATION_FAILED", body="Cuerpo1", faces=">Z", thickness=4)
    assert "chaflán" in r["mensaje"] and "DESPUÉS del vaciado" in r["mensaje"]
    s = _caja_redondeada()                                                    # en ese orden sí anda
    llamar(s, "shell", body="Cuerpo1", faces=">Z", thickness=4)
    llamar(s, "chamfer", edges=">Z", distance=1.5)
    assert geo.es_valida(_forma(s))


def test_t13_un_caja_sin_bisel_no_recibe_el_consejo_del_chaflan():
    s = api.Sesion()
    llamar(s, "create_box", length=100, width=70, height=40)
    llamar(s, "chamfer", edges=">Z", distance=1.5)
    llamar(s, "shell", body="Cuerpo1", faces=">Z", thickness=4)              # el kernel sí puede con una caja recta
    assert geo.es_valida(_forma(s))


# ---------------------------------------------------------------- T-05 · mallas rotas con ok mudo
def _malla_abierta():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=20)
    malla = llamar(s, "tessellate", bodies="Cuerpo1", keep_original=False)["bodies_created"][0]["id"]
    llamar(s, "create_construction_plane", plane="XY", offset=10, name="PC")
    llamar(s, "plane_cut_mesh", bodies=malla, plane="PC", kind="trim", fill=False)         # corta sin tapar
    return s, malla


def test_t05_reparar_o_limpiar_una_malla_que_sigue_abierta_lo_avisa():
    s, malla = _malla_abierta()
    r = api.llamar(s, "repair_mesh", {"bodies": malla, "kind": "merge_vertices"})
    assert r["ok"] and any("borde abierta" in a for a in r["avisos"]), r
    r = api.llamar(s, "clean_mesh", {"bodies": malla, "recalculate_normals": False})
    assert r["ok"] and any("borde abierta" in a for a in r["avisos"]), r
    r = api.llamar(s, "clean_mesh", {"bodies": malla, "fill_holes": True})                  # tapa: ya no avisa
    assert r["ok"] and not any("problemas" in a for a in r["avisos"]), r


def test_t05_una_malla_cerrada_no_recibe_avisos():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=20)
    malla = llamar(s, "tessellate", bodies="Cuerpo1")["bodies_created"][0]["id"]
    r = api.llamar(s, "repair_mesh", {"bodies": malla, "kind": "stitch_and_remove"})
    assert r["ok"] and not r["avisos"], r


# ---------------------------------------------------------------- T-06 · texto sin tope
def test_t06_un_texto_demasiado_largo_o_gigante_se_rechaza():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY", name="B")
    r = falla(s, "add_text", sketch="B", text="W" * (bc.MAX_CARACTERES_TEXTO + 1), height=5)
    assert "caracteres" in r["mensaje"]
    r = falla(s, "add_text", sketch="B", text="hola", height=bc.ALTURA_MAXIMA_TEXTO + 1)
    assert "altura" in r["mensaje"]
    llamar(s, "add_text", sketch="B", text="W" * 40, height=5)                               # lo normal sigue andando


# ---------------------------------------------------------------- T-07 · rangos
def test_t07_las_longitudes_y_los_angulos_tienen_tope_al_usarse_en_un_paso():
    assert pa.LONGITUD_MAXIMA == bc.MEDIDA_MAXIMA
    assert pa.acotar(1e6, pa.LONGITUD) == 1e6 and pa.acotar(2e6, pa.ESCALAR) == 2e6
    with pytest.raises(pa.ErrorExpresion, match="1 km"):
        pa.acotar(2e6, pa.LONGITUD)
    with pytest.raises(pa.ErrorExpresion, match="ángulo"):
        pa.acotar(1e7, pa.ANGULO)
    assert pa.evaluar("2000000 mm") == 2e6                                       # el parámetro suelto puede valer más
    from omnicad.timeline.operaciones import Contexto
    with pytest.raises(pa.ErrorExpresion, match="1 km"):
        Contexto({}).evaluar("2000000 mm")


def test_t07_valores_absurdos_se_rechazan_sin_tocar_el_documento():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=20)
    llamar(s, "create_parameter", name="p", expression="10 mm")
    llamar(s, "sketch_from_spec", name="Q", plane="XY",
           entities=[{"type": "rectangle", "id": "R", "center": [50, 0], "width": 10, "height": 10}])
    llamar(s, "extrude", sketch="Q", profile=0, distance="p")                 # un paso que usa p
    r = falla(s, "set_parameter", name="p", expression="1e308 mm")
    assert "1 km" in r["mensaje"]
    falla(s, "move_body", body="Cuerpo1", translate=[1e300, 0, 0])
    falla(s, "move_body", body="Cuerpo1", rotate=[1e9, 0, 0])
    falla(s, "extrude", sketch="Q", profile=0, distance=1e12)
    falla(s, "fillet", "INVALID_ARGUMENTS", edges="|Z", radius=1e-9)
    falla(s, "chamfer", "INVALID_ARGUMENTS", edges="|Z", distance=1e-9)


def test_t07_un_parametro_suelto_de_mas_de_un_km_avisa():
    s = api.Sesion()
    llamar(s, "create_parameter", name="suelto", expression="10 mm")
    r = api.llamar(s, "set_parameter", {"name": "suelto", "expression": "1e308 mm"})
    assert r["ok"] and any("más de 1 km" in a for a in r["avisos"]), r


def test_t07_una_longitud_negativa_avisa():
    s = api.Sesion()
    llamar(s, "create_parameter", name="alto", expression="10 mm")
    r = api.llamar(s, "set_parameter", {"name": "alto", "expression": "-10 mm"})
    assert r["ok"] and any("negativo" in a for a in r["avisos"]), r
    r = api.llamar(s, "set_parameter", {"name": "alto", "expression": "5 mm"})
    assert r["ok"] and not r["avisos"]


# ---------------------------------------------------------------- T-08 · JSON hostil
def _proyecto_con_receta(tmp_path, receta):
    base = tmp_path / "base.omnicad"
    proyecto.guardar(Documento(), base)
    with zipfile.ZipFile(base) as z:
        miembros = {n: z.read(n) for n in z.namelist()}
    miembros["receta.json"] = receta
    hostil = tmp_path / "hostil.omnicad"
    with zipfile.ZipFile(hostil, "w") as z:
        for nombre, datos in miembros.items():
            z.writestr(nombre, datos)
    return hostil


def test_t08_un_json_anidado_a_100000_niveles_es_un_proyecto_danado(tmp_path):
    hostil = _proyecto_con_receta(tmp_path, b"[" * 100000 + b"]" * 100000)
    with pytest.raises(proyecto.ErrorProyecto, match="profundidad"):
        proyecto.abrir(hostil)
    r = api.llamar(api.Sesion(), "open_document", {"path": str(hostil)})
    assert not r["ok"] and r["error_kind"] == "INVALID_PROJECT"


def test_t08_un_json_roto_tambien(tmp_path):
    hostil = _proyecto_con_receta(tmp_path, b'{"operaciones": [')
    with pytest.raises(proyecto.ErrorProyecto, match="JSON"):
        proyecto.abrir(hostil)


# ---------------------------------------------------------------- T-10 · imagen vectorizada con la tinta invertida
def test_t10_trace_image_con_tinta_invertida_pegada_al_borde_no_se_pasa_de_largo(tmp_path):
    from PIL import Image, ImageDraw

    from omnicad.restricciones.boceto import puntos_primitiva
    imagen = Image.new("RGB", (300, 200), "white")
    dibujo = ImageDraw.Draw(imagen)
    dibujo.ellipse((20, 20, 180, 180), fill="black")
    dibujo.rectangle((190, 40, 280, 160), fill="black")
    ruta = tmp_path / "logo.png"
    imagen.save(ruta)
    for invertir in (False, True):
        s = api.Sesion()
        llamar(s, "create_sketch", plane="XY", name="T")
        llamar(s, "trace_image", path=str(ruta), width=45, invert=invertir, curves=True, sketch="T")
        boceto = next(iter(s.doc.estado_final.bocetos.values())).boceto
        puntos = np.array([q for prim in boceto.geometria() for q in puntos_primitiva(prim)])
        ancho, alto = puntos.max(0) - puntos.min(0)
        # el ancho final es siempre 45; la altura sigue la proporción del contorno: la imagen entera (300 × 200) con la
        # tinta invertida, y con la normal el dibujo (260 × 160)
        assert ancho == pytest.approx(45.0, abs=1.0)
        assert alto == pytest.approx(30.0 if invertir else 27.7, abs=1.0)


# ---------------------------------------------------------------- T-14 · formatos
def test_t14_insert_file_acepta_brep(tmp_path):
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10)
    ruta = tmp_path / "caja.brep"
    llamar(s, "export", path=str(ruta))
    destino = api.Sesion()
    r = llamar(destino, "insert_file", path=str(ruta))
    assert len(r["new_bodies"]) == 1 and r["status"] == "ok"
    assert geo.volumen_exacto(destino.doc.estado_final.cuerpos[r["new_bodies"][0]].forma) == pytest.approx(1000)


def test_t14_el_3mf_de_dos_cuerpos_lleva_dos_objetos_y_al_traerlo_avisa(tmp_path):
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10)
    llamar(s, "create_box", length=5, width=5, height=5, x=30)
    ruta = tmp_path / "dos.3mf"
    llamar(s, "export", path=str(ruta))
    with zipfile.ZipFile(ruta) as z:
        assert z.read("3D/3dmodel.model").decode().count("<object ") == 2
    destino = api.Sesion()
    r = api.llamar(destino, "insert_file", {"path": str(ruta)})
    assert r["ok"] and any("2 objetos" in a for a in r["avisos"]), r
    partes = llamar(destino, "separate_mesh", bodies=r["result"]["new_bodies"][0], by="face_groups")
    assert len(partes["bodies_created"]) + len(partes["bodies_modified"]) == 2


# ---------------------------------------------------------------- T-16 · mensajes y nombres
def test_t16_export_con_ruta_vacia_o_de_carpeta_es_un_argumento_invalido(tmp_path):
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10)
    assert "vacío" in falla(s, "export", "INVALID_ARGUMENTS", path="")["mensaje"]
    assert "carpeta" in falla(s, "export", "INVALID_ARGUMENTS", path=str(tmp_path))["mensaje"]


@pytest.mark.parametrize("valor", ["nan", "inf", "1e300"])
def test_t16_un_dxf_con_coordenadas_imposibles_se_rechaza_con_un_mensaje_claro(tmp_path, valor):
    texto = f"0\nSECTION\n2\nENTITIES\n0\nLINE\n8\n0\n10\n0\n20\n0\n11\n{valor}\n21\n5\n0\nENDSEC\n0\nEOF\n"
    ruta = tmp_path / "malo.dxf"
    ruta.write_text(texto)
    with pytest.raises(dxf.ErrorDXF, match="coordenada"):
        dxf.leer_dxf(ruta)
    s = api.Sesion()
    r = api.llamar(s, "insert_dxf", {"path": str(ruta), "plane": "XY"})
    assert not r["ok"] and r["error_kind"] == "IMPORT_FAILED" and "coordenada" in r["mensaje"], r


def test_t16_las_copias_de_un_patron_no_repiten_nombre():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10)
    llamar(s, "rectangular_pattern", bodies="Cuerpo1", x_count=2, x_spacing=20, y_count=2, y_spacing=20)
    nombres = [c["name"] for c in llamar(s, "get_scene_info")["bodies"]]
    assert len(nombres) == 4 and len(set(nombres)) == 4
    assert nombres[:3] == ["Cuerpo1", "Cuerpo1 (copia)", "Cuerpo1 (copia 2)"]
    llamar(s, "mirror", bodies="Cuerpo1 (copia)", plane="YZ")
    nombres = [c["name"] for c in llamar(s, "get_scene_info")["bodies"]]
    assert len(set(nombres)) == 5 and not any("(copia) (copia)" in n for n in nombres)


# ---------------------------------------------------------------- T-17 · cosméticos
def test_t17_un_cero_negativo_se_guarda_como_cero():
    from omnicad.api.herramientas_boceto import texto_expr
    assert texto_expr(-0.0) == "0.0" and texto_expr(18) == "18.0" and texto_expr(" 5 mm ") == "5 mm"


@pytest.mark.parametrize("pedido,guardada", [("-4", "4"), ("-4 mm", "4 mm"), ("-(2+2)", "(2+2)"), ("-4 - 6", "-(-4 - 6)")])
def test_t17_el_desfase_negativo_guarda_la_cota_sin_doble_signo(pedido, guardada):
    s = api.Sesion()
    llamar(s, "sketch_from_spec", name="P", plane="XY",
           entities=[{"type": "rectangle", "id": "R", "center": [0, 0], "width": 40, "height": 30}])
    llamar(s, "offset_sketch_curves", entity=5, distance=pedido, sketch="P")
    cotas = llamar(s, "get_sketch", sketch="P")["dimensions"]
    assert [c["expression"] for c in cotas if c["type"] == "offset"] == [guardada]


def test_t17_realize_copies_cuenta_solo_las_copias_de_su_paso():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10)
    paso1 = llamar(s, "rectangular_pattern", bodies="Cuerpo1", x_count=2, x_spacing=20, lightweight=True)
    # otro patrón sobre el resultado del primero: sus cuerpos cambian de forma cuando se realiza el primero
    llamar(s, "rectangular_pattern", bodies=["Cuerpo1", "Cuerpo1 (copia)"], y_count=2, y_spacing=40, lightweight=True)
    r = llamar(s, "realize_copies", feature=paso1["feature"]["id"])
    assert r["realized"] == 1


# ---------------------------------------------------------------- T-18 · resumen corto
def test_t18_get_scene_info_y_open_document_tienen_modo_resumido(tmp_path):
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10)
    llamar(s, "create_parameter", name="p", expression="3 mm")
    completo, corto = llamar(s, "get_scene_info"), llamar(s, "get_scene_info", summary=True)
    assert corto["counts"] == {"bodies": 1, "sketches": 0, "components": 0, "joints": 0, "parameters": 1}
    assert [(c["name"], c["type"]) for c in corto["bodies"]] == [("Cuerpo1", "solid")]
    assert set(corto["bodies"][0]) == {"id", "name", "type"}
    assert len(json.dumps(corto)) < len(json.dumps(completo))
    ruta = tmp_path / "doc.omnicad"
    llamar(s, "save_document", path=str(ruta))
    otra = api.Sesion()
    assert llamar(otra, "open_document", path=str(ruta), summary=True)["counts"]["bodies"] == 1
