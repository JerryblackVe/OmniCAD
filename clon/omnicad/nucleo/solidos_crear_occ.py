"""Registro de los temas bajo el nombre histórico y carga diferida de sus símbolos OCC."""
from . import motor as _motor


_espacios = []
_simbolos = {}


def _vincular(espacio):
    _espacios.append(espacio)
    espacio.update(_simbolos)


def _publicar_occ():
    _simbolos.update((k, v) for k, v in globals().items() if not k.startswith("_") or k.isupper())
    for espacio in _espacios:
        espacio.update(_simbolos)


def _iniciar_opencascade():
    if _simbolos:
        return
    global Array1_gp_Pnt2d, BOPAlgo_MakerVolume, BRepAdaptor_CompCurve, BRepAdaptor_Curve
    global BRepAdaptor_Surface, BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepAlgoAPI_Splitter
    global BRepBuilderAPI_Copy, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
    global BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire, BRepBuilderAPI_RightCorner
    global BRepBuilderAPI_Sewing, BRepBuilderAPI_Transform, BRepClass3d_SolidClassifier
    global BRepClass_FaceClassifier, BRepExtrema_DistShapeShape, BRepFill_NoContact
    global BRepGProp, BRepLib, BRepOffsetAPI_DraftAngle, BRepOffsetAPI_MakeOffset
    global BRepOffsetAPI_MakeOffsetShape, BRepOffsetAPI_MakePipeShell, BRepOffsetAPI_ThruSections
    global BRepOffset_MakeOffset, BRepOffset_Skin, BRepPrimAPI_MakeHalfSpace, BRepPrimAPI_MakePrism
    global BRepPrimAPI_MakeRevol, BRepTools, BRepTools_WireExplorer, BRep_Builder, BRep_Tool, ElCLib
    global GCPnts_AbscissaPoint, GProp_GProps, Geom2dAPI_Interpolate, Geom2d_Line, Geom2d_TrimmedCurve
    global GeomAPI_Interpolate, GeomAbs_BSplineCurve, GeomAbs_BSplineSurface, GeomAbs_BezierCurve
    global GeomAbs_Arc, GeomAbs_BezierSurface, GeomAbs_Cylinder, GeomAbs_Intersection, GeomAbs_Line, GeomAbs_Plane
    global GeomLib_IsPlanarSurface, Geom_Circle, Geom_ConicalSurface, Geom_CylindricalSurface, Geom_Line
    global Geom_Plane, HArray1_gp_Pnt, HArray1_gp_Pnt2d, IntCurvesFace_ShapeIntersector, Law_Interpol
    global Law_Linear, List_TopoDS_Shape, ShapeAnalysis_CanonicalRecognition, ShapeAnalysis_Edge, ShapeFix_Face
    global ShapeUpgrade_UnifySameDomain, TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_ON, TopAbs_REVERSED
    global TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX, TopAbs_WIRE, TopExp, TopExp_Explorer, TopLoc_Location
    global TopoDS, TopoDS_Face, TopoDS_Iterator, TopoDS_Shell, TopoDS_Solid
    global _CONVERTIR, _CURVAS_LIBRES, _SUPERFICIES_LIBRES, gp_Ax1, gp_Ax2, gp_Ax3, gp_Circ, gp_Dir
    global gp_Dir2d, gp_Lin, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Trsf, gp_Vec
    from OCP.BOPAlgo import BOPAlgo_MakerVolume
    from OCP.BRep import BRep_Builder, BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_CompCurve, BRepAdaptor_Curve, BRepAdaptor_Surface
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepAlgoAPI_Splitter
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_Copy, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace,
                                    BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire,
                                    BRepBuilderAPI_RightCorner, BRepBuilderAPI_Sewing, BRepBuilderAPI_Transform)
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepFill import BRepFill_NoContact
    from OCP.BRepGProp import BRepGProp
    from OCP.BRepLib import BRepLib
    from OCP.BRepOffset import BRepOffset_MakeOffset, BRepOffset_Skin
    from OCP.BRepOffsetAPI import (BRepOffsetAPI_DraftAngle, BRepOffsetAPI_MakeOffset, BRepOffsetAPI_MakeOffsetShape,
                                   BRepOffsetAPI_MakePipeShell, BRepOffsetAPI_ThruSections)
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace, BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
    from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
    from OCP.ElCLib import ElCLib
    from OCP.GCPnts import GCPnts_AbscissaPoint
    from OCP.Geom import Geom_Circle, Geom_ConicalSurface, Geom_CylindricalSurface, Geom_Line, Geom_Plane
    from OCP.Geom2d import Geom2d_Line, Geom2d_TrimmedCurve
    from OCP.Geom2dAPI import Geom2dAPI_Interpolate
    from OCP.GeomAbs import (GeomAbs_Arc, GeomAbs_BezierCurve, GeomAbs_BezierSurface, GeomAbs_BSplineCurve, GeomAbs_BSplineSurface,
                             GeomAbs_Cylinder, GeomAbs_Intersection, GeomAbs_Line, GeomAbs_Plane)
    from OCP.GeomAPI import GeomAPI_Interpolate
    from OCP.GeomLib import GeomLib_IsPlanarSurface
    from OCP.GProp import GProp_GProps
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    from OCP.Law import Law_Interpol, Law_Linear
    from OCP.OCP.collections import Array1_gp_Pnt2d, HArray1_gp_Pnt, HArray1_gp_Pnt2d, List_TopoDS_Shape
    from OCP.ShapeAnalysis import ShapeAnalysis_CanonicalRecognition, ShapeAnalysis_Edge
    from OCP.ShapeFix import ShapeFix_Face
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.TopAbs import (TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_ON, TopAbs_REVERSED, TopAbs_SHELL,
                            TopAbs_SOLID, TopAbs_VERTEX, TopAbs_WIRE)
    from OCP.TopExp import TopExp, TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS, TopoDS_Face, TopoDS_Iterator, TopoDS_Shell, TopoDS_Solid
    from OCP.gp import gp_Ax1, gp_Ax2, gp_Ax3, gp_Circ, gp_Dir, gp_Dir2d, gp_Lin, gp_Pln, gp_Pnt, gp_Pnt2d, gp_Trsf, gp_Vec
    _CONVERTIR = {TopAbs_FACE: TopoDS.Face, TopAbs_WIRE: TopoDS.Wire, TopAbs_EDGE: TopoDS.Edge,
                  TopAbs_SOLID: TopoDS.Solid, TopAbs_SHELL: TopoDS.Shell, TopAbs_VERTEX: TopoDS.Vertex}
    _SUPERFICIES_LIBRES = (GeomAbs_BSplineSurface, GeomAbs_BezierSurface)
    _CURVAS_LIBRES = (GeomAbs_BSplineCurve, GeomAbs_BezierCurve)
    _publicar_occ()


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()


def _registrar_tema(espacio):
    """Todos los temas despachan por omnikernel.solidos_crear y conservan el nombre público original."""
    nombre = __package__ + ".solidos_crear"
    propias = {k: f for k, f in espacio.items() if getattr(f, "__module__", None) == espacio["__name__"]}
    for funcion in propias.values():
        funcion.__module__ = nombre
    registro = dict(propias, __name__=nombre)
    _motor.registrar(registro, _iniciar_opencascade)
    espacio.update((k, registro[k]) for k in propias)
    _vincular(espacio)
