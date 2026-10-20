# -*- coding: utf-8 -*-
"""
Estilos visuales, cortes y capas de análisis para el render de CPU (`render_cpu.renderizar`). Sin Qt.

Equivale a lo que el visor de la ventana hace con OpenGL (`ui/visor3d.py`):
  - los seis estilos visuales de Fusion (sombreado, alámbrico, con aristas ocultas o solo visibles);
  - el recorte por planos del Análisis de sección (`recortar`);
  - las primitivas extra de los análisis y las cotas (`capas_a_objetos`: tapas, líneas y puntos).
Las líneas son cintas de triángulos que miran a la cámara, sin iluminación (`"emisivo": True`); la oclusión de lo
que está detrás de una pieza la resuelve el z-buffer del rasterizador.
"""
import math

import numpy as np

from . import render_cpu as rc

# Clave de la API (inglés) → clave del visor de la ventana (`ui/visor3d.py › ESTILOS`).
ESTILOS = {"shaded": "sombreado", "shaded_hidden_edges": "sombreado_ocultas",
           "shaded_visible_edges": "sombreado_aristas", "wireframe": "alambrico",
           "wireframe_hidden_edges": "alambrico_ocultas", "wireframe_visible_edges": "alambrico_visibles"}
COLOR_ARISTA = (0.10, 0.11, 0.13)
COLOR_OCULTA = (0.45, 0.47, 0.52)
SESGO = 2e-3                     # las líneas se adelantan este tanto de la distancia de cámara: no se pelean con la cara
_SIN_EFECTOS = {"sombras": False, "oclusion": False, "reflejos": False, "suelo": False}


def segmentos_de_polilineas(polilineas):
    """Polilíneas (Kx3) → pares de vértices de segmentos (2N x 3), como `ui.visor3d._segmentos`."""
    pares = [np.repeat(np.asarray(p, float), 2, axis=0)[1:-1] for p in polilineas if len(p) >= 2]
    return np.concatenate(pares) if pares else np.zeros((0, 3))


# ---------------------------------------------------------------- recorte por planos
def _recortar_atributos(a, normal, punto):
    """a: (k, 3, D) triángulos con atributos por vértice (las 3 primeras columnas son la posición). Conserva la parte con
    (p − punto)·normal ≤ 0 (el lado de atrás de la normal, como el Análisis de sección) y parte los triángulos que
    cruzan el plano (los atributos se interpolan)."""
    d = (a[:, :, :3] - punto) @ normal
    adentro = (d <= 0).sum(1)
    partes = [a[adentro == 3]]
    for i in np.nonzero((adentro == 1) | (adentro == 2))[0]:
        poligono = []
        for j in range(3):
            k = (j + 1) % 3
            dj, dk = d[i, j], d[i, k]
            if dj <= 0:
                poligono.append(a[i, j])
            if (dj <= 0) != (dk <= 0):
                poligono.append(a[i, j] + dj / (dj - dk) * (a[i, k] - a[i, j]))
        partes += [np.stack([poligono[0], poligono[m], poligono[m + 1]])[None] for m in range(1, len(poligono) - 1)]
    return np.concatenate(partes)


def recortar(objetos, cortes):
    """Los mismos objetos de `render_cpu.renderizar` sin lo que cae del lado de la normal de cada corte
    [(normal, punto)]. Los atributos "n", "colores" y "local" se recortan con la geometría."""
    salida = []
    for o in objetos:
        v = np.asarray(o["v"], float).reshape(-1, 3)
        k = len(v) // 3
        columnas = [v[:k * 3], np.asarray(o["n"], float).reshape(-1, 3)[:k * 3]]
        extras = [c for c in ("colores", "local") if o.get(c) is not None]
        columnas += [np.asarray(o[c], float).reshape(-1, 3)[:k * 3] for c in extras]
        a = np.concatenate(columnas, axis=1).reshape(k, 3, -1)
        for normal, punto in cortes:
            normal = np.asarray(normal, float) / np.linalg.norm(normal)
            a = _recortar_atributos(a, normal, np.asarray(punto, float))
        if not len(a):
            continue
        a = a.reshape(-1, a.shape[2])
        n = a[:, 3:6]
        n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        nuevo = dict(o, v=a[:, :3], n=n)
        for i, c in enumerate(extras):
            nuevo[c] = a[:, 6 + 3 * i:9 + 3 * i]
        salida.append(nuevo)
    return salida


def recortar_segmentos(segmentos, cortes):
    """Pares de puntos (2N x 3) sin la parte que cae del lado de la normal de cada corte (como `recortar`)."""
    s = np.asarray(segmentos, float).reshape(-1, 2, 3)
    for normal, punto in cortes:
        normal = np.asarray(normal, float) / np.linalg.norm(normal)
        d = (s - np.asarray(punto, float)) @ normal                      # (m, 2)
        entero = (d <= 0).all(1)
        mixto = ((d <= 0).sum(1) == 1)
        partes = [s[entero]]
        for i in np.nonzero(mixto)[0]:
            a, b = (0, 1) if d[i, 0] <= 0 else (1, 0)                    # a queda adentro
            corte = s[i, a] + d[i, a] / (d[i, a] - d[i, b]) * (s[i, b] - s[i, a])
            partes.append(np.stack([s[i, a], corte])[None])
        s = np.concatenate(partes)
    return s.reshape(-1, 3)


# ---------------------------------------------------------------- líneas y puntos como triángulos
def _geometria_camara(cam, alto):
    R = np.asarray(cam["R"], float)
    d = float(cam["distancia"])
    ojo = np.asarray(cam["objetivo"], float) + R[2] * d
    escala = 2 * math.tan(math.radians(float(cam.get("fov", 40.0))) / 2) / alto        # mundo por píxel, a distancia 1
    return R, d, ojo, escala, bool(cam.get("ortografica"))


def cinta(segmentos, cam, alto, color, grosor=1.6):
    """Objeto de `renderizar` con cada segmento (pares de puntos) como una cinta de `grosor` píxeles que mira a la
    cámara, adelantada hacia ella (`SESGO`). None si no hay segmentos."""
    s = np.asarray(segmentos, float).reshape(-1, 2, 3)
    if not len(s):
        return None
    R, d, ojo, escala, orto = _geometria_camara(cam, alto)
    medio = s.mean(1)
    hacia_ojo = np.tile(R[2], (len(s), 1)) if orto else rc._unit(ojo - medio)
    prof = np.full(len(s), d) if orto else np.maximum((ojo - medio) @ R[2], 1e-9)
    t = s[:, 1] - s[:, 0]
    largo = np.linalg.norm(t, axis=1)
    lado = np.cross(t, hacia_ojo)
    ln = np.linalg.norm(lado, axis=1)
    bueno = (largo > 1e-12) & (ln > 1e-12)
    if not bueno.any():
        return None
    s, hacia_ojo, prof, lado, ln = s[bueno], hacia_ojo[bueno], prof[bueno], lado[bueno], ln[bueno]
    mitad = lado / ln[:, None] * (grosor * escala * prof / 2)[:, None]
    desvio = hacia_ojo * (SESGO * d)
    a0, a1 = s[:, 0] + desvio, s[:, 1] + desvio
    tris = np.stack([a0 - mitad, a1 - mitad, a1 + mitad, a0 - mitad, a1 + mitad, a0 + mitad], axis=1).reshape(-1, 3)
    return {"v": tris, "n": np.repeat(hacia_ojo, 6, axis=0), "color": tuple(color), "acabado": {}, "emisivo": True}


def _puntos(puntos, cam, alto, color, tamano):
    p = np.asarray(puntos, float).reshape(-1, 3)
    if not len(p):
        return None
    R, d, ojo, escala, orto = _geometria_camara(cam, alto)
    prof = np.full(len(p), d) if orto else np.maximum((ojo - p) @ R[2], 1e-9)
    mitad = (R[0] * (tamano * escala / 2))[None, :] * prof[:, None]
    return cinta(np.stack([p - mitad, p + mitad], axis=1), cam, alto, color, grosor=tamano)


def capas_a_objetos(capas, cam, alto):
    """Capas del visor [("tris", Nx3, color, alfa) | ("lineas", 2Nx3, color, ancho) | ("puntos", Nx3, color, tamaño)]
    → objetos de `renderizar`, todos sin iluminación (la tapa de una sección sale del color pedido)."""
    salida = []
    for tipo, puntos, color, extra in capas:
        color = tuple(color) if color is not None else (0.85, 0.30, 0.25)
        puntos = np.asarray(puntos, float).reshape(-1, 3)
        if not len(puntos):
            continue
        if tipo == "tris":
            v = puntos[:len(puntos) // 3 * 3]
            n = np.cross(v[1::3] - v[0::3], v[2::3] - v[0::3])
            n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            salida.append({"v": v, "n": np.repeat(n, 3, axis=0), "color": color, "acabado": {}, "emisivo": True})
        elif tipo == "lineas":
            o = cinta(puntos[:len(puntos) // 2 * 2], cam, alto, color, grosor=max(1.0, float(extra)))
            if o is not None:
                salida.append(o)
        elif tipo == "puntos":
            o = _puntos(puntos, cam, alto, color, max(2.0, float(extra)))
            if o is not None:
                salida.append(o)
    return salida


# ---------------------------------------------------------------- estilos visuales
def _escena_sin_efectos(escena):
    e = dict(rc.escena_normalizada(escena))
    e.update(_SIN_EFECTOS)
    return e


def _dibujar(objetos, cam, escena, ancho, alto, **kw):
    kw.setdefault("supermuestreo", 1)
    return rc.renderizar(objetos, cam, escena, ancho, alto, **kw)


def _oscuros(rgba):
    return rgba[..., :3].astype(np.int32).sum(axis=2) < 3 * 90


def aplicar_estilo(estilo, objetos, segmentos, cam, escena, ancho, alto, **kw):
    """Imagen RGBA uint8 (alto, ancho, 4) de `objetos` con el estilo visual `estilo` (clave de `ESTILOS`).
    `segmentos`: aristas de los cuerpos (pares de puntos, ver `segmentos_de_polilineas`). `kw`: opciones de
    `renderizar` para el pase sombreado (resolución de sombras, mosaico, luces…). "shaded" es `renderizar` tal cual."""
    if estilo not in ESTILOS:
        raise ValueError(f"Estilo visual desconocido: {estilo}")
    if estilo == "shaded":
        return _dibujar(objetos, cam, escena, ancho, alto, **kw)
    oscura = cinta(segmentos, cam, alto, COLOR_ARISTA)
    if estilo == "shaded_visible_edges":
        return _dibujar(objetos + ([oscura] if oscura else []), cam, escena, ancho, alto, **kw)
    sin_efectos = _escena_sin_efectos(escena)
    aux = {"cielo": kw.get("cielo")}
    fondo = _dibujar([], cam, sin_efectos, ancho, alto, **aux)
    if estilo == "wireframe":
        return _dibujar([oscura], cam, sin_efectos, ancho, alto, **aux) if oscura else fondo
    # Aristas visibles: pase aparte con las caras en blanco y las aristas oscuras (todo sin luces ni suelo).
    caras = [dict(o, color=(1.0, 1.0, 1.0), acabado={}, emisivo=True, colores=None, opacidad=1.0) for o in objetos]
    solido = dict(sin_efectos, fondo="color", color_fondo=[1.0, 1.0, 1.0])
    visibles = _oscuros(_dibujar(caras + ([oscura] if oscura else []), cam, solido, ancho, alto, **aux))
    if estilo == "wireframe_visible_edges":
        salida = fondo.copy()
    else:
        base = (_dibujar(objetos + ([oscura] if oscura else []), cam, escena, ancho, alto, **kw)
                if estilo == "shaded_hidden_edges" else fondo)
        salida = base.copy()
        todas = cinta(segmentos, cam, alto, COLOR_OCULTA)
        if todas is not None:
            alfa = _dibujar([todas], cam, sin_efectos, ancho, alto, fondo_transparente=True, **aux)[..., 3] > 128
            rayas = ((np.arange(ancho)[None, :] + np.arange(alto)[:, None]) // 3) % 2 == 0      # línea de trazos
            ocultas = alfa & ~visibles & rayas
            salida[ocultas, :3] = (np.asarray(COLOR_OCULTA) * 255 + 0.5).astype(np.uint8)
    salida[visibles, :3] = (np.asarray(COLOR_ARISTA) * 255 + 0.5).astype(np.uint8)
    return salida
