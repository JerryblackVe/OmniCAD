"""Engrosar agudo: intersección de las paredes desfasadas de una banda reglada (B-633)."""
import numpy as np
from scipy.optimize import least_squares

from . import superficies as sf


def _costura(a, b, muestras):
    """UV sobre ambas paredes: en cada plano perpendicular a la generatriz, resolver el punto común."""
    base, pared, u, v0, v1 = a
    vecina, otra, w, z0, z1 = b
    if base.Value(u, v0).Distance(vecina.Value(w, z1)) < sf._TOL:
        z0, z1 = z1, z0
    eje = sf._unitario(sf._np(base.Value(u, v1)) - sf._np(base.Value(u, v0)), "La generatriz")

    def residuo(uv, origen):
        p = sf._np(pared.Value(*uv[:2]))
        return np.r_[p - sf._np(otra.Value(*uv[2:])), (p - origen) @ eje]

    puntos = []
    for t in muestras:
        v, z = v0 + t * (v1 - v0), z0 + t * (z1 - z0)
        ajuste = least_squares(residuo, [u, v, w, z], args=(sf._np(base.Value(u, v)),), gtol=1e-11, max_nfev=40)
        if np.linalg.norm(ajuste.fun) > sf._TOL:
            return None
        puntos.append(ajuste.x)
    uv = np.asarray(puntos)
    return uv[:, :2], (uv[::-1] if z1 < z0 else uv)[:, 2:]


def _engrosar_cara_lisa(base, espesor):
    """Una cara reglada: offset de OCC con error acotado al 0,1 % del espesor."""
    from OCP.Geom import Geom_OffsetSurface
    from OCP.GeomConvert import GeomConvert_ApproxSurface

    caras = sf.geo.caras(base)
    if len(caras) != 1:
        return None
    cara = caras[0]
    sup = sf.BRepAdaptor_Surface(cara)
    if sup.GetType() != sf.GeomAbs_BSplineSurface or sup.VDegree() != 1:
        return None
    b = sup.BSpline()
    u0, u1, v0, v1 = sf.BRepTools.UVBounds_s(cara)
    pared = Geom_OffsetSurface(b, -espesor if cara.Orientation() == sf.TopAbs_REVERSED else espesor)
    conversion = GeomConvert_ApproxSurface(
        pared, min(5e-4, abs(espesor) * 1e-3), sf.GeomAbs_C1, sf.GeomAbs_C1, 8, 8, 1000, 1)
    if not conversion.IsDone() or conversion.MaxError() > abs(espesor) * 1e-3:
        return None
    exterior = conversion.Surface()
    if not np.allclose(exterior.Bounds(), (u0, u1, v0, v1), rtol=1e-9, atol=1e-9):
        return None
    piezas = [cara, sf.BRepBuilderAPI_MakeFace(exterior, sf._TOL).Face()]
    for v, z in ((v0, v0), (v1, v1)):
        original = sf.BRepBuilderAPI_MakeEdge(b.VIso(v), u0, u1).Edge()
        lejos = sf.BRepBuilderAPI_MakeEdge(exterior.VIso(z)).Edge()
        piezas.append(sf.BRepFill.Face_s(original, lejos))
    cosido = sf.coser(piezas, sf._TOL)
    if not cosido["es_solido"] or len(sf.geo.solidos(cosido["forma"])) != 1:
        return None
    resultado = cosido["forma"]
    if sf.geo.volumen_exacto(resultado) < 0:
        resultado = resultado.Reversed()
    if not sf.geo.es_valida(resultado) or sf._desfase_imposible(base, resultado, espesor, engrosado=True):
        return None
    esperado = sf.geo.area(base) * abs(espesor)
    if abs(abs(sf.geo.volumen(resultado)) - esperado) > 0.05 * esperado:
        return None
    from . import revision
    cantidad, _, completo = revision._autointersecciones_seguras(resultado, 1, 30.0)
    return resultado if completo and not cantidad else None


def engrosar_banda(base, espesor):
    """Solo una vuelta de parches UV enteros, sin recortes. None si no se pueden coser a la piel original."""
    from OCP.Approx import Approx_IsoParametric
    from OCP.collections import Array2_gp_Pnt
    from OCP.Geom import Geom_OffsetSurface
    from OCP.GeomAPI import GeomAPI_PointsToBSplineSurface

    caras = sf.geo.caras(base)
    mapa = sf._mapa_aristas(base)
    costuras, parches = {}, []
    muestras = np.linspace(0, 1, 65)
    for i, cara in enumerate(caras):
        sup = sf.BRepAdaptor_Surface(cara)
        if sup.GetType() != sf.GeomAbs_BSplineSurface or sup.VDegree() != 1:
            return None
        b = sup.BSpline()
        u0, u1, v0, v1 = sf.BRepTools.UVBounds_s(cara)
        aristas = sf.geo._aristas_unicas(cara)
        if b.NbVPoles() != 2 or len(aristas) != 4:
            return None
        pared = Geom_OffsetSurface(b, -espesor if cara.Orientation() == sf.TopAbs_REVERSED else espesor)
        for arista in aristas:
            curva = sf.BRepAdaptor_Curve2d(arista, cara)
            ini, fin = curva.Value(curva.FirstParameter()), curva.Value(curva.LastParameter())
            for lado, u in enumerate((u0, u1)):
                if max(abs(ini.X() - u), abs(fin.X() - u)) < 1e-9 and abs(abs(fin.Y() - ini.Y()) - (v1-v0)) < 1e-9:
                    costuras.setdefault(mapa.FindIndex(arista), []).append(((i, lado), (b, pared, u, v0, v1)))
        parches.append((b, pared, u0, u1, v0, v1))
    bordes = {}
    for par in costuras.values():
        if len(par) != 2:
            return None
        (izq, a), (der, b) = par
        curvas = _costura(a, b, muestras)
        if curvas is None:
            return None
        bordes[izq], bordes[der] = curvas
    if len(bordes) != 2 * len(caras):
        return None

    piezas = list(caras)
    nodos = muestras[::2]
    for i, (b, pared, u0, u1, v0, v1) in enumerate(parches):
        puntos = Array2_gp_Pnt(1, len(nodos), 1, len(nodos))
        izquierda, derecha = bordes[i, 0], bordes[i, 1]
        for j, t in enumerate(nodos, 1):
            for k, uv in enumerate((1-t)*izquierda[::2] + t*derecha[::2], 1):
                puntos.SetValue(j, k, pared.Value(*uv))
        ajuste = GeomAPI_PointsToBSplineSurface()
        ajuste.Interpolate(puntos, Approx_IsoParametric)
        exterior = ajuste.Surface()
        # Medir también entre los nodos: una banda muy curva puede no admitir esta aproximación.
        for t in muestras[1::2]:
            for z, uv in zip(muestras[1::2], (1-t)*izquierda[1::2] + t*derecha[1::2], strict=True):
                if exterior.Value(t, z).Distance(pared.Value(*uv)) > min(1e-3, abs(espesor)*1e-3):
                    return None
        piezas.append(sf.BRepBuilderAPI_MakeFace(exterior, sf._TOL).Face())
        for v, z in ((v0, 0.), (v1, 1.)):
            original = sf.BRepBuilderAPI_MakeEdge(b.VIso(v), u0, u1).Edge()
            lejos = sf.BRepBuilderAPI_MakeEdge(exterior.VIso(z)).Edge()
            piezas.append(sf.BRepFill.Face_s(original, lejos))
    cosido = sf.coser(piezas, sf._TOL)
    return cosido["forma"] if cosido["es_solido"] and len(sf.geo.solidos(cosido["forma"])) == 1 else None
