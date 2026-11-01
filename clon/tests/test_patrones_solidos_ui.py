# -*- coding: utf-8 -*-
"""Diálogos de los patrones de sólido con eventos reales de ratón y teclado (QTest / QMouseEvent) sobre el panel y el
visor: tipo de patrón, dirección 2 derivada, casillas de supresión, modos del circular, asas sobre el recorrido de la
ruta, puntos y la lista de la Multitransformación. Mide posiciones y volúmenes de lo que queda en el documento."""
import math

import numpy as np
import pytest
from test_manipuladores import _arrastrar, _doc_caja, _panel, _raton, app_qt  # noqa: F401  (fixture)

from omnicad.nucleo import geometria as g
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpPrimitiva
from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import ContextoComando, hit_desde_ref
from omnicad.ui.comandos import CATALOGO

EJE_X, EJE_Y, EJE_Z = ({"tipo": "eje", "id": e} for e in "XYZ")


def _hit(doc, ref):
    return hit_desde_ref(ref, doc.estado_final)


def _abrir(clave, doc=None, valores=None):
    doc = doc or _doc_caja()
    v = {"cuerpos": [_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})], **(valores or {})}
    panel, visor, estados = _panel(CATALOGO[clave](), doc, v)
    visor.vista("iso")
    panel.manipuladores.actualizar()
    return panel, visor, estados, doc


def _teclear(widget, texto):
    """Escribe `texto` en un campo como lo haría una persona: lo selecciona entero, teclea y confirma con Tab."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    widget.setFocus()
    QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(widget, texto)
    QTest.keyClick(widget, Qt.Key_Tab)


def _elegir(combo, clave):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    i = combo.findData(clave)
    assert i >= 0, clave
    QTest.keyClick(combo, Qt.Key_Home)
    for _ in range(i):
        QTest.keyClick(combo, Qt.Key_Down)
    assert combo.currentData() == clave


def _marcar(casilla):
    """Clic real sobre el cuadradito de una casilla (el medio del widget puede caer fuera de él)."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    QTest.mouseClick(casilla, Qt.LeftButton, pos=QPoint(6, max(casilla.height() // 2, 6)))


def _clic(visor, xy):
    from PySide6.QtCore import QEvent, Qt
    _raton(visor, QEvent.MouseButtonPress, xy, Qt.LeftButton, Qt.LeftButton)
    _raton(visor, QEvent.MouseButtonRelease, xy, Qt.LeftButton, Qt.NoButton)


def _esquinas(estado, prefijo):
    return sorted(tuple(round(float(x), 4) for x in g.caja_envolvente(c.forma)[0])
                  for cid, c in estado.cuerpos.items() if cid.startswith(prefijo) or cid == "op1.c1")


def _manip(panel, tipo, clave=None):
    return next(m for m in panel.manipuladores.manips if isinstance(m, tipo) and (clave is None or m.clave == clave))


def _asa_n(panel, clave):
    return _manip(panel, mp.AsaCantidad, clave)


def _arrastrar_asa_n(panel, clave, copias):
    gm = panel.manipuladores
    m = _asa_n(panel, clave)
    asa, _p, t = m._asa(gm)
    xy, ok = gm.pantalla([asa, asa + t * m.paso * copias])
    assert ok.all()
    _arrastrar(panel.visor, *xy)


# ---------------------------------------------------------------- rectangular
def test_rectangular_la_direccion_2_derivada_se_ve_y_se_aplica(app_qt):  # noqa: F811
    panel, visor, estados, doc = _abrir("patron_rectangular_3d", valores={
        "dir1": [_hit(_doc_caja(), EJE_X)], "n1": 3, "d1": "30 mm", "distribucion": "espaciado"})
    # con la cantidad 2 en 1 solo hay dirección 1; la 2 se ofrece con su asa de cantidad (como Fusion)
    assert not panel._visible(next(c for c in panel.campos if c.clave == "d2"))
    idents = [m.ident for m in panel.manipuladores.manips]
    assert "cantidad:n2" in idents and "flecha:d2" not in idents
    _teclear(panel.widgets["n2"], "2")
    assert panel.valores["n2"] == 2 and panel._visible(next(c for c in panel.campos if c.clave == "d2"))
    panel._calcular_previa()
    assert "derivada" in panel.widgets["info_dir2"].text()
    flecha = _manip(panel, mp.Flecha, "d2")
    assert np.allclose(flecha.direccion, (0, 1, 0))                  # perpendicular a X: la flecha va por +Y
    _teclear(panel.widgets["d2"], "25 mm")
    panel._calcular_previa()
    assert panel._previa_ok and panel.ultima_op.p["dir2_derivada"] is True
    assert _esquinas(estados[-1], panel.ultima_op.id) == [(x, y, 0.0) for x in (0.0, 30.0, 60.0) for y in (0.0, 25.0)]
    panel.cancelar()
    assert len(doc.operaciones) == 1                                   # cancelar no deja nada en el documento


def test_rectangular_simetria_por_direccion_desde_las_casillas(app_qt):  # noqa: F811
    panel, _visor, estados, _doc = _abrir("patron_rectangular_3d", valores={
        "dir1": [_hit(_doc_caja(), EJE_X)], "n1": 2, "d1": "40 mm", "n2": 2, "d2": "40 mm", "distribucion": "espaciado"})
    _marcar(panel.widgets["simetrico"])
    assert panel.valores["simetrico"] is True and panel.valores["simetrico2"] is False
    panel._calcular_previa()
    op = panel.ultima_op
    assert (op.p["simetrico"], op.p["simetrico2"]) == (True, False)
    assert len(_esquinas(estados[-1], op.id)) == 6                      # 3 en X (simétrico) × 2 en Y (un lado)
    assert min(p[1] for p in _esquinas(estados[-1], op.id)) == pytest.approx(0.0)      # nada del lado −Y
    assert min(p[0] for p in _esquinas(estados[-1], op.id)) == pytest.approx(-40.0)    # y la dirección 1 sí tiene lado −X
    panel.cancelar()


def test_rectangular_supresion_con_clic_en_la_casilla_y_estabilidad(app_qt):  # noqa: F811
    panel, visor, estados, doc = _abrir("patron_rectangular_3d", valores={
        "dir1": [_hit(_doc_caja(), EJE_X)], "n1": 3, "d1": "30 mm", "n2": 2, "d2": "30 mm", "distribucion": "espaciado"})
    _marcar(panel.widgets["ver_casillas"])
    assert panel.valores["ver_casillas"] is True
    casillas = _manip(panel, mp.CasillasCopias)
    assert len(casillas.items) == 6 and casillas.originales == {(0, 0)}
    gm = panel.manipuladores
    punto = next(p for ident, p, _e in casillas.items if ident == (2, 1))
    xy, ok = gm.pantalla([punto])
    assert ok.all()
    _clic(visor, xy[0])                                                  # clic real sobre la casilla de la copia (2, 1)
    assert panel.valores["suprimir"] == "2:1"
    panel._calcular_previa()
    inicial = _esquinas(estados[-1], panel.ultima_op.id)
    assert len(inicial) == 5 and (60.0, 30.0, 0.0) not in inicial and (60.0, 0.0, 0.0) in inicial
    # la exclusión sigue a SU copia al cambiar cantidades y distancias
    _teclear(panel.widgets["n1"], "4")
    _teclear(panel.widgets["d1"], "40 mm")
    panel._calcular_previa()
    despues = _esquinas(estados[-1], panel.ultima_op.id)
    assert len(despues) == 7 and (80.0, 30.0, 0.0) not in despues and (80.0, 0.0, 0.0) in despues
    # tocar la casilla de nuevo la restaura
    casillas = _manip(panel, mp.CasillasCopias)
    xy, _ok = gm.pantalla([next(p for ident, p, _e in casillas.items if ident == (2, 1))])
    _clic(visor, xy[0])
    assert panel.valores["suprimir"] == ""
    panel.cancelar()


def test_rectangular_exclusion_fuera_del_patron_se_explica_y_se_conserva(app_qt):  # noqa: F811
    panel, _visor, _estados, _doc = _abrir("patron_rectangular_3d", valores={
        "dir1": [_hit(_doc_caja(), EJE_X)], "n1": 4, "d1": "30 mm", "distribucion": "espaciado", "suprimir": "3:0"})
    panel._calcular_previa()
    assert panel._previa_ok and not panel.mensaje.text()
    _teclear(panel.widgets["n1"], "2")
    panel._calcular_previa()
    assert "ya no existen" in panel.mensaje.text() and panel.valores["suprimir"] == "3:0"
    assert panel.ultima_op.p["suprimir"] == [[3, 0]]
    panel.cancelar()


def test_suprimir_con_texto_mal_escrito_dice_que_formato_va(app_qt):  # noqa: F811
    panel, _v, _e, _d = _abrir("patron_rectangular_3d", valores={
        "dir1": [_hit(_doc_caja(), EJE_X)], "n1": 3, "d1": "30 mm", "distribucion": "espaciado"})
    _teclear(panel.widgets["suprimir"], "uno, 2:x")
    panel._calcular_previa()
    assert panel.ultima_op is None and "separados por coma" in panel.mensaje.text()
    _teclear(panel.widgets["suprimir"], "0:0")
    panel._calcular_previa()
    assert "original no se puede suprimir" in panel.mensaje.text()
    panel.cancelar()


def test_cambiar_el_tipo_de_patron_conserva_los_objetos(app_qt):  # noqa: F811
    panel, _v, _e, _d = _abrir("patron_rectangular_3d", valores={"dir1": [_hit(_doc_caja(), EJE_X)]})
    _elegir(panel.widgets["forma"], "circular")
    campos = {c.clave: c for c in panel.campos}
    assert panel._visible(campos["eje"]) and not panel._visible(campos["dir1"]) and panel._visible(campos["cuerpos"])
    assert len(panel.valores["cuerpos"]) == 1 and len(panel.valores["dir1"]) == 1            # nada se perdió
    _elegir(panel.widgets["forma"], "rectangular")
    assert panel._visible(campos["dir1"]) and panel.valores["dir1"]
    panel.cancelar()


# ---------------------------------------------------------------- circular
def _doc_cubo_lejos():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="4", largo="4", alto="4", x="30", y="-2"))
    return doc


def _angulos(estado, prefijo):
    res = []
    for cid, c in estado.cuerpos.items():
        if cid.startswith(prefijo) or cid == "op1.c1":
            lo, hi = g.caja_envolvente(c.forma)
            res.append(round(math.degrees(math.atan2((lo[1] + hi[1]) / 2, (lo[0] + hi[0]) / 2)) % 360, 3))
    return sorted(res)


def test_circular_modos_completo_parcial_simetrico_y_el_asa_coincide_con_la_copia(app_qt):  # noqa: F811
    doc = _doc_cubo_lejos()
    panel, _visor, estados, _d = _abrir("patron_circular_3d", doc, {"eje": [_hit(doc, EJE_Z)], "n": 6})
    campos = {c.clave: c for c in panel.campos}
    panel._calcular_previa()
    assert not panel._visible(campos["angulo"]) and "0°, 60°, 120°" in panel.widgets["info_circular"].text()
    assert np.diff(_angulos(estados[-1], panel.ultima_op.id)) == pytest.approx([60.0] * 5, abs=0.05)
    assert "angulo:angulo" not in [m.ident for m in panel.manipuladores.manips]
    # Parcial: tres copias sobre 120° → 0°, 60° y 120°; el asa de cantidad queda en la última copia calculada
    _elegir(panel.widgets["modo"], "parcial")
    _teclear(panel.widgets["n"], "3")
    _teclear(panel.widgets["angulo"], "120 deg")
    panel._calcular_previa()
    assert _angulos(estados[-1], panel.ultima_op.id) == pytest.approx([0, 60, 120], abs=0.05)
    gm = panel.manipuladores
    asa = _asa_n(panel, "n")._asa(gm)[1]                                  # punto de la última copia según el asa
    centros = [(np.array(g.caja_envolvente(c.forma)[0]) + np.array(g.caja_envolvente(c.forma)[1])) / 2
               for cid, c in estados[-1].cuerpos.items() if cid.startswith(panel.ultima_op.id)]
    ultima = min(centros, key=lambda c: abs(math.degrees(math.atan2(c[1], c[0])) - 120))      # la copia a 120°
    assert asa[:2] == pytest.approx(ultima[:2], abs=1e-6)               # el asa y el resultado usan las mismas posiciones
    # Simétrico: n a cada lado hasta ± el ángulo
    _elegir(panel.widgets["modo"], "simetrico")
    _teclear(panel.widgets["angulo"], "90 deg")
    panel._calcular_previa()
    assert _angulos(estados[-1], panel.ultima_op.id) == pytest.approx([0, 45, 90, 270, 315], abs=0.1)
    # Ángulo entre copias
    _elegir(panel.widgets["modo"], "espaciado")
    _teclear(panel.widgets["angulo_paso"], "30 deg")
    panel._calcular_previa()
    assert _angulos(estados[-1], panel.ultima_op.id) == pytest.approx([0, 30, 60], abs=0.05)
    panel.cancelar()


def test_circular_pasar_de_completo_a_parcial_no_deja_los_360_sin_explicar(app_qt):  # noqa: F811
    doc = _doc_cubo_lejos()
    panel, _v, _e, _d = _abrir("patron_circular_3d", doc, {"eje": [_hit(doc, EJE_Z)], "n": 4, "angulo": "360 deg"})
    _elegir(panel.widgets["modo"], "parcial")
    assert panel.valores["angulo"] == "180 deg"                         # 360° sería lo mismo que Completo
    _teclear(panel.widgets["angulo"], "720 deg")
    panel._calcular_previa()
    assert panel.ultima_op is not None and "una vuelta" in panel.mensaje.text()      # el error degenerado se muestra
    panel.cancelar()


def test_circular_arrastrar_el_asa_de_angulo_y_cantidad(app_qt):  # noqa: F811
    doc = _doc_cubo_lejos()
    panel, _visor, _e, _d = _abrir("patron_circular_3d", doc, {
        "eje": [_hit(doc, EJE_Z)], "n": 3, "modo": "parcial", "angulo": "90 deg"})
    _arrastrar_asa_n(panel, "n", 2)
    assert panel.widgets["n"].value() == 5
    panel._calcular_previa()
    assert panel._previa_ok
    panel.cancelar()


# ---------------------------------------------------------------- ruta
def _doc_ruta(puntos):
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="2", alto="2", x="-1", y="-1"))
    b = Boceto()
    for a, c in zip(puntos, puntos[1:], strict=False):
        b.agregar_linea(a, c)
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    doc.agregar(sk)
    return doc, [_hit(doc, {"tipo": "curva_boceto", "boceto": sk.id, "curva": c}) for c in b.curvas]


def test_ruta_compuesta_las_asas_recorren_toda_la_cadena(app_qt):  # noqa: F811
    doc, ruta = _doc_ruta([(0, 0), (30, 0), (30, 30)])
    panel, visor, estados, _d = _abrir("patron_ruta", doc, {"ruta": ruta, "rn": 3, "rd": "30 mm",
                                                         "distribucion": "extension"})
    gm = panel.manipuladores
    tramo = _manip(panel, mp.AsaRecorrido, "rd")
    assert tramo.recorrido.largo == pytest.approx(60.0)                  # las dos aristas, no solo la primera
    assert np.allclose(tramo.asa(gm), (30, 0, 0), atol=1e-6)                       # el final de la primera arista
    # arrastrar el asa por la ruta hasta el final de la segunda arista: distancia = 60 mm (longitud recorrida)
    xy, ok = gm.pantalla([tramo.asa(gm), (30, 30, 0)])
    assert ok.all()
    _arrastrar(visor, *xy)
    assert panel.ctx.evaluar(panel.valores["rd"]) == pytest.approx(60.0, abs=1.5)
    panel._calcular_previa()
    centros = sorted(tuple(round(float(x)) for x in (np.array(g.caja_envolvente(c.forma)[0]) + np.array(g.caja_envolvente(c.forma)[1])) / 2)
                     for cid, c in estados[-1].cuerpos.items() if cid.startswith(panel.ultima_op.id) or cid == "op1.c1")
    assert centros[0] == (0, 0, 1) and centros[-1][:2] == (30, 30) and len(centros) == 3
    # la cantidad se tira sobre el recorrido real: la última copia queda donde el asa dice
    posicion = _asa_n(panel, "rn").posicion(3)[0]
    assert posicion == pytest.approx([30, 30, 0], abs=1.5)
    panel.cancelar()


def test_ruta_insuficiente_avisa_y_el_inicio_se_ve_en_la_ruta(app_qt):  # noqa: F811
    doc, ruta = _doc_ruta([(0, 0), (20, 0)])
    panel, _visor, _estados, _d = _abrir("patron_ruta", doc, {"ruta": ruta, "rn": 5, "rd": "10 mm",
                                                           "distribucion": "espaciado"})
    panel._calcular_previa()
    assert panel._previa_ok and "La ruta no alcanza" in panel.mensaje.text()
    asa = _manip(panel, mp.AsaRuta, "inicio")
    assert asa.asa(panel.manipuladores) == pytest.approx([0, 0, 0], abs=1e-6)
    _teclear(panel.widgets["inicio"], "50")
    assert _manip(panel, mp.AsaRuta, "inicio").asa(panel.manipuladores) == pytest.approx([10, 0, 0], abs=0.3)
    panel.cancelar()


# ---------------------------------------------------------------- puntos
def test_puntos_marcadores_explicacion_y_traslacion_exacta(app_qt):  # noqa: F811
    doc = _doc_caja()
    b = Boceto()
    p1 = b.agregar_punto(50, 0)
    p2 = b.agregar_punto(0, 60)
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=b)
    doc.agregar(sk)
    ref = lambda p: {"tipo": "punto_boceto", "boceto": sk.id, "punto": p}  # noqa: E731
    panel, _v, estados, _d = _abrir("patron_puntos", doc, {"puntos": [_hit(doc, ref(p1)), _hit(doc, ref(p2))]})
    panel._calcular_previa()
    assert "origen" in panel.widgets["info_puntos"].text() and "puntos sueltos" in panel.widgets["info_puntos"].text()
    assert _esquinas(estados[-1], panel.ultima_op.id) == [(0.0, 0.0, 0.0), (0.0, 60.0, 0.0), (50.0, 0.0, 0.0)]
    prims = panel.comando.previa_vista(panel.ctx, panel.valores, panel.ultima_op)
    assert [p[0] for p in prims] == ["lineas", "puntos", "puntos"] and len(prims[1][1]) == 2
    # referencia: el punto (50, 0) va a cada destino; el destino igual a la referencia no repite la copia
    panel.set_valor("referencia", [_hit(doc, ref(p1))])
    panel._calcular_previa()
    assert _esquinas(estados[-1], panel.ultima_op.id) == [(-50.0, 60.0, 0.0), (0.0, 0.0, 0.0)]
    panel.cancelar()


# ---------------------------------------------------------------- multitransformación
def test_multitransformar_lista_agregar_reordenar_quitar_y_aceptar_sin_cambios(app_qt):  # noqa: F811
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    doc = _doc_caja()
    from omnicad.ui.comando import PanelComando
    from omnicad.ui.comandos.patrones import Multitransformar
    from omnicad.ui.visor3d import Visor3D
    visor = Visor3D()
    visor.resize(800, 600)
    visor.set_modelo(doc.estado_final)
    panel = PanelComando(Multitransformar(), ContextoComando(doc), visor,
                         {"cuerpos": [_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})]})
    lista = panel.widgets["lista"]
    assert lista.lista.count() == 1 and "falta la dirección 1" in lista.lista.item(0).text()
    panel._calcular_previa()
    assert panel.ultima_op is None and "Transformación 1" in panel.mensaje.text() and "dirección 1" in panel.mensaje.text()
    panel.set_valor("t_dir1", [_hit(doc, EJE_X)])
    panel.set_valor("t_distribucion", "espaciado")
    _teclear(panel.widgets["t_n1"], "3")
    _teclear(panel.widgets["t_d1"], "30 mm")
    # agregar una Simetría desde el menú del botón
    lista.agregar.menu().actions()[4].trigger()
    assert lista.lista.count() == 2 and panel.valores["t_tipo"] == "simetria" and "Simetría" in lista.lista.item(1).text()
    panel._calcular_previa()
    assert panel.ultima_op is None and "Transformación 2" in panel.mensaje.text() and "plano" in panel.mensaje.text()
    QTest.keyClick(lista.lista, Qt.Key_Up)                              # volver a la 1.ª: la 2.ª sigue incompleta
    assert panel.valores["_sel"] == 0 and panel.valores["t_tipo"] == "rectangular" and panel.valores["t_n1"] == 3
    panel._calcular_previa()
    assert panel.ultima_op is None and "Falta completar la transformación 2" in panel.mensaje.text()
    QTest.keyClick(lista.lista, Qt.Key_Down)
    assert panel.valores["_sel"] == 1 and panel.valores["t_tipo"] == "simetria"
    panel.set_valor("t_plano", [_hit(doc, {"tipo": "plano", "id": "YZ"})])
    panel._calcular_previa()
    assert panel._previa_ok and [t["tipo"] for t in panel.ultima_op.p["transformaciones"]] == ["rectangular", "simetria"]
    assert "2 de 2" in panel.widgets["etapa"].text()
    # reordenar con el botón ▲: la simetría pasa primero (el orden de composición cambia)
    QTest.mouseClick(lista.subir, Qt.LeftButton)
    panel._calcular_previa()
    assert [t["tipo"] for t in panel.ultima_op.p["transformaciones"]] == ["simetria", "rectangular"]
    assert lista.lista.currentRow() == 0 and panel.valores["t_tipo"] == "simetria"
    QTest.mouseClick(lista.quitar, Qt.LeftButton)
    assert lista.lista.count() == 1 and panel.valores["t_tipo"] == "rectangular" and panel.valores["t_n1"] == 3
    assert not lista.quitar.isEnabled()                                  # siempre queda al menos una
    panel.cancelar()
    assert len(doc.operaciones) == 1


def test_multitransformar_abrir_y_aceptar_sin_tocar_conserva_simetria_y_supresion(app_qt):  # noqa: F811
    from omnicad.timeline.ops_solido import OpMultitransformar
    from omnicad.ui.comando import PanelComando
    from omnicad.ui.comandos.patrones import Multitransformar
    from omnicad.ui.visor3d import Visor3D
    doc = _doc_caja()
    t1 = {"tipo": "rectangular", "dir1": EJE_X, "n1": 2, "d1": "40 mm", "dir2": EJE_Y, "n2": 2, "d2": "40 mm",
          "distribucion": "espaciado", "simetrico": True, "simetrico2": False, "suprimir": [[1, 1], 2]}
    t2 = {"tipo": "circular", "eje": EJE_Z, "n": 2, "distribucion": "espaciado", "angulo": "180 deg", "simetrico": False,
          "suprimir": [1]}
    op = OpMultitransformar(doc.nuevo_id(), cuerpos=["op1.c1"], transformaciones=[t1, t2])
    assert doc.agregar(op).estado in ("ok", "aviso")
    antes = sorted(cid for cid in doc.estado_final.cuerpos)
    volumenes = sorted(round(g.volumen(c.forma), 6) for c in doc.estado_final.cuerpos.values())
    visor = Visor3D()
    visor.resize(800, 600)
    ctx = ContextoComando(doc, op=op)
    visor.set_modelo(ctx.estado)
    panel = PanelComando(Multitransformar(), ctx, visor)
    panel._calcular_previa()
    nueva = panel.ultima_op
    assert panel._previa_ok and nueva is not None
    assert nueva.p["transformaciones"][0]["suprimir"] == [[1, 1], [2, 0]] and nueva.p["transformaciones"][0]["simetrico"] is True
    assert nueva.p["transformaciones"][0]["simetrico2"] is False and nueva.p["transformaciones"][1]["suprimir"] == [1]
    panel.aceptar()
    doc.reemplazar(op.id, nueva)
    assert sorted(doc.estado_final.cuerpos) == antes
    assert sorted(round(g.volumen(c.forma), 6) for c in doc.estado_final.cuerpos.values()) == volumenes


# ---------------------------------------------------------------- compatibilidad y límites
@pytest.mark.parametrize("clave, params", [
    ("patron_rectangular_3d", {"forma_patron": "rectangular", "dir1": EJE_X, "n1": 3, "d1": "60 mm", "n2": 4, "d2": "30 mm",
                               "simetrico": True, "suprimir": [1]}),          # n2 sin dir2: nunca se aplicó
    ("patron_rectangular_3d", {"forma_patron": "rectangular", "dir1": EJE_X, "n1": 2, "d1": "30 mm", "dir2": EJE_Y, "n2": 2,
                               "d2": "30 mm", "distribucion": "espaciado", "simetrico": True, "suprimir": [[1, 1]]}),
    ("patron_circular_3d", {"forma_patron": "circular", "eje": EJE_Z, "n": 3, "angulo": "90 deg", "distribucion": "extension",
                            "simetrico": True}),
    ("patron_circular_3d", {"forma_patron": "circular", "eje": EJE_Z, "n": 3, "angulo": "30 deg", "distribucion": "espaciado",
                            "simetrico": True, "suprimir": [-1]}),
    ("patron_circular_3d", {"forma_patron": "circular", "eje": EJE_Z, "n": 5, "angulo": "360 deg", "distribucion": "extension"}),
    ("patron_ruta", {"forma_patron": "ruta", "n1": 3, "d1": "10 mm", "distribucion": "espaciado", "inicio": "0.5",
                     "simetrico": True, "orientacion": "direccion_ruta", "giro": "30 deg", "suprimir": [1]}),
])
def test_abrir_y_aceptar_un_patron_viejo_da_el_mismo_resultado(app_qt, clave, params):  # noqa: F811
    from omnicad.timeline.ops_solido import OpPatron
    doc, ruta = _doc_ruta([(0, 0), (40, 0)])
    if params["forma_patron"] == "ruta":
        params = dict(params, ruta=[h["ref"] for h in ruta])
    viejo = OpPatron(doc.nuevo_id(), cuerpos=["op1.c1"], **params)
    assert doc.agregar(viejo).estado in ("ok", "aviso")
    antes = _esquinas(doc.estado_final, viejo.id)
    cmd = CATALOGO[clave]()
    ctx = ContextoComando(doc, op=viejo)
    nueva = cmd.construir(cmd.desde_op(viejo, ctx), ctx)
    esperado = [(x if isinstance(x, list) else [x, 0]) if params["forma_patron"] == "rectangular" else x
                for x in params.get("suprimir", [])]
    assert nueva.p["suprimir"] == esperado
    doc.reemplazar(viejo.id, nueva)
    assert _esquinas(doc.estado_final, viejo.id) == antes and len(antes) > 1


def test_el_limite_de_instancias_se_explica_y_no_cuelga_el_panel(app_qt):  # noqa: F811
    panel, _v, _e, _d = _abrir("patron_rectangular_3d", valores={
        "dir1": [_hit(_doc_caja(), EJE_X)], "n1": 200, "d1": "30 mm", "n2": 100, "d2": "30 mm", "distribucion": "espaciado"})
    panel._calcular_previa()
    assert not panel._previa_ok and "10.000" in panel.mensaje.text()
    _teclear(panel.widgets["n1"], "3")
    _teclear(panel.widgets["n2"], "2")
    panel._calcular_previa()
    assert panel._previa_ok and not panel.mensaje.text().startswith("⚠")
    panel.cancelar()


# ---------------------------------------------------------------- PAT-2 a PAT-5
def test_pat2_el_punto_de_inicio_va_en_porcentaje_y_la_receta_sigue_en_fraccion(app_qt):  # noqa: F811
    from omnicad.ui.comandos.crear import fraccion_a_porcentaje, porcentaje_a_fraccion, valores_patron
    assert fraccion_a_porcentaje("0.5") == "50" and fraccion_a_porcentaje(0.125) == "12.5" and fraccion_a_porcentaje("") == "0"
    assert porcentaje_a_fraccion("12,5") == "0.125" and porcentaje_a_fraccion("100") == "1" and porcentaje_a_fraccion("") == "0"
    assert fraccion_a_porcentaje("k") == "(k)*100" and porcentaje_a_fraccion("k") == "(k)/100"          # una expresión vieja
    doc, ruta = _doc_ruta([(0, 0), (20, 0)])
    assert valores_patron({"forma_patron": "ruta", "inicio": "0.4"}, doc.estado_final)["inicio"] == "40"
    panel, visor, _estados, _d = _abrir("patron_ruta", doc, {"ruta": ruta, "rn": 2, "rd": "5 mm", "distribucion": "espaciado"})
    _teclear(panel.widgets["inicio"], "25")                              # 25 % de una ruta de 20 mm
    panel._calcular_previa()
    assert panel.ultima_op.p["inicio"] == "0.25"
    gm = panel.manipuladores
    assert _manip(panel, mp.AsaRuta, "inicio").asa(gm) == pytest.approx([5, 0, 0], abs=1e-6)
    xy, ok = gm.pantalla([[5, 0, 0], [15, 0, 0]])                         # se arrastra el disco con el ratón hasta el 75 %
    assert ok.all()
    _arrastrar(visor, *xy)
    assert float(panel.valores["inicio"]) == pytest.approx(75, abs=4)
    panel._calcular_previa()
    assert float(panel.ultima_op.p["inicio"]) == pytest.approx(0.75, abs=0.04)
    panel.cancelar()


def test_pat3_las_copias_suprimidas_se_ven_como_silueta_roja(app_qt):  # noqa: F811
    from omnicad.ui.comandos.asas_patron import ROJO_FANTASMA
    panel, _v, _e, _d = _abrir("patron_rectangular_3d", valores={
        "dir1": [_hit(_doc_caja(), EJE_X)], "n1": 3, "d1": "30 mm", "distribucion": "espaciado", "suprimir": "1:0"})
    panel._calcular_previa()
    prims = panel.comando.previa_vista(panel.ctx, panel.valores, panel.ultima_op)
    assert len(prims) == 1 and prims[0][0] == "lineas" and prims[0][2] == ROJO_FANTASMA
    x = prims[0][1][:, 0]
    assert x.min() == pytest.approx(30.0, abs=1e-3) and x.max() == pytest.approx(50.0, abs=1e-3)    # la copia del paso 1
    panel.set_valor("suprimir", "")
    panel._calcular_previa()
    assert not panel.comando.previa_vista(panel.ctx, panel.valores, panel.ultima_op)
    panel.cancelar()


def test_pat3_las_casillas_tambien_sirven_con_caras_y_con_geometria_de_construccion(app_qt):  # noqa: F811
    from omnicad.nucleo import referencias as refs
    doc = _doc_caja()
    forma = doc.estado_final.cuerpos["op1.c1"].forma
    cara = next(s for s in refs.subformas(forma, "cara") if refs.firma_cara(s)["geom"] == "plano")
    for objeto, valores in (("caras", {"caras": [_hit(doc, refs.referencia("op1.c1", cara, forma))]}),
                            ("construccion", {"construccion": [_hit(doc, {"tipo": "plano", "id": "XY"})]})):
        panel, visor, _e, _d = _abrir("patron_rectangular_3d", doc, {
            "objeto": objeto, "dir1": [_hit(doc, EJE_X)], "n1": 3, "d1": "30 mm", "distribucion": "espaciado", **valores})
        _marcar(panel.widgets["ver_casillas"])
        casillas = _manip(panel, mp.CasillasCopias)
        assert len(casillas.items) == 3 and casillas.originales == {(0, 0)}, objeto
        punto = next(p for ident, p, _x in casillas.items if ident == (1, 0))
        xy, ok = panel.manipuladores.pantalla([punto])
        assert ok.all()
        _clic(visor, xy[0])                                                # clic real sobre la casilla de la copia 1
        assert panel.valores["suprimir"] == "1:0", objeto
        panel._calcular_previa()
        assert panel._previa_ok and panel.ultima_op.p["suprimir"] == [[1, 0]], objeto
        panel.cancelar()


def _panel_multi(doc):
    from omnicad.ui.comandos.patrones import Multitransformar
    panel, visor, estados = _panel(Multitransformar(), doc, {"cuerpos": [_hit(doc, {"tipo": "cuerpo", "cuerpo": "op1.c1"})]})
    visor.vista("iso")
    return panel, visor, estados


def test_pat4_la_multitransformacion_muestra_las_copias_hasta_la_etapa_y_las_asas_de_la_elegida(app_qt):  # noqa: F811
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from omnicad.ui.comandos.asas_patron import AZUL_DESTINO
    doc = _doc_caja()
    panel, _visor, _estados = _panel_multi(doc)
    lista = panel.widgets["lista"]
    panel.set_valor("t_dir1", [_hit(doc, EJE_X)])
    panel.set_valor("t_distribucion", "espaciado")
    _teclear(panel.widgets["t_n1"], "3")
    _teclear(panel.widgets["t_d1"], "30 mm")
    lista.agregar.menu().actions()[4].trigger()                            # 2.ª transformación: una simetría
    panel.set_valor("t_plano", [_hit(doc, {"tipo": "plano", "id": "YZ"})])
    panel._calcular_previa()
    assert panel._previa_ok
    assert not panel.comando.previa_vista(panel.ctx, panel.valores, panel.ultima_op)    # la última etapa es todo el resultado
    QTest.keyClick(lista.lista, Qt.Key_Up)                                 # se elige la 1.ª: el patrón de 3
    panel._calcular_previa()
    assert "Hasta esta etapa quedan 3 instancias" in panel.widgets["etapa"].text()
    prims = panel.comando.previa_vista(panel.ctx, panel.valores, panel.ultima_op)
    assert len(prims) == 2 and all(p[2] == AZUL_DESTINO for p in prims)     # las dos copias del patrón, sin las espejadas
    assert sorted(round(float(p[1][:, 0].min()), 3) for p in prims) == [30.0, 60.0]
    # las asas son las de la transformación elegida y escriben en sus campos (t_…)
    panel.manipuladores.actualizar()
    _arrastrar_asa_n(panel, "t_n1", 1)                                     # una copia más: la cantidad pasa a 4
    assert panel.valores["t_n1"] == 4
    panel._calcular_previa()
    assert panel.ultima_op.p["transformaciones"][0]["n1"] == 4
    QTest.keyClick(lista.lista, Qt.Key_Down)                               # la simetría no tiene asas
    assert not [m for m in panel.manipuladores.manips if getattr(m, "clave", "").startswith("t_")]
    panel.cancelar()


def test_pat5_la_direccion_2_derivada_se_puede_llevar_a_un_plano_de_referencia(app_qt):  # noqa: F811
    doc = _doc_caja()
    base = {"dir1": [_hit(doc, EJE_X)], "n1": 2, "d1": "30 mm", "n2": 2, "d2": "25 mm", "distribucion": "espaciado"}
    panel, _v, estados, _d = _abrir("patron_rectangular_3d", doc, base)
    assert panel._visible(next(c for c in panel.campos if c.clave == "plano_dir2"))
    panel._calcular_previa()
    assert _esquinas(estados[-1], panel.ultima_op.id) == [(x, y, 0.0) for x in (0.0, 30.0) for y in (0.0, 25.0)]
    panel.set_valor("plano_dir2", [_hit(doc, {"tipo": "plano", "id": "XZ"})])        # la 2 queda dentro del plano XZ
    panel._calcular_previa()
    assert panel._previa_ok and "dentro del plano elegido" in panel.widgets["info_dir2"].text()
    assert _esquinas(estados[-1], panel.ultima_op.id) == [(x, 0.0, z) for x in (0.0, 30.0) for z in (0.0, 25.0)]
    assert panel.ultima_op.p["plano_dir2"] == {"tipo": "plano", "id": "XZ"}
    flecha = _manip(panel, mp.Flecha, "d2")
    assert np.allclose(flecha.direccion, (0, 0, 1))                                  # la flecha verde sigue a la elegida
    # un plano perpendicular a la dirección 1 no define nada: el panel lo dice y la vista previa no se calcula
    panel.set_valor("plano_dir2", [_hit(doc, {"tipo": "plano", "id": "YZ"})])
    panel._calcular_previa()
    assert "perpendicular al plano" in panel.widgets["info_dir2"].text() and not panel._previa_ok
    # elegir una dirección 2 explícita oculta el campo del plano
    panel.set_valor("dir2", [_hit(doc, EJE_Y)])
    assert not panel._visible(next(c for c in panel.campos if c.clave == "plano_dir2"))
    panel.cancelar()
