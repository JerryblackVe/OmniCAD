# -*- coding: utf-8 -*-
"""B-335 / B-337: abrir o insertar un STEP no congela la ventana: la lectura y la malla van al proceso aparte, el recibo
a otro hilo, y Cancelar (o Esc) deja el documento como estaba."""
import time

import numpy as np
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QProgressDialog, QPushButton
from test_abrir_externo import _step_con_estructura

from omnicad import api
from omnicad.nucleo import aislado
from omnicad.timeline import calculo_aislado
from omnicad.timeline.operaciones import OpImportarSTEP
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal
from omnicad.ui.visor3d import Visor3D


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 5, "width": 5, "height": 5, "name": "Viejo"})["ok"]
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()
    aislado.cerrar_trabajador()


def _esperar(condicion, segundos=60):
    limite = time.monotonic() + segundos
    while not condicion() and time.monotonic() < limite:
        QTest.qWait(20)
    assert condicion()


def _sin_respuesta(monkeypatch):
    """Un proceso aparte que no contesta: la apertura queda esperando hasta que la persona cancela."""
    monkeypatch.setattr(aislado._Trabajador, "_avisar", lambda self, tarea: None)
    monkeypatch.setattr(aislado, "PLAZO_RECIBIR", 10 ** 6)
    aislado.cerrar_trabajador()


def _cancelar(ventana, como):
    QTest.qWait(300)
    (espera,) = [d for d in ventana.findChildren(QProgressDialog) if d.isVisible()]
    if como == "esc":
        QTest.keyClick(espera, Qt.Key_Escape)
    else:
        QTest.mouseClick(espera.findChild(QPushButton), Qt.LeftButton)
    _esperar(lambda: not any(d.isVisible() for d in ventana.findChildren(QProgressDialog)), 10)
    QTest.qWait(200)


def test_abrir_step_vuelve_enseguida_y_el_documento_llega_despues(tmp_path, monkeypatch, ventana):
    ruta = _step_con_estructura(tmp_path / "conjunto.step")
    viejo, sin_malla = ventana.doc, []
    datos_cuerpo = Visor3D.datos_cuerpo
    monkeypatch.setattr(Visor3D, "datos_cuerpo", lambda self, forma, preparada=None, gruesa=False: (
        sin_malla.append(preparada is None), datos_cuerpo(self, forma, preparada, gruesa))[1])
    inicio = time.perf_counter()
    ventana.abrir_ruta(str(ruta), aparte=True)
    assert time.perf_counter() - inicio < 0.25 and ventana.doc is viejo      # la ventana no esperó a la lectura
    _esperar(lambda: ventana.doc is not viejo)
    cuerpos = {c.nombre: c.id for c in ventana.doc.estado_final.cuerpos.values()}
    assert set(cuerpos) == {"Placa", "Perno"}
    assert {m["id"] for m in ventana.visor._mallas} == set(cuerpos.values())    # se ven, con las mallas del otro hilo
    assert sin_malla and not any(sin_malla)         # la ventana no malló nada: las mallas las hizo el proceso aparte
    assert not hasattr(ventana.doc.estado_final, "_mallas_hijo")     # se usan una vez: otro detalle vuelve a mallar


@pytest.mark.parametrize("como", ["cancelar", "esc"])
def test_cancelar_abrir_step_deja_el_documento_de_antes(tmp_path, monkeypatch, ventana, como):
    ruta = _step_con_estructura(tmp_path / "conjunto.step")
    _sin_respuesta(monkeypatch)
    viejo = ventana.doc
    ventana.abrir_ruta(str(ruta), aparte=True)
    _cancelar(ventana, como)
    assert ventana.doc is viejo and [c.nombre for c in viejo.estado_final.cuerpos.values()] == ["Viejo"]


def test_insertar_step_vuelve_enseguida_y_el_paso_llega_despues(tmp_path, monkeypatch, ventana):
    ruta = _step_con_estructura(tmp_path / "conjunto.step")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(ruta), "")))
    antes = len(ventana.doc.operaciones)
    inicio = time.perf_counter()
    ventana.importar_step()
    assert time.perf_counter() - inicio < 0.25 and len(ventana.doc.operaciones) == antes
    _esperar(lambda: len(ventana.doc.operaciones) == antes + 1)
    assert len(ventana.doc.estado_final.cuerpos) == 3 and "Viejo" in {c.nombre for c in ventana.doc.estado_final.cuerpos.values()}
    assert ventana.doc.resultados[-1].estado == "ok"
    ventana.doc.deshacer()                                   # sigue siendo UN paso de deshacer
    assert [c.nombre for c in ventana.doc.estado_final.cuerpos.values()] == ["Viejo"]


@pytest.mark.parametrize("como", ["cancelar", "esc"])
def test_cancelar_insertar_step_no_toca_el_documento(tmp_path, monkeypatch, ventana, como):
    ruta = _step_con_estructura(tmp_path / "conjunto.step")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(ruta), "")))
    _sin_respuesta(monkeypatch)
    antes = len(ventana.doc.operaciones)
    ventana.importar_step()
    _cancelar(ventana, como)
    assert len(ventana.doc.operaciones) == antes and [c.nombre for c in ventana.doc.estado_final.cuerpos.values()] == ["Viejo"]


def test_insertar_un_step_ilegible_avisa_y_no_deja_un_paso_rojo(tmp_path, monkeypatch, ventana):
    ruta = tmp_path / "roto.step"
    ruta.write_text("ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\n#1=BASURA(;\nENDSEC;\nEND-ISO-10303-21;\n", encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(ruta), "")))
    avisos = []
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a: avisos.append(a[1:])))
    antes = len(ventana.doc.operaciones)
    ventana.importar_step()
    _esperar(lambda: avisos)
    assert avisos[0][0] == "No se pudo importar" and len(ventana.doc.operaciones) == antes


def test_el_proceso_aparte_malla_solo_los_cuerpos_que_la_ventana_no_tiene(tmp_path, monkeypatch):
    """B-337: OpenCascade no suelta el GIL al mallar (un cuerpo de un STEP trababa la ventana 28 s): con `MALLAR` el hijo
    manda la malla de los cuerpos nuevos, y no la de los que ya mandó antes."""
    monkeypatch.setattr(aislado, "MALLAR", (None, 0.3))
    texto = _step_con_estructura(tmp_path / "conjunto.step").read_text(encoding="utf-8")
    doc = api.Sesion().doc
    doc.agregar(OpImportarSTEP(doc.nuevo_id(), "Uno", archivo="a.step", contenido=texto), aparte=True)
    primeros = set(doc.estado_final.cuerpos)
    hechas = doc.estado_final._mallas_hijo
    assert set(hechas) == primeros and len(primeros) == 2
    v, n, seg = next(iter(hechas.values()))
    assert len(v) and len(v) == len(n) and len(v) % 3 == 0 and len(seg)
    doc.agregar(OpImportarSTEP(doc.nuevo_id(), "Dos", archivo="b.step", contenido=texto), aparte=True)
    nuevos = set(doc.estado_final.cuerpos) - primeros
    assert len(nuevos) == 2 and set(doc.estado_final._mallas_hijo) == (nuevos if aislado.TRABAJADOR else nuevos | primeros)
    aislado.cerrar_trabajador()


def test_una_malla_del_proceso_aparte_que_falta_o_vino_rota_se_hace_en_la_ventana(tmp_path, monkeypatch, ventana):
    """Regla de B-453: si el caché del hijo (`_mallas_hijo`) falla, el visor malla por el camino normal y no hay error."""
    leer, tocadas = calculo_aislado._leer_calculo, []

    def romper(salida):
        datos = leer(salida)
        mallas = datos.get("mallas") or {}
        for i, cid in enumerate(list(mallas)):
            tocadas.append(cid)
            if i == 0:
                del mallas[cid]                                          # falta
            else:
                mallas[cid] = (np.zeros((4, 2)), None, "basura")         # rota
        return datos
    monkeypatch.setattr(calculo_aislado, "_leer_calculo", romper)
    avisos = []
    for tipo in ("critical", "warning"):
        monkeypatch.setattr(QMessageBox, tipo, staticmethod(lambda *a: avisos.append(a[1:])))
    viejo = ventana.doc
    ventana.abrir_ruta(str(_step_con_estructura(tmp_path / "conjunto.step")), aparte=True)
    _esperar(lambda: ventana.doc is not viejo)
    QTest.qWait(200)
    assert len(tocadas) == 2 and not avisos
    for m in ventana.visor._mallas:
        v, n = m["v"], m["n"]
        assert len(v) and v.shape[1] == 3 and n.shape == v.shape


def test_un_chaflan_sobre_el_cuerpo_importado_se_ve_con_su_malla_nueva(tmp_path, monkeypatch, ventana):
    """Regla de B-453: la malla del hijo es de UN cálculo; un chaflán (también aparte) sobre el cuerpo importado se ve
    con la malla del cuerpo achaflanado, no con la que quedó del STEP."""
    ruta = _step_con_estructura(tmp_path / "conjunto.step")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(ruta), "")))
    doc, antes = ventana.doc, len(ventana.doc.operaciones)
    ventana.importar_step()
    _esperar(lambda: len(doc.operaciones) == antes + 1)
    placa = next(c for c in doc.estado_final.cuerpos.values() if c.nombre != "Viejo")    # Insertar los renombra

    def malla():
        return next(m for m in ventana.visor._mallas if m["id"] == placa.id)
    inclinadas = lambda n: int(np.sum((np.abs(n[:, 2]) > 0.1) & (np.abs(n[:, 2]) < 0.9)))
    _esperar(lambda: any(m["id"] == placa.id for m in ventana.visor._mallas))
    vieja = malla()
    assert inclinadas(vieja["n"]) == 0                       # una caja: caras a 0° o 90°
    assert api.llamar(api.Sesion(doc), "chamfer", {"edges": ">Z", "distance": 2, "body": placa.nombre})["ok"]
    op = doc.operaciones[-1]
    doc.deshacer()
    ventana._cambio_aparte(lambda: ventana._agregar(op, aparte=True))     # como lo hace la ventana: en el hijo
    _esperar(lambda: len(doc.operaciones) == antes + 2 and doc.resultados[-1].estado == "ok")
    _esperar(lambda: malla()["forma"] is doc.estado_final.cuerpos[placa.id].forma)    # el visor ya tiene la forma nueva
    nueva = malla()
    assert inclinadas(nueva["n"]) > 0 and len(nueva["v"]) > len(vieja["v"])
