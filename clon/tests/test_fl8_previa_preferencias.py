# -*- coding: utf-8 -*-
"""FL-8: la vista previa de Preferencias se repinta una sola vez por tanda de cambios (arrastrar un control o pasar por las
tarjetas de temas repintaba toda la aplicación en cada paso, 0,3 a 1 s cada uno); Aplicar y Cancelar no esperan."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtCore import QSettings
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from omnicad.ui import temas
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal

    QApplication.instance() or QApplication([])
    carpeta = tmp_path_factory.mktemp("fl8_previa")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    QTest.qWait(1)
    yield v
    temas.activar_tipografia()
    v.doc.modificado = False
    v.close()
    v.deleteLater()


def _esperar_la_tanda(v):
    from PySide6.QtTest import QTest
    from omnicad.ui.ventana import PLAZO_PREVIA_PREFERENCIAS_MS
    QTest.qWait(PLAZO_PREVIA_PREFERENCIAS_MS + 120)


def test_una_tanda_de_cambios_repinta_una_sola_vez_con_el_ultimo_valor(ventana):
    llamadas = []
    for k in range(6):                                       # pasar por seis tarjetas de temas
        ventana._pedir_previa("tema", lambda c: llamadas.append(c), f"tema{k}")
    assert llamadas == []                                    # el control ya se movió; lo pesado espera
    _esperar_la_tanda(ventana)
    assert llamadas == ["tema5"]


def test_cada_clase_de_cambio_se_aplica_una_vez_y_en_orden(ventana):
    llamadas = []
    ventana._pedir_previa("tema", lambda: llamadas.append("tema"))
    ventana._pedir_previa("asas", lambda: llamadas.append("asas"))
    ventana._pedir_previa("tema", lambda: llamadas.append("tema2"))      # reemplaza al primero y pasa al final
    _esperar_la_tanda(ventana)
    assert llamadas == ["asas", "tema2"]


def test_aplicar_y_cancelar_no_esperan_ni_dejan_nada_pendiente(ventana, monkeypatch):
    llamadas = []
    monkeypatch.setattr(ventana, "aplicar_preferencias", lambda: llamadas.append("preferencias"))
    monkeypatch.setattr(ventana, "aplicar_tema", lambda *a: llamadas.append("tema"))
    ventana._pedir_previa("asas", lambda: llamadas.append("asas"))
    ventana._aplicar_ahora()                                 # Aplicar: lo pendiente no se pierde, y después todo lo guardado
    assert llamadas == ["asas", "preferencias"] and not ventana._t_previa.isActive() and ventana._previa_pendiente == []
    llamadas.clear()
    ventana._pedir_previa("tema", lambda: llamadas.append("pendiente"))
    ventana._cancelar_previa()                               # Cancelar: vuelve al tema guardado
    assert llamadas == ["tema"] and not ventana._t_previa.isActive()
    _esperar_la_tanda(ventana)
    assert llamadas == ["tema"]                              # lo pendiente no se aplicó después


def test_mover_un_control_de_preferencias_tarda_menos_de_100_ms(ventana):
    """El escenario (i) de FL-8: cada control del diálogo responde en menos de 100 ms (lo pesado queda para después)."""
    import time

    from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QSlider, QSpinBox

    from omnicad.ui.preferencias import DialogoPreferencias

    dlg = DialogoPreferencias(ventana.prefs, ventana, "general")
    dlg.tema_elegido.connect(lambda clave: ventana._pedir_previa("tema", ventana.aplicar_tema, clave))
    dlg.apariencia_cambiada.connect(lambda: ventana._pedir_previa("tema", ventana.aplicar_tema))
    dlg.graficos_cambiados.connect(lambda: ventana._pedir_previa("preferencias", ventana.aplicar_preferencias))
    dlg.asas_cambiadas.connect(lambda: ventana._pedir_previa("asas", ventana._aplicar_estilo_asas))
    lentos = []
    for clave in ("interfaz/tamano_pct", "interfaz/fuente", "boceto/tamano_cotas_pct", "general/tema", "asas/puntos_tamano_pct"):
        c = dlg.controles[clave]
        t = time.perf_counter()
        if isinstance(c, QComboBox):
            c.setCurrentIndex((c.currentIndex() + 1) % c.count())
        elif isinstance(c, (QSlider, QSpinBox, QDoubleSpinBox)):
            c.setValue(c.value() + (1 if c.value() < c.maximum() else -1))
        elif isinstance(c, QCheckBox):
            c.setChecked(not c.isChecked())
        dt = time.perf_counter() - t
        if dt >= 0.1:
            lentos.append((clave, round(dt, 3)))
    ventana._cancelar_previa()
    dlg.reject()
    assert lentos == []
