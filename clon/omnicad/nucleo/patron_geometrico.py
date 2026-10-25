# -*- coding: utf-8 -*-
"""
Patrón geométrico [Plastic > Create > Geometric Pattern de Fusion]: reparte esferas, cilindros, cajas u objetos a medida
sobre una cara plana, con un gradiente de tamaño entre dos límites. Función pura: devuelve la forma con todos los objetos
(la operación la une, la corta, la interseca o la deja como cuerpos nuevos).

Distribuciones (en el plano de la cara, con U y V del plano):
  - rectangular: rejilla; `separacion` "incremento" (cada `distancia`) o "extension" (`cantidad_u` × `cantidad_v` repartidos
    de borde a borde);
  - triangular: filas desfasadas media separación (`distancia` entre vecinos);
  - hexagonal: panal, los vértices de hexágonos de lado `distancia`;
  - circular: anillos concentricos cada `distancia_radial`, con objetos cada `distancia_radial` sobre el arco;
  - radial: `rayos` líneas desde el centro con un objeto cada `distancia_radial`.
La alineación en U (izquierda, centro, derecha) y en V (abajo, medio, arriba) y sus desfases ubican las tres primeras; en
las dos últimas el centro es el de la caja de la cara más el desfase.

Tamaño: crece de `tamano1` (en el centro del patrón) a `tamano2` (en la esquina de la caja de la cara) como
tamano1 + (tamano2 − tamano1)·tᵈ, con t = distancia al centro / distancia a la esquina y d = `dispersion`.
Esfera: diámetro; cilindro: diámetro y altura; caja: lado; a medida: la mayor dimensión de la forma.
"""
import math

import numpy as np

from . import geometria as geo

DISTRIBUCIONES = ("rectangular", "triangular", "hexagonal", "circular", "radial")
OBJETOS = ("esfera", "cilindro", "caja", "personalizado")
MAXIMO_OBJETOS = 2000


def _caja_uv(cara, plano):
    """(u0, u1, v0, v1) de la cara en el plano (u, v) de `plano`."""
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(cara)
    esquinas = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]) - np.asarray(plano.origen, float)
    u, v = esquinas @ np.asarray(plano.u, float), esquinas @ np.asarray(plano.v, float)
    return float(u.min()), float(u.max()), float(v.min()), float(v.max())


def _eje(minimo, maximo, alineacion, desfase, distancia, cantidad, extension, izq, centro_, der):
    """Posiciones sobre un eje (U o V): alineadas a un borde o al centro, cada `distancia` o `cantidad` repartidas."""
    if extension:
        a, b = minimo + desfase, maximo - desfase
        return [a] if cantidad <= 1 else list(np.linspace(a, b, int(cantidad)))
    if alineacion == centro_:
        mid = (minimo + maximo) / 2 + desfase
        n = int(math.floor((maximo - minimo) / distancia / 2 + 1e-9))
        return [mid + k * distancia for k in range(-n, n + 1)]
    if alineacion == izq:
        inicio = minimo + desfase
        n = int(math.floor((maximo - inicio) / distancia + 1e-9))
        return [inicio + k * distancia for k in range(0, n + 1)]
    fin = maximo - desfase
    n = int(math.floor((fin - minimo) / distancia + 1e-9))
    return [fin - k * distancia for k in range(0, n + 1)]


def _estimar(distribucion, u0, u1, v0, v1, p):
    """Cuántos candidatos generaría la distribución (aproximado, sin armarlos)."""
    ancho, alto, d, dr = u1 - u0, v1 - v0, p["distancia"], p["distancia_radial"]
    if distribucion == "rectangular":
        if p["separacion"] == "extension":
            return max(1, int(p["cantidad_u"])) * max(1, int(p["cantidad_v"]))
        return (ancho / d + 1) * (alto / d + 1)
    if distribucion in ("triangular", "hexagonal"):
        if p["separacion"] == "extension" and p["cantidad_u"] > 1:
            d = (ancho - 2 * p["desfase_u"]) / (p["cantidad_u"] - 1)
        return (ancho / d + 1) * (alto / (d * math.sqrt(3) / 2) + 1)
    anillos = (math.hypot(ancho / 2, alto / 2) + abs(p["desfase_u"]) + abs(p["desfase_v"])) / dr
    return math.pi * anillos ** 2 if distribucion == "circular" else int(p["rayos"]) * anillos


def _puntos(distribucion, u0, u1, v0, v1, p):
    """[(u, v)] candidatos de la distribución, sin filtrar por la cara."""
    d, dr = p["distancia"], p["distancia_radial"]
    if distribucion in ("circular", "radial") and dr <= 0:
        raise geo.ErrorGeometria("La distancia radial tiene que ser positiva.")
    if distribucion in ("triangular", "hexagonal") and d <= 0 and not (p["separacion"] == "extension" and p["cantidad_u"] > 1):
        raise geo.ErrorGeometria("La distancia entre objetos tiene que ser positiva.")
    if _estimar(distribucion, u0, u1, v0, v1, p) > 50 * MAXIMO_OBJETOS:      # antes de enumerar: 0,003 mm daría 400 M de puntos
        raise geo.ErrorGeometria(f"El patrón tendría muchísimos más de {MAXIMO_OBJETOS} objetos: aumentá la distancia.")
    cu, cv = (u0 + u1) / 2 + p["desfase_u"], (v0 + v1) / 2 + p["desfase_v"]
    if distribucion == "rectangular":
        us = _eje(u0, u1, p["alineacion_u"], p["desfase_u"], d, p["cantidad_u"], p["separacion"] == "extension",
                  "izquierda", "centro", "derecha")
        vs = _eje(v0, v1, p["alineacion_v"], p["desfase_v"], d, p["cantidad_v"], p["separacion"] == "extension",
                  "abajo", "medio", "arriba")
        return [(u, v) for v in vs for u in us]
    if distribucion in ("triangular", "hexagonal"):
        paso_v = d * math.sqrt(3) / 2
        if p["separacion"] == "extension" and p["cantidad_u"] > 1:
            d = (u1 - u0 - 2 * p["desfase_u"]) / (p["cantidad_u"] - 1)
            paso_v = d * math.sqrt(3) / 2
        us0 = _eje(u0, u1, p["alineacion_u"], p["desfase_u"], d, 0, False, "izquierda", "centro", "derecha")
        vs = _eje(v0, v1, p["alineacion_v"], p["desfase_v"], paso_v, 0, False, "abajo", "medio", "arriba")
        base = us0[0] if us0 else u0
        pts = []
        for j, v in enumerate(vs):
            desfase = d / 2 if j % 2 else 0.0
            for i in range(-1, len(us0) + 1):
                u = base + i * d + desfase
                if u0 - 1e-9 <= u <= u1 + 1e-9 and not (distribucion == "hexagonal" and (i - (j - j % 2) // 2 - j) % 3 == 0):
                    pts.append((u, v))
        return pts
    radio_max = math.hypot((u1 - u0) / 2, (v1 - v0) / 2) + abs(p["desfase_u"]) + abs(p["desfase_v"])
    if dr <= 0:
        raise geo.ErrorGeometria("La distancia radial tiene que ser positiva.")
    if distribucion == "circular":
        pts = [(cu, cv)]
        k = 1
        while k * dr <= radio_max:
            r = k * dr
            n = max(3, int(round(2 * math.pi * r / dr)))
            pts += [(cu + r * math.cos(2 * math.pi * i / n), cv + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
            k += 1
        return pts
    rayos = int(p["rayos"])
    if rayos < 1:
        raise geo.ErrorGeometria("La distribución radial necesita al menos un rayo.")
    pts = [(cu, cv)]
    k = 1
    while k * dr <= radio_max:
        pts += [(cu + k * dr * math.cos(2 * math.pi * i / rayos), cv + k * dr * math.sin(2 * math.pi * i / rayos))
                for i in range(rayos)]
        k += 1
    return pts


def _dentro(cara, centro3d, margen, clasificador, distancia_al_borde):
    from OCP.TopAbs import TopAbs_IN, TopAbs_ON
    estado = clasificador(cara, centro3d)
    if estado != TopAbs_IN and not (estado == TopAbs_ON and margen <= 0):      # sobre el borde solo sin margen
        return False
    return margen <= 0 or distancia_al_borde(centro3d) >= margen - 1e-9


def _objeto(tipo, tam, sobre_la_cara, custom):
    """Un objeto de tamaño `tam` en su marco local (z hacia afuera de la cara): la esfera centrada, el cilindro y la caja con
    la base en el plano de la cara (hacia afuera si `sobre_la_cara`, hacia adentro si no)."""
    z0 = 0.0 if sobre_la_cara else -tam
    if tipo == "esfera":
        return geo.esfera(tam / 2, (0, 0, 0))
    if tipo == "cilindro":
        return geo.cilindro(tam / 2, tam, (0, 0, z0), (0, 0, 1))
    if tipo == "caja":
        return geo.caja(tam, tam, tam, (-tam / 2, -tam / 2, z0))
    (x0, y0, z_0), (x1, y1, z_1) = geo.caja_envolvente(custom)
    centro = np.array([(x0 + x1) / 2, (y0 + y1) / 2, (z_0 + z_1) / 2])
    mayor = max(x1 - x0, y1 - y0, z_1 - z_0)
    f = tam / mayor
    m = np.identity(4)
    m[:3, :3] *= f
    m[:3, 3] = -centro * f
    return geo.transformar(custom, m)


def patron_geometrico(cara, objeto, tamano1, tamano2, *, dispersion=1.0, distribucion="rectangular",
                      sobre_la_cara=True, personalizado=None, **p):
    """Forma (compuesto) con los objetos repartidos sobre la cara plana `cara`.

    `p`: separacion ("incremento" | "extension"), distancia, cantidad_u, cantidad_v, distancia_radial, rayos,
    orientacion ("paralela" | "cara"), alineacion_u, desfase_u, alineacion_v, desfase_v, limpiar_perimetro,
    desfase_perimetro. `sobre_la_cara`: los cilindros y cajas salen hacia afuera (unir, cuerpo nuevo) o entran en el
    material (cortar, intersecar)."""
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepTools import BRepTools
    from OCP.gp import gp_Pnt
    from . import solidos_modificar as sm
    base = dict(separacion="incremento", distancia=10.0, cantidad_u=3, cantidad_v=3, distancia_radial=10.0, rayos=8,
                orientacion="cara", alineacion_u="centro", desfase_u=0.0, alineacion_v="medio", desfase_v=0.0,
                limpiar_perimetro=True, desfase_perimetro=0.0)
    desconocidos = set(p) - set(base)
    if desconocidos:
        raise geo.ErrorGeometria(f"Opciones desconocidas del patrón geométrico: {', '.join(sorted(desconocidos))}")
    p = {**base, **p}
    if distribucion not in DISTRIBUCIONES:
        raise geo.ErrorGeometria(f"Distribución desconocida: {distribucion}")
    if objeto not in OBJETOS:
        raise geo.ErrorGeometria(f"Tipo de objeto desconocido: {objeto}")
    if objeto == "personalizado" and personalizado is None:
        raise geo.ErrorGeometria("El objeto personalizado necesita un cuerpo.")
    if p["distancia"] <= 0 and distribucion in ("rectangular", "triangular", "hexagonal") and p["separacion"] == "incremento":
        raise geo.ErrorGeometria("La distancia entre objetos tiene que ser positiva.")
    if min(tamano1, tamano2) <= 0 or dispersion <= 0:
        raise geo.ErrorGeometria("Los límites de tamaño y la dispersión tienen que ser positivos.")
    plano = sm._plano_de_cara(cara)
    if plano is None:
        raise geo.ErrorGeometria("El patrón geométrico necesita una cara plana.")
    u0, u1, v0, v1 = _caja_uv(cara, plano)
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    esquina = math.hypot((u1 - u0) / 2, (v1 - v0) / 2) or 1.0
    origen, u, v, n = (np.asarray(x, float) for x in (plano.origen, plano.u, plano.v, plano.normal))
    clas = lambda c, q: BRepClass_FaceClassifier(c, gp_Pnt(*q), 1e-6).State()  # noqa: E731
    contorno = BRepTools.OuterWire_s(cara)

    def al_borde(q):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
        return BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*q)).Vertex(), contorno).Value()

    piezas = []
    for pu, pv in _puntos(distribucion, u0, u1, v0, v1, p):
        t = min(1.0, math.hypot(pu - cu, pv - cv) / esquina)
        tam = tamano1 + (tamano2 - tamano1) * t ** dispersion
        q = origen + u * pu + v * pv
        margen = p["desfase_perimetro"] + (tam * math.sqrt(2) / 2 if p["limpiar_perimetro"] else 0.0)
        if not _dentro(cara, q, margen, clas, al_borde):
            continue
        piezas.append((q, tam))
        if len(piezas) > MAXIMO_OBJETOS:
            raise geo.ErrorGeometria(f"El patrón tendría más de {MAXIMO_OBJETOS} objetos: aumentá la distancia o el tamaño.")
    if not piezas:
        raise geo.ErrorGeometria("Ningún objeto entra en la cara con esa distribución, ese tamaño y ese perímetro.")
    rot = np.column_stack([u, v, n]) if p["orientacion"] == "cara" else np.identity(3)
    formas = []
    for q, tam in piezas:
        m = np.identity(4)
        m[:3, :3] = rot
        m[:3, 3] = q
        formas.append(geo.transformar(_objeto(objeto, tam, sobre_la_cara, personalizado), m))
    return geo.compuesto(formas)
