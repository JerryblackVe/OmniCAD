# -*- coding: utf-8 -*-
"""
Consejos de diseño [Plastic > Inspect > Design Advice de Fusion]: revisa un cuerpo contra una regla de plástico y una
dirección de extracción del molde, y devuelve las alertas por cara con un consejo cada una:

  - espesor: pared más fina que el rango de la regla («too_thin»), más gruesa («too_thick») o con una variación respecto
    de la pared típica del cuerpo mayor que la de la regla («variation»);
  - contrasalida («undercut»): una cara que no se ve desde su lado de la dirección de extracción, por lo que el molde no
    la puede formar sin un movimiento lateral;
  - desmoldeo («draft»): una cara casi paralela a la extracción, con un ángulo menor que el mínimo de la regla;
  - filo («knife_edge»): una arista convexa tan aguda que la cuña queda más fina que el umbral de filo a lo largo de más
    de 1 mm.

Todo se mide con rayos sobre 3×3 puntos de cada cara (la mediana para el espesor, el peor punto para el resto), así que
es una revisión por regiones, no una simulación de llenado. Unidades: mm y grados.
"""
import math

import numpy as np

from . import geometria as geo

MUESTRAS = 3                       # puntos por lado de la grilla de cada cara
ALCANCE_FILO = 1.0                 # mm de cuña más fina que el umbral a partir del cual la arista es un filo
EPS = 1e-3                         # mm: lo que se separa el origen del rayo de la superficie

CONSEJOS = {
    "too_thin": "Engrosá la pared o cambiá la regla: una pared tan fina puede no llenarse o quedar frágil.",
    "too_thick": "Vaciá o ahuecá la zona (Vaciado, nervios en lugar de masa): una pared gruesa tarda en enfriarse y se hunde.",
    "variation": "Uniformá el espesor de la pared: los cambios bruscos de espesor causan rechupes y alabeo.",
    "undercut": "Cambiá la dirección de extracción, abrí la zona o rediseñá la cara; si no, el molde necesita un "
                "corredizo lateral.",
    "draft": "Agregá desmoldeo (Modificar › Desmoldeo) con al menos el ángulo mínimo de la regla.",
    "knife_edge": "Redondeá o engrosá el filo (Empalme, Chaflán): una cuña tan fina desgasta el molde y se rompe.",
}


def _intersector(forma):
    from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(forma, 1e-7)
    return inter


def _distancias(inter, origen, direccion, maximo=1e5):
    """Distancias ordenadas (sin repetir) a las que el rayo origen + t·direccion corta el cuerpo."""
    from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
    inter.Perform(gp_Lin(gp_Pnt(*map(float, origen)), gp_Dir(*map(float, direccion))), 0.0, maximo)
    if not inter.IsDone():
        return []
    ws = []
    for w in sorted(inter.WParameter(i) for i in range(1, inter.NbPnt() + 1)):
        if not ws or w - ws[-1] > 1e-6:           # el rayo que pasa por una arista la cuenta dos veces
            ws.append(float(w))
    return ws


def _puntos_cara(cara):
    """[(punto, normal hacia afuera)] de hasta MUESTRAS² puntos dentro de la cara (siempre al menos uno)."""
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepTools import BRepTools
    from OCP.gp import gp_Pnt2d
    from OCP.TopAbs import TopAbs_IN
    from . import solidos_modificar as sm
    u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
    salida = []
    for i in range(1, MUESTRAS + 1):
        for j in range(1, MUESTRAS + 1):
            u, v = u0 + (u1 - u0) * i / (MUESTRAS + 1), v0 + (v1 - v0) * j / (MUESTRAS + 1)
            if BRepClass_FaceClassifier(cara, gp_Pnt2d(u, v), 1e-6).State() == TopAbs_IN:
                salida.append(sm._normal_en(cara, u, v))
    return salida or [sm._punto_normal(cara)]


def _espesor(inter, p, n):
    """Espesor de la pared en el punto p (de normal exterior n): distancia hasta la cara de enfrente, o None."""
    ws = _distancias(inter, np.asarray(p) - n * EPS, -n)
    ws = [w for w in ws if w > 1e-4]
    return ws[0] + EPS if ws else None


def _libre(inter, p, n, d):
    """¿El punto (separado de la superficie sobre la normal) ve el infinito hacia `d` sin chocar con el cuerpo?"""
    return not [w for w in _distancias(inter, np.asarray(p) + n * (10 * EPS), d) if w > 1e-4]


def _es_filo(forma, arista, caras_de_arista, inter, umbral):
    """¿La arista es una cuña convexa que queda más fina que `umbral` en más de ALCANCE_FILO mm?"""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_IN
    from . import solidos_modificar as sm
    caras = [sm.TopoDS.Face(c) for c in sm._padres(caras_de_arista, arista)]
    if len(caras) != 2:
        return False
    c = BRepAdaptor_Curve(arista)
    t = (c.FirstParameter() + c.LastParameter()) / 2
    n = []
    for cara in caras:
        uv = sm.BRepAdaptor_Curve2d(arista, cara).Value(t)
        n.append(sm._normal_en(cara, uv.X(), uv.Y())[1])
    medio = np.array([c.Value(t).X(), c.Value(t).Y(), c.Value(t).Z()])
    suma = n[0] + n[1]
    if np.linalg.norm(suma) < 1e-9:
        return False
    cuña = math.pi - math.acos(max(-1.0, min(1.0, float(n[0] @ n[1]))))
    if cuña <= 1e-3 or umbral / (2 * math.tan(cuña / 2)) <= ALCANCE_FILO:
        return False                                         # la cuenta barata primero: el clasificador es caro
    sonda = medio - suma / np.linalg.norm(suma) * 0.01
    clas = BRepClass3d_SolidClassifier(forma, gp_Pnt(*sonda), 1e-6)
    return clas.State() == TopAbs_IN                         # arista cóncava: no es una cuña de material


def consejos_de_diseno(forma, direccion, regla):
    """Revisa `forma` (sólido) con la `regla` de plástico (dict de `nucleo/plastico.py`) y la dirección de extracción.

    Devuelve {"faces": n, "face_shapes": [caras OCC], "alerts": [{"type", "face": índice 1..n en face_shapes, "value",
    "limit", "advice"}…], "summary": {tipo: n}, "thickness": {"min", "median", "max"}}.
    """
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from . import solidos_modificar as sm
    d = np.asarray(direccion, float)
    if np.linalg.norm(d) < 1e-12:
        raise geo.ErrorGeometria("La dirección de extracción no puede ser nula.")
    d = d / np.linalg.norm(d)
    caras = [sm.TopoDS.Face(c) for c in sm._unicos(forma, TopAbs_FACE)]
    if not caras:
        raise geo.ErrorGeometria("El cuerpo no tiene caras que revisar.")
    inter = _intersector(forma)
    medidas = []
    for i, cara in enumerate(caras, 1):
        pts = _puntos_cara(cara)
        espesores = [e for e in (_espesor(inter, p, n) for p, n in pts) if e is not None]
        talud = min(math.degrees(math.asin(min(1.0, abs(float(n @ d))))) for _, n in pts)
        ciega = False
        for p, n in pts:
            cos = float(n @ d)
            lados = [d] if cos > 1e-6 else [-d] if cos < -1e-6 else [d, -d]
            ciega = ciega or not any(_libre(inter, p, n, s) for s in lados)
        medidas.append({"i": i, "espesor": float(np.median(espesores)) if espesores else None, "talud": talud,
                        "ciega": ciega})
    todos = [m["espesor"] for m in medidas if m["espesor"] is not None]
    mediana = float(np.median(todos)) if todos else 0.0
    alertas = []

    def alerta(tipo, i, valor, limite):
        alertas.append({"type": tipo, "face": i, "value": round(float(valor), 4),
                        "limit": None if limite is None else round(float(limite), 4), "advice": CONSEJOS[tipo]})
    for m in medidas:
        e = m["espesor"]
        if e is not None:
            if e < regla["espesor_min"]:
                alerta("too_thin", m["i"], e, regla["espesor_min"])
            elif e > regla["espesor_max"]:
                alerta("too_thick", m["i"], e, regla["espesor_max"])
            if mediana > 0 and abs(e - mediana) / mediana * 100 > regla["variacion_espesor"]:
                alerta("variation", m["i"], abs(e - mediana) / mediana * 100, regla["variacion_espesor"])
        if m["ciega"]:
            alerta("undercut", m["i"], 0.0, None)
        elif m["talud"] < regla["angulo_minimo"]:
            alerta("draft", m["i"], m["talud"], regla["angulo_minimo"])
    por_arista = sm._ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    vistas = []
    for a in sm._unicos(forma, TopAbs_EDGE):
        if _es_filo(forma, sm.TopoDS.Edge(a), por_arista, inter, regla["umbral_filo"]):
            for cara in sm._padres(por_arista, a):
                k = next(i for i, c in enumerate(caras, 1) if c.IsSame(cara))
                if k not in vistas:
                    vistas.append(k)
                    alerta("knife_edge", k, regla["umbral_filo"], regla["umbral_filo"])
    resumen = {t: sum(a["type"] == t for a in alertas) for t in CONSEJOS}
    return {"faces": len(caras), "face_shapes": caras, "alerts": alertas, "summary": resumen,
            "thickness": {"min": min(todos, default=None), "median": mediana or None, "max": max(todos, default=None)}}
