# -*- coding: utf-8 -*-
"""
Reconocer funciones [Create > Find Features de Fusion]: recorre un cuerpo sin historial (importado) y encuentra los
agujeros, los empalmes y los chaflanes que lo forman. Solo lee la geometría: devuelve lo encontrado con las caras de cada
función y sus medidas (la herramienta de la API las numera como find_faces).

Agujeros: caras cilíndricas cóncavas coaxiales y del mismo radio que juntas dan la vuelta completa; si hay otro agujero
coaxial pegado de otro diámetro es un avellanado (counterbore). Pasante si más allá de los dos extremos hay aire.
Empalmes: caras cilíndricas, toroidales o esféricas que no son agujeros y empalman con sus vecinas (tangentes) por al menos
una arista; el radio es el de la superficie. Chaflanes: caras planas angostas entre dos caras planas distintas, con el mismo
ángulo contra cada vecina (entre 20° y 70° respecto de ella) y angostas respecto de ellas.
"""
import math

import numpy as np

from . import geometria as geo

TOL_TANGENTE = math.radians(1.0)           # dos caras vecinas con menos que esto entre sus normales son tangentes
ANCHO_CHAFLAN_MAX = 0.3                    # ancho de la cara del chaflán / ancho de sus vecinas (aprox.)


def _superficie(cara):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopoDS import TopoDS
    return BRepAdaptor_Surface(TopoDS.Face(cara))


def _normal_y_punto(cara):
    from . import solidos_modificar as sm
    return sm._punto_normal(cara)


def _cilindro(cara):
    """(punto del eje, dirección del eje, radio, ángulo recorrido, largo) de una cara cilíndrica; None si no lo es."""
    from OCP.BRepTools import BRepTools
    from OCP.GeomAbs import GeomAbs_Cylinder
    s = _superficie(cara)
    if s.GetType() != GeomAbs_Cylinder:
        return None
    c = s.Cylinder()
    ax = c.Axis()
    o, d = ax.Location(), ax.Direction()
    u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
    base = np.array([o.X(), o.Y(), o.Z()]) + np.array([d.X(), d.Y(), d.Z()]) * v0
    return base, np.array([d.X(), d.Y(), d.Z()]), c.Radius(), u1 - u0, v1 - v0


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


def _agujeros(forma, caras):
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
        a, b = g["base"], g["base"] + g["eje"] * g["largo"]
        salida.append({"type": "hole", "faces": g["caras"], "diameter": round(2 * g["radio"], 6),
                       "depth": round(g["largo"], 6), "axis_point": [round(float(x), 6) for x in a],
                       "axis": [round(float(x), 6) for x in g["eje"]],
                       "through": _hay_aire(forma, a - g["eje"] * 1e-3) and _hay_aire(forma, b + g["eje"] * 1e-3)})
    # avellanado: dos agujeros coaxiales de distinto diámetro, uno a continuación del otro
    for i, h in enumerate(salida):
        for k in range(i + 1, len(salida)):
            o = salida[k]
            if abs(abs(np.dot(h["axis"], o["axis"])) - 1) < 1e-9 and                     np.linalg.norm(np.cross(h["axis"], np.subtract(h["axis_point"], o["axis_point"]))) < 1e-6 and                     abs(h["diameter"] - o["diameter"]) > 1e-6:
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
                           "convex": convexo if convexo is None else bool(convexo), "tangent_edges": tangentes})
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
                salida.append({"type": "chamfer", "faces": [i], "width": round(float(ancho), 6), "angle": round(q1, 4)})
                break
    return salida


def reconocer_funciones(forma, tipos=("hole", "fillet", "chamfer")):
    """Funciones que forman `forma` (un sólido sin historial): {"faces": n, "face_shapes": [...], "features": [...]}."""
    from OCP.TopAbs import TopAbs_FACE
    from . import solidos_modificar as sm
    desconocidos = set(tipos) - {"hole", "fillet", "chamfer"}
    if desconocidos:
        raise geo.ErrorGeometria(f"Tipo de función desconocido: {', '.join(sorted(desconocidos))}")
    caras = [sm.TopoDS.Face(c) for c in sm._unicos(forma, TopAbs_FACE)]
    if not caras:
        raise geo.ErrorGeometria("El cuerpo no tiene caras.")
    funciones = []
    if "hole" in tipos:
        funciones += _agujeros(forma, caras)
    if "fillet" in tipos:
        funciones += _empalmes(forma, caras)
    if "chamfer" in tipos:
        funciones += _chaflanes(forma, caras)
    return {"faces": len(caras), "face_shapes": caras, "features": funciones}
