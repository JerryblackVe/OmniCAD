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
    assert panel.valores["distancia"] == "0 mm"
    assert [m.ident for m in panel.manipuladores.manips][:1] == ["flecha:distancia"]
    assert "manipuladores" in visor._capas
    medio, d = _sobre_flecha(panel, "flecha:distancia")
    from PySide6.QtCore import QEvent, Qt
    _raton(visor, QEvent.MouseMove, medio, Qt.NoButton, Qt.NoButton)        # al pasar el ratón se aclara
    assert panel.manipuladores._hover == ("flecha:distancia", "flecha")
    _arrastrar(visor, medio, medio + d * 120)
    nueva = panel.ctx.evaluar(panel.valores["distancia"])
    assert nueva > 2 and panel.widgets["distancia"].text() == panel.valores["distancia"]
    assert panel.valores["distancia"].endswith(" mm")
    panel._calcular_previa()
    forma = _cuerpo(estados[-1]).forma
    assert g.volumen(forma) == pytest.approx(200 * nueva, rel=1e-6)
    (_, _, z0), (_, _, z1) = g.caja_envolvente(forma)
    assert (z0, z1) == pytest.approx((0, nueva))
    # La flecha queda en la punta nueva (cola sobre la cara de arriba de la extrusión), en el borde del perfil (P-139).
    flecha = _manip(panel, "flecha:distancia")
    cola, _ = flecha.puntos(panel.manipuladores)
    assert cola == pytest.approx(flecha.origen + (0, 0, nueva)) and flecha.origen[:2] == pytest.approx((0, 0))
    panel.cancelar()


def test_la_flecha_permite_extruir_hacia_el_otro_lado(app_qt):
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, estados = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "distancia": "5 mm"})
    medio, d = _sobre_flecha(panel, "flecha:distancia")
    gestor = panel.manipuladores
    base = gestor.pantalla([_manip(panel, "flecha:distancia").origen])[0][0]
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
    assert caja.parent() is visor and caja.text() == "0 mm" and not caja.isHidden()
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
    assert idents == ["flecha:distancia", "flecha:distancia2", "angulo:conicidad", "angulo:conicidad2"]
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


@pytest.mark.parametrize("direccion, valor", [("dos_lados", "10 mm"), ("dos_lados", "-10 mm"), ("simetrica", "10 mm")])
def test_la_flecha_de_distancia_no_cruza_el_cero_ni_queda_en_cero(app_qt, direccion, valor):
    """B-205: en «Dos lados» el número es una magnitud de su lado; la flecha (también con el valor tecleado negativo)
    queda donde está el cuerpo, y arrastrarla hacia adentro se frena sin pasar al otro lado. B-267: se frena en el
    menor valor que se escribe, no en 0 (que es inválido y dejaba el error en el panel); igual en «Simétrica»."""
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "direccion": direccion,
                                              "distancia": valor, "distancia2": "5 mm"})
    gestor = panel.manipuladores
    if direccion == "dos_lados":
        base, punta = _manip(panel, "flecha:distancia").puntos(gestor)
        assert base[2] == pytest.approx(10) and punta[2] > base[2]      # sobre el perfil, apuntando hacia afuera
        assert _manip(panel, "angulo:conicidad").u[2] > 0             # el asa de la conicidad, del mismo lado
    medio, d = _sobre_flecha(panel, "flecha:distancia")
    _arrastrar(visor, medio, medio - d * 400)                          # muy hacia adentro: pasaría el cero
    final = panel.ctx.evaluar(panel.valores["distancia"])
    assert final * float(valor.split()[0]) > 0 and abs(final) < 10    # achicó, sin cambiar de signo ni llegar a 0
    panel._t_previa.stop()
    panel._calcular_previa()
    assert panel._previa_ok, panel.mensaje.text()
    panel.cancelar()


def test_asas_de_conicidad2_y_desfase_inicio_en_extruir(app_qt):
    """FU-4: asas para la conicidad del lado 2 (solo en «Dos lados») y para el desfase de inicio
    (solo con Inicio=Desfase), como las que ya existen."""
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "direccion": "dos_lados"})
    assert "angulo:conicidad2" in [m.ident for m in panel.manipuladores.manips]
    gestor = panel.manipuladores
    angulo2 = _manip(panel, "angulo:conicidad2")
    asa, ok = gestor.pantalla([angulo2.asa(gestor)])
    assert ok.all()
    centro = gestor.pantalla([angulo2.centro])[0][0]
    afuera = gestor.pantalla([angulo2.centro + angulo2.v * 30])[0][0]
    _arrastrar(visor, asa[0], asa[0] + (afuera - centro) * 0.5)
    conicidad2 = panel.ctx.evaluar(panel.valores["conicidad2"], "angulo")
    assert 0 < conicidad2 < 89 and panel.valores["conicidad2"].endswith(" deg")
    panel.cancelar()
    panel2, visor2, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "inicio": "desfase"})
    assert "flecha:desfase_inicio" in [m.ident for m in panel2.manipuladores.manips]
    medio, d = _sobre_flecha(panel2, "flecha:desfase_inicio")
    _arrastrar(visor2, medio, medio + d * 80)
    desfase = panel2.ctx.evaluar(panel2.valores["desfase_inicio"])
    assert desfase > 2 and panel2.valores["desfase_inicio"].endswith(" mm")
    panel2.cancelar()


# ---------------------------------------------------------------- cierre
@pytest.mark.parametrize("cerrar", ["cancelar", "aceptar"])
def test_al_cerrar_el_panel_no_quedan_capas_ni_cajas(app_qt, cerrar):
    from omnicad.ui.comandos.solido import Extruir
    from omnicad.ui.manipuladores import CajaValor
    doc = _doc_rectangulo()
    ventana = _Ventana()
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)]}, ventana)
    panel.set_valor("distancia", "10 mm")
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
    assert flecha.origen == pytest.approx((10, 0, 20))           # sin clic (al editar, la API): en el medio
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
    manips = [m for m in panel.manipuladores.manips if m.ident == "posicion:calcomania"]
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


def test_bobina_arrastrar_el_asa_cambia_el_diametro(app_qt):
    from omnicad.ui.comandos.crear import Bobina
    from omnicad.ui.manipuladores import AsaRadial
    panel, visor, _ = _panel(Bobina(), Documento(), {})
    gestor = panel.manipuladores
    asa = _manip(panel, "flecha:diametro")
    assert isinstance(asa, AsaRadial)
    assert asa.origen == pytest.approx((0, 0, 0))
    assert asa.direccion == pytest.approx((1, 0, 0))
    punto = asa.puntos(gestor)[0]
    assert punto == pytest.approx((10, 0, 0))
    desde, hasta = gestor.pantalla([punto, punto + asa.direccion * 5])[0]
    _arrastrar(visor, desde, hasta)
    assert panel.ctx.evaluar(panel.valores["diametro"]) == pytest.approx(30, abs=0.1)
    assert panel.widgets["diametro"].text() == panel.valores["diametro"]
    assert panel.valores["altura"] == "30 mm"
    panel.cancelar()


@pytest.mark.parametrize("tipo", ["rev_altura", "altura_paso"])
def test_bobina_arrastrar_la_flecha_cambia_la_altura(app_qt, tipo):
    from omnicad.ui.comandos.crear import Bobina
    panel, visor, _ = _panel(Bobina(), Documento(), {"tipo": tipo})
    flecha = _manip(panel, "flecha:altura")
    assert flecha.origen == pytest.approx((0, 0, 0))
    assert flecha.direccion == pytest.approx((0, 0, 1))
    medio, d = _sobre_flecha(panel, "flecha:altura")
    _arrastrar(visor, medio, medio + d * 40)
    assert panel.ctx.evaluar(panel.valores["altura"]) > 30
    assert panel.widgets["altura"].text() == panel.valores["altura"]
    assert panel.valores["diametro"] == "20 mm"
    for sin_altura in ("espiral", "rev_paso"):
        panel.set_valor("tipo", sin_altura)
        assert [m.ident for m in panel.manipuladores.manips] == ["flecha:diametro"]
        assert set(panel.manipuladores.cajas) == {"diametro"}
    panel.cancelar()


@pytest.mark.parametrize("cara", [False, True])
def test_bobina_asas_respetan_el_plano_y_el_centro_elegidos(app_qt, cara):
    from omnicad.nucleo import referencias as refs
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos.crear import Bobina
    doc = _doc_caja()
    plano = _cara_de_arriba(doc) if cara else hit_desde_ref({"tipo": "plano", "id": "YZ"}, doc.estado_final)
    panel, _, _ = _panel(Bobina(), doc, {"plano": [plano]})
    marco = plano["plano"]
    assert _manip(panel, "flecha:diametro").origen == pytest.approx(marco.origen)
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    vertice = next(v for v in refs.subformas(forma, "vertice") if np.allclose(refs.punto_de_vertice(v), (20, 20, 20)))
    centro = hit_desde_ref(refs.referencia("op1.c1", vertice, caja=g.caja_envolvente(forma)), doc.estado_final)
    panel.set_valor("centro", [centro])
    asa, flecha = (_manip(panel, ident) for ident in ("flecha:diametro", "flecha:altura"))
    assert asa.origen == pytest.approx((20, 20, 20))
    assert flecha.origen == pytest.approx((20, 20, 20))
    assert asa.direccion == pytest.approx(marco.u)
    assert flecha.direccion == pytest.approx(marco.normal)
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
    panel._activar(next(c for c in panel.campos if c.clave == "colocacion"))
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
    assert "angulo:angulo" in idents("patron_circular_3d", {"cuerpos": [cuerpo], "eje": [eje_z], "modo": "parcial"})
    assert "angulo:angulo" not in idents("patron_circular_3d", {"cuerpos": [cuerpo], "eje": [eje_z]})   # completo: 360°
    assert idents("scu", {}) == []                 # como en Fusion: primero se elige el punto (Forzar)
    assert "triada" in idents("scu", {"origen": [hit_desde_ref({"tipo": "punto", "id": "O"}, doc.estado_final)]})
    assert "flecha:diametro" in idents("bobina", {})
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    assert "posicion:calcomania" in idents("lienzo", {"plano": [plano]})
    # «Unión construida» no tiene desfases: sin tríada
    assert idents("union_construida", {}) == []


def test_asa_de_extruir_superficie(app_qt):
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    doc = _doc_rectangulo()
    curva = next(iter(doc.estado_final.bocetos["op1"].boceto.curvas))
    hit = hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": curva}, doc.estado_final)
    panel, _visor, _e = _panel(CATALOGO["sup_extruir"](), doc, {"curvas": [hit]})
    assert {"flecha:distancia", "angulo:conicidad"} <= {m.ident for m in panel.manipuladores.manips}
    panel.cancelar()


def test_asas_de_extruir_superficie_con_la_arista_de_un_cuerpo(app_qt):
    """Con aristas de un cuerpo (sin plano de boceto) también salen las asas, y con dirección elegida."""
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    doc = _doc_caja()
    arista = _arista_de_arriba(doc)
    eje_x = hit_desde_ref({"tipo": "eje", "id": "X"}, doc.estado_final)
    for valores in ({"curvas": [arista]}, {"curvas": [arista], "direccion": [eje_x]}):
        panel, _visor, _e = _panel(CATALOGO["sup_extruir"](), doc, valores)
        assert {"flecha:distancia", "angulo:conicidad"} <= {m.ident for m in panel.manipuladores.manips}
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
    assert "recorrido:rd" in idents("patron_ruta", {"cuerpos": [cuerpo], "ruta": [h_curva]})

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
    gestor = panel.manipuladores
    # P-139: el anillo de Fusion, en el borde del perfil más lejano al eje y a la altura de su centro
    assert angulo.centro == pytest.approx((10, 0, 5)) and angulo.eje == pytest.approx((0, 0, 1))
    asa = gestor.pantalla([angulo.asa(gestor)])[0][0]
    # el asa está a 90° del perfil: arrastrarla un poco más allá agranda el ángulo
    mas = gestor.pantalla([angulo.centro + (angulo.u * np.cos(2.0) + angulo.v * np.sin(2.0)) * angulo._r(gestor)])[0][0]
    _arrastrar(visor, asa, mas)
    valor = panel.ctx.evaluar(panel.valores["angulo"], "angulo")
    assert 100 < valor < 130
    panel._calcular_previa()
    assert g.volumen(_cuerpo(estados[-1]).forma) > 0
    panel.cancelar()


def test_dos_lados_de_la_revolucion_cada_asa_es_la_magnitud_de_su_lado(app_qt):
    """B-210: en «Dos lados» cada ángulo vale por su magnitud (el lado lo elige la dirección), como en el núcleo y
    en la superficie: -45 deg da el mismo cuerpo que 45 deg y el asa no se puede bajar de 0."""
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos.solido import Revolucion

    def panel_dos(valor2):
        doc = Documento()
        b = Boceto()
        b.agregar_rectangulo((5, 0), (10, 10))
        doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano="XZ", boceto=b))
        eje = hit_desde_ref({"tipo": "eje", "id": "Z"}, doc.estado_final)
        return _panel(Revolucion(), doc, {"perfiles": [_perfil(doc)], "eje": [eje], "angulo": "90 deg",
                                         "direccion": "dos_lados", "angulo2": valor2})

    panel, visor, estados = panel_dos("45 deg")
    assert _manip(panel, "angulo:angulo").minimo == 0.0 and _manip(panel, "angulo:angulo2").minimo == 0.0
    panel._calcular_previa()
    v_pos = g.volumen(_cuerpo(estados[-1]).forma)
    panel.cancelar()
    panel2, _, estados2 = panel_dos("-45 deg")
    panel2._calcular_previa()
    assert g.volumen(_cuerpo(estados2[-1]).forma) == pytest.approx(v_pos, rel=1e-6)
    panel2.cancelar()


def test_el_asa_de_profundidad_del_repujado_pasa_por_debajo_de_cero(app_qt):
    """H-99: el asa de Profundidad se puede arrastrar por debajo de 0 (sin tope) y la cola queda del lado que ocupa
    el material: arriba en el relieve, hundida en el grabado, tanto con el signo como con «Grabado» elegido a mano."""
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos.crear import Repujado

    doc = _doc_caja()
    b = Boceto()
    b.agregar_rectangulo((5, 5), (15, 15))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto2", plano="XY", boceto=b))
    est = doc.estado_final
    perfil = est.bocetos["op2"].perfiles[0]
    h_perfil = hit_desde_ref({"tipo": "perfil", "boceto": "op2", **OpExtrusion.referencia_perfil(perfil)}, est)

    def asa(profundidad, tipo):
        panel, _visor, _e = _panel(Repujado(), doc, {"perfiles": [h_perfil], "caras": [_cara_de_arriba(doc)],
                                                    "profundidad": profundidad, "tipo": tipo})
        m = _manip(panel, "flecha:profundidad")
        z = m.puntos(panel.manipuladores)[0][2]          # la cola: 20 + profundidad con su signo
        panel.cancelar()
        return m, z

    m, z = asa("1 mm", "relieve")
    assert m.minimo is None and z == pytest.approx(21)
    assert asa("-1 mm", "grabado")[1] == pytest.approx(19)
    assert asa("1 mm", "grabado")[1] == pytest.approx(19)
    assert asa("-1 mm", "relieve")[1] == pytest.approx(19)


def test_repujado_tiene_asas_de_desfase_y_giro(app_qt):
    """P-142: como Emboss de Fusion, Desfase horizontal, Desfase vertical y Ángulo de giro tienen asa en la vista; la de
    Profundidad y la del giro siguen al texto corrido. Arrastrar la flecha horizontal cambia el valor del campo."""
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos.crear import Repujado

    doc = _doc_caja()
    b = Boceto()
    b.agregar_rectangulo((5, 5), (15, 15))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto2", plano="XY", boceto=b))
    est = doc.estado_final
    perfil = est.bocetos["op2"].perfiles[0]
    h_perfil = hit_desde_ref({"tipo": "perfil", "boceto": "op2", **OpExtrusion.referencia_perfil(perfil)}, est)
    panel, visor, _e = _panel(Repujado(), doc, {"perfiles": [h_perfil], "caras": [_cara_de_arriba(doc)],
                                                "desfase_h": "3 mm", "desfase_v": "2 mm", "giro": "30 deg"})
    assert {"flecha:desfase_h", "flecha:desfase_v", "angulo:giro"} <= {m.ident for m in panel.manipuladores.manips}
    assert _manip(panel, "flecha:profundidad").puntos(panel.manipuladores)[0] == pytest.approx((13, 12, 21))
    assert _manip(panel, "angulo:giro").centro == pytest.approx((13, 12, 20))
    assert _manip(panel, "flecha:desfase_h").puntos(panel.manipuladores)[0] == pytest.approx((13, 10, 20))
    medio, d = _sobre_flecha(panel, "flecha:desfase_h")
    _arrastrar(visor, medio, medio + d * 40)
    assert panel.ctx.evaluar(panel.valores["desfase_h"]) > 3
    panel.cancelar()


# ---------------------------------------------------------------- H-60: asas bien definidas y sin nada encima
def _camara(visor, atras):
    """Cámara que mira hacia -atras (R: derecha, arriba, atrás) y encuadra."""
    from omnicad.ui import manipuladores as mp
    atras = mp.unitario(atras)
    ref = np.array([0.0, 0.0, 1.0]) if abs(atras[2]) < 0.95 else np.array([0.0, 1.0, 0.0])
    der = mp.unitario(np.cross(ref, atras))
    visor.R = np.array([der, np.cross(atras, der), atras])
    visor.encuadrar()


def _vistas(visor, d):
    """Las 4 vistas de la auditoría: de frente al eje `d`, de costado, iso y de costado por el otro lado."""
    from omnicad.ui import manipuladores as mp
    lado = mp.perpendiculares(d)
    return {"frente": lambda: _camara(visor, d), "costado": lambda: _camara(visor, lado[0]),
            "iso": lambda: (visor.vista("iso"), visor.encuadrar()), "otro lado": lambda: _camara(visor, lado[1])}


def _huella_pantalla(gestor):
    gestor.redibujar()
    return gestor.huella_pantalla()


def _sin_nada_encima(gestor):
    """Las cajas visibles no se pisan entre sí ni tapan ningún trazo de las asas."""
    from omnicad.ui import manipuladores as mp
    rects = list(gestor.rectangulos_cajas().values())
    assert not any(a.intersects(b) for i, a in enumerate(rects) for b in rects[i + 1:])
    huella = gestor.huella_pantalla()
    assert all(mp._choques(r, huella) == 0 for r in rects)
    return len(rects)


def test_la_flecha_que_apunta_a_la_camara_sigue_viendose_y_se_arrastra(app_qt):
    from omnicad.ui import manipuladores as mp
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)]})
    gestor = panel.manipuladores
    flecha = _manip(panel, "flecha:distancia")
    _camara(visor, flecha.direccion)                            # la flecha apunta justo a los ojos
    gestor.redibujar()
    assert mp.fraccion_visible(visor, flecha.direccion) < 0.01
    a, b = flecha.puntos(gestor)
    s, ok = gestor.pantalla([a, b])
    assert ok.all() and np.linalg.norm(s[1] - s[0]) >= 0.45 * mp.LARGO_FLECHA      # antes: una mancha de ~0 px
    medio, d = _sobre_flecha(panel, "flecha:distancia")
    antes = panel.ctx.evaluar(panel.valores["distancia"])
    _arrastrar(visor, medio, medio + d * 60)
    assert panel.ctx.evaluar(panel.valores["distancia"]) > antes + 0.5      # arrastrar la flecha dibujada sube el valor (a ~0,015 mm por píxel)
    panel.cancelar()


def test_seccion_usa_la_triada_y_ninguna_caja_tapa_nada_en_4_vistas(app_qt):
    from omnicad.ui import manipuladores as mp
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    doc = _doc_caja()
    plano = hit_desde_ref({"tipo": "plano", "id": "XZ"}, doc.estado_final)
    panel, visor, _ = _panel(CATALOGO["seccion"](), doc, {"plano": [plano], "desfase": "3 mm", "angulo": "10 deg"})
    gestor = panel.manipuladores
    assert [m.ident for m in gestor.manips] == ["triada"]             # ya no una flecha y un arco sueltos
    triada = gestor.manips[0]
    assert triada.centro == pytest.approx(triada.ejes[2] * 3)
    n_cajas = 0
    for nombre, poner in _vistas(visor, triada.ejes[2]).items():
        poner()
        gestor.redibujar()
        triada = gestor.manips[0]
        partes = dict(triada._partes(gestor)[0])
        assert set(partes) == {("eje", 2), ("giro", 0)}, nombre
        s, ok = gestor.pantalla(partes[("eje", 2)])
        assert np.linalg.norm(s[-1] - s[0]) >= 0.45 * mp.LARGO_TRIADA * 0.8, nombre       # el eje se reconoce en toda vista
        for sub in (("eje", 2), ("giro", 0)):                 # con cada asa tomada, su caja de valor no tapa nada
            s, ok = gestor.pantalla(partes[sub])
            gestor._arrastre = {"m": triada, "sub": sub, "estado": {}}
            gestor.sincronizar_cajas()
            n_cajas += _sin_nada_encima(gestor)
            gestor._arrastre = None
            gestor.sincronizar_cajas()
    assert n_cajas >= 6
    # arrastrar el eje de la normal mueve «Distancia» y arrastrar el arco gira «Ángulo»
    _camara(visor, np.array([1.0, -1.0, 0.7]))
    gestor.redibujar()
    triada = gestor.manips[0]
    partes = dict(triada._partes(gestor)[0])
    s, _ = gestor.pantalla(partes[("eje", 2)])
    d = (s[-1] - s[0]) / np.linalg.norm(s[-1] - s[0])
    _arrastrar(visor, s.mean(axis=0), s.mean(axis=0) + d * 40)
    assert panel.ctx.evaluar(panel.valores["desfase"]) != pytest.approx(3.0)
    s, _ = gestor.pantalla(dict(gestor.manips[0]._partes(gestor)[0])[("giro", 0)])
    t = s[len(s) // 2 + 1] - s[len(s) // 2 - 1]
    _arrastrar(visor, s[len(s) // 2], s[len(s) // 2] + t / np.linalg.norm(t) * 40)
    assert panel.ctx.evaluar(panel.valores["angulo"], "angulo") != pytest.approx(10.0)
    panel.cancelar()


def test_las_cajas_de_extruir_y_revolucion_no_tapan_sus_asas_en_4_vistas(app_qt):
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos.solido import Extruir, Revolucion
    doc = _doc_rectangulo()
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "distancia": "10 mm", "conicidad": "5 deg"})
    gestor = panel.manipuladores
    total = 0
    for nombre, poner in _vistas(visor, np.array([0.0, 0.0, 1.0])).items():
        poner()
        visor.distancia *= 2                   # P-139: la flecha sale de la esquina; encuadrado justo, su caja queda afuera
        gestor.redibujar()
        total += _sin_nada_encima(gestor)      # en alguna vista la punta queda fuera de pantalla y su caja se oculta
    assert total >= 2
    panel.cancelar()
    doc = Documento()
    b = Boceto()
    b.agregar_rectangulo((5, 0), (10, 10))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano="XZ", boceto=b))
    eje = hit_desde_ref({"tipo": "eje", "id": "Z"}, doc.estado_final)
    panel, visor, _ = _panel(Revolucion(), doc, {"perfiles": [_perfil(doc)], "eje": [eje], "angulo": "90 deg"})
    for nombre, poner in _vistas(visor, np.array([0.0, 1.0, 0.0])).items():
        poner()
        panel.manipuladores.redibujar()
        _sin_nada_encima(panel.manipuladores)
    panel.cancelar()


def test_las_cajas_de_dos_lados_con_desfase_no_se_pisan(app_qt):
    """B-207: con Inicio=Desfase y Dirección=Dos lados las tres cajas (desfase, lado 1 y lado 2) salen de puntas de
    asa casi superpuestas. Cada par tiene que quedar separado, no pegado ni encima, como en Fusion. Se prueba con el
    perfil chico dentro de una escena grande, que es como lo vio la auditoría (las puntas caían a 1 px)."""
    from omnicad.ui import manipuladores as mp
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="400", largo="400", alto="10", x="-200", y="-450"))
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "inicio": "desfase", "direccion": "dos_lados",
                                             "distancia": "10 mm", "distancia2": "10 mm"})
    gestor = panel.manipuladores
    vistas_con_tres = 0
    for nombre, poner in _vistas(visor, np.array([0.0, 0.0, 1.0])).items():
        poner()
        visor.encuadrar()
        gestor.redibujar()
        rects = gestor.rectangulos_cajas()      # en alguna vista la punta de una flecha queda fuera y su caja se oculta
        vistas_con_tres += len(rects) == 3
        aire = {k: r.getRect() for k, r in rects.items()}
        for a, ra in rects.items():
            for b, rb in rects.items():
                if a >= b:
                    continue
                dx = max(ra.left(), rb.left()) - min(ra.right(), rb.right())
                dy = max(ra.top(), rb.top()) - min(ra.bottom(), rb.bottom())
                assert max(dx, dy) >= mp.AIRE_CAJAS_PX, (nombre, aire, (a, b, dx, dy))
    assert vistas_con_tres, {k: r.getRect() for k, r in gestor.rectangulos_cajas().items()}
    panel.cancelar()


def test_la_triada_de_seccion_esta_en_el_pivote_real_de_giro(app_qt):
    """Con una cara elegida, el centro de la tríada es el origen del plano (el pivote de `Plano.girado`), no el centroide."""
    from omnicad.timeline import entidades as ent
    from omnicad.ui.comandos import CATALOGO
    doc = _doc_caja()
    cara = _cara_de_arriba(doc)
    panel, _visor, _ = _panel(CATALOGO["seccion"](), doc, {"plano": [cara], "desfase": "2 mm", "angulo": "0 deg"})
    plano = ent.como_plano(_manip_de(panel))
    triada = panel.manipuladores.manips[0]
    assert triada.centro == pytest.approx(np.asarray(plano.origen) + np.asarray(plano.normal) * 2)
    assert triada.ejes[0] == pytest.approx(plano.u)             # el arco gira alrededor de u, como `girado`
    panel.cancelar()


def _manip_de(panel):
    from omnicad.ui import manipuladores as mp
    return mp.entidad(panel.valores["plano"][0], panel.ctx.estado)


def test_el_arco_visto_de_canto_se_arrastra_por_la_tangente(app_qt):
    """H-61: un arco de asa visto de canto (se ve como una línea con su asa) se arrastra a lo largo de la tangente
    en pantalla, como la flecha de frente; arrastrar a favor del ángulo lo sube y en contra lo baja."""
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.comandos.solido import Revolucion
    from omnicad.ui import manipuladores as mp_triada
    doc = Documento()
    b = Boceto()
    b.agregar_rectangulo((5, 0), (10, 10))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano="XZ", boceto=b))
    eje = hit_desde_ref({"tipo": "eje", "id": "Z"}, doc.estado_final)
    panel, visor, _ = _panel(Revolucion(), doc, {"perfiles": [_perfil(doc)], "eje": [eje], "angulo": "45 deg"})
    angulo = _manip(panel, "angulo:angulo")
    gestor = panel.manipuladores
    _camara(visor, np.array([1.0, 0.0, 0.0]))          # el plano del arco (eje Z) se ve de canto
    gestor.redibujar()
    t = np.radians(panel.ctx.evaluar(panel.valores["angulo"], "angulo"))
    tangente = -angulo.u * np.sin(t) + angulo.v * np.cos(t)          # sentido del ángulo creciente
    s, ok = gestor.pantalla(np.array([angulo.asa(gestor), angulo.asa(gestor) + tangente * angulo._r(gestor)]))
    assert ok.all()
    e = (s[1] - s[0]) / np.linalg.norm(s[1] - s[0])
    _arrastrar(visor, s[0], s[0] + e * 30)                            # P-139: el anillo (78 px) gira más por píxel
    subio = panel.ctx.evaluar(panel.valores["angulo"], "angulo")
    assert 50 < subio < 90, subio                                     # arrastró a favor: subió
    asa2 = gestor.pantalla([angulo.asa(gestor)])[0][0]
    _arrastrar(visor, asa2, asa2 - e * 30)
    bajo = panel.ctx.evaluar(panel.valores["angulo"], "angulo")
    assert bajo < subio, bajo                                         # en contra: bajó
    panel.cancelar()
    # y el arco de giro de la tríada (Sección), también de canto
    doc2 = _doc_caja()
    plano = hit_desde_ref({"tipo": "plano", "id": "XZ"}, doc2.estado_final)
    panel2, visor2, _ = _panel(CATALOGO["seccion"](), doc2, {"plano": [plano], "desfase": "3 mm", "angulo": "45 deg"})
    triada = _manip(panel2, "triada")
    gestor2 = panel2.manipuladores
    _camara(visor2, triada.ejes[2])                # el plano del arco de giro 0 (⊥ ejes[0]) se ve de canto
    gestor2.redibujar()
    _, a, b = triada._base(0)
    m = np.radians(45.0)                           # el punto del asa, en el medio del arco
    radio = 0.7 * mp_triada.LARGO_TRIADA * triada._partes(gestor2)[1]
    asa3 = triada.centro + (a * np.cos(m) + b * np.sin(m)) * radio
    tangente3 = -a * np.sin(m) + b * np.cos(m)
    s3, ok3 = gestor2.pantalla(np.array([asa3, asa3 + tangente3 * radio]))
    assert ok3.all()
    e3 = (s3[1] - s3[0]) / np.linalg.norm(s3[1] - s3[0])
    _arrastrar(visor2, s3[0], s3[0] + e3 * 50)
    subio3 = panel2.ctx.evaluar(panel2.valores["angulo"], "angulo")
    assert subio3 > 45, subio3                      # arrastró a favor: subió
    panel2.cancelar()


@pytest.mark.parametrize("clave, invertir, crece", [("red", False, (0, 1, 0)), ("red", True, (0, -1, 0)),
                                                    ("nervio", False, (0, 0, 1)), ("nervio", True, (0, 0, -1))])
def test_b219_la_flecha_de_profundidad_apunta_adonde_crece_la_pared(app_qt, clave, invertir, crece):
    """B-219: caja 40³ hueca (paredes de 2) y una línea a y = 30, z = 30. La Red crece por la normal hasta la pared más
    cercana (+Y) y el Nervio dentro del plano (+Z); «Cambiar dirección» los manda al otro lado. La flecha de
    Profundidad sigue ese sentido, y la del espesor del Nervio va por la normal del plano."""
    from omnicad import api
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO

    s = api.Sesion()
    cid = api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 40, "anchor": "corner"})["result"]
    cid = cid["bodies_created"][0]["id"]
    assert api.llamar(s, "shell", {"body": cid, "faces": [], "thickness": 2})["ok"]
    assert api.llamar(s, "create_construction_plane", {"plane": "XZ", "offset": -30, "name": "P30"})["ok"]
    bid = api.llamar(s, "create_sketch", {"plane": "P30"})["result"]["sketch"]["id"]
    assert api.llamar(s, "draw_line", {"sketch": bid, "start_x": 10, "start_y": 30, "end_x": 30, "end_y": 30})["ok"]
    doc = s.doc
    est = doc.estado_final
    curva = next(iter(est.bocetos[bid].boceto.curvas))
    h_curva = hit_desde_ref({"tipo": "curva_boceto", "boceto": bid, "curva": curva}, est)
    panel, _visor, _ = _panel(CATALOGO[clave](), doc, {"curvas": [h_curva], "extension": "profundidad",
                                                       "profundidad": "5 mm", "invertir": invertir})
    flechas = {m.clave: m for m in panel.manipuladores.manips}
    assert np.allclose(flechas["profundidad"].direccion, crece, atol=1e-6)
    assert np.allclose(flechas["profundidad"].origen, (20, 30, 30), atol=1e-6)
    if clave == "nervio":
        assert abs(flechas["espesor"].direccion[1]) == pytest.approx(1.0)
    panel.cancelar()


def test_b343_las_asas_de_la_conicidad_frenan_donde_el_perfil_se_cierra(app_qt):
    """B-343: con conicidad hacia adentro el perfil de 20 × 10 (radio inscripto 5) se cierra a 5/tan|a| de distancia.
    Como Fusion, arrastrar la flecha o el asa del ángulo frena justo antes (−37° → 6,635 mm; 20 mm → −14,04°) y la
    previa sigue sana, en vez de pasar el límite y dejar el error del kernel."""
    import math

    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "distancia": "3 mm", "conicidad": "-37 deg"})
    medio, d = _sobre_flecha(panel, "flecha:distancia")
    _arrastrar(visor, medio, medio + d * 800)                          # muy afuera: pasaría el cierre
    limite = 5 / math.tan(math.radians(37))
    assert limite - 0.1 < panel.ctx.evaluar(panel.valores["distancia"]) < limite
    panel._t_previa.stop()
    panel._calcular_previa()
    assert panel._previa_ok, panel.mensaje.text()
    panel.cancelar()

    panel, visor, _ = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "distancia": "20 mm"})
    visor.distancia *= 3                                               # P-139: el anillo está a 20 mm, en el pie de la flecha
    gestor = panel.manipuladores
    angulo = _manip(panel, "angulo:conicidad")
    asa = gestor.pantalla([angulo.asa(gestor)])[0][0]
    centro = gestor.pantalla([angulo.centro])[0][0]
    afuera = gestor.pantalla([angulo.centro + angulo.v * 30])[0][0]
    _arrastrar(visor, asa, asa - (afuera - centro) * 3)                  # muy hacia adentro: pasaría el cierre
    limite = -math.degrees(math.atan(5 / 20))
    assert limite < panel.ctx.evaluar(panel.valores["conicidad"], "angulo") < limite + 0.5
    panel._t_previa.stop()
    panel._calcular_previa()
    assert panel._previa_ok, panel.mensaje.text()
    panel.cancelar()


def test_b361_los_radios_de_conicidad_se_miden_una_vez_por_perfil(monkeypatch):
    """B-361: sumar un perfil mide solo el nuevo (con 29 perfiles, medirlos todos en cada clic sumaba 0,7 s)."""
    from omnicad.nucleo import solidos_crear as sc
    from omnicad.ui.comandos import solido
    medidas, original = [], sc.radios_conicidad
    monkeypatch.setattr(sc, "radios_conicidad", lambda caras: medidas.append(len(caras)) or original(caras))
    a, b = (g.caras(g.caja(10, 10, 10, (x, 0, 0)))[0] for x in (0, 20))
    assert solido._radios_conicidad([a]) == solido._radios_conicidad([a, b])
    solido._radios_conicidad([a, b])
    assert medidas == [1, 1]
def _arrastrar_con_previa(panel, visor, desde, hasta, pasos=12):
    """Como `_arrastrar`, pero con la vista previa entre movimiento y movimiento (lo que hace el temporizador en la app)."""
    from PySide6.QtCore import QEvent, Qt
    desde, hasta = np.asarray(desde, float), np.asarray(hasta, float)
    _raton(visor, QEvent.MouseButtonPress, desde, Qt.LeftButton, Qt.LeftButton)
    for k in range(1, pasos + 1):
        _raton(visor, QEvent.MouseMove, desde + (hasta - desde) * k / pasos, Qt.NoButton, Qt.LeftButton)
        for _ in range(3):                     # una previa que falla vuelve el valor y pide otra
            panel._t_previa.stop()
            panel._calcular_previa()
            if not panel._t_previa.isActive():
                break
    _raton(visor, QEvent.MouseButtonRelease, hasta, Qt.LeftButton, Qt.NoButton)


@pytest.mark.parametrize("caso", ["empalme", "vaciado", "pulsar"])
def test_b345_el_asa_frena_donde_la_pieza_lo_admite(app_qt, caso):
    """B-345: arrastrada muy pasada del límite (radio de empalme enorme, vaciado más grueso que la caja, pulsar hacia
    adentro más que la caja), el asa queda en el último valor con la previa sana y el panel dice dónde frenó y por qué
    (B-364); tecleado, el mismo valor sí da rojo."""
    from omnicad.ui.comandos.modificar import Empalme, PulsarTirar, Vaciado
    doc = _doc_caja()
    comando, valores, clave, sentido = {
        "empalme": (Empalme(), {"aristas": [_arista_de_arriba(doc)], "radio": "2 mm"}, "radio", 1),
        "vaciado": (Vaciado(), {"caras": [_cara_de_arriba(doc)], "espesor_interior": "2 mm"}, "espesor_interior", 1),
        "pulsar": (PulsarTirar(), {"objetos": [_cara_de_arriba(doc)], "distancia": "-2 mm"}, "distancia", -1),
    }[caso]
    panel, visor, estados = _panel(comando, doc, valores)
    panel._calcular_previa()
    assert panel._previa_ok
    medio, d = _sobre_flecha(panel, f"flecha:{clave}")
    _arrastrar_con_previa(panel, visor, medio, medio + d * 300)
    if caso != "pulsar":                       # B-364: frenar callado parecía arbitrario (pulsar llega a +18 mm sin frenar)
        assert "el asa frena en" in panel.mensaje.text(), panel.mensaje.text()
    valor = panel.ctx.evaluar(panel.valores[clave])
    panel._calcular_previa()
    assert panel._previa_ok and estados[-1] is not None, panel.mensaje.text()
    assert abs(valor) > 2                      # avanzó hasta el límite, no quedó donde arrancó
    panel.set_valor(clave, f"{sentido * 400} mm")    # tecleado no frena: queda en rojo
    panel._calcular_previa()
    assert not panel._previa_ok
    panel.cancelar()


def _cara_lateral(doc):
    from omnicad.nucleo import referencias as refs
    from omnicad.ui.comando import hit_desde_ref
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    cara = next(c for c in refs.subformas(forma, "cara") if np.allclose(g.centro_masa(c, True), (10, 0, 10)))
    return hit_desde_ref(refs.referencia("op1.c1", cara, caja=g.caja_envolvente(forma)), doc.estado_final)


@pytest.mark.parametrize("clave,campos,asa", [
    ("chaflan_3d", lambda d: {"aristas": [_arista_de_arriba(d)]}, "distancia"),
    ("engrosar", lambda d: {"caras": [_cara_de_arriba(d)]}, "espesor"),
    ("desfase_cara", lambda d: {"caras": [_cara_de_arriba(d)], "distancia": "2 mm"}, "distancia"),
    ("sup_desfase", lambda d: {"caras": [_cara_de_arriba(d)], "distancia": "2 mm"}, "distancia"),
    ("desmoldeo", lambda d: {"plano": [_cara_de_arriba(d)], "caras": [_cara_lateral(d)]}, "angulo"),
])
@pytest.mark.parametrize("sentido", [1, -1])
def test_b345_asas_de_los_demas_comandos_dejan_la_previa_sana(app_qt, clave, campos, asa, sentido):
    """B-345: las flechas y el arco de esos comandos, arrastrados muy lejos hacia los dos lados, terminan con la previa
    sana (antes: rojo con radio, espesor o desfase de ±400 mm, o un desmoldeo de ±175°)."""
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui import manipuladores as mp
    doc = _doc_caja()
    panel, visor, estados = _panel(CATALOGO[clave](), doc, campos(doc))
    panel._calcular_previa()
    assert panel._previa_ok, panel.mensaje.text()
    gestor = panel.manipuladores
    m = next(x for x in gestor.manips if getattr(x, "clave", None) == asa)
    if isinstance(m, mp.Angulo):                   # el asa da 17 pasos de 10° alrededor del arco
        r, t0 = m._r(gestor), m._theta(gestor)
        puntos = [m.centro + (m.u * np.cos(t0 + sentido * np.radians(10 * k)) + m.v * np.sin(t0 + sentido * np.radians(10 * k))) * r
                  for k in range(18)]
        s, ok = gestor.pantalla(puntos)
        assert ok.all()
        from PySide6.QtCore import QEvent, Qt
        _raton(visor, QEvent.MouseButtonPress, s[0], Qt.LeftButton, Qt.LeftButton)
        for q in s[1:]:
            _raton(visor, QEvent.MouseMove, q, Qt.NoButton, Qt.LeftButton)
            for _ in range(3):
                panel._t_previa.stop()
                panel._calcular_previa()
                if not panel._t_previa.isActive():
                    break
        _raton(visor, QEvent.MouseButtonRelease, s[-1], Qt.LeftButton, Qt.NoButton)
    else:
        medio, d = _sobre_flecha(panel, f"flecha:{asa}")
        _arrastrar_con_previa(panel, visor, medio, medio + d * 300 * sentido)
    panel._calcular_previa()
    assert panel._previa_ok and estados[-1] is not None, (panel.valores[asa], panel.mensaje.text())
    panel.cancelar()


def test_p139_la_conicidad_de_extruir_es_un_anillo_en_el_pie_de_la_flecha(app_qt):
    """P-139: como Fusion, la conicidad de Extruir es un anillo de 360° centrado en el pie de la flecha de distancia
    (sobre el borde del perfil), sin la V de radios. En reposo se ve un arco corto junto al asa; con el ratón encima, el
    anillo entero (atrás punteado) y la caja de valor. El anillo sigue a la flecha mientras se la arrastra, y arrastrar
    el asa por el anillo inclina el cuerpo."""
    from PySide6.QtCore import QEvent, Qt

    from omnicad.ui import manipuladores as mp
    from omnicad.ui.comandos.solido import Extruir
    doc = _doc_rectangulo()
    panel, visor, estados = _panel(Extruir(), doc, {"perfiles": [_perfil(doc)], "distancia": "10 mm",
                                                    "conicidad": "-20 deg"})
    gestor = panel.manipuladores
    anillo, flecha = _manip(panel, "angulo:conicidad"), _manip(panel, "flecha:distancia")
    assert isinstance(anillo, mp.AnilloAngulo)
    x, y, z = flecha.origen
    assert z == pytest.approx(0) and (min(abs(x), abs(x - 20)) < 1e-6 or min(abs(y), abs(y - 10)) < 1e-6)   # en el borde
    anillo.asa(gestor)
    assert anillo.centro == pytest.approx(flecha.puntos(gestor)[0])                # el pie de la flecha
    r = anillo._r(gestor)

    def radios(prim):
        return np.linalg.norm(prim[1] - anillo.centro, axis=1) / r

    reposo = anillo.dibujar(gestor, None)
    assert radios(reposo[0]) == pytest.approx(1.0, abs=1e-6) and len(reposo[0][1]) < 40        # arco corto, sin V
    asa = gestor.pantalla([anillo.asa(gestor)])[0][0]
    _raton(visor, QEvent.MouseMove, asa, Qt.NoButton, Qt.NoButton)                  # el ratón pasa por el asa
    assert gestor._hover[0] == anillo.ident and "conicidad" in gestor.cajas
    assert anillo.ayuda == "Especificar la distancia y el ángulo de inclinación"
    delante, detras, *_ = anillo.dibujar(gestor, "asa")
    assert radios(delante) == pytest.approx(1.0, abs=1e-6) and radios(detras) == pytest.approx(1.0, abs=1e-6)
    assert len(delante[1]) == pytest.approx(2 * len(detras[1]), abs=8)              # atrás, un tramo sí y otro no
    _raton(visor, QEvent.MouseMove, asa + 200, Qt.NoButton, Qt.NoButton)
    assert "conicidad" not in gestor.cajas

    medio, d = _sobre_flecha(panel, "flecha:distancia")
    _arrastrar(visor, medio, medio + d * 15)
    assert panel.ctx.evaluar(panel.valores["distancia"]) > 10
    anillo.asa(gestor)
    assert anillo.centro == pytest.approx(flecha.puntos(gestor)[0])                # siguió a la flecha
    panel.set_valor("distancia", "10 mm")
    panel._calcular_previa()
    antes = g.volumen(_cuerpo(estados[-1]).forma)
    anillo = _manip(panel, "angulo:conicidad")
    asa = gestor.pantalla([anillo.asa(gestor)])[0][0]
    centro = gestor.pantalla([anillo.centro])[0][0]
    adentro = gestor.pantalla([anillo.centro - anillo.v * 30])[0][0]
    _arrastrar(visor, asa, asa + (adentro - centro) * 0.15)
    assert panel.ctx.evaluar(panel.valores["conicidad"], "angulo") < -20
    panel._calcular_previa()
    assert panel._previa_ok and g.volumen(_cuerpo(estados[-1]).forma) < antes


def test_p143_asa_del_empalme_en_la_punta_libre_de_la_arista(app_qt):
    """P-143: como en Fusion, el asa del radio es una flecha-puntero azul en la última arista elegida, en el punto donde
    se hizo clic (sin clic, en el medio), y señala hacia adentro del material."""
    from omnicad import api
    from omnicad.nucleo import referencias as refs
    from omnicad.ui import manipuladores as mp
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos.modificar import Empalme
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 60, "width": 40, "height": 80})["ok"]
    assert api.llamar(s, "create_box", {"length": 20, "width": 50, "height": 24, "y": -45, "z": 28,
                                        "operation": "join"})["ok"]
    doc = s.doc
    cid, cuerpo = next(iter(doc.estado_final.cuerpos.items()))
    arista = next(e for e in refs.subformas(cuerpo.forma, "arista")
                  if np.allclose(refs.firma_arista(e)["medio"], (-10, -45, 52)))     # arriba a la izquierda del saliente
    hit = hit_desde_ref(refs.referencia(cid, arista, caja=g.caja_envolvente(cuerpo.forma)), doc.estado_final)
    hit["punto"] = np.array([-9.8, -62.0, 52.1])               # el clic, cerca de la punta libre
    panel, _visor, _estados = _panel(Empalme(), doc, {"aristas": [hit], "radio": "2 mm"})
    (asa,) = panel.manipuladores.manips
    assert isinstance(asa, mp.FlechaPuntero) and asa.color == mp.AZUL_ASA
    assert np.allclose(asa.origen, (-10, -62, 52))                 # el punto de la arista más cercano al clic
    assert np.allclose(asa.direccion, np.array([1, 0, -1]) / np.sqrt(2))     # hacia adentro, por la bisectriz
    otra = next(e for e in refs.subformas(cuerpo.forma, "arista")
                if np.allclose(refs.firma_arista(e)["medio"], (10, -45, 28)))       # abajo a la derecha
    panel.set_valor("aristas", [hit, hit_desde_ref(refs.referencia(cid, otra, caja=g.caja_envolvente(cuerpo.forma)),
                                                   doc.estado_final)])
    (asa,) = panel.manipuladores.manips
    assert np.allclose(asa.origen, (10, -45, 28))       # salta a la última arista elegida; sin clic, en su medio
    panel.cancelar()
