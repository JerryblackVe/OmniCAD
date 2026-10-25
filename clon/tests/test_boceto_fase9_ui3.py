"""UI de texto, tercera tanda: editar un texto ligado desde el editor sincroniza su parámetro Text."""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api.herramientas_boceto import op_boceto  # noqa: E402
from omnicad.timeline.operaciones import _contenido_texto  # noqa: E402
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
    lz.editar_parametro_texto = modo._editar_parametro_texto
    lz.valores_parametros = lambda: ventana.doc.parametros.valores()
    modo.lienzo, modo.boceto = lz, b
    modo.paleta, modo.caracter = modo_boceto.PaletaBoceto(), modo_boceto.PanelCaracter()
    lz.texto_en_edicion.connect(modo._opciones_de_texto)
    yield s, lz, tid
    for w in (lz, modo.paleta, modo.caracter, ventana):
        w.close()
        w.deleteLater()
    app.processEvents()


def _texto_real(s, tid):
    """Texto que ve el documento recalculado (con los valores de los parámetros)."""
    t = op_boceto(s, None).boceto.curvas[tid]
    return _contenido_texto(t, s.doc.parametros.valores())


def test_editar_texto_ligado_sincroniza_el_parametro(modo_texto):
    s, lz, tid = modo_texto
    assert s.doc.parametros.valores()["Text"] == "Hola"
    lz.editar_texto(tid, lz.a_px(10, 20))
    lz.entrada.campos[0].setText("Chau")
    lz.entrada.aceptado.emit([c.text() for c in lz.entrada.campos])
    assert s.doc.parametros.valores()["Text"] == "Chau"
    assert lz.b.curvas[tid].texto == "{Text}"
    assert _texto_real(s, tid) == "Chau"
    # deshacer el cambio del editor deja el boceto ligado y el parámetro no queda desfasado
    lz.deshacer()
    assert lz.b.curvas[tid].texto == "{Text}"
    assert _contenido_texto(lz.b.curvas[tid], s.doc.parametros.valores()) == s.doc.parametros.valores()["Text"]
    # el paso de deshacer del documento devuelve el valor original del parámetro
    assert api.llamar(s, "undo", {})["ok"]
    assert s.doc.parametros.valores()["Text"] == "Hola"
    assert _texto_real(s, tid) == "Hola"
