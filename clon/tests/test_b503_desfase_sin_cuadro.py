# -*- coding: utf-8 -*-
"""B-503 (parte 2): Cara de desfase sobre letras. Si el paso nuevo falla, el panel lo dice en un renglón, sin cuadro, y
el documento queda como estaba; y el mensaje del núcleo ya no habla de roscas cuando son letras (regla 14)."""
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from _calculo_aparte import esperar_barra
from omnicad import api
from omnicad.nucleo import geometria as geo, motor
from omnicad.nucleo import referencias as refs
from omnicad.nucleo import solidos_modificar as sm
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import ErrorOperacion, OpPrimitiva
from omnicad.ui.comandos.primitivas import Caja
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_la_letra_que_no_se_desfasa_no_nombra_la_rosca(monkeypatch):
    """Si el núcleo no logra desfasar las letras (estudio de E11), el mensaje no habla de roscas."""
    s = api.Sesion()
    for nombre, args in (("create_box", {"length": 40, "width": 20, "height": 3}),
                         ("create_sketch", {"plane": ">Z", "name": "T"}),
                         ("add_text", {"text": "t", "x": -5, "y": -5, "height": 10}),
                         ("extrude", {"sketch": "T", "profile": "text", "distance": 3, "operation": "join"})):
        assert api.llamar(s, nombre, args)["ok"]
    forma = next(iter(s.doc.estado_final.cuerpos.values())).forma
    letra = [c for c in geo.caras(forma) if refs.cara_libre(c)]
    assert letra
    ok = sm.desfasar_caras(forma, letra[:1], 0.5)     # B-842: la «t» ahora sí se desfasa por el contorno
    assert geo.es_valida(ok) and geo.volumen(ok) > geo.volumen(forma)
    monkeypatch.setattr(sm, "_desfase_kernel", lambda *a: (None, False))
    monkeypatch.setattr(sm, "_desfase_por_contorno", lambda *a: None)
    with pytest.raises(geo.ErrorGeometria) as e:
        sm.desfasar_caras(forma, letra[:1], 0.5)
    assert str(e.value) == "⚠ No se pudo desfasar estas caras 0.5 mm"


@pytest.fixture
def ventana(tmp_path):
    app = QApplication.instance() or QApplication([])
    with motor.fijar_motor("opencascade"):
        v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
        d = Documento()
        d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="2", largo="5", alto="3"))
        v.set_documento(d)
        v.show()
        app.processEvents()
        yield v
        if v.panel is not None:
            v.panel.cancelar()
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        app.processEvents()


def test_aceptar_un_paso_que_falla_deja_un_renglon_en_el_panel_sin_cuadro(ventana, monkeypatch):
    v = ventana
    cuadros = []
    for tipo in ("critical", "warning", "information"):
        monkeypatch.setattr(QMessageBox, tipo, staticmethod(lambda *a: cuadros.append(a[1:])))
    comando = Caja()
    comando.PREVIA = False
    panel = v.ejecutar_comando(comando)
    campo = panel.widgets["ancho"]
    QTest.mouseClick(campo, Qt.LeftButton)
    QTest.keyClick(campo, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClicks(campo, "4 mm")
    QTest.qWait(280)
    antes, deshacer, rehacer = v.doc.a_dict(), list(v.doc._deshacer), list(v.doc._rehacer)

    original = OpPrimitiva.ejecutar

    def no_se_puede(self, estado, ctx):
        if self.id == "op1":
            return original(self, estado, ctx)
        raise ErrorOperacion("No se pudo hacer esta caja")
    monkeypatch.setattr(OpPrimitiva, "ejecutar", no_se_puede)
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    esperar_barra(v)
    assert cuadros == []
    assert v.panel is panel and panel.isVisible()
    assert panel.mensaje.text() == "No se pudo hacer esta caja" and panel.icono_mensaje.text() == "✖"
    assert v.doc.a_dict() == antes and v.doc._deshacer == deshacer and v.doc._rehacer == rehacer
    assert v.doc.resultados[-1].estado == "ok"
