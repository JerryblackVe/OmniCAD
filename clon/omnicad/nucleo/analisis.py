# -*- coding: utf-8 -*-
"""
Análisis e inspección (menú Inspeccionar de Fusion): Medir, Interferencia, Propiedades físicas,
Centro de masa, materiales físicos, mapas de color (curvatura, desmoldeo, accesibilidad, radio mínimo,
cebra, mapa de entorno), peine de curvatura, isocurvas y sección.

Funciones puras, sin Qt: devuelven dicts, formas OCC o arrays numpy que la interfaz solo dibuja.
Los mapas de color devuelven (vertices Nx3, normales Nx3, colores Nx3) float32 como triángulos sueltos
(3 filas por triángulo, como `geo.teselar`, pero con los triángulos grandes subdivididos); colores RGB
0..1. Las normales son las de la superficie exacta en cada nodo (no las del triángulo), así la cebra y
los reflejos salen suaves. Los mapas sobre formas aceptan `alta_calidad` (muestreo más fino, como la
casilla "Alta calidad"), `deflexion` y `angular` (los de `geo.teselar_por_cara`).
Curvaturas con signo de "material": positivas en zonas convexas, negativas en cóncavas (1/mm).
"""
import math

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Section
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.BRepLProp import BRepLProp_CLProps, BRepLProp_SLProps
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import (GeomAbs_Circle, GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Line, GeomAbs_Plane,
                         GeomAbs_Sphere, GeomAbs_Torus)
from OCP.GProp import GProp_GProps
from OCP.IntTools import IntTools_FClass2d
from OCP.OCP.collections import (IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher,
                                 IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher)
from OCP.TopAbs import (TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_OUT, TopAbs_REVERSED, TopAbs_VERTEX,
                        TopAbs_WIRE)
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Shape
from OCP.gp import gp_Ax2, gp_Ax3, gp_Dir, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Vec

from . import geometria as geo

VERDE = (0.20, 0.75, 0.30)
AMARILLO = (0.98, 0.85, 0.15)
ROJO = (0.88, 0.18, 0.15)

# ---------------------------------------------------------------- materiales físicos
# Biblioteca básica (Modificar > Material físico / Administrar materiales). Densidades nominales de
# tablas de ingeniería en g/cm³; color de aspecto RGB 0..1 para el visor.
TABLA_MATERIALES = {
    "Acero": {"densidad": 7.85, "color": (0.62, 0.63, 0.65)},
    "Acero inoxidable": {"densidad": 8.00, "color": (0.75, 0.76, 0.78)},
    "Aluminio 6061": {"densidad": 2.70, "color": (0.80, 0.81, 0.83)},
    "Latón": {"densidad": 8.47, "color": (0.80, 0.65, 0.30)},
    "Cobre": {"densidad": 8.96, "color": (0.78, 0.45, 0.28)},
    "ABS": {"densidad": 1.06, "color": (0.90, 0.90, 0.88)},
    "PLA": {"densidad": 1.24, "color": (0.95, 0.95, 0.95)},
    "PETG": {"densidad": 1.27, "color": (0.70, 0.85, 0.90)},
    "Nylon": {"densidad": 1.14, "color": (0.93, 0.92, 0.86)},
    "Policarbonato": {"densidad": 1.20, "color": (0.85, 0.90, 0.95)},
    "Madera (pino)": {"densidad": 0.50, "color": (0.85, 0.70, 0.48)},
    "Vidrio": {"densidad": 2.50, "color": (0.70, 0.85, 0.85)},
    "Titanio": {"densidad": 4.51, "color": (0.55, 0.55, 0.58)},
    "Hierro fundido": {"densidad": 7.20, "color": (0.35, 0.35, 0.36)},
}


# ---------------------------------------------------------------- utilidades
def _np(p):
    return np.array([p.X(), p.Y(), p.Z()], float)


def _tupla(v):
    return tuple(float(c) for c in v)


def _unitario(v, nombre="dirección"):
    v = np.asarray(v, float).reshape(3)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise geo.ErrorGeometria(f"La {nombre} no puede ser nula.")
    return v / n


def _normalizar_filas(m):
    largo = np.linalg.norm(m, axis=1, keepdims=True)
    largo[largo < 1e-15] = 1.0
    return m / largo


def _a_forma(x):
    """Forma OCC tal cual, o un punto (array de 3) convertido en vértice."""
    if isinstance(x, TopoDS_Shape):
        if x.IsNull():
            raise geo.ErrorGeometria("La selección está vacía.")
        return x
    p = np.asarray(x, float).reshape(-1)
    if p.size != 3:
        raise geo.ErrorGeometria("Un punto debe tener 3 coordenadas.")
    return BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, p))).Vertex()


def _largo(forma):
    p = GProp_GProps()
    BRepGProp.LinearProperties_s(forma, p)
    return p.Mass()


def _aristas_unicas(forma):
    mapa = IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapes_s(forma, TopAbs_EDGE, mapa)
    return [TopoDS.Edge(mapa.FindKey(i)) for i in range(1, mapa.Size() + 1)]


# ---------------------------------------------------------------- medir
def _info_arista(arista):
    curva = BRepAdaptor_Curve(arista)
    info = {"tipo": "arista", "largo": _largo(arista)}
    t = curva.GetType()
    if t == GeomAbs_Line:
        info["direccion"] = _tupla(_np(curva.Line().Direction()))
    elif t == GeomAbs_Circle:
        c = curva.Circle()
        info.update(radio=c.Radius(), diametro=2 * c.Radius(), centro=_tupla(_np(c.Location())),
                    eje=_tupla(_np(c.Axis().Direction())))
    return info


def _info_cara(cara):
    sup = BRepAdaptor_Surface(cara)
    perimetro = sum(_largo(e) for e in _aristas_unicas(cara)
                    if not BRep_Tool.Degenerated_s(e) and not BRep_Tool.IsClosed_s(e, cara))
    info = {"tipo": "cara", "area": geo.area(cara), "perimetro": perimetro}
    t = sup.GetType()
    signo = -1.0 if cara.Orientation() == TopAbs_REVERSED else 1.0
    if t == GeomAbs_Plane and not sup.Plane().Position().Direct():
        signo = -signo                      # ejes indirectos (tapas de una revolución): la normal es −eje
    if t == GeomAbs_Plane:
        info["superficie"] = "plano"
        info["normal"] = _tupla(_np(sup.Plane().Axis().Direction()) * signo)
        # Cara circular (disco): Fusion muestra también el centro.
        externo = BRepTools.OuterWire_s(cara)
        externas = [] if externo.IsNull() else _aristas_unicas(externo)
        if len(externas) == 1 and BRepAdaptor_Curve(externas[0]).GetType() == GeomAbs_Circle:
            c = BRepAdaptor_Curve(externas[0]).Circle()
            info.update(radio=c.Radius(), diametro=2 * c.Radius(), centro=_tupla(_np(c.Location())))
    elif t == GeomAbs_Cylinder:
        c = sup.Cylinder()
        info.update(superficie="cilindro", radio=c.Radius(), diametro=2 * c.Radius(),
                    centro=_tupla(_np(c.Location())), eje=_tupla(_np(c.Axis().Direction())))
    elif t == GeomAbs_Sphere:
        s = sup.Sphere()
        info.update(superficie="esfera", radio=s.Radius(), diametro=2 * s.Radius(), centro=_tupla(_np(s.Location())))
    elif t == GeomAbs_Torus:   # empalme alrededor de una arista circular
        s = sup.Torus()
        info.update(superficie="toroide", radio=s.MinorRadius(), diametro=2 * s.MinorRadius(),
                    radio_mayor=s.MajorRadius())
    elif t == GeomAbs_Cone:
        info.update(superficie="cono", semiangulo=math.degrees(abs(sup.Cone().SemiAngle())))
    return info


def _info_entidad(x):
    if not isinstance(x, TopoDS_Shape):
        return {"tipo": "punto", "posicion": _tupla(np.asarray(x, float).reshape(3))}
    t = x.ShapeType()
    if t == TopAbs_VERTEX:
        return {"tipo": "vertice", "posicion": _tupla(_np(BRep_Tool.Pnt_s(TopoDS.Vertex(x))))}
    if t == TopAbs_EDGE:
        return _info_arista(TopoDS.Edge(x))
    if t == TopAbs_FACE:
        return _info_cara(TopoDS.Face(x))
    if t == TopAbs_WIRE:
        return {"tipo": "contorno", "largo": _largo(x)}
    caja = geo.caja_envolvente(x)
    info = {"tipo": "cuerpo", "area": geo.area(x), "caja": caja}
    if geo.solidos(x):
        info["volumen"] = geo.volumen(x)
        info["centro_masa"] = geo.centro_masa(x)
    return info


def _direccion_angular(x):
    """('linea', dir) para aristas rectas, ('plano', normal) para caras planas; None si no aplica."""
    if not isinstance(x, TopoDS_Shape):
        return None
    if x.ShapeType() == TopAbs_EDGE:
        c = BRepAdaptor_Curve(TopoDS.Edge(x))
        if c.GetType() == GeomAbs_Line:
            return "linea", _np(c.Line().Direction())
    elif x.ShapeType() == TopAbs_FACE:
        s = BRepAdaptor_Surface(TopoDS.Face(x))
        if s.GetType() == GeomAbs_Plane:
            return "plano", _np(s.Plane().Axis().Direction())
    return None


def _angulo(a, b):
    """Ángulo agudo (0..90°) entre rectas, planos o recta-plano, como lo informa Medir."""
    da, db = _direccion_angular(a), _direccion_angular(b)
    if da is None or db is None:
        return None
    c = min(1.0, abs(float(da[1] @ db[1])))
    if da[0] == db[0]:
        return math.degrees(math.acos(c))
    return math.degrees(math.asin(c))   # recta con plano: complemento del ángulo con la normal


def _punto_a_recta(p, origen, d):
    return origen + d * float((p - origen) @ d)


def _centro_a_centro(ia, ib):
    """Distancia entre centros de arcos/círculos/esferas o ejes de cilindros (opción "centro a centro")."""
    if "centro" not in ia or "centro" not in ib or "radio" not in ia or "radio" not in ib:
        return None
    ca, cb = np.array(ia["centro"]), np.array(ib["centro"])
    eje_a = np.array(ia["eje"]) if ia.get("superficie") == "cilindro" else None
    eje_b = np.array(ib["eje"]) if ib.get("superficie") == "cilindro" else None
    if eje_a is None and eje_b is None:
        pa, pb = ca, cb
    elif eje_a is None:
        pa, pb = ca, _punto_a_recta(ca, cb, eje_b)
    elif eje_b is None:
        pa, pb = _punto_a_recta(cb, ca, eje_a), cb
    else:
        # Puntos más cercanos entre dos rectas (si son paralelas, cualquiera sirve).
        w = ca - cb
        b = float(eje_a @ eje_b)
        den = 1.0 - b * b
        if den < 1e-12:
            pa, pb = ca, _punto_a_recta(ca, cb, eje_b)
        else:
            d, e = float(eje_a @ w), float(eje_b @ w)
            pa, pb = ca + eje_a * ((b * e - d) / den), cb + eje_b * ((e - b * d) / den)
    dc = float(np.linalg.norm(pb - pa))
    suma = ia["radio"] + ib["radio"]
    return {"distancia": dc, "punto_a": _tupla(pa), "punto_b": _tupla(pb),
            "minima": dc - suma, "maxima": dc + suma}


def medir(a, b=None, *, centro_a_centro=False):
    """Inspeccionar > Medir. `a` y `b`: cara, arista, vértice, cuerpo (formas OCC) o punto (array de 3).

    Con una sola selección devuelve {"a": info}: largo de arista; área y perímetro (largo de lazos) de
    cara; radio/diámetro/centro si es circular o cilíndrica; volumen, área, caja y centro de masa de un
    cuerpo; posición de un vértice. Con dos agrega: "distancia" mínima con "punto_a"/"punto_b" sobre cada
    selección, "delta" (ΔX, ΔY, ΔZ de a hacia b), "angulo" (aristas rectas / caras planas) y, si ambas
    son circulares, "centro_a_centro" con las distancias mínima y máxima según los diámetros.
    `centro_a_centro=True` hace que la distancia principal sea entre centros (como la opción de Fusion).
    """
    info_a = _info_entidad(a)
    if b is None:
        return {"a": info_a}
    info_b = _info_entidad(b)
    dist = BRepExtrema_DistShapeShape(_a_forma(a), _a_forma(b))
    if not dist.IsDone() or dist.NbSolution() == 0:
        raise geo.ErrorGeometria("No se pudo medir la distancia entre las selecciones.")
    pa, pb = _np(dist.PointOnShape1(1)), _np(dist.PointOnShape2(1))
    res = {"a": info_a, "b": info_b, "distancia": dist.Value(), "punto_a": _tupla(pa), "punto_b": _tupla(pb),
           "delta": _tupla(pb - pa)}
    ang = _angulo(a, b)
    if ang is not None:
        res["angulo"] = ang
    cc = _centro_a_centro(info_a, info_b)
    if cc is not None:
        res["centro_a_centro"] = cc
        if centro_a_centro:
            res.update(distancia=cc["distancia"], punto_a=cc["punto_a"], punto_b=cc["punto_b"],
                       delta=_tupla(np.array(cc["punto_b"]) - np.array(cc["punto_a"])))
    elif centro_a_centro:
        raise geo.ErrorGeometria("Centro a centro necesita dos selecciones circulares (arco, círculo o cilindro).")
    return res


# ---------------------------------------------------------------- interferencias
# Espesor medio (2·volumen/área, en mm) por debajo del cual el volumen común es contacto con error de redondeo.
ESPESOR_MIN_INTERFERENCIA = 1e-3


def _cajas_se_tocan(ca, cb, tol):
    if ca is None or cb is None:
        return False
    (a0, a1), (b0, b1) = ca, cb
    return all(a0[i] <= b1[i] + tol and b0[i] <= a1[i] + tol for i in range(3))


def interferencias(cuerpos, *, caras_coincidentes=False):
    """Inspeccionar > Interferencia. `cuerpos`: dict id → forma.

    Lista de {"a", "b", "volumen", "forma", "coincidente"} por cada par que se superpone; la forma es el
    volumen de interferencia (BRepAlgoAPI_Common). Primero filtra por caja envolvente (rápido). Con
    `caras_coincidentes=True` también informa los pares que solo se tocan en caras (volumen 0, "area" y
    las caras comunes en "forma"), como la opción "Incluir caras coincidentes".

    Dos cuerpos apoyados cara con cara con una inclinación de redondeo (1e-5 rad) dan un volumen común de
    milésimas de mm³ pero de espesor casi nulo: eso es contacto, no interferencia. Un par cuenta solo si
    el espesor medio del volumen común (2·volumen/área) llega a ESPESOR_MIN_INTERFERENCIA (0,001 mm).
    """
    ids = list(cuerpos)
    cajas = {i: geo.caja_envolvente(cuerpos[i]) for i in ids}
    salida = []
    for n, ia in enumerate(ids):
        for ib in ids[n + 1:]:
            if not _cajas_se_tocan(cajas[ia], cajas[ib], 1e-6):
                continue
            fa, fb = cuerpos[ia], cuerpos[ib]
            comun = geo.booleano(fa, fb, "intersecar")
            vol = geo.volumen(comun) if not geo.esta_vacia(comun) else 0.0
            escala = min(abs(geo.volumen(fa)), abs(geo.volumen(fb))) or 1.0
            if vol > 1e-9 * escala and 2 * vol >= ESPESOR_MIN_INTERFERENCIA * geo.area(comun):
                salida.append({"a": ia, "b": ib, "volumen": vol, "forma": comun, "coincidente": False})
            elif caras_coincidentes:
                # Booleano entre las cáscaras (dimensión 2): devuelve solo las porciones de cara compartidas.
                op = BRepAlgoAPI_Common(geo.compuesto(geo.caras(fa)), geo.compuesto(geo.caras(fb)))
                if op.IsDone() and not geo.esta_vacia(op.Shape()):
                    area = geo.area(op.Shape())
                    if area > 1e-9:
                        salida.append({"a": ia, "b": ib, "volumen": 0.0, "forma": op.Shape(), "area": area,
                                       "coincidente": True})
    return salida


# ---------------------------------------------------------------- propiedades físicas
def _matriz(m):
    return np.array([[m.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)], float)


def propiedades_fisicas(forma, densidad_g_cm3=7.85):
    """Propiedades (clic derecho > Propiedades): masa, volumen, área, densidad, centro de masa e inercia.

    Unidades como Fusion: g, mm³, mm², g/cm³ y g·mm². "inercia_centro" e "inercia_origen" son tensores
    3x3 con productos de inercia en convención de mecánica (Ixy = −∫xy dm), respecto del centro de masa
    y del origen (teorema de Steiner). "momentos_principales" y "ejes_principales" respecto del centro.
    """
    if densidad_g_cm3 <= 0:
        raise geo.ErrorGeometria("La densidad debe ser positiva.")
    if not geo.solidos(forma):
        raise geo.ErrorGeometria("Las propiedades físicas necesitan un cuerpo sólido.")
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(forma, props)
    vol = props.Mass()
    rho = densidad_g_cm3 * 1e-3            # g/mm³
    masa = vol * rho
    c = _np(props.CentreOfMass())
    i_centro = _matriz(props.MatrixOfInertia()) * rho
    i_origen = i_centro + masa * (float(c @ c) * np.eye(3) - np.outer(c, c))
    principales = props.PrincipalProperties()
    momentos = tuple(float(m) * rho for m in principales.Moments())
    ejes = [_tupla(_np(e)) for e in (principales.FirstAxisOfInertia(), principales.SecondAxisOfInertia(),
                                     principales.ThirdAxisOfInertia())]
    return {"masa": masa, "volumen": vol, "area": geo.area(forma), "densidad": float(densidad_g_cm3),
            "centro_masa": _tupla(c), "inercia_centro": i_centro.tolist(), "inercia_origen": i_origen.tolist(),
            "momentos_principales": momentos, "ejes_principales": ejes}


def centro_de_masa(formas, densidades=None):
    """Inspeccionar > Centro de masa de varios cuerpos: promedio ponderado por masa (o volumen si no hay
    densidades en g/cm³). Acepta una forma, una lista o un dict id → forma."""
    if isinstance(formas, TopoDS_Shape):
        formas = [formas]
    elif isinstance(formas, dict):
        formas = list(formas.values())
    formas = list(formas)
    if not formas:
        raise geo.ErrorGeometria("No hay cuerpos para calcular el centro de masa.")
    if densidades is None:
        densidades = [1.0] * len(formas)
    if len(densidades) != len(formas):
        raise geo.ErrorGeometria("Hace falta una densidad por cuerpo.")
    total, suma = 0.0, np.zeros(3)
    for forma, dens in zip(formas, densidades, strict=True):
        p = GProp_GProps()
        BRepGProp.VolumeProperties_s(forma, p)
        m = p.Mass() * float(dens)
        total += m
        suma += _np(p.CentreOfMass()) * m
    if abs(total) < 1e-15:
        raise geo.ErrorGeometria("Los cuerpos no tienen volumen.")
    return _tupla(suma / total)


# ---------------------------------------------------------------- muestreo del teselado
def _indices(tri, cara):
    idx = np.array([tri.Triangle(i).Get() for i in range(1, tri.NbTriangles() + 1)], int).reshape(-1, 3) - 1
    if cara.Orientation() == TopAbs_REVERSED:
        idx = idx[:, [0, 2, 1]]
    return idx


def _props_nodos(cara, tri, idx, tris, curvatura):
    """Normal exacta (hacia afuera del material) y curvaturas en cada nodo de la triangulación."""
    m = tri.NbNodes()
    # Respaldo: normal promediada de los triángulos (polos de esferas, nodos sin UV).
    nt = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    plana = np.zeros((m, 3))
    for k in range(3):
        np.add.at(plana, idx[:, k], nt)
    plana = _normalizar_filas(plana)
    curv = np.zeros((m, 4)) if curvatura else None
    sup = BRepAdaptor_Surface(cara)
    signo = -1.0 if cara.Orientation() == TopAbs_REVERSED else 1.0
    if sup.GetType() == GeomAbs_Plane:
        if not sup.Plane().Position().Direct():
            signo = -signo                  # ejes indirectos: la normal es −eje
        return np.tile(_np(sup.Plane().Axis().Direction()) * signo, (m, 1)), curv
    if not tri.HasUVNodes():
        return plana, curv
    normales = plana.copy()
    if curvatura:
        curv[:] = np.nan
    props = BRepLProp_SLProps(sup, 2 if curvatura else 1, 1e-9)
    # OCC mide la curvatura respecto de la normal natural (esfera con normal afuera → −1/R);
    # con signo −signo queda positiva en lo convexo del material.
    s = -signo
    for i in range(m):
        uv = tri.UVNode(i + 1)
        props.SetParameters(uv.X(), uv.Y())
        if props.IsNormalDefined():
            n = props.Normal()
            normales[i] = (n.X() * signo, n.Y() * signo, n.Z() * signo)
        if curvatura and props.IsCurvatureDefined():
            k1, k2 = s * props.MinCurvature(), s * props.MaxCurvature()
            curv[i] = (min(k1, k2), max(k1, k2), s * props.MeanCurvature(), props.GaussianCurvature())
    if curvatura:
        for j in range(4):
            col = curv[:, j]
            malos = np.isnan(col)
            if malos.any():
                col[malos] = 0.0 if malos.all() else np.nanmean(col)
    return normales, curv


_PATRONES = {}


def _patron(n):
    """Baricéntricas (3·n², 3) de la subdivisión regular de un triángulo en n² (misma orientación)."""
    if n not in _PATRONES:
        def b(i, j):
            return ((n - i - j) / n, i / n, j / n)
        sub = []
        for i in range(n):
            for j in range(n - i):
                sub.append((b(i, j), b(i + 1, j), b(i, j + 1)))
                if i + j < n - 1:
                    sub.append((b(i + 1, j), b(i + 1, j + 1), b(i, j + 1)))
        _PATRONES[n] = np.array(sub, float).reshape(-1, 3)
    return _PATRONES[n]


class _Bloque:
    """Triángulos de una cara en el muestreo: sabe pasar valores por nodo a los vértices sueltos."""

    def __init__(self, cara, tri, loc, idx, tris, grupos, inicio):
        self.cara, self.tri, self.loc, self.idx, self.tris = cara, tri, loc, idx, tris
        self.grupos, self.inicio = grupos, inicio
        self.tamano = sum(len(sel) * len(_patron(n)) for sel, n in grupos)

    def expandir(self, valores):
        """Interpolación baricéntrica de valores por nodo (M x c) → (vértices de la cara x c)."""
        partes = [np.einsum("pk,tkc->tpc", _patron(n), valores[self.idx[sel]]).reshape(-1, valores.shape[1])
                  for sel, n in self.grupos]
        return np.concatenate(partes)

    def expandir_borde(self, marcados):
        """Máscara por nodo → vértices: un vértice nuevo queda marcado solo si todos los nodos que lo
        generan (peso > 0) están marcados, así una marca de arista no se derrama hacia el interior."""
        partes = []
        for sel, n in self.grupos:
            usa = (_patron(n) > 1e-12).astype(float)                       # (P, 3)
            libres = (~marcados[self.idx[sel]]).astype(float)              # (T, 3)
            partes.append((libres @ usa.T == 0).reshape(-1))
        return np.concatenate(partes)


def _malla(forma, deflexion, angular, curvatura, alta_calidad=False):
    """(vertices Nx3, normales Nx3, curv Nx4 | None, bloques) a partir de `geo.teselar_por_cara`.

    Los triángulos grandes (caras planas: solo tienen nodos en el borde) se subdividen hasta un lado
    de diagonal/40 (diagonal/120 con `alta_calidad`, la casilla "Alta calidad" de Fusion), así un color
    por vértice puede mostrar, p. ej., la mitad tapada de una cara. Normales y curvaturas se calculan
    exactas en los nodos y se interpolan. curv = (k_min, k_max, media, gaussiana).
    """
    caras_tris = geo.teselar_por_cara(forma, deflexion, angular)
    if not caras_tris:
        raise geo.ErrorGeometria("La forma no tiene caras para analizar.")
    todos = np.concatenate([t.reshape(-1, 3) for _c, t in caras_tris])
    diag = float(np.linalg.norm(todos.max(axis=0) - todos.min(axis=0))) or 1.0
    largo_max = diag / (120.0 if alta_calidad else 40.0)
    verts, norms, curvs, bloques = [], [], [], []
    inicio = 0
    for cara, tris in caras_tris:
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(cara, loc)
        idx = _indices(tri, cara)
        n_nodo, k_nodo = _props_nodos(cara, tri, idx, tris, curvatura)
        lados = np.linalg.norm(tris - np.roll(tris, 1, axis=1), axis=2).max(axis=1)
        nsub = np.clip(np.ceil(lados / largo_max), 1, 16).astype(int)
        grupos = [(np.nonzero(nsub == n)[0], int(n)) for n in np.unique(nsub)]
        bloque = _Bloque(cara, tri, loc, idx, tris, grupos, inicio)
        verts.append(np.concatenate([np.einsum("pk,tkj->tpj", _patron(n), tris[sel]).reshape(-1, 3)
                                     for sel, n in grupos]))
        norms.append(_normalizar_filas(bloque.expandir(n_nodo)))
        if curvatura:
            curvs.append(bloque.expandir(k_nodo))
        bloques.append(bloque)
        inicio += bloque.tamano
    v = np.concatenate(verts).astype(np.float32)
    n = np.concatenate(norms).astype(np.float32)
    k = np.concatenate(curvs) if curvatura else None
    return v, n, k, bloques


def _pintar(mascaras_colores, n):
    """Colores Nx3 float32 a partir de [(máscara, color)], en orden (la última gana)."""
    col = np.zeros((n, 3), np.float32)
    for mascara, color in mascaras_colores:
        col[mascara] = color
    return col


# ---------------------------------------------------------------- mapa de curvatura
_TIPOS_CURVATURA = {"minima": 0, "maxima": 1, "media": 2, "gaussiana": 3}
# Paleta de Fusion para la curvatura: violeta/añil/azul negativa, verde plana, amarillo/naranja/rojo positiva.
_PARADAS = np.array([-1.0, -2 / 3, -1 / 3, 0.0, 1 / 3, 2 / 3, 1.0])
_COLORES_RAMPA = np.array([(0.50, 0.00, 0.80), (0.25, 0.10, 0.85), (0.00, 0.45, 1.00), (0.10, 0.80, 0.25),
                           (1.00, 0.92, 0.10), (1.00, 0.55, 0.00), (0.90, 0.10, 0.10)])


def _rampa(t):
    return np.stack([np.interp(t, _PARADAS, _COLORES_RAMPA[:, k]) for k in range(3)], axis=1).astype(np.float32)


def valores_curvatura(forma, *, tipo="gaussiana", alta_calidad=False, deflexion=0.05, angular=0.3):
    """(vertices, normales, valores N) de curvatura por vértice: "gaussiana" (1/mm²), "media", "maxima" o
    "minima" (principales, 1/mm). Positiva en lo convexo. Base de `colores_curvatura`."""
    if tipo not in _TIPOS_CURVATURA:
        raise geo.ErrorGeometria(f"Tipo de curvatura desconocido: {tipo}")
    v, n, k, _ = _malla(forma, deflexion, angular, True, alta_calidad)
    return v, n, k[:, _TIPOS_CURVATURA[tipo]].astype(np.float32)


def colores_curvatura(forma, *, tipo="gaussiana", rango=None, bandas=False, alta_calidad=False, deflexion=0.05,
                      angular=0.3):
    """Inspeccionar > Análisis de mapa de curvatura → (vertices, normales, colores).

    `rango`: escala del degradé. Un número r pinta [−r, r] (rojo = +r, verde = 0, violeta = −r); una
    tupla (min, max) estira ese intervalo; None = automático (percentil 95 de |valor|).
    `bandas=True` = visualización "Bandas" (7 colores sin transición) en vez de "Suave".
    """
    v, n, val = valores_curvatura(forma, tipo=tipo, alta_calidad=alta_calidad, deflexion=deflexion,
                                  angular=angular)
    val = val.astype(float)
    if rango is None:
        r = float(np.percentile(np.abs(val), 95)) if val.size else 0.0
        if r < 1e-12:
            r = float(np.abs(val).max()) if val.size else 0.0
        t = val / (r if r > 1e-12 else 1.0)
    elif np.ndim(rango) == 0:
        if float(rango) <= 0:
            raise geo.ErrorGeometria("El rango de curvatura debe ser positivo.")
        t = val / float(rango)
    else:
        lo, hi = map(float, rango)
        if hi <= lo:
            raise geo.ErrorGeometria("El rango de curvatura necesita mínimo < máximo.")
        t = 2.0 * (val - lo) / (hi - lo) - 1.0
    t = np.clip(t, -1.0, 1.0)
    if bandas:
        t = np.round(t * 3.0) / 3.0
    return v, n, _rampa(t)


# ---------------------------------------------------------------- desmoldeo
def angulos_desmoldeo(forma, direccion, *, alta_calidad=False, deflexion=0.05, angular=0.3):
    """(vertices, normales, ángulos N en grados): ángulo de desmoldeo de cada vértice respecto de la
    dirección de extracción (+90 = cara hacia la dirección, 0 = pared paralela, negativo = contrasalida)."""
    d = _unitario(direccion, "dirección de extracción")
    v, n, _, _ = _malla(forma, deflexion, angular, False, alta_calidad)
    ang = np.degrees(np.arcsin(np.clip(n.astype(float) @ d, -1.0, 1.0)))
    return v, n, ang.astype(np.float32)


def colores_desmoldeo(forma, direccion, angulo_min=0.0, angulo_max=3.0, *, alta_calidad=False, deflexion=0.05,
                      angular=0.3):
    """Inspeccionar > Análisis de desmoldeo (Draft Analysis) → (vertices, normales, colores).

    Verde: ángulo ≥ angulo_max (desmoldeo positivo suficiente). Amarillo: entre ambos (neutro, zona de
    línea de partición). Rojo: ≤ angulo_min (insuficiente o contrasalida). Ángulos en grados.
    """
    if angulo_max < angulo_min:
        raise geo.ErrorGeometria("El ángulo máximo de desmoldeo debe ser ≥ al mínimo.")
    v, n, ang = angulos_desmoldeo(forma, direccion, alta_calidad=alta_calidad, deflexion=deflexion,
                                  angular=angular)
    tol = 1e-6
    return v, n, _pintar([(np.ones(len(ang), bool), AMARILLO), (ang >= angulo_max - tol, VERDE),
                          (ang <= angulo_min + tol, ROJO)], len(ang))


# ---------------------------------------------------------------- accesibilidad
def _rayos_chocan(origenes, d, tris, eps):
    """Máscara: el rayo origen + t·d (t > eps) atraviesa algún triángulo. Möller–Trumbore vectorizado
    (como d es común a todos los rayos, u, v y t salen de tres productos matriciales) con una grilla
    2D en el plano perpendicular a d para no probar cada rayo contra todos los triángulos."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = b - a, c - a
    h = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, h)
    ok = np.abs(det) > 1e-12 * max(1.0, float(np.abs(e1).max()) ** 2)
    a, e1, e2, h, det = a[ok], e1[ok], e2[ok], h[ok], det[ok]
    choca = np.zeros(len(origenes), bool)
    if not len(a) or not len(origenes):
        return choca
    g = np.cross(e1, d)
    nv = np.cross(e1, e2)
    inv = 1.0 / det
    ah, ag, an = np.einsum("ij,ij->i", a, h), np.einsum("ij,ij->i", a, g), np.einsum("ij,ij->i", a, nv)
    # Grilla en el plano ⟂ d.
    p1 = np.cross(d, (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 1.0, 0.0))
    p1 /= np.linalg.norm(p1)
    p2 = np.cross(d, p1)
    base = np.stack([p1, p2], axis=1)
    o2 = origenes @ base
    t2 = np.einsum("tkj,jl->tkl", np.stack([a, a + e1, a + e2], axis=1), base)
    lo, hi = o2.min(axis=0) - eps, o2.max(axis=0) + eps
    celdas = int(np.clip(math.sqrt(len(a)) / 2, 1, 64))
    paso = np.maximum((hi - lo) / celdas, 1e-12)

    def celda(x):
        return np.clip(((x - lo) / paso).astype(int), 0, celdas - 1)

    tmin, tmax = t2.min(axis=1), t2.max(axis=1)
    fuera = np.any(tmax < lo, axis=1) | np.any(tmin > hi, axis=1)
    i0, i1 = celda(tmin - eps), celda(tmax + eps)
    i0[fuera], i1[fuera] = 1, 0                      # rango vacío
    nx = np.maximum(i1[:, 0] - i0[:, 0] + 1, 0)
    ny = np.maximum(i1[:, 1] - i0[:, 1] + 1, 0)
    cuenta = nx * ny
    tri_rep = np.repeat(np.arange(len(a)), cuenta)
    k = np.arange(cuenta.sum()) - np.repeat(np.cumsum(cuenta) - cuenta, cuenta)
    cx = np.repeat(i0[:, 0], cuenta) + k % np.repeat(np.maximum(nx, 1), cuenta)
    cy = np.repeat(i0[:, 1], cuenta) + k // np.repeat(np.maximum(nx, 1), cuenta)
    clave_tri = cx * celdas + cy
    orden = np.argsort(clave_tri, kind="stable")
    clave_tri, tri_rep = clave_tri[orden], tri_rep[orden]
    co = celda(o2)
    clave_rayo = co[:, 0] * celdas + co[:, 1]
    orden_r = np.argsort(clave_rayo, kind="stable")
    claves, cortes = np.unique(clave_rayo[orden_r], return_index=True)
    for clave, rayos in zip(claves, np.split(orden_r, cortes[1:]), strict=True):
        i, j = np.searchsorted(clave_tri, clave), np.searchsorted(clave_tri, clave, side="right")
        if i == j:
            continue
        ts = tri_rep[i:j]
        o = origenes[rayos]
        u = (o @ h[ts].T - ah[ts]) * inv[ts]
        v = (o @ g[ts].T - ag[ts]) * inv[ts]
        t = (o @ nv[ts].T - an[ts]) * inv[ts]
        golpe = (u >= 0.0) & (v >= 0.0) & (u + v <= 1.0) & (t > eps)
        choca[rayos] = golpe.any(axis=1)
    return choca


def _accesible(v, n, d, oclusion, tris):
    ve = v.astype(float)
    ne = n.astype(float)
    candidato = ne @ d >= -1e-6
    if not oclusion or not candidato.any():
        return candidato
    diag = float(np.linalg.norm(ve.max(axis=0) - ve.min(axis=0))) or 1.0
    eps = 1e-6 * diag
    # Un rayo por posición+normal distinta (cada nodo aparece en ~6 triángulos); el origen se separa
    # apenas de la superficie para no chocar con las caras vecinas que comparten el vértice.
    sel = np.nonzero(candidato)[0]
    clave = np.round(np.hstack([ve[sel], ne[sel]]) / (eps * 10), 0)
    unicos, inversa = np.unique(clave, axis=0, return_index=False, return_inverse=True)
    primero = np.zeros(len(unicos), int)
    primero[inversa.reshape(-1)] = np.arange(len(sel))
    origenes = ve[sel][primero] + ne[sel][primero] * (100 * eps) + d * eps
    choca = _rayos_chocan(origenes, d, tris, eps)
    acc = candidato.copy()
    acc[sel] = ~choca[inversa.reshape(-1)]
    return acc


def colores_accesibilidad(forma, direccion, *, ambos_sentidos=False, oclusion=True, alta_calidad=False,
                          deflexion=0.05, angular=0.3):
    """Inspeccionar > Análisis de accesibilidad → (vertices, normales, colores).

    `direccion`: hacia donde está la herramienta (p. ej. +Z = desde arriba). Verde = accesible (la cara
    no le da la espalda y un rayo hacia la herramienta no choca con el propio cuerpo); rojo = no
    accesible (contrasalida o tapado). `ambos_sentidos=True` = "Ambas direcciones" (d o −d).
    `oclusion=False` usa solo normal·dirección (más rápido).
    """
    d = _unitario(direccion, "dirección de acceso")
    v, n, _, bloques = _malla(forma, deflexion, angular, False, alta_calidad)
    tris = np.concatenate([b.tris for b in bloques])     # sin subdividir: mismo cuerpo, menos triángulos
    acc = _accesible(v, n, d, oclusion, tris)
    if ambos_sentidos:
        acc |= _accesible(v, n, -d, oclusion, tris)
    return v, n, _pintar([(np.ones(len(acc), bool), ROJO), (acc, VERDE)], len(acc))


# ---------------------------------------------------------------- radio mínimo
def _normal_en(cara, arista, t):
    uv = BRepAdaptor_Curve2d(arista, cara).Value(t)
    p = BRepLProp_SLProps(BRepAdaptor_Surface(cara), uv.X(), uv.Y(), 1, 1e-9)
    if not p.IsNormalDefined():
        return None
    signo = -1.0 if cara.Orientation() == TopAbs_REVERSED else 1.0
    return _np(p.Normal()) * signo


def _es_concava(arista, vecinas):
    """Arista viva cóncava (rincón interior): la cara 1 avanza hacia afuera de la cara 2."""
    caras = []
    for f in vecinas:
        if not any(f.IsSame(g) for g in caras):
            caras.append(f)
    if len(caras) != 2:
        return False
    f1, f2 = TopoDS.Face(caras[0]), TopoDS.Face(caras[1])
    ex = TopExp_Explorer(f1, TopAbs_EDGE)
    orient = None
    while ex.More():
        if ex.Current().IsSame(arista):
            orient = ex.Current().Orientation()
            break
        ex.Next()
    curva = BRepAdaptor_Curve(arista)
    t = 0.5 * (curva.FirstParameter() + curva.LastParameter())
    p, tg = gp_Pnt(), gp_Vec()
    curva.D1(t, p, tg)
    if tg.Magnitude() < 1e-12:
        return False
    tg = _np(tg) / tg.Magnitude() * (1.0 if orient == TopAbs_FORWARD else -1.0)
    n1, n2 = _normal_en(f1, arista, t), _normal_en(f2, arista, t)
    if n1 is None or n2 is None:
        return False
    # El interior de la cara queda a la izquierda del borde visto desde la normal: n × t.
    return float(np.cross(n1, tg) @ n2) > 0.05


def _mascara_aristas_concavas(forma, bloques, n_total):
    vecinas = IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapesAndAncestors_s(forma, TopAbs_EDGE, TopAbs_FACE, vecinas)
    cache = {}
    mascara = np.zeros(n_total, bool)
    for bloque in bloques:
        nodos = np.zeros(bloque.tri.NbNodes(), bool)
        for arista in _aristas_unicas(bloque.cara):
            if BRep_Tool.Degenerated_s(arista) or BRep_Tool.IsClosed_s(arista, bloque.cara):
                continue
            clave = vecinas.FindIndex(arista)
            if clave == 0:
                continue
            if clave not in cache:
                cache[clave] = _es_concava(arista, vecinas.FindFromIndex(clave))
            if cache[clave]:
                pol = BRep_Tool.PolygonOnTriangulation_s(arista, bloque.tri, bloque.loc)
                if pol is not None:
                    lista = pol.Nodes()
                    for j in range(1, pol.NbNodes() + 1):
                        nodos[lista.Value(j) - 1] = True
        if nodos.any():
            mascara[bloque.inicio:bloque.inicio + bloque.tamano] = bloque.expandir_borde(nodos)
    return mascara


def colores_radio_minimo(forma, radio_herramienta, *, aristas_vivas=True, alta_calidad=False, deflexion=0.05,
                         angular=0.3):
    """Inspeccionar > Análisis de radio mínimo → (vertices, normales, colores).

    Rojo donde una fresa de `radio_herramienta` (mm) no entra: zonas cóncavas con radio de curvatura
    menor que el de la herramienta y, con `aristas_vivas=True` ("Curvas vivas"), los rincones interiores
    sin empalme (radio 0). Verde en el resto (zonas planas, convexas o cóncavas con radio suficiente).
    """
    if radio_herramienta <= 0:
        raise geo.ErrorGeometria("El radio de la herramienta debe ser positivo.")
    v, n, k, bloques = _malla(forma, deflexion, angular, True, alta_calidad)
    malo = k[:, 0] * float(radio_herramienta) < -(1.0 + 1e-6)
    if aristas_vivas:
        malo |= _mascara_aristas_concavas(forma, bloques, len(v))
    return v, n, _pintar([(np.ones(len(v), bool), VERDE), (malo, ROJO)], len(v))


# ---------------------------------------------------------------- cebra y mapa de entorno
def _reflejo(normales, direccion_vista):
    n = _normalizar_filas(np.asarray(normales, float).reshape(-1, 3))
    v = _unitario(direccion_vista, "dirección de vista")
    return n, v, v - 2.0 * (n @ v)[:, None] * n


def _base_vista(v, arriba):
    up = np.asarray(arriba, float) - v * float(np.asarray(arriba, float) @ v)
    if np.linalg.norm(up) < 1e-9:     # mirando justo hacia "arriba": se toma otro eje
        up = np.array([0.0, 1.0, 0.0]) - v * v[1]
    up /= np.linalg.norm(up)
    return up, np.cross(v, up)


def colores_cebra(normales, direccion_vista, *, frecuencia=8, vertical=False, arriba=(0.0, 0.0, 1.0)):
    """Inspeccionar > Análisis de cebra: franjas blancas/negras de reflexión (sin "Bloquear franjas":
    dependen de la cámara). `frecuencia` = repeticiones (1..100), `vertical` = dirección de las franjas.
    Recibe las normales por vértice (p. ej. de otro mapa) y devuelve colores Nx3; vectorizado, barato."""
    frecuencia = int(np.clip(frecuencia, 1, 100))
    _n, v, r = _reflejo(normales, direccion_vista)
    up, derecha = _base_vista(v, arriba)
    s = np.clip(r @ (derecha if vertical else up), -1.0, 1.0)
    fase = np.arcsin(s) / math.pi + 0.5                 # 0..1 sobre todo el hemisferio reflejado
    negra = (np.floor(fase * 2 * frecuencia).astype(int) % 2) == 1
    col = np.full((len(s), 3), 0.97, np.float32)
    col[negra] = 0.06
    return col


def _suave(x0, x1, x):
    t = np.clip((x - x0) / (x1 - x0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def colores_mapa_entorno(normales, direccion_vista, *, arriba=(0.0, 0.0, 1.0), rotacion=0.0):
    """Inspeccionar > Mapa de entorno: cromo espejado que refleja un estudio procedural (cielo con
    degradé, horizonte marcado, piso oscuro y dos softboxes). `rotacion` (grados) gira el entorno
    alrededor de `arriba`, como el control "Girar". Vectorizado: se recalcula con cada cámara."""
    _n, _v, r = _reflejo(normales, direccion_vista)
    up = _unitario(arriba, "dirección arriba")
    e1 = np.cross(up, (1.0, 0.0, 0.0) if abs(up[0]) < 0.9 else (0.0, 1.0, 0.0))
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(up, e1)
    elev = np.clip(r @ up, -1.0, 1.0)
    azim = np.arctan2(r @ e2, r @ e1) + math.radians(rotacion)
    alto = np.abs(elev)[:, None]
    cielo = (1 - alto ** 0.6) * np.array([0.93, 0.94, 0.96]) + alto ** 0.6 * np.array([0.30, 0.50, 0.80])
    piso = (1 - alto ** 0.5) * np.array([0.42, 0.40, 0.37]) + alto ** 0.5 * np.array([0.10, 0.09, 0.09])
    col = np.where(elev[:, None] >= 0, cielo, piso)
    # Línea de horizonte nítida (lo que hace "leer" la continuidad en un cromo).
    col *= (1.0 - 0.35 * (1.0 - _suave(0.0, 0.03, alto)))
    # Dos softboxes rectangulares.
    luz = np.zeros(len(elev))
    for az0 in (math.radians(45.0), math.radians(225.0)):
        dif = np.abs((azim - az0 + math.pi) % (2 * math.pi) - math.pi)
        caja = (1 - _suave(0.25, 0.32, dif)) * _suave(0.25, 0.30, elev) * (1 - _suave(0.70, 0.75, elev))
        luz = np.maximum(luz, caja)
    col = col * (1 - luz[:, None]) + luz[:, None] * 1.0
    return np.clip(col, 0.0, 1.0).astype(np.float32)


# ---------------------------------------------------------------- peine de curvatura
def _lista_aristas(aristas):
    if isinstance(aristas, TopoDS_Shape):
        if aristas.ShapeType() == TopAbs_EDGE:
            return [TopoDS.Edge(aristas)]
        return _aristas_unicas(aristas)
    salida = []
    for a in aristas:
        salida.extend(_lista_aristas(a))
    return salida


def peine_curvatura(aristas, *, densidad=30, escala=1.0):
    """Inspeccionar > Análisis de peine de curvatura sobre aristas (una arista, lista o forma).

    Devuelve {"puas": Mx2x3 (base, punta), "envolventes": [Kx3 por arista], "curvaturas": [K por arista],
    "factor": mm por (1/mm)}. `densidad` = púas por arista (2..100). Las púas salen del lado opuesto al
    centro de curvatura con largo κ·factor; factor = escala·20 % de la diagonal / κ máxima (relativa,
    como el control "Escala" de Fusion).
    """
    densidad = int(np.clip(densidad, 2, 100))
    muestras = []
    for arista in _lista_aristas(aristas):
        if BRep_Tool.Degenerated_s(arista):
            continue
        curva = BRepAdaptor_Curve(arista)
        props = BRepLProp_CLProps(curva, 2, 1e-9)
        pts, dirs, ks = [], [], []
        for t in np.linspace(curva.FirstParameter(), curva.LastParameter(), densidad):
            props.SetParameter(float(t))
            p = _np(props.Value())
            k, n = 0.0, np.zeros(3)
            if props.IsTangentDefined():
                k = props.Curvature()
                if k > 1e-12:
                    c = gp_Pnt()
                    props.CentreOfCurvature(c)
                    n = _unitario(_np(c) - p)
            pts.append(p)
            dirs.append(n)
            ks.append(k)
        muestras.append((np.array(pts), np.array(dirs), np.array(ks)))
    if not muestras:
        raise geo.ErrorGeometria("No hay aristas para el peine de curvatura.")
    todos = np.concatenate([m[0] for m in muestras])
    diag = float(np.linalg.norm(todos.max(axis=0) - todos.min(axis=0))) or 1.0
    kmax = max(float(m[2].max()) for m in muestras)
    factor = float(escala) * 0.2 * diag / kmax if kmax > 1e-12 else 0.0
    puas, envolventes = [], []
    for pts, dirs, ks in muestras:
        puntas = pts - dirs * (ks * factor)[:, None]
        puas.append(np.stack([pts, puntas], axis=1))
        envolventes.append(puntas.astype(np.float32))
    return {"puas": np.concatenate(puas).astype(np.float32), "envolventes": envolventes,
            "curvaturas": [m[2].astype(np.float32) for m in muestras], "factor": factor}


# ---------------------------------------------------------------- isocurvas
def _isocurva(sup, clasif, fijo, desde, hasta, puntos, en_u):
    """Tramos de una isocurva dentro del dominio de la cara (bordes ajustados por bisección)."""
    def uv(t):
        return (t, fijo) if en_u else (fijo, t)

    def adentro(t):
        return clasif.Perform(gp_Pnt2d(*uv(t)), True) != TopAbs_OUT

    def borde(t_in, t_out):
        for _ in range(12):
            m = 0.5 * (t_in + t_out)
            if adentro(m):
                t_in = m
            else:
                t_out = m
        return t_in

    ts = np.linspace(desde, hasta, puntos)
    dentro = [adentro(t) for t in ts]
    tramos, actual = [], []
    for i, t in enumerate(ts):
        if dentro[i]:
            if not actual and i > 0:
                actual.append(borde(t, ts[i - 1]))
            actual.append(t)
        elif actual:
            actual.append(borde(ts[i - 1], t))
            tramos.append(actual)
            actual = []
    if actual:
        tramos.append(actual)
    return [np.array([_np(sup.Value(*uv(t))) for t in tramo], np.float32) for tramo in tramos if len(tramo) >= 2]


def isocurvas(forma, *, n_u=10, n_v=10, puntos=48):
    """Inspeccionar > Análisis de isocurvas → {"u": [Kx3], "v": [Kx3]}.

    "u": curvas que corren en dirección U (v constante), `n_u` por cara; "v": las que corren en V.
    Recortadas al dominio de la cara de forma aproximada (muestreo + bisección del borde).
    """
    salida = {"u": [], "v": []}
    for cara in geo.caras(forma):
        sup = BRepAdaptor_Surface(cara)
        u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
        if not all(map(math.isfinite, (u0, u1, v0, v1))):
            continue
        clasif = IntTools_FClass2d(cara, 1e-7)
        for j in range(1, n_u + 1):
            salida["u"] += _isocurva(sup, clasif, v0 + (v1 - v0) * j / (n_u + 1), u0, u1, puntos, True)
        for j in range(1, n_v + 1):
            salida["v"] += _isocurva(sup, clasif, u0 + (u1 - u0) * j / (n_v + 1), v0, v1, puntos, False)
    return salida


# ---------------------------------------------------------------- sección
def _tamano(forma, plano):
    caja = geo.caja_envolvente(forma)
    if caja is None:
        raise geo.ErrorGeometria("La forma está vacía.")
    lo, hi = np.array(caja[0]), np.array(caja[1])
    centro = (lo + hi) / 2
    largo = float(np.linalg.norm(hi - lo)) + abs(float((centro - plano.origen) @ plano.normal)) + 1.0
    return centro - plano.normal * float((centro - plano.origen) @ plano.normal), 2 * largo


def seccion(forma, plano):
    """Inspeccionar > Análisis de sección: el corte de la forma por `plano` (geo.Plano).

    {"polilineas": [Kx3] del contorno (BRepAlgoAPI_Section), "largo" del contorno, "cara": caras de corte
    (forma OCC, para sombrear con rayado), "area", "triangulos": Tx3x3 de la cara de corte}.
    """
    # Ejes del gp_Pln = ejes u, v del plano: así los parámetros de la lámina coinciden con plano.a_uv.
    pln = gp_Pln(gp_Ax3(gp_Pnt(*map(float, plano.origen)), gp_Dir(*map(float, plano.normal)),
                        gp_Dir(*map(float, plano.u))))
    op = BRepAlgoAPI_Section(forma, pln, False)
    op.Build()
    if not op.IsDone():
        raise geo.ErrorGeometria("El kernel no pudo calcular la sección.")
    contorno = op.Shape()
    centro, lado = _tamano(forma, plano)
    u0, v0 = plano.a_uv(centro)
    lamina = BRepBuilderAPI_MakeFace(pln, u0 - lado, u0 + lado, v0 - lado, v0 + lado).Face()
    cara = geo.booleano(forma, lamina, "intersecar")
    vacia = geo.esta_vacia(cara)
    tris = [t for _c, t in geo.teselar_por_cara(cara)] if not vacia else []
    return {"polilineas": geo.polilineas_aristas(contorno), "largo": _largo(contorno),
            "cara": None if vacia else cara, "area": 0.0 if vacia else geo.area(cara),
            "triangulos": np.concatenate(tris).astype(np.float32) if tris else np.zeros((0, 3, 3), np.float32)}


def cortar_medio_espacio(forma, plano, *, invertir=False):
    """La parte de la forma "detrás" del plano (lado opuesto a la normal), para mostrar el corte como el
    Análisis de sección. `invertir=True` = "Voltear": conserva el lado de la normal."""
    centro, lado = _tamano(forma, plano)
    n = -plano.normal if invertir else plano.normal
    esquina = centro - plano.u * lado - np.cross(n, plano.u) * lado - n * lado
    caja = BRepPrimAPI_MakeBox(gp_Ax2(gp_Pnt(*map(float, esquina)), gp_Dir(*map(float, n)),
                                      gp_Dir(*map(float, plano.u))), 2 * lado, 2 * lado, lado).Shape()
    return geo.booleano(forma, caja, "intersecar")
