# -*- coding: utf-8 -*-
"""FL-2: al teclear la distancia de Extruir (Nuevo o Cortar) o el ángulo de Revolución, la malla barata se ve enseguida,
antes de que llegue la forma exacta del proceso aparte; Aceptar da siempre el sólido del kernel."""
import time

import numpy as np
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.nucleo import geometria as geo, render_cpu as rc
from omnicad.timeline.operaciones import OpExtrusion
from omnicad.ui import comando
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.solido import Extruir, Revolucion
from omnicad.ui.manipuladores import CAPA_PREVIA
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _escena():
    """Placa 60 × 50 × 10 (x de -40 a 20) y, sobre su cara de arriba, un rectángulo 40 × 30 con un agujero de r 5
    («Perfil»); aparte, un rectángulo 10 × 20 y una línea central a 5 mm para girarlo («Giro»)."""
    s = api.Sesion()
    _llamar(s, "create_box", length=60, width=50, height=10, x=-10, y=-10)
    _llamar(s, "sketch_from_spec", name="Giro", plane="XY", entities=[
        {"type": "rectangle", "corner1": [50, 0], "corner2": [60, 20]}])
    _llamar(s, "draw_line", sketch="Giro", start_x=45, start_y=0, end_x=45, end_y=30, centerline=True)
    _llamar(s, "create_construction_plane", plane="XY", offset=10, name="Arriba")
    _llamar(s, "sketch_from_spec", name="Perfil", plane="Arriba", entities=[
        {"type": "rectangle", "corner1": [0, 0], "corner2": [40, 30]}, {"type": "circle", "center": [20, 15], "radius": 5}])
    return s


def _perfiles(s, boceto):
    """Índices de los perfiles de más de 100 mm² del boceto (deja afuera el círculo del hueco)."""
    return [i for i, pf in enumerate(s.doc.estado_final.bocetos[s.paso(boceto).id].perfiles) if geo.area(pf.cara) > 100]


def _volumen(doc):
    return sum(geo.volumen_exacto(c.forma) for c in doc.estado_final.cuerpos.values())


def test_prisma_unidad_con_un_hueco_da_el_volumen_del_kernel():
    s = _escena()
    br = s.doc.estado_final.bocetos[s.paso("Perfil").id]
    perfil = max(br.perfiles, key=lambda pf: geo.area(pf.cara))      # el rectángulo con el hueco
    tris = geo.teselar(perfil.cara)[0].reshape(-1, 3, 3)
    inicio = time.perf_counter()
    prisma = rc.PrismaVisual(*rc.prisma_unidad(tris, br.plano.normal), br.plano.origen, br.plano.normal)
    assert (time.perf_counter() - inicio) * 1000 < 50
    for a, b in ((0, 7), (-3, 2), (5, -4)):
        v, n, seg = prisma.transformar(a, b)
        t = v.reshape(-1, 3, 3) - v.mean(0)
        volumen = np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6   # malla cerrada y hacia afuera
        assert volumen == pytest.approx((40 * 30 - np.pi * 25) * abs(b - a), rel=0.005)
        assert np.allclose(np.linalg.norm(n, axis=1), 1, atol=1e-6) and len(seg) % 2 == 0


@pytest.mark.parametrize("cmd, boceto, campo, texto, operacion, herramienta, args", [
    (Extruir, "Perfil", "distancia", "12", "nuevo", "extrude", {"distance": "12", "operation": "new_body"}),
    (Extruir, "Perfil", "distancia", "-4", "cortar", "extrude", {"distance": "-4", "operation": "cut", "reverse": False}),
    (Revolucion, "Giro", "angulo", "90", "nuevo", "revolve", {"angle": "90 deg", "axis": 15, "operation": "new_body"}),
])
def test_teclear_muestra_la_malla_ya_y_aceptar_da_el_solido_exacto(tmp_path, monkeypatch, cmd, boceto, campo, texto,
                                                                   operacion, herramienta, args):
    monkeypatch.setattr(comando, "PREVIA_APARTE", True)         # como en la app: la forma exacta va al proceso aparte
    app = QApplication.instance() or QApplication([])
    s = _escena()
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    try:
        p = v.ejecutar_comando(cmd())
        for i in _perfiles(s, boceto):
            perfil = s.doc.estado_final.bocetos[s.paso(boceto).id].perfiles[i]
            p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": s.paso(boceto).id,
                                      **OpExtrusion.referencia_perfil(perfil)}, p.ctx.estado))
        p.set_valor("operacion", operacion)
        widget = p.widgets[campo]
        QTest.mouseClick(widget, Qt.LeftButton)
        QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
        inicio = time.perf_counter()
        QTest.keyClicks(widget, texto)
        p._t_previa.stop()
        p._calcular_previa()
        ms = (time.perf_counter() - inicio) * 1000
        assert ms < 50, f"la previa barata tardó {ms:.0f} ms"
        assert p._previa_ok and p._hijo_previa is not None       # la malla ya está y la exacta todavía no llegó
        nuevos = [c.forma for k, c in v.visor._estado.cuerpos.items() if k not in p.ctx.estado.cuerpos]
        rojo = v.visor._capas.get(CAPA_PREVIA)
        if operacion == "cortar":       # la pieza intacta y la herramienta en rojo translúcido, como Fusion
            assert nuevos == [] and rojo and rojo[0][0] == "tris"
            caja = np.array([rojo[0][1].min(0), rojo[0][1].max(0)])
            assert np.allclose(caja, [[0, 0, 6], [40, 30, 10]], atol=1e-6)
        else:
            assert len(nuevos) == 1 and rc.es_malla(nuevos[0]) and not rojo
            if cmd is Revolucion:       # el cuarto de anillo de radios 5 a 15 alrededor de x = 45, del lado de +Z o -Z
                caja = np.array([nuevos[0].vertices.min(0), nuevos[0].vertices.max(0)])
                assert np.allclose(caja[:, :2], [[45, 0], [60, 20]], atol=1e-6) and np.ptp(caja[:, 2]) == pytest.approx(15)
        limite = time.monotonic() + 60
        while p._hijo_previa is not None and time.monotonic() < limite:
            QTest.qWait(20)
        assert p._previa_ok, p.mensaje.text()
        assert not any(rc.es_malla(c.forma) for c in v.visor._estado.cuerpos.values())   # la exacta reemplazó a la malla
        QTest.mouseClick(p.boton_ok, Qt.LeftButton)
        while v.panel is not None and time.monotonic() < limite:
            QTest.qWait(20)
        assert v.panel is None
        assert not any(rc.es_malla(c.forma) for c in v.doc.estado_final.cuerpos.values())
        ref = _escena()
        _llamar(ref, herramienta, sketch=boceto, profile=_perfiles(ref, boceto), **args)   # los mismos valores que el panel
        assert _volumen(v.doc) == pytest.approx(_volumen(ref.doc), rel=1e-9)
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()
