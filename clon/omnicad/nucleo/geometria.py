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
import os
import random

import numpy as np
from . import motor as _motor

# B-48: el paralelismo de OpenCascade se apaga con OMNICAD_SIN_PARALELO=1 para medir/aislar caídas nativas
# (reusa formas entre hilos). Queda como interruptor de diagnóstico; el valor por defecto no cambia.
PARALELO = os.environ.get("OMNICAD_SIN_PARALELO", "").strip().lower() not in ("1", "si", "sí", "true", "on")


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
    global BRepPrimAPI_MakeSphere, BRepPrimAPI_MakeTorus, BRepTools, BRepTools_WireExplorer, BRep_Builder, BRep_Tool, Bnd_Box
    global GCPnts_TangentialDeflection, GProp_GProps, GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane
    global GeomAbs_Sphere, GeomAbs_SurfaceOfExtrusion, GeomAbs_SurfaceOfRevolution, GeomAbs_Torus
    global Poly_Triangle, Poly_Triangulation, ShapeAnalysis_Surface
    global IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher
    global IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher, ShapeUpgrade_UnifySameDomain, TopAbs_COMPOUND
    global TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_ON, TopAbs_REVERSED, TopAbs_SHELL, TopAbs_SOLID
    global TopAbs_VERTEX, TopAbs_WIRE, TopExp, TopExp_Explorer, TopLoc_Location, TopoDS, TopoDS_Compound
    global TopoDS_Face, TopoDS_Iterator, TopoDS_Shell, TopoDS_Solid, _ANALITICAS, gp_Ax1, gp_Ax2, gp_Dir
    global gp_Pnt, gp_Pnt2d, gp_Trsf, gp_Vec
    from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
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
    from OCP.Poly import Poly_Triangle, Poly_Triangulation
    from OCP.ShapeAnalysis import ShapeAnalysis_Surface
    from OCP.ShapeFix import ShapeFix_Shape
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopAbs import (TopAbs_COMPOUND, TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_ON,
                            TopAbs_REVERSED, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX, TopAbs_WIRE)
    from OCP.OCP.collections import (IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher,
                                     IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher)
    from OCP.TopExp import TopExp, TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS, TopoDS_Compound, TopoDS_Face, TopoDS_Iterator, TopoDS_Shell, TopoDS_Solid
    from OCP.BRep import BRep_Builder
    from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Pnt2d, gp_Trsf, gp_Vec
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

    def girado(self, grados, nombre=None):
        """El plano girado `grados` (regla de la mano derecha) alrededor de su eje u, que pasa por su origen."""
        t = math.radians(float(grados))
        normal = self.normal * math.cos(t) + np.cross(self.u, self.normal) * math.sin(t)
        return Plano.desde_marco(self.origen, normal, self.u, nombre or self.nombre)

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


def _booleana(objetivo, herramienta, operacion, *, paralelo=True, fuzzy=0.0, invertir=False, nurbs=False, sanar=False,
              pegar=False, obb=False, con_historial=False, varias=False):
    """Una pasada del kernel (BOP). `invertir` cambia objetivo y herramienta (solo 'unir' e 'intersecar', que son
    simétricas); `fuzzy` es la tolerancia difusa en mm; `paralelo=False` corre en un solo hilo; `nurbs` pasa la
    herramienta a B-spline (misma forma, otro algoritmo de intersección: el de toro contra cilindro falla); `sanar`
    repara el resultado con ShapeFix (sólidos inválidos que el kernel devuelve sin quejarse); `pegar` activa el modo
    pegado (GlueShift: las caras que solo se tocan no se recomputan); `obb` usa la caja envolvente orientada para
    descartar intersecciones.
    `con_historial`: devuelve también las copias de caras de las entradas que no cambiaron, para su revisión.
    `varias`: cada sólido de `herramienta` entra como herramienta propia (un compuesto de sólidos que se tocan no
    sirve de argumento)."""
    entradas = (objetivo, herramienta)
    clases = {"unir": BRepAlgoAPI_Fuse, "cortar": BRepAlgoAPI_Cut, "intersecar": BRepAlgoAPI_Common}
    from OCP.collections import List_TopoDS_Shape
    if nurbs:
        herramienta = BRepBuilderAPI_NurbsConvert(herramienta, True).Shape()
    if invertir:
        objetivo, herramienta = herramienta, objetivo
    args, herr = List_TopoDS_Shape(), List_TopoDS_Shape()
    args.Append(_segmentar_tubo_cerrado(objetivo))
    for h in solidos(herramienta) if varias else [herramienta]:
        herr.Append(_segmentar_tubo_cerrado(h))
    op = clases[operacion]()
    op.SetArguments(args)
    op.SetTools(herr)
    op.SetRunParallel(paralelo and PARALELO)   # OpenCascade reparte el trabajo en varios núcleos (1,9–2× medido)
    if fuzzy:
        op.SetFuzzyValue(fuzzy)
    if pegar:
        from OCP.BOPAlgo import BOPAlgo_GlueShift
        op.SetGlue(BOPAlgo_GlueShift)
    if obb:
        op.SetUseOBB(True)
    op.Build()
    if not op.IsDone():
        raise ErrorGeometria(f"La operación '{operacion}' falló en el kernel.")
    resultado = op.Shape()
    if sanar:
        # Copia ANTES de ShapeFix: el resultado comparte topología con las entradas y ShapeFix repara «in place»,
        # dejando inválida la forma viva que llamó (B-39: después el guard de entradas tapaba el problema).
        reparador = ShapeFix_Shape(BRepBuilderAPI_Copy(resultado).Shape())
        reparador.Perform()
        resultado = reparador.Shape()
    if con_historial:
        resultado, intactas = _unificar_caras(resultado, entradas)
        return _quitar_cables_colgados(resultado), intactas
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
    {"pegar": True}, {"obb": True},                  # GlueShift y caja orientada: dos caminos de intersección distintos
)
_TOPE_VOLUMEN_BOOLEANA = 1e-3     # parte del volumen de la pieza más chica que se tolera de más o de menos (más 1e-6 del total)
_RESOLUCION_BOOLEANA = 1e-5       # mm: debajo de esto una herramienta deja autointersecciones o partes sueltas (B-128)
_MUESTRAS_AFUERA = 16
_MUESTRAS_COMUN = (500, 4000)    # B-144: muestreo del común intermedio; la 2.ª etapa solo si la diferencia es ambigua
_MAX_PIEZAS_REVISADAS = 16


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


_MAX_CONTORNOS_REVISADOS = 200   # BRepCheck clasifica los contornos de una cara de a pares: 3000 agujeros cuestan 11 s
_MAX_CARAS_REVISADAS = 200       # revisar también cáscaras y sólidos, sin penalizar los cuerpos grandes


def _caja_adentro(interior, exterior):
    """True si la caja `interior` entra en la caja `exterior`."""
    a0, a1, c0, c1 = exterior.CornerMin(), exterior.CornerMax(), interior.CornerMin(), interior.CornerMax()
    return (c0.X() >= a0.X() and c0.Y() >= a0.Y() and c0.Z() >= a0.Z()
            and c1.X() <= a1.X() and c1.Y() <= a1.Y() and c1.Z() <= a1.Z())


def _clasificador(solido):
    """Clasificador de puntos de `solido`. Una booleana puede dejar invertida la orientación de una entrada, y entonces
    adentro y afuera se cambian: el punto del infinito lo delata."""
    c = BRepClass3d_SolidClassifier(solido)
    c.PerformInfinitePoint(1e-7)
    return BRepClass3d_SolidClassifier(solido.Reversed()) if c.State() == TopAbs_IN else c


def _muestras_adentro(forma, cuantas, intentos):
    """Hasta `cuantas` puntos al azar del interior de `forma`. Semilla fija: el veredicto no cambia de corrida a corrida."""
    caja = _caja_occ(forma, 1e-5, holgada=True)
    if caja is None:
        return
    c0, c1 = caja.CornerMin(), caja.CornerMax()
    clasificadores = [_clasificador(s) for s in solidos(forma)]
    rng = random.Random("b39-enterrada")
    dados = 0
    for _ in range(intentos):
        p = gp_Pnt(rng.uniform(c0.X(), c1.X()), rng.uniform(c0.Y(), c1.Y()), rng.uniform(c0.Z(), c1.Z()))
        for c in clasificadores:
            c.Perform(p, 1e-7)
            if c.State() == TopAbs_IN:
                yield p
                dados += 1
                break
        if dados == cuantas:
            return


def _parte_afuera(chica, grande, cuantas=_MUESTRAS_AFUERA, al_menos=1):
    """Qué parte de `chica` queda afuera de `grande` (0 a 1), contando puntos: el kernel no sirve para decidirlo (con un
    contacto casi tangente el común de dos toros devolvía un toro entero). None si no se puede saber. `cuantas` sube
    la precisión (y el costo: ~0,03 s con 500, ~0,25 s con 4000 en piezas chicas). `al_menos`: si se juntan menos
    muestras que las pedidas, None: con menos puntos el margen de error sale mal (una herramienta rala, como un anillo,
    deja la caja casi vacía) y el margen desmentiría un corte bueno.
    shortcut: si la caja de `chica` entra en la de un `grande` de más de _MAX_CARAS_REVISADAS caras da None sin muestrear
    (7 ms por punto en una placa de 3000 agujeros), subir si aparece una pieza perdida en un hueco de un cuerpo grande."""
    if len(caras(grande)) > _MAX_CARAS_REVISADAS:
        cg, cc = _caja_occ(grande, 1e-5, holgada=True), _caja_occ(chica, 1e-5, holgada=True)
        if cg is None or cc is None or _caja_adentro(cc, cg):
            return None
    clasificadores = [_clasificador(s) for s in solidos(grande)]

    def adentro(p):
        for c in clasificadores:
            c.Perform(p, 1e-7)
            if c.State() in (TopAbs_IN, TopAbs_ON):
                return True
        return False
    muestras = list(_muestras_adentro(chica, cuantas, 20 * cuantas))
    if len(muestras) < al_menos:
        return None
    return sum(not adentro(p) for p in muestras) / len(muestras)


def _comun_desmentido(objetivo, herramienta, operacion, vr, volumenes):
    """Cada booleana afirma cuánto comparten las piezas: unir va + vb − vr, cortar va − vr, intersecar vr. Si afirma un
    extremo (la chica entera adentro, o nada en común) cae justo en el borde del rango de volumen, donde un resultado
    malo pasa: dos toros casi tangentes perdían uno al unir y una esfera apoyada en una pared no cortaba nada (B-125).
    Ahí lo comprueban los puntos con un margen de 1/4 de la chica (un falso positivo rechaza un resultado bueno). El
    kernel también pierde material EN EL MEDIO del rango (B-144: una esfera casi tangente a una pared quitaba 104 de
    los 122,5 mm³ compartidos y el margen de 1/4 no lo ve): ahí se prueba la proporción reclamada contra un muestreo
    más fino, con margen de 4,5 desvíos de esa proporción; solo si la diferencia queda ambigua se afina el muestreo.
    Unir sin nada en común no se mira: es lo normal y no pierde material. El muestreo fino se salta cuando la pieza es
    compleja o la herramienta es rala (un anillo no llena las muestras): mejor sin chequeo que lento o falso.
    Devuelve el problema o None."""
    vb, vh = volumenes
    v = min(vb, vh)
    tol = 1e-6 * (vb + vh) + _TOPE_VOLUMEN_BOOLEANA * v
    comun = {"unir": vb + vh - vr, "cortar": vb - vr, "intersecar": vr}[operacion]
    chica, grande = (objetivo, herramienta) if vb <= vh else (herramienta, objetivo)
    if operacion != "unir" and tol < comun < v - tol:
        if len(caras(chica)) > _MAX_CARAS_REVISADAS or len(caras(grande)) > _MAX_CARAS_REVISADAS:
            return None       # el muestreo fino sería lento sobre una pieza compleja: mejor sin chequeo que lento
        for cuantas in _MUESTRAS_COMUN:
            afuera = _parte_afuera(chica, grande, cuantas, al_menos=cuantas)
            if afuera is None:
                return None
            dif = abs(comun - (1 - afuera) * v)
            # desvío de la proporción muestreada si el común reclamado fuera el verdadero, en mm³
            ruido = 4.5 * math.sqrt(comun * (v - comun) / cuantas)
            if dif >= ruido:
                break                # desmentida con confianza: cae al aviso de abajo
            if dif < ruido * (2 / 4.5):
                return None          # consistente con el muestreo
            # ambigua: se afina con más muestras; si sigue ambigua, no se desmiente
        else:
            return None
    else:
        if operacion == "unir" and comun < v - tol:
            return None
        afuera = _parte_afuera(chica, grande)
        if afuera is None or abs(comun - (1 - afuera) * v) < v / 4:
            return None
    return 2, (f"el resultado dice que las piezas comparten {comun:.6g} mm³ y los puntos dan cerca de "
               f"{(1 - afuera) * v:.6g} mm³"), abs(comun - (1 - afuera) * v), vb + vh


def _es_valida_tras_booleana(resultado, entradas, caras_intactas=()):
    """Como `es_valida`, pero solo de las caras que la booleana creó o cambió: el resto son las de las entradas (la
    booleana comparte su topología) y ya las revisó quien las hizo; revisar todo cuesta lo de la cara con más contornos
    al cuadrado (B-39 pagaba 12 de 15 s en una placa de 3000 agujeros). Si el resultado es un sólido chico (hasta
    _MAX_CARAS_REVISADAS caras) se revisa ENTERO: los defectos de cáscara/sólido no los ve ninguna revisión por cara.
    El cierre del sólido lo cubren `_aristas_defectuosas` y el volumen de `_problema_booleana`. Las caras de las
    entradas siguen siendo válidas porque `unificar_caras` y `sanar` copian antes de tocar topología compartida (B-39).
    shortcut: una cara cambiada con más de _MAX_CONTORNOS_REVISADOS contornos no se revisa, subir si aparece un caso.
    Los resultados chicos se revisan en serie, manteniendo los controles geométricos completos.
    `caras_intactas` identifica las copias que el historial de unificación conserva sin cambios."""
    if solidos(resultado) and len(caras(resultado)) <= _MAX_CARAS_REVISADAS:
        return BRepCheck_Analyzer(resultado, GeomControls=True, theIsParallel=False).IsValid()
    conocidas = IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
    for e in entradas:
        for c in caras(e):
            conocidas.Add(c)
    for c in caras_intactas:
        conocidas.Add(c)
    builder, nuevas = BRep_Builder(), TopoDS_Compound()
    builder.MakeCompound(nuevas)
    for c in caras(resultado):
        if not conocidas.Contains(c) and sum(1 for _ in _explorar(c, TopAbs_WIRE)) <= _MAX_CONTORNOS_REVISADOS:
            builder.Add(nuevas, c)
    if len(caras(nuevas)) <= _MAX_CARAS_REVISADAS:
        return BRepCheck_Analyzer(nuevas, GeomControls=True, theIsParallel=False).IsValid()
    return _brepcheck_estable(nuevas)


def _problema_booleana(objetivo, herramienta, operacion, resultado, volumenes, caras_intactas=()):
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
        if operacion == "cortar":
            # B-165: un agujero tangente a dos paredes borraba la caja y le quedaba el 8 % en las esquinas; el margen de
            # 1/4 de `_comun_desmentido` no lo ve. Si no queda nada, el objetivo fuera de la herramienta lo desmiente.
            afuera = _parte_afuera(objetivo, herramienta, _MUESTRAS_COMUN[0])
            if afuera is not None and afuera > 0.01:
                return 2, (f"el resultado quedó vacío aunque el {afuera:.0%} del objetivo está fuera de la "
                           "herramienta"), float("inf"), 0.0
        return None if volumenes is None else _comun_desmentido(objetivo, herramienta, operacion, 0.0, volumenes)
    try:
        if volumenes is not None:
            vb, vh = volumenes
            vr = abs(_integral(resultado, BRepGProp.VolumeProperties_s))
            chica, grande = (objetivo, herramienta) if vb <= vh else (herramienta, objetivo)
            # Misma tolerancia que el oráculo del fuzz: una integración B-spline que se pasa no es «casi correcta»
            tol = 1e-6 * (vb + vh) + _TOPE_VOLUMEN_BOOLEANA * min(vb, vh)
            limites = {"unir": (max(vb, vh), vb + vh), "cortar": (vb - vh, vb), "intersecar": (0.0, min(vb, vh))}
            minimo, maximo = limites[operacion]
            if vr < minimo - tol or vr > maximo + tol:
                exceso = max(minimo - vr, vr - maximo)
                return 2, f"volumen {vr:.6g} mm³ fuera de lo posible ({minimo:.6g} a {maximo:.6g})", exceso, vb + vh
            desmentido = _comun_desmentido(objetivo, herramienta, operacion, vr, volumenes)
            if desmentido:
                return desmentido
            if operacion == "cortar" and vr > maximo - tol:
                # B-107: un corte que no quita nada cuando la herramienta sí atraviesa el material (el reintento
                # GlueShift devolvía el objetivo intacto con una cara tangente). El rango «hasta vb» no lo ve.
                try:
                    comun = abs(_integral(_booleana(objetivo, herramienta, "intersecar", paralelo=False),
                                          BRepGProp.VolumeProperties_s))
                except Exception:  # noqa: BLE001 — sin medir el común no se puede afirmar nada
                    comun = 0.0
                # El común puede devolver la chica entera aunque casi ni se toquen (B-125): las muestras lo desmienten
                if tol < comun <= (1 - (_parte_afuera(chica, grande) or 0.0) / 2) * min(vb, vh) * (1 + 1e-6):
                    return 2, (f"el corte no quitó material aunque la herramienta lo atraviesa "
                               f"({comun:.6g} mm³)"), comun, vb + vh
    except Exception:  # noqa: BLE001 — una integración que falla no es motivo para rechazar el resultado
        pass
    problemas, peso = [], 0.0
    libres, no_manifold = _aristas_defectuosas(resultado)
    if libres or no_manifold:
        (l1, n1), (l2, n2) = _aristas_defectuosas(objetivo), _aristas_defectuosas(herramienta)
        if libres > l1 + l2 or no_manifold > n1 + n2:
            problemas.append(f"{libres} aristas libres y {no_manifold} no manifold")
            peso += libres + no_manifold
    if (not _es_valida_tras_booleana(resultado, (objetivo, herramienta), caras_intactas)
            and es_valida(objetivo) and es_valida(herramienta)):
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


def _queda_enterrada(forma, base):
    """True si TODO el material de `forma` queda dentro de `base` (B-39: «herramienta enterrada»). Unir no cambiaría
    nada y lo correcto es devolver `base` tal cual, sin pasar por la fusión del kernel, cuyo contacto casi tangente
    era el que dejaba aristas libres. Filtros del más barato al más caro: superficies libres (ahí no se acorta),
    caja envolvente de `forma` contenida en la de `base` (baratas, Add_s), todos los vértices adentro de (o sobre)
    un sólido, muestras al azar de `forma` adentro de `base` (el kernel no es confiable acá: el común de un toro
    cruzando la pared devolvía el toro entero) y la resta `forma - base` vacía. Un resto con caras impide el atajo,
    aunque su volumen sea una fracción diminuta de la herramienta: puede ser un saliente real."""
    if not (solidos(forma) and solidos(base)):
        return False
    if es_forma_libre(forma) or es_forma_libre(base):
        return False       # con superficies libres la integración exacta puede errar: no se acorta, camino normal
    # Cajas BARATAS (Add_s) con 1e-5 de margen: la exacta (AddOptimal) sobre una pieza de cientos de caras B-spline
    # cuesta ~0,4 s (BINCHA); la caja solo descarta. Las muestras descartan y la resta exterior confirma.
    ba, bb = _caja_occ(base, 1e-5, holgada=True), _caja_occ(forma, 1e-5, holgada=True)
    if ba is None or bb is None or not _caja_adentro(bb, ba):
        return False
    sols_b = solidos(base)
    for v in _explorar(forma, TopAbs_VERTEX):
        p = BRep_Tool.Pnt_s(TopoDS.Vertex(v))
        if not any(BRepClass3d_SolidClassifier(s, p, 1e-7).State() in (TopAbs_IN, TopAbs_ON) for s in sols_b):
            return False
    dentro = 0
    for p in _muestras_adentro(forma, 200, 2000):
        dentro += 1
        if not any(BRepClass3d_SolidClassifier(s, p, 1e-7).State() in (TopAbs_IN, TopAbs_ON) for s in sols_b):
            return False                           # una muestra adentro de la forma y afuera del material
    if dentro < 50:
        return False
    try:
        resto = _booleana(forma, base, "cortar")
    except ErrorGeometria:
        return False                           # el kernel no pudo confirmar: que decida la fusión normal
    return esta_vacia(resto)


def _es_diminuta(forma):
    """True si `forma` es un sólido que entra en un cubo de _RESOLUCION_BOOLEANA de lado."""
    caja = _caja_occ(forma, 0.0, holgada=True) if solidos(forma) else None    # la exacta: ~0,4 s en cientos de B-spline
    if caja is None:
        return False
    c0, c1 = caja.CornerMin(), caja.CornerMax()
    return max(c1.X() - c0.X(), c1.Y() - c0.Y(), c1.Z() - c0.Z()) < _RESOLUCION_BOOLEANA


def _sin_cambios(forma, avisos):
    """B-128: una herramienta diminuta no cambia nada; pasarla por el kernel deja autointersecciones o partes sueltas."""
    if avisos is not None:
        avisos.append("una pieza mide menos de 0,00001 mm, por debajo de la precisión del modelado: no cambió nada.")
    return forma


def booleano(objetivo, herramienta, operacion, avisos=None):
    """'unir' | 'cortar' | 'intersecar' (FeatureOperations Join/Cut/Intersect de Fusion).

    `avisos` (lista, opcional): recibe el texto de lo que sale igual pero el usuario tiene que saber.

    B-39: si una forma queda entera dentro de la otra, unir devuelve la que la contiene sin tocar el kernel (el
    contacto casi tangente de una herramienta enterrada era el que dejaba aristas libres). El kernel a veces devuelve
    además un resultado imposible con un contacto casi tangente (una esfera centrada a 1e-6 mm de la cara de una
    pared devolvía SOLO la esfera, 806 mm³ en vez de 75 722) o distinto de una corrida a otra: se verifica el
    resultado (volumen dentro de lo posible, sin aristas libres ni no manifold nuevas, sólido válido) y, si no es
    creíble, se reintenta (un hilo, roles invertidos, tolerancia difusa, GlueShift, caja orientada). Si ninguno
    lo arregla, NUNCA se devuelve geometría sospechosa: es un error claro."""
    if operacion not in ("unir", "cortar", "intersecar"):
        raise ErrorGeometria(f"Operación booleana desconocida: {operacion}")
    volumenes = _volumenes_entrada(objetivo, herramienta)
    if volumenes is None:           # un cuerpo diminuto no llega al mínimo de volumen de `_volumenes_entrada`
        diminuta_h, diminuta_o = _es_diminuta(herramienta), _es_diminuta(objetivo)
        if operacion == "intersecar" and (diminuta_h or diminuta_o):
            return compuesto([])    # lo común tampoco llega a la precisión del modelado
        if operacion != "intersecar" and diminuta_h:
            return _sin_cambios(objetivo, avisos)
        if operacion == "unir" and diminuta_o:
            return _sin_cambios(herramienta, avisos)
    if operacion == "unir":
        if _queda_enterrada(herramienta, objetivo):
            return objetivo
        if _queda_enterrada(objetivo, herramienta):
            return herramienta
    return _booleana_verificada(objetivo, herramienta, operacion, volumenes, avisos)


def cortar_varias(objetivo, formas, avisos=None):
    """Combine › Cut de Fusion con varias Tool Bodies, en UNA pasada del kernel: de a una, cada pasada revisa un resultado
    cada vez más grande y el tiempo crecía con el cuadrado de las herramientas (T-20). Una pasada sola puede saltear
    una herramienta sin salirse del rango de volumen (1433 mm³ en 300 casos al azar), así que solo vale con herramientas
    separadas y si quita justo lo que cada una le quita sola al objetivo. Si no, lanza ErrorGeometria y quien llama corta
    de a una, que es más lento pero verifica cada herramienta."""
    if not all(solidos(f) for f in formas):
        raise ErrorGeometria("Cortar con varias herramientas juntas necesita que todas sean sólidos.")
    pesan = [f for f in formas if not _es_diminuta(f)]
    if len(pesan) < len(formas):
        _sin_cambios(objetivo, avisos)
    if not pesan:
        return objetivo
    cajas = [_caja_occ(f, 1e-5, holgada=True) for f in pesan]
    if not all(a.IsOut(b) for a, b in itertools.combinations(cajas, 2)):
        raise ErrorGeometria("Las herramientas se superponen: hay que cortar de a una.")
    herramienta = compuesto(pesan)
    volumenes = _volumenes_entrada(objetivo, herramienta)
    if volumenes is None:
        raise ErrorGeometria("Con superficies libres el volumen no comprueba el corte: hay que cortar de a una.")

    def medir(forma):
        return 0.0 if esta_vacia(forma) else abs(_integral(forma, BRepGProp.VolumeProperties_s))
    # El corte verificado de cada una, no el común: en un caso el común daba de menos igual que la pasada conjunta
    quita = sum(volumenes[0] - medir(booleano(objetivo, f, "cortar")) for f in pesan)
    resultado = _booleana_verificada(objetivo, herramienta, "cortar", volumenes, avisos, varias=True)
    if abs(volumenes[0] - quita - medir(resultado)) > 1e-6 * (volumenes[0] + quita):
        raise ErrorGeometria("El corte conjunto no quitó lo que debía: hay que cortar de a una.")
    return resultado


def _booleana_verificada(objetivo, herramienta, operacion, volumenes, avisos, **modo):
    """Corre el kernel y verifica el resultado; si no es creíble, reintenta (ver `booleano`). `modo`: va a cada pasada."""
    resultado, intactas = _booleana(objetivo, herramienta, operacion, con_historial=True, **modo)
    problema = _problema_booleana(objetivo, herramienta, operacion, resultado, volumenes, intactas)
    if problema is None:
        return resultado
    mejor, peor_problema = resultado, problema
    for intento in _REINTENTOS_BOOLEANA:
        if intento.get("invertir") and operacion == "cortar":
            continue
        if intento.get("nurbs") and (problema[0] < 2 and volumenes is None):
            continue                # sin volúmenes de referencia no hay cómo saber si el B-spline cambió el resultado
        try:
            candidato, intactas = _booleana(objetivo, herramienta, operacion, con_historial=True, **modo, **intento)
        except ErrorGeometria:
            continue
        p = _problema_booleana(objetivo, herramienta, operacion, candidato, volumenes, intactas)
        if p is None and intento.get("nurbs") and problema[0] < 2:
            # El B-spline mueve el volumen unas milésimas (285: +0,8 % de la herramienta, un contacto tangente que ya era
            # correcto). Vale solo si el cambio es grande: el resultado anterior decía «sin contacto» con aristas rotas.
            if not _cambia_el_volumen(resultado, candidato, volumenes):
                continue
        if p is None:
            return candidato
        if (p[0], p[2]) < (peor_problema[0], peor_problema[2]):
            mejor, peor_problema = candidato, p
    if peor_problema[0] >= 2:
        raise ErrorGeometria(f"La operación '{operacion}' dio un resultado imposible ({peor_problema[1]}) y el kernel "
                             "no logró corregirlo: probá mover la pieza una milésima de milímetro.")
    libres, no_manifold = _aristas_defectuosas(mejor)
    (la, _), (lb, _) = _aristas_defectuosas(objetivo), _aristas_defectuosas(herramienta)
    if libres > la + lb or "sólido inválido" in peor_problema[1]:
        # No estanco o inválido: nunca sale en silencio (B-39). Solo-no-manifold SÍ se devuelve: el cuerpo sigue
        # estanco y puede ser la geometría real (un agujero tangente a una pared pellizca el material, B-126).
        raise ErrorGeometria(f"La operación '{operacion}' quedó sin un resultado estanco o válido ({peor_problema[1]}) "
                             "y el kernel no logró corregirlo: probá mover la pieza una milésima de milímetro.")
    if avisos is not None:
        avisos.append(f"quedaron {no_manifold} aristas compartidas por más de dos caras (posible contacto tangente "
                      "o en cuña); revisalo con check_geometry.")
    return mejor


def unificar_caras(forma):
    """Fusiona las caras coplanares (o sobre la misma superficie) que deja una booleana, como el resultado limpio
    de Fusion. Sin esto, unir dos prismas en L deja la cara de atrás partida en dos y un empalme más grande que
    el tramo partido falla. Si no se puede simplificar, devuelve la forma tal cual."""
    return _unificar_caras(forma)[0]


def _unificar_caras(forma, entradas=()):
    """Forma unificada y copias de caras de las entradas que el historial conserva intactas."""
    try:
        # Aislar la topología protege las entradas; conservar su malla evita volver a teselar todo el cuerpo.
        copia = BRepBuilderAPI_Copy(forma, copyGeom=False, copyMesh=True)
        u = ShapeUpgrade_UnifySameDomain(copia.Shape(), True, True, False)
        u.Build()
        resultado = u.Shape()
        if resultado.IsNull():
            return forma, ()
        if not entradas or len(caras(resultado)) <= _MAX_CARAS_REVISADAS:
            return resultado, ()  # los sólidos chicos se revisan enteros, sin el filtro por caras conocidas
        historial = u.History()
        hay_cambios = historial.HasModified() or historial.HasRemoved()
        conocidas = IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
        for entrada in entradas:
            for cara in caras(entrada):
                conocidas.Add(cara)
        intactas = []
        for cara in caras(forma):
            if not conocidas.Contains(cara):
                continue
            duplicada = copia.ModifiedShape(cara)
            subformas = (s for tipo in (TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX) for s in _explorar(duplicada, tipo))
            if not hay_cambios or not any(historial.IsRemoved(s) or historial.Modified(s).Size() for s in subformas):
                intactas.append(duplicada)
        return resultado, intactas
    except Exception:  # noqa: BLE001
        return forma, ()


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
    kernel perdía material sin avisar) o le falta una pieza entera (B-125); entonces `unir_todos` une de a pares, que sí
    reintenta. Solo entre sólidos.
    shortcut: con más de _MAX_PIEZAS_REVISADAS piezas que se solapan no se buscan piezas perdidas (retícula: miles de
    barras), subir si aparece un caso."""
    try:
        if esta_vacia(unida):
            return False
        if any(es_forma_libre(f) or not solidos(f) for f in (*formas, unida)):
            return True
        vols = [abs(_integral(f, BRepGProp.VolumeProperties_s)) for f in formas]
        tol = 1e-6 * sum(vols) + _TOPE_VOLUMEN_BOOLEANA * min(vols)
        v = abs(_integral(unida, BRepGProp.VolumeProperties_s))
        if not max(vols) - tol <= v <= sum(vols) + tol:
            return False
        return (v >= sum(vols) - tol or len(formas) > _MAX_PIEZAS_REVISADAS
                or not any((_parte_afuera(f, unida) or 0.0) >= 0.25 for f in formas))
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
            op.SetRunParallel(PARALELO)
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
_EPS_VOLUMEN = 1e-8               # error relativo de la integración adaptativa del volumen de una forma libre (B-129)
_CARAS_FINAS = 300                # caras de la forma hasta las que se integra fino (cada una cuesta de 0,4 a unos 10 ms)
# Polos de una cara B-spline hasta los que la integración adaptativa es rápida y confiable. Medido en las piezas de
# EXTRUSOR XOX.f3z: con ≤ 170 polos coincide con Eps 1e-12; con 244 o más tarda de 0,2 a 2 s y puede errar 1 % a 10 %
# (más que la de siempre), y el cuerpo de la cartera del .f3d subió 0,4 % y tardó 3 veces más.
_POLOS_FINOS = 170


def es_forma_libre(forma):
    """True si alguna cara es B-spline, Bézier, desfasada u otra superficie libre."""
    return any(BRepAdaptor_Surface(c).GetType() not in _ANALITICAS for c in caras(forma))


def _apta_para_integral_fina(forma):
    """True si la forma tiene hasta `_CARAS_FINAS` caras y sus caras libres son todas B-spline de hasta `_POLOS_FINOS`
    polos (B-129: lentes de esferas, agujeros roscados chicos). Las libres grandes siguen con la integración de siempre."""
    from OCP.GeomAbs import GeomAbs_BSplineSurface
    lista = caras(forma)
    if len(lista) > _CARAS_FINAS:
        return False
    for c in lista:
        sup = BRepAdaptor_Surface(c)
        if sup.GetType() in _ANALITICAS:
            continue
        if sup.GetType() != GeomAbs_BSplineSurface:
            return False
        bs = sup.BSpline()
        if bs.NbUPoles() * bs.NbVPoles() > _POLOS_FINOS:
            return False
    return True


def _por_malla(forma, funcion, deflexion, relativa):
    """Volumen o área sobre la malla de una COPIA (la malla de la vista no se toca). None si una cara no se malló."""
    copia = BRepBuilderAPI_Copy(forma).Shape()
    BRepMesh_IncrementalMesh(copia, deflexion, relativa, 0.2, True)
    if any(BRep_Tool.Triangulation_s(c, TopLoc_Location()) is None for c in caras(copia)):
        return None
    p = GProp_GProps()
    funcion(copia, p, False, False, True) if funcion is BRepGProp.VolumeProperties_s else funcion(copia, p, False, True)
    return p.Mass()


def _integral(forma, funcion, eps=None):
    """Volumen o área por la integración exacta de OpenCascade, sin el control por malla de `_propiedades`. Con `eps`
    (solo volumen) la integración es adaptativa hasta ese error relativo estimado; si el kernel falla en una forma
    rota, vale la integración por defecto (sin esa precisión, pero con un número)."""
    if eps is not None:
        try:
            p = GProp_GProps()
            funcion(forma, p, eps)
            return p.Mass()
        except Exception:  # noqa: BLE001 — Standard_Failure de OCP en formas degeneradas
            pass
    p = GProp_GProps()
    funcion(forma, p)
    return p.Mass()


def _propiedades(forma, funcion):
    """Volumen o área. La integración de OpenCascade es exacta y rápida con caras analíticas y con la mayoría de las
    libres (barridos, recubrimientos, bobinas), pero en superficies libres muy recortadas puede errar mucho: el fuelle
    de un .f3d de Fusion daba 180 791 mm³ contra 124 672 de Fusion (con tolerancia, 125 050 en 27 s). Con caras libres
    se controla contra una malla rápida; si difieren más de 5 % (un error grosero: la malla se equivoca menos de 1,5 %
    incluso en un alambre de 1 mm), vale una malla fina: 124 718 mm³ en ~1 s."""
    if not es_forma_libre(forma):
        return _integral(forma, funcion)
    if funcion is BRepGProp.VolumeProperties_s and _apta_para_integral_fina(forma):
        # B-129: la lente de dos esferas erraba hasta 0,5 mm³. Sin malla de control: los errores groseros que ella
        # atrapa son de caras libres grandes, y acá no hay ninguna.
        return _integral(forma, funcion, _EPS_VOLUMEN)
    exacto = _integral(forma, funcion)
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


def _dentro_de_cara(cara, punto, tolerancia=1e-7):
    """Pertenencia en UV de una cara plana: evita la costosa proyección general del clasificador 3D."""
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.ElSLib import ElSLib
    superficie = BRepAdaptor_Surface(cara)
    if superficie.GetType() != GeomAbs_Plane:
        return False
    uv = ElSLib.Parameters_s(superficie.Plane(), gp_Pnt(*map(float, punto)))
    return BRepClass_FaceClassifier(cara, gp_Pnt2d(*uv), tolerancia).State() == TopAbs_IN


def punto_dentro(cara):
    """Punto interior de una cara plana, para clasificar perfiles de boceto como `Sketch.profiles` de Fusion.

    Verifica el centro del mayor triángulo útil. Sin malla o si el redondeo desplaza ese punto fuera de la cara,
    busca sobre el B-rep exacto. No modifica los contornos ni rellena los agujeros.
    """
    from OCP.BRepClass3d import BRepClass3d_SolidExplorer
    if cara is None or cara.IsNull() or cara.ShapeType() != TopAbs_FACE:
        raise ErrorGeometria("El perfil no tiene una cara válida para calcular su punto interior.")
    try:
        tris = np.asarray(teselar(cara)[0], float).reshape(-1, 3, 3)
        if len(tris):
            areas = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
            utiles = np.isfinite(areas) & (areas > 0)
            if utiles.any():
                punto = tris[int(np.argmax(np.where(utiles, areas, -1)))].mean(axis=0)
                if _dentro_de_cara(cara, punto):
                    return punto
    except Exception:  # noqa: BLE001 — OCC puede fallar al mallar una cara válida; se consulta su B-rep
        pass
    try:
        if not es_valida(cara) or _integral(cara, BRepGProp.SurfaceProperties_s) <= 0:
            raise ErrorGeometria("El perfil tiene una cara inválida o sin área interior. Revisá sus contornos.")
        if BRepAdaptor_Surface(cara).GetType() != GeomAbs_Plane:
            raise ErrorGeometria("El punto interior del perfil necesita una cara plana.")
        caja = caja_envolvente(cara)
        escala = math.dist(*caja)
        trabajo, cambio = cara, None
        if 0 < escala < 1e-3:
            # El clasificador falla por debajo de su precisión absoluta; una copia a escala evita esa ambigüedad.
            cambio = gp_Trsf()
            cambio.SetScale(gp_Pnt(*caja[0]), 1 / escala)
            trabajo = TopoDS.Face(BRepBuilderAPI_Transform(cara, cambio, True).Shape())
        punto = gp_Pnt()
        if BRepClass3d_SolidExplorer.FindAPointInTheFace_s(trabajo, punto) and _dentro_de_cara(
                trabajo, (punto.X(), punto.Y(), punto.Z())):
            if cambio is not None:
                punto.Transform(cambio.Inverted())
            return np.array([punto.X(), punto.Y(), punto.Z()])
    except ErrorGeometria:
        raise
    except Exception as e:  # noqa: BLE001 — las excepciones nativas de OCC no comparten una clase base
        raise ErrorGeometria("No se pudo clasificar el interior del perfil con OpenCascade.") from e
    raise ErrorGeometria("La cara es válida, pero no se pudo localizar un punto interior sin triangulación. "
                         "Revisá las tolerancias de sus contornos.")


def _brepcheck_estable(forma):
    """Confirma en serie los fallos del análisis paralelo, sin desactivar los controles geométricos."""
    if BRepCheck_Analyzer(forma, GeomControls=True, theIsParallel=PARALELO).IsValid():
        return True
    return BRepCheck_Analyzer(forma, GeomControls=True, theIsParallel=False).IsValid()


def es_valida(forma):
    return _brepcheck_estable(forma)


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


def cajas_solapan(a, b):
    """¿Dos cajas envolventes (mínimo, máximo) comparten volumen? Apoyarse en una cara no cuenta."""
    return all(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) > 1e-6 for i in range(3))


def solapan(a, b):
    """¿Dos sólidos comparten volumen? Apoyarse en una cara no cuenta. La caja envolvente descarta casi todo sin booleana."""
    if not cajas_solapan(caja_envolvente(a), caja_envolvente(b)):
        return False
    comun = booleano(a, b, "intersecar")
    return not esta_vacia(comun) and abs(volumen_exacto(comun)) > 1e-6


def se_tocan(a, b, tolerancia=1e-6):
    """True si las formas se tocan o se superponen, también cuando una queda entera dentro de un sólido de la otra.
    BRepExtrema_DistShapeShape solo mira «adentro» cuando la forma es un SOLID: con un COMPOUND (lo que devuelve toda
    booleana) mide entre los bordes, y una cavidad interna daba «no se tocan» (el corte automático la salteaba).
    La distancia exacta entre formas enteras cuesta 2–7 s por par en piezas de 20–230 caras, así que se mide cara con
    cara, solo entre las que se solapan por caja envolvente, y se corta al primer contacto."""
    caras_a, caras_b = caras(a), caras(b)
    if len(caras_a) < len(caras_b):
        a, b, caras_a, caras_b = b, a, caras_b, caras_a      # `b` es la de menos caras: su caja exacta cuesta poco
    ba, bb = _caja_occ(a, tolerancia, holgada=bool(caras_a)), _caja_occ(b, tolerancia)
    if ba is not None and bb is not None and ba.IsOut(bb):
        return False
    if _adentro(a, b, tolerancia) or _adentro(b, a, tolerancia):     # ~4 ms; resuelve superposición y contención
        return True
    if ba is None or bb is None or not caras_a or not caras_b:       # un vértice o aristas sueltas: forma entera
        d = BRepExtrema_DistShapeShape(a, b)
        return d.IsDone() and d.Value() <= tolerancia
    cercanas_b = [(f, x) for f in caras_b
                  if (g := _caja_occ(f, tolerancia, holgada=True)) is not None and not g.IsOut(ba)
                  and (x := _caja_occ(f, tolerancia)) is not None and not x.IsOut(ba)]
    for fa in caras_a:
        grosera = _caja_occ(fa, tolerancia, holgada=True)
        if grosera is None or grosera.IsOut(bb):
            continue
        xa = _caja_occ(fa, tolerancia)
        if xa is None or xa.IsOut(bb):
            continue
        for fb, xb in cercanas_b:
            if not xa.IsOut(xb):
                d = BRepExtrema_DistShapeShape(fa, fb)
                if d.IsDone() and d.Value() <= tolerancia:
                    return True
    return False


def _caja_occ(forma, holgura, holgada=False):
    """Bnd_Box de OCC de `forma` agrandada en `holgura` (con la tolerancia de la forma), o None si no tiene geometría.
    `holgada`: la caja barata (Add_s, 0,006 ms por cara en vez de 4 ms) es más grande que la exacta: sirve para descartar
    caras, no para decidir que dos formas están lejos (una pieza B-spline a 60 mm no se descartaba)."""
    b = Bnd_Box()
    if holgada:
        BRepBndLib.Add_s(forma, b, False)
    else:
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
    return [(cara, _triangulos_cara(cara, tri, loc))
            for cara, tri, loc in _triangulaciones(forma, deflexion, angular, rehacer)]


def _triangulaciones(forma, deflexion, angular, rehacer=False):
    """Caras y triangulaciones OCC antes de convertirlas: permite reusar los arrays de las caras intactas.
    B-153: las caras que OCC abandonó a medio mallar se reparan acá, así ningún consumidor (`teselar`, el visor, el
    análisis) recibe una malla con agujeros."""
    if rehacer:
        BRepTools.Clean_s(forma)
    BRepMesh_IncrementalMesh(forma, deflexion, False, angular, True)
    for cara in caras(forma):
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(cara, loc)
        if tri is None:
            continue
        if _cara_incompleta(tri):
            tri, loc = _reparar_cara(cara, tri, loc, deflexion, angular)
        yield cara, tri, loc


def _cara_incompleta(tri):
    """B-153: True si OCC abandonó la cara a medio mallar. Una triangulación sana de un contorno con V nodos tiene al
    menos V − 2 triángulos (Euler: T = 2·V − 2 − B con nodos interiores, o T = V − 2 sin ellos); menos, es que faltan
    (Rugged Box `obj_3`: 67 nodos y 2 triángulos)."""
    return tri.NbTriangles() < tri.NbNodes() - 2


def _reparar_cara(cara, tri, loc, deflexion, angular):
    """(a) Reintenta mallar SOLO la cara, a un solo hilo (el abandono suele venir del mallado en paralelo del cuerpo
    entero) y con la triangulación parcial borrada, que si no OCC la cree buena y no la toque. Si la cara sigue
    incompleta, (b) la rellena con su contorno (`_rellenar_cara`). Si nada alcanza, se restaura la parcial de antes
    (B-151 ya aparta sus nodos sin llenar): la cara no puede quedarse sin triangulación."""
    BRep_Builder().UpdateFace(cara, None)      # borra solo la triangulación de esta cara, sin tocar las aristas
    BRepMesh_IncrementalMesh(cara, deflexion, False, angular, False)
    nuevo = BRep_Tool.Triangulation_s(cara, loc)
    if nuevo is not None and not _cara_incompleta(nuevo):
        return nuevo, loc
    rellena = _rellenar_cara(cara, tri, loc)
    if rellena is not None:
        BRep_Builder().UpdateFace(cara, rellena)
        return rellena, loc
    BRep_Builder().UpdateFace(cara, tri)
    return tri, loc


def _cruz2(a, b):
    """Producto cruz de vectores 2D (los de numpy 2 ya no aceptan pares 2D en `np.cross`)."""
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _rellenar_cara(cara, tri, loc):
    """B-153 (camino b): rellena una cara abandonada triangulando su contorno (los nodos de los polígonos de sus
    aristas sobre la triangulación parcial, que son los mismos puntos que usan las caras vecinas: la malla queda
    cerrada). Devuelve la `Poly_Triangulation` nueva, o None si no puede: contorno abierto o con nodos repetidos
    (costura de un cilindro), más de un contorno (cara con agujeros) o UV no calculable."""
    contornos = []
    for alambre in _explorar(cara, TopAbs_WIRE):
        contorno = []
        ex = BRepTools_WireExplorer(TopoDS.Wire(alambre), cara)
        while ex.More():
            arista = ex.Current()
            pol = BRep_Tool.PolygonOnTriangulation_s(arista, tri, loc)
            if pol is None:
                return None
            ns = [pol.Nodes().Value(i) for i in range(pol.Nodes().Lower(), pol.Nodes().Upper() + 1)]
            if arista.Orientation() == TopAbs_REVERSED:
                ns.reverse()
            if contorno and ns and ns[0] == contorno[-1]:
                ns = ns[1:]
            contorno.extend(ns)
            ex.Next()
        if len(contorno) > 2 and contorno[0] == contorno[-1]:
            contorno.pop()
        if len(contorno) < 3 or len(set(contorno)) != len(contorno):
            return None
        contornos.append(contorno)
    if len(contornos) != 1:
        return None
    contorno = contornos[0]
    if tri.HasUVNodes():
        pts = np.array([[tri.UVNode(i).X(), tri.UVNode(i).Y()] for i in contorno], float)
    else:
        try:
            proyecta = ShapeAnalysis_Surface(BRep_Tool.Surface_s(cara))
            trsf = loc.Transformation()
            pts = []
            for i in contorno:
                uv = proyecta.ValueOfUV(tri.Node(i).Transformed(trsf), 1e-6)
                pts.append([uv.X(), uv.Y()])
            pts = np.array(pts, float)
        except Exception:  # noqa: BLE001 — superficie sin proyección: mejor rendirse que inventar una malla mala
            return None
    vueltas = _cruz2(pts, np.roll(pts, -1, axis=0)).sum()
    if abs(float(vueltas)) == 0.0:
        return None
    if float(vueltas) < 0:    # antihorario en UV, como mallan las sanas
        contorno.reverse()
        pts = pts[::-1]
    tris = _triangular_poligono(pts)
    if not tris:
        return None
    nueva = Poly_Triangulation(len(contorno), len(tris), True)
    uv = {nodo: gp_Pnt2d(float(p[0]), float(p[1])) for nodo, p in zip(contorno, pts, strict=True)}
    for k, nodo in enumerate(contorno):
        nueva.SetNode(k + 1, tri.Node(nodo))
        nueva.SetUVNode(k + 1, uv[nodo])
    for k, (a, b, c) in enumerate(tris):
        nueva.SetTriangle(k + 1, Poly_Triangle(contorno[a], contorno[b], contorno[c]))
    return nueva


def _triangular_poligono(pts):
    """Triangulación por orejas de un polígono simple (pts Nx2 en sentido antihorario): tríos de índices. Contornos
    de caras abandonadas: decenas o cientos de nodos, un caso raro, así que el O(n²) no molesta."""
    resto = list(range(len(pts)))
    tris = []
    while len(resto) > 3:
        elegida = None
        for k in range(len(resto)):
            a, b, c = resto[k - 1], resto[k], resto[(k + 1) % len(resto)]
            if float(_cruz2(pts[c] - pts[b], pts[a] - pts[b])) <= 0.0:
                continue                       # no es un oído convexo
            otros = np.array([pts[i] for i in resto if i not in (a, b, c)], float)
            if len(otros) and bool(((_cruz2(pts[b] - pts[a], otros - pts[a]) > 0) &
                                    (_cruz2(pts[c] - pts[b], otros - pts[b]) > 0) &
                                    (_cruz2(pts[a] - pts[c], otros - pts[c]) > 0)).any()):
                continue                       # un punto dentro del oído
            elegida = k
            break
        if elegida is None:
            # solo quedan vértices colineales o enredados: soltar el más parecido a colineal (sin triángulo) o rendirse
            cruces = [abs(float(_cruz2(pts[resto[(k + 1) % len(resto)]] - pts[resto[k]],
                                       pts[resto[k - 1]] - pts[resto[k]]))) for k in range(len(resto))]
            escala = max(float(np.abs(pts - pts.mean(axis=0)).max()), 1e-9)
            if min(cruces) > 1e-9 * escala * escala:
                return []
            resto.pop(int(np.argmin(cruces)))
            continue
        a, b, c = resto[elegida - 1], resto[elegida], resto[(elegida + 1) % len(resto)]
        tris.append((a, b, c))
        resto.pop(elegida)
    tris.append((resto[0], resto[1], resto[2]))
    return tris


def _nodos_mundo(tri, loc):
    trsf = loc.Transformation()
    return np.array([[p.X(), p.Y(), p.Z()] for p in
                     (tri.Node(i).Transformed(trsf) for i in range(1, tri.NbNodes() + 1))], float)


def _indices_cara(cara, tri, loc):
    """Índices Kx3 de los triángulos de la cara con su orientación, sin los que apuntan a un nodo sin llenar."""
    idx = np.array([tri.Triangle(i).Get() for i in range(1, tri.NbTriangles() + 1)], int).reshape(-1, 3) - 1
    if len(np.unique(idx)) < tri.NbNodes():
        idx = idx[_nodos_de_la_cara(cara, _nodos_mundo(tri, loc))[idx].all(axis=1)]
    if cara.Orientation() == TopAbs_REVERSED:
        idx = idx[:, [0, 2, 1]]
    return idx


def _triangulos_cara(cara, tri, loc):
    """Triángulos Kx3x3 en coordenadas del mundo, con el mismo orden y precisión de OCC."""
    return _nodos_mundo(tri, loc)[_indices_cara(cara, tri, loc)]


def _nodos_de_la_cara(cara, nodos):
    """B-151: en una cara muy fina el mallador de OCC abandona la cara a medias (por eso sobran nodos) y un triángulo
    puede apuntar a un nodo que nunca llenó: memoria basura que cae en cualquier lado. Máscara de los nodos que están
    en la caja de la cara."""
    caja = _caja_occ(cara, 1e-3, holgada=True)
    p0, p1 = caja.CornerMin(), caja.CornerMax()
    return ((nodos >= (p0.X(), p0.Y(), p0.Z())) & (nodos <= (p1.X(), p1.Y(), p1.Z()))).all(axis=1)


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
