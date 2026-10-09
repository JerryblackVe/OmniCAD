# -*- coding: utf-8 -*-
"""Ícono de la app y portada (pantalla de carga): están, se leen y el ícono trae los tamaños de Windows."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize  # noqa: E402
from PySide6.QtGui import QIcon, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad import RECURSOS  # noqa: E402
from omnicad.ui import arranque  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def test_icono_ico_con_los_tamanos_de_windows_y_png_para_linux():
    _app()
    tamanos = QIcon(str(RECURSOS / "omnicad.ico")).availableSizes()
    assert {QSize(t, t) for t in (16, 24, 32, 48, 256)} <= set(tamanos)
    for nombre, lado in (("omnicad_256.png", 256), ("omnicad_512.png", 512)):
        img = QImage(str(RECURSOS / nombre))
        assert (img.width(), img.height()) == (lado, lado) and img.hasAlphaChannel()
        assert img.pixelColor(0, 0).alpha() == 0                 # esquinas transparentes (sin el verde de origen)


def test_poner_icono_y_portada():
    app = _app()
    arranque.poner_icono(app)
    assert not app.windowIcon().isNull()
    portada = arranque.mostrar_portada(app)
    assert portada is not None and portada.isVisible()
    ancho_logico = portada.pixmap().width() / portada.pixmap().devicePixelRatio()
    assert ancho_logico <= arranque.ANCHO_PORTADA + 1
    portada.close()
    portada.deleteLater()


def test_la_version_de_pyproject_es_la_de_omnicad():
    """Dos lugares con la versión: omnicad.VERSION (app e instaladores) y pyproject.toml (pip)."""
    import tomllib
    from pathlib import Path

    from omnicad import VERSION
    datos = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert datos["project"]["version"] == VERSION
