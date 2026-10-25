# -*- coding: utf-8 -*-
"""
Reconocer funciones [Create > Find Features de Fusion]: recorre un cuerpo sin historial (importado) y encuentra las
funciones que lo forman. Solo lee la geometría: devuelve lo encontrado con las caras de cada función y sus medidas (la
herramienta de la API las numera como find_faces; `rebuild_features` rehace en el timeline los agujeros, empalmes y
chaflanes con estas medidas).

Agujeros: caras cilíndricas cóncavas coaxiales y del mismo radio que juntas dan la vuelta completa (más su fondo plano si
es ciego); si hay otro agujero coaxial pegado de otro diámetro es un avellanado (counterbore). Pasante si más allá de los
dos extremos, junto a la pared, hay aire. Empalmes: caras cilíndricas, toroidales o esféricas que no son agujeros y
empalman con sus vecinas (tangentes) por al menos una arista; el radio es el de la superficie. Chaflanes: caras planas
angostas entre dos caras planas distintas, con el mismo ángulo contra cada vecina (entre 20° y 70°) y angostas respecto
de ellas.
Extrusión: TODO el cuerpo es un prisma (dos tapas planas iguales y el resto de las caras paralelas a la dirección).
Revolución: TODAS las caras son de revolución alrededor de un mismo eje (planos perpendiculares a él, cilindros, conos,
toros y superficies de revolución coaxiales, esferas centradas en él). Simetría y patrones: grupos de agujeros, empalmes
o chaflanes iguales cuyos centros forman una rejilla equiespaciada (rectangular), un círculo equiespaciado (circular) o
se reflejan en un plano X, Y o Z que pasa por el centro de la caja del cuerpo (simetría).
"""
import math

import numpy as np

from . import geometria as geo

TOL_TANGENTE = math.radians(1.0)           # dos caras vecinas con menos que esto entre sus normales son tangentes
ANCHO_CHAFLAN_MAX = 0.3                    # ancho de la cara del chaflán / ancho de sus vecinas (aprox.)
TIPOS = ("hole", "fillet", "chamfer", "extrude", "revolve", "mirror", "circular_pattern", "rectangular_pattern")
_PATRONES = ("mirror", "circular_pattern", "rectangular_pattern")


def _superficie(cara):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopoDS import TopoDS
    return BRepAdaptor_Surface(TopoDS.Face(cara))


def _normal_y_punto(cara):
    from . import solidos_modificar as sm
    return sm._punto_normal(cara)


def _vec(d):
    return np.array([d.X(), d.Y(), d.Z()], float)


def _r(v):
    return [round(float(x), 6) + 0.0 for x in v]


def _cilindro(cara):
    """(punto del eje, dirección del eje, radio, ángulo recorrido, largo) de una cara cilíndrica; None si no lo es."""
    from OCP.BRepTools import BRepTools
    from OCP.GeomAbs import GeomAbs_Cylinder
    s = _superficie(cara)
    if s.GetType() != GeomAbs_Cylinder:
        return None
    c = s.Cylinder()
    ax = c.Axis()
    o, d = _vec(ax.Location()), _vec(ax.Direction())
    u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
    return o + d * v0, d, c.Radius(), u1 - u0, v1 - v0


def _concava(cara, base, eje):
    """¿La normal exterior de la cara apunta hacia el eje (la cara es la pared de un agujero)?"""
    p, n = _normal_y_punto(cara)
    radial = (p - base) - eje * float((p - base) @ eje)
    return float(n @ radial) < 0


def _hay_aire(forma, punto):
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_OUT
    return BRepClass3d_SolidClassifier(forma, gp_Pnt(*map(float, punto)), 1e-6).State() == TopAbs_OUT


def _perpendicular(eje):
    v = np.cross(eje, [1.0, 0, 0] if abs(eje[0]) < 0.9 else [0, 1.0, 0])
    return v / np.linalg.norm(v)


def _abierto(forma, extremo, eje, sentido, radio):
    """¿Hay aire más allá del extremo junto a la pared? (Sobre el eje no: ahí puede seguir otro agujero coaxial.)"""
    return _hay_aire(forma, extremo + eje * sentido * 1e-3 + _perpendicular(eje) * radio * (1 - 1e-3))


def _indice(caras, f):
    return next(i for i, c in enumerate(caras, 1) if c.IsSame(f))


def _fondo(caras, indices, punto, eje, vecinas):
    """Caras planas vecinas de las paredes, perpendiculares al eje y en el plano del fondo del agujero."""
    from OCP.GeomAbs import GeomAbs_Plane
    from . import solidos_modificar as sm
    salida = []
    for i in indices:
        for e in sm._aristas(caras[i - 1]):
            for f in sm._padres(vecinas, e):
                k = _indice(caras, f)
                if k in indices or k in salida or _superficie(f).GetType() != GeomAbs_Plane:
                    continue
                p, n = _normal_y_punto(caras[k - 1])
                if abs(abs(float(n @ eje)) - 1) < 1e-9 and abs(float((p - punto) @ eje)) < 1e-6:
                    salida.append(k)
    return salida


def _agujeros(forma, caras):
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from . import solidos_modificar as sm
    vecinas = sm._ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    grupos = []                                                    # cilindros cóncavos coaxiales del mismo radio
    for i, cara in enumerate(caras, 1):
        c = _cilindro(cara)
        if c is None or not _concava(cara, c[0], c[1]):
            continue
        base, eje, radio, angulo, largo = c
        for g in grupos:
            if (abs(g["radio"] - radio) < 1e-6 and abs(abs(float(g["eje"] @ eje)) - 1) < 1e-9
                    and np.linalg.norm(np.cross(g["eje"], base - g["base"])) < 1e-6):
                g["caras"].append(i)
                g["angulo"] += angulo
                g["largo"] = max(g["largo"], largo)
                break
        else:
            grupos.append({"caras": [i], "radio": radio, "eje": eje, "base": base, "angulo": angulo, "largo": largo})
    salida = []
    for g in grupos:
        if g["angulo"] < 2 * math.pi - 1e-3:
            continue                                               # una ranura o una media caña, no un agujero
        eje, r = g["eje"], g["radio"]
        a, b = g["base"], g["base"] + eje * g["largo"]
        abre_a, abre_b = _abierto(forma, a, eje, -1, r), _abierto(forma, b, eje, 1, r)
        entrada = a if abre_a else b if abre_b else None
        fondo = [] if abre_a == abre_b else _fondo(caras, g["caras"], b if abre_a else a, eje, vecinas)
        salida.append({"type": "hole", "faces": g["caras"] + fondo, "diameter": round(2 * r, 6),
                       "depth": round(g["largo"], 6), "axis_point": _r(a), "axis": _r(eje),
                       "through": abre_a and abre_b, "entry_point": None if entrada is None else _r(entrada)})
    # avellanado: dos agujeros coaxiales de distinto diámetro, uno a continuación del otro
    for i, h in enumerate(salida):
        for k in range(i + 1, len(salida)):
            o = salida[k]
            if (abs(abs(np.dot(h["axis"], o["axis"])) - 1) < 1e-9
                    and np.linalg.norm(np.cross(h["axis"], np.subtract(h["axis_point"], o["axis_point"]))) < 1e-6
                    and abs(h["diameter"] - o["diameter"]) > 1e-6):
                h["counterbore_with"] = k
                o["counterbore_with"] = i
    return salida


def _empalmes(forma, caras):
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Sphere, GeomAbs_Torus
    from . import solidos_modificar as sm
    vecinas = sm._ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    salida = []
    for i, cara in enumerate(caras, 1):
        s = _superficie(cara)
        tipo = s.GetType()
        if tipo == GeomAbs_Cylinder:
            c = _cilindro(cara)
            if _concava(cara, c[0], c[1]) and c[3] >= 2 * math.pi - 1e-3:
                continue                                           # pared completa de un agujero (de afuera o de adentro)
            radio, convexo = c[2], not _concava(cara, c[0], c[1])
        elif tipo == GeomAbs_Torus:
            radio = s.Torus().MinorRadius()
            convexo = None
        elif tipo == GeomAbs_Sphere:
            radio, convexo = s.Sphere().Radius(), None
        else:
            continue
        tangentes = 0
        for e in sm._aristas(cara):
            try:
                if len(sm._padres(vecinas, e)) == 2 and sm._angulo_entre_caras(forma, e) < TOL_TANGENTE:
                    tangentes += 1
            except geo.ErrorGeometria:
                continue
        if tangentes:
            salida.append({"type": "fillet", "faces": [i], "radius": round(float(radio), 6),
                           "convex": convexo if convexo is None else bool(convexo), "tangent_edges": tangentes,
                           "center": _r(_normal_y_punto(cara)[0])})
    return salida


def _largo_recto(arista):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    c = BRepAdaptor_Curve(arista)
    return abs(c.LastParameter() - c.FirstParameter())


def _chaflanes(forma, caras):
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from . import solidos_modificar as sm
    vecinas = sm._ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    salida = []
    for i, cara in enumerate(caras, 1):
        if _superficie(cara).GetType() != GeomAbs_Plane:
            continue
        bordes = []                                                # (quiebre en grados, arista, ancho de la vecina)
        for e in sm._aristas(cara):
            otros = [f for f in sm._padres(vecinas, e) if not f.IsSame(cara)]
            largo = _largo_recto(e)
            if len(otros) != 1 or _superficie(otros[0]).GetType() != GeomAbs_Plane or largo < 1e-9:
                continue
            try:
                quiebre = math.degrees(sm._angulo_entre_caras(forma, e))
            except geo.ErrorGeometria:
                continue
            if 20 <= quiebre <= 70:
                bordes.append((quiebre, e, geo.area(otros[0]) / largo))
        for k, (q1, e1, w1) in enumerate(bordes):                  # dos aristas con el mismo quiebre: las largas del chaflán
            par = next((b2 for b2 in bordes[k + 1:] if abs(b2[0] - q1) <= 5), None)
            if par is None:
                continue
            ancho = geo.area(cara) / ((_largo_recto(e1) + _largo_recto(par[1])) / 2)      # trapecio en las esquinas
            if ancho <= ANCHO_CHAFLAN_MAX * min(w1, par[2]):
                salida.append({"type": "chamfer", "faces": [i], "width": round(float(ancho), 6), "angle": round(q1, 4),
                               # chaflán simétrico: la cara es la base de un isósceles de lados `distance`
                               "distance": round(float(ancho / (2 * math.cos(math.radians(q1)))), 6),
                               "center": _r(_normal_y_punto(cara)[0])})
                break
    return _cadenas(forma, caras, salida, vecinas)


def _cadenas(forma, caras, chaflanes, vecinas):
    """Chaflanes unidos por caras cónicas tangentes (alrededor de una esquina redondeada) son UNA función."""
    from OCP.GeomAbs import GeomAbs_Cone
    from . import solidos_modificar as sm
    planos = {f["faces"][0]: f for f in chaflanes}
    vistos, salida = set(), []
    for i, f in planos.items():
        if i in vistos:
            continue
        grupo, pila = [], [i]
        while pila:
            k = pila.pop()
            if k in vistos:
                continue
            vistos.add(k)
            grupo.append(k)
            for e in sm._aristas(caras[k - 1]):
                for g in sm._padres(vecinas, e):
                    j = _indice(caras, g)
                    if j in vistos or not (j in planos or _superficie(g).GetType() == GeomAbs_Cone):
                        continue
                    try:
                        if sm._angulo_entre_caras(forma, e) < TOL_TANGENTE:
                            pila.append(j)
                    except geo.ErrorGeometria:
                        continue
        salida.append(dict(f, faces=sorted(grupo)))
    return salida


# ---------------------------------------------------------------- extrusión y revolución (el cuerpo entero)
def _paralelo(a, b):
    return abs(abs(float(a @ b)) - 1) < 1e-9


def _extrusion(forma, caras):
    from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_SurfaceOfExtrusion
    info = []                                                      # (plano?, normal o dirección, punto)
    for cara in caras:
        s = _superficie(cara)
        t = s.GetType()
        if t == GeomAbs_Plane:
            p, n = _normal_y_punto(cara)
            info.append((True, n, p))
        elif t == GeomAbs_Cylinder:
            info.append((False, _vec(s.Cylinder().Axis().Direction()), None))
        elif t == GeomAbs_SurfaceOfExtrusion:
            info.append((False, _vec(s.Direction()), None))
        else:
            return []
    candidatas = []
    for plano, n, _p in info:
        if plano and not any(_paralelo(n, c) for c in candidatas):
            candidatas.append(n)
    volumen = abs(geo.volumen(forma))
    for d in candidatas:
        tapas = [i for i, (plano, n, _p) in enumerate(info) if plano and _paralelo(n, d)]
        if len(tapas) != 2 or not all(abs(float(n @ d)) < 1e-9 if plano else _paralelo(n, d)
                                      for i, (plano, n, _p) in enumerate(info) if i not in tapas):
            continue
        a0, a1 = geo.area(caras[tapas[0]]), geo.area(caras[tapas[1]])
        largo = float((info[tapas[1]][2] - info[tapas[0]][2]) @ d)
        if abs(a0 - a1) > 1e-6 * a0 or abs(volumen - a0 * abs(largo)) > 1e-3 * volumen:
            continue
        return [{"type": "extrude", "faces": [tapas[0] + 1, tapas[1] + 1], "direction": _r(d if largo > 0 else -d),
                 "distance": round(abs(largo), 6), "profile_area": round(a0, 6)}]
    return []


def _ejes(cara):
    """('eje', punto, dirección), ('centro', punto, None) o ('plano', punto, normal) de la superficie; None si no es de
    revolución alrededor de nada."""
    from OCP.GeomAbs import (GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Sphere,
                             GeomAbs_SurfaceOfRevolution, GeomAbs_Torus)
    s = _superficie(cara)
    t = s.GetType()
    ejes = {GeomAbs_Cylinder: lambda: s.Cylinder().Axis(), GeomAbs_Cone: lambda: s.Cone().Axis(),
            GeomAbs_Torus: lambda: s.Torus().Axis(), GeomAbs_SurfaceOfRevolution: s.AxeOfRevolution}
    if t in ejes:
        ax = ejes[t]()
        return "eje", _vec(ax.Location()), _vec(ax.Direction())
    if t == GeomAbs_Sphere:
        return "centro", _vec(s.Sphere().Location()), None
    if t == GeomAbs_Plane:
        p, n = _normal_y_punto(cara)
        return "plano", p, n
    return None


def _revolucion(forma, caras):
    datos = [_ejes(c) for c in caras]
    if any(d is None for d in datos):
        return []
    eje = next(((p, d) for t, p, d in datos if t == "eje"), None)
    if eje is None:
        return []
    o, d = eje
    def sobre_eje(p):
        return np.linalg.norm(np.cross(d, p - o)) < 1e-6

    laterales = []                                                 # planos que contienen el eje: revolución parcial
    for i, (t, p, v) in enumerate(datos):
        if (t == "eje" and not (_paralelo(v, d) and sobre_eje(p))) or (t == "centro" and not sobre_eje(p)):
            return []
        if t == "plano" and not _paralelo(v, d):
            if abs(float(v @ d)) > 1e-9 or abs(float((p - o) @ v)) > 1e-6:
                return []
            laterales.append(i)
    if len(laterales) not in (0, 2):
        return []
    angulo = 360.0
    if laterales:
        def radial(p):
            r = (p - o) - d * float((p - o) @ d)
            return r / np.linalg.norm(r)
        r1, r2 = (radial(datos[i][1]) for i in laterales)
        angulo = math.degrees(math.acos(float(np.clip(r1 @ r2, -1, 1))))
        c = np.array(geo.centro_masa(forma))
        if float(radial(c) @ (r1 + r2)) < 0:                       # el cuerpo queda del lado de afuera de la bisectriz
            angulo = 360.0 - angulo
    return [{"type": "revolve", "faces": [i + 1 for i in laterales], "axis_point": _r(o), "axis": _r(d),
             "angle": round(angulo, 4)}]


# ---------------------------------------------------------------- simetría y patrones (grupos de funciones iguales)
def _firma(f):
    if f["type"] == "hole":
        return ("hole", round(f["diameter"], 4), round(f["depth"], 4), f["through"],
                tuple(round(abs(x), 4) for x in f["axis"]))
    if f["type"] == "fillet":
        return ("fillet", round(f["radius"], 4), f["convex"])
    return ("chamfer", round(f["width"], 4), round(f["angle"], 1))


def _centro(f):
    if f["type"] == "hole":                                        # el medio del eje: no depende del sentido del cilindro
        return np.array(f["axis_point"]) + np.array(f["axis"]) * f["depth"] / 2
    return np.array(f["center"])


def _equiespaciados(valores, tol):
    pasos = np.diff(sorted(valores))
    return len(pasos) > 0 and pasos.min() > tol and pasos.max() - pasos.min() < tol


def _unicos(valores, tol):
    salida = []
    for v in sorted(valores):
        if not salida or v - salida[-1] > tol:
            salida.append(v)
    return salida


def _rejilla(P, tol):
    """Direcciones [(dirección, cantidad, paso)] si los puntos forman una rejilla equiespaciada de 1 o 2 direcciones."""
    dirs = []
    for q in P[1:]:
        v = q - P[0]
        u = v / np.linalg.norm(v)
        if not any(_paralelo(u, w) for w in dirs):
            dirs.append(u)
    if len(dirs) == 1:
        s = [float((q - P[0]) @ dirs[0]) for q in P]
        if len(P) >= 3 and _equiespaciados(s, tol):
            return [(dirs[0], len(P), np.diff(sorted(s))[0])]
        return None
    for u in dirs:
        for v in dirs:
            if _paralelo(u, v):
                continue
            base = np.stack([u, v], 1)
            st, *_ = np.linalg.lstsq(base, (P - P[0]).T, rcond=None)
            if np.abs(base @ st - (P - P[0]).T).max() > tol:
                return None                                        # no son coplanares
            s, t = _unicos(st[0], tol), _unicos(st[1], tol)
            if (len(s) * len(t) == len(P) and len(s) >= 2 and len(t) >= 2
                    and (len(s) == 2 or _equiespaciados(s, tol)) and (len(t) == 2 or _equiespaciados(t, tol))):
                return [(u, len(s), s[1] - s[0]), (v, len(t), t[1] - t[0])]
    return None


def _circulo(P, tol):
    """(centro, normal, paso en grados) si los puntos están equiespaciados sobre un círculo (vuelta completa)."""
    c = P.mean(0)
    _u, sv, vt = np.linalg.svd(P - c)
    n = vt[2]
    radios = np.linalg.norm(P - c, axis=1)
    if len(P) < 3 or sv[2] > tol or radios.max() - radios.min() > tol or radios.min() < tol:
        return None
    e1 = (P[0] - c) / radios[0]
    e2 = np.cross(n, e1)
    angulos = sorted(math.atan2(float((p - c) @ e2), float((p - c) @ e1)) % (2 * math.pi) for p in P)
    pasos = np.diff(angulos + [angulos[0] + 2 * math.pi])
    if pasos.max() - pasos.min() > 1e-4:
        return None
    return c, n, math.degrees(pasos[0])


def _espejo(P, centro, tol):
    """Normal (X, Y o Z) del plano por `centro` que refleja los puntos entre sí (ninguno sobre el plano)."""
    for n in np.eye(3):
        d = (P - centro) @ n
        if np.abs(d).min() < tol:
            continue
        reflejados = P - 2 * np.outer(d, n)
        if all(np.linalg.norm(P - q, axis=1).min() < tol for q in reflejados):
            return n
    return None


def _patrones(forma, funciones, tipos):
    grupos = {}
    for f in funciones:
        grupos.setdefault(_firma(f), []).append(f)
    bb = geo.caja_envolvente(forma)
    centro = (np.array(bb[0]) + np.array(bb[1])) / 2
    tol = 1e-6 * max(1.0, float(np.linalg.norm(np.subtract(bb[1], bb[0]))))
    salida = []
    for (tipo, *_), miembros in grupos.items():
        if len(miembros) < 2:
            continue
        P = np.array([_centro(f) for f in miembros])
        comun = {"feature": tipo, "count": len(miembros), "faces": sorted(i for f in miembros for i in f["faces"]),
                 "centers": [_r(p) for p in P]}
        rejilla = _rejilla(P, tol)
        circulo = None if rejilla else _circulo(P, tol)
        normal = None if rejilla or circulo else _espejo(P, centro, tol)
        if rejilla and "rectangular_pattern" in tipos:
            salida.append(dict(comun, type="rectangular_pattern",
                               directions=[{"direction": _r(u), "count": k, "step": round(float(p), 6)}
                                           for u, k, p in rejilla]))
        elif circulo and "circular_pattern" in tipos:
            c, n, paso = circulo
            salida.append(dict(comun, type="circular_pattern", axis_point=_r(c), axis=_r(n), angle_step=round(paso, 4)))
        elif normal is not None and "mirror" in tipos:
            salida.append(dict(comun, type="mirror", plane_point=_r(centro), plane_normal=_r(normal)))
    return salida


def reconocer_funciones(forma, tipos=TIPOS):
    """Funciones que forman `forma` (un sólido sin historial): {"faces": n, "face_shapes": [...], "features": [...]}."""
    from OCP.TopAbs import TopAbs_FACE
    from . import solidos_modificar as sm
    desconocidos = set(tipos) - set(TIPOS)
    if desconocidos:
        raise geo.ErrorGeometria(f"Tipo de función desconocido: {', '.join(sorted(desconocidos))}")
    caras = [sm.TopoDS.Face(c) for c in sm._unicos(forma, TopAbs_FACE)]
    if not caras:
        raise geo.ErrorGeometria("El cuerpo no tiene caras.")
    patrones = bool(set(tipos) & set(_PATRONES))
    locales = {"hole": _agujeros, "fillet": _empalmes, "chamfer": _chaflanes}
    halladas = {t: f(forma, caras) for t, f in locales.items() if t in tipos or patrones}
    funciones = [f for t, fs in halladas.items() if t in tipos for f in fs]
    if "extrude" in tipos:
        funciones += _extrusion(forma, caras)
    if "revolve" in tipos:
        funciones += _revolucion(forma, caras)
    if patrones:
        funciones += _patrones(forma, [f for fs in halladas.values() for f in fs], tipos)
    return {"faces": len(caras), "face_shapes": caras, "features": funciones}
