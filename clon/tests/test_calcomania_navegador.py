# -*- coding: utf-8 -*-
"""Calcomanía integrada al navegador y a su cuerpo (revisión del 2026-10-17).

Referencia: Fusion 360. La calcomanía vive en la carpeta «Calcomanías» del navegador (con su ojo), su menú tiene
Editar calcomanía / Reemplazar archivo de imagen / Suprimir / Cambiar nombre / Mostrar-ocultar / Buscar…, y va con su
cuerpo: si el cuerpo se oculta, se borra, se mueve o se copia, la calcomanía lo acompaña."""
import base64
import os

import numpy as np
import pytest
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api
from omnicad.io_archivos import proyecto
from omnicad.timeline.ops_insertar import calcomanias_vigentes

from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


def _png(ruta, color="#cc3355", tam=(160, 80)):
    Image.new("RGB", tam, color).save(ruta)
    return str(ruta)


def _escena(tmp_path, imagen="eloisa.png"):
    """Una caja de 100 × 60 × 20 con una calcomanía en su cara de arriba."""
    s = api.Sesion()
    assert api.llamar(s, "create_box", {"length": 100, "width": 60, "height": 20})["ok"]
    cara = api.llamar(s, "find_faces", {"selector": ">Z"})["result"]["faces"][0]["id"]
    r = api.llamar(s, "set_decal", {"image": _png(tmp_path / imagen), "face": cara, "width": 40})
    assert r["ok"], r
    return s, r["result"]["feature"]["id"]


def _centro_x(sesion, ident):
    datos = dict(calcomanias_vigentes(sesion.doc, sesion.doc.estado_final))[ident]
    return float(np.asarray(datos["malla"]["vertices"])[:, 0].mean())


# ---------------------------------------------------------------- núcleo (sin ventana)
def test_la_calcomania_se_llama_como_su_imagen_y_sabe_de_que_cuerpo_es(tmp_path):
    s, deco = _escena(tmp_path)
    op = s.paso(deco)
    assert op.nombre == "eloisa"                                   # como Fusion, no «Calcomanía»
    d = s.doc.estado_final.lienzos[deco]
    assert d["cuerpo"] == "op1.c1" and d["archivo"] == "eloisa.png"
    r = api.llamar(s, "set_decal", {"feature": deco, "name": "Ventana"})
    assert r["ok"] and s.paso(deco).nombre == "Ventana"
    assert api.llamar(s, "set_decal", {"feature": deco, "name": "  "})["error_kind"] == "INVALID_ARGUMENTS"


def test_get_scene_info_lista_las_calcomanias_con_su_cuerpo(tmp_path):
    s, deco = _escena(tmp_path)
    info = api.llamar(s, "get_scene_info", {})["result"]
    assert [(d["id"], d["name"], d["body"], d["on_body"]) for d in info["decals"]] == [(deco, "eloisa", "op1.c1", True)]
    corto = api.llamar(s, "get_scene_info", {"summary": True})["result"]
    assert corto["decals"] == [{"id": deco, "name": "eloisa", "body": "op1.c1"}]


def test_la_calcomania_sigue_a_su_cuerpo_cuando_se_mueve(tmp_path):
    """Moverla DESPUÉS de pegar la calcomanía: la calcomanía va con la cara, no se queda en el aire."""
    s, deco = _escena(tmp_path)
    antes = _centro_x(s, deco)
    assert api.llamar(s, "move_body", {"body": "op1.c1", "translate": [50, 0, 0]})["ok"]
    assert _centro_x(s, deco) == pytest.approx(antes + 50, abs=0.2)
    assert api.llamar(s, "move_body", {"body": "op1.c1", "translate": [0, 0, 30]})["ok"]
    z = np.asarray(dict(calcomanias_vigentes(s.doc, s.doc.estado_final))[deco]["malla"]["vertices"])[:, 2]
    assert z.mean() == pytest.approx(50.0, abs=0.2)                # tapa a 20 + 30


def test_la_calcomania_se_va_con_su_cuerpo(tmp_path):
    """El cuerpo desaparece del modelo (queda unido a otro): la calcomanía no queda flotando."""
    s, deco = _escena(tmp_path)
    otra = api.llamar(s, "create_box", {"length": 30, "width": 30, "height": 30, "x": 200})
    assert otra["ok"]
    destino = otra["result"]["bodies_created"][0]["id"]
    assert len(dict(calcomanias_vigentes(s.doc, s.doc.estado_final))) == 1
    assert api.llamar(s, "boolean_operation", {"target": destino, "tools": ["op1.c1"]})["ok"]
    assert "op1.c1" not in s.doc.estado_final.cuerpos
    assert dict(calcomanias_vigentes(s.doc, s.doc.estado_final)) == {}
    assert api.llamar(s, "get_scene_info", {})["result"]["decals"][0]["on_body"] is False


def test_las_copias_del_cuerpo_llevan_su_calcomania(tmp_path):
    s, deco = _escena(tmp_path)
    assert api.llamar(s, "rectangular_pattern", {"bodies": ["op1.c1"], "x_count": 2, "x_spacing": 150})["ok"]
    vigentes = dict(calcomanias_vigentes(s.doc, s.doc.estado_final))
    copias = [k for k in vigentes if k.startswith(deco + "@")]
    assert len(copias) == 1
    x0, x1 = _centro_x(s, deco), float(np.asarray(vigentes[copias[0]]["malla"]["vertices"])[:, 0].mean())
    assert x1 == pytest.approx(x0 + 150, abs=0.2)


def test_reemplazar_imagen_cambia_solo_el_archivo(tmp_path):
    s, deco = _escena(tmp_path)
    s.doc.estado_final.lienzos[deco]                                # existe
    api.llamar(s, "set_decal", {"feature": deco, "opacity": 60, "x": "5 mm"})
    antes = dict(s.paso(deco).p)
    nueva = _png(tmp_path / "otra.png", "#2255cc", (100, 100))
    r = api.llamar(s, "decal_view", {"decal": deco, "action": "replace_image", "image": nueva})
    assert r["ok"], r
    p = s.paso(deco).p
    assert p["archivo"] == "otra.png" and p["imagen"] != antes["imagen"] and p["proporcion"] == pytest.approx(1.0)
    assert p["opacidad"] == 60 and p["dx"] == antes["dx"] and p["plano"] == antes["plano"]
    assert base64.b64decode(p["imagen"])[:4] == b"\x89PNG"
    assert s.paso(deco).nombre == "eloisa"                          # el nombre no cambia por cambiar la imagen


def test_decal_view_errores(tmp_path):
    s, deco = _escena(tmp_path)
    r = api.llamar(s, "decal_view", {"decal": "op1", "action": "edit"})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"          # op1 es la caja, no una calcomanía
    r = api.llamar(s, "decal_view", {"decal": deco, "action": "edit"})
    assert not r["ok"] and r["error_kind"] == "APP_NOT_RUNNING"            # abrir el panel pide la ventana
    r = api.llamar(s, "decal_view", {"decal": deco, "action": "replace_image"})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


def test_manage_browser_acepta_calcomanias_en_un_conjunto(tmp_path):
    s, deco = _escena(tmp_path)
    r = api.llamar(s, "manage_browser", {"action": "create_set", "items": [deco], "name": "Arte"})
    assert r["ok"], r
    assert r["result"]["selection_sets"][0]["items"] == [deco]


def test_guardar_y_abrir_conserva_la_calcomania_y_su_cuerpo(tmp_path):
    s, deco = _escena(tmp_path)
    ruta = proyecto.guardar(s.doc, tmp_path / "con_calco.omnicad")
    d = proyecto.abrir(ruta)
    assert d.estado_final.lienzos[deco]["cuerpo"] == "op1.c1" and d.operacion(deco).nombre == "eloisa"


# ---------------------------------------------------------------- ventana
@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    ruta = tmp_path_factory.mktemp("calco") / "preferencias.ini"
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    v.resize(1280, 800)
    v.show()
    QTest.qWait(1)
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)


@pytest.fixture
def v(ventana, tmp_path):
    s, deco = _escena(tmp_path)
    ventana.set_documento(s.doc)
    QTest.qWait(30)
    ventana.deco, ventana.sesion_calco = deco, s
    yield ventana
    if ventana.panel is not None:
        ventana.panel.cancelar()
    ventana.doc.modificado = False


def _visibles(v):
    return [ident for ident, _datos in v.visor.config.lienzos]


def test_el_navegador_tiene_la_carpeta_calcomanias_con_la_fila_y_su_ojo(v):
    nav = v.navegador
    carpeta = nav.item("__calcomanias__")
    assert carpeta is not None and carpeta.text(0) == "Calcomanías" and carpeta.isExpanded()
    fila = nav.item(v.deco)
    assert fila.parent() is carpeta and fila.text(0) == "eloisa" and fila.data(0, nav_rol_tipo()) == "calcomania"
    assert nav.item("__lienzos__") is None                          # no queda mezclada con los lienzos
    assert [c.text(0) for c in (carpeta.child(i) for i in range(carpeta.childCount()))] == ["eloisa"]


def nav_rol_tipo():
    from omnicad.ui.navegador import ROL_TIPO
    return ROL_TIPO


def test_ocultar_el_cuerpo_oculta_la_calcomania(v):
    assert v.deco in _visibles(v)
    v._ojo("op1.c1")                                                # el ojo del cuerpo en el navegador
    assert v.deco not in _visibles(v)
    v._ojo("op1.c1")
    assert v.deco in _visibles(v)


def test_el_ojo_de_la_calcomania_y_el_de_su_carpeta(v):
    v._ojo(v.deco)
    assert v.deco not in _visibles(v) and v.navegador.item(v.deco).data(0, nav_rol_ojo()) is False
    v._ojo(v.deco)
    assert v.deco in _visibles(v)
    v._ojo("__calcomanias__")
    assert v.deco not in _visibles(v)
    v._ojo("__calcomanias__")
    assert v.deco in _visibles(v)


def nav_rol_ojo():
    from omnicad.ui.navegador import ROL_OJO
    return ROL_OJO


def test_ocultar_el_componente_oculta_sus_cuerpos_y_la_calcomania(v):
    s = v.sesion_calco
    assert api.llamar(s, "create_component", {"bodies": ["op1.c1"], "name": "Tapa"})["ok"]
    QTest.qWait(30)
    comp = next(iter(v.doc.estado_final.componentes))
    assert v.deco in _visibles(v) and "op1.c1" in v.visor._formas
    v._ojo(comp)
    assert v.deco not in _visibles(v) and "op1.c1" not in v.visor._formas


def test_ocultar_por_api_y_el_atajo_v(v):
    v.mostrar_elementos(["op1.c1"], False)
    assert v.deco not in _visibles(v)
    v.mostrar_elementos(["op1.c1"], True)
    v.mostrar_elementos([v.deco], False)
    assert v.deco not in _visibles(v) and "op1.c1" in v.visor._formas
    v.mostrar_elementos([v.deco], True)
    assert v.deco in _visibles(v)


def test_el_menu_tiene_las_opciones_de_fusion_en_su_orden(v):
    from omnicad.ui import acciones_navegador as an
    menu = an.menu(v, v.navegador.item(v.deco))
    textos = [a.text().split("\t")[0] if not a.isSeparator() else "-" for a in menu.actions()]
    assert textos == ["Crear conjunto de selección", "-", "Editar calcomanía", "Reemplazar archivo de imagen", "-",
                      "Suprimir", "Cambiar nombre", "Mostrar/ocultar", "-", "Buscar en la ventana",
                      "Buscar en la secuencia temporal"]


def test_editar_calcomania_reabre_el_panel_con_sus_valores(v):
    from omnicad.ui import acciones_navegador as an
    api.llamar(v.sesion_calco, "set_decal", {"feature": v.deco, "opacity": 55, "x": "7 mm"})
    menu = an.menu(v, v.navegador.item(v.deco))
    next(a for a in menu.actions() if a.text() == "Editar calcomanía").trigger()
    QTest.qWait(50)
    assert v.panel is not None and v.panel.comando.CLAVE == "calcomania"
    assert v.panel.valores["opacidad"] == 55 and "7" in str(v.panel.valores["dx"])
    v.panel.cancelar()
    v.navegador._doble_clic(v.navegador.item(v.deco), 0)             # el doble clic hace lo mismo
    QTest.qWait(50)
    assert v.panel is not None and v.panel.comando.CLAVE == "calcomania"


def test_suprimir_cambiar_nombre_y_buscar_desde_el_menu(v, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    from omnicad.ui import acciones_navegador as an
    menu = an.menu(v, v.navegador.item(v.deco))
    accion = lambda texto: next(a for a in menu.actions() if a.text().split("\t")[0] == texto)  # noqa: E731
    # Reemplazar archivo de imagen
    nueva = _png(tmp_path / "otra.png", "#22aa44", (50, 100))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (nueva, ""))
    accion("Reemplazar archivo de imagen").trigger()
    assert v.doc.operacion(v.deco).p["archivo"] == "otra.png" and v.doc.operacion(v.deco).nombre == "eloisa"
    # Buscar en la ventana: la cámara se centra en la calcomanía
    v.visor.vista("arriba")
    accion("Buscar en la ventana").trigger()
    assert abs(v.visor.objetivo[0] - 0) < 60 and abs(v.visor.objetivo[1] - 0) < 40
    # Buscar en la secuencia temporal
    accion("Buscar en la secuencia temporal").trigger()
    # Cambiar nombre (en el lugar) y volver al menú después de recalcular
    v._renombrar_desde_navegador("calcomania", v.deco, "Arte frontal")
    assert v.navegador.item(v.deco).text(0) == "Arte frontal"
    # Suprimir
    menu = an.menu(v, v.navegador.item(v.deco))
    next(a for a in menu.actions() if a.text().split("\t")[0] == "Suprimir").trigger()
    assert all(o.id != v.deco for o in v.doc.operaciones) and v.navegador.item("__calcomanias__") is None
    v.doc.deshacer()
    assert v.navegador.item(v.deco) is not None and v.deco in _visibles(v)         # deshacer la trae de vuelta
    v.doc.rehacer()
    assert v.navegador.item(v.deco) is None


def test_decal_view_en_vivo_por_el_puente(v):
    s = v.sesion_calco
    s.vista_calcomania = v.vista_calcomania
    r = api.llamar(s, "decal_view", {"decal": v.deco, "action": "edit"})
    assert r["ok"], r
    QTest.qWait(50)
    assert v.panel is not None and v.panel.comando.CLAVE == "calcomania"
    v.panel.cancelar()
    r = api.llamar(s, "decal_view", {"decal": "eloisa", "action": "find_in_timeline"})
    assert r["ok"], r


def test_abrir_un_proyecto_con_calcomania_la_muestra_en_el_navegador(v, tmp_path):
    ruta = proyecto.guardar(v.doc, tmp_path / "guardado.omnicad")
    deco = v.deco
    from omnicad.timeline.documento import Documento
    v.set_documento(Documento())
    assert v.navegador.item(deco) is None
    v.set_documento(proyecto.abrir(ruta))
    QTest.qWait(30)
    assert v.navegador.item(deco).text(0) == "eloisa" and deco in _visibles(v)


def test_un_patron_enorme_no_calcula_cientos_de_calcomanias(tmp_path, monkeypatch):
    from omnicad.timeline import ops_insertar
    monkeypatch.setattr(ops_insertar, "MAX_COPIAS", 1)
    s, deco = _escena(tmp_path)
    assert api.llamar(s, "rectangular_pattern", {"bodies": ["op1.c1"], "x_count": 3, "x_spacing": 150})["ok"]
    copias = [k for k in dict(calcomanias_vigentes(s.doc, s.doc.estado_final)) if k.startswith(deco + "@")]
    assert len(copias) == 1
