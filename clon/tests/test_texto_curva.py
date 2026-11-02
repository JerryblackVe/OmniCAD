# -*- coding: utf-8 -*-
"""Texto en curva que toca o cruza otra curva y su extrusión: B-132 a B-134, B-136, B-137, TXT-8 y TXT-9."""
import importlib.util
import os

import pytest

from omnicad import api, nativo
from omnicad.api.herramientas_boceto import info_perfiles
from omnicad.nucleo import fuentes
from omnicad.nucleo import perfiles as pf

@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


hay_arial = pytest.mark.skipif(fuentes.buscar_fuente("Arial") is None, reason="No hay Arial instalada")
ESCALA = (2048 / 1466) ** 2                              # Arial: la altura es el alto de la A, no el tamaño de fuente
LETRAS = ESCALA * (150.3397 + 160.2536 + 87.8284 + 138.6253)   # H, O, L y A de «HOLA» altura 30 (sin huecos)
HUECOS = ESCALA * (206.7867 + 35.8249)                   # el de la O y el de la A
DISCO = 10207.0345                                       # π·57²


def ok(r):
    assert r["ok"], r
    return r["result"]


def hola(s, **extra):
    ok(api.llamar(s, "create_sketch", {"plane": "XZ", "name": "b"}))
    c = ok(api.llamar(s, "draw_circle", {"sketch": "b", "center_x": 0, "center_y": 0, "radius": 57}))["entities"][0]["id"]
    t = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "HOLA", "font": "Arial", "height": 30, "path_entity": c,
                                      "path_side": "right", "path_position": 0.25, **extra}))["entities"][0]["id"]
    return c, t, s.doc.estado_final.bocetos[s.paso("b").id]


def cuerpos(s):
    return sorted(b["volume"] for b in ok(api.llamar(s, "get_scene_info", {}))["bodies"])


@hay_arial
@pytest.mark.parametrize("separado", [0, 2])
def test_hola_sobre_el_circulo_extruye_cuatro_letras_con_los_huecos_vacios(separado):
    s = api.Sesion()
    hola(s, path_offset=separado)
    ok(api.llamar(s, "extrude", {"sketch": "b", "profile": "text", "distance": 10}))
    assert cuerpos(s) == pytest.approx([ESCALA * v for v in (878.284, 1386.253, 1503.397, 1602.536)], abs=0.1)
    assert sum(cuerpos(s)) == pytest.approx(10 * LETRAS, abs=0.5)


@hay_arial
def test_el_texto_no_parte_al_circulo_y_el_circulo_no_parte_las_letras():
    _c, t, br = hola(api.Sesion())
    letras, huecos = pf.partes_de_texto(br.perfiles, [t])
    assert len(letras) == 4 and sum(p.area for p in letras) == pytest.approx(LETRAS, abs=0.01)
    assert len(huecos) == 2 and sum(p.area for p in huecos) == pytest.approx(HUECOS, abs=0.01)
    assert len(br.perfiles) == 7


@hay_arial
@pytest.mark.parametrize("colocacion", ["above", "below"])
def test_el_disco_mide_lo_mismo_que_en_fusion(colocacion):
    """B-134: Fusion real da 1 perfil de 10207,03 con HOLA de 30 mm sobre el círculo de R57, por arriba y por abajo."""
    c, _t, br = hola(api.Sesion(), path_placement=colocacion)
    disco = max(br.perfiles, key=lambda p: p.area)
    assert disco.area == pytest.approx(DISCO, abs=0.01) and disco.firma == {c}


def _caja(br):
    """Caja del primer perfil. `caja_uv` solo viene armada con el módulo de Rust."""
    caja = info_perfiles(br)[0]["bounding_box"]
    return (*caja["min"], *caja["max"])


@hay_arial
def test_un_texto_adentro_de_la_o_de_otro_no_es_su_hueco():
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    a = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "O", "font": "Arial", "height": 60}))["entities"][0]["id"]
    br = s.doc.estado_final.bocetos[s.paso("b").id]
    x0, y0, x1, y1 = _caja(br)
    b = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "I", "font": "Arial", "height": 5, "x": (x0 + x1) / 2,
                                      "y": (y0 + y1) / 2}))["entities"][0]["id"]
    br = s.doc.estado_final.bocetos[s.paso("b").id]
    letras, huecos = pf.partes_de_texto(br.perfiles, [a, b])
    assert len(letras) == 2 and len(huecos) == 1


@hay_arial
def test_una_referencia_vieja_al_disco_cortado_encuentra_el_disco_entero():
    c, t, br = hola(api.Sesion())
    perfil, nota = pf.buscar_por_firma_tolerante(br.perfiles, [c, t], [0.0, 0.2])
    assert perfil.area == pytest.approx(DISCO, abs=0.01) and nota


@hay_arial
@pytest.mark.parametrize("profile, volumen", [("largest", 10 * DISCO), ("sketch", 10 * DISCO)])
def test_extruir_el_disco_con_el_texto_adentro_no_suma_dos_veces(profile, volumen):
    s = api.Sesion()
    hola(s, path_side="left", path_offset=5)
    ok(api.llamar(s, "extrude", {"sketch": "b", "profile": profile, "distance": 10}))
    assert cuerpos(s) == pytest.approx([volumen], abs=1)


@hay_arial
def test_una_recta_que_cruza_la_o_no_la_parte():
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    t = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "O", "font": "Arial", "height": 30}))["entities"][0]["id"]
    br = s.doc.estado_final.bocetos[s.paso("b").id]
    x0, y0, x1, y1 = _caja(br)
    area_total = sum(p.area for p in pf.letras_de_texto(br.perfiles, [t]))
    area_hueco = sum(p.area for p in br.perfiles) - area_total
    ok(api.llamar(s, "draw_line", {"sketch": "b", "start_x": x0 - 5, "start_y": (y0 + y1) / 2, "end_x": x1 + 5,
                                   "end_y": (y0 + y1) / 2}))
    br = s.doc.estado_final.bocetos[s.paso("b").id]
    letras, huecos = pf.partes_de_texto(br.perfiles, [t])
    assert len(letras) == 1 and len(huecos) == 1
    assert sum(p.area for p in letras) == pytest.approx(area_total, abs=1e-3)
    assert sum(p.area for p in huecos) == pytest.approx(area_hueco, abs=1e-3)


@hay_arial
def test_no_queda_ningun_resto_y_el_disco_conserva_su_area():
    s = api.Sesion()
    hola(s)
    g = ok(api.llamar(s, "get_sketch", {"sketch": "b"}))
    assert len(g["profiles"]) == 7 and min(p["area"] for p in g["profiles"]) > 1
    assert max(p["area"] for p in g["profiles"]) == pytest.approx(DISCO, abs=0.01)


def test_una_cinta_de_menos_de_un_micron_no_es_un_perfil_pero_un_cuadrado_chico_si():
    assert pf._sin_area(pf.Perfil(None, 5e-5, (0, 0), frozenset(), caja_uv=(0, 0, 0.3, 0)))
    assert not pf._sin_area(pf.Perfil(None, 1e-6, (0, 0), frozenset(), caja_uv=(0, 0, 1e-3, 1e-3)))
    assert not pf._sin_area(pf.Perfil(None, 1.29, (0, 0), frozenset(), caja_uv=(0, 0, 5.2, 0.7)))


def test_extruir_un_resto_sin_area_se_rechaza_con_un_mensaje_claro(monkeypatch):
    monkeypatch.setattr(pf, "_sin_area", lambda _p: False)
    pf._CACHE_PERFILES.clear()
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    ok(api.llamar(s, "draw_rectangle", {"sketch": "b", "x1": 0, "y1": 0, "x2": 200, "y2": 0.0005}))
    g = ok(api.llamar(s, "get_sketch", {"sketch": "b"}))
    assert g["profiles"][0]["area"] == pytest.approx(0.1, abs=1e-3)
    r = api.llamar(s, "extrude", {"sketch": "b", "profile": 0, "distance": 100})
    pf._CACHE_PERFILES.clear()
    assert not r["ok"] and "no tiene volumen" in r["mensaje"]
    assert ok(api.llamar(s, "get_scene_info", {}))["bodies"] == []


@hay_arial
@pytest.mark.skipif(nativo.disponible() is None, reason="Sin el módulo de Rust")
@pytest.mark.parametrize("lado, posicion", [("right", 0.1), ("right", 0.2), ("right", 0.475), ("left", 0.075), ("left", 0.1)])
def test_el_disco_no_se_pierde_cuando_una_letra_apoya_sobre_el_circulo(lado, posicion):
    """B-137: en estas posiciones el arreglo planar de Rust unía caras sin avisar (6 perfiles y 692 mm² contra 9 y 10985)."""
    s = api.Sesion()
    _c, _t, br = hola(s, path_side=lado, path_position=posicion)
    referencia = pf._detectar_occ(br.boceto.geometria(), br.plano)
    juntos = pf.detectar(br.boceto.geometria(), br.plano)
    assert sum(p.area for p in juntos) == pytest.approx(sum(p.area for p in referencia), abs=0.01)
    assert max(p.area for p in juntos) == pytest.approx(max(p.area for p in referencia), abs=0.01)


@hay_arial
def test_profile_sketch_toma_todo_el_boceto_con_el_texto_y_sin_los_huecos():
    s = api.Sesion()
    _c, _t, br = hola(s, path_offset=2)
    assert len(pf.perfiles_de_boceto(br)) == 5                 # 4 letras y el disco
    ok(api.llamar(s, "extrude", {"sketch": "b", "profile": "sketch", "distance": 10}))
    assert sum(cuerpos(s)) == pytest.approx(10 * (LETRAS + DISCO), abs=1)


def test_perfiles_de_boceto_sin_texto_son_todos():
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    ok(api.llamar(s, "draw_circle", {"sketch": "b", "center_x": 0, "center_y": 0, "radius": 5}))
    ok(api.llamar(s, "draw_circle", {"sketch": "b", "center_x": 0, "center_y": 0, "radius": 8}))
    br = s.doc.estado_final.bocetos[s.paso("b").id]
    assert len(pf.perfiles_de_boceto(br)) == 2


# ---------------------------------------------------------------- TXT-9: colocación, Voltear, Ajustar y curva cambiada
def texto_en_linea(**extra):
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    c = ok(api.llamar(s, "draw_line", {"sketch": "b", "start_x": 0, "start_y": 0, "end_x": 100, "end_y": 0}))["entities"][0]["id"]
    t = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "HE", "font": "Arial", "height": 30, "path_entity": c,
                                      "align": "left", "path_position": 0.1, **extra}))["entities"][0]["id"]
    return s, t


def caja_texto(s, t):
    pts = [q for p in s.doc.estado_final.bocetos[s.paso("b").id].boceto.primitivas(t)
           for q in ((p[2], p[3]) if p[0] == "linea" else p[2])]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return min(xs), min(ys), max(xs), max(ys)


@hay_arial
def test_abajo_cuelga_las_letras_de_la_curva_con_la_misma_lectura():
    s, t = texto_en_linea()
    x0, y0, x1, y1 = caja_texto(s, t)
    assert y0 == pytest.approx(0, abs=1e-6) and y1 == pytest.approx(30, abs=0.02)      # apoyadas: la base sobre la línea
    ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "path_placement": "below"}))
    a0, b0, a1, b1 = caja_texto(s, t)
    assert (b0, b1) == pytest.approx((-y1, 0), abs=1e-6) and (a0, a1) == pytest.approx((x0, x1), abs=1e-6)
    d = ok(api.llamar(s, "get_sketch", {"sketch": "b"}))
    assert next(e for e in d["entities"] if e["id"] == t)["path_placement"] == "below"
    assert api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "path_placement": "izq"})["ok"] is False


@hay_arial
def test_una_receta_vieja_sin_colocacion_abre_arriba_y_la_nueva_la_guarda():
    from omnicad.restricciones.boceto import Boceto, Texto
    s, t = texto_en_linea()
    d = s.paso("b").boceto.curvas[t].a_dict()
    assert "camino_colocacion" not in d                        # por defecto no se escribe: la receta queda igual
    b = Boceto.desde_dict(s.paso("b").boceto.a_dict())
    assert isinstance(b.curvas[t], Texto) and b.curvas[t].camino_colocacion == "arriba"
    ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "path_placement": "below"}))
    assert s.paso("b").boceto.curvas[t].a_dict()["camino_colocacion"] == "abajo"
    assert Boceto.desde_dict(s.paso("b").boceto.a_dict()).curvas[t].camino_colocacion == "abajo"


@hay_arial
def test_voltear_un_texto_en_curva_espeja_las_letras_sin_moverlo_de_lugar():
    s, t = texto_en_linea(path_offset=2)
    antes = caja_texto(s, t)
    areas = sorted(round(p.area, 3) for p in s.doc.estado_final.bocetos[s.paso("b").id].perfiles)
    base = s.doc.estado_final.bocetos[s.paso("b").id].boceto.primitivas(t)
    for args in ({"flip_h": True}, {"flip_h": False, "flip_v": True}):
        ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, **args}))
        br = s.doc.estado_final.bocetos[s.paso("b").id]
        x0, y0, x1, y1 = caja_texto(s, t)
        assert (x1 - x0, y0, y1) == pytest.approx((antes[2] - antes[0], antes[1], antes[3]), abs=1e-6)
        assert sorted(round(p.area, 3) for p in br.perfiles) == areas
        assert br.boceto.primitivas(t) != base


@hay_arial
def test_ajustar_a_la_curva_reparte_el_texto_en_todo_el_largo():
    s, t = texto_en_linea(fit_path=True)
    x0, _y0, x1, _y1 = caja_texto(s, t)
    assert x0 == pytest.approx(0, abs=4) and x1 == pytest.approx(100, abs=4)


@hay_arial
def test_cambiar_la_curva_despues_de_crear_el_texto_lo_arrastra():
    s = api.Sesion()
    c, t, _br = hola(s, path_offset=2)
    y = caja_texto(s, t)[3]
    ok(api.llamar(s, "set_circle_radius", {"sketch": "b", "curve": c, "radius": 80}))
    assert caja_texto(s, t)[3] == pytest.approx(y + 23, abs=0.4)
    otra = ok(api.llamar(s, "draw_line", {"sketch": "b", "start_x": -100, "start_y": 200, "end_x": 100, "end_y": 200}))
    ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "path_entity": otra["entities"][0]["id"], "path_side": "left"}))
    assert caja_texto(s, t)[1] > 199


def test_lado_natural_se_lee_de_izquierda_a_derecha_y_por_fuera_en_una_curva_cerrada():
    from omnicad.restricciones.boceto import lado_natural
    assert lado_natural(("circulo", 1, (0, 0), 57.0)) == "der"
    assert lado_natural(("linea", 1, (0, 0), (10, 0))) == "izq"
    assert lado_natural(("linea", 1, (10, 0), (0, 0))) == "der"


# ---------------------------------------------------------------- interfaz, sin ventana principal
@hay_arial
def test_panel_caracter_muestra_el_espaciado_en_porcentaje_del_ancho_medio(app_qt):
    from omnicad.ui.modo_boceto import PanelCaracter
    panel = PanelCaracter()
    salidas = []
    panel.cambio.connect(lambda k, v: salidas.append((k, v)))
    panel.cargar({"altura_texto": 30.0, "espaciado": 0.05 * fuentes.espaciado_cien("Arial", 30), "fuente": "Arial"})
    assert panel.interletraje.suffix() == " %" and panel.interletraje.value() == pytest.approx(5.0, abs=0.01)
    assert salidas == []
    panel.interletraje.setValue(10.0)
    assert salidas[-1] == ("espaciado", pytest.approx(1.84992, abs=1e-4))
    panel.altura.setValue(60.0)
    assert salidas[-1] == ("espaciado", pytest.approx(3.69984, abs=1e-4))    # el porcentaje se mantiene con otra altura
    panel.camino_colocacion.setCurrentIndex(panel.camino_colocacion.findData("abajo"))
    assert salidas[-1] == ("camino_colocacion", "abajo")
    panel.cargar({"altura_texto": 30.0, "camino_colocacion": "abajo"})
    assert panel.camino_colocacion.currentText() == "Abajo"


@hay_arial
def test_el_lienzo_usa_el_contenido_del_parametro_y_aguanta_una_expresion_rota(app_qt):
    """B-137: la sombra eran los perfiles de «{Text}» sin resolver."""
    from omnicad.nucleo.geometria import Plano
    from omnicad.restricciones import Boceto
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    b.agregar_circulo((100, 0), 5)
    t = b.agregar_texto((0, 0), "{Text}", altura=30, fuente="Arial")
    b.curvas[t].parametro_texto = "Text"
    lz = Lienzo(b, TablaParametros().evaluar, plano=Plano("XY"))
    crudo = sum(1 for g in b.geometria() if g[1] == t)
    lz.valores_parametros = lambda: {"Text": "I"}
    assert sum(1 for g in lz.geometria_real() if g[1] == t) == 4 < crudo       # la «I» son 4 rectas
    assert b.curvas[t].texto == "{Text}"                       # lo guardado no cambia
    lz.seleccion = {t}
    caja = lz._caja_marco()
    assert caja is None or caja[2] - caja[0] < 10              # el marco es el de la «I»
    lz.valores_parametros = lambda: {"Text": "{noexiste}"}
    assert any(g[0] == "circulo" for g in lz.geometria_real()) # los demás perfiles no se pierden


def _ventanas_que_se_muestran(funcion):
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QApplication
    vistas = []

    class Espia(QObject):
        def eventFilter(self, o, e):
            if e.type() == QEvent.Show and o.isWidgetType() and o.isWindow():
                vistas.append(type(o).__name__)
            return False
    espia = Espia()
    QApplication.instance().installEventFilter(espia)
    try:
        funcion()
    finally:
        QApplication.instance().removeEventFilter(espia)
    return vistas


def test_armar_un_panel_no_muestra_ninguna_ventana_suelta(app_qt):
    """B-136: `setVisible(True)` sobre un widget sin padre lo abre como ventana hasta que un layout lo adopta."""
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.formulario import Seccion, fila_mensaje
    from omnicad.ui.visor3d import Visor3D
    s = api.Sesion()
    visor = Visor3D()
    guardados = []

    def armar():
        guardados.append(fila_mensaje(100, 20))
        guardados.append(Seccion("Una sección"))
        guardados.append(PanelComando(CATALOGO["extruir"](), ContextoComando(s.doc, None), visor, {}))
    assert _ventanas_que_se_muestran(armar) == []
    guardados[-1].cancelar()
    visor.deleteLater()


@hay_arial
def test_una_letra_elige_el_texto_entero_y_elegir_el_boceto_toma_todo_sin_los_huecos(app_qt):
    from omnicad.timeline.operaciones import OpExtrusion
    from omnicad.ui.comando import ContextoComando, PanelComando, hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.visor3d import Visor3D
    s = api.Sesion()
    _c, _t, br = hola(s)
    estado, bid = s.doc.estado_final, s.paso("b").id
    visor = Visor3D()
    visor.resize(500, 400)
    visor.set_modelo(estado)
    panel = PanelComando(CATALOGO["extruir"](), ContextoComando(s.doc, None), visor, {})
    panel.show()
    panel._activar(next(c for c in panel.campos if c.clave == "perfiles"))
    hits = {round(p.area): hit_desde_ref({"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(p)}, estado)
            for p in br.perfiles}
    for area in (171, 313):                                    # la L y la O
        panel._elegida(hits[area])
        assert len(panel.valores["perfiles"]) == 4, area
        panel._elegida(hits[area])
        assert panel.valores["perfiles"] == []
    panel._elegida(hits[404])                                  # el hueco de la O
    assert panel.valores["perfiles"] == [] and visor.es_hueco_texto(hits[404])
    assert visor.hits_texto(hits[10207]) is None               # el disco se elige solo
    panel._elegida(hits[171])                                  # el texto ya elegido: el boceto suma lo que falta
    assert panel.elegir_boceto(bid)
    assert len(panel.valores["perfiles"]) == 5                 # las 4 letras y el disco
    assert panel.elegir_boceto(bid) and panel.valores["perfiles"] == []       # otra vez: sale
    assert panel.elegir_boceto("no_existe") is False
    panel.cancelar()
    visor.deleteLater()


def _paradas(lado="izq", **opciones):
    return fuentes.paradas_en_camino("AB", ((-50, 0), (50, 0)), "Arial", 10, posicion=0.5, lado=lado, **opciones)


@hay_arial
@pytest.mark.parametrize("ajustar", [False, True])
def test_el_cursor_de_un_texto_volteado_en_curva_sigue_a_las_letras(ajustar):
    normal, espejo = _paradas(ajustar=ajustar), _paradas(ajustar=ajustar, voltear_h=True)
    for (abajo, arriba), (abajo_v, arriba_v) in zip(normal, espejo, strict=True):
        assert abajo_v == pytest.approx((-abajo[0], abajo[1]), abs=1e-6)         # la primera parada queda a la derecha
        assert arriba_v == pytest.approx((-arriba[0], arriba[1]), abs=1e-6)


@hay_arial
def test_el_cursor_volteado_de_arriba_abajo_y_el_del_boceto_siguen_a_las_letras():
    from omnicad.restricciones.boceto import Boceto, paradas_cursor, primitivas_entidad
    normal, espejo = _paradas(), _paradas(voltear_v=True)
    alto = max(q[1] for g in fuentes.contornos_en_camino("AB", ((-50, 0), (50, 0)), "Arial", 10)
               for q in (g[2:4] if g[0] == "linea" else g[2]))
    for (abajo, _), (abajo_v, _) in zip(normal, espejo, strict=True):
        assert abajo_v == pytest.approx((abajo[0], alto - abajo[1]), abs=1e-6)
    b = Boceto()
    linea = b.agregar_linea((-50, 0), (50, 0))
    t = b.curvas[b.agregar_texto((0, 0), "AB", altura=10, camino=linea, alineacion="centro", voltear_h=True)]
    prim = primitivas_entidad(b.curvas[linea], b.coords)[0]
    assert paradas_cursor(t, (0, 0), prim)["paradas"][0][0][0] > 0            # el boceto le pasa el volteo al cursor


def _parametros(s):
    return {p.nombre: p.expresion for p in s.doc.parametros}


def _texto_h(**extra):
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    t = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "H", "font": "Arial", "height": 30, **extra}))["entities"][0]["id"]
    return s, t


def _altura(s, t):
    return s.doc.estado_final.bocetos[s.paso("b").id].boceto.curvas[t].altura


@hay_arial
def test_cada_texto_crea_text_y_text_height_y_un_deshacer_los_quita_junto_con_el_texto():
    s, t = _texto_h()
    assert _parametros(s) == {"Text": "H", "Text_height": "30 mm"}
    ok(api.llamar(s, "add_text", {"sketch": "b", "text": "I", "font": "Arial", "height": 7.5}))
    assert _parametros(s)["Text_1"] == "I" and _parametros(s)["Text_height_1"] == "7.5 mm"
    ok(api.llamar(s, "undo", {}))
    assert set(_parametros(s)) == {"Text", "Text_height"}
    ok(api.llamar(s, "set_parameter", {"name": "Text_height", "expression": "12 mm"}))
    assert _altura(s, t) == pytest.approx(12)


@hay_arial
def test_cambiar_la_altura_de_un_texto_ligado_cambia_su_text_height_y_no_lo_suelta():
    s, t = _texto_h()
    ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "height": 12}))
    assert _parametros(s)["Text_height"] == "12 mm" and _altura(s, t) == pytest.approx(12)
    ok(api.llamar(s, "create_parameter", {"name": "ancho", "expression": "20 mm"}))
    ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "height": "ancho / 2"}))
    assert _parametros(s)["Text_height"] == "ancho / 2" and _altura(s, t) == pytest.approx(10)
    ok(api.llamar(s, "set_parameter", {"name": "ancho", "expression": "40 mm"}))
    assert _altura(s, t) == pytest.approx(20)
    ok(api.llamar(s, "transform_sketch", {"sketch": "b", "entities": [t], "scale": 2}))
    assert _parametros(s)["Text_height"] == "40 mm" and _altura(s, t) == pytest.approx(40)
    ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "height": "Text_height * 2"}))     # se cita a sí mismo
    assert _altura(s, t) == pytest.approx(80) and _parametros(s)["Text_height"] == "40 mm"


@hay_arial
def test_copiar_un_texto_con_escala_no_cambia_el_original():
    s, t = _texto_h()
    ok(api.llamar(s, "transform_sketch", {"sketch": "b", "entities": [t], "scale": 2, "dx": 100, "copy": True}))
    br = s.doc.estado_final.bocetos[s.paso("b").id]
    assert sorted(c.altura for c in br.boceto.curvas.values() if c.tipo == "texto") == pytest.approx([30, 60])
    assert _parametros(s)["Text_height"] == "30 mm"


@hay_arial
def test_sketch_from_spec_liga_el_texto_y_una_receta_vieja_sigue_sin_parametro_de_altura():
    from omnicad.restricciones.boceto import Boceto
    s = api.Sesion()
    ok(api.llamar(s, "sketch_from_spec", {"plane": "XY", "name": "b", "entities": [
        {"type": "text", "text": "H", "font": "Arial", "height": 9}]}))
    assert _parametros(s) == {"Text": "H", "Text_height": "9 mm"}
    b = Boceto()
    t = b.agregar_texto((0, 0), "H", altura=9)
    assert "parametro_altura" not in b.curvas[t].a_dict()
    assert Boceto.desde_dict(b.a_dict()).curvas[t].parametro_altura is None


@hay_arial
def test_desglosar_borra_los_parametros_del_texto_salvo_el_que_use_otro():
    s, t = _texto_h()
    ok(api.llamar(s, "explode_text", {"sketch": "b", "entity": t}))
    assert _parametros(s) == {}
    ok(api.llamar(s, "undo", {}))
    assert set(_parametros(s)) == {"Text", "Text_height"}
    ok(api.llamar(s, "create_parameter", {"name": "doble", "expression": "Text_height * 2"}))
    ok(api.llamar(s, "explode_text", {"sketch": "b", "entity": t}))
    assert set(_parametros(s)) == {"Text_height", "doble"}                     # Fusion: el que usa otro no se borra


@pytest.mark.skipif(importlib.util.find_spec("omnikernel") is None, reason="Sin el módulo omnikernel")
def test_omnikernel_tampoco_lista_los_restos_sin_area():
    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import motor

    def rectangulo(primero, x0, y0, x1, y1):
        esquinas = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return [("linea", primero + i, esquinas[i], esquinas[(i + 1) % 4]) for i in range(4)]
    plano = geo.Plano("XY")
    cinta, cuadro = rectangulo(1, 0.0, 0.0, 30.0, 5e-4), rectangulo(5, 0.0, 10.0, 1.0, 11.0)
    with motor.fijar_motor("omnikernel"):
        assert [round(p.area, 3) for p in pf.detectar(cinta + cuadro, plano)] == [1.0]
    with motor.fijar_motor("opencascade"):
        assert [round(p.area, 3) for p in pf.detectar(cinta + cuadro, plano)] == [1.0]


@pytest.mark.skipif(importlib.util.find_spec("omnikernel") is None, reason="Sin el módulo omnikernel")
def test_omnikernel_extruye_un_perfil_comun(monkeypatch):
    monkeypatch.setenv("OMNICAD_MOTOR", "omnikernel")
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    ok(api.llamar(s, "draw_rectangle", {"sketch": "b", "x1": 0, "y1": 0, "x2": 10, "y2": 10}))
    ok(api.llamar(s, "extrude", {"sketch": "b", "profile": 0, "distance": 5}))
    assert len(ok(api.llamar(s, "get_scene_info", {}))["bodies"]) == 1


@hay_arial
def test_la_barra_del_texto_va_en_porcentaje_del_ancho_medio(app_qt):
    from PySide6.QtWidgets import QLabel
    from test_texto_vectores import _lienzo_con_cuadro
    b, lz = _lienzo_con_cuadro("HH")                                          # cuadro de 20 mm de alto
    assert "Espaciado (%)" in [e.text() for e in lz.entrada.findChildren(QLabel)]
    cien = fuentes.espaciado_cien("Arial", 20)
    for escrito, pct in (("10", 10), ("10,5", 10.5), ("10 %", 10), ("-5", -5), ("", 0)):
        lz.entrada.campos[3].setText(escrito)
        assert lz.opciones["espaciado"] == pytest.approx(pct * cien / 100), escrito
    lz.entrada.campos[3].setText("abc")                                       # a medias: el último valor bueno queda
    assert lz.opciones["espaciado"] == pytest.approx(0.0)
    lz.entrada.aceptado.emit(["HH", "20", "0", "25", "1"])
    t = next(c for c in b.curvas.values() if c.tipo == "texto")
    assert t.espaciado == pytest.approx(0.25 * cien)
    lz.editar_texto(t.id, lz.a_px(0, 0))
    assert lz.entrada.campos[3].text() == "25"
    lz.entrada.aceptado.emit(["HH", "40", "0", "25", "1"])
    assert t.espaciado == pytest.approx(0.5 * cien)                           # el % se mantiene con otra altura


@pytest.mark.parametrize("fuente, mm", [("Arial", 6.1664), ("Times New Roman", 5.9193), ("Courier New", 10.5043)])
def test_el_cien_por_ciento_es_el_ancho_medio_de_la_fuente_medido_en_fusion(fuente, mm):
    if fuentes.buscar_fuente(fuente) is None:
        pytest.skip(f"No hay {fuente} instalada")
    assert fuentes.espaciado_cien(fuente, 10) == pytest.approx(mm, abs=1e-4)
    assert fuentes.espaciado_cien(fuente, 25) == pytest.approx(2.5 * mm, abs=1e-3)      # sigue a la altura


@hay_arial
@pytest.mark.parametrize("letra", ["H", "i"])
def test_character_spacing_suma_lo_mismo_con_cualquier_letra(letra):
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    ok(api.llamar(s, "add_text", {"sketch": "b", "text": letra * 11, "font": "Arial", "height": 10}))
    t = ok(api.llamar(s, "add_text", {"sketch": "b", "text": letra * 11, "font": "Arial", "height": 10, "y": 30,
                                      "character_spacing": 100}))["entities"][0]["id"]
    br = s.doc.estado_final.bocetos[s.paso("b").id]
    x = {i: [q[0] for g in br.boceto.geometria() if g[1] == i for q in ((g[2], g[3]) if g[0] == "linea" else g[2])]
         for i in {g[1] for g in br.boceto.geometria()}}
    anchos = sorted(max(v) - min(v) for v in x.values())
    assert (anchos[1] - anchos[0]) / 10 == pytest.approx(6.1664, abs=1e-3)
    g = ok(api.llamar(s, "get_sketch", {"sketch": "b"}))
    datos = next(e for e in g["entities"] if e["id"] == t)
    assert datos["character_spacing"] == pytest.approx(100) and datos["letter_spacing"] == pytest.approx(6.1664, abs=1e-3)


@hay_arial
def test_character_spacing_en_las_demas_herramientas():
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    t = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "HH", "font": "Arial", "height": 10}))["entities"][0]["id"]
    ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "character_spacing": 50}))
    assert s.paso("b").boceto.curvas[t].espaciado == pytest.approx(3.0832, abs=1e-3)
    r = api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "character_spacing": 50, "letter_spacing": 1})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"
    r = ok(api.llamar(s, "sketch_from_spec", {"name": "c", "plane": "XY", "entities": [
        {"type": "text", "text": "HH", "height": 10, "character_spacing": 100}]}))
    b = s.paso("c").boceto
    assert next(c for c in b.curvas.values() if c.tipo == "texto").espaciado == pytest.approx(6.1664, abs=1e-3)


@hay_arial
def test_el_espaciado_sigue_a_text_height_y_un_texto_viejo_queda_igual():
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    t = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "HH", "font": "Arial", "height": 10,
                                      "letter_spacing": 1.5}))["entities"][0]["id"]
    bid = s.paso("b").id

    def resuelto():
        return s.doc.estado_final.bocetos[bid].boceto.curvas[t]

    ok(api.llamar(s, "set_parameter", {"name": "Text_height", "expression": "20 mm"}))
    assert (resuelto().altura, resuelto().espaciado) == (pytest.approx(20), pytest.approx(3.0))
    ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "x": 5}))       # editar no vuelve a escalarlo
    assert (resuelto().altura, resuelto().espaciado) == (pytest.approx(20), pytest.approx(3.0))
    s.paso("b").boceto.curvas[t].altura_a = False                              # un texto de antes: guarda mm a su escala
    ok(api.llamar(s, "set_parameter", {"name": "Text_height", "expression": "40 mm"}))
    assert (resuelto().altura, resuelto().espaciado) == (pytest.approx(40), pytest.approx(3.0))


@hay_arial
def test_la_copia_de_un_texto_escala_su_espaciado_con_text_height():
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    t = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "HH", "font": "Arial", "height": 10,
                                      "letter_spacing": 1.5}))["entities"][0]["id"]
    r = ok(api.llamar(s, "copy_sketch_entities", {"entities": [t], "source_sketch": "b", "sketch": "b", "dy": 30}))
    copia = next(i for i in s.paso("b").boceto.curvas if i != t and s.paso("b").boceto.curvas[i].tipo == "texto")
    assert r and s.paso("b").boceto.curvas[copia].parametro_altura is None
    ok(api.llamar(s, "set_parameter", {"name": "Text_height", "expression": "20 mm"}))
    resuelto = s.doc.estado_final.bocetos[s.paso("b").id].boceto.curvas[copia]
    assert (resuelto.altura, resuelto.espaciado) == (pytest.approx(20), pytest.approx(3.0))


def _alto(boceto, tid):
    ys = [q[1] for p in boceto.primitivas(tid) for q in ((p[2], p[3]) if p[0] == "linea" else p[2])]
    return max(ys) - min(ys)


@pytest.mark.parametrize("fuente, mm", [("Arial", 6.1664), ("Times New Roman", 5.9193), ("Courier New", 10.5043)])
def test_un_texto_nuevo_mide_como_en_fusion(fuente, mm):
    """B-152: la A mide la altura y, a esa escala, 100 % suma por hueco lo medido en Fusion real, cada fuente con la suya."""
    if fuentes.buscar_fuente(fuente) is None:
        pytest.skip(f"No hay {fuente} instalada")
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    a = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "A", "font": fuente, "height": 10}))["entities"][0]["id"]
    sin, con = (ok(api.llamar(s, "add_text", {"sketch": "b", "text": "H" * 11, "font": fuente, "height": 10, "y": y,
                                              "character_spacing": pct}))["entities"][0]["id"] for y, pct in ((40, 0), (80, 100)))
    b = s.doc.estado_final.bocetos[s.paso("b").id].boceto

    def ancho(tid):
        xs = [q[0] for p in b.primitivas(tid) for q in ((p[2], p[3]) if p[0] == "linea" else p[2])]
        return max(xs) - min(xs)

    assert _alto(b, a) == pytest.approx(10, abs=1e-6)
    assert (ancho(con) - ancho(sin)) / 10 == pytest.approx(mm, abs=1e-3)


@hay_arial
def test_un_texto_de_una_receta_anterior_se_ve_igual_y_el_nuevo_guarda_su_marca(tmp_path):
    from omnicad.restricciones import Boceto
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    t = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "H", "font": "Arial", "height": 10}))["entities"][0]["id"]
    ruta = str(tmp_path / "nuevo.omnicad")
    ok(api.llamar(s, "save_document", {"path": ruta}))
    ok(api.llamar(s, "open_document", {"path": ruta}))
    b = s.doc.estado_final.bocetos[s.paso("b").id].boceto
    assert b.curvas[t].altura_a and _alto(b, t) == pytest.approx(10, abs=1e-6)
    # una receta anterior no trae la marca: la altura sigue siendo el tamaño de la fuente
    receta = b.a_dict()
    curva = next(c for c in receta["curvas"] if c["id"] == t)
    del curva["altura_a"]
    viejo = Boceto.desde_dict(receta)
    assert not viejo.curvas[t].altura_a and _alto(viejo, t) == pytest.approx(7.158, abs=1e-3)
    assert "altura_a" not in viejo.curvas[t].a_dict()


@hay_arial
def test_get_sketch_dice_que_mide_la_altura_y_edit_text_pasa_un_texto_viejo():
    s = api.Sesion()
    ok(api.llamar(s, "create_sketch", {"plane": "XY", "name": "b"}))
    t = ok(api.llamar(s, "add_text", {"sketch": "b", "text": "H", "font": "Arial", "height": 10}))["entities"][0]["id"]

    def medida():
        g = ok(api.llamar(s, "get_sketch", {"sketch": "b"}))
        return next(e for e in g["entities"] if e["id"] == t)["height_basis"]

    assert medida() == "letter_a"
    ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "height_basis": "font_size"}))
    assert medida() == "font_size"
    assert _alto(s.doc.estado_final.bocetos[s.paso("b").id].boceto, t) == pytest.approx(7.158, abs=1e-3)
    ok(api.llamar(s, "edit_text", {"sketch": "b", "entity": t, "height_basis": "letter_a"}))
    assert _alto(s.doc.estado_final.bocetos[s.paso("b").id].boceto, t) == pytest.approx(10, abs=1e-6)


@hay_arial
def test_el_texto_3d_nuevo_mide_la_a_y_el_de_una_receta_anterior_queda_igual():
    from omnicad.restricciones import boceto3d
    nuevo = boceto3d._contornos("A", 10, "Arial")
    viejo = boceto3d._contornos("A", 10, "Arial", False)
    alto = lambda polis: max(q[1] for p in polis for q in p) - min(q[1] for p in polis for q in p)  # noqa: E731
    assert alto(nuevo) == pytest.approx(10, abs=1e-6) and alto(viejo) == pytest.approx(7.158, abs=1e-3)


@hay_arial
def test_los_huecos_de_las_letras_no_se_pintan_sobre_el_disco(app_qt):
    from omnicad.ui.visor3d import perfiles_a_pintar, tris_perfil_terminado
    s = api.Sesion()
    c, t, br = hola(s, path_side="left", path_offset=5)
    huecos = pf.partes_de_texto(br.perfiles, [t])[1]
    pintados = perfiles_a_pintar(br.perfiles, br.boceto)
    assert huecos and not {id(h) for h in huecos} & {id(p) for p in pintados}
    assert any(p.firma == {c} for p in pintados)
    assert len(tris_perfil_terminado(br)) == len(pintados)


@hay_arial
def test_un_texto_viejo_se_ve_igual_y_abrirlo_sin_tocar_no_cambia_sus_mm(app_qt):
    from test_texto_vectores import _lienzo_con_cuadro
    from omnicad.restricciones.boceto import Texto
    assert Texto(1, 0, "HOLA", altura=10, espaciado=1.5).a_dict()["espaciado"] == 1.5      # la receta sigue en mm
    b, lz = _lienzo_con_cuadro("HH")
    lz.entrada.aceptado.emit(["HH", "20", "0", "0", "1"])
    t = next(c for c in b.curvas.values() if c.tipo == "texto")
    t.espaciado = 1.2345678
    lz.editar_texto(t.id, lz.a_px(0, 0))
    lz.entrada.aceptado.emit([c.text() for c in lz.entrada.campos])
    assert t.espaciado == 1.2345678
