# -*- coding: utf-8 -*-
"""La ventana real (offscreen) con las herramientas en vivo de B-80: selección por API (MCP-50), captura de la vista
(MCP-46) y el estado del visor que dejan set_visual_style, set_view y set_grid (MCP-44)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api import protocolo_puente as proto  # noqa: E402


@pytest.fixture(scope="module")
def app_qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("vivo")
    anterior = os.environ.get(proto.VARIABLE_CARPETA)
    os.environ[proto.VARIABLE_CARPETA] = str(carpeta)          # nunca el puente.json real del usuario
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)
    if anterior is None:
        os.environ.pop(proto.VARIABLE_CARPETA, None)
    else:
        os.environ[proto.VARIABLE_CARPETA] = anterior


@pytest.fixture
def sesion(ventana):
    """Sesión con los hooks de la ventana (lo que arma el puente) sobre un documento nuevo con una caja."""
    from omnicad.timeline.documento import Documento
    from omnicad.ui.puente import PuenteAgentes
    ventana.set_documento(Documento())
    s = PuenteAgentes(ventana).sesion
    ok(s, "create_box", length=20, width=20, height=20, name="Caja")
    return s


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def test_elegir_caras_y_aristas_se_ve_en_la_ventana_y_se_lee_de_vuelta(ventana, sesion):
    r = ok(sesion, "select_entities", kind="face", selector=">Z", body="Caja")
    assert r["count"] == 1 and ventana.leer_seleccion() == [r["selection"][0]["ref"]]
    assert ventana.visor._capas["preseleccion"]                               # quedó resaltada en la vista
    r = ok(sesion, "select_entities", kind="edge", selector="|Z", body="Caja", mode="add")
    assert r["count"] == 5 and ok(sesion, "get_selection")["count"] == 5
    ok(sesion, "select_entities", kind="edge", selector="|Z", body="Caja", mode="remove")
    assert [h["tipo"] for h in ventana.seleccion] == ["cara"]
    ok(sesion, "select_entities", kind="body", selector="Caja")
    assert [h["tipo"] for h in ventana.seleccion] == ["cuerpo"]
    ok(sesion, "select_bodies", bodies=[])                                    # limpiar sigue yendo por select_bodies
    assert ok(sesion, "get_selection")["count"] == 0


def test_elegir_perfiles_de_un_boceto(ventana, sesion):
    ok(sesion, "create_sketch", plane="XY", name="Boceto")
    ok(sesion, "draw_circle", radius=3)
    r = ok(sesion, "select_entities", kind="profile", sketch="Boceto", profile=0)
    assert r["count"] == 1 and ventana.seleccion[0]["tipo"] == "perfil"


def test_la_captura_es_un_png_de_la_vista_real_y_se_puede_reescalar(ventana, sesion):
    ventana.visor.vista("iso")
    r = ok(sesion, "capture_viewport")
    assert r["image"].png.startswith(b"\x89PNG") and r["width"] > 0 and r["height"] > 0
    r = ok(sesion, "capture_viewport", width=120, height=80)
    assert (r["width"], r["height"]) == (120, 80) and r["image"].png.startswith(b"\x89PNG")


def test_el_estado_del_visor_de_los_agentes_se_aplica_a_la_ventana(ventana, sesion):
    c = ventana.visor.config
    ok(sesion, "set_visual_style", style="wireframe_hidden_edges", environment="fotomaton", shadows=True,
       reflections=True, ground_plane=True)
    assert c.estilo_visual == "alambrico_ocultas" and c.entorno == "fotomaton"
    assert c.efectos["sombra_suelo"] and c.efectos["reflejo"] and c.efectos["suelo"]
    ok(sesion, "set_visual_style", style="shaded", shadows=False)
    assert c.estilo_visual == "sombreado" and not c.efectos["sombra_suelo"] and c.efectos["reflejo"]
    ok(sesion, "set_grid", show=True)
    assert c.rejilla is True
    ok(sesion, "set_grid", show=False)
    assert c.rejilla is False
    ok(sesion, "set_view", view="top", projection="orthographic")
    assert c.camara == "ortografica" and abs(ventana.visor.R[2][2]) > 0.99      # mira desde arriba
    ventana.visor.vista("iso")                                                  # la persona orbita...
    ok(sesion, "set_visual_style", style="wireframe")                            # ...y un cambio ajeno no le pisa la cámara
    assert abs(ventana.visor.R[2][2]) < 0.99


def test_borrar_o_deshacer_el_estilo_devuelve_lo_que_eligio_la_persona(ventana, sesion):
    c, p = ventana.visor.config, ventana.prefs
    ok(sesion, "set_visual_style", style="wireframe_visible_edges", shadows=True)
    assert c.estilo_visual == "alambrico_visibles" and c.efectos["sombra_suelo"]
    ok(sesion, "set_visual_style", clear=True)
    assert c.estilo_visual == p["vista/estilo_visual"] and c.efectos["sombra_suelo"] == p["vista/efecto_sombra_suelo"]
    ok(sesion, "undo")                                                          # deshacer el clear vuelve el estilo
    assert c.estilo_visual == "alambrico_visibles" and c.efectos["sombra_suelo"]
    ok(sesion, "undo")                                                          # y deshacer el set lo saca
    assert c.estilo_visual == p["vista/estilo_visual"]
    ok(sesion, "set_grid", show=True)
    assert c.rejilla is True
    ok(sesion, "undo")
    assert c.rejilla == p["vista/rejilla"]
