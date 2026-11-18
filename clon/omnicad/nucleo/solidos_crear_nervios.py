"""Sólidos › Crear: nervios."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import (
    _alambre, _aristas_de, _cadenas, _caras_de, _engrosar_lamina, _es_cerrado, _gdir, _gvec, _perpendicular,
    _piezas_que_tocan, _pnt, _punto_en, _rayo, _trasladar, _unificar, _unir, _unit, _validar,
)

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BRepAdaptor_Surface, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeVertex, BRepOffsetAPI_DraftAngle,
        BRepPrimAPI_MakePrism, GeomAbs_Plane, TopoDS, gp_Pln,
    )


# ================================================================ 5. nervio y red
def _extender_extremos(alambre, largo):
    """Prolonga por la tangente los dos extremos de un alambre abierto (Extend Curves de Fusion)."""
    if _es_cerrado(alambre):
        return alambre
    p0, t0 = _punto_en(alambre, 0.0)
    p1, t1 = _punto_en(alambre, 1.0)
    return _alambre([BRepBuilderAPI_MakeEdge(_pnt(p0 - t0 * largo), _pnt(p0)).Edge()] + _aristas_de(alambre)
                    + [BRepBuilderAPI_MakeEdge(_pnt(p1), _pnt(p1 + t1 * largo)).Edge()])


def _sentido_hacia_cuerpo(cuerpo, alambre, candidatos, invertir, *, exigir_cara=True):
    """De los sentidos candidatos, el que choca antes con el cuerpo partiendo del medio de la curva. Con `invertir`
    («Cambiar dirección») se toma el contrario, que tiene que dar con una cara si `exigir_cara` (Al siguiente):
    si no, el nervio o la red quedaría colgando en el aire."""
    medio, _ = _punto_en(alambre, 0.5)
    mejor = None
    for d in candidatos:
        choques = [h for h in _rayo(cuerpo, medio, d) if h > 1e-7]
        if choques and (mejor is None or choques[0] < mejor[0]):
            mejor = (choques[0], d)
    if mejor is None:
        raise geo.ErrorGeometria("⚠ Del boceto no se llega al cuerpo.")
    if not invertir:
        return mejor[1]
    opuesto = -mejor[1]
    if exigir_cara and not [h for h in _rayo(cuerpo, medio, opuesto) if h > 1e-7]:
        raise geo.ErrorGeometria("⚠ Invertido no llega: mové el boceto.")
    return opuesto


def _sentido_curva(cuerpo, w, n, invertir, red, exigir_cara):
    """Sentido en que crece la pared desde la curva `w`: la red, por la normal del plano; el nervio, dentro del plano y
    perpendicular a la cuerda. Hacia la cara más cercana del cuerpo (la contraria con `invertir`)."""
    if red:
        candidatos = (-n, n)
    else:
        m = _unit(np.cross(n, _punto_en(w, 1.0)[0] - _punto_en(w, 0.0)[0]), "cuerda de la curva")
        candidatos = (m, -m)
    return _sentido_hacia_cuerpo(cuerpo, w, candidatos, invertir, exigir_cara=exigir_cara)


def sentido_crecimiento(cuerpo, aristas_curvas, normal_plano, invertir=False, *, red=False):
    """(punto medio de la primera curva, sentido en que crece) del Nervio o la Red, el mismo que usan `nervio` y
    `red`: para que el asa de la profundidad apunte adonde va la pared (B-219)."""
    w = _cadenas(aristas_curvas)[0]
    return _punto_en(w, 0.5)[0], _sentido_curva(cuerpo, w, _unit(normal_plano, "normal del plano del boceto"),
                                                invertir, red, exigir_cara=False)


def _diagonal(forma):
    bb = geo.caja_envolvente(forma)
    return float(np.linalg.norm(np.subtract(bb[1], bb[0])))


def _hasta_el_cuerpo(bruto, cuerpo, curvas, direccion, largo, que, profundidad):
    """Red de Fusion: limita las prolongaciones a la sombra del cuerpo hacia el perfil, sin cortar el inicio.
    El corte volumétrico conserva la llegada oblicua en todo el grosor y las uniones entre curvas."""
    sombras = [cuerpo]
    for cara in _caras_de(cuerpo):
        plano = geo.plano_de_cara(cara)
        if plano is not None and float(plano.normal @ direccion) >= -1e-7:
            continue
        prisma = BRepPrimAPI_MakePrism(cara, _gvec(-direccion * largo)).Shape()
        volumen = geo.volumen(prisma)
        if abs(volumen) > 1e-9:
            sombras.append(prisma if volumen > 0 else prisma.Reversed())
    bruto = geo.booleano(bruto, _unir(sombras), "intersecar")
    piezas = _piezas_que_tocan(geo.booleano(bruto, cuerpo, "cortar"), curvas)
    if not piezas:
        raise geo.ErrorGeometria(f"{que}: la curva queda dentro del cuerpo.")
    resultado = _unir(piezas)
    if profundidad is None and not geo.se_tocan(resultado, cuerpo, 1e-4):
        raise geo.ErrorGeometria(f"⚠ {que}: no llega al cuerpo.")
    return _validar(resultado, que)


def _lamina_hasta_el_cuerpo(lamina, cuerpo, curvas, finales, que, profundidad):
    """Al siguiente de Nervio/Red de Fusion: recorta la lámina antes de darle espesor.
    El extremo auxiliar lejano no puede quedar en el resultado de «Al siguiente»."""
    piezas = [c for c in _caras_de(geo.booleano(lamina, cuerpo, "cortar"))
              if any(geo.se_tocan(c, w, 1e-5) for w in curvas)]
    if not piezas:
        raise geo.ErrorGeometria(f"{que}: la curva queda dentro del cuerpo.")
    resultado = geo.compuesto(piezas)
    if profundidad is None and (not geo.se_tocan(resultado, cuerpo, 1e-4)
                               or any(geo.se_tocan(resultado, f, 1e-5) for f in finales)):
        raise geo.ErrorGeometria(f"⚠ {que}: no llega al cuerpo.")
    return resultado


def _engrosar_nervio(recorte, cuerpo, n, lo, hi, profundidad):
    """Engrosa el Nervio de Fusion y lleva sus caras de llegada planas al contacto oblicuo real."""
    llegadas = []
    if profundidad is None:
        for cara in _caras_de(cuerpo):
            plano = geo.plano_de_cara(cara)
            if plano is not None and 1e-7 < abs(float(plano.normal @ n)) < 1 - 1e-7:
                llegadas.append((cara, -math.asin(float(plano.normal @ n))))
    if not llegadas:
        return _unir([BRepPrimAPI_MakePrism(_trasladar(f, n * lo), _gvec(n * (hi - lo))).Shape()
                      for f in _caras_de(recorte)])
    solidos = []
    for cara in _caras_de(recorte):
        prisma = BRepPrimAPI_MakePrism(cara, _gvec(n * (hi - lo)))
        forma = prisma.Shape()
        ajuste = BRepOffsetAPI_DraftAngle(forma)
        neutro = gp_Pln(_pnt(geo.plano_de_cara(cara).origen - n * lo), _gdir(n))
        ajustadas = False
        for arista in _aristas_de(cara):
            for llegada, angulo in llegadas:
                if not _aristas_de(geo.booleano(arista, llegada, "intersecar")):
                    continue
                for lateral in prisma.Generated(arista):
                    ajuste.Add(TopoDS.Face(lateral), _gdir(n), angulo, neutro, False)
                    if not ajuste.AddDone():
                        raise geo.ErrorGeometria("⚠ Nervio: no se pudo ajustar la cara oblicua.")
                    ajustadas = True
                break
        if ajustadas:
            ajuste.Build()
            if not ajuste.IsDone():
                raise geo.ErrorGeometria("⚠ Nervio: no se pudo ajustar la llegada.")
            forma = _validar(ajuste.Shape(), "Nervio con llegada oblicua")
        solidos.append(_trasladar(forma, n * lo))
    return _unir(solidos)


def _desmoldear_pared(bruto, direccion, angulo, origen, *, recortado):
    """Desmoldeo del Nervio/Red de Fusion: inclina los laterales originales sobre la pared `recortado`.
    El plano neutro pasa por `origen` y es normal a la extracción `direccion`. Con extracción por defecto,
    un ángulo positivo engorda la base; uno negativo la afina."""
    from .solidos_modificar import _cara_dentro_de, desmoldeo
    d = _unit(direccion, "dirección de desmoldeo")
    laterales = []
    for cara in _caras_de(bruto):
        if BRepAdaptor_Surface(cara).GetType() == GeomAbs_Plane:
            normal = _unit(geo.plano_de_cara(cara).normal)
            if abs(float(normal @ d)) > 1e-6:           # tapas y fondos: no se inclinan
                continue
        laterales.append(cara)
    # El prisma auxiliar puede cruzarse lejos del cuerpo; inclinar solo la pared real y sus caras originales.
    laterales = [c for c in _caras_de(recortado) if any(_cara_dentro_de(c, f) for f in laterales)]
    plano_neutro = geo.Plano.desde_marco(origen, d, _perpendicular(d))
    return desmoldeo(recortado, laterales, d, angulo, plano_neutro)


def nervio(cuerpo, aristas_curva, normal_plano, espesor, *, profundidad=None, direccion="simetrica",
           invertir=False, extender=True, angulo_desmoldeo=0.0, direccion_desmoldeo=None, invertir_desmoldeo=False):
    """Nervio (Rib) de Fusion [SLD-RIB]: pared delgada que crece desde una o varias curvas abiertas, PARALELA al
    plano del boceto y perpendicular a la cuerda de cada curva, hasta las caras más cercanas del cuerpo ("To Next")
    o una `profundidad` — un nervio por curva, unidos en un solo paso, como en Fusion. El espesor se mide
    perpendicular al plano: "simetrica" (mitad a cada lado), "lado1" (hacia +normal) o "lado2". `invertir` cambia el
    sentido de crecimiento. Devuelve solo el nervio, ya recortado contra el cuerpo (la unión la hace la capa de
    operaciones). `angulo_desmoldeo` (Draft Angle) positivo afina el nervio hacia su borde libre; el negativo
    invierte el efecto. `direccion_desmoldeo` (Draft Pull Direction) es la extracción (por defecto, del cuerpo hacia
    la curva). El plano neutro pasa por el punto medio de cada curva: allí se conserva el espesor, también con una
    extracción oblicua."""
    n = _unit(normal_plano, "normal del plano del boceto")
    cadenas = _cadenas(aristas_curva)
    if not cadenas or any(_es_cerrado(w) for w in cadenas):
        raise geo.ErrorGeometria("El nervio necesita una curva abierta.")
    if espesor <= 0:
        raise geo.ErrorGeometria("El espesor del nervio debe ser positivo.")
    lo, hi = {"simetrica": (-espesor / 2, espesor / 2), "lado1": (0.0, espesor),
              "lado2": (-espesor, 0.0)}.get(direccion, (None, None))
    if lo is None:
        raise geo.ErrorGeometria(f"Dirección de espesor desconocida: {direccion}")
    largo_max = 2 * _diagonal(cuerpo)
    nervios = []
    for w in cadenas:
        m = _sentido_curva(cuerpo, w, n, invertir, False, exigir_cara=profundidad is None)
        w_ext = _extender_extremos(w, largo_max) if extender else w
        region = _unificar(BRepPrimAPI_MakePrism(w_ext, _gvec(m * (profundidad or largo_max))).Shape())
        recorte = _lamina_hasta_el_cuerpo(region, cuerpo, [w], [_trasladar(w_ext, m * largo_max)], "Nervio",
                                          profundidad)
        recortado = _engrosar_nervio(recorte, cuerpo, n, lo, hi, profundidad)
        recortado = _validar(geo.booleano(recortado, cuerpo, "cortar"), "Nervio")
        if abs(angulo_desmoldeo) > 1e-9:
            bruto = _unir([BRepPrimAPI_MakePrism(_trasladar(f, n * lo), _gvec(n * (hi - lo))).Shape()
                           for f in _caras_de(region)])
            pull = -m if direccion_desmoldeo is None else _unit(direccion_desmoldeo, "dirección de desmoldeo")
            if float(pull @ m) > 0:             # la extracción va del cuerpo hacia el borde libre (la curva)
                pull = -pull
            if invertir_desmoldeo:              # Flip Direction de Draft Pull Direction
                pull = -pull
            recortado = _desmoldear_pared(bruto, pull, angulo_desmoldeo, _punto_en(w, 0.5)[0], recortado=recortado)
        nervios.append(recortado)
    return nervios[0] if len(nervios) == 1 else _validar(_unir(nervios), "Nervio")   # B-214: un nervio por curva


def red(cuerpo, aristas_curvas, normal_plano, espesor, profundidad=None, *, direccion="simetrica",
        invertir=False, extender=True, angulo_desmoldeo=0.0):
    """Red (Web) de Fusion [SLD-WEB]: una o varias curvas abiertas se extruyen PERPENDICULARES al plano del
    boceto hasta las caras más cercanas del cuerpo ("To Next") o una `profundidad`; el espesor va en el plano,
    a los dos lados de la curva ("simetrica") o a uno ("lado1" = izquierda de la curva mirando desde +normal).
    `extender` prolonga las curvas hasta el cuerpo (Extend Curves). `angulo_desmoldeo` (Draft Angle) afina la red
    hacia su borde libre. Devuelve el sólido de la red ya recortado."""
    n = _unit(normal_plano, "normal del plano del boceto")
    cadenas = _cadenas(aristas_curvas)
    if not cadenas or any(_es_cerrado(w) for w in cadenas):
        raise geo.ErrorGeometria("La red necesita curvas abiertas.")
    if espesor <= 0:
        raise geo.ErrorGeometria("El espesor de la red debe ser positivo.")
    d = _sentido_curva(cuerpo, cadenas[0], n, invertir, True, exigir_cara=profundidad is None)
    # Engrosar la lámina con +t va a la izquierda de la curva mirando desde el sentido de extrusión.
    s = 1.0 if float(d @ n) > 0 else -1.0
    espesores = {"simetrica": [espesor / 2, -espesor / 2], "lado1": [s * espesor],
                 "lado2": [-s * espesor]}.get(direccion)
    if espesores is None:
        raise geo.ErrorGeometria(f"Dirección de espesor desconocida: {direccion}")
    largo_max = 2 * _diagonal(cuerpo)
    solidos = []
    for w in cadenas:
        w_ext = _extender_extremos(w, largo_max) if extender else w
        lamina = BRepPrimAPI_MakePrism(w_ext, _gvec(d * (profundidad or largo_max))).Shape()
        solidos += [_engrosar_lamina(lamina, e) for e in espesores]
    bruto = _unir(solidos)
    recortado = _hasta_el_cuerpo(bruto, cuerpo, cadenas, d, largo_max, "Red", profundidad)
    if abs(angulo_desmoldeo) > 1e-9:
        return _desmoldear_pared(bruto, -d, angulo_desmoldeo, _punto_en(cadenas[0], 0.5)[0], recortado=recortado)
    return recortado


def unir_con_empalme(cuerpo, pieza, radio):
    """Une una red al cuerpo y redondea (Fillet Radius de la Red) las aristas CÓNCAVAS donde se encuentran."""
    from .solidos_modificar import empalme_reglas
    unido = geo.booleano(cuerpo, pieza, "unir")
    if radio <= 0:
        return unido
    de_la_red = [c for c in geo.caras(unido)
                 if geo.se_tocan(BRepBuilderAPI_MakeVertex(_pnt(geo.centro_masa(c, True))).Vertex(), pieza, 1e-5)]
    if not de_la_red:
        raise geo.ErrorGeometria("⚠ No se hallaron las caras de la red.")
    return empalme_reglas(unido, de_la_red, radio=radio, tipo="todas", redondeos="empalmes")


_registrar_tema(globals())
