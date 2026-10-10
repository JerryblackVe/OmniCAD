# -*- coding: utf-8 -*-
"""Íconos extra (omnicad/ui/iconos_extra.py): están todos, cada uno pinta, no se repiten ni se salen
de la grilla, y no pisan a los de iconos.py.

`python tests/test_iconos_extra.py` regenera la hoja de contacto en evidencias/capturas/iconos_extra.png.
"""
import hashlib
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
HOJA = RAIZ.parent / "evidencias" / "capturas" / "iconos_extra.png"

# El contrato: un ícono por comando, agrupados como en la cinta.
SECCIONES = {
    "SÓLIDO / CREAR": ["barrido", "solevacion", "nervio", "red", "labio", "repujado", "saliente", "encaje_presion",
                       "agujero", "rosca", "bobina", "tuberia", "patron_rectangular_3d", "patron_circular_3d",
                       "patron_ruta", "simetria_3d", "engrosar", "relleno_contorno", "cuerpo_envolvente",
                       "operacion_base", "derivar", "crear_forma", "engranaje_3d", "eje_escalonado"],
    "MODIFICAR": ["pulsar_tirar", "empalme_3d", "chaflan_3d", "vaciado", "desmoldeo", "escala_3d", "desfase_cara",
                  "reemplazar_cara", "dividir_cara", "dividir_cuerpo", "division_silueta", "mover_copiar", "alinear",
                  "suprimir", "quitar", "material_fisico", "aspecto", "administrar_materiales", "lista_materiales"],
    "CONSTRUIR": ["scu", "plano_angulo", "plano_tangente", "plano_medio", "plano_perpendicular", "plano_dos_aristas",
                  "plano_tres_puntos", "plano_ruta", "eje_cilindro", "eje_perpendicular", "eje_dos_planos",
                  "eje_dos_puntos", "eje_arista", "punto_vertice", "punto_dos_aristas", "punto_tres_planos",
                  "punto_centro", "punto_arista_plano", "punto_ruta"],
    "INSPECCIONAR": ["interferencia", "curvatura_peine", "cebra", "mapa_entorno", "angulo_desmoldeo",
                     "mapa_curvatura", "isocurva", "accesibilidad", "radio_minimo", "seccion", "centro_masa",
                     "colores_componente", "revisar_geometria", "reparar_cuerpo"],
    "INSERTAR": ["calcomania", "insertar_svg", "insertar_dxf", "vectorizar_imagen", "insertar_malla", "insertar_componente", "fijacion"],
    "ENSAMBLAR": ["nuevo_componente", "union", "union_construida", "origen_union", "grupo_rigido",
                  "accionar_uniones", "vinculo_movimiento", "conjunto_contacto", "estudio_movimiento",
                  "fijar_componente"],
    "SELECCIONAR": ["seleccion_ventana", "seleccion_libre", "seleccion_pintura", "filtro_seleccion"],
    "SUPERFICIE": ["sup_extruir", "sup_revolucion", "sup_barrido", "sup_solevacion", "parche", "reglada",
                   "sup_desfase", "recortar_sup", "destrimar", "extender_sup", "coser", "descoser", "invertir_normal"],
    "MALLA": ["malla_teselar", "reparar_malla", "grupos_caras", "reducir_malla", "remallar", "cortar_plano",
              "vaciado_malla", "combinar_mallas", "suavizar_malla", "separar_malla", "escalar_malla",
              "convertir_malla", "borrar_rellenar", "alinear_malla", "exportar_malla"],
    "CHAPA": ["reglas_chapa", "pestana", "pestana_contorno", "pestana_solevada", "dobladillo", "cierre_esquina",
              "desgarro", "unir_plegando", "plegar", "desplegar", "patron_plano", "convertir_chapa"],
    "ESPACIOS / VARIOS": ["dibujo", "render", "animacion", "configuracion_tabla", "parametros_exportar",
                          "parametros_importar", "secuencias"],
}
NOMBRES = [n for lista in SECCIONES.values() for n in lista]


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if sys.platform == "win32":                              # sin esto, el modo offscreen no encuentra fuentes
        os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def modulos():
    _app()
    from omnicad.ui import iconos, iconos_extra
    return iconos, iconos_extra


def _pintar(funcion, escala=2, margen=0):
    """Imagen ARGB del ícono a `escala` px por unidad, con `margen` px libres alrededor de la grilla 32×32."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    lado = 32 * escala + 2 * margen
    img = QImage(lado, lado, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(margen, margen)
    p.scale(escala, escala)
    funcion(p)
    p.end()
    return img


def _alfas(img):
    return bytes(img.constBits())[3::4]          # ARGB32 en memoria little-endian: B, G, R, A


def test_estan_todos_y_no_sobran(modulos):
    _, extra = modulos
    assert len(NOMBRES) == len(set(NOMBRES)) == 144
    assert sorted(extra.DIBUJOS_EXTRA) == sorted(NOMBRES)


def test_no_pisan_los_iconos_base(modulos):
    base, extra = modulos
    pisados = [n for n, f in extra.DIBUJOS_EXTRA.items() if n in base.DIBUJOS and base.DIBUJOS[n] is not f]
    assert pisados == []


@pytest.mark.parametrize("nombre", NOMBRES)
def test_pinta_dentro_de_la_grilla(modulos, nombre):
    _, extra = modulos
    margen = 16
    img = _pintar(extra.DIBUJOS_EXTRA[nombre], 2, margen)
    alfa = _alfas(img)
    lado = img.width()
    opacos = sum(1 for a in alfa if a > 40)
    assert opacos > 300, f"{nombre}: casi no pinta ({opacos} píxeles)"
    tol = 2                                                          # 1 unidad de grilla por el antialias
    fuera = sum(1 for i, a in enumerate(alfa) if a > 60 and not (
        margen - tol <= i % lado < lado - margen + tol and margen - tol <= i // lado < lado - margen + tol))
    assert fuera == 0, f"{nombre}: {fuera} píxeles fuera de la grilla 32×32"


def test_ninguno_repetido(modulos):
    base, extra = modulos
    huellas = {}
    todos = {n: f for n, f in base.DIBUJOS.items() if n not in extra.DIBUJOS_EXTRA}
    todos.update(extra.DIBUJOS_EXTRA)
    for nombre, funcion in todos.items():
        huella = hashlib.sha1(bytes(_pintar(funcion, 1).constBits())).hexdigest()
        assert huella not in huellas, f"{nombre} se dibuja igual que {huellas.get(huella)}"
        huellas[huella] = nombre


def test_hoja_de_contacto(modulos, tmp_path):
    ruta = generar_hoja(tmp_path / "hoja.png")
    from PySide6.QtGui import QImage
    img = QImage(str(ruta))
    assert not img.isNull() and img.width() > 900 and img.height() > 1500


# ---------------------------------------------------------------- hoja de contacto (evidencia visual)
def generar_hoja(ruta=HOJA, columnas=8):
    """PNG con todos los íconos por sección: cada uno a 2× (para inspeccionarlo) y a tamaño real, con su nombre."""
    _app()
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QPainter

    from omnicad.ui.iconos_extra import DIBUJOS_EXTRA
    ancho_c, alto_c, titulo = 140, 100, 30
    filas = sum(-(-len(lista) // columnas) for lista in SECCIONES.values())
    img = QImage(columnas * ancho_c, filas * alto_c + len(SECCIONES) * titulo, QImage.Format_ARGB32)
    img.fill(QColor("#f4f4f4"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    y = 0
    for seccion, lista in SECCIONES.items():
        p.fillRect(QRectF(0, y, img.width(), titulo), QColor("#dcdfe3"))
        f = QFont("Segoe UI")
        f.setPixelSize(15)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#333333"))
        p.drawText(QRectF(10, y, img.width() - 20, titulo), Qt.AlignVCenter | Qt.AlignLeft, seccion)
        y += titulo
        for k, nombre in enumerate(lista):
            x0, y0 = (k % columnas) * ancho_c, y + (k // columnas) * alto_c
            p.fillRect(QRectF(x0 + 4, y0 + 4, ancho_c - 8, alto_c - 8), QColor("#ffffff"))
            p.drawImage(x0 + 14, y0 + 8, _pintar(DIBUJOS_EXTRA[nombre], 2))
            p.drawImage(x0 + 94, y0 + 24, _pintar(DIBUJOS_EXTRA[nombre], 1))
            f.setPixelSize(11)
            f.setBold(False)
            p.setFont(f)
            p.setPen(QColor("#222222"))
            p.drawText(QRectF(x0, y0 + 74, ancho_c, 20), Qt.AlignCenter, nombre)
        y += -(-len(lista) // columnas) * alto_c
    p.end()
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    img.save(str(ruta))
    return Path(ruta)


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    print(generar_hoja(Path(sys.argv[1]) if len(sys.argv) > 1 else HOJA))
