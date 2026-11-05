# -*- coding: utf-8 -*-
"""ASM-20: los paneles de Unión y Unión como está muestran los campos en el orden de Fusion y ocultan los que no
aplican al tipo elegido. Joint reference (fusion-assemble): pestaña Position › Componente 1 (Mode, geometría, Snap),
Componente 2, Joint Alignment (Angle, Offset X/Y/Z, Flip); pestaña Motion › Type, ejes de Rotation/Translation
(Rotate, Slide, Axis, Normal, Pitch, Yaw) y los límites por movimiento. As-Built Joint reference: Components y
después Motion › Type, sin desfases."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.timeline.ops_ensamblar import (CLAVES_MOVIMIENTO,  # noqa: E402
                                           MOVIMIENTOS, OpUnion, principal_de)
from omnicad.ui.comandos.ensamblar import Union, UnionComoEsta  # noqa: E402

# Ejes primero (la fila Rotation/Translation de Fusion), después los valores; en la bola no hay desplegable X/Y/Z de
# giro (el balanceo sale del cabeceo y la guiñada) pero queda su eje propio (ASM-11).
MOVIMIENTO = {
    "rigida": [],
    "revolucion": ["eje_giro", "ref_eje_giro", "giro"],
    "deslizante": ["eje_desliz", "ref_eje_desliz", "desliz"],
    "cilindrica": ["eje_giro", "ref_eje_giro", "giro", "desliz"],
    "pasador_ranura": ["eje_giro", "ref_eje_giro", "eje_desliz", "ref_eje_desliz", "giro", "desliz"],
    "planar": ["eje_giro", "ref_eje_giro", "giro", "desliz", "desliz2"],
    "bola": ["ref_eje_giro", "eje_cabeceo", "ref_eje_cabeceo", "eje_guinada", "ref_eje_guinada",
             "giro", "giro2", "giro3"],
}
POSICION = {"union": ["modo1", "origen1", "clave1", "modo2", "origen2", "clave2", "angulo"],
            "construida": ["modo1", "origen1", "clave1", "origen2"]}


def _visibles(cmd, tipo, avanzado=False):
    """Las claves del panel que se ven con ese tipo de movimiento (los dos orígenes en modo «simple»), en el orden
    en que el panel los dibuja."""
    v = dict(OpUnion.PARAMS, tipo=tipo)
    return [c.clave for c in cmd.campos(None)
            if bool(c.avanzado) == avanzado and (c.visible_si is None or c.visible_si(v))]


def _limites_esperados(tipo, sin_desfases=False):
    dof = sum(MOVIMIENTOS[tipo], [])
    esperado = [] if sin_desfases else ["dx", "dy", "dz", "voltear"]
    if dof:
        esperado += ["minimo", "maximo"]
    for clave in CLAVES_MOVIMIENTO:
        if clave in dof:
            if clave != principal_de(tipo):
                esperado += [f"min_{clave}", f"max_{clave}"]
            esperado += [f"reposo_{clave}", f"inv_{clave}"]
    return esperado


@pytest.mark.parametrize("tipo", list(MOVIMIENTO))
def test_union_muestra_los_campos_de_fusion_en_orden(tipo):
    assert _visibles(Union(), tipo) == POSICION["union"] + ["tipo"] + MOVIMIENTO[tipo]


@pytest.mark.parametrize("tipo", list(MOVIMIENTO))
def test_union_construida_muestra_los_campos_de_fusion_en_orden(tipo):
    assert _visibles(UnionComoEsta(), tipo) == POSICION["construida"] + ["tipo"] + MOVIMIENTO[tipo]


@pytest.mark.parametrize("tipo", list(MOVIMIENTO))
def test_union_muestra_en_mas_opciones_los_limites_del_movimiento_elegido(tipo):
    assert _visibles(Union(), tipo, avanzado=True) == _limites_esperados(tipo)


@pytest.mark.parametrize("tipo", list(MOVIMIENTO))
def test_union_construida_sin_desfases_y_con_sus_limites(tipo):
    """Una unión como está conserva la posición actual: los desfases de Joint Alignment no van ni vacíos."""
    assert _visibles(UnionComoEsta(), tipo, avanzado=True) == _limites_esperados(tipo, sin_desfases=True)


# ---------------------------------------------------------------- el panel en la ventana
@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("union_campos")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def _componentes(v):
    """Dos cajas, cada una en su componente: sin componentes el comando Unión ni abre (verificar)."""
    if hasattr(v, "_union_comps"):
        return
    s = api.Sesion(v.doc)
    for nombre, x in (("Base", 0), ("Pieza", 100)):
        r = api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 20, "x": x})
        assert r["ok"], r
        r = api.llamar(s, "create_component", {"bodies": [r["result"]["bodies_created"][0]["id"]],
                                               "name": nombre, "grounded": nombre == "Base"})
        assert r["ok"], r
    v._union_comps = True


def _cambiar_tipo(p, tipo):
    """Como la persona: elige el tipo en el combo real (no `set_valor`)."""
    campo = next(c for c in p.campos if c.clave == "tipo")
    p.widgets["tipo"].setCurrentIndex(list(campo.opciones).index(tipo))
    QTest.qWait(30)


@pytest.mark.parametrize("tipo", list(MOVIMIENTO))
def test_panel_union_en_ventana_chica_muestra_lo_que_aplica(ventana, tipo):
    from omnicad.ui.comandos import CATALOGO
    v = ventana
    _componentes(v)
    v.resize(800, 520)
    QTest.qWait(30)
    p = v.ejecutar_comando(CATALOGO["union"]())
    assert p is not None
    QTest.qWait(30)
    try:
        _cambiar_tipo(p, tipo)
        assert v.area.rect().contains(p.boton_ok.mapTo(v.area, p.boton_ok.rect().bottomRight())), tipo
        visibles = [c.clave for c in p.campos if not c.avanzado and p.widgets[c.clave].isVisible()]
        assert visibles == POSICION["union"] + ["tipo"] + MOVIMIENTO[tipo]
    finally:
        p.cancelar()
        QTest.qWait(10)
