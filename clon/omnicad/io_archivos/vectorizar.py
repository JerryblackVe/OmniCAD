# -*- coding: utf-8 -*-
"""
Imagen → vector: convierte un PNG/JPG/BMP en contornos cerrados (para grabar, cortar o extruir un logo).

Método: se toma la «tinta» de la imagen (oscuridad o, si hay transparencia, la opacidad), se suaviza con un
filtro gaussiano, se trazan las curvas de nivel del umbral con contourpy (con precisión de subpíxel, los
agujeros salen como contornos aparte) y se simplifican con Ramer-Douglas-Peucker. Nada de librerías de
trazado externas: Pillow, numpy, scipy y contourpy.

Salida: primitivas como las de `svg.leer_svg` — ('polilinea', [(x, y)…], True) en píxeles, Y hacia arriba —
o, con `curvas=True`, ('curva', [(x, y)…], True): una spline de ajuste cerrada por contorno (más suave y con
muchas menos entidades; los contornos de menos de MIN_PUNTOS_CURVA vértices quedan polilíneas). Con
`angulo_esquina > 0` el contorno se parte en sus esquinas: ('curva', [(x, y)…], False) por tramo, o
('linea', a, b) si el tramo tiene solo dos puntos. El paso a milímetros lo hace
`boceto_archivos.boceto_desde_primitivas`.
"""
from pathlib import Path

import numpy as np

CANALES = ("auto", "luminosidad", "alfa")
MIN_PUNTOS_CURVA = 12       # con curvas=True, un contorno con menos vértices que esto queda polígono (ver `vectorizar_imagen`)


class ErrorVectorizar(ValueError):
    pass


def _otsu(tinta):
    """Umbral de Otsu (0-255) de una imagen de tinta uint8."""
    hist = np.bincount(tinta.ravel(), minlength=256).astype(float)
    total = hist.sum()
    if total == 0:
        return 128.0
    suma = float(np.dot(np.arange(256), hist))
    wb = sb = 0.0
    mejor, umbral = -1.0, 128
    for t in range(256):
        wb += hist[t]
        if wb == 0:
            continue
        wf = total - wb
        if wf == 0:
            break
        sb += t * hist[t]
        mb, mf = sb / wb, (suma - sb) / wf
        entre = wb * wf * (mb - mf) ** 2
        if entre > mejor:
            mejor, umbral = entre, t
    return float(umbral) + 0.5


def _rdp(pts, tol):
    """Ramer-Douglas-Peucker de una polilínea abierta (Nx2)."""
    n = len(pts)
    if n < 3:
        return pts
    keep = np.zeros(n, bool)
    keep[0] = keep[-1] = True
    pila = [(0, n - 1)]
    while pila:
        i, j = pila.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        seg = pts[i + 1:j]
        d = b - a
        largo = float(np.hypot(d[0], d[1]))
        if largo < 1e-12:
            dist = np.hypot(seg[:, 0] - a[0], seg[:, 1] - a[1])
        else:
            dist = np.abs(d[0] * (seg[:, 1] - a[1]) - d[1] * (seg[:, 0] - a[0])) / largo
        k = int(np.argmax(dist))
        if dist[k] > tol:
            m = i + 1 + k
            keep[m] = True
            pila += [(i, m), (m, j)]
    return pts[keep]


def _simplificar_cerrado(pts, tol):
    """RDP de un contorno cerrado (sin repetir el primer punto al final): se parte en el punto más lejano."""
    if len(pts) < 4:
        return pts
    k = int(np.argmax(np.hypot(pts[:, 0] - pts[0, 0], pts[:, 1] - pts[0, 1])))
    a = _rdp(pts[:k + 1], tol)
    b = _rdp(np.vstack([pts[k:], pts[:1]]), tol)
    return np.vstack([a[:-1], b[:-1]])


def _area(pts):
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _dobles(pts):
    """Ángulo (en grados) que el contorno dobla en cada vértice: 0 si sigue derecho."""
    d1 = pts - np.roll(pts, 1, axis=0)          # del vértice anterior a este
    d2 = np.roll(pts, -1, axis=0) - pts          # de este al siguiente
    l1 = np.hypot(d1[:, 0], d1[:, 1])
    l2 = np.hypot(d2[:, 0], d2[:, 1])
    cos = np.zeros(len(pts))
    ok = (l1 > 1e-12) & (l2 > 1e-12)
    cos[ok] = (d1[ok] * d2[ok]).sum(axis=1) / (l1[ok] * l2[ok])
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def _tramos_por_esquinas(pts, angulo):
    """El contorno partido en sus esquinas: los tramos abiertos que van de esquina a esquina (vacío si no
    hay esquinas)."""
    esquinas = [i for i, d in enumerate(_dobles(pts)) if d > angulo]
    if len(esquinas) < 2:
        return []
    salida = []
    for k, i in enumerate(esquinas):
        j = esquinas[(k + 1) % len(esquinas)]
        salida.append(pts[i:j + 1] if i < j else np.vstack([pts[i:], pts[:j + 1]]))
    return salida


def vectorizar_imagen(ruta, *, umbral=None, invertir=False, suavizado=1.0, tolerancia=0.5, area_minima=4.0,
                      canal="auto", maximo_lado=2000, curvas=False, angulo_esquina=0.0):
    """Contornos de la imagen como primitivas en píxeles (Y hacia arriba, origen en la esquina inferior
    izquierda de la imagen).

    umbral: 0-255 sobre la tinta; None = Otsu. invertir: la tinta es lo claro. suavizado: sigma del filtro en
    píxeles (0 = sin filtro). tolerancia: desvío máximo de la simplificación, en píxeles. area_minima: los
    contornos de menos píxeles² se descartan (ruido). canal: "luminosidad", "alfa" o "auto" (alfa si la
    imagen tiene transparencia real). maximo_lado: si la imagen es más grande se reduce para trazarla.
    angulo_esquina: en grados, el doble a partir del cual un vértice es una esquina. 0 = sin detección (todo
    como antes). Con curvas=True, el contorno se parte en sus esquinas: entre esquina y esquina sale un tramo
    abierto (una spline, o una recta si el tramo tiene dos puntos) y los tramos comparten sus puntas, así que
    el perfil sigue cerrado. Solo afecta a los contornos que salen como spline (los de más de MIN_PUNTOS_CURVA
    vértices): los que quedan polilínea no cambian. Un contorno con una sola esquina no se parte (quedaría
    abierto)."""
    from PIL import Image
    p = Path(ruta)
    if not p.is_file():
        raise ErrorVectorizar(f"No existe la imagen: {ruta}")
    if canal not in CANALES:
        raise ErrorVectorizar(f"canal es uno de {', '.join(CANALES)}.")
    if not tolerancia >= 0 or not suavizado >= 0 or not area_minima >= 0:
        raise ErrorVectorizar("tolerancia, suavizado y area_minima no pueden ser negativos.")
    if not angulo_esquina >= 0:
        raise ErrorVectorizar("El ángulo de esquina no puede ser negativo.")
    try:
        with Image.open(p) as original:
            original.load()
            img = original.copy()
    except Exception as e:  # noqa: BLE001 — Pillow lanza de todo según el formato
        raise ErrorVectorizar(f"No se pudo leer la imagen: {e}") from e
    ancho0, alto0 = img.size
    if ancho0 < 2 or alto0 < 2:
        raise ErrorVectorizar("La imagen es demasiado chica.")
    factor = 1.0
    if max(ancho0, alto0) > maximo_lado:
        factor = maximo_lado / max(ancho0, alto0)
        img = img.resize((max(2, round(ancho0 * factor)), max(2, round(alto0 * factor))), Image.LANCZOS)
    rgba = img.convert("RGBA")
    a = np.asarray(rgba, dtype=np.float64)
    alfa = a[:, :, 3]
    usar_alfa = canal == "alfa" or (canal == "auto" and alfa.min() < 250)
    if usar_alfa:
        tinta = alfa
    else:
        lum = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
        lum = lum * (alfa / 255.0) + 255.0 * (1 - alfa / 255.0)          # lo transparente cuenta como blanco
        tinta = 255.0 - lum
    if invertir:
        tinta = 255.0 - tinta
    if suavizado > 0:
        from scipy.ndimage import gaussian_filter
        tinta = gaussian_filter(tinta, suavizado)
    nivel = _otsu(np.clip(tinta, 0, 255).astype(np.uint8)) if umbral is None else float(umbral)
    if not 0 < nivel < 255:
        raise ErrorVectorizar("El umbral tiene que estar entre 0 y 255 (sin incluirlos).")
    alto, ancho = tinta.shape
    z = np.pad(tinta, 1, constant_values=0.0)           # borde de «papel» para que todo contorno cierre
    import contourpy
    gen = contourpy.contour_generator(z=z, line_type=contourpy.LineType.Separate)
    lineas = gen.lines(nivel)
    salida = []
    for ln in lineas:
        pts = np.asarray(ln, dtype=float)
        if len(pts) < 4 or not np.allclose(pts[0], pts[-1]):
            continue
        pts = pts[:-1]
        # índices del arreglo con borde → píxeles de la imagen: el centro del píxel (i, j) está en (i + .5, j + .5)
        x = (pts[:, 0] - 1 + 0.5) / factor
        y = (alto - (pts[:, 1] - 1 + 0.5)) / factor
        pts = np.column_stack([x, y])
        if abs(_area(pts)) < area_minima / (factor * factor):
            continue
        pts = _simplificar_cerrado(pts, tolerancia / factor)
        if len(pts) < 3 or abs(_area(pts)) < 1e-9:
            continue
        # Un spline de ajuste cerrado por pocos vértices se pasa de largo en las esquinas (un rectángulo de la tinta
        # invertida, pegado al borde de la imagen, salía 53 × 45 en vez de 45 × 30: T-10 de la prueba de tortura): ese
        # contorno es casi un polígono y, simplificado a `tolerancia`, el polígono ya es igual de fiel.
        spline = curvas and len(pts) >= MIN_PUNTOS_CURVA
        tramos = _tramos_por_esquinas(pts, angulo_esquina) if spline and angulo_esquina > 0 else []
        if not tramos:
            salida.append(("curva" if spline else "polilinea", [tuple(q) for q in pts], True))
            continue
        # Con esquinas: el contorno se parte en tramos abiertos que comparten sus puntas (el perfil sigue cerrado).
        for tramo in tramos:
            if len(tramo) == 2:
                salida.append(("linea", tuple(tramo[0]), tuple(tramo[1])))
            else:
                salida.append(("curva", [tuple(q) for q in tramo], False))
    if not salida:
        raise ErrorVectorizar("No se encontró nada para vectorizar con ese umbral: probá con otro umbral, "
                              "invertir o canal.")
    return salida
