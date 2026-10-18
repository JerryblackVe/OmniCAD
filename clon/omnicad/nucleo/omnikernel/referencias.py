# -*- coding: utf-8 -*-
"""Firmas nativas; la búsqueda de referencias conserva la política común de la app."""
import numpy as np

from .. import referencias as comun


class _Mapa:
    def __init__(self, lista):
        self.lista = lista

    def Size(self):
        return len(self.lista)

    def FindKey(self, i):
        return self.lista[i - 1]

    def FindIndex(self, sub):
        return next((i for i, s in enumerate(self.lista, 1) if s.IsSame(sub)), 0)


def mapa_de_subformas(forma, tipo):
    return _Mapa(forma.subformas(tipo))


def subformas(forma, tipo):
    return forma.subformas(tipo)


def tipo_topologico(sub):
    return sub.tipo if sub.tipo != "cuerpo" else None


def firma_cara(cara):
    return cara.firma()


firma_arista = firma_cara
firma_vertice = firma_cara


def punto_de_vertice(v):
    return np.array(v.firma()["punto"])


# Comparar firmas y elegir la candidata son política de la aplicación, no geometría de un kernel.
firma = comun.firma.__wrapped__
referencia = comun.referencia.__wrapped__
resolver = comun.resolver.__wrapped__
resolver_varias = comun.resolver_varias.__wrapped__
_distancia = comun._distancia.__wrapped__
_distancia_local = comun._distancia_local.__wrapped__
