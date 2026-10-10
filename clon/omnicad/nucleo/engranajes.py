# -*- coding: utf-8 -*-
"""
Engranajes, ruedas de cadena y ejes escalonados en el núcleo (funciones puras: números → formas OCC o dicts).

Equivalencias: Fusion 360 no tiene un comando nativo de engranajes (lo resuelve con el complemento «Spur Gear» de
Utilidades › Complementos); en FreeCAD son PartDesign › Involute Gear, Sprocket y Shaft Design Wizard. Acá se
replican esas FUNCIONES escritas desde cero: nada de código de FreeCAD (LGPL) ni de Autodesk.

Fuentes (matemática estándar, no código):
  - Perfil de referencia ISO 53: ángulo de presión α = 20°, altura de cabeza ha = 1·m, de pie hf = 1,25·m
    (holgura de fondo c = 0,25·m).
  - Geometría de la evolvente, desplazamiento de perfil x, engranajes helicoidales (módulo y ángulo de presión
    transversales), distancia entre centros de trabajo y grado de recubrimiento: ISO 21771 (antes DIN 3960).
  - Rueda de cadena de rodillos: forma del hueco de ISO 606 (radio de asiento ri, ángulo de asiento α, radio del
    flanco re y diámetros primitivo, de fondo y exterior), con la forma MEDIA entre la de hueco mínimo y máximo.

Posición canónica de las formas: eje +Z, la cara de abajo en z = 0 (sube hasta el ancho), el centro en el origen y
el primer diente apuntando a +X (la cremallera: línea primitiva sobre el eje X, dientes hacia +Y). `colocar` lleva
esa posición a un plano con su centro.

Simplificaciones (dichas, no escondidas): bajo el círculo base el flanco sigue en línea radial hasta el fondo (no
se modela el socavado ni el empalme de pie del tallado por generación); el fondo es un arco del círculo de pie con
esquinas vivas. `socavado` y `datos_par` avisan cuándo el diente real quedaría socavado o habría interferencia.
Unidades: mm y grados.
"""
import math

import numpy as np
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon,
                                BRepBuilderAPI_MakeWire)
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.GC import GC_MakeArcOfCircle
from OCP.GeomAPI import GeomAPI_Interpolate
from OCP.OCP.collections import HArray1_gp_Pnt
from OCP.gp import gp_Pnt, gp_Vec

from . import geometria as geo

ADENDO = 1.0                 # altura de cabeza del perfil de referencia ISO 53 (× módulo)
HOLGURA = 0.25               # holgura de fondo del perfil de referencia ISO 53 (× módulo)
MUESTRAS_EVOLVENTE = 24      # puntos por flanco que interpola la B-spline de la evolvente
DIENTES_MAXIMOS = 1000

# Cadenas de rodillos de ISO 606 (serie europea B y serie americana A = ANSI 40…80): paso p, diámetro del rodillo d1
# y ancho interior mínimo b1 (mm). Valores de la tabla de la norma tomados de memoria: conviene verificarlos contra
# la edición vigente antes de fabricar. Para otra cadena: «personalizada» con paso y rodillo propios.
CADENAS = {
    "05B": (8.0, 5.0, 3.0), "06B": (9.525, 6.35, 5.72), "08B": (12.7, 8.51, 7.75), "10B": (15.875, 10.16, 9.65),
    "12B": (19.05, 12.07, 11.68), "16B": (25.4, 15.88, 17.02),
    "08A": (12.7, 7.92, 7.85), "10A": (15.875, 10.16, 9.40), "12A": (19.05, 11.91, 12.57),
    "16A": (25.4, 15.88, 15.75),
}
REMATES = {"ninguno": "Ninguno", "chaflan": "Chaflán", "empalme": "Empalme"}


# ---------------------------------------------------------------- utilidades
def _inv(a):
    """Función evolvente: inv(α) = tan α − α (α en radianes)."""
    return math.tan(a) - a


def _inv_inversa(y):
    """α tal que inv(α) = y (Newton; y ≥ 0)."""
    if y < 0:
        raise geo.ErrorGeometria("El ángulo de presión de trabajo da negativo: revisá los desplazamientos de perfil.")
    a = (3 * y) ** (1 / 3) if y > 0 else 0.0           # inv(α) ≈ α³/3 para α chico
    for _ in range(60):
        f = _inv(a) - y
        d = math.tan(a) ** 2
        if d < 1e-300:
            break
        paso = f / d
        a -= paso
        if abs(paso) < 1e-15:
            break
    return a


def _finito(valor, que):
    try:
        v = float(valor)
    except (TypeError, ValueError):
        raise geo.ErrorGeometria(f"{que} tiene que ser un número; llegó {valor!r}.") from None
    if not math.isfinite(v):
        raise geo.ErrorGeometria(f"{que} tiene que ser un número finito; llegó {valor!r}.")
    return v


def _positivo(valor, que):
    v = _finito(valor, que)
    if v <= 0:
        raise geo.ErrorGeometria(f"{que} tiene que ser mayor que cero; llegó {v:g}.")
    return v


def _entero(valor, que, minimo):
    v = _finito(valor, que)
    n = round(v)
    if abs(v - n) > 1e-9:
        raise geo.ErrorGeometria(f"{que} tiene que ser un número entero; llegó {v:g}.")
    if n < minimo or n > DIENTES_MAXIMOS:
        raise geo.ErrorGeometria(f"{que} tiene que estar entre {minimo} y {DIENTES_MAXIMOS}; llegó {n}.")
    return int(n)


def _pnt(x, y, z=0.0):
    return gp_Pnt(float(x), float(y), float(z))


def _polar(r, ang):
    return (r * math.cos(ang), r * math.sin(ang))


def _linea(a, b):
    return BRepBuilderAPI_MakeEdge(_pnt(*a), _pnt(*b)).Edge()


def _arco(a, medio, b):
    return BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(_pnt(*a), _pnt(*medio), _pnt(*b)).Value()).Edge()


def _spline(puntos):
    arr = HArray1_gp_Pnt(1, len(puntos))
    for i, p in enumerate(puntos):
        arr.SetValue(i + 1, _pnt(*p))
    interp = GeomAPI_Interpolate(arr, False, 1e-9)
    interp.Perform()
    if not interp.IsDone():
        raise geo.ErrorGeometria("No se pudo construir la curva evolvente del flanco.")
    return BRepBuilderAPI_MakeEdge(interp.Curve()).Edge()


def _cara(aristas):
    w = BRepBuilderAPI_MakeWire()
    for a in aristas:
        w.Add(a)
        if not w.IsDone():
            raise geo.ErrorGeometria("El contorno del perfil no cierra (aristas que no se tocan).")
    cara = BRepBuilderAPI_MakeFace(w.Wire(), True)
    if not cara.IsDone():
        raise geo.ErrorGeometria("No se pudo armar la cara del perfil.")
    return cara.Face()


def _extruir(cara, ancho):
    return BRepPrimAPI_MakePrism(cara, gp_Vec(0.0, 0.0, float(ancho))).Shape()


def _validar(forma, que):
    if forma is None or geo.esta_vacia(forma) or not geo.es_valida(forma):
        raise geo.ErrorGeometria(f"{que}: el kernel devolvió una forma inválida con estas medidas.")
    return forma


def _con_agujero(forma, diametro, ancho, maximo, que):
    """Corta el agujero central (Ø `diametro`, 0 = sin agujero) a lo largo de todo el ancho."""
    d = _finito(diametro, "El diámetro del agujero")
    if d < 0:
        raise geo.ErrorGeometria(f"El diámetro del agujero no puede ser negativo; llegó {d:g} mm.")
    if d == 0:
        return forma
    if d >= maximo:
        raise geo.ErrorGeometria(f"El agujero de Ø{d:g} mm no entra en {que}: tiene que ser menor que "
                                 f"Ø{maximo:.4g} mm.")
    return geo.booleano(forma, geo.cilindro(d / 2, ancho + 2.0, base=(0, 0, -1.0)), "cortar")


def colocar(forma, origen, normal, eje_u):
    """Lleva una forma de la posición canónica (eje +Z, primer diente hacia +X) a `origen` con su eje en `normal`
    y su +X en `eje_u` (proyectado sobre el plano). Equivale a ubicar el engranaje en un plano y un punto."""
    n = np.asarray(normal, float)
    n = n / (np.linalg.norm(n) or 1.0)
    u = np.asarray(eje_u, float)
    u = u - n * float(u @ n)
    if np.linalg.norm(u) < 1e-9:
        u = np.cross(n, (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0))
    u = u / np.linalg.norm(u)
    m = np.identity(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = u, np.cross(n, u), n, np.asarray(origen, float)
    return geo.transformar(forma, m)


# ---------------------------------------------------------------- medidas de un engranaje de evolvente
def medidas_engranaje(modulo, dientes, angulo_presion=20.0, helice=0.0, desplazamiento=0.0, holgura=HOLGURA,
                      juego=0.0):
    """Medidas de un engranaje cilíndrico de evolvente (ISO 21771) sin modelarlo: el «Spur Gear» de Fusion y el
    «Involute Gear» de FreeCAD las calculan igual. `modulo` es el módulo NORMAL (en el recto, el módulo), `helice`
    el ángulo de hélice β en grados (0 = recto), `desplazamiento` el coeficiente x, `holgura` el coeficiente c* de
    holgura de fondo y `juego` el juego circunferencial del PAR en el primitivo (cada rueda adelgaza la mitad).

    Devuelve un dict en mm y grados: módulo y ángulo de presión transversales, diámetros primitivo, base, exterior y
    de fondo, paso circular, paso base, espesor del diente en el primitivo, semiángulos del diente en el primitivo,
    el base y el exterior (radianes, para el perfil) y la torsión por mm de ancho."""
    m = _positivo(modulo, "El módulo")
    z = _entero(dientes, "La cantidad de dientes", 3)
    alfa = _finito(angulo_presion, "El ángulo de presión")
    if not 5.0 <= alfa <= 35.0:
        raise geo.ErrorGeometria(f"El ángulo de presión tiene que estar entre 5° y 35°; llegó {alfa:g}°.")
    beta = _finito(helice, "El ángulo de hélice")
    if abs(beta) > 45.0:
        raise geo.ErrorGeometria(f"El ángulo de hélice tiene que estar entre −45° y 45°; llegó {beta:g}°.")
    x = _finito(desplazamiento, "El desplazamiento de perfil")
    if abs(x) > 2.0:
        raise geo.ErrorGeometria(f"El desplazamiento de perfil tiene que estar entre −2 y 2; llegó {x:g}.")
    c = _finito(holgura, "La holgura de fondo")
    if not 0.0 <= c <= 1.0:
        raise geo.ErrorGeometria(f"La holgura de fondo tiene que estar entre 0 y 1 (× módulo); llegó {c:g}.")
    j = _finito(juego, "El juego")
    if j < 0:
        raise geo.ErrorGeometria(f"El juego no puede ser negativo; llegó {j:g} mm.")
    an, b = math.radians(alfa), math.radians(beta)
    mt = m / math.cos(b)
    at = math.atan(math.tan(an) / math.cos(b))
    r = z * mt / 2
    rb = r * math.cos(at)
    ra = r + m * (ADENDO + x)
    rf = r - m * (ADENDO + c - x)
    if rf <= 0:
        raise geo.ErrorGeometria(f"Con {z} dientes el círculo de fondo queda en el centro: usá más dientes o un "
                                 "desplazamiento de perfil positivo.")
    espesor = mt * (math.pi / 2 + 2 * x * math.tan(an)) - j / 2
    if espesor <= 0:
        raise geo.ErrorGeometria(f"El juego de {j:g} mm es más grande que el diente ({2 * (espesor + j / 2):.4g} mm "
                                 "de espesor en el primitivo).")
    tp = espesor / (2 * r)                         # semiángulo del diente en el primitivo
    tb = tp + _inv(at)                             # … en el círculo base
    ta = tb - _inv(math.acos(min(1.0, rb / ra))) if ra > rb else tb
    return {"modulo": m, "dientes": z, "angulo_presion": alfa, "helice": beta, "desplazamiento": x, "holgura": c,
            "juego": j, "modulo_transversal": mt, "angulo_presion_transversal": math.degrees(at),
            "diametro_primitivo": 2 * r, "diametro_base": 2 * rb, "diametro_exterior": 2 * ra,
            "diametro_fondo": 2 * rf, "paso": math.pi * mt, "paso_base": math.pi * mt * math.cos(at),
            "espesor_primitivo": espesor, "semiangulo_primitivo": tp, "semiangulo_base": tb,
            "semiangulo_exterior": ta, "espesor_exterior": 2 * ta * ra,
            "torsion_por_mm": math.degrees(math.tan(b) / r)}


def dientes_minimos_teorico(angulo_presion=20.0, helice=0.0):
    """Límite teórico de socavado al tallar por generación con el perfil de referencia ISO 53 y x = 0:
    z_g = 2·ha*·cos β / sen² αt (17,1 con 20°; 31,9 con 14,5°)."""
    an, b = math.radians(angulo_presion), math.radians(helice)
    at = math.atan(math.tan(an) / math.cos(b))
    return 2 * ADENDO * math.cos(b) / math.sin(at) ** 2


def dientes_minimos(angulo_presion=20.0, helice=0.0):
    """Menor cantidad ENTERA de dientes sin ningún socavado con x = 0: el límite teórico redondeado hacia arriba
    (18 con 20°, 32 con 14,5°). Las tablas suelen decir 17 para 20° porque con 17 el socavado es despreciable
    (x mínimo 0,006); acá se usa el criterio estricto, el mismo de `socavado`."""
    return math.ceil(dientes_minimos_teorico(angulo_presion, helice) - 1e-9)


def socavado(dientes, angulo_presion=20.0, desplazamiento=0.0, helice=0.0):
    """Verificación de socavado (ISO 21771): {"socavado": bool, "desplazamiento_minimo": x_mín,
    "dientes_minimos": z_mín}. Con x < x_mín = ha* − z·sen² αt / (2·cos β) el diente tallado queda socavado."""
    an, b = math.radians(angulo_presion), math.radians(helice)
    at = math.atan(math.tan(an) / math.cos(b))
    x_min = ADENDO - dientes * math.sin(at) ** 2 / (2 * math.cos(b))
    return {"socavado": desplazamiento < x_min - 1e-9, "desplazamiento_minimo": x_min,
            "dientes_minimos": dientes_minimos(angulo_presion, helice)}


def distancia_entre_centros(modulo, dientes1, dientes2, angulo_presion=20.0, desplazamiento1=0.0,
                            desplazamiento2=0.0, helice=0.0):
    """Distancia entre centros de trabajo de un par exterior (ISO 21771): sin desplazamientos (o si suman 0) es
    m·(z1 + z2) / (2·cos β); si no, sale del ángulo de presión de trabajo inv αw = inv αt + 2·tan αn·(x1 + x2) /
    (z1 + z2)."""
    return datos_par(modulo, dientes1, dientes2, angulo_presion, desplazamiento1, desplazamiento2,
                     helice)["distancia_centros"]


def datos_par(modulo, dientes1, dientes2, angulo_presion=20.0, desplazamiento1=0.0, desplazamiento2=0.0,
              helice=0.0, holgura=HOLGURA):
    """Datos de un par exterior de engranajes (ISO 21771): distancia entre centros, ángulo de presión de trabajo,
    relación, grado de recubrimiento εα, holguras de fondo reales y verificación de interferencia (la cabeza de una
    rueda que entra bajo el círculo base de la otra) y de socavado de cada una."""
    g1 = medidas_engranaje(modulo, dientes1, angulo_presion, helice, desplazamiento1, holgura)
    g2 = medidas_engranaje(modulo, dientes2, angulo_presion, helice, desplazamiento2, holgura)
    z1, z2 = g1["dientes"], g2["dientes"]
    an = math.radians(angulo_presion)
    at = math.radians(g1["angulo_presion_transversal"])
    suma_x = g1["desplazamiento"] + g2["desplazamiento"]
    if abs(suma_x) < 1e-12:
        aw = at
    else:
        aw = _inv_inversa(_inv(at) + 2 * math.tan(an) * suma_x / (z1 + z2))
    r1, r2 = g1["diametro_primitivo"] / 2, g2["diametro_primitivo"] / 2
    a = (r1 + r2) * math.cos(at) / math.cos(aw)
    rb1, rb2 = g1["diametro_base"] / 2, g2["diametro_base"] / 2
    ra1, ra2 = g1["diametro_exterior"] / 2, g2["diametro_exterior"] / 2
    rf1, rf2 = g1["diametro_fondo"] / 2, g2["diametro_fondo"] / 2
    linea = a * math.sin(aw)                                     # tramo T1–T2 de la línea de engrane
    e1, e2 = math.sqrt(max(ra1 ** 2 - rb1 ** 2, 0)), math.sqrt(max(ra2 ** 2 - rb2 ** 2, 0))
    recubrimiento = (e1 + e2 - linea) / g1["paso_base"]
    return {"distancia_centros": a, "angulo_presion_trabajo": math.degrees(aw), "relacion": z2 / z1,
            "recubrimiento": recubrimiento, "holgura_fondo1": a - ra2 - rf1, "holgura_fondo2": a - ra1 - rf2,
            "interferencia1": e2 > linea + 1e-9,          # la cabeza de 2 entra bajo el círculo base de 1
            "interferencia2": e1 > linea + 1e-9,
            "socavado1": socavado(z1, angulo_presion, g1["desplazamiento"], helice)["socavado"],
            "socavado2": socavado(z2, angulo_presion, g2["desplazamiento"], helice)["socavado"],
            "engranaje1": g1, "engranaje2": g2}


# ---------------------------------------------------------------- perfil y sólido del engranaje
def _evolvente(rb, r_desde, r_hasta, n=MUESTRAS_EVOLVENTE):
    """[(ρ, φ)] de la evolvente del círculo base rb entre los radios dados: φ = inv(αρ), cos αρ = rb/ρ."""
    t0 = math.sqrt(max((r_desde / rb) ** 2 - 1.0, 0.0))
    t1 = math.sqrt(max((r_hasta / rb) ** 2 - 1.0, 0.0))
    salida = []
    for i in range(n):      # paso parejo en el ángulo de rodadura t: desvío < 1e-5 mm con 24 puntos (z = 20 y 40)
        t = t0 + (t1 - t0) * i / (n - 1)
        salida.append((rb * math.sqrt(1.0 + t * t), t - math.atan(t)))
    salida[0] = (r_desde, salida[0][1])
    salida[-1] = (r_hasta, t1 - math.atan(t1))
    return salida


def perfil_engranaje(modulo, dientes, angulo_presion=20.0, helice=0.0, desplazamiento=0.0, holgura=HOLGURA,
                     juego=0.0, giro=0.0):
    """Cara plana (XY, centro en el origen) del perfil transversal de un engranaje de evolvente: flancos de evolvente
    (B-spline por puntos exactos), arco de cabeza, línea radial bajo el círculo base y arco de fondo. `giro` (grados)
    gira el perfil alrededor de Z; con 0 el primer diente apunta a +X. Es el boceto que dibuja el complemento
    «Spur Gear» de Fusion."""
    g = medidas_engranaje(modulo, dientes, angulo_presion, helice, desplazamiento, holgura, juego)
    z, rb = g["dientes"], g["diametro_base"] / 2
    ra, rf = g["diametro_exterior"] / 2, g["diametro_fondo"] / 2
    tb, ta = g["semiangulo_base"], g["semiangulo_exterior"]
    if ta * ra < 1e-3:
        raise geo.ErrorGeometria(f"Los dientes quedan en punta antes del diámetro exterior (Ø{2 * ra:.4g} mm): bajá "
                                 "el desplazamiento de perfil, el juego o el ángulo de presión.")
    radial = rf < rb
    tr = tb if radial else tb - _inv(math.acos(rb / rf))       # semiángulo del diente en el fondo
    paso = 2 * math.pi / z
    if paso - 2 * tr < 1e-6:
        raise geo.ErrorGeometria(f"Con {z} dientes y estos desplazamientos los dientes se tocan en el fondo: bajá el "
                                 "desplazamiento de perfil o usá más dientes.")
    if ra <= max(rf, rb if radial else rf):
        raise geo.ErrorGeometria("El diámetro exterior quedó por debajo del de fondo: revisá el desplazamiento.")
    evo = _evolvente(rb, rb if radial else rf, ra)
    giro = math.radians(_finito(giro, "El giro"))
    aristas = []
    for k in range(z):
        c = giro + k * paso
        izq = [_polar(rho, c - tb + phi) for rho, phi in evo]
        der = [_polar(rho, c + tb - phi) for rho, phi in reversed(evo)]
        if radial:
            aristas.append(_linea(_polar(rf, c - tb), izq[0]))
        aristas.append(_spline(izq))
        aristas.append(_arco(izq[-1], _polar(ra, c), der[0]))
        aristas.append(_spline(der))
        fin = _polar(rf, c + tr)
        if radial:
            aristas.append(_linea(der[-1], fin))
        else:
            fin = der[-1]
        aristas.append(_arco(fin, _polar(rf, c + paso / 2), _polar(rf, c + paso - tr)))
    return _cara(aristas)


def engranaje(modulo, dientes, *, angulo_presion=20.0, ancho=10.0, helice=0.0, desplazamiento=0.0,
              holgura=HOLGURA, juego=0.0, agujero=0.0, giro=0.0):
    """Engranaje cilíndrico de evolvente, recto (helice = 0) o helicoidal: CREAR › Engranaje (complemento «Spur
    Gear» de Fusion; PartDesign › Involute Gear de FreeCAD). Sólido con el eje en +Z, de z = 0 a z = ancho.

    El helicoidal se barre con torsión a lo largo del eje: el perfil gira ancho·tan β / r (r = radio primitivo
    transversal); β > 0 es hélice a derechas. `agujero`: diámetro del agujero central (0 = macizo)."""
    b = _positivo(ancho, "El ancho")
    g = medidas_engranaje(modulo, dientes, angulo_presion, helice, desplazamiento, holgura, juego)
    cara = perfil_engranaje(modulo, dientes, angulo_presion, helice, desplazamiento, holgura, juego, giro)
    torsion = g["torsion_por_mm"] * b
    if abs(torsion) < 1e-9:
        forma = _extruir(cara, b)
    else:
        from .solidos_crear import barrer
        forma = barrer([cara], _eje_z(b), torsion=torsion)
    forma = _con_agujero(forma, agujero, b, g["diametro_fondo"] - g["modulo"], "el engranaje")
    return _validar(forma, "Engranaje")


def _eje_z(largo):
    return BRepBuilderAPI_MakeEdge(_pnt(0, 0, 0), _pnt(0, 0, largo)).Edge()


def fase_segundo(dientes1, dientes2, direccion=0.0, giro1=0.0):
    """Giro (grados) del segundo engranaje para que engrane con el primero: con el centro del segundo en la
    `direccion` (grados) vista desde el primero, el primero girado `giro1` y los dos con el primer diente hacia +X,
    el segundo tiene que mostrar un HUECO hacia el primero cuando este le muestra un diente («medio diente»)."""
    z1, z2 = int(dientes1), int(dientes2)
    rel = z1 / z2
    return direccion + 180.0 + 180.0 / z2 + (direccion - giro1) * rel


def par_engranajes(modulo, dientes1, dientes2, *, angulo_presion=20.0, ancho=10.0, helice=0.0,
                   desplazamiento1=0.0, desplazamiento2=0.0, holgura=HOLGURA, juego=0.0, agujero1=0.0,
                   agujero2=0.0, direccion=0.0, giro=0.0):
    """Par de engranajes exteriores que engranan: el primero en el origen (girado `giro` grados) y el segundo a la
    distancia entre centros de trabajo en la `direccion` dada (grados desde +X), girado para que sus huecos reciban
    los dientes del primero («medio diente»). Con hélice, el segundo es de la mano contraria. `juego` es el juego del
    par (cada rueda adelgaza la mitad). Devuelve {"engranaje1", "engranaje2", "centro2", "giro2", **datos_par}."""
    datos = datos_par(modulo, dientes1, dientes2, angulo_presion, desplazamiento1, desplazamiento2, helice, holgura)
    if datos["holgura_fondo1"] < -1e-9 or datos["holgura_fondo2"] < -1e-9:
        raise geo.ErrorGeometria("Con estos desplazamientos la cabeza de un engranaje toca el fondo del otro: bajá la "
                                 "suma de los desplazamientos o acortá la cabeza.")
    z1, z2 = datos["engranaje1"]["dientes"], datos["engranaje2"]["dientes"]
    direccion = _finito(direccion, "La dirección del segundo engranaje")
    giro = _finito(giro, "El giro")
    giro2 = fase_segundo(z1, z2, direccion, giro)
    f1 = engranaje(modulo, z1, angulo_presion=angulo_presion, ancho=ancho, helice=helice,
                   desplazamiento=desplazamiento1, holgura=holgura, juego=juego, agujero=agujero1, giro=giro)
    f2 = engranaje(modulo, z2, angulo_presion=angulo_presion, ancho=ancho, helice=-_finito(helice, "La hélice"),
                   desplazamiento=desplazamiento2, holgura=holgura, juego=juego, agujero=agujero2, giro=giro2)
    a, d = datos["distancia_centros"], math.radians(direccion)
    centro2 = (a * math.cos(d), a * math.sin(d), 0.0)
    f2 = geo.trasladar(f2, centro2)
    return dict(datos, engranaje1=f1, engranaje2=f2, centro2=centro2, giro2=giro2)


# ---------------------------------------------------------------- cremallera
def cremallera(modulo, dientes, *, angulo_presion=20.0, ancho=10.0, alto=None, holgura=HOLGURA, juego=0.0):
    """Cremallera recta con el perfil de referencia ISO 53 (el «Rack» del taller Gear de FreeCAD): paso π·m, flancos
    rectos inclinados el ángulo de presión, cabeza m y pie (1 + c)·m. Sólido en XY extruido en +Z: la línea
    primitiva sobre el eje X de x = 0 a x = dientes·π·m (los extremos caen en el medio de un hueco), los dientes
    hacia +Y y la base en y = −alto (`alto`: de la base a la línea primitiva; por defecto el pie más un módulo, 2,25·m)."""
    m = _positivo(modulo, "El módulo")
    n = _entero(dientes, "La cantidad de dientes", 1)
    alfa = _finito(angulo_presion, "El ángulo de presión")
    if not 5.0 <= alfa <= 35.0:
        raise geo.ErrorGeometria(f"El ángulo de presión tiene que estar entre 5° y 35°; llegó {alfa:g}°.")
    c = _finito(holgura, "La holgura de fondo")
    if not 0.0 <= c <= 1.0:
        raise geo.ErrorGeometria(f"La holgura de fondo tiene que estar entre 0 y 1 (× módulo); llegó {c:g}.")
    j = _finito(juego, "El juego")
    if j < 0:
        raise geo.ErrorGeometria(f"El juego no puede ser negativo; llegó {j:g} mm.")
    b = _positivo(ancho, "El ancho")
    ha, hf = ADENDO * m, (ADENDO + c) * m
    alto = (hf + m) if alto is None else _positivo(alto, "El alto")
    if alto <= hf + 1e-6:
        raise geo.ErrorGeometria(f"El alto de la cremallera (de la base a la línea primitiva) tiene que ser mayor que "
                                 f"el pie del diente ({hf:.4g} mm); llegó {alto:g} mm.")
    p = math.pi * m
    t = math.tan(math.radians(alfa))
    s2 = p / 4 - j / 4                          # medio espesor en la línea primitiva
    w_cabeza, w_pie = s2 - ha * t, s2 + hf * t
    if w_cabeza < 1e-4:
        raise geo.ErrorGeometria("Los dientes de la cremallera quedan en punta: bajá el ángulo de presión o el juego.")
    if p - 2 * w_pie < 1e-4:
        raise geo.ErrorGeometria("Los dientes de la cremallera se tocan en el fondo: bajá la holgura o el ángulo de "
                                 "presión.")
    largo = n * p
    pol = BRepBuilderAPI_MakePolygon()
    for x, y in [(0.0, -alto), (largo, -alto), (largo, -hf)]:
        pol.Add(_pnt(x, y))
    for k in reversed(range(n)):
        xc = (k + 0.5) * p
        for x, y in ((xc + w_pie, -hf), (xc + w_cabeza, ha), (xc - w_cabeza, ha), (xc - w_pie, -hf)):
            pol.Add(_pnt(x, y))
    pol.Add(_pnt(0.0, -hf))
    pol.Close()
    cara = BRepBuilderAPI_MakeFace(pol.Wire(), True).Face()
    return _validar(_extruir(cara, b), "Cremallera")


# ---------------------------------------------------------------- rueda de cadena (ISO 606)
def datos_rueda_cadena(paso, rodillo, dientes):
    """Medidas de ISO 606 de la rueda para cadena de rodillos de paso p y rodillo d1: diámetro primitivo
    d = p / sen(180°/z), de fondo df = d − d1, exterior mínimo y máximo, y los límites del hueco (radio de asiento
    ri, ángulo de asiento α y radio del flanco re de las formas de hueco mínimo y máximo)."""
    p = _positivo(paso, "El paso de la cadena")
    d1 = _positivo(rodillo, "El diámetro del rodillo")
    z = _entero(dientes, "La cantidad de dientes", 6)
    if d1 >= 0.9 * p:
        raise geo.ErrorGeometria(f"El rodillo (Ø{d1:g} mm) no entra en el paso de {p:g} mm.")
    d = p / math.sin(math.pi / z)
    return {"paso": p, "rodillo": d1, "dientes": z, "diametro_primitivo": d, "diametro_fondo": d - d1,
            "diametro_exterior_min": d + p * (1 - 1.6 / z) - d1, "diametro_exterior_max": d + 1.25 * p - d1,
            "radio_asiento_min": 0.505 * d1, "radio_asiento_max": 0.505 * d1 + 0.069 * d1 ** (1 / 3),
            "angulo_asiento_min": 120.0 - 90.0 / z, "angulo_asiento_max": 140.0 - 90.0 / z,
            "radio_flanco_min": 0.12 * d1 * (z + 2), "radio_flanco_max": 0.008 * d1 * (z * z + 180)}


def ancho_diente_cadena(ancho_interior, paso):
    """Ancho del diente de ISO 606 para cadena simple: 0,93·b1 con paso ≤ 12,7 mm y 0,95·b1 con paso mayor."""
    return (0.93 if paso <= 12.7 + 1e-9 else 0.95) * ancho_interior


def _circulo_por_recta(centro, radio, angulo):
    """Radio (positivo, el mayor) donde la recta por el origen en `angulo` corta el círculo dado; None si no."""
    u = np.array([math.cos(angulo), math.sin(angulo)])
    c = np.asarray(centro, float)
    b = float(c @ u)
    disc = b * b - (float(c @ c) - radio * radio)
    if disc < 0:
        return None
    return b + math.sqrt(disc)


def _circulo_por_circulo(c1, r1, r2, cerca):
    """Intersección del círculo (c1, r1) con el círculo (origen, r2) más cercana al punto `cerca`."""
    c1 = np.asarray(c1, float)
    d = float(np.linalg.norm(c1))
    if d < 1e-12 or d > r1 + r2 or d < abs(r1 - r2):
        return None
    a = (r2 * r2 - r1 * r1 + d * d) / (2 * d)
    h = math.sqrt(max(r2 * r2 - a * a, 0.0))
    e = c1 / d
    base = e * a
    pts = [base + h * np.array([-e[1], e[0]]), base - h * np.array([-e[1], e[0]])]
    return min(pts, key=lambda q: float(np.linalg.norm(q - np.asarray(cerca, float))))


def rueda_cadena(paso, rodillo, dientes, *, ancho=7.0, agujero=0.0):
    """Rueda dentada para cadena de rodillos con la forma de diente de ISO 606 (PartDesign › Sprocket de FreeCAD):
    en cada hueco, un arco de asiento de radio ri centrado en el rodillo que abarca el ángulo de asiento α, y dos
    flancos de radio re tangentes a él; arriba, el arco del diámetro exterior. Se usa la forma MEDIA entre la de
    hueco mínimo y la de hueco máximo, y el diámetro exterior medio de la norma (más bajo si el diente quedara en
    punta). Sólido con el eje en +Z, de z = 0 a z = ancho."""
    datos = datos_rueda_cadena(paso, rodillo, dientes)
    b = _positivo(ancho, "El ancho")
    z, p = datos["dientes"], datos["paso"]
    rp = datos["diametro_primitivo"] / 2
    ri = (datos["radio_asiento_min"] + datos["radio_asiento_max"]) / 2
    alfa = math.radians((datos["angulo_asiento_min"] + datos["angulo_asiento_max"]) / 2)
    re = (datos["radio_flanco_min"] + datos["radio_flanco_max"]) / 2
    paso_ang = 2 * math.pi / z
    C = np.array([rp, 0.0])                                       # rodillo del hueco 0, sobre +X
    T = C + ri * np.array([math.cos(math.pi - alfa / 2), math.sin(math.pi - alfa / 2)])   # fin del asiento
    F = T + re * (T - C) / ri                                     # centro del flanco: del otro lado del diente
    r_punta = _circulo_por_recta(F, re, paso_ang / 2)
    ra = (datos["diametro_exterior_min"] + datos["diametro_exterior_max"]) / 4
    if r_punta is not None:
        ra = min(ra, r_punta - 0.02 * p)
    if ra <= float(np.linalg.norm(T)) + 1e-3:
        raise geo.ErrorGeometria("Con estas medidas el diente de la rueda de cadena no tiene flanco: revisá el paso y "
                                 "el rodillo.")
    Q = _circulo_por_circulo(F, re, ra, T)
    if Q is None or math.atan2(Q[1], Q[0]) >= paso_ang / 2 - 1e-6:
        raise geo.ErrorGeometria("El diente de la rueda de cadena queda en punta: revisá el paso y el rodillo.")

    def mitad(a, b_, centro, radio):
        """Punto medio del arco (centro, radio) entre a y b (el arco corto)."""
        ang_a = math.atan2(a[1] - centro[1], a[0] - centro[0])
        ang_b = math.atan2(b_[1] - centro[1], b_[0] - centro[0])
        dif = (ang_b - ang_a + math.pi) % (2 * math.pi) - math.pi
        m = ang_a + dif / 2
        return (centro[0] + radio * math.cos(m), centro[1] + radio * math.sin(m))

    def rot(q, ang):
        c, s = math.cos(ang), math.sin(ang)
        return (c * q[0] - s * q[1], s * q[0] + c * q[1])

    T_ab = (T[0], -T[1])                                   # extremo de abajo del asiento (simétrico)
    Q_t, T_t = (float(Q[0]), float(Q[1])), (float(T[0]), float(T[1]))
    fondo = (rp - ri, 0.0)
    flanco_medio = mitad(T_t, Q_t, F, re)
    aristas = []
    for k in range(z):
        g = k * paso_ang
        aristas.append(_arco(rot(T_ab, g), rot(fondo, g), rot(T_t, g)))                 # asiento
        aristas.append(_arco(rot(T_t, g), rot(flanco_medio, g), rot(Q_t, g)))           # flanco que sube
        aristas.append(_arco(rot(Q_t, g), _polar(ra, g + paso_ang / 2), rot((Q_t[0], -Q_t[1]), g + paso_ang)))
        aristas.append(_arco(rot((Q_t[0], -Q_t[1]), g + paso_ang),                     # flanco que baja
                             rot((flanco_medio[0], -flanco_medio[1]), g + paso_ang), rot(T_ab, g + paso_ang)))
    forma = _extruir(_cara(aristas), b)
    forma = _con_agujero(forma, agujero, b, 2 * (rp - ri) - 0.2 * p, "la rueda de cadena")
    return _validar(forma, "Rueda de cadena")


# ---------------------------------------------------------------- eje escalonado (asistente de ejes)
def _tramos(tramos):
    """Valida la tabla de tramos y la normaliza a [(diámetro, largo, (remate, medida) inicio, (…) fin)]."""
    if not isinstance(tramos, (list, tuple)) or not tramos:
        raise geo.ErrorGeometria("El eje necesita al menos un tramo (diámetro y largo).")
    salida = []
    for i, t in enumerate(tramos, 1):
        if not isinstance(t, dict):
            raise geo.ErrorGeometria(f"El tramo {i} tiene que ser un dict con diámetro y largo.")
        d = _positivo(t.get("diametro"), f"El diámetro del tramo {i}")
        largo = _positivo(t.get("largo"), f"El largo del tramo {i}")
        remates = []
        for lado in ("inicio", "fin"):
            tipo = t.get(lado) or "ninguno"
            if tipo not in REMATES:
                raise geo.ErrorGeometria(f"El remate «{lado}» del tramo {i} tiene que ser {', '.join(REMATES)}; "
                                         f"llegó {tipo!r}.")
            medida = 0.0
            if tipo != "ninguno":
                medida = _positivo(t.get(f"medida_{lado}"), f"La medida del {REMATES[tipo].lower()} ({lado}) del "
                                                            f"tramo {i}")
            remates.append((tipo, medida))
        salida.append((d, largo, remates[0], remates[1]))
    return salida


def eje_escalonado(tramos):
    """Asistente de ejes (PartDesign › Shaft Design Wizard de FreeCAD): un eje de revolución armado con una tabla
    de tramos, cada uno con su diámetro, su largo y, en cada extremo, un chaflán (45°) o un empalme opcional sobre
    la esquina de ese tramo (convexa en el escalón que baja o en la punta, cóncava en el que sube).

    `tramos`: [{"diametro", "largo", "inicio": "ninguno"|"chaflan"|"empalme", "medida_inicio", "fin", "medida_fin"}].
    Sólido con el eje en +Z, del z = 0 al largo total."""
    datos = _tramos(tramos)
    # Contorno (radio, z) del medio perfil, con cada esquina anotada con su remate.
    puntos = [((0.0, 0.0), None)]
    z = 0.0
    for i, (d, largo, ini, fin) in enumerate(datos):
        r = d / 2
        puntos.append(((r, z), (ini, i + 1, "inicio")))
        z += largo
        puntos.append(((r, z), (fin, i + 1, "fin")))
    puntos.append(((0.0, z), None))
    # Dos esquinas iguales (tramos del mismo diámetro): no hay escalón donde rematar.
    limpios = []
    for q, rem in puntos:
        if limpios and math.dist(limpios[-1][0], q) < 1e-9:
            for r_ in (limpios[-1][1], rem):
                if r_ is not None and r_[0][0] != "ninguno":
                    raise geo.ErrorGeometria(f"El tramo {r_[1]} tiene un {REMATES[r_[0][0]].lower()} en el {r_[2]}, "
                                             "pero ahí no hay escalón: el tramo vecino tiene el mismo diámetro.")
            limpios[-1] = (q, None)
            continue
        limpios.append((q, rem))
    # Se quitan los puntos alineados (tramos del mismo diámetro dejan un vértice en el medio de una recta).
    n = len(limpios)
    vertices = []
    for k in range(n):
        a, b, c = limpios[k - 1][0], limpios[k][0], limpios[(k + 1) % n][0]
        cruz = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cruz) < 1e-12:
            continue
        vertices.append(limpios[k])
    n = len(vertices)
    retiro = []                                   # cuánto se come cada remate de las dos rectas de su esquina
    for (_q, rem) in vertices:
        retiro.append(rem[0][1] if rem is not None and rem[0][0] != "ninguno" else 0.0)
    for k in range(n):
        a, b = vertices[k][0], vertices[(k + 1) % n][0]
        largo = math.dist(a, b)
        if retiro[k] + retiro[(k + 1) % n] > largo + 1e-9:
            quien = [vertices[i][1] for i in (k, (k + 1) % n) if vertices[i][1] is not None and retiro[i] > 0]
            nombres = " y ".join(f"{REMATES[r[0][0]].lower()} de {r[0][1]:g} mm ({r[2]} del tramo {r[1]})"
                                 for r in quien)
            raise geo.ErrorGeometria(f"El {nombres} no entra: el lado donde se apoya mide {largo:.4g} mm.")

    def hacia(desde, hasta, d):
        v = np.subtract(hasta, desde)
        return tuple(np.asarray(desde, float) + v / np.linalg.norm(v) * d)

    def p3(q):
        return (q[0], 0.0, q[1])                   # (radio, z) → punto 3D en el plano XZ

    aristas, inicio, previo = [], None, None
    for k in range(n):
        q, rem = vertices[k]
        s = retiro[k]
        if s > 0:
            entra, sale = hacia(q, vertices[k - 1][0], s), hacia(q, vertices[(k + 1) % n][0], s)
        else:
            entra = sale = q
        if previo is not None and math.dist(previo, entra) > 1e-9:
            aristas.append(_linea(p3(previo), p3(entra)))
        if inicio is None:
            inicio = entra
        if s > 0 and rem[0][0] == "chaflan":
            aristas.append(_linea(p3(entra), p3(sale)))
        elif s > 0:
            centro = np.add(entra, sale) - np.asarray(q, float)
            medio = centro + (np.asarray(q, float) - centro) / np.linalg.norm(np.subtract(q, centro)) * s
            aristas.append(_arco(p3(entra), p3(tuple(medio)), p3(sale)))
        previo = sale
    if math.dist(previo, inicio) > 1e-9:
        aristas.append(_linea(p3(previo), p3(inicio)))
    cara = _cara(aristas)
    return _validar(geo.revolver([cara], (0, 0, 0), (0, 0, 1), 360.0), "Eje")


def volumen_eje(tramos):
    """Volumen exacto del eje escalonado (Pappus): cilindros menos los chaflanes y empalmes de las esquinas
    convexas, más los de las cóncavas. Sirve para verificar `eje_escalonado`."""
    datos = _tramos(tramos)
    vol = sum(math.pi * (d / 2) ** 2 * largo for d, largo, _i, _f in datos)
    for i, (d, _largo, ini, fin) in enumerate(datos):
        r = d / 2
        for (tipo, s), vecino in ((ini, datos[i - 1][0] / 2 if i > 0 else 0.0),
                                  (fin, datos[i + 1][0] / 2 if i + 1 < len(datos) else 0.0)):
            if tipo == "ninguno":
                continue
            convexa = vecino < r
            if tipo == "chaflan":
                area, desde_esquina = s * s / 2, s / 3
            else:
                area = s * s * (1 - math.pi / 4)
                desde_esquina = s * (10 - 3 * math.pi) / (12 - 3 * math.pi)
            radio_c = r - desde_esquina if convexa else r + desde_esquina
            vol += (-1 if convexa else 1) * 2 * math.pi * radio_c * area
    return vol
