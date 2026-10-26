# -*- coding: utf-8 -*-
"""
«De dónde viene esta cara»: qué paso del timeline creó una cara, arista o vértice y cuáles la modificaron.

Se calcula BAJO DEMANDA (al elegir algo en la vista o al pedirlo por API), no en cada recálculo: se camina hacia
atrás por los estados que el documento ya guarda. En cada paso, si el cuerpo conserva la misma forma el paso no la
tocó; si no, la subforma se busca en el cuerpo de antes (misma subforma OCC, o la de firma geométrica parecida):
- no está → ese paso la CREÓ;
- está con otra geometría → ese paso la MODIFICÓ y se sigue buscando su origen en el cuerpo de antes;
- está igual (una operación que rehízo la topología) → no cuenta.
shortcut: es una aproximación por geometría, no el historial Modified/Generated del kernel (SC3); una cara que un
paso deja idéntica a otra no se distingue. Una cara que viene de otro cuerpo (la herramienta de una resta) se
atribuye al paso que la unió, y un cuerpo importado o una malla no dan origen (None).
"""
import logging
import math

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import referencias as refs

log = logging.getLogger("omnicad")
UMBRAL_PREDECESOR = 0.3         # distancia de firma máxima para decir «es la misma cara de antes» (lo modificado
                                # real da < 0.05; una cara nueva que se le parece de lejos, > 0.6)
UMBRAL_IGUAL = 1e-6             # por debajo, el paso no cambió la subforma
TOL_PORTADORA = 1e-4            # mm: dos subformas están en la misma recta, plano, círculo o cilindro


def origen_de(doc, ref):
    """{"creo": id del paso, "modificaron": [ids en orden], "cuerpo": id} de una referencia a cara, arista o vértice
    (o a un cuerpo: lo creó el paso del cuerpo). None si no se puede saber (el cuerpo ya no existe o no es OCC)."""
    tipo = ref.get("tipo")
    estado = doc.estado_en(doc.marcador)
    cuerpo = estado.cuerpos.get(ref.get("cuerpo"))
    if cuerpo is None:
        return None
    if tipo == "cuerpo":
        return {"creo": cuerpo.op_id, "modificaron": [], "cuerpo": cuerpo.id}
    if tipo not in ("cara", "arista", "vertice") or getattr(cuerpo, "tipo", "solido") != "solido":
        return None
    try:
        sub = refs.resolver(cuerpo.forma, ref)
        return None if sub is None else _caminar(doc, cuerpo.id, tipo, sub)
    except Exception:       # noqa: BLE001 — forma de otro motor o referencia rara: sin origen, no un error
        log.debug("origen_de: no se pudo rastrear %s", ref, exc_info=True)
        return None


def _caminar(doc, cid, tipo, sub):
    modificaron = []
    despues = doc.estado_en(doc.marcador).cuerpos[cid]
    for k in range(doc.marcador - 1, -1, -1):
        op = doc.operaciones[k]
        if op.suprimida:
            continue
        antes = doc.estado_en(k).cuerpos.get(cid)
        if antes is None:
            return {"creo": op.id, "modificaron": modificaron[::-1], "cuerpo": cid}
        if antes.forma is despues.forma:
            continue
        previa = _previa(antes.forma, tipo, sub)
        if previa is None:
            return {"creo": op.id, "modificaron": modificaron[::-1], "cuerpo": cid}
        sub, cambio = previa
        if cambio:
            modificaron.append(op.id)
        despues = antes
    return None         # todos los pasos hasta el principio están suprimidos


def _previa(antes, tipo, sub):
    """(subforma de `antes` de la que viene `sub`, si cambió) o None si `sub` nació en este paso."""
    if refs.mapa_de_subformas(antes, tipo).FindIndex(sub):
        return sub, False
    ref = refs.referencia("", sub)      # sin posición relativa a la caja: un paso que agranda el cuerpo la desplaza
    previa = refs.resolver(antes, ref)
    if previa is None:
        return None
    caja = geo.caja_envolvente(antes)
    escala = max(math.dist(caja[0], caja[1]), 1e-6) if caja else 1.0
    vieja = refs.firma(previa)
    if not (_misma_portadora(tipo, ref["firma"], vieja) and _se_solapan(sub, previa, ref["firma"], vieja)):
        return None
    d = refs._distancia(tipo, ref["firma"], vieja, escala)
    return (previa, d > UMBRAL_IGUAL) if d <= UMBRAL_PREDECESOR else None


_PUNTO = {"cara": "centro", "arista": "medio", "vertice": "punto"}


def _se_solapan(a, b, fa, fb, tol=1e-3):
    """¿El punto representativo de una de las dos subformas cae dentro de la caja de la otra? Recortada o ampliada por
    un paso sigue ocupando el mismo lugar; la copia de un patrón, sobre la misma recta o el mismo plano, no."""
    k = _PUNTO[_tipo(a)]
    return any(all(mn - tol <= x <= mx + tol for x, mn, mx in zip(f[k], *geo.caja_envolvente(forma), strict=True))
               for forma, f in ((b, fa), (a, fb)))


def _tipo(sub):
    return refs.tipo_topologico(sub)


def _misma_portadora(tipo, nueva, vieja):
    """¿La subforma nueva está sobre la misma recta, plano, círculo o cilindro que la vieja? Recortada o partida por un
    paso, sigue siendo la misma (modificada); en otro lugar (el borde tangente de un empalme, una cara desplazada) es
    otra, nacida en el paso. Para las geometrías libres no hay portadora que comparar: vale la distancia de firma."""
    if nueva["geom"] != vieja["geom"]:
        return False
    g = nueva["geom"]
    if tipo == "vertice":
        return math.dist(nueva["punto"], vieja["punto"]) <= TOL_PORTADORA
    if tipo == "arista" and g == "linea":
        a, b = (np.array(p) for p in vieja["extremos"])
        d = (b - a) / max(np.linalg.norm(b - a), 1e-12)
        return all(np.linalg.norm(np.cross(np.array(p) - a, d)) <= TOL_PORTADORA for p in nueva["extremos"])
    if tipo == "arista" and g == "circulo":
        return abs(nueva["radio"] - vieja["radio"]) <= TOL_PORTADORA and math.dist(nueva["centro"], vieja["centro"]) <= TOL_PORTADORA
    if tipo == "cara" and g == "plano":
        n = np.array(vieja["normal"])
        return float(np.dot(n, nueva["normal"])) >= 1 - 1e-6 and abs(float(np.dot(n, np.array(nueva["centro"]) - vieja["centro"]))) <= TOL_PORTADORA
    if tipo == "cara" and g == "cilindro":
        return abs(nueva["radio"] - vieja["radio"]) <= TOL_PORTADORA and abs(float(np.dot(nueva["eje"], vieja["eje"]))) >= 1 - 1e-6
    return True
