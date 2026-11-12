# -*- coding: utf-8 -*-
"""
ENSAMBLAR de Fusion [Fusion-Assemble]: componentes, uniones (las 7 de Fusion), uniones «como está»,
orígenes de unión, grupos rígidos, vínculos de movimiento e insertar otro diseño como componente.

Modelo: cada cuerpo pertenece a un componente (`Cuerpo.componente`, "" = la raíz). Una unión calcula un
marco (origen + ejes) sobre la geometría del componente 1 y otro sobre la del componente 2 y MUEVE los
cuerpos del componente 1 para que los marcos coincidan (caras enfrentadas, como en Fusion; dos ejes, como
un perno en un agujero, en el mismo sentido; «Voltear» invierte eso), con ángulo y desfases. Después aplica el movimiento de la unión (giro,
deslizamiento…) según sus valores, que se cambian con «Accionar uniones». Cada unión deja en
`estado.uniones` lo necesario para accionarla o animarla sin recalcular.
"""
import math
import re

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import referencias as refs
from . import entidades as ent
from .operaciones import (ANGULO, ErrorOperacion, Operacion, ParametroMalFormado, _deps_objetivo, _migrador,
                          _resolver, _version_de, registrar_operacion)

TIPOS_UNION = {"rigida": "Rígida", "revolucion": "Revolución", "deslizante": "Deslizante", "cilindrica": "Cilíndrica",
               "pasador_ranura": "Pasador-ranura", "planar": "Planar", "bola": "Bola"}
# grados de libertad: (giros, desplazamientos) por tipo
MOVIMIENTOS = {"rigida": ([], []), "revolucion": (["giro"], []), "deslizante": ([], ["desliz"]),
               "cilindrica": (["giro"], ["desliz"]), "pasador_ranura": (["giro"], ["desliz"]),
               "planar": (["giro"], ["desliz", "desliz2"]), "bola": (["giro", "giro2", "giro3"], [])}
EJES = {"X": 0, "Y": 1, "Z": 2}
PUNTOS_CLAVE = ("centro", "inicio", "fin")      # punto de ajuste («Snap») del origen de unión, ver `_marco`
# Modo del origen de unión (Joint reference › Mode): una cara/arista/punto, el medio de dos caras o el cruce de dos aristas.
MODOS_POSICION = {"simple": "Simple", "entre_caras": "Entre dos caras", "interseccion": "Intersección de dos aristas"}
CLAVES_MOVIMIENTO = ("giro", "giro2", "giro3", "desliz", "desliz2")


def exigir_numero(texto):
    """«nan» e «inf» (con signo o en mayúsculas) no son números: el mensaje lo dice, en vez de «Nombre desconocido»."""
    if re.fullmatch(r"\s*[+-]?(nan|inf|infinity)\s*", str(texto or ""), re.IGNORECASE):
        raise ErrorOperacion(f"No es un número: «{str(texto).strip()}». Escribí un valor finito (por ejemplo 30 o 45 deg).")


def es_fijo(estado, comp):
    """El componente no se mueve con una unión: fijo (Ground) o anclado (Pin)."""
    datos = estado.componentes.get(comp, {})
    return bool(datos.get("fijo") or datos.get("anclado"))


def principal_de(tipo):
    """El movimiento que recortan los límites de siempre (`minimo`, `maximo`): el giro si la unión gira."""
    return "giro" if MOVIMIENTOS[tipo][0] else "desliz"


def limites_expr(p, clave):
    """(mínimo, máximo, reposo, invertir) en texto de un movimiento de la unión `p`. Los del movimiento principal
    siguen en `minimo` y `maximo` (las recetas viejas); el resto y el reposo y «invertir» van en `limites_dof`."""
    extra = (p.get("limites_dof") or {}).get(clave) or {}
    if clave == principal_de(p["tipo"]):
        return p.get("minimo"), p.get("maximo"), extra.get("reposo"), bool(extra.get("invertir"))
    return extra.get("minimo"), extra.get("maximo"), extra.get("reposo"), bool(extra.get("invertir"))


# ---------------------------------------------------------------- marcos (orígenes de unión)
def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ErrorOperacion("Dirección nula en el origen de la unión.")
    return v / n


def marco_desde(origen, z, x=None):
    """Matriz 4x4 (columnas: X, Y, Z, origen) de un marco ortonormal derecho."""
    z = _unit(z)
    if x is None or abs(float(np.dot(_unit(x), z))) > 0.999:
        x = np.cross((0, 0, 1.0), z) if abs(z[2]) < 0.9 else np.cross(z, (0, 1.0, 0))
        x = np.cross(z, np.cross(x, z))
    x = _unit(np.asarray(x, float) - z * float(np.dot(x, z)))
    y = np.cross(z, x)
    m = np.identity(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, np.asarray(origen, float)
    return m


def marco_de(e, punto_clave="centro", version=1):
    """Origen de unión «simple» sobre una entidad resuelta (como el «Snap» del diálogo Unión).
    `version` es la «version_marco» de la unión: 1 = el marco de las recetas viejas (se conserva para que
    abran igual), 2 = el de ahora (ver `_marco`)."""
    return _marco(e, punto_clave, version)[0]


def _eje_canonico(d):
    """El eje con su componente mayor positiva (empates: Z, luego Y, luego X): no depende de si la cara es
    un agujero o un saliente ni de cómo se construyó."""
    d = _unit(d)
    i = max(range(3), key=lambda k: (round(abs(float(d[k])), 9), k))
    return d if d[i] > 0 else -d


def _x_del_mundo(z):
    """El eje del mundo menos alineado con `z` (empates: X, luego Y, luego Z): la X del marco de un eje."""
    i = min(range(3), key=lambda k: (round(abs(float(z[k])), 9), k))
    return np.identity(3)[i]


def _marco_de_eje(origen, d):
    z = _eje_canonico(d)
    return marco_desde(origen, z, _x_del_mundo(z))


def _marco(e, punto_clave="centro", version=1):
    """(marco, es_eje). Con versión 2: el origen de una cara plana es el centro de su contorno exterior (no
    el centroide de área, que se corre con los agujeros) y los marcos de eje (cara cilíndrica o cónica,
    arista circular) son deterministas: eje canónico, X del mundo y origen en el eje, en el centro de la
    arista circular o, en una cara, en el medio (o el inicio o el fin) de su largo, como el Snap de Fusion."""
    nuevo = (version or 1) >= 2
    if e.tipo == "plano" or (e.tipo == "boceto" and e.plano is not None):
        # Un «Origen de unión» puesto sobre un cilindro o una arista circular sigue siendo un marco de eje.
        eje = e.tipo == "plano" and bool(getattr(e.plano, "eje_de_union", False))
        return marco_desde(e.plano.origen, e.plano.normal, e.plano.u), eje
    if e.tipo == "cara":
        f = refs.firma_cara(e.forma)
        if e.plano is not None:
            if nuevo:
                return marco_desde(_centro_contorno_exterior(e.forma), e.plano.normal, e.plano.u), False
            centro = np.array(f["centro"])
            circ = _centro_circular(e.forma)
            return marco_desde(circ if circ is not None else centro, e.plano.normal, e.plano.u), False
        if "eje" in f:
            p, d = ent.como_eje(e)
            if nuevo:
                return _marco_de_eje(_punto_del_eje(e.forma, p, _eje_canonico(d), punto_clave), d), True
            c = np.array(f["centro"])
            pie = p + d * float((c - p) @ d)
            return marco_desde(pie, d), False
        return marco_desde(f["centro"], (0, 0, 1)), False
    if e.tipo in ("arista", "curva_boceto") and e.forma is not None:
        f = refs.firma_arista(e.forma)
        if f["geom"] == "circulo":
            from ..nucleo.consultas import eje_circulo
            eje = eje_circulo(e.forma)
            if nuevo:
                return _marco_de_eje(f["centro"], eje), True
            return marco_desde(f["centro"], eje), False
        return _marco_resto(e, f, punto_clave), False
    if nuevo and e.tipo == "eje":
        # Eje de construcción: marco de eje como el del cilindro del que suele salir.
        p, d = e.eje
        return _marco_de_eje(p, d), True
    return _marco_resto(e, None, punto_clave), False


def _punto_del_eje(cara, p, z, punto_clave):
    """Punto del eje (p, z) en el medio, el inicio o el fin del largo de la cara cilíndrica o cónica: los
    centros de sus aristas circulares extremas. El largo sale de los límites de la cara en el parámetro
    axial de la superficie."""
    from ..nucleo.consultas import punto_del_eje
    return punto_del_eje(cara, p, z, punto_clave)


def _marco_resto(e, f, punto_clave):
    """Aristas no circulares, ejes y puntos (igual en las dos versiones del marco)."""
    if f is not None:
        a, b = (np.array(p) for p in f["extremos"])
        if e.tipo == "arista" and f["geom"] == "linea" and e.eje is not None:
            a, d = e.eje      # B-294: el sentido que ya resolvió B-283; sin él, conserva el de antes.
            b = a + d * f["largo"]
        p = {"inicio": a, "fin": b}.get(punto_clave, np.array(f["medio"]))
        if f["geom"] == "linea":
            return marco_desde(p, b - a)
        return marco_desde(p, e.plano.normal if e.plano is not None else (0, 0, 1))
    if e.tipo == "eje":
        p, d = e.eje
        return marco_desde(p, d)
    if e.punto is not None:
        return marco_desde(e.punto, e.plano.normal if e.plano is not None else (0, 0, 1))
    raise ErrorOperacion("No se puede poner un origen de unión en esa selección.")


def _centro_circular(cara):
    """Centro del contorno circular de una cara plana (agujero o disco), si lo tiene."""
    circulos = [refs.firma_arista(a) for a in refs.subformas(cara, "arista")]
    circulos = [c for c in circulos if c["geom"] == "circulo"]
    if len(circulos) == 1 or (circulos and all(np.allclose(c["centro"], circulos[0]["centro"]) for c in circulos)):
        return np.array(circulos[0]["centro"])
    return None


def _centro_contorno_exterior(cara):
    """Centro del contorno exterior de una cara plana, sin contar sus agujeros: el centro del círculo si el
    contorno es circular (disco, arandela) o radial partido (semicírculos concéntricos + radios: el agujero
    pasante partido en dos tapas) y, si no, el centroide de la región que encierra."""
    from ..nucleo.consultas import cara_del_contorno, contorno_exterior
    exterior = contorno_exterior(cara)
    if exterior is None:
        return np.array(refs.firma_cara(cara)["centro"])
    aristas = [refs.firma_arista(a) for a in refs.subformas(exterior, "arista")]
    circulos = [a for a in aristas if a["geom"] == "circulo"]
    if circulos and all(np.allclose(c["centro"], circulos[0]["centro"], atol=1e-6) for c in circulos):
        centro = np.array(circulos[0]["centro"], float)
        if len(circulos) == len(aristas):
            return centro
        radios = [c["radio"] for c in circulos]
        rmin, rmax = min(radios), max(radios)

        def _radial(h):  # línea con los extremos entre rmin y rmax y la dirección apuntando al centro
            a, b = (np.array(p, float) for p in h["extremos"])
            d = b - a
            medio = (a + b) / 2 - centro
            n_m = np.linalg.norm(medio)
            return (rmin - 1e-6 <= np.linalg.norm(a - centro) <= rmax + 1e-6 and
                    rmin - 1e-6 <= np.linalg.norm(b - centro) <= rmax + 1e-6 and
                    (n_m < 1e-9 or float(np.linalg.norm(np.cross(d, medio))) < 1e-6 * np.linalg.norm(d) * n_m))

        if all(_radial(a) for a in aristas if a["geom"] != "circulo"):
            return centro
    return np.array(refs.firma_cara(cara_del_contorno(exterior, cara))["centro"])


def _marco_entre_caras(a, b, version):
    """Origen centrado entre dos caras planas paralelas: sobre el centro de la primera, a medio camino de la
    segunda, con la normal de la primera (Between Two Faces)."""
    if a.plano is None or b.plano is None:
        raise ErrorOperacion("«Entre dos caras» necesita dos caras planas (o planos).")
    n = _unit(a.plano.normal)
    if abs(float(np.dot(n, _unit(b.plano.normal)))) < 1 - 1e-6:
        raise ErrorOperacion("Las dos caras tienen que ser paralelas para centrar el origen entre ellas.")
    ca, cb = _marco(a, "centro", version)[0][:3, 3], _marco(b, "centro", version)[0][:3, 3]
    return marco_desde(ca + n * float((cb - ca) @ n) / 2, n, a.plano.u)


def _marco_interseccion(a, b):
    """Origen en el cruce, prolongado, de dos aristas rectas no paralelas (Two Edge Intersection): X siguiendo la
    primera arista y Z perpendicular al plano de las dos."""
    p1, d1 = _recta_de(a)
    p2, d2 = _recta_de(b)
    n = np.cross(d1, d2)
    if np.linalg.norm(n) < 1e-9 * np.linalg.norm(d1) * np.linalg.norm(d2):
        raise ErrorOperacion("Las dos aristas son paralelas: no se cruzan.")
    s, t = np.linalg.solve(np.c_[d1, -d2, n], p2 - p1)[:2]
    q1, q2 = p1 + d1 * s, p2 + d2 * t
    if np.linalg.norm(q1 - q2) > 1e-6 * max(1.0, np.linalg.norm(q1)):
        raise ErrorOperacion("Las dos aristas no se cruzan (no están en el mismo plano): no hay intersección.")
    return marco_desde((q1 + q2) / 2, n, d1)


def _marco_modo(estado, origen, origen_b, modo, clave, version):
    """(marco, es_eje, entidad) del origen de unión en el modo pedido: «simple» es `_marco`; «entre_caras» e
    «interseccion» usan además la segunda selección `origen_b`."""
    e = _resolver(origen, estado)
    if modo in (None, "", "simple"):
        marco, eje = _marco(e, clave, version)
        if eje and e.tipo != "plano":
            # B-177: el eje canónico se elige en el sistema del componente, no del mundo: si un padre lo gira, no salta.
            m = _matriz_de(estado, _componente_de(estado, e))
            local = np.linalg.inv(m) @ marco
            marco = m @ _marco_de_eje(local[:3, 3], local[:3, 2])
        return marco, eje, e
    if modo not in MODOS_POSICION:
        raise ErrorOperacion(f"Modo de posición desconocido: «{modo}». Modos: {', '.join(MODOS_POSICION)}.")
    if not origen_b:
        raise ErrorOperacion(f"El modo «{MODOS_POSICION[modo]}» necesita la segunda selección: "
                             f"{'otra cara' if modo == 'entre_caras' else 'otra arista'}.")
    e2 = _resolver(origen_b, estado)
    return (_marco_entre_caras(e, e2, version) if modo == "entre_caras" else _marco_interseccion(e, e2)), False, e


def _eje_propio(estado, ref, F2, m0, comps):
    """Eje elegido por la persona (arista, eje, cilindro) como ([punto], [dirección]) en el marco `F2` de la unión.
    Si pertenece a un componente que la unión mueve, se toma ya movido por la alineación `m0`."""
    e = _resolver(ref, estado)
    try:
        punto, dire = ent.como_eje(e)
    except ent.ErrorReferencia as x:
        raise ErrorOperacion(f"El eje de movimiento no sirve: {x}") from x
    punto, dire = np.asarray(punto, float), np.asarray(dire, float)
    if e.tipo == "cara" and e.plano is not None:           # una cara plana: su normal por el centro de la cara
        punto = _centro_contorno_exterior(e.forma)
    elif e.tipo in ("arista", "curva_boceto") and e.forma is not None:
        f = refs.firma_arista(e.forma)
        if f["geom"] == "circulo":                         # el eje de un círculo pasa por su centro, no por un punto suyo
            punto = np.array(f["centro"], float)
    if _componente_de(estado, e) in comps:
        punto, dire = (m0 @ np.r_[punto, 1.0])[:3], m0[:3, :3] @ dire
    inv = np.linalg.inv(F2)
    return [float(x) for x in (inv @ np.r_[punto, 1.0])[:3]], [float(x) for x in inv[:3, :3] @ dire]


def _rot(eje, grados):
    a = math.radians(grados)
    c, s = math.cos(a), math.sin(a)
    m = np.identity(4)
    i, j = {0: (1, 2), 1: (2, 0), 2: (0, 1)}[eje]
    m[i, i], m[i, j], m[j, i], m[j, j] = c, -s, s, c
    return m


def _tras(v):
    m = np.identity(4)
    m[:3, 3] = v
    return m


def eje_local(eje):
    """(punto, dirección unitaria) de un eje de la unión en su marco: «X», «Y», «Z» o un eje propio
    ([punto], [dirección]) que sale de una arista, un eje o un cilindro (`_eje_propio`)."""
    if isinstance(eje, str):
        return np.zeros(3), np.identity(3)[EJES[eje]]
    return np.asarray(eje[0], float), _unit(eje[1])


def _giro_en(eje, grados):
    """Giro de `grados` alrededor de un eje de la unión (el origen del marco o un eje propio que no lo cruza)."""
    if isinstance(eje, str):
        return _rot(EJES[eje], grados)
    p, d = eje_local(eje)
    a = math.radians(grados)
    k = np.array([[0, -d[2], d[1]], [d[2], 0, -d[0]], [-d[1], d[0], 0]])
    m = np.identity(4)
    m[:3, :3] = np.identity(3) + math.sin(a) * k + (1 - math.cos(a)) * (k @ k)
    return _tras(p) @ m @ _tras(-p)


def ejes_bola(ejes):
    """(centro, balanceo, cabeceo, guiñada) de una bola con Pitch y Yaw elegidos (ASM-11): `ejes` es
    {"cabeceo": eje, "guinada": eje} con ejes «X», «Y», «Z» o propios ([punto], [dirección]); lo que falta vale Y para
    el cabeceo y X para la guiñada. La guiñada se vuelve perpendicular al cabeceo y el balanceo (Roll) sale solo, como
    en Fusion: guiñada × cabeceo (con Y y X, el Z del marco). Las tres giran alrededor del punto del eje de cabeceo
    (el origen del marco si es X, Y o Z)."""
    centro, cabeceo = eje_local(ejes.get("cabeceo") or "Y")
    guinada = eje_local(ejes.get("guinada") or "X")[1]
    guinada = guinada - float(guinada @ cabeceo) * cabeceo
    largo = float(np.linalg.norm(guinada))
    if largo < 1e-6:
        raise ErrorOperacion("El eje de cabeceo (Pitch) y el de guiñada (Yaw) son paralelos: elegí dos ejes distintos.")
    guinada = guinada / largo
    return centro, np.cross(guinada, cabeceo), cabeceo, guinada


def movimiento(tipo, valores, eje_giro="Z", eje_desliz="X"):
    """Transformación (en el marco de la unión) que produce el movimiento con esos valores. Cada eje es «X», «Y»,
    «Z» o un eje propio ([punto], [dirección]) en ese marco. En la bola con Pitch y Yaw elegidos (`ejes_bola`) el
    segundo eje es el dict {"cabeceo", "guinada"} y el balanceo sale de los dos."""
    g, d = MOVIMIENTOS[tipo]
    m = np.identity(4)
    if tipo == "bola" and isinstance(eje_desliz, dict):
        centro, balanceo, cabeceo, guinada = ejes_bola(eje_desliz)
        return (_giro_en((centro, balanceo), valores.get("giro", 0.0))
                @ _giro_en((centro, cabeceo), valores.get("giro2", 0.0))
                @ _giro_en((centro, guinada), valores.get("giro3", 0.0)))
    if tipo in ("deslizante", "cilindrica"):
        m = _tras(eje_local(eje_giro if tipo == "cilindrica" else eje_desliz)[1] * valores.get("desliz", 0.0))
    elif tipo == "pasador_ranura":
        m = _tras(eje_local(eje_desliz)[1] * valores.get("desliz", 0.0))
    elif tipo == "planar":
        if isinstance(eje_giro, str):
            a, b = (np.identity(3)[i] for i in range(3) if i != EJES[eje_giro])
        else:
            a, b = marco_desde((0, 0, 0), eje_local(eje_giro)[1])[:3, :2].T
        m = _tras(a * valores.get("desliz", 0.0) + b * valores.get("desliz2", 0.0))
    if tipo == "bola" and not isinstance(eje_giro, str):     # eje propio = el de balanceo; los otros dos salen de él
        p, z = eje_local(eje_giro)
        G = marco_desde(p, z)
        return G @ _rot(2, valores.get("giro", 0.0)) @ _rot(1, valores.get("giro2", 0.0)) \
            @ _rot(0, valores.get("giro3", 0.0)) @ np.linalg.inv(G)
    if "giro" in g:
        m = m @ (_giro_en(eje_giro, valores.get("giro", 0.0)) if tipo != "bola" else _rot(2, valores.get("giro", 0.0)))
    if tipo == "bola":
        m = m @ _rot(1, valores.get("giro2", 0.0)) @ _rot(0, valores.get("giro3", 0.0))
    return m


def direccion_eje(F, eje):
    """Dirección en el mundo de un eje de la unión de marco F (para dibujar el asa del Accionar)."""
    return F[:3, :3] @ eje_local(eje)[1]


def _recta_de(e):
    """(punto, dirección) de una arista recta, una línea de boceto o un eje de construcción."""
    if e.eje is not None:
        return np.asarray(e.eje[0], float), np.asarray(e.eje[1], float)
    if e.tipo in ("arista", "curva_boceto") and e.forma is not None:
        f = refs.firma_arista(e.forma)
        if f["geom"] == "linea":
            a, b = (np.array(p, float) for p in f["extremos"])
            return a, b - a
    raise ErrorOperacion("La intersección de dos aristas necesita dos aristas rectas (o ejes).")


# ---------------------------------------------------------------- operaciones
def _componente_de(estado, e):
    if e.cuerpo is None:
        return None
    return estado.cuerpo(e.cuerpo).componente or ""


def _mover_cuerpo(c, m):
    if getattr(c, "tipo", "solido") == "malla":
        nueva = c.forma.copia()
        nueva.vertices = (np.c_[nueva.vertices, np.ones(len(nueva.vertices))] @ m.T)[:, :3]
        c.forma = nueva
    else:
        c.forma = geo.transformar(c.forma, m)


def _mover_componentes(estado, comps, m):
    for c in estado.cuerpos.values():
        if (c.componente or "") in comps:
            _mover_cuerpo(c, m)
    for k in comps:
        if k in estado.componentes:
            actual = np.asarray(estado.componentes[k].get("matriz", np.identity(4).tolist()), float)
            estado.componentes[k]["matriz"] = (m @ actual).tolist()


def familia(estado, comp):
    """ASM-9: el componente más todos los que cuelgan de él (su subensamblaje): mover el padre los lleva a todos."""
    salida, pendientes = set(), [comp]
    while pendientes:
        k = pendientes.pop()
        if k not in salida:
            salida.add(k)
            pendientes += [h for h, d in estado.componentes.items() if d.get("padre") == k]
    return salida


def ruta_componente(estado, comp):
    """«Padre › Hijo»: el nombre del componente precedido por los de sus antecesores."""
    nombres, vistos = [], set()
    while comp and comp in estado.componentes and comp not in vistos:
        vistos.add(comp)
        nombres.append(str(estado.componentes[comp].get("nombre") or comp))
        comp = estado.componentes[comp].get("padre") or ""
    return " › ".join(reversed(nombres))


def grupo_rigido(estado, comp):
    """El componente, sus subcomponentes y todos los que caen en su grupo rígido, encadenando grupos que comparten
    componentes (A+B y B+C mueven A, B y C juntos) y sumando los subcomponentes de cada uno."""
    salida = familia(estado, comp)
    creció = True
    while creció:
        creció = False
        for g in estado.grupos_rigidos:
            if salida & set(g) and not set(g) <= salida:
                for k in g:
                    salida |= familia(estado, k)
                creció = True
    return salida


def _matriz_de(estado, comp):
    return np.asarray(estado.componentes.get(comp, {}).get("matriz", np.identity(4).tolist()), float)


def pose_de_reasignar(estado, cuerpos):
    """La pose con la que arranca un componente que recibe `cuerpos` en ESTE momento (B-123): la de su
    componente anterior si todos traen la misma, o la identidad si vienen movidos por uniones distintas.
    El paso la guarda (`OpComponente.p["pose"]`) para que la reasignación no se corra cuando después se
    acciona una unión de aquel componente."""
    elegidos = list({c.id: c for c in map(estado.cuerpo, cuerpos)}.values())
    matrices = [_matriz_de(estado, c.componente) for c in elegidos]
    comun = matrices[0] if matrices else np.identity(4)
    return comun if all(np.allclose(m, comun, atol=1e-9) for m in matrices) else np.identity(4)


def pose_de_componente(estado, padre):
    """B-178: la matriz del componente en este momento (identidad en la raíz). Un paso creado después de una unión la
    guarda (`pose_padre` del componente hijo, `pose` de un punto de agujero) para seguir al componente cuando
    después se acciona la unión."""
    return _matriz_de(estado, padre) if padre else np.identity(4)


def _matriz_de_cuerpos(estado, cuerpos, nombre, ctx, pose=None):
    """La matriz con la que arranca un componente que recibe `cuerpos`. Cada cuerpo llega con el movimiento de su
    componente anterior ya aplicado a la forma: si todos traen el mismo, el nuevo lo hereda y nadie se mueve. Si traen
    distintos, ninguna matriz los representa juntos y cada uno vuelve a donde se modeló: su posición relativa deja de
    depender de las uniones de los componentes de donde salieron (B-108). Con `pose` (guardada en la receta al
    reasignar, B-123) el resultado es siempre esa pose: los cuerpos se llevan a ella, así accionar después las
    uniones de sus componentes anteriores no los mueve."""
    elegidos = list({c.id: c for c in map(estado.cuerpo, cuerpos)}.values())
    matrices = [_matriz_de(estado, c.componente) for c in elegidos]
    comun = matrices[0] if matrices else np.identity(4)
    if pose is not None:
        if not all(np.allclose(m, comun, atol=1e-9) for m in matrices):
            ctx.aviso(f"Los cuerpos de «{nombre}» venían movidos por uniones distintas: quedan en la pose guardada "
                      "al reasignarlos.")
        for c, m in zip(elegidos, matrices, strict=True):
            if not np.allclose(m, pose, atol=1e-9):
                _mover_cuerpo(c, pose @ np.linalg.inv(m))
        return pose
    if all(np.allclose(m, comun, atol=1e-9) for m in matrices):
        return comun
    for c, m in zip(elegidos, matrices, strict=True):
        _mover_cuerpo(c, np.linalg.inv(m))
    ctx.aviso(f"Los cuerpos de «{nombre}» venían movidos por uniones distintas: vuelven a donde se modelaron para "
              "conservar su posición relativa.")
    return np.identity(4)


class OpComponente(Operacion):
    """ENSAMBLAR › Nuevo componente [GUID-5966BF6B]: crea un componente y le pasa los cuerpos elegidos
    («Desde cuerpos»). `fijo` es «Fijar» (Ground): una unión no puede moverlo. `padre` («Parent», ASM-9): el componente
    del que cuelga (id, nombre o uno de sus cuerpos; "" = la raíz); mover el padre lo mueve. `version_pose` (2 en los
    nuevos; 1 en las recetas viejas, ver `_migrador`): con 2 el componente tiene en cuenta el movimiento que traen sus
    cuerpos (`_matriz_de_cuerpos`); con 1 arranca siempre en la identidad. `pose` (B-123, solo con version_pose 2): la
    pose congelada del momento en que se reasignaron los cuerpos (`pose_de_reasignar`); sin ella (recetas viejas) la
    pose heredada se recalcula con la actual de sus componentes anteriores, como siempre."""
    TIPO, ETIQUETA, ICONO = "componente", "Componente", "▣"
    PARAMS = {"cuerpos": [], "fijo": False, "version_pose": 2, "padre": "", "pose": None, "pose_padre": None}
    migrar_receta = _migrador("version_pose")

    def dependencias(self):
        return (_deps_objetivo(self.p["cuerpos"]) | _dep_componente(self.p.get("padre") or "")) - {self.id}

    def ejecutar(self, estado, ctx):
        padre = ""
        if self.p.get("padre"):
            padre = componente_por_ref(estado, self.p["padre"])
            if padre is None:
                raise ErrorOperacion(f"No encuentro el componente padre «{self.p['padre']}» en este punto del timeline. "
                                     f"Componentes: {', '.join(c.get('nombre') or k for k, c in estado.componentes.items()) or 'ninguno'}.")
        matriz = np.identity(4)
        if _version_de(self.p, "version_pose") >= 2:
            pose = None
            if self.p.get("pose") is not None:
                try:
                    pose = np.asarray(self.p["pose"], float)
                    if pose.shape != (4, 4):
                        raise ValueError
                except (TypeError, ValueError):
                    raise ParametroMalFormado(self.p["pose"], "se esperaba la matriz 4x4 de la pose congelada del "
                                              "momento de reasignar los cuerpos.") from None
            matriz = _matriz_de_cuerpos(estado, self.p["cuerpos"], self.nombre, ctx, pose)
        base = matriz
        if padre and self.p.get("pose_padre") is not None:
            # B-178: los cuerpos se modelaron con el padre en `pose_padre`; si hoy está en otra pose (se accionó una
            # unión suya antes de este paso), el hijo lo sigue.
            delta = _matriz_de(estado, padre) @ np.linalg.inv(np.asarray(self.p["pose_padre"], float))
            if not np.allclose(delta, np.identity(4), atol=1e-9):
                for cid in self.p["cuerpos"]:
                    _mover_cuerpo(estado.cuerpo(cid), delta)
                matriz = delta @ matriz
            base = matriz        # B-353: lo que sigue al padre es heredado, no el movimiento de otra unión
        estado.componentes[self.id] = {"nombre": self.nombre, "padre": padre, "fijo": bool(self.p["fijo"]),
                                       "matriz": matriz.tolist(), "base": base.tolist()}
        if padre and self.p.get("pose_padre") is not None:
            estado.componentes[self.id]["pose_padre"] = self.p["pose_padre"]
        viejos = {estado.cuerpo(cid).componente for cid in self.p["cuerpos"]} - {"", self.id}
        for cid in self.p["cuerpos"]:
            estado.cuerpo(cid).componente = self.id
        for k in sorted(viejos):       # ASM-7: el componente de donde salió su único cuerpo queda vacío
            if k in estado.componentes and not any(c.componente == k for c in estado.cuerpos.values()):
                nombre = estado.componentes[k].get("nombre") or k
                ctx.aviso(f"El componente «{nombre}» quedó sin cuerpos{' (estaba fijo)' if es_fijo(estado, k) else ''}: "
                          "sus uniones ya no mueven ni sujetan nada. Borralo o pasale otro cuerpo.")


def _camino_lazo(estado, comp1, comp2):
    """Camino previo entre los componentes; raíz y componentes fijos son tierra."""
    if not any(comp1 == u["comp1"] or comp1 in u["componentes"] for u in estado.uniones.values()):
        return []

    def nodo(comp):
        return "" if not comp or es_fijo(estado, comp) else comp

    grafo = {}
    for uid, u in estado.uniones.items():
        a, b = nodo(u["comp1"]), nodo(u["comp2"])
        grafo.setdefault(a, []).append((b, uid))
        grafo.setdefault(b, []).append((a, uid))
    pendientes = [(nodo(comp2), [])]
    vistos = {nodo(comp2)}
    for actual, camino in pendientes:
        if actual == nodo(comp1):
            return camino
        for vecino, uid in grafo.get(actual, []):
            if vecino not in vistos:
                vistos.add(vecino)
                pendientes.append((vecino, camino + [uid]))
    return []


def _marco_local(estado, comp, marco, canonico):
    return {"local": (np.linalg.inv(_matriz_de(estado, comp)) @ marco).tolist(), "canonico": canonico}


def _marco_en_pose(datos, matriz):
    local = np.asarray(datos["local"], float)
    if datos["canonico"]:          # B-177: canónico en el sistema del componente, como `_marco_modo`
        local = _marco_de_eje(local[:3, 3], local[:3, 2])
    return matriz @ local


def _resolver_lazo(estado, ctx, cierre, camino):
    """Resuelve en matrices, sin transformar OCC durante las iteraciones."""
    from scipy.optimize import least_squares
    from scipy.spatial.transform import Rotation

    uniones = [(uid, u) for uid, u in estado.uniones.items() if uid in camino] + [(None, cierre)]
    if any(not u.get("reaplicar") or u.get("cierra_lazo") for _, u in uniones):
        ctx.aviso(f"Lazo cerrado no resuelto: «{cierre['nombre']}» incluye una unión como está sobre una pieza "
                  "ya movida o un lazo previo que no se puede re-aplicar como cadena.")
        return False
    accionada = max(range(len(uniones)), key=lambda i: uniones[i][1]["accionada"])
    if not uniones[accionada][1]["accionada"] or not any(MOVIMIENTOS[uniones[accionada][1]["tipo"]]):
        accionada = 0
    variables = [(i, k) for i, (_, u) in enumerate(uniones) if i != accionada
                 for k in sum(MOVIMIENTOS[u["tipo"]], [])]
    inicial = np.array([uniones[i][1]["valores"][k] for i, k in variables], float)
    poses = {k: _matriz_de(estado, k) for k in estado.componentes}
    poses[""] = np.identity(4)
    escala = max(1.0, *(np.linalg.norm(np.asarray(u["reaplicar"][lado]["local"])[:3, 3])
                        for _, u in uniones for lado in ("marco1", "marco2")))
    factores = np.array([180.0 if k.startswith("giro") else escala for _, k in variables])

    def probar(x):
        valores = [dict(u["valores"]) for _, u in uniones]
        for (i, k), v in zip(variables, x, strict=True):
            valores[i][k] = float(v)
        nuevas = dict(poses)
        for i, (_, u) in enumerate(uniones[:-1]):
            datos = u["reaplicar"]
            base = np.asarray(datos["bases"][u["comp1"]], float)
            f1 = _marco_en_pose(datos["marco1"], base)
            f2 = _marco_en_pose(datos["marco2"], nuevas[u["comp2"]])
            delta = (f2 @ movimiento(u["tipo"], valores[i], u["eje_giro"], u["eje_desliz"])
                     @ np.asarray(datos["alinear"]) @ np.linalg.inv(f1))
            for comp, matriz in datos["bases"].items():
                nuevas[comp] = delta @ np.asarray(matriz)
        datos = cierre["reaplicar"]
        f1 = _marco_en_pose(datos["marco1"], nuevas[cierre["comp1"]])
        f2 = _marco_en_pose(datos["marco2"], nuevas[cierre["comp2"]])
        objetivo = (f2 @ movimiento(cierre["tipo"], valores[-1], cierre["eje_giro"], cierre["eje_desliz"])
                    @ np.asarray(datos["alinear"]))
        error = np.r_[f1[:3, 3] - objetivo[:3, 3],
                      Rotation.from_matrix(objetivo[:3, :3].T @ f1[:3, :3]).as_rotvec() * escala]
        return error, nuevas, valores

    def residual(x):
        return probar(x)[0]

    def distancia(x):
        diferencia = x - inicial
        for j, (_, k) in enumerate(variables):
            if k.startswith("giro"):
                diferencia[j] = (diferencia[j] + 180) % 360 - 180
        return np.linalg.norm(diferencia)

    solucion = None
    # shortcut: pocas semillas angulares, no búsqueda global de todas las ramas de un mecanismo espacial.
    for giro in (0, 90, -90, 180):
        semilla = inicial.copy()
        for j, (_, k) in enumerate(variables):
            if k.startswith("giro"):
                semilla[j] += giro
        if variables:
            resultado = least_squares(residual, semilla, x_scale=factores, max_nfev=160,
                                      xtol=1e-14, ftol=1e-14, gtol=1e-14)
            candidato = resultado.x if resultado.success else None
        else:
            candidato = semilla
        if candidato is not None and np.linalg.norm(residual(candidato)) < 1e-7:
            if solucion is None or distancia(candidato) < distancia(solucion):
                solucion = candidato
            if distancia(solucion) < 1e-10:
                break
    mensaje = (f"Lazo cerrado sin solución: la unión «{cierre['nombre']}» cierra el lazo pero la geometría "
               "no alcanza la posición pedida (por ejemplo, una biela más corta que la manivela).")
    if solucion is None:
        raise ErrorOperacion(mensaje)
    for j, (_, k) in enumerate(variables):
        if k.startswith("giro"):
            solucion[j] = inicial[j] + (solucion[j] - inicial[j] + 180) % 360 - 180
    _, nuevas, valores = probar(solucion)
    movidos = {comp for _, u in uniones[:-1] for comp in u["componentes"]}
    # Las ramas colgadas conservan su pose relativa al padre, incluso fuera del camino del lazo.
    pendientes = set(movidos)
    while pendientes:
        padre = pendientes.pop()
        delta = nuevas[padre] @ np.linalg.inv(poses[padre])
        for uid, u in estado.uniones.items():
            if uid not in camino and u["comp2"] == padre:
                for comp in u["componentes"]:
                    if comp not in movidos and comp and not es_fijo(estado, comp):
                        nuevas[comp] = delta @ poses[comp]
                        movidos.add(comp)
                        pendientes.add(comp)
    for comp in movidos:
        _mover_componentes(estado, {comp}, nuevas[comp] @ np.linalg.inv(poses[comp]))
    # Verificación independiente con la geometría real, no solo con los marcos guardados.
    datos = cierre["reaplicar"]
    if datos.get("como_esta"):
        f1 = _marco_en_pose(datos["marco1"], _matriz_de(estado, cierre["comp1"]))
        f2 = _marco_en_pose(datos["marco2"], _matriz_de(estado, cierre["comp2"]))
    else:
        f1 = _marco_modo(estado, datos["origen1"], datos.get("origen1b"), datos.get("modo1"), datos["clave1"],
                         datos["version"])[0]
        f2 = _marco_modo(estado, datos["origen2"], datos.get("origen2b"), datos.get("modo2"), datos["clave2"],
                         datos["version"])[0]
    objetivo = (f2 @ movimiento(cierre["tipo"], valores[-1], cierre["eje_giro"], cierre["eje_desliz"])
                @ np.asarray(datos["alinear"]))
    if (np.linalg.norm(f1[:3, 3] - objetivo[:3, 3]) >= 1e-6 or
            np.linalg.norm(Rotation.from_matrix(objetivo[:3, :3].T @ f1[:3, :3]).as_rotvec()) >= 1e-6):
        raise ErrorOperacion(mensaje)
    for i, (uid, u) in enumerate(uniones):
        datos = u["reaplicar"]
        marco = _marco_en_pose(datos["marco2"], nuevas[u["comp2"]])
        actualizado = dict(u, valores=valores[i], marco=marco.tolist())
        if uid is None:
            cierre.update(actualizado)  # cierre todavía no pertenece a ningún estado anterior
        else:
            estado.uniones[uid] = actualizado
        if i != accionada and any(MOVIMIENTOS[u["tipo"]]):
            clave = "giro" if MOVIMIENTOS[u["tipo"]][0] else "desliz"
            v = valores[i][clave]
            minimo, maximo = datos["limites"]
            if (minimo is not None and v < minimo) or (maximo is not None and v > maximo):
                ctx.aviso(f"La unión «{u['nombre']}» resuelta en el lazo ({v:g}) viola sus límites de movimiento.")
    return True


class OpUnion(Operacion):
    """ENSAMBLAR › Unión [ASM-CREATE-JOINT] y Unión como está [ASM-CREATE-AS-BUILT-JOINT].

    `version_marco` (2 en las uniones nuevas; 1 en las recetas viejas, ver `_migrador`): con 2
    el marco es el de `_marco` y dos marcos de eje (perno en agujero, rueda en eje, también a través de un
    «Origen de unión» puesto sobre ellos) quedan con los ejes en el mismo sentido; «Voltear» los opone. La unión «como está» con `origen2` (un cuerpo del componente 2)
    liga el componente 1 al 2: conserva la posición modelada respecto de él y lo sigue cuando se mueve.
    Al cerrar un lazo, la última unión accionada conserva su movimiento (por defecto, la primera del timeline);
    se resuelven numéricamente los giros y deslizamientos de las demás. Los lazos superpuestos y las uniones
    como está sobre piezas ya movidas conservan el comportamiento secuencial con un aviso.

    Modo de cada origen (`modo1`, `modo2`; ASM-10): «simple», «entre_caras» o «interseccion» (usan `origen1b` /
    `origen2b`, la segunda cara o arista). Ejes propios (`ref_eje_giro`, `ref_eje_desliz`; ASM-11): una arista,
    un eje o un cilindro en vez de X, Y o Z del marco. Límites por movimiento, reposo e invertir
    (`limites_dof`; ASM-12): {"giro2": {"minimo", "maximo", "reposo", "invertir"}}; los del movimiento
    principal siguen en `minimo` y `maximo`."""
    TIPO, ETIQUETA, ICONO = "union", "Unión", "⚙"
    PARAMS = {"tipo": "rigida", "origen1": None, "origen2": None, "clave1": "centro", "clave2": "centro",
              "angulo": "0 deg", "dx": "0 mm", "dy": "0 mm", "dz": "0 mm", "voltear": False, "como_esta": False,
              "eje_giro": "Z", "eje_desliz": "X", "giro": "0 deg", "giro2": "0 deg", "giro3": "0 deg",
              "desliz": "0 mm", "desliz2": "0 mm", "minimo": "", "maximo": "", "version_marco": 2, "accionada": 0,
              "modo1": "simple", "modo2": "simple", "origen1b": None, "origen2b": None,
              "ref_eje_giro": None, "ref_eje_desliz": None, "limites_dof": {}, "eje_cabeceo": "", "eje_guinada": "",
              "ref_eje_cabeceo": None, "ref_eje_guinada": None}
    EXPRESIONES = ("angulo", "dx", "dy", "dz", "giro", "giro2", "giro3", "desliz", "desliz2")
    OPCIONES = {"tipo": TIPOS_UNION, "clave1": PUNTOS_CLAVE, "clave2": PUNTOS_CLAVE, "eje_giro": EJES,
                "eje_desliz": EJES, "modo1": MODOS_POSICION, "modo2": MODOS_POSICION,
                "eje_cabeceo": ("", *EJES), "eje_guinada": ("", *EJES)}
    migrar_receta = _migrador("version_marco")

    def dependencias(self):
        p = self.p
        return (super().dependencias() | ent.dependencias_de(
            p["origen1"], p["origen2"], p.get("origen1b"), p.get("origen2b"), p.get("ref_eje_giro"),
            p.get("ref_eje_desliz"), p.get("ref_eje_cabeceo"), p.get("ref_eje_guinada"))) - {self.id}

    def limites(self, ctx, clave):
        """(mínimo, máximo) de un movimiento en grados o mm, con «invertir» ya aplicado; None = sin límite."""
        mn, mx, _reposo, invertir = limites_expr(self.p, clave)
        tipo = ANGULO if clave.startswith("giro") else "longitud"
        lim = [ctx.evaluar(x, tipo) if str(x or "").strip() else None for x in (mn, mx)]
        if invertir:
            lim = [None if lim[1] is None else -lim[1], None if lim[0] is None else -lim[0]]
        return lim

    def valores(self, ctx, aviso=None):
        """Valores del movimiento. Los límites (Joint Motion Limits) de cada movimiento lo recortan; con `aviso`
        se avisa cuando lo hacen."""
        g = {k: ctx.evaluar(self.p[k], ANGULO) for k in ("giro", "giro2", "giro3")}
        g.update({k: ctx.evaluar(self.p[k]) for k in ("desliz", "desliz2")})
        etiqueta = {"giro": "El giro pedido", "giro2": "El cabeceo pedido", "giro3": "La guiñada pedida",
                    "desliz": "La distancia pedida", "desliz2": "La distancia 2 pedida"}
        for clave in sum(MOVIMIENTOS[self.p["tipo"]], []):
            unidad = "°" if clave.startswith("giro") else " mm"
            mn, mx = self.limites(ctx, clave)
            for valor, cual, recorta in ((mn, "es menor que el límite mínimo", max),
                                         (mx, "supera el límite máximo", min)):
                if valor is not None and recorta(g[clave], valor) != g[clave]:
                    if aviso is not None:
                        aviso(f"{etiqueta[clave]} ({g[clave]:g}{unidad}) {cual} ({valor:g}{unidad}): la unión quedó "
                              f"en {valor:g}{unidad}.")
                    g[clave] = valor
        return g

    def _ejes(self, estado, F2, m0, comps):
        """(eje de giro, eje de deslizamiento) efectivos: X, Y, Z del marco o el eje propio elegido. En la bola con
        Pitch o Yaw elegidos (ASM-11), el segundo es {"cabeceo": eje, "guinada": eje} (`ejes_bola`)."""
        p = self.p
        giro, desliz = tuple(_eje_propio(estado, p[ref], F2, m0, comps) if p.get(ref) else p[eje]
                             for eje, ref in (("eje_giro", "ref_eje_giro"), ("eje_desliz", "ref_eje_desliz")))
        if p["tipo"] == "bola" and any(p.get(k) for k in ("eje_cabeceo", "eje_guinada", "ref_eje_cabeceo",
                                                           "ref_eje_guinada")):
            elegir = lambda eje, ref: (_eje_propio(estado, p[ref], F2, m0, comps) if p.get(ref)       # noqa: E731
                                       else p.get(eje) or None)
            desliz = {"cabeceo": elegir("eje_cabeceo", "ref_eje_cabeceo"),
                      "guinada": elegir("eje_guinada", "ref_eje_guinada")}
        return giro, desliz

    def ejecutar(self, estado, ctx):
        p = self.p
        self._usados = set()
        for k in (*self.EXPRESIONES, "minimo", "maximo"):
            exigir_numero(p.get(k))
        version = _version_de(p, "version_marco")
        accionada = self.entero("accionada", minimo=0)
        if not p["origen1"]:
            raise ErrorOperacion("Elegí el origen de la unión en el componente 1.")
        F1, eje1, e1 = _marco_modo(estado, p["origen1"], p.get("origen1b"), p.get("modo1"), p["clave1"], version)
        comp1 = _componente_de(estado, e1)
        if not comp1:
            raise ErrorOperacion("El componente 1 tiene que ser un componente (no la raíz): creá uno con "
                                 "ENSAMBLAR › Nuevo componente.")
        if es_fijo(estado, comp1):
            raise ErrorOperacion("El componente 1 está fijo: no se puede mover con una unión.")
        valores = self.valores(ctx, ctx.aviso)
        reaplicar = None
        comps = grupo_rigido(estado, comp1)
        fijos = [c for c in comps if es_fijo(estado, c)]
        if fijos:
            nombre = estado.componentes[fijos[0]].get("nombre") or fijos[0]
            raise ErrorOperacion(f"El componente 1 está en un grupo rígido con «{nombre}», que está fijo: no se "
                                 "puede mover con una unión.")
        if p["como_esta"]:
            comp2, seguir = "", np.identity(4)
            if p["origen2"]:
                comp2 = _componente_de(estado, _resolver(p["origen2"], estado)) or ""
                if comp2 == comp1:
                    raise ErrorOperacion("Los dos orígenes están en el mismo componente.")
            camino = _camino_lazo(estado, comp1, comp2)
            base = estado.componentes[comp1].get("base", np.identity(4).tolist())       # la heredada no es movimiento
            ya_movida = not np.allclose(_matriz_de(estado, comp1), base, atol=1e-9)
            if comp2 and ya_movida and not camino:
                # Otra unión anterior ya movió el componente 1: se queda donde está (no se pisa ese movimiento).
                ctx.aviso("Otra unión ya mueve el componente 1: la unión como está lo deja donde está. Para que "
                          "siga al componente 2, elegí como componente 1 la pieza que no tiene otra unión.")
            elif comp2 and not ya_movida:
                # Posición modelada respecto del componente 2: lo que él se movió, el 1 también.
                m1 = _matriz_de(estado, comp1)
                datos1 = estado.componentes[comp1]
                if datos1.get("padre") == comp2 and datos1.get("pose_padre") is not None:
                    m1 = m1 @ np.asarray(datos1["pose_padre"], float)       # B-353: el hijo ya sigue a su padre
                seguir = _matriz_de(estado, comp2) @ np.linalg.inv(m1)
            F2 = seguir @ F1
            ejes = self._ejes(estado, F2, seguir, comps)
            mov = movimiento(p["tipo"], valores, *ejes)
            m = F2 @ mov @ np.linalg.inv(F2) @ seguir
            if not (comp2 and ya_movida) or camino:
                marco = _marco_local(estado, comp1, F1, False)
                if version >= 2 and eje1 and e1.tipo != "plano":
                    local = np.asarray(marco["local"], float)
                    marco["local"] = _marco_de_eje(local[:3, 3], local[:3, 2]).tolist()
                # El marco modelado es compartido y rígido: el movimiento es relativo al componente 2.
                reaplicar = {"marco1": marco, "marco2": marco, "alinear": np.identity(4).tolist(),
                             "como_esta": True}
        else:
            if not p["origen2"]:
                raise ErrorOperacion("Elegí el origen de la unión en el componente 2.")
            F2, eje2, e2 = _marco_modo(estado, p["origen2"], p.get("origen2b"), p.get("modo2"), p["clave2"], version)
            comp2 = _componente_de(estado, e2) or ""
            if comp2 == comp1:
                raise ErrorOperacion("Los dos orígenes están en el mismo componente.")
            opuestos = not (version >= 2 and eje1 and eje2)       # caras enfrentadas; dos ejes: mismo sentido
            enfrentar = _rot(0, 180.0) if opuestos != bool(p["voltear"]) else np.identity(4)
            desfase = _tras([ctx.evaluar(p[k]) for k in ("dx", "dy", "dz")])
            alinear = desfase @ _rot(2, ctx.evaluar(p["angulo"], ANGULO)) @ enfrentar
            m0 = F2 @ alinear @ np.linalg.inv(F1)
            z1 = F1[:3, 2]
            if version >= 2 and not p["voltear"] and float((m0[:3, :3] @ z1) @ z1) < -0.99:
                ctx.aviso("La unión dejó el componente 1 dado vuelta respecto de cómo está modelado; si no es lo "
                          "que querías, marcá «Voltear».")
            ejes = self._ejes(estado, F2, m0, comps)
            m = F2 @ movimiento(p["tipo"], valores, *ejes) @ alinear @ np.linalg.inv(F1)
            reaplicar = {"marco1": _marco_local(estado, comp1, F1, version >= 2 and eje1 and e1.tipo != "plano"),
                         "marco2": _marco_local(estado, comp2, F2, version >= 2 and eje2 and e2.tipo != "plano"),
                         "alinear": alinear.tolist()}
        # ASM-3: cuenta el componente resuelto aquí, también en cuerpos divididos, copiados o reasignados.
        self._usados = (comps | {comp2}) - {"", self.id}
        if reaplicar is not None:
            reaplicar.update(bases={c: _matriz_de(estado, c).tolist() for c in comps},
                             origen1=p["origen1"], origen2=p["origen2"], clave1=p["clave1"], clave2=p["clave2"],
                             modo1=p.get("modo1"), modo2=p.get("modo2"), origen1b=p.get("origen1b"),
                             origen2b=p.get("origen2b"), version=version,
                             limites=self.limites(ctx, principal_de(p["tipo"])))
        union = {"nombre": self.nombre, "tipo": p["tipo"], "comp1": comp1, "comp2": comp2,
                 "componentes": sorted(comps), "marco": F2.tolist(), "eje_giro": ejes[0],
                 "eje_desliz": ejes[1], "valores": valores, "reaplicar": reaplicar, "accionada": accionada}
        camino = _camino_lazo(estado, comp1, comp2)
        if camino:
            if _resolver_lazo(estado, ctx, union, camino):
                estado.uniones[self.id] = dict(union, cierra_lazo=True)
                return
        _mover_componentes(estado, comps, m)
        estado.uniones[self.id] = union


def siguiente_accion(operaciones):
    """Prioridad de la próxima unión accionada en el documento; conserva el orden entre recálculos."""
    return 1 + max((o.entero("accionada", minimo=0) for o in operaciones if isinstance(o, OpUnion)), default=0)


class OpOrigenUnion(Operacion):
    """ENSAMBLAR › Origen de la unión [ASM-CREATE-JOINT-ORIGIN]: un marco guardado que después sirve para
    unir. Se guarda como plano de construcción (su plano XY) con el ángulo pedido. `version_marco` como en
    `OpUnion`."""
    TIPO, ETIQUETA, ICONO = "origen_union", "Origen de unión", "⌖"
    PARAMS = {"origen": None, "clave": "centro", "angulo": "0 deg", "dx": "0 mm", "dy": "0 mm", "dz": "0 mm",
              "version_marco": 2, "modo": "simple", "origen_b": None}
    EXPRESIONES = ("angulo", "dx", "dy", "dz")
    OPCIONES = {"clave": PUNTOS_CLAVE, "modo": MODOS_POSICION}
    migrar_receta = _migrador("version_marco")

    def dependencias(self):
        return ent.dependencias_de(self.p["origen"], self.p.get("origen_b")) - {self.id}

    def ejecutar(self, estado, ctx):
        version = _version_de(self.p, "version_marco")
        if not self.p["origen"]:
            raise ErrorOperacion("Elegí dónde va el origen.")
        F, eje, _e = _marco_modo(estado, self.p["origen"], self.p.get("origen_b"), self.p.get("modo"),
                                 self.p["clave"], version)
        F = F @ _tras([ctx.evaluar(self.p[k]) for k in ("dx", "dy", "dz")]) @ _rot(2, ctx.evaluar(self.p["angulo"], ANGULO))
        plano = geo.Plano.desde_marco(F[:3, 3], F[:3, 2], F[:3, 0], self.nombre)
        plano.eje_de_union = eje        # una unión lo trata como el cilindro o la arista de donde salió
        estado.planos[self.id] = plano


def componente_por_ref(estado, ref):
    """Componente que nombra `ref`: su id (el del paso que lo creó, p. ej. "op5"), su nombre sin importar
    mayúsculas o el id de uno de sus cuerpos ("op2.c1"). None si no hay ninguno."""
    if not isinstance(ref, str) or not ref.strip():
        return None
    if ref in estado.componentes:
        return ref
    nombre = ref.strip().casefold()
    hallados = [k for k, c in estado.componentes.items() if str(c.get("nombre") or "").casefold() == nombre]
    if len(hallados) > 1:
        raise ErrorOperacion(f"Hay varios componentes llamados «{ref}»: usá el id.")
    if hallados:
        return hallados[0]
    cuerpo = estado.cuerpos.get(ref)
    return cuerpo.componente if cuerpo is not None and cuerpo.componente else None


class OpGrupoRigido(Operacion):
    """ENSAMBLAR › Grupo rígido [ASM-CREATE-RIGID-GROUP]: los componentes se mueven juntos. Cada componente
    se nombra por id, por nombre o por el id de uno de sus cuerpos (`componente_por_ref`). `incluir_hijos` es «Incluir
    componentes secundarios» (ASM-9): también entran al grupo los subcomponentes de cada uno; sin marcar, un
    subcomponente sigue a su padre pero puede moverse solo."""
    TIPO, ETIQUETA, ICONO = "grupo_rigido", "Grupo rígido", "⛓"
    PARAMS = {"componentes": [], "incluir_hijos": False}

    def dependencias(self):
        lista = self.p["componentes"] if isinstance(self.p["componentes"], (list, tuple)) else []
        ids = {c.split(".")[0] for c in lista if isinstance(c, str) and re.fullmatch(r"op\d+(\..*)?", c)}
        return (super().dependencias() | ids) - {self.id}

    def ejecutar(self, estado, ctx):
        if not estado.componentes:
            raise ErrorOperacion("Todavía no hay componentes en este punto del timeline: creá uno con "
                                 "ENSAMBLAR › Nuevo componente.")
        ids, faltan = [], []
        for ref in self.p["componentes"]:
            comp = componente_por_ref(estado, ref)
            if comp is None:
                faltan.append(ref)
            elif comp not in ids:
                ids.append(comp)
        self._usados = set(ids) - {self.id}
        if faltan or len(ids) < 2:
            no_hay = f" No encontré: {', '.join(f'«{r}»' for r in faltan)}." if faltan else ""
            hay = ", ".join(f"{c.get('nombre') or k} ({k})" for k, c in estado.componentes.items())
            raise ErrorOperacion(f"Elegí al menos dos componentes existentes.{no_hay} Componentes disponibles: {hay}.")
        if self.p.get("incluir_hijos"):
            ids = _con_subcomponentes(estado, ids)
        estado.grupos_rigidos = estado.grupos_rigidos + [ids]


def _clave_movimiento(u, elegido):
    """El movimiento de la unión `u` que entra en un vínculo: el elegido o, sin elegir, el giro si gira y si no el
    deslizamiento."""
    giros, desliz = MOVIMIENTOS[u["tipo"]]
    if not elegido:
        return "giro" if giros else "desliz"
    if elegido not in giros + desliz:
        raise ErrorOperacion(f"La unión «{u['nombre']}» no tiene el movimiento «{elegido}»: tiene "
                             f"{', '.join(giros + desliz) or 'ninguno (es rígida)'}.")
    return elegido


class OpVinculoMovimiento(Operacion):
    """ENSAMBLAR › Vínculo de movimiento [GUID-074622A9]: la unión 2 se mueve en proporción a la 1.

    El valor vinculado REEMPLAZA al de la unión 2 (`version_vinculo` 2). Las recetas viejas (1) lo sumaban
    sobre la posición ya calculada de la unión 2 y abren igual que antes. Las dos uniones pueden ser la misma
    (ASM-13): `mov1` y `mov2` son entonces dos movimientos distintos de ella (un tornillo: el giro manda sobre el
    deslizamiento)."""
    TIPO, ETIQUETA, ICONO = "vinculo_movimiento", "Vínculo de movimiento", "⇄"
    PARAMS = {"union1": "", "union2": "", "factor": "1", "invertir": False, "version_vinculo": 2,
              "mov1": "", "mov2": ""}
    EXPRESIONES = ("factor",)
    migrar_receta = _migrador("version_vinculo")

    def dependencias(self):
        return {self.p["union1"], self.p["union2"]} - {"", self.id}

    def ejecutar(self, estado, ctx):
        version = _version_de(self.p, "version_vinculo")
        u1, u2 = estado.uniones.get(self.p["union1"]), estado.uniones.get(self.p["union2"])
        faltan = [f"«{i}»" for i, u in ((self.p["union1"], u1), (self.p["union2"], u2)) if not u]
        if faltan:
            raise ErrorOperacion(f"El vínculo necesita la unión {' y la unión '.join(faltan)}, que no está calculada: "
                                 "está suprimida, borrada o después de este paso.")
        clave1 = _clave_movimiento(u1, self.p.get("mov1"))
        clave2 = _clave_movimiento(u2, self.p.get("mov2"))
        misma = self.p["union1"] == self.p["union2"]
        if misma and clave1 == clave2:
            raise ErrorOperacion(f"Para relacionar dos movimientos de la misma unión («{u1['nombre']}») hay que elegir dos "
                                 f"distintos (los dos son «{clave1}»): elegí el de la unión 1 y el de la unión 2 (por "
                                 "ejemplo, giro y deslizamiento de una cilíndrica).")
        if self.p["union2"] in estado.vinculos:
            otro = estado.uniones.get(estado.vinculos[self.p["union2"]], {})
            raise ErrorOperacion(f"La unión «{u2['nombre']}» ya la mueve el vínculo «{otro.get('nombre', 'otro')}»: "
                                 "una unión solo puede seguir a un vínculo.")
        actual, vistos = self.p["union1"], set()
        while actual in estado.vinculos and actual not in vistos:
            vistos.add(actual)
            actual = estado.vinculos[actual]
            if actual == self.p["union2"]:
                raise ErrorOperacion(f"El vínculo «{u1['nombre']}» → «{u2['nombre']}» armaría un círculo: "
                                     f"«{u2['nombre']}» ya mueve a «{u1['nombre']}».")
        factor = ctx.evaluar(self.p["factor"], "escalar") * (-1 if self.p["invertir"] else 1)
        if not math.isfinite(factor) or factor == 0:
            raise ErrorOperacion("La relación del vínculo no puede ser cero: la unión 2 no se movería.")
        estado.vinculos[self.p["union2"]] = self.p["union1"]
        F2 = np.asarray(u2["marco"], float)
        if version < 2:
            extra = dict.fromkeys(MOVIMIENTOS[u2["tipo"]][0] + MOVIMIENTOS[u2["tipo"]][1], 0.0)
            extra[clave2] = u1["valores"][clave1] * factor
            m = F2 @ movimiento(u2["tipo"], extra, u2["eje_giro"], u2["eje_desliz"]) @ np.linalg.inv(F2)
            _mover_componentes(estado, set(u2["componentes"]), m)
            return
        # Se deshace el movimiento propio de la unión 2 y se aplica el vinculado (exacto también en planar y
        # pasador-ranura, donde giro y desplazamiento no conmutan).
        viejos = u2["valores"]
        nuevos = dict(viejos, **{clave2: u1["valores"][clave1] * factor})
        m = (F2 @ movimiento(u2["tipo"], nuevos, u2["eje_giro"], u2["eje_desliz"])
             @ np.linalg.inv(movimiento(u2["tipo"], viejos, u2["eje_giro"], u2["eje_desliz"])) @ np.linalg.inv(F2))
        _mover_componentes(estado, set(u2["componentes"]), m)
        enlace = {"union1": self.p["union1"], "clave1": clave1, "clave2": clave2, "factor": factor}
        # dict nuevo: la copia del estado es superficial; `vinculo` lo usa el estudio de movimiento (`poses_de_estudio`)
        estado.uniones[self.p["union2"]] = dict(u2, valores=nuevos, vinculo=enlace)


def _comp_o_error(estado, ref):
    comp = componente_por_ref(estado, ref)
    if comp is None:
        hay = ", ".join(f"{c.get('nombre') or k} ({k})" for k, c in estado.componentes.items()) or "ninguno"
        raise ErrorOperacion(f"No encontré el componente «{ref}». Componentes: {hay}.")
    return comp


def _dep_componente(ref):
    return {ref.split(".")[0]} if isinstance(ref, str) and re.fullmatch(r"op\d+(\..*)?", ref) else set()


class OpAnclar(Operacion):
    """ENSAMBLAR › Anclar / Desanclar [Pin / Unpin]: fija el componente a la raíz como un paso del timeline. Una
    unión no puede moverlo mientras esté anclado (como uno fijo), pero se puede desanclar más adelante."""
    TIPO, ETIQUETA, ICONO = "anclar", "Anclar", "📌"
    PARAMS = {"componente": "", "anclado": True}

    def dependencias(self):
        return (super().dependencias() | _dep_componente(self.p["componente"])) - {self.id}

    def ejecutar(self, estado, ctx):
        comp = _comp_o_error(estado, self.p["componente"])
        self._usados = {comp}
        estado.componentes[comp] = dict(estado.componentes[comp], anclado=bool(self.p["anclado"]))


class OpCopiarComponente(Operacion):
    """ENSAMBLAR › Duplicar con uniones [Duplicate With Joints] — el paso «Copy Component» que deja cada instancia: un
    componente nuevo con copias de todos los cuerpos de `componente`, en la misma pose y con la misma matriz (una unión
    posterior lo lleva a su destino). Las copias son independientes: OmniCAD no tiene instancias asociativas de
    componentes. Un subensamblaje se copia entero: sus subcomponentes quedan como `<id>.s1`, `<id>.s2`… (ASM-9)."""
    TIPO, ETIQUETA, ICONO = "copiar_componente", "Copiar componente", "▣"
    PARAMS = {"componente": ""}

    def dependencias(self):
        return (super().dependencias() | _dep_componente(self.p["componente"])) - {self.id}

    def ejecutar(self, estado, ctx):
        origen = _comp_o_error(estado, self.p["componente"])
        self._usados = familia(estado, origen)
        if not any((c.componente or "") in self._usados for c in estado.cuerpos.values()):
            raise ErrorOperacion("El componente no tiene cuerpos que copiar.")
        copiar_componente(estado, origen, self.id, self.id, lambda c: c.forma.copia()
                          if getattr(c, "tipo", "solido") == "malla" else geo.transformar(c.forma, np.identity(4)))


def copiar_componente(estado, origen, nuevo, op_id, forma, padre=""):
    """Copia `origen` como el componente `nuevo` (colgado de `padre`) con copias de sus cuerpos (`forma(c)` da la forma
    copiada, creadas por el paso `op_id`) y, debajo, sus subcomponentes como `nuevo.s1`, `nuevo.s2`… (ASM-9)."""
    from .operaciones import atributos_copia
    datos = estado.componentes[origen]
    hijos = [h for h, d in estado.componentes.items() if d.get("padre") == origen]
    estado.componentes[nuevo] = {"nombre": estado.nombre_de_copia(datos.get("nombre") or origen), "padre": padre,
                                 "fijo": False, "matriz": list(datos.get("matriz", np.identity(4).tolist())),
                                 **({"origen": datos["origen"]} if "origen" in datos else {})}
    for c in [c for c in estado.cuerpos.values() if (c.componente or "") == origen]:
        cid = estado.nuevo_cuerpo(op_id, forma(c), c.tipo, nombre=estado.nombre_de_copia(c.nombre), **atributos_copia(c))
        estado.cuerpo(cid).componente = nuevo
    for n, h in enumerate(hijos, 1):
        copiar_componente(estado, h, f"{nuevo}.s{n}", op_id, forma, nuevo)


class OpPosicionInicial(Operacion):
    """ENSAMBLAR › Editar posición inicial [Edit Initial Position]: mueve y gira un componente respecto de donde se
    creó. Primero se gira (X, luego Y, luego Z) alrededor del centro de su caja envolvente y después se desplaza."""
    TIPO, ETIQUETA, ICONO = "posicion_inicial", "Posición inicial", "✥"
    PARAMS = {"componente": "", "x": "0 mm", "y": "0 mm", "z": "0 mm", "rx": "0 deg", "ry": "0 deg", "rz": "0 deg"}
    EXPRESIONES = ("x", "y", "z", "rx", "ry", "rz")

    def dependencias(self):
        return (super().dependencias() | _dep_componente(self.p["componente"])) - {self.id}

    def ejecutar(self, estado, ctx):
        for k in self.EXPRESIONES:
            exigir_numero(self.p[k])
        comp = _comp_o_error(estado, self.p["componente"])
        comps = familia(estado, comp)
        self._usados = {comp}
        cuerpos = [c for c in estado.cuerpos.values() if (c.componente or "") in comps]
        if not cuerpos:
            raise ErrorOperacion("El componente no tiene cuerpos que mover.")
        cajas = [geo.caja_envolvente(c.forma) if getattr(c, "tipo", "solido") != "malla" else c.forma.caja()
                 for c in cuerpos]
        centro = (np.min([c[0] for c in cajas], axis=0) + np.max([c[1] for c in cajas], axis=0)) / 2
        giro = (_rot(2, ctx.evaluar(self.p["rz"], ANGULO)) @ _rot(1, ctx.evaluar(self.p["ry"], ANGULO))
                @ _rot(0, ctx.evaluar(self.p["rx"], ANGULO)))
        m = _tras([ctx.evaluar(self.p[k]) for k in ("x", "y", "z")]) @ _tras(centro) @ giro @ _tras(-centro)
        _mover_componentes(estado, comps, m)


class OpCapturarPosicion(Operacion):
    """ENSAMBLAR › Posición › Capturar posición [Capture Position]: deja como posición de referencia la que tienen
    ahora los componentes (todos, o los elegidos). No mueve nada: es el punto al que vuelve «Revertir posición»."""
    TIPO, ETIQUETA, ICONO = "capturar_posicion", "Capturar posición", "◎"
    PARAMS = {"componentes": []}

    def dependencias(self):
        ids = set().union(*(_dep_componente(c) for c in self.p["componentes"])) if self.p["componentes"] else set()
        return (super().dependencias() | ids) - {self.id}

    def ejecutar(self, estado, ctx):
        comps = ([_comp_o_error(estado, c) for c in self.p["componentes"]] if self.p["componentes"]
                 else list(estado.componentes))
        if not comps:
            raise ErrorOperacion("Todavía no hay componentes en este punto del timeline: creá uno con "
                                 "ENSAMBLAR › Nuevo componente.")
        self._usados = set(comps)
        for k in _con_subcomponentes(estado, comps):
            estado.componentes[k] = dict(estado.componentes[k], captura=_matriz_de(estado, k).tolist())


class OpRevertirPosicion(Operacion):
    """ENSAMBLAR › Posición › Revertir [Revert]: devuelve los componentes (todos, o los elegidos) a su última posición
    capturada o, si nunca se capturó, a donde se modelaron."""
    TIPO, ETIQUETA, ICONO = "revertir_posicion", "Revertir posición", "↶"
    PARAMS = {"componentes": []}

    def dependencias(self):
        ids = set().union(*(_dep_componente(c) for c in self.p["componentes"])) if self.p["componentes"] else set()
        return (super().dependencias() | ids) - {self.id}

    def ejecutar(self, estado, ctx):
        comps = ([_comp_o_error(estado, c) for c in self.p["componentes"]] if self.p["componentes"]
                 else list(estado.componentes))
        if not comps:
            raise ErrorOperacion("Todavía no hay componentes en este punto del timeline: creá uno con "
                                 "ENSAMBLAR › Nuevo componente.")
        self._usados = set(comps)
        for k in _con_subcomponentes(estado, comps):        # cada uno vuelve a SU captura: el orden no importa
            meta = np.asarray(estado.componentes[k].get("captura", np.identity(4).tolist()), float)
            _mover_componentes(estado, {k}, meta @ np.linalg.inv(_matriz_de(estado, k)))


def _con_subcomponentes(estado, comps):
    """Los componentes elegidos más los que cuelgan de cada uno (capturar o revertir un padre alcanza al subensamblaje)."""
    return list(dict.fromkeys(h for k in comps for h in [k, *sorted(familia(estado, k) - {k})]))


def valores_de_estudio(estado, valores):
    """{id de unión: {movimiento: valor}} con TODOS los valores de cada unión: los pedidos en `valores` y, en las que
    siguen a un vínculo, el que sale de la otra unión."""
    uniones = estado.uniones
    efectivos = {k: dict(u["valores"], **valores.get(k, {})) for k, u in uniones.items()}
    for _ in range(len(uniones)):                       # los vínculos encadenados se resuelven en orden
        for k, u in uniones.items():
            v = u.get("vinculo")
            if v and (k not in valores or v["union1"] == k) and v["union1"] in efectivos:
                efectivos[k][v["clave2"]] = efectivos[v["union1"]].get(v["clave1"], 0.0) * v["factor"]
    return efectivos


def poses_de_estudio(estado, valores, libres=None):
    """Estudio de movimiento: {id de cuerpo: matriz 4x4} para ver las uniones con otros valores SIN recalcular.
    `valores` = {id de unión: {movimiento: valor}} (grados o mm; lo que falte se queda como está). Una unión que
    sigue a un vínculo toma su valor de la otra. Cada unión mueve los cuerpos de sus componentes y también los de las
    uniones que cuelgan de ellos (su componente 2 es uno de los que mueve). `libres` = {componente: [x, y, z]}: lo que
    se desplazan los componentes que ninguna unión mueve, y con ellos lo que cuelga."""
    libres = libres or {}
    uniones = estado.uniones
    efectivos = valores_de_estudio(estado, valores)
    delta = {}
    for k, u in uniones.items():
        F = np.asarray(u["marco"], float)
        eje = (u["eje_giro"], u["eje_desliz"])
        delta[k] = F @ movimiento(u["tipo"], efectivos[k], *eje) @ np.linalg.inv(
            movimiento(u["tipo"], u["valores"], *eje)) @ np.linalg.inv(F)
    quien_mueve = {}                                           # componente -> la última unión que lo mueve
    for k, u in uniones.items():
        for comp in u["componentes"]:
            quien_mueve[comp] = k
    for comp, d in estado.componentes.items():    # ASM-9: un subcomponente creado después de la unión sigue a su padre
        padre, vistos = d.get("padre") or "", set()
        while comp not in quien_mueve and padre and padre not in vistos:
            vistos.add(padre)
            if padre in quien_mueve:
                quien_mueve[comp] = quien_mueve[padre]
            padre = estado.componentes.get(padre, {}).get("padre") or ""

    def total(k, vistos=()):
        padre = quien_mueve.get(uniones[k]["comp2"])
        if padre is None or padre == k or padre in vistos:
            return _tras(libres.get(uniones[k]["comp2"], (0.0, 0.0, 0.0))) @ delta[k]
        return total(padre, (*vistos, k)) @ delta[k]

    poses = {cid: _tras(libres[c.componente]) for cid, c in estado.cuerpos.items() if c.componente in libres}
    poses.update({cid: total(quien_mueve[c.componente]) for cid, c in estado.cuerpos.items()
                  if c.componente in quien_mueve})
    return poses


class OpInsertarDiseno(Operacion):
    """INSERTAR › Insertar componente / derivación [ASM-INSERT-FUSION-DESIGN]: los cuerpos finales de otro
    diseño (.omnicad) entran como un componente nuevo. La receta se guarda adentro (copia independiente). `fijo`
    como en `OpComponente` (Fijar)."""
    TIPO, ETIQUETA, ICONO = "insertar_diseno", "Insertar diseño", "⇩"
    PARAMS = {"archivo": "", "receta": None, "fijo": False}

    def ejecutar(self, estado, ctx):
        from .documento import Documento
        if not self.p["receta"]:
            raise ErrorOperacion("La inserción no tiene el diseño.")
        otro = Documento.desde_dict(self.p["receta"])
        estado.componentes[self.id] = {"nombre": self.p["archivo"] or self.nombre, "padre": "",
                                       "fijo": bool(self.p.get("fijo")), "matriz": np.identity(4).tolist()}
        for c in otro.estado_final.cuerpos.values():
            estado.nuevo_cuerpo(self.id, c.forma, c.tipo, nombre=c.nombre, apariencia=c.apariencia,
                                material=c.material, componente=self.id)


def _rotar_a(a, b, centro):
    """Matriz 4x4 que gira alrededor de `centro` lo mínimo para llevar la dirección `a` a `b` (180° si son opuestas)."""
    a, b = _unit(a), _unit(b)
    eje = np.cross(a, b)
    s, c = float(np.linalg.norm(eje)), float(a @ b)
    if s < 1e-9:
        if c > 0:
            return np.identity(4)
        eje, s, c = _unit(np.cross(a, (1.0, 0, 0) if abs(a[0]) < 0.9 else (0, 1.0, 0))), 0.0, -1.0
    return _giro_eje(eje / (s or 1.0), math.atan2(s, c), centro)


def _giro_eje(k, alfa, centro):
    """Matriz 4x4 que gira `alfa` rad (regla de la mano derecha) alrededor del eje unitario `k` por `centro`."""
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    r = np.identity(4)
    r[:3, :3] = np.identity(3) + math.sin(alfa) * K + (1 - math.cos(alfa)) * (K @ K)
    return _tras(centro) @ r @ _tras(-np.asarray(centro, float))


def _clase_de_alinear(e):
    """«plano», «eje» o «punto»: qué geometría es para Alinear (cara plana o plano; cara cilíndrica o cónica, arista y eje;
    vértice y punto)."""
    if e.tipo == "plano" or (e.tipo == "cara" and e.plano is not None):
        return "plano"
    if e.tipo == "eje" or (e.tipo == "cara" and "eje" in refs.firma_cara(e.forma)) or e.tipo in ("arista", "curva_boceto"):
        return "eje"
    if e.tipo in ("vertice", "punto", "punto_boceto") and e.punto is not None:
        return "punto"
    raise ErrorOperacion("Alinear: elegí una cara, una arista, un vértice, un plano, un eje o un punto.")


def _alinear(e1, e2, desfase, voltear):
    """Movimiento (4x4, mundo) que lleva la geometría `e1` a estar alineada con `e2` (ASM-17 › Alinear de Constrain
    Components): dos planos quedan coplanares a `desfase` mm, con la orientación que menos los gira (al ras si miran
    hacia el mismo lado, enfrentados si miran opuesto: «la orientación sale de la combinación de geometrías»; «Voltear»
    la invierte); dos ejes (cilindro, arista circular o recta, eje) quedan concéntricos o colineales, y dos aristas circulares
    también centro con centro; dos puntos coinciden."""
    c1, c2 = _clase_de_alinear(e1), _clase_de_alinear(e2)
    F1, _ = _marco(e1, "centro", 2)
    F2, _ = _marco(e2, "centro", 2)
    o1, o2 = F1[:3, 3], F2[:3, 3]
    if c1 == c2 == "punto":
        if abs(desfase) > 1e-12:
            raise ErrorOperacion("Alinear: el desfase no se aplica a dos puntos.")
        return _tras(o2 - o1)
    if c1 != c2 or c1 == "punto":
        raise ErrorOperacion(f"Alinear: la combinación {c1}–{c2} todavía no está. Hoy: cara-cara, eje-eje y punto-punto.")
    n2 = _unit(F2[:3, 2])
    sentido = (-1.0 if float(F1[:3, 2] @ n2) < 0 else 1.0) * (-1.0 if voltear else 1.0)
    giro = _rotar_a(F1[:3, 2], sentido * n2, o1)
    if c1 == "plano":
        return _tras(n2 * (float((o2 - o1) @ n2) + desfase)) @ giro
    w = o2 - o1
    ambas_circulares = all(e.tipo in ("arista", "curva_boceto") and refs.firma_arista(e.forma)["geom"] == "circulo"
                           for e in (e1, e2))
    paso = w if ambas_circulares else w - float(w @ n2) * n2
    return _tras(paso + n2 * desfase) @ giro


def _marco_plano(e, e_b, version=2):
    """Marco del plano de referencia de Centro: el de la cara o plano `e` (modo simple) o el plano medio entre `e` y
    `e_b` (modo «entre dos caras»)."""
    if e_b is not None:
        return _marco_entre_caras(e, e_b, version)
    if _clase_de_alinear(e) != "plano":
        raise ErrorOperacion("Centro: elegí caras planas o planos.")
    return _marco(e, "centro", version)[0]


def _centrar(F1, F2, voltear):
    """Movimiento (4x4, mundo) que deja el plano de `F1` coplanar con el de `F2` (ASM-17 › Centro de Constrain Components:
    una cara, o el plano medio de dos, queda a medio camino de las dos caras del otro componente). Como Alinear de dos
    planos, con la orientación que menos gira; «Voltear» la invierte. No desliza en el plano."""
    o1, o2, n2 = F1[:3, 3], F2[:3, 3], _unit(F2[:3, 2])
    sentido = (-1.0 if float(F1[:3, 2] @ n2) < 0 else 1.0) * (-1.0 if voltear else 1.0)
    return _tras(n2 * float((o2 - o1) @ n2)) @ _rotar_a(F1[:3, 2], sentido * n2, o1)


def _direccion_de(e):
    """Dirección unitaria de la geometría para Ángulo: la normal de un plano o cara plana, o el eje de un cilindro, una
    arista o un eje de construcción."""
    if _clase_de_alinear(e) == "punto":
        raise ErrorOperacion("Ángulo: un punto no tiene dirección; elegí una cara, una arista o un eje.")
    return _unit(_marco(e, "centro", 2)[0][:3, 2])


def _angular(e1, e2, grados, voltear, e_ref=None):
    """Giro (4x4, mundo, por el centro de la geometría 1) que deja el ángulo entre las direcciones de `e1` y `e2` en
    `grados` (ASM-17 › Ángulo de Constrain Components): entre planos, el de sus normales. Sin referencia gira por el
    camino más corto y el ángulo va de 0 a 180°. Con `e_ref` (arista o eje, «Angle Reference») el ángulo es con signo,
    medido alrededor de ese eje, y no queda ambiguo. «Voltear» da vuelta la geometría 1."""
    d1, d2 = _direccion_de(e1) * (-1.0 if voltear else 1.0), _direccion_de(e2)
    o1 = _marco(e1, "centro", 2)[0][:3, 3]
    if e_ref is None:
        phi = math.acos(max(-1.0, min(1.0, float(d1 @ d2))))
        k = np.cross(d1, d2)
        if np.linalg.norm(k) < 1e-9:
            k = np.cross(d1, (1.0, 0, 0) if abs(d1[0]) < 0.9 else (0, 1.0, 0))
        return _giro_eje(_unit(k), phi - math.radians(grados), o1)
    a = _direccion_de(e_ref)
    p1, p2 = d1 - a * float(d1 @ a), d2 - a * float(d2 @ a)
    if np.linalg.norm(p1) < 1e-9 or np.linalg.norm(p2) < 1e-9:
        raise ErrorOperacion("Ángulo: la referencia es paralela a una de las geometrías; elegí otra arista o eje de referencia.")
    psi = math.atan2(float(a @ np.cross(p2, p1)), float(p2 @ p1))
    return _giro_eje(a, math.radians(grados) - psi, o1)


class OpRestriccion(Operacion):
    """ENSAMBLAR › Restricción de componentes [ASM-17, Constrain Components]: de los cuatro tipos de Fusion hoy están
    Alinear, Ángulo y Centro. Mueve el componente de `ref1` respecto de `ref2` (si el primero está fijo o es la raíz, se mueve
    el segundo: «Component 2 moves to Component 1»). `desfase` es la distancia (Alinear) o el ángulo (Ángulo, con
    `ref_angulo` opcional: la arista o el eje que fija el sentido). Centro: `modo1`/`modo2` son «simple» (la cara `ref1`/`ref2`)
    o «entre_caras» (con la segunda cara `ref1b`/`ref2b`); al menos uno es «entre_caras». Lo que falta de Fusion: Tangente, filas de
    varias restricciones (conjuntos), límites de desfase y resolver todas a la vez."""
    TIPO, ETIQUETA, ICONO = "restriccion", "Restricción", "⛓"
    PARAMS = {"tipo": "alinear", "ref1": None, "ref2": None, "desfase": "0 mm", "voltear": False, "ref_angulo": None,
              "modo1": "simple", "modo2": "simple", "ref1b": None, "ref2b": None}
    EXPRESIONES = ("desfase",)
    OPCIONES = {"tipo": {"alinear": "Alinear", "angulo": "Ángulo", "centro": "Centro"},
                "modo1": {"simple": "Simple", "entre_caras": "Entre dos caras"},
                "modo2": {"simple": "Simple", "entre_caras": "Entre dos caras"}}

    def dependencias(self):
        return (super().dependencias() | ent.dependencias_de(self.p["ref1"], self.p["ref2"], self.p.get("ref_angulo"),
                                                                 self.p.get("ref1b"), self.p.get("ref2b"))) - {self.id}

    def ejecutar(self, estado, ctx):
        p = self.p
        if p["tipo"] not in ("alinear", "angulo", "centro"):
            raise ErrorOperacion(f"La restricción «{p['tipo']}» todavía no está: hoy Alinear, Ángulo y Centro.")
        if not p["ref1"] or not p["ref2"]:
            raise ErrorOperacion("Elegí la geometría de los dos componentes.")
        exigir_numero(p["desfase"])
        e1, e2 = _resolver(p["ref1"], estado), _resolver(p["ref2"], estado)
        c1, c2 = _componente_de(estado, e1) or "", _componente_de(estado, e2) or ""
        invertido = False
        if c1 == c2:
            raise ErrorOperacion("Las dos selecciones están en el mismo componente: elegí geometría de otro componente.")
        e1b = e2b = None
        if p["tipo"] == "centro":
            e1b, e2b = self._segundas_caras(estado, e1, e2, c1, c2)
        if not c1 or es_fijo(estado, c1):                   # «Component 2 moves to Component 1»
            if not c2 or es_fijo(estado, c2):
                raise ErrorOperacion("Los dos componentes están fijos o son la raíz: ninguno se puede mover.")
            e1, e2, c1, c2, e1b, e2b = e2, e1, c2, c1, e2b, e1b
            invertido = True
        comps = grupo_rigido(estado, c1)
        fijos = [c for c in comps if es_fijo(estado, c)]
        if fijos:
            nombre = estado.componentes[fijos[0]].get("nombre") or fijos[0]
            raise ErrorOperacion(f"El componente a mover está en un grupo rígido con «{nombre}», que está fijo.")
        self._usados = (comps | {c2}) - {"", self.id}
        if p["tipo"] == "alinear":
            m = _alinear(e1, e2, ctx.evaluar(p["desfase"]), bool(p["voltear"]))
        elif p["tipo"] == "centro":
            m = _centrar(_marco_plano(e1, e1b), _marco_plano(e2, e2b), bool(p["voltear"]))
        else:
            e_ref = _resolver(p["ref_angulo"], estado) if p.get("ref_angulo") else None
            grados = ctx.evaluar(p["desfase"], ANGULO)
            m = _angular(e1, e2, -grados if invertido and e_ref is not None else grados, bool(p["voltear"]), e_ref)
        _mover_componentes(estado, comps, m)

    def _segundas_caras(self, estado, e1, e2, c1, c2):
        """(e1b, e2b) de Centro: la segunda cara de cada componente que está en «entre_caras» (None si es «simple»).
        Fusion exige «Entre dos caras» en al menos uno."""
        p, salida = self.p, []
        for n, e, c in (("1", e1, c1), ("2", e2, c2)):
            modo = p.get("modo" + n) or "simple"
            if modo not in ("simple", "entre_caras"):
                raise ErrorOperacion(f"Centro: modo de posición desconocido «{modo}». Modos: simple, entre_caras.")
            if modo == "simple":
                salida.append(None)
                continue
            if not p.get("ref" + n + "b"):
                raise ErrorOperacion(f"Centro: el componente {n} está en «Entre dos caras»: elegí su segunda cara.")
            eb = _resolver(p["ref" + n + "b"], estado)
            if (_componente_de(estado, eb) or "") != c:
                raise ErrorOperacion(f"Centro: las dos caras del componente {n} tienen que ser del mismo componente.")
            salida.append(eb)
        if salida == [None, None]:
            raise ErrorOperacion("Centro: al menos un componente tiene que estar en «Entre dos caras» (centra entre dos caras del otro).")
        return salida


registrar_operacion(OpComponente, OpUnion, OpOrigenUnion, OpGrupoRigido, OpVinculoMovimiento, OpAnclar,
                    OpPosicionInicial, OpCapturarPosicion, OpRevertirPosicion, OpInsertarDiseno, OpCopiarComponente, OpRestriccion)
