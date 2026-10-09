# -*- coding: utf-8 -*-
"""
Espacio de trabajo DIBUJO: planos 2D a partir del diseño (Fusion › Nuevo dibujo › Desde diseño).

Equivalencias con la ayuda de Fusion (libro "Drawing"):
  - Base / Projected / Section / Detail View  →  Vista(tipo="base" | "proyectada" | "seccion" | "detalle")
  - Style: Visible Edges / Visible and Hidden Edges  →  estilo "visibles" | "visibles_ocultas" (None = del padre)
  - Tangent Edges: Full Length / Shortened / Off     →  tangentes "completas" | "acortadas" | "no"
  - Projection angle: ISO 1.er diedro / ASME 3.er diedro  →  Dibujo.diedro "primero" | "tercero"
  - Center Mark / Center Line (automáticas y manuales); Dimension (lineal, alineada, radio, diámetro, angular,
    ordenadas); Text; Leader; Table (lista de piezas); Balloon; Title block con atributos; Sheet Size ISO A4–A0
    y ASME A–E con zonas.

Proyección: eliminación exacta de líneas ocultas de OpenCascade (HLRBRep_Algo + HLRBRep_HLRToShape) o, con
metodo="rapido", la poligonal sobre el teselado (HLRBRep_PolyAlgo).

Sistemas de coordenadas:
  - "modelo 2D" de una vista: mm del modelo sobre el plano de proyección, en los ejes de pantalla de la vista;
  - "hoja": mm del papel, origen abajo a la izquierda, y hacia arriba.
  Una vista convierte con  hoja = posicion + escala · R(rotacion) · (p − centro).

Salida para pintar o exportar: lista de (capa, primitiva) con las primitivas de `io_archivos.dxf`:
('linea', p1, p2), ('polilinea', pts, cerrada), ('circulo', c, r), ('arco', c, r, a0, a1),
('texto', p, altura, texto, rotacion_grados, alineacion), ('solido', pts).
Módulo puro: sin Qt ni timeline; recibe las formas de los cuerpos.
"""
import datetime
import math

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.GCPnts import GCPnts_TangentialDeflection
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Line, GeomAbs_Plane
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape, HLRBRep_PolyAlgo, HLRBRep_PolyHLRToShape
from OCP.OCP.collections import IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher
from OCP.TopAbs import TopAbs_EDGE, TopAbs_REVERSED, TopAbs_WIRE
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Shape
from OCP.gp import gp_Ax2, gp_Dir, gp_Pln, gp_Pnt

from . import geometria as geo

# ---------------------------------------------------------------- hoja
TAMANOS_HOJA = {   # (ancho, alto) en mm, horizontal (Sheet Size reference)
    "A4": (297.0, 210.0), "A3": (420.0, 297.0), "A2": (594.0, 420.0), "A1": (841.0, 594.0), "A0": (1189.0, 841.0),
    "ANSI A": (279.4, 215.9), "ANSI B": (431.8, 279.4), "ANSI C": (558.8, 431.8), "ANSI D": (863.6, 558.8),
    "ANSI E": (1117.6, 863.6)}
ZONAS_HOJA = {     # (horizontales, verticales): ISO 5457 y ASME Y14.1
    "A4": (6, 4), "A3": (8, 6), "A2": (12, 8), "A1": (16, 12), "A0": (24, 16),
    "ANSI A": (4, 2), "ANSI B": (4, 2), "ANSI C": (4, 4), "ANSI D": (8, 4), "ANSI E": (8, 4)}
ESCALAS = (1 / 1000, 1 / 500, 1 / 200, 1 / 100, 1 / 50, 1 / 20, 1 / 10, 1 / 5, 1 / 2, 1.0,
           2.0, 5.0, 10.0, 20.0, 50.0, 100.0)   # ISO 5455
MARGEN = 10.0
ANCHO_CAJETIN, ALTO_CAJETIN = 180.0, 36.0

# Capas: grosor (mm), tipo de línea, color ACI. Las usan la pantalla, el PDF y el DXF.
CAPAS = {
    "VISIBLE": {"grosor": 0.5, "tipo": "continua", "color": 7},
    "OCULTA": {"grosor": 0.25, "tipo": "trazos", "color": 8},
    "TANGENTE": {"grosor": 0.18, "tipo": "continua", "color": 9},
    "CENTRO": {"grosor": 0.18, "tipo": "trazo_punto", "color": 1},
    "RAYADO": {"grosor": 0.18, "tipo": "continua", "color": 8},
    "CONTORNO": {"grosor": 0.25, "tipo": "continua", "color": 7},
    "SECCION": {"grosor": 0.35, "tipo": "trazo_punto", "color": 7},
    "CORTE": {"grosor": 0.7, "tipo": "continua", "color": 7},       # extremos gruesos y flechas del corte
    "COTAS": {"grosor": 0.18, "tipo": "continua", "color": 3},
    "TEXTO": {"grosor": 0.25, "tipo": "continua", "color": 7},
    "TABLAS": {"grosor": 0.25, "tipo": "continua", "color": 7},
    "CAJETIN": {"grosor": 0.35, "tipo": "continua", "color": 7},
    "MARCO": {"grosor": 0.7, "tipo": "continua", "color": 7},
}

ALTURA_TEXTO = 3.5      # ISO 3098
FLECHA, MEDIA_FLECHA = 3.0, 0.5
HUECO_EXT, EXCESO_EXT = 1.0, 2.0      # líneas de referencia: separación del objeto y exceso sobre la cota
SOBREPASO_EJE = 3.0                   # cuánto pasan las líneas de centro del contorno
PASO_RAYADO = 2.5                     # separación del rayado en la hoja (mm)


def tamano_hoja(nombre, orientacion="horizontal"):
    """(ancho, alto) en mm de una hoja ISO A4–A0 o ASME A–E, horizontal o vertical."""
    if nombre not in TAMANOS_HOJA:
        raise geo.ErrorGeometria(f"Tamaño de hoja desconocido: {nombre}")
    a, b = TAMANOS_HOJA[nombre]
    return (a, b) if orientacion == "horizontal" else (b, a)


def formatear(valor, decimales=2):
    """Número de cota sin ceros finales ("12.5", "10")."""
    t = f"{valor:.{decimales}f}".rstrip("0").rstrip(".")
    return "0" if t in ("-0", "") else t


def texto_escala(escala):
    """0.5 → "1:2", 2 → "2:1" (formato Ratio de Fusion)."""
    if escala <= 0:
        raise geo.ErrorGeometria("La escala debe ser positiva.")
    return f"{formatear(escala, 4)}:1" if escala >= 1 else f"1:{formatear(1 / escala, 4)}"


def leer_escala(texto):
    """Acepta "1:2", "2:1", "1/2" o "0.5" (formatos Ratio, Fraction y Decimal de Fusion)."""
    t = str(texto).strip().replace(",", ".").replace(" ", "")
    try:
        if ":" in t or "/" in t:
            a, b = t.replace("/", ":").split(":")
            valor = float(a) / float(b)
        else:
            valor = float(t)
    except (ValueError, ZeroDivisionError):
        raise geo.ErrorGeometria(f"Escala no válida: «{texto}».") from None
    if not (valor > 0 and math.isfinite(valor)):
        raise geo.ErrorGeometria(f"Escala no válida: «{texto}».")
    return valor


def escala_automatica(ancho, alto, ancho_util, alto_util, fraccion=0.4):
    """La mayor escala normalizada con la que la vista ocupa como mucho `fraccion` del área útil (Fusion calcula
    la escala de la vista base al crearla; deja lugar para las proyectadas)."""
    ancho, alto = max(ancho, 1e-6), max(alto, 1e-6)
    validas = [e for e in ESCALAS if ancho * e <= ancho_util * fraccion and alto * e <= alto_util * fraccion]
    return max(validas) if validas else ESCALAS[0]


# ---------------------------------------------------------------- direcciones de vista
def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise geo.ErrorGeometria("Dirección nula.")
    return v / n


class Marco:
    """Dirección de una vista: e apunta al observador; x e y son la derecha y el arriba de la pantalla."""
    __slots__ = ("e", "x", "y")

    def __init__(self, e, x, y=None):
        self.e = _unit(e)
        x = np.asarray(x, float)
        self.x = _unit(x - self.e * float(x @ self.e))
        self.y = np.cross(self.e, self.x) if y is None else _unit(y)

    def a_2d(self, puntos):
        p = np.asarray(puntos, float)
        return np.stack([p @ self.x, p @ self.y], axis=-1)

    def a_3d(self, puntos, profundidad=0.0):
        p = np.asarray(puntos, float)
        return p[..., :1] * self.x + p[..., 1:2] * self.y + profundidad * self.e

    def ax2(self):
        return gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*map(float, self.e)), gp_Dir(*map(float, self.x)))

    def a_lista(self):
        return [self.e.tolist(), self.x.tolist()]


# (hacia el observador, arriba de la pantalla). Z hacia arriba: el frente mira desde −Y (plano XZ).
ORIENTACIONES = {
    "frontal": ((0, -1, 0), (0, 0, 1)), "trasera": ((0, 1, 0), (0, 0, 1)),
    "superior": ((0, 0, 1), (0, 1, 0)), "inferior": ((0, 0, -1), (0, -1, 0)),
    "derecha": ((1, 0, 0), (0, 0, 1)), "izquierda": ((-1, 0, 0), (0, 0, 1)),
    "iso_se": ((1, -1, 1), (0, 0, 1)), "iso_so": ((-1, -1, 1), (0, 0, 1)),
    "iso_ne": ((1, 1, 1), (0, 0, 1)), "iso_no": ((-1, 1, 1), (0, 0, 1)),
}
NOMBRES_ORIENTACION = {
    "frontal": "Frontal", "superior": "Superior", "derecha": "Derecha", "izquierda": "Izquierda",
    "inferior": "Inferior", "trasera": "Trasera", "iso_se": "Isométrica SE", "iso_so": "Isométrica SO",
    "iso_ne": "Isométrica NE", "iso_no": "Isométrica NO"}


def _marco_con_arriba(e, arriba):
    e = _unit(e)
    y = np.asarray(arriba, float)
    y = y - e * float(y @ e)
    if np.linalg.norm(y) < 1e-9:
        y = np.array([0.0, 1.0, 0.0]) - e * e[1]
    y = _unit(y)
    return Marco(e, np.cross(y, e), y)


def marco_orientacion(nombre):
    """Marco de una orientación de vista base (Orientation del diálogo Drawing View)."""
    if nombre not in ORIENTACIONES:
        raise geo.ErrorGeometria(f"Orientación de vista desconocida: {nombre}")
    return _marco_con_arriba(*ORIENTACIONES[nombre])


def direccion_proyectada(dx, dy):
    """Sector de la posición respecto de la vista padre: (±1, 0) o (0, ±1) ortogonal, diagonal = isométrica."""
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        raise geo.ErrorGeometria("La vista proyectada tiene que quedar a un costado de la vista padre.")
    k = round(math.degrees(math.atan2(dy, dx)) / 45.0) % 8
    return [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)][k]


def _marco_girado(padre, m, signo):
    """Vista vecina en la dirección de hoja m (unitaria): signo +1 = 3.er diedro / sección, −1 = 1.er diedro.
    La profundidad de la padre (−e) queda hacia signo·m y la dirección perpendicular se conserva (alineación)."""
    mx, my = float(m[0]), float(m[1])
    q = -my * padre.x + mx * padre.y
    e = signo * (mx * padre.x + my * padre.y)
    x = signo * mx * (-padre.e) - my * q
    y = signo * my * (-padre.e) + mx * q
    return Marco(e, x, y)


def marco_proyectado(padre, direccion, diedro="primero"):
    """Marco de una vista proyectada (Projected View) puesta en `direccion` respecto de la padre.

    3.er diedro (ASME): la vista a la derecha muestra lo que se ve desde la derecha; 1.er diedro (ISO): desde
    la izquierda. En diagonal da una isométrica mirando desde ese cuadrante (igual en los dos diedros)."""
    mx, my = direccion
    if mx and my:
        return _marco_con_arriba(padre.e + mx * padre.x + my * padre.y, padre.y)
    return _marco_girado(padre, (mx, my), 1 if diedro == "tercero" else -1)


# ---------------------------------------------------------------- proyección con líneas ocultas
CATEGORIAS = ("visibles", "silueta", "tangentes", "ocultas", "silueta_oculta", "tangentes_ocultas")
_COMPUESTOS = {"visibles": "VCompound", "silueta": "OutLineVCompound", "tangentes": "Rg1LineVCompound",
               "ocultas": "HCompound", "silueta_oculta": "OutLineHCompound", "tangentes_ocultas": "Rg1LineHCompound"}


def _aristas_unicas(forma):
    mapa = IndexedMap_TopoDS_Shape_TopTools_ShapeMapHasher()
    TopExp.MapShapes_s(forma, TopAbs_EDGE, mapa)
    return [TopoDS.Edge(mapa.FindKey(i)) for i in range(1, mapa.Size() + 1)]


def _puntos_arista(arista, deflexion, angular=0.15):
    curva = BRepAdaptor_Curve(arista)
    if curva.GetType() == GeomAbs_Line:
        pts = [curva.Value(curva.FirstParameter()), curva.Value(curva.LastParameter())]
    else:
        d = GCPnts_TangentialDeflection(curva, angular, deflexion)
        pts = [d.Value(i) for i in range(1, d.NbPoints() + 1)]
    arr = np.array([[p.X(), p.Y(), p.Z()] for p in pts], float)
    return arr[::-1] if arista.Orientation() == TopAbs_REVERSED else arr


def _polilineas(compuesto, deflexion):
    if compuesto is None or compuesto.IsNull():
        return []
    salida = []
    ex = TopExp_Explorer(compuesto, TopAbs_EDGE)
    while ex.More():
        arista = TopoDS.Edge(ex.Current())
        ex.Next()
        if BRep_Tool.Degenerated_s(arista):
            continue
        try:
            p = _puntos_arista(arista, deflexion)[:, :2]
        except Exception:  # noqa: BLE001 — una arista rara del HLR se omite, no tumba la vista
            continue
        if len(p) >= 2 and np.abs(np.diff(p, axis=0)).sum() > 1e-9:
            salida.append(p)
    return salida


def _distancia_a_segmentos(p, a, b):
    """Distancia de cada punto p (k, 2) al conjunto de segmentos a→b (m, 2): array (k,)."""
    d = b - a
    largo2 = (d * d).sum(1)
    largo2[largo2 == 0] = 1.0
    rel = p[:, None, :] - a[None]
    t = np.clip((rel * d[None]).sum(2) / largo2, 0.0, 1.0)
    return np.linalg.norm(rel - t[..., None] * d[None], axis=2).min(1)


def _quitar_superpuestas(ocultas, visibles, tol):
    """Tramos ocultos que caen sobre una arista visible: no se dibujan (Fusion no los muestra)."""
    if not ocultas or not visibles:
        return ocultas
    a = np.concatenate([v[:-1] for v in visibles])
    b = np.concatenate([v[1:] for v in visibles])
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    salida = []
    for pl in ocultas:
        cmin, cmax = pl.min(0) - tol, pl.max(0) + tol
        sel = np.all(hi >= cmin, axis=1) & np.all(lo <= cmax, axis=1)
        if not sel.any():
            salida.append(pl)
            continue
        muestras = np.concatenate([pl[:-1], (pl[:-1] + pl[1:]) / 2, pl[1:]])
        cubierto = _distancia_a_segmentos(muestras, a[sel], b[sel]) <= tol
        n = len(pl) - 1
        tapado = cubierto[:n] & cubierto[n:2 * n] & cubierto[2 * n:]
        actual = None
        for i in range(n):
            if tapado[i]:
                actual = None
                continue
            if actual is None:
                actual = [pl[i]]
                salida.append(actual)
            actual.append(pl[i + 1])
    return [np.asarray(s) for s in salida]


def proyectar(forma, marco, metodo="exacto", deflexion=None):
    """Proyección con eliminación de líneas ocultas: {categoría: [arrays Kx2]} en mm del modelo.

    Categorías: visibles, silueta, tangentes (aristas suaves), ocultas, silueta_oculta, tangentes_ocultas.
    metodo="exacto" usa HLRBRep_Algo; "rapido" usa HLRBRep_PolyAlgo sobre el teselado (más veloz en piezas
    complejas, aristas curvas poligonales)."""
    vacio = {c: [] for c in CATEGORIAS}
    if forma is None or geo.esta_vacia(forma):
        return vacio
    caja = geo.caja_envolvente(forma)
    diag = float(np.linalg.norm(np.subtract(caja[1], caja[0]))) if caja else 1.0
    deflexion = deflexion or max(diag * 2e-4, 1e-3)
    proyector = HLRAlgo_Projector(marco.ax2())
    try:
        if metodo == "rapido":
            BRepMesh_IncrementalMesh(forma, deflexion * 5, False, 0.3, True)
            algo = HLRBRep_PolyAlgo()
            algo.Load(forma)
            algo.Projector(proyector)
            algo.Update()
            conv = HLRBRep_PolyHLRToShape()
            conv.Update(algo)
        else:
            algo = HLRBRep_Algo()
            algo.Add(forma)
            algo.Projector(proyector)
            algo.Update()
            algo.Hide()
            conv = HLRBRep_HLRToShape(algo)
        salida = {c: _polilineas(getattr(conv, n)(), deflexion) for c, n in _COMPUESTOS.items()}
    except Exception as e:  # noqa: BLE001
        raise geo.ErrorGeometria(f"No se pudo proyectar la vista: {e}") from e
    tol = max(diag * 1e-5, 1e-5)
    visibles = salida["visibles"] + salida["silueta"] + salida["tangentes"]
    for c in ("ocultas", "silueta_oculta", "tangentes_ocultas"):
        salida[c] = _quitar_superpuestas(salida[c], visibles, tol)
    return salida


def caja_2d(polilineas):
    """(xmin, ymin, xmax, ymax) de una lista de arrays Kx2 (None si está vacía)."""
    if not polilineas:
        return None
    todo = np.concatenate(polilineas)
    return (*todo.min(0).tolist(), *todo.max(0).tolist())


# ---------------------------------------------------------------- ejes y marcas de centro
def circulos_de_frente(forma, marco):
    """Aristas circulares vistas de frente (eje paralelo a la mirada): [(centro 2D, radio, completo)].

    `completo` = la circunferencia cierra 360° a una misma profundidad (agujero o redondo, no un empalme)."""
    grupos = {}
    for arista in _aristas_unicas(forma):
        curva = BRepAdaptor_Curve(arista)
        if curva.GetType() != GeomAbs_Circle:
            continue
        circ = curva.Circle()
        d = circ.Axis().Direction()
        if abs(abs(d.X() * marco.e[0] + d.Y() * marco.e[1] + d.Z() * marco.e[2]) - 1.0) > 1e-6:
            continue
        p = circ.Location()
        c3 = np.array([p.X(), p.Y(), p.Z()])
        c2 = marco.a_2d(c3)
        clave = (round(c2[0], 4), round(c2[1], 4), round(circ.Radius(), 4), round(float(c3 @ marco.e), 4))
        grupos[clave] = grupos.get(clave, 0.0) + abs(curva.LastParameter() - curva.FirstParameter())
    circulos = {}
    for (x, y, r, _prof), giro in grupos.items():
        completo = giro >= 2 * math.pi - 1e-6
        clave = (x, y, r)
        circulos[clave] = circulos.get(clave, False) or completo
    return [(np.array([x, y]), r, completo) for (x, y, r), completo in sorted(circulos.items())]


def ejes_de_cilindros(forma, marco):
    """Ejes de caras cilíndricas vistas de costado (agujeros, redondos): [(p0 2D, p1 2D)]. Solo cilindros de
    al menos media vuelta (un empalme no lleva eje). Ejes colineales se unen."""
    lineas = {}
    for cara in geo.caras(forma):
        sup = BRepAdaptor_Surface(cara)
        if sup.GetType() != GeomAbs_Cylinder:
            continue
        eje = sup.Cylinder().Axis()
        d = np.array([eje.Direction().X(), eje.Direction().Y(), eje.Direction().Z()])
        if abs(float(d @ marco.e)) > 1e-6:
            continue
        umin, umax, vmin, vmax = BRepTools.UVBounds_s(cara)
        if umax - umin < math.pi - 1e-6:
            continue
        o = np.array([eje.Location().X(), eje.Location().Y(), eje.Location().Z()])
        a, b = marco.a_2d(o + d * vmin), marco.a_2d(o + d * vmax)
        u = _unit(b - a)
        if u[0] < -1e-9 or (abs(u[0]) <= 1e-9 and u[1] < 0):
            u = -u
        normal = np.array([-u[1], u[0]])
        clave = (round(u[0], 5), round(u[1], 5), round(float(a @ normal), 4))
        ts = [float(a @ u), float(b @ u)]
        if clave in lineas:
            ts += lineas[clave][1]
        lineas[clave] = (normal * clave[2], [min(ts), max(ts)], u)
    return [(base + u * t0, base + u * t1) for base, (t0, t1), u in lineas.values()]


# ---------------------------------------------------------------- sección y detalle
def cortar_por_linea(forma, padre, p1, p2, lado=1):
    """Corte de una vista de sección (Section View): el plano contiene la línea p1→p2 (modelo 2D de la vista
    padre) y la dirección de mirada; se quita el material del lado del observador, que queda a la izquierda
    de p1→p2 con lado=+1 y a la derecha con lado=−1 (BRepAlgoAPI_Cut con un medio espacio).

    Devuelve (forma cortada, marco de la sección, (origen 3D, normal 3D del plano))."""
    p1, p2 = np.asarray(p1, float), np.asarray(p2, float)
    if np.linalg.norm(p2 - p1) < 1e-9:
        raise geo.ErrorGeometria("La línea de sección necesita dos puntos distintos.")
    t = _unit(p2 - p1)
    m = (1 if lado >= 0 else -1) * np.array([-t[1], t[0]])
    origen = padre.a_3d(p1)
    normal = m[0] * padre.x + m[1] * padre.y
    cara = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(*map(float, origen)), gp_Dir(*map(float, normal)))).Face()
    medio = BRepPrimAPI_MakeHalfSpace(cara, gp_Pnt(*map(float, origen + normal))).Solid()
    corte = BRepAlgoAPI_Cut(forma, medio)
    if not corte.IsDone():
        raise geo.ErrorGeometria("El corte de la vista de sección falló en el kernel.")
    return corte.Shape(), _marco_girado(padre, m, 1), (origen, normal)


def _lazo(cable, cara, deflexion):
    pts = []
    ex = BRepTools_WireExplorer(cable, cara)
    while ex.More():
        arista = ex.Current()
        ex.Next()
        if BRep_Tool.Degenerated_s(arista):
            continue
        p = _puntos_arista(arista, deflexion)
        if pts and np.linalg.norm(pts[-1][-1] - p[0]) < 1e-7:
            p = p[1:]
        pts.append(p)
    return np.concatenate(pts) if pts else np.zeros((0, 3))


def caras_de_corte(forma_cortada, plano, marco, deflexion=0.01):
    """Caras que quedaron sobre el plano de corte (las que se rayan): [[lazo 2D, ...] por cara]."""
    origen, normal = plano
    regiones = []
    for cara in geo.caras(forma_cortada):
        sup = BRepAdaptor_Surface(cara)
        if sup.GetType() != GeomAbs_Plane:
            continue
        pln = sup.Plane()
        d, loc = pln.Axis().Direction(), pln.Location()
        if abs(abs(d.X() * normal[0] + d.Y() * normal[1] + d.Z() * normal[2]) - 1.0) > 1e-7:
            continue
        if abs(float((np.array([loc.X(), loc.Y(), loc.Z()]) - origen) @ normal)) > 1e-6:
            continue
        lazos = []
        ex = TopExp_Explorer(cara, TopAbs_WIRE)
        while ex.More():
            lazo = _lazo(TopoDS.Wire(ex.Current()), cara, deflexion)
            ex.Next()
            if len(lazo) >= 3:
                lazos.append(marco.a_2d(lazo))
        if lazos:
            regiones.append(lazos)
    return regiones


def area_lazo(lazo):
    """Área con signo (fórmula del zapatero) de un lazo cerrado Kx2."""
    x, y = lazo[:, 0], lazo[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def rayado(lazos, angulo=45.0, paso=1.0):
    """Rayado de una región (Hatch, patrón ANSI31): array (n, 2, 2) de segmentos. Regla par-impar entre los
    lazos (los agujeros quedan sin rayar); las líneas pasan por múltiplos de `paso` desde el origen, así dos
    regiones vecinas quedan alineadas."""
    if not lazos or paso <= 0:
        return np.zeros((0, 2, 2))
    a = math.radians(angulo)
    c, s = math.cos(a), math.sin(a)
    pa = np.concatenate([np.asarray(lz, float) for lz in lazos])
    pb = np.concatenate([np.roll(np.asarray(lz, float), -1, axis=0) for lz in lazos])
    ua, va = pa @ (c, s), pa @ (-s, c)
    ub, vb = pb @ (c, s), pb @ (-s, c)
    segmentos = []
    for k in range(math.ceil(va.min() / paso), math.floor(va.max() / paso) + 1):
        v = k * paso
        cruza = (va <= v) != (vb <= v)
        if not cruza.any():
            continue
        t = (v - va[cruza]) / (vb[cruza] - va[cruza])
        u = np.sort(ua[cruza] + t * (ub[cruza] - ua[cruza]))
        for u0, u1 in zip(u[0::2], u[1::2], strict=False):
            if u1 - u0 > 1e-9:
                segmentos.append([[u0 * c - v * s, u0 * s + v * c], [u1 * c - v * s, u1 * s + v * c]])
    return np.array(segmentos, float).reshape(-1, 2, 2)


def _intervalo_en_circulo(a, b, c, r):
    d = b - a
    qa = float(d @ d)
    if qa < 1e-18:
        return None
    f = a - c
    qb, qc = 2 * float(d @ f), float(f @ f) - r * r
    disc = qb * qb - 4 * qa * qc
    if disc <= 0:
        return None
    raiz = math.sqrt(disc)
    t0, t1 = max(0.0, (-qb - raiz) / (2 * qa)), min(1.0, (-qb + raiz) / (2 * qa))
    return (t0, t1) if t1 - t0 > 1e-12 else None


def recortar_a_circulo(polilineas, centro, radio):
    """Partes de las polilíneas dentro de un círculo (borde de la vista de detalle)."""
    c = np.asarray(centro, float)
    salida = []
    for pl in polilineas:
        actual = None
        for a, b in zip(pl[:-1], pl[1:], strict=True):
            iv = _intervalo_en_circulo(a, b, c, radio)
            if iv is None:
                actual = None
                continue
            pa, pb = a + iv[0] * (b - a), a + iv[1] * (b - a)
            if actual is None or np.linalg.norm(actual[-1] - pa) > 1e-9:
                actual = [pa]
                salida.append(actual)
            actual.append(pb)
            if iv[1] < 1.0:
                actual = None
    return [np.asarray(s) for s in salida]


def _acortar(pl, fraccion=0.15):
    """Arista tangente acortada (Tangent Edges: Shortened): se quita `fraccion` del largo en cada punta."""
    tramos = np.linalg.norm(np.diff(pl, axis=0), axis=1)
    acum = np.concatenate([[0.0], np.cumsum(tramos)])
    total = acum[-1]
    if total < 1e-9:
        return pl
    t = np.linspace(total * fraccion, total * (1 - fraccion), max(2, len(pl)))
    return np.stack([np.interp(t, acum, pl[:, 0]), np.interp(t, acum, pl[:, 1])], axis=1)


# ---------------------------------------------------------------- anotaciones (coordenadas de hoja)
def _p(v):
    return (float(v[0]), float(v[1]))


def _texto(p, texto, altura=ALTURA_TEXTO, rotacion=0.0, alineacion="centro", capa="COTAS"):
    return (capa, ("texto", _p(p), float(altura), str(texto), float(rotacion), alineacion))


def _flecha(punta, direccion, capa="COTAS"):
    """Punta de flecha rellena; `direccion` es hacia donde apunta."""
    d = _unit(direccion)
    n = np.array([-d[1], d[0]])
    base = np.asarray(punta, float) - d * FLECHA
    return (capa, ("solido", [_p(punta), _p(base + n * MEDIA_FLECHA), _p(base - n * MEDIA_FLECHA)]))


def _linea(a, b, capa="COTAS"):
    return (capa, ("linea", _p(a), _p(b)))


def _rotacion_legible(u):
    """Ángulo (grados) del texto paralelo a u, sin quedar cabeza abajo; y la normal "arriba" del texto."""
    ang = math.degrees(math.atan2(u[1], u[0]))
    if ang > 90.0 + 1e-6 or ang <= -90.0 + 1e-6:
        ang += 180.0 if ang <= 0 else -180.0
    r = math.radians(ang)
    return ang, np.array([-math.sin(r), math.cos(r)])


def ancho_texto(texto, altura=ALTURA_TEXTO):
    """Ancho aproximado de un texto (para cajas de selección y tablas)."""
    return 0.72 * altura * max(1, len(str(texto)))


def dibujar_cota_lineal(p1, p2, lugar, texto, modo="alineada"):
    """Cota lineal horizontal, vertical o alineada (Linear / Aligned Dimension) con líneas de referencia."""
    p1, p2, lugar = (np.asarray(v, float) for v in (p1, p2, lugar))
    if modo == "horizontal":
        u = np.array([1.0, 0.0]) if p2[0] >= p1[0] else np.array([-1.0, 0.0])
    elif modo == "vertical":
        u = np.array([0.0, 1.0]) if p2[1] >= p1[1] else np.array([0.0, -1.0])
    else:
        u = _unit(p2 - p1)
    n = np.array([-u[1], u[0]])
    a = p1 + n * float((lugar - p1) @ n)
    b = p2 + n * float((lugar - p2) @ n)
    prims = []
    for p, q in ((p1, a), (p2, b)):
        lado = float((q - p) @ n)
        if abs(lado) > HUECO_EXT:
            s = math.copysign(1.0, lado)
            prims.append(_linea(p + n * s * HUECO_EXT, q + n * s * EXCESO_EXT))
    largo = float(np.linalg.norm(b - a))
    if largo < 1e-9:
        return prims
    d = (b - a) / largo
    if largo >= 2 * FLECHA + 1.0:
        prims += [_linea(a, b), _flecha(a, -d), _flecha(b, d)]
    else:   # cota chica: flechas por fuera
        prims += [_linea(a - d * 2 * FLECHA, b + d * 2 * FLECHA), _flecha(a, d), _flecha(b, -d)]
    rot, arriba = _rotacion_legible(d)
    prims.append(_texto((a + b) / 2 + arriba * 1.0, texto, rotacion=rot))
    return prims


def dibujar_cota_radial(centro, radio, lugar, texto, diametro=False):
    """Cota de radio (R) o de diámetro (⌀) con quiebre horizontal hacia el texto (Radius / Diameter)."""
    c, lugar = np.asarray(centro, float), np.asarray(lugar, float)
    dv = lugar - c
    u = _unit(dv) if np.linalg.norm(dv) > 1e-9 else np.array([1.0, 0.0])
    borde = c + u * radio
    fin = lugar if np.linalg.norm(dv) > radio else borde
    inicio = c - u * radio if diametro else c
    prims = [_linea(inicio, fin), _flecha(borde, u)]
    if diametro:
        prims.append(_flecha(c - u * radio, -u))
    s = 1.0 if u[0] >= 0 else -1.0
    ancho = ancho_texto(texto)
    prims.append(_linea(fin, fin + np.array([s * (ancho + 1.0), 0.0])))
    prims.append(_texto(fin + np.array([s * 0.5, 1.0]), texto, alineacion="izq" if s > 0 else "der"))
    return prims


def interseccion_rectas(a0, a1, b0, b1):
    """Punto de corte de las rectas a0a1 y b0b1 (None si son paralelas)."""
    a0, a1, b0, b1 = (np.asarray(v, float) for v in (a0, a1, b0, b1))
    da, db = a1 - a0, b1 - b0
    den = da[0] * db[1] - da[1] * db[0]
    if abs(den) < 1e-12 * max(1.0, float(np.linalg.norm(da) * np.linalg.norm(db))):
        return None
    t = ((b0[0] - a0[0]) * db[1] - (b0[1] - a0[1]) * db[0]) / den
    return a0 + t * da


def sector_angular(a0, a1, b0, b1, lugar):
    """(vértice, ángulo inicial, barrido) en radianes del ángulo entre dos aristas que contiene a `lugar`."""
    v = interseccion_rectas(a0, a1, b0, b1)
    if v is None:
        raise geo.ErrorGeometria("Las aristas son paralelas: no forman un ángulo.")
    dos_pi = 2 * math.pi
    aq = math.atan2(lugar[1] - v[1], lugar[0] - v[0]) % dos_pi
    rayos = []
    for p, q in ((a0, a1), (b0, b1)):
        ang = math.atan2(q[1] - p[1], q[0] - p[0])
        rayos += [ang % dos_pi, (ang + math.pi) % dos_pi]
    rayos.sort()
    # las dos rectas parten el plano en 4 sectores: el de la cota es el que contiene al cursor
    for i, inicio in enumerate(rayos):
        fin = rayos[(i + 1) % 4] + (dos_pi if i == 3 else 0.0)
        if inicio <= aq < fin or inicio <= aq + dos_pi < fin:
            return v, inicio, fin - inicio
    return v, rayos[0], (rayos[1] - rayos[0]) % dos_pi


def dibujar_cota_angular(a0, a1, b0, b1, lugar, texto=None, decimales=1):
    """Cota angular entre dos aristas (Angular Dimension): arco por `lugar`. Devuelve (primitivas, grados)."""
    lugar = np.asarray(lugar, float)
    v, t1, barrido = sector_angular(a0, a1, b0, b1, lugar)
    r = max(float(np.linalg.norm(lugar - v)), 1e-6)
    t2 = t1 + barrido
    grados = math.degrees(barrido)
    texto = texto if texto is not None else formatear(grados, decimales) + "°"
    prims = [("COTAS", ("arco", _p(v), r, t1, t2))]
    da = _unit(np.asarray(a1, float) - np.asarray(a0, float))
    for t, signo in ((t1, -1.0), (t2, 1.0)):
        dirr = np.array([math.cos(t), math.sin(t)])
        seg = (a0, a1) if abs(dirr[0] * da[1] - dirr[1] * da[0]) < 1e-6 else (b0, b1)
        punta = v + dirr * r
        prims.append(_flecha(punta, signo * np.array([-dirr[1], dirr[0]])))
        alcance = max(float((np.asarray(p, float) - v) @ dirr) for p in seg)
        if r > alcance + HUECO_EXT:
            prims.append(_linea(v + dirr * (alcance + HUECO_EXT), v + dirr * (r + EXCESO_EXT)))
    medio = t1 + barrido / 2
    dm = np.array([math.cos(medio), math.sin(medio)])
    rot, _ = _rotacion_legible(np.array([-dm[1], dm[0]]))
    prims.append(_texto(v + dm * (r + 1.0), texto, rotacion=rot))
    return prims, grados


def dibujar_cota_ordenada(punto, lugar, texto, eje="x"):
    """Cota de ordenadas (Ordinate Dimension): directriz desde el punto y el valor en su punta."""
    p, lugar = np.asarray(punto, float), np.asarray(lugar, float)
    i = 1 if eje == "x" else 0          # eje x: la directriz es vertical
    s = 1.0 if lugar[i] >= p[i] else -1.0
    inicio, fin = p.copy(), p.copy()
    inicio[i] += s * HUECO_EXT
    fin[i] = lugar[i]
    prims = [_linea(inicio, fin)] if abs(fin[i] - inicio[i]) > 1e-9 else []
    alin = "izq" if s > 0 else "der"
    if eje == "x":
        prims.append(_texto(fin + np.array([ALTURA_TEXTO / 2, s * 0.8]), texto, rotacion=90.0, alineacion=alin))
    else:
        prims.append(_texto(fin + np.array([s * 0.8, -ALTURA_TEXTO / 2]), texto, alineacion=alin))
    return prims


def dibujar_marca_centro(centro, radio):
    """Marca de centro (Center Mark): cruz de líneas de centro que sobrepasa la circunferencia."""
    c = np.asarray(centro, float)
    largo = radio + SOBREPASO_EJE
    return [_linea(c - (largo, 0), c + (largo, 0), "CENTRO"), _linea(c - (0, largo), c + (0, largo), "CENTRO")]


def dibujar_linea_centro(p0, p1):
    """Línea de centro (Center Line) entre dos puntos, prolongada SOBREPASO_EJE en cada punta."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    if np.linalg.norm(p1 - p0) < 1e-9:
        return []
    u = _unit(p1 - p0)
    return [_linea(p0 - u * SOBREPASO_EJE, p1 + u * SOBREPASO_EJE, "CENTRO")]


def dibujar_nota(flecha, posicion, texto):
    """Nota con directriz (Leader): flecha, directriz, quiebre horizontal y texto."""
    f, p = np.asarray(flecha, float), np.asarray(posicion, float)
    prims = []
    if np.linalg.norm(p - f) > 1e-6:
        prims += [_linea(f, p, "TEXTO"), _flecha(f, f - p, "TEXTO")]
    s = 1.0 if p[0] >= f[0] else -1.0
    prims.append(_linea(p, p + (s * 2.0, 0), "TEXTO"))
    x = p[0] + s * 3.0
    for i, t in enumerate(str(texto).split("\n")):
        prims.append(_texto((x, p[1] - ALTURA_TEXTO / 2 - i * ALTURA_TEXTO * 1.6), t,
                            alineacion="izq" if s > 0 else "der", capa="TEXTO"))
    return prims


def dibujar_globo(punto, posicion, numero, radio=4.0):
    """Globo (Balloon): círculo con el número del elemento y directriz con flecha hasta la pieza."""
    q, c = np.asarray(punto, float), np.asarray(posicion, float)
    prims = [("TABLAS", ("circulo", _p(c), float(radio)))]
    if np.linalg.norm(q - c) > radio + 1e-6:
        borde = c + _unit(q - c) * radio
        prims += [_linea(borde, q, "TABLAS"), _flecha(q, q - c, "TABLAS")]
    prims.append(_texto((c[0], c[1] - ALTURA_TEXTO / 2), numero, capa="TABLAS"))
    return prims


def dibujar_tabla(posicion, filas, alto_fila=7.0, hacia_arriba=False):
    """Tabla (lista de piezas): `filas` = [encabezado, fila1, …]; `posicion` = esquina superior izquierda
    (inferior izquierda si hacia_arriba, con el encabezado abajo, como Fusion en la mitad inferior de la hoja)."""
    if not filas:
        return []
    ncol = max(len(f) for f in filas)
    anchos = [max(ancho_texto(f[i] if i < len(f) else "") for f in filas) + 4.0 for i in range(ncol)]
    x0, y0 = float(posicion[0]), float(posicion[1])
    total_x, total_y = sum(anchos), alto_fila * len(filas)
    s = 1.0 if hacia_arriba else -1.0
    prims = [("TABLAS", ("polilinea", [(x0, y0), (x0 + total_x, y0), (x0 + total_x, y0 + s * total_y),
                                       (x0, y0 + s * total_y)], True))]
    for k in range(1, len(filas)):
        prims.append(_linea((x0, y0 + s * k * alto_fila), (x0 + total_x, y0 + s * k * alto_fila), "TABLAS"))
    x = x0
    for a in anchos[:-1]:
        x += a
        prims.append(_linea((x, y0), (x, y0 + s * total_y), "TABLAS"))
    for k, fila in enumerate(filas):
        y_centro = y0 + s * (k + 0.5) * alto_fila
        x = x0
        for i, celda in enumerate(fila):
            prims.append(_texto((x + anchos[i] / 2, y_centro - 2.5 / 2), celda, altura=2.5, capa="TABLAS"))
            x += anchos[i]
    return prims


# ---------------------------------------------------------------- hoja: marco, zonas y cajetín
def dibujar_marco(ancho, alto, tamano):
    """Borde de la hoja con zonas numeradas (columnas) y con letras (filas), como el Border de Fusion."""
    nh, nv = ZONAS_HOJA.get(tamano, (max(2, 2 * round(ancho / 100)), max(2, 2 * round(alto / 100))))
    if alto > ancho and tamano in ZONAS_HOJA:
        nh, nv = nv, nh
    m, e = MARGEN, MARGEN / 2
    prims = [("MARCO", ("polilinea", [(m, m), (ancho - m, m), (ancho - m, alto - m), (m, alto - m)], True)),
             ("CAJETIN", ("polilinea", [(e, e), (ancho - e, e), (ancho - e, alto - e), (e, alto - e)], True))]
    paso_x, paso_y = (ancho - 2 * m) / nh, (alto - 2 * m) / nv
    for i in range(nh):
        x = m + (i + 0.5) * paso_x
        for y in (e + 1.25, alto - e - 3.75):
            prims.append(_texto((x, y), str(i + 1), altura=2.5, capa="CAJETIN"))
        if i:
            xx = m + i * paso_x
            prims += [_linea((xx, e), (xx, m), "CAJETIN"), _linea((xx, alto - m), (xx, alto - e), "CAJETIN")]
    for j in range(nv):
        y = alto - m - (j + 0.5) * paso_y - 1.25
        letra = chr(ord("A") + j % 26)
        for x in (e + 2.5, ancho - e - 2.5):
            prims.append(_texto((x, y), letra, altura=2.5, capa="CAJETIN"))
        if j:
            yy = alto - m - j * paso_y
            prims += [_linea((e, yy), (m, yy), "CAJETIN"), _linea((ancho - m, yy), (ancho - e, yy), "CAJETIN")]
    return prims


def caja_cajetin(ancho, alto):
    """(x0, y0, x1, y1) del cajetín: abajo a la derecha, apoyado en el marco."""
    x1, y0 = ancho - MARGEN, MARGEN
    return (x1 - ANCHO_CAJETIN, y0, x1, y0 + ALTO_CAJETIN)


def _simbolo_diedro(cx, cy, diedro):
    """Símbolo de proyección (ISO 5456-2): tronco de cono visto de frente y de costado."""
    # El cono tiene la punta chica a la izquierda. 1.er diedro: la vista desde la izquierda (círculos) va a la
    # derecha del trapecio; 3.er diedro: va a su izquierda.
    d_mayor, d_menor, largo, sep = 7.0, 3.5, 7.0, 3.0
    x = cx - (largo + sep + d_mayor) / 2
    if diedro == "tercero":
        x_circ, xa = x + d_mayor / 2, x + d_mayor + sep
    else:
        xa, x_circ = x, x + largo + sep + d_mayor / 2
    xb = xa + largo
    trap = [(xa, cy - d_menor / 2), (xb, cy - d_mayor / 2), (xb, cy + d_mayor / 2), (xa, cy + d_menor / 2)]
    return [("CAJETIN", ("polilinea", trap, True)),
            ("CAJETIN", ("circulo", (x_circ, cy), d_mayor / 2)),
            ("CAJETIN", ("circulo", (x_circ, cy), d_menor / 2)),
            _linea((xa - 1.5, cy), (xb + 1.5, cy), "CENTRO"),
            _linea((x_circ - d_mayor / 2 - 1.5, cy), (x_circ + d_mayor / 2 + 1.5, cy), "CENTRO"),
            _linea((x_circ, cy - d_mayor / 2 - 1.5), (x_circ, cy + d_mayor / 2 + 1.5), "CENTRO")]


CAMPOS_CAJETIN = {"titulo": "Título", "numero_pieza": "Nº de pieza", "autor": "Dibujó", "fecha": "Fecha",
                  "escala": "Escala", "hoja": "Hoja", "tamano": "Tamaño", "material": "Material",
                  "proyeccion": "Proyección"}


def dibujar_cajetin(ancho, alto, campos, diedro="primero"):
    """Cajetín (Title block) con los atributos de Fusion: Title, Part Number, Drawn By, Drawn Date, Drawing
    Scale, Sheet Number, Paper Size, Material y el símbolo del diedro."""
    x0, y0, x1, y1 = caja_cajetin(ancho, alto)
    filas = [  # (alto de fila, [(campo, ancho)]) de arriba hacia abajo
        (14.0, [("titulo", 125.0), ("numero_pieza", 55.0)]),
        (11.0, [("autor", 55.0), ("fecha", 40.0), ("escala", 30.0), ("hoja", 30.0), ("tamano", 25.0)]),
        (11.0, [("material", 125.0), ("proyeccion", 55.0)])]
    prims = [("CAJETIN", ("polilinea", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True))]
    y = y1
    for alto_fila, celdas in filas:
        if y < y1:
            prims.append(_linea((x0, y), (x1, y), "CAJETIN"))
        x = x0
        for campo, ancho_celda in celdas:
            if x > x0:
                prims.append(_linea((x, y), (x, y - alto_fila), "CAJETIN"))
            prims.append(_texto((x + 1.2, y - 2.6), CAMPOS_CAJETIN[campo], altura=1.8, alineacion="izq",
                                capa="CAJETIN"))
            if campo == "proyeccion":
                prims += _simbolo_diedro(x + ancho_celda / 2 + 6.0, y - alto_fila / 2 - 0.8, diedro)
                prims.append(_texto((x + 2.0, y - alto_fila + 2.0), "ISO E" if diedro == "primero" else "ISO A",
                                    altura=1.8, alineacion="izq", capa="CAJETIN"))
            else:
                h = 5.0 if campo == "titulo" else ALTURA_TEXTO
                valor = str(campos.get(campo, "") or "")
                maximo = max(1, int((ancho_celda - 3) / (0.72 * h)))
                if len(valor) > maximo:
                    valor = valor[:maximo - 1] + "…"
                prims.append(_texto((x + 2.0, y - alto_fila + 2.4), valor, altura=h, alineacion="izq",
                                    capa="CAJETIN"))
            x += ancho_celda
        y -= alto_fila
    return prims


# ---------------------------------------------------------------- modelo del dibujo
def _iguales(a, b):
    """Compara firmas que contienen formas OCC (IsEqual) y números/arrays."""
    if isinstance(a, TopoDS_Shape) or isinstance(b, TopoDS_Shape):
        return isinstance(a, TopoDS_Shape) and isinstance(b, TopoDS_Shape) and a.IsEqual(b)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_iguales(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return np.shape(a) == np.shape(b) and bool(np.allclose(a, b))
    return a == b


def _lista(v):
    return None if v is None else np.asarray(v, float).tolist()


class Vista:
    """Vista de dibujo. Datos persistentes en CAMPOS; el resto es geometría calculada."""
    CAMPOS = ("id", "tipo", "padre", "cuerpos", "orientacion", "direccion", "escala", "posicion", "rotacion",
              "estilo", "tangentes", "marcas_centro", "etiqueta", "linea", "lado", "centro_detalle",
              "radio_detalle")

    def __init__(self, id, tipo, **datos):
        self.id, self.tipo = id, tipo
        self.padre = datos.get("padre")
        self.cuerpos = list(datos.get("cuerpos") or [])
        self.orientacion = datos.get("orientacion", "frontal")
        self.direccion = tuple(datos["direccion"]) if datos.get("direccion") is not None else None
        self.escala = float(datos.get("escala") or 1.0)
        self.posicion = np.asarray(datos.get("posicion", (100.0, 100.0)), float)
        self.rotacion = float(datos.get("rotacion", 0.0))
        self.estilo = datos.get("estilo")
        self.tangentes = datos.get("tangentes", "completas")
        self.marcas_centro = bool(datos.get("marcas_centro", True))
        self.etiqueta = datos.get("etiqueta", "")
        self.linea = np.asarray(datos["linea"], float) if datos.get("linea") is not None else None
        self.lado = int(datos.get("lado", 1))
        self.centro_detalle = (np.asarray(datos["centro_detalle"], float)
                               if datos.get("centro_detalle") is not None else None)
        self.radio_detalle = float(datos.get("radio_detalle") or 0.0)
        # calculado
        self.marco = None
        self.lineas = {c: [] for c in CATEGORIAS}
        self.rayado = np.zeros((0, 2, 2))
        self.regiones = []
        self.circulos = []
        self.ejes = []
        self.centro = np.zeros(2)
        self.caja = None
        self.error = ""

    def a_dict(self):
        d = {}
        for k in self.CAMPOS:
            v = getattr(self, k)
            d[k] = _lista(v) if isinstance(v, np.ndarray) else (list(v) if isinstance(v, tuple) else v)
        return d

    def _rot(self):
        r = math.radians(self.rotacion)
        return np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])

    def a_hoja(self, puntos):
        p = np.asarray(puntos, float)
        return self.posicion + self.escala * ((p - self.centro) @ self._rot().T)

    def de_hoja(self, puntos):
        p = np.asarray(puntos, float)
        return self.centro + ((p - self.posicion) / self.escala) @ self._rot()

    def caja_hoja(self, margen=2.0):
        """(x0, y0, x1, y1) de la vista en la hoja."""
        if self.caja is None:
            c = self.posicion
            return (c[0] - 10, c[1] - 10, c[0] + 10, c[1] + 10)
        x0, y0, x1, y1 = self.caja
        esq = self.a_hoja([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        lo, hi = esq.min(0) - margen, esq.max(0) + margen
        return (*lo.tolist(), *hi.tolist())


class Dibujo:
    """Plano de varias vistas y anotaciones sobre una hoja (documento de dibujo de Fusion, una hoja)."""

    def __init__(self, tamano="A3", orientacion="horizontal", norma="ISO"):
        tamano_hoja(tamano, orientacion)
        self.tamano, self.orientacion, self.norma = tamano, orientacion, norma
        self.diedro = "primero" if norma == "ISO" else "tercero"
        self.cajetin = {"titulo": "", "numero_pieza": "", "autor": "", "material": "", "hoja": "1 / 1",
                        "fecha": datetime.date.today().strftime("%d/%m/%Y"), "escala": ""}
        self.metodo = "exacto"
        self.vistas = []          # en orden de dependencia: una padre siempre antes que sus hijas
        self.anotaciones = []     # dicts serializables (coordenadas del modelo 2D si tienen "vista")
        self.contador = 0
        self._formas, self._nombres, self._cache = {}, {}, {}

    # ------------------------------------------------------------ consultas
    @property
    def ancho(self):
        return tamano_hoja(self.tamano, self.orientacion)[0]

    @property
    def alto(self):
        return tamano_hoja(self.tamano, self.orientacion)[1]

    def area_util(self):
        """(x0, y0, x1, y1) del área de dibujo dentro del marco, sin la franja del cajetín."""
        return (MARGEN, MARGEN + ALTO_CAJETIN, self.ancho - MARGEN, self.alto - MARGEN)

    def vista(self, vid):
        for v in self.vistas:
            if v.id == vid:
                return v
        raise geo.ErrorGeometria(f"No existe la vista '{vid}'.")

    def anotacion(self, aid):
        for a in self.anotaciones:
            if a["id"] == aid:
                return a
        raise geo.ErrorGeometria(f"No existe la anotación '{aid}'.")

    def hijas(self, vid):
        return [v for v in self.vistas if v.padre == vid]

    def raiz(self, v):
        while v.padre is not None:
            v = self.vista(v.padre)
        return v

    def estilo_efectivo(self, v):
        while v.estilo is None and v.padre is not None:
            v = self.vista(v.padre)
        return v.estilo or "visibles"

    def _nuevo_id(self, prefijo):
        usados = {v.id for v in self.vistas} | {a["id"] for a in self.anotaciones}
        self.contador += 1
        while f"{prefijo}{self.contador}" in usados:
            self.contador += 1
        return f"{prefijo}{self.contador}"

    def _siguiente_etiqueta(self):
        usadas = {v.etiqueta for v in self.vistas}
        for k in range(26 * 27):
            letra = chr(ord("A") + k % 26) * (1 + k // 26)
            if letra[0] not in "IOQ" and letra not in usadas:
                return letra
        return "?"

    # ------------------------------------------------------------ cálculo
    def actualizar(self, formas, nombres=None):
        """Recalcula las vistas cuyo modelo cambió (Update drawing views). `formas` = {id de cuerpo: forma}.
        Devuelve True si alguna vista cambió."""
        self._formas = dict(formas)
        if nombres is not None:
            self._nombres = dict(nombres)
        cambio = False
        for v in self.vistas:
            cambio |= self._calcular(v)
        if cambio:
            for v in self.vistas:
                self._alinear(v)
        return cambio

    def _forma_de(self, v):
        raiz = self.raiz(v)
        formas = [self._formas[c] for c in raiz.cuerpos if c in self._formas]
        faltan = [c for c in raiz.cuerpos if c not in self._formas]
        if not formas:
            return None, faltan
        return (formas[0] if len(formas) == 1 else geo.compuesto(formas)), faltan

    def _firma(self, v):
        raiz = self.raiz(v)
        cuerpos = tuple((c, self._formas.get(c)) for c in raiz.cuerpos)
        # la escala solo cambia la geometría donde hay rayado (su paso es fijo en la hoja)
        escala = v.escala if v.tipo in ("seccion", "detalle") else None
        propia = (v.tipo, v.orientacion, v.direccion, _lista(v.linea), v.lado, _lista(v.centro_detalle),
                  v.radio_detalle, escala, self.diedro, self.metodo)
        padre = self._cache[v.padre][0] if v.padre in self._cache else None
        return (propia, cuerpos, padre)

    _GEOMETRIA = ("marco", "lineas", "rayado", "regiones", "circulos", "ejes", "centro", "caja", "error")

    def _calcular(self, v):
        firma = self._firma(v)
        anterior = self._cache.get(v.id)
        if anterior is not None and _iguales(anterior[0], firma):
            if v.marco is None:          # vista recién cargada (deshacer): toma la geometría de la caché
                for k, val in anterior[1].items():
                    setattr(v, k, val)
            return False
        v.error = ""
        v.lineas = {c: [] for c in CATEGORIAS}
        v.rayado, v.regiones, v.circulos, v.ejes = np.zeros((0, 2, 2)), [], [], []
        try:
            self._geometria(v)
        except geo.ErrorGeometria as e:
            v.error = str(e)
        todas = [p for c in CATEGORIAS for p in v.lineas[c]]
        if v.tipo == "detalle" and v.centro_detalle is not None:
            r = v.radio_detalle
            c = v.centro_detalle
            v.caja = (c[0] - r, c[1] - r, c[0] + r, c[1] + r)
            v.centro = c.copy()
        else:
            v.caja = caja_2d(todas)
            if v.caja is not None:
                v.centro = np.array([(v.caja[0] + v.caja[2]) / 2, (v.caja[1] + v.caja[3]) / 2])
        self._cache[v.id] = (firma, {k: getattr(v, k) for k in self._GEOMETRIA})
        return True

    def _geometria(self, v):
        if v.tipo == "base":
            v.marco = marco_orientacion(v.orientacion)
        elif v.tipo == "proyectada":
            v.marco = marco_proyectado(self.vista(v.padre).marco, v.direccion, self.diedro)
        elif v.tipo == "detalle":
            padre = self.vista(v.padre)
            v.marco = padre.marco
            c, r = v.centro_detalle, v.radio_detalle
            v.lineas = {k: recortar_a_circulo(ls, c, r) for k, ls in padre.lineas.items()}
            paso = PASO_RAYADO / v.escala
            segs = [s for reg in padre.regiones for s in rayado(reg, 45.0, paso)]
            v.rayado = np.array([s for s in recortar_a_circulo(segs, c, r) if len(s) == 2]).reshape(-1, 2, 2)
            v.circulos = [(cc, rr, comp) for cc, rr, comp in padre.circulos if np.linalg.norm(cc - c) < r]
            v.ejes = [(s[0], s[-1]) for s in recortar_a_circulo([np.array([a, b]) for a, b in padre.ejes], c, r)]
            return
        forma, faltan = self._forma_de(v)
        if forma is None:
            raise geo.ErrorGeometria("Los cuerpos de la vista ya no existen en el diseño.")
        if v.tipo == "seccion":
            padre = self.vista(v.padre)
            forma, v.marco, plano = cortar_por_linea(forma, padre.marco, v.linea[0], v.linea[1], v.lado)
            v.regiones = caras_de_corte(forma, plano, v.marco)
            paso = PASO_RAYADO / v.escala
            v.rayado = np.concatenate([rayado(reg, 45.0, paso) for reg in v.regiones]) if v.regiones \
                else np.zeros((0, 2, 2))
        v.lineas = proyectar(forma, v.marco, self.metodo)
        v.circulos = circulos_de_frente(forma, v.marco)
        v.ejes = ejes_de_cilindros(forma, v.marco)
        if faltan:
            v.error = "Faltan cuerpos del diseño: " + ", ".join(faltan)

    def _eje_alineacion(self, v):
        """Dirección de hoja en la que la vista se puede mover sin perder la alineación con la padre."""
        if v.tipo == "proyectada" and v.direccion and not (v.direccion[0] and v.direccion[1]):
            return np.array(v.direccion, float)
        if v.tipo == "seccion" and v.linea is not None:
            t = _unit(v.linea[1] - v.linea[0])
            return v.lado * np.array([-t[1], t[0]])
        return None

    def _alinear(self, v):
        """Proyectadas ortogonales y secciones quedan alineadas con su padre (como en Fusion)."""
        m = self._eje_alineacion(v)
        if m is None or v.padre is None:
            return
        padre = self.vista(v.padre)
        if padre.rotacion or v.rotacion:
            return
        p2d = np.array([-m[1], m[0]])
        r_padre = padre._rot()
        m_hoja = r_padre @ m
        p_hoja = r_padre @ p2d
        if abs(v.escala - padre.escala) < 1e-12:
            objetivo = float(padre.posicion @ p_hoja) + v.escala * float((v.centro - padre.centro) @ p2d)
        else:
            objetivo = float(padre.posicion @ p_hoja)
        v.posicion = m_hoja * float(v.posicion @ m_hoja) + p_hoja * objetivo

    def _alinear_descendientes(self, vid):
        for h in self.hijas(vid):
            self._alinear(h)
            self._alinear_descendientes(h.id)

    # ------------------------------------------------------------ crear vistas
    def agregar_vista_base(self, cuerpos, orientacion="frontal", posicion=None, escala=None,
                           estilo="visibles_ocultas", tangentes="completas", marcas_centro=True):
        """Vista base (Base View). Sin escala, se elige la normalizada que entra en el área útil."""
        if not cuerpos:
            raise geo.ErrorGeometria("Elegí al menos un cuerpo para la vista base.")
        marco_orientacion(orientacion)
        x0, y0, x1, y1 = self.area_util()
        if posicion is None:
            posicion = (x0 + (x1 - x0) * 0.3, y0 + (y1 - y0) * 0.62)
        v = Vista(self._nuevo_id("v"), "base", cuerpos=list(cuerpos), orientacion=orientacion,
                  posicion=posicion, escala=escala or 1.0, estilo=estilo, tangentes=tangentes,
                  marcas_centro=marcas_centro)
        self.vistas.append(v)
        self._calcular(v)
        if escala is None and v.caja is not None:
            v.escala = escala_automatica(v.caja[2] - v.caja[0], v.caja[3] - v.caja[1], x1 - x0, y1 - y0)
        return v

    def agregar_vista_proyectada(self, padre_id, posicion):
        """Vista proyectada (Projected View): la posición respecto de la padre elige la dirección."""
        padre = self.vista(padre_id)
        posicion = np.asarray(posicion, float)
        dx, dy = (posicion - padre.posicion) @ padre._rot()
        direccion = direccion_proyectada(dx, dy)
        iso = bool(direccion[0] and direccion[1])
        v = Vista(self._nuevo_id("v"), "proyectada", padre=padre_id, direccion=direccion, escala=padre.escala,
                  posicion=posicion, estilo="visibles" if iso else None, tangentes=padre.tangentes,
                  marcas_centro=padre.marcas_centro and not iso)
        self.vistas.append(v)
        self._calcular(v)
        self._alinear(v)
        return v

    def agregar_vista_seccion(self, padre_id, p1, p2, posicion):
        """Vista de sección (Section View) con la línea p1→p2 dada en la hoja; el lado donde se coloca la vista
        es el del observador (las flechas de la línea miran hacia la pieza)."""
        padre = self.vista(padre_id)
        a, b = padre.de_hoja(p1), padre.de_hoja(p2)
        if np.linalg.norm(b - a) < 1e-9:
            raise geo.ErrorGeometria("La línea de sección necesita dos puntos distintos.")
        t = b - a
        lado_hoja = padre.de_hoja(posicion) - a
        lado = 1 if (t[0] * lado_hoja[1] - t[1] * lado_hoja[0]) >= 0 else -1
        v = Vista(self._nuevo_id("v"), "seccion", padre=padre_id, linea=[a, b], lado=lado, escala=padre.escala,
                  posicion=posicion, estilo="visibles", tangentes=padre.tangentes,
                  marcas_centro=padre.marcas_centro, etiqueta=self._siguiente_etiqueta())
        self.vistas.append(v)
        self._calcular(v)
        self._alinear(v)
        return v

    def agregar_vista_detalle(self, padre_id, centro, radio, posicion, escala=None):
        """Vista de detalle (Detail View): círculo (centro y radio en la hoja) ampliado; por defecto al doble."""
        padre = self.vista(padre_id)
        if radio <= 0:
            raise geo.ErrorGeometria("El círculo de detalle necesita un radio positivo.")
        v = Vista(self._nuevo_id("v"), "detalle", padre=padre_id, centro_detalle=padre.de_hoja(centro),
                  radio_detalle=radio / padre.escala, escala=escala or padre.escala * 2, posicion=posicion,
                  estilo=None, tangentes=padre.tangentes, marcas_centro=padre.marcas_centro,
                  etiqueta=self._siguiente_etiqueta())
        self.vistas.append(v)
        self._calcular(v)
        return v

    def editar_vista(self, vid, **cambios):
        """Cambia escala, estilo, tangentes, marcas de centro o etiqueta (diálogo Drawing View)."""
        v = self.vista(vid)
        for k, val in cambios.items():
            if k not in ("escala", "estilo", "tangentes", "marcas_centro", "etiqueta"):
                raise geo.ErrorGeometria(f"Propiedad de vista no editable: {k}")
            if k == "escala" and not val > 0:
                raise geo.ErrorGeometria("La escala debe ser positiva.")
            setattr(v, k, val)
        for w in [v] + self._descendientes(vid):
            if "escala" in cambios and w is not v and w.tipo in ("proyectada", "seccion"):
                w.escala = self.vista(w.padre).escala     # heredan la escala (las de detalle no)
            self._calcular(w)
        self._alinear(v)
        self._alinear_descendientes(vid)

    def _descendientes(self, vid):
        salida = []
        for h in self.hijas(vid):
            salida += [h] + self._descendientes(h.id)
        return salida

    # ------------------------------------------------------------ anotaciones
    def _modelo(self, vid, puntos_hoja):
        return self.vista(vid).de_hoja(puntos_hoja).tolist()

    def agregar_cota(self, tipo, vista_id, puntos, lugar, **extra):
        """Cota asociada a una vista; `puntos` y `lugar` en la hoja (se guardan en el modelo 2D de la vista).

        tipo: "horizontal" | "vertical" | "alineada" (2 puntos), "radio" | "diametro" (centro + extra radio en
        la hoja), "angulo" (4 puntos: dos aristas), "ordenada_x" | "ordenada_y" (origen y punto)."""
        esperados = {"horizontal": 2, "vertical": 2, "alineada": 2, "radio": 1, "diametro": 1, "angulo": 4,
                     "ordenada_x": 2, "ordenada_y": 2}
        if tipo not in esperados:
            raise geo.ErrorGeometria(f"Tipo de cota desconocido: {tipo}")
        if len(puntos) != esperados[tipo]:
            raise geo.ErrorGeometria(f"La cota {tipo} necesita {esperados[tipo]} puntos.")
        v = self.vista(vista_id)
        a = {"id": self._nuevo_id("a"), "tipo": "cota", "subtipo": tipo, "vista": vista_id,
             "puntos": self._modelo(vista_id, puntos), "lugar": self._modelo(vista_id, [lugar])[0],
             "texto": extra.get("texto")}
        if tipo in ("radio", "diametro"):
            a["radio"] = float(extra["radio"]) / v.escala
        if tipo == "angulo":
            sector_angular(*np.asarray(a["puntos"]), np.asarray(a["lugar"]))   # valida que no sean paralelas
        self.anotaciones.append(a)
        return a

    def agregar_texto(self, posicion, texto, altura=ALTURA_TEXTO):
        a = {"id": self._nuevo_id("a"), "tipo": "texto", "posicion": _lista(posicion), "texto": str(texto),
             "altura": float(altura)}
        self.anotaciones.append(a)
        return a

    def agregar_nota(self, flecha, posicion, texto, vista_id=None):
        """Nota con directriz (Leader). Con vista, la flecha y el texto se mueven con ella."""
        a = {"id": self._nuevo_id("a"), "tipo": "nota", "vista": vista_id, "texto": str(texto)}
        if vista_id:
            a["flecha"], a["posicion"] = self._modelo(vista_id, [flecha, posicion])
        else:
            a["flecha"], a["posicion"] = _lista(flecha), _lista(posicion)
        self.anotaciones.append(a)
        return a

    def agregar_tabla(self, posicion):
        """Lista de piezas (Table › Parts List) con los cuerpos de las vistas base."""
        a = {"id": self._nuevo_id("a"), "tipo": "tabla", "posicion": _lista(posicion)}
        self.anotaciones.append(a)
        return a

    def agregar_globo(self, vista_id, punto, posicion, numero=None):
        """Globo (Balloon) que señala una pieza; sin número toma el elemento de la lista de piezas."""
        v = self.vista(vista_id)
        pm = v.de_hoja(punto)
        a = {"id": self._nuevo_id("a"), "tipo": "globo", "vista": vista_id, "punto": pm.tolist(),
             "posicion": v.de_hoja(posicion).tolist(), "numero": str(numero or self.numero_de_pieza(vista_id, pm))}
        self.anotaciones.append(a)
        return a

    def agregar_linea_centro(self, vista_id, p0, p1):
        a = {"id": self._nuevo_id("a"), "tipo": "linea_centro", "vista": vista_id,
             "puntos": self._modelo(vista_id, [p0, p1])}
        self.anotaciones.append(a)
        return a

    def agregar_marca_centro(self, vista_id, centro, radio):
        v = self.vista(vista_id)
        a = {"id": self._nuevo_id("a"), "tipo": "marca_centro", "vista": vista_id,
             "centro": v.de_hoja(centro).tolist(), "radio": float(radio) / v.escala}
        self.anotaciones.append(a)
        return a

    def lista_piezas(self):
        """[encabezado, filas…] de la lista de piezas: cuerpos de las vistas base agrupados por nombre."""
        ids = []
        for v in self.vistas:
            if v.tipo == "base":
                ids += [c for c in v.cuerpos if c not in ids]
        cuentas = {}
        for c in ids:
            nombre = self._nombres.get(c, c)
            cuentas[nombre] = cuentas.get(nombre, 0) + 1
        filas = [["ELEMENTO", "CANT.", "NÚMERO DE PIEZA", "MATERIAL"]]
        for i, (nombre, n) in enumerate(cuentas.items(), 1):
            filas.append([str(i), str(n), nombre, self.cajetin.get("material", "") or "—"])
        return filas

    def numero_de_pieza(self, vista_id, punto_modelo):
        """Elemento de la lista de piezas del cuerpo bajo el punto (por la caja proyectada de cada cuerpo)."""
        v = self.vista(vista_id)
        raiz = self.raiz(v)
        nombres = [f[2] for f in self.lista_piezas()[1:]]
        mejor = None
        for c in raiz.cuerpos:
            forma = self._formas.get(c)
            caja = geo.caja_envolvente(forma) if forma is not None else None
            if caja is None or v.marco is None:
                continue
            esq = np.array([[x, y, z] for x in (caja[0][0], caja[1][0]) for y in (caja[0][1], caja[1][1])
                            for z in (caja[0][2], caja[1][2])])
            p2 = v.marco.a_2d(esq)
            lo, hi = p2.min(0), p2.max(0)
            if np.all(punto_modelo >= lo - 1e-6) and np.all(punto_modelo <= hi + 1e-6):
                area = float(np.prod(hi - lo))
                if mejor is None or area < mejor[0]:
                    mejor = (area, c)
        if mejor is None:
            return 1
        nombre = self._nombres.get(mejor[1], mejor[1])
        return nombres.index(nombre) + 1 if nombre in nombres else 1

    # ------------------------------------------------------------ modificar
    def elemento(self, eid):
        for v in self.vistas:
            if v.id == eid:
                return v
        return self.anotacion(eid)

    # qué se corre al mover cada anotación: la cota mueve su línea, no los puntos medidos (como en Fusion)
    _MOVIBLE = {"cota": ("lugar",), "nota": ("posicion",), "globo": ("posicion",), "texto": ("posicion",),
                "tabla": ("posicion",), "linea_centro": ("puntos",), "marca_centro": ("centro",)}

    def restringir_movimiento(self, eid, delta):
        """El desplazamiento que se permite: una vista alineada con su padre solo se corre en esa dirección."""
        delta = np.asarray(delta, float)
        for v in self.vistas:
            if v.id == eid:
                m = self._eje_alineacion(v)
                if m is not None and not v.rotacion and not self.vista(v.padre).rotacion:
                    m_hoja = self.vista(v.padre)._rot() @ m
                    return m_hoja * float(delta @ m_hoja)
        return delta

    def mover(self, eid, delta):
        """Mueve una vista o anotación (Move). Una vista alineada solo se corre en su dirección; sus vistas
        proyectadas y de sección la acompañan."""
        delta = self.restringir_movimiento(eid, delta)
        for v in self.vistas:
            if v.id == eid:
                v.posicion = v.posicion + delta
                for d in self._descendientes(v.id):
                    if d.tipo in ("proyectada", "seccion"):
                        d.posicion = d.posicion + delta
                self._alinear_descendientes(v.id)
                return
        a = self.anotacion(eid)
        if a.get("vista"):
            v = self.vista(a["vista"])
            delta = (v._rot().T @ delta) / v.escala
        for k in self._MOVIBLE[a["tipo"]]:
            a[k] = (np.asarray(a[k], float) + delta).tolist()

    def girar(self, vid, grados):
        """Gira una vista (Rotate) alrededor de su centro."""
        v = self.vista(vid)
        v.rotacion = (v.rotacion + float(grados)) % 360.0

    def borrar(self, eid):
        """Borra una vista (con sus vistas hijas y anotaciones) o una anotación (Delete)."""
        if any(v.id == eid for v in self.vistas):
            ids = {eid} | {d.id for d in self._descendientes(eid)}
            self.vistas = [v for v in self.vistas if v.id not in ids]
            self.anotaciones = [a for a in self.anotaciones if a.get("vista") not in ids]
            for i in ids:
                self._cache.pop(i, None)
            return
        self.anotacion(eid)
        self.anotaciones = [a for a in self.anotaciones if a["id"] != eid]

    # ------------------------------------------------------------ primitivas para pintar/exportar
    def campos_cajetin(self):
        campos = dict(self.cajetin)
        if not campos.get("escala"):
            base = next((v for v in self.vistas if v.tipo == "base"), None)
            campos["escala"] = texto_escala(base.escala) if base else ""
        campos["tamano"] = self.tamano
        return campos

    def primitivas_hoja(self):
        return dibujar_marco(self.ancho, self.alto, self.tamano) + \
            dibujar_cajetin(self.ancho, self.alto, self.campos_cajetin(), self.diedro)

    def primitivas_vista(self, v):
        """Aristas de la vista en la hoja, por capa, más ejes, rayado, etiquetas y lo que las hijas marcan
        sobre ella (línea de corte A-A, círculo de detalle)."""
        prims = []
        ocultas = self.estilo_efectivo(v) == "visibles_ocultas"

        def poner(lineas, capa):
            for pl in lineas:
                h = v.a_hoja(pl)
                if len(h) == 2:
                    prims.append((capa, ("linea", _p(h[0]), _p(h[1]))))
                else:
                    prims.append((capa, ("polilinea", [_p(q) for q in h], False)))

        poner(v.lineas["visibles"] + v.lineas["silueta"], "VISIBLE")
        if v.tangentes != "no":
            tg = v.lineas["tangentes"]
            poner([_acortar(t) for t in tg] if v.tangentes == "acortadas" else tg, "TANGENTE")
        if ocultas:
            poner(v.lineas["ocultas"] + v.lineas["silueta_oculta"], "OCULTA")
        for s in v.rayado:
            h = v.a_hoja(s)
            prims.append(("RAYADO", ("linea", _p(h[0]), _p(h[1]))))
        if v.marcas_centro:
            por_centro = {}
            for c, r, completo in v.circulos:
                if completo:
                    k = (round(c[0], 3), round(c[1], 3))
                    por_centro[k] = max(por_centro.get(k, (c, 0.0)), (c, r), key=lambda t: t[1])
            for c, r in por_centro.values():
                prims += dibujar_marca_centro(v.a_hoja(c), r * v.escala)
            for a, b in v.ejes:
                prims += dibujar_linea_centro(v.a_hoja(a), v.a_hoja(b))
        if v.tipo == "detalle":
            prims.append(("CONTORNO", ("circulo", _p(v.posicion), v.radio_detalle * v.escala)))
        caja = v.caja_hoja(0.0)
        etiqueta = None
        if v.tipo == "seccion":
            etiqueta = f"{v.etiqueta}-{v.etiqueta}"
        elif v.tipo == "detalle":
            etiqueta = f"{v.etiqueta} ({texto_escala(v.escala)})"
        if etiqueta:
            if v.tipo == "seccion" and v.padre and abs(v.escala - self.vista(v.padre).escala) > 1e-12:
                etiqueta += f" ({texto_escala(v.escala)})"
            prims.append(_texto(((caja[0] + caja[2]) / 2, caja[1] - 8.0), etiqueta, altura=5.0, capa="TEXTO"))
        if v.error:
            prims.append(_texto(v.posicion, v.error, altura=2.5, capa="TEXTO"))
        for h in self.hijas(v.id):
            prims += self._marcas_de_hija(v, h)
        return prims

    def _marcas_de_hija(self, v, h):
        if h.tipo == "seccion" and h.linea is not None:
            a, b = v.a_hoja(h.linea[0]), v.a_hoja(h.linea[1])
            u = _unit(b - a)
            a, b = a - u * 3.0, b + u * 3.0
            m_hoja = v._rot() @ (h.lado * np.array([-(h.linea[1] - h.linea[0])[1], (h.linea[1] - h.linea[0])[0]]))
            m_hoja = _unit(m_hoja)
            # ISO 128: línea de trazo y punto fina, gruesa en los extremos; flechas en la dirección de mirada
            prims = [_linea(a, b, "SECCION"), _linea(a, a + u * 5.0, "CORTE"), _linea(b - u * 5.0, b, "CORTE")]
            for p in (a, b):
                cola = p + m_hoja * 8.0
                prims += [_linea(cola, p + m_hoja * FLECHA, "CONTORNO"), _flecha(p, -m_hoja, "CORTE"),
                          _texto(cola + m_hoja * 1.5 - (0, 2.5), h.etiqueta, altura=5.0, capa="TEXTO")]
            return prims
        if h.tipo == "detalle" and h.centro_detalle is not None:
            c = v.a_hoja(h.centro_detalle)
            r = h.radio_detalle * v.escala
            return [("CONTORNO", ("circulo", _p(c), r)),
                    _texto(c + np.array([r * 0.75 + 1.5, r * 0.75 + 1.5]), h.etiqueta, altura=5.0, capa="TEXTO")]
        return []

    def valor_cota(self, a):
        """Valor real (mm del modelo o grados) de una cota: no depende de la escala de la vista."""
        p = np.asarray(a["puntos"], float)
        t = a["subtipo"]
        if t == "horizontal":
            return abs(p[1][0] - p[0][0])
        if t == "vertical":
            return abs(p[1][1] - p[0][1])
        if t == "alineada":
            return float(np.linalg.norm(p[1] - p[0]))
        if t == "radio":
            return a["radio"]
        if t == "diametro":
            return 2 * a["radio"]
        if t == "angulo":
            return math.degrees(sector_angular(*p, np.asarray(a["lugar"], float))[2])
        return abs(p[1][0 if t == "ordenada_x" else 1] - p[0][0 if t == "ordenada_x" else 1])

    def texto_cota(self, a):
        if a.get("texto"):
            return a["texto"]
        valor = self.valor_cota(a)
        t = a["subtipo"]
        if t == "angulo":
            return formatear(valor, 1) + "°"
        prefijo = {"radio": "R", "diametro": "⌀"}.get(t, "")
        return prefijo + formatear(valor)

    def primitivas_anotacion(self, a):
        t = a["tipo"]
        v = self.vista(a["vista"]) if a.get("vista") else None
        if t == "cota":
            p = v.a_hoja(a["puntos"])
            lugar = v.a_hoja(a["lugar"])
            st, texto = a["subtipo"], self.texto_cota(a)
            if st in ("horizontal", "vertical", "alineada"):
                modo = st
                if v.rotacion and st != "alineada":    # en una vista girada se mide sobre los ejes de la vista
                    modo = "alineada"
                    q = np.asarray(a["puntos"], float)
                    q1 = q[1].copy()
                    q1[1 if st == "horizontal" else 0] = q[0][1 if st == "horizontal" else 0]
                    p = v.a_hoja([q[0], q1])
                return dibujar_cota_lineal(p[0], p[1], lugar, texto, modo)
            if st in ("radio", "diametro"):
                return dibujar_cota_radial(p[0], a["radio"] * v.escala, lugar, texto, st == "diametro")
            if st == "angulo":
                return dibujar_cota_angular(*p, lugar, texto)[0]
            return dibujar_cota_ordenada(p[1], lugar, texto, "x" if st == "ordenada_x" else "y")
        if t == "texto":
            prims = []
            for i, linea in enumerate(str(a["texto"]).split("\n")):
                pos = np.asarray(a["posicion"], float) - (0, i * a["altura"] * 1.6)
                prims.append(_texto(pos, linea, altura=a["altura"], alineacion="izq", capa="TEXTO"))
            return prims
        if t == "nota":
            f, pos = (v.a_hoja([a["flecha"], a["posicion"]]) if v else (a["flecha"], a["posicion"]))
            return dibujar_nota(f, pos, a["texto"])
        if t == "tabla":
            pos = np.asarray(a["posicion"], float)
            return dibujar_tabla(pos, self.lista_piezas(), hacia_arriba=pos[1] < self.alto / 2)
        if t == "globo":
            return dibujar_globo(v.a_hoja(a["punto"]), v.a_hoja(a["posicion"]), a["numero"])
        if t == "linea_centro":
            p = v.a_hoja(a["puntos"])
            return dibujar_linea_centro(p[0], p[1])
        if t == "marca_centro":
            return dibujar_marca_centro(v.a_hoja(a["centro"]), a["radio"] * v.escala)
        raise geo.ErrorGeometria(f"Anotación desconocida: {t}")

    def primitivas_por_elemento(self):
        """[(clave, primitivas)]: "hoja", cada vista y cada anotación (para la pantalla)."""
        salida = [("hoja", self.primitivas_hoja())]
        salida += [(v.id, self.primitivas_vista(v)) for v in self.vistas]
        for a in self.anotaciones:
            try:
                salida.append((a["id"], self.primitivas_anotacion(a)))
            except (geo.ErrorGeometria, KeyError, IndexError) as e:
                salida.append((a["id"], [_texto(a.get("posicion") or (20, 20), f"⚠ {e}", altura=2.5, capa="TEXTO")]))
        return salida

    def primitivas(self):
        """Todo el plano: [(capa, primitiva)] en mm de la hoja (para PDF y DXF)."""
        return [p for _, ps in self.primitivas_por_elemento() for p in ps]

    # ------------------------------------------------------------ enganche (snap) y selección
    def puntos_clave(self):
        """[(vista, punto modelo 2D, punto hoja)]: puntas de aristas, puntos medios de rectas y centros."""
        salida = []
        for v in self.vistas:
            cats = ["visibles", "silueta", "tangentes"]
            if self.estilo_efectivo(v) == "visibles_ocultas":
                cats += ["ocultas", "silueta_oculta"]
            puntos = []
            for c in cats:
                for pl in v.lineas[c]:
                    if np.linalg.norm(pl[0] - pl[-1]) > 1e-9:   # en una curva cerrada la punta es arbitraria
                        puntos += [pl[0], pl[-1]]
                    if len(pl) == 2:
                        puntos.append((pl[0] + pl[1]) / 2)
            puntos += [c for c, _r, _comp in v.circulos]
            if not puntos:
                continue
            unicos = np.unique(np.round(np.array(puntos), 6), axis=0)
            for pm, ph in zip(unicos, v.a_hoja(unicos), strict=True):
                salida.append((v.id, pm, ph))
        return salida

    def punto_cercano(self, p_hoja, tol):
        """(vista, punto modelo, punto hoja) más cercano a p_hoja dentro de `tol` mm de hoja, o None."""
        p = np.asarray(p_hoja, float)
        mejor = None
        for vid, pm, ph in self.puntos_clave():
            d = float(np.linalg.norm(ph - p))
            if d <= tol and (mejor is None or d < mejor[0]):
                mejor = (d, vid, pm, ph)
        return None if mejor is None else mejor[1:]

    def segmento_cercano(self, p_hoja, tol):
        """(vista, a modelo, b modelo) de la arista recta visible más cercana, o None."""
        p = np.asarray(p_hoja, float)
        mejor = None
        for v in self.vistas:
            rectas = [pl for c in ("visibles", "silueta", "ocultas") for pl in v.lineas[c] if len(pl) == 2]
            if not rectas:
                continue
            arr = np.array(rectas)
            h = v.a_hoja(arr.reshape(-1, 2)).reshape(-1, 2, 2)
            seg = h[:, 1] - h[:, 0]
            largo2 = np.maximum((seg * seg).sum(1), 1e-18)
            t = np.clip(((p - h[:, 0]) * seg).sum(1) / largo2, 0.0, 1.0)
            d = np.linalg.norm(p - (h[:, 0] + t[:, None] * seg), axis=1)
            i = int(np.argmin(d))
            if d[i] <= tol and (mejor is None or d[i] < mejor[0]):
                mejor = (float(d[i]), v.id, arr[i][0], arr[i][1])
        return None if mejor is None else mejor[1:]

    def circulo_cercano(self, p_hoja, tol):
        """(vista, centro modelo, radio modelo, completo) de la circunferencia más cercana al punto, o None."""
        p = np.asarray(p_hoja, float)
        mejor = None
        for v in self.vistas:
            for c, r, completo in v.circulos:
                d = abs(float(np.linalg.norm(v.a_hoja(c) - p)) - r * v.escala)
                if d <= tol and (mejor is None or d < mejor[0]):
                    mejor = (d, v.id, c, r, completo)
        return None if mejor is None else mejor[1:]

    def vista_en(self, p_hoja):
        """Id de la vista bajo el punto de la hoja (la de menor caja si se superponen), o None."""
        p = np.asarray(p_hoja, float)
        mejor = None
        for v in self.vistas:
            x0, y0, x1, y1 = v.caja_hoja()
            if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
                area = (x1 - x0) * (y1 - y0)
                if mejor is None or area < mejor[0]:
                    mejor = (area, v.id)
        return None if mejor is None else mejor[1]

    # ------------------------------------------------------------ serialización
    def a_dict(self):
        return {"version": 1, "hoja": {"tamano": self.tamano, "orientacion": self.orientacion, "norma": self.norma,
                                       "diedro": self.diedro},
                "cajetin": dict(self.cajetin), "metodo": self.metodo, "contador": self.contador,
                "vistas": [v.a_dict() for v in self.vistas],
                "anotaciones": [dict(a) for a in self.anotaciones]}

    @classmethod
    def desde_dict(cls, datos):
        version = datos.get("version", 1)
        if version > 1:
            raise geo.ErrorGeometria(f"El dibujo es de una versión más nueva ({version}) que la soportada (1).")
        hoja = datos.get("hoja", {})
        d = cls(hoja.get("tamano", "A3"), hoja.get("orientacion", "horizontal"), hoja.get("norma", "ISO"))
        d.diedro = hoja.get("diedro", d.diedro)
        d.cajetin.update(datos.get("cajetin", {}))
        d.metodo = datos.get("metodo", "exacto")
        d.contador = int(datos.get("contador", 0))
        d.vistas = [Vista(**{k: v for k, v in vd.items() if k in Vista.CAMPOS}) for vd in datos.get("vistas", [])]
        d.anotaciones = [dict(a) for a in datos.get("anotaciones", [])]
        return d
