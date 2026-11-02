# -*- coding: utf-8 -*-
"""INSPECCIONAR igual a Fusion (INS-1 a INS-8 y P-25f): opciones nuevas de cálculo, API, documentos viejos, Sustainability
Insights y los campos nuevos del panel. Números exactos."""
import io
import json
import os

import numpy as np
import pytest
from PIL import Image

from omnicad import api
from omnicad.nucleo import analisis as an
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import sustentabilidad as su
from omnicad.timeline import analisis_vista as av
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, esperado="INVALID_ARGUMENTS", **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"] and r["error_kind"] == esperado, r
    return r


def dos_cajas():
    """Dos cajas que se superponen 500 mm³, cada una en su componente."""
    s = api.Sesion()
    a = ok(s, "create_box", length=10, width=20, height=30, anchor="corner", name="A")["bodies_created"][0]["id"]
    b = ok(s, "create_box", length=10, width=10, height=10, x=5, anchor="corner", name="B")["bodies_created"][0]["id"]
    ca = ok(s, "create_component", name="Tapa", bodies=[a])["component"]["id"]
    cb = ok(s, "create_component", name="Base", bodies=[b])["component"]["id"]
    return s, a, b, ca, cb


def imagen(s, **args):
    r = ok(s, "get_viewport_image", width=96, height=96, **args)
    return np.asarray(Image.open(io.BytesIO(r["image"].png)).convert("RGB"), float)


# ---------------------------------------------------------------- un documento viejo se ve igual
def test_analisis_viejos_dan_los_colores_de_siempre():
    """Un análisis guardado antes de estas opciones (sin sus claves) pinta exactamente lo que pintaba."""
    forma = geo.caja(10, 20, 30)

    class Estado:
        cuerpos = {"c": type("C", (), {"forma": forma, "tipo": "solido"})()}
    d = (0.0, 0.0, 1.0)
    for tipo, params, viejo in (("desmoldeo", {"angulo_min": 1.0, "angulo_max": 2.0}, an.colores_desmoldeo(forma, d, 1.0, 2.0)),
                                ("accesibilidad", {}, an.colores_accesibilidad(forma, d)),
                                ("radio_minimo", {"radio": 2.0}, an.colores_radio_minimo(forma, 2.0))):
        _v, _n, c = av.calcular(tipo, params, Estado())["mallas"]["c"]
        assert np.array_equal(np.round(c, 5), np.round(np.asarray(viejo[2], np.float32).reshape(-1, 3), 5)), tipo
    n = np.array([[0, 0, 1.0], [0.6, 0, 0.8]])
    nuevo = av.calcular("mapa_entorno", {}, Estado())["colores"](n, np.array(d))
    assert np.array_equal(nuevo, an.colores_mapa_entorno(n, np.array(d)))
    # Un documento viejo: el tipo y sus params vuelven de la receta sin claves nuevas.
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="20", alto="30"))
    nombre = doc.agregar_analisis("radio_minimo", {"radio": 2.0})
    otro = Documento.desde_dict(doc.a_dict())
    assert otro.analisis[nombre]["params"] == {"radio": 2.0}


# ---------------------------------------------------------------- INS-1: mapas de entorno
def test_cada_entorno_refleja_distinto_y_rota():
    n = np.array([[0.0, 0.0, 1.0], [0.7, 0.0, 0.7], [0.0, 0.7, 0.7], [-0.7, 0.0, 0.7]])
    d = np.array([0.0, -1.0, 0.0])
    mapas = {k: np.asarray(an.colores_mapa_entorno(n, d, entorno=k)) for k in an.ENTORNOS_ANALISIS}
    assert len(mapas) == 13 and len({m.tobytes() for m in mapas.values()}) == 13
    giro = an.colores_mapa_entorno(n, d, entorno="plaza", rotacion=90.0)
    assert not np.array_equal(giro, mapas["plaza"])
    assert not np.array_equal(an.colores_mapa_entorno(n, d, entorno="plaza", reflejo=False), mapas["plaza"])


# ---------------------------------------------------------------- INS-4 y 5
def test_desmoldeo_degrade_y_zona_de_tolerancia():
    forma = geo.caja(10, 10, 10)
    _v, _n, c = an.colores_desmoldeo(forma, (0, 0, 1), 0.0, 3.0, degradado=True, tolerancia=(-1.0, 1.0))
    c = np.asarray(c).reshape(-1, 3)
    amarillo = (np.abs(c - np.asarray(an.AMARILLO)) < 1e-3).all(1)
    assert 0.5 < amarillo.mean() < 0.8                       # las 4 caras laterales (0°) caen en la banda
    assert (np.abs(c - np.asarray(an.VERDE)) < 1e-3).all(1).any() and (np.abs(c - np.asarray(an.ROJO)) < 1e-3).all(1).any()


def test_accesibilidad_ambos_sentidos_ve_las_dos_tapas():
    forma = geo.caja(10, 10, 10)
    verde = np.asarray(an.VERDE, np.float32)

    def porcentaje(**k):
        _v, _n, c = an.colores_accesibilidad(forma, (0, 0, 1), **k)
        return float((np.asarray(c, np.float32).reshape(-1, 3) == verde).all(1).mean())
    assert porcentaje(ambos_sentidos=True) > porcentaje()


def test_radio_minimo_degrade_entre_dos_radios():
    forma = geo.cortar_varias(geo.caja(30, 30, 10), [geo.cilindro(3, 20, base=(15, 15, -5))])       # agujero de radio 3: cóncavo
    verde = np.asarray(an.VERDE, np.float32)
    amplio = np.asarray(an.colores_radio_minimo(forma, 5.0, radio_minimo=1.0, aristas_vivas=False)[2], np.float32).reshape(-1, 3)
    justo = np.asarray(an.colores_radio_minimo(forma, 3.5, radio_minimo=3.0, aristas_vivas=False)[2], np.float32).reshape(-1, 3)
    assert (amplio != verde).any(1).sum() > 0                 # el radio 3 cae entre 1 y 5: ni rojo puro ni verde
    assert (justo != verde).any(1).sum() >= (amplio != verde).any(1).sum()
    hueca = geo.cortar_varias(geo.caja(40, 40, 30), [geo.caja(36, 36, 40, origen=(2, 2, 2))])
    c = np.asarray(an.colores_radio_minimo(hueca, 25.0, radio_minimo=0.0)[2], np.float32).reshape(-1, 3)
    rojo = float((c == np.asarray(an.ROJO, np.float32)).all(1).mean())
    assert 0 < rojo < 0.25                                    # una banda junto a los rincones, no las paredes enteras
    with pytest.raises(geo.ErrorGeometria, match="radio mínimo"):
        an.colores_radio_minimo(forma, 5.0, radio_minimo=6.0)


# ---------------------------------------------------------------- API de análisis
def test_manage_analysis_opciones_nuevas_se_guardan_solo_si_se_dan():
    s, a, *_ = dos_cajas()
    ok(s, "manage_analysis", action="add", type="environment_map", name="E", environment="plaza", rotation=45, mirror_finish=False, bodies=[a])
    assert s.doc.analisis["E"]["params"] == {"cuerpos": [a], "entorno": "plaza", "rotacion": 45.0, "reflejo": False}
    ok(s, "manage_analysis", action="add", type="environment_map", name="E2")
    assert s.doc.analisis["E2"]["params"] == {}
    ok(s, "manage_analysis", action="add", type="draft", name="D", tolerance_min=0.5, tolerance_max=1.5, opacity=40, high_quality=True)
    p = s.doc.analisis["D"]["params"]
    assert p["tolerancia"] == [0.5, 1.5] and p["degradado"] is True and p["opacidad"] == 40 and p["alta_calidad"] is True
    ok(s, "manage_analysis", action="add", type="draft", name="D2")
    assert "degradado" not in s.doc.analisis["D2"]["params"] and "opacidad" not in s.doc.analisis["D2"]["params"]
    ok(s, "manage_analysis", action="add", type="accessibility", name="Ac", change_direction="both", opacity=50)
    assert s.doc.analisis["Ac"]["params"]["sentido"] == "ambas"
    ok(s, "manage_analysis", action="add", type="min_radius", name="R", radius=4, min_radius=1, sharp_edges=False, opacity=70)
    assert {k: s.doc.analisis["R"]["params"][k] for k in ("radio", "radio_minimo", "aristas_vivas", "opacidad")} == {
        "radio": 4.0, "radio_minimo": 1.0, "aristas_vivas": False, "opacidad": 70}
    falla(s, "manage_analysis", action="add", type="environment_map", environment="marte")
    falla(s, "manage_analysis", action="add", type="draft", tolerance_min=2, tolerance_max=1)
    falla(s, "manage_analysis", action="add", type="min_radius", radius=2, min_radius=3)


def test_isocurva_con_caras_elegidas():
    s, a, *_ = dos_cajas()
    cara = ok(s, "find_faces", body=a, selector=">Z")["faces"][0]["id"]
    ok(s, "manage_analysis", action="add", type="isocurve", name="I", faces=cara, body=a)
    r = s.doc.analisis["I"]["params"]["caras"]
    assert len(r) == 1 and av.calcular("isocurva", s.doc.analisis["I"]["params"], s.doc.estado_final)["capas"]


def test_editar_analisis_conserva_nombre_y_se_deshace():
    s, *_ = dos_cajas()
    ok(s, "manage_analysis", action="add", type="zebra", name="Z", frequency=8)
    ok(s, "manage_analysis", action="edit", name="Z", frequency=20)
    assert list(s.doc.analisis) == ["Z"] and s.doc.analisis["Z"]["params"]["frecuencia"] == 20
    ok(s, "undo")
    assert s.doc.analisis["Z"]["params"]["frecuencia"] == 8
    falla(s, "manage_analysis", action="edit", name="No hay")
    falla(s, "manage_analysis", action="edit")


def test_analyze_geometry_opciones_y_centro_de_masa():
    s, a, b, ca, _cb = dos_cajas()
    r = ok(s, "analyze_geometry", type="draft", tolerance_min=-1, tolerance_max=1, bodies=[a])
    assert r["bodies"][0]["tolerance_percent"] > 50
    uno = ok(s, "analyze_geometry", type="accessibility", bodies=[a])["bodies"][0]["accessible_percent"]
    dos = ok(s, "analyze_geometry", type="accessibility", bodies=[a], change_direction="both")["bodies"][0]["accessible_percent"]
    assert dos > uno
    r = ok(s, "analyze_geometry", type="center_of_mass", bodies=[a])
    assert r["center_of_mass"] == pytest.approx([5, 10, 15]) and r["mass_g"] == pytest.approx(6000 * 7.85e-3)
    assert ok(s, "analyze_geometry", type="center_of_mass", components=[ca])["center_of_mass"] == pytest.approx([5, 10, 15])
    falla(s, "analyze_geometry", type="center_of_mass", components=["Ninguno"], esperado="COMPONENT_NOT_FOUND")


# ---------------------------------------------------------------- centro de masa como análisis (INS-7)
def test_centro_de_masa_guardado_se_dibuja_y_sirve_para_medir():
    s, a, *_ = dos_cajas()
    ok(s, "manage_analysis", action="add", type="center_of_mass", name="CdM", bodies=[a])
    capas = av.calcular("centro_masa", s.doc.analisis["CdM"]["params"], s.doc.estado_final, s.doc.propiedades)["capas"]
    assert [c[0] for c in capas] == ["puntos", "puntos"] and np.allclose(capas[0][1][0], (5, 10, 15))
    r = ok(s, "measure_distance", a="CdM", b=[5, 10, 25])
    assert r["distance"] == pytest.approx(10) and r["a"]["kind"] == "center_of_mass"
    otra = Documento.desde_dict(s.doc.a_dict())
    assert otra.analisis["CdM"]["tipo"] == "centro_masa"


# ---------------------------------------------------------------- medir e interferencia (INS-2 y 3)
def test_measure_distance_componente_texto_y_delta_del_componente():
    s, a, b, ca, cb = dos_cajas()
    r = ok(s, "measure_distance", a="Tapa", b=[-10, 0, 0], secondary_unit="cm", precision=2)
    assert r["distance"] == pytest.approx(10) and r["a"]["kind"] == "component" and r["text"] == "10.00 mm (1.00 cm)"
    assert "text" not in ok(s, "measure_distance", a="Tapa", b=[-10, 0, 0])
    s.doc.estado_final.componentes[ca]["matriz"] = [[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    r = ok(s, "measure_distance", a=a, b=[-10, 5, 5], delta_system="component_a")
    assert r["delta"] == pytest.approx([0, 10, 0])
    falla(s, "measure_distance", a=a, b=b, precision=9)


def test_texto_secundario_en_cada_potencia():
    assert an.texto_secundario(25.4, 1, 2, "pulg") == " (1.00 pulg.)"
    assert an.texto_secundario(1e6, 2, 1, "m") == " (1.0 m²)"
    assert an.texto_secundario(1000, 3, 0, "cm") == " (1 cm³)"
    assert an.texto_secundario(1, 1, 2, "ninguno") == ""


def test_interferencia_por_componentes_y_quitar_volumen():
    s, a, b, _ca, cb = dos_cajas()
    assert ok(s, "check_interference", components=["Tapa", "Base"])["pairs"][0]["volume"] == pytest.approx(500)
    falla(s, "remove_interference", pairs=[{"target": a}])
    pasos = len(s.doc.operaciones)
    ok(s, "remove_interference", pairs=[{"target": a, "tool": b}])
    assert len(s.doc.operaciones) == pasos + 1
    fis = ok(s, "get_physical_properties", bodies=[a, b])["bodies"]
    assert [round(c["volume"]) for c in fis] == [5500, 1000]
    assert ok(s, "check_interference", bodies=[a, b])["count"] == 0


# ---------------------------------------------------------------- colores de componente (INS-7)
def test_color_de_ciclo_cambia_la_paleta_y_se_guarda():
    from omnicad.timeline.aspectos_doc import PALETA_COMPONENTES, colores_componentes
    s, _a, _b, ca, cb = dos_cajas()
    assert colores_componentes(s.doc) == {ca: PALETA_COMPONENTES[0], cb: PALETA_COMPONENTES[1]}
    antes = imagen(s, component_colors=True)
    r = ok(s, "cycle_component_color", component="Tapa")
    assert r["color"] == "#%02x%02x%02x" % PALETA_COMPONENTES[1] and colores_componentes(s.doc)[cb] == PALETA_COMPONENTES[1]
    assert np.abs(imagen(s, component_colors=True) - antes).mean() > 0.1
    otra = Documento.desde_dict(s.doc.a_dict())
    assert colores_componentes(otra)[ca] == PALETA_COMPONENTES[1]
    ok(s, "undo")
    assert colores_componentes(s.doc)[ca] == PALETA_COMPONENTES[0]
    for _i in range(len(PALETA_COMPONENTES)):
        ok(s, "cycle_component_color", component=ca)
    assert colores_componentes(s.doc)[ca] == PALETA_COMPONENTES[0]     # da la vuelta


def test_mapa_del_navegador_y_timeline_comparten_paleta():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.timeline.aspectos_doc import PALETA_COMPONENTES as enteros
    from omnicad.ui.panel_timeline import PALETA_COMPONENTES as colores
    assert [c.getRgb()[:3] for c in colores] == list(enteros)


# ---------------------------------------------------------------- grupos de caras de malla (P-25f)
def test_grupos_de_caras_de_malla():
    from omnicad.nucleo.malla import Malla
    v = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 0, 1]], float)
    m = Malla(v, np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]]), grupos=np.array([0, 0, 1, 2]))
    tv, tn, tc = an.colores_grupos_malla(m)
    assert len(tv) == len(tn) == len(tc) == 12
    assert len({tuple(np.round(c, 3)) for c in tc}) == 3
    assert np.array_equal(tc[0], tc[3]) and not np.array_equal(tc[0], tc[6])


def test_imagen_con_grupos_de_caras():
    s = api.Sesion()
    b = ok(s, "create_box", length=20, width=20, height=20)["bodies_created"][0]["id"]
    ok(s, "tessellate", bodies=b, keep_original=False)
    malla = next(c for c in s.doc.estado_final.cuerpos.values() if c.tipo == "malla")
    ok(s, "generate_face_groups", bodies=malla.id, angle=30)
    assert np.abs(imagen(s, mesh_face_groups=True) - imagen(s)).mean() > 0.5


# ---------------------------------------------------------------- Sustainability Insights (P-25f)
@pytest.fixture
def materiales(tmp_path, monkeypatch):
    ruta = tmp_path / "materiales.json"
    monkeypatch.setenv(su.VAR_MATERIALES, str(ruta))
    return ruta


def test_estimar_con_cuenta_a_la_vista():
    e = su.estimar(1_000_000, "Aluminio")                      # 1000 cm³ × 2,70 g/cm³ = 2,7 kg
    assert e["masa_kg"] == pytest.approx(2.7) and e["co2_kg"] == pytest.approx(2.7 * 9.16) and "ICE" in e["fuente"]
    with pytest.raises(geo.ErrorGeometria, match="sin|con fuente"):
        su.estimar(1000, "ASA")
    with pytest.raises(geo.ErrorGeometria, match="desconocido"):
        su.estimar(1000, "Unobtainio")
    with pytest.raises(geo.ErrorGeometria, match="mayor que cero"):
        su.estimar(0, "ABS")


def test_todo_factor_de_fabrica_tiene_fuente_o_queda_vacio():
    for nombre, d in su.MATERIALES.items():
        assert (d["co2"] is None) == (not d["fuente"]), nombre
    assert [n for n, d in su.MATERIALES.items() if d["co2"] is None] == ["ASA"]


def test_material_cercano():
    assert su.material_cercano("Aluminio 6061") == "Aluminio"
    assert su.material_cercano("Acero inoxidable") == "Acero inoxidable"
    assert su.material_cercano("Madera (pino)") == "" and su.material_cercano(None) == ""


def test_materiales_propios_importar_y_exportar(materiales, tmp_path):
    assert su.definir_material(" Bio ", 2.5, 1.3, "ABS") == "Bio"
    assert su.estimar(1_000_000, "Bio")["co2_kg"] == pytest.approx(1.3 * 2.5)
    salida = tmp_path / "salida.json"
    assert su.exportar_materiales(salida) == 1
    su.borrar_material("Bio")
    assert su.materiales_propios() == {}
    datos = json.loads(salida.read_text(encoding="utf-8"))
    datos["materiales"]["Malo"] = {"co2": "mucho", "densidad": 1}
    datos["materiales"]["Raro"] = {"co2": 1, "densidad": 1, "parecido": ["ABS"]}
    datos["materiales"]["ABS"] = {"co2": 1, "densidad": 1}     # no pisa uno de fábrica
    salida.write_text(json.dumps(datos), encoding="utf-8")
    assert su.importar_materiales(salida) == (["Bio"], ["Malo", "Raro", "ABS"])
    for mal in (("", 1, 1), ("X", 0, 1), ("X", 1, -1), ("ABS", 1, 1), ("X", 1, 1, "Marte"), ("X", float("nan"), 1)):
        with pytest.raises(geo.ErrorGeometria):
            su.definir_material(*mal)
    salida.write_bytes(b"{" * (su.TOPE_IMPORTAR + 1))
    with pytest.raises(geo.ErrorGeometria, match="grande"):
        su.importar_materiales(salida)


def test_api_de_sustainability(materiales):
    s, a, b, *_ = dos_cajas()
    falla(s, "estimate_carbon_footprint", body=a)                  # sin material físico ni material
    ok(s, "set_material", bodies=[a], material="Aluminio 6061")
    r = ok(s, "estimate_carbon_footprint", body=a)
    assert r["estimate"] is True and r["material"] == "Aluminio" and r["volume_mm3"] == pytest.approx(6000)
    assert r["mass_kg"] == pytest.approx(0.0162) and r["co2_kg"] == pytest.approx(0.0162 * 9.16, abs=1e-6) and "ICE" in r["source"]
    assert ok(s, "estimate_carbon_footprint", body=a, stock_volume=12000)["co2_kg"] == pytest.approx(r["co2_kg"] * 2, abs=1e-5)
    assert ok(s, "estimate_carbon_footprint", body=a, stock_body=b)["volume_mm3"] == pytest.approx(1000)
    r2 = ok(s, "estimate_carbon_footprint", body=a, region="Sudamérica", country="Argentina")
    assert r2["co2_kg"] == r["co2_kg"] and r2["country"] == "Argentina"
    falla(s, "estimate_carbon_footprint", body=a, stock_volume=1, stock_body=b)
    falla(s, "estimate_carbon_footprint", body=a, region="Atlántida")
    falla(s, "estimate_carbon_footprint", body=a, region="Asia", country="Argentina")
    falla(s, "estimate_carbon_footprint", body=a, country="Argentina")
    falla(s, "estimate_carbon_footprint", body=a, material="ASA")
    lista = ok(s, "manage_carbon_materials")
    assert len(lista["materials"]) == 13 and set(lista["regions"]) == set(su.REGIONES)
    ok(s, "manage_carbon_materials", action="add", name="Bio", co2_per_kg=2, density=1, similar_to="ABS")
    assert ok(s, "estimate_carbon_footprint", body=a, material="Bio")["mass_kg"] == pytest.approx(0.006)
    ok(s, "manage_carbon_materials", action="remove", name="Bio")
    falla(s, "manage_carbon_materials", action="remove", name="Bio")
    falla(s, "manage_carbon_materials", action="export")


def test_preferencia_de_unidades_secundarias():
    s = api.Sesion()
    claves = {p["key"]: p for p in ok(s, "get_preferences", keys=["medir/secundarias"])["preferences"]}
    assert claves["medir/secundarias"]["default"] == "ninguno" and "pulg" in claves["medir/secundarias"]["options"]


# ---------------------------------------------------------------- el panel
@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_deslizador_doble_no_cruza_los_topes(app_qt):
    from omnicad.ui.comando import _DeslizadorDoble
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    d = _DeslizadorDoble(0.0, 10.0)
    d.resize(200, 20)
    d.poner(2.0, 8.0)
    medio, vistos = d.height() // 2, []
    d.movido.connect(lambda i, valor: vistos.append((i, valor)))
    QTest.mousePress(d, Qt.LeftButton, pos=QPoint(round(d.x_de(0)), medio))
    QTest.mouseMove(d, QPoint(190, medio))                   # lo lleva más allá del otro tope
    QTest.mouseRelease(d, Qt.LeftButton, pos=QPoint(190, medio))
    assert vistos[-1] == (0, pytest.approx(8.0))


def test_panel_de_sustainability_textos_y_estimacion(app_qt, materiales):
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.sustentabilidad import Sustentabilidad
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="20", alto="30"))
    cmd, ctx = Sustentabilidad(), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    assert cmd._manufactura(v, ctx).startswith("Seleccione un cuerpo") and cmd._material_cuerpo(v, ctx).startswith("No hay cuerpo")
    v["cuerpo"] = [hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)]
    assert cmd._manufactura(v, ctx) == "Pieza sólida" and "Elegí" in cmd._resultado(v, ctx)
    v["material"] = "aluminio"
    texto = cmd._resultado(v, ctx)
    assert "Estimación: 0.148 kg" in texto and "0.0162 kg × 9.16" in texto and "ICE" in texto
    v.update(material="asa")
    assert "no tiene un factor" in cmd._resultado(v, ctx)
    v.update(material="abs", sobrescritura="manual", stock_volumen="12000")
    assert "0.0127 kg" in cmd._resultado(v, ctx)
    doc.estado_final.cuerpos["op1.c1"].tipo = "malla"
    assert "no es un sólido" in cmd._resultado(dict(v, sobrescritura="no"), ctx)
    assert cmd.aplicar(v, ctx) is None and len(doc.operaciones) == 1
