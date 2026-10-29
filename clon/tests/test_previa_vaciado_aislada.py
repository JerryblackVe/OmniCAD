"""Previa de Vaciado en un proceso aparte (P-51): la malla es solo visual; lo aceptado sale del kernel en el padre."""
import time
from pathlib import Path
import runpy
from types import SimpleNamespace

import numpy as np
import pytest
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
    fin = time.perf_counter() + 15
    while p._hijo_previa is not None and time.perf_counter() < fin:
        QTest.qWait(10)
    assert p._hijo_previa is None, "El hijo no terminó"


def test_el_hijo_real_no_bloquea_y_cancelar_no_toca_documento(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    antes = ventana.doc.a_dict()
    latidos = []
    reloj = QTimer()
    reloj.timeout.connect(lambda: latidos.append(time.perf_counter()))
    reloj.start(10)
    p._calcular_previa()
    antes["contador"] = ventana.doc.a_dict()["contador"]  # construir reserva ids aun si se cancela
    assert p._hijo_previa is not None and not p._previa_ok
    esperar(p)
    reloj.stop()
    assert len(latidos) >= 3 and p._previa_ok, p.mensaje.text()
    assert es_malla(ventana.visor._estado.cuerpo("op1.c1").forma)
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

        def __init__(self, tarea, datos):
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


def test_cancelar_mata_solo_el_hijo_de_esa_previa(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    p._calcular_previa()
    hijo = p._hijo_previa.proceso
    p.cancelar()
    assert hijo.poll() is not None and not p._t_hijo.isActive()


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
    assert es_malla(ventana.visor._estado.cuerpo("op1.c1").forma)   # hay una previa estimada a la vista
    p.set_valor("espesor_interior", "0.4")
    p._t_previa.stop()
    p._calcular_previa()
    antes = ventana.doc.a_dict()      # construir la operación reserva ids: se mide después
    p._hijo_previa.proceso.kill()
    esperar(p)
    assert not p._previa_ok and "vista previa" in p.mensaje.text() and "falló" in p.mensaje.text()
    assert not any(es_malla(c.forma) for c in ventana.visor._estado.cuerpos.values())   # no queda nada estimado
    assert ventana.doc.a_dict() == antes and ventana.panel is p
    p._calcular_previa()           # la app sigue: el siguiente cálculo arranca otro hijo y termina
    esperar(p)
    assert p._previa_ok and es_malla(ventana.visor._estado.cuerpo("op1.c1").forma)


def test_un_hijo_que_pasa_su_plazo_se_corta_y_avisa(ventana, monkeypatch):
    p = panel(ventana, monkeypatch)
    p._calcular_previa()
    hijo = p._hijo_previa
    hijo.tope = 0.0
    esperar(p)
    assert hijo.proceso.poll() is not None
    assert not p._previa_ok and "plazo" in p.mensaje.text()
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
    assert ventana.panel is None and any(o.TIPO == "vaciado" for o in ventana.doc.operaciones)
