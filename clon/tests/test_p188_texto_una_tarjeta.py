# -*- coding: utf-8 -*-
"""P-188: al editar un texto hay UNA tarjeta (Carácter): la barra flotante de valores queda oculta y el panel de
objetos vectoriales no se abre encima. Ángulo, ✓ y ✕ viven en Carácter."""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api.herramientas_boceto import op_boceto  # noqa: E402
from omnicad.ui import editor_boceto, modo_boceto  # noqa: E402


@pytest.fixture
def modo_texto():
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {"plane": "XY"})["ok"]
    assert api.llamar(s, "add_text", {"text": "Hola", "x": 10, "y": 20})["ok"]
    b = op_boceto(s, None).boceto.copia()
    tid = next(i for i, c in b.curvas.items() if c.tipo == "texto")
    ventana = QWidget()
    ventana.doc = s.doc
    ventana.area = SimpleNamespace(reubicar=lambda: None)
    ventana.mensaje = lambda *a: None
    modo = modo_boceto.ModoBoceto(ventana)
    lz = editor_boceto.Lienzo(b, lambda *a: ventana.doc.parametros.evaluar(*a))
    lz.valores_parametros = lambda: ventana.doc.parametros.valores()
    modo.lienzo, modo.boceto = lz, b
    modo.paleta, modo.tarjeta = modo_boceto.PaletaBoceto(), modo_boceto.TarjetaHerramienta()
    area = QWidget()
    modo.caracter = modo._paneles["caracter"] = modo._armar_caracter(area)
    lz.texto_en_edicion.connect(modo._opciones_de_texto)
    yield lz, tid, modo
    for w in (lz, modo.paleta, modo.tarjeta, area, ventana):
        w.close()
        w.deleteLater()
    app.processEvents()


def test_una_tarjeta_al_editar_texto(modo_texto):
    lz, tid, modo = modo_texto
    lz.editar_texto(tid, lz.a_px(10, 20))
    assert lz.entrada is not None and not lz.entrada.isVisible()          # barra oculta, sigue siendo el motor
    assert modo.caracter.fila_aceptar.isVisibleTo(modo.caracter)          # ✓ y ✕ en Carácter
    assert not modo.caracter._cuerpo_de["Espaciado"].isVisibleTo(modo.caracter)   # lo avanzado, plegado
    assert modo.caracter.alineacion.isVisibleTo(modo.caracter)            # alineación a la vista (UX-5)
    assert not modo.caracter._cuerpo_de["Alineación y curva"].isVisibleTo(modo.caracter)
    assert modo.caracter.b_ayuda.text() == "?"                            # UX-13
    modo.caracter.angulo.setValue(30.0)                                   # el ángulo llega a la barra oculta
    assert float(lz.entrada.campos[2].text().replace(",", ".")) == pytest.approx(30.0)
    modo.caracter.cancelado.emit()
    assert lz.entrada is None


def test_aceptar_desde_caracter_guarda_el_angulo(modo_texto):
    lz, tid, modo = modo_texto
    lz.editar_texto(tid, lz.a_px(10, 20))
    modo.caracter.angulo.setValue(30.0)
    modo.caracter.aceptado.emit()
    assert lz.entrada is None
    assert lz.b.curvas[tid].angulo == pytest.approx(30.0)


def test_texto_nuevo_tambien_una_tarjeta(modo_texto):
    lz, _tid, modo = modo_texto
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, 0.0)))
    lz.clics.append((None, (0.0, 0.0)))                                   # mismo lugar = texto de 5 mm
    lz._procesar_clics()
    assert lz.entrada is not None and lz.entrada.isHidden()               # P-188: la barra no es una 2.ª tarjeta
    assert modo.caracter.fila_aceptar.isVisibleTo(modo.caracter)
