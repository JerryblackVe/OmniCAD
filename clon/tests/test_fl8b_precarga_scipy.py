# -*- coding: utf-8 -*-
"""FL-8b: el primer boceto que se cierra no carga scipy en el hilo de la ventana (2,3 a 3,3 s en Windows).
La ventana lo carga en un hilo aparte al abrir."""
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

CLON = Path(__file__).resolve().parent.parent
GUION = """
import sys
from omnicad.restricciones import Boceto
from omnicad.restricciones.solver import resolver
from omnicad.ui.ventana import _precargar_scipy
if sys.argv[1] == "con":
    _precargar_scipy()
antes = set(sys.modules)
b = Boceto()
b.agregar_rectangulo((0, 0), (30, 20))
b.agregar_cota("distancia", [next(iter(b.curvas))], "50")       # sin una cota que mueva algo no corre least_squares
assert resolver(b, {k: 50.0 for k in b.cotas}).ok
print(" ".join(sorted(m for m in set(sys.modules) - antes if m.startswith("scipy"))))
"""


@pytest.mark.parametrize("precarga", ["sin", "con"])
def test_la_precarga_cubre_todo_lo_que_importa_el_solver(precarga):
    r = subprocess.run([sys.executable, "-c", GUION, precarga], cwd=CLON, capture_output=True, text=True, timeout=120,
                       env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    assert r.returncode == 0, r.stderr
    importados = r.stdout.split()
    if precarga == "sin":
        assert "scipy.optimize" in importados        # el rectángulo de la prueba sí pasa por least_squares
    else:
        assert importados == []                       # nada queda para el hilo de la ventana


def test_la_ventana_precarga_en_un_hilo_aparte(tmp_path, monkeypatch):
    from PySide6.QtCore import QEventLoop, QSettings, QTimer
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui import ventana
    from omnicad.ui.preferencias import Preferencias
    hilos, listo = [], threading.Event()
    monkeypatch.setattr(ventana, "_precargar_scipy", lambda: (hilos.append(threading.current_thread()), listo.set()))
    v = ventana.VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    try:
        assert hilos == []                            # no compite con el arranque de la ventana
        bucle = QEventLoop()
        QTimer.singleShot(1500, bucle.quit)
        bucle.exec()                                  # como app.exec: suelta el GIL (QTest.qWait no)
        assert listo.wait(10)                         # el hilo ya arrancó; con la máquina cargada puede tardar en correr
        assert len(hilos) == 1 and hilos[0] is not threading.main_thread()
    finally:
        v.doc.modificado = False
        v.close()
        v.deleteLater()
