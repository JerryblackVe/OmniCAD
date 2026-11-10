# -*- coding: utf-8 -*-
"""P-122: al cerrar el panel de un comando, el visor se redibuja una vez con el estado nuevo. Antes `_cerrar` emitía la
previa vacía y la ventana redibujaba también el estado VIEJO (antes del paso): 1,1 s de más al aceptar un Agujero en
el llavero de Gerardo (cuerpo de 414 caras), y un instante del modelo sin el agujero."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402
from omnicad.api import selectores as sl  # noqa: E402

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("p122") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1400, 900)
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


@pytest.fixture
def v(ventana, monkeypatch):
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    ventana.set_documento(s.doc)
    QTest.qWait(20)
    ventana.sesion = s
    ventana.mostrados = []
    original = ventana.visor.set_modelo
    monkeypatch.setattr(ventana.visor, "set_modelo", lambda estado, *a, **k: (ventana.mostrados.append(estado),
                                                                               original(estado, *a, **k))[1])
    yield ventana
    if ventana.panel is not None:
        ventana.panel.cancelar()
    ventana.doc.modificado = False


def _agujero(v):
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    v.ejecutar_comando(CATALOGO["agujero"]())
    p = v.panel
    (c, e), = sl.elegir(v.sesion, ">Z", "cara", None)
    hit = hit_desde_ref(sl.referencia(c, e), v.doc.estado_final)
    hit["punto"] = (50.0, 30.0, 20.0)
    p._activar(next(x for x in p.campos if x.clave == "colocacion"))
    p._elegida(hit)
    QTest.qWait(50)
    assert p._previa_ok, p.mensaje.text()
    return p


def test_aceptar_no_redibuja_el_estado_viejo(v):
    p = _agujero(v)
    viejo = p.ctx.estado
    v.mostrados.clear()
    p.aceptar()
    QTest.qWait(20)
    assert len(v.doc.operaciones) == 2 and v.panel is None
    assert viejo not in v.mostrados, "se redibujó el modelo de antes del agujero"
    assert v.mostrados[-1] is v.doc.estado_final


def test_cancelar_redibuja_una_vez_sin_la_previa(v):
    p = _agujero(v)
    v.mostrados.clear()
    p.cancelar()
    QTest.qWait(20)
    assert len(v.doc.operaciones) == 1 and v.panel is None
    assert v.mostrados == [v.doc.estado_final]
