"""Gizmos de CONSTRUIR: Plano y Punto sobre una ruta, Plano tangente (ángulo) y Plano perpendicular (distancia)."""
import numpy as np
import pytest
from test_manipuladores import _arrastrar, _doc_caja, _doc_rectangulo, _panel, _visor, app_qt  # noqa: F401  (fixture)

from omnicad import api
from omnicad.nucleo import geometria as g, referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.comandos.construir import METODOS as CATALOGO_CONSTRUIR


def _linea_del_rectangulo(doc):
    curva = next(iter(doc.estado_final.bocetos["op1"].boceto.curvas))
    return hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": curva}, doc.estado_final)


def _abrir(clave, doc, valores):
    p, visor, _ = _panel(CATALOGO[clave](), doc, valores)
    visor.vista("iso")
    p.manipuladores.actualizar()
    return p


def _arrastrar_a(p, desde, hasta):
    gm = p.manipuladores
    xy, ok = gm.pantalla([desde, hasta])
    assert ok.all()
    _arrastrar(p.visor, *xy)


@pytest.mark.parametrize("clave", ["plano_ruta", "punto_ruta"])
def test_asa_de_ruta_se_desliza_y_puede_pasar_el_final(app_qt, clave):  # noqa: F811
    doc = _doc_rectangulo()
    p = _abrir(clave, doc, {"r0": [_linea_del_rectangulo(doc)]})
    gm = p.manipuladores
    asa = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    assert gm.valor("posicion") == 0.5 and "posicion" in gm.cajas
    final = asa.puntos_ruta[np.searchsorted(asa.ts, 1.0)]                       # el extremo de la ruta
    _arrastrar_a(p, asa.asa(gm), final)
    assert gm.valor("posicion") == pytest.approx(1.0, abs=0.03)
    _arrastrar_a(p, asa.asa(gm), asa.puntos_ruta[-1])                           # más allá del final
    assert gm.valor("posicion") > 1.15
    _arrastrar_a(p, asa.asa(gm), asa.puntos_ruta[0])                            # y antes del inicio
    assert gm.valor("posicion") < -0.15
    p._calcular_previa()
    assert p._previa_ok
    p.cancelar()


def test_teclear_la_posicion_mueve_el_asa(app_qt):  # noqa: F811
    doc = _doc_rectangulo()
    p = _abrir("plano_ruta", doc, {"r0": [_linea_del_rectangulo(doc)]})
    gm = p.manipuladores
    asa = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    antes = asa.asa(gm).copy()
    p.set_valor("posicion", "0.9")
    despues = next(m for m in gm.manips if isinstance(m, mp.AsaRuta)).asa(gm)
    assert not np.allclose(antes, despues)
    p.cancelar()


def test_muestras_de_ruta_prolongan_recto_fuera_del_largo():
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Pnt

    from omnicad.nucleo import construccion as cs
    arista = BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(10, 0, 0)).Edge()
    pts = cs.muestras_ruta(arista, [-0.5, 0, 0.5, 1, 1.5])
    assert pts[:, 0] == pytest.approx([-5, 0, 5, 10, 15])


def _doc_cilindro():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="10", alto="30"))
    return doc


def _cara_lateral(doc):
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    cara = next(c for c in refs.subformas(forma, "cara") if "eje" in refs.firma_cara(c))
    return hit_desde_ref(refs.referencia("op1.c1", cara, caja=g.caja_envolvente(forma)), doc.estado_final)


def test_plano_tangente_gira_con_el_asa_de_angulo(app_qt):  # noqa: F811
    doc = _doc_cilindro()
    p = _abrir("plano_tangente", doc, {"r0": [_cara_lateral(doc)]})
    gm = p.manipuladores
    m = next(m for m in gm.manips if isinstance(m, mp.Angulo))
    assert m.radio == pytest.approx(10, abs=1e-6) and np.allclose(abs(m.eje), (0, 0, 1))
    objetivo = m.centro + (m.u * np.cos(np.radians(70)) + m.v * np.sin(np.radians(70))) * m._r(gm)
    _arrastrar_a(p, m.asa(gm), objetivo)
    assert gm.valor("angulo") == pytest.approx(70, abs=2)
    p._calcular_previa()
    assert p._previa_ok
    p.cancelar()


def test_plano_perpendicular_tiene_distancia_con_flecha_y_el_plano_se_corre(app_qt):  # noqa: F811
    doc = _doc_caja()
    cara = next(c for c in refs.subformas(doc.estado_final.cuerpos["op1.c1"].forma, "cara")
                if np.allclose(g.centro_masa(c, True), (10, 10, 20)))
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    hit_cara = hit_desde_ref(refs.referencia("op1.c1", cara, caja=g.caja_envolvente(forma)), doc.estado_final)
    vertice = refs.subformas(forma, "vertice")[0]
    hit_v = hit_desde_ref(refs.referencia("op1.c1", vertice, caja=g.caja_envolvente(forma)), doc.estado_final)
    p = _abrir("plano_perpendicular", doc, {"r0": [hit_cara], "r1": [hit_v]})
    gm = p.manipuladores
    flecha = next(m for m in gm.manips if isinstance(m, mp.Flecha))
    assert flecha.clave == "desfase"
    a, b = flecha.puntos(gm)
    _arrastrar_a(p, (a + b) / 2, (a + b) / 2 + flecha.direccion * 6)
    assert gm.valor("desfase") == pytest.approx(6, abs=0.5)
    p._calcular_previa()
    assert p._previa_ok
    p.cancelar()


def test_api_distance_corre_el_plano_perpendicular_y_sin_ella_nada_cambia():
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 20})
    base = api.llamar(s, "create_construction_plane", {"type": "perpendicular", "references": [">Z", [10, 10, 20]]})
    corrido = api.llamar(s, "create_construction_plane", {"type": "perpendicular", "references": [">Z", [10, 10, 20]],
                                                          "distance": 5})
    assert base["ok"] and corrido["ok"]
    o0, o1 = (np.array(r["result"]["origin"], float) for r in (base, corrido))
    assert np.linalg.norm(o1 - o0) == pytest.approx(5)


# ---------------------------------------------------------------- panel único «Geometría de construcción» (CON-1)
def _doc_y_panel(clave, valores=None):
    doc = _doc_caja()
    p = _abrir(clave, doc, valores or {})
    return doc, p


@pytest.mark.parametrize("clave", list(CATALOGO_CONSTRUIR))
def test_cada_entrada_abre_el_panel_unico_con_tipo_y_metodo(app_qt, clave):  # noqa: F811
    p = _panel(CATALOGO[clave](), _doc_caja(), {})[0]
    assert p.titulo.text() == "GEOMETRÍA DE CONSTRUCCIÓN"
    assert p.valores["tipo"] == clave.split("_")[0] and p.valores["metodo"] == clave
    assert p.widgets["metodo"].findData(clave) >= 0 and not p.widgets["metodo"].itemIcon(p.widgets["metodo"].findData(clave)).isNull()
    p.cancelar()


def test_cambiar_tipo_y_metodo_cambia_las_entradas_y_conserva_lo_que_sirve(app_qt):  # noqa: F811
    doc = _doc_caja()
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    p = _abrir("plano_desfase", doc, {"r0": [plano]})
    p.set_valor("metodo", "plano_medio")
    assert p.valores["r0"] == [plano] and p.etiquetas["r0"].text() == "Plano 1"
    assert p._visible(p._por_clave["r1"]) and not p._visible(p._por_clave["distancia"])
    p.set_valor("metodo", "plano_tangente")                  # un plano no es una cara curva: se suelta
    assert p.valores["r0"] == [] and p.activa.clave == "r0" and p.etiquetas["r1"].text() == "Objeto de referencia"
    p.set_valor("tipo", "punto")
    assert p.valores["metodo"] == "punto_vertice" and p.widgets["metodo"].count() == 6
    p.cancelar()


def test_editar_abre_el_mismo_panel_con_su_metodo_y_tipo_fijo(app_qt):  # noqa: F811
    from omnicad.timeline.operaciones import OpPlano
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos import comando_para
    doc = _doc_caja()
    op = OpPlano(doc.nuevo_id(), "Mi plano", tipo="medio", refs=[{"tipo": "plano", "id": "XY"}, {"tipo": "plano", "id": "XZ"}])
    doc.agregar(op)
    p = PanelComando(comando_para(op)(), ContextoComando(doc, None, op), _visor(doc.estado_final))
    assert p.valores["metodo"] == "plano_medio" and len(p.valores["r0"]) == 1 and len(p.valores["r1"]) == 1
    assert not p.widgets["tipo"].isEnabled() and p.titulo.toolTip() == "EDITAR GEOMETRÍA DE CONSTRUCCIÓN"
    assert p.comando.construir(p.valores, p.ctx).nombre == "Mi plano"
    p.cancelar()


def test_el_visor_no_deja_elegir_una_spline_donde_va_una_linea():
    from omnicad.ui.comando import acepta
    from omnicad.ui.comandos.construir import EJE
    assert not acepta(EJE, {"tipo": "curva_boceto", "ref": {}, "es_linea": False})
    assert acepta(EJE, {"tipo": "curva_boceto", "ref": {}, "es_linea": True})


def test_asa_de_ruta_en_milimetros_y_flecha_sobre_un_eje(app_qt):  # noqa: F811
    doc = _doc_rectangulo()
    p = _abrir("plano_ruta", doc, {"r0": [_linea_del_rectangulo(doc)], "tipo_distancia": "absoluto"})
    gm = p.manipuladores
    gm.actualizar()
    asa = next(m for m in gm.manips if isinstance(m, mp.AsaRuta))
    assert asa.clave == "distancia" and asa.factor > 1
    p.cancelar()
    eje = hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)
    p = _abrir("plano_ruta", doc, {"r0": [eje]})
    gm = p.manipuladores
    gm.actualizar()
    assert p._visible(p._por_clave["distancia"]) and not p._visible(p._por_clave["tipo_distancia"])
    assert [m.clave for m in gm.manips] == ["distancia"]
    p.cancelar()


def test_forzado_con_ctrl_engancha_al_punto_mas_cercano_de_la_cara(app_qt, monkeypatch):  # noqa: F811
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    doc = _doc_caja()
    p = _abrir("punto_vertice", doc, {})
    visor = p.visor
    visor.set_modelo(doc.estado_final)
    visor.repaint()
    medio = visor.proyectar((3, 3, 20))                       # sobre la tapa de la caja, lejos de todo punto de forzado
    assert visor.elegir_entidad(medio, {"forzado"}) is None
    monkeypatch.setattr(QApplication, "keyboardModifiers", staticmethod(lambda: Qt.ControlModifier))
    hit = visor.elegir_entidad(medio, {"forzado"})
    assert hit is not None and hit["tipo"] == "forzado" and hit["ref"]["modo"] == "centro_cara"
    assert hit["punto"] == pytest.approx((10, 10, 20))
    p.cancelar()


def test_nombres_de_planos_siguen_a_las_casillas(app_qt):  # noqa: F811
    from omnicad.nucleo import geometria as geo
    p, visor, _ = _panel(CATALOGO["plano_medio"](), _doc_caja(), {})
    c = visor.config
    c.origen = {"xy": True, "xz": False, "yz": False}
    c.planos_usuario = [("op9", "Tapa", geo.Plano("XY", 5.0))]
    assert [t for t, _q in visor.etiquetas_planos()] == ["XY", "Tapa"]
    c.visibilidad["nombres_planos_construccion"] = False
    assert [t for t, _q in visor.etiquetas_planos()] == ["XY"]
    assert visor.plano_visible("op9")                         # ocultar el nombre no oculta el plano
    c.visibilidad["nombres_planos_origen"] = False
    assert visor.etiquetas_planos() == []
    p.cancelar()


def test_scu_abre_con_forzar_y_panel_de_informacion(app_qt):  # noqa: F811
    doc = _doc_caja()
    p = _panel(CATALOGO["scu"](), doc, {})[0]
    assert [c.clave for c in p.campos if p._visible(c)] == ["origen"]
    info = p.comando.info
    assert not info.isHidden() and "punto de referencia" in info.texto.text()
    info.boton_cerrar.click()
    assert info.isHidden() and p.comando.info is info         # cerrarlo no cancela el comando
    p.set_valor("origen", [hit_desde_ref({"tipo": "punto", "id": "O"}, doc.estado_final)])
    assert {"rx", "ry", "rz", "dx", "dy", "dz", "eje_z", "eje_x"} <= {c.clave for c in p.campos if p._visible(c)}
    assert p.comando.construir(p.valores, p.ctx).p["eje_x"] is None      # Eje X es opcional, como en la API
    p.cancelar()
    assert p.comando.info is None
