# -*- coding: utf-8 -*-
"""Hallazgos de las pruebas de uso (PROJECT_LOG.md › «Hallazgos de pruebas de uso»), uno por prueba:
Seleccionar sale de la herramienta de boceto, Insertar SVG/DXF/imagen dentro del boceto abierto, Medir con cota
guía y valor en vivo, menú del timeline según el tipo de paso y primitivas como comando con panel."""
import math
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import geometria as g  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPrimitiva  # noqa: E402

PLANO = g.Plano("XY")
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="20mm" viewBox="0 0 40 20">'
       '<rect x="0" y="0" width="40" height="20" fill="none" stroke="#000"/>'
       '<circle cx="10" cy="10" r="5" fill="none" stroke="#000"/></svg>')


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("prefs") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    QTest.qWait(1)
    yield v
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False                  # si no, al cerrar pregunta si se descartan los cambios (modal)
    v.close()
    v.deleteLater()
    QTest.qWait(1)


@pytest.fixture
def v(ventana):
    """La ventana con un documento nuevo y sin boceto ni panel abiertos."""
    ventana.set_documento(Documento())
    yield ventana
    if ventana.panel is not None:
        ventana.panel.cancelar()
    if ventana.modo_boceto.activo:
        ventana.modo_boceto.cancelar()


@pytest.fixture
def svg(tmp_path):
    ruta = tmp_path / "dibujo.svg"
    ruta.write_text(SVG, encoding="utf-8")
    return ruta


# ---------------------------------------------------------------- 1. Seleccionar sale de la herramienta de boceto
def test_seleccionar_sale_de_la_herramienta_de_boceto(v):
    mb = v.modo_boceto
    mb.iniciar(Boceto(), PLANO, {"op": None, "plano": "XY"})
    mb.herramienta("linea")
    assert mb.lienzo.herramienta == "linea"
    v.visor.set_modo("orbita")
    v.acciones["seleccionar"].trigger()                   # botón SELECCIONAR › Seleccionar de la cinta
    assert mb.lienzo.herramienta == "seleccionar"         # antes seguía en «linea» (modo dibujo)
    assert v.visor.modo is None
    assert not mb.acciones["sk_linea"].isChecked()          # la cinta del boceto ya no marca Línea


def test_seleccionar_fuera_del_boceto_corta_la_eleccion_de_plano(v):
    v.crear_boceto()
    assert v.visor.modo == "elegir_plano" and v._eleccion == "boceto"
    v.acciones["seleccionar"].trigger()
    assert v.visor.modo is None and v._eleccion is None


# ---------------------------------------------------------------- 2. Insertar SVG/DXF/imagen dentro del boceto
def test_insertar_svg_en_el_boceto_abierto_no_cambia_de_plano(v, svg):
    from omnicad.ui.comandos import CATALOGO
    mb = v.modo_boceto
    plano = g.Plano.desde_marco((7, 0, 15), (1, 0, 0), (0, 1, 0))      # plano vertical x = 7 (no es el XY)
    b = Boceto()
    b.agregar_circulo((100, 0), 3)
    mb.iniciar(b, plano, {"op": None, "plano": "cara", "marco": plano.marco(), "cara": None})
    antes = len(mb.lienzo.b.curvas)
    panel = v.ejecutar_comando(CATALOGO["insertar_svg"](), valores={"archivo": str(svg)})
    assert mb.activo and v.visor.modo != "elegir_plano"        # antes: salía del boceto y pedía un plano
    assert "plano" not in panel.widgets                          # no pide plano: va al boceto abierto
    panel.set_valor("dx", "5 mm")
    panel._calcular_previa()
    previa = v.visor._capas.get("previa_insertar")
    assert previa and len(previa[0][1]) > 0
    assert np.allclose(previa[0][1][:, 0], 7)                    # la vista previa está en el plano del boceto
    panel.aceptar()
    assert v.panel is None and mb.activo
    nuevas = len(mb.lienzo.b.curvas) - antes
    assert nuevas == 5                                            # rectángulo (4 líneas) + círculo
    xs = [mb.lienzo.b.coords(p)[0] for p in mb.lienzo.b.puntos]
    assert min(xs) == pytest.approx(5)                            # desplazamiento X aplicado
    assert "previa_insertar" not in v.visor._capas
    mb.lienzo.deshacer()                                           # un solo paso de deshacer del boceto
    assert len(mb.lienzo.b.curvas) == antes
    mb.terminar()
    op = v.doc.operaciones[-1]
    assert isinstance(op, OpBoceto) and len(v.doc.operaciones) == 1
    assert np.allclose(v.doc.estado_final.bocetos[op.id].plano.normal, (1, 0, 0))   # el plano no cambió


def test_insertar_dxf_en_el_boceto_y_terminar_cierra_el_panel(v, tmp_path):
    from omnicad.io_archivos.dxf import escribir_dxf
    from omnicad.ui.comandos import CATALOGO
    ruta = tmp_path / "linea.dxf"
    escribir_dxf(str(ruta), [("linea", (0, 0), (30, 0)), ("circulo", (0, 0), 4)])
    mb = v.modo_boceto
    mb.iniciar(Boceto(), PLANO, {"op": None, "plano": "XY", "marco": None, "cara": None})
    panel = v.ejecutar_comando(CATALOGO["insertar_dxf"](), valores={"archivo": str(ruta)})
    assert mb.activo and panel is v.panel
    mb.terminar()                                                  # «Terminar boceto» con el panel abierto
    assert v.panel is None


def test_lienzo_sigue_pidiendo_plano_aunque_haya_un_boceto():
    from omnicad.ui.comandos.insertar import InsertarDXF, InsertarSVG, Lienzo, VectorizarImagen
    from omnicad.ui.comandos.insertar_en_boceto import admite
    assert admite(InsertarSVG()) and admite(InsertarDXF()) and admite(VectorizarImagen())
    assert not admite(Lienzo())                                   # la imagen de referencia no es geometría del boceto


# ---------------------------------------------------------------- 3. Medir: cota guía, flechas y valor en vivo
class _VentanaFalsa:
    """Lo que Medir y el panel usan de la ventana: el visor y las medidas de abajo a la derecha."""

    def __init__(self, visor):
        self.visor, self.textos = visor, []

    def info_seleccion(self, texto):
        self.textos.append(texto)


def _doc_cajas():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="20", alto="30"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="5", alto="10", x="50"))
    return doc


def _cara(doc, cid, centro):
    from omnicad.nucleo import referencias as refs
    from omnicad.ui.comando import hit_desde_ref
    forma = doc.estado_final.cuerpos[cid].forma
    sub = next(s for s in refs.subformas(forma, "cara") if np.allclose(refs.firma_cara(s)["centro"], centro))
    return hit_desde_ref(refs.referencia(cid, sub, forma), doc.estado_final)


def _visor(doc):
    from omnicad.ui.visor3d import Visor3D
    visor = Visor3D()
    visor.resize(800, 600)
    visor.set_modelo(doc.estado_final)
    visor.vista("iso")
    visor.encuadrar()
    return visor


def _panel(comando, doc, valores=None, op=None):
    from omnicad.ui.comando import ContextoComando, PanelComando
    visor = _visor(doc)
    panel = PanelComando(comando, ContextoComando(doc, _VentanaFalsa(visor), op), visor, valores)
    return panel, visor


def _panel_medir(doc, valores):
    from omnicad.ui.comandos.inspeccionar import Medir
    return _panel(Medir(), doc, valores)


def test_cota_guia_tiene_linea_flechas_y_etiqueta():
    from omnicad.ui import analisis_vista as av
    c = av.cota_guia((0, 0, 0), (10, 0, 0), "10 mm", tam=1.0, vista=(0, 0, 1))
    lineas = [p for p in c["capas"] if p[0] == "lineas"]
    flechas = [p[1] for p in c["capas"] if p[0] == "tris"]
    assert np.allclose(lineas[0][1], [(0, 0, 0), (10, 0, 0)])           # la línea de cota
    assert len(flechas) == 2                                              # una flecha en cada punta
    puntas = sorted(tuple(float(x) for x in np.round(f[0], 6)) for f in flechas)
    assert puntas == [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)]                 # tocan los puntos medidos
    assert all(np.allclose(f[:, 2], 0) for f in flechas)                 # de frente a la vista (plano XY)
    (p, texto), = c["etiquetas"]
    assert np.allclose(p, (5, 0, 0)) and texto == "10 mm"                # valor en el punto medio
    corta = av.cota_guia((0, 0, 0), (1, 0, 0), "1 mm", tam=1.0)
    assert any(p[0] == "lineas" and len(p[1]) == 4 for p in corta["capas"])   # corta: flechas afuera
    d = av.cota_diametro((0, 0, 0), 5, (0, 0, 1), "Ø 10 mm", tam=1.0, vista=(0, 0, 1))
    a, b = d["capas"][0][1]
    assert math.dist(a, b) == pytest.approx(10) and abs(a[2]) < 1e-9


def test_medir_muestra_cota_y_valor_al_elegir(app_qt):
    doc = _doc_cajas()
    a, b = _cara(doc, "op1.c1", (0, 10, 15)), _cara(doc, "op1.c1", (10, 10, 15))
    panel, visor = _panel_medir(doc, {"a": [a], "b": [b]})
    panel._calcular_previa()
    assert "Distancia: 10 mm" in panel.widgets["resultado"].text()       # valor en el panel
    capa = visor._capas["medida"]
    assert sum(1 for p in capa if p[0] == "tris") == 2                    # dos flechas
    linea = next(p[1] for p in capa if p[0] == "lineas")
    assert math.dist(linea[0], linea[1]) == pytest.approx(10)            # entre los puntos más cercanos
    assert visor.textos_etiquetas("medida") == ["10 mm"]                 # valor en la vista, sobre la cota
    panel.cancelar()
    assert "medida" not in visor._capas and visor.textos_etiquetas("medida") == []


def test_medir_una_sola_seleccion_da_diametro_o_area(app_qt):
    from omnicad.nucleo import referencias as refs
    from omnicad.ui.comando import hit_desde_ref
    doc = _doc_cajas()
    forma = doc.estado_final.cuerpos["op2.c1"].forma
    lateral = next(s for s in refs.subformas(forma, "cara") if refs.firma_cara(s)["geom"] == "cilindro")
    hit = hit_desde_ref(refs.referencia("op2.c1", lateral, forma), doc.estado_final)
    panel, visor = _panel_medir(doc, {"a": [hit]})
    panel._calcular_previa()
    assert visor.textos_etiquetas("medida") == ["Ø 10 mm"]
    panel.set_valor("a", [_cara(doc, "op1.c1", (5, 10, 30))])
    panel._calcular_previa()
    assert visor.textos_etiquetas("medida") == ["200 mm²"]
    panel.cancelar()


def test_medir_valor_en_vivo_bajo_el_cursor_antes_del_segundo_clic(app_qt):
    doc = _doc_cajas()
    a, b = _cara(doc, "op1.c1", (0, 10, 15)), _cara(doc, "op1.c1", (10, 10, 15))
    panel, visor = _panel_medir(doc, {"a": [a]})
    panel._calcular_previa()
    visor.entidad_sobre.emit(b)                                           # el ratón pasa por la otra cara
    assert visor.textos_etiquetas("medida_previa") == ["≈ 10 mm"]
    assert visor._capas["medida_previa"]
    visor.entidad_sobre.emit(None)                                        # el ratón se va: se borra
    assert "medida_previa" not in visor._capas
    panel.cancelar()
    visor.entidad_sobre.emit(b)                                           # cerrado: ya no escucha
    assert "medida_previa" not in visor._capas


# ---------------------------------------------------------------- 4. menú del timeline según el tipo de paso
def _doc_timeline():
    from omnicad.timeline.ops_ensamblar import OpUnion
    doc = Documento()
    b = Boceto()
    b.agregar_rectangulo((0, 0), (20, 10))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano="XY", boceto=b))
    perfil = doc.estado_final.bocetos["op1"].perfiles[0]
    doc.agregar(OpExtrusion(doc.nuevo_id(), "Extrusión1", boceto="op1",
                            perfiles=[OpExtrusion.referencia_perfil(perfil)], distancia="5", operacion="nuevo"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Esfera1", forma="esfera", radio="3", x="50"))
    doc.agregar(OpUnion(doc.nuevo_id(), "Unión1", tipo="rigida"))       # incompleta (con error): igual tiene menú
    return doc


def _textos(t, op_id):
    return [e.texto if e is not None else "-" for e in t.entradas_menu(op_id)]


def _entrada(t, op_id, texto):
    return next(e for e in t.entradas_menu(op_id) if e is not None and e.texto == texto)


def test_menu_del_timeline_es_distinto_para_boceto_operacion_y_union(app_qt):
    from omnicad.ui.panel_timeline import PanelTimeline
    t = PanelTimeline()
    t.actualizar(_doc_timeline())
    boceto, extrusion, esfera, union = (_textos(t, f"op{i}") for i in (1, 2, 3, 4))
    assert boceto[0] == "Editar boceto" and "Suprimir boceto" in boceto
    assert extrusion[:2] == ["Editar operación…", "Editar boceto de perfil"]
    assert "Editar boceto de perfil" not in esfera and esfera[0] == "Editar operación…"
    assert union[:2] == ["Editar unión…", "Animar unión"] and "Suprimir unión" in union
    for textos in (boceto, extrusion, esfera, union):
        for comun in ("Renombrar…", "Rodar marcador aquí", "Retroceder antes de este paso", "Buscar en navegador",
                      "Eliminar"):
            assert comun in textos
        assert "Retroceder hasta aquí" not in textos                    # unificado con «Rodar marcador aquí»
        assert "Desactivar operaciones" not in textos and "Configurar" not in textos   # fuera de alcance


def test_menu_del_timeline_emite_lo_que_corresponde(app_qt):
    from omnicad.ui.panel_timeline import PanelTimeline
    t = PanelTimeline()
    doc = _doc_timeline()
    t.actualizar(doc)
    editados, marcas, buscados, animadas = [], [], [], []
    t.editar.connect(editados.append)
    t.marcador.connect(marcas.append)
    t.buscar_navegador.connect(buscados.append)
    t.animar_union.connect(animadas.append)
    _entrada(t, "op2", "Editar boceto de perfil").funcion()           # abre el boceto de la extrusión
    _entrada(t, "op1", "Rodar marcador aquí").funcion()               # marcador justo después del boceto
    _entrada(t, "op3", "Retroceder antes de este paso").funcion()
    _entrada(t, "op3", "Buscar en navegador").funcion()
    _entrada(t, "op4", "Animar unión").funcion()
    assert editados == ["op1"] and marcas == [1, 2] and buscados == ["op3"] and animadas == ["op4"]
    assert not _entrada(t, "op4", "Rodar marcador aquí").habilitada   # el marcador ya está ahí (al final)


def test_menu_con_dos_bocetos_de_perfil_es_un_submenu(app_qt):
    from PySide6.QtWidgets import QMenu

    from omnicad.timeline.ops_solido import OpSolevacion
    from omnicad.ui.panel_timeline import PanelTimeline, _llenar_menu, bocetos_de_perfil
    doc = _doc_timeline()
    b = Boceto()
    b.agregar_circulo((40, 40), 4)
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto2", plano="XY", boceto=b))          # op5
    secciones = [{"tipo": "perfil", "boceto": bid, **OpExtrusion.referencia_perfil(
        doc.estado_final.bocetos[bid].perfiles[0])} for bid in ("op1", "op5")]
    doc.agregar(OpSolevacion(doc.nuevo_id(), "Solevación1", secciones=secciones))   # op6 (coplanares: con error)
    assert [o.id for o in bocetos_de_perfil(doc, doc.operacion("op6"))] == ["op1", "op5"]
    assert bocetos_de_perfil(doc, doc.operacion("op3")) == []
    t = PanelTimeline()
    t.actualizar(doc)
    sub = _entrada(t, "op6", "Editar boceto de perfil")
    assert [h.texto for h in sub.hijos] == ["Boceto1", "Boceto2"]
    editados = []
    t.editar.connect(editados.append)
    sub.hijos[1].funcion()
    assert editados == ["op5"]
    m = QMenu()                                                       # el menú real se arma igual
    _llenar_menu(m, t.entradas_menu("op6"))
    textos = [a.text() for a in m.actions() if not a.isSeparator()]
    assert textos[:2] == ["Editar operación…", "Editar boceto de perfil"]
    assert [a.text() for a in m.actions()[1].menu().actions()] == ["Boceto1", "Boceto2"]


def test_buscar_en_navegador_elige_el_elemento_del_paso(v):
    v.set_documento(_doc_timeline())
    assert v.buscar_en_navegador("op1") == "op1"                       # el boceto
    assert v.navegador.arbol.currentItem() is v.navegador.item("op1")
    assert v.buscar_en_navegador("op2") == "op2.c1"                    # el cuerpo que crea la extrusión
    assert v.navegador.arbol.currentItem() is v.navegador.item("op2.c1")
    assert v.navegador.item("op2.c1").parent().isExpanded()             # la carpeta «Cuerpos» se despliega


def test_api_set_marker_y_get_profile_sketches():
    from omnicad import api
    s = api.Sesion()
    s.doc = _doc_timeline()
    r = api.llamar(s, "set_marker", {"after": "Boceto1"})
    assert r["ok"] and r["result"]["marker"] == 1 and s.doc.marcador == 1
    assert [p["id"] for p in r["result"]["rolled_back"]] == ["op2", "op3", "op4"]
    assert api.llamar(s, "set_marker", {"before": "op3"})["result"]["marker"] == 2
    assert api.llamar(s, "set_marker", {"position": 4})["result"]["marker"] == 4
    assert api.llamar(s, "undo", {})["ok"] and s.doc.marcador == 2          # deshacer devuelve el marcador
    mal = api.llamar(s, "set_marker", {"position": 1, "after": "op1"})
    assert not mal["ok"] and mal["error_kind"] == "INVALID_ARGUMENTS"
    assert api.llamar(s, "set_marker", {"position": 9})["error_kind"] == "INVALID_ARGUMENTS"
    r = api.llamar(s, "get_profile_sketches", {"feature": "Extrusión1"})
    assert r["ok"] and r["result"]["sketches"] == [{"id": "op1", "name": "Boceto1"}]
    assert api.llamar(s, "get_profile_sketches", {"feature": "op3"})["result"]["sketches"] == []


def test_api_set_marker_avanza_aunque_un_paso_tenga_error():
    from omnicad import api
    s = api.Sesion()
    s.doc = _doc_timeline()
    api.llamar(s, "set_marker", {"position": 0})
    r = api.llamar(s, "set_marker", {"position": 4})                     # la unión incompleta queda con error
    assert r["ok"] and r["result"]["marker"] == 4 and [e["id"] for e in r["result"]["errors"]] == ["op4"]
    assert any("Unión1" in a for a in r["avisos"])


# ---------------------------------------------------------------- 5. primitivas: comandos con panel y Diámetro
def _plano_xy(punto):
    return {"tipo": "plano", "ref": {"tipo": "plano", "id": "XY"}, "dibujo": [], "punto": np.asarray(punto, float),
            "plano": g.Plano("XY")}


def test_la_cinta_abre_el_comando_esfera_con_diametro_y_clic_en_plano(v):
    v.acciones["esfera"].trigger()                                        # SÓLIDO › CREAR › Esfera
    panel = v.panel
    assert panel is not None and panel.comando.CLAVE == "esfera"         # panel de comando, no el diálogo viejo
    assert "diametro" in panel.widgets and "radio" not in panel.widgets
    panel.set_valor("diametro", "30 mm")
    panel._elegida(_plano_xy((5, 6, 0)))                                  # clic en el plano XY: ahí va el centro
    assert not panel.widgets["x"].isVisibleTo(panel)                      # X/Y/Z se ocultan: manda el clic
    panel._calcular_previa()
    assert "Centro: (5; 6; 0) mm" in panel.widgets["posicion"].text()
    idents = {m.ident for m in panel.manipuladores.manips}
    assert {"posicion:centro", "flecha:diametro"} <= idents               # aro del centro y asa del diámetro
    panel.aceptar()
    op = v.doc.operaciones[-1]
    assert op.TIPO == "primitiva" and op.nombre == "Esfera1"
    assert op.p["forma"] == "esfera" and op.p["radio"] == "15 mm"         # se guarda el RADIO (receta igual)
    assert (op.p["x"], op.p["y"], op.p["z"]) == ("5 mm", "6 mm", "0 mm")
    cuerpo = next(iter(v.doc.estado_final.cuerpos.values()))
    assert g.volumen(cuerpo.forma) == pytest.approx(4 / 3 * math.pi * 15 ** 3, rel=1e-6)
    assert g.es_valida(cuerpo.forma)


def test_arrastrar_el_aro_mueve_el_centro_por_el_plano(app_qt):
    from omnicad.ui.comandos.primitivas import Esfera
    doc = Documento()
    panel, _visor = _panel(Esfera(), doc, {"centro": [_plano_xy((0, 0, 0))], "diametro": "10 mm"})
    aro = next(m for m in panel.manipuladores.manips if m.ident == "posicion:centro")
    panel.manipuladores.escribir(aro.al_mover(np.array([12.0, -3.0, 0.0])))
    op = panel.comando.construir(panel.valores, panel.ctx)
    assert (op.p["x"], op.p["y"], op.p["z"]) == ("12 mm", "-3 mm", "0 mm")


def test_diametro_y_radio_se_traducen_en_los_dos_sentidos():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.primitivas import diametro_desde_radio, radio_desde_diametro
    doc = Documento()
    doc.parametros.agregar("d_eje", "8 mm")
    ctx = ContextoComando(doc)
    assert radio_desde_diametro("20 mm", ctx) == "10 mm"
    assert radio_desde_diametro("d_eje", ctx) == "(d_eje) / 2"           # sigue al parámetro
    assert diametro_desde_radio("(d_eje) / 2", ctx) == "d_eje"
    assert diametro_desde_radio("10", ctx) == "20 mm"
    assert diametro_desde_radio("d_eje + 1 mm", ctx) == "2 * (d_eje + 1 mm)"


def test_cilindro_sobre_cara_de_arriba_y_de_abajo_y_cara_lateral_rechazada(app_qt):
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.primitivas import Cilindro
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="10"))
    cmd, ctx = Cilindro(), ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    arriba = dict(_cara(doc, "op1.c1", (10, 10, 10)), punto=np.array([10.0, 10.0, 10.0]))
    v.update(centro=[arriba], diametro="6 mm", alto="5 mm")
    op = cmd.construir(v, ctx)
    (x0, y0, z0), (x1, y1, z1) = g.caja_envolvente(doc.previsualizar(op, len(doc.operaciones))[0].cuerpos[f"{op.id}.c1"].forma)
    assert (z0, z1) == pytest.approx((10, 15)) and (x0, x1) == pytest.approx((7, 13))
    abajo = dict(_cara(doc, "op1.c1", (10, 10, 0)), punto=np.array([10.0, 10.0, 0.0]))
    v.update(centro=[abajo])
    op = cmd.construir(v, ctx)
    assert op.p["z"] == "0 mm - (5 mm)"                                   # crece hacia abajo, siguiendo al alto
    (_, _, z0), (_, _, z1) = g.caja_envolvente(doc.previsualizar(op, len(doc.operaciones))[0].cuerpos[f"{op.id}.c1"].forma)
    assert (z0, z1) == pytest.approx((-5, 0))
    v.update(centro=[_cara(doc, "op1.c1", (20, 10, 5))])                  # cara vertical: OpPrimitiva no la orienta
    with pytest.raises(ErrorComando, match="eje en Z"):
        cmd.construir(v, ctx)


def test_clic_cerca_del_centro_de_la_cara_se_engancha(app_qt):
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.primitivas import Cilindro
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="10"))
    cmd, ctx, visor = Cilindro(), ContextoComando(doc), _visor(doc)
    campo = next(c for c in cmd.campos(ctx) if c.clave == "centro")
    cerca = dict(_cara(doc, "op1.c1", (10, 10, 10)), punto=np.array([10.05, 9.97, 10.0]))
    assert np.allclose(cmd.ajustar_hit(campo, cerca, ctx, visor)["punto"], (10, 10, 10))
    lejos = dict(cerca, punto=np.array([4.0, 13.0, 10.0]))
    assert cmd.ajustar_hit(campo, lejos, ctx, visor) is None                # lejos de todo: vale el clic


def test_editar_una_primitiva_vieja_abre_el_comando_y_conserva_la_receta(app_qt):
    from omnicad.ui.comandos import comando_para
    from omnicad.ui.comandos.primitivas import Caja, Toroide
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="20", alto="30", x="1", y="2", z="3"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="toroide", radio_mayor="20 mm", radio_menor="5 mm", z="50"))
    caja, toro = doc.operaciones
    assert comando_para(caja) is Caja and comando_para(toro) is Toroide
    panel, _visor = _panel(Caja(), doc, op=caja)
    assert (panel.valores["x"], panel.valores["ancho"]) == ("1", "10")
    assert "Esquina mínima" in Caja()._texto_posicion(panel.valores, panel.ctx)
    nueva = panel.comando.construir(panel.valores, panel.ctx)
    assert nueva.id == caja.id and nueva.p == caja.p                      # sin cambios: la misma receta
    panel, _visor = _panel(Toroide(), doc, op=toro)
    assert (panel.valores["diametro"], panel.valores["diametro_tubo"]) == ("40 mm", "10 mm")
    panel.set_valor("diametro_tubo", "50 mm")
    with pytest.raises(Exception, match="menor"):
        panel.comando.construir(panel.valores, panel.ctx)


def test_api_primitivas_aceptan_diametro():
    from omnicad import api
    s = api.Sesion()
    api.llamar(s, "create_parameter", {"name": "d", "expression": "12 mm"})
    r = api.llamar(s, "create_sphere", {"diameter": 20})
    assert r["ok"] and s.doc.operaciones[-1].p["radio"] == "10.0"
    assert api.llamar(s, "create_cylinder", {"diameter": "d", "height": 5, "x": 50})["ok"]
    assert s.doc.operaciones[-1].p["radio"] == "(d) / 2"
    assert api.llamar(s, "create_torus", {"major_diameter": 40, "minor_diameter": 10, "z": 80})["ok"]
    assert (s.doc.operaciones[-1].p["radio_mayor"], s.doc.operaciones[-1].p["radio_menor"]) == ("20.0", "5.0")
    for args in ({"radius": 5, "diameter": 10}, {}, {"diameter": -2}):
        assert api.llamar(s, "create_sphere", args)["error_kind"] == "INVALID_ARGUMENTS", args
