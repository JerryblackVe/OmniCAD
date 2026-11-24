"""Sólidos › Crear: comun."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import math
from .solidos_crear_occ import _registrar_tema

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BRepAdaptor_CompCurve, BRepAdaptor_Curve, BRepAdaptor_Surface, BRepBuilderAPI_Copy, BRepBuilderAPI_MakeEdge,
        BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeWire, BRepOffset_MakeOffset,
        BRepOffset_Skin, BRepTools_WireExplorer, BRep_Tool, GCPnts_AbscissaPoint, GeomAbs_Intersection, GeomAbs_Plane,
        IntCurvesFace_ShapeIntersector, ShapeUpgrade_UnifySameDomain, TopAbs_EDGE, TopAbs_FACE, TopAbs_REVERSED,
        TopAbs_WIRE, TopExp, TopExp_Explorer, TopoDS, _CONVERTIR, gp_Ax3, gp_Dir, gp_Lin, gp_Pln, gp_Pnt, gp_Vec,
    )


_MARGEN = 1.0   # mm que las herramientas "hasta" y "todo" pasan de largo antes de recortarse


def lado_todo(lo, hi, signo):
    """P-160 (Gerardo): «Todo» con «Un lado» va hacia donde hay cuerpos (`lo`, `hi`: dónde empiezan y terminan sobre la
    dirección, desde el perfil): si hay de un solo lado, hacia ese; si hay de los dos, el de la flecha (`signo`)."""
    delante, detras = hi > 1e-6, lo < -1e-6
    if not (delante or detras):
        raise geo.ErrorGeometria("⚠ «Todo» no atraviesa ningún cuerpo.")
    return signo if delante and detras else (1.0 if delante else -1.0)


# ================================================================ utilidades
def _unit(v, que="dirección"):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise geo.ErrorGeometria(f"La {que} no puede ser nula.")
    return v / n


def _pnt(p):
    return gp_Pnt(*map(float, p))


def _gdir(d):
    return gp_Dir(*map(float, d))


def _gvec(v):
    return gp_Vec(*map(float, v))


def _xyz(p):
    return np.array([p.X(), p.Y(), p.Z()], float)


def _perpendicular(n):
    n = _unit(n)
    aux = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
    return _unit(np.cross(n, aux))




def _tipado(forma):
    """Las transformaciones devuelven TopoDS_Shape genérico: se baja al tipo concreto (cara, alambre…)."""
    f = _CONVERTIR.get(forma.ShapeType())
    return f(forma) if f else forma


def _trasladar(forma, vector):
    return _tipado(geo.trasladar(forma, vector))


def _lista(x):
    if x is None:
        return []
    return [y for y in x if y is not None] if isinstance(x, (list, tuple)) else [x]


def _explorar(forma, tipo):
    ex = TopExp_Explorer(forma, tipo)
    while ex.More():
        yield ex.Current()
        ex.Next()


def _caras_de(x):
    """Caras de una cara, una forma o una lista de ellas."""
    salida = []
    for f in _lista(x):
        salida += [TopoDS.Face(c) for c in _explorar(f, TopAbs_FACE)]
    return salida


def _aristas_de(x):
    salida = []
    for f in _lista(x):
        if f.ShapeType() == TopAbs_WIRE:
            ex = BRepTools_WireExplorer(TopoDS.Wire(f))
            while ex.More():
                salida.append(ex.Current())
                ex.Next()
        else:
            salida += [TopoDS.Edge(e) for e in _explorar(f, TopAbs_EDGE)]
    return salida


def _extremos(arista):
    a = BRep_Tool.Pnt_s(TopExp.FirstVertex_s(arista, True))
    b = BRep_Tool.Pnt_s(TopExp.LastVertex_s(arista, True))
    return _xyz(a), _xyz(b)


def _cadenas(x, tol=1e-5):
    """Agrupa aristas sueltas (o alambres) en alambres encadenados. Devuelve una lista de alambres."""
    alambres = [TopoDS.Wire(f) for f in _lista(x) if f.ShapeType() == TopAbs_WIRE]
    pendientes = _aristas_de([f for f in _lista(x) if f.ShapeType() != TopAbs_WIRE])
    while pendientes:
        cadena = [pendientes.pop(0)]
        ini, fin = _extremos(cadena[0])
        agrego = True
        while agrego and pendientes:
            agrego = False
            for i, e in enumerate(pendientes):
                a, b = _extremos(e)
                if np.linalg.norm(a - fin) < tol or np.linalg.norm(b - fin) < tol:
                    cadena.append(e)
                    fin = b if np.linalg.norm(a - fin) < tol else a
                elif np.linalg.norm(a - ini) < tol or np.linalg.norm(b - ini) < tol:
                    cadena.insert(0, e)
                    ini = b if np.linalg.norm(a - ini) < tol else a
                else:
                    continue
                pendientes.pop(i)
                agrego = True
                break
        mk = BRepBuilderAPI_MakeWire()
        for e in cadena:
            mk.Add(e)
        if not mk.IsDone():
            raise geo.ErrorGeometria("⚠ No se pudo encadenar las aristas.")
        alambres.append(mk.Wire())
    return alambres


def _alambre(x):
    """Un único alambre continuo a partir de aristas, un alambre o una lista de aristas."""
    alambres = _cadenas(x)
    if len(alambres) != 1:
        raise geo.ErrorGeometria("⚠ La ruta no es una sola cadena de aristas.")
    return alambres[0]


_longitud = geo.longitud


def _es_cerrado(alambre):
    a = BRep_Tool.Pnt_s(TopExp.FirstVertex_s(_aristas_de(alambre)[0], True))
    b = BRep_Tool.Pnt_s(TopExp.LastVertex_s(_aristas_de(alambre)[-1], True))
    return a.Distance(b) < 1e-6


def _punto_en(alambre, fraccion):
    """(punto, tangente unitaria) a una fracción 0..1 de la longitud del alambre."""
    c = BRepAdaptor_CompCurve(alambre)
    largo = GCPnts_AbscissaPoint.Length_s(c)
    fraccion = min(max(fraccion, 0.0), 1.0)
    if fraccion <= 0:
        u = c.FirstParameter()
    elif fraccion >= 1:
        u = c.LastParameter()
    else:
        u = GCPnts_AbscissaPoint(c, fraccion * largo, c.FirstParameter()).Parameter()
    p, v = gp_Pnt(), gp_Vec()
    c.D1(u, p, v)
    return _xyz(p), _unit(_xyz(v), "tangente de la ruta")


def _recortar_alambre(alambre, fraccion, inicio=0.0):
    """Tramo entre dos fracciones de longitud (opción Distancia de barrido y tubería)."""
    if not math.isfinite(fraccion) or fraccion > 1.0 + 1e-9:
        raise geo.ErrorGeometria(f"⚠ La distancia va de 0 a 1: recibió {fraccion:g}.")
    if fraccion >= 1.0 - 1e-9 and inicio == 0:
        return alambre
    if fraccion - inicio <= 1e-6:
        raise geo.ErrorGeometria("⚠ La distancia debe ser mayor que cero.")
    total = _longitud(alambre)
    objetivo, desde, acumulado = min(fraccion, 1.0) * total, inicio * total, 0.0
    mk = BRepBuilderAPI_MakeWire()
    for e in _aristas_de(alambre):
        largo = _longitud(e)
        a, b = max(0.0, desde - acumulado), min(largo, objetivo - acumulado)
        acumulado += largo
        if b - a <= 1e-9:
            continue
        if a <= 1e-9 and b >= largo - 1e-9:
            mk.Add(e)
            continue
        curva = BRepAdaptor_Curve(e)
        geom = BRep_Tool.Curve_s(e, 0.0, 0.0)
        if e.Orientation() == TopAbs_REVERSED:
            extremo = curva.LastParameter()
            u1 = extremo if a <= 1e-9 else GCPnts_AbscissaPoint(curva, -a, extremo).Parameter()
            u0 = GCPnts_AbscissaPoint(curva, -b, extremo).Parameter()
            nueva = BRepBuilderAPI_MakeEdge(geom, u0, u1).Edge().Reversed()
        else:
            extremo = curva.FirstParameter()
            u0 = extremo if a <= 1e-9 else GCPnts_AbscissaPoint(curva, a, extremo).Parameter()
            u1 = GCPnts_AbscissaPoint(curva, b, extremo).Parameter()
            nueva = BRepBuilderAPI_MakeEdge(geom, u0, u1).Edge()
        mk.Add(TopoDS.Edge(nueva))
        if acumulado >= objetivo - 1e-9:
            break
    return mk.Wire()


def _marcos(alambre, n=64):
    """Muestras (punto, tangente, u, v) a lo largo del alambre con un marco de rotación mínima
    (método de doble reflexión): sirve para torsión de barridos y patrones orientados a la ruta."""
    c = BRepAdaptor_CompCurve(alambre)
    largo = GCPnts_AbscissaPoint.Length_s(c)
    pts, tans = [], []
    for i in range(n):
        s = largo * i / (n - 1)
        u = c.FirstParameter() if i == 0 else (
            c.LastParameter() if i == n - 1 else GCPnts_AbscissaPoint(c, s, c.FirstParameter()).Parameter())
        p, v = gp_Pnt(), gp_Vec()
        c.D1(u, p, v)
        pts.append(_xyz(p))
        tans.append(_unit(_xyz(v), "tangente de la ruta"))
    r = _perpendicular(tans[0])
    marcos = [(pts[0], tans[0], r, np.cross(tans[0], r))]
    for i in range(n - 1):
        v1 = pts[i + 1] - pts[i]
        c1 = float(v1 @ v1)
        if c1 < 1e-18:
            rl, tl = r, tans[i]
        else:
            rl = r - (2 / c1) * float(v1 @ r) * v1
            tl = tans[i] - (2 / c1) * float(v1 @ tans[i]) * v1
        v2 = tans[i + 1] - tl
        c2 = float(v2 @ v2)
        r = rl - (2 / c2) * float(v2 @ rl) * v2 if c2 > 1e-18 else rl
        r = _unit(r - tans[i + 1] * float(r @ tans[i + 1]))
        marcos.append((pts[i + 1], tans[i + 1], r, np.cross(tans[i + 1], r)))
    return marcos


def _unificar(forma):
    """Fusiona caras coplanares/cosuperficiales que dejan las uniones (como el resultado limpio de Fusion)."""
    try:
        u = ShapeUpgrade_UnifySameDomain(forma, True, True, False)
        u.Build()
        return u.Shape()
    except Exception:  # noqa: BLE001 — si no se puede simplificar, se devuelve tal cual
        return forma


def _unir(formas):
    formas = [f for f in formas if f is not None and not geo.esta_vacia(f)]
    if not formas:
        raise geo.ErrorGeometria("La operación no produjo geometría.")
    return _unificar(geo.unir_todos(formas)) if len(formas) > 1 else formas[0]


def _validar(forma, que):
    if forma is None or geo.esta_vacia(forma):
        raise geo.ErrorGeometria(f"{que}: el resultado quedó vacío.")
    if not geo.es_valida(forma):
        raise geo.ErrorGeometria(f"⚠ {que}: el kernel dio un sólido inválido.")
    return forma


def _piezas_que_tocan(forma, inicios, tol=1e-5):
    return [s for s in geo.solidos(forma) if any(geo.se_tocan(s, i, tol) for i in inicios)]


def _normal_superficie(cara):
    """Normal geométrica de una cara plana (sin tener en cuenta la orientación de la cara)."""
    sup = BRepAdaptor_Surface(cara)
    if sup.GetType() != GeomAbs_Plane:
        raise geo.ErrorGeometria("El perfil debe ser una cara plana.")
    d = sup.Plane().Axis().Direction()
    return np.array([d.X(), d.Y(), d.Z()])


def _caja_proyectada(forma, origen, direccion):
    """(mín, máx) de la proyección de la caja envolvente de `forma` sobre una recta."""
    bb = geo.caja_envolvente(forma)
    if bb is None:
        raise geo.ErrorGeometria("El objeto no tiene geometría.")
    return _proyectar_caja(bb, origen, direccion)


def _proyectar_caja(bb, origen, direccion):
    esquinas = np.array([[x, y, z] for x in (bb[0][0], bb[1][0]) for y in (bb[0][1], bb[1][1])
                         for z in (bb[0][2], bb[1][2])])
    proy = (esquinas - np.asarray(origen, float)) @ np.asarray(direccion, float)
    return float(proy.min()), float(proy.max())


def _rayo(forma, punto, direccion, largo=1e5):
    """Distancias a lo largo de un rayo a las que corta la forma (ordenadas)."""
    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(forma, 1e-7)
    inter.Perform(gp_Lin(_pnt(punto), _gdir(direccion)), 0.0, largo)
    if not inter.IsDone():
        return []
    return sorted(inter.WParameter(i) for i in range(1, inter.NbPnt() + 1))


def _engrosar_lamina(lamina, espesor):
    """Sólido de dar espesor a una lámina (cara o cáscara) hacia su normal (negativo = hacia atrás)."""
    from .superficies import _PUNTA_DE_CONO, _punta_de_cono
    if _punta_de_cono(lamina):              # B-493: OpenCascade cerraba el programa en vez de fallar
        raise geo.ErrorGeometria("No se pudo dar espesor: " + _PUNTA_DE_CONO)
    mk = BRepOffset_MakeOffset()
    # B-850: BRepOffset agranda IN PLACE las tolerancias de la entrada: la lámina puede compartir topología con
    # los perfiles cacheados del boceto y envenenaría lo que se dibuje después. Copia, como ShapeFix (B-39).
    mk.Initialize(BRepBuilderAPI_Copy(lamina).Shape(), float(espesor), 1e-6, BRepOffset_Skin, False, False,
                  GeomAbs_Intersection, True)
    mk.MakeOffsetShape()
    if not mk.IsDone():
        raise geo.ErrorGeometria("No se pudo dar espesor a la superficie.")
    return mk.Shape()


def _poligono(puntos):
    mk = BRepBuilderAPI_MakePolygon()
    for p in puntos:
        mk.Add(_pnt(p))
    mk.Close()
    return mk.Wire()


def _cara(alambre):
    mk = BRepBuilderAPI_MakeFace(alambre, True)
    if not mk.IsDone():
        raise geo.ErrorGeometria("El contorno no es plano o no está cerrado.")
    return mk.Face()


def cara_de_plano(plano, tamano=1e3):
    """Cara cuadrada grande sobre un geo.Plano: así se pasan los planos de construcción como herramientas."""
    pln = gp_Pln(gp_Ax3(_pnt(plano.origen), _gdir(plano.normal), _gdir(plano.u)))
    return BRepBuilderAPI_MakeFace(pln, -tamano, tamano, -tamano, tamano).Face()


_registrar_tema(globals())
