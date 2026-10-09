# -*- coding: utf-8 -*-
"""Espacio RENDERIZAR: biblioteca de aspectos, escena, rasterizador y render de CPU (sombras, fondo, transparencia),
y la ventana (aspectos en el documento, render a PNG, galería, persistencia). Lo gráfico con OpenGL se verifica
con capturas nativas (evidencias/capturas/render.png); acá corre offscreen, donde no hay OpenGL y el render cae
al motor de CPU."""
import json
import math
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import render_cpu as rc


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _malla(forma):
    caras = geo.teselar_por_cara(forma, 0.05, 0.3)
    tris = np.concatenate([t for _, t in caras])
    grupos = np.concatenate([np.full(len(t), i) for i, (_, t) in enumerate(caras)])
    return rc.normales_suaves(tris, grupos, 60.0)


def _arriba(objetivo, distancia, fov=40.0):
    """Cámara ortográfica mirando hacia abajo (-Z): x a la derecha, y hacia arriba en la imagen."""
    return rc.camara(np.identity(3), objetivo, distancia, fov, ortografica=True)


def _pixel(cam, p, ancho, alto):
    proy, vista = rc.matrices_camara(cam, ancho / alto)
    h = proy @ vista @ np.r_[p, 1.0]
    return int((h[0] / h[3] + 1) / 2 * ancho), int((1 - h[1] / h[3]) / 2 * alto)


# ---------------------------------------------------------------- aspectos y escena
def test_biblioteca_de_aspectos():
    categorias = {a["categoria"] for a in rc.BIBLIOTECA_ASPECTOS.values()}
    assert categorias == set(rc.CATEGORIAS)
    color, ac = rc.aspecto("Vidrio - Transparente")
    assert len(color) == 3 and ac["transparencia"] > 0.9 and ac["metalico"] == 0
    color, ac = rc.aspecto("Latón - Pulido")
    assert ac["metalico"] == 1.0 and ac["rugosidad"] < 0.2 and ac["nombre"] == "Latón - Pulido"
    assert rc.aspecto("Madera - Roble")[1]["patron"] == "madera"
    with pytest.raises(geo.ErrorGeometria):
        rc.aspecto("Unobtainium")


def test_acabado_normalizado():
    defecto = rc.acabado_normalizado()
    assert defecto["nombre"] == rc.ASPECTO_DEFECTO and defecto["metalico"] == 1.0
    assert rc.acabado_normalizado(material="Vidrio")["transparencia"] == pytest.approx(0.9)
    assert rc.acabado_normalizado(material="Madera (pino)")["patron"] == "madera"
    acotado = rc.acabado_normalizado({"metalico": 2.0, "rugosidad": -1, "basura": 3})
    assert acotado["metalico"] == 1.0 and acotado["rugosidad"] == 0.0 and "basura" not in acotado


def test_escena_normalizada_y_focal():
    e = rc.escena_normalizada({"rotacion": 370, "exposicion": 99, "fondo": "raro", "inventado": 1})
    assert e["rotacion"] == pytest.approx(10.0) and e["exposicion"] == 6.0 and e["fondo"] == "entorno"
    assert "inventado" not in e and e["entorno"] == "fotomaton"
    assert rc.focal_a_fov(50) == pytest.approx(26.99, abs=0.01)
    assert rc.fov_a_focal(rc.focal_a_fov(35)) == pytest.approx(35.0)


def test_mapa_de_tonos_y_srgb():
    assert rc.lineal_a_srgb(rc.srgb_a_lineal([0.2, 0.5, 0.8])) == pytest.approx([0.2, 0.5, 0.8])
    assert rc.mapa_tonos([0.0])[0] == pytest.approx(0.0, abs=1e-6)
    assert rc.mapa_tonos([1e6])[0] == pytest.approx(1.0, abs=1e-3)
    assert rc.mapa_tonos([0.3], 1.0)[0] > rc.mapa_tonos([0.3], 0.0)[0]       # más exposición = más claro


# ---------------------------------------------------------------- rasterizador, normales y sombras
def test_rasterizar_triangulo_y_profundidad():
    sx, sy = np.array([[0.0, 10.0, 0.0]]), np.array([[0.0, 0.0, 10.0]])
    z, ids = rc.rasterizar(sx, sy, np.zeros((1, 3)), 10, 10)
    assert (ids >= 0).sum() == 55                 # centros de píxel con i + j ≤ 9 (la diagonal entra)
    # dos triángulos superpuestos: gana el más cercano (z menor)
    sx2 = np.array([[0.0, 10.0, 0.0], [0.0, 10.0, 0.0]])
    sy2 = np.array([[0.0, 0.0, 10.0], [0.0, 0.0, 10.0]])
    z, ids = rc.rasterizar(sx2, sy2, np.array([[0.5] * 3, [0.2] * 3]), 10, 10)
    assert set(ids[ids >= 0]) == {1} and z[0] == pytest.approx(0.2)


def test_normales_suaves_de_un_cilindro():
    v, n = _malla(geo.cilindro(10, 20))
    assert len(v) == len(n) and len(v) % 3 == 0
    lado = np.abs(v[:, 2] - 10) < 9.9                            # vértices del costado (no de las tapas)
    tapa = (np.abs(n[:, 2]) > 0.99)
    radial = v[:, :2] / np.linalg.norm(v[:, :2], axis=1, keepdims=True)
    costado = lado & ~tapa
    assert np.all(np.einsum("ij,ij->i", n[costado, :2], radial[costado]) > 0.995)   # suaves y hacia afuera
    assert tapa.sum() > 0 and np.allclose(np.abs(n[tapa, 2]), 1.0, atol=1e-3)


def test_mapa_de_sombras():
    placa = geo.caja(20, 20, 2, (0, 0, 10))
    v, _n = _malla(placa)
    luz = rc.luces(0.0)[0]
    m = rc.MapaSombras(v.reshape(-1, 3, 3), luz, 512)
    # el centro de la placa proyectado sobre el suelo según la luz queda a la sombra; lejos, iluminado
    sombreado = np.array([10.0, 10.0, 10.0]) - luz / luz[2] * 10.0
    assert m.visibilidad(sombreado[None], np.array([[0, 0, 1.0]]))[0] < 0.05
    assert m.visibilidad(np.array([[80.0, 80.0, 0.0]]), np.array([[0, 0, 1.0]]))[0] == 1.0


# ---------------------------------------------------------------- render de CPU
@pytest.fixture(scope="module")
def cubo():
    v, n = _malla(geo.caja(10, 10, 10))
    color, ac = rc.aspecto("Plástico - Brillante (Rojo)")
    return [{"v": v, "n": n, "color": color, "acabado": ac}]


def test_render_fondo_de_color_exacto(cubo):
    cam = _arriba((5, 5, 5), 40.0)
    escena = {"fondo": "color", "color_fondo": [0.2, 0.4, 0.6], "suelo": False}
    img = rc.renderizar(cubo, cam, escena, 48, 36, 1, res_sombras=256)
    assert img.shape == (36, 48, 4) and img.dtype == np.uint8
    assert tuple(img[0, 0]) == (51, 102, 153, 255)
    cx, cy = _pixel(cam, (5, 5, 10), 48, 36)
    r, g, b, _a = img[cy, cx]
    assert r > 120 and g < 80 and b < 80                       # el cubo rojo, visto desde arriba


def test_render_sombra_sobre_el_suelo(cubo):
    cam = _arriba((5, 5, 5), 60.0)
    escena = {"fondo": "color", "color_fondo": [1.0, 1.0, 1.0], "reflejos": False, "oclusion": False}
    img = rc.renderizar(cubo, cam, escena, 64, 64, 1, res_sombras=512)
    luz = rc.luces(0.0)[0]
    en_sombra = np.array([5.0, 5.0, 8.0]) - luz / luz[2] * 8.0     # la luz entra por -x, -y: sombra hacia +x, +y
    x, y = _pixel(cam, en_sombra, 64, 64)
    xl, yl = _pixel(cam, (-14.0, -14.0, 0.0), 64, 64)
    assert img[y, x, 0] < 190                                  # oscurecido por la sombra
    assert img[yl, xl, 0] >= 250                               # lejos de la sombra: el fondo blanco


def test_render_fondo_transparente(cubo):
    cam = _arriba((5, 5, 5), 40.0)
    img = rc.renderizar(cubo, cam, {"reflejos": False}, 48, 36, 1, fondo_transparente=True, res_sombras=256)
    cx, cy = _pixel(cam, (5, 5, 10), 48, 36)
    assert img[0, 0, 3] == 0 and img[cy, cx, 3] == 255


def test_render_vidrio_deja_ver_el_fondo(cubo):
    v, n = cubo[0]["v"], cubo[0]["n"]
    color, ac = rc.aspecto("Vidrio - Transparente")
    cam = _arriba((5, 5, 5), 40.0)
    escena = {"fondo": "color", "color_fondo": [0.0, 0.8, 0.0], "suelo": False}
    img = rc.renderizar([{"v": v, "n": n, "color": color, "acabado": ac}], cam, escena, 48, 36, 1, res_sombras=256)
    cx, cy = _pixel(cam, (5, 5, 10), 48, 36)
    assert img[cy, cx, 1] > img[cy, cx, 0] + 40               # a través del vidrio se ve el verde del fondo


def test_render_supermuestreo_y_tamano(cubo):
    cam = rc.camara(np.identity(3), (5, 5, 5), 50.0, 40.0)
    img = rc.renderizar(cubo, cam, {"suelo": False}, 30, 20, 2, res_sombras=256)
    assert img.shape == (20, 30, 4)
    with pytest.raises(geo.ErrorGeometria):
        rc.renderizar(cubo, cam, None, 0, 10)


def test_guardar_png(tmp_path, cubo):
    from PIL import Image
    img = rc.renderizar(cubo, _arriba((5, 5, 5), 40.0), None, 32, 24, 1, res_sombras=256)
    ruta = tmp_path / "r.png"
    rc.guardar_png(img, ruta)
    assert Image.open(ruta).size == (32, 24)


# ---------------------------------------------------------------- ventana y lienzo
def test_color_y_acabado_prioridad():
    from omnicad.ui.render import color_y_acabado
    from omnicad.ui.visor3d import ACERO

    class C:
        tipo, apariencia, material = "solido", None, None
    c = C()
    assert color_y_acabado(c, {})[0] == pytest.approx(list(ACERO))
    c.apariencia = (0.1, 0.2, 0.3)
    assert color_y_acabado(c, {})[0] == pytest.approx([0.1, 0.2, 0.3])
    assert color_y_acabado(c, {"material": "Latón"})[0] == pytest.approx([0.80, 0.65, 0.30])
    color, ac = color_y_acabado(c, {"apariencia": [1, 0, 0], "acabado": {"metalico": 1.0, "nombre": "X"}})
    assert color == [1.0, 0.0, 0.0] and ac["metalico"] == 1.0 and ac["nombre"] == "X"


def test_ventana_aplica_aspectos_en_el_documento(qapp):
    from omnicad.ejemplo import crear_documento_ejemplo
    from omnicad.ui.render import VentanaRender
    doc = crear_documento_ejemplo()
    v = VentanaRender(doc)
    cid = list(doc.estado_final.cuerpos)[0]
    v.aplicar_aspecto("Latón - Pulido", [cid])
    color, ac = rc.aspecto("Latón - Pulido")
    assert doc.propiedades[cid]["apariencia"] == color
    assert doc.propiedades[cid]["acabado"]["metalico"] == 1.0
    assert v.lienzo.objetos[cid]["acabado"]["nombre"] == "Latón - Pulido"
    assert v.lienzo.objetos[cid]["color"] == pytest.approx(color)
    v.quitar_aspecto([cid])
    assert "apariencia" not in doc.propiedades.get(cid, {}) and "acabado" not in doc.propiedades.get(cid, {})
    assert v.lienzo.objetos[cid]["acabado"]["nombre"] == rc.ASPECTO_DEFECTO
    v.close()


def test_ventana_renderiza_png_y_galeria(qapp, tmp_path):
    from PIL import Image
    from omnicad.ejemplo import crear_documento_ejemplo
    from omnicad.ui.render import VentanaRender
    v = VentanaRender(crear_documento_ejemplo())
    v.lienzo.resize(400, 300)
    v.lienzo.encuadrar()
    ruta = tmp_path / "render.png"
    r = v.renderizar(64, 48, "gl", 1, False, str(ruta))       # sin OpenGL (offscreen) cae al motor de CPU
    assert r is not None and "CPU" in r["motor"] and r["ruta"] == str(ruta)
    assert Image.open(ruta).size == (64, 48)
    assert r["imagen"].shape == (48, 64, 4) and r["imagen"][..., :3].std() > 5
    assert len(v.renders) == 1 and v.galeria.lista.count() == 1
    r2 = v.volver_a_renderizar(0)
    assert r2["camara"] == r["camara"] and len(v.renders) == 2
    v.close()


def test_ventana_a_dict_ida_y_vuelta(qapp):
    from omnicad.ejemplo import crear_documento_ejemplo
    from omnicad.ui.render import VentanaRender
    doc = crear_documento_ejemplo()
    v = VentanaRender(doc)
    v.set_escena({"entorno": "cielo_oscuro", "exposicion": 1.5, "focal": 85, "fondo": "color"})
    v.lienzo.orbitar(30, 10)
    datos = json.loads(json.dumps(v.a_dict()))
    w = VentanaRender(doc)
    w.desde_dict(datos)
    assert w.lienzo.escena["entorno"] == "cielo_oscuro" and w.lienzo.escena["exposicion"] == 1.5
    assert w.lienzo.fov == pytest.approx(rc.focal_a_fov(85))
    assert np.allclose(w.lienzo.R, v.lienzo.R, atol=1e-9)
    v.close()
    w.close()


def test_lienzo_transformaciones_y_opacidad(qapp):
    from omnicad.ejemplo import crear_documento_ejemplo
    from omnicad.ui.render import LienzoRender
    doc = crear_documento_ejemplo()
    lz = LienzoRender()
    lz.cargar(doc.estado_final, doc.propiedades)
    cid = list(lz.objetos)[0]
    v0 = lz.objetos[cid]["v0"].copy()
    m = np.identity(4)
    m[:3, 3] = (10, 0, 0)
    lz.set_transformaciones({cid: m})
    malla = next(x for x in lz._mallas if x["id"] == cid)
    assert np.allclose(malla["v"], v0 + np.array([10, 0, 0], np.float32), atol=1e-4)
    lz.opacidad = {cid: 0.25}
    obj = next(o for o in lz.objetos_render() if np.allclose(o["v"], malla["v"]))
    assert obj["opacidad"] == 0.25
    assert lz.z_suelo == pytest.approx(float(v0[:, 2].min()))
    assert math.isfinite(lz.fov)


def test_dialogos_y_paneles(qapp, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QDialog
    from omnicad.ejemplo import crear_documento_ejemplo
    from omnicad.ui import render as ur
    v = ur.VentanaRender(crear_documento_ejemplo())
    d = ur.DialogoRenderizar(v, (640, 480), tmp_path / "a.png")
    assert d.valores()["ancho"] == 1920 and d.valores()["alto"] == 1080
    d.preset.setCurrentIndex(len(ur.PRESETS) - 1)               # personalizado con relación bloqueada
    d.ancho.setValue(960)
    assert d.valores()["alto"] == 540
    recibidas = []
    v.panel_escena.escena_cambiada.connect(recibidas.append)
    v.mostrar_escena()
    assert v.panel_escena.rugosidad.valor() == pytest.approx(rc.ESCENA_DEFECTO["rugosidad_suelo"])
    v.panel_escena.suelo.setChecked(False)
    assert recibidas and recibidas[-1]["suelo"] is False and v.lienzo.escena["suelo"] is False
    v.mostrar_aspecto()
    v.panel_aspecto._seleccionar("Oro - Pulido")
    assert v.panel_aspecto.elegido() == "Oro - Pulido"
    cid = list(v.lienzo.objetos)[0]
    v._clic_cuerpo({"cuerpo": cid})                              # con el panel abierto, el clic aplica el aspecto
    assert v.doc.propiedades[cid]["acabado"]["nombre"] == "Oro - Pulido"
    v.alternar_lienzo(True)
    assert v.lienzo.alta_calidad and v.acciones["lienzo"].isChecked()
    monkeypatch.setattr(ur.DialogoRenderizar, "exec", lambda self: QDialog.Accepted)
    monkeypatch.setattr(ur.DialogoRenderizar, "valores", lambda self: {
        "ancho": 40, "alto": 30, "motor": "cpu", "supermuestreo": 1, "fondo_transparente": True,
        "ruta": str(tmp_path / "b.png")})
    v.dialogo_renderizar()
    assert len(v.renders) == 1 and v.renders[0]["imagen"].shape == (30, 40, 4)
    assert (tmp_path / "b.png").exists()
    v.close()
