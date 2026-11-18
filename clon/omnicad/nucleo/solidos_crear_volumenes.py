"""Sólidos › Crear: volumenes."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import (
    _caras_de, _engrosar_lamina, _lista, _perpendicular, _proyectar_caja, _unir, _unit, _validar, cara_de_plano,
)
from .solidos_crear_nervios import _diagonal

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BOPAlgo_MakerVolume, BRepBuilderAPI_Sewing, BRepOffsetAPI_MakeOffsetShape, BRepOffset_Skin,
        GeomAbs_Intersection, List_TopoDS_Shape,
    )


# ================================================================ 12. engrosar
def engrosar(caras_o_cascaron, espesor, *, direccion="un_lado"):
    """Engrosar (Thicken) de Fusion [GUID-471827A2…]: sólido a partir de caras o una cáscara. "un_lado":
    espesor positivo hacia la normal de las caras, negativo hacia atrás; "simetrica": mitad a cada lado."""
    caras = _caras_de(caras_o_cascaron)
    if not caras:
        raise geo.ErrorGeometria("Elegí al menos una cara para engrosar.")
    if abs(espesor) < 1e-9:
        raise geo.ErrorGeometria("El espesor no puede ser cero.")
    if len(caras) == 1:
        lamina = caras[0]
    else:
        cosido = BRepBuilderAPI_Sewing(1e-6)
        for c in caras:
            cosido.Add(c)
        cosido.Perform()
        lamina = cosido.SewedShape()
    if direccion == "simetrica":
        from .superficies import _PUNTA_DE_CONO, _punta_de_cono
        if _punta_de_cono(lamina):              # B-493: el desfase de la mitad también cerraba el programa
            raise geo.ErrorGeometria("No se pudo engrosar: " + _PUNTA_DE_CONO)
        mo = BRepOffsetAPI_MakeOffsetShape()
        mo.PerformByJoin(lamina, -espesor / 2, 1e-6, BRepOffset_Skin, False, False, GeomAbs_Intersection)
        if not mo.IsDone():
            raise geo.ErrorGeometria("⚠ No se pudo engrosar de forma simétrica.")
        lamina = mo.Shape()
    elif direccion != "un_lado":
        raise geo.ErrorGeometria(f"Dirección de engrosado desconocida: {direccion}")
    return _validar(_engrosar_lamina(lamina, espesor), "Engrosar")


# ================================================================ 13. relleno de contorno
def relleno_contorno_celdas(herramientas, *, tamano_plano=1e3):
    """Celdas del Relleno de contorno (Boundary Fill) [GUID-575E005F…]: todos los volúmenes cerrados que
    forman las herramientas (cuerpos, caras/superficies o geo.Plano). Lista de dicts {solido, centroide,
    volumen} ordenada por centroide, para que el índice de cada celda sea estable."""
    args = List_TopoDS_Shape()
    for h in _lista(herramientas):
        args.Append(cara_de_plano(h, tamano_plano) if isinstance(h, geo.Plano) else h)
    mv = BOPAlgo_MakerVolume()
    mv.SetArguments(args)
    mv.SetIntersect(True)
    mv.Perform()
    if mv.HasErrors():
        raise geo.ErrorGeometria("⚠ No se pudieron calcular celdas del relleno.")
    celdas = [{"solido": s, "centroide": tuple(round(c, 6) for c in geo.centro_masa(s)), "volumen": geo.volumen(s)}
              for s in geo.solidos(mv.Shape())]
    return sorted(celdas, key=lambda c: c["centroide"])


def relleno_contorno(herramientas, indices, **opciones):
    """Sólido formado por las celdas elegidas (índices de `relleno_contorno_celdas`)."""
    celdas = relleno_contorno_celdas(herramientas, **opciones)
    if not celdas:
        raise geo.ErrorGeometria("Las herramientas no encierran ningún volumen.")
    try:
        elegidas = [celdas[i]["solido"] for i in indices]
    except IndexError:
        raise geo.ErrorGeometria("Índice de celda fuera de rango.") from None
    return _validar(_unir(elegidas), "Relleno de contorno")


# ================================================================ 14. sólido envolvente
def _circulo_minimo(puntos):
    """Círculo mínimo que contiene puntos 2D (Welzl iterativo, orden aleatorio con semilla fija)."""
    pts = np.unique(np.round(np.asarray(puntos, float), 9), axis=0)
    pts = pts[np.random.default_rng(0).permutation(len(pts))]

    def circuncentro(a, b, c):
        d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
        if abs(d) < 1e-12:       # alineados: el diámetro es el par más lejano
            par = max(((a, b), (a, c), (b, c)), key=lambda q: np.linalg.norm(q[0] - q[1]))
            return (par[0] + par[1]) / 2
        ux = ((a @ a) * (b[1] - c[1]) + (b @ b) * (c[1] - a[1]) + (c @ c) * (a[1] - b[1])) / d
        uy = ((a @ a) * (c[0] - b[0]) + (b @ b) * (a[0] - c[0]) + (c @ c) * (b[0] - a[0])) / d
        return np.array([ux, uy])

    c, r, eps = pts[0], 0.0, 1e-9
    for i in range(len(pts)):
        if np.linalg.norm(pts[i] - c) <= r + eps:
            continue
        c, r = pts[i], 0.0
        for j in range(i):
            if np.linalg.norm(pts[j] - c) <= r + eps:
                continue
            c = (pts[i] + pts[j]) / 2
            r = float(np.linalg.norm(pts[i] - c))
            for k in range(j):
                if np.linalg.norm(pts[k] - c) > r + eps:
                    c = circuncentro(pts[i], pts[j], pts[k])
                    r = float(np.linalg.norm(pts[i] - c))
    return c, r


def marco_ortonormal(z=None, x=None, y=None):
    """Marco derecho 3x3 (columnas X, Y, Z) con dos de sus ejes: Z y X, Z e Y, o X e Y. El segundo se
    ortogonaliza respecto del primero (el primero manda, como los pares de Fusion)."""
    dados = [(n, v) for n, v in (("z", z), ("x", x), ("y", y)) if v is not None]
    if len(dados) != 2:
        raise geo.ErrorGeometria("La orientación necesita exactamente dos ejes.")
    (n1, v1), (n2, v2) = dados
    a = _unit(v1, f"eje {n1.upper()}")
    b = np.asarray(v2, float)
    b = b - a * (b @ a)
    if np.linalg.norm(b) < 1e-9 * max(1.0, np.linalg.norm(v2)):
        raise geo.ErrorGeometria("⚠ Los dos ejes son paralelos: elegí otros.")
    b = b / np.linalg.norm(b)
    c = np.cross(a, b)
    ejes = {n1: a, n2: b}
    # (z, x) → y = z × x ; (z, y) → x = y × z ; (x, y) → z = x × y   (derecha)
    if "z" in ejes and "x" in ejes:
        ejes["y"] = c
    elif "z" in ejes and "y" in ejes:
        ejes["x"] = -c
    else:
        ejes["z"] = c
    return np.column_stack([ejes["x"], ejes["y"], ejes["z"]])


def _marco_automatico(comp):
    """Marco de la caja orientada que mejor se ajusta (Bnd_OBB del kernel)."""
    from OCP.Bnd import Bnd_OBB
    from OCP.BRepBndLib import BRepBndLib
    obb = Bnd_OBB()
    BRepBndLib.AddOBB_s(comp, obb, True, True, False)
    if obb.IsVoid():
        raise geo.ErrorGeometria("No hay geometría para envolver.")
    ejes = [obb.XDirection(), obb.YDirection(), obb.ZDirection()]
    x, y, z = (np.array([d.X(), d.Y(), d.Z()]) for d in ejes)
    return marco_ortonormal(z=z, x=x)


def _caja_en_marco(comp, marco, margen):
    R = np.asarray(marco, float)
    de_marco = np.identity(4)
    de_marco[:3, :3] = R
    a_marco = np.identity(4)
    a_marco[:3, :3] = R.T
    bb = geo.caja_envolvente(geo.transformar(comp, a_marco))
    (x0, y0, z0), (x1, y1, z1) = bb
    caja = geo.caja(x1 - x0 + 2 * margen, y1 - y0 + 2 * margen, z1 - z0 + 2 * margen,
                    (x0 - margen, y0 - margen, z0 - margen))
    return geo.transformar(caja, de_marco)


def _cilindro_en_eje(pts, z, margen, limites=None):
    """(radio, base, alto) del cilindro mínimo de eje `z` que contiene los puntos `pts`."""
    u = _perpendicular(z)
    v = np.cross(z, u)
    centro2d, radio = _circulo_minimo(np.column_stack([pts @ u, pts @ v]))
    lo, hi = limites if limites is not None else (float((pts @ z).min()), float((pts @ z).max()))
    base = centro2d[0] * u + centro2d[1] * v + z * (lo - margen)
    return radio + margen, base, hi - lo + 2 * margen


def solido_envolvente(formas, *, tipo="caja", margen=0.0, eje="z", marco=None, espesor_tubo=None):
    """Sólido envolvente (Bounding Solid) [SLD-CREATE-BOUNDING-SOLID]: "caja" (exacta), "cilindro", "tubo"
    (cilindro hueco: pared `espesor_tubo`, por defecto la décima parte del radio) o "esfera" (la mínima de la
    caja envolvente: centro en su centro, radio hasta la esquina más lejana) que contienen a la forma.
    Orientación: sin `marco`, los ejes del modelo (el cilindro, alrededor de `eje`: "x", "y", "z" o vector);
    con `marco`, una matriz 3x3 (columnas X, Y, Z, ver `marco_ortonormal`; el cilindro va sobre su Z) o
    "automatica" (la menor: caja orientada del kernel; el cilindro, sobre el eje de la caja que lo achica más).
    `margen` agranda en todas las direcciones."""
    comp = geo.compuesto(_lista(formas))
    bb = geo.caja_envolvente(comp)
    if bb is None:
        raise geo.ErrorGeometria("No hay geometría para envolver.")
    if tipo not in ("caja", "cilindro", "tubo", "esfera"):
        raise geo.ErrorGeometria(f"Tipo de sólido envolvente desconocido: {tipo}")
    if isinstance(marco, str) and marco != "automatica":
        raise geo.ErrorGeometria(f"Orientación desconocida: {marco}")
    if tipo == "esfera":                    # la mínima que envuelve la caja envolvente: centro en el centro, radio a la esquina
        centro = (np.asarray(bb[0], float) + np.asarray(bb[1], float)) / 2
        return geo.esfera(float(np.linalg.norm(np.asarray(bb[1], float) - centro)) + margen, tuple(centro))
    if tipo == "caja":
        if marco is None:
            (x0, y0, z0), (x1, y1, z1) = bb
            return geo.caja(x1 - x0 + 2 * margen, y1 - y0 + 2 * margen, z1 - z0 + 2 * margen,
                            (x0 - margen, y0 - margen, z0 - margen))
        return _caja_en_marco(comp, _marco_automatico(comp) if isinstance(marco, str) else marco, margen)
    verts, _ = geo.teselar(comp, deflexion=max(1e-3, 1e-4 * _diagonal(comp)), angular=0.1)
    pts = np.asarray(verts, float)
    if marco is None:
        ejes = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
        if isinstance(eje, str) and eje not in ejes:
            raise geo.ErrorGeometria(f"Eje desconocido: {eje}")
        z = _unit(ejes[eje] if isinstance(eje, str) else eje, "eje del cilindro")
        limites = _proyectar_caja(bb, (0.0, 0.0, 0.0), z) if isinstance(eje, str) else None
        radio, base, alto = _cilindro_en_eje(pts, z, margen, limites)
    elif isinstance(marco, str):
        R0 = _marco_automatico(comp)
        candidatos = [_cilindro_en_eje(pts, R0[:, i], margen) + (R0[:, i],) for i in range(3)]
        radio, base, alto, z = min(candidatos, key=lambda c: c[0] ** 2 * c[2])
    else:
        z = _unit(np.asarray(marco, float)[:, 2], "eje Z de la orientación")
        radio, base, alto = _cilindro_en_eje(pts, z, margen)
    exterior = geo.cilindro(radio, alto, base=tuple(base), eje=tuple(z))
    if tipo == "cilindro":
        return exterior
    pared = radio / 10 if espesor_tubo is None else float(espesor_tubo)
    if not 0 < pared < radio:
        raise geo.ErrorGeometria(f"⚠ La pared del tubo va de 0 a {radio:g} mm.")
    hueco = geo.cilindro(radio - pared, alto + 2.0, base=tuple(base - z), eje=tuple(z))
    return geo.booleano(exterior, hueco, "cortar")


def _es_material(celda, material):
    """¿La celda de `volumen_fluido` está dentro del material? (más de la mitad de su volumen se solapa)"""
    v = geo.volumen(celda)
    comun = geo.booleano(celda, material, "intersecar")
    return not geo.esta_vacia(comun) and geo.volumen(comun) > 0.5 * v


def volumen_fluido(solidos, tapas=(), *, tipo="interno", forma_externa="caja", margen=10.0, separar_caras=False):
    """Volumen de fluido (Fluid Volume) [SLD-FLUID-VOLUME]: el sólido que ocupa el interior ("interno") o el
    exterior ("externo") de un diseño, para análisis de flujo. `tapas` son superficies que cubren las aberturas
    (sin ellas el interior no queda cerrado). El interno copia las caras del modelo: cada celda cerrada que no es
    material. El externo es una caja, un cilindro (eje Z) o una semiesfera (mitad superior) que rodea el modelo
    `margen` mm, menos el modelo (y su interior tapado). `separar_caras` (Split Result) deja una cara por
    superficie del modelo; si no, las tangentes o del mismo dominio se funden."""
    if tipo not in ("interno", "externo"):
        raise geo.ErrorGeometria(f"Tipo de volumen de fluido desconocido: {tipo}")
    solidos, tapas = _lista(solidos), _lista(tapas)
    if not solidos:
        raise geo.ErrorGeometria("Elegí los cuerpos del diseño.")
    material = geo.unir_todos(solidos) if len(solidos) > 1 else solidos[0]
    args = List_TopoDS_Shape()
    for forma in (*solidos, *tapas):
        for cara in geo.caras(forma):
            args.Append(cara)
    mv = BOPAlgo_MakerVolume()
    mv.SetArguments(args)
    mv.SetIntersect(True)
    mv.Perform()
    if mv.HasErrors():
        raise geo.ErrorGeometria("⚠ No se pudo calcular el volumen de fluido.")
    celdas = geo.solidos(mv.Shape())
    libres = [c for c in celdas if not _es_material(c, material)]
    if tipo == "interno":
        if not libres:
            raise geo.ErrorGeometria("Sin volumen interior: tapá las aberturas.")
        resultado = _unir(libres)
    else:
        bb = geo.caja_envolvente(geo.compuesto([*solidos, *tapas]))
        (x0, y0, z0), (x1, y1, z1) = bb
        if forma_externa == "caja":
            fuera = geo.caja(x1 - x0 + 2 * margen, y1 - y0 + 2 * margen, z1 - z0 + 2 * margen,
                             (x0 - margen, y0 - margen, z0 - margen))
        elif forma_externa == "cilindro":
            radio = math.hypot(x1 - x0, y1 - y0) / 2 + margen
            fuera = geo.cilindro(radio, z1 - z0 + 2 * margen, base=((x0 + x1) / 2, (y0 + y1) / 2, z0 - margen))
        elif forma_externa == "semiesfera":
            c = ((x0 + x1) / 2, (y0 + y1) / 2, z0)
            radio = max(math.dist(c, (x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)) + margen
            fuera = geo.booleano(geo.esfera(radio, c), geo.caja(4 * radio, 4 * radio, 2 * radio,
                                                                (c[0] - 2 * radio, c[1] - 2 * radio, z0 - 2 * radio)),
                                 "cortar")
        else:
            raise geo.ErrorGeometria(f"Forma exterior desconocida: {forma_externa}")
        resultado = geo.booleano(fuera, _unir(celdas) if celdas else material, "cortar")
    if not separar_caras:
        resultado = geo.unificar_caras(resultado)
    return _validar(resultado, "Volumen de fluido")


_registrar_tema(globals())
