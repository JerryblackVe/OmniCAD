# -*- coding: utf-8 -*-
"""
Convierte las entidades ACIS de un `sab.ArchivoSAB` en sólidos y superficies de OpenCascade.

Topología ACIS → OCC: body › lump › shell › face › loop › coedge › edge › vertex. Cada vértice y cada arista se
crean una sola vez y se comparten entre caras, así el cuerpo queda cosido sin coser. Las curvas p (pcurves), las
costuras de las superficies periódicas y las tolerancias las completa ShapeFix al final, como hace el lector STEP.

Geometría: plano, cono/cilindro (también elíptico recto), esfera, toro y spline; recta, elipse/círculo e
intcurve. Las splines procedurales de ACIS (barridos, empalmes, offsets…) se toman de la aproximación B-spline que
el archivo guarda junto a su definición. Fusion trabaja en centímetros: `convertir` devuelve milímetros.

Sin Qt.
"""
import math
from collections import Counter

from OCP.BRep import BRep_Builder
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.Geom import (Geom_BSplineCurve, Geom_BSplineSurface, Geom_Circle, Geom_ConicalSurface,
                      Geom_CylindricalSurface, Geom_Ellipse, Geom_Line, Geom_Plane, Geom_SphericalSurface,
                      Geom_SurfaceOfLinearExtrusion, Geom_ToroidalSurface)
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Ax2, gp_Ax3, gp_Dir, gp_Pnt, gp_Trsf
from OCP.ShapeFix import ShapeFix_Shape
from OCP.OCP.collections import (Array1_double, Array1_gp_Pnt, Array1_int, Array2_double, Array2_gp_Pnt,
                                 IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher)
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_REVERSED, TopAbs_SOLID
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS_Edge, TopoDS_Face, TopoDS_Shell, TopoDS_Solid, TopoDS_Vertex, TopoDS_Wire

from .sab import Puntero, Subtipo

MM_POR_UNIDAD = 10.0          # Fusion guarda el B-rep en centímetros
TOLERANCIA = 1e-6             # la resabs de ShapeManager (en centímetros); ShapeFix la agranda donde haga falta
PRECISION_ARREGLO = 1e-4      # cm: con menos, ShapeFix no reconoce los vértices que caen en un polo o en un ápice
_EPS = 1e-12


class ErrorACIS(ValueError):
    """La entidad no se puede convertir (tipo no soportado o datos incoherentes)."""


def convertir(archivo, nombre="Cuerpo"):
    """Los cuerpos de `archivo` (sab.ArchivoSAB). Devuelve (partes, avisos): `partes` es una lista de (forma OCC en
    mm, "solido" | "superficie", marca); `avisos`, textos para el usuario (caras que no se pudieron leer).

    `marca` es la marca de tiempo que Fusion pone a cada cuerpo del diseño al modificarlo. Los cuerpos sin marca
    son auxiliares (perfiles de bocetos, superficies de construcción) y se dejan afuera, salvo que ningún cuerpo
    del archivo la tenga (versiones que no la usan)."""
    conv = _Convertidor(archivo)
    cuerpos = archivo.de_tipo("body")
    marcas = {b.indice: conv.marca_tiempo(b) for b in cuerpos}
    con_marca = any(m is not None for m in marcas.values())
    partes = []
    for cuerpo in cuerpos:
        marca = marcas[cuerpo.indice]
        if con_marca and marca is None:
            continue
        partes += [(forma, tipo, marca) for forma, tipo in conv.cuerpo(cuerpo)]
    avisos = []
    if conv.omitidas:
        detalle = ", ".join(f"{n} × {t}" for t, n in conv.omitidas.most_common())
        avisos.append(f"{nombre}: no se pudieron leer {sum(conv.omitidas.values())} caras ({detalle}); "
                      "esos cuerpos entran como superficie abierta.")
    return partes, avisos


class _Convertidor:
    def __init__(self, archivo):
        self.sab = archivo
        self.B = BRep_Builder()
        self.d = self._desplazamiento()
        self.vertices, self.aristas, self.curvas, self.superficies = {}, {}, {}, {}
        self.omitidas = Counter()

    # ------------------------------------------------------------ campos
    def _desplazamiento(self):
        """Los registros de ShapeManager reciente traen atributo, id y un puntero extra antes de sus datos (3
        campos); versiones viejas, menos. Se mide en el primer «point»: sus datos empiezan en la posición."""
        for e in self.sab.entidades:
            if e is not None and e.tipo == "point":
                for i, v in enumerate(e.campos):
                    if isinstance(v, tuple):
                        return i - 3
        return 0

    def _c(self, ent, k):
        """Campo `k` según la disposición de ShapeManager 232 (atributo, id, extra, datos…)."""
        i = k + self.d
        return ent.campos[i] if 0 <= i < len(ent.campos) else None

    def _ent(self, ptr):
        return self.sab.entidad(ptr) if isinstance(ptr, Puntero) else None

    def _lista(self, primero, k_siguiente):
        """Recorre una lista enlazada de entidades (siguiente en el campo `k_siguiente`)."""
        vistos, ent = set(), self._ent(primero)
        while ent is not None and ent.indice not in vistos:
            vistos.add(ent.indice)
            yield ent
            ent = self._ent(self._c(ent, k_siguiente))

    def marca_tiempo(self, ent):
        """Valor del atributo «Timestamp_attrib_def» de la entidad (la cadena de atributos sigue el campo 2), o None."""
        vistos, at = set(), self._ent(ent.campos[0] if ent.campos else None)
        while at is not None and at.indice not in vistos:
            vistos.add(at.indice)
            if "Timestamp_attrib_def" in at.campos:
                resto = at.campos[at.campos.index("Timestamp_attrib_def") + 1:]
                return next((v for v in resto if isinstance(v, float)), None)
            at = self._ent(self._c(at, 2))
        return None

    # ------------------------------------------------------------ cuerpos
    def cuerpo(self, body):
        partes = []
        for lump in self._lista(self._c(body, 3), 3):
            for shell in self._lista(self._c(lump, 4), 3):
                caras, completas = [], True
                for face in self._lista(self._c(shell, 5), 3):
                    cara = self._cara(face)
                    if cara is None:
                        completas = False
                    else:
                        caras.append(cara)
                if caras:
                    partes.append(self._cerrar(caras, completas))
        trsf = self._transformacion(self._ent(self._c(body, 5)))
        return [(self._a_mm(forma, trsf), tipo) for forma, tipo in partes]

    def _cerrar(self, caras, completas):
        shell = TopoDS_Shell()
        self.B.MakeShell(shell)
        for cara in caras:
            self.B.Add(shell, cara)
        forma = shell
        if completas and _cerrado(shell):
            solido = TopoDS_Solid()
            self.B.MakeSolid(solido)
            self.B.Add(solido, shell)
            forma = solido
        arreglo = ShapeFix_Shape(forma)
        arreglo.SetPrecision(PRECISION_ARREGLO)
        arreglo.SetMaxTolerance(PRECISION_ARREGLO * 100)
        arreglo.Perform()
        forma = arreglo.Shape()
        if _tiene_solido(forma):
            if _volumen(forma) < 0:
                forma.Reverse()
            return forma, "solido"
        return forma, "superficie"

    def _transformacion(self, ent):
        if ent is None or ent.tipo != "transform":
            return None
        filas = [v for v in ent.campos if isinstance(v, tuple)]
        escala = next((v for v in ent.campos if isinstance(v, float)), 1.0)
        if len(filas) < 4:
            return None
        (a, b, c), t = filas[:3], filas[3]
        if (a, b, c, t, escala) == ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0, 0.0), 1.0):
            return None
        trsf = gp_Trsf()
        # ACIS usa vectores fila (p' = p·A + t); gp_Trsf, columnas: se traspone.
        trsf.SetValues(a[0] * escala, b[0] * escala, c[0] * escala, t[0],
                       a[1] * escala, b[1] * escala, c[1] * escala, t[1],
                       a[2] * escala, b[2] * escala, c[2] * escala, t[2])
        return trsf

    def _a_mm(self, forma, trsf):
        if trsf is not None:
            forma = BRepBuilderAPI_Transform(forma, trsf, True).Shape()
        escala = gp_Trsf()
        escala.SetScale(gp_Pnt(0, 0, 0), MM_POR_UNIDAD)
        return BRepBuilderAPI_Transform(forma, escala, True).Shape()

    # ------------------------------------------------------------ caras
    def _cara(self, face):
        sup_ent = self._ent(self._c(face, 7))
        try:
            superficie, invertida = self._superficie(sup_ent)
        except ErrorACIS as e:
            self.omitidas[str(e)] += 1
            return None
        al_reves = bool(self._c(face, 8)) != invertida
        cara = TopoDS_Face()
        self.B.MakeFace(cara, superficie, TOLERANCIA)
        for loop in self._lista(self._c(face, 4), 3):
            alambre = TopoDS_Wire()
            self.B.MakeWire(alambre)
            n = 0
            for coedge in self._ciclo(loop):
                arista = self._arista(self._ent(self._c(coedge, 6)))
                if arista is None:
                    continue
                if bool(self._c(coedge, 7)) != al_reves:
                    arista = arista.Reversed()
                self.B.Add(alambre, arista)
                n += 1
            if n:
                self.B.Add(cara, alambre)
        if al_reves:
            cara.Reverse()
        return cara

    def _ciclo(self, loop):
        primero = self._ent(self._c(loop, 4))
        vistos, co = set(), primero
        while co is not None and co.indice not in vistos:
            vistos.add(co.indice)
            yield co
            co = self._ent(self._c(co, 3))

    # ------------------------------------------------------------ aristas y vértices
    def _vertice(self, ent):
        v = self.vertices.get(ent.indice)
        if v is None:
            punto = self._ent(self._c(ent, 5))
            if punto is None:
                raise ErrorACIS("vértice sin punto")
            x, y, z = self._c(punto, 3)
            v = TopoDS_Vertex()
            self.B.MakeVertex(v, gp_Pnt(x, y, z), TOLERANCIA)
            self.vertices[ent.indice] = v
        return v

    def _arista(self, ent):
        if ent is None:
            return None
        if ent.indice in self.aristas:
            return self.aristas[ent.indice]
        arista = None
        curva_ent = self._ent(self._c(ent, 8))
        if curva_ent is not None:
            curva, convertir_param = self._curva(curva_ent)
            if curva is not None:
                v0, v1 = self._vertice(self._ent(self._c(ent, 3))), self._vertice(self._ent(self._c(ent, 5)))
                s0, s1 = self._c(ent, 4), self._c(ent, 6)
                al_reves = bool(self._c(ent, 9))
                if al_reves:                       # parámetro de la arista = -parámetro de la curva
                    t0, t1, va, vb = -s1, -s0, v1, v0
                else:
                    t0, t1, va, vb = s0, s1, v0, v1
                arista = TopoDS_Edge()
                self.B.MakeEdge(arista, curva, TOLERANCIA)
                self.B.Add(arista, va.Oriented(TopAbs_FORWARD))
                self.B.Add(arista, vb.Oriented(TopAbs_REVERSED))
                self.B.Range(arista, convertir_param(t0), convertir_param(t1))
                if al_reves:
                    arista.Reverse()
        self.aristas[ent.indice] = arista
        return arista

    # ------------------------------------------------------------ curvas
    def _curva(self, ent):
        """(Geom_Curve, función parámetro ACIS → parámetro OCC), o (None, None) si no se puede."""
        if ent.indice in self.curvas:
            return self.curvas[ent.indice]
        try:
            r = self._curva_nueva(ent)
        except (ErrorACIS, RuntimeError, TypeError, ValueError, IndexError):
            r = (None, None)
        self.curvas[ent.indice] = r
        return r

    def _curva_nueva(self, ent):
        t = ent.tipo
        if t == "straight-curve":
            raiz, dire = self._c(ent, 3), self._c(ent, 4)
            largo = math.sqrt(sum(c * c for c in dire))
            factor = largo if largo > _EPS else 1.0
            return Geom_Line(gp_Pnt(*raiz), gp_Dir(*dire)), (lambda s: s * factor)
        if t == "ellipse-curve":
            centro, normal, mayor, razon = self._c(ent, 3), self._c(ent, 4), self._c(ent, 5), self._c(ent, 6)
            a = math.sqrt(sum(c * c for c in mayor))
            if abs(razon - 1.0) < 1e-12:
                return Geom_Circle(gp_Ax2(gp_Pnt(*centro), gp_Dir(*normal), gp_Dir(*mayor)), a), (lambda s: s)
            if razon < 1.0:
                return (Geom_Ellipse(gp_Ax2(gp_Pnt(*centro), gp_Dir(*normal), gp_Dir(*mayor)), a, a * razon),
                        (lambda s: s))
            menor = gp_Dir(*normal).Crossed(gp_Dir(*mayor))   # el eje menor de ACIS pasa a ser el mayor
            return (Geom_Ellipse(gp_Ax2(gp_Pnt(*centro), gp_Dir(*normal), menor), a * razon, a),
                    (lambda s: s - math.pi / 2))
        if t == "intcurve-curve":
            sub = self.sab.resolver(_primer_subtipo(ent.campos))
            if sub is None:
                raise ErrorACIS("intcurve sin datos")
            bs3 = _buscar_bs3(sub, superficie=False)
            if bs3 is None:
                raise ErrorACIS(f"intcurve {sub.nombre} sin aproximación")
            return _bspline_curva(bs3, invertir=bool(self._c(ent, 3))), (lambda s: s)
        raise ErrorACIS(f"curva {t}")

    # ------------------------------------------------------------ superficies
    def _superficie(self, ent):
        """(Geom_Surface, invertida): `invertida` = la normal de la superficie OCC es la opuesta a la de ACIS."""
        if ent is None:
            raise ErrorACIS("cara sin superficie")
        if ent.indice not in self.superficies:
            try:
                self.superficies[ent.indice] = self._superficie_nueva(ent)
            except ErrorACIS as e:
                self.superficies[ent.indice] = e
            except (RuntimeError, TypeError, ValueError, IndexError) as e:
                self.superficies[ent.indice] = ErrorACIS(f"{ent.tipo} inválida ({type(e).__name__})")
        r = self.superficies[ent.indice]
        if isinstance(r, ErrorACIS):
            raise r
        return r

    def _superficie_nueva(self, ent):
        t = ent.tipo
        if t == "plane-surface":
            raiz, normal, u = self._c(ent, 3), self._c(ent, 4), self._c(ent, 5)
            return Geom_Plane(gp_Ax3(gp_Pnt(*raiz), gp_Dir(*normal), gp_Dir(*u))), False
        if t == "cone-surface":
            centro, normal, mayor, razon = self._c(ent, 3), self._c(ent, 4), self._c(ent, 5), self._c(ent, 6)
            seno, coseno = [v for v in ent.campos[7 + self.d:] if isinstance(v, float)][:2]
            radio = math.sqrt(sum(c * c for c in mayor))
            ejes = gp_Ax3(gp_Pnt(*centro), gp_Dir(*normal), gp_Dir(*mayor))
            invertida = coseno < 0
            if abs(razon - 1.0) > 1e-12:
                if abs(seno) > _EPS:
                    raise ErrorACIS("cono elíptico")
                elipse = (Geom_Ellipse(ejes.Ax2(), radio, radio * razon) if razon < 1 else
                          Geom_Ellipse(gp_Ax2(gp_Pnt(*centro), gp_Dir(*normal),
                                              gp_Dir(*normal).Crossed(gp_Dir(*mayor))), radio * razon, radio))
                return Geom_SurfaceOfLinearExtrusion(elipse, gp_Dir(*normal)), invertida
            if abs(seno) < _EPS:
                return Geom_CylindricalSurface(ejes, radio), invertida
            return Geom_ConicalSurface(ejes, math.atan(seno / coseno), radio), invertida
        if t == "sphere-surface":
            centro, radio, u, polo = self._c(ent, 3), self._c(ent, 4), self._c(ent, 5), self._c(ent, 6)
            return Geom_SphericalSurface(gp_Ax3(gp_Pnt(*centro), gp_Dir(*polo), gp_Dir(*u)), abs(radio)), radio < 0
        if t == "torus-surface":
            centro, normal, mayor, menor, u = (self._c(ent, k) for k in range(3, 8))
            return (Geom_ToroidalSurface(gp_Ax3(gp_Pnt(*centro), gp_Dir(*normal), gp_Dir(*u)), abs(mayor), abs(menor)),
                    menor < 0)
        if t == "spline-surface":
            sub = self.sab.resolver(_primer_subtipo(ent.campos))
            if sub is None:
                raise ErrorACIS("spline sin datos")
            bs3 = _buscar_bs3(sub, superficie=True)
            if bs3 is None:
                raise ErrorACIS(f"spline {sub.nombre} sin aproximación")
            return _bspline_superficie(bs3), bool(self._c(ent, 3))
        raise ErrorACIS(t)


# ---------------------------------------------------------------- B-splines (formato bs3 de ACIS)
def _primer_subtipo(campos):
    return next((v for v in campos if isinstance(v, Subtipo)), None)


def _buscar_bs3(sub, superficie):
    """La primera curva o superficie B-spline (`nubs`/`nurbs`) del nivel superior del subtipo. Los subtipos
    anidados (curvas de definición, superficies de apoyo) se saltean."""
    it = sub.items
    for i, v in enumerate(it):
        if v not in ("nubs", "nurbs") or not isinstance(v, str) or i + 4 >= len(it):
            continue
        if v == "nurbs" and isinstance(it[i + 3], str):
            es_sup = True
        else:
            es_sup = not isinstance(it[i + 4], float)
        if es_sup == superficie:
            return (_leer_bs3_superficie if superficie else _leer_bs3_curva)(it, i)
    return None


def _nudos(it, j, n):
    nudos, mults = [], []
    for _ in range(n):
        nudos.append(float(it[j]))
        mults.append(int(it[j + 1]))
        j += 2
    return nudos, mults, j


def _leer_bs3_curva(it, i):
    racional, grado, cierre, nk = it[i] == "nurbs", int(it[i + 1]), int(it[i + 2]), int(it[i + 3])
    nudos, mults, j = _nudos(it, i + 4, nk)
    dim = 4 if racional else 3
    n = sum(mults) - grado + 1
    valores = it[j:j + n * dim]
    if len(valores) < n * dim or not all(isinstance(x, float) for x in valores):
        raise ErrorACIS("curva B-spline truncada")
    puntos = [tuple(valores[k * dim:(k + 1) * dim]) for k in range(n)]
    return {"grado": grado, "racional": racional, "cierre": cierre, "nudos": nudos, "mults": mults,
            "puntos": puntos}


def _leer_bs3_superficie(it, i):
    racional, du, dv = it[i] == "nurbs", int(it[i + 1]), int(it[i + 2])
    j = i + 3
    if isinstance(it[j], str):                  # «both», «u» o «v»: en qué dirección es racional
        j += 1
    cierre_u, cierre_v = int(it[j]), int(it[j + 1])
    nku, nkv = int(it[j + 4]), int(it[j + 5])
    nudos_u, mults_u, j = _nudos(it, j + 6, nku)
    nudos_v, mults_v, j = _nudos(it, j, nkv)
    dim = 4 if racional else 3
    nu, nv = sum(mults_u) - du + 1, sum(mults_v) - dv + 1
    valores = it[j:j + nu * nv * dim]
    if len(valores) < nu * nv * dim or not all(isinstance(x, float) for x in valores):
        raise ErrorACIS("superficie B-spline truncada")
    puntos = [tuple(valores[k * dim:(k + 1) * dim]) for k in range(nu * nv)]
    return {"du": du, "dv": dv, "racional": racional, "cierre": (cierre_u, cierre_v), "nudos_u": nudos_u,
            "mults_u": mults_u, "nudos_v": nudos_v, "mults_v": mults_v, "nu": nu, "nv": nv, "puntos": puntos}


def _mults_occ(mults, grado, n_polos):
    """ACIS guarda los extremos con multiplicidad = grado; OCC (sujeta) pide grado + 1."""
    m = list(mults)
    if sum(m) - grado - 1 == n_polos:
        return m
    m[0] += 1
    m[-1] += 1
    if sum(m) - grado - 1 != n_polos:
        raise ErrorACIS("nudos y polos no coinciden")
    return m


def _arr_real(valores):
    a = Array1_double(1, len(valores))
    for k, v in enumerate(valores, 1):
        a.SetValue(k, v)
    return a


def _arr_ent(valores):
    a = Array1_int(1, len(valores))
    for k, v in enumerate(valores, 1):
        a.SetValue(k, v)
    return a


def _bspline_curva(bs3, invertir=False):
    """Geom_BSplineCurve. Con `invertir`, la curva se recorre al revés y su parámetro t pasa a -t (como hace
    ACIS con una intcurve de sentido invertido)."""
    nudos, mults, puntos = bs3["nudos"], bs3["mults"], bs3["puntos"]
    if invertir:
        nudos, mults, puntos = [-k for k in reversed(nudos)], list(reversed(mults)), list(reversed(puntos))
    grado = bs3["grado"]
    mults = _mults_occ(mults, grado, len(puntos))
    polos = Array1_gp_Pnt(1, len(puntos))
    for k, p in enumerate(puntos, 1):
        polos.SetValue(k, gp_Pnt(p[0], p[1], p[2]))
    if bs3["racional"]:
        return Geom_BSplineCurve(polos, _arr_real([p[3] for p in puntos]), _arr_real(nudos), _arr_ent(mults), grado)
    return Geom_BSplineCurve(polos, _arr_real(nudos), _arr_ent(mults), grado)


def _bspline_superficie(bs3):
    nu, nv, puntos = bs3["nu"], bs3["nv"], bs3["puntos"]
    mu = _mults_occ(bs3["mults_u"], bs3["du"], nu)
    mv = _mults_occ(bs3["mults_v"], bs3["dv"], nv)
    polos = Array2_gp_Pnt(1, nu, 1, nv)
    pesos = Array2_double(1, nu, 1, nv) if bs3["racional"] else None
    for k, p in enumerate(puntos):              # u varía más rápido
        i, j = k % nu + 1, k // nu + 1
        polos.SetValue(i, j, gp_Pnt(p[0], p[1], p[2]))
        if pesos is not None:
            pesos.SetValue(i, j, p[3])
    args = (_arr_real(bs3["nudos_u"]), _arr_real(bs3["nudos_v"]), _arr_ent(mu), _arr_ent(mv), bs3["du"], bs3["dv"])
    if pesos is not None:
        return Geom_BSplineSurface(polos, pesos, *args)
    return Geom_BSplineSurface(polos, *args)


# ---------------------------------------------------------------- utilidades
def _cerrado(shell):
    """Cada arista (con curva) la usan exactamente dos caras: el shell encierra un volumen."""
    mapa = IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapesAndAncestors_s(shell, TopAbs_EDGE, TopAbs_FACE, mapa)
    return mapa.Extent() > 0 and all(mapa.FindFromIndex(k).Size() == 2 for k in range(1, mapa.Extent() + 1))


def _tiene_solido(forma):
    return TopExp_Explorer(forma, TopAbs_SOLID).More()


def _volumen(forma):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(forma, props)
    return props.Mass()


def es_valida(forma):
    return BRepCheck_Analyzer(forma).IsValid()

