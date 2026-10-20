# -*- coding: utf-8 -*-
"""Herramientas del grupo "animacion" (espacio ANIMACIÓN, bug B-80): crear guiones, acciones de transformar,
explosión automática, invertir, copiar/renombrar/borrar, el cuadro a un tiempo dado (con imagen) y Publicar
video; y la transacción de `doc.espacios` (MCP-0b): una herramienta que falla no deja cambios, un cambio de
guion es UN paso de deshacer y deshacer lo revierte. Todo sin abrir la ventana: los cuadros salen del
render de CPU (`nucleo/render_cpu`)."""
import copy
import os

import numpy as np
import pytest

from omnicad import api
from omnicad.nucleo import animacion as anim


@pytest.fixture()
def sesion():
    s = api.Sesion()
    for nombre, x in (("Izquierda", -15.0), ("Derecha", 15.0)):
        r = api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 10, "x": x, "name": nombre})
        assert r["ok"], r
    return s


def _centro(s, cid):
    return anim.centros_de(s.doc.estado_final)[cid]


def _posicion(s, fr, cid):
    """Dónde está el centro del cuerpo en el cuadro `fr` (resultado de get_animation_frame)."""
    M = np.asarray(fr["state"]["matrices"][cid], float).reshape(4, 4)
    return M[:3, :3] @ _centro(s, cid) + M[:3, 3]


def _frame(s, **kwargs):
    r = api.llamar(s, "get_animation_frame", {"width": 64, "height": 48, **kwargs})
    assert r["ok"], r
    return r["result"]


def test_crear_guion_y_transformar_mueve_a_mitad_de_camino(sesion):
    s = sesion
    r = api.llamar(s, "create_storyboard", {"name": "Armado"})
    assert r["ok"] and r["result"] == {"name": "Armado", "index": 0, "storyboards": 1, "current": "Armado"}
    izq, der = list(s.doc.estado_final.cuerpos)
    r = api.llamar(s, "add_animation_action", {"storyboard": "Armado", "type": "transform", "bodies": [izq],
                                               "translation": [10, 0, 0], "start": 0, "duration": 2})
    assert r["ok"] and r["result"]["id"] == "a1" and r["result"]["duration_total"] == 2.0
    ini, mitad, fin = (_frame(s, storyboard="Armado", time=t) for t in (0.0, 1.0, 2.0))
    c = _centro(s, izq)
    assert _posicion(s, ini, izq)[0] == pytest.approx(c[0], abs=1e-6)          # todavía no empezó
    assert _posicion(s, mitad, izq)[0] == pytest.approx(c[0] + 5.0, abs=1e-6)  # suavizado(0.5) = 0.5 → 5 mm
    assert _posicion(s, fin, izq)[0] == pytest.approx(c[0] + 10.0, abs=1e-6)
    assert _posicion(s, fin, der)[0] == pytest.approx(_centro(s, der)[0], abs=1e-6)   # el otro no se mueve
    assert fin["duration"] == 2.0 and fin["image"].ancho == 64 and fin["image"].alto == 48
    assert fin["image"].png.startswith(b"\x89PNG\r\n\x1a\n")


def test_invertir_guion(sesion):
    s = sesion
    api.llamar(s, "create_storyboard", {"name": "Ida"})
    cid = next(iter(s.doc.estado_final.cuerpos))
    api.llamar(s, "add_animation_action", {"storyboard": "Ida", "bodies": [cid], "translation": [10, 0, 0],
                                           "start": 0, "duration": 2})
    r = api.llamar(s, "reverse_storyboard", {"storyboard": "Ida"})
    assert r["ok"] and r["result"]["duration"] == 2.0
    principio, final = _frame(s, time=0.0), _frame(s, time=2.0)
    c = _centro(s, cid)
    assert _posicion(s, principio, cid)[0] == pytest.approx(c[0] + 10.0, abs=1e-6)   # empieza donde terminaba
    assert _posicion(s, final, cid)[0] == pytest.approx(c[0], abs=1e-6)              # y vuelve al diseño


def test_copiar_renombrar_borrar(sesion):
    s = sesion
    api.llamar(s, "create_storyboard", {"name": "Uno"})
    r = api.llamar(s, "copy_storyboard", {"storyboard": "Uno"})
    assert r["ok"] and r["result"]["name"] == "Uno (copia)" and r["result"]["index"] == 1
    r = api.llamar(s, "rename_storyboard", {"storyboard": 0, "new_name": "Principal"})
    assert r["ok"] and r["result"]["name"] == "Principal"
    r = api.llamar(s, "rename_storyboard", {"storyboard": "Principal", "new_name": "uno (copia)"})
    assert not r["ok"] and r["error_kind"] == "NAME_EXISTS"
    r = api.llamar(s, "delete_storyboard", {"storyboard": "Principal"})
    assert r["ok"] and r["result"]["storyboards"] == 1
    nombres = [g["name"] for g in api.llamar(s, "list_storyboards", {})["result"]["storyboards"]]
    assert nombres == ["Uno (copia)"]
    r = api.llamar(s, "delete_storyboard", {})                 # el último no desaparece: queda limpio
    assert r["ok"] and r["result"]["storyboards"] == 1
    r = api.llamar(s, "get_storyboard", {"storyboard": "Principal"})
    assert not r["ok"] and r["error_kind"] == "STORYBOARD_NOT_FOUND"
    r = api.llamar(s, "get_storyboard", {"storyboard": 0})
    assert r["ok"] and r["result"]["storyboard"]["nombre"] == "Uno (copia)"
    assert r["result"]["storyboard"]["acciones"] == []


def test_explosion_automatica_mueve_las_piezas(sesion):
    s = sesion
    api.llamar(s, "create_storyboard", {"name": "Explosión"})
    izq, der = list(s.doc.estado_final.cuerpos)
    r = api.llamar(s, "auto_explode", {"storyboard": "Explosión", "level": "all", "distance": 30,
                                        "start": 0, "duration": 1})
    assert r["ok"] and sorted(r["result"]["bodies"]) == sorted([izq, der])
    fin = _frame(s, storyboard="Explosión", time=1.0)
    d_izq = _posicion(s, fin, izq) - _centro(s, izq)
    d_der = _posicion(s, fin, der) - _centro(s, der)
    assert d_izq == pytest.approx([-30.0, 0.0, 0.0], abs=1e-6)      # la más lejos se mueve `distance`
    assert d_der == pytest.approx([30.0, 0.0, 0.0], abs=1e-6)
    r = api.llamar(s, "auto_explode", {"storyboard": "Explosión", "distance": 0})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


def test_publicar_gif_y_secuencia_png(sesion, tmp_path):
    s = sesion
    api.llamar(s, "create_storyboard", {"name": "Video"})
    cid = next(iter(s.doc.estado_final.cuerpos))
    api.llamar(s, "add_animation_action", {"storyboard": "Video", "bodies": [cid], "translation": [20, 0, 0],
                                           "start": 0, "duration": 2})
    ruta = tmp_path / "anim.gif"
    r = api.llamar(s, "export_animation_video", {"path": str(ruta), "storyboard": "Video", "format": "gif",
                                                 "width": 64, "height": 48, "fps": 1})
    assert r["ok"], r
    assert r["result"]["frames"] == 3                             # tiempos(2.0, 1) = [0, 1, 2]
    assert ruta.exists()
    from PIL import Image
    with Image.open(ruta) as gif:
        assert gif.n_frames == 3 and gif.size == (64, 48)
    carpeta = tmp_path / "cuadros"
    r = api.llamar(s, "export_animation_video", {"path": str(carpeta), "storyboard": "Video", "format": "png",
                                                 "width": 32, "height": 24, "fps": 1})
    assert r["ok"] and r["result"]["frames"] == 3
    assert len(r["result"]["files"]) == 3 and all(os.path.exists(f) for f in r["result"]["files"])
    with Image.open(r["result"]["files"][0]) as png:
        assert png.size == (32, 24)


def test_editar_y_borrar_acciones(sesion):
    s = sesion
    api.llamar(s, "create_storyboard", {"name": "Edición"})
    cid = next(iter(s.doc.estado_final.cuerpos))
    a = api.llamar(s, "add_animation_action", {"bodies": [cid], "translation": [5, 0, 0]})["result"]
    r = api.llamar(s, "edit_animation_action", {"action": a["id"], "start": 1, "duration": 3,
                                                "translation": [8, 0, 0]})
    assert r["ok"] and r["result"]["start"] == 1 and r["result"]["duration"] == 3
    assert r["result"]["duration_total"] == 4.0
    acciones = api.llamar(s, "get_storyboard", {})["result"]["storyboard"]["acciones"]
    assert acciones[0]["traslacion"] == [8, 0, 0] and acciones[0]["inicio"] == 1
    r = api.llamar(s, "edit_animation_action", {"action": "a9"})
    assert not r["ok"] and r["error_kind"] == "ACTION_NOT_FOUND"
    r = api.llamar(s, "delete_animation_action", {"action": a["id"]})
    assert r["ok"] and r["result"]["actions"] == 0 and r["result"]["duration_total"] == 0.0


def test_camara_y_anotacion_del_guion(sesion):
    s = sesion
    api.llamar(s, "create_storyboard", {"name": "Visita"})
    r = api.llamar(s, "set_animation_camera", {"storyboard": "Visita", "view": "front", "start": 0, "duration": 1})
    assert r["ok"]
    r = api.llamar(s, "add_animation_annotation", {"storyboard": "Visita", "text": "Mira esto",
                                                    "point": [0, 0, 20], "start": 0, "duration": 0})
    assert r["ok"] and r["result"]["text"] == "Mira esto"
    fr = _frame(s, storyboard="Visita", time=1.0)
    assert fr["state"]["camera"] is not None and fr["state"]["notes"][0]["text"] == "Mira esto"
    fr = _frame(s, storyboard="Visita", time=0.5)
    assert fr["state"]["notes"][0]["text"] == "Mira esto"      # duracion 0 = hasta el final
    r = api.llamar(s, "set_animation_camera", {"camera": {"objetivo": [0, 0, 0]}})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


def test_una_herramienta_que_falla_deja_los_espacios_iguales(sesion):
    s = sesion
    api.llamar(s, "create_storyboard", {"name": "Uno"})
    antes = copy.deepcopy(s.doc.espacios)
    r = api.llamar(s, "add_animation_action", {"bodies": ["No existe"], "translation": [1, 0, 0]})
    assert not r["ok"] and r["error_kind"] == "BODY_NOT_FOUND"
    assert s.doc.espacios == antes
    # la transacción también restaura si falla sin haber agregado ningún paso de deshacer (MCP-0b)
    with pytest.raises(RuntimeError):
        with s.transaccion():
            s.doc.espacios["animacion"]["guiones"] = []
            raise RuntimeError("boom")
    assert s.doc.espacios == antes


def test_deshacer_revierte_un_cambio_de_guion(sesion):
    s = sesion
    api.llamar(s, "create_storyboard", {"name": "Uno"})
    api.llamar(s, "create_storyboard", {"name": "Dos"})
    nombres = [g["name"] for g in api.llamar(s, "list_storyboards", {})["result"]["storyboards"]]
    assert nombres == ["Uno", "Dos"]
    assert api.llamar(s, "undo", {})["ok"]                       # un cambio de guion = UN paso de deshacer
    nombres = [g["name"] for g in api.llamar(s, "list_storyboards", {})["result"]["storyboards"]]
    assert nombres == ["Uno"]
    assert api.llamar(s, "redo", {})["ok"]
    nombres = [g["name"] for g in api.llamar(s, "list_storyboards", {})["result"]["storyboards"]]
    assert nombres == ["Uno", "Dos"]


def test_la_transaccion_avisa_cambio_de_espacios(sesion):
    s = sesion
    avisos = []
    s.al_cambiar_espacios = lambda: avisos.append(s.doc.espacios["animacion"]["actual"])
    api.llamar(s, "create_storyboard", {"name": "Uno"})
    api.llamar(s, "create_storyboard", {"name": "Dos"})
    assert avisos == [0, 1]                                      # el puente hace que la ventana relea (MCP-0c)
    api.llamar(s, "undo", {})
    api.llamar(s, "redo", {})
    assert avisos == [0, 1, 0, 1]                                # deshacer y rehacer también avisan


def test_el_formato_es_el_de_la_ventana(sesion):
    """Lo que escriben las herramientas lo lee `VentanaAnimacion.desde_dict` tal cual (MCP-0d/0e)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    s = sesion
    api.llamar(s, "create_storyboard", {"name": "Armado"})
    cid = next(iter(s.doc.estado_final.cuerpos))
    api.llamar(s, "add_animation_action", {"storyboard": "Armado", "bodies": [cid], "translation": [10, 0, 0],
                                           "start": 0, "duration": 2})
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.ui.animacion import VentanaAnimacion
    v = VentanaAnimacion(s.doc)
    try:
        v.desde_dict(s.doc.espacios["animacion"])
        assert v.guion.nombre == "Armado" and len(v.guion.acciones) == 1
        assert v.guion.acciones[0]["cuerpos"] == [cid] and v.guion.acciones[0]["traslacion"] == [10, 0, 0]
        assert v.a_dict() == s.doc.espacios["animacion"]         # ida y vuelta sin perder nada
    finally:
        v.close()


def test_el_servidor_mcp_expone_el_grupo_animacion():
    from omnicad.api import doc_markdown
    from omnicad.servidor_mcp.servidor import GRUPOS_POR_DEFECTO
    assert "animacion" in GRUPOS_POR_DEFECTO and "animacion" in doc_markdown.GRUPOS
