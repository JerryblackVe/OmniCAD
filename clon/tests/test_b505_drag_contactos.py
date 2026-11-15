# -*- coding: utf-8 -*-
"""B-505: `drag_component` mueve la posición sin capturar (devuelve moved y la nueva traslación), avisa si no se movió
nada y respeta los conjuntos de contactos (H-119)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from omnicad.timeline.posicion import pendiente_de
from test_h119_contactos import _llamar, _montaje
from test_posicion_ventana import ventana  # noqa: F401  (la fixture)


def _corrimiento(r, nombre):
    """Cuánto se corrió el componente respecto de donde está capturado."""
    c = next(c for c in r["result"]["components"] if c["name"] == nombre)
    return [a - b for a, b in zip(c["translation"], c["previous_translation"], strict=True)]


def test_arrastrar_con_union_mueve_y_deja_la_posicion_sin_capturar():
    s, _ = _montaje()
    r = _llamar(s, "drag_component", component="Piston", offset=[30, 0, 0])
    assert r["ok"] and r["result"]["moved"] is True and r["result"]["uncaptured"] is True
    assert _corrimiento(r, "Piston")[0] == pytest.approx(30, abs=1e-3)
    assert pendiente_de(s.doc) is not None
    assert _llamar(s, "capture_position")["ok"]                      # capturarla la deja en el documento


def test_arrastrar_un_componente_libre_lo_traslada():
    s = api.Sesion()
    _llamar(s, "create_box", length=10, width=10, height=10)
    _llamar(s, "create_box", length=10, width=10, height=10, x=100)
    _llamar(s, "create_component", bodies=["Cuerpo1"], name="Base", grounded=True)
    _llamar(s, "create_component", bodies=["Cuerpo2"], name="Libre")
    r = _llamar(s, "drag_component", component="Libre", offset=[0, 25, 0])
    assert r["ok"] and r["result"]["moved"] is True
    assert _corrimiento(r, "Libre")[1] == pytest.approx(25, abs=1e-3)


def test_si_no_se_mueve_nada_lo_dice():
    s, _ = _montaje()
    r = _llamar(s, "drag_component", component="Piston", offset=[0, 0, 0])
    assert r["ok"] and r["result"]["moved"] is False
    assert any("No se movió" in a for a in r["avisos"])


def test_con_contactos_el_arrastre_que_choca_se_rechaza_y_no_deja_pendiente():
    s, _ = _montaje()
    assert _llamar(s, "set_contact_mode", mode="all")["ok"]
    r = _llamar(s, "drag_component", component="Piston", offset=[60, 0, 0])      # entra en la pared (x 55..65)
    assert r["ok"] is False and r["error_kind"] == "CONTACT_BLOCKED"
    assert pendiente_de(s.doc) is None
    assert _llamar(s, "drag_component", component="Piston", offset=[50, 0, 0])["ok"]    # tocar no es chocar
    assert _llamar(s, "set_contact_mode", mode="none")["ok"]
    assert _llamar(s, "drag_component", component="Piston", offset=[60, 0, 0])["ok"]


def test_arrastre_con_mouse_contra_la_pared_vuelve_atras_y_avisa(ventana, monkeypatch):  # noqa: F811
    """Ventana: con los contactos prendidos, soltar el mouse con una pieza dentro de otra la deja donde estaba y avisa."""
    from PySide6.QtCore import QEvent, QPointF, Qt
    from test_posicion_ventana import PUNTO, _evento
    v = ventana
    avisos = []
    monkeypatch.setattr(v, "mensaje", lambda texto, ms=5000: avisos.append(texto))

    def arrastrar():
        a = v.visor.proyectar(PUNTO)
        fin = v.visor.proyectar(PUNTO + [100, 0, 0]) - v.visor.proyectar(PUNTO)        # 100 mm hacia la otra pieza (x 70..90)
        _evento(v, QEvent.MouseButtonPress, a, Qt.LeftButton, Qt.LeftButton)
        for i in range(1, 6):
            _evento(v, QEvent.MouseMove, a + QPointF(fin) * (i / 5), Qt.NoButton, Qt.LeftButton)
        _evento(v, QEvent.MouseButtonRelease, a + QPointF(fin), Qt.LeftButton, Qt.NoButton)

    s = api.Sesion(v.doc)
    arrastrar()                                                 # sin contactos: dónde cae la pieza con este gesto
    p = pendiente_de(v.doc)
    assert p is not None
    x, y, z = p.poses()[v.cuerpo][:3, 3]
    v.doc.posicion_pendiente = None
    muro = _llamar(s, "create_box", length=60, width=60, height=60, x=x - 30, y=y - 30, z=z - 30)["result"]["bodies_created"][0]["id"]
    assert _llamar(s, "create_component", bodies=[muro], name="Muro", grounded=True)["ok"]
    assert _llamar(s, "set_contact_mode", mode="all")["ok"]
    arrastrar()                                                 # el mismo gesto ahora cae dentro del muro
    assert pendiente_de(v.doc) is None and any("chocaría" in a for a in avisos)
    assert _llamar(s, "set_contact_mode", mode="none")["ok"]
    arrastrar()
    assert pendiente_de(v.doc) is not None                      # control: sin contactos el mismo gesto sí queda pendiente
