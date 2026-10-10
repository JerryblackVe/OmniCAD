# -*- coding: utf-8 -*-
"""Manipuladores en la vista estilo Fusion: flecha de distancia, caja de valor, arcos de ángulo y tríada."""
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPrimitiva


@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class _Ventana:
    """Lo único que el panel usa de la ventana para las medidas de abajo a la derecha."""

    def __init__(self):
        self.textos = []

    def info_seleccion(self, texto):
        self.textos.append(texto)


def _visor(estado):
    from omnicad.ui.visor3d import Visor3D
    v = Visor3D()
    v.resize(800, 600)
    v.set_modelo(estado)
    v.vista("iso")
    v.encuadrar()
    return v


def _doc_rectangulo(plano="XY"):
    doc = Documento()
    b = Boceto()
    b.agregar_rectangulo((0, 0), (20, 10))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano=plano, boceto=b))
    return doc


def _perfil(doc):
    from omnicad.ui.comando import hit_desde_ref
    perfil = doc.estado_final.bocetos["op1"].perfiles[0]
    return hit_desde_ref({"tipo": "perfil", "boceto": "op1", **OpExtrusion.referencia_perfil(perfil)}, doc.estado_final)


def _doc_caja():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20"))
    return doc


def _panel(comando, doc, valores, ventana=None):
    from omnicad.ui.comando import ContextoComando, PanelComando
    visor = _visor(doc.estado_final)
    panel = PanelComando(comando, ContextoComando(doc, ventana), visor, valores)
    estados = []
    panel.previa.connect(estados.append)
    return panel, visor, estados


def _raton(visor, tipo, p, boton, botones):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    p = QPointF(float(p[0]), float(p[1]))
    QApplication.sendEvent(visor, QMouseEvent(tipo, p, p, boton, botones, Qt.NoModifier))


def _arrastrar(visor, desde, hasta, pasos=6):
    from PySide6.QtCore import QEvent, Qt
    desde, hasta = np.asarray(desde, float), np.asarray(hasta, float)
    _raton(visor, QEvent.MouseButtonPress, desde, Qt.LeftButton, Qt.LeftButton)
    for k in range(1, pasos + 1):
        _raton(visor, QEvent.MouseMove, desde + (hasta - desde) * k / pasos, Qt.NoButton, Qt.LeftButton)
    _raton(visor, QEvent.MouseButtonRelease, hasta, Qt.LeftButton, Qt.NoButton)


def _manip(panel, ident):
    return next(m for m in panel.manipuladores.manips if m.ident == ident)


def _sobre_flecha(panel, ident):
    """(punto de pantalla en el medio de la flecha, dirección de la flecha en pantalla)."""
    gestor = panel.manipuladores
    a, b = _manip(panel, ident).puntos(gestor)
    s, ok = gestor.pantalla([a, b])
    assert ok.all()
    d = s[1] - s[0]
    return (s[0] + s[1]) / 2, d / np.linalg.norm(d)


def _cuerpo(estado):
    return next(iter(estado.cuerpos.values()))


# ---------------------------------------------------------------- Extruir: flecha + caja de valor
def test_arrastrar_la_flecha_de_extruir_cambia_la_distancia_y_la_previa(app_qt):
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, estados = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)]})
    assert [m.ident for m in panel.manipuladores.manips][:1] == ["flecha:distancia"]
    assert "manipuladores" in visor._capas
    medio, d = _sobre_flecha(panel, "flecha:distancia")
    from PySide6.QtCore import QEvent, Qt
    _raton(visor, QEvent.MouseMove, medio, Qt.NoButton, Qt.NoButton)        # al pasar el ratón se aclara
    assert panel.manipuladores._hover == ("flecha:distancia", "flecha")
    _arrastrar(visor, medio, medio + d * 120)
    nueva = panel.ctx.evaluar(panel.valores["distancia"])
    assert nueva > 12 and panel.widgets["distancia"].text() == panel.valores["distancia"]
    assert panel.valores["distancia"].endswith(" mm")
    panel._calcular_previa()
    forma = _cuerpo(estados[-1]).forma
    assert g.volumen(forma) == pytest.approx(200 * nueva, rel=1e-6)
    (_, _, z0), (_, _, z1) = g.caja_envolvente(forma)
    assert (z0, z1) == pytest.approx((0, nueva))
    # La flecha queda en la punta nueva (cola sobre la cara de arriba de la extrusión).
    cola, _ = _manip(panel, "flecha:distancia").puntos(panel.manipuladores)
    assert cola == pytest.approx((10, 5, nueva))
    panel.cancelar()


def test_la_flecha_permite_extruir_hacia_el_otro_lado(app_qt):
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, estados = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "distancia": "5 mm"})
    medio, d = _sobre_flecha(panel, "flecha:distancia")
    gestor = panel.manipuladores
    base = gestor.pantalla([[10, 5, 0]])[0][0]
    # se arrastra hasta pasar bien al otro lado del perfil
    _arrastrar(visor, medio, base - d * 3 * np.linalg.norm(medio - base))
    valor = panel.ctx.evaluar(panel.valores["distancia"])
    assert valor < 0
    panel._calcular_previa()
    (_, _, z0), (_, _, z1) = g.caja_envolvente(_cuerpo(estados[-1]).forma)
    assert (z0, z1) == pytest.approx((valor, 0))
    panel.cancelar()


def test_la_caja_de_valor_edita_el_campo_y_lo_sigue(app_qt):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)]})
    caja = panel.manipuladores.cajas["distancia"]
    assert caja.parent() is visor and caja.text() == "10 mm" and not caja.isHidden()
    caja.setFocus()
    caja.selectAll()
    QTest.keyClicks(caja, "25 mm")
    QTest.keyClick(caja, Qt.Key_Return)
    assert panel.valores["distancia"] == "25 mm" and panel.widgets["distancia"].text() == "25 mm"
    visor.setFocus()                                   # el campo del panel manda sobre la caja
    panel.set_valor("distancia", "12 mm")
    assert caja.text() == "12 mm"
    # sigue a la flecha: al cambiar el valor la caja se corre…
    from PySide6.QtWidgets import QApplication
    visor.distancia *= 4
    panel.manipuladores.redibujar()
    pos = caja.pos()
    panel.set_valor("distancia", "40 mm")
    assert caja.pos().y() < pos.y()
    # …y al mover la cámara (la vista avisa con camara_cambiada en cada cuadro)
    pos = caja.pos()
    visor.desplazar(120, 0)
    visor.camara_cambiada.emit()
    QApplication.processEvents()
    assert caja.pos().x() > pos.x()
    # una expresión inválida no se aplica
    caja.setText("xx +")
    assert panel.manipuladores.aplicar_caja(caja) is False and panel.valores["distancia"] == "40 mm"
    panel.cancelar()


def test_extruir_dos_lados_y_conicidad(app_qt):
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "direccion": "dos_lados"})
    idents = [m.ident for m in panel.manipuladores.manips]
    assert idents == ["flecha:distancia", "flecha:distancia2", "angulo:conicidad"]
    assert set(panel.manipuladores.cajas) == {"distancia", "distancia2"}
    gestor = panel.manipuladores
    angulo = _manip(panel, "angulo:conicidad")
    asa, ok = gestor.pantalla([angulo.asa(gestor)])
    assert ok.all()
    # arrastrar el asa de la conicidad hacia afuera (lado +X del perfil) abre el ángulo
    centro = gestor.pantalla([angulo.centro])[0][0]
    afuera = gestor.pantalla([angulo.centro + angulo.v * 30])[0][0]
    _arrastrar(visor, asa[0], asa[0] + (afuera - centro) * 0.5)
    conicidad = panel.ctx.evaluar(panel.valores["conicidad"], "angulo")
    assert 0 < conicidad < 89 and panel.valores["conicidad"].endswith(" deg")
    panel.cancelar()


# ---------------------------------------------------------------- cierre
@pytest.mark.parametrize("cerrar", ["cancelar", "aceptar"])
def test_al_cerrar_el_panel_no_quedan_capas_ni_cajas(app_qt, cerrar):
    from omnicad.ui.comandos.solido import Extruir
    from omnicad.ui.manipuladores import CajaValor
    doc = _doc_rectangulo()
    ventana = _Ventana()
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)]}, ventana)
    panel._calcular_previa()
    assert visor.findChildren(CajaValor)
    getattr(panel, cerrar)()
    assert not [k for k in visor._capas if k in ("manipuladores", "previa_comando", "seleccion")]
    assert not visor.findChildren(CajaValor)
    assert ventana.textos[-1] == ""
    # el visor ya no tiene el filtro: un arrastre después de cerrar no cambia nada
    assert panel.manipuladores.eventFilter(visor, None) is False


def test_medidas_de_lo_elegido_abajo_a_la_derecha(app_qt):
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    ventana = _Ventana()
    panel, _, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)]}, ventana)
    assert ventana.textos[-1] == "1 Perfil | Área: 200.000 mm^2"
    panel.set_valor("perfiles", [])
    assert ventana.textos[-1] == ""
    panel.cancelar()


def test_comando_sin_manipuladores_queda_como_antes(app_qt):
    from omnicad.ui.comandos.modificar import Combinar
    doc = _doc_caja()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="5", largo="5", alto="5", x="30"))
    panel, visor, _ = _panel(Combinar(), doc, {})
    assert panel.manipuladores is None and "manipuladores" not in visor._capas
    panel.cancelar()


# ---------------------------------------------------------------- Mover/copiar: tríada
def _hit_cuerpo(doc):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)


def test_la_triada_mueve_un_cuerpo(app_qt):
    from omnicad.ui.comandos.modificar import MoverCopiar
    doc = _doc_caja()
    panel, visor, estados = _panel(MoverCopiar(), doc, {"cuerpos": [_hit_cuerpo(doc)]})
    triada = _manip(panel, "triada")
    assert triada.centro == pytest.approx((10, 10, 10))           # pivote: centro del cuerpo
    gestor = panel.manipuladores
    k = gestor.escala(triada.centro)
    # flecha X: se arrastra a lo largo de su dirección en pantalla
    a, b = gestor.pantalla([triada.centro + [60 * k, 0, 0], triada.centro + [90 * k, 0, 0]])[0]
    d = (b - a) / np.linalg.norm(b - a)
    _arrastrar(visor, a, a + d * 80)
    dx = panel.ctx.evaluar(panel.valores["dx"])
    assert dx > 5 and panel.valores["dy"] == "0 mm" and panel.valores["dz"] == "0 mm"
    panel._calcular_previa()
    (x0, y0, z0), (x1, _, _) = g.caja_envolvente(_cuerpo(estados[-1]).forma)
    assert (x0, x1, y0, z0) == pytest.approx((dx, 20 + dx, 0, 0), abs=1e-6)
    # la tríada acompaña al cuerpo
    assert _manip(panel, "triada").centro == pytest.approx((10 + dx, 10, 10))
    # arco de giro alrededor de Z: cambia rz
    triada = _manip(panel, "triada")
    arco = dict(triada._partes(gestor)[0])[("giro", 2)]
    s, _ = gestor.pantalla(arco)
    medio = s[len(s) // 2]
    tangente = s[len(s) // 2 + 1] - s[len(s) // 2 - 1]
    _arrastrar(visor, medio, medio + tangente / np.linalg.norm(tangente) * 40)
    assert abs(panel.ctx.evaluar(panel.valores["rz"], "angulo")) > 1
    # cuadradito del plano XY: mueve X e Y a la vez, Z queda
    triada = _manip(panel, "triada")
    cuadro = dict(triada._partes(gestor)[0])[("plano", 2)]
    s, _ = gestor.pantalla(cuadro[:4])
    dx_antes = panel.valores["dx"]
    _arrastrar(visor, s.mean(axis=0), s.mean(axis=0) + (30, 25))
    assert panel.valores["dx"] != dx_antes and panel.valores["dy"] != "0 mm" and panel.valores["dz"] == "0 mm"
    panel.cancelar()
    assert "manipuladores" not in visor._capas


def test_mover_trasladar_con_direccion_y_girar(app_qt):
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos.modificar import MoverCopiar
    doc = _doc_caja()
    eje_z = hit_desde_ref({"tipo": "eje", "id": "Z"}, doc.estado_final)
    panel, visor, _ = _panel(MoverCopiar(), doc, {"cuerpos": [_hit_cuerpo(doc)], "tipo": "traslacion",
                                                  "direccion": [eje_z]})
    assert [m.ident for m in panel.manipuladores.manips] == ["flecha:distancia"]
    panel.set_valor("tipo", "rotacion")
    panel.set_valor("eje", [eje_z])
    angulo = _manip(panel, "angulo:angulo")
    assert angulo.radio == pytest.approx(np.hypot(10, 10))
    panel.cancelar()


# ---------------------------------------------------------------- resto de los comandos
def _arista_de_arriba(doc):
    from omnicad.nucleo import referencias as refs
    from omnicad.ui.comando import hit_desde_ref
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    arista = next(e for e in refs.subformas(forma, "arista") if np.allclose(refs.firma_arista(e)["medio"], (10, 0, 20)))
    return hit_desde_ref(refs.referencia("op1.c1", arista, caja=g.caja_envolvente(forma)), doc.estado_final)


def _cara_de_arriba(doc):
    from omnicad.nucleo import referencias as refs
    from omnicad.ui.comando import hit_desde_ref
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    cara = next(c for c in refs.subformas(forma, "cara") if np.allclose(g.centro_masa(c, True), (10, 10, 20)))
    return hit_desde_ref(refs.referencia("op1.c1", cara, caja=g.caja_envolvente(forma)), doc.estado_final)


def test_flecha_del_empalme_sobre_la_arista(app_qt):
    from omnicad.ui.comandos.modificar import Empalme
    doc = _doc_caja()
    panel, visor, estados = _panel(Empalme(), doc, {"aristas": [_arista_de_arriba(doc)], "radio": "2 mm"})
    flecha = _manip(panel, "flecha:radio")
    assert flecha.origen == pytest.approx((10, 0, 20))
    assert flecha.direccion == pytest.approx((0, np.sqrt(0.5), -np.sqrt(0.5)))     # hacia adentro del material
    medio, d = _sobre_flecha(panel, "flecha:radio")
    _arrastrar(visor, medio, medio + d * 40)
    assert panel.ctx.evaluar(panel.valores["radio"]) > 2
    panel._calcular_previa()
    assert g.volumen(_cuerpo(estados[-1]).forma) < 8000
    panel.cancelar()


def test_manipuladores_de_chaflan_vaciado_pulsar_y_plano(app_qt):
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos.construir import CATALOGO_LOCAL
    from omnicad.ui.comandos.modificar import Chaflan, PulsarTirar, Vaciado
    doc = _doc_caja()
    casos = [
        (Chaflan(), {"aristas": [_arista_de_arriba(doc)]}, ["flecha:distancia"]),
        (Vaciado(), {"caras": [_cara_de_arriba(doc)]}, ["flecha:espesor_interior"]),
        (Vaciado(), {"caras": [_cara_de_arriba(doc)], "direccion": "ambos"},
         ["flecha:espesor_interior", "flecha:espesor_exterior"]),
        (PulsarTirar(), {"objetos": [_cara_de_arriba(doc)]}, ["flecha:distancia"]),
        (PulsarTirar(), {"objetos": [_arista_de_arriba(doc)]}, ["flecha:distancia"]),
        (CATALOGO_LOCAL["plano_desfase"](), {"r0": [hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)]},
         ["flecha:distancia"]),
    ]
    for comando, valores, esperado in casos:
        panel, visor, _ = _panel(comando, doc, valores)
        assert [m.ident for m in panel.manipuladores.manips] == esperado, comando.CLAVE
        panel.cancelar()
    # Pulsar/tirar sobre la cara de arriba: la flecha sale por la normal (+Z) y tirar agrega material
    panel, visor, estados = _panel(PulsarTirar(), doc, {"objetos": [_cara_de_arriba(doc)]})
    flecha = _manip(panel, "flecha:distancia")
    assert flecha.direccion == pytest.approx((0, 0, 1))
    medio, d = _sobre_flecha(panel, "flecha:distancia")
    _arrastrar(visor, medio, medio + d * 60)
    panel._calcular_previa()
    assert g.volumen(_cuerpo(estados[-1]).forma) > 8000 + 400
    panel.cancelar()


def test_agujero_con_flecha_de_profundidad_y_previa_roja(app_qt):
    from omnicad.ui.comandos.crear import Agujero
    from omnicad.ui.manipuladores import ROJO_PREVIA
    doc = _doc_caja()
    cara = _cara_de_arriba(doc)
    cara["punto"] = np.array([10.0, 10.0, 20.0])
    panel, visor, estados = _panel(Agujero(), doc, {"colocacion": [cara], "profundidad": "8 mm"})
    flecha = _manip(panel, "flecha:profundidad")
    assert flecha.origen == pytest.approx((10, 10, 20)) and flecha.direccion == pytest.approx((0, 0, -1))
    panel._calcular_previa()
    previa = visor._capas.get("previa_comando")
    assert previa and previa[0][2] == ROJO_PREVIA and len(previa[0][1]) > 0
    medio, d = _sobre_flecha(panel, "flecha:profundidad")
    _arrastrar(visor, medio, medio + d * 30)
    assert panel.ctx.evaluar(panel.valores["profundidad"]) > 8
    panel.cancelar()
    assert "previa_comando" not in visor._capas


def test_agujero_se_mueve_arrastrando_su_aro_por_la_cara(app_qt):
    """El agujero puesto con un clic sobre una cara se puede correr con el ratón (antes quedaba donde se hizo clic)."""
    from omnicad.ui.comandos.crear import Agujero
    doc = _doc_caja()
    cara = _cara_de_arriba(doc)
    cara["punto"] = np.array([10.0, 10.0, 20.0])
    panel, visor, estados = _panel(Agujero(), doc, {"colocacion": [cara], "profundidad": "8 mm"})
    asa = _manip(panel, "posicion:agujero0")
    gestor = panel.manipuladores
    ini = gestor.pantalla([asa.punto])[0][0]
    destino = gestor.pantalla([asa.punto + np.array([5.0, 0.0, 0.0])])[0][0]
    _arrastrar(visor, ini, destino)
    nuevo = np.asarray(panel.valores["colocacion"][0]["punto"], float)
    assert nuevo[0] == pytest.approx(15.0, abs=0.6) and nuevo[1] == pytest.approx(10.0, abs=0.6)
    assert nuevo[2] == pytest.approx(20.0, abs=1e-6)               # sigue sobre la cara
    panel._calcular_previa()
    assert estados and g.es_valida(_cuerpo(estados[-1]).forma)
    panel.cancelar()


def test_dibujo_insertado_se_corre_arrastrando_su_aro(app_qt):
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos.insertar import InsertarSVG
    doc = _doc_rectangulo()
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    panel, visor, _estados = _panel(InsertarSVG(), doc, {"plano": [plano], "dx": "0 mm", "dy": "0 mm"})
    manips = [m for m in panel.manipuladores.manips if m.ident == "posicion:desplazamiento"]
    if not manips:                                  # el hit de un plano de origen no trae su marco: sin aro
        pytest.skip("el hit del plano no trae geometría")
    gestor = panel.manipuladores
    asa = manips[0]
    ini = gestor.pantalla([asa.punto])[0][0]
    destino = gestor.pantalla([asa.punto + np.array([8.0, 0.0, 0.0])])[0][0]
    _arrastrar(visor, ini, destino)
    assert panel.ctx.evaluar(panel.valores["dx"]) == pytest.approx(8.0, abs=0.7)
    panel.cancelar()


def test_agujero_diametro_con_asa_en_el_borde(app_qt):
    """Como Fusion: se tira del borde del agujero y el diámetro cambia (con su caja de valor)."""
    from omnicad.ui.comandos.crear import Agujero
    doc = _doc_caja()
    cara = _cara_de_arriba(doc)
    cara["punto"] = np.array([10.0, 10.0, 20.0])
    panel, visor, _estados = _panel(Agujero(), doc, {"colocacion": [cara], "diametro": "6 mm"})
    asa = _manip(panel, "flecha:diametro")
    assert asa.origen == pytest.approx((10, 10, 20)) and abs(asa.direccion[2]) < 1e-9     # radial, sobre la cara
    gestor = panel.manipuladores
    base = gestor.pantalla([asa.puntos(gestor)[0]])[0][0]
    hacia = gestor.pantalla([asa.puntos(gestor)[0] + asa.direccion * 5.0])[0][0] - base
    _arrastrar(visor, base, base + hacia / np.linalg.norm(hacia) * 25)
    assert panel.ctx.evaluar(panel.valores["diametro"]) != pytest.approx(6.0)
    assert "diametro" in panel.manipuladores.cajas
    panel.cancelar()


def test_puntos_de_enganche_de_una_cara(app_qt):
    from omnicad.ui import manipuladores as mp
    doc = _doc_caja()
    from omnicad.ui.manipuladores import entidad
    cara = entidad(_cara_de_arriba(doc), doc.estado_final).forma
    pts = mp.puntos_enganche_cara(cara)
    tipos = sorted(t for _p, t in pts)
    assert tipos == ["centro"] + ["medio"] * 4 + ["vertice"] * 4
    centro = next(p for p, t in pts if t == "centro")
    assert centro == pytest.approx((10, 10, 20))


def test_agujero_se_engancha_al_centro_de_la_cara_al_arrastrar(app_qt):
    """Fusion marca el centro de la superficie y el agujero se engancha ahí al acercarse."""
    from omnicad.ui.comandos.crear import Agujero
    doc = _doc_caja()
    cara = _cara_de_arriba(doc)
    cara["punto"] = np.array([4.0, 4.0, 20.0])
    panel, visor, _estados = _panel(Agujero(), doc, {"colocacion": [cara], "profundidad": "8 mm"})
    asa = _manip(panel, "posicion:agujero0")
    assert len(asa.candidatos) == 9
    gestor = panel.manipuladores
    ini = gestor.pantalla([asa.punto])[0][0]
    cerca = gestor.pantalla([np.array([10.0, 10.0, 20.0])])[0][0] + np.array([4.0, 3.0])    # a 5 px del centro
    _arrastrar(visor, ini, cerca)
    nuevo = np.asarray(panel.valores["colocacion"][0]["punto"], float)
    assert nuevo == pytest.approx((10.0, 10.0, 20.0), abs=1e-6)             # enganchado exacto
    # el centro marcado en azul
    assert _manip(panel, "posicion:agujero0")._enganchado() is not None
    panel.cancelar()


def test_clic_sobre_la_cara_engancha_al_centro(app_qt):
    from omnicad.ui.comandos.crear import Agujero
    doc = _doc_caja()
    cara = _cara_de_arriba(doc)
    panel, visor, _estados = _panel(Agujero(), doc, {})
    centro = np.array([10.0, 10.0, 20.0])
    px = visor.puntos_pantalla(np.array([centro]))[0][0] + np.array([5.0, 4.0])
    # un clic a 6 px del centro: el visor da el punto 3D de la cara bajo ese píxel
    o, r = visor.rayo(type("P", (), {"x": lambda s: px[0], "y": lambda s: px[1]})())
    t = (20.0 - o[2]) / r[2]
    cara["punto"] = np.asarray(o, float) + np.asarray(r, float) * t
    assert np.linalg.norm(cara["punto"] - centro) > 0.05
    panel.show()
    panel._activar(panel.campos[0])
    panel._elegida(cara)
    punto = np.asarray(panel.valores["colocacion"][0]["punto"], float)
    assert punto == pytest.approx(centro, abs=1e-6)
    panel.cancelar()


def test_asas_en_la_vista_de_otros_comandos(app_qt):
    """Flechas, arcos, aros y tríada en comandos que antes solo tenían campos de texto."""
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    doc = _doc_caja()
    cara = _cara_de_arriba(doc)
    cuerpo = hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)
    eje_x = hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)
    eje_z = hit_desde_ref({"tipo": "eje", "id": "Z"}, doc.estado_final)

    def idents(clave, valores, d=doc):
        panel, _visor, _e = _panel(CATALOGO[clave](), d, valores)
        res = [m.ident for m in panel.manipuladores.manips]
        panel.cancelar()
        return res

    assert "flecha:espesor" in idents("engrosar", {"caras": [cara]})
    assert "flecha:distancia" in idents("sup_desfase", {"caras": [cara]})
    assert "flecha:d1" in idents("patron_rectangular_3d", {"cuerpos": [cuerpo], "dir1": [eje_x]})
    assert "angulo:angulo" in idents("patron_circular_3d", {"cuerpos": [cuerpo], "eje": [eje_z]})
    assert "triada" in idents("scu", {})
    assert "flecha:diametro" in idents("bobina", {})
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    assert "posicion:desplazamiento" in idents("lienzo", {"plano": [plano]})
    # «Unión construida» no tiene desfases: sin tríada
    assert idents("union_construida", {}) == []


def test_asa_de_extruir_superficie(app_qt):
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    doc = _doc_rectangulo()
    curva = next(iter(doc.estado_final.bocetos["op1"].boceto.curvas))
    hit = hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": curva}, doc.estado_final)
    panel, _visor, _e = _panel(CATALOGO["sup_extruir"](), doc, {"curvas": [hit]})
    assert "flecha:distancia" in [m.ident for m in panel.manipuladores.manips]
    panel.cancelar()


def test_asas_en_la_vista_lote_2(app_qt):
    """Nervio, Red, Repujado, Rosca, Tubería, Dobladillo, Extender, Reglada, Empalme de superficie, Plegar,
    Plano en ángulo, Desmoldeo y Patrón en trayectoria ya tienen su asa."""
    from omnicad.nucleo import referencias as refs
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO

    # caja + un boceto con un rectángulo sobre el plano XY
    doc = _doc_caja()
    b = Boceto()
    b.agregar_rectangulo((2, 2), (8, 6))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto2", plano="XY", boceto=b))
    est = doc.estado_final
    boc = est.bocetos["op2"]
    curva = next(iter(boc.boceto.curvas))
    h_curva = hit_desde_ref({"tipo": "curva_boceto", "boceto": "op2", "curva": curva}, est)
    h_perfil = hit_desde_ref({"tipo": "perfil", "boceto": "op2", **OpExtrusion.referencia_perfil(boc.perfiles[0])}, est)
    cuerpo = hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, est)
    cara_sup = _cara_de_arriba(doc)
    arista = _arista_de_arriba(doc)
    forma = est.cuerpos["op1.c1"].forma
    lateral = next(c for c in refs.subformas(forma, "cara") if np.allclose(g.centro_masa(c, True), (0, 10, 10)))
    h_lateral = hit_desde_ref(refs.referencia("op1.c1", lateral, caja=g.caja_envolvente(forma)), est)
    plano_xy = hit_desde_ref({"tipo": "plano", "id": "XY"}, est)
    eje_x = hit_desde_ref({"tipo": "eje", "id": "X"}, est)
    eje_z = hit_desde_ref({"tipo": "eje", "id": "Z"}, est)

    def idents(clave, valores, d=doc):
        panel, _visor, _e = _panel(CATALOGO[clave](), d, valores)
        res = [m.ident for m in panel.manipuladores.manips]
        panel.cancelar()
        return res

    assert "flecha:espesor" in idents("nervio", {"curvas": [h_curva]})
    assert "flecha:profundidad" in idents("red", {"curvas": [h_curva], "extension": "profundidad"})
    assert "flecha:profundidad" in idents("repujado", {"perfiles": [h_perfil], "cara": [cara_sup]})
    assert "flecha:tamano" in idents("tuberia", {"ruta": [h_curva]})
    assert "flecha:longitud" in idents("dobladillo", {"aristas": [arista]})
    assert "flecha:distancia" in idents("extender_sup", {"aristas": [arista]})
    assert "flecha:distancia" in idents("reglada", {"aristas": [arista], "direccion": [eje_z]})
    assert "flecha:medida" in idents("sup_empalme", {"aristas": [arista]})
    assert "angulo:angulo" in idents("plegar", {"cara": [cara_sup], "lineas": [h_curva]})
    assert "angulo:angulo" in idents("plano_angulo", {"r0": [eje_x]})
    assert "angulo:angulo" in idents("desmoldeo", {"plano": [plano_xy], "caras": [h_lateral]})
    assert "flecha:d1" in idents("patron_ruta", {"cuerpos": [cuerpo], "ruta": [h_curva]})

    # rosca: cilindro, sin «longitud completa»
    dc = Documento()
    dc.agregar(OpPrimitiva(dc.nuevo_id(), forma="cilindro", radio="5", alto="20"))
    cil = dc.estado_final.cuerpos["op1.c1"].forma
    lateral_c = next(c for c in refs.subformas(cil, "cara") if refs.firma_cara(c).get("geom") == "cilindro")
    h_cil = hit_desde_ref(refs.referencia("op1.c1", lateral_c, caja=g.caja_envolvente(cil)), dc.estado_final)
    res = idents("rosca", {"caras": [h_cil], "largo_completo": False}, d=dc)
    assert "flecha:longitud" in res and "flecha:desfase" in res


def test_el_agujero_no_sale_de_la_cara(app_qt):
    from omnicad.ui.comandos.crear import Agujero
    doc = _doc_caja()
    cara = _cara_de_arriba(doc)
    cara["punto"] = np.array([10.0, 10.0, 20.0])
    panel, visor, _e = _panel(Agujero(), doc, {"colocacion": [cara], "profundidad": "8 mm"})
    asa = _manip(panel, "posicion:agujero0")
    gestor = panel.manipuladores
    ini = gestor.pantalla([asa.punto])[0][0]
    afuera = gestor.pantalla([np.array([60.0, 10.0, 20.0])])[0][0]          # 40 mm fuera del borde de la cara
    _arrastrar(visor, ini, afuera)
    nuevo = np.asarray(panel.valores["colocacion"][0]["punto"], float)
    assert 0.0 <= nuevo[0] <= 20.0 and 0.0 <= nuevo[1] <= 20.0
    panel.cancelar()


def test_angulo_de_la_revolucion(app_qt):
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos.solido import Revolucion
    doc = Documento()
    b = Boceto()
    b.agregar_rectangulo((5, 0), (10, 10))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano="XZ", boceto=b))
    eje = hit_desde_ref({"tipo": "eje", "id": "Z"}, doc.estado_final)
    panel, visor, estados = _panel(Revolucion(), doc, {"perfiles": [_perfil(doc)], "eje": [eje], "angulo": "90 deg"})
    angulo = _manip(panel, "angulo:angulo")
    assert angulo.radio == pytest.approx(7.5) and angulo.eje == pytest.approx((0, 0, 1))
    gestor = panel.manipuladores
    asa = gestor.pantalla([angulo.asa(gestor)])[0][0]
    # el asa está a 90° del perfil: arrastrarla un poco más allá agranda el ángulo
    mas = gestor.pantalla([angulo.centro + (angulo.u * np.cos(2.0) + angulo.v * np.sin(2.0)) * 7.5])[0][0]
    _arrastrar(visor, asa, mas)
    valor = panel.ctx.evaluar(panel.valores["angulo"], "angulo")
    assert 100 < valor < 130
    panel._calcular_previa()
    assert g.volumen(_cuerpo(estados[-1]).forma) > 0
    panel.cancelar()
