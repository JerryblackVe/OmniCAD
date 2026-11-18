"""Previa de Vaciado en un proceso aparte (P-51): la malla es solo visual; lo aceptado sale del kernel en el padre."""
import time
from pathlib import Path
import runpy
from types import SimpleNamespace

import numpy as np
import pytest
from _calculo_aparte import esperar_barra
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad.nucleo import aislado, geometria as geo
from omnicad.nucleo.render_cpu import es_malla
from omnicad.timeline.calculo_aislado import leer_previa_visual, previa_visual
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.ops_modificar import OpVaciado
from omnicad.ui.comando import PanelComando, hit_desde_ref
from omnicad.ui.comandos.modificar import Vaciado
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def documento():
    d = Documento()
    d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="100", largo="60", alto="20"))
    return d


@pytest.fixture(scope="module")
def placa():
    banco = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/medir_previa_comandos.py"))
    receta, _ = banco["_modelo"]("placa200")
    return receta


@pytest.mark.parametrize("espesor", np.linspace(0.1, 1.0, 10))
def test_la_previa_visual_nunca_entra_en_el_solido_aceptado(espesor, placa):
    d = Documento.desde_dict(placa)
    cid = next(iter(d.estado_final.cuerpos))
    op = OpVaciado(d.nuevo_id(), cuerpos=[cid], espesor_interior=str(espesor))
    receta = d.a_dict()
    exacto, _ = d.previsualizar(op, en_vivo=True)
    referencia = exacto.cuerpo(cid).forma
    d._previa = None
    salida = previa_visual(receta, op.a_dict(), None, 0.05, 0.3)
    vista, avisos = leer_previa_visual(salida, d.estado_final)
    assert not avisos and es_malla(vista.cuerpo(cid).forma)
    assert d.a_dict() == receta and d._previa is None
    assert not es_malla(d.estado_final.cuerpo(cid).forma)
    assert d.agregar(op).estado == "ok"
    aceptado = d.estado_final.cuerpo(cid).forma
    assert not es_malla(aceptado) and geo.es_valida(aceptado)
    assert geo.volumen_exacto(aceptado) == pytest.approx(geo.volumen_exacto(referencia), rel=1e-6)
    assert np.allclose(geo.caja_envolvente(aceptado), geo.caja_envolvente(referencia), rtol=1e-6)


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(documento(), prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def panel(ventana, monkeypatch):
    monkeypatch.setattr(PanelComando, "_previa_pesada", lambda *a: True)
    p = ventana.ejecutar_comando(Vaciado())
    p._elegida(hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, p.ctx.estado))
    p._t_previa.stop()
    return p


def esperar(p):
    """B-449: espera a que la ventana junte la previa, sin plazo fijo (bajo carga el hijo tarda lo que tarde). Corta solo si
    el proceso aparte murió y la ventana no lo recogió en 200 vueltas del bucle; un cuelgue de verdad lo corta el producto
    (`TOPE_PREVUELO_PARAMETROS`) y el turno de `turno.py`."""
    muerto = 0
    while p._hijo_previa is not None and muerto < 200:
        QTest.qWait(10)
        proceso = getattr(p._hijo_previa, "proceso", None)      # None: todavía espera su turno detrás de otra previa
        muerto = muerto + 1 if proceso is not None and proceso.poll() is not None else 0
    assert p._hijo_previa is None, "El proceso aparte terminó y la ventana no recogió la previa"


class _HijoFalso:
    """Un hijo que sigue vivo durante `vueltas` vueltas del bucle y después la ventana lo recoge (`p._hijo_previa = None`)."""

    def __init__(self, panel_falso, vueltas, muere=False):
        self.panel, self.vueltas, self.muere = panel_falso, vueltas, muere
        self.proceso = SimpleNamespace(poll=lambda: 1 if self.muere else None)

    def vuelta(self):
        self.vueltas -= 1
        if self.vueltas <= 0 and not self.muere:
            self.panel._hijo_previa = None


def test_b449_esperar_no_tiene_plazo_fijo_mientras_el_hijo_vive(monkeypatch):
    """Reproduce la carga de la VPS sin cargarla: un reloj que corre 1 s por consulta y un hijo vivo durante 100 vueltas.
    Con el plazo de 15 s de antes, `esperar` fallaba a la vuelta 15; ahora espera hasta que la ventana lo recoja."""
    falso = SimpleNamespace(_hijo_previa=None)
    falso._hijo_previa = _HijoFalso(falso, vueltas=100)
    reloj = iter(range(10 ** 6))
    monkeypatch.setattr(time, "perf_counter", lambda: next(reloj))
    monkeypatch.setattr(QTest, "qWait", lambda _ms: falso._hijo_previa and falso._hijo_previa.vuelta())
    esperar(falso)
    assert falso._hijo_previa is None


def test_b449_esperar_falla_si_el_proceso_murio_y_la_ventana_no_lo_recogio(monkeypatch):
    falso = SimpleNamespace(_hijo_previa=None)
    falso._hijo_previa = _HijoFalso(falso, vueltas=0, muere=True)
    monkeypatch.setattr(QTest, "qWait", lambda _ms: None)
    with pytest.raises(AssertionError, match="no recogió"):
        esperar(falso)


def test_el_hijo_real_no_bloquea_y_cancelar_no_toca_documento(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    antes = ventana.doc.a_dict()
    atendidos = []  # eventos que la ventana atiende mientras el hijo corre (sin depender del reloj)

    def latir():
        if p._hijo_previa is not None:
            atendidos.append(1)
            QTimer.singleShot(0, latir)

    p._calcular_previa()
    p._t_hijo.setInterval(2000)   # el hijo caliente de la suite contesta en milisegundos: al demorar la recepción, el conteo de latidos no depende de la carga
    antes["contador"] = ventana.doc.a_dict()["contador"]  # construir reserva ids aun si se cancela
    assert p._hijo_previa is not None and not p._previa_ok
    QTimer.singleShot(0, latir)
    esperar(p)
    assert len(atendidos) >= 3 and p._previa_ok, p.mensaje.text()
    assert "op1.c1" in ventana.visor._estado._mallas_previa      # la dibuja la malla del proceso aparte
    assert ventana.doc.a_dict() == antes
    QTest.keyClick(p, Qt.Key_Escape)
    assert ventana.panel is None and ventana.doc.a_dict() == antes
    assert not es_malla(ventana.visor._estado.cuerpo("op1.c1").forma)


def test_mover_muchas_veces_lanza_solo_el_ultimo_pendiente(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    pedidos = []
    salida = previa_visual(ventana.doc.a_dict(), OpVaciado("op2", cuerpos=["op1.c1"]).a_dict(), None, 0.05, 0.3)

    class Hijo:
        listo = False

        def __init__(self, tarea, datos, tope=None):
            pedidos.append(datos["operacion"]["params"]["espesor_interior"])

        def sondear(self):
            return salida if self.listo else None

        def cancelar(self):
            pass

    monkeypatch.setattr(aislado, "CalculoPendiente", Hijo)
    p._calcular_previa()
    for valor in ("0.4", "0.6", "0.8"):
        p.set_valor("espesor_interior", valor)
        p._t_previa.stop()
        p._calcular_previa()
    assert len(pedidos) == 1
    p._hijo_previa.listo = True
    p._recibir_previa()
    assert pedidos == ["1 mm", "0.8"] and not p._previa_ok
    p._hijo_previa.listo = True
    p._recibir_previa()
    assert p._previa_ok and p._hijo_previa is None


def test_b455_un_error_interno_del_hijo_rehace_la_previa_en_la_ventana(tmp_path, monkeypatch):
    """B-455: un error del hijo que no es de los valores (un TypeError, como B-432) salía en rojo y Aceptar no reintentaba.
    Ahora la misma previa se rehace en la ventana sin mostrarlo. El cuerpo ya lo modificó un paso anterior (movido y
    girado; Vaciado sin caras falla sobre uno unido o cortado: B-459)."""
    from omnicad.timeline.ops_modificar import OpMover
    d = documento()
    d.agregar(OpMover(d.nuevo_id(), cuerpos=["op1.c1"], dz="15 mm", rz="30 deg"))
    assert geo.caja_envolvente(d.estado_final.cuerpo("op1.c1").forma)[0][2] == pytest.approx(15)
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(d, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        class Hijo:
            def __init__(self, tarea, datos, tope=None):
                pass

            def sondear(self):
                raise aislado.FalloInterno("'NoneType' object is not subscriptable")

            def cancelar(self):
                pass

        monkeypatch.setattr(aislado, "CalculoPendiente", Hijo)
        p = panel(v, monkeypatch)
        p._calcular_previa()
        assert p._hijo_previa is not None and not p._previa_ok
        p._recibir_previa()
        assert p._previa_ok and p._hijo_previa is None, p.mensaje.text()
        assert "NoneType" not in p.mensaje.text() and "⚠" not in p.mensaje.text()
        hueco = v.visor._estado.cuerpo("op1.c1").forma
        assert not es_malla(hueco) and geo.volumen(hueco) == pytest.approx(17688, rel=1e-3)    # exacta, vaciada en la ventana

        class Imposible(Hijo):
            def sondear(self):
                raise aislado.FalloDelCalculo("El espesor es demasiado grande.")

        monkeypatch.setattr(aislado, "CalculoPendiente", Imposible)
        p._calcular_previa()
        p._recibir_previa()
        assert not p._previa_ok and "⚠ El espesor es demasiado grande." in p.mensaje.text()     # un valor imposible sí
    finally:
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def test_b455_el_hijo_distingue_un_error_interno_de_uno_de_los_valores():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    try:
        BRepPrimAPI_MakeBox(0, 0, 0).Shape()
    except Exception as e:  # noqa: BLE001 — el kernel lanza su propia clase
        del_kernel = e
    assert aislado._fallo(TypeError("x"))["_interno"] is True
    assert aislado._fallo(geo.ErrorGeometria("y")) == {"_fallo": "y", "_interno": False}
    assert aislado._fallo(del_kernel)["_interno"] is False
    assert aislado._fallo(MemoryError())["_interno"] is False       # en la ventana la tumbaría


def test_cancelar_deja_de_esperar_y_no_mata_al_trabajador(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    p._calcular_previa()
    trabajador = p._hijo_previa.proceso
    p.cancelar()
    assert trabajador.poll() is None and not p._t_hijo.isActive()


def test_cancelar_mata_solo_el_hijo_propio_de_esa_previa(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    with aislado._ocupado:                  # trabajador ocupado: la previa va a un hijo propio
        p._calcular_previa()
    hijo = p._hijo_previa.proceso
    assert p._hijo_previa.trabajador is None
    p.cancelar()
    assert hijo.poll() is not None and not p._t_hijo.isActive()


def test_un_valor_nuevo_corta_una_vez_el_calculo_que_se_alarga(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    pedidos, cortes = [], []

    class Hijo:
        inicio = -1e9               # ya pasó la paciencia

        def __init__(self, tarea, datos, tope=None):
            pedidos.append(datos["operacion"]["params"]["espesor_interior"])

        def sondear(self):
            return None

        def cancelar(self, ya=False):
            cortes.append(ya)

    monkeypatch.setattr(aislado, "CalculoPendiente", Hijo)
    monkeypatch.setattr(aislado, "costo_reinicio", lambda: 1.0)     # FL-1: un trabajador que ya contestó
    p._calcular_previa()
    p._recibir_previa()                         # sin valor nuevo no se corta nada
    assert not cortes
    p.set_valor("espesor_interior", "0.4")
    p._t_previa.stop()
    p._calcular_previa()
    p._recibir_previa()
    assert cortes == [True] and pedidos == ["1 mm", "0.4"] and p._t_hijo.isActive()
    p.set_valor("espesor_interior", "0.6")
    p._t_previa.stop()
    p._calcular_previa()
    p._recibir_previa()                         # el segundo no se corta: tiene que rehacer el documento
    assert cortes == [True] and pedidos == ["1 mm", "0.4"] and p._pendiente_hijo is not None
    p._cancelar_previa_hijo()


def test_el_visor_reusa_los_arrays_que_volvieron_del_hijo(ventana, monkeypatch):
    import omnicad.ui.visor3d as vis
    d = ventana.doc
    salida = previa_visual(d.a_dict(), OpVaciado("op2", cuerpos=["op1.c1"]).a_dict(), None, 0.05, 0.3)
    estado, _ = leer_previa_visual(salida, d.estado_final)

    def prohibido(*a, **k):
        pytest.fail("Se volvió a teselar o a calcular aristas dentro de la ventana")

    monkeypatch.setattr(vis, "teselar_cuerpo", prohibido)
    monkeypatch.setattr(vis, "aristas_cuerpo", prohibido)
    ventana.visor.set_modelo(estado)
    v, n, seg = estado._mallas_previa["op1.c1"]
    dibujado = ventana.visor._mallas[0]
    assert np.array_equal(dibujado["v"], v) and np.array_equal(dibujado["n"], n)
    assert np.array_equal(dibujado["seg"], seg)


def test_la_previa_reusa_bocetos_solo_con_el_mismo_origen_y_visibilidad(ventana, monkeypatch):
    import omnicad.ui.visor3d as vis
    d = ventana.doc
    entrada = d.estado_final
    entrada.bocetos["marco"] = SimpleNamespace(op_id="marco")
    llamadas = []
    monkeypatch.setattr(vis, "polilineas_boceto", lambda br: llamadas.append(br) or [np.array([[0, 0, 0], [1, 1, 0]])])
    ventana.visor.set_modelo(entrada)
    assert len(llamadas) == 1 and len(ventana.visor._bocetos) == 2
    salida = previa_visual(d.a_dict(), OpVaciado("op2", cuerpos=["op1.c1"]).a_dict(), None, 0.05, 0.3)
    estado, _ = leer_previa_visual(salida, entrada)
    ventana.visor.set_modelo(estado)
    assert len(llamadas) == 1 and len(ventana.visor._bocetos) == 2
    ventana.visor.set_modelo(estado, ocultos={"marco"})
    assert len(ventana.visor._bocetos) == 0
    otra, _ = leer_previa_visual(salida, entrada.copia())
    ventana.visor.set_modelo(otra)
    assert len(llamadas) == 2 and len(ventana.visor._bocetos) == 2


def test_cambiar_espesor_mueve_el_asa_sin_medir_todas_las_caras(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    g = p.manipuladores
    original = p.comando.manipuladores
    llamadas = []

    def medir(*a):
        llamadas.append(1)
        return original(*a)

    monkeypatch.setattr(p.comando, "manipuladores", medir)
    g._base_apoyo = None
    g.actualizar()
    antes = g.manips[0].puntos(g)[0].copy()   # la cola; la punta cambia además con la escala de pantalla (perspectiva)
    p.set_valor("espesor_interior", "3")
    p._t_previa.stop()
    despues = g.manips[0].puntos(g)[0]
    assert len(llamadas) == 1 and np.linalg.norm(despues - antes) == pytest.approx(2)
    p.set_valor("direccion", "ambos")
    p._t_previa.stop()
    assert len(llamadas) == 2 and len(g.manips) == 2
    p.set_valor("caras", [])
    p._t_previa.stop()
    assert len(llamadas) == 3 and not g.manips


def test_un_hijo_que_muere_apaga_la_previa_con_un_mensaje_y_la_app_sigue(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    p._calcular_previa()
    esperar(p)
    assert "op1.c1" in ventana.visor._estado._mallas_previa   # hay una previa estimada a la vista
    p.set_valor("espesor_interior", "0.4")
    p._t_previa.stop()
    p._calcular_previa()
    antes = ventana.doc.a_dict()      # construir la operación reserva ids: se mide después
    p._hijo_previa.proceso.kill()
    esperar(p)
    assert not p._previa_ok and "vista previa" in p.mensaje.text() and (
        "falló" in p.mensaje.text() or "kernel cayó" in p.mensaje.text())     # kill(): Windows sale con 1, Linux con -9
    assert not getattr(ventana.visor._estado, "_mallas_previa", None)   # no queda nada estimado
    assert ventana.doc.a_dict() == antes and ventana.panel is p
    p._calcular_previa()           # la app sigue: el siguiente cálculo arranca otro hijo y termina
    esperar(p)
    assert p._previa_ok and "op1.c1" in ventana.visor._estado._mallas_previa


def test_un_hijo_que_pasa_su_plazo_se_corta_y_avisa(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    p._calcular_previa()
    hijo = p._hijo_previa
    hijo.tope = 0.0
    esperar(p)
    assert hijo.proceso.poll() is not None
    assert not p._previa_ok and "tardaba demasiado" in p.mensaje.text()
    assert not any(es_malla(c.forma) for c in ventana.visor._estado.cuerpos.values())
    assert ventana.panel is p


def test_un_cuerpo_que_ya_no_existe_no_rompe_la_decision_de_la_previa(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    monkeypatch.undo()    # sin forzar: la caja tiene 6 caras, no es pesada
    assert not p._previa_pesada(OpVaciado("opX", cuerpos=["op9.c9"]))


def test_aceptar_con_la_previa_aparte_en_vuelo_aplica_el_vaciado_exacto(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    p._calcular_previa()
    assert p._hijo_previa is not None and not p._previa_ok       # la malla aún no llegó
    p.aceptar()                                                   # no espera al hijo
    esperar_barra(ventana)                                        # FL-3b: el paso se calcula en otro hilo
    assert ventana.panel is None
    assert any(o.TIPO == "vaciado" for o in ventana.doc.operaciones)
    forma = ventana.doc.estado_final.cuerpo("op1.c1").forma
    assert not es_malla(forma) and geo.es_valida(forma)


def test_aceptar_tras_caer_el_hijo_sigue_funcionando(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    p._calcular_previa()
    p._hijo_previa.proceso.kill()
    esperar(p)
    assert not p._previa_ok
    p.aceptar()
    esperar_barra(ventana)                                        # FL-3b: el paso se calcula en otro hilo
    assert ventana.panel is None and any(o.TIPO == "vaciado" for o in ventana.doc.operaciones)
