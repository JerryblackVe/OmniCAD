# -*- coding: utf-8 -*-
"""Gramática visual de los íconos (docs/plan_iconos.md › Gramática), lo que se puede medir sobre los dibujos reales:
margen de 2 unidades en la grilla 32×32 y color de familia. El resto (una silueta por verbo, insignias en una sola
esquina) lo miden `test_iconos_unicos.py` y `test_insignias.py`."""
import numpy as np
import pytest
from test_iconos_extra import SECCIONES
from test_iconos_unicos import hoja_iconos  # noqa: F401  (fixture: carga scripts/hoja_iconos.py con Qt offscreen)

MARGEN = 2.0            # unidades libres a cada borde de la grilla 32×32
TOLERANCIA = 0.5        # se mide a dos píxeles por unidad: un píxel de antialias
# Tono dominante (grados, centro de un cajón de 30°) de los píxeles con color de cada familia de la cinta.
TONO_FAMILIA = {"SÓLIDO / CREAR": 195, "MODIFICAR": 195, "CHAPA": 195, "PLÁSTICO": 195,    # azul
                "SUPERFICIE": 45,                                                          # naranja / ámbar
                "MALLA": 165}                                                              # verde azulado
EXCEPCIONES_COLOR = {
    "relleno_contorno": "el relleno de la región se ve naranja",
    "aspecto": "muestra de color: no pertenece a una familia",
    "material_fisico": "muestra de material: no pertenece a una familia",
    "administrar_materiales": "muestras de materiales: no pertenece a una familia",
    "crear_forma": "familia Forma (T-Splines): violeta",
    "suprimir": "el tachado es rojo",
    "reemplazar_cara": "la cara nueva es una superficie (ámbar)",
    "convertir_malla": "convierte entre sólido y malla: lleva los dos colores",
    "cortar_plano": "el plano de corte es naranja",
    "limpiar_malla": "la escoba amarilla es la acción",
}


@pytest.fixture(autouse=True)
def _con_qt(hoja_iconos):  # noqa: F811
    """Los tres tests dibujan con QPixmap: la fixture de test_iconos_unicos crea la aplicación Qt offscreen."""


def _pixeles(nombre):
    """Matriz RGBA (64×64: dos píxeles por unidad de la grilla) del dibujo tal como lo ve el usuario."""
    from PySide6.QtGui import QImage

    from omnicad.ui import iconos
    img = iconos.pixmap(nombre, 64, 1).toImage().convertToFormat(QImage.Format_ARGB32)
    bgra = np.frombuffer(img.constBits(), np.uint8).reshape(64, 64, 4)
    return bgra[..., [2, 1, 0, 3]].astype(float) / 255


def margen(nombre):
    """Unidades de la grilla libres entre el dibujo y el borde más cercano."""
    ys, xs = np.where(_pixeles(nombre)[..., 3] > 0.24)
    return min(xs.min(), ys.min(), 63 - xs.max(), 63 - ys.max()) / 2


def tono_dominante(nombre):
    """Tono (grados, cajón de 30°) que más píxeles con color tiene; None si el dibujo no tiene color (acero, grises)."""
    px = _pixeles(nombre)
    r, g, b, a = (px[..., i][px[..., 3] > 0.24] for i in range(4))
    mayor, menor = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    con_color = ((mayor - menor) / np.maximum(mayor, 1e-6) > 0.25) & (mayor > 0.35)
    if con_color.sum() < 10:
        return None
    r, g, b, mayor, menor = (v[con_color] for v in (r, g, b, mayor, menor))
    d = np.maximum(mayor - menor, 1e-6)
    tono = np.where(mayor == r, ((g - b) / d) % 6, np.where(mayor == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return int(np.bincount((tono // 30).astype(int), minlength=12).argmax()) * 30 + 15


def test_todo_dibujo_deja_dos_unidades_de_margen():
    """`iconos.pixmap` achica solo los dibujos que se pegan al borde (`_escala_de_margen`): ninguno puede quedar fuera."""
    from omnicad.ui import iconos
    fallos = [f"{n}: margen {margen(n):.2f}" for n in sorted(iconos.DIBUJOS)
              if n not in iconos.SIN_AJUSTE and margen(n) < MARGEN - TOLERANCIA]
    assert not fallos, "Íconos que se pegan al borde de la grilla:\n" + "\n".join(fallos)


def test_cada_icono_tiene_el_color_de_su_familia():
    fallos = []
    for seccion, tono in TONO_FAMILIA.items():
        for nombre in SECCIONES[seccion]:
            obtenido = tono_dominante(nombre)
            if obtenido not in (tono, None) and nombre not in EXCEPCIONES_COLOR:
                fallos.append(f"{seccion} › {nombre}: tono {obtenido}, esperado {tono}")
    assert not fallos, "Íconos fuera del color de su familia (o agregarlos a EXCEPCIONES_COLOR con motivo):\n" + "\n".join(fallos)


def test_las_excepciones_de_color_siguen_siendo_excepciones():
    esperado = {n: t for s, t in TONO_FAMILIA.items() for n in SECCIONES[s]}
    sobran = [n for n in EXCEPCIONES_COLOR if tono_dominante(n) in (esperado[n], None)]
    assert not sobran, f"Ya no hace falta exceptuarlos: {sobran}"
