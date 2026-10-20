# -*- coding: utf-8 -*-
"""Motor de render de CPU (B-80, MCP-44/45): colores por vértice, objetos sin iluminación, recorte por planos,
capas de análisis y los seis estilos visuales. Imágenes chicas: ninguna prueba pasa de un par de segundos."""
import numpy as np
import pytest

from omnicad.nucleo import render_cpu as rc
from omnicad.nucleo import render_estilos as re

ANCHO, ALTO = 96, 72
FONDO = {"fondo": "color", "color_fondo": [1.0, 1.0, 1.0], "suelo": False, "sombras": False,
         "oclusion": False, "reflejos": False}


def caja(lo=(0, 0, 0), hi=(10, 10, 10)):
    """Objeto de renderizar: una caja de 12 triángulos con normales por cara."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    p = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    caras = [((0, 3, 2, 1), (0, 0, -1)), ((4, 5, 6, 7), (0, 0, 1)), ((0, 1, 5, 4), (0, -1, 0)),
             ((2, 3, 7, 6), (0, 1, 0)), ((1, 2, 6, 5), (1, 0, 0)), ((3, 0, 4, 7), (-1, 0, 0))]
    v, n = [], []
    for (a, b, c, d), normal in caras:
        v += [p[a], p[b], p[c], p[a], p[c], p[d]]
        n += [normal] * 6
    return {"v": np.array(v), "n": np.array(n, float), "color": (0.6, 0.6, 0.7), "acabado": {}}


def camara_iso(objetos):
    pts = np.concatenate([o["v"] for o in objetos])
    centro = (pts.min(0) + pts.max(0)) / 2
    atras = np.array([1.0, -1.0, 0.8])
    atras /= np.linalg.norm(atras)
    derecha = np.cross((0.0, 0.0, 1.0), atras)
    derecha /= np.linalg.norm(derecha)
    R = np.array([derecha, np.cross(atras, derecha), atras])
    return rc.camara(R, centro, float(np.linalg.norm(pts.max(0) - pts.min(0))) * 2.2, 40.0)


def dibujar(objetos, cam=None, **kw):
    return rc.renderizar(objetos, cam or camara_iso(objetos), FONDO, ANCHO, ALTO, supermuestreo=1, **kw)


def pixeles_de(img, color, tol=6):
    c = (np.asarray(color) * 255 + 0.5).astype(int)
    return int((np.abs(img[..., :3].astype(int) - c).max(axis=2) <= tol).sum())


# ---------------------------------------------------------------- colores por vértice y objetos emisivos
def test_colores_por_vertice_pintan_la_malla_y_sin_ellos_no_cambia_nada():
    o = caja()
    base = dibujar([o])
    rojo = dibujar([dict(o, colores=np.tile([0.9, 0.05, 0.05], (len(o["v"]), 1)))])
    celdas = rojo[..., :3].astype(int)
    caja_roja = (celdas[..., 0] > 3 * celdas[..., 1]) & (celdas[..., 0] > 120)
    assert caja_roja.sum() > 500                                     # la caja se ve roja
    assert not np.array_equal(base, rojo)
    assert np.array_equal(base, dibujar([dict(o, colores=None)]))     # colores=None = el color de siempre
    mixto = dibujar([o, dict(caja((30, 0, 0), (40, 10, 10)), colores=np.tile([0.1, 0.9, 0.1], (36, 1)))])
    m = mixto[..., :3].astype(int)
    assert (m[..., 1] > 2 * m[..., 0]).sum() > 100                   # una verde...
    assert ((np.abs(m[..., 0] - m[..., 1]) < 12) & (m[..., 0] < 235)).sum() > 100     # ...y la otra gris


def test_objeto_emisivo_sale_con_su_color_exacto_sin_luces():
    o = dict(caja(), color=(0.2, 0.8, 0.3), emisivo=True)
    img = dibujar([o])
    assert pixeles_de(img, (0.2, 0.8, 0.3), tol=2) > 500             # sin iluminación: el color tal cual
    gris = dibujar([dict(o, emisivo=False)])
    assert pixeles_de(gris, (0.2, 0.8, 0.3), tol=2) < pixeles_de(img, (0.2, 0.8, 0.3), tol=2) / 4


# ---------------------------------------------------------------- recorte por planos
def test_recortar_deja_solo_el_lado_de_atras_y_conserva_atributos():
    o = dict(caja(), colores=np.tile([1.0, 0.0, 0.0], (36, 1)), local=caja()["v"].copy())
    (r,) = re.recortar([o], [((0, 0, 1), (0, 0, 4))])
    assert r["v"][:, 2].max() == pytest.approx(4) and r["v"][:, 2].min() == pytest.approx(0)
    assert len(r["v"]) == len(r["n"]) == len(r["colores"]) == len(r["local"]) and len(r["v"]) % 3 == 0
    assert np.allclose(np.linalg.norm(r["n"], axis=1), 1)
    en_planta = sum(abs(np.cross(t[1] - t[0], t[2] - t[0])[2]) for t in r["v"].reshape(-1, 3, 3)) / 2
    assert en_planta == pytest.approx(100)                           # queda el piso; las paredes no se ven en planta
    assert re.recortar([o], [((0, 0, 1), (0, 0, -1))]) == []         # todo del lado de la normal: desaparece
    (entero,) = re.recortar([o], [((0, 0, 1), (0, 0, 99))])
    assert len(entero["v"]) == 36                                    # todo atrás del plano: queda igual
    (dos,) = re.recortar([o], [((0, 0, 1), (0, 0, 8)), ((1, 0, 0), (3, 0, 0))])
    assert dos["v"][:, 2].max() == pytest.approx(8) and dos["v"][:, 0].max() == pytest.approx(3)


def test_recorte_se_ve_en_la_imagen():
    o = caja()
    cam = camara_iso([o])
    entero = dibujar([o], cam)
    medio = dibujar(re.recortar([o], [((0, 0, 1), (0, 0, 3))]), cam)
    ocupado = lambda img: int((img[..., :3].astype(int).sum(axis=2) < 3 * 250).sum())     # noqa: E731
    assert 0 < ocupado(medio) < ocupado(entero) * 0.8


# ---------------------------------------------------------------- capas y líneas
def test_capas_a_objetos_arma_tapas_lineas_y_puntos_sin_iluminacion():
    o = caja()
    cam = camara_iso([o])
    tapa = np.array([[0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 0, 10], [10, 10, 10], [0, 10, 10]], float)
    rayas = np.array([[0, 0, 0], [10, 10, 10]], float)
    objetos = re.capas_a_objetos([("tris", tapa, (0.85, 0.30, 0.25), 0.85), ("lineas", rayas, (0, 0, 1), 3.0),
                                  ("puntos", np.array([[5, 5, 5.0]]), (0, 1, 0), 8)], cam, ALTO)
    assert len(objetos) == 3 and all(x["emisivo"] for x in objetos)
    assert re.capas_a_objetos([("lineas", np.zeros((0, 3)), None, 1.0)], cam, ALTO) == []
    img = dibujar([dict(o, opacidad=0.0), objetos[0]], cam)
    assert pixeles_de(img, (0.85, 0.30, 0.25), tol=2) > 200          # la tapa sale del color pedido
    linea = re.cinta(np.array([[0, 0, 0], [10, 10, 10.0]]), cam, ALTO, (0, 0, 1), grosor=3.0)
    assert linea is not None and len(linea["v"]) == 6
    assert re.cinta(np.zeros((0, 3)), cam, ALTO, (0, 0, 0)) is None
    assert re.cinta(np.array([[1, 1, 1], [1, 1, 1.0]]), cam, ALTO, (0, 0, 0)) is None     # segmento sin largo


def test_las_lineas_quedan_detras_de_las_piezas():
    o = caja((0, 0, 0), (10, 10, 10))
    cam = camara_iso([o])
    por_dentro = np.array([[5, 5, 2], [5, 5, 8.0]])                  # adentro de la caja: la tapa la oculta
    afuera = re.cinta(por_dentro + [0, 0, 10], cam, ALTO, (0, 0, 1), grosor=3.0)       # sobre la tapa: se ve
    dentro = re.cinta(por_dentro, cam, ALTO, (0, 0, 1), grosor=3.0)
    assert pixeles_de(dibujar([o, afuera], cam), (0, 0, 1), tol=2) > 0
    assert pixeles_de(dibujar([o, dentro], cam), (0, 0, 1), tol=2) == 0


# ---------------------------------------------------------------- estilos visuales
def estilo(nombre, objetos, cam):
    seg = re.segmentos_de_polilineas([np.array([a, b], float) for a, b in aristas_de_caja()])
    return re.aplicar_estilo(nombre, objetos, seg, cam, FONDO, ANCHO, ALTO)


def aristas_de_caja(lo=(0, 0, 0), hi=(10, 10, 10)):
    c = [(x, y, z) for z in (lo[2], hi[2]) for y in (lo[1], hi[1]) for x in (lo[0], hi[0])]
    return [(c[i], c[j]) for i in range(8) for j in range(i + 1, 8)
            if sum(a != b for a, b in zip(c[i], c[j], strict=True)) == 1]


def test_los_seis_estilos_dibujan_lo_que_dicen():
    o = caja()
    cam = camara_iso([o])
    imagenes = {e: estilo(e, [o], cam) for e in re.ESTILOS}
    assert all(i.shape == (ALTO, ANCHO, 4) and i.dtype == np.uint8 for i in imagenes.values())
    assert np.array_equal(imagenes["shaded"], dibujar([o], cam))                      # shaded = renderizar tal cual
    oscuros = {e: int(re._oscuros(i).sum()) for e, i in imagenes.items()}
    assert oscuros["shaded"] == 0 and oscuros["wireframe"] > 0
    assert oscuros["wireframe"] > oscuros["wireframe_visible_edges"] > 0             # las ocultas no se dibujan
    assert oscuros["shaded_visible_edges"] > 0
    hidden = pixeles_de(imagenes["wireframe_hidden_edges"], re.COLOR_OCULTA, tol=3)
    assert hidden > 0 and pixeles_de(imagenes["wireframe_visible_edges"], re.COLOR_OCULTA, tol=3) == 0
    assert pixeles_de(imagenes["shaded_hidden_edges"], re.COLOR_OCULTA, tol=3) > 0
    assert pixeles_de(imagenes["shaded_visible_edges"], re.COLOR_OCULTA, tol=3) == 0
    # sombreado con aristas visibles = la caja sombreada más líneas; el alámbrico no tiene caras sombreadas
    gris = lambda img: int(((img[..., :3].astype(int).sum(axis=2) < 3 * 240) & ~re._oscuros(img)).sum())   # noqa: E731
    assert gris(imagenes["shaded_visible_edges"]) > 500 and gris(imagenes["wireframe"]) < 100


def test_estilo_desconocido_y_sin_aristas():
    o = caja()
    cam = camara_iso([o])
    with pytest.raises(ValueError, match="Estilo visual desconocido"):
        re.aplicar_estilo("raro", [o], np.zeros((0, 3)), cam, FONDO, ANCHO, ALTO)
    for e in re.ESTILOS:                                              # sin aristas (una malla) no se rompe
        assert re.aplicar_estilo(e, [o], np.zeros((0, 3)), cam, FONDO, ANCHO, ALTO).shape == (ALTO, ANCHO, 4)
