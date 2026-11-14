# -*- coding: utf-8 -*-
"""B-440: salir del boceto y poner una cota trababan la ventana (E11: 3043 ms al salir con un texto recién escrito,
478-546 ms por cota, con 42 geometrías). Medido en la VPS con 24 geometrías, un texto «HOLA» y 61 curvas:
- salir con un texto nuevo: 435-750 ms → 250-300 ms. El relleno clasificaba cada letra dos veces (por texto y por
  objeto) y en cada pasada mallaba la letra para hallar un punto interior (~4 ms por letra);
- salir con un texto que ya estaba: 150-210 ms → 95-130 ms (la capa vectorial se rearmaba con otro solver, ~70 ms)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402
from omnicad.nucleo import perfiles as perfiles_mod  # noqa: E402

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

TEXTO = {"type": "text", "text": "HOLA BOB", "x": 0, "y": 0, "height": 10, "font": "DejaVu Sans"}


def _boceto_con_texto(s):
    r = api.llamar(s, "sketch_from_spec", {"name": "Letras", "entities": [
        TEXTO, {"type": "rectangle", "corner1": [-5, -5], "corner2": [80, 20]}]})
    assert r["ok"], r
    return s.paso("Letras")


def test_cada_letra_se_malla_una_sola_vez(monkeypatch):
    s = api.Sesion()
    op = _boceto_con_texto(s)
    br = s.doc.estado_final.bocetos[op.id]
    llamadas = []
    original = perfiles_mod._punto_adentro
    monkeypatch.setattr(perfiles_mod, "_punto_adentro", lambda cara: (llamadas.append(cara), original(cara))[1])
    primera = perfiles_mod.sin_huecos(br.perfiles, br.boceto)
    letras = sum(1 for p in br.perfiles if p.firma and len(p.firma) == 1 and br.boceto.curvas[next(iter(p.firma))].tipo == "texto")
    assert letras > 0 and len(llamadas) == letras      # antes, el doble: por texto y por objeto
    # el relleno vuelve a clasificar en cada cota y al terminar: `detectar` devuelve los mismos perfiles de su caché
    assert perfiles_mod.detectar_boceto(br.boceto, br.plano)[0] is br.perfiles[0]
    assert [id(p) for p in perfiles_mod.sin_huecos(br.perfiles, br.boceto)] == [id(p) for p in primera]
    assert len(llamadas) == letras
    assert len(primera) == 8           # el marco y las 7 letras, sin los huecos de la O, las A y las B


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("b440") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1400, 900)
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def test_salir_del_boceto_no_rearma_la_capa_del_texto(ventana, monkeypatch):
    from omnicad.ui import vectores_en_vista
    s = api.Sesion()
    op = _boceto_con_texto(s)
    ventana.set_documento(s.doc)
    QTest.qWait(20)
    capa = ventana.vectores.capas[op.id]
    creadas = []
    original = vectores_en_vista.LienzoVectorial.__init__
    monkeypatch.setattr(vectores_en_vista.LienzoVectorial, "__init__",
                        lambda self, *a: (creadas.append(self), original(self, *a))[1])
    ventana.editar_operacion(op.id)
    assert ventana.modo_boceto.activo and op.id not in ventana.vectores.capas       # en edición no recibe clics
    lz = ventana.modo_boceto.lienzo
    linea = lz.b.agregar_linea(lz.b.agregar_punto(100, 0), lz.b.agregar_punto(130, 10))
    assert ventana.modo_boceto.terminar()
    QTest.qWait(20)
    assert ventana.vectores.capas[op.id] is capa and not creadas
    assert linea in capa.b.curvas                       # la capa muestra el boceto terminado, no el de antes
    assert ventana._intentar(lambda: ventana.doc.eliminar(op.id))
    QTest.qWait(20)
    assert op.id not in ventana.vectores.capas and op.id not in ventana.vectores.dormidas
    ventana.doc.modificado = False

