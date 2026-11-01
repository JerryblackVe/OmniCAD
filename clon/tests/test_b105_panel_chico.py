# -*- coding: utf-8 -*-
"""B-105: en una ventana chica el panel de un comando entra en el visor (con barra) y Aceptar/Cancelar se ven."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("panel_chico")
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


def _perfil(v):
    from omnicad.restricciones import Boceto
    from omnicad.timeline.operaciones import OpBoceto, OpExtrusion
    from omnicad.ui.comando import hit_desde_ref
    b = Boceto()
    b.agregar_rectangulo((0, 0), (20, 10))
    v.doc.agregar(OpBoceto(v.doc.nuevo_id(), "Boceto1", boceto=b))
    paso = v.doc.operaciones[-1]
    datos = v.doc.estado_final.bocetos[paso.id].perfiles[0]
    return hit_desde_ref({"tipo": "perfil", "boceto": paso.id, **OpExtrusion.referencia_perfil(datos)},
                         v.doc.estado_final)


@pytest.mark.parametrize("ancho,alto", [(1024, 640), (800, 520)])
def test_panel_de_comando_entra_en_el_visor_y_los_botones_se_ven(ventana, ancho, alto):
    from omnicad.ui.comandos.solido import Extruir
    v = ventana
    if not hasattr(v, "_perfil_b105"):
        v._perfil_b105 = _perfil(v)
    perfil = v._perfil_b105
    v.resize(ancho, alto)
    QTest.qWait(30)
    p = v.ejecutar_comando(Extruir(), valores={"perfiles": [perfil]})
    assert p is not None
    QTest.qWait(30)
    marco = v.area.rect()
    assert marco.contains(p.geometry()), (ancho, alto, p.geometry().getRect(), marco.getRect())
    cancelar = next(b for b in p.findChildren(type(p.boton_ok)) if b.text() == "Cancelar")
    for boton in (p.boton_ok, cancelar):
        assert marco.contains(boton.mapTo(v.area, boton.rect().bottomRight())), (ancho, alto, boton.text())
    p.cancelar()
    QTest.qWait(10)


@pytest.mark.parametrize("ancho,alto", [(1024, 640), (800, 520)])
def test_en_ventana_baja_el_cuerpo_del_panel_conserva_varias_filas(ventana, ancho, alto):
    """El panel sube sobre el ViewCube cuando debajo no queda lugar: el cuerpo desplazable no se reduce a una fila."""
    from omnicad.ui.comandos.solido import Extruir
    v = ventana
    if not hasattr(v, "_perfil_b105"):
        v._perfil_b105 = _perfil(v)
    v.resize(ancho, alto)
    QTest.qWait(30)
    p = v.ejecutar_comando(Extruir(), valores={"perfiles": [v._perfil_b105]})
    QTest.qWait(30)
    assert v.area.rect().contains(p.geometry()), (p.geometry().getRect(), v.area.rect().getRect())
    assert p.desplazador.height() >= 110, (ancho, alto, p.desplazador.height())
    p.cancelar()


def _cambiar_combo(panel, clave, valor):
    """Como la persona: elige otra opción en el combo real (no `set_valor`)."""
    campo = next(c for c in panel.campos if c.clave == clave)
    panel.widgets[clave].setCurrentIndex(list(campo.opciones).index(valor))
    QTest.qWait(30)


def _curva(v):
    from omnicad.ui.comando import hit_desde_ref
    paso = v.doc.operaciones[-1]
    b = v.doc.estado_final.bocetos[paso.id].boceto
    return hit_desde_ref({"tipo": "curva_boceto", "boceto": paso.id, "curva": next(iter(b.curvas))}, v.doc.estado_final)


@pytest.mark.parametrize("clave,cambios", [
    ("extruir", [("extension", "objeto"), ("direccion", "dos_lados")]),
    ("revolucion", [("direccion", "dos_lados")]),
    ("sup_extruir", [("extension", "objeto"), ("lados", "dos_lados")]),
])
def test_el_panel_crece_cuando_un_cambio_de_modo_muestra_campos(ventana, clave, cambios):
    """B-113: al cambiar de modo con el combo real aparecen campos nuevos y el cuerpo del panel tiene que crecer hasta
    mostrarlos (sin barra ni «Más opciones» cortado) mientras haya lugar en el visor."""
    from omnicad.ui.comandos import CATALOGO
    v = ventana
    if not hasattr(v, "_perfil_b105"):
        v._perfil_b105 = _perfil(v)
    v.resize(1280, 900)
    QTest.qWait(30)
    valores = {"curvas": [_curva(v)]} if clave == "sup_extruir" else {"perfiles": [v._perfil_b105]}
    p = v.ejecutar_comando(CATALOGO[clave](), valores=valores)
    QTest.qWait(30)
    for campo, valor in cambios:
        _cambiar_combo(p, campo, valor)
        assert p.desplazador.verticalScrollBar().maximum() == 0, (clave, campo, p.desplazador.verticalScrollBar().maximum())
        assert v.area.rect().contains(p.geometry()), (clave, p.geometry().getRect())
    p.cancelar()
    QTest.qWait(10)


def test_con_poco_lugar_el_panel_sigue_entrando_aunque_aparezcan_campos(ventana):
    """B-113 y B-105 juntos: en 800×520 el panel que crece por un cambio de modo y recibe un mensaje de error de varias
    líneas (su alto asienta recién al volver al bucle de eventos) sigue dentro del visor."""
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import CATALOGO
    v = ventana
    if not hasattr(v, "_perfil_b105"):
        v._perfil_b105 = _perfil(v)
    v.resize(800, 520)
    QTest.qWait(30)
    eje = hit_desde_ref({"tipo": "eje", "id": "Z"}, v.doc.estado_final)
    p = v.ejecutar_comando(CATALOGO["sup_revolucion"](), valores={"curvas": [_curva(v)], "eje": [eje]})
    QTest.qWait(30)
    _cambiar_combo(p, "lados", "dos_lados")
    p.set_valor("angulo", "400 deg")
    p._t_previa.stop()
    p._calcular_previa()
    QTest.qWait(60)
    assert "360" in p.mensaje.text(), p.mensaje.text()          # el mensaje largo es el que hace falta para esta prueba
    assert v.area.rect().contains(p.geometry()), (p.geometry().getRect(), v.area.rect().getRect())
    p.cancelar()
    QTest.qWait(10)
