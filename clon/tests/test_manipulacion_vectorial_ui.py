# -*- coding: utf-8 -*-
"""Regresiones de interacción: el mismo clic selecciona y permite transformar el recurso completo."""
import math

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.restricciones import Boceto
from omnicad.restricciones import objetos as ob
from omnicad.timeline.parametros import TablaParametros
from omnicad.ui.editor_boceto import Lienzo
from omnicad.ui.objetos_vectoriales import PanelObjetos


def raton(widget, tipo, pos, mods=Qt.NoModifier):
    QApplication.sendEvent(widget, QMouseEvent(tipo, QPointF(pos), widget.mapToGlobal(QPointF(pos)),
        Qt.NoButton if tipo == QEvent.MouseMove else Qt.LeftButton,
        Qt.NoButton if tipo == QEvent.MouseButtonRelease else Qt.LeftButton, mods))


def arrastrar(lz, inicio, fin, mods=Qt.NoModifier):
    raton(lz, QEvent.MouseButtonPress, inicio, mods)
    raton(lz, QEvent.MouseMove, fin, mods)
    raton(lz, QEvent.MouseButtonRelease, fin, mods)


def teclear(campo, texto, tecla=Qt.Key_Return):
    campo.setFocus()
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    QTest.keyClick(campo, tecla)


@pytest.fixture
def editor():
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    oid = ob.crear(b, b.agregar_rectangulo((10, 10), (50, 30)), "Logo")
    lz = Lienzo(b, TablaParametros().evaluar)
    lz.resize(1100, 700)
    lz.ajustar_grilla = lz.objetos.snap = False
    panel = PanelObjetos(lz.objetos, lz)
    panel.move(780, 0)
    lz.show()
    app.processEvents()
    QTest.mouseClick(lz, Qt.LeftButton, pos=lz.a_px(20, 15).toPoint())
    app.processEvents()
    yield lz, panel, oid
    lz.close()
    lz.deleteLater()
    app.processEvents()


def test_arrastrar_desde_el_centro_mueve_y_no_cambia_el_pivote(editor):
    lz, _panel, oid = editor
    arrastrar(lz, lz.a_px(30, 20), lz.a_px(60, 40))
    assert ob.caja(lz.b, [oid]) == pytest.approx((40, 30, 80, 50))
    assert lz.b.objetos[oid]["pivote"] is None
    assert lz.seleccion == [oid] and len(lz.historial) == 1


@pytest.mark.parametrize("asa", range(8))
def test_cada_tirador_respeta_la_casilla_de_proporciones(editor, asa):
    lz, _panel, oid = editor
    inicio = lz.objetos.manijas()[f"escala{asa}"]
    mm = lz.a_mm(inicio)
    centro = (30, 20)
    destino = lz.a_px(*(np.asarray(centro) + 1.5 * (np.asarray(mm) - centro)))
    arrastrar(lz, inicio, destino)
    x0, y0, x1, y1 = ob.caja(lz.b, [oid])
    assert (x1 - x0) / (y1 - y0) == pytest.approx(2)
    assert x1 - x0 > 40


def test_escape_en_campo_descarta_previa_y_no_aplica_al_cambiar_foco(editor):
    lz, panel, _oid = editor
    antes = lz.b.a_dict()
    teclear(panel.campos["ancho"], "73 mm", Qt.Key_Escape)
    QTest.mouseClick(panel.nombre, Qt.LeftButton)
    assert lz.b.a_dict() == antes
    assert lz.objetos.previa is None and not panel.campos["ancho"].isModified()
    assert not lz.historial


def test_perfiles_no_compiten_y_volver_recupera_la_seleccion(editor):
    lz, panel, oid = editor
    QTest.mouseClick(panel.perfiles, Qt.LeftButton, pos=QPoint(8, panel.perfiles.height() // 2))
    QTest.mouseClick(lz, Qt.LeftButton, pos=lz.a_px(20, 15).toPoint())
    assert lz.perfiles_sel == [0] and not lz.seleccion
    QTest.mouseClick(panel.perfiles, Qt.LeftButton, pos=QPoint(8, panel.perfiles.height() // 2))
    assert lz.seleccion == [oid] and not lz.perfiles_sel
    assert len(lz.objetos.manijas()) == 10


def test_deshacer_rehacer_conservan_objeto_y_panel(editor):
    lz, panel, oid = editor
    teclear(panel.campos["x"], "25 mm")
    lz.deshacer()
    assert lz.seleccion == [oid] and panel.campos["x"].isEnabled()
    lz.rehacer()
    assert lz.seleccion == [oid] and ob.caja(lz.b, [oid])[0] == pytest.approx(25)


def test_giro_desde_manija_confirmado_y_cancelado(editor):
    lz, _panel, oid = editor
    antes = lz.b.a_dict()
    inicio = lz.objetos.manijas()["rotar"]
    p = np.asarray(lz.objetos.pivote())
    u = np.asarray(lz.a_mm(inicio)) - p
    a = math.radians(30)
    fin = lz.a_px(*(p + np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]) @ u))
    raton(lz, QEvent.MouseButtonPress, inicio)
    raton(lz, QEvent.MouseMove, fin)
    assert lz.b.a_dict() == antes
    QTest.keyClick(lz, Qt.Key_Escape)
    raton(lz, QEvent.MouseButtonRelease, fin)
    assert lz.b.a_dict() == antes
    arrastrar(lz, inicio, fin)
    assert lz.objetos.estado()["angulo"] == pytest.approx(30)
    assert lz.seleccion == [oid] and len(lz.historial) == 1


@pytest.fixture
def ventana_vectorial(tmp_path):
    from PySide6.QtCore import QSettings
    from omnicad import api
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpBoceto
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    b = Boceto()
    oid = ob.crear(b, b.agregar_rectangulo((10, 10), (50, 30)), "Logo")
    doc = Documento()
    doc.agregar(OpBoceto("logo", "Logo", boceto=b, plano="XY"))
    s = api.Sesion(doc)
    v = VentanaPrincipal(doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    app.processEvents()
    v.visor.vista("arriba")
    v.visor.encuadrar()
    app.processEvents()
    yield v, s, oid
    if v.panel is not None:
        v.panel.cancelar()
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def test_un_clic_y_un_arrastre_en_el_visor_sin_abrir_boceto(ventana_vectorial):
    v, _s, oid = ventana_vectorial
    inicio = v.visor.proyectar(np.array([20, 15, 0.0]))
    raton(v.visor, QEvent.MouseButtonPress, inicio)
    assert not v.modo_boceto.activo
    gestor = getattr(v, "vectores", None)
    assert gestor is not None and gestor.activo is not None
    lz = gestor.activo
    assert lz.objetos.seleccion() == [oid] and len(lz.objetos.manijas()) == 10
    antes = v.doc.a_dict()
    lz.objetos.snap = False
    destino = v.visor.proyectar(np.array([40, 30, 0.0]))
    raton(v.visor, QEvent.MouseMove, destino)
    assert v.doc.a_dict() == antes
    n = len(v.doc._deshacer)
    raton(v.visor, QEvent.MouseButtonRelease, destino)
    b = v.doc.estado_final.bocetos["logo"].boceto
    assert ob.caja(b, [oid]) == pytest.approx((30, 25, 70, 45))
    assert len(v.doc._deshacer) == n + 1
    assert lz.objetos.seleccion() == [oid]
    v._deshacer()
    assert ob.caja(v.doc.estado_final.bocetos["logo"].boceto, [oid]) == pytest.approx((10, 10, 50, 30))


@pytest.mark.parametrize("ancho,alto", [(1024, 640), (800, 520)])
def test_encuadrar_deja_las_diez_manijas_fuera_de_las_tarjetas(ventana_vectorial, ancho, alto):
    v, _s, oid = ventana_vectorial
    v.editar_operacion("logo")
    v.resize(ancho, alto)
    lz = v.modo_boceto.lienzo
    lz.seleccion = [oid]
    lz._notificar_seleccion()
    QApplication.processEvents()
    v.acciones["ajustar"].trigger()
    QApplication.processEvents()
    panel = v.modo_boceto.objetos
    assert v.width() == ancho
    for q in lz.objetos.manijas().values():
        assert lz.rect().contains(q.toPoint())
        assert not panel.geometry().contains(q.toPoint())
        assert not v.navegador.geometry().contains(q.toPoint())
    terminar = v.modo_boceto.paleta.b_terminar
    assert not panel.geometry().contains(terminar.mapTo(v.area, terminar.rect().center()))


def test_un_mensaje_largo_no_impide_una_ventana_real_de_800_pixeles(ventana_vectorial):
    v, _s, _oid = ventana_vectorial
    texto = "Arrastrá el objeto; Mayús restringe el eje, Ctrl suspende las guías y Esc cancela. " * 8
    v.mensaje(texto)
    v.resize(800, 520)
    QApplication.processEvents()
    assert v.width() == 800 and v.height() == 520
    assert v.timeline.estado.toolTip() == texto


def test_transformar_despues_de_extruir_recalcula_el_solido(ventana_vectorial):
    from omnicad import api
    from omnicad.nucleo import geometria as geo
    v, s, oid = ventana_vectorial
    assert api.llamar(s, "extrude", {"sketch": "logo", "profile": f"object:{oid}", "distance": 3})["ok"]
    # El objeto se elige en el navegador incluso si su sólido tapa el dibujo.
    gestor = getattr(v, "vectores", None)
    assert gestor is not None
    gestor.seleccionar("logo", [oid])
    panel = gestor.activo.objetos.panel
    teclear(panel.campos["ancho"], "80 mm")
    cuerpo = next(iter(v.doc.estado_final.cuerpos.values()))
    assert geo.volumen(cuerpo.forma) == pytest.approx(9600)
    assert geo.es_valida(cuerpo.forma) and all(r.estado != "error" for r in v.doc.resultados)


def test_panel_contextual_compacto_vacio_bloqueado_y_texto(editor):
    lz, panel, oid = editor
    assert not panel.avanzadas.abierta
    assert all(panel.campos[k].isVisible() for k in ("x", "y", "ancho", "alto", "angulo"))
    assert all(not panel.campos[k].isVisible() for k in ("sx", "sy", "px", "py"))
    assert not panel.texto.isVisible() and not panel.botones["Convertir texto"].isVisible()
    assert not panel.botones["Agrupar"].isEnabled() and panel.botones["Agrupar"].toolTip()
    QTest.mouseClick(panel.botones["Bloquear"], Qt.LeftButton)
    assert lz.b.objetos[oid]["bloqueado"] and not panel.campos["x"].isEnabled()
    assert "desbloque" in panel.indicacion.text().lower()
    QTest.mouseClick(panel.botones["Bloquear"], Qt.LeftButton)
    assert not lz.b.objetos[oid]["bloqueado"] and panel.campos["x"].isEnabled()
    lz.seleccion = []
    lz._notificar_seleccion()
    assert "Seleccioná un vector" in panel.indicacion.text() and not panel.principal.isVisible()


@pytest.mark.parametrize("clave,texto,esperado", [
    ("x", "-12,5 mm", -12.5), ("y", "2 cm", 20), ("ancho", "20 mm + 40 mm", 60),
    ("alto", "15.25 mm", 15.25), ("angulo", "90 deg", 90), ("sx", "1.5", 1.5),
    ("sy", "2", 2), ("px", "-5 mm", -5), ("py", "7.5 mm", 7.5)])
def test_cada_campo_se_teclea_aplica_y_se_deshace(editor, clave, texto, esperado):
    lz, panel, oid = editor
    if clave in ("sx", "sy", "px", "py"):
        QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
        panel.desplazador.ensureWidgetVisible(panel.campos[clave])
    antes = lz.b.a_dict()
    teclear(panel.campos[clave], texto, Qt.Key_Tab)
    assert lz.objetos.estado()[clave] == pytest.approx(esperado)
    assert len(lz.historial) == 1 and lz.seleccion == [oid]
    lz.deshacer()
    assert lz.b.a_dict() == antes
    lz.rehacer()
    assert lz.objetos.estado()[clave] == pytest.approx(esperado)


@pytest.mark.parametrize("clave,texto", [("ancho", ""), ("alto", "0"), ("ancho", "-3"),
    ("sx", "nan"), ("x", "1e20 mm"), ("ancho", "1e9 mm"), ("angulo", "abc")])
def test_valores_invalidos_no_dejan_una_previa_ni_modifican(editor, clave, texto):
    lz, panel, _oid = editor
    antes = lz.b.a_dict()
    campo = panel.campos[clave]
    if clave == "sx":
        QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
    campo.setFocus()
    campo.selectAll()
    QTest.keyClick(campo, Qt.Key_Backspace)
    QTest.keyClicks(campo, texto)
    QTest.keyClick(campo, Qt.Key_Return)
    assert panel.error.text()
    assert lz.b.a_dict() == antes and lz.objetos.previa is None
    QTest.keyClick(campo, Qt.Key_Escape)
    assert not campo.isModified()


def test_centrar_restaurar_duplicar_agrupar_y_desagrupar(editor):
    lz, panel, oid = editor
    curvas = set(lz.b.curvas)
    QTest.mouseClick(panel.botones["Centrar"], Qt.LeftButton)
    assert ob.caja(lz.b, [oid]) == pytest.approx((-20, -10, 20, 10))
    QTest.mouseClick(panel.botones["Restablecer"], Qt.LeftButton)
    assert ob.caja(lz.b, [oid]) == pytest.approx((10, 10, 50, 30)) and set(lz.b.curvas) == curvas
    QTest.mouseClick(panel.botones["Duplicar"], Qt.LeftButton)
    copia = lz.objetos.seleccion()[0]
    assert copia != oid and len(ob.raices(lz.b)) == 2
    QTest.mouseClick(lz, Qt.LeftButton, pos=lz.a_px(15, 15).toPoint())
    QTest.mouseClick(lz, Qt.LeftButton, Qt.ControlModifier, lz.a_px(55, 15).toPoint())
    assert set(lz.objetos.seleccion()) == {oid, copia}
    QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
    QTest.mouseClick(panel.organizar.boton, Qt.LeftButton)
    panel.desplazador.ensureWidgetVisible(panel.botones["Agrupar"])
    QTest.mouseClick(panel.botones["Agrupar"], Qt.LeftButton)
    grupo = lz.objetos.seleccion()[0]
    assert ob.raices(lz.b) == [grupo]
    QTest.mouseClick(panel.botones["Desagrupar"], Qt.LeftButton)
    assert set(ob.raices(lz.b)) == {oid, copia}


def test_pivote_contextual_no_modifica_contornos(editor):
    lz, panel, oid = editor
    antes = lz.b.geometria()
    QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
    panel.desplazador.ensureWidgetVisible(panel.pivote_manual)
    QTest.mouseClick(panel.pivote_manual, Qt.LeftButton, pos=QPoint(8, panel.pivote_manual.height() // 2))
    arrastrar(lz, lz.objetos.manijas()["pivote"], lz.a_px(0, 0))
    assert ob.pivote(lz.b, oid) == pytest.approx((0, 0)) and lz.b.geometria() == antes


def test_formula_tecleada_sigue_al_parametro_y_a_la_extrusion(ventana_vectorial):
    from omnicad import api
    from omnicad.nucleo import geometria as geo
    v, s, oid = ventana_vectorial
    assert api.llamar(s, "create_parameter", {"name": "ancho_logo", "expression": "60 mm"})["ok"]
    assert api.llamar(s, "extrude", {"sketch": "logo", "profile": f"object:{oid}", "distance": 3})["ok"]
    v.vectores.seleccionar("logo", [oid])
    teclear(v.vectores.activo.objetos.panel.campos["ancho"], "ancho_logo")
    assert ob.expresiones(v.doc.operaciones[0].boceto)
    r = api.llamar(s, "set_parameter", {"name": "ancho_logo", "expression": "80 mm"})
    assert r["ok"], r
    cuerpo = next(iter(v.doc.estado_final.cuerpos.values()))
    assert geo.volumen(cuerpo.forma) == pytest.approx(9600) and geo.es_valida(cuerpo.forma)
    v.editar_operacion("logo")
    lz = v.modo_boceto.lienzo
    lz.seleccion = [oid]
    assert lz.objetos.estado()["ancho"] == pytest.approx(80)


@pytest.mark.parametrize("clave,expresion,nueva,esperado", [
    ("x", "12 mm", "32 mm", 32), ("y", "14 mm", "30 mm", 30),
    ("angulo", "22 deg", "45 deg", 45), ("sx", "1.5", "2", 2), ("sy", "1.5", "2", 2)])
def test_formula_de_campo_se_conserva_incluso_con_escala_local_girada(ventana_vectorial, clave, expresion, nueva, esperado):
    from omnicad import api
    v, s, oid = ventana_vectorial
    if clave in ("sx", "sy"):
        assert api.llamar(s, "transform_vector_objects", {"sketch": "logo", "objects": [oid], "angle": 30})["ok"]
        assert api.llamar(s, "set_vector_object", {"sketch": "logo", "object": oid, "keep_proportions": False})["ok"]
    assert api.llamar(s, "create_parameter", {"name": "medida_logo", "expression": expresion,
        "kind": "scalar" if clave in ("sx", "sy") else "auto"})["ok"]
    v.vectores.seleccionar("logo", [oid])
    lz = v.vectores.activo
    panel = lz.objetos.panel
    if clave in ("sx", "sy"):
        QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
    teclear(panel.campos[clave], "medida_logo")
    assert not panel.error.text(), panel.error.text()
    r = api.llamar(s, "set_parameter", {"name": "medida_logo", "expression": nueva})
    assert r["ok"], r
    assert lz.objetos.estado()[clave] == pytest.approx(esperado)


def test_seleccion_api_en_vivo_usa_el_mismo_control_del_visor(ventana_vectorial):
    from types import SimpleNamespace
    from omnicad import api
    from omnicad.ui.puente import PuenteAgentes
    v, s, oid = ventana_vectorial
    puente = SimpleNamespace(ventana=v, sesion=s)
    s.seleccionar_objetos_vectoriales = lambda ids, modo, sketch: PuenteAgentes._seleccionar_objetos_vectoriales(puente, ids, modo, sketch)
    r = api.llamar(s, "select_vector_objects", {"objects": [oid], "sketch": "logo"})
    assert r["ok"] and r["result"]["count"] == 1
    assert v.vectores.activo.objetos.seleccion() == [oid]


def test_insertar_en_boceto_permite_arrastrar_antes_de_aceptar(ventana_vectorial, tmp_path, monkeypatch):
    from omnicad.ui import manipuladores as mp
    from omnicad.ui.comandos.insertar import InsertarSVG
    from omnicad.io_archivos import boceto_archivos
    v, _s, _oid = ventana_vectorial
    ruta = tmp_path / "antes_de_aceptar.svg"
    ruta.write_text('<svg width="100mm" height="100mm" viewBox="0 0 100 100">'
                    '<rect x="10" y="10" width="10" height="10"/></svg>', encoding="utf-8")
    v.editar_operacion("logo")
    lz = v.modo_boceto.lienzo
    antes = lz.b.a_dict()
    p = v.ejecutar_comando(InsertarSVG(), valores={"archivo": str(ruta)})
    QApplication.processEvents()
    g = p.manipuladores
    assert len(g.manips) == 7
    assert lz.testAttribute(Qt.WA_TransparentForMouseEvents)
    m = next(m for m in g.manips if isinstance(m, mp.PosicionCalcomania))
    muestras = p.comando.segmentos_previa(p.valores, p.ctx)
    llamadas = []
    construir = boceto_archivos.boceto_desde_primitivas
    def contar(*args, **kwargs):
        llamadas.append(True)
        return construir(*args, **kwargs)
    monkeypatch.setattr(boceto_archivos, "boceto_desde_primitivas", contar)
    xy, ok = g.pantalla([m.punto, m.punto + m.u * 6 - m.v * 4])
    assert ok.all()
    arrastrar(v.visor, QPointF(*xy[0]), QPointF(*xy[1]))
    p._calcular_previa_ahora()
    assert (g.valor("dx"), g.valor("dy")) == pytest.approx((6, -4), abs=.3)
    assert lz.b.a_dict() == antes
    assert llamadas == []
    nuevas = p.comando.segmentos_previa(p.valores, p.ctx)
    assert np.mean(nuevas - muestras, axis=0) == pytest.approx([6, -4, 0], abs=.3)
    QTest.mouseClick(p.boton_ok, Qt.LeftButton)
    assert v.panel is None and not lz.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert len(lz.historial) == 1 and len(ob.raices(lz.b)) == 2
    lz.deshacer()
    assert lz.b.a_dict() == antes


def test_campo_del_documento_anterior_no_modifica_el_nuevo(ventana_vectorial):
    from omnicad.timeline.documento import Documento
    v, _s, oid = ventana_vectorial
    v.vectores.seleccionar("logo", [oid])
    lz = v.vectores.activo
    campo = lz.objetos.panel.campos["ancho"]
    campo.setFocus()
    campo.selectAll()
    QTest.keyClicks(campo, "80 mm")
    nuevo = Documento()
    v.set_documento(nuevo)
    assert not lz.aplicar_cambio(lambda: ob.transformar(lz.b, [oid], ob.afin(10, 0)))
    assert nuevo.operaciones == [] and not nuevo.puede_deshacer()


def test_confirmacion_que_romperia_extrusion_revierte_documento_y_seleccion(ventana_vectorial):
    from omnicad import api
    v, s, oid = ventana_vectorial
    assert api.llamar(s, "extrude", {"sketch": "logo", "profile": f"object:{oid}", "distance": 3})["ok"]
    v.vectores.seleccionar("logo", [oid])
    lz = v.vectores.activo
    antes, n = v.doc.a_dict(), len(v.doc._deshacer)
    assert not lz.objetos.aplicar(lambda: [lz.b.eliminar(i) for i in ob.curvas(lz.b, [oid])])
    assert v.doc.a_dict() == antes and len(v.doc._deshacer) == n
    assert lz.objetos.seleccion() == [oid] and lz.objetos.panel.error.text()
    assert all(r.estado != "error" for r in v.doc.resultados)


def test_arrastre_cancelado_al_perder_ventana_restauracion_exacta(editor):
    lz, _panel, oid = editor
    antes = lz.b.a_dict()
    raton(lz, QEvent.MouseButtonPress, lz.a_px(20, 15))
    raton(lz, QEvent.MouseMove, lz.a_px(40, 25))
    QApplication.sendEvent(lz, QEvent(QEvent.WindowDeactivate))
    raton(lz, QEvent.MouseButtonRelease, lz.a_px(40, 25))
    assert lz.b.a_dict() == antes and not lz.historial and lz.seleccion == [oid]


def test_alinear_distribuir_visibilidad_y_validacion_desde_el_panel(editor):
    lz, panel, oid = editor
    nuevos = []
    lz.aplicar_cambio(lambda: nuevos.extend(ob.crear(lz.b, lz.b.agregar_rectangulo((x, y), (x + 20, y + 10)))
                       for x, y in ((80, 35), (140, 60))), anclar=False)
    lz.escala, lz.centro = 2, [60, 30]
    for n, xy in enumerate(((20, 15), (90, 40), (150, 65))):
        QTest.mouseClick(lz, Qt.LeftButton, Qt.ControlModifier if n else Qt.NoModifier, lz.a_px(*xy).toPoint())
    assert set(lz.objetos.seleccion()) == {oid, *nuevos}
    QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
    QTest.mouseClick(panel.organizar.boton, Qt.LeftButton)
    panel.alineacion.setFocus()
    QTest.keyClick(panel.alineacion, Qt.Key_Home)
    for _ in range(3):
        QTest.keyClick(panel.alineacion, Qt.Key_Down)  # Abajo
    QTest.mouseClick(panel.b_alinear, Qt.LeftButton)
    assert all(ob.caja(lz.b, [i])[1] == pytest.approx(10) for i in [oid, *nuevos])
    panel.alineacion.setFocus()
    QTest.keyClick(panel.alineacion, Qt.Key_End)
    QTest.keyClick(panel.alineacion, Qt.Key_Up)  # Distribuir horizontal
    panel.separacion.setFocus()
    QTest.keyClicks(panel.separacion, "5 mm")
    QTest.mouseClick(panel.b_alinear, Qt.LeftButton)
    cajas = sorted(ob.caja(lz.b, [i]) for i in [oid, *nuevos])
    assert [cajas[k + 1][0] - cajas[k][2] for k in (0, 1)] == pytest.approx([5, 5])
    QTest.mouseClick(panel.visible, Qt.LeftButton, pos=QPoint(8, panel.visible.height() // 2))
    assert all(not lz.b.objetos[i]["visible"] for i in [oid, *nuevos])
    lz.deshacer()
    assert all(lz.b.objetos[i]["visible"] for i in [oid, *nuevos])
    panel.desplazador.ensureWidgetVisible(panel.geometria.boton)
    QTest.mouseClick(panel.geometria.boton, Qt.LeftButton)
    QApplication.processEvents()
    panel.desplazador.ensureWidgetVisible(panel.botones["Validar"])
    assert panel.botones["Validar"].isEnabled()
    QTest.mouseClick(panel.botones["Validar"], Qt.LeftButton)
    assert panel.error.text() == "Perfiles válidos: 3"


def test_botones_de_geometria_y_selector_de_pivote_modifican_realmente(editor, tmp_path):
    from omnicad.io_archivos.svg import leer_svg
    from omnicad.io_archivos.boceto_archivos import boceto_desde_primitivas
    from omnicad.api.herramientas_objetos_vectoriales import regiones
    lz, panel, _oid = editor
    ruta = tmp_path / "colineales.svg"
    ruta.write_text('<svg width="100mm" height="100mm" viewBox="0 0 100 100">'
                    '<path d="M10 10H20H30V30H10Z"/></svg>', encoding="utf-8")
    lz.aplicar_cambio(lambda: boceto_desde_primitivas(leer_svg(ruta), destino=lz.b), anclar=False)
    lz.escala, lz.centro = 2, [50, 50]
    QTest.mouseClick(lz, Qt.LeftButton, pos=lz.a_px(15, 80).toPoint())
    oid = lz.objetos.seleccion()[0]
    QTest.mouseClick(panel.avanzadas.boton, Qt.LeftButton)
    panel.desplazador.ensureWidgetVisible(panel.pivotes)
    panel.pivotes.setFocus()
    QTest.keyClick(panel.pivotes, Qt.Key_Home)
    QTest.keyClick(panel.pivotes, Qt.Key_Down)
    QTest.keyClick(panel.pivotes, Qt.Key_Down)
    QTest.keyClick(panel.pivotes, Qt.Key_Return)
    assert ob.pivote(lz.b, oid) == pytest.approx((10, 70))
    QTest.mouseClick(panel.geometria.boton, Qt.LeftButton)
    panel.desplazador.ensureWidgetVisible(panel.botones["Simplificar"])
    QTest.mouseClick(panel.botones["Simplificar"], Qt.LeftButton)
    assert len(ob.curvas(lz.b, [oid])) == 4
    assert "1 trazos" in panel.error.text()
    panel.desplazador.ensureWidgetVisible(panel.desfase)
    panel.desfase.setFocus()
    panel.desfase.selectAll()
    QTest.keyClicks(panel.desfase, "2 mm")
    panel.esquinas.setFocus()
    QTest.keyClick(panel.esquinas, Qt.Key_End)
    panel.desplazador.ensureWidgetVisible(panel.b_desfasar)
    QTest.mouseClick(panel.b_desfasar, Qt.LeftButton)
    offset = lz.objetos.seleccion()[0]
    assert offset != oid and sum(p.area for p in regiones(lz.b, lz._plano_perfiles(), [offset])[1]) == pytest.approx(576)
    panel.desplazador.ensureWidgetVisible(panel.botones["Duplicar"])
    QTest.mouseClick(panel.botones["Duplicar"], Qt.LeftButton)
    copia = lz.objetos.seleccion()[0]
    QTest.mouseClick(lz, Qt.LeftButton, pos=lz.a_px(9, 69).toPoint())
    QTest.mouseClick(lz, Qt.LeftButton, Qt.ControlModifier, lz.a_px(41, 75).toPoint())
    assert set(lz.objetos.seleccion()) == {offset, copia}
    panel.desplazador.ensureWidgetVisible(panel.botones["Unir perfiles"])
    QTest.mouseClick(panel.botones["Unir perfiles"], Qt.LeftButton)
    unido = lz.objetos.seleccion()[0]
    assert unido not in (offset, copia)
    assert sum(p.area for p in regiones(lz.b, lz._plano_perfiles(), [unido])[1]) == pytest.approx(816)
