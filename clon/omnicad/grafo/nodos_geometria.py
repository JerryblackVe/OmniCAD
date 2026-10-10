# -*- coding: utf-8 -*-
"""
Nodos de geometría (GH3) sobre el núcleo (`nucleo/geometria.py` y compañía): curvas planas, primitivas, mover,
rotar, escalar, simetría, booleanas y medidas. Cada nodo es una función pura: recibe formas OCC, puntos y números y
devuelve formas nuevas (nunca modifica las que recibe).

Equivalencias con Fusion: caja / cilindro / esfera / toroide = CREAR › primitivas; mover y rotar = MODIFICAR › Mover;
escalar = MODIFICAR › Escala; simetría = CREAR › Simetría; unir / cortar / intersecar = MODIFICAR › Combinar;
volumen, área, caja envolvente y centro de masa = INSPECCIONAR › Propiedades; extruir = CREAR › Extruir (de un perfil).
"""
import math

from ..nucleo import geometria as geo
from ..timeline.parametros import ANGULO, LONGITUD
from .nodos import E, ErrorNodo, S, nodo
from .tipos import Curva, Plano, _cruz, _norma

ORIGEN = (0.0, 0.0, 0.0)
EJE_Z = (0.0, 0.0, 1.0)


def plano_geo(plano):
    """Plano del grafo → `geo.Plano` del núcleo."""
    return geo.Plano.desde_marco(plano.origen, plano.z, plano.x, "Grafo")


def aristas(curva):
    """Aristas OCC de una curva del grafo."""
    from ..nucleo import perfiles
    salida = [e for _cid, e in perfiles.aristas_boceto(list(curva.primitivas), plano_geo(curva.plano))]
    if not salida:
        raise ErrorNodo("La curva es degenerada (largo o radio nulo).")
    return salida


def _positivo(valor, que):
    if not valor > 0:
        raise ErrorNodo(f"{que} tiene que ser mayor que 0 (llegó {valor:g}).")
    return valor


# ================================================================ curvas
@nodo("linea", "Línea", "curvas", "Segmento recto de a a b.",
      [E("a", "punto", ORIGEN), E("b", "punto", (10.0, 0.0, 0.0))], [S("curva", "curva")])
def _linea(a, b):
    d = tuple(y - x for x, y in zip(a, b, strict=True))
    largo = _norma(d)
    if largo < 1e-9:
        raise ErrorNodo("Los dos extremos de la línea coinciden.")
    u = tuple(c / largo for c in d)
    ref = EJE_Z if abs(u[2]) < 0.9 else (1.0, 0.0, 0.0)
    normal = _cruz(u, ref)
    plano = Plano.desde(a, normal, u)
    return Curva(plano, [("linea", "l", (0.0, 0.0), (largo, 0.0))], False, f"línea de {largo:g} mm")


@nodo("circulo", "Círculo", "curvas", "Círculo de radio dado con centro en el origen del plano.",
      [E("plano", "plano", "XY"), E("radio", "numero", 5.0, unidad=LONGITUD)], [S("curva", "curva")])
def _circulo(plano, radio):
    _positivo(radio, "El radio")
    return Curva(plano, [("circulo", "c", (0.0, 0.0), radio)], True, f"círculo R{radio:g}")


@nodo("rectangulo", "Rectángulo", "curvas", "Rectángulo de ancho (eje x del plano) por largo (eje y), centrado en el "
      "origen del plano.",
      [E("plano", "plano", "XY"), E("ancho", "numero", 10.0, unidad=LONGITUD),
       E("largo", "numero", 10.0, unidad=LONGITUD)], [S("curva", "curva")])
def _rectangulo(plano, ancho, largo):
    _positivo(ancho, "El ancho")
    _positivo(largo, "El largo")
    w, h = ancho / 2, largo / 2
    esquinas = [(-w, -h), (w, -h), (w, h), (-w, h)]
    lados = [("linea", f"r{i}", esquinas[i], esquinas[(i + 1) % 4]) for i in range(4)]
    return Curva(plano, lados, True, f"rectángulo {ancho:g} × {largo:g}")


@nodo("largo_curva", "Largo de curva", "curvas", "Largo de la curva (mm).", [E("curva", "curva")],
      [S("largo", "numero")])
def _largo_curva(curva):
    return math.fsum(geo.longitud(e) for e in aristas(curva))


@nodo("extruir", "Extruir", "curvas",
      "Sólido que sale de extruir la región encerrada por una curva cerrada, en la normal de su plano (distancia "
      "negativa = hacia el otro lado).",
      [E("curva", "curva"), E("distancia", "numero", 10.0, unidad=LONGITUD)], [S("cuerpo", "cuerpo")])
def _extruir(curva, distancia):
    from ..nucleo import perfiles
    if not curva.cerrada:
        raise ErrorNodo("Solo se extruye una curva cerrada (círculo, rectángulo…).")
    if abs(distancia) < 1e-9:
        raise ErrorNodo("La distancia de extrusión no puede ser 0.")
    regiones = perfiles.detectar(list(curva.primitivas), plano_geo(curva.plano))
    if not regiones:
        raise ErrorNodo("La curva no encierra ninguna región.")
    return geo.extruir([r.cara for r in regiones], curva.plano.z, distancia)


# ================================================================ primitivas
@nodo("caja", "Caja", "solidos", "Caja de ancho (X) × largo (Y) × alto (Z); «centro» es el centro de la base, como en "
      "create_box.",
      [E("centro", "punto", ORIGEN), E("ancho", "numero", 10.0, unidad=LONGITUD),
       E("largo", "numero", 10.0, unidad=LONGITUD), E("alto", "numero", 10.0, unidad=LONGITUD)],
      [S("cuerpo", "cuerpo")])
def _caja(centro, ancho, largo, alto):
    return geo.caja(ancho, largo, alto, (centro[0] - ancho / 2, centro[1] - largo / 2, centro[2]))


@nodo("cilindro", "Cilindro", "solidos", "Cilindro de radio y alto dados; «base» es el centro de la base y «eje» su "
      "dirección.",
      [E("base", "punto", ORIGEN), E("radio", "numero", 5.0, unidad=LONGITUD),
       E("alto", "numero", 10.0, unidad=LONGITUD), E("eje", "vector", EJE_Z)], [S("cuerpo", "cuerpo")])
def _cilindro(base, radio, alto, eje):
    if _norma(eje) < 1e-12:
        raise ErrorNodo("El eje del cilindro no puede ser nulo.")
    return geo.cilindro(radio, alto, base, eje)


@nodo("esfera", "Esfera", "solidos", "Esfera de radio dado.",
      [E("centro", "punto", ORIGEN), E("radio", "numero", 5.0, unidad=LONGITUD)], [S("cuerpo", "cuerpo")])
def _esfera(centro, radio):
    return geo.esfera(radio, centro)


@nodo("toroide", "Toroide", "solidos", "Toroide (anillo) con radio mayor (al centro del tubo) y radio menor (del "
      "tubo).",
      [E("centro", "punto", ORIGEN), E("radio_mayor", "numero", 10.0, unidad=LONGITUD),
       E("radio_menor", "numero", 2.0, unidad=LONGITUD), E("eje", "vector", EJE_Z)], [S("cuerpo", "cuerpo")])
def _toroide(centro, radio_mayor, radio_menor, eje):
    if _norma(eje) < 1e-12:
        raise ErrorNodo("El eje del toroide no puede ser nulo.")
    return geo.toroide(radio_mayor, radio_menor, centro, eje)


# ================================================================ transformaciones
@nodo("mover", "Mover", "solidos", "El cuerpo desplazado por un vector (una copia: el original no cambia).",
      [E("cuerpo", "cuerpo"), E("vector", "vector", (0.0, 0.0, 10.0))], [S("cuerpo", "cuerpo")])
def _mover(cuerpo, vector):
    return geo.trasladar(cuerpo, vector)


@nodo("rotar", "Rotar", "solidos", "El cuerpo girado un ángulo (grados, regla de la mano derecha) alrededor del eje que "
      "pasa por «centro».",
      [E("cuerpo", "cuerpo"), E("angulo", "numero", 90.0, unidad=ANGULO), E("eje", "vector", EJE_Z),
       E("centro", "punto", ORIGEN)], [S("cuerpo", "cuerpo")])
def _rotar(cuerpo, angulo, eje, centro):
    if _norma(eje) < 1e-12:
        raise ErrorNodo("El eje de rotación no puede ser nulo.")
    return geo.rotar(cuerpo, centro, eje, angulo)


@nodo("escalar", "Escalar", "solidos", "El cuerpo escalado (uniforme) desde «centro».",
      [E("cuerpo", "cuerpo"), E("factor", "numero", 2.0), E("centro", "punto", ORIGEN)], [S("cuerpo", "cuerpo")])
def _escalar(cuerpo, factor, centro):
    from ..nucleo import solidos_modificar
    return solidos_modificar.escalar(cuerpo, centro, factor=factor)


@nodo("simetria", "Simetría", "solidos", "Copia reflejada del cuerpo respecto de un plano.",
      [E("cuerpo", "cuerpo"), E("plano", "plano", "YZ")], [S("cuerpo", "cuerpo")])
def _simetria(cuerpo, plano):
    from ..nucleo import solidos_crear
    return solidos_crear.simetria(cuerpo, plano_geo(plano))


# ================================================================ booleanas
@nodo("unir", "Unir", "solidos", "Une todos los cuerpos de la lista en uno (los que no se tocan quedan como piezas "
      "separadas del mismo resultado).",
      [E("cuerpos", "cuerpo", acceso="lista")], [S("cuerpo", "cuerpo")])
def _unir(cuerpos):
    formas = [c for c in cuerpos if c is not None]
    if not formas:
        raise ErrorNodo("No hay cuerpos para unir.")
    return geo.unir_todos(formas)


@nodo("cortar", "Cortar", "solidos", "Resta del cuerpo todas las herramientas de la lista.",
      [E("cuerpo", "cuerpo"), E("herramientas", "cuerpo", acceso="lista")], [S("cuerpo", "cuerpo")])
def _cortar(cuerpo, herramientas):
    resultado = cuerpo
    for h in herramientas:
        if h is not None:
            resultado = geo.booleano(resultado, h, "cortar")
    if geo.esta_vacia(resultado):
        raise ErrorNodo("El corte no dejó nada del cuerpo.")
    return resultado


@nodo("intersecar", "Intersecar", "solidos", "Lo que tienen en común dos cuerpos.",
      [E("a", "cuerpo"), E("b", "cuerpo")], [S("cuerpo", "cuerpo")])
def _intersecar(a, b):
    resultado = geo.booleano(a, b, "intersecar")
    if geo.esta_vacia(resultado):
        raise ErrorNodo("Los cuerpos no se superponen: la intersección está vacía.")
    return resultado


@nodo("separar", "Separar piezas", "solidos", "Las piezas sólidas sueltas de un cuerpo (p. ej. tras unir cuerpos "
      "que no se tocan).",
      [E("cuerpo", "cuerpo")], [S("piezas", "cuerpo", acceso="lista")])
def _separar(cuerpo):
    return geo.solidos(cuerpo) or [cuerpo]


# ================================================================ medidas
@nodo("volumen", "Volumen", "solidos", "Volumen del cuerpo (mm³).", [E("cuerpo", "cuerpo")],
      [S("volumen", "numero")])
def _volumen(cuerpo):
    return float(geo.volumen(cuerpo))


@nodo("area", "Área", "solidos", "Área de la superficie del cuerpo (mm²).", [E("cuerpo", "cuerpo")],
      [S("area", "numero")])
def _area(cuerpo):
    return float(geo.area(cuerpo))


@nodo("caja_envolvente", "Caja envolvente", "solidos", "Esquinas mínima y máxima de la caja envolvente y su tamaño.",
      [E("cuerpo", "cuerpo")], [S("minimo", "punto"), S("maximo", "punto"), S("tamano", "vector")])
def _caja_envolvente(cuerpo):
    caja = geo.caja_envolvente(cuerpo)
    if caja is None:
        raise ErrorNodo("El cuerpo está vacío: no tiene caja envolvente.")
    p0, p1 = (tuple(float(c) for c in p) for p in caja)
    return p0, p1, tuple(b - a for a, b in zip(p0, p1, strict=True))


@nodo("centro_masa", "Centro de masa", "solidos", "Centro de masa (de volumen) del cuerpo.", [E("cuerpo", "cuerpo")],
      [S("punto", "punto")])
def _centro_masa(cuerpo):
    return tuple(float(c) for c in geo.centro_masa(cuerpo))
