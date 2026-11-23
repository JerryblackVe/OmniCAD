# -*- coding: utf-8 -*-
"""FL-9: el trabajador de las previas arranca con la ventana, para que la primera previa no espere abrir el proceso."""
import time

import pytest
from _calculo_aparte import barra, esperar_barra
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QPushButton

from omnicad.nucleo import aislado
from omnicad.timeline.documento import Documento
from omnicad.ui import comando
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_la_ventana_precalienta_el_trabajador_si_la_previa_va_aparte(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(aislado, "precalentar", lambda receta, doc=None: llamadas.append(receta))
    app = QApplication.instance() or QApplication([])
    for aparte in (False, True):
        monkeypatch.setattr(comando, "PREVIA_APARTE", aparte)
        v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
        assert len(llamadas) == aparte        # con la previa en la ventana (las pruebas) no abre un proceso de más
    assert llamadas[0]["operaciones"] == []   # le pasa la receta del documento: lo arma antes de la primera previa


def test_el_trabajador_precalentado_importa_solo_y_no_cuenta_lo_que_espero_quieto():
    from omnicad import api
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})["ok"]
    aislado.cerrar_trabajador()
    aislado.precalentar(s.doc.a_dict())
    t = aislado._trabajador
    assert t is not None and t.proceso.poll() is None
    limite = time.monotonic() + 30
    while not (t.carpeta / "despierto").exists() and time.monotonic() < limite:
        time.sleep(0.05)
    assert (t.carpeta / "despierto").exists()     # ya importó OCP y el timeline, sin que nadie le pida nada
    time.sleep(1.5)                                # quieto, como mientras la persona abre un comando
    inicio = time.monotonic()
    salida = aislado.correr_json("recalcular_documento", {"receta": s.doc.a_dict()}, 60)
    pedido = time.monotonic() - inicio
    assert salida["pasos"] == 1 and aislado._trabajador is t       # esperó al precalentado: el mismo trabajador
    # el costo de uno nuevo es importar + el primer pedido; antes contaba también los 1,5 s de espera
    assert aislado.costo_reinicio() < time.time() - t.creado - 1.0
    assert aislado.costo_reinicio() >= pedido * 0.5


def test_un_precalentado_que_se_cuelga_se_corta_y_no_traba_las_previas(monkeypatch):
    """Un archivo cuyo recálculo cuelga el kernel (B-48) no deja al trabajador tomado para siempre: vence como una previa."""
    monkeypatch.setattr(aislado, "TOPE_PREVUELO_PARAMETROS", 0.05)
    monkeypatch.setattr(aislado._Trabajador, "_avisar", lambda self, tarea: None)      # nunca contesta
    aislado.cerrar_trabajador()
    aislado.precalentar(Documento().a_dict())
    proceso = aislado._trabajador.proceso
    assert aislado._previa_en_curso is not None
    fin = time.monotonic() + 5
    while proceso.poll() is None and time.monotonic() < fin:
        time.sleep(0.01)
    assert proceso.poll() is not None and aislado._previa_en_curso is None


def _pedido_perdido(monkeypatch, veces):
    """El aviso por la tubería se pierde `veces` veces, como en Windows (B-418): el trabajador despierta y no lo ve."""
    monkeypatch.setattr(aislado, "PLAZO_RECIBIR", 0.1)      # despierto, no lo toma enseguida: como el plazo real, más corto
    avisar, perdidos = aislado._Trabajador._avisar, []

    def avisar_a_veces(self, tarea):
        if len(perdidos) < veces:
            perdidos.append(tarea)
            return
        avisar(self, tarea)
    monkeypatch.setattr(aislado._Trabajador, "_avisar", avisar_a_veces)
    return perdidos


def _esperar(calculo, tope=60):
    limite = time.monotonic() + tope
    while time.monotonic() < limite:
        salida = calculo.sondear()
        if salida is not None:
            return salida
        time.sleep(0.02)
    raise AssertionError("la previa no llegó nunca")


def test_b418_un_pedido_que_no_llega_se_reintenta_con_otro_trabajador(monkeypatch):
    perdidos = _pedido_perdido(monkeypatch, 1)
    aislado.cerrar_trabajador()
    calculo = aislado.CalculoPendiente("recalcular_documento", {"receta": Documento().a_dict()})
    primero = calculo.trabajador.proceso
    assert _esperar(calculo)["pasos"] == 0          # antes: «Calculando…» para siempre
    assert perdidos and primero.poll() is not None and aislado._trabajador.proceso is not primero


def test_b418_si_se_pierde_otra_vez_va_a_un_hijo_de_una_sola_tarea(monkeypatch):
    """Dos trabajadores seguidos sin tomar el pedido (la tubería falla, Windows): lo calcula un hijo que lo lee de un archivo."""
    _pedido_perdido(monkeypatch, 4)
    aislado.cerrar_trabajador()
    calculo = aislado.CalculoPendiente("recalcular_documento", {"receta": Documento().a_dict()})
    assert _esperar(calculo)["pasos"] == 0
    assert calculo.trabajador is None and calculo.proceso is not None
    assert aislado.correr_json("recalcular_documento", {"receta": Documento().a_dict()}, 60)["pasos"] == 0   # el de Aceptar


def test_b418_un_precalentado_cuyo_pedido_no_llega_no_deja_esperando_a_la_previa(monkeypatch):
    _pedido_perdido(monkeypatch, 1)                 # se pierde el «calentar», no la previa
    aislado.cerrar_trabajador()
    aislado.precalentar(Documento().a_dict())
    assert aislado._previa_en_curso is not None
    calculo = aislado.CalculoPendiente("recalcular_documento", {"receta": Documento().a_dict()})
    assert _esperar(calculo, tope=20)["pasos"] == 0          # antes esperaba los 900 s del precalentado


def _prisma_e11(p):
    """El prisma con que E11 colgó Aceptar en Windows (tanda 10)."""
    for clave, valor in (("ancho", "30,5"), ("largo", "2*10"), ("alto", "15")):
        p.set_valor(clave, valor)


@pytest.mark.lento        # 8 comandos, cada uno con su pedido perdido y el proceso nuevo del reintento: ~15 s
def test_b418_en_la_ventana_la_previa_en_frio_llega_aunque_se_pierda_el_pedido(tmp_path, monkeypatch):
    """B-418: con la app recién abierta, Extruir, Barrido, Solevación, Agujero, las primitivas (aparte desde FL-1), Rosca
    modelada (desde P-78) y Empalme se quedaban en «Calculando…» para siempre si el trabajador nuevo no tomaba el pedido (Windows)."""
    import math

    from PySide6.QtTest import QTest

    from omnicad import api
    from omnicad.nucleo import geometria as geo, referencias as refs
    from omnicad.timeline.operaciones import OpExtrusion
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO

    monkeypatch.setattr(comando, "PREVIA_APARTE", True)
    s, k = api.Sesion(), 15 * math.sqrt(0.5)
    ids = {}
    for nombre, plano, ents in (
            ("E", "XY", [{"type": "rectangle", "corner1": [-60, 0], "corner2": [-40, 10]}]),
            ("P", "XY", [{"type": "circle", "center": [0, 0], "radius": 3}]),
            ("R", "XZ", [{"type": "arc", "start": [0, 0], "mid": [15 - k, k], "end": [15, 15]}]),
            ("L0", "XY", [{"type": "circle", "center": [0, 60], "radius": 4}]),
            ("L1", "Z20", [{"type": "circle", "center": [0, 60], "radius": 2}])):
        if plano == "Z20":
            assert api.llamar(s, "create_construction_plane", {"plane": "XY", "offset": 20, "name": "Z20"})["ok"]
        assert api.llamar(s, "sketch_from_spec", {"name": nombre, "plane": plano, "entities": ents})["ok"]
        ids[nombre] = s.doc.operaciones[-1].id
    assert api.llamar(s, "create_cylinder", {"radius": 5, "height": 20, "x": 80, "name": "Eje"})["ok"]
    est = s.doc.estado_final

    def perfil(nombre):
        br = est.bocetos[ids[nombre]]
        return hit_desde_ref({"tipo": "perfil", "boceto": ids[nombre], **OpExtrusion.referencia_perfil(br.perfiles[0])}, est)

    eje = next(c for c in est.cuerpos.values() if c.nombre == "Eje")
    cara = next(c for c in refs.subformas(eje.forma, "cara") if refs.firma_cara(c).get("geom") == "cilindro")
    ruta = hit_desde_ref({"tipo": "curva_boceto", "boceto": ids["R"],
                          "curva": next(iter(est.bocetos[ids["R"]].boceto.curvas))}, est)

    def campo(p, clave):
        p.activa = next(c for c in p.campos if getattr(c, "clave", None) == clave)

    def extruir(p):
        p._elegida(perfil("E"))
        p.set_valor("distancia", "5 mm")

    def barrido(p):
        campo(p, "perfiles")
        p._elegida(perfil("P"))
        campo(p, "ruta")
        p._elegida(ruta)

    def rosca(p):
        p._elegida(hit_desde_ref({"tipo": "cara", "cuerpo": eje.id, "firma": refs.firma_cara(cara)}, est))
        p.set_valor("modelada", True)

    def solevacion(p):
        p.set_valor("secciones", [perfil("L0"), perfil("L1")])

    def agujero(p):
        tapa = max((c for c in refs.subformas(eje.forma, "cara") if refs.firma_cara(c).get("geom") == "plano"),
                   key=lambda c: geo.caja_envolvente(c)[0][2])
        hit = hit_desde_ref(refs.referencia(eje.id, tapa, eje.forma), est)
        hit["punto"] = [80.0, 0.0, 20.0]
        campo(p, "colocacion")
        p._elegida(hit)
        p.set_valor("diametro", "2 mm")

    def empalme(p):
        arista = refs.subformas(eje.forma, "arista")[0]
        campo(p, "aristas")
        p._elegida(hit_desde_ref(refs.referencia(eje.id, arista, eje.forma), est))

    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        aislado.cerrar_trabajador()                      # en frío, como con la app recién abierta
        for clave, elegir in (("extruir", extruir), ("barrido", barrido), ("solevacion", solevacion),
                              ("agujero", agujero), ("rosca", rosca), ("empalme_3d", empalme), ("caja", _prisma_e11),
                              ("cilindro", lambda p: p.set_valor("alto", "15 mm"))):
            # De la segunda en adelante el trabajador llega despierto (el reintento de la anterior queda vivo): el
            # «en frío» es el de abrir la app y arrancar un proceso por comando costaba 8 arranques de más.
            perdidos = _pedido_perdido(monkeypatch, 1)
            p = v.ejecutar_comando(CATALOGO[clave]())
            elegir(p)
            limite = time.monotonic() + 60
            while (p._t_previa.isActive() or p._hijo_previa is not None) and time.monotonic() < limite:
                QTest.qWait(20)
            assert perdidos and p._previa_aparte, clave
            assert p._previa_ok and p._hijo_previa is None, (clave, p.mensaje.text())
            assert any(len(m[0]) for m in getattr(v.visor._estado, "_mallas_previa", {}).values()), clave
            p.cancelar()
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def _ventana(tmp_path, monkeypatch, doc=None):
    monkeypatch.setattr(comando, "PREVIA_APARTE", True)
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(doc or Documento(), prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    aislado.cerrar_trabajador()                         # en frío, como con la app recién abierta
    return app, v


def _cerrar(app, v):
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()
    aislado.cerrar_trabajador()


@pytest.mark.parametrize("clave", ["caja", "extruir"])
def test_b418_aceptar_con_los_pedidos_perdidos_crea_el_paso_y_el_cuerpo(tmp_path, monkeypatch, clave):
    """E11 (tanda 10): Aceptar en el prisma con la previa sin llegar dejaba el panel tomado más de 120 s. Gerardo: Extruir
    con la previa en «Calculando…» anotaba Aceptar como exitoso sin paso ni cuerpo a la vista."""
    from omnicad import api
    from omnicad.timeline.operaciones import OpExtrusion
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    s = api.Sesion()
    assert api.llamar(s, "sketch_from_spec", {"plane": "XY", "entities": [
        {"type": "rectangle", "corner1": [0, 0], "corner2": [30.5, 20]}]})["ok"]
    boceto = s.doc.operaciones[-1].id
    app, v = _ventana(tmp_path, monkeypatch, s.doc)
    pasos = len(v.doc.operaciones)
    perdidos = _pedido_perdido(monkeypatch, 2)          # el de la previa y el primero de Aceptar
    sueltos = []                                        # un hijo de una sola tarea no tiene el aviso ni el reintento
    correr = aislado._correr
    monkeypatch.setattr(aislado, "_correr", lambda tarea, *a, **k: sueltos.append(tarea) or correr(tarea, *a, **k))
    try:
        p = v.ejecutar_comando(CATALOGO[clave]())
        if clave == "caja":
            _prisma_e11(p)
        else:
            est = v.doc.estado_final
            ref = OpExtrusion.referencia_perfil(est.bocetos[boceto].perfiles[0])
            p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": boceto, **ref}, est))
            p.set_valor("distancia", "15 mm")
        inicio = time.monotonic()
        p.aceptar()
        esperar_barra(v)                                # FL-3b: el paso se calcula en otro hilo, con su barra
        assert v.panel is None, p.mensaje.text()
        assert len(perdidos) == 2 and not sueltos, sueltos
        nuevo = v.doc.operaciones[-1]
        assert len(v.doc.operaciones) == pasos + 1 and v.doc.resultados[-1].estado == "ok", v.doc.resultados[-1].mensaje
        (cuerpo,) = [c for c in v.doc.estado_final.cuerpos.values() if c.op_id == nuevo.id]
        assert cuerpo.id in {m["id"] for m in v.visor._mallas}          # y se ve
        assert time.monotonic() - inicio < 30
    finally:
        _cerrar(app, v)


@pytest.mark.parametrize("como", ["esc", "cancelar"])
def test_b418_esc_o_cancelar_salen_aunque_el_proceso_aparte_no_conteste(tmp_path, monkeypatch, como):
    from PySide6.QtTest import QTest

    from omnicad.ui.comandos import CATALOGO

    def salir(p):
        if como == "esc":
            QTest.keyClick(p, Qt.Key_Escape)
        else:       # por la QWindow, como un clic de verdad (al botón directo no pasaba por donde se perdía)
            ventana = p.window()
            QTest.mouseClick(ventana.windowHandle(), Qt.LeftButton, Qt.NoModifier,
                             p.boton_cancelar.mapTo(ventana, p.boton_cancelar.rect().center()))

    app, v = _ventana(tmp_path, monkeypatch)
    _pedido_perdido(monkeypatch, 10 ** 6)
    monkeypatch.setattr(aislado, "PLAZO_RECIBIR", 10 ** 6)     # sin el aviso de B-418: un trabajador que no contesta nunca
    pasos = len(v.doc.operaciones)
    try:
        p = v.ejecutar_comando(CATALOGO["caja"]())       # con la previa en vuelo
        _prisma_e11(p)
        QTest.qWait(300)
        assert p._hijo_previa is not None
        salir(p)
        assert v.panel is None
        p = v.ejecutar_comando(CATALOGO["caja"]())       # con Aceptar esperando al proceso aparte
        _prisma_e11(p)
        inicio = time.monotonic()
        p.aceptar()                                      # FL-3b: espera en otro hilo; Esc y Cancelar son los de su barra
        QTest.qWait(1500)
        espera = barra(v)
        if como == "esc":
            QTest.keyClick(espera, Qt.Key_Escape)
        else:
            QTest.mouseClick(espera.findChild(QPushButton), Qt.LeftButton)
        esperar_barra(v, 8)
        assert time.monotonic() - inicio < 10
        QTest.qWait(50)
        assert v.panel is None and len(v.doc.operaciones) == pasos and not v.doc.estado_final.cuerpos
    finally:
        _cerrar(app, v)


def test_b418_cerrar_el_panel_con_la_previa_perdida_no_traba_deshacer_ni_el_comando_siguiente(tmp_path, monkeypatch):
    """E11 (tanda 10, Revolución): tras cerrar el panel con la previa sin llegar, «Calculando en un proceso aparte…» no
    terminaba, Ctrl+Z no deshacía y el MCP decía «Ya hay un cálculo en un proceso aparte»."""
    from PySide6.QtTest import QTest

    from omnicad import api
    from omnicad.ui.comandos import CATALOGO
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 1)     # deshacer va al proceso aparte, como un documento grande
    monkeypatch.setattr(Documento, "_receta_barata", lambda self, datos: False)   # FL-5 apagado: deshacer la única
    monkeypatch.setattr(Documento, "_solo_primitivas", lambda self, desde: False)  # caja ya no calcula nada
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})["ok"]
    monkeypatch.setattr(comando, "PREVIA_APARTE", True)
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    aislado.cerrar_trabajador()
    perdidos = _pedido_perdido(monkeypatch, 3)    # la previa y los dos trabajadores de deshacer: lo hace un hijo suelto
    try:
        p = v.ejecutar_comando(CATALOGO["caja"]())
        _prisma_e11(p)
        QTest.qWait(300)
        assert p._hijo_previa is not None
        p.cancelar()
        inicio = time.monotonic()
        v._deshacer()
        esperar_barra(v, 30)                            # FL-3b: deshacer calcula en otro hilo, con su barra
        assert not v.doc.estado_final.cuerpos and len(perdidos) == 3
        assert time.monotonic() - inicio < 30 and not v.doc._esperando_hijo
        p = v.ejecutar_comando(CATALOGO["cilindro"]())
        p.set_valor("alto", "15 mm")
        limite = time.monotonic() + 60
        while (p._t_previa.isActive() or p._hijo_previa is not None) and time.monotonic() < limite:
            QTest.qWait(20)
        assert p._previa_ok, p.mensaje.text()
    finally:
        _cerrar(app, v)
