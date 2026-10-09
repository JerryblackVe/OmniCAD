# -*- coding: utf-8 -*-
"""Piezas de la interfaz estilo Fusion que se pueden probar sin abrir ventanas."""
import pytest
from PySide6.QtCore import QSettings

from omnicad.ui import formato
from omnicad.ui.panel_timeline import MARCADOR, destino_arrastre
from omnicad.ui.preferencias import DEFECTOS, Preferencias, migrar_ajustes


@pytest.fixture
def prefs(tmp_path):
    return Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))


# ---------------------------------------------------------------- timeline: arrastrar y soltar
CLAVES = ["op1", "op2", MARCADOR, "op3", "op4"]          # marcador después del 2.º paso


@pytest.mark.parametrize("fila, esperado", [(0, 0), (1, 1), (2, 2), (4, 3), (5, 4)])
def test_soltar_el_marcador(fila, esperado):
    assert destino_arrastre(CLAVES, MARCADOR, fila) == esperado


@pytest.mark.parametrize("origen, fila, esperado", [
    ("op1", 5, 3),      # al final
    ("op4", 0, 0),      # al principio
    ("op3", 1, 1),      # entre op1 y op2 (el marcador no cuenta)
    ("op2", 2, 1),      # soltado en su mismo lugar
])
def test_soltar_un_paso(origen, fila, esperado):
    assert destino_arrastre(CLAVES, origen, fila) == esperado


# ---------------------------------------------------------------- preferencias
def test_preferencias_por_defecto_y_tipos(prefs):
    assert prefs["general/autoguardado_min"] == DEFECTOS["general/autoguardado_min"]
    assert prefs["vista/efecto_aa"] is True
    assert prefs["general/tipo_orbita"] == "libre"
    assert prefs["general/raton"] == "fusion"          # el de Fusion: arrastrar con el izquierdo hace la ventana


def test_preferencias_persisten_con_su_tipo(tmp_path, prefs):
    prefs["general/invertir_zoom"] = True
    prefs["unidades/precision"] = 1
    prefs.q.sync()
    otra = Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))
    assert otra["general/invertir_zoom"] is True        # en el .ini queda como texto "true"
    assert otra["unidades/precision"] == 1


def test_restablecer_no_borra_el_estado_de_la_vista(prefs):
    prefs["material/aspecto"] = "paleta"
    prefs["vista/efecto_suelo"] = True
    prefs["vista/estilo_visual"] = "alambrico"
    prefs.restablecer()
    assert prefs["material/aspecto"] == "acero"
    assert prefs["vista/efecto_suelo"] is False          # los efectos son preferencias (Gráficos)
    assert prefs["vista/estilo_visual"] == "alambrico"   # el estado de la vista no se toca


def test_preferencias_del_nombre_anterior_se_migran_una_vez(tmp_path):
    viejos = QSettings(str(tmp_path / "viejo.ini"), QSettings.IniFormat)
    viejos.setValue("general/raton", "fusionclone")
    viejos.setValue("general/autoguardado_min", 7)
    nuevos = QSettings(str(tmp_path / "nuevo.ini"), QSettings.IniFormat)
    assert migrar_ajustes(nuevos, viejos)
    p = Preferencias(nuevos)
    assert p["general/raton"] == "omnicad" and p["general/autoguardado_min"] == 7
    viejos.setValue("general/autoguardado_min", 30)
    assert not migrar_ajustes(nuevos, viejos)          # ya hay preferencias nuevas: no se pisan
    assert p["general/autoguardado_min"] == 7


def test_clave_desconocida_es_error(prefs):
    with pytest.raises(KeyError):
        prefs["no/existe"] = 1


def test_recientes_sin_duplicados_y_mas_nuevo_primero(prefs):
    for ruta in ("a.omnicad", "b.omnicad", "A.omnicad"):
        prefs.agregar_reciente(ruta)
    assert prefs.recientes() == ["A.omnicad", "b.omnicad"]       # Windows: mismas rutas sin distinguir mayúsculas
    prefs.quitar_reciente("b.omnicad")
    assert prefs.recientes() == ["A.omnicad"]


# ---------------------------------------------------------------- formato de números
@pytest.mark.parametrize("config, valor, angular, esperado", [
    ((3, 1, True), 12.0, False, "12"),
    ((3, 1, True), 12.5, False, "12.5"),
    ((3, 1, False), 12.5, False, "12.500"),
    ((2, 1, True), 0.004, False, "0"),
    ((3, 1, True), 37.25, True, "37.2"),          # precisión angular aparte (redondeo bancario de Python)
    ((0, 0, True), 7.6, False, "8"),
])
def test_formato_numero(config, valor, angular, esperado):
    formato.configurar(*config)
    try:
        assert formato.numero(valor, angular=angular) == esperado
    finally:
        formato.configurar()


def test_texto_atajo_en_castellano():
    from omnicad.ui.ventana import texto_atajo
    assert texto_atajo("Ctrl+Shift+S") == "Control+Mayúsculas+S"
    assert texto_atajo("E") == "E"


def test_dentro_del_poligono_regla_par_impar():
    """Reemplaza a matplotlib.path (la app instalada no trae matplotlib y la selección en ventana se colgaba)."""
    import numpy as np

    from omnicad.ui.ventana import dentro_del_poligono
    cuadrado = [(0, 0), (10, 0), (10, 5), (0, 5)]
    assert dentro_del_poligono([(5, 2), (11, 2), (-1, 2), (5, 6)], cuadrado).tolist() == [True, False, False, False]
    estrella = [(0, 0), (8, 1), (9, 9), (4, 5), (1, 8)]                  # cóncavo: (4, 6) cae en la muesca
    assert dentro_del_poligono([(5, 3), (4, 6), (2, 6)], estrella).tolist() == [True, False, True]
    assert dentro_del_poligono(np.zeros((0, 2)), cuadrado).shape == (0,)
