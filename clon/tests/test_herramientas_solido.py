# -*- coding: utf-8 -*-
"""Herramientas de SÓLIDO iguales a Fusion (docs/brechas_herramientas_solido.md, CAP-n): campos nuevos del panel y opciones
nuevas, cada una con su resultado numérico y su parámetro en la API."""
import math
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api.sesion import Sesion  # noqa: E402
from omnicad.nucleo import geometria as geo, referencias as refs, solidos_crear as sc  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpPrimitiva  # noqa: E402
from omnicad.ui.comando import (Alternar, Botones, Comando, ContextoComando, Deslizador, Expresion, PanelComando,  # noqa: E402
                                Seleccion)
from omnicad.ui.comandos import CATALOGO  # noqa: E402
from omnicad.ui.visor3d import Visor3D  # noqa: E402


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


def _llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r.get("ok"), r
    return r["result"]


def _caja_redondeada():
    """Caja 40×20×10 con la arista +X+Z empalmada: la tapa, el empalme y la cara +X son una cadena tangente."""
    s = Sesion()
    _llamar(s, "create_box", length=40, width=20, height=10)
    _llamar(s, "fillet", edges="|Y and >X and >Z", radius=3)
    return s


def _volumen(s):
    return sum(geo.volumen(c.forma) for c in s.doc.estado_final.cuerpos.values())


def _panel(comando, doc, valores=None):
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    p = PanelComando(comando, ContextoComando(doc), visor, valores or {})
    return p, visor


def _doc_caja():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20"))
    return doc


# ---------------------------------------------------------------- CAP-10: botones con ícono
class _Prueba(Comando):
    CLAVE, TITULO, ICONO, SIN_OP = "prueba_botones", "Prueba", "caja", True

    def campos(self, ctx):
        return [Botones("modo", "Modo", {"a": ("Primero", "op_unir"), "b": ("Segundo", "op_cortar")}, defecto="b"),
                Alternar("invertir", "Cambiar dirección", "cambiar_direccion"),
                Deslizador("veces", "Veces", 20, 0, 100),
                Seleccion("cosa", "Cosa", {"cuerpo"}, minimo=0, seccion="Sección uno"),
                Expresion("largo", "Largo", "1 mm", seccion="Sección uno"),
                Expresion("suelto", "Suelto", "2 mm"),
                Expresion("extra", "Extra", "3 mm", pestana="Análisis"),
                Seleccion("otra", "Otra", {"cuerpo"}, minimo=0, pestana="Análisis")]

    def construir(self, v, ctx):
        return None


def test_botones_es_un_boton_por_opcion_con_el_nombre_en_el_tooltip_y_el_mismo_valor(app_qt):
    p, _ = _panel(_Prueba(), _doc_caja())
    fila = p.widgets["modo"]
    assert fila.count() == 2 and fila.currentData() == "b"
    assert fila.boton("a").toolTip() == "Primero" and fila.boton("b").toolTip() == "Segundo"
    assert not fila.boton("a").icon().isNull()
    p.show()
    QTest.mouseClick(fila.boton("a"), Qt.LeftButton)
    assert p.valores["modo"] == "a" and fila.currentData() == "a"
    assert fila.boton("a").isChecked() and not fila.boton("b").isChecked()
    p.set_valor("modo", "b")
    assert fila.boton("b").isChecked()
    p.cancelar()


def test_botones_entra_en_el_resumen_y_en_los_preajustes_como_una_lista(app_qt):
    from omnicad.ui import preajustes_ui
    p, _ = _panel(_Prueba(), _doc_caja())
    p.widgets["modo"].setCurrentIndex(0)
    assert preajustes_ui.valores_guardables(p)["modo"] == "a"
    assert p._texto_valor(p._por_clave["modo"], "a") == "Primero"
    p.cancelar()


def test_alternar_queda_apretado_y_guarda_un_booleano(app_qt):
    p, _ = _panel(_Prueba(), _doc_caja())
    b = p.widgets["invertir"]
    assert isinstance(b, QToolButton) and b.toolTip() == "Cambiar dirección"
    p.show()
    QTest.mouseClick(b, Qt.LeftButton)
    assert p.valores["invertir"] is True and b.isChecked()
    p.set_valor("invertir", False)
    assert not b.isChecked()
    p.cancelar()


def test_deslizador_sincroniza_numero_y_barra(app_qt):
    p, _ = _panel(_Prueba(), _doc_caja())
    w = p.widgets["veces"]
    w.deslizador.setValue(55)
    assert w.numero.value() == 55 and p.valores["veces"] == 55
    p.set_valor("veces", 7)
    assert w.deslizador.value() == 7
    p.cancelar()


def test_una_seccion_plegable_guarda_sus_campos_y_lo_de_despues_queda_debajo(app_qt):
    p, _ = _panel(_Prueba(), _doc_caja())
    p.show()
    QApplication.processEvents()
    s = p.plegables["Sección uno"]
    assert s.abierta and s.isAncestorOf(p.widgets["largo"]) and not s.isAncestorOf(p.widgets["suelto"])
    assert p.widgets["suelto"].mapTo(p, QPoint(0, 0)).y() > s.mapTo(p, QPoint(0, 0)).y()
    s.boton.click()
    assert not p.widgets["largo"].isVisible() and not p._a_la_vista(p._por_clave["cosa"])
    p.cancelar()


def test_las_pestanas_muestran_solo_lo_suyo_y_mueven_la_seleccion(app_qt):
    p, visor = _panel(_Prueba(), _doc_caja())
    p.show()
    QApplication.processEvents()
    assert [p.barra_pestanas.tabText(i) for i in range(p.barra_pestanas.count())] == ["Operación", "Análisis"]
    assert p.widgets["largo"].isVisible() and not p.widgets["extra"].isVisible()
    p.barra_pestanas.setCurrentIndex(1)
    QApplication.processEvents()
    assert p.widgets["extra"].isVisible() and not p.widgets["largo"].isVisible()
    assert p.activa.clave == "otra"
    p.barra_pestanas.setCurrentIndex(0)
    assert p.widgets["largo"].isVisible()
    p.cancelar()


# ---------------------------------------------------------------- CAP-12: paneles como Fusion
def _doc(lado=20):
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho=str(lado), largo=str(lado), alto=str(lado)))
    return doc


@pytest.mark.parametrize("clave, campo, valor", [
    ("barrido", "cadena", True), ("rosca", "modelada", False), ("revolucion", "proyectar_eje", True),
    ("division_silueta", "operacion", "vaciado"), ("red", "extender", True), ("engrosar", "cadena", True),
    ("dividir_cara", "cadena", True), ("desmoldeo", "cadena_tangente", True), ("reemplazar_cara", "cadena_tangente", False),
])
def test_valores_por_defecto_del_panel_como_fusion(clave, campo, valor):
    campos = {c.clave: c for c in CATALOGO[clave]().campos(ContextoComando(_doc()))}
    assert campos[campo].defecto is valor or campos[campo].defecto == valor
    assert not campos[campo].avanzado


# Lo que Fusion trae al abrir el panel, igual en el panel y en la herramienta del MCP/CLI (H-92).
# El PARAMS de la operación NO: es lo que calcula una receta guardada sin la clave (SUP-29 y CAP-12).
DEFECTOS_FUSION = [
    # comando, campo del panel, herramienta, parámetro de la API, valor, texto del campo (el de Fusion en español)
    ("revolucion", "proyectar_eje", "revolve", "project_axis", True, "Eje de proyecto"),
    ("sup_revolucion", "proyectar_eje", "create_surface_revolve", "project_axis", True, "Eje de proyecto"),
    ("sup_revolucion", "cadena", "create_surface_revolve", "chain", True, "Selección de cadena"),
    # H-86: «Simétrica» mide el largo total, mitad a cada lado, también al abrir el panel
    ("extruir", "medida", "extrude", "symmetric_measure", "total", "Medida"),
    ("sup_extruir", "medida", "create_surface_extrude", "symmetric_measure", "total", "Medida"),
]


def _defecto_api(herramienta, param):
    h = next(x for x in api.catalogo() if x["nombre"] == herramienta)
    return h["esquema"]["properties"][param]["default"]


@pytest.mark.parametrize("clave, campo, herramienta, param, valor, etiqueta", DEFECTOS_FUSION)
def test_el_defecto_del_panel_y_la_api_es_el_de_fusion(clave, campo, herramienta, param, valor, etiqueta):
    """H-92: la captura de Fusion en español (analisis/capturas_fusion/SUPERFICIE/Revolucion) muestra el panel de
    Revolución con «Eje de proyecto» y «Encadenando» marcados; ese nombre y ese defecto tienen que ser los mismos
    tecleando en la ventana y llamando a la herramienta, y el paso creado por cualquiera de las dos los escribe."""
    cmd = CATALOGO[clave]()
    campo_panel = next(c for c in cmd.campos(ContextoComando(_doc())) if c.clave == campo)
    assert campo_panel.etiqueta == etiqueta, f"{clave} › {campo}: dice «{campo_panel.etiqueta}»"
    assert campo_panel.defecto == valor
    assert _defecto_api(herramienta, param) == valor


def test_el_paso_creado_desde_la_api_lleva_el_defecto_de_fusion_escrito():
    """H-92: `revolve` y `create_surface_revolve` guardan el eje proyectado aunque no se pida, así que el paso que
    abre la ventana trae la casilla marcada; el PARAMS sin la clave sigue calculando como una receta vieja."""
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XZ", name="Perfil")
    _llamar(s, "draw_rectangle", x1=10, y1=0, x2=20, y2=5)
    _llamar(s, "revolve", sketch="Perfil", axis="z", angle="90 deg")
    op = s.doc.operaciones[-1]
    assert op.p["proyectar_eje"] is True
    assert type(op).PARAMS["proyectar_eje"] is False        # la receta vieja, sin la clave, calcula como antes
    s2 = api.Sesion()
    _llamar(s2, "create_sketch", plane="XZ", name="Perfil")
    _llamar(s2, "draw_line", start_x=10, start_y=0, end_x=10, end_y=5)
    curva = _llamar(s2, "get_sketch", sketch="Perfil")["entities"][0]["id"]
    _llamar(s2, "create_surface_revolve", profiles={"sketch": "Perfil", "curve": curva}, axis="z", angle="90 deg")
    op2 = s2.doc.operaciones[-1]
    assert op2.p["proyectar_eje"] is True and op2.p["cadena"] is True


def test_eje_perpendicular_al_perfil_no_estorba():
    """H-92: con la casilla marcada por defecto, girar una recta de un boceto XY alrededor del eje Z tiene que dar
    el cilindro de siempre (2·π·10·20 = 1256,64 mm²): un eje perpendicular no se proyecta y queda donde está."""
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XY", name="B")
    _llamar(s, "draw_line", start_x=10, start_y=0, end_x=10, end_y=20)
    curva = _llamar(s, "get_sketch", sketch="B")["entities"][0]["id"]
    cid = _llamar(s, "create_surface_revolve", profiles={"sketch": "B", "curve": curva}, axis="z",
                  angle="360 deg")["bodies_created"][0]["id"]
    assert geo.area(s.cuerpo(cid).forma) == pytest.approx(2 * math.pi * 10 * 20, rel=1e-6)


def test_eje_de_proyecto_con_aristas_de_un_cuerpo_no_estorba():
    """Con el defecto nuevo (marcado), girar aristas de un cuerpo sigue andando: sin plano de perfil no hay nada
    que proyectar, así que la casilla encendida por defecto no puede ser un error para el que no la tocó."""
    areas = []
    for extra in ({}, {"project_axis": False}):
        s = api.Sesion()
        _llamar(s, "create_surface_box", length=20, width=20, height=20)
        arista = next(e["id"] for e in _llamar(s, "find_edges", selector=">Z")["edges"]
                      if e["direction"] == [1.0, 0.0, 0.0])           # paralela al eje X: malla de revolución limpia
        r = _llamar(s, "create_surface_revolve", profiles=arista, axis="x", angle="90 deg", **extra)
        areas.append(geo.area(s.cuerpo(r["bodies_created"][0]["id"]).forma))
    assert areas[0] == pytest.approx(areas[1], rel=1e-9)


def test_el_orden_de_rosca_y_de_extruir_es_el_de_fusion():
    ctx = ContextoComando(_doc())
    orden = [c.clave for c in CATALOGO["rosca"]().campos(ctx)]
    claves = ["caras", "modelada", "largo_completo", "tipo_rosca", "mano", "recordar"]
    assert [orden.index(c) for c in claves] == sorted(orden.index(c) for c in claves)
    orden = [c.clave for c in CATALOGO["extruir"]().campos(ctx)]
    assert orden.index("perfiles") < orden.index("inicio") < orden.index("direccion")


def test_agujero_trae_la_seccion_configuracion_de_la_forma_con_punto_de_taladro(app_qt):
    p, _ = _panel(CATALOGO["agujero"](), _doc())
    assert "Configuración de la forma" in p.plegables
    assert isinstance(p._por_clave["punta"], Botones) and not p._por_clave["punta"].avanzado
    assert p._por_clave["punta"].opciones["plana"][0] == "Plano" and p._por_clave["hasta"].etiqueta == "A"
    p.cancelar()


def test_un_paso_modelado_vuelve_a_abrir_con_roscado_y_la_casilla_modelado():
    doc = _doc()
    cmd = CATALOGO["agujero"]()
    ctx = ContextoComando(doc)
    from omnicad.timeline.ops_solido import OpAgujero
    v = cmd.desde_op(OpAgujero("x", rosca="modelada", designacion="M8", posiciones=[]), ctx)
    assert v["rosca"] == "cosmetica" and v["rosca_modelada"] is True
    assert cmd._rosca_del_paso(v) == "modelada"


def test_textos_de_fusion_en_operacion_y_desplazamiento():
    from omnicad.ui.comandos import comunes, modificar
    assert comunes.OPCIONES_OPERACION["intersecar"][0] == "Intersección"
    assert comunes.OPCIONES_OPERACION["nuevo"][0] == "Cuerpo nuevo"
    assert modificar.TIPOS_DESPLAZAMIENTO["rotacion"][0] == "Rotar"


# ---------------------------------------------------------------- CAP-6: cadena
def _cara(s, selector, cuerpo=None):
    return api.llamar(s, "find_faces", {"selector": selector, **({"body": cuerpo} if cuerpo else {})})["result"]["faces"][0]["id"]


def test_engrosar_con_cadena_suma_las_caras_tangentes():
    solo = _caja_redondeada()
    tapa = _cara(solo, ">Z")
    _llamar(solo, "thicken", faces=tapa, thickness=1)
    sola = geo.volumen(solo.doc.estado_final.cuerpos["op3.c1"].forma)
    cadena = _caja_redondeada()
    _llamar(cadena, "thicken", faces=_cara(cadena, ">Z"), thickness=1, chain=True)
    con = geo.volumen(cadena.doc.estado_final.cuerpos["op3.c1"].forma)
    # tapa 37×20 sola; con la cadena se suman el empalme y la cara +X (7×20) y el volumen tiene que subir al menos eso.
    assert sola == pytest.approx(37 * 20, rel=0.02)
    assert con > sola + 7 * 20 * 0.9
    assert geo.es_valida(cadena.doc.estado_final.cuerpos["op3.c1"].forma)


def test_dividir_cara_con_cadena_tambien_parte_las_tangentes():
    def caras(chain):
        s = _caja_redondeada()
        _llamar(s, "split_face", faces=_cara(s, ">Z"), tool="XZ", chain=chain)
        return len(geo.caras(s.doc.estado_final.cuerpos["op1.c1"].forma))
    # la caja redondeada tiene 7 caras; XZ pasa por Y = 0: sin cadena parte la tapa, con cadena también empalme y cara +X.
    assert caras(False) == 8 and caras(True) == 10


def test_desmoldeo_con_cadena_tangente_inclina_las_tangentes_y_sin_ella_solo_la_elegida():
    def caso(chain):
        s = Sesion()
        _llamar(s, "create_box", length=30, width=30, height=20, x=15, y=15)
        _llamar(s, "fillet", edges="|Z and >X and >Y", radius=4)
        return s, api.llamar(s, "draft", {"faces": _cara(s, ">X"), "angle": 5, "neutral": "XY", "tangent_chain": chain})
    s, r = caso(True)
    assert r["ok"] and _volumen(s) < 17931.33 - 500                  # la cadena inclina cara +X, empalme y cara +Y
    assert geo.es_valida(s.doc.estado_final.cuerpos["op1.c1"].forma)
    s, r = caso(False)
    assert not r["ok"] or _volumen(s) != pytest.approx(16927.53, rel=1e-6)   # sola, la cara no arrastra a las tangentes
    from omnicad.timeline.ops_modificar import OpDesmoldeo
    assert OpDesmoldeo.PARAMS["cadena_tangente"] is True             # una receta vieja sigue inclinando igual


def test_reemplazar_cara_con_cadena_tangente_lleva_toda_la_cadena(monkeypatch):
    from omnicad.nucleo import solidos_modificar as sm
    from omnicad.timeline.ops_modificar import OpReemplazarCara
    assert OpReemplazarCara.PARAMS["cadena_tangente"] is False       # una receta vieja sigue igual
    vistas = []
    monkeypatch.setattr(sm, "reemplazar_cara", lambda forma, caras, destino: vistas.append(len(caras)) or forma)
    for chain in (False, True):
        s = _caja_redondeada()
        _llamar(s, "replace_face", faces=_cara(s, ">Z"), target="XY", tangent_chain=chain)
    assert vistas == [1, 3]                                          # tapa sola; tapa, empalme y cara +X


def test_solevacion_con_cadena_arma_la_seccion_con_las_aristas_tangentes():
    s = Sesion()
    _llamar(s, "create_box", length=20, width=20, height=5, x=10, y=10)
    _llamar(s, "fillet", edges="|Z", radius=3)
    _llamar(s, "create_construction_plane", plane="XY", offset=30)
    _llamar(s, "create_sketch", plane=s.doc.operaciones[-1].id)
    bid = s.doc.operaciones[-1].id
    _llamar(s, "draw_circle", sketch=bid, center_x=10, center_y=10, radius=6)
    aristas = api.llamar(s, "find_edges", {"selector": ">Z"})["result"]["edges"]
    _llamar(s, "loft", sections=[aristas[0]["id"], {"sketch": bid, "profile": 0}], chain=True)
    nuevos = [c for k, c in s.doc.estado_final.cuerpos.items() if k != "op1.c1"]
    assert len(nuevos) == 1 and geo.es_valida(nuevos[0].forma)
    assert geo.volumen(nuevos[0].forma) > math.pi * 36 * 30 * 0.9


# ---------------------------------------------------------------- CAP-4: toroide
@pytest.mark.parametrize("posicion, mayor", [("inside", 15), ("center", 20), ("outside", 25)])
def test_toroide_con_posicion_corre_el_tubo_respecto_del_circulo(posicion, mayor):
    s = Sesion()
    _llamar(s, "create_torus", major_diameter=40, minor_diameter=10, position=posicion)
    forma = s.doc.estado_final.cuerpos["op1.c1"].forma
    assert geo.volumen(forma) == pytest.approx(2 * math.pi ** 2 * mayor * 25, rel=1e-3)
    caja = np.array(geo.caja_envolvente(forma))
    assert caja[1][0] == pytest.approx(mayor + 5, abs=1e-3)


def test_toroide_sin_posicion_abre_igual_que_antes():
    assert OpPrimitiva.PARAMS["posicion_toroide"] == "centro"
    s = Sesion()
    _llamar(s, "create_torus", major_radius=20, minor_radius=5)
    assert geo.volumen(s.doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(2 * math.pi ** 2 * 20 * 25, rel=1e-3)


def test_el_panel_del_toroide_reabre_la_posicion_y_avisa_si_no_entra(app_qt):
    from omnicad.ui.comando import ErrorComando
    doc = Documento()
    cmd = CATALOGO["toroide"]()
    ctx = ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    assert cmd.campos(ctx)[1].etiqueta == "Diámetro interior"
    v.update(posicion_toroide="exterior")
    op = cmd.construir(v, ctx)
    assert op.p["posicion_toroide"] == "exterior"
    assert cmd.desde_op(op, ctx)["posicion_toroide"] == "exterior"
    v.update(posicion_toroide="interior", diametro="12 mm", diametro_tubo="10 mm")
    with pytest.raises(ErrorComando):
        cmd.construir(v, ctx)


# ---------------------------------------------------------------- CAP-5: llenado de contorno
def _dos_planos_y_caja():
    s = Sesion()
    _llamar(s, "create_box", length=20, width=20, height=20)
    return s


def test_llenado_de_contorno_elimina_las_herramientas():
    s = _dos_planos_y_caja()
    _llamar(s, "create_box", length=20, width=20, height=20, x=10, name="B")
    ids = list(s.doc.estado_final.cuerpos)
    _llamar(s, "create_boundary_fill", tools=ids, cells=[1], remove_tools=True)
    quedan = s.doc.estado_final.cuerpos
    assert not set(ids) & set(quedan) and len(quedan) == 1
    assert geo.volumen(next(iter(quedan.values())).forma) == pytest.approx(10 * 20 * 20, rel=1e-3)


def test_el_panel_de_llenado_elige_celdas_con_la_lista_y_con_las_casillas(app_qt):
    s = _dos_planos_y_caja()
    _llamar(s, "create_box", length=20, width=20, height=20, x=10, name="B")
    doc = s.doc
    cuerpos = [{"tipo": "cuerpo", "cuerpo": c} for c in doc.estado_final.cuerpos]
    from omnicad.ui.comando import hit_desde_ref
    p, visor = _panel(CATALOGO["relleno_contorno"](), doc, {"herramientas": [hit_desde_ref(r, doc.estado_final) for r in cuerpos]})
    p.show()
    QApplication.processEvents()
    lista = p.widgets["celdas"]
    assert lista.count() == 3 and lista.item(0).checkState() == Qt.Checked
    lista.item(1).setCheckState(Qt.Checked)
    assert p.valores["celdas"] == "1, 2"
    p._calcular_previa()
    assert p.ultima_op.p["celdas"] == [0, 1]
    casillas = p.comando.manipuladores(p.ctx, p.valores)[0]
    assert [i[2] for i in casillas.items] == ["ok", "ok", "suprimida"]
    assert casillas.alternar(3) == {"celdas": "1, 2, 3"}
    p.set_valor("celdas", "2")
    assert [lista.item(i).checkState() == Qt.Checked for i in range(3)] == [False, True, False]
    prims = p.comando.previa_vista(p.ctx, p.valores, p.ultima_op)
    assert len(prims) == 3 and prims[1][3] > prims[0][3]
    p.cancelar()


# ---------------------------------------------------------------- CAP-9: selección
def test_escala_tiene_una_sola_fila_entidades_para_cuerpos_y_bocetos():
    doc = _doc()
    cmd = CATALOGO["escala_3d"]()
    campos = cmd.campos(ContextoComando(doc))
    assert campos[0].clave == "entidades" and campos[0].filtros == {"cuerpo", "curva_boceto"}
    assert "cuerpos" not in {c.clave for c in campos} and "bocetos" not in {c.clave for c in campos}


def test_alinear_toma_el_cuerpo_de_desde():
    from omnicad.ui.comando import hit_desde_ref
    doc = _doc()
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    cara = refs.subformas(forma, "cara")[0]
    ctx = ContextoComando(doc)
    cmd = CATALOGO["alinear"]()
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    assert v["objeto"] == "cuerpos"
    v.update(origen=[hit_desde_ref(refs.referencia("op1.c1", cara, forma), doc.estado_final)],
             destino=[hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)], cuerpos=[])
    assert cmd.construir(v, ctx).p["cuerpos"] == ["op1.c1"]


def test_definir_punto_de_giro_entra_al_modo_y_se_cierra_con_terminado(app_qt):
    p, _ = _panel(CATALOGO["mover_copiar"](), _doc())
    b = p.widgets["definir_pivote"]
    assert not p._visible(p._por_clave["pivote"]) and b.toolTip() == "Definir punto de giro"
    p.show()
    QTest.mouseClick(b, Qt.LeftButton)
    assert p._visible(p._por_clave["pivote"]) and b.toolTip() == "Terminado"
    QTest.mouseClick(b, Qt.LeftButton)
    assert not p._visible(p._por_clave["pivote"]) and b.toolTip() == "Definir punto de giro"
    p.cancelar()


def test_mover_una_curva_suelta_deja_las_demas_en_su_lugar():
    s = Sesion()
    _llamar(s, "create_sketch", plane="XY")
    bid = s.doc.operaciones[-1].id
    _llamar(s, "draw_line", sketch=bid, start_x=0, start_y=0, end_x=10, end_y=0)
    _llamar(s, "draw_line", sketch=bid, start_x=0, start_y=20, end_x=10, end_y=20)
    boceto = s.doc.estado_final.bocetos[bid].boceto
    primera, segunda = list(boceto.curvas)[:2]
    _llamar(s, "move_body", sketch_curves=[{"sketch": bid, "curve": segunda}], translate=[0, 5, 0])
    final = s.doc.estado_final.bocetos[bid].boceto
    assert final.puntos_de([primera]) and final.coords(final.curvas[primera].p1)[1] == pytest.approx(0)
    assert final.coords(final.curvas[segunda].p1)[1] == pytest.approx(25)
    r = api.llamar(s, "move_body", {"sketch_curves": [{"sketch": bid, "curve": segunda}], "translate": [0, 0, 5]})
    assert not r["ok"] and "plano" in r["mensaje"]


def test_tocar_un_paso_del_timeline_lo_suma_a_las_operaciones_de_simetria(app_qt):
    s = Sesion()
    _llamar(s, "create_box", length=20, width=20, height=20)
    doc = s.doc
    primero = doc.operaciones[0]
    p, _ = _panel(CATALOGO["simetria_3d"](), doc, {"objeto": "operaciones"})
    p.comando.al_tocar_paso(p, primero.id)
    assert p.valores["pasos"] == primero.nombre
    p.comando.al_tocar_paso(p, primero.id)
    assert p.valores["pasos"] == ""
    p.set_valor("objeto", "cuerpos")
    p.comando.al_tocar_paso(p, primero.id)
    assert p.valores["pasos"] == ""
    p.cancelar()


# ---------------------------------------------------------------- CAP-2: los 18 tipos de rosca y las 6 cónicas
def _rosca_media(fam):
    """La designación del tipo con el diámetro más cerca de 12 mm: chica para modelar rápido, sin ser diminuta."""
    tams = sc.tamanos_rosca(fam)
    return min((sc.datos_rosca(sc.designaciones_rosca(fam, t)[0]) for t in tams), key=lambda d: abs(d["diametro"] - 12))


PARALELAS = [k for k, f in sc.FAMILIAS_ROSCA.items() if not f["conica"]]
CONICAS = [k for k, f in sc.FAMILIAS_ROSCA.items() if f["conica"]]


def test_estan_los_24_tipos_en_el_orden_de_fusion():
    assert len(PARALELAS) == 18 and len(CONICAS) == 6
    assert sc.FAMILIAS_ROSCA["ansi_metrica"]["nombre"] == "Perfil en M métrico ANSI" == list(sc.FAMILIAS_ROSCA.values())[0]["nombre"]
    assert sc.tamanos_rosca("iso_metrica")[0] == "M0.25" and sc.tamanos_rosca("iso_metrica")[-1] == "M1060"
    t = sc.tamanos_rosca("unificada")
    assert t.index("#1") < t.index("1/4") < t.index("4") == len(t) - 1      # por diámetro, aunque se hayan sumado filas


def test_las_filas_viejas_de_la_tabla_no_cambian():
    d = sc.datos_rosca("M10")
    assert (d["designacion"], d["paso"], d["diametro"], d["broca"]) == ("M10x1.5", 1.5, 10.0, 8.5)
    assert sc.datos_rosca("GB M6x1")["familia"] == "gb_metrica" and sc.datos_rosca("M6x1")["familia"] == "iso_metrica"


@pytest.mark.parametrize("fam", PARALELAS)
def test_cada_tipo_cosmetica_y_modelada(fam):
    d = _rosca_media(fam)
    largo = round(max(5 * d["paso"], 6), 2)
    s = Sesion()
    _llamar(s, "create_cylinder", diameter=d["diametro"], height=largo)
    vol = _volumen(s)
    _llamar(s, "create_thread", faces="%CYLINDER", thread=d["designacion"], modeled=False)
    assert _volumen(s) == pytest.approx(vol)
    _llamar(s, "undo")
    _llamar(s, "create_thread", faces="%CYLINDER", thread=d["designacion"], modeled=True)
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma)
    nucleo = math.pi * d["diametro_menor"] ** 2 / 4 * largo
    assert nucleo * 0.9 < _volumen(s) < vol                      # le sacó material y no pasó del núcleo


@pytest.mark.parametrize("fam", [k for k in PARALELAS if sc.FAMILIAS_ROSCA[k].get("solo_exterior")])
def test_solo_exterior_no_va_en_un_agujero(fam):
    d = _rosca_media(fam)
    s = Sesion()
    _llamar(s, "create_box", length=30, width=30, height=10)
    r = api.llamar(s, "create_hole", {"face": ">Z", "diameter": d["diametro_menor"], "depth": 5, "hole_tap": "cosmetic",
                                      "thread": d["designacion"]})
    assert not r["ok"] and "solo exterior" in r["mensaje"]
    assert api.llamar(s, "thread_info", {"thread": d["designacion"]})["result"]["external_only"] is True


@pytest.mark.parametrize("fam", CONICAS)
def test_cada_conica_en_agujero(fam):
    d = _rosca_media(fam)
    s = Sesion()
    _llamar(s, "create_box", length=40, width=40, height=30)
    vol = _volumen(s)
    _llamar(s, "create_hole", face=">Z", depth=15, hole_tap="taper", thread=d["designacion"])
    assert geo.es_valida(next(iter(s.doc.estado_final.cuerpos.values())).forma)
    assert _volumen(s) < vol - math.pi * (d["diametro_menor"] / 2) ** 2 * 15 * 0.8


def _lateral(s):
    """Hit de la primera cara cilíndrica del primer cuerpo."""
    from omnicad.ui.comando import hit_desde_ref
    cid, cuerpo = next(iter(s.doc.estado_final.cuerpos.items()))
    cara = next(c for c in refs.subformas(cuerpo.forma, "cara") if refs.firma_cara(c)["geom"] == "cilindro")
    return hit_desde_ref(refs.referencia(cid, cara, cuerpo.forma), s.doc.estado_final)


def test_designacion_y_biblioteca_del_panel(app_qt):
    from omnicad.ui.comandos.crear import Rosca
    s = Sesion()
    _llamar(s, "create_cylinder", diameter=12, height=20)
    p, _ = _panel(Rosca(), s.doc)
    p.set_valor("caras", [_lateral(s)])
    assert p.valores["tipo_rosca"] == "iso_metrica" and p.widgets["des_tipo_rosca"].currentText() == "Automático"
    p.set_valor("tam_iso_metrica", "M10")
    combo = p.widgets["des_tipo_rosca"]
    assert [combo.itemData(i) for i in range(combo.count())][:2] == ["auto", "M10x1.5"] and combo.count() > 3
    assert p.comando.construir(p.valores, p.ctx).p["designacion"] == "M10x1.5"          # «Automático»: la de paso preferido
    p.set_valor("des_tipo_rosca", "M10x1.25")
    assert p.comando.construir(p.valores, p.ctx).p["designacion"] == "M10x1.25"
    p.set_valor("tipo_rosca", "gb_metrica")
    assert p.valores["des_tipo_rosca"] == "auto"                                        # la de otro tipo no queda colgada
    tipo = p.widgets["tipo_rosca"]
    assert tipo.count() == 18
    p.widgets["biblioteca"].mas.click()
    dlg = p.biblioteca
    dlg.tipo.setCurrentIndex(dlg.tipo.findData("din_madera"))
    dlg.filtro.setText("3x")
    assert not dlg.seleccionar.isEnabled() and dlg.tabla.rowCount() >= 1
    dlg.tabla.selectRow(0)
    elegida = dlg.elegida()
    dlg.seleccionar.click()
    assert (p.valores["tipo_rosca"], p.valores["des_tipo_rosca"]) == ("din_madera", elegida) and elegida.startswith("DIN ")
    assert p.widgets["des_tipo_rosca"].currentData() == elegida and " " not in p.widgets["des_tipo_rosca"].currentText()
    p.cancelar()


def test_una_cara_interior_no_ofrece_los_solo_exteriores(app_qt):
    from omnicad.ui.comandos.crear import Rosca
    s = Sesion()
    _llamar(s, "create_box", length=30, width=30, height=10)
    _llamar(s, "create_hole", face=">Z", diameter=8, depth=5)
    p, _ = _panel(Rosca(), s.doc)
    p.set_valor("caras", [_lateral(s)])
    tipo = p.widgets["tipo_rosca"]
    assert tipo.findData("din_madera") < 0 and tipo.findData("iso_metrica") >= 0 and tipo.count() == 12
    p.cancelar()


# ---------------------------------------------------------------- CAP-3 y SUP-20: opciones de análisis y pestaña Análisis
def _esfera():
    from omnicad.nucleo import analisis as an
    s = Sesion()
    _llamar(s, "create_sphere", radius=10)
    return s, an, next(iter(s.doc.estado_final.cuerpos.values())).forma


def test_cebra_opacidad_y_rayas_fijas():
    from omnicad.nucleo import analisis as an
    n = np.random.default_rng(1).normal(size=(200, 3))
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    assert np.unique(np.round(an.colores_cebra(n, (0, 0, 1), opacidad=100).astype(float), 2)).tolist() == [0.06, 0.97]
    assert an.colores_cebra(n, (0, 0, 1), opacidad=0) == pytest.approx(0.72)
    assert an.colores_cebra(n, (0, 0, 1), opacidad=50).max() == pytest.approx((0.97 + 0.72) / 2)
    from omnicad.timeline import analisis_vista as av
    s, _an, _f = _esfera()
    fijo = av.calcular("cebra", {"vista_fija": [0.0, 0.0, 1.0]}, s.doc.estado_final)["colores"]
    assert fijo(n, (1, 0, 0)) == pytest.approx(fijo(n, (0, 1, 0)))                    # no sigue a la cámara


def test_mapa_escala_bandas_y_limite():
    s, an, forma = _esfera()
    _v, _n, c1 = an.colores_curvatura(forma, tipo="maxima", rango=1.0)                # κ = 0,1: cerca del verde
    _v, _n, c2 = an.colores_curvatura(forma, tipo="maxima", rango=0.1)                # en el límite: rojo
    assert c1[:, 1].mean() > c2[:, 1].mean() and c2[:, 0].mean() > 0.85
    assert an.colores_curvatura(forma, tipo="maxima", rango=1.0, escala=10)[2] == pytest.approx(c2, abs=0.03)
    assert an.colores_curvatura(forma, tipo="maxima", rango=0.1, opacidad=0)[2] == pytest.approx(0.72)
    from omnicad.timeline import analisis_vista as av
    d = av.calcular("curvatura", {"tipo_curvatura": "gaussiana", "bandas": True, "opacidad": 50, "escala": 2.0}, s.doc.estado_final)
    assert len(next(iter(d["mallas"].values()))[2])


def test_isocurva_tipo_y_peines():
    from omnicad.nucleo import analisis as an
    from omnicad.timeline import analisis_vista as av
    s = Sesion()
    _llamar(s, "create_cylinder", radius=10, height=30)
    ambas = av.calcular("isocurva", {"densidad": 5}, s.doc.estado_final)["capas"]
    solo_u = av.calcular("isocurva", {"densidad": 5, "tipo_iso": "u"}, s.doc.estado_final)["capas"]
    assert len(ambas[0][1]) and len(ambas[1][1]) and len(solo_u[0][1]) and not len(solo_u[1][1])
    con_peines = av.calcular("isocurva", {"densidad": 5, "peines": True, "densidad_peine": 20}, s.doc.estado_final)["capas"]
    assert len(con_peines) == 3 and len(con_peines[2][1])
    recta = np.c_[np.linspace(0, 10, 9), np.zeros(9), np.zeros(9)]
    puas = an.peines_isocurva([recta], densidad=9)["puas"]
    assert np.allclose(puas[:, 0], puas[:, 1])                                       # recta: curvatura nula, sin púas
    t = np.linspace(0, 2 * np.pi, 200)
    puas = an.peines_isocurva([np.c_[10 * np.cos(t), 10 * np.sin(t), 0 * t]], densidad=40)["puas"]
    alto = np.linalg.norm(puas[:, 1] - puas[:, 0], axis=1)
    assert alto.min() > 0 and alto.max() / alto.min() < 1.05                         # círculo: púas parejas


def test_manage_analysis_con_las_opciones_nuevas():
    s, _an, _f = _esfera()
    _llamar(s, "manage_analysis", action="add", type="zebra", opacity=40, lock_stripes=True, high_quality=True, bodies=["op1.c1"])
    _llamar(s, "manage_analysis", action="add", type="curvature", curvature_type="max", limit=0.2, display="bands", scale=2, opacity=70)
    _llamar(s, "manage_analysis", action="add", type="isocurve", density=4, isocurve_type="v", combs=True, comb_density=30, comb_scale=5)
    a = list(s.doc.analisis.values())
    assert a[0]["params"]["opacidad"] == 40 and a[0]["params"]["vista_fija"] and a[0]["params"]["alta_calidad"]
    assert a[1]["params"]["limite"] == 0.2 and a[1]["params"]["bandas"] and a[1]["params"]["escala"] == 2
    assert a[2]["params"]["tipo_iso"] == "v" and a[2]["params"]["peines"] and a[2]["params"]["escala_peine"] == 5
    assert api.llamar(s, "get_viewport_image", {"width": 120, "height": 90})["ok"]
    assert not api.llamar(s, "manage_analysis", {"action": "add", "type": "zebra", "isocurve_type": "u"})["ok"]


def _tres_perfiles():
    """Tres caras planas apiladas (de cajas sueltas) para solevar."""
    s = Sesion()
    for z in (0, 30, 60):
        _llamar(s, "create_box", length=20, width=20, height=2, z=z)
    forma = {k: c.forma for k, c in s.doc.estado_final.cuerpos.items()}
    from omnicad.ui.comando import hit_desde_ref

    def tapa(cid):
        cara = max((c for c in refs.subformas(forma[cid], "cara") if refs.firma_cara(c)["geom"] == "plano"),
                   key=lambda c: geo.caja_envolvente(c)[0][2])
        return hit_desde_ref(refs.referencia(cid, cara, forma[cid]), s.doc.estado_final)
    return s, [tapa(k) for k in forma]


def test_solevacion_lista_con_condicion_por_fila(app_qt):
    s, hits = _tres_perfiles()
    p, _ = _panel(CATALOGO["solevacion"](), s.doc)
    p.set_valor("secciones", hits)
    fila = p.filas_sel["secciones"]
    assert fila.tabla.rowCount() == 3 and fila.tabla.columnCount() == 2
    media = fila.tabla.cellWidget(1, 1)
    assert [media.itemData(i) for i in range(media.count())] == ["libre", "direccion"]
    media.setCurrentIndex(1)
    assert p.valores["medias"] == "2:90 deg:1"
    fila.tabla.selectRow(1)
    assert p._visible(p._por_clave["angulo_medio"]) and not p._visible(p._por_clave["angulo_fin"])
    p.set_valor("angulo_medio", "80 deg")
    op = p.comando.construir(p.valores, p.ctx)
    assert op.p["condiciones_medias"]["1"]["angulo"] == "80 deg" and op.p["cadena"] is True and op.p["fusionar_tangentes"] is True
    fila.abajo.click()
    assert [h["ref"] for h in p.valores["secciones"]] == [h["ref"] for h in (hits[0], hits[2], hits[1])]
    fila.menos.click()
    assert len(p.valores["secciones"]) == 2 and fila.tabla.rowCount() == 2
    p.cancelar()


def test_p147_flechas_del_peso_de_despegue(app_qt):
    """P-147: cada perfil en «Dirección» trae la flecha del Peso de despegue, como Loft de Fusion. Sale del centro del
    perfil en el sentido de la solevación y se corre lo mismo que la sección auxiliar (peso × 0,15 × distancia)."""
    from omnicad.ui import manipuladores as mp
    s, hits = _tres_perfiles()
    p, _ = _panel(CATALOGO["solevacion"](), s.doc, {"secciones": hits})
    assert p.manipuladores.manips == []                       # todo en «Libre»: sin flechas
    p.set_valores({"condicion_inicio": "direccion", "condicion_fin": "direccion", "peso_fin": "2"})
    p.filas_sel["secciones"].tabla.cellWidget(1, 1).setCurrentIndex(1)       # el del medio también en «Dirección»
    p.filas_sel["secciones"].tabla.selectRow(1)
    assert [m.clave for m in p.manipuladores.manips] == ["peso_medio"]     # como Fusion: las del perfil elegido
    p.filas_sel["secciones"].tabla.setCurrentCell(-1, -1)                 # sin fila elegida: los dos extremos
    asas = {m.clave: m for m in p.manipuladores.manips}
    assert set(asas) == {"peso_inicio", "peso_fin"}
    p.filas_sel["secciones"].tabla.selectRow(1)
    asas["peso_medio"] = p.manipuladores.manips[0]
    for clave, z, factor in (("peso_inicio", 2, 4.5), ("peso_medio", 32, 4.5), ("peso_fin", 62, 4.5)):
        a = asas[clave]
        assert isinstance(a, mp.Flecha) and a.origen == pytest.approx((0, 0, z)) and a.factor == pytest.approx(factor)
        assert a.direccion == pytest.approx((0, 0, 1))        # del primer perfil al último, también en el último
    assert asas["peso_fin"].puntos(p.manipuladores)[0] == pytest.approx((0, 0, 62 + 2 * 4.5))
    p.cancelar()


def test_reabrir_solevacion_conserva_fila_y_aristas(app_qt):
    s, hits = _tres_perfiles()
    comando = CATALOGO["solevacion"]()
    p, _ = _panel(comando, s.doc)
    p.set_valor("secciones", hits)
    p.filas_sel["secciones"].tabla.cellWidget(1, 1).setCurrentIndex(1)
    p.set_valor("aristas_tangentes", "mantener")
    op = comando.construir(p.valores, p.ctx)
    p.cancelar()
    s.doc.agregar(op)
    v = comando.desde_op(op, ContextoComando(s.doc))
    assert v["aristas_tangentes"] == "mantener" and v["medias"] == "2:90 deg:1" and len(v["secciones"]) == 3


@pytest.mark.parametrize("clave", ["barrido", "solevacion", "sup_barrido", "sup_solevacion", "parche", "reglada", "extender_sup"])
def test_los_dialogos_traen_la_pestana_analisis(clave, app_qt):
    p, _ = _panel(CATALOGO[clave](), Documento())
    assert [p.barra_pestanas.tabText(i) for i in range(p.barra_pestanas.count())] == ["Operación", "Análisis"]
    p.barra_pestanas.setCurrentIndex(1)
    assert p.widgets["ana_tipo"].count() == 4
    p.cancelar()


def test_la_pestana_analisis_pinta_la_vista_previa(app_qt):
    s, hits = _tres_perfiles()
    p, visor = _panel(CATALOGO["solevacion"](), s.doc)
    p.set_valor("secciones", hits[:2])
    p.barra_pestanas.setCurrentIndex(1)
    p.widgets["ana_tipo"].boton("cebra").click()
    p._calcular_previa()
    assert p._previa_ok, p.mensaje.text()
    assert p.valores["ana_frecuencia"] == 20 and visor.funcion_colores is not None
    p.widgets["ana_tipo"].boton("isocurva").click()
    p._calcular_previa()
    assert visor.funcion_colores is None
    p.widgets["ana_tipo"].boton("ninguno").click()
    p._calcular_previa()
    assert visor.funcion_colores is None
    p.cancelar()


def test_comandos_sueltos_de_analisis_tienen_las_opciones(app_qt):
    doc = _doc()
    for clave, claves in (("cebra", {"orientacion", "frecuencia", "opacidad", "bloquear", "alta_calidad", "cuerpos"}),
                          ("mapa_curvatura", {"tipo_curvatura", "visualizar", "escala", "limite", "opacidad_mapa", "alta_calidad_mapa"}),
                          ("isocurva", {"tipo_iso", "densidad", "peines", "densidad_peine", "escala_peine"})):
        p, _ = _panel(CATALOGO[clave](), doc)
        assert claves <= set(p.valores), clave
        assert p.comando.params(p.valores, p.ctx)
        p.cancelar()


# ---------------------------------------------------------------- rosca modelada: el corte según el largo
@pytest.mark.parametrize("rosca, diametro, largo", [("M8x1.25", 8, 8.75), ("M8x1.25", 8, 15), ("M12x1.75", 12, 8.75), ("M12x1.75", 12, 12),
                                                    ("M16x2", 16, 16), ("M16x2", 16, 18)])
@pytest.mark.parametrize("clase", ["auto", ""])
def test_rosca_modelada_corta_en_cualquier_largo(rosca, diametro, largo, clase):
    d = sc.datos_rosca(rosca)
    s = Sesion()
    _llamar(s, "create_cylinder", diameter=diametro, height=largo)
    vol = _volumen(s)
    _llamar(s, "create_thread", faces="%CYLINDER", thread=rosca, modeled=True, thread_class=clase)
    assert geo.es_valida(next(iter(s.doc.estado_final.cuerpos.values())).forma)
    nucleo = math.pi * d["diametro_menor"] ** 2 / 4 * largo
    assert nucleo * 0.95 < _volumen(s) < vol * 0.95                                    # ni sin cortar ni de más


# ---------------------------------------------------------------- CAP-8: dibujar primitivas con el mouse
def _raton(visor, tipo, p, boton, botones):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent
    p = QPointF(float(p[0]), float(p[1]))
    QApplication.sendEvent(visor, QMouseEvent(tipo, p, p, boton, botones, Qt.NoModifier))


def _dibujar(clave, campo, doc=None, medir=None):
    """Clic en el plano XY en el centro de la vista, mover 60 px a la derecha y clic. Devuelve (panel, punto 3D del primer clic)."""
    from PySide6.QtCore import QEvent
    from omnicad.ui.comando import hit_desde_ref
    doc = doc or Documento()
    p, visor = _panel(CATALOGO[clave](), doc)
    visor.resize(800, 600)
    visor.objetivo = np.zeros(3)
    p.show()
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    o, r = visor.rayo(QPoint(400, 300))
    centro = o + r * (-o[2] / r[2])
    p._activar(p._por_clave[campo])
    p._elegida(dict(plano, punto=centro))
    assert p.manipuladores.trazo is not None
    o, r = visor.rayo(QPoint(460, 260))
    borde = o + r * (-o[2] / r[2])
    _raton(visor, QEvent.MouseMove, (430, 280), Qt.NoButton, Qt.NoButton)
    _raton(visor, QEvent.MouseMove, (460, 260), Qt.NoButton, Qt.NoButton)
    _raton(visor, QEvent.MouseButtonPress, (460, 260), Qt.LeftButton, Qt.LeftButton)
    assert p.manipuladores.trazo is None
    _raton(visor, QEvent.MouseButtonRelease, (460, 260), Qt.LeftButton, Qt.NoButton)
    _raton(visor, QEvent.MouseMove, (500, 200), Qt.NoButton, Qt.NoButton)     # ya fijo: mover no cambia nada
    return p, centro, borde


@pytest.mark.parametrize("clave, campo", [("cilindro", "centro"), ("esfera", "centro"), ("toroide", "centro"), ("bobina", "plano")])
def test_clic_y_mover_dibuja_el_diametro(clave, campo, app_qt):
    p, centro, borde = _dibujar(clave, campo)
    d = float(p.ctx.evaluar(p.valores["diametro"]))
    assert d == pytest.approx(2 * np.linalg.norm(borde - centro), rel=0.02)
    op = p.comando.construir(p.valores, p.ctx)
    assert op is not None
    p.cancelar()


def test_el_prisma_se_dibuja_de_esquina_a_esquina(app_qt):
    p, esquina, opuesta = _dibujar("caja", "centro")
    ancho, largo = (float(p.ctx.evaluar(p.valores[k])) for k in ("ancho", "largo"))
    assert ancho == pytest.approx(abs(opuesta[0] - esquina[0]), rel=0.02) and largo == pytest.approx(abs(opuesta[1] - esquina[1]), rel=0.02)
    op = p.comando.construir(p.valores, p.ctx)
    p.cancelar()
    doc = Documento()
    doc.agregar(op)
    caja = geo.caja_envolvente(next(iter(doc.estado_final.cuerpos.values())).forma)
    assert (caja[0][0], caja[1][0]) == pytest.approx(sorted((esquina[0], opuesta[0])), abs=0.05)


def test_sin_mover_el_clic_va_a_las_asas(app_qt):
    from PySide6.QtCore import QEvent
    from omnicad.ui.comando import hit_desde_ref
    doc = Documento()
    p, visor = _panel(CATALOGO["cilindro"](), doc)
    visor.resize(800, 600)
    p.show()
    p._activar(p._por_clave["centro"])
    p._elegida(dict(hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final), punto=np.zeros(3)))
    _raton(visor, QEvent.MouseButtonPress, (5, 5), Qt.LeftButton, Qt.LeftButton)
    assert p.manipuladores.trazo is None and p.valores["diametro"] == "20 mm"
    _raton(visor, QEvent.MouseButtonRelease, (5, 5), Qt.LeftButton, Qt.NoButton)
    p.cancelar()


def test_bobina_con_el_centro_en_el_clic(app_qt):
    from omnicad.ui.comando import hit_desde_ref
    s = Sesion()
    r = _llamar(s, "create_coil", diameter=20, center_point=[30, 5, 0])
    caja = geo.caja_envolvente(next(iter(s.doc.estado_final.cuerpos.values())).forma)
    assert (caja[0][0] + caja[1][0]) / 2 == pytest.approx(30, abs=0.5) and r
    doc = Documento()
    comando = CATALOGO["bobina"]()
    p, _ = _panel(comando, doc)
    assert not p._visible(p._por_clave["centro"]) and p.etiquetas["plano"].text().startswith("Plano")
    p.set_valor("plano", [dict(hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final), punto=np.array((12.0, 0, 0)))])
    op = comando.construir(p.valores, p.ctx)
    p.cancelar()
    assert op.p["centro_xyz"] == [12.0, 0.0, 0.0]
    doc.agregar(op)
    v = comando.desde_op(op, ContextoComando(doc))
    assert list(v["plano"][0]["punto"]) == [12.0, 0.0, 0.0]


# ---------------------------------------------------------------- CAP-1: Editar cara
def _tapa(s):
    cid, cuerpo = next(iter(s.doc.estado_final.cuerpos.items()))
    cara = max(geo.caras(cuerpo.forma), key=lambda c: geo.caja_envolvente(c)[0][2])
    return cid, cuerpo.forma, cara


def _caja_edicion():
    s = Sesion()
    _llamar(s, "create_box", length=40, width=40, height=10)
    return s


def test_nucleo_editar_cara_da_el_volumen_de_la_cuenta():
    from omnicad.nucleo import editar_cara as ec
    _cid, forma, tapa = _tapa(_caja_edicion())
    g = ec.grilla_cara(tapa, 1, 1)
    assert g["fijos"].shape == (4, 4) and not g["fijos"].any() and int((~g["contorno"]).sum()) == 4   # bicúbica: los 4 de adentro
    r = ec.editar_cara(forma, tapa, 1, 1, {(i, j): (0, 0, 5) for i in (1, 2) for j in (1, 2)})
    assert geo.es_valida(r) and geo.volumen_exacto(r) == pytest.approx(16000 + 1600 * 4 / 16 * 5, rel=1e-6)   # ∫ Bernstein = 1/4


def test_nucleo_editar_cara_lateral_de_cilindro_y_disco():
    from omnicad.nucleo import editar_cara as ec
    s = Sesion()
    _llamar(s, "create_cylinder", radius=10, height=30)
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    lateral = next(c for c in refs.subformas(forma, "cara") if refs.firma_cara(c)["geom"] == "cilindro")
    r = ec.editar_cara(forma, lateral, 4, 2, {(3, 2): (3, 0, 0)})
    assert geo.es_valida(r) and geo.volumen_exacto(r) != pytest.approx(geo.volumen_exacto(forma), rel=1e-3)
    disco = max(geo.caras(forma), key=lambda c: geo.caja_envolvente(c)[0][2])
    g = ec.grilla_cara(disco, 6, 6)
    assert g["fijos"][0, 0] and not g["fijos"][4, 4]                                 # las esquinas de afuera del disco no se mueven
    r = ec.editar_cara(forma, disco, 6, 6, {(4, 4): (0, 0, 4)})
    assert geo.es_valida(r) and geo.volumen_exacto(r) > geo.volumen_exacto(forma) + 10


def test_api_edit_face_guarda_y_reabre_la_forma(tmp_path):
    s = _caja_edicion()
    g = _llamar(s, "get_face_grid", face=">Z")
    assert g["size"] == [4, 4] and g["contour"][0][0] and not g["contour"][1][1] and not g["fixed"][0][0]
    r = _llamar(s, "edit_face", face=">Z", moves=[{"u": 1, "v": 1, "offset": [0, 0, 8]}])
    assert r
    vol = _volumen(s)
    assert vol == pytest.approx(16000 + 1600 / 16 * 8, rel=1e-6)
    assert geo.es_valida(next(iter(s.doc.estado_final.cuerpos.values())).forma)
    ruta = str(tmp_path / "cara.omnicad")
    _llamar(s, "save_document", path=ruta)
    otra = Sesion()
    _llamar(otra, "open_document", path=ruta)
    assert _volumen(otra) == pytest.approx(vol, rel=1e-9)
    assert not api.llamar(s, "edit_face", {"face": ">Z", "moves": [{"u": 1, "offset": [1, 0, 0]}]})["ok"]


def test_acciones_de_seleccion_de_la_grilla():
    from omnicad.ui.comandos import editar_cara as ec
    n = (5, 5)
    assert ec.aumentar({(2, 2)}, *n) == {(i, j) for i in (1, 2, 3) for j in (1, 2, 3)}
    assert ec.contraer(ec.aumentar({(2, 2)}, *n), *n) == {(2, 2)}
    fila = {(1, 2), (2, 2)}
    assert ec.contorno(fila, *n) == {(i, 2) for i in range(5)}
    assert ec.contorno_mas(fila, *n) == {(0, 2), (1, 2), (2, 2), (3, 2)}
    assert ec.contorno_menos({(i, 2) for i in range(5)}, *n) == {(i, 2) for i in (1, 2, 3)}
    assert ec.anilla(fila, *n) == {(i, j) for i in (1, 2) for j in range(5)}
    assert ec.anilla_mas(fila, *n) == {(i, j) for i in (1, 2) for j in (1, 2, 3)}
    assert ec.invertir({(0, 0)}, 2, 2) == {(0, 1), (1, 0), (1, 1)}
    assert ec.rango({(1, 1), (3, 2)}, *n) == {(i, j) for i in (1, 2, 3) for j in (1, 2)}


def _panel_cara(n=1):
    from omnicad.ui.comando import hit_desde_ref
    s = _caja_edicion()
    cid, forma, tapa = _tapa(s)
    comando = CATALOGO["editar_cara"]()
    p, visor = _panel(comando, s.doc)
    visor.resize(800, 600)
    p.set_valor("cara", [hit_desde_ref(refs.referencia(cid, tapa, forma), s.doc.estado_final)])
    if n > 1:
        p.set_valor("n_u", n)
        p.set_valor("n_v", n)
    return s, comando, p, visor


def test_panel_editar_cara_filas_de_fusion(app_qt):
    _s, comando, p, _v = _panel_cara()
    assert p.valores["filtro"] == "todo" and p.widgets["modo"].count() == 4 and p.widgets["espacio"].count() == 4
    assert set(p.plegables) == {"Opciones de selección", "Dividir caras", "Curvatura en peines", "Simetría", "Entradas numéricas"}
    assert not p.plegables["Opciones de selección"].abierta and p.plegables["Dividir caras"].abierta
    assert [m.ident for m in p.manipuladores.manips] == ["grilla_cara"]
    p.set_valor("comprobar", True)
    assert not p.manipuladores.manips
    p.cancelar()


def test_panel_editar_cara_mover_punto_y_reabrir(app_qt):
    s, comando, p, _v = _panel_cara()
    comando.elegir(p, {(1, 1)})
    assert comando.sel == {(1, 1)} and any(isinstance(m, type(p.manipuladores.manips[1])) for m in p.manipuladores.manips[1:])
    p.set_valor("dz", "8 mm")
    assert p.valores["despl"]["1,1"] == pytest.approx([0, 0, 8])
    op = comando.construir(p.valores, p.ctx)
    p.cancelar()
    s.doc.agregar(op)
    assert _volumen(s) == pytest.approx(16000 + 1600 / 16 * 8, rel=1e-6)
    from omnicad.ui.comando import ContextoComando as C
    v = comando.desde_op(op, C(s.doc, None, op))
    assert v["despl"] == op.p["desplazamientos"] and v["cara"]


def test_panel_editar_cara_giro_escala_y_simetria(app_qt):
    _s, comando, p, _v = _panel_cara(4)
    comando.elegir(p, {(2, 3), (3, 3)})
    p.set_valor("sim_u", True)
    p.set_valor("dz", "2 mm")
    assert set(p.valores["despl"]) == {"2,3", "3,3", "4,3"}                          # (3,3) cae en el eje de la grilla de 7
    p.set_valor("dz", "0 mm")
    p.set_valor("sim_u", False)
    comando.elegir(p, {(2, 2), (4, 2)})
    p.set_valor("escala", "2")
    a, b = p.valores["despl"]["2,2"], p.valores["despl"]["4,2"]
    assert a[0] == pytest.approx(-b[0]) and abs(a[0]) > 1                           # se separan desde el centro
    p.set_valor("escala", "1")
    comando.elegir(p, {(2, 2), (4, 2)})
    p.set_valor("rz", "90 deg")
    q = comando._posiciones(p.valores, comando.grilla(p.valores, p.ctx))
    assert q[2, 2][0] == pytest.approx(q[4, 2][0])                                  # quedaron uno arriba del otro
    p.cancelar()


def test_panel_editar_cara_espacio_seleccion_y_dividir(app_qt):
    _s, comando, p, _v = _panel_cara(2)
    comando.elegir(p, {(2, 2)})
    p.set_valor("espacio", "seleccion")
    p.set_valor("dz", "4 mm")
    assert abs(p.valores["despl"]["2,2"][2]) == pytest.approx(4)                     # la normal de la tapa
    forma_antes = dict(p.valores["despl"])
    p.set_valor("n_u", 3)
    assert p.valores["despl"] and p.valores["despl"] != forma_antes
    assert comando.construir(p.valores, p.ctx).p["n_u"] == 3
    p._calcular_previa()
    assert p._previa_ok, p.mensaje.text()
    p.cancelar()


def test_clic_en_la_vista_elige_segun_el_filtro(app_qt):
    from PySide6.QtCore import QEvent
    _s, comando, p, visor = _panel_cara(2)
    p.manipuladores.actualizar()
    g = p.manipuladores.manips[0]
    s, _ok = p.manipuladores.pantalla([g.puntos[2, 2]])
    p.set_valor("filtro", "vertice")
    _raton(visor, QEvent.MouseMove, s[0], Qt.NoButton, Qt.NoButton)
    _raton(visor, QEvent.MouseButtonPress, s[0], Qt.LeftButton, Qt.LeftButton)
    _raton(visor, QEvent.MouseButtonRelease, s[0], Qt.LeftButton, Qt.NoButton)
    assert comando.sel == {(2, 2)}
    p.set_valor("filtro", "arista")
    medio = (p.manipuladores.pantalla([g.puntos[2, 2]])[0][0] + p.manipuladores.pantalla([g.puntos[3, 2]])[0][0]) / 2
    _raton(visor, QEvent.MouseButtonPress, medio, Qt.LeftButton, Qt.LeftButton)
    _raton(visor, QEvent.MouseButtonRelease, medio, Qt.LeftButton, Qt.NoButton)
    assert comando.sel == {(2, 2), (3, 2)}
    p.cancelar()


def test_peines_y_atajos_de_editar_cara(app_qt):
    from PySide6.QtGui import QShortcut
    _s, comando, p, _v = _panel_cara(2)
    p.set_valor("peine_u", True)
    comando.elegir(p, {(2, 2)})
    p.set_valor("dz", "5 mm")
    assert comando.dibujo_peines(p)
    claves = {a.key().toString() for a in p.findChildren(QShortcut)}
    assert {"Alt+W", "Alt+E", "Alt+R", "Alt+Z", "Alt+X", "Alt+C", "Alt+V", "Alt+A", "Alt+S", "Alt+D", "Alt+F", "Alt+P", "Alt+O", "Alt+I",
            "Alt+L", "Alt+K", "Alt+J", "Alt+N", "Alt+M", "Shift+Up", "Shift+Down"} <= claves
    p.cancelar()


# ---------------------------------------------------------------- CAP-13: el contorno y Alt
@pytest.mark.parametrize("dz, volumen", [(5, 18000), (-5, 14000)])
def test_cap13_mover_una_fila_del_contorno_da_el_volumen_de_la_cuenta(dz, volumen):
    from omnicad.nucleo import editar_cara as ec
    _cid, forma, tapa = _tapa(_caja_edicion())
    r = ec.editar_cara(forma, tapa, 1, 1, {(i, 3): (0, 0, dz) for i in range(4)})           # ∫ v³ = 1/4
    assert geo.es_valida(r) and geo.volumen_exacto(r) == pytest.approx(volumen, rel=1e-5)
    assert len(geo.caras(r)) == 6 and geo.caja_envolvente(r)[1][2] == pytest.approx(15 if dz > 0 else 10, abs=1e-2)


def test_cap13_toda_la_grilla_lleva_las_vecinas_y_una_esquina_tambien():
    from omnicad.nucleo import editar_cara as ec
    _cid, forma, tapa = _tapa(_caja_edicion())
    r = ec.editar_cara(forma, tapa, 1, 1, {(i, j): (0, 0, 5) for i in range(4) for j in range(4)})
    assert geo.volumen_exacto(r) == pytest.approx(24000, rel=1e-9) and geo.es_valida(r)
    r = ec.editar_cara(forma, tapa, 1, 1, {(0, 0): (0, 0, 8)})
    assert geo.volumen_exacto(r) == pytest.approx(16000 + 1600 / 16 * 8, rel=1e-5) and geo.es_valida(r)
    assert geo.caja_envolvente(r)[1][2] == pytest.approx(18, abs=1e-2)


def test_cap13_las_vecinas_inclinadas_siguen_en_su_plano():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeWedge

    from omnicad.nucleo import editar_cara as ec
    cuna = BRepPrimAPI_MakeWedge(40.0, 40.0, 20.0, 10.0).Shape()
    tope = max(geo.caras(cuna), key=lambda c: (geo.caja_envolvente(c)[0][1], geo.area(c)))
    r = ec.editar_cara(cuna, tope, 1, 1, {(i, j): (0, 5, 0) for i in range(4) for j in range(4)})
    assert geo.es_valida(r) and geo.volumen_exacto(r) == pytest.approx(20000 + (10 + 6.25) / 2 * 5 * 20, rel=1e-6)


def test_cap13_en_curvas_y_lo_que_queda_fijo():
    from omnicad.nucleo import editar_cara as ec
    forma = geo.cilindro(10, 30)
    lateral, disco = max(geo.caras(forma), key=geo.area), max(geo.caras(forma), key=lambda c: geo.caja_envolvente(c)[0][2])
    g = ec.grilla_cara(lateral, 4, 2)
    assert g["fijos"][0].all() and g["fijos"][-1].all() and g["contorno"][3, 0] and g["contorno"][3, 4]
    p = g["puntos"][3, 4]
    r = ec.editar_cara(forma, lateral, 4, 2, {(3, 4): (p[0] * 0.3, p[1] * 0.3, 0)})
    assert geo.es_valida(r) and geo.volumen_exacto(r) > geo.volumen_exacto(forma) * 1.002
    assert geo.caja_envolvente(r)[1][2] == pytest.approx(30, abs=1e-3)                       # la tapa sigue en su plano
    with pytest.raises(geo.ErrorGeometria, match="queda fijo"):
        ec.editar_cara(forma, lateral, 4, 2, {(0, 2): (1, 0, 0)})
    g = ec.grilla_cara(disco, 6, 6)
    i, j = np.argwhere(g["contorno"])[0]
    r = ec.editar_cara(forma, disco, 6, 6, {(int(i), int(j)): (0, 0, 4)})
    assert geo.es_valida(r) and geo.caja_envolvente(r)[1][2] > 31 and geo.area(r) > geo.area(forma)


def test_cap13_cara_con_un_agujero_ciego_y_cara_ya_editada():
    from omnicad.nucleo import editar_cara as ec
    s = Sesion()
    _llamar(s, "create_box", length=40, width=40, height=10)
    _llamar(s, "create_hole", face=">Z", depth=5, diameter=10)
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    tapa = max(geo.caras(forma), key=lambda c: (round(geo.caja_envolvente(c)[0][2], 3), geo.area(c)))
    r = ec.editar_cara(forma, tapa, 1, 1, {(i, 3): (0, 0, 5) for i in range(4)})
    assert geo.es_valida(r) and geo.volumen_exacto(r) == pytest.approx(17555.9, abs=0.5)     # lo de la caja, menos lo que sube el agujero
    assert len(geo.solidos(r)) == 1
    s = _caja_edicion()
    _llamar(s, "edit_face", face=">Z", moves=[{"u": i, "v": 3, "offset": [0, 0, 5]} for i in range(4)])
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    cara = max(geo.caras(forma), key=lambda c: geo.caja_envolvente(c)[1][2] + geo.area(c) * 1e-3)
    r = ec.editar_cara(forma, cara, 1, 1, {(0, 0): (0, 0, 3)})
    assert geo.es_valida(r) and geo.volumen_exacto(r) == pytest.approx(18000 + 1600 / 16 * 3, rel=1e-4)


def test_cap13_no_pierde_material_de_otro_solido_ni_la_pieza_que_queda_abajo():
    from omnicad.nucleo import editar_cara as ec
    a, b = geo.caja(40, 40, 10), geo.trasladar(geo.caja(10, 10, 10), (100, 0, 0))
    dos = geo.compuesto([a, b])
    tapa = max(geo.caras(a), key=lambda c: geo.caja_envolvente(c)[0][2])
    tapa = next(c for c in geo.caras(dos) if c.IsSame(tapa))
    r = ec.editar_cara(dos, tapa, 1, 1, {(i, 3): (0, 0, 5) for i in range(4)})
    assert len(geo.solidos(r)) == 2 and geo.volumen_exacto(r) == pytest.approx(18000 + 1000, rel=1e-5)
    # una grilla que baja en el medio hasta el piso parte la tapa en dos: quedan las dos
    _cid, forma, tapa = _tapa(_caja_edicion())
    r = ec.editar_cara(forma, tapa, 2, 1, {(2, j): (0, 0, -25) for j in range(4)})
    assert len(geo.solidos(r)) == 2 and geo.es_valida(r)


def test_cap13_superficie_con_la_cara_dada_vuelta():
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Pnt

    from omnicad.nucleo import editar_cara as ec
    from omnicad.nucleo import superficies as sf
    lamina = sf.extruir_superficie(BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(20, 0, 0)).Edge(), (0, 1, 0), 20)
    cara = geo.caras(lamina)[0].Reversed()
    r = ec.editar_cara(cara, geo.caras(cara)[0], 1, 1, {(0, 0): (0, 0, 5)})
    assert geo.es_valida(r) and geo.area(r) > 400 and geo.area(r) < 1000                     # una cara con el contorno al revés daría el plano entero
    assert geo.caras(r)[0].Orientation() == geo.caras(cara)[0].Orientation()


def test_cap13_cortes_de_un_archivo_ajeno_y_punto_afuera():
    from omnicad.nucleo import editar_cara as ec
    _cid, _forma, tapa = _tapa(_caja_edicion())
    for malo in ("abc", 5, [None], [0.0], [float("nan")]):
        with pytest.raises(geo.ErrorGeometria, match="cortes"):
            ec.grilla_cara(tapa, 1, 1, malo)
    s = _caja_edicion()
    r = api.llamar(s, "edit_face", {"face": ">Z", "extrude": True, "moves": [{"u": 99, "v": 1, "offset": [0, 0, 1]}]})
    assert not r["ok"] and "afuera" in r["mensaje"]


def test_cap13_vecinas_tangentes_suben_a_plomo():
    from omnicad.nucleo import editar_cara as ec
    s = _caja_edicion()
    _llamar(s, "fillet", edges="|Y", radius=2)
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    tapa = max(geo.caras(forma), key=lambda c: (round(geo.caja_envolvente(c)[0][2], 3), geo.area(c)))
    r = ec.editar_cara(forma, tapa, 1, 1, {(i, 3): (0, 0, 3) for i in range(4)})
    assert geo.es_valida(r) and len(geo.solidos(r)) == 1
    assert geo.volumen_exacto(r) == pytest.approx(geo.volumen_exacto(forma) + 36 * 40 * 3 / 4, rel=1e-4)


def test_desfase_de_caras_con_un_agujero_ciego_sigue_siendo_solido():
    s = _caja_edicion()
    _llamar(s, "create_hole", face=">Z", depth=5, diameter=10)
    _llamar(s, "offset_faces", faces=">Z", distance=3)
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    assert len(geo.solidos(forma)) == 1 and geo.es_valida(forma)
    assert geo.volumen_exacto(forma) == pytest.approx(16000 - 78.54 * 5 + (1600 - 78.54) * 3 + 78.54 * 0, rel=1e-2)


def test_cap13_movimiento_que_no_cambia_nada_y_superficies():
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Pnt

    from omnicad.nucleo import editar_cara as ec
    from omnicad.nucleo import superficies as sf
    _cid, forma, tapa = _tapa(_caja_edicion())
    with pytest.raises(geo.ErrorGeometria, match="misma superficie"):
        ec.editar_cara(forma, tapa, 1, 1, {(0, 0): (5, 0, 0)})
    lamina = sf.extruir_superficie(BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(20, 0, 0)).Edge(), (0, 1, 0), 20)
    cara = geo.caras(lamina)[0]
    r = ec.editar_cara(lamina, cara, 1, 1, {(0, 0): (0, 0, 5)})
    assert geo.es_valida(r) and geo.area(r) > 400 and geo.caja_envolvente(r)[1][2] == pytest.approx(5, abs=1e-3)
    dos = sf.coser([sf.extruir_superficie(BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(20, 0, 0)).Edge(), (0, 1, 0), 20),
                    sf.extruir_superficie(BRepBuilderAPI_MakeEdge(gp_Pnt(20, 0, 0), gp_Pnt(40, 0, 0)).Edge(), (0, 1, 0), 20)], 1e-3)["forma"]
    cara = min(geo.caras(dos), key=lambda c: geo.caja_envolvente(c)[0][0])                   # x de 0 a 20: su borde x = 20 es el cosido
    g = ec.grilla_cara(cara, 1, 1)
    libre = next((int(i), int(j)) for i, j in np.argwhere(g["contorno"]) if g["puntos"][i, j][0] == pytest.approx(0))
    cosido = next((int(i), int(j)) for i, j in np.argwhere(g["contorno"]) if g["puntos"][i, j][0] == pytest.approx(20))
    r = ec.editar_cara(dos, cara, 1, 1, {libre: (0, 0, 5)})
    assert geo.es_valida(r) and len(geo.caras(r)) == 2 and geo.caja_envolvente(r)[1][2] == pytest.approx(5, abs=1e-2)
    assert sf.bordes_de_costura(geo.caras(r), 1e-3)["aristas_cosidas"] == 1
    with pytest.raises(geo.ErrorGeometria, match="borde libre"):
        ec.editar_cara(dos, cara, 1, 1, {cosido: (0, 0, 5)})


def test_cap13_extruir_suma_lineas_sin_cambiar_la_forma():
    from omnicad.nucleo import editar_cara as ec
    _cid, forma, tapa = _tapa(_caja_edicion())
    viejos = {(2, 2): (0.0, 0.0, 6.0)}
    r = ec.extruir_grilla(ec.divisiones(tapa, 2, 2), viejos, {(2, 2)})
    assert len(r["cortes_u"]) == 2 and len(r["cortes_v"]) == 2
    assert ec.grilla_cara(tapa, 2, 2, r["cortes_u"], r["cortes_v"])["puntos"].shape[:2] == (7, 7)
    a = ec.editar_cara(forma, tapa, 2, 2, viejos)
    b = ec.editar_cara(forma, tapa, 2, 2, r["desplazamientos"], r["cortes_u"], r["cortes_v"])
    assert geo.volumen_exacto(b) == pytest.approx(geo.volumen_exacto(a), rel=1e-6)
    i, j = r["puntos"][(2, 2)]
    alto = ec.editar_cara(forma, tapa, 2, 2, {(i, j): (0, 0, 8)}, r["cortes_u"], r["cortes_v"])
    ancho = ec.editar_cara(forma, tapa, 2, 2, {(2, 2): (0, 0, 8)})
    assert geo.es_valida(alto) and geo.volumen_exacto(alto) < geo.volumen_exacto(ancho)      # más cuadros: el bulto es más angosto
    final = (2, 2, [float(c) for c in np.linspace(0.01, 0.31, 32)], [])
    with pytest.raises(geo.ErrorGeometria, match="cortes"):
        ec.extruir_grilla(final, {}, {(5, 2)})
    with pytest.raises(geo.ErrorGeometria, match="cortes"):
        ec.grilla_cara(tapa, 1, 1, [1.5])


def test_cap13_espaciado_de_contorno_suma_una_fila_junto_al_borde():
    from omnicad.nucleo import editar_cara as ec
    _cid, forma, tapa = _tapa(_caja_edicion())
    assert ec.grilla_cara(tapa, 1, 1, espaciado=4)["puntos"].shape[:2] == (6, 6)
    assert ec.divisiones(tapa, 1, 1, espaciado=4)[2] == pytest.approx([0.1, 0.9])
    assert ec.grilla_cara(tapa, 1, 1, espaciado=0)["puntos"].shape[:2] == (4, 4)
    with pytest.raises(geo.ErrorGeometria, match="espaciado"):
        ec.grilla_cara(tapa, 1, 1, espaciado=20)
    with pytest.raises(geo.ErrorGeometria, match="espaciado"):
        ec.grilla_cara(tapa, 1, 1, espaciado=float("inf"))


def test_cap13_api_contorno_extruir_espaciado_y_receta_vieja(tmp_path):
    s = _caja_edicion()
    assert _llamar(s, "get_face_grid", face=">Z", contour_spacing=4)["size"] == [6, 6]
    _llamar(s, "edit_face", face=">Z", moves=[{"u": i, "v": 3, "offset": [0, 0, 5]} for i in range(4)])
    assert _volumen(s) == pytest.approx(18000, rel=1e-5)
    s = _caja_edicion()
    _llamar(s, "edit_face", face=">Z", length_factor=2, width_factor=2, moves=[{"u": 2, "v": 2, "offset": [0, 0, 8]}], extrude=True)
    op = s.doc.operaciones[-1]
    assert len(op.p["cortes_u"]) == 2 and len(op.p["desplazamientos"]) == 1 and _volumen(s) > 16000
    ruta = str(tmp_path / "alt.omnicad")
    _llamar(s, "save_document", path=ruta)
    otra = Sesion()
    _llamar(otra, "open_document", path=ruta)
    assert _volumen(otra) == pytest.approx(_volumen(s), rel=1e-9)
    s = _caja_edicion()
    _llamar(s, "edit_face", face=">Z", contour_spacing="4 mm", moves=[{"u": 2, "v": 2, "offset": [0, 0, 8]}])
    assert s.doc.operaciones[-1].p["espaciado"] == "4 mm" and _volumen(s) > 16000
    assert not api.llamar(s, "edit_face", {"face": ">Z", "moves": [], "extrude": True})["ok"]
    from omnicad.timeline.ops_modificar import OpEditarCara
    s = _caja_edicion()
    cid, forma, tapa = _tapa(s)
    vieja = OpEditarCara(s.doc.nuevo_id(), cara=refs.referencia(cid, tapa, forma), n_u=1, n_v=1, desplazamientos={"1,1": [0, 0, 8]})   # sin claves nuevas
    assert s.doc.agregar(vieja).estado == "ok" and _volumen(s) == pytest.approx(16000 + 1600 / 16 * 8, rel=1e-9)


def test_cap13_panel_contorno_alt_y_reabrir(app_qt):
    from omnicad.ui.comando import ContextoComando as C
    s, comando, p, _v = _panel_cara(2)
    comando.elegir(p, {(0, 0)})
    assert comando.sel == {(0, 0)}                                                           # el contorno ya se elige
    comando.elegir(p, {(2, 2)})
    comando.extruir(p)
    assert len(p.valores["cortes_u"]) == 2 and len(comando.sel) == 1 and p.manipuladores.manips[0].puntos.shape[:2] == (7, 7)
    p.set_valor("dz", "6 mm")
    assert len(p.valores["despl"]) == 1 and next(iter(p.valores["despl"].values())) == pytest.approx([0, 0, 6])
    uno = dict(p.valores["despl"])
    p.set_valor("n_u", 5)
    assert p.manipuladores.manips[0].puntos.shape[0] == 10 and p.valores["despl"] != uno
    p.set_valor("espaciado", "2 mm")
    assert p.manipuladores.manips[0].puntos.shape[0] == 12 and p.valores["despl"]
    p.set_valor("espaciado", "500 mm")                                                       # no entra: rojo, sin romper la grilla
    p.set_valor("espaciado", "2 mm")
    op = comando.construir(p.valores, p.ctx)
    p.cancelar()
    s.doc.agregar(op)
    assert s.doc.resultados[-1].estado in ("ok", "aviso") and _volumen(s) > 16000
    v = comando.desde_op(op, C(s.doc, None, op))
    assert v["cortes_u"] == op.p["cortes_u"] and v["espaciado"] == "2 mm"


def test_cap13_alt_al_arrastrar_la_triada_extruye(app_qt, monkeypatch):
    from omnicad.ui.comandos import editar_cara as modulo
    _s, comando, p, _v = _panel_cara(2)
    comando.elegir(p, {(2, 2)})
    triada = p.manipuladores.manips[1]
    assert isinstance(triada, modulo.TriadaCara)
    llamadas = []
    monkeypatch.setattr(modulo.mp.Triada, "empezar", lambda *a: llamadas.append(a) or {})
    triada.empezar(p.manipuladores, (0, 0), ("eje", 2))
    assert llamadas and not p.valores.get("cortes_u")                                        # sin Alt: la grilla no cambia
    monkeypatch.setattr(modulo.QApplication, "keyboardModifiers", staticmethod(lambda: modulo.mp.Qt.AltModifier))
    triada.empezar(p.manipuladores, (0, 0), ("eje", 2))
    assert len(p.valores["cortes_u"]) == 2
    p.cancelar()


# ---------------------------------------------------------------- lo que encontró la revisión final
@pytest.mark.parametrize("fam", [k for k in PARALELAS if not sc.FAMILIAS_ROSCA[k].get("solo_exterior")])
def test_cada_tipo_modelado_en_un_agujero(fam):
    d = _rosca_media(fam)
    s = Sesion()
    _llamar(s, "create_box", length=40, width=40, height=14)
    _llamar(s, "create_hole", face=">Z", depth=10, hole_tap="modeled", thread=d["designacion"])
    assert geo.es_valida(next(iter(s.doc.estado_final.cuerpos.values())).forma) and _volumen(s) < 40 * 40 * 14


def test_editar_cara_rechaza_factores_y_valores_de_un_archivo_ajeno():
    from omnicad.nucleo import editar_cara as ec
    from omnicad.timeline.ops_modificar import OpEditarCara
    s = _caja_edicion()
    _cid, forma, tapa = _tapa(s)
    with pytest.raises(geo.ErrorGeometria, match="1 a 32"):
        ec.grilla_cara(tapa, 100000, 1)
    with pytest.raises(geo.ErrorGeometria, match="finitos"):
        ec.editar_cara(forma, tapa, 1, 1, {(1, 1): (float("nan"), 0, 0)})
    assert not api.llamar(s, "edit_face", {"face": ">Z", "length_factor": 100000, "moves": []})["ok"]
    assert not api.llamar(s, "get_face_grid", {"face": ">Z", "length_factor": 100000})["ok"]
    assert OpEditarCara.PARAMS["n_u"] == 1
    r = api.llamar(s, "run_operation", {"type": "editar_cara", "params": {"cara": None, "desplazamientos": {"a,b": [0, 0, 1]}}})
    assert not r["ok"]


def test_dividir_caras_conserva_la_forma_editada():
    from omnicad.nucleo import editar_cara as ec
    _cid, forma, tapa = _tapa(_caja_edicion())
    viejos = {(1, 1): (0.0, 0.0, 8.0)}
    nuevos = ec.remuestrear(viejos, (1, 1), (2, 2))
    a = geo.volumen_exacto(ec.editar_cara(forma, tapa, 1, 1, viejos))
    b = geo.volumen_exacto(ec.editar_cara(forma, tapa, 2, 2, nuevos))
    assert b == pytest.approx(a, rel=1e-6)                                           # 2 refina a 1: la misma superficie


def test_panel_dividir_dos_veces_el_mismo_factor_no_suaviza(app_qt):
    _s, comando, p, _v = _panel_cara()
    comando.elegir(p, {(1, 1)})
    p.set_valor("dz", "8 mm")
    p.set_valor("n_u", 2)
    uno = dict(p.valores["despl"])
    comando.al_cambiar(p, "n_u")
    assert p.valores["despl"] == uno
    p.cancelar()


def test_quitar_un_perfil_del_medio_no_traba_aceptar(app_qt):
    s, hits = _tres_perfiles()
    p, _ = _panel(CATALOGO["solevacion"](), s.doc)
    p.set_valor("secciones", hits)
    fila = p.filas_sel["secciones"]
    fila.tabla.cellWidget(1, 1).setCurrentIndex(1)
    assert p.valores["medias"]
    fila.tabla.selectRow(1)
    fila.menos.click()
    assert p.valores["medias"] == "" and p.comando.construir(p.valores, p.ctx) is not None
    p.cancelar()


def test_preajuste_mueve_el_numero_y_el_deslizador(app_qt):
    p, _ = _panel(CATALOGO["cebra"](), _doc())
    p.set_valores({"frecuencia": 40})
    assert p.widgets["frecuencia"].numero.value() == 40 and p.widgets["frecuencia"].deslizador.value() == 40
    p.cancelar()
