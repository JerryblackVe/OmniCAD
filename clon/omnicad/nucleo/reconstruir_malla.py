# -*- coding: utf-8 -*-
"""
Reconstruir un sólido desde una malla, sin IA (RI-2, docs/plan_reconstruir_solido.md): las decisiones geométricas, puras.
Mide la malla (`formas_malla`) y arma el plan; la herramienta `reconstruct_from_mesh` lo vuelve pasos normales del timeline
y el juez (`comparar_malla`) dice cuánto se acercó.

- `estrategia`: revolución si casi toda la superficie gira alrededor de un eje; si no, prisma en la dirección que mejor
  explica la pieza.
- `capas`: el prisma como una pila de tramos, entre las alturas de los planos perpendiculares a la dirección. Cada tramo sale
  del corte de mayor área: un agujero lateral o un empalme le comen área a los cortes que los cruzan, no al del cuerpo.
- `perfil_revolucion`: el medio corte que contiene al eje.
- `plan_agujeros` y `plan_acabados`: agujeros, patrones, empalmes y chaflanes, leídos de la ficha.
- `residuos` y `bloque`: lo que falta y lo que sobra, como cáscaras que se reconstruyen y se suman o se cortan.

El método sigue la idea de CADFit (arXiv 2605.01171): cortes, lazos, medidas ajustadas y residuos M−S y S−M, escrito desde
cero: no se usa su código y acá no hay red neuronal.
"""
import numpy as np

from . import geometria as geo
from . import malla as ml
from . import malla_seccion as ms

PARALELO = 1 - 1e-4                  # coseno: dos direcciones son la misma
AREA_NIVEL = 1e-4                    # plano más chico que esto (parte del área) no marca una altura
PRISMA_MINIMO = 0.75                 # volumen de la cáscara / (área del corte × alto): debajo de esto no es un prisma


def _paralelas(a, b):
    return abs(float(np.dot(a, b))) >= PARALELO


def _r(x):
    return round(float(x), 4) + 0.0


def _eje_mundo(d):
    for nombre, e in (("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1))):
        if _paralelas(d, e):
            return nombre
    return None


def _perpendicular(d):
    """Un vector unitario perpendicular a `d`."""
    u = np.cross(d, (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0))
    return u / np.linalg.norm(u)


# ---------------------------------------------------------------- qué estrategia
def _explica(ficha, d):
    """Parte del área que un prisma en la dirección `d` modela de una: planos a lo largo o de través y curvas paralelas."""
    total = 0.0
    for f in ficha["shapes"]:
        if f["type"] == "plane":
            c = abs(float(np.dot(f["normal"], d)))
            total += f["area"] * (c >= PARALELO or c <= 1 - PARALELO)
        elif f["type"] == "cylinder":
            total += f["area"] * _paralelas(f["axis"], d)
    return total / ficha["area"]


def direcciones(ficha):
    """Direcciones candidatas de prisma, de la que más explica a la que menos: normales de planos y ejes de cilindros."""
    salida = []
    for f in sorted(ficha["shapes"], key=lambda x: -x["area"]):
        d = f.get("normal") if f["type"] == "plane" else f.get("axis") if f["type"] == "cylinder" else None
        if d is not None and not any(_paralelas(d, x) for x in salida):
            salida.append(np.array(d, float))
    return sorted(salida, key=lambda d: -_explica(ficha, d))


def _niveles(ficha, d):
    """Cuántas alturas de planos hay a lo largo de `d`: cada una de más es una extrusión y una costura de más."""
    return len({round(float(np.dot(f["point"], d)) / (2 * ficha["tolerance"])) for f in ficha["shapes"]
                if f["type"] == "plane" and _paralelas(f["normal"], d) and f["area"] >= AREA_NIVEL * ficha["area"]})


def _es_revolucion(ficha):
    eje = ficha["revolution_axis"]
    curvas = sum(f["type"] != "plane" for f in ficha["shapes"])
    return eje is not None and eje["share"] >= 0.98 and curvas >= 2


def estrategia(ficha):
    """Estrategias a probar, en orden: [{"kind": "revolve", "axis_point", "axis"} y/o {"kind": "prism", "direction"}]."""
    prismas = [{"kind": "prism", "direction": d} for d in sorted(direcciones(ficha)[:3], key=lambda d: _niveles(ficha, d))]
    giro = []
    if ficha["revolution_axis"] is not None and ficha["revolution_axis"]["share"] >= 0.9:
        eje = ficha["revolution_axis"]
        giro = [{"kind": "revolve", "axis_point": np.array(eje["axis_point"], float), "axis": np.array(eje["axis"], float)}]
    return giro + prismas if _es_revolucion(ficha) else prismas + giro


def alineacion(e, ficha):
    """Rotación y traslación que dejan la pieza alineada con los ejes, o None si ya lo está: {"R", "t"}, con R de columnas
    (u, v, d). Un plano de construcción no acepta puntos libres: una pieza girada se modela derecha y al final un paso
    Mover la deja en su lugar. Para una revolución, además, el eje pasa a ser Z por el origen."""
    d = np.asarray(e["direction"] if e["kind"] == "prism" else e["axis"], float)
    if _eje_mundo(d) is not None:                       # solo ahí hay plano de origen sobre el que dibujar
        return None
    u = next((np.array(f["normal"], float) for f in sorted(ficha["shapes"], key=lambda x: -x["area"])
              if f["type"] == "plane" and abs(float(np.dot(f["normal"], d))) < 1e-4), _perpendicular(d))
    R = np.c_[u, np.cross(d, u), d]
    return {"R": R, "t": np.asarray(e["axis_point"], float) if e["kind"] == "revolve" else np.zeros(3)}


def mover(m, a):
    """La malla en el marco alineado."""
    return ml.Malla((m.vertices - a["t"]) @ a["R"], m.caras, m.grupos)


def en_marco(e, a):
    """La estrategia vista desde el marco alineado."""
    if e["kind"] == "prism":
        return {"kind": "prism", "direction": np.array([0.0, 0.0, 1.0])}
    return {"kind": "revolve", "axis_point": np.zeros(3), "axis": np.array([0.0, 0.0, 1.0])}


def angulos(R):
    """Giros [rx, ry, rz] en grados de `move_body`, que aplica X, después Y y después Z."""
    ry = np.arcsin(np.clip(-R[2, 0], -1, 1))
    if abs(R[2, 0]) > 1 - 1e-9:                                 # ry = ±90: rx y rz giran lo mismo, alcanza con rx
        return [float(np.degrees(x)) for x in (np.arctan2(-R[1, 2], R[1, 1]), ry, 0.0)]
    return [float(np.degrees(x)) for x in (np.arctan2(R[2, 1], R[2, 2]), ry, np.arctan2(R[1, 0], R[0, 0]))]


def marco(d, m):
    """Plano de origen perpendicular a `d` (alineada), desplazado al extremo de la malla: {"plane": "XY", "offset": mm}."""
    V = m.vertices[np.unique(m.caras)]
    for nombre in ("XY", "XZ", "YZ"):
        plano = geo.Plano(nombre)
        if _paralelas(plano.normal, d):
            return {"plane": nombre, "offset": _r((V @ plano.normal).min())}
    raise geo.ErrorGeometria("La dirección no sigue un eje del mundo.")


def marco_eje(o, a):
    """Plano de origen que contiene al eje (alineado): {"plane": "XZ", "offset": mm}."""
    for nombre in ("XZ", "YZ", "XY"):
        plano = geo.Plano(nombre)
        if abs(float(plano.normal @ a)) < 1e-6:
            return {"plane": nombre, "offset": _r(np.asarray(o, float) @ plano.normal)}
    raise geo.ErrorGeometria("El eje no sigue un eje del mundo.")


# ---------------------------------------------------------------- lazos y regiones
def _lazos(m, plano):
    """Lazos cerrados del corte de la malla con el plano; [(P, área)] sin signo. Un corte que no toca nada no es error."""
    try:
        cortes = ms.seccion(m, plano)
    except geo.ErrorGeometria:
        return []
    salida = []
    for P, cerrada in cortes:
        if cerrada and len(P) >= 3 and abs(ml._area_2d(P)) > 1e-6:
            salida.append((P, abs(ml._area_2d(P))))
    return salida


def regiones(lazos):
    """Agrupa lazos por contención: [{"outer": P, "holes": [P], "area": neta}]; una isla dentro de un hueco es otra región."""
    lazos = sorted(lazos, key=lambda x: -x[1])
    contenedores = [[j for j in range(i) if ml._punto_en_poligono(lazos[i][0][0], lazos[j][0])] for i in range(len(lazos))]
    salida, de = [], {}
    for i, (P, area) in enumerate(lazos):
        if len(contenedores[i]) % 2 == 0:
            de[i] = len(salida)
            salida.append({"outer": P, "holes": [], "area": area})
        else:
            padre = de[contenedores[i][-1]]
            salida[padre]["holes"].append(P)
            salida[padre]["area"] -= area
    return salida


def _area(regs):
    return sum(r["area"] for r in regs)


def _circulo_de(P, tol):
    """(centro, radio) si la polilínea cerrada P es un círculo dentro de `tol`."""
    c = ms._circulo(P)
    if c is None or float(np.abs(np.linalg.norm(P - c[0], axis=1) - c[1]).max()) > tol:
        return None
    return c


def circulos(ficha, plano, d):
    """Cilindros paralelos a `d` vistos en el plano: [(centro uv, radio)] exactos, para acomodar los arcos ajustados."""
    salida = []
    for f in ficha["shapes"]:
        if f["type"] == "cylinder" and _paralelas(f["axis"], d):
            q = np.array(f["axis_point"]) - plano.origen
            salida.append((np.array([q @ plano.u, q @ plano.v]), f["radius"]))
    return salida


def _sobre_circulo(p, c, r):
    d = p - c
    return c + d * (r / max(float(np.linalg.norm(d)), 1e-12))


def _sin_colineales(P, cerrada):
    """Saca los puntos que no doblan: el corte pasa por las diagonales de las facetas, en mitad de cada cuerda."""
    e1, e2 = P - np.roll(P, 1, 0), np.roll(P, -1, 0) - P
    largos = np.maximum(np.linalg.norm(e1, axis=1) * np.linalg.norm(e2, axis=1), 1e-300)
    dobla = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) / largos > 1e-6
    if not cerrada:
        dobla[[0, -1]] = True
    return P[dobla] if dobla.sum() >= 3 else P


def _sobre_arco(Q, c, r, tol):
    """Qué tramos de la polilínea corren sobre el círculo: sus dos puntas caen en él, a menos de 60° entre sí (las cuatro
    esquinas de un rectángulo también caben en un círculo)."""
    d = Q - c
    radio = np.linalg.norm(d, axis=1)
    en = np.abs(radio - r) <= tol
    return en[:-1] & en[1:] & ((d[:-1] * d[1:]).sum(1) >= 0.5 * radio[:-1] * radio[1:])


def _corrida(fila):
    """Cuántos tramos seguidos, desde el primero, corren sobre el círculo."""
    return int(np.argmin(fila)) if not fila.all() else len(fila)


def _crudas(P, cerrada, tol, exactos):
    """Como `ms._lineas_arcos`, pero lo que corre sobre un círculo medido es un solo arco: el ajuste libre deja en tramos
    rectos un empalme de pocas facetas."""
    Q = ms.cerrar(P) if cerrada else P
    sigue = np.array([_sobre_arco(Q, c, r, tol) for c, r in exactos]).reshape(len(exactos), len(Q) - 1)
    if not sigue.any():
        return ms._lineas_arcos(P, cerrada, tol)
    if cerrada:
        cortes = np.flatnonzero(~(sigue & np.roll(sigue, 1, 1)).any(0) & sigue.any(0))
        if not len(cortes):                                     # la vuelta entera sobre un círculo
            c, r = exactos[int(np.argmax(sigue.all(1)))]
            return [{"tipo": "circulo", "centro": c, "radio": r, "datos": P, "cerrada": True}]
        Q, sigue = ms.cerrar(np.roll(P, -int(cortes[0]), 0)), np.roll(sigue, -int(cortes[0]), 1)
    curvas, suelto, i = [], 0, 0
    while i < sigue.shape[1]:
        largos = [_corrida(fila[i:]) for fila in sigue]
        k = int(np.argmax(largos))
        if largos[k] < 2:
            i += 1
            continue
        if i > suelto:
            curvas += ms._lineas_arcos(Q[suelto:i + 1], False, tol)
        R = Q[i:i + largos[k] + 1]
        curvas.append({"tipo": "arco", "puntos": [R[0], R[len(R) // 2], R[-1]], "datos": R, "exacto": exactos[k]})
        suelto = i = i + largos[k]
    if suelto < sigue.shape[1]:
        curvas += ms._lineas_arcos(Q[suelto:], False, tol)
    return curvas


def _curvas(P, cerrada, tol, exactos):
    """Polilínea → líneas y arcos encadenados. Un arco o círculo que coincide con un cilindro medido toma sus medidas
    exactas: el corte pasa por las cuerdas y quedaría apenas adentro."""
    crudas = _crudas(_sin_colineales(P, cerrada), cerrada, tol, exactos)
    if len(crudas) == 1 and crudas[0]["tipo"] == "circulo":
        c, r = crudas[0]["centro"], crudas[0]["radio"]
        for cc, rr in exactos:
            if np.linalg.norm(cc - c) <= 2 * tol and abs(rr - r) <= 2 * tol:
                c, r = cc, rr
                break
        return [{"tipo": "circulo", "centro": c, "radio": r}]
    juntas = [np.array(c["puntos"][0], float) for c in crudas] + [np.array(crudas[-1]["puntos"][-1], float)]
    medios = [np.array(c["puntos"][1], float) if c["tipo"] == "arco" else None for c in crudas]
    for i, c in enumerate(crudas):
        if c["tipo"] != "arco":
            continue
        a = ms._arco3(c["datos"])
        cerca = [c["exacto"]] if "exacto" in c else [
            (cc, rr) for cc, rr in exactos if a is not None and np.linalg.norm(cc - a[0]) <= 3 * tol and abs(rr - a[1]) <= 3 * tol]
        for cc, rr in cerca[:1]:
            juntas[i], juntas[i + 1] = _sobre_circulo(juntas[i], cc, rr), _sobre_circulo(juntas[i + 1], cc, rr)
            medios[i] = _sobre_circulo(medios[i], cc, rr)
    if cerrada:
        juntas[-1] = juntas[0]
    salida = []
    for i, c in enumerate(crudas):
        if np.linalg.norm(juntas[i + 1] - juntas[i]) < 1e-3:
            continue
        salida.append({"tipo": "arco", "a": juntas[i], "m": medios[i], "b": juntas[i + 1]} if c["tipo"] == "arco"
                      else {"tipo": "linea", "a": juntas[i], "b": juntas[i + 1]})
    return salida


def entidades(curvas):
    """Entidades de `sketch_from_spec`."""
    def xy(p):
        return [_r(p[0]), _r(p[1])]
    salida = []
    for c in curvas:
        if c["tipo"] == "circulo":
            salida.append({"type": "circle", "center": xy(c["centro"]), "radius": _r(c["radio"])})
        elif c["tipo"] == "arco":
            salida.append({"type": "arc", "start": xy(c["a"]), "mid": xy(c["m"]), "end": xy(c["b"])})
        else:
            salida.append({"type": "line", "start": xy(c["a"]), "end": xy(c["b"])})
    return salida


# ---------------------------------------------------------------- prisma: capas
def alturas(m, ficha, plano, tol):
    """Alturas (sobre la normal del plano) de los extremos y de los planos perpendiculares con área."""
    h = (m.vertices[np.unique(m.caras)] - plano.origen) @ plano.normal
    niveles = [float(h.min()), float(h.max())]
    for f in ficha["shapes"]:
        if f["type"] == "plane" and _paralelas(f["normal"], plano.normal) and f["area"] >= AREA_NIVEL * ficha["area"]:
            niveles.append(float((np.array(f["point"]) - plano.origen) @ plano.normal))
    salida = []
    for x in sorted(niveles):
        if not salida or x - salida[-1] > tol:
            salida.append(x)
    return salida


def _sin_circulos(regs, quitar, tol):
    """Saca de las regiones los lazos que son agujeros que después se hacen con su paso."""
    salida = []
    for r in regs:
        huecos = []
        area = r["area"]
        for P in r["holes"]:
            c = _circulo_de(P, tol)
            if c is not None and any(np.linalg.norm(cc - c[0]) <= 2 * tol and abs(rr - c[1]) <= 2 * tol for cc, rr in quitar):
                area += abs(ml._area_2d(P))
            else:
                huecos.append(P)
        salida.append(dict(r, holes=huecos, area=area))
    return salida


def _iguales(a, b, tol):
    """¿Dos cortes son el mismo? (Cada lazo de uno pasa por el otro, dentro de la tolerancia.)"""
    if len(a) != len(b) or abs(_area(a) - _area(b)) > 0.002 * max(_area(a), 1e-9):
        return False
    def lazos(regs):
        return [ms.cerrar(P) for r in regs for P in (r["outer"], *r["holes"])]
    A, B = lazos(a), lazos(b)
    return len(A) == len(B) and all(min(float(ms.distancia(P, Q).max()) for Q in B) <= tol for P in A)


def capas(m, ficha, plano, tol, agujeros=()):
    """Tramos del prisma, de abajo arriba: [{"h0", "h1", "regions": [...]}]. Los tramos con el mismo corte se juntan."""
    d = plano.normal
    niveles = alturas(m, ficha, plano, tol)
    quitar = []
    for h in agujeros:
        if _paralelas(h["axis"], d):
            q = np.array(h["entry"]) - plano.origen
            uv = np.array([q @ plano.u, q @ plano.v])
            quitar.append((uv, h["diameter"] / 2))
            if h["counterbore"]:
                quitar.append((uv, h["counterbore"]["diameter"] / 2))
    salida = []
    for a, b in zip(niveles, niveles[1:], strict=False):
        margen = min(0.02 * (b - a), tol)
        mejor = []
        for h in (a + margen, (a + b) / 2, b - margen):
            regs = _sin_circulos(regiones(_lazos(m, plano.desplazado(h))), quitar, tol)
            if _area(regs) > _area(mejor):
                mejor = regs
        if not mejor:
            continue
        if salida and salida[-1]["h1"] >= a - 1e-9 and _iguales(salida[-1]["regions"], mejor, tol):
            salida[-1]["h1"] = b
        else:
            salida.append({"h0": a, "h1": b, "regions": mejor})
    return salida


def curvas_region(r, tol, exactos):
    """Curvas del contorno y de los huecos de una región."""
    salida = []
    for P in (r["outer"], *r["holes"]):
        salida += _curvas(P, True, tol, exactos)
    return salida


# ---------------------------------------------------------------- revolución
def perfil_revolucion(m, plano, o, a, tol, exactos=()):
    """Medio corte por el eje (o, a), en coordenadas del plano. Devuelve [{"curves": [...], "closing": [p, q] o None, "area"}]:
    cada lazo del lado positivo; el que toca el eje queda abierto y `closing` es su tramo sobre el eje."""
    q = np.array([(np.asarray(o) - plano.origen) @ plano.u, (np.asarray(o) - plano.origen) @ plano.v])
    e = np.array([np.dot(a, plano.u), np.dot(a, plano.v)], float)
    e /= np.linalg.norm(e)

    def lado(P):
        w = P - q
        return w[:, 0] * e[1] - w[:, 1] * e[0]

    def sobre_eje(p):
        return q + e * float((p - q) @ e)

    medios = {}
    for P, _ in _lazos(m, plano):
        s = lado(P)
        medios[1] = medios.get(1, 0.0) + float(np.abs(s[s > 0]).sum())
        medios[-1] = medios.get(-1, 0.0) + float(np.abs(s[s < 0]).sum())
    signo = 1 if medios.get(1, 0.0) >= medios.get(-1, 0.0) else -1
    salida = []
    margen = max(tol * 0.1, 1e-6)
    for P, area in _lazos(m, plano):
        s = lado(P) * signo
        if (s > -margen).all():
            salida.append({"curves": _curvas(P, True, tol, exactos), "closing": None, "area": area})
            continue
        if (s < margen).all():
            continue
        # el lazo cruza el eje: se recorre desde un punto del lado negativo y se guardan los tramos positivos
        k = int(np.argmin(s))
        P, s = np.roll(P, -k, axis=0), np.roll(s, -k)
        Q, t = np.vstack([P, P[:1]]), np.r_[s, s[0]]
        i = 0
        while i < len(s):
            if t[i] <= 0:
                i += 1
                continue
            ini = i
            while i < len(s) and t[i + 1] > 0:
                i += 1
            fin = i + 1
            A, B = (sobre_eje(Q[j] + (Q[g] - Q[j]) * (t[j] / (t[j] - t[g]))) for j, g in ((ini, ini - 1), (fin - 1, fin)))
            cadena = np.vstack([A, Q[ini:fin], B])
            cadena = cadena[np.r_[True, np.linalg.norm(np.diff(cadena, axis=0), axis=1) > 1e-7]]
            if len(cadena) >= 2:
                salida.append({"curves": _curvas(cadena, False, tol, exactos), "closing": [B, A],
                               "area": abs(ml._area_2d(cadena))})
            i = fin
    return salida


def circulos_revolucion(ficha, plano, o, a):
    """Arcos exactos del medio corte: esferas y toros coaxiales, vistos en el plano del eje."""
    o, a = np.asarray(o, float), np.asarray(a, float)
    salida = []
    for f in ficha["shapes"]:
        if f["type"] == "sphere":
            c = np.array(f["center"]) - plano.origen
            salida.append((np.array([c @ plano.u, c @ plano.v]), f["radius"]))
        elif f["type"] == "torus":
            for lado in (1, -1):
                c = np.array(f["center"]) + lado * f["major_radius"] * plano.u - plano.origen
                salida.append((np.array([c @ plano.u, c @ plano.v]), f["minor_radius"]))
    return salida


# ---------------------------------------------------------------- agujeros y patrones
def plan_agujeros(ficha):
    """Agujeros a crear con su paso: uno por eje, juntando el abocardado con su agujero. Cada uno: {"diameter", "through",
    "depth", "entry", "axis", "counterbore": {"diameter", "depth"} o None, "shapes"}."""
    usados, salida = set(), []
    formas = {f["id"]: f for f in ficha["shapes"]}
    ordenados = sorted(ficha["holes"], key=lambda h: h["diameter"])
    for h in ordenados:
        if h["shape"] in usados:
            continue
        a, o = np.array(h["axis"], float), np.array(h["axis_point"], float)
        coaxial = [x for x in ordenados if x["shape"] != h["shape"] and x["shape"] not in usados and _paralelas(x["axis"], a)
                   and np.linalg.norm(np.cross(a, np.subtract(x["axis_point"], o))) < 1e-2]
        fin = o + a * h["depth"]
        iguales = [x for x in coaxial if abs(x["diameter"] - h["diameter"]) < 1e-3]     # el mismo agujero, cruzado por otro
        coaxial = [x for x in coaxial if abs(x["diameter"] - h["diameter"]) >= 1e-3]
        for x in iguales:
            usados.add(x["shape"])
            puntas = [o, fin, np.array(x["axis_point"], float), np.array(x["axis_point"], float) + a * x["depth"]]
            o, fin = min(puntas, key=lambda p: float(p @ a)), max(puntas, key=lambda p: float(p @ a))
        extremos = [o, fin]
        largo = float(np.linalg.norm(fin - o))
        boca = coaxial[0] if coaxial else None
        if boca is not None:
            B0 = np.array(boca["axis_point"], float)
            B1 = B0 + a * boca["depth"]
            lejos = max((B0, B1), key=lambda p: min(np.linalg.norm(p - o), np.linalg.norm(p - fin)))
            cerca = min(extremos, key=lambda p: np.linalg.norm(p - lejos))
            otro = fin if cerca is o else o
            usados.add(boca["shape"])
            entrada, total = lejos, float(np.linalg.norm(lejos - otro))
        elif h["floor_shape"] is not None:
            piso = np.array(formas[h["floor_shape"]].get("point", o), float)
            entrada, total = max(extremos, key=lambda p: abs(float((p - piso) @ a))), largo
        else:
            entrada, total = fin, largo
        usados.add(h["shape"])
        salida.append({"diameter": h["diameter"], "through": bool(h["through"]) and all(x["through"] for x in iguales),
                       "depth": _r(total), "entry": [_r(x) for x in entrada], "axis": [float(x) for x in a],
                       "counterbore": None if boca is None else {"diameter": boca["diameter"], "depth": boca["depth"]},
                       "shapes": [h["shape"]] + [x["shape"] for x in iguales] + ([boca["shape"]] if boca else [])})
    return salida


def agrupar_patrones(ficha, agujeros):
    """Reparte los agujeros en patrones y sueltos: (sueltos, [{"hole", "kind", ...}]). Un patrón se usa si sus direcciones
    siguen ejes del mundo (rectangular) o si es de vuelta completa (circular)."""
    por_forma = {k: h for h in agujeros for k in h["shapes"]}
    usados, grupos = set(), []
    for p in ficha["patterns"]:
        miembros = [por_forma[k] for k in p["shapes"] if k in por_forma and por_forma[k]["counterbore"] is None]
        if len(miembros) != p["count"] or any(id(h) in usados for h in miembros):
            continue
        if p["type"] == "rectangular_pattern":
            ejes = [_eje_mundo(x["direction"]) for x in p["directions"]]
            if None in ejes:
                continue
            base = [np.abs(np.array(x["direction"], float)) for x in p["directions"]]
            primero = min(miembros, key=lambda h: tuple(float(np.dot(h["entry"], b)) for b in base))
            grupos.append({"hole": primero, "kind": "rectangular", "axes": ejes, "counts": [x["count"] for x in p["directions"]],
                           "steps": [x["step"] for x in p["directions"]]})
        else:
            grupos.append({"hole": miembros[0], "kind": "circular", "count": p["count"], "axis_point": p["axis_point"],
                           "axis": p["axis"]})
        usados.update(id(h) for h in miembros)
    return [h for h in agujeros if id(h) not in usados], grupos


# ---------------------------------------------------------------- empalmes y chaflanes
def _esquina(a, b):
    """Recta donde se cortan dos planos (puntos sobre cada uno, normales): (punto, dirección); None si son paralelos."""
    na, nb = np.array(a["normal"], float), np.array(b["normal"], float)
    d = np.cross(na, nb)
    if np.linalg.norm(d) < 1e-6:
        return None
    A = np.array([na, nb, d])
    p = np.linalg.solve(A, [na @ np.array(a["point"]), nb @ np.array(b["point"]), d @ np.array(a["point"])])
    return p, d / np.linalg.norm(d)


def _en_recta(p, punto, d):
    return punto + d * float((np.asarray(p) - punto) @ d)


def _empalme_recto(f, fichas):
    """Arista de un empalme recto: la esquina de los dos planos tangentes al cilindro."""
    a = np.array(f["axis"], float)
    o = np.array(f["axis_point"], float)
    planos = [fichas[k] for k in f["neighbors"] if fichas[k]["type"] == "plane"]
    tangentes = [p for p in planos if abs(float(np.dot(p["normal"], a))) < 1e-3
                 and abs(abs(float((o - np.array(p["point"])) @ np.array(p["normal"]))) - f["radius"]) < 0.02 * max(f["radius"], 1)]
    if len(tangentes) < 2:
        return None
    r = _esquina(tangentes[0], tangentes[1])
    return None if r is None else _en_recta(o + a * f["height"] / 2, *r)


def _borde_redondo(f, fichas):
    """Arista circular de un toro o un cono: donde se cortan el plano perpendicular y la pared coaxial vecinos."""
    a = np.array(f["axis"], float)
    plano = next((fichas[k] for k in f["neighbors"] if fichas[k]["type"] == "plane"
                  and _paralelas(fichas[k]["normal"], a)), None)
    pared = next((fichas[k] for k in f["neighbors"] if fichas[k]["type"] == "cylinder" and _paralelas(fichas[k]["axis"], a)), None)
    if plano is None or pared is None:
        return None
    centro = np.array(pared["axis_point"], float)
    z = float((np.array(plano["point"]) - centro) @ a)
    radial = np.array(f["sample_point"]) - centro
    radial -= a * float(radial @ a)
    radial /= max(float(np.linalg.norm(radial)), 1e-12)
    return centro + a * z + radial * pared["radius"]


def _chaflan(f, fichas):
    """(punto de la esquina, distancia sobre cada cara) de un chaflán plano: la esquina de sus dos planos vecinos."""
    nc = np.array(f["normal"], float)
    pc = np.array(f["point"], float)
    planos = [fichas[k] for k in f["neighbors"] if fichas[k]["type"] == "plane"]
    candidatos = sorted(planos, key=lambda p: -p["area"])
    for i, a in enumerate(candidatos):
        for b in candidatos[i + 1:]:
            r = _esquina(a, b)
            if r is None or abs(float(np.dot(nc, r[1]))) > 1e-3:
                continue
            x = _en_recta(pc, *r)
            ea, eb = np.cross(r[1], a["normal"]), np.cross(r[1], b["normal"])
            altura = abs(float((x - pc) @ nc))
            ca, cb = abs(float(ea @ nc)), abs(float(eb @ nc))
            if ca < 1e-3 or cb < 1e-3:
                continue
            return x, altura / ca, altura / cb
    return None


def plan_acabados(ficha, direccion=None):
    """Empalmes y chaflanes que la pila de extrusiones no da: los que no siguen a `direccion` (con None, todos).
    Devuelve ([{"kind": "fillet" o "chamfer", "size", "size2", "edges": [puntos]}], [lo que no se pudo ubicar])."""
    fichas = {f["id"]: f for f in ficha["shapes"]}
    grupos, sueltos = {}, []
    agujeros = {h["shape"] for h in ficha["holes"]}

    def sumar(tipo, medida, medida2, punto):
        clave = (tipo, round(medida, 2), round(medida2, 2))
        grupos.setdefault(clave, {"kind": tipo, "size": medida, "size2": medida2, "edges": []})["edges"].append(
            [_r(x) for x in punto])

    for f in ficha["shapes"]:
        if f["id"] in agujeros:
            continue
        sigue = direccion is not None and f["type"] == "cylinder" and _paralelas(f["axis"], direccion)
        if f["type"] == "cylinder" and not sigue and f["arc_degrees"] < 300:
            p = _empalme_recto(f, fichas)
            sumar("fillet", f["radius"], f["radius"], p) if p is not None else sueltos.append(f)
        elif f["type"] == "torus":
            p = _borde_redondo(f, fichas)
            sumar("fillet", f["minor_radius"], f["minor_radius"], p) if p is not None else sueltos.append(f)
        elif f["type"] == "cone":
            p = _borde_redondo(f, fichas)
            if p is None:
                sueltos.append(f)
            else:
                alto = abs(f["height"])
                ancho = abs(f["radius_end"] - f["radius_start"])
                sumar("chamfer", alto, ancho, p)
        elif f["type"] == "plane" and direccion is not None:
            c = abs(float(np.dot(f["normal"], direccion)))
            if c < PARALELO and c > 1 - PARALELO:
                r = _chaflan(f, fichas)
                if r is None:
                    sueltos.append(f)
                else:
                    sumar("chamfer", r[1], r[2], r[0])
    return list(grupos.values()), sueltos


# ---------------------------------------------------------------- residuos
def residuos(objetivo, actual, tol, tope=6):
    """Cáscaras de lo que falta y lo que sobra: [{"kind": "add" o "cut", "mesh": Malla, "volume"}], de la mayor a la menor.
    Una cáscara más fina que la tolerancia es ruido del teselado, no una función sin modelar."""
    salida = []
    for tipo, a, b in (("add", objetivo, actual), ("cut", actual, objetivo)):
        try:
            resto = ml.combinar([a, b], operacion="cortar", motor="manifold")
        except geo.ErrorGeometria:
            continue
        for s in ml.separar(resto, tipo="cascaras"):
            v, area = abs(s.volumen()), s.area()
            if area > 0 and 2 * v / area > tol and len(s.caras) >= 4:
                salida.append({"kind": tipo, "mesh": s, "volume": v})
    return sorted(salida, key=lambda r: -r["volume"])[:tope]


def bloque(shell, tol):
    """Mejor prisma para una cáscara residual: {"direction", "fit"} o None. Se prueba cada eje, los únicos con plano de
    origen, y se queda con el que más se parece a un prisma (volumen contra área × alto)."""
    V = shell.vertices[np.unique(shell.caras)]
    mejor, puntaje = None, PRISMA_MINIMO
    for d in np.eye(3):
        u = _perpendicular(d)
        h = V @ d
        a, b = float(h.min()), float(h.max())
        if b - a <= tol:
            continue
        plano = geo.Plano.desde_marco(d * ((a + b) / 2), d, u)
        regs = regiones(_lazos(shell, plano))
        area = _area(regs)
        if area <= 0:
            continue
        s = abs(shell.volumen()) / (area * (b - a))
        if abs(1 - s) < abs(1 - puntaje) or mejor is None and s >= PRISMA_MINIMO:
            mejor, puntaje = d, s
    return None if mejor is None else {"direction": mejor, "fit": puntaje}


def desviacion_ajuste(tolerancia):
    """Cuánto puede apartarse un perfil de su corte: alcanza la mitad de la tolerancia pedida y no hace falta menos."""
    return max(min(tolerancia / 2, 0.05), 1e-3)
