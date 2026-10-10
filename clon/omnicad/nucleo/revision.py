# -*- coding: utf-8 -*-
"""
Revisar geometría e impresión 3D (INSPECCIONAR › Revisar geometría) y Reparar.

Replica las FUNCIONES de (escritas desde cero sobre OpenCascade y numpy, sin copiar código):
  - FreeCAD Part › Check Geometry, Set Tolerance y Refine Shape (F2 de `docs/brechas_freecad.md`);
  - la caja de herramientas de impresión 3D de Blender (3D Print Toolbox: sólido cerrado, intersecciones,
    espesor, voladizos, aristas filosas y «Hacer manifold»; B2 de `docs/brechas_blender.md`);
  - ShowEdges y ThicknessAnalysis de Rhino (aristas abiertas y no manifold, espesor; RH13 de `docs/brechas_rhino.md`).
Fusion 360 no tiene un comando equivalente para sólidos (lo más cercano es MALLA › Reparar, que acá se reusa).

Funciones puras, sin Qt ni timeline. Reciben una forma OCC o una `nucleo.malla.Malla`:
  - `revisar(forma)` → validez del kernel (con el detalle de qué falla), estanqueidad, aristas libres y no
    manifold, autointersecciones, tolerancias, caras degeneradas, cáscaras y sólidos;
  - `revisar_impresion(forma, espesor_minimo, angulo_voladizo, angulo_filoso)` → espesor mínimo (rayos hacia
    adentro desde la malla), zonas en voladizo, aristas filosas, volumen, área y caja;
  - `reparar(forma, tolerancia=…)` → forma arreglada (coser, tolerancias, ShapeFix y refinar);
  - `resumen(informe)` → líneas de texto para mostrar el informe.
Cada problema es {"tipo", "gravedad" ("error" | "aviso"), "mensaje", "punto" (x, y, z) o None} y, si es una
arista o un borde, "segmentos" (pares de puntos 2Kx3, como GL_LINES) para resaltarlo en la vista; los que miden
algo traen "valor" (mm o mm²).
"""
import math

import numpy as np
from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer, BOPAlgo_CheckStatus
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_MakeVertex
from OCP.BRepCheck import BRepCheck_Analyzer, BRepCheck_Face, BRepCheck_Shell, BRepCheck_Status, BRepCheck_Wire
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.OCP.collections import (IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher,
                                 IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher)
from OCP.ShapeFix import ShapeFix_Shape, ShapeFix_ShapeTolerance
from OCP.TopAbs import (TopAbs_COMPOUND, TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX,
                        TopAbs_WIRE)
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Shape
from OCP.gp import gp_Pnt

from . import analisis as an
from . import geometria as geo
from . import malla as ml

TOLERANCIA_ALTA = 0.01        # mm: una tolerancia de vértice, arista o cara mayor que esto se avisa
LARGO_DIMINUTO = 1e-4         # mm: aristas más cortas (restos de booleanas o de un STEP mal exportado)
_AREA_DEGENERADA = 1e-12      # fracción de diagonal² por debajo de la cual una cara es degenerada (área ~0)
MAX_PROBLEMAS = 200           # problemas que se devuelven con su ubicación (los conteos son siempre completos)
MUESTRAS_ESPESOR = 2000       # rayos para medir el espesor (triángulos elegidos al azar, pesados por área)
_PARES_POR_TANDA = 1_000_000  # rayos × triángulos por tanda en el cálculo del espesor (8 MB por arreglo)
_PARES_TOTALES = 400_000_000  # tope de rayos × triángulos: con mallas enormes se usan menos rayos
_RAYOS_POR_TANDA = 16         # rayos vecinos (orden de Morton) que comparten la caja de búsqueda

_NOMBRE_TIPO = {TopAbs_VERTEX: "vértice", TopAbs_EDGE: "arista", TopAbs_WIRE: "contorno", TopAbs_FACE: "cara",
                TopAbs_SHELL: "cáscara", TopAbs_SOLID: "sólido", TopAbs_COMPOUND: "compuesto"}
# Qué quiere decir cada estado de BRepCheck (los que usa el detalle de una cara o una cáscara inválida).
_ESTADOS = {
    "BRepCheck_SelfIntersectingWire": "el contorno se cruza a sí mismo",
    "BRepCheck_IntersectingWires": "dos contornos de la cara se cruzan",
    "BRepCheck_InvalidImbricationOfWires": "un agujero queda fuera del contorno exterior",
    "BRepCheck_BadOrientationOfSubshape": "hay partes con la orientación invertida",
    "BRepCheck_BadOrientation": "orientación inválida",
    "BRepCheck_NotClosed": "el contorno no está cerrado",
    "BRepCheck_NotConnected": "partes desconectadas",
    "BRepCheck_EmptyWire": "contorno vacío",
    "BRepCheck_EmptyShell": "cáscara vacía",
    "BRepCheck_RedundantEdge": "arista repetida",
    "BRepCheck_RedundantWire": "contorno repetido",
    "BRepCheck_RedundantFace": "cara repetida",
    "BRepCheck_InvalidMultiConnexity": "una arista une más de dos caras",
    "BRepCheck_UnorientableShape": "no se puede orientar",
    "BRepCheck_InvalidWire": "contorno inválido",
    "BRepCheck_InvalidImbricationOfShells": "cáscaras mal anidadas",
    "BRepCheck_EnclosedRegion": "región encerrada inválida",
}


# ---------------------------------------------------------------- utilidades
def _np(p):
    return np.array([p.X(), p.Y(), p.Z()], float)


def _tupla(v):
    return tuple(float(c) for c in v)


def _n(x):
    """Número corto con coma decimal (para los mensajes)."""
    return f"{float(x):.4g}".replace(".", ",")


def _unicas(forma, tipo):
    mapa = IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapes_s(forma, tipo, mapa)
    return [mapa.FindKey(i) for i in range(1, mapa.Size() + 1)]


def _problema(tipo, gravedad, mensaje, punto=None, segmentos=None, valor=None):
    p = {"tipo": tipo, "gravedad": gravedad, "mensaje": mensaje, "punto": None if punto is None else _tupla(punto)}
    if segmentos is not None:
        p["segmentos"] = np.asarray(segmentos, float).reshape(-1, 3)
    if valor is not None:
        p["valor"] = float(valor)
    return p


def _exigir_forma(forma):
    if not isinstance(forma, TopoDS_Shape) or forma.IsNull():
        raise geo.ErrorGeometria("No hay forma para revisar: el cuerpo está vacío.")
    if geo.caja_envolvente(forma) is None:
        raise geo.ErrorGeometria("La forma está vacía: no tiene geometría para revisar.")


def _diagonal_caja(caja):
    return float(np.linalg.norm(np.subtract(caja[1], caja[0]))) if caja else 0.0


def _medio_arista(arista):
    try:
        c = BRepAdaptor_Curve(arista)
        return _np(c.Value(0.5 * (c.FirstParameter() + c.LastParameter())))
    except Exception:  # noqa: BLE001 — arista sin curva 3D: el promedio de sus vértices
        pts = [_np(BRep_Tool.Pnt_s(TopoDS.Vertex(v))) for v in _unicas(arista, TopAbs_VERTEX)]
        return np.mean(pts, axis=0) if pts else None


def _segmentos_arista(arista, deflexion):
    pol = geo.polilinea_arista(arista, deflexion)
    if len(pol) < 2:
        return None
    return np.repeat(np.asarray(pol, float), 2, axis=0)[1:-1]


def _punto_en(forma):
    """Punto SOBRE la forma cercano a su centro (el centro de masa de una cara curva cae fuera de ella)."""
    caja = geo.caja_envolvente(forma)
    if caja is None:
        return None
    p = (np.array(caja[0]) + np.array(caja[1])) / 2
    try:
        props = GProp_GProps()
        BRepGProp.SurfaceProperties_s(forma, props)
        if props.Mass() > 1e-15:
            p = _np(props.CentreOfMass())
        d = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, p))).Vertex(), forma)
        if d.IsDone() and d.NbSolution():
            return _np(d.PointOnShape2(1))
    except Exception:  # noqa: BLE001 — sin proyección vale el centro
        pass
    return p


def _area(forma):
    props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(forma, props)
    return abs(props.Mass())


# ---------------------------------------------------------------- topología B-rep
def _caras_de(vecinas, i):
    """Caras distintas que comparten la arista i del mapa arista → caras (una costura aparece dos veces)."""
    unicas = []
    for f in vecinas.FindFromIndex(i):
        if not any(f.IsSame(g) for g in unicas):
            unicas.append(f)
    return unicas


def _topologia(forma):
    """Aristas libres (de una sola cara, sin contar las costuras de caras periódicas), no manifold (más de dos
    caras), sueltas (sin cara), cáscaras abiertas y sólidos de una forma B-rep."""
    vecinas = IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapesAndAncestors_s(forma, TopAbs_EDGE, TopAbs_FACE, vecinas)
    libres, no_manifold, sueltas, dobles = [], [], 0, []
    for i in range(1, vecinas.Size() + 1):
        arista = TopoDS.Edge(vecinas.FindKey(i))
        if BRep_Tool.Degenerated_s(arista):
            continue
        caras = _caras_de(vecinas, i)
        if not caras:
            sueltas += 1
        elif len(caras) == 1:
            if not BRep_Tool.IsClosed_s(arista, TopoDS.Face(caras[0])):
                libres.append(arista)
        elif len(caras) > 2:
            no_manifold.append((arista, len(caras)))
        else:
            dobles.append((i, arista))
    cascaras = [TopoDS.Shell(s) for s in _unicas(forma, TopAbs_SHELL)]
    abiertas = [s for s in cascaras if BRepCheck_Shell(s).Closed(True) != BRepCheck_Status.BRepCheck_NoError]
    solidos = geo.solidos(forma)
    return {"vecinas": vecinas, "libres": libres, "no_manifold": no_manifold, "sueltas": sueltas, "dobles": dobles,
            "cascaras": cascaras, "abiertas": abiertas, "solidos": solidos,
            "cerrado": bool(solidos) and not libres and not abiertas}


def es_estanca(forma):
    """True si el cuerpo es estanco: B-rep con sólidos, sin aristas libres ni cáscaras abiertas; malla cerrada y
    orientada (cada arista entre dos triángulos que la recorren en sentidos opuestos)."""
    if isinstance(forma, ml.Malla):
        return forma.es_cerrada()
    _exigir_forma(forma)
    return _topologia(forma)["cerrado"]


# ---------------------------------------------------------------- validez (BRepCheck con detalle)
def _textos_estados(estados):
    textos = []
    for s in estados:
        if s == BRepCheck_Status.BRepCheck_NoError:
            continue
        t = _ESTADOS.get(s.name, s.name.replace("BRepCheck_", ""))
        if t not in textos:
            textos.append(t)
    return textos


def _estados_cara(cara):
    """Estados de BRepCheck propios de una cara y de sus contornos (los que OCP deja leer de a uno)."""
    estados = []
    try:
        bf = BRepCheck_Face(cara)
        estados += [bf.IntersectWires(True), bf.ClassifyWires(True), bf.OrientationOfWires(True)]
        for w in _unicas(cara, TopAbs_WIRE):
            bw = BRepCheck_Wire(TopoDS.Wire(w))
            estados += [bw.Closed(True), bw.Closed2d(cara, True), bw.Orientation(cara, True),
                        bw.SelfIntersect(cara, TopoDS_Edge(), TopoDS_Edge(), True)]
    except Exception:  # noqa: BLE001 — una cara muy rota puede hacer fallar el chequeo detallado
        pass
    return estados


def _detalle_validez(forma, caras, topo):
    """Problemas que explican por qué BRepCheck marca la forma como inválida: caras (contornos que se cruzan,
    agujeros afuera, aristas fuera de tolerancia), cáscaras mal orientadas y sólidos mal armados."""
    problemas = []
    for cara in caras:
        cara = TopoDS.Face(cara)
        if BRepCheck_Analyzer(cara).IsValid():
            continue
        textos = _textos_estados(_estados_cara(cara))
        detalle = ", ".join(textos) if textos else "aristas o vértices fuera de tolerancia (la curva no coincide " \
                                                     "con la superficie)"
        problemas.append(_problema("cara_invalida", "error", f"Cara inválida: {detalle}.", _punto_en(cara)))
    for cascara in topo["cascaras"]:
        try:
            orient = BRepCheck_Shell(cascara).Orientation(True)
        except Exception:  # noqa: BLE001
            continue
        textos = _textos_estados([orient])
        if textos:
            problemas.append(_problema("cascara_invalida", "error", f"Cáscara inválida: {', '.join(textos)}.",
                                       _punto_en(cascara)))
    if not problemas:
        for solido in topo["solidos"]:
            if not BRepCheck_Analyzer(solido).IsValid():
                problemas.append(_problema("solido_invalido", "error", "Sólido inválido: las cáscaras están mal "
                                           "armadas o anidadas.", _punto_en(solido)))
    if not problemas:
        problemas.append(_problema("invalido", "error", "El kernel marca la forma como inválida (sin más detalle).",
                                   _punto_en(forma)))
    return problemas


# ---------------------------------------------------------------- autointersecciones
def _punto_comun(formas):
    if len(formas) >= 2:
        try:
            d = BRepExtrema_DistShapeShape(formas[0], formas[1])
            if d.IsDone() and d.NbSolution():
                return (_np(d.PointOnShape1(1)) + _np(d.PointOnShape2(1))) / 2
        except Exception:  # noqa: BLE001
            pass
    return _punto_en(formas[0]) if formas else None


def _autointersecciones(forma, limite):
    """(cantidad, problemas, completo) del análisis de autointersección de BOPAlgo_ArgumentAnalyzer (el que usa
    FreeCAD en Check Geometry › «Run BOP check»)."""
    analizador = BOPAlgo_ArgumentAnalyzer()
    analizador.SetShape1(forma)
    analizador.SelfInterMode = True
    analizador.Perform()
    if not analizador.HasFaulty():
        return 0, [], True
    cantidad, problemas, completo = 0, [], True
    for r in analizador.GetCheckResult():
        estado = r.GetCheckStatus()
        if estado != BOPAlgo_CheckStatus.BOPAlgo_SelfIntersect:
            completo = completo and estado != BOPAlgo_CheckStatus.BOPAlgo_OperationAborted
            continue
        cantidad += 1
        if len(problemas) < limite:
            formas = list(r.GetFaultyShapes1())
            entre = " y ".join(_NOMBRE_TIPO.get(f.ShapeType(), "forma") for f in formas[:2]) or "formas"
            problemas.append(_problema("autointerseccion", "error", f"Autointersección entre {entre}.",
                                       _punto_comun(formas)))
    return cantidad, problemas, completo


# ---------------------------------------------------------------- revisar (B-rep)
def _revisar_brep(forma, autointersecciones, tolerancia_maxima, max_problemas):
    _exigir_forma(forma)
    caja = geo.caja_envolvente(forma)
    diag = _diagonal_caja(caja) or 1.0
    deflexion = max(diag / 400.0, 1e-4)
    caras = _unicas(forma, TopAbs_FACE)
    aristas = _unicas(forma, TopAbs_EDGE)
    vertices = _unicas(forma, TopAbs_VERTEX)
    topo = _topologia(forma)
    valido = geo.es_valida(forma)
    # Cada tipo de problema se arma (con su ubicación) hasta `max_problemas` veces: los demás no entrarían en la
    # lista final, que conserva el orden dentro de cada gravedad; los conteos son siempre completos.
    problemas = [] if valido else _detalle_validez(forma, caras, topo)
    for arista in topo["libres"][:max_problemas]:
        problemas.append(_problema("arista_libre", "error" if topo["solidos"] else "aviso",
                                   "Arista libre (abierta): borde de una sola cara.", _medio_arista(arista),
                                   _segmentos_arista(arista, deflexion)))
    for arista, n in topo["no_manifold"][:max_problemas]:
        problemas.append(_problema("arista_no_manifold", "error", f"Arista no manifold: la comparten {n} caras.",
                                   _medio_arista(arista), _segmentos_arista(arista, deflexion), valor=n))
    n_auto, completo = None, True
    if autointersecciones:
        try:
            n_auto, extra, completo = _autointersecciones(forma, max_problemas)
            problemas += extra
        except Exception:  # noqa: BLE001 — el análisis booleano puede fallar en formas muy rotas
            n_auto, completo = None, False
    degeneradas = [c for c in caras if _area(c) <= _AREA_DEGENERADA * diag * diag]
    for cara in degeneradas[:max_problemas]:
        problemas.append(_problema("cara_degenerada", "error", "Cara degenerada: su área es casi cero.",
                                   _punto_en(cara)))
    diminutas = [(a, geo.longitud(a)) for a in map(TopoDS.Edge, aristas) if not BRep_Tool.Degenerated_s(a)]
    diminutas = [(a, largo) for a, largo in diminutas if largo < LARGO_DIMINUTO]
    for a, largo in diminutas[:max_problemas]:
        problemas.append(_problema("arista_diminuta", "aviso", f"Arista diminuta: {_n(largo)} mm.", _medio_arista(a),
                                   valor=largo))
    tol_v = [BRep_Tool.Tolerance_s(TopoDS.Vertex(v)) for v in vertices]
    tol_a = [BRep_Tool.Tolerance_s(TopoDS.Edge(a)) for a in aristas]
    tol_c = [BRep_Tool.Tolerance_s(TopoDS.Face(c)) for c in caras]
    altas = 0
    for nombre, lista, tolerancias, punto in (
            ("vértice", vertices, tol_v, lambda s: _np(BRep_Tool.Pnt_s(TopoDS.Vertex(s)))),
            ("arista", aristas, tol_a, lambda s: _medio_arista(TopoDS.Edge(s))),
            ("cara", caras, tol_c, _punto_en)):
        for s, t in zip(lista, tolerancias, strict=True):
            if tolerancia_maxima is not None and t > tolerancia_maxima:
                if altas < max_problemas:
                    problemas.append(_problema("tolerancia_alta", "aviso", f"Tolerancia de {nombre} alta: {_n(t)} mm.",
                                               punto(s), valor=t))
                altas += 1
    solidos = topo["solidos"]
    sobran = lambda n: max(0, n - max_problemas)  # noqa: E731 — problemas contados que no se armaron
    errores = sobran(len(topo["no_manifold"])) + sobran(len(degeneradas)) + (n_auto or 0) - sum(
        p["tipo"] == "autointerseccion" for p in problemas)
    avisos = sobran(len(diminutas)) + sobran(altas)
    if solidos:
        errores += sobran(len(topo["libres"]))
    else:
        avisos += sobran(len(topo["libres"]))
    return _cerrar_informe({
        "tipo_cuerpo": "brep", "valido": valido, "cerrado": topo["cerrado"], "solidos": len(solidos),
        "cascaras": len(topo["cascaras"]), "cascaras_abiertas": len(topo["abiertas"]), "caras": len(caras),
        "aristas": len(aristas), "vertices": len(vertices), "aristas_libres": len(topo["libres"]),
        "aristas_no_manifold": len(topo["no_manifold"]), "aristas_sueltas": topo["sueltas"],
        "autointersecciones": n_auto, "autointersecciones_completo": completo,
        "caras_degeneradas": len(degeneradas), "aristas_diminutas": len(diminutas), "tolerancias_altas": altas,
        "tolerancias": {"vertice": max(tol_v, default=0.0), "arista": max(tol_a, default=0.0),
                        "cara": max(tol_c, default=0.0)},
        "volumen": geo.volumen(forma) if solidos else None, "area": geo.area(forma), "caja": caja,
    }, problemas, max_problemas, errores, avisos)


def _cerrar_informe(informe, problemas, max_problemas, errores_sin_armar=0, avisos_sin_armar=0):
    """Ordena los problemas (errores primero, sin cambiar el orden dentro de cada gravedad), deja los primeros
    `max_problemas` y cuenta todos: los armados más los que se contaron sin armar (más allá del tope por tipo)."""
    orden = {"error": 0, "aviso": 1}
    problemas = sorted(problemas, key=lambda p: orden.get(p["gravedad"], 2))
    informe["problemas"] = problemas[:max_problemas]
    informe["errores"] = sum(1 for p in problemas if p["gravedad"] == "error") + errores_sin_armar
    informe["avisos"] = sum(1 for p in problemas if p["gravedad"] == "aviso") + avisos_sin_armar
    informe["truncado"] = informe["errores"] + informe["avisos"] > len(informe["problemas"])
    return informe


# ---------------------------------------------------------------- revisar (malla)
def _grupos_aristas(aristas, n_vertices):
    """Índices de `aristas` (Kx2 de vértices) agrupados por cadenas conectadas (un agujero, un borde)."""
    if not len(aristas):
        return []
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    grafo = coo_matrix((np.ones(len(aristas)), (aristas[:, 0], aristas[:, 1])), shape=(n_vertices, n_vertices))
    _, etiqueta = connected_components(grafo, directed=False)
    por_arista = etiqueta[aristas[:, 0]]
    return [np.flatnonzero(por_arista == e) for e in np.unique(por_arista)]


def _problemas_aristas_malla(v, aristas, tipo, gravedad, texto):
    """Un problema por cadena de aristas conectadas, con el centro y los segmentos para resaltarla."""
    salida = []
    for grupo in _grupos_aristas(aristas, len(v)):
        pares = aristas[grupo]
        segmentos = v[pares].reshape(-1, 3)
        n = len(grupo)
        salida.append(_problema(tipo, gravedad, texto.format(n=n, s="" if n == 1 else "s"), segmentos.mean(0),
                                segmentos, valor=n))
    return salida


def _revisar_malla(m, max_problemas):
    v, c = m.vertices, m.caras
    if not len(c):
        raise geo.ErrorGeometria("La malla está vacía: no tiene triángulos para revisar.")
    info = ml.analizar(m)
    topo = ml._Topo(c, len(v))
    problemas = []
    libres = topo.aristas[topo.cuenta == 1]
    problemas += _problemas_aristas_malla(v, libres, "arista_libre", "error",
                                          "Borde abierto: {n} arista{s} de un solo triángulo.")
    no_manifold = topo.aristas[topo.cuenta > 2]
    problemas += _problemas_aristas_malla(v, no_manifold, "arista_no_manifold", "error",
                                          "No manifold: {n} arista{s} compartida{s} por más de dos triángulos.")
    _f1, _f2, mismo, ids = topo.pares()
    invertidas = topo.aristas[np.unique(ids[mismo])] if mismo.any() else np.zeros((0, 2), np.int64)
    problemas += _problemas_aristas_malla(v, invertidas, "normales_invertidas", "error",
                                          "Normales invertidas: {n} arista{s} entre triángulos de orientación "
                                          "opuesta.")
    diag = ml._diagonal(v) or 1.0
    degenerados = np.flatnonzero((c[:, 0] == c[:, 1]) | (c[:, 1] == c[:, 2]) | (c[:, 0] == c[:, 2])
                                 | (m.areas_caras() <= (1e-9 * diag) ** 2))
    centros = m.triangulos().mean(1)
    for k in degenerados[:max_problemas]:
        problemas.append(_problema("cara_degenerada", "error", "Triángulo degenerado: área casi cero.", centros[k]))
    volumen = info["volumen"]
    if info["cerrada"] and volumen < 0:
        problemas.append(_problema("volumen_negativo", "error", "Las normales apuntan hacia adentro (volumen "
                                   "negativo).", v[np.unique(c)].mean(0)))
    caja = m.caja()
    valido = not len(no_manifold) and not len(degenerados) and not len(invertidas) and not (
        info["cerrada"] and volumen < 0)
    return _cerrar_informe({
        "tipo_cuerpo": "malla", "valido": valido, "cerrado": bool(info["cerrada"]), "solidos": None,
        "cascaras": info["cascaras"], "cascaras_abiertas": int((~ml._cascaras(c, len(v))[1]).sum()),
        "caras": len(c), "aristas": len(topo.aristas), "vertices": len(v), "aristas_libres": len(libres),
        "aristas_no_manifold": len(no_manifold), "aristas_sueltas": 0, "autointersecciones": None,
        "autointersecciones_completo": False, "caras_degeneradas": len(degenerados), "aristas_diminutas": 0,
        "tolerancias_altas": 0, "tolerancias": None, "normales_invertidas": len(invertidas),
        "volumen_negativo": bool(info["cerrada"] and volumen < 0),
        "volumen": abs(volumen) if info["cerrada"] else None, "area": info["area"], "caja": caja,
    }, problemas, max_problemas, max(0, len(degenerados) - max_problemas))


def revisar(forma, *, autointersecciones=True, tolerancia_maxima=TOLERANCIA_ALTA, max_problemas=MAX_PROBLEMAS):
    """Revisar geometría (FreeCAD Part › Check Geometry; Rhino ShowEdges): diagnóstico de un cuerpo.

    `forma`: forma OCC (sólido, superficie, compuesto) o `nucleo.malla.Malla`. Devuelve un dict con:
    "valido" (BRepCheck; en mallas: sin no manifold, degenerados ni normales invertidas), "cerrado" (estanco),
    conteos ("solidos", "cascaras", "cascaras_abiertas", "caras", "aristas", "vertices", "aristas_libres",
    "aristas_no_manifold", "autointersecciones" —None si no se revisaron o en mallas—, "caras_degeneradas",
    "aristas_diminutas", "tolerancias_altas"), "tolerancias" máximas {"vertice", "arista", "cara"} (None en
    mallas), "volumen" (None si no es cerrado), "area", "caja" y "problemas" (los primeros `max_problemas`,
    errores primero; "truncado" dice si había más; "errores" y "avisos" los cuentan a todos).
    `autointersecciones=False` saltea BOPAlgo_ArgumentAnalyzer (lo más lento en piezas grandes).
    `tolerancia_maxima` (mm): tolerancias mayores se avisan; None no las avisa.
    """
    if int(max_problemas) < 0:
        raise geo.ErrorGeometria("La cantidad máxima de problemas no puede ser negativa.")
    if isinstance(forma, ml.Malla):
        return _revisar_malla(forma, int(max_problemas))
    return _revisar_brep(forma, bool(autointersecciones), tolerancia_maxima, int(max_problemas))


# ---------------------------------------------------------------- impresión 3D
def _choques(o, d, tri, eps):
    """(t, j) del primer triángulo de `tri` (los arreglos de `_preparar`) que corta cada rayo; (inf, −1) si
    ninguno. En tandas de _PARES_POR_TANDA pares rayo-triángulo."""
    a, e1, e2, N, largo_n, aN, e2xa, axe1 = tri
    t_salida, j_salida = np.full(len(o), np.inf), np.full(len(o), -1, np.int64)
    paso = max(1, _PARES_POR_TANDA // max(len(a), 1))
    for i in range(0, len(o), paso):
        oo, dd = o[i:i + paso], d[i:i + paso]
        det = -(dd @ N.T)
        ok = np.abs(det) > 1e-9 * largo_n
        det = np.where(ok, det, 1.0)
        od = np.cross(oo, dd)
        u = (od @ e2.T - dd @ e2xa.T) / det
        v = (-(od @ e1.T) - dd @ axe1.T) / det
        t = (oo @ N.T - aN) / det
        t = np.where(ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > eps), t, np.inf)
        j = t.argmin(axis=1)
        mejor = t[np.arange(len(j)), j]
        t_salida[i:i + paso] = mejor
        j_salida[i:i + paso] = np.where(np.isfinite(mejor), j, -1)
    return t_salida, j_salida


def _orden_morton(puntos):
    """Orden de los puntos sobre la curva Z (código de Morton de 10 bits por eje): los consecutivos quedan cerca."""
    lo, hi = puntos.min(0), puntos.max(0)
    q = np.floor((puntos - lo) / np.maximum(hi - lo, 1e-300) * 1023).astype(np.int64)
    codigo = np.zeros(len(puntos), np.int64)
    for bit in range(10):
        for eje in range(3):
            codigo |= ((q[:, eje] >> bit) & 1) << (3 * bit + eje)
    return np.argsort(codigo, kind="stable")


def _preparar(a, e1, e2):
    N = np.cross(e1, e2)
    return a, e1, e2, N, np.linalg.norm(N, axis=1), np.einsum("ij,ij->i", a, N), np.cross(e2, a), np.cross(a, e1)


def primer_choque(origenes, direcciones, triangulos, eps):
    """(t, triángulo) del primer triángulo que corta cada rayo origen + t·dirección con t > eps; (inf, −1) si
    ninguno. `triangulos`: Tx3x3; direcciones unitarias.

    Möller–Trumbore vectorizado con una dirección por rayo (`analisis._rayos_chocan` es el caso de una dirección
    común): los productos mixtos se arman como (rayos x 3) @ (3 x triángulos), sin arreglos de rayos x triángulos
    x 3. Para no probar cada rayo contra todos los triángulos, la búsqueda va por alcances crecientes (diagonal/64,
    ×4 cada vez): cada tanda de rayos vecinos prueba solo los triángulos cuya caja toca la de sus segmentos, y un
    choque a menos del alcance ya es el más cercano; los que no chocan pasan a la vuelta siguiente."""
    O = np.asarray(origenes, float).reshape(-1, 3)
    D = np.asarray(direcciones, float).reshape(-1, 3)
    T = np.asarray(triangulos, float).reshape(-1, 3, 3)
    distancia, indice = np.full(len(O), np.inf), np.full(len(O), -1, np.int64)
    if not len(O) or not len(T):
        return distancia, indice
    e1, e2 = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    sanos = np.flatnonzero(np.linalg.norm(np.cross(e1, e2), axis=1) > 1e-300)
    T, e1, e2 = T[sanos], e1[sanos], e2[sanos]
    todos = _preparar(T[:, 0], e1, e2)
    lo_t, hi_t = T.min(axis=1), T.max(axis=1)
    diag = float(np.linalg.norm(hi_t.max(0) - lo_t.min(0))) or 1.0
    pendientes = _orden_morton(O)                     # rayos vecinos en la misma tanda: cajas chicas
    alcance = diag / 64
    while len(pendientes):
        final = alcance > 2 * diag
        quedan = []
        for i in range(0, len(pendientes), _RAYOS_POR_TANDA):
            r = pendientes[i:i + _RAYOS_POR_TANDA]
            o, d = O[r], D[r]
            if final:
                cand, tri = None, todos
            else:
                fin = o + d * alcance
                lo, hi = np.minimum(o, fin).min(0) - eps, np.maximum(o, fin).max(0) + eps
                cand = np.flatnonzero(np.all(hi_t >= lo, axis=1) & np.all(lo_t <= hi, axis=1))
                if not len(cand):
                    quedan.append(r)
                    continue
                tri = tuple(x[cand] for x in todos)
            t, j = _choques(o, d, tri, eps)
            ok = np.isfinite(t) if final else t <= alcance
            distancia[r[ok]] = t[ok]
            indice[r[ok]] = sanos[j[ok] if cand is None else cand[j[ok]]]
            quedan.append(r[~ok])
        pendientes = np.zeros(0, np.int64) if final else np.concatenate(quedan)
        alcance *= 4
    return distancia, indice


def espesores(m, *, muestras=MUESTRAS_ESPESOR, semilla=0):
    """Espesor de pared de una malla cerrada por rayos (como ThicknessAnalysis de Rhino o el espesor de la caja de
    impresión de Blender): desde `muestras` puntos al azar sobre la superficie (repartidos por área; semilla fija,
    el resultado se repite) se tira un rayo hacia adentro (−normal del triángulo) y el espesor es la distancia al
    primer triángulo que corta. Con mallas muy grandes se usan menos rayos (tope de _PARES_TOTALES).

    Devuelve (puntos Sx3, espesores S —nan donde el rayo no corta nada: malla abierta—, triángulo de cada punto S,
    triángulo opuesto S o −1). La precisión es la del teselado: exacta en caras planas."""
    tris = m.triangulos()
    normales = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    largo = np.linalg.norm(normales, axis=1)
    diag = ml._diagonal(m.vertices) or 1.0
    candidatos = np.flatnonzero(largo > (1e-9 * diag) ** 2)
    if not len(candidatos):
        return np.zeros((0, 3)), np.zeros(0), np.zeros(0, np.int64), np.zeros(0, np.int64)
    s = min(int(muestras), max(200, int(_PARES_TOTALES // max(len(tris), 1))))
    azar = np.random.default_rng(semilla)
    origen = np.sort(azar.choice(candidatos, s, p=largo[candidatos] / largo[candidatos].sum()))
    r1, r2 = np.sqrt(azar.random(s)), azar.random(s)               # punto uniforme dentro del triángulo
    t = tris[origen]
    puntos = (1 - r1)[:, None] * t[:, 0] + (r1 * (1 - r2))[:, None] * t[:, 1] + (r1 * r2)[:, None] * t[:, 2]
    n = normales[origen] / largo[origen, None]
    distancia, opuesto = primer_choque(puntos, -n, tris, 1e-7 * diag)
    return puntos, np.where(np.isfinite(distancia), distancia, np.nan), origen, opuesto


def _zonas_finas(puntos, espesor, umbral, lado):
    """Zonas de pared más fina que `umbral`: las muestras finas a menos de `lado` mm unas de otras forman una
    zona (enlace simple: una pared fina grande queda en una sola, las dos caras de la pared también). [(índice de
    la muestra más fina, cantidad de muestras)], de la más fina a la más gruesa."""
    finas = np.flatnonzero(np.nan_to_num(espesor, nan=np.inf) < umbral)
    if not len(finas):
        return []
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    n = len(finas)
    pares = cKDTree(puntos[finas]).query_pairs(lado, output_type="ndarray").reshape(-1, 2)
    _, zona = connected_components(coo_matrix((np.ones(len(pares)), (pares[:, 0], pares[:, 1])), shape=(n, n)),
                                   directed=False)
    salida = []
    for z in np.unique(zona):
        k = finas[zona == z]
        salida.append((int(k[np.argmin(espesor[k])]), len(k)))
    return sorted(salida, key=lambda x: espesor[x[0]])


def _voladizos(m, angulo_voladizo):
    """[(área, centro, segmentos del contorno)] de las zonas en voladizo: triángulos cuya normal mira hacia
    abajo a menos de (90° − angulo_voladizo) de −Z, sin contar los apoyados en la cama (z mínima); cada zona es
    un grupo de triángulos vecinos."""
    tris = m.triangulos()
    n = m.normales_caras()
    areas = m.areas_caras()
    limite = math.cos(math.radians(90.0 - float(angulo_voladizo)))
    hacia_abajo = -n[:, 2]
    z0 = float(m.vertices[np.unique(m.caras), 2].min())
    tol = 1e-6 * (ml._diagonal(m.vertices) or 1.0) + 1e-9
    en_cama = np.all(tris[:, :, 2] <= z0 + tol, axis=1)
    mascara = (hacia_abajo > limite + 1e-12) & ~en_cama & (areas > 0)
    sel = np.flatnonzero(mascara)
    if not len(sel):
        return []
    etiqueta, _ = ml._cascaras(m.caras[sel], len(m.vertices))
    zonas = []
    for e in np.unique(etiqueta):
        k = sel[etiqueta == e]
        area = float(areas[k].sum())
        centro = (tris[k].mean(1) * areas[k, None]).sum(0) / max(area, 1e-300)
        topo = ml._Topo(m.caras[k], len(m.vertices))
        borde = topo.aristas[topo.cuenta == 1]
        zonas.append((area, centro, m.vertices[borde].reshape(-1, 3)))
    return sorted(zonas, key=lambda z: -z[0])


def _filosas_brep(topo, angulo_filoso):
    """[(arista, ángulo interior)] de las aristas convexas cuyo ángulo interior (el del material entre las dos
    caras) es menor que `angulo_filoso`: filos de cuchillo que una impresora no reproduce."""
    salida = []
    for i, arista in topo["dobles"]:
        caras = _caras_de(topo["vecinas"], i)
        f1, f2 = TopoDS.Face(caras[0]), TopoDS.Face(caras[1])
        try:
            curva = BRepAdaptor_Curve(arista)
            t = 0.5 * (curva.FirstParameter() + curva.LastParameter())
            n1, n2 = an._normal_en(f1, arista, t), an._normal_en(f2, arista, t)
        except Exception:  # noqa: BLE001 — arista sin curva en alguna de las caras
            continue
        if n1 is None or n2 is None:
            continue
        interior = 180.0 - math.degrees(math.acos(float(np.clip(n1 @ n2, -1.0, 1.0))))
        if interior < angulo_filoso and not an._es_concava(arista, topo["vecinas"].FindFromIndex(i)):
            salida.append((arista, interior))
    return salida


def _filosas_malla(m, angulo_filoso):
    """[(par de vértices, ángulo interior)] de las aristas convexas de la malla más agudas que `angulo_filoso`."""
    v, c = m.vertices, m.caras
    topo = ml._Topo(c, len(v))
    f1, f2, mismo, ids = topo.pares()
    if not len(f1):
        return []
    n = m.normales_caras()
    interior = 180.0 - np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", n[f1], n[f2]), -1.0, 1.0)))
    pares = topo.aristas[ids]
    opuesto = c[f2].sum(1) - pares.sum(1)                   # el vértice de f2 que no está en la arista
    diag = ml._diagonal(v) or 1.0
    convexa = np.einsum("ij,ij->i", n[f1], v[opuesto] - v[pares[:, 0]]) < -1e-9 * diag
    sel = np.flatnonzero(~mismo & convexa & (interior < angulo_filoso))
    return [(pares[k], float(interior[k])) for k in sel]


def revisar_impresion(forma, *, espesor_minimo=0.8, angulo_voladizo=45.0, angulo_filoso=20.0,
                      muestras=MUESTRAS_ESPESOR, max_problemas=MAX_PROBLEMAS):
    """Revisión de impresión 3D (Blender 3D Print Toolbox; Rhino ThicknessAnalysis) de una forma OCC o una Malla.

    - Espesor: rayos hacia adentro desde `muestras` puntos de la malla (la del cuerpo o su teselado); "espesor_minimo"
      es el menor medido y cada zona más fina que `espesor_minimo` (mm) es un problema "espesor_fino".
    - Voladizos: zonas que miran hacia abajo más allá de `angulo_voladizo` (grados desde la vertical; 45° es lo
      habitual sin soportes), sin contar la cara apoyada en la cama: "area_voladizo" (mm²) y un problema
      "voladizo" (aviso) por zona.
    - Aristas filosas: convexas con ángulo interior menor que `angulo_filoso` (grados): problema "arista_filosa".
    - Abierto: un cuerpo no estanco no se puede imprimir (problema "abierto").
    Devuelve además "cerrado", "volumen", "area", "caja", "imprimible" (estanco y sin zonas finas) y, como
    `revisar`, "problemas" (los primeros `max_problemas`), "truncado", "errores" y "avisos".
    Limitación: el espesor por rayos mide de pared a pared en la dirección de la normal (no la esfera inscrita) y
    su precisión es la del teselado (exacta en caras planas).
    """
    if not espesor_minimo >= 0 or not math.isfinite(espesor_minimo):
        raise geo.ErrorGeometria("El espesor mínimo tiene que ser un número mayor o igual que cero (mm).")
    if not 0 < angulo_voladizo < 90:
        raise geo.ErrorGeometria("El ángulo de voladizo tiene que estar entre 0° y 90° (desde la vertical).")
    if not 0 <= angulo_filoso < 180:
        raise geo.ErrorGeometria("El ángulo de filo tiene que estar entre 0° y 180°.")
    if int(muestras) < 1:
        raise geo.ErrorGeometria("Hace falta al menos una muestra para medir el espesor.")
    max_problemas = int(max_problemas)
    if max_problemas < 0:
        raise geo.ErrorGeometria("La cantidad máxima de problemas no puede ser negativa.")
    problemas = []
    if isinstance(forma, ml.Malla):
        if not len(forma.caras):
            raise geo.ErrorGeometria("La malla está vacía: no tiene triángulos para revisar.")
        m, tipo_cuerpo = forma, "malla"
        cerrado = m.es_cerrada()
        volumen = abs(m.volumen()) if cerrado else None
        area, caja = m.area(), m.caja()
        todas = _filosas_malla(m, angulo_filoso)
        filosas = [(ang, m.vertices[par]) for par, ang in todas[:max_problemas]]
    else:
        _exigir_forma(forma)
        tipo_cuerpo = "brep"
        topo = _topologia(forma)
        cerrado = topo["cerrado"]
        caja = geo.caja_envolvente(forma)
        deflexion = max(_diagonal_caja(caja) / 400.0, 1e-4)
        volumen = geo.volumen(forma) if topo["solidos"] else None
        area = geo.area(forma)
        m = ml.desde_brep(forma, refinamiento="medio")
        todas = _filosas_brep(topo, angulo_filoso)
        filosas = [(ang, _segmentos_arista(a, deflexion)) for a, ang in todas[:max_problemas]]
    if not cerrado:
        centro = None if caja is None else (np.array(caja[0]) + np.array(caja[1])) / 2
        problemas.append(_problema("abierto", "error", "El cuerpo no es estanco (tiene bordes abiertos): no se puede "
                                   "imprimir así. Usá Reparar o revisá la geometría.", centro))
    puntos, espesor, origen, _opuesto = espesores(m, muestras=muestras)
    medidos = np.isfinite(espesor)
    minimo = float(np.nanmin(espesor)) if medidos.any() else None
    diag = _diagonal_caja(caja) or 1.0
    zonas_finas = _zonas_finas(puntos, espesor, espesor_minimo, max(2.0 * espesor_minimo, diag / 50.0, 1e-6))
    normales = m.normales_caras()
    for k, _cuantas in zonas_finas:
        medio = puntos[k] - normales[origen[k]] * espesor[k] / 2          # el centro de la pared
        problemas.append(_problema("espesor_fino", "error", f"Pared de {_n(espesor[k])} mm (mínimo {_n(espesor_minimo)}"
                                   " mm).", medio, valor=espesor[k]))
    zonas = _voladizos(m, angulo_voladizo)
    for area_z, centro, borde in zonas:
        problemas.append(_problema("voladizo", "aviso", f"Voladizo de {_n(area_z)} mm² (más de "
                                   f"{_n(angulo_voladizo)}° desde la vertical): necesita soportes.", centro, borde,
                                   valor=area_z))
    for ang, segs in filosas:
        segs = None if segs is None else np.asarray(segs, float).reshape(-1, 3)
        problemas.append(_problema("arista_filosa", "aviso", f"Arista filosa: ángulo interior de {_n(ang)}°.",
                                   None if segs is None or not len(segs) else segs.mean(0), segs, valor=ang))
    return _cerrar_informe({
        "tipo_cuerpo": tipo_cuerpo, "cerrado": bool(cerrado), "volumen": volumen, "area": area, "caja": caja,
        "espesor_minimo": minimo, "umbral_espesor": float(espesor_minimo), "muestras": len(puntos),
        "zonas_finas": len(zonas_finas), "angulo_voladizo": float(angulo_voladizo),
        "area_voladizo": float(sum(z[0] for z in zonas)), "zonas_voladizo": len(zonas),
        "angulo_filoso": float(angulo_filoso), "aristas_filosas": len(todas),
        "imprimible": bool(cerrado) and not zonas_finas,
    }, problemas, max_problemas, 0, len(todas) - len(filosas))


# ---------------------------------------------------------------- reparar
def reparar(forma, *, tolerancia=0.01, coser=True, refinar=True, arreglar=True):
    """Reparar (FreeCAD Check Geometry › reparar, Set Tolerance y Refine Shape; «Hacer manifold» de la caja de
    impresión 3D de Blender). Devuelve una forma NUEVA (no toca la de entrada).

    B-rep, en este orden: `coser` (si tiene aristas libres: BRepBuilderAPI_Sewing con `tolerancia`; si queda
    estanco pasa a sólido, como `superficies.coser`), tolerancias (las mayores que `tolerancia` se bajan a
    `tolerancia`: Set Tolerance), `arreglar` (ShapeFix_Shape: orientación de caras, contornos, curvas sobre la
    cara, con `tolerancia` como máximo) y `refinar` (UnifySameDomain: une caras coplanares y aristas colineales).
    `tolerancia` en mm; 0 = sin tope (ShapeFix usa la del kernel y coser 1e-6 mm).
    Malla: `malla.reparar(tipo="coser_y_quitar")` (une vértices a menos de `tolerancia`, corrige degenerados,
    orienta las normales y cierra agujeros).
    """
    tol = float(tolerancia or 0.0)
    if tol < 0 or not math.isfinite(tol):
        raise geo.ErrorGeometria("La tolerancia de reparación no puede ser negativa.")
    if isinstance(forma, ml.Malla):
        return ml.reparar(forma, tipo="coser_y_quitar", tolerancia=tol if tol > 0 else None)
    _exigir_forma(forma)
    r = BRepBuilderAPI_Copy(forma).Shape()
    if coser and _topologia(r)["libres"]:
        from . import superficies as sf
        r = sf.coser([r], tol if tol > 0 else 1e-6)["forma"]
    if tol > 0:
        ShapeFix_ShapeTolerance().LimitTolerance(r, 0.0, tol)
    if arreglar:
        arreglo = ShapeFix_Shape(r)
        if tol > 0:
            arreglo.SetPrecision(min(tol, 1e-7))
            arreglo.SetMaxTolerance(tol)
        arreglo.Perform()
        r = arreglo.Shape()
    if refinar:
        r = geo.unificar_caras(r)
    if r is None or r.IsNull() or geo.esta_vacia(r):
        raise geo.ErrorGeometria("La reparación dejó la forma vacía: probá con otra tolerancia o sin refinar.")
    return r


# ---------------------------------------------------------------- texto
def resumen(informe):
    """Líneas de texto (español) que resumen un informe de `revisar` o de `revisar_impresion`."""
    lineas = []
    if "espesor_minimo" in informe:
        lineas.append("Estanco: sí" if informe["cerrado"] else "Estanco: NO (bordes abiertos)")
        e = informe["espesor_minimo"]
        lineas.append(f"Espesor mínimo: {'—' if e is None else _n(e) + ' mm'} (umbral {_n(informe['umbral_espesor'])} "
                      f"mm, {informe['muestras']} muestras); zonas finas: {informe['zonas_finas']}")
        lineas.append(f"Voladizo (> {_n(informe['angulo_voladizo'])}°): {_n(informe['area_voladizo'])} mm² en "
                      f"{informe['zonas_voladizo']} zona(s)")
        lineas.append(f"Aristas filosas (< {_n(informe['angulo_filoso'])}°): {informe['aristas_filosas']}")
        lineas.append("Imprimible: sí" if informe["imprimible"] else "Imprimible: NO")
    else:
        if informe["tipo_cuerpo"] == "malla":
            lineas.append(f"Malla: {informe['caras']} triángulos, {informe['cascaras']} cáscara(s)")
        else:
            lineas.append(f"{informe['solidos']} sólido(s), {informe['cascaras']} cáscara(s), {informe['caras']} "
                          f"caras, {informe['aristas']} aristas")
        lineas.append("Válido: sí" if informe["valido"] else "Válido: NO")
        lineas.append("Estanco: sí" if informe["cerrado"] else "Estanco: NO")
        lineas.append(f"Aristas libres: {informe['aristas_libres']} · no manifold: {informe['aristas_no_manifold']}")
        auto = informe["autointersecciones"]
        lineas.append("Autointersecciones: " + ("no revisadas" if auto is None else str(auto)))
        lineas.append(f"Caras degeneradas: {informe['caras_degeneradas']}")
        if informe.get("normales_invertidas") is not None:
            lineas.append(f"Normales invertidas: {informe['normales_invertidas']}")
        tol = informe.get("tolerancias")
        if tol:
            lineas.append(f"Tolerancia máx.: vértice {_n(tol['vertice'])} · arista {_n(tol['arista'])} · cara "
                          f"{_n(tol['cara'])} mm")
    if informe.get("volumen") is not None:
        lineas.append(f"Volumen: {_n(informe['volumen'])} mm³ · área: {_n(informe['area'])} mm²")
    else:
        lineas.append(f"Área: {_n(informe['area'])} mm²")
    caja = informe.get("caja")
    if caja:
        tam = np.subtract(caja[1], caja[0])
        lineas.append(f"Caja: {_n(tam[0])} × {_n(tam[1])} × {_n(tam[2])} mm")
    return lineas
