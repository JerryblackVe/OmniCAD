"""Vigilante, privacidad de Qt y encendido/apagado reversible en una ventana real."""
import json
import sys
import time

from PySide6.QtCore import QSettings, qWarning
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import registro_uso as ru
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def test_vigilante_muestras_y_ganchos_reversibles(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    anterior = sys.excepthook
    vistos = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: vistos.append(args))
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    v.show()
    c = v.registro_uso
    try:
        assert not c.reloj.isActive() and ru.activo is None
        v.prefs["general/registro_uso"] = True
        v.aplicar_preferencias()
        assert c.indicador.isVisible() and c.reloj.isActive()
        time.sleep(0.35)
        QTest.qWait(80)
        qWarning("SECRETO QT C:/datos/privado")
        e = ValueError("SECRETO SLOT")
        sys.excepthook(type(e), e, None)
        c._muestra -= 40                                     # la cadencia de fábrica es 30 s, no 5
        v.visor._cuadros_uso.extend([10, 20, 100])
        c._latido()
        ru.activo.cola.join()
        es = [json.loads(l) for p in ru.carpeta().glob("sesion_*.jsonl") for l in p.read_text(encoding="utf-8").splitlines()]
        assert {"bloqueo_ui", "error", "memoria", "visor_cuadros"} <= {e["tipo"] for e in es}
        volcado = json.dumps(es, ensure_ascii=False)
        assert "SECRETO QT" not in volcado and "privado" not in volcado    # lo que dice Qt: solo su longitud
        assert "SECRETO SLOT" in volcado                       # el texto de una excepción de la app sí se guarda
        assert len(vistos) == 1
        v.prefs["general/registro_uso"] = False
        v.aplicar_preferencias()
        assert not c.reloj.isActive() and not c.indicador.isVisible() and ru.activo is None
        assert sys.excepthook != c._excepcion
        assert v.visor._cuadros_uso is None
        app.processEvents()
    finally:
        c.configurar(False)
        v.doc.modificado = False
        v.close()
        v.deleteLater()
        sys.excepthook = anterior
        ru.ultimo = None
