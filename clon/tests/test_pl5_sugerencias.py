# -*- coding: utf-8 -*-
"""PL5 (brechas_plasticity.md): tira de comandos sugeridos según lo elegido (`ui/sugerencias.py`)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.nucleo import referencias as refs  # noqa: E402
from omnicad.ui.sugerencias import MAXIMO, SUGERIDOS, comandos_sugeridos  # noqa: E402

TODOS = {c for lista in SUGERIDOS.values() for c in lista}


def test_cada_tipo_sugiere_sus_comandos_en_orden_y_sin_pasar_del_maximo():
    assert comandos_sugeridos({"cara"}, TODOS) == ["pulsar_tirar", "desfase", "vaciado", "aspecto", "medir"]
    assert comandos_sugeridos({"arista"}, TODOS) == ["empalme_3d", "chaflan_3d", "desfase", "medir"]
    assert comandos_sugeridos({"perfil"}, TODOS) == ["extruir", "revolucion"]
    assert comandos_sugeridos({"cuerpo"}, TODOS) == ["mover_copiar", "aspecto", "material_fisico", "quitar"]
    assert comandos_sugeridos(set(), TODOS) == []
    assert comandos_sugeridos({"plano"}, TODOS) == []                     # sin sugerencias propias


def test_varios_tipos_no_repiten_y_el_tope_se_puede_levantar():
    mezcla = comandos_sugeridos({"cara", "arista"}, TODOS)
    assert len(mezcla) == MAXIMO == len(set(mezcla)) and mezcla[:3] == ["pulsar_tirar", "desfase", "vaciado"]
    assert len(comandos_sugeridos({"cara", "arista"}, TODOS, maximo=None)) == 7


def test_solo_salen_los_comandos_que_existen():
    assert comandos_sugeridos({"cara"}, {"vaciado", "medir"}) == ["vaciado", "medir"]
    assert comandos_sugeridos({"cara"}, set()) == []


def test_las_claves_sugeridas_son_comandos_que_existen():
    """Si se renombra un comando, su botón desaparecería de la tira (y del clic derecho) sin que nada falle."""
    from omnicad.ui.comandos import CATALOGO
    assert TODOS <= set(CATALOGO)


@pytest.fixture
def ventana(tmp_path):
    QApplication.instance() or QApplication([])
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.resize(1200, 800)
    v.show()
    v.cargar_ejemplo()
    QTest.qWait(30)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(10)


def _hit_cara_de_arriba(v):
    from omnicad.ui.comando import hit_desde_ref
    cid = next(iter(v.doc.estado_final.cuerpos))
    forma = v.doc.estado_final.cuerpos[cid].forma
    cara = max(geo.caras(forma), key=lambda c: refs.firma(c)["centro"][2])
    return hit_desde_ref(refs.referencia(cid, cara, forma), v.doc.estado_final)


def _botones(v):
    return [b.text() for b in v.tira.findChildren(QToolButton)]


def test_al_elegir_una_cara_aparece_la_tira_con_sus_comandos(ventana):
    v = ventana
    assert not v.tira.isVisible()
    v._seleccionar([_hit_cara_de_arriba(v)])
    assert v.tira.isVisible() and v.tira.claves == ["pulsar_tirar", "desfase", "vaciado", "aspecto", "medir"]
    assert _botones(v) == ["Pulsar/tirar", "Desfase", "Vaciado", "Aspecto", "Medir"]
    g = v.area.geometry()
    assert v.tira.geometry().bottom() < v.area.barra.geometry().top() and abs(v.tira.geometry().center().x() - g.center().x()) < 3
    v._seleccionar([])
    assert not v.tira.isVisible()


def test_un_clic_ejecuta_el_comando_con_lo_elegido(ventana):
    v = ventana
    v._seleccionar([_hit_cara_de_arriba(v)])
    v.tira.findChildren(QToolButton)[1].click()                    # «Desfase»
    assert v.panel is not None and type(v.panel.comando).__name__ == "Desfase"
    assert len(v.panel.valores["objetos"]) == 1                    # la cara quedó en el campo del comando
    assert not v.tira.isVisible()                                  # con un comando abierto la tira se va
    v._seleccionar([_hit_cara_de_arriba(v)])
    assert not v.tira.isVisible()
    v.panel.cancelar()


def test_en_un_boceto_abierto_no_hay_tira(ventana):
    v = ventana
    v._seleccionar([_hit_cara_de_arriba(v)])
    assert v.tira.isVisible()
    v.crear_boceto()
    v._plano_elegido({"ref": "XY", "plano": geo.Plano("XY"), "marco": None})
    assert v.modo_boceto.activo and not v.tira.isVisible()          # abrir el boceto la esconde aunque haya selección
    v._seleccionar([_hit_cara_de_arriba(v)])
    assert not v.tira.isVisible()
    v.modo_boceto.terminar()


def test_un_documento_nuevo_borra_lo_elegido_y_la_tira(ventana):
    v = ventana
    v._seleccionar([_hit_cara_de_arriba(v)])
    assert v.tira.isVisible()
    v.doc.modificado = False
    v.nuevo()
    assert v.seleccion == [] and not v.tira.isVisible()


def test_sin_barra_de_navegacion_la_tira_baja_al_borde(ventana):
    v = ventana
    v._seleccionar([_hit_cara_de_arriba(v)])
    con_barra = v.tira.geometry().bottom()
    v.area.barra.hide()
    v.area.reubicar()
    assert v.tira.geometry().bottom() > con_barra                 # no queda flotando sobre el hueco de la barra
    assert v.tira.geometry().bottom() == v.area.height() - 8 - 1


def test_el_clic_derecho_usa_la_misma_lista(ventana):
    v = ventana
    v._seleccionar([_hit_cara_de_arriba(v)])
    titulos = [f[0] for f in v._contexto_radial() if f]
    for esperado in ("Pulsar/tirar", "Desfase", "Vaciado", "Aspecto", "Medir"):
        assert esperado in titulos
