# -*- coding: utf-8 -*-
"""B-608: Empalme o Chaflán sobre una caja (pocas caras, todas planas) calculan la previa en la ventana: el kernel tarda
15-25 ms y el proceso aparte costaba 1,5 s en la VPS y 9-17 s en Windows. Un cuerpo con caras curvas sigue yendo aparte."""
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.timeline.ops_modificar import OpChaflan, OpEmpalme
from omnicad.ui import comando
from omnicad.ui.comandos.modificar import Empalme
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def _llamar(sesion, nombre, **argumentos):
    r = api.llamar(sesion, nombre, argumentos)
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def ventana(tmp_path, monkeypatch):
    monkeypatch.setattr(comando, "PREVIA_APARTE", True)
    s = api.Sesion()
    _llamar(s, "create_box", length=143, width=106, height=40, name="Caja")
    _llamar(s, "chamfer", body="Caja", edges="|Z", distance="5 mm")         # ya modificada: 10 caras, todas planas
    _llamar(s, "create_box", length=40, width=40, height=20, x=200, name="Redonda")
    _llamar(s, "fillet", body="Redonda", edges="|Z", radius="5 mm")          # caras cilíndricas
    app = QApplication.instance() or QApplication([])
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _id(v, nombre):
    return next(c.id for c in v.doc.estado_final.cuerpos.values() if c.nombre == nombre)


@pytest.mark.parametrize("clase", [OpEmpalme, OpChaflan])
def test_empalme_y_chaflan_sobre_una_caja_van_en_la_ventana(ventana, clase):
    caja, redonda = _id(ventana, "Caja"), _id(ventana, "Redonda")
    p = ventana.ejecutar_comando(Empalme())
    assert p._ms_previa is None                                              # sin medida previa
    assert not p._previa_pesada(clase("opX", aristas=[{"cuerpo": caja}]))
    assert p._previa_pesada(clase("opX", aristas=[{"cuerpo": redonda}]))     # caras curvas: aparte, como siempre
    assert p._previa_pesada(clase("opX", aristas=[{"cuerpo": "op9.c9"}]))    # un cuerpo que no existe: camino normal


def test_otras_operaciones_sobre_la_caja_siguen_aparte(ventana):
    from omnicad.timeline.ops_modificar import OpVaciado
    p = ventana.ejecutar_comando(Empalme())
    assert p._previa_pesada(OpVaciado("opX", cuerpos=[_id(ventana, "Caja")]))


def test_empalme_de_la_caja_ya_achaflanada_no_abre_el_proceso_aparte(ventana, monkeypatch):
    """Previa y Aceptar de punta a punta, sin trabajador: el radio que no entra lo dice la previa en la ventana."""
    import numpy as np

    from omnicad.nucleo import aislado
    from omnicad.nucleo import referencias as refs
    aislado.cerrar_trabajador()
    monkeypatch.setattr(aislado, "_trabajador_vivo", lambda: pytest.fail("abrió el proceso aparte"))
    caja = _id(ventana, "Caja")
    forma = ventana.doc.estado_final.cuerpos[caja].forma
    arriba = [refs.referencia(caja, s, forma) for s in refs.subformas(forma, "arista")
              if np.isclose(refs.firma(s)["medio"][2], 40) and abs(refs.firma(s)["medio"][0] - 71.5) < 1e-6]
    pasos = len(ventana.doc.operaciones)
    p = ventana.ejecutar_comando(Empalme())
    p.set_valor("aristas", [{"ref": r} for r in arriba])
    p.set_valor("radio", "50 mm")
    p._t_previa.stop()
    p._calcular_previa()
    assert not p._previa_ok and not p._previa_aparte and "entra" in p.mensaje.text()
    p.set_valor("radio", "5 mm")
    p._t_previa.stop()
    p._calcular_previa()
    assert p._previa_ok and not p._previa_aparte
    p.aceptar()
    assert len(ventana.doc.operaciones) == pasos + 1 and ventana.doc.resultados[-1].estado == "ok"
