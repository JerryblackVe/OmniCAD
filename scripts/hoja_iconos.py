# -*- coding: utf-8 -*-
"""Hoja del timeline y comparación de dibujos a tamaño real, sin abrir ventanas.

Desde la raíz: clon/.venv/Scripts/python.exe scripts/hoja_iconos.py [salida.png] [--sin-uso]
"""
import argparse
import os
import re
import sys
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "evidencias" / "capturas" / "iconos_timeline.png"
sys.path.insert(0, str(RAIZ / "clon"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))


@lru_cache(maxsize=1)
def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def pasos():
    """Lista ordenada (clave, dibujo) de comandos con paso y tipos sin comando."""
    from omnicad.timeline.operaciones import TIPOS_OPERACION
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.panel_timeline import icono_operacion

    filas, cubiertos = [], set()
    for c in CATALOGO.values():
        if c.CLASE_OP is None:
            continue
        op = c.CLASE_OP("x")
        if hasattr(c, "TIPO_CONSTR"):
            op.p["tipo"] = c.TIPO_CONSTR
        variante = getattr(c, "VARIANTE", None)
        if variante is not None:
            clave, valor = variante
            op.p[clave] = valor
        filas.append((c.CLAVE, icono_operacion(op)))
        cubiertos.add(c.CLASE_OP.TIPO)
    for tipo, clase in TIPOS_OPERACION.items():
        if tipo not in cubiertos:
            filas.append((tipo, icono_operacion(clase("x"))))
    return sorted(filas)


def iconos_usados():
    """Nombres de dibujo que usan los comandos de la cinta y los pasos del timeline."""
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.panel_timeline import ICONO_TIPO

    usados = {c.ICONO for c in CATALOGO.values() if c.ICONO}
    usados.update(nombre for _, nombre in pasos())
    usados.update(ICONO_TIPO.values())
    return usados


def dibujos_sin_uso():
    """Dibujos sin referencias en comandos, timeline ni literales del programa."""
    from omnicad.ui import iconos

    usados = iconos_usados()
    excluidos = {"iconos.py", "iconos_extra.py", "iconos_tema.py"}
    textos = "\n".join(
        ruta.read_text(encoding="utf-8")
        for ruta in (RAIZ / "clon" / "omnicad").rglob("*.py")
        if ruta.name not in excluidos
    )
    # shortcut: aproximación por texto; cuenta también literales en comentarios y docstrings.
    usados.update(re.findall(r"[\"']([a-zA-Z0-9_]+)[\"']", textos))
    prefijos = re.findall(r"icono\(f[\"']([a-z0-9_]+)\{", textos)          # icono(f"orbita_{clave}") usa todos los orbita_*
    return sorted(n for n in set(iconos.DIBUJOS) - usados if not n.startswith(tuple(prefijos)))


@lru_cache(maxsize=None)
def _pixmap(nombre):
    """Dibujo a 24 px compuesto sobre blanco opaco, cacheado por nombre."""
    _app()
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPainter, QPixmap

    from omnicad.ui import iconos, iconos_tema

    pm = QPixmap(24, 24)
    pm.fill(Qt.white)
    pintor = QPainter(pm)
    # El dibujo tal cual (tema claro): con un tema oscuro activo, iconos.pixmap ya pasa por iconos_tema y pinta otro gris.
    pintor.drawPixmap(0, 0, (iconos_tema._original or iconos.pixmap)(nombre, 24, 1))
    pintor.end()
    return pm


def distancia(a, b):
    """Diferencia absoluta media de color (RGB) a 24 px: idénticos 0, blanco/negro 1. 24×3 bytes por fila: sin relleno."""
    from PySide6.QtGui import QImage

    imagen_a = _pixmap(a).toImage().convertToFormat(QImage.Format_RGB888)
    imagen_b = _pixmap(b).toImage().convertToFormat(QImage.Format_RGB888)
    gris_a = np.frombuffer(imagen_a.constBits(), np.uint8).astype(np.int16)
    gris_b = np.frombuffer(imagen_b.constBits(), np.uint8).astype(np.int16)
    return float(np.abs(gris_a - gris_b).mean() / 255)


def mas_cercanos(nombres, n=15):
    """Los n pares distintos con menor distancia, sin repetir nombres ni pares."""
    return sorted((distancia(a, b), a, b) for a, b in combinations(sorted(set(nombres)), 2))[:n]


def hoja(ruta, filas):
    """Guarda un PNG de cinco columnas, a 32/24/16 px en tema claro y oscuro."""
    _app()
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QPainter

    from omnicad.ui import iconos, iconos_tema, temas

    claro = temas.INCLUIDOS["claro_moderno"]["colores"]
    oscuro = temas.INCLUIDOS["oscuro_moderno"]["colores"]
    ancho, alto = 280, 100
    imagen = QImage(5 * ancho, max(1, (len(filas) + 4) // 5) * alto, QImage.Format_ARGB32)
    imagen.fill(QColor(claro["fondo"]))
    pintor = QPainter(imagen)
    pintor.setRenderHint(QPainter.TextAntialiasing)
    fuente = QFont("Segoe UI")
    fuente.setPixelSize(11)
    pintor.setFont(fuente)
    for indice, (clave, nombre) in enumerate(filas):
        x, y = (indice % 5) * ancho, (indice // 5) * alto
        pintor.setPen(QColor(claro["texto"]))
        pintor.drawText(QRectF(x + 4, y, ancho - 8, 22), Qt.AlignCenter, clave)
        for lado, colores in enumerate((claro, oscuro)):
            inicio = x + 4 + lado * 136
            pintor.fillRect(QRectF(inicio, y + 23, 132, 46), QColor(colores["fondo"]))
            for desplazamiento, tam in ((12, 32), (56, 24), (92, 16)):
                pm = iconos.pixmap(nombre, tam, 1)
                if lado == 1:
                    pm = iconos_tema.adaptar(pm, oscuro)
                pintor.drawPixmap(inicio + desplazamiento, y + 30 + (32 - tam) // 2, pm)
        pintor.setPen(QColor("#c62828" if nombre == "caja" else claro["texto"]))
        pintor.drawText(QRectF(x + 4, y + 73, ancho - 8, 22), Qt.AlignCenter, nombre)
    pintor.end()
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not imagen.save(str(ruta), "PNG"):
        raise OSError(f"No se pudo guardar la hoja de íconos en {ruta}")
    return ruta


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("salida", nargs="?", type=Path, default=SALIDA, help="Ruta del PNG de salida")
    argumentos.add_argument("--sin-uso", action="store_true", help="Listar dibujos sin referencias")
    opciones = argumentos.parse_args()
    _app()
    if opciones.sin_uso:
        nombres = dibujos_sin_uso()
        for nombre in nombres:
            print(nombre)
        print(f"Total: {len(nombres)} dibujos sin uso")
    else:
        filas = pasos()
        print(hoja(opciones.salida, filas))
        genericos = sum(nombre == "caja" for _, nombre in filas)
        print(f"{len(filas)} pasos, {genericos} con ícono genérico («caja»)")
