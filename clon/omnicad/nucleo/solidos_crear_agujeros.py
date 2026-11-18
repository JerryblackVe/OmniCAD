"""Sólidos › Crear: agujeros."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import functools
import re
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import (
    _MARGEN, _caja_proyectada, _cara, _gdir, _perpendicular, _pnt, _poligono, _rayo, _unit, _validar, _xyz,
)
from .solidos_crear_roscas import (
    FAMILIAS_ROSCA, _armar_surco, _perfil_clase, _surco_rosca, datos_rosca, diametro_taladro_rosca,
)

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BRepAdaptor_Curve, BRepBuilderAPI_Copy, BRepPrimAPI_MakeRevol, GeomAbs_Line, TopAbs_FACE, TopLoc_Location,
        TopoDS, gp_Ax1, gp_Trsf, gp_Vec,
    )


# ================================================================ 7. agujero
# Agujeros de paso (Fusion: tipo «Con holgura») para tornillos métricos, ISO 273: diámetro del agujero (mm) en
# las series fina, media y gruesa. ISO 273 es la fuente de cada fila.
PASO_LIBRE_ISO273 = {
    "M1.6": (1.7, 1.8, 2.0), "M2": (2.2, 2.4, 2.6), "M2.5": (2.7, 2.9, 3.1), "M3": (3.2, 3.4, 3.6),
    "M3.5": (3.7, 3.9, 4.2), "M4": (4.3, 4.5, 4.8), "M5": (5.3, 5.5, 5.8), "M6": (6.4, 6.6, 7.0),
    "M8": (8.4, 9.0, 10.0), "M10": (10.5, 11.0, 12.0), "M12": (13.0, 13.5, 14.5), "M14": (15.0, 15.5, 16.5),
    "M16": (17.0, 17.5, 18.5), "M18": (19.0, 20.0, 21.0), "M20": (21.0, 22.0, 24.0), "M22": (23.0, 24.0, 26.0),
    "M24": (25.0, 26.0, 28.0), "M27": (28.0, 30.0, 32.0), "M30": (31.0, 33.0, 35.0), "M33": (34.0, 36.0, 38.0),
    "M36": (37.0, 39.0, 42.0), "M39": (40.0, 42.0, 45.0), "M42": (43.0, 45.0, 48.0), "M45": (46.0, 48.0, 52.0),
    "M48": (50.0, 52.0, 56.0), "M52": (54.0, 56.0, 62.0), "M56": (58.0, 62.0, 66.0), "M60": (62.0, 66.0, 70.0),
    "M64": (66.0, 70.0, 74.0)}
AJUSTES_PASO_LIBRE = ("fino", "normal", "grueso")       # series de ISO 273 (Fusion: cercano, normal, holgado)


def diametro_paso_libre(tamano, ajuste="normal"):
    """Diámetro del agujero con holgura (Clearance de Fusion) para un tornillo métrico según ISO 273: «M8» (o
    «M8x1.25»: el paso no cuenta) con ajuste "fino", "normal" (serie media) o "grueso". Ej.: M8 normal = 9 mm."""
    if ajuste not in AJUSTES_PASO_LIBRE:
        raise geo.ErrorGeometria(f"Ajuste desconocido: {ajuste} (hay {', '.join(AJUSTES_PASO_LIBRE)}).")
    m = re.fullmatch(r"\s*[Mm]\s*(\d+(?:\.\d+)?)(?:\s*[xX×]\s*\d+(?:\.\d+)?)?\s*", str(tamano or ""))
    clave = f"M{float(m.group(1)):g}" if m else None
    if clave not in PASO_LIBRE_ISO273:
        raise geo.ErrorGeometria(f"⚠ ISO 273 no tiene «{tamano}» (va M1.6 a M64).")
    return PASO_LIBRE_ISO273[clave][AJUSTES_PASO_LIBRE.index(ajuste)]


def profundidad_hasta(punto, direccion, objetivo, desfase=0.0):
    """Extensión «Hasta» del agujero de Fusion: distancia desde `punto` según `direccion` hasta `objetivo`, que es
    un geo.Plano (plano de construcción), una cara (si es plana se toma su plano extendido, como «extender caras»
    de Fusion) o un cuerpo (el primer corte del rayo con él). `desfase` se suma (positivo = más hondo)."""
    p, d = np.asarray(punto, float), _unit(direccion, "dirección del agujero")
    plano = objetivo if isinstance(objetivo, geo.Plano) else None
    if plano is None and getattr(objetivo, "ShapeType", None) and objetivo.ShapeType() == TopAbs_FACE:
        plano = geo.plano_de_cara(TopoDS.Face(objetivo))
    if plano is not None:
        den = float(d @ plano.normal)
        if abs(den) < 1e-9:
            raise geo.ErrorGeometria("⚠ El plano «hasta» no corta al agujero.")
        t = float((plano.origen - p) @ plano.normal) / den
    else:
        cortes = [x for x in _rayo(objetivo, p, d) if x > 1e-6]
        if not cortes:
            raise geo.ErrorGeometria("⚠ El agujero no llega a la cara «hasta».")
        t = cortes[0]
    t += float(desfase)
    if t <= 1e-6:
        raise geo.ErrorGeometria("⚠ La cara «hasta» queda detrás del agujero.")
    return t


def punto_por_referencias(cara, aristas, distancias):
    """Posición «Referencias» del agujero de Fusion: el punto de la cara plana `cara` que queda a `distancias[i]`
    (mm) de cada una de las dos aristas rectas `aristas` (proyectadas sobre la cara), hacia el lado de la cara.
    Las aristas no pueden ser paralelas."""
    plano = geo.plano_de_cara(TopoDS.Face(cara))
    if plano is None:
        raise geo.ErrorGeometria("⚠ Referencias: la cara debe ser plana.")
    aristas, distancias = list(aristas), [float(x) for x in distancias]
    if len(aristas) != 2 or len(distancias) != 2:
        raise geo.ErrorGeometria("⚠ Referencias: dos aristas y dos distancias.")
    centro = plano.a_uv(geo.centro_masa(cara, superficie=True))
    filas, lados = [], []
    for arista, dist in zip(aristas, distancias, strict=True):
        curva = BRepAdaptor_Curve(TopoDS.Edge(arista))
        if curva.GetType() != GeomAbs_Line:
            raise geo.ErrorGeometria("⚠ Las referencias del agujero no son rectas.")
        a = np.array(plano.a_uv(_xyz(curva.Value(curva.FirstParameter()))))
        b = np.array(plano.a_uv(_xyz(curva.Value(curva.LastParameter()))))
        if np.linalg.norm(b - a) < 1e-9:
            raise geo.ErrorGeometria("⚠ Una arista de referencia es perpendicular.")
        t = (b - a) / np.linalg.norm(b - a)
        n = np.array([-t[1], t[0]])
        if float((np.asarray(centro) - a) @ n) < 0:          # la normal mira hacia el lado de la cara
            n = -n
        filas.append(n)
        lados.append(dist + float(a @ n))
    m = np.array(filas)
    if abs(np.linalg.det(m)) < 1e-6:
        raise geo.ErrorGeometria("⚠ Las aristas de referencia son paralelas.")
    u, v = np.linalg.solve(m, np.array(lados))
    return plano.a_3d(u, v)


def herramienta_agujero(punto, direccion, *, tipo="simple", diametro=None, profundidad=10.0, punta="angulo",
                        angulo_punta=118.0, diam_abocardado=None, prof_abocardado=None, diam_avellanado=None,
                        angulo_avellanado=90.0, roscado=None, mano="derecha", clase="", holgura=0.0,
                        conicidad=0.0, tabla=True, variante_surco=0):
    """Sólido a restar de un agujero de Fusion (revolución del medio perfil). `variante_surco`: ver `_armar_surco`. `direccion` apunta hacia el
    material; `profundidad` llega hasta el hombro (sin la punta, como en Fusion). `roscado` = designación de
    TABLA_ROSCAS: el agujero se hace al diámetro menor y se le suma el surco helicoidal de la rosca; `clase`
    ("6H", "2B", "auto"…: ver `tolerancias`) lleva el diámetro menor y los flancos al centro de su tolerancia y
    `holgura` (mm, radial) agranda todo para imprimir en 3D. `conicidad` (diámetro por mm de profundidad, p. ej.
    1/16 en las roscas de tubería cónicas) angosta el agujero hacia el fondo (Roscado cónico). `tabla`: ver
    `_perfil_clase`. Con rosca, la herramienta se arma una vez en el origen y se traslada (B-578)."""
    opciones = dict(tipo=tipo, diametro=diametro, profundidad=profundidad, punta=punta, angulo_punta=angulo_punta,
                    diam_abocardado=diam_abocardado, prof_abocardado=prof_abocardado, diam_avellanado=diam_avellanado,
                    angulo_avellanado=angulo_avellanado, roscado=roscado, mano=mano, clase=clase, holgura=holgura,
                    conicidad=conicidad, tabla=tabla, variante_surco=variante_surco)
    if roscado:
        try:    # B-578: unir el surco al agujero tardaba 0,4 s y se repetía en cada cambio de cota de la pieza
            base = _rosca_en_origen(tuple(map(float, _unit(direccion))), tuple(sorted(opciones.items())))
            lugar = gp_Trsf()
            lugar.SetTranslation(gp_Vec(*map(float, punto)))
            return BRepBuilderAPI_Copy(base, False).Shape().Moved(TopLoc_Location(lugar))  # la copia no toca la caché
        except Exception:  # noqa: BLE001 — vía rápida: si falla, el camino de siempre
            pass
    return _herramienta_agujero(punto, direccion, **opciones)


@functools.lru_cache(maxsize=16)
def _rosca_en_origen(direccion, opciones):
    return _herramienta_agujero((0.0, 0.0, 0.0), direccion, **dict(opciones))


def _herramienta_agujero(punto, direccion, *, tipo, diametro, profundidad, punta, angulo_punta, diam_abocardado,
                         prof_abocardado, diam_avellanado, angulo_avellanado, roscado, mano, clase, holgura, conicidad,
                         tabla, variante_surco):
    a = _perfil_agujero(punto, direccion, tipo, diametro, profundidad, punta, angulo_punta, diam_abocardado,
                        prof_abocardado, diam_avellanado, angulo_avellanado, roscado, clase, holgura, conicidad, tabla)
    p, d = a["punto"], a["direccion"]
    e = _perpendicular(d)
    perfil = _cara(_poligono([p + e * rho + d * zz for rho, zz in a["medio"]]))
    herramienta = BRepPrimAPI_MakeRevol(perfil, gp_Ax1(_pnt(p), _gdir(d)), 2 * math.pi).Shape()
    if roscado:
        datos = a["rosca"]
        surco, torno = _armar_surco(lambda extra: _surco_rosca(
            p, d, datos["diametro"], datos["paso"], 0.0, profundidad, True, mano, radio_cara=a["radio"], partes=True,
            extra=extra, **a["perfil"]), variante_surco)
        if torno is not None:                         # la holgura deja sin espesor la cresta: se agranda el agujero
            herramienta = geo.booleano(herramienta, torno, "unir")
        herramienta = geo.booleano(herramienta, surco, "unir")
    return _validar(herramienta, "Agujero")


def exigir_profundidad_agujero(profundidad):
    """Rechaza una profundidad no positiva de Agujero de Fusion; el sentido se elige con Invertir."""
    if profundidad is None or profundidad <= 0:
        raise geo.ErrorGeometria("La profundidad del agujero debe ser positiva.")


def _perfil_agujero(punto, direccion, tipo, diametro, profundidad, punta, angulo_punta, diam_abocardado,
                    prof_abocardado, diam_avellanado, angulo_avellanado, roscado, clase, holgura, conicidad, tabla=True):
    """Valida un agujero y da su medio perfil [(radio, profundidad)…] desde el eje (común a los dos motores)."""
    d = _unit(direccion, "dirección del agujero")
    p = np.asarray(punto, float)
    datos = perfil = None
    if roscado:
        datos = datos_rosca(roscado)
        if datos["conica"]:
            raise geo.ErrorGeometria("⚠ Rosca cónica no se modela: usá cosmético.")
        if datos["solo_exterior"]:
            raise geo.ErrorGeometria(f"⚠ «{FAMILIAS_ROSCA[datos['familia']]['nombre']}»: rosca externa.")
        if conicidad:
            raise geo.ErrorGeometria("⚠ Agujero cónico: sin rosca paralela.")
        perfil = _perfil_clase(datos, clase, True, holgura, tabla)
        diametro = diametro_taladro_rosca(roscado, clase, holgura)
    if diametro is None or diametro <= 0:
        raise geo.ErrorGeometria("El diámetro del agujero debe ser positivo.")
    exigir_profundidad_agujero(profundidad)
    if conicidad < 0 or conicidad * profundidad >= diametro:
        raise geo.ErrorGeometria("⚠ La conicidad cierra el agujero.")
    r = diametro / 2
    radio = lambda z: r - conicidad / 2 * z  # noqa: E731 — radio del agujero a la profundidad z
    medio = [(0.0, 0.0)]
    if tipo == "simple":
        medio.append((r, 0.0))
    elif tipo == "abocardado":
        if not diam_abocardado or diam_abocardado <= diametro or not prof_abocardado or prof_abocardado <= 0:
            raise geo.ErrorGeometria("⚠ Abocardado: diámetro mayor y hondo > 0.")
        if prof_abocardado >= profundidad:
            raise geo.ErrorGeometria("⚠ El abocardado es más hondo que el agujero.")
        medio += [(diam_abocardado / 2, 0.0), (diam_abocardado / 2, prof_abocardado),
                  (radio(prof_abocardado), prof_abocardado)]
    elif tipo == "avellanado":
        if not diam_avellanado or diam_avellanado <= diametro or not 0 < angulo_avellanado < 180:
            raise geo.ErrorGeometria("⚠ Avellanado: diámetro y ángulo 0°–180°.")
        h = (diam_avellanado - diametro) / 2 / math.tan(math.radians(angulo_avellanado) / 2)
        if h >= profundidad:
            raise geo.ErrorGeometria("El avellanado es más profundo que el agujero.")
        medio += [(diam_avellanado / 2, 0.0), (radio(h), h)]
    else:
        raise geo.ErrorGeometria(f"Tipo de agujero desconocido: {tipo}")
    r_fondo = radio(profundidad)
    medio.append((r_fondo, profundidad))
    if punta == "angulo":
        if not 0 < angulo_punta < 180:
            raise geo.ErrorGeometria("⚠ Ángulo de la punta: de 0° a 180°.")
        medio.append((0.0, profundidad + r_fondo / math.tan(math.radians(angulo_punta) / 2)))
    elif punta == "plana":
        medio.append((0.0, profundidad))
    else:
        raise geo.ErrorGeometria(f"Punta de broca desconocida: {punta}")
    return {"punto": p, "direccion": d, "medio": medio, "radio": r, "rosca": datos, "perfil": perfil}


def agujero(cuerpo, punto, direccion, *, profundidad=None, **opciones):
    """Agujero (Hole) de Fusion [GUID-0DFCBD4F…, GUID-3A76B269…]: devuelve la HERRAMIENTA a restar del
    cuerpo. `profundidad=None` = extensión "Todo" (pasante: llega al otro lado del cuerpo, punta plana).
    El resto de las opciones son las de `herramienta_agujero`."""
    d = _unit(direccion, "dirección del agujero")
    if profundidad is None:
        _, hi = _caja_proyectada(cuerpo, punto, d)
        if hi <= 0:
            raise geo.ErrorGeometria("⚠ El cuerpo no está del lado del agujero.")
        profundidad = hi + _MARGEN
        opciones["punta"] = "plana"
    return herramienta_agujero(punto, d, profundidad=profundidad, **opciones)


def agujero_sin_pellizco(antes, despues):
    """True si el corte del agujero NO sumó aristas compartidas por más de dos caras (`antes`: las formas de los cuerpos
    cortados; `despues`: lo que quedó)."""
    contar = lambda formas: sum(geo._aristas_defectuosas(f)[1] for f in formas)  # noqa: E731
    return contar(despues) <= contar(antes)


def exigir_agujero_sin_pellizco(antes, despues):
    """B-165: error si el corte del agujero sumó aristas compartidas por más de dos caras (`antes`: las formas de los
    cuerpos cortados; `despues`: lo que quedó). Un agujero tangente a una pared deja el material con espesor cero,
    algo que no se puede fabricar; la booleana suelta (Combinar) lo deja pasar con un aviso (B-126)."""
    if not agujero_sin_pellizco(antes, despues):
        raise geo.ErrorGeometria("⚠ El agujero toca una pared: espesor cero.")   # regla 14: un renglón


def exigir_agujeros_separados(herramientas, tol=1e-4):
    """B-506: dos agujeros del MISMO paso que se tocan justo en el borde (tangentes, sin pisarse) dejan un cuerpo que se
    cruza consigo mismo y BRepCheck no lo ve; `exigir_agujero_sin_pellizco` tampoco, porque se cortan juntos. Solo se
    miden los pares cuyas cajas se tocan (una grilla de 200 agujeros separados no mide ninguno)."""
    from itertools import combinations

    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    cajas = [geo.caja_envolvente(h) for h in herramientas]
    for i, j in combinations(range(len(herramientas)), 2):
        (a0, a1), (b0, b1) = cajas[i], cajas[j]
        if any(a0[k] > b1[k] + tol or b0[k] > a1[k] + tol for k in range(3)):
            continue
        a, b = herramientas[i], herramientas[j]
        d = BRepExtrema_DistShapeShape(a, b)
        if d.IsDone() and d.Value() <= tol and geo.volumen(BRepAlgoAPI_Common(a, b).Shape()) <= tol:
            raise geo.ErrorGeometria("Dos agujeros se tocan justo: espesor cero.")


_registrar_tema(globals())
