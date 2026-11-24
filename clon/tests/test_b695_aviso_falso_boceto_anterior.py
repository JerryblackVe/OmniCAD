# -*- coding: utf-8 -*-
"""B-695: editar el texto de un boceto ANTERIOR a una extrusión no debe anunciar errores de pasos posteriores."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.nucleo import fuentes  # noqa: E402

# B-851: «DejaVu Sans» es la predeterminada de Linux y en Windows no está: se prueba con la primera instalada.
FUENTE = next((n for n in ("DejaVu Sans", "Arial") if fuentes.resolver_fuente(n)), fuentes.familias()[0])


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("b695") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1400, 900)
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()


def _doc():
    s = api.Sesion()
    r = api.llamar(s, "sketch_from_spec", {"name": "Letras", "entities": [
        {"type": "text", "text": "ABCDE", "x": 0, "y": 0, "height": 10, "font": FUENTE},
        {"type": "rectangle", "corner1": [-5, -5], "corner2": [40, 20]}]})
    assert r["ok"], r
    return s


def test_editar_texto_anterior_no_anuncia_errores(ventana):
    s = _doc()
    r = api.llamar(s, "extrude", {"sketch": "Letras", "profile": "text", "distance": 5})
    assert r["ok"], r
    r = api.llamar(s, "move_body", {"body": "op2.c5", "translate": [0, 0, 3]})
    assert r["ok"], r
    cuerpos = [c for c in s.doc.estado_final.cuerpos]
    assert cuerpos, "la extrusión no creó cuerpos"
    ventana.set_documento(s.doc)
    QTest.qWait(20)
    avisos = []
    orig = ventana.aviso_flotante
    ventana.aviso_flotante = lambda t, n="advertencia", d=None: (avisos.append((n, t)), orig(t, n, d))[1]
    op = s.paso("Letras")
    QTest.qWait(50)
    ventana.editar_operacion(op.id)
    for valor in ("ABC", "ABCD", "VWXYZ"):       # como al teclear: el cuerpo op2.c5 deja de existir y vuelve
        ventana.modo_boceto._editar_parametro_texto("Text", valor)
        QTest.qWait(30)
    assert ventana.modo_boceto.terminar()
    QTest.qWait(50)
    assert ventana.doc.parametros.obtener("Text").expresion == "VWXYZ"
    assert not [a for a in avisos if a[0] == "error"], avisos
    assert all(r.estado != "error" for r in ventana.doc.resultados)
