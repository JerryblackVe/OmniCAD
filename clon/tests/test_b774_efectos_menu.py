"""B-774: el arranque desactiva las animaciones de los menús."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from omnicad.ui.arranque import desactivar_efectos_menu


def test_b774_efectos_de_menu_apagados():
    app = QApplication.instance() or QApplication([])
    efectos = (Qt.UI_FadeMenu, Qt.UI_AnimateMenu)
    anteriores = [app.isEffectEnabled(e) for e in efectos]
    try:
        for efecto in efectos:
            app.setEffectEnabled(efecto, True)
        desactivar_efectos_menu(app)
        assert not any(app.isEffectEnabled(e) for e in efectos)
    finally:
        for efecto, anterior in zip(efectos, anteriores, strict=True):
            app.setEffectEnabled(efecto, anterior)


def test_b774_arranque_pide_apagar_ambos_efectos(monkeypatch):
    app = QApplication.instance() or QApplication([])
    llamadas = []
    monkeypatch.setattr(app, "setEffectEnabled", lambda efecto, activo: llamadas.append((efecto, activo)))
    desactivar_efectos_menu(app)
    assert llamadas == [(Qt.UI_FadeMenu, False), (Qt.UI_AnimateMenu, False)]
