# -*- coding: utf-8 -*-
"""
Boceto 3D de Fusion («3D Sketch» de la paleta de boceto [SKT-3D-SKETCH, SKT-CREATE-3D-SKETCH,
SKT-REF-3D-SKETCH-SUPPORTED-CMD, SKT-REF-3D-SKETCH-SUPPORTED-CONSTRAINT]): curvas fuera del plano del boceto, para
rutas de barrido, solevaciones y tuberías. Vive DENTRO del boceto 2D (`Boceto.geo3d`), como en Fusion, y comparte su
numeración de ids.

Coordenadas del boceto (mm): x, y sobre el plano y z a lo largo de su normal; en un boceto sobre XY son las del mundo.
`Boceto.geo3d` es un dict JSON (vacío si el boceto no tiene nada en 3D):
  puntos {id: [x, y, z]},
  curvas {id: {"tipo", "puntos": [ids], "construccion": bool, ...}} con tipo
    linea [inicio, fin] · spline [puntos de paso] (+ "cerrada") · arco [inicio, paso, fin] ·
    circulo [centro] + "radio", "normal" · elipse [centro] + "eje_mayor" (vector), "radio_menor", "normal" ·
    conica [inicio, vértice, fin] + "rho" · texto [origen] + "texto", "altura", "fuente", "u", "v" (ejes del texto);
    "origen" (opcional) anota de qué selección salió una curva de Intersection Curve / Project To Surface,
  restricciones {id: {"tipo", "entidades", "eje"?}}, cotas {id: {"entidades", "expresion", "tipo"?: "angulo"}}.
Las herramientas de Fusion en 3D son Línea, Arco, Spline, Rectángulo, Círculo, Elipse, Punto, Texto y Cónica; las
restricciones, Horizontal/Vertical (acá «eje»), Coincidente, Tangente, Igual, Paralela, Perpendicular, Fijo, Punto medio,
Concéntrica y Colineal. Cotas: distancia 3D entre dos puntos, largo de una línea y ángulo entre dos líneas. El solver es
propio (mínimos cuadrados de scipy), aparte del solver 2D: mueve PUNTOS; radios, normales y ejes de círculos, elipses y
textos son datos (los cambian mover/rotar/escalar).
"""
import math

import numpy as np

from ..nucleo import curvas3d
from ..nucleo import geometria as geo
from .boceto import ErrorBoceto, puntos_primitiva

EJES = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
TIPOS_RESTRICCION = ("coincidente", "eje", "paralela", "perpendicular", "tangente", "igual", "punto_medio", "fijo",
                     "concentrica", "colineal")
CON_CENTRO = ("arco", "circulo", "elipse")
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


def _unitario(v, nombre):
    v = np.array(_xyz(v))
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        raise ErrorBoceto(f"{nombre} no puede ser el vector nulo.")
    return v / n


def _positivo(v, nombre):
    try:
        v = float(v)
    except (TypeError, ValueError) as e:
        raise ErrorBoceto(f"{nombre} tiene que ser un número.") from e
    if not (math.isfinite(v) and v > 0):
        raise ErrorBoceto(f"{nombre} tiene que ser mayor que 0 (llegó {v:g}).")
    return v


def _lista(v):
    return [float(c) + 0.0 for c in v]


def tipo_de(b, ident):
    """'punto' o el tipo de la curva; ErrorBoceto si el id no es de la geometría 3D."""
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


def _curva(b, tipo, pts, construccion, **extra):
    g = datos(b)
    ids = [agregar_punto(b, p) for p in pts]
    if any(a == c for a, c in zip(ids, ids[1:], strict=False)):
        raise ErrorBoceto("Dos puntos seguidos de la curva coinciden: tienen que ser distintos.")
    cid = b._nuevo_id()
    g["curvas"][cid] = {"tipo": tipo, "puntos": ids, "construccion": bool(construccion), **extra}
    return cid


def agregar_linea(b, p, q, construccion=False):
    return _curva(b, "linea", [p, q], construccion)


def agregar_spline(b, pts, construccion=False, cerrada=False):
    """Spline de ajuste 3D: pasa por todos los puntos (al menos dos); `cerrada` la cierra suave sobre el primero."""
    pts = list(pts)
    if len(pts) < (3 if cerrada else 2):
        raise ErrorBoceto("Una spline necesita al menos dos puntos (tres si es cerrada).")
    return _curva(b, "spline", pts, construccion, **({"cerrada": True} if cerrada else {}))


def agregar_arco(b, inicio, paso, fin, construccion=False):
    """Arco de 3 puntos (3D Sketch › Arco): de `inicio` a `fin` pasando por `paso`."""
    a, m, c = (np.array(_xyz(p)) for p in (inicio, paso, fin))
    if np.linalg.norm(np.cross(m - a, c - a)) < _TOL * max(1.0, np.linalg.norm(c - a)) ** 2:
        raise ErrorBoceto("Los tres puntos del arco están alineados (o repetidos): no definen un círculo.")
    return _curva(b, "arco", [a, m, c], construccion)


def agregar_circulo(b, centro, radio, normal=(0, 0, 1), construccion=False):
    """Círculo 3D (3D Sketch › Círculo) de centro y radio, en el plano perpendicular a `normal`."""
    return _curva(b, "circulo", [centro], construccion, radio=_positivo(radio, "El radio"),
                  normal=_lista(_unitario(normal, "La normal")))


def agregar_elipse(b, centro, eje_mayor, radio_menor, normal=(0, 0, 1), construccion=False):
    """Elipse 3D: `eje_mayor` es el vector del centro al extremo del eje mayor (perpendicular a `normal`)."""
    n, e = _unitario(normal, "La normal"), np.array(_xyz(eje_mayor))
    if np.linalg.norm(e) < _TOL:
        raise ErrorBoceto("El eje mayor de la elipse no puede medir 0.")
    if abs(float(e @ n)) > 1e-9 * np.linalg.norm(e):
        raise ErrorBoceto("El eje mayor de la elipse tiene que ser perpendicular a su normal (estar en su plano).")
    return _curva(b, "elipse", [centro], construccion, eje_mayor=_lista(e),
                  radio_menor=_positivo(radio_menor, "El radio menor"), normal=_lista(n))


def agregar_conica(b, inicio, vertice, fin, rho=0.5, construccion=False):
    """Curva cónica 3D: extremos, vértice (cruce de las tangentes) y rho (0 < rho < 1; 0,5 = parábola)."""
    try:
        rho = float(rho)
    except (TypeError, ValueError) as e:
        raise ErrorBoceto("rho tiene que ser un número entre 0 y 1.") from e
    if not 0 < rho < 1:
        raise ErrorBoceto(f"rho tiene que estar entre 0 y 1, sin incluirlos (llegó {rho:g}).")
    a, v, c = (np.array(_xyz(p)) for p in (inicio, vertice, fin))
    if np.linalg.norm(np.cross(v - a, c - a)) < _TOL:
        raise ErrorBoceto("El vértice de la cónica no puede estar alineado con sus extremos.")
    return _curva(b, "conica", [a, v, c], construccion, rho=rho)


def _base(u, v):
    """(u, v) ortonormales del plano de la tríada (v se endereza perpendicular a u)."""
    u = _unitario(u, "El eje x del plano")
    v = np.array(_xyz(v)) - np.dot(_xyz(v), u) * u
    return u, _unitario(v, "El eje y del plano (paralelo al x)")


def agregar_rectangulo(b, esquina, opuesta, u=(1, 0, 0), v=(0, 1, 0), construccion=False):
    """Rectángulo de 2 puntos en el plano (u, v) que pasa por `esquina` (la opuesta se proyecta a ese plano): cuatro
    líneas encadenadas con perpendicular y dos paralelas, como el de Fusion. Devuelve los ids de las líneas."""
    u, v = _base(u, v)
    p0 = np.array(_xyz(esquina))
    d = np.array(_xyz(opuesta)) - p0
    ancho, alto = float(d @ u), float(d @ v)
    if abs(ancho) < _TOL or abs(alto) < _TOL:
        raise ErrorBoceto("El rectángulo necesita ancho y alto distintos de 0 en el plano elegido.")
    esquinas = [p0, p0 + ancho * u, p0 + ancho * u + alto * v, p0 + alto * v]
    lineas = [agregar_linea(b, esquinas[i], esquinas[(i + 1) % 4], construccion) for i in range(4)]
    agregar_restriccion(b, "perpendicular", lineas[:2])
    agregar_restriccion(b, "paralela", [lineas[0], lineas[2]])
    agregar_restriccion(b, "paralela", [lineas[1], lineas[3]])
    return lineas


def _contornos(texto, altura, fuente):
    from ..nucleo import fuentes
    try:
        return [puntos_primitiva(p) for p in fuentes.contornos_texto(texto, fuente, altura)]
    except fuentes.ErrorFuente as e:
        raise ErrorBoceto(str(e)) from e


def agregar_texto(b, origen, texto, altura, u=(1, 0, 0), v=(0, 1, 0), fuente="Arial", construccion=False):
    """Texto 3D (3D Sketch › Texto): una línea de texto con la base en `origen`, a lo largo de `u` y hacia arriba
    según `v` (el plano de la tríada). Sus contornos se dibujan como polilíneas."""
    if not isinstance(texto, str) or not texto.strip():
        raise ErrorBoceto("Escribí el texto (no puede quedar vacío).")
    altura = _positivo(altura, "La altura del texto")
    u, v = _base(u, v)
    if not _contornos(texto, altura, fuente):
        raise ErrorBoceto(f"La fuente «{fuente}» no tiene contornos para «{texto}».")
    return _curva(b, "texto", [origen], construccion, texto=texto, altura=altura, fuente=str(fuente),
                  u=_lista(u), v=_lista(v))


_FIRMAS = {"coincidente": ({"punto", "punto"}, {"punto", "linea"}), "eje": ({"linea"},),
           "paralela": ({"linea"},), "perpendicular": ({"linea"},), "igual": ({"linea"},), "colineal": ({"linea"},),
           "tangente": ({"linea", "spline"}, {"spline"}), "punto_medio": ({"punto", "linea"},)}
_CANTIDAD = {"eje": 1}


def agregar_restriccion(b, tipo, entidades, eje=None):
    if tipo not in TIPOS_RESTRICCION:
        raise ErrorBoceto(f"Restricción 3D desconocida: {tipo!r}. Valen: {', '.join(TIPOS_RESTRICCION)}.")
    entidades = list(entidades)
    tipos = [tipo_de(b, e) for e in entidades]
    distintas = len(set(entidades)) == len(entidades)
    if tipo == "fijo":
        if not entidades:
            raise ErrorBoceto("Fijar necesita al menos una entidad.")
    elif tipo == "concentrica":
        if len(entidades) != 2 or not distintas or not set(tipos) <= set(CON_CENTRO):
            raise ErrorBoceto(f"La restricción concéntrica une dos arcos, círculos o elipses (llegó {'+'.join(tipos)}).")
    elif len(entidades) != _CANTIDAD.get(tipo, 2) or set(tipos) not in _FIRMAS[tipo] or not distintas:
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


def agregar_cota(b, entidades, expresion, tipo="distancia"):
    """Cota 3D: distancia entre dos puntos o largo de una línea (`tipo` distancia), o ángulo entre dos líneas
    (`tipo` angulo, en grados). `expresion`: texto (puede usar parámetros)."""
    entidades = list(entidades)
    tipos = [tipo_de(b, e) for e in entidades]
    if tipo == "angulo":
        if tipos != ["linea", "linea"] or entidades[0] == entidades[1]:
            raise ErrorBoceto("La cota angular 3D mide el ángulo entre dos líneas.")
    elif tipos not in (["linea"], ["punto", "punto"]):
        raise ErrorBoceto("La cota 3D mide el largo de una línea o la distancia entre dos puntos.")
    kid = b._nuevo_id()
    datos(b)["cotas"][kid] = {"entidades": entidades, "expresion": str(expresion),
                              **({"tipo": "angulo"} if tipo == "angulo" else {})}
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


def transformar(b, ids, matriz, traslacion=(0, 0, 0), centro=(0, 0, 0), copiar=False):
    """Mover / rotar / escalar (y con `copiar`, copiar) entidades 3D: p' = centro + matriz·(p − centro) + traslación.
    `matriz` es una semejanza (giro × escala uniforme). Las curvas se llevan sus puntos; radios, alturas, normales y
    ejes se transforman con ellas. Devuelve los ids transformados (los nuevos si se copió)."""
    m = np.asarray(matriz, float)
    det = float(np.linalg.det(m)) if m.shape == (3, 3) else 0.0
    if not det > 1e-12:
        raise ErrorBoceto("La transformación tiene que ser un giro con escala positiva.")
    escala = det ** (1 / 3)
    giro = m / escala
    c0, t = np.array(_xyz(centro)), np.array(_xyz(traslacion))
    g = datos(b)
    faltan = [i for i in ids if i not in g["puntos"] and i not in g["curvas"]]
    if faltan or not ids:
        raise ErrorBoceto(f"No existen las entidades 3D {faltan}." if faltan else "Elegí qué transformar.")
    curvas = [i for i in ids if i in g["curvas"]]
    puntos = list(dict.fromkeys([p for c in curvas for p in g["curvas"][c]["puntos"]]
                                + [i for i in ids if i in g["puntos"]]))
    nuevo = {p: _lista(c0 + m @ (np.array(g["puntos"][p]) - c0) + t) for p in puntos}
    mapa = {p: agregar_punto(b, nuevo[p], unir=False) for p in puntos} if copiar else {p: p for p in puntos}
    if not copiar:
        for p in puntos:
            g["puntos"][p] = nuevo[p]
    salida = []
    for cid in curvas:
        c = dict(g["curvas"][cid], puntos=[mapa[p] for p in g["curvas"][cid]["puntos"]])
        c.pop("origen", None)                       # movida, ya no es la curva que dejó la intersección
        for clave in ("radio", "radio_menor", "altura"):
            if clave in c:
                c[clave] = c[clave] * escala
        for clave, mat in (("normal", giro), ("u", giro), ("v", giro), ("eje_mayor", m)):
            if clave in c:
                c[clave] = _lista(mat @ np.array(c[clave]))
        nid = b._nuevo_id() if copiar else cid
        g["curvas"][nid] = c
        salida.append(nid)
    return salida + [mapa[i] for i in ids if i not in curvas]


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


def _circuncentro(a, m, c):
    ab, ac = m - a, c - a
    n = np.cross(ab, ac)
    return a + (np.cross(n, ab) * (ac @ ac) + np.cross(ac, n) * (ab @ ab)) / (2 * max(n @ n, 1e-24))


def _centro(g, P, cid):
    pts = g["curvas"][cid]["puntos"]
    return _circuncentro(*(P[p] for p in pts)) if g["curvas"][cid]["tipo"] == "arco" else P[pts[0]]


def _P(b):
    return {p: np.array(v, float) for p, v in datos(b)["puntos"].items()}


def centro(b, cid):
    """Centro (coordenadas del boceto) de un arco, círculo o elipse 3D."""
    return _centro(datos(b), _P(b), cid)


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
        elif t == "colineal":
            fs.append(lambda P, a=e[0], c=e[1]: np.concatenate([np.cross(u(d(P, a)), u(d(P, c))),
                                                                np.cross(u(d(P, a)), P[ext(c)[0]] - P[ext(a)[0]])]))
        elif t == "perpendicular":
            fs.append(lambda P, a=e[0], c=e[1]: [float(u(d(P, a)) @ u(d(P, c)))])
        elif t == "igual":
            fs.append(lambda P, a=e[0], c=e[1]: [np.linalg.norm(d(P, a)) - np.linalg.norm(d(P, c))])
        elif t == "punto_medio":
            p, c = sorted(e, key=lambda i: i not in g["puntos"])
            fs.append(lambda P, p=p, c=c: P[p] - (P[ext(c)[0]] + P[ext(c)[1]]) / 2)
        elif t == "concentrica":
            fs.append(lambda P, a=e[0], c=e[1]: _centro(g, P, a) - _centro(g, P, c))
    for k, cota in g["cotas"].items():
        e, v = cota["entidades"], float(valores[k])
        if cota.get("tipo") == "angulo":
            fs.append(lambda P, a=e[0], c=e[1], v=math.radians(v): [math.atan2(
                np.linalg.norm(np.cross(u(d(P, a)), u(d(P, c)))), float(u(d(P, a)) @ u(d(P, c)))) - v])
            continue
        a, c = (ext(e[0])[0], ext(e[0])[1]) if len(e) == 1 else e
        fs.append(lambda P, a=a, c=c, v=v: [np.linalg.norm(P[c] - P[a]) - v])
    return fs


def resolver(b, valores):
    """Resuelve la geometría 3D de `b` EN EL LUGAR con las cotas `valores` ({id: mm o grados}). Si queda en conflicto
    no mueve nada y devuelve ok=False. Grados de libertad: coordenadas libres − rango del jacobiano."""
    g = datos(b)
    if not g["puntos"]:
        return Resultado3D(True, 0)
    for k, cota in g["cotas"].items():
        if not valores.get(k, 0) > 0:
            return Resultado3D(False, None, f"La cota 3D {k} tiene que medir más que 0.")
        if cota.get("tipo") == "angulo" and not valores[k] < 180:
            return Resultado3D(False, None, f"La cota angular 3D {k} tiene que medir menos de 180°.")
    fijos = puntos_fijos(b)
    libres = [p for p in g["puntos"] if p not in fijos]
    fs = _ecuaciones(b, valores)
    x0 = np.array([c for p in libres for c in g["puntos"][p]], float)

    def puntos(x):
        P = _P(b)
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
            g["puntos"][p] = _lista(v)
    gdl = len(x0) - int(np.linalg.matrix_rank(sol.jac, tol=1e-8))
    return Resultado3D(True, gdl)


def _tangente(b, entidades):
    """(curva a, spline s, punto común): a es una línea o una spline y s una spline que empieza o termina en un
    extremo de a. ErrorBoceto si no comparten extremo."""
    g = datos(b)
    a, s = sorted(entidades, key=lambda i: g["curvas"][i]["tipo"] != "linea")
    pa, ps = g["curvas"][a]["puntos"], g["curvas"][s]["puntos"]
    for extremo in (0, -1):
        if ps[extremo] in (pa[0], pa[-1]):
            return a, s, ps[extremo]
    raise ErrorBoceto("Para la tangencia, la spline tiene que empezar o terminar en un extremo de la otra curva "
                      "(dibujala desde ese extremo: se encadenan solas).")


def _tangentes(b, cid, P):
    """{índice: vector} de la spline `cid` por sus tangencias. Con una línea, la dirección de la línea; entre dos
    splines, la cuerda entre los puntos vecinos al común (la misma para las dos: continuidad G1)."""
    g = datos(b)
    pts, salida = g["curvas"][cid]["puntos"], {}
    vecino = lambda c, p: g["curvas"][c]["puntos"][1 if g["curvas"][c]["puntos"][0] == p else -2]  # noqa: E731
    for r in g["restricciones"].values():
        if r["tipo"] != "tangente" or cid not in r["entidades"]:
            continue
        a, s, comun = _tangente(b, r["entidades"])
        if g["curvas"][a]["tipo"] == "linea":
            t = P[comun] - P[next(p for p in g["curvas"][a]["puntos"] if p != comun)]
        else:
            t = P[vecino(s, comun)] - P[vecino(a, comun)]          # del lado de a hacia el de s
        al_inicio = pts[0] == comun
        salida[0 if al_inicio else len(pts) - 1] = t if al_inicio == (cid == s) else -t
    return salida


# ---------------------------------------------------------------- geometría OCC
def a_mundo(plano, p):
    """Coordenadas del boceto [x, y, z] → punto 3D del mundo."""
    return plano.a_3d(p[0], p[1]) + plano.normal * p[2]


def a_boceto(plano, p, vector=False):
    """Punto (o vector) del mundo → coordenadas del boceto [x, y, z]."""
    d = np.asarray(p, float) - (0 if vector else plano.origen)
    return _lista((d @ plano.u, d @ plano.v, d @ plano.normal))


def _vec(plano, v):
    return np.asarray(v, float) @ np.array([plano.u, plano.v, plano.normal])


def _polilineas_texto(c, P, plano):
    o, u, v = P[c["puntos"][0]], np.array(c["u"]), np.array(c["v"])
    return [np.array([a_mundo(plano, o + x * u + y * v) for x, y in uv], np.float32)
            for uv in _contornos(c["texto"], c["altura"], c.get("fuente", "Arial")) if len(uv) >= 2]


def arista(b, cid, plano):
    """Arista OCC de la curva 3D `cid` en el mundo (la spline respeta sus tangencias); el texto da un compuesto de
    aristas rectas."""
    g = datos(b)
    c = g["curvas"][cid]
    P = _P(b)
    pts = [a_mundo(plano, P[p]) for p in c["puntos"]]
    t = c["tipo"]
    try:
        if t == "linea":
            return curvas3d.arista_recta(pts[0], pts[1])
        if t == "arco":
            return curvas3d.arista_arco(*pts)
        if t == "circulo":
            return curvas3d.arista_circulo(pts[0], c["radio"], _vec(plano, c["normal"]))
        if t == "elipse":
            return curvas3d.arista_elipse(pts[0], _vec(plano, c["eje_mayor"]), c["radio_menor"],
                                          _vec(plano, c["normal"]))
        if t == "conica":
            return curvas3d.arista_conica(*pts, c["rho"])
        if t == "texto":
            return curvas3d.compuesto_polilineas(_polilineas_texto(c, P, plano))
        tangentes = {i: _vec(plano, v) for i, v in _tangentes(b, cid, P).items()}
        return curvas3d.arista_spline(pts, tangentes, c.get("cerrada", False))
    except geo.ErrorGeometria as e:
        raise ErrorBoceto(f"No se pudo construir la curva 3D {cid}: {e}") from e


def polilineas_de(b, cid, plano, muestras=48):
    """Polilíneas (Nx3, mundo) de la curva 3D `cid` (varias si es un texto)."""
    c, P = datos(b)["curvas"][cid], _P(b)
    if c["tipo"] == "linea":
        return [np.array([a_mundo(plano, P[p]) for p in c["puntos"]], np.float32)]
    if c["tipo"] == "texto":
        return _polilineas_texto(c, P, plano)
    return [curvas3d.muestrear(arista(b, cid, plano), muestras)]


def polilineas(b, plano, muestras=48):
    """Polilíneas (Nx3, mundo) de las curvas 3D para dibujarlas en la vista (salta las que no se pueden construir)."""
    salida = []
    for cid in datos(b)["curvas"]:
        try:
            salida.extend(polilineas_de(b, cid, plano, muestras))
        except ErrorBoceto:
            continue
    return salida


def agregar_desde_mundo(b, desc, plano, construccion=False, origen=None):
    """Agrega la curva descrita por `curvas3d.describir` (coordenadas del mundo) al boceto 3D. `origen` anota de qué
    selección salió (Intersection Curve / Project To Surface). Devuelve el id."""
    t = desc["tipo"]
    pts = [a_boceto(plano, p) for p in desc.get("puntos", ())]
    if t == "linea":
        cid = agregar_linea(b, *pts, construccion)
    elif t == "arco":
        cid = agregar_arco(b, *pts, construccion)
    elif t == "circulo":
        cid = agregar_circulo(b, a_boceto(plano, desc["centro"]), desc["radio"],
                              a_boceto(plano, desc["normal"], vector=True), construccion)
    elif t == "elipse":
        cid = agregar_elipse(b, a_boceto(plano, desc["centro"]), a_boceto(plano, desc["eje_mayor"], vector=True),
                             desc["radio_menor"], a_boceto(plano, desc["normal"], vector=True), construccion)
    else:
        cid = agregar_spline(b, pts, construccion, desc.get("cerrada", False))
    if origen:
        datos(b)["curvas"][cid]["origen"] = origen
    return cid


# ---------------------------------------------------------------- serialización (claves enteras ↔ listas JSON)
def a_dict(g):
    return {"puntos": [[k, *v] for k, v in g.get("puntos", {}).items()],
            **{t: [{"id": k, **v} for k, v in g.get(t, {}).items()] for t in ("curvas", "restricciones", "cotas")}}


def desde_dict(d):
    g = {"puntos": {int(p[0]): [float(v) for v in p[1:4]] for p in d.get("puntos", [])}}
    for t in ("curvas", "restricciones", "cotas"):
        g[t] = {int(x["id"]): {k: v for k, v in x.items() if k != "id"} for x in d.get(t, [])}
    return g
