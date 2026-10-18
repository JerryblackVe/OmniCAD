# -*- coding: utf-8 -*-
"""Empaqueta la malla y las normales calculadas por el kernel nativo."""


def _mallas_por_cara(forma, deflexion, angular, rehacer=False):
    m = forma.teselar(deflexion, angular)
    indices = m["indices"].reshape(-1, 3)
    vertices = m["vertices"].reshape(-1, 3)[indices]
    normales = m["normales"].reshape(-1, 3)[indices]
    if forma.tipo == "cara":            # el kernel ya filtró los triángulos de esa cara
        return [(forma, vertices.reshape(-1, 3), normales.reshape(-1, 3))]
    return [(cara, vertices[m["caras"] == i].reshape(-1, 3), normales[m["caras"] == i].reshape(-1, 3))
            for i, cara in enumerate(forma.subformas("cara"))]
