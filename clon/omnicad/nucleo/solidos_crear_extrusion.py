"""Sólidos › Crear: extrusion."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import (
    _MARGEN, _aristas_de, _cadenas, _caja_proyectada, _cara, _caras_de, _engrosar_lamina, _explorar, _extremos,
    _gdir, _gvec, _piezas_que_tocan, _pnt, _poligono, _proyectar_caja, _trasladar, _unir, _unit, _validar,
    cara_de_plano, lado_todo,
)

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BRepAdaptor_Curve, BRepAlgoAPI_Splitter, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace,
        BRepBuilderAPI_MakeWire, BRepClass_FaceClassifier,
        BRepOffsetAPI_DraftAngle, BRepOffsetAPI_MakeOffset, BRepOffsetAPI_ThruSections, BRepPrimAPI_MakeHalfSpace,
        BRepPrimAPI_MakePrism, BRepTools, BRepTools_WireExplorer, GeomAbs_Arc, GeomAbs_Intersection, GeomAbs_Line,
        GeomAPI_Interpolate, HArray1_gp_Pnt,
        List_TopoDS_Shape, TopAbs_EDGE, TopAbs_FACE, TopAbs_IN, TopAbs_REVERSED, TopAbs_WIRE, TopoDS, gp_Pln, gp_Pnt,
    )


# ================================================================ 1. extrusión
def _prisma(cara, n, d, conicidad=0.0, aristas_fijas=()):
    """Extrusión de una cara plana una distancia `d` (con signo) según `n`, con ángulo de inclinación en
    grados (positivo = se ensancha, como en Fusion)."""
    geo.exigir_longitud(d, "La distancia de extrusión")
    if abs(conicidad) < 1e-9:
        return BRepPrimAPI_MakePrism(cara, _gvec(np.asarray(n, float) * d)).Shape()
    if abs(conicidad) >= 89.0:
        raise geo.ErrorGeometria("⚠ La inclinación debe ir de -89° a 89°.")
    if conicidad < 0 and not aristas_fijas:     # con aristas fijas (perfiles vecinos) el cierre es otro
        recortado = _recorte_en_vertice(cara, n, d, conicidad)
        if recortado is not None:
            return recortado
    n = np.asarray(n, float)
    plano = geo.plano_de_cara(cara)
    if plano is None or abs(float(plano.normal @ n)) < 1e-9:
        raise geo.ErrorGeometria("⚠ Con inclinación, el perfil debe ser plano.")
    if abs(float(plano.normal @ n)) < 1 - 1e-9 and any(
            BRepAdaptor_Curve(e).GetType() != GeomAbs_Line for e in _aristas_de(cara)):
        return _prisma_curvo_inclinado(cara, n, d, conicidad)
    # Prisma recto + desmoldeo de las caras laterales con el plano del perfil como plano neutro: las
    # esquinas quedan vivas (tronco de pirámide), como en Fusion. LocOpe_DPrism las redondea al ensanchar.
    tirar = n * math.copysign(1.0, d)
    mk = BRepPrimAPI_MakePrism(cara, _gvec(n * d))
    prisma = mk.Shape()
    fijas = [f for e in aristas_fijas for f in mk.Generated(e)]
    neutro = gp_Pln(_pnt(plano.origen), _gdir(plano.normal))
    da = BRepOffsetAPI_DraftAngle(prisma)
    inclinadas = 0
    for f in geo.caras(prisma):
        if any(f.IsSame(fija) for fija in fijas):
            continue
        pl = geo.plano_de_cara(f)
        if pl is not None and abs(abs(float(pl.normal @ plano.normal)) - 1) < 1e-9:
            continue   # tapas
        da.Add(f, _gdir(tirar), math.radians(-conicidad), neutro, True)
        if not da.AddDone():
            return _conicidad_sin_draft(cara, n, d, conicidad, fijas, "No se pudo inclinar una cara lateral de la extrusión.")
        inclinadas += 1
    if not inclinadas:
        return prisma
    da.Build()
    if not da.IsDone():
        return _conicidad_sin_draft(cara, n, d, conicidad, fijas, "El kernel no pudo aplicar la inclinación a la extrusión.")
    try:
        return _validar(da.Shape(), "Extrusión con inclinación")
    except geo.ErrorGeometria as error:
        return _conicidad_sin_draft(cara, n, d, conicidad, fijas, str(error))


def _conicidad_sin_draft(cara, n, distancia, conicidad, fijas, mensaje):
    """DraftAngle falló. Con curvas, el lateral reglado llega hasta el cierre (B-362: DraftAngle fallaba antes del
    cierre de un círculo y con cualquier elipse o letra de splines); si tampoco se puede, el error indica el cierre."""
    if not any(BRepAdaptor_Curve(e).GetType() != GeomAbs_Line for e in _aristas_de(cara)):
        raise geo.ErrorGeometria(mensaje)
    radio = radios_conicidad([cara])[0 if conicidad < 0 else 1]
    cierre = radio / abs(math.tan(math.radians(conicidad)))
    if not fijas:   # con caras fijas (perfiles vecinos) el lateral reglado las inclinaría
        try:
            return _prisma_curvo_inclinado(cara, n, distancia, conicidad)
        except geo.ErrorGeometria as error:
            mensaje = str(error)
    if 0 < cierre < math.inf:
        motivo = ("La distancia alcanza o supera ese cierre." if abs(distancia) >= cierre else
                  "El kernel falla antes de ese cierre; probá una distancia o un ángulo menor.")
        mensaje = f"{mensaje} El perfil se cierra aproximadamente a {cierre:.3f} mm. {motivo}"
    raise geo.ErrorGeometria(mensaje)


def _firma(forma, plano):
    """(signos de las áreas de los lazos, cantidad de aristas): el contorno exterior suma y cada hueco resta. Si un
    desfase cambia la firma, algo se cerró: una barra angosta, una ranura, un hueco o la pared entre el hueco y el borde
    (ahí el kernel cambia el hueco por un pedazo suelto con la misma cantidad de lazos y aristas)."""
    ejes = np.array([plano.u, plano.v], float).T
    signos, aristas = [], 0
    for w in _explorar(forma, TopAbs_WIRE):
        tramos = []
        ex = BRepTools_WireExplorer(TopoDS.Wire(w))
        while ex.More():
            q = (np.asarray(geo.polilinea_arista(ex.Current(), 0.05), float) - plano.origen) @ ejes
            tramos.append(q[::-1] if ex.Orientation() == TopAbs_REVERSED else q)
            aristas += 1
            ex.Next()
        p = np.concatenate(tramos) if tramos else np.zeros((0, 2))
        signos.append(1 if np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]) > 0 else -1)
    return tuple(sorted(signos)), aristas


def _desfasado(cara, plano, r):
    """Firma del contorno de la cara desfasado `r` (negativo = hacia adentro); None si el kernel no lo arma."""
    try:
        mk = BRepOffsetAPI_MakeOffset(cara, GeomAbs_Arc)   # con Intersection no desfasa hacia adentro una cara con hueco
        mk.Perform(r)
        return _firma(mk.Shape(), plano) if mk.IsDone() else None
    except Exception:  # noqa: BLE001 — un desfase que el kernel no arma cuenta como cerrado
        return None


def _cierre(cara, signo):
    """Mayor desfase hacia `signo` (−1 adentro, +1 afuera) que deja la firma del contorno igual; inf si nunca cambia."""
    plano = geo.plano_de_cara(cara)
    if plano is None:
        raise geo.ErrorGeometria("La cara del perfil no es plana.")
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(cara)
    lados = sorted(abs(float(np.dot(np.subtract((x1, y1, z1), (x0, y0, z0)), e))) for e in (plano.u, plano.v))
    # hacia adentro todo se cierra antes de medio lado corto; hacia afuera, una ranura o un hueco antes de medio lado largo
    alto = (lados[0] if signo < 0 else lados[1]) / 2 * 1.01
    base = _desfasado(cara, plano, signo * alto * 1e-6)      # la junta en arco suma un arco en cada esquina convexa
    if base is None:
        return 0.0
    if _desfasado(cara, plano, signo * alto) == base:
        return math.inf
    bajo = 0.0
    for _ in range(18):                          # 2⁻¹⁸ de medio lado: menos de 0,001 mm en una pieza de 400
        medio = (bajo + alto) / 2
        if _desfasado(cara, plano, signo * medio) == base:
            bajo = medio
        else:
            alto = medio
    return bajo


def _cara_poligonal_conicidad(cara):
    """Contorno aproximado solo para medir el cierre; conserva el exterior y los huecos."""
    # shortcut: hasta 16 aristas originales y 96 segmentos; letras complejas quedan sin tope hasta medirlas sin
    # bloquear el arrastre (objetivo: menos de 0,3 s por perfil típico).
    if len(_aristas_de(cara)) > 16:
        return None
    exterior = BRepTools.OuterWire_s(cara)
    alambres = [exterior] + [TopoDS.Wire(w) for w in _explorar(cara, TopAbs_WIRE) if not w.IsSame(exterior)]
    tolerancia = max(1e-7, math.sqrt(geo.area(cara)) * 0.001)
    contornos, segmentos = [], 0
    for alambre in alambres:
        puntos = []
        ex = BRepTools_WireExplorer(alambre)
        while ex.More():
            tramo = geo.polilinea_arista(ex.Current(), tolerancia)
            if len(tramo) < 2:
                return None
            if ex.Current().Orientation() == TopAbs_REVERSED:
                tramo = tramo[::-1]
            puntos.extend(tramo[:-1])
            segmentos += len(tramo) - 1
            if segmentos > 96:
                return None
            ex.Next()
        contornos.append(_poligono(puntos))
    mk = BRepBuilderAPI_MakeFace(contornos[0], True)
    for hueco in contornos[1:]:
        mk.Add(hueco)
    return mk.Face() if mk.IsDone() else None


def radios_conicidad(caras):
    """(adentro, afuera): hasta dónde se puede achicar o agrandar el contorno de estas caras antes de que algo se cierre
    (inf: sin tope). Las curvas se aproximan con segmentos solo para esta medición.
    Una extrusión con conicidad a desfasa su perfil d·tan|a| (hacia adentro si a < 0): con perfiles no convexos lo que
    se cierra primero es lo más angosto (una barra, una ranura, un hueco), no el círculo más grande. Fusion frena ahí las
    asas de distancia y de ángulo (B-343, B-360)."""
    adentro = afuera = math.inf
    for cara in caras:
        cara = TopoDS.Face(cara)
        if any(BRepAdaptor_Curve(e).GetType() != GeomAbs_Line for e in _aristas_de(cara)):
            cara = _cara_poligonal_conicidad(cara)
            if cara is None:
                continue
        adentro = min(adentro, _cierre(cara, -1))
        afuera = min(afuera, _cierre(cara, 1))
    return adentro, afuera


_CIERRES = {}


def _cierre_adentro(cara):
    """`radios_conicidad([cara])[0]` (~0,1 s) recordado por el contorno: al arrastrar un asa el perfil se rearma igual."""
    clave = tuple(np.round(np.concatenate([geo.polilinea_arista(e, 0.01) for e in _aristas_de(cara)]), 6).ravel())
    if clave not in _CIERRES:
        if len(_CIERRES) > 64:
            _CIERRES.clear()
        _CIERRES[clave] = radios_conicidad([cara])[0]
    return _CIERRES[clave]


def _recorte_en_vertice(cara, n, d, conicidad):
    """B-508: con conicidad negativa que pasa el cierre, Fusion recorta en el vértice (el kernel armaba un doble cono).
    El prisma hasta el cierre si ahí se cierra TODO el perfil (la tapa queda en menos del 1 % de la base); None si la
    distancia no llega o si solo se cierra un cuello angosto (sigue el camino de siempre, que da el error)."""
    cierre = _cierre_adentro(cara) / math.tan(math.radians(-conicidad)) * (1 - 1e-4)  # en el vértice justo no hay tapa
    if abs(d) <= cierre:
        return None
    try:
        recortado = _prisma(cara, n, math.copysign(cierre, d), conicidad)
        normal = geo.plano_de_cara(cara).normal
        tapas = [geo.area(f) for f in geo.caras(recortado)
                 if (p := geo.plano_de_cara(f)) is not None and abs(abs(float(p.normal @ normal)) - 1) < 1e-9]
    except (geo.ErrorGeometria, AttributeError):
        return None
    return recortado if min(tapas, default=math.inf) < 0.01 * geo.area(cara) else None


def _prisma_curvo_inclinado(cara, n, d, conicidad):
    """Extruir › Inicio Objeto: lateral reglado entre la base curva y su desfase en el plano neutro.

    DraftAngle no admite el lateral de una elipse oblicua. El extremo conserva el plano de inicio
    trasladado según la dirección; los huecos se cierran al ensanchar el material. También es el respaldo de
    `_prisma` cuando DraftAngle falla con curvas (B-362).
    """
    exterior = BRepTools.OuterWire_s(TopoDS.Face(cara))
    desfase = abs(d) * math.tan(math.radians(conicidad))
    alambres = [exterior] + [TopoDS.Wire(w) for w in _explorar(cara, TopAbs_WIRE) if not w.IsSame(exterior)]

    def lateral(desfasar, revisar_cierre):
        piezas, tapas = [], []
        for i, w in enumerate(alambres):
            s = desfase if i == 0 else -desfase
            extremo = desfasar(w, s)
            if revisar_cierre:
                # si el desfase cambia la cantidad de aristas, algo se cerró: el tope de las letras que no se pueden medir
                chico = math.copysign(min(abs(s), 1e-3), s)
                if len(_aristas_de(extremo)) != len(_aristas_de(desfasar(w, chico))):
                    raise geo.ErrorGeometria("⚠ La inclinación cierra parte del perfil.")
            tapas.append(_cara(extremo))
            mk = BRepOffsetAPI_ThruSections(True, True)
            mk.AddWire(w)
            mk.AddWire(_trasladar(extremo, n * d))
            mk.Build()
            if not mk.IsDone():
                raise geo.ErrorGeometria("⚠ No se pudo crear el lateral curvo.")
            piezas.append(_validar(mk.Shape(), "Extrusión curva con inclinación"))
        # un hueco que cruza el borde o pisa otro hueco ya cerró la pared: la tapa pierde menos que la suma de los huecos
        tapa, esperada = tapas[0], abs(geo.area(tapas[0]))
        for hueco in tapas[1:]:
            tapa, esperada = geo.booleano(tapa, hueco, "cortar"), esperada - abs(geo.area(hueco))
        if len(tapas) > 1 and abs(geo.area(tapa) - esperada) > 1e-6 * abs(geo.area(tapas[0])):
            raise geo.ErrorGeometria("⚠ La inclinación cierra parte del perfil.")
        resultado = piezas[0]
        for hueco in piezas[1:]:
            resultado = geo.booleano(resultado, hueco, "cortar")
        return _validar(resultado, "Extrusión curva con inclinación")

    try:
        return lateral(_desfase_alambre, True)
    except geo.ErrorGeometria as primero:
        # B-362: MakeOffset con juntas vivas falla o deja un alambre que ThruSections no puede emparejar con
        # contornos de letras que mezclan rectas y splines; muestrear cada arista sí conserva los dos extremos.
        try:
            return lateral(_desfase_alambre_muestreado, False)
        except geo.ErrorGeometria:
            if "cierra parte del perfil" in str(primero):
                raise primero
            raise


def _sentido_alambre(alambre):
    """+1 si el desfase positivo de MakeOffset agranda el lazo, −1 si lo achica: sigue el sentido del alambre, y el
    hueco de una cara de boceto viene al revés que el de una booleana."""
    cara = _cara(alambre)
    mo = BRepOffsetAPI_MakeOffset(alambre, GeomAbs_Intersection, False)
    mo.Perform(1e-3 * math.sqrt(abs(geo.area(cara))))
    aristas = _aristas_de(mo.Shape()) if mo.IsDone() else []
    if not aristas:
        return 1
    c = BRepAdaptor_Curve(aristas[0])          # un punto del lazo desfasado: dentro del original = se achicó
    adentro = BRepClass_FaceClassifier(cara, c.Value((c.FirstParameter() + c.LastParameter()) / 2), 1e-9).State()
    return -1 if adentro == TopAbs_IN else 1


def _desfase_alambre(alambre, d):
    """Desfase 2D de un alambre cerrado y plano (positivo = agranda el lazo), con esquinas vivas."""
    mo = BRepOffsetAPI_MakeOffset(alambre, GeomAbs_Intersection, False)
    mo.Perform(float(d) * _sentido_alambre(alambre))
    if not mo.IsDone():
        raise geo.ErrorGeometria("⚠ No se pudo desfasar (espesor muy grande).")
    alambres = [TopoDS.Wire(w) for w in _explorar(mo.Shape(), TopAbs_WIRE)]
    if len(alambres) != 1:
        raise geo.ErrorGeometria("⚠ El desfase se partió en varios lazos.")
    return alambres[0]


def _desfase_alambre_muestreado(alambre, d):
    """Desfase de un alambre arista por arista (punto + d·normal) con uniones en esquina viva (B-362).

    MakeOffset con junta Intersection falla con los contornos de letras que mezclan rectas y splines, y con la junta
    en arco el kernel se cae. Cada arista conserva su cantidad de tramos, así ThruSections arma el lateral reglado
    contra la base exacta."""
    plano = geo.plano_de_cara(_cara(alambre))
    if plano is None:
        raise geo.ErrorGeometria("⚠ No se pudo desfasar (espesor muy grande).")
    normal = np.asarray(plano.normal, float)
    tramos, area = [], 0.0
    ex = BRepTools_WireExplorer(alambre)
    while ex.More():
        arista = ex.Current()
        puntos = np.asarray(geo.polilinea_arista(arista, 0.01), float)
        if len(puntos) < 2:
            raise geo.ErrorGeometria("⚠ No se pudo desfasar (espesor muy grande).")
        if arista.Orientation() == TopAbs_REVERSED:
            puntos = puntos[::-1]
        tramos.append(puntos)
        q = np.array([[plano.u @ p, plano.v @ p] for p in puntos])
        area += np.sum(q[:-1, 0] * q[1:, 1] - q[1:, 0] * q[:-1, 1])   # área con signo: dice para qué lado crece
        ex.Next()
    if len(tramos) < 2:
        raise geo.ErrorGeometria("⚠ No se pudo desfasar (espesor muy grande).")
    sentido = 1.0 if area >= 0 else -1.0
    desplazados = []
    for puntos in tramos:
        q = np.zeros_like(puntos)
        for i in range(len(puntos)):
            t = puntos[min(i + 1, len(puntos) - 1)] - puntos[max(i - 1, 0)]
            t = t / (np.linalg.norm(t) or 1.0)
            q[i] = puntos[i] + sentido * d * np.cross(t, normal)
        desplazados.append(q)
    uniones = [_union_esquina(desplazados[i - 1][-2:], desplazados[i][:2], d, plano)
               for i in range(len(desplazados))]
    aristas = []
    for i, q in enumerate(desplazados):
        recorrido = [uniones[i]] + list(q[1:-1]) + [uniones[(i + 1) % len(uniones)]]
        limpio = [recorrido[0]]
        for p in recorrido[1:]:
            if np.linalg.norm(p - limpio[-1]) > 1e-7:
                limpio.append(p)
        if len(limpio) < 2:
            raise geo.ErrorGeometria("⚠ No se pudo desfasar (espesor muy grande).")
        if len(limpio) == 2:
            aristas.append(BRepBuilderAPI_MakeEdge(gp_Pnt(*map(float, limpio[0])),
                                                   gp_Pnt(*map(float, limpio[1]))).Edge())
            continue
        puntos = HArray1_gp_Pnt(1, len(limpio))
        for k, p in enumerate(limpio):
            puntos.SetValue(k + 1, gp_Pnt(*map(float, p)))
        interp = GeomAPI_Interpolate(puntos, False, 1e-7)
        interp.Perform()
        if not interp.IsDone():
            raise geo.ErrorGeometria("⚠ No se pudo desfasar (espesor muy grande).")
        aristas.append(BRepBuilderAPI_MakeEdge(interp.Curve()).Edge())
    mk = BRepBuilderAPI_MakeWire()
    for arista in aristas:
        mk.Add(arista)
    if not mk.IsDone():
        raise geo.ErrorGeometria("⚠ No se pudo desfasar (espesor muy grande).")
    return mk.Wire()


def _union_esquina(previas, siguientes, d, plano):
    """Esquina viva entre dos tramos desfasados: cruce de sus tangentes; si se van paralelas, el punto medio."""
    a, b = previas[-2], previas[-1]
    c, e = siguientes[0], siguientes[1]
    p = np.array([[plano.u @ a, plano.v @ a], [plano.u @ b, plano.v @ b]])
    q = np.array([[plano.u @ c, plano.v @ c], [plano.u @ e, plano.v @ e]])
    d1, d2 = p[1] - p[0], q[1] - q[0]
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return (b + c) / 2
    t = ((q[0][0] - p[0][0]) * d2[1] - (q[0][1] - p[0][1]) * d2[0]) / den
    cruce = p[0] + t * d1
    if np.linalg.norm(cruce - (p[1] + q[0]) / 2) > max(4 * abs(d), 0.5):   # un cruce disparatado es un lazo cerrado
        return (b + c) / 2
    return plano.a_3d(float(cruce[0]), float(cruce[1]))


def _bandas_cerradas(caras, espesor, ubicacion):
    """Caras planas de pared delgada a lo largo de cada lazo de los perfiles (Thin Extrude con perfil
    cerrado). lado1 = hacia afuera de cada lazo, lado2 = hacia adentro, centro = mitad y mitad."""
    if espesor <= 0:
        raise geo.ErrorGeometria("El espesor de pared debe ser positivo.")
    a, b = {"lado1": (0.0, espesor), "lado2": (-espesor, 0.0),
            "centro": (-espesor / 2, espesor / 2)}.get(ubicacion, (None, None))
    if a is None:
        raise geo.ErrorGeometria(f"Ubicación de pared desconocida: {ubicacion}")
    bandas = []
    for cara in caras:
        for w in _explorar(cara, TopAbs_WIRE):
            w = TopoDS.Wire(w)
            exterior = _cara(_desfase_alambre(w, b) if b else w)
            interior = _cara(_desfase_alambre(w, a) if a else w)
            bandas += _caras_de(geo.booleano(exterior, interior, "cortar"))
    return bandas


def _extruir_perfiles_vecinos(caras, n, base, lados):
    """Extruir de Fusion: inclina el exterior común y conserva un sólido por perfil, en su orden."""
    caras = _caras_de(_trasladar(geo.compuesto(caras), n * base))
    aristas = [_aristas_de(c) for c in caras]
    vecinos = [set() for _ in caras]
    fijas = [[] for _ in caras]
    for i, bordes in enumerate(aristas):
        for j in range(i + 1, len(caras)):
            comunes = [e for e in bordes if any(e.IsSame(f) for f in aristas[j])]
            if comunes:
                vecinos[i].add(j)
                vecinos[j].add(i)
                fijas[i].extend(comunes)
                fijas[j].extend(comunes)
    if not any(vecinos):
        return None
    pendientes = set(range(len(caras)))
    por_perfil = [[] for _ in caras]
    while pendientes:
        grupo, cola = set(), [min(pendientes)]
        while cola:
            i = cola.pop()
            if i not in pendientes:
                continue
            pendientes.remove(i)
            grupo.add(i)
            cola.extend(vecinos[i] & pendientes)
        grupo = sorted(grupo)
        region = _caras_de(_unir([caras[i] for i in grupo]))
        if len(region) != 1:
            raise geo.ErrorGeometria("⚠ No se pudieron unir los perfiles vecinos.")
        for d, conicidad in lados:
            limite = _prisma(region[0], n, d, conicidad) if len(grupo) > 1 and abs(conicidad) >= 1e-9 else None
            anteriores = []
            for i in grupo:
                forma = _prisma(caras[i], n, d, conicidad, aristas_fijas=fijas[i])
                if limite is not None:
                    forma = geo.booleano(forma, limite, "intersecar")
                    caja = geo.caja_envolvente(forma)
                    # Al ensanchar, dos bordes exteriores pueden pisarse junto al fin de una pared compartida.
                    for anterior, caja_anterior in anteriores:
                        if caja is not None and geo.cajas_solapan(caja, caja_anterior):
                            forma = geo.booleano(forma, anterior, "cortar")
                    anteriores.append((forma, caja))
                por_perfil[i].append(_validar(forma, "Extrusión de perfiles vecinos"))
    return geo.compuesto([_unir(partes) for partes in por_perfil])


def _herramienta_extrusion(caras, abiertas, n, base, lados, delgado):
    """Une los prismas de cada lado (lista de (distancia con signo, conicidad)). Cada lado es una extrusión
    independiente con su conicidad, como en Fusion («Two Sides: adjust the settings independently for each side»):
    las dos comparten el plano neutro, que es el plano del perfil movido `base`."""
    if len(caras) > 1 and not abiertas and any(abs(c) >= 1e-9 for _, c in lados):
        vecinos = _extruir_perfiles_vecinos(caras, n, base, lados)
        if vecinos is not None:
            return vecinos
    solidos = []
    for d, conicidad in lados:
        for cara in caras:
            solidos.append(_prisma(_trasladar(cara, n * base), n, d, conicidad))
    if abiertas:
        if any(abs(c) > 1e-9 for _, c in lados):
            raise geo.ErrorGeometria("⚠ La extrusión delgada no admite inclinación.")
        lo = min([0.0] + [d for d, _ in lados])
        hi = max([0.0] + [d for d, _ in lados])
        t, ubic = float(delgado["espesor"]), delgado.get("ubicacion", "centro")
        for w in abiertas:
            lamina = BRepPrimAPI_MakePrism(_trasladar(w, n * (base + lo)), _gvec(n * (hi - lo))).Shape()
            if ubic == "lado1":
                solidos.append(_engrosar_lamina(lamina, t))
            elif ubic == "lado2":
                solidos.append(_engrosar_lamina(lamina, -t))
            elif ubic == "centro":
                solidos += [_engrosar_lamina(lamina, t / 2), _engrosar_lamina(lamina, -t / 2)]
            else:
                raise geo.ErrorGeometria(f"Ubicación de pared desconocida: {ubic}")
    return _unir(solidos)


def _distancia_a_plano(origen, n, cara_plana):
    pl = geo.plano_de_cara(cara_plana)
    coseno = float(n @ pl.normal)
    if abs(coseno) < 1e-9:
        raise geo.ErrorGeometria("⚠ El plano objetivo es paralelo al avance.")
    return float((pl.origen - origen) @ pl.normal) / coseno


def extruir_avanzado(caras, normal, *, distancia1=None, inicio_desfase=0.0, direccion="un_lado", distancia2=None,
                     conicidad1=0.0, conicidad2=0.0, medida_simetrica="mitad", delgado=None, aristas=None,
                     hasta=None, hasta_modo="cara", hasta_desfase=0.0, hasta_caja=None, inicio_plano=None,
                     hasta_dueno=None):
    """Extrusión completa de Fusion [SLD-EXTRUDE-SOLID, SLD-REF-EXTRUDE]. Devuelve el sólido herramienta.

    - Inicio: plano del perfil desplazado `inicio_desfase` según la normal (Start = Offset), o `inicio_plano`
      (`geo.Plano` inclinado, Start = Object): el perfil se proyecta sobre él a lo largo de la normal.
    - Dirección: "un_lado" (distancia1 con signo), "dos_lados" (distancia1 hacia +n y distancia2 hacia -n,
      cada uno con su conicidad) o "simetrica" (`medida_simetrica` "mitad" = distancia1 a cada lado,
      "total" = distancia1 en total).
    - Conicidad: ángulo de inclinación en grados; positivo = se ensancha.
    - Delgada: `delgado={"espesor": t, "ubicacion": "lado1"|"lado2"|"centro"}`; con perfiles cerrados (caras)
      o abiertos (`aristas`, una o varias cadenas en el plano del boceto; lado1 = izquierda de la curva
      mirando desde +n).
    - Extensión "Al objeto" (lado 1): `hasta` = cara (plana o curva) o cuerpo; `hasta_modo` "cara" | "cuerpo"
      (hasta las caras del cuerpo) | "a_traves" (atraviesa el cuerpo) | "adyacentes" (cara y vecinas de
      `hasta_dueno`, su forma dueña); `hasta_desfase` corre el final.
    - Extensión "Todo": `hasta_caja` = caja envolvente ((x0,y0,z0),(x1,y1,z1)) de los cuerpos visibles.
    """
    n = _unit(normal, "normal de extrusión")
    caras = _caras_de(caras)
    abiertas = _cadenas(aristas) if aristas is not None else []
    if not caras and not abiertas:
        raise geo.ErrorGeometria("Elegí al menos un perfil para extruir.")
    if abiertas and not delgado:
        raise geo.ErrorGeometria("⚠ Perfil abierto: solo extrusión delgada.")
    if delgado and caras:
        caras = _bandas_cerradas(caras, float(delgado["espesor"]), delgado.get("ubicacion", "lado1"))
    if inicio_plano is not None:      # después de las bandas: el espesor de la pared se mide en el plano del perfil
        caras = [geo.proyectar_sobre_plano(c, n, inicio_plano) for c in caras]
        abiertas = [geo.proyectar_sobre_plano(w, n, inicio_plano) for w in abiertas]
    if direccion not in ("un_lado", "dos_lados", "simetrica"):
        raise geo.ErrorGeometria(f"Dirección de extrusión desconocida: {direccion}")
    base = float(inicio_desfase)
    inicios = [_trasladar(f, n * base) for f in caras + abiertas]
    origen = np.mean([geo.centro_masa(f, superficie=True) if f.ShapeType() == TopAbs_FACE else
                      np.mean(_extremos(_aristas_de(f)[0]), axis=0) for f in inicios], axis=0)
    holgura = _MARGEN
    if inicio_plano is not None:   # la base inclinada no está toda a la altura de `origen`: pasar de largo desde toda
        tramos = [_caja_proyectada(f, origen, n) for f in inicios]
        holgura += max(h for _, h in tramos) - min(lo for lo, _ in tramos)

    if hasta_caja is not None:                       # extensión "Todo"
        lo, hi = _proyectar_caja(hasta_caja, origen, n)
        signo = -1.0 if (distancia1 is not None and distancia1 < 0) else 1.0
        if direccion == "un_lado":
            signo = lado_todo(lo, hi, signo)
            lados = [(signo * ((hi if signo > 0 else -lo) + holgura), conicidad1)]
        else:
            lados = [(max(hi, 0.0) + holgura, conicidad1), (min(lo, 0.0) - holgura, conicidad2)]
        return _validar(_herramienta_extrusion(caras, abiertas, n, base, lados, delgado), "Extrusión")

    if hasta is not None:                            # extensión "Al objeto" en el lado 1
        if direccion == "dos_lados" and distancia2:  # 0 = sin lado 2
            geo.exigir_longitud(distancia2, "La distancia del lado 2")
        es_cara = hasta.ShapeType() == TopAbs_FACE
        plano_obj = geo.plano_de_cara(TopoDS.Face(hasta)) if es_cara else None
        if hasta_modo == "adyacentes":
            if not es_cara:
                raise geo.ErrorGeometria("⚠ Hasta caras adyacentes necesita una cara.")
        # plano paralelo al perfil: alcanza una distancia (con la base inclinada no: la tapa saldría inclinada)
        paralelo = plano_obj is not None and inicio_plano is None and abs(float(n @ plano_obj.normal)) > 1 - 1e-9
        if paralelo:
            d = _distancia_a_plano(origen, n, TopoDS.Face(hasta))
            fin = d + math.copysign(1.0, d) * hasta_desfase    # B-484: positivo = más lejos, negativo = más cerca
            if fin * d <= 0:
                num = [f"{x:g}".replace(".", ",") for x in (hasta_desfase, abs(d))]
                raise geo.ErrorGeometria(f"⚠ El desfase deja el objeto a {num[1]} mm.")
            d = fin
            lados1 = [(d, conicidad1)]
            herr = None
            if hasta_modo == "adyacentes" and hasta_dueno is not None:
                # No alargar la conicidad más allá del límite si la cara ya cubre toda la tapa real.
                try:
                    herr = _herramienta_extrusion(caras, abiertas, n, base, lados1, delgado)
                    tapas = [c for c in _caras_de(herr) if (pl := geo.plano_de_cara(c)) is not None
                             and abs(float(n @ pl.normal)) > 1 - 1e-9
                             and abs(float((pl.origen - origen) @ n) - d) < 1e-7]
                    limite = _trasladar(hasta, n * math.copysign(1.0, d) * hasta_desfase) if hasta_desfase else hasta
                    paralelo = bool(tapas) and geo.area(geo.booleano(geo.compuesto(tapas), limite, "cortar")) < 1e-7
                except geo.ErrorGeometria:
                    paralelo = False
                if paralelo:
                    lados1 = []
        if not paralelo:
            if hasta_modo == "adyacentes" and hasta_dueno is not None:
                hasta = _limite_adyacente(hasta, hasta_dueno)
                plano_obj = None
            lo, hi = _caja_proyectada(hasta, origen, n)
            signo = -1.0 if (distancia1 is not None and distancia1 < 0) or (hi <= 0 < -lo) else 1.0
            objeto = hasta
            if hasta_desfase:                        # B-484: hacia el lado de la extrusión, no siempre hacia +n
                objeto = _trasladar(hasta, n * signo * hasta_desfase)
                lo, hi = _caja_proyectada(objeto, origen, n)
            alcance = (hi if signo > 0 else -lo) + holgura
            if alcance <= holgura:
                raise geo.ErrorGeometria("El objeto está del otro lado del perfil.")
            largo = _herramienta_extrusion(caras, abiertas, n, base, [(signo * alcance, conicidad1)], delgado)
            herr = _recortar_hasta(largo, inicios, objeto, hasta_modo, plano_obj, origen)
            if hasta_modo == "adyacentes":
                # Ninguna parte puede pasar de largo por fuera del parche de caras límite.
                extremo = hi + holgura / 2 if signo > 0 else lo - holgura / 2
                tam = 2 * math.dist(*geo.caja_envolvente(largo))
                tapa = BRepBuilderAPI_MakeFace(gp_Pln(_pnt(origen + n * extremo), _gdir(n)),
                                               -tam, tam, -tam, tam).Face()
                if geo.se_tocan(herr, tapa):
                    raise geo.ErrorGeometria("⚠ El límite «adyacentes» no cubre el perfil.")
            lados1 = []
        lados2 = []
        if direccion == "dos_lados" and distancia2:
            lados2 = [(-abs(distancia2), conicidad2)]
        elif direccion == "simetrica":
            raise geo.ErrorGeometria("⚠ «Al objeto» no va con dirección simétrica.")
        partes = [herr] if herr is not None else []
        if lados1 or lados2:
            partes.append(_herramienta_extrusion(caras, abiertas, n, base, lados1 + lados2, delgado))
        return _validar(_unir(partes), "Extrusión")

    if distancia1 is None:
        raise geo.ErrorGeometria("Falta la distancia de extrusión.")
    if direccion == "dos_lados" and distancia2 is None:
        raise geo.ErrorGeometria("Falta la distancia del lado 2.")
    geo.exigir_distancias_extrusion(direccion, distancia1, distancia2, medida_simetrica)
    if direccion == "un_lado":
        lados = [(float(distancia1), conicidad1)]
    elif direccion == "dos_lados":
        lados = [(abs(distancia1), conicidad1), (-abs(distancia2), conicidad2)]
    else:
        if medida_simetrica not in ("mitad", "total"):
            raise geo.ErrorGeometria(f"Medida simétrica desconocida: {medida_simetrica}")
        h = abs(distancia1) if medida_simetrica == "mitad" else abs(distancia1) / 2
        lados = [(h, conicidad1), (-h, conicidad1)]
    return _validar(_herramienta_extrusion(caras, abiertas, n, base, lados, delgado), "Extrusión")


def _limite_adyacente(cara, dueno):
    """Extruir › Hasta caras adyacentes: parche de la cara elegida y las que comparten sus aristas."""
    from .solidos_modificar import _ancestros, _padres
    mapa = _ancestros(dueno, TopAbs_EDGE, TopAbs_FACE)
    caras = [cara]
    for arista in _aristas_de(cara):
        for vecina in _padres(mapa, arista):
            if not any(vecina.IsSame(c) for c in caras):
                caras.append(TopoDS.Face(vecina))
    return geo.compuesto(caras)


def _recortar_hasta(herr, inicios, objeto, modo, plano_obj, origen):
    """Recorta una herramienta larga para que termine en el objeto (cara o cuerpo)."""
    if objeto.ShapeType() == TopAbs_FACE or modo == "adyacentes":
        if plano_obj is not None:   # plano oblicuo: semiespacio del lado del perfil
            semi = BRepPrimAPI_MakeHalfSpace(cara_de_plano(plano_obj, 1e5), _pnt(origen)).Solid()
            piezas = _piezas_que_tocan(geo.booleano(herr, semi, "intersecar"), inicios)
        else:                       # cara curva: se parte la herramienta con la cara
            sp = BRepAlgoAPI_Splitter()
            if modo == "adyacentes":
                sp.SetNonDestructive(True)
            args, herramientas = List_TopoDS_Shape(), List_TopoDS_Shape()
            args.Append(herr)
            for cara in _caras_de(objeto):
                herramientas.Append(cara)
            sp.SetArguments(args)
            sp.SetTools(herramientas)
            sp.Build()
            if not sp.IsDone():
                raise geo.ErrorGeometria("⚠ No se pudo cortar la extrusión con la cara.")
            piezas = _piezas_que_tocan(sp.Shape(), inicios)
            if len(geo.solidos(sp.Shape())) < 2:
                if modo == "adyacentes":
                    raise geo.ErrorGeometria("⚠ El límite «adyacentes» no cubre el perfil.")
                raise geo.ErrorGeometria("⚠ La extrusión no llega entera a la cara.")
        return _unir(piezas)
    if modo not in ("cara", "cuerpo", "a_traves", "llega"):
        raise geo.ErrorGeometria(f"Modo de extensión desconocido: {modo}")
    piezas = _piezas_que_tocan(geo.booleano(herr, objeto, "cortar"), inicios)
    if modo == "llega":
        piezas = [geo.booleano(p, objeto, "intersecar") for p in piezas]
        if all(geo.esta_vacia(p) for p in piezas):
            raise geo.ErrorGeometria("El perfil queda dentro del cuerpo objetivo.")
        return _unir(piezas)
    if modo == "a_traves":
        piezas.append(geo.booleano(herr, objeto, "intersecar"))
    if not piezas:
        raise geo.ErrorGeometria("El perfil queda dentro del cuerpo objetivo.")
    return _unir(piezas)


_registrar_tema(globals())
