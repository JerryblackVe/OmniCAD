# -*- coding: utf-8 -*-
"""Búsqueda de comandos por nombre, para la caja de herramientas (tecla S, ui/caja_herramientas.py).

Sin mayúsculas ni tildes («chaflan» encuentra «Chaflán»), todas las palabras en cualquier orden, y solo los
comandos que se pueden usar en ese momento: los grisados no aparecen (la regla de honestidad de la cinta) y los
de boceto, solo dentro de un boceto. `coincidencias` es pura (sin Qt) y se prueba sola.
"""
import re
import unicodedata

MAXIMO = 12                         # resultados por defecto
# Fuera de la búsqueda: la propia caja de herramientas y los filtros de selección («Caras», «Cuerpos»…), que
# sueltos parecen comandos.
EXCLUIDAS = ("caja_herramientas",)
PREFIJOS_EXCLUIDOS = ("filtro_",)


def _plano(texto):
    """Minúsculas y sin tildes: «Chaflán» → «chaflan»."""
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def coincidencias(consulta, entradas, maximo=MAXIMO):
    """Claves de `entradas` ((clave, nombre), …) cuyo nombre contiene TODAS las palabras de `consulta`, de la más
    parecida a la menos: primero los nombres que empiezan con la consulta, después los que tienen una palabra que
    empieza con ella y al final el resto; a igual puntaje, el nombre más corto. Sin mayúsculas ni tildes."""
    palabras = _plano(consulta).split()
    if not palabras:
        return []
    frase = " ".join(palabras)
    puntuadas = []
    for orden, (clave, nombre) in enumerate(entradas):
        n = _plano(nombre)
        if not all(p in n for p in palabras):
            continue
        if n.startswith(frase):
            puntaje = 0
        elif any(w.startswith(palabras[0]) for w in re.findall(r"\w+", n)):
            puntaje = 1
        else:
            puntaje = 2
        puntuadas.append((puntaje, len(n), orden, clave))
    return [clave for *_, clave in sorted(puntuadas)][:maximo]


def nombre_accion(accion):
    """Nombre de un comando sin el atajo ni los «&»: «Extruir\tE» → «Extruir»."""
    return accion.text().split("\t")[0].replace("&", "").strip()


def comandos_disponibles(acciones):
    """(clave, nombre) de los comandos que se pueden usar ahora (habilitados y visibles), sin nombres repetidos.
"""
    vistos, lista = set(), []
    for clave, a in acciones.items():
        nombre = nombre_accion(a)
        if (not nombre or nombre in vistos or not a.isEnabled() or not a.isVisible() or clave in EXCLUIDAS
                or clave.startswith(PREFIJOS_EXCLUIDOS)):
            continue
        vistos.add(nombre)
        lista.append((clave, nombre))
    return lista
