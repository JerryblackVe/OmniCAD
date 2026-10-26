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
import itertools
import math

import numpy as np
from . import motor as _motor


def lista_occ(lista):
    """Los elementos de una lista de OCP (TopTools_ListOfShape…) como lista de Python. Recorrerla con `for` cuesta
    ~0,5 ms fijos por recorrido (su iterador); con `islice` y el tamaño, ~5 µs (`bench_rendimiento.py frontera`)."""
    return list(itertools.islice(lista, lista.Size()))


def _iniciar_opencascade():
    global BRepAdaptor_Curve, BRepAdaptor_Surface, BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
    global ShapeFix_Shape
    global BRepBndLib, BRepBuilderAPI_Copy, BRepBuilderAPI_NurbsConvert, BRepBuilderAPI_Transform, BRepCheck_Analyzer
    global BRepClass3d_SolidClassifier, BRepExtrema_DistShapeShape, BRepGProp, BRepMesh_IncrementalMesh
    global BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
    global BRepPrimAPI_MakeSphere, BRepPrimAPI_MakeTorus, BRepTools, BRep_Builder, BRep_Tool, Bnd_Box
    global GCPnts_TangentialDeflection, GProp_GProps, GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane
    global GeomAbs_Sphere, GeomAbs_SurfaceOfExtrusion, GeomAbs_SurfaceOfRevolution, GeomAbs_Torus
    global IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher
    global IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher, ShapeUpgrade_UnifySameDomain, TopAbs_COMPOUND
    global TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_REVERSED, TopAbs_SHELL, TopAbs_SOLID
    global TopAbs_VERTEX, TopAbs_WIRE, TopExp, TopExp_Explorer, TopLoc_Location, TopoDS, TopoDS_Compound
    global TopoDS_Face, TopoDS_Iterator, TopoDS_Shell, TopoDS_Solid, _ANALITICAS, gp_Ax1, gp_Ax2, gp_Dir
    global gp_Pnt, gp_Trsf, gp_Vec
    from OCP.BRepTools import BRepTools
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_NurbsConvert, BRepBuilderAPI_Transform
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
    from OCP.ShapeFix import ShapeFix_Shape
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopAbs import (TopAbs_COMPOUND, TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_REVERSED,
                            TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX, TopAbs_WIRE)
    from OCP.OCP.collections import (IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher,
                                     IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher)
    from OCP.TopExp import TopExp, TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS, TopoDS_Compound, TopoDS_Face, TopoDS_Iterator, TopoDS_Shell, TopoDS_Solid
    from OCP.BRep import BRep_Builder
    from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
    _ANALITICAS = (GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Sphere, GeomAbs_Torus, GeomAbs_SurfaceOfExtrusion,
                   GeomAbs_SurfaceOfRevolution)


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()


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
    return plano_desde_normal(n, (loc.X(), loc.Y(), loc.Z()))


def plano_desde_normal(n, punto):
    """Plano de boceto con normal saliente `n` que pasa por `punto`, con los ejes de `plano_de_cara`."""
    n = np.asarray(n, float)
    origen = n * float(n @ np.asarray(punto, float))
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
    if abs(angulo_grados) > 360.0 + 1e-6:
        raise ErrorGeometria("El ángulo de revolución no puede pasar de 360°: más de una vuelta se pisa a sí misma.")
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


def _segmentar_tubo_cerrado(forma):
    """Divide longitudinalmente el lateral B-spline de un tubo antes de clasificarlo en una booleana.

    B-52: un lateral cerrado que recorre varias vueltas confunde al BOP al cruzar un toroide;
    dividir su dominio conserva la superficie y permite clasificar cada tramo por separado.
    shortcut: solo tubos de tres caras; ampliar a otros barridos cuando haya un reproductor.
    """
    from OCP.GeomAbs import GeomAbs_BSplineSurface
    from OCP.ShapeUpgrade import ShapeUpgrade_ShapeDivideArea

    cs = caras(forma)
    if len(cs) != 3:
        return forma
    for cara in cs:
        sup = BRepAdaptor_Surface(cara)
        if (sup.GetType() != GeomAbs_BSplineSurface or not sup.IsUClosed() or sup.IsVClosed()
                or sup.BSpline().NbVPoles() <= 4 * sup.BSpline().NbUPoles()):
            continue
        # Dos tramos por intervalo de nudos del barrido, sin aproximar ni mover sus caras.
        cantidad = 2 * (sup.BSpline().NbVKnots() - 1)
        division = ShapeUpgrade_ShapeDivideArea(forma)
        division.SetSplittingByNumber(True)
        division.NbParts = cantidad
        division.SetNumbersUVSplits(1, cantidad)
        division.Perform()
        resultado = division.Result()
        if (resultado.IsNull() or not es_valida(resultado)
                or abs(volumen_exacto(resultado) - volumen_exacto(forma)) > 1e-6 * abs(volumen_exacto(forma))):
            return forma                  # no se pudo dividir sin alterar nada: la booleana sigue como antes
        return resultado
    return forma


def _booleana(objetivo, herramienta, operacion, *, paralelo=True, fuzzy=0.0, invertir=False, nurbs=False, sanar=False):
    """Una pasada del kernel (BOP). `invertir` cambia objetivo y herramienta (solo 'unir' e 'intersecar', que son
    simétricas); `fuzzy` es la tolerancia difusa en mm; `paralelo=False` corre en un solo hilo; `nurbs` pasa la
    herramienta a B-spline (misma forma, otro algoritmo de intersección: el de toro contra cilindro falla); `sanar`
    repara el resultado con ShapeFix (sólidos inválidos que el kernel devuelve sin quejarse)."""
    clases = {"unir": BRepAlgoAPI_Fuse, "cortar": BRepAlgoAPI_Cut, "intersecar": BRepAlgoAPI_Common}
    from OCP.collections import List_TopoDS_Shape
    if nurbs:
        herramienta = BRepBuilderAPI_NurbsConvert(herramienta, True).Shape()
    if invertir:
        objetivo, herramienta = herramienta, objetivo
    args, herr = List_TopoDS_Shape(), List_TopoDS_Shape()
    args.Append(_segmentar_tubo_cerrado(objetivo))
    herr.Append(_segmentar_tubo_cerrado(herramienta))
    op = clases[operacion]()
    op.SetArguments(args)
    op.SetTools(herr)
    op.SetRunParallel(paralelo)      # OpenCascade reparte el trabajo en varios núcleos (1,9–2× medido)
    if fuzzy:
        op.SetFuzzyValue(fuzzy)
    op.Build()
    if not op.IsDone():
        raise ErrorGeometria(f"La operación '{operacion}' falló en el kernel.")
    resultado = op.Shape()
    if sanar:
        reparador = ShapeFix_Shape(resultado)
        reparador.Perform()
        resultado = reparador.Shape()
    return _quitar_cables_colgados(unificar_caras(resultado))


# Reintentos de una booleana cuyo resultado no es creíble (B-39). Orden: lo que no cambia la geometría primero.
_REINTENTOS_BOOLEANA = (
    {"sanar": True},                     # el kernel devolvía un sólido inválido sin avisar: ShapeFix lo deja válido
    {"paralelo": False},                 # el modo paralelo del kernel a veces da un resultado distinto (1 de 15)
    {"invertir": True},                  # objetivo y herramienta intercambiados: otro camino de clasificación
    {"fuzzy": 1e-6},                     # tolerancia difusa: un contacto tangente casi exacto
    {"nurbs": True},                     # herramienta en B-spline: un toro cruzando un cilindro devolvía «sin contacto»
    {"fuzzy": 1e-5}, {"fuzzy": 1e-4},
    {"nurbs": True, "invertir": True},
    {"fuzzy": 1e-6, "sanar": True}, {"nurbs": True, "sanar": True},     # lo que salvó el volumen pero salió inválido
)
_TOPE_VOLUMEN_BOOLEANA_ERROR = 1e-4   # exceso (parte del volumen total) a partir del cual ya no se devuelve el resultado
_TOPE_VOLUMEN_BOOLEANA = 1e-3     # parte del volumen de la pieza más chica que se tolera de más o de menos (más 1e-6 del total)


def _aristas_defectuosas(forma):
    """(aristas libres, aristas no manifold) de una forma: libre = una sola cara (que no es costura); no manifold =
    más de dos caras."""
    vecinas = IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapesAndAncestors_s(forma, TopAbs_EDGE, TopAbs_FACE, vecinas)
    libres = no_manifold = 0
    for i in range(1, vecinas.Size() + 1):
        arista = TopoDS.Edge(vecinas.FindKey(i))
        if BRep_Tool.Degenerated_s(arista):
            continue
        unicas = []
        for f in lista_occ(vecinas.FindFromIndex(i)):
            if not any(f.IsSame(u) for u in unicas):
                unicas.append(f)
        if len(unicas) == 1 and not BRep_Tool.IsClosed_s(arista, TopoDS.Face(unicas[0])):
            libres += 1
        elif len(unicas) > 2:
            no_manifold += 1
    return libres, no_manifold


def _volumenes_entrada(objetivo, herramienta):
    """(volumen del objetivo, de la herramienta) por integración exacta, medidos ANTES de la booleana: el kernel
    puede invertir la orientación de una entrada al correr (el volumen de la herramienta pasa a negativo). None si
    alguna tiene superficies libres, donde la integración exacta puede errar mucho."""
    if any(es_forma_libre(f) or not solidos(f) for f in (objetivo, herramienta)):
        return None
    vols = tuple(abs(_integral(f, BRepGProp.VolumeProperties_s)) for f in (objetivo, herramienta))
    return vols if min(vols) > 1e-9 else None


def _problema_booleana(objetivo, herramienta, operacion, resultado, volumenes):
    """None si el resultado de la booleana es creíble; si no, (gravedad, texto, exceso, escala). Gravedad 2: volumen
    imposible (el kernel perdió material o inventó; `exceso` es cuánto se pasa del rango, `escala` el volumen total de
    las entradas); 1: sólido inválido o aristas libres / no manifold que las entradas no tenían (`exceso` pesa cuántos).
    `volumenes`: lo que devolvió `_volumenes_entrada` (o None). Solo se verifica entre sólidos: una cara o una
    superficie como herramienta (extrusión «hasta objeto», recortes) da resultados sin volumen y con bordes libres."""
    if not (solidos(objetivo) and solidos(herramienta)):
        return None
    if resultado is None or resultado.IsNull() or esta_vacia(resultado):
        # Intersecar sin nada en común es legítimo; cortar solo si la herramienta cubre todo el objetivo. Unir nunca
        # da vacío (una herramienta con 1e-6 mm de solape contra una placa hacía desaparecer ambas).
        if operacion == "unir":
            return 2, "el resultado quedó vacío", float("inf"), 0.0
        if operacion == "cortar" and volumenes is not None and volumenes[0] > volumenes[1] * (1 + 1e-6) + 1e-6:
            return 2, "el resultado quedó vacío aunque la herramienta no cubre el objetivo", float("inf"), 0.0
        return None
    try:
        if volumenes is not None:
            vb, vh = volumenes
            vr = abs(_integral(resultado, BRepGProp.VolumeProperties_s))
            # Un resultado con caras B-spline (el reintento con nurbs) integra menos exacto: tolerancia 30 veces mayor
            tol = 1e-6 * (vb + vh) + _TOPE_VOLUMEN_BOOLEANA * (30 if es_forma_libre(resultado) else 1) * min(vb, vh)
            limites = {"unir": (max(vb, vh), vb + vh), "cortar": (vb - vh, vb), "intersecar": (0.0, min(vb, vh))}
            minimo, maximo = limites[operacion]
            if vr < minimo - tol or vr > maximo + tol:
                exceso = max(minimo - vr, vr - maximo)
                return 2, f"volumen {vr:.6g} mm³ fuera de lo posible ({minimo:.6g} a {maximo:.6g})", exceso, vb + vh
    except Exception:  # noqa: BLE001 — una integración que falla no es motivo para rechazar el resultado
        pass
    problemas, peso = [], 0.0
    libres, no_manifold = _aristas_defectuosas(resultado)
    if libres or no_manifold:
        (l1, n1), (l2, n2) = _aristas_defectuosas(objetivo), _aristas_defectuosas(herramienta)
        if libres > l1 + l2 or no_manifold > n1 + n2:
            problemas.append(f"{libres} aristas libres y {no_manifold} no manifold")
            peso += libres + no_manifold
    if not es_valida(resultado) and es_valida(objetivo) and es_valida(herramienta):
        problemas.append("sólido inválido")
        peso += 10.0                        # un sólido inválido rompe las operaciones que siguen: peor que un par de aristas
    return (1, " y ".join(problemas), peso, 0.0) if problemas else None


def _cambia_el_volumen(a, b, volumenes):
    """True si dos resultados de la misma booleana difieren en más de 5 % de la pieza más chica de las entradas."""
    try:
        va, vb = (abs(_integral(f, BRepGProp.VolumeProperties_s)) for f in (a, b))
    except Exception:  # noqa: BLE001
        return False
    return abs(va - vb) > 0.05 * min(volumenes)


def booleano(objetivo, herramienta, operacion):
    """'unir' | 'cortar' | 'intersecar' (FeatureOperations Join/Cut/Intersect de Fusion).

    B-39: el kernel a veces devuelve un resultado imposible con un contacto casi tangente (una esfera centrada a
    1e-6 mm de la cara de una pared devolvía SOLO la esfera, 806 mm³ en vez de 75 722) o distinto de una corrida a
    otra. Se verifica el resultado (volumen dentro de lo posible, sin aristas libres ni no manifold nuevas, sólido
    válido) y, si no es creíble, se reintenta (un hilo, roles invertidos, tolerancia difusa 1e-6…1e-4 mm). Si
    ninguno lo arregla, gana el menos malo; un volumen imposible nunca se devuelve: es un error claro."""
    if operacion not in ("unir", "cortar", "intersecar"):
        raise ErrorGeometria(f"Operación booleana desconocida: {operacion}")
    volumenes = _volumenes_entrada(objetivo, herramienta)
    resultado = _booleana(objetivo, herramienta, operacion)
    problema = _problema_booleana(objetivo, herramienta, operacion, resultado, volumenes)
    if problema is None:
        return resultado
    mejor, peor_problema = resultado, problema
    for intento in _REINTENTOS_BOOLEANA:
        if intento.get("invertir") and operacion == "cortar":
            continue
        if intento.get("nurbs") and (problema[0] < 2 and volumenes is None):
            continue                # sin volúmenes de referencia no hay cómo saber si el B-spline cambió el resultado
        try:
            candidato = _booleana(objetivo, herramienta, operacion, **intento)
        except ErrorGeometria:
            continue
        p = _problema_booleana(objetivo, herramienta, operacion, candidato, volumenes)
        if p is None and intento.get("nurbs") and problema[0] < 2:
            # El B-spline mueve el volumen unas milésimas (285: +0,8 % de la herramienta, un contacto tangente que ya era
            # correcto). Vale solo si el cambio es grande: el resultado anterior decía «sin contacto» con aristas rotas.
            if not _cambia_el_volumen(resultado, candidato, volumenes):
                continue
        if p is None:
            return candidato
        if (p[0], p[2]) < (peor_problema[0], peor_problema[2]):
            mejor, peor_problema = candidato, p
    if peor_problema[0] >= 2 and peor_problema[2] > _TOPE_VOLUMEN_BOOLEANA_ERROR * peor_problema[3]:
        raise ErrorGeometria(f"La operación '{operacion}' dio un resultado imposible ({peor_problema[1]}) y el kernel "
                             "no logró corregirlo: probá mover la pieza una milésima de milímetro.")
    return mejor


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


def _quitar_cables_colgados(forma):
    """Saca de las caras los cables internos ABIERTOS cuyas aristas tocan una sola cara.

    El kernel deja esos cables cuando una booleana tiene contacto TANGENCIAL: unir un cuerpo cuyo
    disco de apoyo queda justo tangente a una cara curva del objetivo (B-28: el puerto de
    oxidante del motor cohete contra la pared interior r=45 de la camisa) cuelga de esa cara los
    tramos de la línea de tangencia que no unen nada. Son restos topológicos sin volumen ni área:
    «Revisar geometría» los cuenta como aristas libres y el cuerpo sale «no estanco» con todo su
    material. Si no hay nada que sacar (lo normal), o la forma reconstruida no queda tan bien como
    la original, se devuelve tal cual: peor caso, el defecto queda como estaba."""
    if forma is None or forma.IsNull() or forma.ShapeType() not in (TopAbs_SOLID, TopAbs_COMPOUND):
        return forma
    vecinas = IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapesAndAncestors_s(forma, TopAbs_EDGE, TopAbs_FACE, vecinas)
    colgantes = []
    for i in range(1, vecinas.Size() + 1):
        arista = TopoDS.Edge(vecinas.FindKey(i))
        if BRep_Tool.Degenerated_s(arista):
            continue
        unicas = []
        for f in lista_occ(vecinas.FindFromIndex(i)):
            if not any(f.IsSame(u) for u in unicas):
                unicas.append(f)          # una costura de cara periódica aparece dos veces
        if len(unicas) == 1 and not BRep_Tool.IsClosed_s(arista, TopoDS.Face(unicas[0])):
            colgantes.append(arista)
    if not colgantes:
        return forma

    def es_colgante(a):
        return any(a.IsSame(c) for c in colgantes)

    builder = BRep_Builder()

    def reconstruir(cara_cruda):
        """Cara nueva sin los cables colgados (con las orientaciones ALMACENADAS, sin componer), o None."""
        vista = TopoDS.Face(cara_cruda)
        vista.Orientation(TopAbs_FORWARD)      # explorar los cables con su orientación guardada
        exterior = BRepTools.OuterWire_s(vista)
        quedan, saco = [], False
        exw = TopExp_Explorer(vista, TopAbs_WIRE)
        while exw.More():
            w = TopoDS.Wire(exw.Current())
            if (exterior is not None and w.IsSame(exterior)) or w.Closed():
                quedan.append(w)                # el borde de la cara y los agujeros reales se quedan
            else:
                exa = TopExp_Explorer(w, TopAbs_EDGE)
                while exa.More():
                    if not es_colgante(TopoDS.Edge(exa.Current())):
                        quedan.append(w)        # el cable une esta cara con otra: no es un resto
                        break
                    exa.Next()
                else:
                    saco = True
            exw.Next()
        if not saco:
            return None
        loc = TopLoc_Location()
        superficie = BRep_Tool.Surface_s(vista, loc)
        nueva = TopoDS_Face()
        builder.MakeFace(nueva, superficie, loc, BRep_Tool.Tolerance_s(vista))
        for w in quedan:
            builder.Add(nueva, w)
        nueva.Orientation(cara_cruda.Orientation())
        nueva.Location(cara_cruda.Location())
        return nueva

    def hijos(shape):
        """Subformas directas con su orientación y ubicación ALMACENADAS (sin componer)."""
        it = TopoDS_Iterator(shape, False, False)
        while it.More():
            yield it.Value()
            it.Next()

    solidos_crudos = [forma] if forma.ShapeType() == TopAbs_SOLID else list(hijos(forma))
    if not solidos_crudos or any(s.ShapeType() != TopAbs_SOLID for s in solidos_crudos):
        return forma
    caras_antes = len(caras(forma))
    nuevos = []
    for solido in solidos_crudos:
        nuevo_solido = TopoDS_Solid()
        builder.MakeSolid(nuevo_solido)
        for cascara in hijos(solido):
            if cascara.ShapeType() != TopAbs_SHELL:
                return forma
            nueva_cascara = TopoDS_Shell()
            builder.MakeShell(nueva_cascara)
            for cara in hijos(cascara):
                nueva = reconstruir(cara)
                builder.Add(nueva_cascara, cara if nueva is None else nueva)
            nueva_cascara.Orientation(cascara.Orientation())
            nueva_cascara.Location(cascara.Location())
            builder.Add(nuevo_solido, nueva_cascara)
        nuevo_solido.Orientation(solido.Orientation())
        nuevo_solido.Location(solido.Location())
        nuevos.append(nuevo_solido)
    limpia = nuevos[0] if len(nuevos) == 1 else None
    if limpia is None:
        compuesto = TopoDS_Compound()
        builder.MakeCompound(compuesto)
        for s in nuevos:
            builder.Add(compuesto, s)
        limpia = compuesto
    volumen_original = volumen(forma)
    mejora = (es_valida(limpia) and len(caras(limpia)) == caras_antes
              and len(solidos(limpia)) == len(solidos_crudos)
              and abs(volumen(limpia) - volumen_original) <= 1e-4 * max(volumen_original, 1e-9))
    return limpia if mejora else forma


def _union_general_creible(formas, unida):
    """False si la unión de varias formas no está vacía y su volumen cae fuera de [la mayor, la suma] (B-39: el
    kernel perdía material sin avisar); entonces `unir_todos` une de a pares, que sí reintenta. Solo entre sólidos."""
    try:
        if esta_vacia(unida):
            return False
        if any(es_forma_libre(f) or not solidos(f) for f in (*formas, unida)):
            return True
        vols = [abs(_integral(f, BRepGProp.VolumeProperties_s)) for f in formas]
        tol = 1e-6 * sum(vols) + _TOPE_VOLUMEN_BOOLEANA * min(vols)
        return max(vols) - tol <= abs(_integral(unida, BRepGProp.VolumeProperties_s)) <= sum(vols) + tol
    except Exception:  # noqa: BLE001 — una integración que falla no rechaza la unión
        return True


def unir_todos(formas):
    """Une todas las formas. Con más de dos, una sola operación general (una pasada del kernel en vez de una unión
    por pieza contra un resultado cada vez más grande: con el texto de un repujado era lo que más tardaba)."""
    formas = [f for f in formas if f is not None]
    if not formas:
        raise ErrorGeometria("No hay geometría para unir.")
    if len(formas) > 2:
        try:
            from OCP.collections import List_TopoDS_Shape
            args, herr = List_TopoDS_Shape(), List_TopoDS_Shape()
            args.Append(formas[0])
            for f in formas[1:]:
                herr.Append(f)
            op = BRepAlgoAPI_Fuse()
            op.SetArguments(args)
            op.SetTools(herr)
            op.SetRunParallel(True)
            op.Build()
            if op.IsDone() and not op.Shape().IsNull():
                unida = _quitar_cables_colgados(unificar_caras(op.Shape()))
                if _union_general_creible(formas, unida):
                    return unida
        except Exception:  # noqa: BLE001 — si la operación general no puede, queda la unión de a pares
            pass
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


def punto_toca(forma, punto, tolerancia=1e-6):
    """¿El punto está sobre la forma (o dentro de ella si es un sólido), con esa tolerancia?"""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    return se_tocan(BRepBuilderAPI_MakeVertex(gp_Pnt(*[float(c) for c in punto])).Vertex(), forma, tolerancia)


def es_valida(forma):
    return BRepCheck_Analyzer(forma, True, True).IsValid()    # en paralelo: 125 → 68 ms medido (plan_cpp.md P19)


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
    booleana) mide entre los bordes, y una cavidad interna daba «no se tocan» (el corte automático la salteaba).
    La distancia exacta entre formas enteras cuesta 2–7 s por par en piezas de 20–230 caras, así que se mide cara con
    cara, solo entre las que se solapan por caja envolvente, y se corta al primer contacto."""
    ba, bb = _caja_occ(a, tolerancia), _caja_occ(b, tolerancia)
    if ba is not None and bb is not None and ba.IsOut(bb):
        return False
    if _adentro(a, b, tolerancia) or _adentro(b, a, tolerancia):     # ~4 ms; resuelve superposición y contención
        return True
    caras_a, caras_b = caras(a), caras(b)
    if ba is None or bb is None or not caras_a or not caras_b:       # un vértice o aristas sueltas: forma entera
        d = BRepExtrema_DistShapeShape(a, b)
        return d.IsDone() and d.Value() <= tolerancia
    cercanas_b = [(f, x) for f in caras_b if (x := _caja_occ(f, tolerancia)) is not None and not x.IsOut(ba)]
    for fa in caras_a:
        xa = _caja_occ(fa, tolerancia)
        if xa is None or xa.IsOut(bb):
            continue
        for fb, xb in cercanas_b:
            if not xa.IsOut(xb):
                d = BRepExtrema_DistShapeShape(fa, fb)
                if d.IsDone() and d.Value() <= tolerancia:
                    return True
    return False


def _caja_occ(forma, holgura):
    """Bnd_Box de OCC de `forma` agrandada en `holgura` (con la tolerancia de la forma), o None si no tiene geometría."""
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(forma, b, False, True)
    if b.IsVoid():
        return None
    b.Enlarge(holgura)
    return b


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


def _aristas_unicas(forma):
    """Las aristas de una forma, sin repetir: TopExp visita una arista compartida una vez por cada cara."""
    mapa = IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapes_s(forma, TopAbs_EDGE, mapa)
    return [TopoDS.Edge(mapa.FindKey(i)) for i in range(1, mapa.Size() + 1)]


def _rotar(v, eje, angulo_rad):
    """Rotación de Rodrigues del vector v alrededor de un eje unitario."""
    c, s = math.cos(angulo_rad), math.sin(angulo_rad)
    return v * c + np.cross(eje, v) * s + eje * float(eje @ v) * (1 - c)


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


_motor.registrar(globals(), _iniciar_opencascade)
