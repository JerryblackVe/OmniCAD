# -*- coding: utf-8 -*-
"""Cobertura de los 5 tipos de Proyectar del boceto con valores raros que no tenían test.

Preparado para la prueba E7 (resumen y opciones de Fusion en `docs/seguimiento/preparado/PROYECTAR-5-tipos.md`):
vacío, cero, negativos, el tope de las isoparamétricas y un cuerpo oculto. No cambia código de la app: fija lo que ya
hace y avisa si deja de hacerlo.
"""
import numpy as np
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def falla(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert not r["ok"], r
    return r


def _caja_con_dos_bocetos():
    """Caja de 40×40×10, un boceto «Fuente» con un círculo de R5 y un boceto «Destino» vacío.

    Devuelve la sesión y la referencia del círculo, para no depender de su id."""
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=40, height=10)
    llamar(s, "create_sketch", plane="XY", name="Fuente")
    circulo = llamar(s, "draw_circle", center_x=0, center_y=0, radius=5)["entities"][0]["id"]
    llamar(s, "create_sketch", plane="XY", name="Destino")
    return s, {"sketch": "Fuente", "curve": circulo}


# ---------------------------------------------------------------- Proyectar a superficie (Project to Surface)
def test_project_to_surface_sin_caras_se_rechaza():
    """Fusion no deja proyectar sin caras destino; la API tiene que decirlo, no devolver una lista vacía."""
    s, curva = _caja_con_dos_bocetos()
    r = falla(s, "project_to_surface", faces=[], curves=[curva])
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "caras" in r["mensaje"]


def test_project_to_surface_con_direccion_cero_se_rechaza():
    """A lo largo de un vector: [0, 0, 0] no define una dirección (el núcleo dividiría por cero)."""
    s, curva = _caja_con_dos_bocetos()
    r = falla(s, "project_to_surface", faces=[">Z"], curves=[curva], mode="vector", direction=[0, 0, 0])
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "nulo" in r["mensaje"]


# ---------------------------------------------------------------- Intersecar (Intersection Curve)
def test_intersect_curves_sin_nada_se_rechaza():
    """Sin curvas y con menos de dos objetivos no hay nada que cortar."""
    s, _ = _caja_con_dos_bocetos()
    r = falla(s, "intersect_curves")
    assert r["error_kind"] == "INVALID_ARGUMENTS"


def test_intersect_curves_con_una_cara_curva_como_plano_se_rechaza():
    """Una referencia tiene que ser un plano o una cara plana: la cara lateral de un cilindro no lo es."""
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=40)
    llamar(s, "create_sketch", plane="XY", name="Corte")
    lateral = llamar(s, "find_faces", selector="%CYLINDER")["faces"][0]["id"]
    r = falla(s, "intersect_curves", references=[lateral])
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "plana" in r["mensaje"]


# ---------------------------------------------------------------- Incluir geometría 3D (Include 3D Geometry)
def test_include_3d_con_un_vertice_que_no_existe_no_toca_el_boceto():
    """Un punto que no cae sobre ningún vértice (a 0,001 mm) se rechaza y el boceto queda igual."""
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=40, height=10)
    llamar(s, "create_sketch", plane="XY", name="Boceto")
    r = falla(s, "include_3d_geometry", vertices=[[999, 999, 999]])
    assert r["error_kind"] == "ELEMENT_NOT_FOUND" and "999" in r["mensaje"]
    assert llamar(s, "get_sketch", sketch="Boceto").get("entities_3d", []) == []


# ---------------------------------------------------------------- Perfil giratorio (Spun Profile)
def test_perfil_giratorio_con_tolerancia_negativa_se_rechaza():
    """La tolerancia es una distancia: negativa no tiene sentido (el tope de 0 ya tenía test)."""
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10)
    llamar(s, "create_sketch", plane="XZ", name="Giro")
    r = falla(s, "project_spun_profile", axis="Z", bodies=["Cuerpo1"], tolerance=-0.5)
    assert r["error_kind"] == "INVALID_ARGUMENTS" and "mayor que cero" in r["mensaje"]
    assert llamar(s, "get_sketch", sketch="Giro").get("projections", []) == []


# ---------------------------------------------------------------- Curva isoparamétrica (Isoparametric Curve)
def test_isoparametrica_con_cantidad_sobre_el_tope_se_rechaza():
    """El tope es 200 curvas por pedido: 201 es un error de unidad (una distancia en mm contra una cara enorme)."""
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=40)
    llamar(s, "create_sketch", plane="XY", name="Iso")
    lateral = llamar(s, "find_faces", selector="%CYLINDER")["faces"][0]["id"]
    r = falla(s, "isoparametric_curve", face=lateral, point=[10, 0, 15], direction="u",
              type="distributed", quantity=201)
    assert r["error_kind"] == "INVALID_GEOMETRY" and "tope 200" in r["mensaje"]
    assert llamar(s, "get_sketch", sketch="Iso").get("entities_3d", []) == []


# ---------------------------------------------------------------- Cuerpo oculto (la ventana)
@pytest.fixture
def ventana(tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    app = QApplication.instance() or QApplication([])
    prefs = QSettings(str(tmp_path_factory.mktemp("prep_proyectar") / "prefs.ini"), QSettings.IniFormat)
    v = VentanaPrincipal(prefs=Preferencias(prefs))
    v.resize(1280, 720)
    v.show()
    app.processEvents()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def _clic_en(v, punto):
    lz = v.modo_boceto.lienzo
    q = v.visor.mapToGlobal(v.visor.proyectar(np.array(punto, float)).toPoint())
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier, lz.mapFromGlobal(q))
    QApplication.processEvents()


def test_un_cuerpo_oculto_no_se_elige_para_proyectar(ventana):
    """Como Fusion: lo oculto no está en el lienzo y el clic no lo elige. Visible, el mismo clic sí lo elige."""
    s = api.Sesion()
    cuerpo = llamar(s, "create_box", length=40, width=40, height=10)["bodies_created"][0]["id"]
    llamar(s, "create_sketch", plane="XY", name="Boceto")
    ventana.set_documento(s.doc)
    ventana.visor.encuadrar()
    QApplication.processEvents()
    ventana.editar_operacion(s.paso("Boceto").id)
    QApplication.processEvents()
    try:
        ventana.modo_boceto.herramienta("proyectar")
        QApplication.processEvents()
        lz = ventana.modo_boceto.lienzo
        ventana._ojo(cuerpo)                        # el ojo del navegador: lo oculta
        QApplication.processEvents()
        _clic_en(ventana, (0.0, 0.0, 10.0))         # el centro de la cara de arriba de la caja
        assert lz._elegidos_proy == []
        ventana._ojo(cuerpo)                        # lo vuelve a mostrar
        QApplication.processEvents()
        _clic_en(ventana, (0.0, 0.0, 10.0))
        assert len(lz._elegidos_proy) == 1
    finally:
        if ventana.modo_boceto.activo:
            ventana.modo_boceto.cancelar()
