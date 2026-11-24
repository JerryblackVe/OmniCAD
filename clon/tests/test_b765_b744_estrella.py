"""B-765 y B-744: la estrella no persiste un grosor inválido del Nervio."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.nucleo import preajustes as pre  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.ui.comando import ContextoComando, PanelComando  # noqa: E402
from omnicad.ui.comandos.crear import Nervio  # noqa: E402
from omnicad.ui.visor3d import Visor3D  # noqa: E402


def test_estrella_valida_antes_de_guardar(tmp_path, monkeypatch):
    ruta = tmp_path / "preajustes.json"
    monkeypatch.setenv(pre.VAR_PREAJUSTES, str(ruta))
    pre.guardar("nervio", "Mis valores", {"espesor": "3 mm"})
    pre.definir_defecto("nervio", "Mis valores")
    app = QApplication.instance() or QApplication([])
    doc = Documento()
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    panel = PanelComando(Nervio(), ContextoComando(doc), visor)
    panel.show()
    app.processEvents()
    campo = panel.widgets["espesor"]
    anterior = ruta.read_bytes()
    try:
        for texto in ("abc", "2+", "-5", "1e9", ""):
            campo.setFocus()
            campo.selectAll()
            QTest.keyClick(campo, Qt.Key_Backspace)
            if texto:
                QTest.keyClicks(campo, texto)
            QTest.mouseClick(panel.boton_estrella, Qt.LeftButton)
            assert "No se guardó: Grosor no es válido" in panel.mensaje.text()
            assert ruta.read_bytes() == anterior
        campo.setFocus()
        campo.selectAll()
        QTest.keyClicks(campo, "4 mm")
        QTest.mouseClick(panel.boton_estrella, Qt.LeftButton)
        assert "siempre" in panel.mensaje.text()
        assert pre.listar("nervio")["default"] == "Mis valores"
        assert pre.valores_iniciales("nervio")["espesor"] == "4 mm"
    finally:
        panel.cancelar()
