"""Sólidos › Crear: solevacion."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
from . import revision as rv
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import _alambre, _aristas_de, _caras_de, _explorar, _lista, _pnt, _unit, _validar, _xyz
from .solidos_crear_repujado import _normal_orientada

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BRepAdaptor_Curve, BRepAdaptor_Surface, BRepBuilderAPI_Copy, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace,
        BRepBuilderAPI_MakeVertex, BRepClass_FaceClassifier, BRepGProp, BRepLib, BRepOffsetAPI_MakePipeShell,
        BRepOffsetAPI_ThruSections, BRepTools, BRep_Builder, BRep_Tool, ElCLib, GProp_GProps, GeomAPI_Interpolate,
        GeomAbs_Line, GeomLib_IsPlanarSurface, Geom_Circle, Geom_Line, Geom_Plane, HArray1_gp_Pnt,
        ShapeAnalysis_CanonicalRecognition, TopAbs_FACE, TopAbs_IN, TopAbs_ON, TopAbs_VERTEX, TopAbs_WIRE,
        TopLoc_Location, TopoDS, _CURVAS_LIBRES, _SUPERFICIES_LIBRES, gp_Ax2, gp_Ax3, gp_Circ, gp_Dir, gp_Lin, gp_Pln,
        gp_Pnt, gp_Vec,
    )


# ================================================================ 4. solevado
def _seccion(s):
    """('vertice', TopoDS_Vertex) | ('alambre', exterior, [interiores])."""
    if isinstance(s, (tuple, list, np.ndarray)) and len(s) == 3 and all(np.isscalar(c) for c in s):
        return ("vertice", BRepBuilderAPI_MakeVertex(_pnt(s)).Vertex())
    if s.ShapeType() == TopAbs_VERTEX:
        return ("vertice", TopoDS.Vertex(s))
    if s.ShapeType() == TopAbs_FACE:
        cara = TopoDS.Face(s)
        exterior = BRepTools.OuterWire_s(cara)
        interiores = [TopoDS.Wire(w) for w in _explorar(cara, TopAbs_WIRE) if not w.IsSame(exterior)]
        return ("alambre", exterior, interiores)
    return ("alambre", _alambre(s), [])


# Cuánto (mm) puede apartarse una cara o arista libre de su plano, recta o círculo para pasarla a esa forma exacta.
_TOL_CANONICA = 1e-6


def _plano_canonico(cara, tol):
    """(Geom_Plane, ubicación) de una cara libre que es plana, con la normal de su superficie (así la cara no se da
    vuelta), o None."""
    loc = TopLoc_Location()
    sup = BRep_Tool.Surface_s(cara, loc)
    prueba = GeomLib_IsPlanarSurface(sup, tol)
    if not prueba.IsPlanar():
        return None
    pln = prueba.Plan()
    u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    sup.D1((u0 + u1) / 2, (v0 + v1) / 2, p, du, dv)
    normal = du.Crossed(dv)
    if normal.Magnitude() < 1e-12:          # punto singular: no se sabe el sentido
        return None
    if normal.Dot(gp_Vec(pln.Axis().Direction())) < 0:
        pln = gp_Pln(gp_Ax3(pln.Location(), pln.Axis().Direction().Reversed(), pln.XAxis().Direction()))
    return Geom_Plane(pln), loc


def _curva_canonica(arista, tol):
    """(curva, a, z) de una arista libre que es recta o arco: Geom_Line o Geom_Circle recorrida de a a z en el mismo
    sentido que la original, o None."""
    ad = BRepAdaptor_Curve(arista)
    f, l = ad.FirstParameter(), ad.LastParameter()
    p0, p1 = ad.Value(f), ad.Value(l)
    cerrada = p0.Distance(p1) <= tol
    rec = ShapeAnalysis_CanonicalRecognition(arista)
    if not cerrada and rec.IsLine(tol, gp_Lin()):
        return Geom_Line(p0, gp_Dir(gp_Vec(p0, p1))), 0.0, p0.Distance(p1)
    circ = gp_Circ()
    if not rec.IsCircle(tol, circ):
        return None
    q = ad.Value(f + (l - f) * (0.25 if cerrada else 0.5))          # un punto intermedio da el sentido
    if any(circ.Distance(x) > 10 * tol for x in (p0, q, p1)):
        return None

    def avance(x):
        return (ElCLib.Parameter_s(circ, x) - ElCLib.Parameter_s(circ, p0)) % (2 * math.pi)
    if avance(q) > (math.pi if cerrada else avance(p1)):            # va al revés que el eje del círculo
        eje = circ.Position()
        circ = gp_Circ(gp_Ax2(eje.Location(), eje.Direction().Reversed(), eje.XDirection()), circ.Radius())
    a = ElCLib.Parameter_s(circ, p0)
    return Geom_Circle(circ), a, a + (2 * math.pi if cerrada else avance(p1))


def _canonizar(forma, tol=_TOL_CANONICA):
    """Pasa a plano las caras B-spline/Bézier planas y a recta o círculo las aristas que lo son, como las entrega
    Fusion. ThruSections (también el reglado) deja todo B-spline aunque las secciones sean polígonos o círculos:
    sin plano no hay normal para bocetar ni ubicar agujeros, y sin círculo la rosca, los agujeros, las uniones y
    las fijaciones no ven las aristas. Trabaja sobre una copia y, si quedara inválida, devuelve la forma tal cual."""
    if forma is None or geo.esta_vacia(forma):
        return forma
    copia = BRepBuilderAPI_Copy(forma).Shape()
    b = BRep_Builder()
    cambio = False
    for cara in _caras_de(copia):            # primero las caras: en un plano las pcurvas se calculan solas
        if BRepAdaptor_Surface(cara).GetType() not in _SUPERFICIES_LIBRES:
            continue
        plano = _plano_canonico(cara, tol)
        if plano is not None:
            b.UpdateFace(cara, plano[0], plano[1], BRep_Tool.Tolerance_s(cara))
            cambio = True
    for arista in _aristas_de(copia):        # repetidas (una por cara): la segunda vez ya no es libre
        if BRep_Tool.Degenerated_s(arista) or BRepAdaptor_Curve(arista).GetType() not in _CURVAS_LIBRES:
            continue
        canonica = _curva_canonica(arista, tol)
        if canonica is None:
            continue
        curva, a, z = canonica
        b.UpdateEdge(arista, curva, TopLoc_Location(), BRep_Tool.Tolerance_s(arista))
        b.Range(arista, a, z, True)
        b.SameParameter(arista, False)
        b.SameRange(arista, False)
        BRepLib.SameParameter_s(arista, tol)    # rehace las pcurvas de las caras libres al rango nuevo
        cambio = True
    if not cambio:
        return forma
    BRepLib.UpdateTolerances_s(copia)
    return copia if geo.es_valida(copia) else forma


def _loft(alambres, solido, reglada, cerrada, compatibilizar=True):
    ts = BRepOffsetAPI_ThruSections(solido, reglada)
    ts.CheckCompatibility(compatibilizar)
    for tipo, forma in alambres:
        (ts.AddVertex if tipo == "vertice" else ts.AddWire)(forma)
    if cerrada:
        ts.AddWire(alambres[0][1])
    ts.Build()
    if not ts.IsDone():
        raise geo.ErrorGeometria("El kernel no pudo solevar estas secciones.")
    forma = ts.Shape()
    # Con distinta cantidad de aristas (rectángulo → círculo) el ajuste es imprescindible: no hay otra versión.
    if not compatibilizar or len({len(geo._aristas_unicas(f)) for t, f in alambres if t != "vertice"}) > 1:
        return forma
    # B-173: el ajuste de compatibilidad del kernel puede correr la costura de un spline cerrado y plegar la pared
    # (3 splines de 86 puntos: 1,87 L en vez de 4 L, y el volumen cambia de signo según el orden). Sin el ajuste sale
    # bien si las costuras ya vienen alineadas. Solo si las dos versiones difieren se paga la revisión del pliegue.
    try:
        otra = _loft(alambres, solido, reglada, cerrada, False)
    except Exception:  # noqa: BLE001 — sin el ajuste el kernel puede fallar (Standard_Failure): queda la primera
        return forma
    medida = geo.volumen_exacto if solido else geo.area      # B-419: en la superficie se pliega igual
    v1, v2 = medida(forma), medida(otra)
    if abs(v1 - v2) <= 1e-6 * max(abs(v1), abs(v2), 1.0):
        return forma
    return otra if _plegada(forma, solido) and not _plegada(otra, solido) else forma


def _plegada(forma, solido=True):
    """True si la solevación se da vuelta (volumen ≤ 0) o se autointersecta (None, si la revisión no terminó, no cuenta)."""
    return (solido and geo.volumen_exacto(forma) <= 0) or bool(rv._autointersecciones_seguras(forma, 0, 10)[0])


def _auxiliar_direccion(w, normal, delta, angulo, signo=1.0):
    """Sección auxiliar de una condición «Dirección»: copia del contorno `w` corrida `delta` según `normal` y escalada
    para que la superficie salga con `angulo` (grados desde el plano de la sección; `signo` -1 la achica)."""
    c = _centro_alambre(w)
    radio = max(1e-6, float(np.linalg.norm(np.subtract(*geo.caja_envolvente(w)[::-1]))) / 2)
    escala = 1.0 + signo * delta / math.tan(math.radians(angulo)) / radio
    if escala <= 0.05:
        raise geo.ErrorGeometria("⚠ Ese ángulo achica la sección a casi nada.")
    m = np.identity(4)
    m[:3, :3] *= escala
    m[:3, 3] = c + np.asarray(normal, float) * delta - escala * c
    return ("alambre", TopoDS.Wire(geo.transformar(w, m)))


def _hacia_afuera_de_la_cara(cara, punto):
    """Dirección unitaria, dentro del plano tangente de `cara`, que sale de ella perpendicular a su borde en `punto`
    (un punto del borde). En una esquina promedia la de las aristas que se juntan ahí."""
    from OCP.GeomAPI import GeomAPI_ProjectPointOnCurve
    from OCP.ShapeAnalysis import ShapeAnalysis_Surface
    superficie = ShapeAnalysis_Surface(BRep_Tool.Surface_s(cara))
    uv = superficie.ValueOfUV(_pnt(punto), 1e-6)
    n = _normal_orientada(cara, uv.X(), uv.Y())[1]
    suma = np.zeros(3)
    for e in _aristas_de(cara):
        if BRep_Tool.Degenerated_s(e) or BRep_Tool.IsClosed_s(e, cara):
            # El polo y la costura de una cara periódica no delimitan su borde real.
            continue
        curva = BRepAdaptor_Curve(e)
        proy = GeomAPI_ProjectPointOnCurve(_pnt(punto), BRep_Tool.Curve_s(e, 0.0, 0.0), curva.FirstParameter(), curva.LastParameter())
        if proy.NbPoints() == 0 or proy.LowerDistance() > 1e-5 * max(1.0, float(np.linalg.norm(punto))):
            continue
        p, t = gp_Pnt(), gp_Vec()
        curva.D1(proy.LowerDistanceParameter(), p, t)
        d = np.cross(n, _unit(_xyz(t), "tangente del borde"))
        d = _unit(d)
        pr = punto + d * 1e-3
        uv_pr = superficie.ValueOfUV(_pnt(pr), 1e-7)
        if BRepClass_FaceClassifier(cara, uv_pr, 1e-7).State() in (TopAbs_IN, TopAbs_ON):
            # Clasificar en UV: la proyección 3D puede caer en el borde recortado y confundir el lado.
            d = -d
        suma += d
    if float(np.linalg.norm(suma)) < 1e-9:
        raise geo.ErrorGeometria("⚠ La sección no toca el borde de la cara.")
    return _unit(suma)


def _auxiliar_tangente(w, cara, delta, sobre_la_superficie=False):
    """Sección auxiliar de una condición «Tangente»: el contorno `w` (sobre el borde de `cara`) corrido `delta` por el plano
    tangente de la cara hacia afuera, para que la superficie siga a la cara. Cada arista se corre por sus puntos
    (rectas: los extremos; curvas: puntos interpolados o su círculo exacto). Con `sobre_la_superficie` (condición «Suave», G2) cada punto
    se proyecta además sobre la superficie que sostiene a la cara, prolongada: dos secciones así (a `delta` y a
    `2 delta`) hacen que la solevación siga la curvatura de la cara, no solo su plano tangente."""
    from OCP.GC import GC_MakeCircle
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    superficie = BRep_Tool.Surface_s(cara) if sobre_la_superficie else None
    nuevas = []
    for e in _aristas_de(w):
        curva = BRepAdaptor_Curve(e)
        a, z = curva.FirstParameter(), curva.LastParameter()
        k = 9 if sobre_la_superficie or curva.GetType() != GeomAbs_Line else 2
        cerrada = BRep_Tool.IsClosed_s(e)
        if cerrada:
            k -= 1                         # la interpolación periódica no repite el primer punto
        pts = []
        for i in range(k):
            q = _xyz(curva.Value(a + (z - a) * i / (k if cerrada else k - 1)))
            p = q + delta * _hacia_afuera_de_la_cara(cara, q)
            if superficie is not None:
                proy = GeomAPI_ProjectPointOnSurf(_pnt(p), superficie)
                if proy.NbPoints() == 0:
                    raise geo.ErrorGeometria("⚠ La cara no llega hasta donde pide «Suave».")
                p = _xyz(proy.NearestPoint())
            pts.append(p)
        if cerrada and isinstance(curva.Curve().Curve(), Geom_Circle):
            circulo = GC_MakeCircle(_pnt(pts[0]), _pnt(pts[k // 4]), _pnt(pts[k // 2]))
            if circulo.IsDone() and all(circulo.Value().Circ().Distance(_pnt(p)) <= _TOL_CANONICA for p in pts):
                # Una sección circular exacta conserva la costura y no ondula como una spline interpolada.
                nuevas.append(BRepBuilderAPI_MakeEdge(circulo.Value()).Edge())
                continue
        if k == 2:
            nuevas.append(BRepBuilderAPI_MakeEdge(_pnt(pts[0]), _pnt(pts[1])).Edge())
        else:
            arreglo = HArray1_gp_Pnt(1, k)
            for i, q in enumerate(pts):
                arreglo.SetValue(i + 1, _pnt(q))
            ip = GeomAPI_Interpolate(arreglo, cerrada, 1e-7)
            ip.Perform()
            if not ip.IsDone():
                raise geo.ErrorGeometria("⚠ No se pudo armar la sección de «Tangente».")
            nuevas.append(BRepBuilderAPI_MakeEdge(ip.Curve()).Edge())
    return ("alambre", _alambre(nuevas))


def _con_condiciones(exteriores, inicio, fin, medias=None):
    """Condiciones de borde (End Conditions) de la primera y la última sección, y «Dirección» en las intermedias
    (`medias`: {posición: condición}). Se agrega, a poca distancia, una sección auxiliar por el lado que corresponda: copia
    corrida y ensanchada o angostada según el ángulo («Dirección») o corrida por el plano tangente de la cara
    («Tangente», `cond["cara"]`) para que la superficie salga con esa dirección. «Suave» (G2) pone dos auxiliares sobre la
    superficie prolongada de la cara (a 0,5 y 1,5 veces la distancia de la tangente), así sigue también su curvatura; con
    otras proporciones la solevación ondula entre las secciones. Es una aproximación: la solevación pasa por las
    secciones auxiliares."""
    exteriores = list(exteriores)
    pedidos = [(0, inicio), (len(exteriores) - 1, fin)] + sorted((int(k), v) for k, v in (medias or {}).items())
    delante, detras = {}, {}                   # secciones auxiliares por posición: después y antes de la sección
    for pos, cond in pedidos:
        if not cond or cond.get("tipo", "libre") == "libre":
            continue
        if not 0 <= pos < len(exteriores):
            raise geo.ErrorGeometria(f"⚠ No hay sección en la posición {pos + 1}.")
        if cond["tipo"] not in ("direccion", "tangente", "suave", "punto_tangente"):
            raise geo.ErrorGeometria(f"Condición de borde desconocida: {cond['tipo']}")
        tipo, w = exteriores[pos]
        if cond["tipo"] == "punto_tangente":         # Point Tangent: cúpula, con las secciones de la superficie
            vecino = exteriores[1] if pos == 0 else exteriores[-2]
            if tipo != "vertice" or pos not in (0, len(exteriores) - 1) or vecino[0] != "alambre":
                raise geo.ErrorGeometria("⚠ «Punto tangente» necesita un perfil punto.")
            if float(cond.get("peso", 1.0)) <= 0:
                raise geo.ErrorGeometria("⚠ El peso de la condición debe ser positivo.")
            from .superficies import _domo
            (delante if pos == 0 else detras)[pos] = _domo(_xyz(BRep_Tool.Pnt_s(w)), vecino[1], float(cond.get("peso", 1.0)))
            continue
        if tipo != "alambre":
            raise geo.ErrorGeometria("⚠ La condición de borde necesita un contorno.")
        # P-147d: como Fusion, se mide desde la normal (0 = perpendicular) y da vueltas; acá, desde el plano de la sección
        angulo, peso = (90.0 - float(cond.get("angulo", 0.0))) % 360.0, float(cond.get("peso", 1.0))
        if not 0 < angulo < 180 or peso <= 0:
            raise geo.ErrorGeometria("Ángulo de borde entre −90° y 90°; peso > 0.")
        es_extremo = pos in (0, len(exteriores) - 1)
        if cond["tipo"] in ("tangente", "suave") and not es_extremo:
            raise geo.ErrorGeometria(f"⚠ Condición {'Tangente' if cond['tipo'] == 'tangente' else 'Suave'}: solo en los extremos.")
        c = _centro_alambre(w)
        lados = ([(pos + 1, delante)] if pos == 0 else [(pos - 1, detras)] if pos == len(exteriores) - 1
                 else [(pos + 1, delante), (pos - 1, detras)])
        for vecino, destino in lados:
            otro = exteriores[vecino]
            if otro[0] != "alambre":
                raise geo.ErrorGeometria("⚠ La condición de borde necesita un contorno.")
            c2 = _centro_alambre(otro[1])
            delta = peso * 0.15 * float(np.linalg.norm(c2 - c))
            if cond["tipo"] in ("tangente", "suave"):
                cara = cond.get("cara")
                if cara is None:
                    raise geo.ErrorGeometria(f"⚠ Condición {'Tangente' if cond['tipo'] == 'tangente' else 'Suave'}: falta la cara tangente.")
                if cond["tipo"] == "tangente":
                    destino[pos] = [_auxiliar_tangente(w, cara, delta)]
                else:               # G2: dos secciones (a 0,5 y 1,5 pasos) sobre la superficie prolongada de la cara
                    cerca, lejos = (_auxiliar_tangente(w, cara, k * delta, True) for k in (0.5, 1.5))
                    destino[pos] = [cerca, lejos]
                continue
            normal = np.asarray(geo.plano_de_cara(BRepBuilderAPI_MakeFace(w, True).Face()).normal, float)
            if float((c2 - c) @ normal) < 0:
                normal = -normal
            destino[pos] = [_auxiliar_direccion(w, normal, delta, angulo,
                                                -1.0 if (not es_extremo and destino is detras) else 1.0)]
    salida = []
    for i, sec in enumerate(exteriores):
        salida += reversed(detras.get(i, []))        # las auxiliares se guardan de la más cercana a la más lejana
        salida.append(sec)
        salida += delante.get(i, [])
    return salida


def solevar(secciones, *, carriles=(), linea_central=None, cerrada=False, solido=True, reglada=False,
            condicion_inicio=None, condicion_fin=None, fusionar_tangentes=False, condiciones_medias=None,
            condicion_exacta=False):
    """Solevado (Loft) de Fusion [SLD-LOFT-SOLID].

    `condicion_inicio` / `condicion_fin` (End Conditions de la primera y la última sección): {"tipo": "libre"},
    {"tipo": "direccion", "angulo": grados desde la normal de la sección (0 = perpendicular, como Fusion; da vueltas), "peso": 1} o
    {"tipo": "tangente", "cara": TopoDS_Face (la que la superficie sigue; la sección está sobre su borde), "peso": 1}.
    `condiciones_medias`: {posición de una sección intermedia: {"tipo": "direccion", ...}}. Las condiciones se combinan
    con el carril y la línea central (H-91, como la superficie); no con cerrada ni reglada. Con `condicion_exacta`
    Dirección, Tangente y Suave de los extremos fijan la derivada de salida (`superficies._exacta_posible`); sin ella
    (recetas viejas) se aproximan con secciones auxiliares. `fusionar_tangentes` (Tangent Edges › Merge) une
    las caras que quedan tangentes entre sí.

    secciones: caras (se respetan los agujeros si todas tienen la misma cantidad), alambres/aristas, o un
    punto/vértice como primera o última sección. `cerrada` une la última sección con la primera. Con
    `linea_central` se usa MakePipeShell con todas las secciones. Con `carriles` (cualquier cantidad, como Fusion) se comparte
    la construcción de secciones intermedias de la solevación de superficie, conservando las esquinas;
    el sólido se cierra con tapas sobre esas mismas secciones. Los contornos y carriles curvos se aproximan
    por muestras (ver superficies._solevar_con_rieles). Las formas analíticas se recuperan si cumplen la
    tolerancia de _canonizar.
    """
    secs = [_seccion(s) for s in _lista(secciones)]
    if len(secs) < 2:
        raise geo.ErrorGeometria("El solevado necesita al menos dos secciones.")
    if any(s[0] == "vertice" for s in secs[1:-1]):
        raise geo.ErrorGeometria("⚠ El punto solo va al inicio o al final.")
    if cerrada and any(s[0] == "vertice" for s in secs):
        raise geo.ErrorGeometria("⚠ Un solevado cerrado no admite puntos.")
    _exigir_puntos_utiles(secs)
    carriles = _lista(carriles)
    if carriles and linea_central is not None:
        raise geo.ErrorGeometria("⚠ Carriles o línea central, no los dos.")
    exteriores = [(s[0], s[1]) for s in secs]
    if not (carriles or linea_central is not None or cerrada):
        _exigir_ida(exteriores)
    condiciones = any(c and c.get("tipo", "libre") != "libre"
                      for c in (condicion_inicio, condicion_fin, *(condiciones_medias or {}).values()))
    if condiciones and cerrada:
        raise geo.ErrorGeometria("Cerrada: sin condición de borde.")      # no tiene perfiles extremos
    if condiciones and reglada:
        raise geo.ErrorGeometria("Tramos rectos: sin condición de borde.")  # un tramo recto no sale con otra dirección
    if cerrada and (linea_central is not None or carriles):
        raise geo.ErrorGeometria("⚠ Cerrado no va con línea central ni carril.")
    from . import superficies as sfc       # H-91: la superficie ya combina las condiciones con rieles y línea central
    exacta = (condicion_exacta and condiciones and not condiciones_medias and linea_central is None
              and sfc._exacta_posible(exteriores, (condicion_inicio, condicion_fin)))
    if carriles:
        forma = sfc._solevar_con_rieles(exteriores, [_alambre(c) for c in carriles], condicion_inicio, condicion_fin,
                                        condiciones_medias, False, exacta, solido=solido)
    elif linea_central is not None:
        if any(c and c.get("tipo") == "punto_tangente" for c in (condicion_inicio, condicion_fin)):
            raise geo.ErrorGeometria("Punto tangente: sin línea central.")  # las secciones de la cúpula se cruzarían
        if condiciones:
            exteriores = sfc._con_condiciones(exteriores, condicion_inicio, condicion_fin, condiciones_medias)
        espina = _alambre(linea_central)
        ps = BRepOffsetAPI_MakePipeShell(espina)
        ps.SetMode(False)
        for _t, f in exteriores:
            ps.Add(f, False, False)
        try:
            ps.Build()
            hecho = ps.IsDone()
        except Exception:  # noqa: BLE001 — OCC lanza Standard_ConstructionError en los casos que no resuelve
            hecho = False
        if not hecho:
            raise geo.ErrorGeometria("⚠ No se pudo solevar con esa línea central.")
        if solido:
            ps.MakeSolid()
        forma = ps.Shape()
    else:
        forma = sfc._cupula(secs, condicion_inicio, condicion_fin, solido) if condiciones else None
        if forma is None and exacta:
            forma = sfc._solevar_con_rieles(exteriores, [], condicion_inicio, condicion_fin, None, False, True,
                                            solido=solido)
        if forma is None:
            if condiciones:         # receta vieja (sin `condicion_exacta`) o perfiles que no se emparejan: auxiliares
                exteriores = _con_condiciones(exteriores, condicion_inicio, condicion_fin, condiciones_medias)
            forma = _loft(exteriores, solido, reglada, cerrada)
        huecos = [s[2] for s in secs if s[0] == "alambre"]
        if solido and huecos and all(huecos) and len({len(h) for h in huecos}) == 1:
            for k in range(len(huecos[0])):
                cadena = [("alambre", huecos[0][k])]
                for siguiente in huecos[1:]:   # empareja cada agujero con el más cercano de la sección siguiente
                    c = _centro_alambre(cadena[-1][1])
                    cercano = min(siguiente, key=lambda w, c=c: np.linalg.norm(_centro_alambre(w) - c))
                    cadena.append(("alambre", cercano))
                forma = geo.booleano(forma, _loft(cadena, True, reglada, cerrada), "cortar")
    forma = _canonizar(forma)
    if fusionar_tangentes:
        forma = geo.unificar_caras(forma)
    forma = _validar(forma, "Solevado")
    # B-243: un peso alto en la condición de borde pliega la pared sobre sí misma; es_valida no lo ve y Fusion lo rechaza.
    # H-91: con carril o línea central la B-spline es densa y el análisis agota los 10 s sin contar nada; ahí revisa el
    # paso (`ops_solido._exigir_sin_autointersecciones`, B-462).
    guiada = bool(carriles) or linea_central is not None
    if condiciones and solido and not guiada and rv._autointersecciones_seguras(forma, 0, 10)[0]:
        raise geo.ErrorGeometria("Solevado: el sólido se autointersecta.")
    return forma


def _exigir_puntos_utiles(secs):
    """B-451: un punto como sección solo sirve con un perfil y fuera de su plano. Dos puntos solos, o el centro del
    círculo tomado como punto en el plano del perfil (Fusion también lo elige con el clic cerca del centro), dan un
    solevado plano o un «el kernel no pudo»: se dice qué pasa."""
    from .desfase_aristas import plano_de_aristas
    if all(t == "vertice" for t, *_ in secs):
        raise geo.ErrorGeometria("Solevado: elegí al menos un perfil.")
    if len(secs) != 2:  # con secciones intermedias el conjunto no es plano aunque el punto toque el plano del vecino
        return
    for i in (0, 1):
        if secs[i][0] != "vertice":
            continue
        vecino = secs[1][1] if i == 0 else secs[-2][1]
        if secs[1 if i == 0 else -2][0] == "vertice":
            continue
        try:
            plano = plano_de_aristas(geo._aristas_unicas(vecino))
        except geo.ErrorGeometria:
            continue                                   # perfil alabeado o recto: no hay plano contra el que comparar
        d = float(np.dot(_xyz(BRep_Tool.Pnt_s(secs[i][1])) - plano.origen, plano.normal))
        if abs(d) < 1e-6:
            raise geo.ErrorGeometria("Solevado: punto en el plano del perfil.")


def _exigir_ida(secciones):
    """B-416: secciones que van y vuelven (un centro queda detrás del anterior en el camino de la primera a la última,
    como n, p, m en el antebrazo) pliegan la solevación sobre sí misma; el kernel la arma igual, a veces con volumen
    negativo. Fusion las une en el orden elegido (Reorder): se rechaza y se pide ordenarlas. Un arco (la del medio más
    alta) sigue avanzando: vale."""
    c = [_xyz(BRep_Tool.Pnt_s(f)) if t == "vertice" else _centro_alambre(f) for t, f in secciones]
    eje = c[-1] - c[0]
    avance = [float(np.dot(x - c[0], eje)) for x in c]
    for i in range(len(c) - 1):
        if avance[i + 1] < avance[i] - 1e-9 * float(np.dot(eje, eje)):
            raise geo.ErrorGeometria(f"Solevado: la sección {i + 2} va hacia atrás.")


def _centro_alambre(w):
    p = GProp_GProps()
    BRepGProp.LinearProperties_s(w, p)
    return _xyz(p.CentreOfMass())


_registrar_tema(globals())
