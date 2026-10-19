# -*- coding: utf-8 -*-
"""Consultas y primitivas con paridad verificada en procesos separados."""
from functools import lru_cache

import numpy as np
import omnikernel as k


@lru_cache(maxsize=32)                  # referencias fuertes: pocas, para no retener documentos cerrados
def _propiedades(forma):
    """Volumen, área, centros y validez en una sola pasada: una forma del kernel no cambia (es inmutable)."""
    return forma.propiedades()


def caja(ancho, largo, alto, origen=(0, 0, 0)):
    return k.primitiva("caja", [ancho, largo, alto], origen)


def cilindro(radio, alto, base=(0, 0, 0), eje=(0, 0, 1)):
    return k.primitiva("cilindro", [radio, alto], base, eje)


def volumen(forma):
    return _propiedades(forma)["volumen"] if forma.tipo == "cuerpo" else 0.0


volumen_exacto = volumen


def area(forma):
    return _propiedades(forma)["area"] if forma.tipo == "cuerpo" else forma.firma().get("area", 0.0)


def centro_masa(forma, superficie=False):
    if forma.tipo == "cuerpo":
        return tuple(_propiedades(forma)["centro_superficie" if superficie else "centro"])
    return tuple(forma.firma()["centro"])


def caja_envolvente(forma):
    if forma is None or forma.IsNull():
        return None
    if forma.tipo != "cuerpo":
        from .. import motor
        motor.sin_soporte("la caja envolvente de una cara, arista o vértice sueltos")
    return _caja(forma)


@lru_cache(maxsize=32)
def _caja(forma):
    return tuple(tuple(p) for p in forma.caja())


def es_valida(forma):
    return _propiedades(forma)["valida"]


def caras(forma):
    return forma.subformas("cara")


def solidos(forma):
    return forma.subformas("solido")


def esta_vacia(forma):
    return forma is None or forma.IsNull()


def teselar_por_cara(forma, deflexion=0.05, angular=0.3, rehacer=False):
    m = forma.teselar(deflexion, angular)
    v, indices = m["vertices"].reshape(-1, 3), m["indices"].reshape(-1, 3)
    if forma.tipo == "cara":            # el kernel ya filtró los triángulos de esa cara
        return [(forma, v[indices])]
    return [(cara, v[indices[m["caras"] == i]]) for i, cara in enumerate(caras(forma))]


def teselar(forma, deflexion=0.05, angular=0.3, rehacer=False):
    m = forma.teselar(deflexion, angular)
    indices = m["indices"].reshape(-1, 3)
    vertices = m["vertices"].reshape(-1, 3)[indices].reshape(-1, 3)
    normales = m["normales"].reshape(-1, 3)[indices].reshape(-1, 3)
    return vertices, normales


def teselar_aparte(forma, deflexion=0.05, angular=0.3):
    return teselar(forma, deflexion, angular)


def polilineas_aristas(forma, deflexion=0.05):
    m = forma.teselar(deflexion)
    puntos, limites = m["aristas"].reshape(-1, 3), m["offsets_aristas"]
    return [puntos[a:b] for a, b in zip(limites[:-1], limites[1:], strict=True)]


def toroide(radio_mayor, radio_menor, centro=(0, 0, 0), eje=(0, 0, 1)):
    from ..geometria import ErrorGeometria
    if radio_menor <= 0 or radio_mayor <= radio_menor:
        raise ErrorGeometria("El toroide necesita radio mayor > radio menor > 0.")
    return k.primitiva("toroide", [radio_mayor, radio_menor], centro, eje)


def transformar(forma, matriz):
    return forma.transformar(np.asarray(matriz, float).tolist())


def trasladar(forma, vector):
    m = np.eye(4)
    m[:3, 3] = vector
    return transformar(forma, m)


def matriz_rotacion(punto, eje, radianes):
    """Matriz 4x4 del giro alrededor de la recta (punto, eje), regla de la mano derecha (Rodrigues): solo arma la
    transformación; el kernel la aplica."""
    e = np.asarray(eje, float) / np.linalg.norm(eje)
    x = np.array([[0, -e[2], e[1]], [e[2], 0, -e[0]], [-e[1], e[0], 0]])
    r = np.eye(3) + np.sin(radianes) * x + (1 - np.cos(radianes)) * x @ x
    m = np.eye(4)
    m[:3, :3], m[:3, 3] = r, np.asarray(punto, float) - r @ np.asarray(punto, float)
    return m


def rotar(forma, punto, eje, angulo_grados):
    return transformar(forma, matriz_rotacion(punto, eje, np.radians(angulo_grados)))


def booleano(objetivo, herramienta, operacion):
    from ..geometria import ErrorGeometria
    if operacion not in ("unir", "cortar", "intersecar"):
        raise ErrorGeometria(f"Operación booleana desconocida: {operacion}")
    return objetivo.booleano(herramienta, operacion)


def unir_todos(formas):
    from ..geometria import ErrorGeometria
    formas = [f for f in formas if f is not None]
    if not formas:
        raise ErrorGeometria("No hay geometría para unir.")
    resultado = formas[0]
    for f in formas[1:]:
        resultado = booleano(resultado, f, "unir")
    return resultado


def extruir(caras, normal, distancia, simetrica=False):
    from .. import geometria as comun
    comun.exigir_longitud.__wrapped__(distancia, "La distancia de extrusión")
    n = np.asarray(normal, float) / np.linalg.norm(normal)
    solidos = []
    for cara in caras:
        if simetrica:
            solidos.append(trasladar(cara.extruir((n * abs(distancia)).tolist()), -n * abs(distancia) / 2))
        else:
            solidos.append(cara.extruir((n * distancia).tolist()))
    return unir_todos(solidos)


def revolver(caras, punto_eje, dir_eje, angulo_grados):
    from ..geometria import ErrorGeometria
    if abs(angulo_grados) < 1e-9:
        raise ErrorGeometria("El ángulo de revolución no puede ser cero.")
    angulo = max(-360.0, min(360.0, angulo_grados))
    eje = np.asarray(dir_eje, float) * (1 if angulo > 0 else -1)      # el kernel gira solo en sentido positivo
    return unir_todos([c.revolver(list(map(float, punto_eje)), eje.tolist(), abs(angulo)) for c in caras])


def esfera(radio, centro=(0, 0, 0)):
    from ..geometria import ErrorGeometria
    if radio <= 0:
        raise ErrorGeometria("El radio de la esfera debe ser positivo.")
    return k.primitiva("esfera", [radio], centro)


def se_tocan(a, b, tolerancia=1e-6):
    """Contacto, superposición o una forma entera dentro de un sólido de la otra (FK-008)."""
    return a.distancia(b) <= tolerancia


def compuesto(formas):
    formas = list(formas)
    if any(f.tipo != "cuerpo" for f in formas):
        from .. import motor
        motor.sin_soporte("un compuesto con caras, aristas o vértices sueltos")
    return k.compuesto(formas)


def plano_de_cara(cara):
    f = cara.firma()
    if f["geom"] != "plano":
        return None
    from .. import geometria as comun
    return comun.plano_desde_normal(f["normal"], f["centro"])


def polilinea_arista(arista, deflexion=0.05):
    """La polilínea de una arista: el kernel da las de todo el cuerpo en el orden de sus aristas."""
    cuerpo = arista.subformas("cuerpo")[0]
    aristas = cuerpo.subformas("arista")
    i = next((j for j, a in enumerate(aristas) if a.IsSame(arista)), None)
    if i is None:
        return np.zeros((0, 3), np.float32)
    return polilineas_aristas(cuerpo, deflexion)[i]
