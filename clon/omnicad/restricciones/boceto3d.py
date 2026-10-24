# -*- coding: utf-8 -*-
"""
Boceto 3D de Fusion («3D Sketch» de la paleta de boceto [SKT-3D-SKETCH, SKT-REF-3D-SKETCH-SUPPORTED-CMD,
SKT-REF-3D-SKETCH-SUPPORTED-CONSTRAINT]): curvas fuera del plano del boceto, para rutas de barrido, solevaciones y
tuberías. Vive DENTRO del boceto 2D (`Boceto.geo3d`), como en Fusion, y comparte su numeración de ids.

Coordenadas del boceto (mm): x, y sobre el plano y z a lo largo de su normal; en un boceto sobre XY son las del mundo.
`Boceto.geo3d` es un dict JSON (vacío si el boceto no tiene nada en 3D):
  puntos {id: [x, y, z]}, curvas {id: {"tipo": "linea"|"spline", "puntos": [ids], "construccion": bool}},
  restricciones {id: {"tipo", "entidades", "eje"?}}, cotas {id: {"entidades", "expresion"}}.
Restricciones: coincidente, eje (la Horizontal/Vertical de Fusion: alinea una línea con X, Y o Z), paralela,
perpendicular, tangente (línea–spline con un extremo común), igual, punto_medio y fijo. Cota: distancia 3D entre
dos puntos o largo de una línea. El solver es propio (mínimos cuadrados de scipy), aparte del solver 2D.
"""
import math

import numpy as np

from ..nucleo import curvas3d
from ..nucleo import geometria as geo
from .boceto import ErrorBoceto

EJES = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
TIPOS_RESTRICCION = ("coincidente", "eje", "paralela", "perpendicular", "tangente", "igual", "punto_medio", "fijo")
_TOL = 1e-6


def datos(b):
    """El `geo3d` del boceto con sus cuatro tablas (las crea al primer uso)."""
    for clave in ("puntos", "curvas", "restricciones", "cotas"):
        b.geo3d.setdefault(clave, {})
    return b.geo3d


def _xyz(p):
    try:
        x, y, z = (float(v) for v in p)
    except (TypeError, ValueError) as e:
        raise ErrorBoceto(f"Un punto 3D es [x, y, z] (tres números): llegó {p!r}.") from e
    if not all(math.isfinite(v) for v in (x, y, z)):
        raise ErrorBoceto(f"Las coordenadas tienen que ser números finitos: llegó {p!r}.")
    return [x, y, z]


def tipo_de(b, ident):
    """'punto', 'linea' o 'spline'; ErrorBoceto si el id no es de la geometría 3D."""
    g = datos(b)
    if ident in g["puntos"]:
        return "punto"
    if ident in g["curvas"]:
        return g["curvas"][ident]["tipo"]
    raise ErrorBoceto(f"No existe la entidad 3D {ident}.")


# ---------------------------------------------------------------- creación
def agregar_punto(b, p, unir=True):
    """Punto 3D; con `unir`, si ya hay uno en ese lugar se reusa (así las curvas dibujadas seguidas se encadenan)."""
    p = _xyz(p)
    g = datos(b)
    if unir:
        for pid, q in g["puntos"].items():
            if math.dist(p, q) < _TOL:
                return pid
    pid = b._nuevo_id()
    g["puntos"][pid] = p
    return pid


def _curva(b, tipo, pts, construccion):
    g = datos(b)
    ids = [agregar_punto(b, p) for p in pts]
    if any(a == c for a, c in zip(ids, ids[1:], strict=False)):
        raise ErrorBoceto("Dos puntos seguidos de la curva coinciden: tienen que ser distintos.")
    cid = b._nuevo_id()
    g["curvas"][cid] = {"tipo": tipo, "puntos": ids, "construccion": bool(construccion)}
    return cid


def agregar_linea(b, p, q, construccion=False):
    return _curva(b, "linea", [p, q], construccion)


def agregar_spline(b, pts, construccion=False):
    """Spline de ajuste 3D: pasa por todos los puntos (al menos dos)."""
    pts = list(pts)
    if len(pts) < 2:
        raise ErrorBoceto("Una spline necesita al menos dos puntos.")
    return _curva(b, "spline", pts, construccion)


_FIRMAS = {"coincidente": ({"punto", "punto"}, {"punto", "linea"}), "eje": ({"linea"},),
           "paralela": ({"linea"},), "perpendicular": ({"linea"},), "igual": ({"linea"},),
           "tangente": ({"linea", "spline"},), "punto_medio": ({"punto", "linea"},)}
_CANTIDAD = {"eje": 1}


def agregar_restriccion(b, tipo, entidades, eje=None):
    if tipo not in TIPOS_RESTRICCION:
        raise ErrorBoceto(f"Restricción 3D desconocida: {tipo!r}. Valen: {', '.join(TIPOS_RESTRICCION)}.")
    entidades = list(entidades)
    tipos = [tipo_de(b, e) for e in entidades]
    if tipo == "fijo":
        if not entidades:
            raise ErrorBoceto("Fijar necesita al menos una entidad.")
    elif len(entidades) != _CANTIDAD.get(tipo, 2) or set(tipos) not in _FIRMAS[tipo] or (
            len(set(entidades)) != len(entidades)):
        esperado = " o ".join("+".join(sorted(f)) for f in _FIRMAS[tipo])
        raise ErrorBoceto(f"La restricción {tipo} se aplica a {esperado} (llegó {'+'.join(tipos)}).")
    datos_r = {"tipo": tipo, "entidades": entidades}
    if tipo == "eje":
        if eje not in EJES:
            raise ErrorBoceto(f"La restricción de eje necesita el eje: x, y o z (llegó {eje!r}).")
        datos_r["eje"] = eje
    if tipo == "tangente":
        _tangente(b, entidades)
    rid = b._nuevo_id()
    datos(b)["restricciones"][rid] = datos_r
    return rid


def agregar_cota(b, entidades, expresion):
    """Cota de distancia 3D: entre dos puntos o el largo de una línea. `expresion`: texto (puede usar parámetros)."""
    entidades = list(entidades)
    tipos = [tipo_de(b, e) for e in entidades]
    if tipos not in (["linea"], ["punto", "punto"]):
        raise ErrorBoceto("La cota 3D mide el largo de una línea o la distancia entre dos puntos.")
    kid = b._nuevo_id()
    datos(b)["cotas"][kid] = {"entidades": entidades, "expresion": str(expresion)}
    return kid


def borrar(b, ids):
    """Borra entidades, restricciones o cotas 3D. Con una curva se van sus restricciones y cotas y los puntos que
    ninguna otra curva usa; con un punto, las curvas que lo usan. Devuelve los ids borrados."""
    g = datos(b)
    todos = set(g["puntos"]) | set(g["curvas"]) | set(g["restricciones"]) | set(g["cotas"])
    faltan = [i for i in ids if i not in todos]
    if faltan:
        raise ErrorBoceto(f"No existen las entidades 3D {faltan}.")
    borrar_ids = set(ids)
    borrar_ids |= {c for c, d in g["curvas"].items() if borrar_ids & set(d["puntos"])}
    usados = {p for c, d in g["curvas"].items() if c not in borrar_ids for p in d["puntos"]}
    borrar_ids |= {p for c in borrar_ids & set(g["curvas"]) for p in g["curvas"][c]["puntos"] if p not in usados}
    for tabla in ("restricciones", "cotas"):
        borrar_ids |= {k for k, d in g[tabla].items() if borrar_ids & set(d["entidades"])}
    for tabla in ("puntos", "curvas", "restricciones", "cotas"):
        for k in borrar_ids & set(g[tabla]):
            del g[tabla][k]
    return sorted(borrar_ids)


# ---------------------------------------------------------------- solver
class Resultado3D:
    def __init__(self, ok, gdl, mensaje=""):
        self.ok, self.gdl, self.mensaje = ok, gdl, mensaje


def puntos_fijos(b):
    g = datos(b)
    fijos = set()
    for r in g["restricciones"].values():
        if r["tipo"] == "fijo":
            for e in r["entidades"]:
                fijos |= {e} if e in g["puntos"] else set(g["curvas"].get(e, {}).get("puntos", ()))
    return fijos


def _ecuaciones(b, valores):
    """Lista de funciones P → residuos (P: {id: array xyz})."""
    g = datos(b)
    ext = lambda c: g["curvas"][c]["puntos"]  # noqa: E731
    d = lambda P, c: P[ext(c)[-1]] - P[ext(c)[0]]  # noqa: E731
    u = lambda v: v / max(np.linalg.norm(v), 1e-12)  # noqa: E731
    fs = []
    for r in g["restricciones"].values():
        t, e = r["tipo"], r["entidades"]
        if t == "coincidente":
            p, o = sorted(e, key=lambda i: i not in g["puntos"])
            if o in g["puntos"]:
                fs.append(lambda P, p=p, o=o: P[p] - P[o])
            else:
                fs.append(lambda P, p=p, o=o: np.cross(P[p] - P[ext(o)[0]], u(d(P, o))))
        elif t == "eje":
            otros = [i for i, n in enumerate("xyz") if n != r["eje"]]
            fs.append(lambda P, c=e[0], k=otros: d(P, c)[k])
        elif t == "paralela":
            fs.append(lambda P, a=e[0], c=e[1]: np.cross(u(d(P, a)), u(d(P, c))))
        elif t == "perpendicular":
            fs.append(lambda P, a=e[0], c=e[1]: [float(u(d(P, a)) @ u(d(P, c)))])
        elif t == "igual":
            fs.append(lambda P, a=e[0], c=e[1]: [np.linalg.norm(d(P, a)) - np.linalg.norm(d(P, c))])
        elif t == "punto_medio":
            p, c = sorted(e, key=lambda i: i not in g["puntos"])
            fs.append(lambda P, p=p, c=c: P[p] - (P[ext(c)[0]] + P[ext(c)[1]]) / 2)
    for k, cota in g["cotas"].items():
        e = cota["entidades"]
        a, c = (ext(e[0])[0], ext(e[0])[1]) if len(e) == 1 else e
        fs.append(lambda P, a=a, c=c, v=float(valores[k]): [np.linalg.norm(P[c] - P[a]) - v])
    return fs


def resolver(b, valores):
    """Resuelve la geometría 3D de `b` EN EL LUGAR con las cotas `valores` ({id: mm}). Si queda en conflicto no
    mueve nada y devuelve ok=False. Grados de libertad: coordenadas libres − rango del jacobiano."""
    g = datos(b)
    if not g["puntos"]:
        return Resultado3D(True, 0)
    for k in g["cotas"]:
        if not valores.get(k, 0) > 0:
            return Resultado3D(False, None, f"La cota 3D {k} tiene que medir más que 0 mm.")
    fijos = puntos_fijos(b)
    libres = [p for p in g["puntos"] if p not in fijos]
    fs = _ecuaciones(b, valores)
    x0 = np.array([c for p in libres for c in g["puntos"][p]], float)

    def puntos(x):
        P = {p: np.array(v, float) for p, v in g["puntos"].items()}
        for i, p in enumerate(libres):
            P[p] = x[3 * i:3 * i + 3]
        return P

    def residuos(x):
        P = puntos(x)
        return np.concatenate([np.ravel(f(P)) for f in fs]) if fs else np.zeros(0)

    if not fs or not libres:
        r = residuos(x0)
        ok = not len(r) or float(np.max(np.abs(r))) < _TOL
        return Resultado3D(ok, len(x0), "" if ok else "Restricciones 3D en conflicto (sobre geometría fija).")
    from scipy.optimize import least_squares
    sol = least_squares(residuos, x0, method="trf", xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=2000)
    if float(np.max(np.abs(residuos(sol.x)))) > _TOL:
        return Resultado3D(False, None, "Restricciones o cotas 3D en conflicto: quitá alguna.")
    for p, v in puntos(sol.x).items():
        if p in libres:
            g["puntos"][p] = [float(c) + 0.0 for c in v]
    gdl = len(x0) - int(np.linalg.matrix_rank(sol.jac, tol=1e-8))
    return Resultado3D(True, gdl)


def _tangente(b, entidades):
    """(linea, spline, índice del extremo de la spline: 0 o -1, punto común). ErrorBoceto si no comparten extremo."""
    g = datos(b)
    linea, spline = sorted(entidades, key=lambda i: g["curvas"][i]["tipo"] != "linea")
    pl, ps = g["curvas"][linea]["puntos"], g["curvas"][spline]["puntos"]
    for extremo in (0, -1):
        if ps[extremo] in pl:
            return linea, spline, extremo, ps[extremo]
    raise ErrorBoceto("Para la tangencia, la spline tiene que empezar o terminar en un extremo de la línea "
                      "(dibujala desde ese extremo: se encadenan solas).")


# ---------------------------------------------------------------- geometría OCC
def a_mundo(plano, p):
    """Coordenadas del boceto [x, y, z] → punto 3D del mundo."""
    return plano.a_3d(p[0], p[1]) + plano.normal * p[2]


def arista(b, cid, plano):
    """Arista OCC de la curva 3D `cid` en el mundo (la spline respeta sus tangencias con líneas)."""
    g = datos(b)
    c = g["curvas"][cid]
    pts = [a_mundo(plano, g["puntos"][p]) for p in c["puntos"]]
    if c["tipo"] == "linea":
        return curvas3d.arista_recta(pts[0], pts[1])
    tangentes = {}
    for r in g["restricciones"].values():
        if r["tipo"] == "tangente" and cid in r["entidades"]:
            linea, _, extremo, comun = _tangente(b, r["entidades"])
            otro = next(p for p in g["curvas"][linea]["puntos"] if p != comun)
            s, o = a_mundo(plano, g["puntos"][comun]), a_mundo(plano, g["puntos"][otro])
            tangentes[extremo % len(pts)] = s - o if extremo == 0 else o - s
    try:
        return curvas3d.arista_spline(pts, tangentes)
    except geo.ErrorGeometria as e:
        raise ErrorBoceto(f"No se pudo construir la spline 3D {cid}: {e}") from e


def polilineas(b, plano, muestras=48):
    """Polilíneas (Nx3, mundo) de las curvas 3D para dibujarlas en la vista."""
    salida = []
    for cid, c in datos(b)["curvas"].items():
        if c["tipo"] == "linea":
            salida.append(np.array([a_mundo(plano, b.geo3d["puntos"][p]) for p in c["puntos"]], np.float32))
            continue
        try:
            salida.append(curvas3d.muestrear(arista(b, cid, plano), muestras))
        except ErrorBoceto:
            continue
    return salida


# ---------------------------------------------------------------- serialización (claves enteras ↔ listas JSON)
def a_dict(g):
    return {"puntos": [[k, *v] for k, v in g.get("puntos", {}).items()],
            **{t: [{"id": k, **v} for k, v in g.get(t, {}).items()] for t in ("curvas", "restricciones", "cotas")}}


def desde_dict(d):
    g = {"puntos": {int(p[0]): [float(v) for v in p[1:4]] for p in d.get("puntos", [])}}
    for t in ("curvas", "restricciones", "cotas"):
        g[t] = {int(x["id"]): {k: v for k, v in x.items() if k != "id"} for x in d.get(t, [])}
    return g
