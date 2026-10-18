# -*- coding: utf-8 -*-
"""Operaciones locales de OmniKernel con la firma de `nucleo/solidos_modificar.py`.

Las variantes que el kernel no tiene (radio variable, dos distancias, vaciado exterior…) informan
MOTOR_SIN_SOPORTE. La paridad está probada sobre cuerpos de caras planas (donde la cadena tangente no
agrega aristas); sobre caras curvas todo queda sin soporte (faltante FK-004).
"""
import numpy as np

from .. import motor
from ..geometria import ErrorGeometria
from .geometria import _mallable


def _sin_curvas(forma, que):
    """La paridad está probada en cuerpos de caras planas; con caras curvas faltan las cadenas tangentes (FK-004)."""
    if any(c.firma()["geom"] != "plano" for c in forma.subformas("cara")):
        motor.sin_soporte(f"{que} sobre un cuerpo con caras curvas")


def _modificar(forma, operacion, subformas, valor=0.0, plano=None):
    resultado = forma.modificar(operacion, list(subformas), float(valor), plano)
    if not resultado.propiedades()["valida"]:
        raise ErrorGeometria(f"{operacion.capitalize()}: el resultado no es un sólido válido.")
    return _mallable(resultado)


def _aristas_de_grupos(forma, grupos, que, tipo_valido, clave):
    if not grupos:
        raise ErrorGeometria(f"Elegí al menos una arista para {que}.")
    valores, aristas = set(), []
    for g in grupos:
        if g.get("tipo", tipo_valido) != tipo_valido:
            motor.sin_soporte(f"{que} de tipo «{g.get('tipo')}»")
        if not g.get("aristas"):
            raise ErrorGeometria(f"Un conjunto de {que} no tiene aristas.")
        valores.add(float(g.get(clave, 0)))
        aristas += g["aristas"]
    if len(valores) != 1:
        motor.sin_soporte(f"{que} con medidas distintas en un mismo paso")
    valor = valores.pop()
    if valor <= 0:
        raise ErrorGeometria(f"La medida de {que} debe ser positiva.")
    _sin_curvas(forma, que)
    return aristas, valor


def _sin_esquinas(aristas, que):
    """Las esquinas de varias aristas dan otra topología que OpenCascade (faltante FK-006)."""
    puntos = [tuple(np.round(p, 6)) for a in aristas for p in a.firma()["extremos"]]
    if len(puntos) != len(set(puntos)):
        motor.sin_soporte(f"{que} de aristas que se juntan en una esquina")


def empalme(forma, grupos, *, cadena_tangente=True):
    aristas, radio = _aristas_de_grupos(forma, grupos, "empalme", "constante", "radio")
    _sin_esquinas(aristas, "el empalme")
    return _modificar(forma, "empalme", aristas, radio)


def chaflan(forma, grupos, *, cadena_tangente=True):
    if any(g.get("cara") is not None or g.get("voltear") for g in grupos or []):
        motor.sin_soporte("chaflán con cara de referencia o volteado")
    aristas, d = _aristas_de_grupos(forma, grupos, "chaflán", "distancia_igual", "distancia")
    _sin_esquinas(aristas, "el chaflán")
    return _modificar(forma, "chaflan", aristas, d)


def vaciado(forma, caras_quitar, *, espesor_interior, espesor_exterior=0.0, direccion="interior",
            tangente=True, tipo="afilado"):
    if direccion not in ("interior", "exterior", "ambos"):
        raise ErrorGeometria(f"Dirección de vaciado desconocida: {direccion}")
    if direccion != "interior" or tipo != "afilado" or not caras_quitar:
        motor.sin_soporte("el vaciado exterior, redondeado o sin caras abiertas")
    if float(espesor_interior) <= 0:
        raise ErrorGeometria("Los espesores del vaciado deben ser positivos.")
    _sin_curvas(forma, "vaciado")
    return _modificar(forma, "vaciado", caras_quitar, espesor_interior)


def desmoldeo(forma, caras, direccion_extraccion, angulo, plano_neutro, *, lados="uno", angulo2=None):
    if lados not in ("uno", "dos", "simetrico"):
        raise ErrorGeometria(f"Opción de lados desconocida: {lados}")
    if lados != "uno":
        motor.sin_soporte("el desmoldeo de dos lados o simétrico")
    if not caras:
        raise ErrorGeometria("Elegí las caras a desmoldear.")
    _sin_curvas(forma, "desmoldeo")
    d = np.asarray(direccion_extraccion, float)
    if np.linalg.norm(d) < 1e-12:
        raise ErrorGeometria("La dirección de extracción no puede ser nula.")
    if abs(abs(float(d @ plano_neutro.normal)) - np.linalg.norm(d)) > 1e-9:
        motor.sin_soporte("el desmoldeo con dirección de extracción no normal al plano neutro")
    return _modificar(forma, "desmoldeo", caras, angulo,
                      (plano_neutro.origen.tolist(), (d / np.linalg.norm(d)).tolist()))


def desfasar_caras(forma, caras, distancia, *, tangente=True):
    if not caras:
        raise ErrorGeometria("Elegí las caras a desfasar.")
    if abs(float(distancia)) < 1e-9:
        return forma
    _sin_curvas(forma, "desfase de caras")
    return _modificar(forma, "desfase_caras", caras, distancia)


def quitar_caras(forma, caras):
    if not caras:
        raise ErrorGeometria("Elegí las caras a quitar.")
    _sin_curvas(forma, "quitar caras")
    return _modificar(forma, "quitar_caras", caras)
