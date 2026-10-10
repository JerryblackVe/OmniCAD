# -*- coding: utf-8 -*-
"""
Núcleo geométrico: envoltorio fino sobre OpenCascade (paquete `cadquery-ocp`).

Por qué B-rep y OpenCascade: Fusion 360 trabaja sobre un kernel B-rep (Autodesk ShapeManager,
37 DLL ASM*232 y cuerpos `.smb` dentro del .f3d — informe_analisis.md §1 y §4). Un kernel
B-rep permite booleanos exactos y exportar STEP. OpenCascade es el kernel B-rep open source.

Unidades: milímetros y grados (los grados se pasan a radianes solo acá).
El resto de la aplicación no importa OCP directamente: todo pasa por este módulo y
por `perfiles.py`, así la capa de kernel queda aislada.
"""
import math

import numpy as np
from OCP.BRepTools import BRepTools
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_Transform
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import (BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism,
                             BRepPrimAPI_MakeRevol, BRepPrimAPI_MakeSphere, BRepPrimAPI_MakeTorus)
from OCP.Bnd import Bnd_Box
from OCP.GCPnts import GCPnts_TangentialDeflection
from OCP.GeomAbs import (GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Sphere, GeomAbs_SurfaceOfExtrusion,
                         GeomAbs_SurfaceOfRevolution, GeomAbs_Torus)
from OCP.GProp import GProp_GProps
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_IN, TopAbs_REVERSED, TopAbs_SOLID, TopAbs_VERTEX
from OCP.OCP.collections import IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec


class ErrorGeometria(RuntimeError):
    pass


# ---------------------------------------------------------------- planos de boceto
class Plano:
    """Plano de boceto: origen + ejes u, v y normal (como los planos de construcción de Fusion)."""
    DEFINICIONES = {
        # nombre: (normal, eje u)  →  eje v = normal × u
        "XY": ((0, 0, 1), (1, 0, 0)),
        "XZ": ((0, -1, 0), (1, 0, 0)),
        "YZ": ((1, 0, 0), (0, 1, 0)),
    }

    def __init__(self, nombre="XY", desplazamiento=0.0):
        if nombre not in self.DEFINICIONES:
            raise ErrorGeometria(f"Plano desconocido: {nombre}")
        n, u = self.DEFINICIONES[nombre]
        self.nombre = nombre
        self.normal = np.array(n, float)
        self.u = np.array(u, float)
        self.v = np.cross(self.normal, self.u)
        self.origen = self.normal * float(desplazamiento)

    def a_3d(self, u, v):
        return self.origen + self.u * u + self.v * v

    def pnt(self, u, v):
        return gp_Pnt(*map(float, self.a_3d(u, v)))

    def ax2(self, cu=0.0, cv=0.0):
        return gp_Ax2(self.pnt(cu, cv), gp_Dir(*self.normal), gp_Dir(*self.u))

    def dir_3d(self, du, dv):
        d = self.u * du + self.v * dv
        return d / (np.linalg.norm(d) or 1.0)

    @classmethod
    def desde_marco(cls, origen, normal, u, nombre="Cara"):
        """Plano libre (cara plana o plano de construcción): origen, normal y eje u (se ortonormaliza)."""
        n = np.asarray(normal, float)
        n = n / (np.linalg.norm(n) or 1.0)
        u = np.asarray(u, float)
        u = u - n * float(u @ n)
        if np.linalg.norm(u) < 1e-9:
            u = np.cross(n, (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0))
        p = cls.__new__(cls)
        p.nombre, p.normal, p.u = nombre, n, u / np.linalg.norm(u)
        p.v = np.cross(p.normal, p.u)
        p.origen = np.asarray(origen, float)
        return p

    def desplazado(self, distancia, nombre=None):
        return Plano.desde_marco(self.origen + self.normal * float(distancia), self.normal, self.u,
                                 nombre or self.nombre)

    def a_uv(self, punto):
        d = np.asarray(punto, float) - self.origen
        return float(d @ self.u), float(d @ self.v)

    def marco(self):
        return {"origen": [float(c) for c in self.origen], "normal": [float(c) for c in self.normal],
                "u": [float(c) for c in self.u]}


def plano_de_cara(cara):
    """Plano de boceto sobre una cara plana (None si la cara no es plana).

    Ejes como al bocetar sobre una cara en Fusion: en caras verticales, v apunta hacia +Z (el boceto
    queda "derecho" al mirarlo); en caras horizontales, u sigue a +X. El origen es la proyección
    del origen del mundo sobre el plano (no depende del tamaño de la cara).
    """
    sup = BRepAdaptor_Surface(cara)
    if sup.GetType() != GeomAbs_Plane:
        return None
    pln = sup.Plane()
    d, loc = pln.Axis().Direction(), pln.Location()
    n = np.array([d.X(), d.Y(), d.Z()])
    if not pln.Position().Direct():         # ejes indirectos (tapas de una revolución): la normal es −eje
        n = -n
    if cara.Orientation() == TopAbs_REVERSED:
        n = -n
    origen = n * float(n @ np.array([loc.X(), loc.Y(), loc.Z()]))
    if abs(n[2]) > 0.9:
        u = np.array([1.0, 0.0, 0.0])
    else:
        v = np.array([0.0, 0.0, 1.0]) - n * n[2]
        u = np.cross(v / np.linalg.norm(v), n)
    return Plano.desde_marco(origen, n, u)


def _dir(v):
    return gp_Dir(*map(float, v))


# ---------------------------------------------------------------- primitivas
def _primitiva(constructor, que):
    """La forma del constructor de OCC, comprobada: con medidas extremas (radio de 5e8 mm o de 1e-7 mm) el kernel
    devuelve una forma inválida sin avisar, o lanza Standard_DomainError (caja de 1e-8 mm)."""
    try:
        forma = constructor().Shape()
    except Exception:  # noqa: BLE001 — Standard_DomainError / Standard_ConstructionError de OCC
        forma = None
    if forma is None or not es_valida(forma):
        raise ErrorGeometria(f"No se puede construir {que}: las medidas son demasiado grandes o demasiado chicas "
                             "para el kernel.")
    return forma


def caja(ancho, largo, alto, origen=(0, 0, 0)):
    if min(ancho, largo, alto) <= 0:
        raise ErrorGeometria("Las medidas de la caja deben ser positivas.")
    return _primitiva(lambda: BRepPrimAPI_MakeBox(gp_Pnt(*map(float, origen)), float(ancho), float(largo),
                                                  float(alto)), "la caja")


def cilindro(radio, alto, base=(0, 0, 0), eje=(0, 0, 1)):
    if radio <= 0 or alto <= 0:
        raise ErrorGeometria("Radio y alto del cilindro deben ser positivos.")
    return _primitiva(lambda: BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*map(float, base)), _dir(eje)), float(radio),
                                                       float(alto)), "el cilindro")


def esfera(radio, centro=(0, 0, 0)):
    if radio <= 0:
        raise ErrorGeometria("El radio de la esfera debe ser positivo.")
    return _primitiva(lambda: BRepPrimAPI_MakeSphere(gp_Pnt(*map(float, centro)), float(radio)), "la esfera")


def toroide(radio_mayor, radio_menor, centro=(0, 0, 0), eje=(0, 0, 1)):
    if radio_menor <= 0 or radio_mayor <= radio_menor:
        raise ErrorGeometria("El toroide necesita radio mayor > radio menor > 0.")
    return _primitiva(lambda: BRepPrimAPI_MakeTorus(gp_Ax2(gp_Pnt(*map(float, centro)), _dir(eje)),
                                                    float(radio_mayor), float(radio_menor)), "el toroide")


# ---------------------------------------------------------------- operaciones
def trasladar(forma, vector):
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(*map(float, vector)))
    return BRepBuilderAPI_Transform(forma, t, True).Shape()


def rotar(forma, punto, eje, angulo_grados):
    t = gp_Trsf()
    t.SetRotation(gp_Ax1(gp_Pnt(*map(float, punto)), _dir(eje)), math.radians(angulo_grados))
    return BRepBuilderAPI_Transform(forma, t, True).Shape()


def transformar(forma, matriz):
    """Aplica una matriz 4x4 rígida (rotación + traslación; también escala uniforme)."""
    m = np.asarray(matriz, float)
    t = gp_Trsf()
    t.SetValues(*m[0, :4], *m[1, :4], *m[2, :4])
    return BRepBuilderAPI_Transform(forma, t, True).Shape()


def cara_de_plano(plano, tam=1e4):
    """Cara cuadrada grande sobre un plano (para usar un plano de construcción como límite o herramienta)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pln
    return BRepBuilderAPI_MakeFace(gp_Pln(plano.ax2().Location(), gp_Dir(*map(float, plano.normal))),
                                   -tam, tam, -tam, tam).Face()


LONGITUD_MINIMA = 1e-6   # mm: OCC no construye un prisma de 1e-7 mm (su Precision::Confusion); desde 2e-7 sí


def exigir_longitud(valor, que, minimo=LONGITUD_MINIMA):
    """Error claro si una distancia de extrusión (en valor absoluto) es menor que `minimo`: el kernel
    fallaría con «BRepSweep_Prism::Constructor». `que`: «La distancia de extrusión», «La profundidad…»."""
    if abs(valor) < minimo:
        raise ErrorGeometria(f"{que} tiene que ser de al menos {minimo:.6f} mm; recibió {valor:g} mm.")


def exigir_distancias_extrusion(direccion, distancia1, distancia2=None, medida="mitad"):
    """Revisa las distancias de una extrusión por distancia con el nombre de su campo y el valor que se escribió, no
    el largo de cada prisma (la simétrica «mitad» arma uno del doble). En la simétrica con medida total cada lado mide
    la mitad: ahí el mínimo se duplica."""
    exigir_longitud(distancia1, "La distancia de extrusión")
    if direccion == "dos_lados":
        exigir_longitud(distancia2, "La distancia del lado 2")
    elif direccion == "simetrica" and medida == "total":
        exigir_longitud(distancia1, "La distancia total de la extrusión simétrica", 2 * LONGITUD_MINIMA)


def extruir(caras, normal, distancia, simetrica=False):
    """Extrusión de una o más caras planas (equivalente a ExtrudeFeature con DistanceExtentDefinition
    o SymmetricExtentDefinition). Distancia negativa = sentido contrario a la normal."""
    exigir_longitud(distancia, "La distancia de extrusión")
    n = np.asarray(normal, float) / np.linalg.norm(normal)
    solidos = []
    for cara in caras:
        base = cara
        if simetrica:
            base = trasladar(cara, -n * abs(distancia) / 2)
            vec = n * abs(distancia)
        else:
            vec = n * distancia
        solidos.append(BRepPrimAPI_MakePrism(base, gp_Vec(*map(float, vec))).Shape())
    return unir_todos(solidos)


def revolver(caras, punto_eje, dir_eje, angulo_grados):
    """Revolución de caras alrededor de un eje (equivalente a RevolveFeature con AngleExtentDefinition)."""
    if abs(angulo_grados) < 1e-9:
        raise ErrorGeometria("El ángulo de revolución no puede ser cero.")
    ang = math.radians(max(-360.0, min(360.0, angulo_grados)))
    eje = gp_Ax1(gp_Pnt(*map(float, punto_eje)), _dir(dir_eje))
    solidos = []
    for c in caras:
        rev = BRepPrimAPI_MakeRevol(c, eje, ang)
        if not rev.IsDone():        # OCC lo marca así cuando el sólido se cortaría a sí mismo
            raise ErrorGeometria("El perfil cruza el eje de revolución: tiene que quedar de un solo lado del eje "
                                 "(puede apoyarse en él).")
        forma = rev.Shape()
        if sin_volumen(forma):
            raise ErrorGeometria("La revolución no genera un sólido: el eje no puede ser perpendicular al plano "
                                 "del perfil.")
        solidos.append(forma)
    return unir_todos(solidos)


def booleano(objetivo, herramienta, operacion):
    """'unir' | 'cortar' | 'intersecar' (FeatureOperations Join/Cut/Intersect de Fusion)."""
    clases = {"unir": BRepAlgoAPI_Fuse, "cortar": BRepAlgoAPI_Cut, "intersecar": BRepAlgoAPI_Common}
    if operacion not in clases:
        raise ErrorGeometria(f"Operación booleana desconocida: {operacion}")
    op = clases[operacion](objetivo, herramienta)
    if not op.IsDone():
        raise ErrorGeometria(f"La operación '{operacion}' falló en el kernel.")
    return unificar_caras(op.Shape())


def unificar_caras(forma):
    """Fusiona las caras coplanares (o sobre la misma superficie) que deja una booleana, como el resultado limpio
    de Fusion. Sin esto, unir dos prismas en L deja la cara de atrás partida en dos y un empalme más grande que el
    tramo partido falla. Si no se puede simplificar, devuelve la forma tal cual."""
    try:
        u = ShapeUpgrade_UnifySameDomain(forma, True, True, False)
        u.Build()
        resultado = u.Shape()
    except Exception:  # noqa: BLE001
        return forma
    return resultado if not resultado.IsNull() else forma


def unir_todos(formas):
    formas = [f for f in formas if f is not None]
    if not formas:
        raise ErrorGeometria("No hay geometría para unir.")
    resultado = formas[0]
    for f in formas[1:]:
        resultado = booleano(resultado, f, "unir")
    return resultado


def compuesto(formas):
    c = TopoDS_Compound()
    b = BRep_Builder()
    b.MakeCompound(c)
    for f in formas:
        b.Add(c, f)
    return c


# ---------------------------------------------------------------- consultas
# Caras que la integración de OpenCascade resuelve bien (las barridas por una curva también: es una sola dirección).
_ANALITICAS = (GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Sphere, GeomAbs_Torus, GeomAbs_SurfaceOfExtrusion,
               GeomAbs_SurfaceOfRevolution)
_CONTROL_RELATIVO = 1e-3          # malla de control: desvío relativo al tamaño de cada cara (rápida, ~0,3 s)
_DEFLEXION_FINA = 3e-5            # malla fina: de la diagonal de la caja (~0,01 mm en una pieza de 300 mm)
_DEFLEXION_MINIMA = 0.01          # mm: menos hace fallar el mallado de algunas B-spline (queda una cara sin malla)
_ERROR_GROSERO = 0.05             # diferencia relativa a partir de la cual la integración exacta se descarta


def es_forma_libre(forma):
    """True si alguna cara es B-spline, Bézier, desfasada u otra superficie libre."""
    return any(BRepAdaptor_Surface(c).GetType() not in _ANALITICAS for c in caras(forma))


def _por_malla(forma, funcion, deflexion, relativa):
    """Volumen o área sobre la malla de una COPIA (la malla de la vista no se toca). None si una cara no se malló."""
    copia = BRepBuilderAPI_Copy(forma).Shape()
    BRepMesh_IncrementalMesh(copia, deflexion, relativa, 0.2, True)
    if any(BRep_Tool.Triangulation_s(c, TopLoc_Location()) is None for c in caras(copia)):
        return None
    p = GProp_GProps()
    funcion(copia, p, False, False, True) if funcion is BRepGProp.VolumeProperties_s else funcion(copia, p, False, True)
    return p.Mass()


def _integral(forma, funcion):
    """Volumen o área por la integración exacta de OpenCascade, sin el control por malla de `_propiedades`."""
    p = GProp_GProps()
    funcion(forma, p)
    return p.Mass()


def _propiedades(forma, funcion):
    """Volumen o área. La integración de OpenCascade es exacta y rápida con caras analíticas y con la mayoría de las
    libres (barridos, recubrimientos, bobinas), pero en superficies libres muy recortadas puede errar mucho: el fuelle
    de un .f3d de Fusion daba 180 791 mm³ contra 124 672 de Fusion (con tolerancia, 125 050 en 27 s). Con caras libres
    se controla contra una malla rápida; si difieren más de 5 % (un error grosero: la malla se equivoca menos de 1,5 %
    incluso en un alambre de 1 mm), vale una malla fina: 124 718 mm³ en ~1 s."""
    exacto = _integral(forma, funcion)
    if not es_forma_libre(forma):
        return exacto
    control = _por_malla(forma, funcion, _CONTROL_RELATIVO, True)
    if control is None or abs(exacto - control) <= _ERROR_GROSERO * abs(control):
        return exacto
    caja = caja_envolvente(forma)
    fino = _por_malla(forma, funcion, max(_DEFLEXION_MINIMA, math.dist(*caja) * _DEFLEXION_FINA if caja else 0), False)
    return fino if fino is not None else control


def volumen(forma):
    return _propiedades(forma, BRepGProp.VolumeProperties_s)


def volumen_exacto(forma):
    """Volumen por integración exacta, sin malla (barato aun con B-spline): para comparar dos formas o descartar las
    degeneradas. Para informar un volumen, `volumen`."""
    return _integral(forma, BRepGProp.VolumeProperties_s)


TAMANO_MINIMO = 1e-3    # mm: un sólido más chico no sirve (la tolerancia del kernel es 1e-7 mm)
_CHATO = 1e-6           # |V| / (área · diagonal): degenerados ≤ 3,5e-8; una lámina de 0,01 × 100 × 100, 3,5e-5


def sin_volumen(forma):
    """True si un sólido no encierra volumen: vacío, más chico que TAMANO_MINIMO o chato (solevación entre perfiles
    coplanares, perfil paralelo a la ruta, escala casi nula). Una lámina de t × L × L da |V| / (A · d) ≈ t / (2,8 L):
    se acepta desde t ≈ 3e-6 · L. Es para sólidos (formas cerradas): una superficie no tiene volumen."""
    bb = caja_envolvente(forma)
    if bb is None:
        return True
    d = math.dist(*bb)
    if d < TAMANO_MINIMO:
        return True
    return abs(volumen_exacto(forma)) <= _CHATO * _integral(forma, BRepGProp.SurfaceProperties_s) * d


def area(forma):
    return _propiedades(forma, BRepGProp.SurfaceProperties_s)


def longitud(forma):
    p = GProp_GProps()
    BRepGProp.LinearProperties_s(forma, p)
    return p.Mass()


def centro_masa(forma, superficie=False):
    p = GProp_GProps()
    (BRepGProp.SurfaceProperties_s if superficie else BRepGProp.VolumeProperties_s)(forma, p)
    c = p.CentreOfMass()
    return (c.X(), c.Y(), c.Z())


def caja_envolvente(forma):
    """Caja envolvente exacta. Add_s usaría la malla de visualización (si ya se teseló) y la agranda
    con la tolerancia: una placa de 80 mm medía 80,085. AddOptimal sin triangulación mide el sólido."""
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(forma, b, False, False)
    if b.IsVoid():
        return None
    p0, p1 = b.CornerMin(), b.CornerMax()   # OCP 8: Bnd_Box.Get() ya no es convertible a Python
    return (p0.X(), p0.Y(), p0.Z()), (p1.X(), p1.Y(), p1.Z())


def es_valida(forma):
    return BRepCheck_Analyzer(forma).IsValid()


def _explorar(forma, tipo):
    ex = TopExp_Explorer(forma, tipo)
    while ex.More():
        yield ex.Current()
        ex.Next()


def solidos(forma):
    return [TopoDS.Solid(s) for s in _explorar(forma, TopAbs_SOLID)]


def caras(forma):
    return [TopoDS.Face(f) for f in _explorar(forma, TopAbs_FACE)]


def esta_vacia(forma):
    return forma is None or not any(True for _ in _explorar(forma, TopAbs_FACE))


def se_tocan(a, b, tolerancia=1e-6):
    """True si las formas se tocan o se superponen, también cuando una queda entera dentro de un sólido de la otra.
    BRepExtrema_DistShapeShape solo mira «adentro» cuando la forma es un SOLID: con un COMPOUND (lo que devuelve toda
    booleana) mide entre los bordes, y una cavidad interna daba «no se tocan» (el corte automático la salteaba)."""
    d = BRepExtrema_DistShapeShape(a, b)
    if d.IsDone() and d.Value() <= tolerancia:
        return True
    return _adentro(a, b, tolerancia) or _adentro(b, a, tolerancia)


def _adentro(a, b, tolerancia):
    """True si alguna pieza de `b` (cada sólido, o `b` entera si no tiene) queda dentro de un sólido de `a`. Se usa
    con los bordes separados: entonces cada pieza está entera adentro o entera afuera y basta un vértice."""
    sols = solidos(a)
    if not sols:
        return False
    for pieza in solidos(b) or [b]:
        v = next(_explorar(pieza, TopAbs_VERTEX), None)
        if v is None:
            continue
        p = BRep_Tool.Pnt_s(TopoDS.Vertex(v))
        if any(BRepClass3d_SolidClassifier(s, p, tolerancia).State() == TopAbs_IN for s in sols):
            return True
    return False


# ---------------------------------------------------------------- teselado para el visor y exportación
def teselar_por_cara(forma, deflexion=0.05, angular=0.3, rehacer=False):
    """[(cara, triángulos Kx3x3)]: sirve para elegir caras con el ratón (picking). OpenCascade guarda la malla en la
    forma y, si ya tiene una MÁS FINA, la reusa aunque se pida una más gruesa (cilindro: 88 triángulos pedidos, 396
    devueltos); `rehacer=True` la borra antes para que el detalle pedido se respete."""
    if rehacer:
        BRepTools.Clean_s(forma)
    BRepMesh_IncrementalMesh(forma, deflexion, False, angular, True)
    salida = []
    for cara in caras(forma):
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(cara, loc)
        if tri is None:
            continue
        trsf = loc.Transformation()
        nodos = np.array([[p.X(), p.Y(), p.Z()] for p in
                          (tri.Node(i).Transformed(trsf) for i in range(1, tri.NbNodes() + 1))], float)
        idx = np.array([tri.Triangle(i).Get() for i in range(1, tri.NbTriangles() + 1)], int) - 1
        if cara.Orientation() == TopAbs_REVERSED:
            idx = idx[:, [0, 2, 1]]
        salida.append((cara, np.stack([nodos[idx[:, 0]], nodos[idx[:, 1]], nodos[idx[:, 2]]], axis=1)))
    return salida


def teselar(forma, deflexion=0.05, angular=0.3, rehacer=False):
    """Devuelve (vertices Nx3, normales Nx3) como triángulos sueltos (3 filas por triángulo), float32.
    `rehacer`: ver `teselar_por_cara`. Equivale a la malla de visualización de Fusion (Preferencias › Gráficos)."""
    verts, norms = [], []
    for _cara, tris in teselar_por_cara(forma, deflexion, angular, rehacer):
        a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
        n = np.cross(b - a, c - a)
        largo = np.linalg.norm(n, axis=1, keepdims=True)
        largo[largo == 0] = 1.0
        n = n / largo
        verts.append(np.stack([a, b, c], axis=1).reshape(-1, 3))
        norms.append(np.repeat(n, 3, axis=0))
    if not verts:
        return np.zeros((0, 3), np.float32), np.zeros((0, 3), np.float32)
    return np.concatenate(verts).astype(np.float32), np.concatenate(norms).astype(np.float32)


def teselar_aparte(forma, deflexion=0.05, angular=0.3):
    """Como `teselar`, pero sobre una copia de la topología que comparte la geometría: la malla guardada en `forma`
    queda intacta. Para los niveles de detalle a la distancia del visor (malla más gruesa para piezas que se ven
    chicas) sin pisar la malla que usan el dibujo de cerca y la elección de caras."""
    return teselar(BRepBuilderAPI_Copy(forma, False, False).Shape(), deflexion, angular)


def triangulos_indexados(forma, deflexion=0.05, angular=0.3):
    """Vértices únicos + índices (para OBJ/STL) a partir del teselado."""
    v, _ = teselar(forma, deflexion, angular)
    if len(v) == 0:
        return v, np.zeros((0, 3), int)
    redondeo = np.round(v.astype(np.float64), 6)
    unicos, inversos = np.unique(redondeo, axis=0, return_inverse=True)
    return unicos, inversos.reshape(-1, 3)


def polilinea_arista(arista, deflexion=0.05):
    """Una arista como polilínea 3D (array Kx3); vacía si la arista es degenerada o rara."""
    if BRep_Tool.Degenerated_s(arista):
        return np.zeros((0, 3), np.float32)
    try:
        d = GCPnts_TangentialDeflection(BRepAdaptor_Curve(arista), 0.2, deflexion)
        return np.array([[p.X(), p.Y(), p.Z()] for p in (d.Value(i) for i in range(1, d.NbPoints() + 1))], np.float32)
    except Exception:  # noqa: BLE001
        return np.zeros((0, 3), np.float32)


def polilineas_aristas(forma, deflexion=0.05):
    """Aristas como polilíneas 3D (lista de arrays Kx3) para dibujar el contorno de los cuerpos."""
    salida = []
    # TopExp_Explorer visita una arista compartida una vez por cada cara: el mapa las deja únicas.
    mapa = IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapes_s(forma, TopAbs_EDGE, mapa)
    for i in range(1, mapa.Size() + 1):
        arista = TopoDS.Edge(mapa.FindKey(i))
        if BRep_Tool.Degenerated_s(arista):
            continue
        try:
            curva = BRepAdaptor_Curve(arista)
            d = GCPnts_TangentialDeflection(curva, 0.2, deflexion)
            pts = [d.Value(i) for i in range(1, d.NbPoints() + 1)]
        except Exception:  # noqa: BLE001 — aristas raras: se omiten solo para el dibujo
            continue
        if len(pts) >= 2:
            salida.append(np.array([[p.X(), p.Y(), p.Z()] for p in pts], np.float32))
    return salida
