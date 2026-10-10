# -*- coding: utf-8 -*-
"""
SÓLIDO › MODIFICAR de Fusion sobre OpenCascade: empalme, chaflán, vaciado, desmoldeo, escala,
desfase / reemplazo / división de caras, división de cuerpo, división por silueta, mover/alinear y
supresión de caras (modelado directo).

Funciones puras: reciben formas OCC, numpy, `geo.Plano` o números y devuelven formas OCC (o
matrices 4x4 numpy). Milímetros y grados. Los errores salen como `geo.ErrorGeometria`.

Límites del kernel (no los tiene OpenCascade, no se emulan):
- Empalme: sin esquina "Setback", sin continuidad G2, sin radio asimétrico ni "Full Round".
  OpenCascade SIEMPRE propaga el empalme/chaflán por la cadena tangente de la arista
  (`cadena_tangente=False` no puede cortarla).
- Chaflán: la esquina es siempre tipo "Chamfer" (cara triangular); "Miter" y "Blend" no existen.
- Desmoldeo: solo caras planas, cilíndricas o cónicas (BRepOffsetAPI_DraftAngle); sin "Parting Line".
"""
import math

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Curve2d, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Defeaturing, BRepAlgoAPI_Section, BRepAlgoAPI_Splitter
from OCP.BRepBuilderAPI import (BRepBuilderAPI_GTransform, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace,
                                BRepBuilderAPI_MakeVertex, BRepBuilderAPI_Transform)
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepFeat import BRepFeat_SplitShape
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer, BRepFilletAPI_MakeFillet
from OCP.BRepGProp import BRepGProp_Face
from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
from OCP.BRepLib import BRepLib
from OCP.BRepOffset import BRepOffset_Analyse, BRepOffset_MakeOffset, BRepOffset_Skin
from OCP.BRepOffsetAPI import (BRepOffsetAPI_DraftAngle, BRepOffsetAPI_MakeOffsetShape,
                               BRepOffsetAPI_MakeThickSolid)
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepTools import BRepTools
from OCP.ChFiDS import ChFiDS_Concave, ChFiDS_Convex, ChFiDS_Tangential
from OCP.Geom2dAPI import Geom2dAPI_PointsToBSpline
from OCP.GeomAbs import (GeomAbs_Arc, GeomAbs_C2, GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Intersection,
                         GeomAbs_Plane, GeomAbs_Sphere, GeomAbs_Torus)
from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
from OCP.OCP.collections import (Array1_gp_Pnt2d, IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher,
                                 IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher, List_TopoDS_Shape)
from OCP.ShapeFix import ShapeFix_Shape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Face, TopoDS_Shape
from OCP.gp import (gp_Ax3, gp_Cylinder, gp_Dir, gp_GTrsf, gp_Lin, gp_Mat, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Trsf,
                    gp_Vec, gp_XYZ)

from . import geometria as geo

TOL = 1e-6


# ---------------------------------------------------------------- utilidades internas
def _np(p):
    return np.array([p.X(), p.Y(), p.Z()], float)


def _unicos(forma, tipo):
    mapa = IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapes_s(forma, tipo, mapa)
    return [mapa.FindKey(i) for i in range(1, mapa.Size() + 1)]


def _aristas(forma):
    return [TopoDS.Edge(e) for e in _unicos(forma, TopAbs_EDGE)]


def _ancestros(forma, tipo_hijo, tipo_padre):
    mapa = IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapesAndAncestors_s(forma, tipo_hijo, tipo_padre, mapa)
    return mapa


def _padres(mapa, hijo):
    """Padres únicos (sin repetir la cara de una arista de costura) en el orden del mapa."""
    if not mapa.Contains(hijo):
        return []
    salida = []
    for p in mapa.FindFromKey(hijo):
        if not any(p.IsSame(q) for q in salida):
            salida.append(p)
    return salida


def _contiene(lista, forma):
    return any(forma.IsSame(x) for x in lista)


def _lista_occ(formas):
    lista = List_TopoDS_Shape()
    for f in formas:
        lista.Append(f)
    return lista


def _diagonal(forma):
    caja = geo.caja_envolvente(forma)
    if caja is None:
        raise geo.ErrorGeometria("La forma está vacía.")
    return float(np.linalg.norm(np.subtract(caja[1], caja[0]))) or 1.0


def _centro(forma):
    p0, p1 = geo.caja_envolvente(forma)
    return (np.array(p0) + np.array(p1)) / 2


def _unificar(forma):
    """Junta caras y aristas coplanares que dejan los booleanos (como Fusion, que no deja costuras)."""
    u = ShapeUpgrade_UnifySameDomain(forma, True, True, False)
    u.Build()
    return u.Shape()


def _fusionar_costuras(forma):
    """Tras partir caras periódicas (cilindro, toro) la costura del kernel deja una cara de más:
    se vuelven a unir las piezas de la misma superficie SOLO a través de aristas de costura."""
    u = ShapeUpgrade_UnifySameDomain(forma, True, True, False)
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    for e in _aristas(forma):
        if not any(BRep_Tool.IsClosed_s(e, TopoDS.Face(f)) for f in _padres(arista_caras, e)):
            u.KeepShape(e)
    u.Build()
    return u.Shape()


def _validar(forma, operacion):
    if forma is None or forma.IsNull() or geo.esta_vacia(forma):
        raise geo.ErrorGeometria(f"{operacion}: el kernel devolvió una forma vacía.")
    if not geo.es_valida(forma):
        arreglo = ShapeFix_Shape(forma)
        arreglo.Perform()
        forma = arreglo.Shape()
        if not geo.es_valida(forma):
            raise geo.ErrorGeometria(f"{operacion}: el resultado no es un sólido válido.")
    return forma


def _normal_en(cara, u, v):
    """Punto y normal unitaria (respeta la orientación de la cara: apunta hacia afuera del material)."""
    p, n = gp_Pnt(), gp_Vec()
    BRepGProp_Face(cara).Normal(float(u), float(v), p, n)
    m = n.Magnitude()
    return _np(p), (_np(n) / m if m > 1e-12 else np.zeros(3))


def _punto_normal(cara):
    """Punto representativo de la cara (proyección del centroide) y su normal hacia afuera."""
    c = geo.centro_masa(cara, superficie=True)
    proy = GeomAPI_ProjectPointOnSurf(gp_Pnt(*c), BRep_Tool.Surface_s(cara))
    if proy.NbPoints() > 0:
        u, v = proy.LowerDistanceParameters()
    else:
        u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
        u, v = (u0 + u1) / 2, (v0 + v1) / 2
    return _normal_en(cara, u, v)


def _normal_en_arista(arista, cara, t):
    uv = BRepAdaptor_Curve2d(arista, cara).Value(t)
    return _normal_en(cara, uv.X(), uv.Y())[1]


def _plano_de_cara(cara):
    """geo.Plano de una cara plana con la normal hacia afuera del material (None si no es plana)."""
    if BRepAdaptor_Surface(cara).GetType() != GeomAbs_Plane:
        return None
    p, n = _punto_normal(cara)
    return geo.Plano.desde_marco(p, n, (1.0, 0.0, 0.0))


def _cara_plana(plano, centro, semilado):
    """Cara rectangular grande sobre `plano`, centrada en la proyección de `centro`."""
    c = np.asarray(centro, float)
    c = c - plano.normal * float((c - plano.origen) @ plano.normal)
    ax3 = gp_Ax3(gp_Pnt(*c), gp_Dir(*plano.normal), gp_Dir(*plano.u))
    s = float(semilado)
    return BRepBuilderAPI_MakeFace(gp_Pln(ax3), -s, s, -s, s).Face()


def _cara_extendida(cara, valor):
    salida = TopoDS_Face()
    try:
        BRepLib.ExtendFace_s(cara, float(valor), True, True, True, True, salida)
    except Exception:  # noqa: BLE001 — superficies que no admiten extensión: se usa la original
        return cara
    return cara if salida.IsNull() else salida


def _herramienta_corte(herramienta, forma, extender):
    """Plano → cara grande; cara → cara (extendida si se pide); aristas/cuerpo → tal cual."""
    diag = _diagonal(forma)
    if isinstance(herramienta, geo.Plano):
        return _cara_plana(herramienta, _centro(forma), 2 * diag)
    if isinstance(herramienta, (list, tuple)):
        return geo.compuesto(list(herramienta))
    if isinstance(herramienta, TopoDS_Shape):
        if herramienta.ShapeType() == TopAbs_FACE:
            cara = TopoDS.Face(herramienta)
            if extender:
                if BRepAdaptor_Surface(cara).GetType() == GeomAbs_Plane:
                    return _cara_plana(_plano_de_cara(cara), _centro(forma), 2 * diag)
                return _cara_extendida(cara, 2 * diag)
            return cara
        return herramienta
    raise geo.ErrorGeometria("Herramienta de división no reconocida (plano, cara, aristas o cuerpo).")


def _partir(forma, herramientas):
    """BRepAlgoAPI_Splitter: parte `forma` con las herramientas (General Fuse)."""
    sp = BRepAlgoAPI_Splitter()
    sp.SetArguments(_lista_occ([forma]))
    sp.SetTools(_lista_occ(herramientas))
    sp.Build()
    if not sp.IsDone():
        raise geo.ErrorGeometria("La división falló en el kernel.")
    return sp.Shape()


def _tangente_en_vertice(arista, vertice):
    t = BRep_Tool.Parameter_s(TopoDS.Vertex(vertice), arista)
    p, v = gp_Pnt(), gp_Vec()
    BRepAdaptor_Curve(arista).D1(t, p, v)
    m = v.Magnitude()
    return _np(v) / m if m > 1e-12 else np.zeros(3)


def _analisis(forma, tol_ang):
    return BRepOffset_Analyse(forma, math.radians(tol_ang))


def _tipos_arista(analisis, arista):
    return {iv.Type() for iv in analisis.Type(arista)}


# ---------------------------------------------------------------- selección (cadenas tangentes)
def aristas_cadena_tangente(forma, arista, tol_ang=1.0):
    """Aristas unidas a `arista` con continuidad tangente en sus vértices (opción "Tangent Chain")."""
    vert_aristas = _ancestros(forma, TopAbs_VERTEX, TopAbs_EDGE)
    cadena, pendientes = [arista], [arista]
    sen_tol = math.sin(math.radians(tol_ang))
    while pendientes:
        e = pendientes.pop(0)
        for v in _unicos(e, TopAbs_VERTEX):
            te = _tangente_en_vertice(e, v)
            for otra in _padres(vert_aristas, v):
                otra = TopoDS.Edge(otra)
                if _contiene(cadena, otra) or BRep_Tool.Degenerated_s(otra):
                    continue
                if np.linalg.norm(np.cross(te, _tangente_en_vertice(otra, v))) < sen_tol:
                    cadena.append(otra)
                    pendientes.append(otra)
    return cadena


def caras_tangentes(forma, cara, tol_ang=1.0):
    """Cara + todas las caras unidas a ella por aristas tangentes (cadena de caras tangentes)."""
    analisis = _analisis(forma, tol_ang)
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    cadena, pendientes = [cara], [cara]
    while pendientes:
        f = pendientes.pop(0)
        for e in _unicos(f, TopAbs_EDGE):
            e = TopoDS.Edge(e)
            if ChFiDS_Tangential not in _tipos_arista(analisis, e):
                continue
            for otra in _padres(arista_caras, e):
                if not _contiene(cadena, otra):
                    cadena.append(TopoDS.Face(otra))
                    pendientes.append(TopoDS.Face(otra))
    return cadena


def _ampliar_tangentes(forma, aristas, activo):
    if not activo:
        return list(aristas)
    salida = []
    for a in aristas:
        for e in aristas_cadena_tangente(forma, a):
            if not _contiene(salida, e):
                salida.append(e)
    return salida


# ---------------------------------------------------------------- empalme
def _angulo_entre_caras(forma, arista):
    """Ángulo (rad) entre las normales de las dos caras de la arista, en su punto medio."""
    caras = _padres(_ancestros(forma, TopAbs_EDGE, TopAbs_FACE), arista)
    if len(caras) != 2:
        raise geo.ErrorGeometria("La arista no separa exactamente dos caras.")
    c = BRepAdaptor_Curve(arista)
    t = (c.FirstParameter() + c.LastParameter()) / 2
    n1 = _normal_en_arista(arista, TopoDS.Face(caras[0]), t)
    n2 = _normal_en_arista(arista, TopoDS.Face(caras[1]), t)
    return math.acos(max(-1.0, min(1.0, float(n1 @ n2))))


def empalme(forma, grupos, *, cadena_tangente=True):
    """Empalme (Fillet, tipo Fillet) por conjuntos de selección, cada uno con su tipo de radio.

    grupos: [{"aristas": [TopoDS_Edge], "tipo": "constante" | "variable" | "cuerda",
              "radio": r, "radios": [(posición 0..1, r), ...], "cuerda": c}]
    "cuerda" (Chord Length): radio = c / (2·sen(φ/2)), φ = ángulo entre normales en el medio de la arista.
    "variable": la posición se mide sobre cada arista (0 = inicio, 1 = fin), como los Radius Points.
    """
    if not grupos:
        raise geo.ErrorGeometria("Elegí al menos una arista para empalmar.")
    mf = BRepFilletAPI_MakeFillet(forma)
    for grupo in grupos:
        tipo = grupo.get("tipo", "constante")
        aristas = _ampliar_tangentes(forma, grupo.get("aristas") or [], cadena_tangente)
        if not aristas:
            raise geo.ErrorGeometria("Un conjunto de empalme no tiene aristas.")
        for e in aristas:
            if mf.Contour(e):           # ya está en un contorno (OpenCascade propaga por tangencia)
                continue
            if tipo == "constante":
                r = float(grupo.get("radio", 0))
                if r <= 0:
                    raise geo.ErrorGeometria("El radio del empalme debe ser positivo.")
                mf.Add(r, e)
            elif tipo == "cuerda":
                c = float(grupo.get("cuerda", 0))
                phi = _angulo_entre_caras(forma, e)
                if c <= 0 or phi < 1e-6:
                    raise geo.ErrorGeometria("La cuerda debe ser positiva y la arista no puede ser tangente.")
                mf.Add(c / (2 * math.sin(phi / 2)), e)
            elif tipo == "variable":
                puntos = sorted((float(u), float(r)) for u, r in grupo.get("radios", []))
                if len(puntos) < 2 or puntos[0][0] < 0 or puntos[-1][0] > 1 or min(r for _, r in puntos) <= 0:
                    raise geo.ErrorGeometria("El radio variable necesita ≥ 2 puntos con posición 0..1 y radio > 0.")
                arr = Array1_gp_Pnt2d(1, len(puntos))
                for i, (u, r) in enumerate(puntos, 1):
                    arr.SetValue(i, gp_Pnt2d(u, r))
                mf.Add(arr, e)
            else:
                raise geo.ErrorGeometria(f"Tipo de radio desconocido: {tipo}")
    if mf.NbContours() == 0:
        raise geo.ErrorGeometria("Las aristas elegidas no pertenecen al cuerpo.")
    try:
        mf.Build()
    except Exception:  # noqa: BLE001 — StdFail_NotDone
        pass
    if not mf.IsDone():
        raise geo.ErrorGeometria("El empalme falló: el radio es demasiado grande para las caras vecinas.")
    return _validar(mf.Shape(), "Empalme")


def empalme_reglas(forma, caras_a, caras_b=None, *, radio, tipo="todas", redondeos="ambos"):
    """Rule Fillet: "todas" = todas las aristas de caras_a; "entre" = aristas compartidas entre
    caras_a y caras_b. redondeos: "ambos" | "redondeos" (solo convexas) | "empalmes" (solo cóncavas)."""
    if tipo not in ("todas", "entre"):
        raise geo.ErrorGeometria(f"Regla desconocida: {tipo}")
    if tipo == "entre" and not caras_b:
        raise geo.ErrorGeometria("La regla 'entre' necesita dos conjuntos de caras.")
    filtro = {"ambos": {ChFiDS_Convex, ChFiDS_Concave}, "redondeos": {ChFiDS_Convex},
              "empalmes": {ChFiDS_Concave}}.get(redondeos)
    if filtro is None:
        raise geo.ErrorGeometria(f"Opción Rounds/Fillets desconocida: {redondeos}")
    analisis = _analisis(forma, 1.0)
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    elegidas = []
    for e in _aristas(forma):
        caras = _padres(arista_caras, e)
        if len(caras) != 2 or BRep_Tool.Degenerated_s(e) or not (_tipos_arista(analisis, e) & filtro):
            continue
        en_a = [_contiene(caras_a, f) for f in caras]
        if tipo == "todas":
            ok = any(en_a)
        else:
            en_b = [_contiene(caras_b, f) for f in caras]
            ok = (en_a[0] and en_b[1]) or (en_a[1] and en_b[0])
        if ok:
            elegidas.append(e)
    if not elegidas:
        raise geo.ErrorGeometria("La regla no encontró aristas para empalmar.")
    return empalme(forma, [{"aristas": elegidas, "tipo": "constante", "radio": radio}], cadena_tangente=False)


# ---------------------------------------------------------------- chaflán
def chaflan(forma, grupos, *, cadena_tangente=True):
    """Chaflán (Chamfer) por conjuntos de selección.

    grupos: [{"aristas": [TopoDS_Edge], "tipo": "distancia_igual" | "dos_distancias" | "distancia_angulo",
              "distancia": d (d1), "distancia2": d2, "angulo": grados, "cara": TopoDS_Face opcional,
              "voltear": bool}]
    "cara" es el lado donde se mide la primera distancia; si no viene se toma la primera cara vecina
    de la arista (orden estable del kernel) y "voltear" pasa a la otra (botón Flip de Fusion).
    Esquina: siempre tipo "Chamfer" (Miter/Blend no existen en OpenCascade).
    """
    if not grupos:
        raise geo.ErrorGeometria("Elegí al menos una arista para el chaflán.")
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    mc = BRepFilletAPI_MakeChamfer(forma)
    for grupo in grupos:
        tipo = grupo.get("tipo", "distancia_igual")
        d1 = float(grupo.get("distancia", 0))
        if d1 <= 0:
            raise geo.ErrorGeometria("La distancia del chaflán debe ser positiva.")
        aristas = _ampliar_tangentes(forma, grupo.get("aristas") or [], cadena_tangente)
        if not aristas:
            raise geo.ErrorGeometria("Un conjunto de chaflán no tiene aristas.")
        for e in aristas:
            if mc.Contour(e):
                continue
            if tipo == "distancia_igual":
                mc.Add(d1, e)
                continue
            vecinas = _padres(arista_caras, e)
            if len(vecinas) != 2:
                raise geo.ErrorGeometria("La arista del chaflán no separa dos caras.")
            cara = grupo.get("cara")
            if cara is None or not _contiene(vecinas, cara):
                cara = vecinas[0]
            if grupo.get("voltear"):
                cara = vecinas[1] if cara.IsSame(vecinas[0]) else vecinas[0]
            cara = TopoDS.Face(cara)
            if tipo == "dos_distancias":
                d2 = float(grupo.get("distancia2", 0))
                if d2 <= 0:
                    raise geo.ErrorGeometria("La segunda distancia del chaflán debe ser positiva.")
                mc.Add(d1, d2, e, cara)
            elif tipo == "distancia_angulo":
                ang = float(grupo.get("angulo", 45.0))
                if not 0 < ang < 90:
                    raise geo.ErrorGeometria("El ángulo del chaflán debe estar entre 0 y 90 grados.")
                mc.AddDA(d1, math.radians(ang), e, cara)
            else:
                raise geo.ErrorGeometria(f"Tipo de chaflán desconocido: {tipo}")
    if mc.NbContours() == 0:
        raise geo.ErrorGeometria("Las aristas elegidas no pertenecen al cuerpo.")
    try:
        mc.Build()
    except Exception:  # noqa: BLE001 — StdFail_NotDone
        pass
    if not mc.IsDone():
        raise geo.ErrorGeometria("El chaflán falló: la distancia es demasiado grande para las caras vecinas.")
    return _validar(mc.Shape(), "Chaflán")


# ---------------------------------------------------------------- vaciado
def _cara_sigue_puesta(resultado, cara, espesor):
    """True si la cara quitada sigue tapando el resultado. Se mira el punto central de la cara: en un vaciado bien
    hecho queda en la abertura, lejos de las paredes. Solo se decide si ese punto cae dentro de la cara y a más de
    cuatro espesores de su borde (más cerca, el canto de una pared inclinada puede taparlo con razón)."""
    p, _ = _punto_normal(cara)
    v = BRepBuilderAPI_MakeVertex(gp_Pnt(*p)).Vertex()
    if not geo.se_tocan(v, cara, 1e-5) or geo.se_tocan(v, geo.compuesto(_aristas(cara)), 4 * espesor):
        return False
    return geo.se_tocan(v, resultado, 1e-5)


def _medida_minima(forma):
    """La medida más chica de la caja envolvente de `forma` (mm)."""
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(forma)
    return min(x1 - x0, y1 - y0, z1 - z0)


def _demasiado_grueso(forma, espesor, hueco=False):
    """Mensaje si el espesor no entra en la pieza (None si entra): con caras quitadas, una pared no puede ser más
    gruesa que la medida más chica de la caja envolvente; en un hueco cerrado, ni la mitad (las dos paredes de
    enfrente se tocan y no queda cavidad)."""
    medida = _medida_minima(forma)
    limite = medida / 2 if hueco else medida
    if abs(espesor) < limite - 1e-9:
        return None
    if hueco:
        return (f"El vaciado falló: el espesor ({abs(espesor):g} mm) es demasiado grande para un hueco cerrado: tiene "
                f"que ser menor que la mitad de la medida más chica de la pieza ({medida:g} mm).")
    return (f"El vaciado falló: el espesor ({abs(espesor):g} mm) es demasiado grande para la pieza (su medida más "
            f"chica es {medida:g} mm).")


def _resultado_imposible(forma, resultado, espesor):
    """True si lo que devolvió el kernel no puede ser el vaciado de `forma`: volumen cero o negativo (un sólido «al
    revés»), o material fuera de donde puede quedar la pared (hacia adentro, dentro de la caja de la pieza y con menos
    volumen que ella; hacia afuera, dentro de la caja agrandada en el espesor). Pasaba sin error: una caja de
    40 × 40 × 10 vaciada 25 mm salía más alta y con más volumen; un prisma con cortes cerca de la cara quitada, con
    volumen negativo."""
    despues = geo.volumen_exacto(resultado)
    if despues <= 0:
        return True
    caja, caja_r = geo.caja_envolvente(forma), geo.caja_envolvente(resultado)
    if caja_r is None:
        return True
    holgura = max(0.0, espesor) + max(1e-4 * math.dist(*caja), 1e-5)
    if any(r < a - holgura for r, a in zip(caja_r[0], caja[0], strict=True)) or \
            any(r > b + holgura for r, b in zip(caja_r[1], caja[1], strict=True)):
        return True
    return espesor < 0 and despues > geo.volumen_exacto(forma) * (1 + 1e-9)


def _falla_kernel(forma, espesor, hueco=False):
    """Mensaje para un vaciado que el kernel no hizo (o hizo mal) con un espesor que, en principio, entra."""
    return _demasiado_grueso(forma, espesor, hueco) or (
        f"El vaciado falló: el kernel no pudo hacerlo con {abs(espesor):g} mm en esta geometría (¿una pared, un "
        "empalme o el hueco entre un corte y la cara quitada más finos que el espesor?). Probá un espesor menor o "
        "vaciar antes de cortar.")


def _cascara(forma, caras, espesor, union):
    ts = BRepOffsetAPI_MakeThickSolid()
    try:
        ts.MakeThickSolidByJoin(forma, _lista_occ(caras), float(espesor), TOL, BRepOffset_Skin, False, False, union)
        ts.Build()
    except Exception as e:  # noqa: BLE001 — p. ej. Standard_NoSuchObject «BRep_Tool:: no parameter on edge»
        raise geo.ErrorGeometria(_demasiado_grueso(forma, espesor) or
                                 "El vaciado falló: el kernel no pudo con ese espesor en esta geometría. Probá otro "
                                 "espesor o vaciar antes de cortar.") from e
    if not ts.IsDone():
        raise geo.ErrorGeometria(_falla_kernel(forma, espesor))
    resultado = ts.Shape()
    if _resultado_imposible(forma, resultado, espesor):
        raise geo.ErrorGeometria(_falla_kernel(forma, espesor))
    # Con cortes que cruzan la cara quitada, MakeThickSolid puede dar IsDone y devolver el cuerpo tal cual o apenas
    # tocado, con la cara todavía puesta. La historia no sirve para verlo: en un vaciado bien hecho también da la
    # cara quitada por «modificada» y no por borrada.
    antes = geo.volumen_exacto(forma)
    if (abs(geo.volumen_exacto(resultado) - antes) <= 1e-9 * abs(antes)
            or any(_cara_sigue_puesta(resultado, c, abs(espesor)) for c in caras)):
        raise geo.ErrorGeometria(_demasiado_grueso(forma, espesor) or
                                 "El vaciado falló: el kernel no pudo quitar esas caras (¿cortes o agujeros que "
                                 "cruzan la cara quitada?). Probá otro espesor o vaciar antes de cortar.")
    return resultado


def _desfase_cuerpo(forma, distancia, union):
    """El cuerpo desfasado `distancia` (negativa = hacia adentro) para un hueco cerrado. Hacia adentro, si el
    espesor no deja cavidad falla antes de llamar al kernel (devolvía el cuerpo sin cambios o un error del corte)."""
    if distancia < 0 and (mensaje := _demasiado_grueso(forma, distancia, hueco=True)):
        raise geo.ErrorGeometria(mensaje)
    mo = BRepOffsetAPI_MakeOffsetShape()
    try:
        mo.PerformByJoin(forma, float(distancia), TOL, BRepOffset_Skin, False, False, union)
    except Exception as e:  # noqa: BLE001 — fallos de OCC sin texto útil
        raise geo.ErrorGeometria(_falla_kernel(forma, distancia, hueco=True)) from e
    if not mo.IsDone():
        raise geo.ErrorGeometria(_falla_kernel(forma, distancia, hueco=True))
    desfasado = mo.Shape()
    antes, despues = geo.volumen_exacto(forma), geo.volumen_exacto(desfasado)
    if (_resultado_imposible(forma, desfasado, distancia) or (distancia < 0 and despues >= antes)
            or (distancia > 0 and despues <= antes)):
        raise geo.ErrorGeometria(_falla_kernel(forma, distancia, hueco=True))
    return desfasado


def vaciado(forma, caras_quitar, *, espesor_interior, espesor_exterior=0.0, direccion="interior",
            tangente=True, tipo="afilado"):
    """Vaciado (Shell): quita `caras_quitar` y deja paredes de espesor constante.

    direccion: "interior" | "exterior" | "ambos" (usa espesor_interior / espesor_exterior).
    Sin caras = cuerpo hueco cerrado (cavidad interna, opción Body de Fusion).
    tangente: suma las caras tangentes a las elegidas (Tangent Chain).
    tipo: "afilado" (Sharp Offset) | "redondeado" (Rounded Offset).
    """
    if direccion not in ("interior", "exterior", "ambos"):
        raise geo.ErrorGeometria(f"Dirección de vaciado desconocida: {direccion}")
    union = {"afilado": GeomAbs_Intersection, "redondeado": GeomAbs_Arc}.get(tipo)
    if union is None:
        raise geo.ErrorGeometria(f"Tipo de vaciado desconocido: {tipo}")
    ti = float(espesor_interior) if direccion in ("interior", "ambos") else 0.0
    te = float(espesor_exterior) if direccion in ("exterior", "ambos") else 0.0
    if ti < 0 or te < 0 or (direccion != "exterior" and ti <= 0) or (direccion != "interior" and te <= 0):
        raise geo.ErrorGeometria("Los espesores del vaciado deben ser positivos.")
    caras = []
    for c in caras_quitar or []:
        for t in (caras_tangentes(forma, c) if tangente else [c]):
            if not _contiene(caras, t):
                caras.append(t)
    if caras:
        partes = []
        if ti:
            partes.append(_cascara(forma, caras, -ti, union))
        if te:
            partes.append(_cascara(forma, caras, te, union))
        resultado = partes[0] if len(partes) == 1 else _unificar(geo.unir_todos(partes))
    else:
        exterior = _desfase_cuerpo(forma, te, union) if te else forma
        interior = _desfase_cuerpo(forma, -ti, union) if ti else forma
        resultado = geo.booleano(exterior, interior, "cortar")
    return _validar(resultado, "Vaciado")


# ---------------------------------------------------------------- desmoldeo
def desmoldeo(forma, caras, direccion_extraccion, angulo, plano_neutro, *, lados="uno", angulo2=None):
    """Desmoldeo (Draft, tipo Fixed Plane): inclina las caras `angulo` grados alrededor de su
    intersección con `plano_neutro`. Ángulo positivo = el cuerpo se angosta hacia la dirección de
    extracción (se quita material del lado al que apunta). lados: "uno" | "dos" (angulo2 del otro
    lado) | "simetrico". En "dos"/"simetrico" las caras se parten primero por el plano neutro."""
    if lados not in ("uno", "dos", "simetrico"):
        raise geo.ErrorGeometria(f"Opción de lados desconocida: {lados}")
    if not caras:
        raise geo.ErrorGeometria("Elegí las caras a desmoldear.")
    d = np.asarray(direccion_extraccion, float)
    if np.linalg.norm(d) < 1e-12:
        raise geo.ErrorGeometria("La dirección de extracción no puede ser nula.")
    d = d / np.linalg.norm(d)
    a1 = float(angulo)
    a2 = a1 if lados == "simetrico" else (float(angulo2) if angulo2 is not None else None)
    if lados == "dos" and a2 is None:
        raise geo.ErrorGeometria("El desmoldeo de dos lados necesita el segundo ángulo.")
    pln = gp_Pln(gp_Pnt(*map(float, plano_neutro.origen)), gp_Dir(*map(float, plano_neutro.normal)))
    if lados == "uno":
        objetivo, trabajo = forma, [(c, d, a1) for c in caras]
    else:
        objetivo = dividir_cara(forma, caras, plano_neutro)
        piezas = []
        for c in caras:
            for f in geo.caras(objetivo):
                if _cara_dentro_de(f, c) and not _contiene(piezas, f):
                    piezas.append(f)
        trabajo = []
        for f in piezas:
            s = float((np.array(geo.centro_masa(f, True)) - plano_neutro.origen) @ d)
            trabajo.append((f, d, a1) if s >= 0 else (f, -d, a2))
    da = BRepOffsetAPI_DraftAngle(objetivo)
    for cara, direc, ang in trabajo:
        if abs(ang) < 1e-12:
            continue
        da.Add(cara, gp_Dir(*direc), math.radians(ang), pln)
        if not da.AddDone():
            raise geo.ErrorGeometria("Una cara no admite desmoldeo (solo planas, cilíndricas o cónicas, "
                                     "y no paralelas al plano neutro).")
    try:
        da.Build()
    except Exception:  # noqa: BLE001
        pass
    if not da.IsDone():
        raise geo.ErrorGeometria("El desmoldeo falló en el kernel (ángulo demasiado grande?).")
    return _validar(da.Shape(), "Desmoldeo")


def _cara_dentro_de(pieza, cara):
    """¿La pieza (resultado de partir) proviene de `cara`? Misma superficie y su centro sobre la cara."""
    if pieza.IsSame(cara):
        return True
    p, _ = _punto_normal(pieza)
    return geo.se_tocan(BRepBuilderAPI_MakeVertex(gp_Pnt(*p)).Vertex(), cara, 1e-5)


# ---------------------------------------------------------------- escala y transformaciones
def escalar(forma, punto, factor=None, factores=None):
    """Escala (Scale) desde `punto`: uniforme (`factor`) o no uniforme (`factores` = (sx, sy, sz))."""
    if (factor is None) == (factores is None):
        raise geo.ErrorGeometria("Indicá un factor uniforme o tres factores, no ambos.")
    p = np.asarray(punto, float)
    if factor is not None:
        if factor <= 0:
            raise geo.ErrorGeometria("El factor de escala debe ser positivo.")
        t = gp_Trsf()
        t.SetScale(gp_Pnt(*p), float(factor))
        return BRepBuilderAPI_Transform(forma, t, True).Shape()
    s = np.asarray(factores, float)
    if s.shape != (3,) or np.any(s <= 0):
        raise geo.ErrorGeometria("Los tres factores de escala deben ser positivos.")
    m = np.eye(4)
    m[:3, :3] = np.diag(s)
    m[:3, 3] = p - s * p
    return transformar(forma, m)


def matriz_traslacion(v):
    m = np.eye(4)
    m[:3, 3] = np.asarray(v, float)
    return m


def matriz_rotacion(punto, eje, angulo):
    """Rotación de `angulo` grados alrededor del eje (punto, dirección), regla de la mano derecha."""
    k = np.asarray(eje, float)
    if np.linalg.norm(k) < 1e-12:
        raise geo.ErrorGeometria("El eje de rotación no puede ser nulo.")
    k = k / np.linalg.norm(k)
    a = math.radians(float(angulo))
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    r = np.eye(3) + math.sin(a) * kx + (1 - math.cos(a)) * kx @ kx
    p = np.asarray(punto, float)
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = p - r @ p
    return m


def matriz_desde_puntos(p_origen, p_destino):
    """Point to Point de Move/Copy: traslación que lleva p_origen a p_destino."""
    return matriz_traslacion(np.asarray(p_destino, float) - np.asarray(p_origen, float))


def transformar(forma, matriz4x4):
    """Move/Copy con una matriz 4x4 (filas: [R | t]). Rígida o con escala uniforme → gp_Trsf (exacto);
    con escala no uniforme o corte → gp_GTrsf (convierte la geometría a B-spline)."""
    m = np.asarray(matriz4x4, float)
    if m.shape != (4, 4) or not np.allclose(m[3], (0, 0, 0, 1)):
        raise geo.ErrorGeometria("La matriz de transformación debe ser 4x4 afín (última fila 0 0 0 1).")
    r, t = m[:3, :3], m[:3, 3]
    det = float(np.linalg.det(r))
    if abs(det) < 1e-12:
        raise geo.ErrorGeometria("La matriz de transformación es singular.")
    s = math.copysign(abs(det) ** (1 / 3), det)       # escala con signo: un espejo es escala −1 · giro
    rot = r / s
    if np.allclose(rot.T @ rot, np.eye(3), atol=1e-9):
        tr = gp_Trsf()
        tr.SetValues(*rot[0], 0.0, *rot[1], 0.0, *rot[2], 0.0)
        if abs(s - 1) > 1e-12:
            esc = gp_Trsf()
            esc.SetScaleFactor(s)
            tr = esc.Multiplied(tr)
        mov = gp_Trsf()
        mov.SetTranslation(gp_Vec(*t))
        return BRepBuilderAPI_Transform(forma, mov.Multiplied(tr), True).Shape()
    gt = gp_GTrsf()
    gt.SetVectorialPart(gp_Mat(*r[0], *r[1], *r[2]))
    gt.SetTranslationPart(gp_XYZ(*t))
    return BRepBuilderAPI_GTransform(forma, gt, True).Shape()


def _rotacion_entre(a, b):
    """Matriz 3x3 de giro mínimo que lleva el vector unitario a sobre b."""
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    eje = np.cross(a, b)
    s, c = np.linalg.norm(eje), float(a @ b)
    if s < 1e-12:
        if c > 0:
            return np.eye(3)
        perp = np.cross(a, (1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0))
        return matriz_rotacion((0, 0, 0), perp, 180.0)[:3, :3]
    return matriz_rotacion((0, 0, 0), eje, math.degrees(math.atan2(s, c)))[:3, :3]


def _datos_alineacion(ref):
    tipo = ref.get("tipo")
    if tipo == "punto":
        return tipo, np.asarray(ref["punto"], float), None
    if tipo == "plano":
        if "plano" in ref:
            return tipo, np.asarray(ref["plano"].origen, float), np.asarray(ref["plano"].normal, float)
        return tipo, np.asarray(ref["origen"], float), np.asarray(ref["normal"], float)
    if tipo == "eje":
        return tipo, np.asarray(ref["punto"], float), np.asarray(ref["direccion"], float)
    raise geo.ErrorGeometria(f"Referencia de alineación desconocida: {tipo}")


def alinear(forma, origen, destino, *, voltear=False):
    """Align: devuelve (forma alineada o None si forma es None, matriz 4x4) que lleva origen sobre destino.

    origen/destino: {"tipo": "punto", "punto"} | {"tipo": "plano", "origen", "normal"} (o "plano": geo.Plano)
    | {"tipo": "eje", "punto", "direccion"}. Plano sobre plano queda ENFRENTADO (normales opuestas, como
    al apoyar una cara contra otra en Fusion); eje sobre eje queda con la misma dirección. `voltear`
    invierte el resultado 180° (Flip). Un punto puede ir a cualquier destino (se usa su punto/origen).
    """
    t_o, p_o, d_o = _datos_alineacion(origen)
    t_d, p_d, d_d = _datos_alineacion(destino)
    r = np.eye(3)
    if t_o != "punto":
        if t_o != t_d:
            raise geo.ErrorGeometria("Solo se alinea plano con plano, eje con eje o un punto con cualquier cosa.")
        objetivo = -d_d if t_o == "plano" else d_d
        r = _rotacion_entre(d_o, -objetivo if voltear else objetivo)
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = p_d - r @ p_o
    return (transformar(forma, m) if forma is not None else None), m


# ---------------------------------------------------------------- desfase y reemplazo de caras
def _cara_dada_vuelta(mo, forma, caras, resultado, dist):
    """True si el kernel desfasó una cara curva más que su radio y la «dio vuelta» por el eje: la cara nueva no queda
    a `dist` de la original (un cilindro de radio 10 achicado 12 mm salía de radio 2; un agujero de radio 5 llenado
    14,9 mm salía MÁS GRANDE, de radio 9,9) o el volumen cambia al revés de lo pedido (positivo agrega material)."""
    if geo.solidos(forma):          # en una superficie abierta el «volumen» no dice nada
        antes, despues = geo.volumen_exacto(forma), geo.volumen_exacto(resultado)
        if (dist > 0 and despues < antes) or (dist < 0 and despues > antes):
            return True
    for cara in caras:
        for nueva in mo.Generated(cara):
            medida = BRepExtrema_DistShapeShape(nueva, cara)
            medida.Perform()
            if medida.IsDone() and abs(medida.Value() - abs(dist)) > 1e-3 * abs(dist) + 1e-6:
                return True
    return False


def desfasar_caras(forma, caras, distancia, *, tangente=True):
    """Offset Face / Press Pull sobre caras: mueve las caras a lo largo de su normal (positivo = hacia
    afuera, agrega material) y extiende las vecinas. tangente: arrastra las caras tangentes."""
    if not caras:
        raise geo.ErrorGeometria("Elegí las caras a desfasar.")
    dist = float(distancia)
    if abs(dist) < 1e-9:
        return forma
    todas = []
    for c in caras:
        for t in (caras_tangentes(forma, c) if tangente else [c]):
            if not _contiene(todas, t):
                todas.append(t)
    resultado = None
    try:
        mo = BRepOffset_MakeOffset()
        mo.Initialize(forma, 0.0, TOL, BRepOffset_Skin, False, False, GeomAbs_Intersection, False, False)
        for c in todas:
            mo.SetOffsetOnFace(c, dist)
        mo.MakeOffsetShape()
        if mo.IsDone() and not mo.Shape().IsNull() and geo.es_valida(mo.Shape()) and not geo.esta_vacia(mo.Shape()):
            resultado = mo.Shape()
            dada_vuelta = _cara_dada_vuelta(mo, forma, todas, resultado, dist)
    except Exception:  # noqa: BLE001 — se intenta la alternativa por extrusión
        resultado = None
    if resultado is not None:
        if dada_vuelta:
            raise geo.ErrorGeometria(f"Desfase de caras: con {abs(dist):g} mm la cara se da vuelta: la distancia es igual "
                                     "o mayor que su radio de curvatura (un cilindro no se achica, ni un agujero se "
                                     "cierra, más que su radio). Probá una distancia menor.")
        return resultado
    planos = [_plano_de_cara(c) for c in todas]
    if any(p is None for p in planos):
        raise geo.ErrorGeometria("El desfase de caras falló en el kernel.")
    return _reemplazar(forma, [(c, p.desplazado(dist)) for c, p in zip(todas, planos, strict=True)],
                       operacion="Desfase de caras")


def _largo_extension(cara, destino, d, diag):
    if isinstance(destino, geo.Plano):
        dn = float(d @ destino.normal)
        if abs(dn) < 1e-9:
            raise geo.ErrorGeometria("El destino es perpendicular a la cara: no se puede extender hasta él.")
        ts = [abs(float((destino.origen - _np(BRep_Tool.Pnt_s(TopoDS.Vertex(v)))) @ destino.normal) / dn)
              for v in _unicos(cara, TopAbs_VERTEX)]
        return max(ts + [0.0]) + diag
    return 2 * (diag + _diagonal(destino))


def _cruce_rayo(punto, direccion, cara):
    """Parámetro (con signo) del cruce más cercano de la recta punto + t·dirección con la cara."""
    inter = BRepIntCurveSurface_Inter()
    inter.Init(cara, gp_Lin(gp_Pnt(*map(float, punto)), gp_Dir(*map(float, direccion))), 1e-7)
    ts = []
    while inter.More():
        ts.append(inter.W())
        inter.Next()
    ts = [t for t in ts if abs(t) > 1e-9]
    return min(ts, key=abs) if ts else None


def _reemplazar(forma, pares, operacion="Reemplazar cara"):
    """Replace Face por extrusión: cada cara origen se extruye a lo largo de su normal hacia afuera
    (lo que queda entre la cara y el destino se SUMA) y hacia adentro (se RESTA). `operacion` nombra el comando en
    los mensajes de error (también lo usa el desfase de caras)."""
    diag = _diagonal(forma)
    sumar, restar = [], []
    for cara, destino in pares:
        c, d = _punto_normal(cara)
        largo = _largo_extension(cara, destino, d, diag)
        lados = ((1.0, sumar), (-1.0, restar))
        if isinstance(destino, geo.Plano):
            herr = _cara_plana(destino, c, largo + 2 * diag)
        else:
            # un destino curvo puede cortar la normal de los dos lados (p. ej. un tubo que envuelve
            # al cuerpo): manda el cruce más cercano al centro de la cara → extender O recortar.
            herr = destino
            t = _cruce_rayo(c, d, destino)
            if t is None:
                raise geo.ErrorGeometria("El destino no corta la normal de la cara origen.")
            lados = lados[:1] if t > 0 else lados[1:]
        for signo, lista in lados:
            prisma = BRepPrimAPI_MakePrism(cara, gp_Vec(*(d * signo * largo)))
            tapa = prisma.LastShape()
            piezas = geo.solidos(_partir(prisma.Shape(), [herr]))
            if len(piezas) > 1:
                lista.extend(p for p in piezas if not geo.se_tocan(p, tapa, 1e-7))
    if not sumar and not restar:
        raise geo.ErrorGeometria("El destino no corta por completo la extensión de las caras elegidas.")
    resultado = geo.unir_todos([forma] + sumar)
    for pieza in restar:
        resultado = geo.booleano(resultado, pieza, "cortar")
    if restar and (geo.esta_vacia(resultado) or not geo.solidos(resultado)):
        raise geo.ErrorGeometria(f"{operacion}: no queda material: la cara entra hasta atravesar todo el cuerpo. "
                                 "Probá una distancia menor.")
    return _validar(_unificar(resultado), operacion)


def reemplazar_cara(forma, caras_origen, destino):
    """Replace Face: quita las caras origen y lleva el cuerpo (extiende o recorta) hasta `destino`
    (geo.Plano o una cara plana o curva). Límite: la extensión es un prisma según la normal de cada
    cara origen; coincide con Fusion cuando las caras vecinas son perpendiculares a la cara origen
    (cuerpos prismáticos). Con vecinas inclinadas Fusion las prolonga y acá quedan "a plomo".
    Con destino curvo cada cara se extiende O se recorta entera (según el cruce más cercano de la
    normal en su centro); con destino plano puede extenderse de un lado y recortarse del otro."""
    if not caras_origen:
        raise geo.ErrorGeometria("Elegí las caras a reemplazar.")
    if isinstance(destino, TopoDS_Shape) and destino.ShapeType() == TopAbs_FACE:
        destino = TopoDS.Face(destino)
        plano = _plano_de_cara(destino)
        if plano is not None:
            destino = plano
        else:
            destino = _cara_extendida(destino, _diagonal(forma))
    elif not isinstance(destino, geo.Plano):
        raise geo.ErrorGeometria("El destino debe ser un plano o una cara.")
    return _reemplazar(forma, [(c, destino) for c in caras_origen])


def mover_caras(forma, caras, matriz):
    """Move/Copy de caras (modelado directo): cada cara PLANA se reemplaza por su plano transformado
    (las vecinas se extienden o recortan). Límite: solo caras planas; mover cilindros/curvas no está."""
    m = np.asarray(matriz, float)
    pares = []
    for c in caras:
        plano = _plano_de_cara(c)
        if plano is None:
            raise geo.ErrorGeometria("Mover caras solo admite caras planas.")
        o = m[:3, :3] @ plano.origen + m[:3, 3]
        n = np.linalg.inv(m[:3, :3]).T @ plano.normal
        pares.append((c, geo.Plano.desde_marco(o, n, m[:3, :3] @ plano.u)))
    try:
        return _reemplazar(forma, pares)
    except geo.ErrorGeometria as e:
        if "no corta" in str(e):
            return forma            # el movimiento deja las caras en su mismo plano
        raise


# ---------------------------------------------------------------- división
def dividir_cara(forma, caras, herramienta, *, extender=True):
    """Split Face: parte solo las `caras` elegidas con un plano, una cara o aristas.

    Se calcula la sección de la herramienta con cada cara y esas aristas parten la cara
    (BRepAlgoAPI_Splitter con aristas como herramienta: las vecinas no se tocan). Sin `extender`,
    la herramienta tiene que atravesar la cara por completo."""
    if not caras:
        raise geo.ErrorGeometria("Elegí las caras a dividir.")
    if isinstance(herramienta, TopoDS_Edge) or (isinstance(herramienta, (list, tuple)) and herramienta
                                                and all(isinstance(h, TopoDS_Edge) for h in herramienta)):
        cortes = [herramienta] if isinstance(herramienta, TopoDS_Edge) else list(herramienta)
    else:
        herr = _herramienta_corte(herramienta, forma, extender)
        cortes = []
        for c in caras:
            sec = BRepAlgoAPI_Section(c, herr, True)
            if sec.IsDone():
                cortes.extend(_aristas(sec.Shape()))
    if not cortes:
        raise geo.ErrorGeometria("La herramienta no corta las caras elegidas.")
    antes = len(geo.caras(forma))
    resultado = _fusionar_costuras(_partir(forma, cortes))
    if len(geo.caras(resultado)) <= antes:
        raise geo.ErrorGeometria("La herramienta no atraviesa las caras elegidas (probá extenderla).")
    return _validar(resultado, "Dividir cara")


def dividir_cuerpo(forma, herramienta, *, extender=True):
    """Split Body: parte el cuerpo con un plano, una cara (extendida si se pide) o un cuerpo.
    Devuelve los sólidos ordenados por centro de masa (x, y, z) y volumen."""
    herr = _herramienta_corte(herramienta, forma, extender)
    piezas = geo.solidos(_partir(forma, [herr]))
    if len(piezas) < 2:
        raise geo.ErrorGeometria("La herramienta no divide el cuerpo (probá extenderla).")

    def clave(s):
        c = geo.centro_masa(s)
        return (round(c[0], 6), round(c[1], 6), round(c[2], 6), round(geo.volumen(s), 6))
    return [_validar(s, "Dividir cuerpo") for s in sorted(piezas, key=clave)]


def _herramientas_silueta(cara, d, diag):
    """Herramientas analíticas cuyo corte con la cara es su silueta (n·d = 0)."""
    sup = BRepAdaptor_Surface(cara)
    tipo = sup.GetType()
    if tipo == GeomAbs_Cylinder:
        ax = sup.Cylinder().Axis()
        a, p = _np(ax.Direction()), _np(ax.Location())
        dp = d - a * float(d @ a)
        if np.linalg.norm(dp) < 1e-9:
            return []
        return [_cara_plana(geo.Plano.desde_marco(p, dp, a), p, 2 * diag)]
    if tipo == GeomAbs_Sphere:
        c = _np(sup.Sphere().Location())
        return [_cara_plana(geo.Plano.desde_marco(c, d, (1, 0, 0)), c, 2 * diag)]
    if tipo == GeomAbs_Cone:
        cono = sup.Cone()
        pos = cono.Position()
        x, y, z = _np(pos.XDirection()), _np(pos.YDirection()), _np(pos.Direction())
        alfa, apice = cono.SemiAngle(), _np(cono.Apex())
        dx, dy, dz = float(d @ x), float(d @ y), float(d @ z)
        rho = math.hypot(dx, dy)
        if rho < 1e-12 or abs(math.tan(alfa) * dz / rho) >= 1:
            return []
        phi0, delta = math.atan2(dy, dx), math.acos(math.tan(alfa) * dz / rho)
        g = [math.sin(alfa) * (math.cos(u) * x + math.sin(u) * y) + math.cos(alfa) * z
             for u in (phi0 + delta, phi0 - delta)]
        n = np.cross(g[0], g[1])
        if np.linalg.norm(n) < 1e-12:
            return []
        return [_cara_plana(geo.Plano.desde_marco(apice, n, g[0]), apice, 2 * diag)]
    if tipo == GeomAbs_Torus:
        tor = sup.Torus()
        ax = tor.Position()
        a, c = _np(ax.Direction()), _np(ax.Location())
        dp = d - a * float(d @ a)
        if np.linalg.norm(dp) < 1e-9:
            return [_cara_plana(geo.Plano.desde_marco(c, a, (1, 0, 0)), c, 2 * diag)]
        if abs(float(d @ a)) < 1e-9:
            cil = gp_Cylinder(gp_Ax3(gp_Pnt(*c), gp_Dir(*a)), tor.MajorRadius())
            h = 2 * diag
            return [_cara_plana(geo.Plano.desde_marco(c, d, a), c, 2 * diag),
                    BRepBuilderAPI_MakeFace(cil, 0.0, 2 * math.pi, -h, h).Face()]
    return None


def _silueta_numerica(cara, d, n=40):
    """Silueta n·d = 0 por marching squares en el espacio (u, v) de la cara: aristas B-spline
    sobre la superficie (para toroides oblicuos y superficies libres)."""
    u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
    us, vs = np.linspace(u0, u1, n + 1), np.linspace(v0, v1, n + 1)

    def g(u, v):
        return float(_normal_en(cara, u, v)[1] @ d)

    G = np.array([[g(u, v) for v in vs] for u in us])

    def cruce(i, j, i2, j2):
        a, b = G[i, j], G[i2, j2]
        pa, pb = np.array([us[i], vs[j]]), np.array([us[i2], vs[j2]])
        for _ in range(3):               # secante sobre el lado de la grilla
            t = a / (a - b) if a != b else 0.5
            pm = pa + (pb - pa) * t
            gm = g(*pm)
            if abs(gm) < 1e-10:
                break
            if (gm > 0) == (a > 0):
                pa, a = pm, gm
            else:
                pb, b = pm, gm
        return pm

    puntos, vecinos = {}, {}
    for i in range(n):
        for j in range(n):
            lados = {("h", i, j): (i, j, i + 1, j), ("h", i, j + 1): (i, j + 1, i + 1, j + 1),
                     ("v", i, j): (i, j, i, j + 1), ("v", i + 1, j): (i + 1, j, i + 1, j + 1)}
            cortados = []
            for k, (a, b, c, e) in lados.items():
                if (G[a, b] > 0) != (G[c, e] > 0):
                    if k not in puntos:
                        puntos[k] = cruce(a, b, c, e)
                    cortados.append(k)
            for k1, k2 in zip(cortados[0::2], cortados[1::2], strict=False):
                vecinos.setdefault(k1, []).append(k2)
                vecinos.setdefault(k2, []).append(k1)
    superficie = BRep_Tool.Surface_s(cara)
    aristas, usados = [], set()
    for inicio in sorted(vecinos, key=lambda k: len(vecinos[k])):
        if inicio in usados:
            continue
        camino, actual = [inicio], inicio
        usados.add(inicio)
        while True:
            sig = [k for k in vecinos[actual] if k not in usados]
            if not sig:
                break
            actual = sig[0]
            usados.add(actual)
            camino.append(actual)
        if len(camino) < 2:
            continue
        arr = Array1_gp_Pnt2d(1, len(camino))
        for i, k in enumerate(camino, 1):
            arr.SetValue(i, gp_Pnt2d(*map(float, puntos[k])))
        curva = Geom2dAPI_PointsToBSpline(arr, 1, 3, GeomAbs_C2, 1e-7).Curve()
        arista = BRepBuilderAPI_MakeEdge(curva, superficie).Edge()
        BRepLib.BuildCurves3d_s(arista)
        aristas.append(arista)
    return aristas


def division_silueta(forma, direccion):
    """Silhouette Split (operación "Split Faces Only"): parte cada cara curva por su silueta vista
    desde `direccion` (lugar donde normal·dirección = 0). Cilindros, conos, esferas y toroides con
    vista axial o perpendicular: exacto (cortes con planos/cilindros). Toroides oblicuos y superficies
    libres: aproximado por marching squares (grilla 40x40 en u, v). Las caras planas no se parten."""
    d = np.asarray(direccion, float)
    if np.linalg.norm(d) < 1e-12:
        raise geo.ErrorGeometria("La dirección de vista no puede ser nula.")
    d = d / np.linalg.norm(d)
    diag = _diagonal(forma)
    resultado, partida = forma, False
    cortes = []
    for cara in geo.caras(forma):                       # 1) superficies analíticas: corte exacto
        if BRepAdaptor_Surface(cara).GetType() == GeomAbs_Plane:
            continue
        for h in _herramientas_silueta(cara, d, diag) or []:
            sec = BRepAlgoAPI_Section(cara, h, True)
            if sec.IsDone():
                cortes.extend(_aristas(sec.Shape()))
    if cortes:
        resultado, partida = _partir(forma, cortes), True
    divisor = BRepFeat_SplitShape(resultado)            # 2) resto: curvas numéricas sobre cada cara
    numericas = False
    for cara in geo.caras(resultado):
        if BRepAdaptor_Surface(cara).GetType() == GeomAbs_Plane or \
                _herramientas_silueta(cara, d, diag) is not None:
            continue
        for e in _silueta_numerica(cara, d):
            divisor.Add(e, cara)
            numericas = True
    if numericas:
        try:
            divisor.Build()
        except Exception:  # noqa: BLE001
            pass
        if not divisor.IsDone():
            raise geo.ErrorGeometria("No se pudo partir una cara libre por su silueta.")
        resultado, partida = divisor.Shape(), True
    if not partida:
        raise geo.ErrorGeometria("El cuerpo no tiene silueta en esa dirección.")
    return _validar(_fusionar_costuras(resultado), "División por silueta")


# ---------------------------------------------------------------- supresión de caras
def quitar_caras(forma, caras):
    """Delete de caras en modelado directo (defeaturing): quita las caras y cierra el hueco
    prolongando las vecinas (agujeros, salientes, empalmes, chaflanes)."""
    if not caras:
        raise geo.ErrorGeometria("Elegí las caras a quitar.")
    df = BRepAlgoAPI_Defeaturing()
    df.SetShape(forma)
    for c in caras:
        df.AddFaceToRemove(c)
    df.SetRunParallel(False)
    df.Build()
    if not df.IsDone():
        raise geo.ErrorGeometria("No se pudieron quitar esas caras: las vecinas no cierran el hueco.")
    # Como Suprimir caras de Fusion: cura el hueco o falla (en Fusion, dejarlo abierto es otro comando, de superficies).
    # Con la tapa de una caja, el defeaturing da IsDone y devuelve el cuerpo tal cual sin borrar nada.
    if not all(df.IsDeleted(c) for c in caras):
        raise geo.ErrorGeometria("No se pueden borrar esas caras: las caras vecinas no alcanzan a cerrar el hueco "
                                 "(por ejemplo, la tapa de una caja).")
    return _validar(df.Shape(), "Quitar caras")
