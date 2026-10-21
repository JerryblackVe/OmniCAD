# -*- coding: utf-8 -*-
"""Fuzzer de B-39: uniones booleanas con herramientas enterradas (total o parcialmente) en un cuerpo base.

Para cada caso (semilla fija) arma una base (pared, caja hueca, tubo, placa con agujero) y de 1 a 4 herramientas
(cilindro, caja, esfera, toro, prisma hexagonal, cuña) puestas contra rasgos de la base: caras internas y
externas, tapas, aristas, con tangencia exacta o desplazada por 0, 1e-9, 1e-6, 1e-3 mm. Une una por una y mide:
validez, un solo sólido, estanqueidad (aristas libres / no manifold) y el volumen contra el que sale de otra
cuenta (Vb + Vh − Vcomún y Vb + V(h − b)); las herramientas se unen en dos órdenes y deben dar el mismo volumen.

Uso (desde clon/): .venv/Scripts/python.exe ../scripts/fuzz_b39.py [--casos N] [--semilla S] [--desde I]
Sale con 0 si no hay fallos. Con fallos imprime cada caso mínimo reproducible (semilla + índice)."""
import argparse
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "clon"))

from OCP.BRepPrimAPI import BRepPrimAPI_MakeWedge  # noqa: E402
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.nucleo import revision as rv  # noqa: E402

EPS = (0.0, 1e-9, 1e-6, 1e-3)
REL = 1e-6          # tolerancia relativa de volumen


# ---------------------------------------------------------------- bases
def base_pared(r):
    return geo.booleano(geo.cilindro(30, 140), geo.cilindro(27, 140), "cortar"), {
        "caras": [27.0, 30.0], "z": [0.0, 140.0], "centro": (0, 0, 70), "radial": True, "r": (27.0, 30.0)}


def base_caja_hueca(r):
    ext = geo.caja(60, 50, 40, (-30, -25, 0))
    hueco = geo.caja(54, 44, 34, (-27, -22, 3))
    cuerpo = geo.booleano(ext, hueco, "cortar")
    return cuerpo, {"caras": [27.0, 30.0], "z": [3.0, 37.0, 0.0, 40.0], "centro": (0, 0, 20), "radial": False,
                    "xs": (-30, -27, 27, 30), "ys": (-25, -22, 22, 25)}


def base_tubo(r):
    # tubo abierto con extremos: pared r10–12, alto 80
    return geo.booleano(geo.cilindro(12, 80), geo.cilindro(10, 80), "cortar"), {
        "caras": [10.0, 12.0], "z": [0.0, 80.0], "centro": (0, 0, 40), "radial": True, "r": (10.0, 12.0)}


def base_placa(r):
    placa = geo.caja(80, 60, 8, (-40, -30, 0))
    agujero = geo.cilindro(10, 8, (0, 0, 0))
    return geo.booleano(placa, agujero, "cortar"), {
        "caras": [10.0], "z": [0.0, 8.0], "centro": (0, 0, 4), "radial": True, "r": (10.0, 10.0),
        "xs": (-40, 40), "ys": (-30, 30)}


BASES = {"pared": base_pared, "caja_hueca": base_caja_hueca, "tubo": base_tubo, "placa": base_placa}


# ---------------------------------------------------------------- herramientas
def cuna(dx, dy, dz, origen):
    w = BRepPrimAPI_MakeWedge(gp_Ax2(gp_Pnt(*origen), gp_Dir(0, 0, 1)), dx, dy, dz, dx * 0.4)
    return w.Shape()


def prisma_hex(r, h, base, eje):
    caras = [geo.cilindro(r, h, base, eje)]
    # prisma hexagonal = caja rotada intersectada 3 veces: más simple, una caja larga y otra girada 60° y 120°
    ancho = r * 1.7
    cajas = []
    for ang in (0, 60, 120):
        c = geo.caja(ancho, 4 * r, h, (-ancho / 2, -2 * r, 0))
        cajas.append(geo.rotar(c, (0, 0, 0), (0, 0, 1), ang))
    p = cajas[0]
    for c in cajas[1:]:
        p = geo.booleano(p, c, "intersecar")
    return p, caras


def poner(forma, eje, pos):
    """Gira una herramienta modelada sobre +Z para que su eje sea `eje` y la traslada a `pos`."""
    if eje == (1, 0, 0):
        forma = geo.rotar(forma, (0, 0, 0), (0, 1, 0), 90)
    elif eje == (0, 1, 0):
        forma = geo.rotar(forma, (0, 0, 0), (1, 0, 0), -90)
    return geo.trasladar(forma, pos)


def herramienta(rng, tipo, tam):
    """Herramienta centrada en el origen (caja envolvente simétrica) para ubicarla por su centro."""
    if tipo == "cilindro":
        r, h = tam * rng.uniform(0.3, 1.0), tam * rng.uniform(0.5, 3.0)
        return geo.cilindro(r, h, (0, 0, -h / 2)), (r, r, h / 2)
    if tipo == "caja":
        a, b, c = (tam * rng.uniform(0.4, 2.0) for _ in range(3))
        return geo.caja(a, b, c, (-a / 2, -b / 2, -c / 2)), (a / 2, b / 2, c / 2)
    if tipo == "esfera":
        r = tam * rng.uniform(0.4, 1.2)
        return geo.esfera(r), (r, r, r)
    if tipo == "toro":
        rm = tam * rng.uniform(0.8, 1.6)
        rn = rm * rng.uniform(0.2, 0.6)
        return geo.toroide(rm, rn), (rm + rn, rm + rn, rn)
    if tipo == "prisma":
        r, h = tam * rng.uniform(0.4, 1.0), tam * rng.uniform(0.5, 2.5)
        p, _ = prisma_hex(r, h, (0, 0, 0), (0, 0, 1))
        return geo.trasladar(p, (0, 0, -h / 2)), (r, r, h / 2)
    d = tam * rng.uniform(0.6, 2.0)
    return geo.trasladar(cuna(d, d * 0.8, d * 0.7, (0, 0, 0)), (-d / 2, -d * 0.4, -d * 0.35)), (d / 2, d * 0.4, d * 0.35)


TIPOS = ("cilindro", "caja", "esfera", "toro", "prisma", "cuna")


def ubicar(rng, info, semi, base_nombre):
    """Posición del centro de la herramienta: apoyada contra un rasgo de la base con tangencia ± eps, o libre."""
    cx, cy, cz = info["centro"]
    modo = rng.choice(("tangente_interior", "tangente_exterior", "enterrada", "coplanar_tapa", "arista", "libre"))
    eps = rng.choice(EPS) * rng.choice((-1, 1))
    ang = rng.uniform(0, 2 * math.pi) if rng.random() < 0.5 else rng.choice((0, math.pi / 2, math.pi, 3 * math.pi / 2))
    z = rng.choice(info["z"][:2]) if rng.random() < 0.2 else cz + rng.uniform(-0.4, 0.4) * (cz * 2 if cz else 10)
    if info.get("radial"):
        r0, r1 = info["r"]
        if modo == "tangente_interior":
            rad = r0 + semi[0] + eps     # la herramienta toca la cara interior desde adentro de la pared
        elif modo == "tangente_exterior":
            rad = r1 - semi[0] + eps
        elif modo == "enterrada":
            rad = (r0 + r1) / 2 + rng.uniform(-0.1, 0.1) * (r1 - r0)
        elif modo == "coplanar_tapa":
            rad = (r0 + r1) / 2
            z = info["z"][rng.randrange(2)] + (semi[2] if rng.random() < 0.5 else -semi[2]) + eps
        elif modo == "arista":
            rad = r0 if rng.random() < 0.5 else r1
            rad += eps
        else:
            rad = rng.uniform(r0 - 3, r1 + 3)
        return (rad * math.cos(ang), rad * math.sin(ang), z), modo, eps
    xs, ys = info["xs"], info["ys"]
    lado = rng.randrange(4)
    if lado < 2:
        x = (xs[1] if lado == 0 else xs[2])
        x += (semi[0] if lado == 0 else -semi[0]) * (1 if modo != "tangente_exterior" else -1) + eps
        if modo == "enterrada":
            x = (xs[0] + xs[1]) / 2 if lado == 0 else (xs[2] + xs[3]) / 2
        return (x, rng.uniform(-15, 15), z), modo, eps
    y = (ys[1] if lado == 2 else ys[2])
    y += (semi[1] if lado == 2 else -semi[1]) * (1 if modo != "tangente_exterior" else -1) + eps
    if modo == "enterrada":
        y = (ys[0] + ys[1]) / 2 if lado == 2 else (ys[2] + ys[3]) / 2
    return (rng.uniform(-15, 15), y, z), modo, eps


# ---------------------------------------------------------------- oráculo de volumen por puntos
def fraccion_fuera(base, h, puntos=800, semilla=1):
    """Fracción de la herramienta que queda fuera de la base, por puntos al azar (error típico ~2 % de la herramienta).
    Es independiente de las booleanas del kernel: arbitra cuando la unión, el común y el corte no coinciden."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    rng = random.Random(semilla)
    caja_h = geo.caja_envolvente(h)
    sh, sb = geo.solidos(h), geo.solidos(base)
    dentro = fuera = 0
    while dentro < puntos:
        p = gp_Pnt(*(rng.uniform(caja_h[0][i], caja_h[1][i]) for i in range(3)))
        if not any(BRepClass3d_SolidClassifier(s, p, 1e-9).State().name == "TopAbs_IN" for s in sh):
            continue
        dentro += 1
        if not any(BRepClass3d_SolidClassifier(s, p, 1e-9).State().name == "TopAbs_IN" for s in sb):
            fuera += 1
    return fuera / dentro


# ---------------------------------------------------------------- un caso
def generar(semilla, indice):
    rng = random.Random(f"{semilla}-{indice}")
    base_nombre = rng.choice(list(BASES))
    base, info = BASES[base_nombre](rng)
    n = rng.randint(1, 4)
    herr = []
    for _ in range(n):
        tipo = rng.choice(TIPOS)
        tam = rng.choice((1.0, 2.0, 2.5, 4.0, 6.0))
        forma, semi = herramienta(rng, tipo, tam)
        eje = rng.choice(((0, 0, 1), (1, 0, 0), (0, 1, 0)))
        if eje != (0, 0, 1):
            semi = {(1, 0, 0): (semi[2], semi[1], semi[0]), (0, 1, 0): (semi[0], semi[2], semi[1])}[eje]
        pos, modo, eps = ubicar(rng, info, semi, base_nombre)
        herr.append((tipo, tam, eje, pos, modo, eps, poner(forma, eje, pos)))
    return base_nombre, base, herr


def medir(base, h, ligero=False):
    """Unión base ∪ h y sus chequeos. Devuelve (resultado, lista de fallos). `ligero`: solo lo barato (válida, sin
    aristas nuevas, volumen dentro de lo posible, no vacía); sin las cuentas con común y corte ni el conteo por puntos."""
    fallos = []
    if not (geo.es_valida(base) and geo.es_valida(h)):
        return base, ["entrada_invalida"]
    vb, vh = geo.volumen_exacto(base), geo.volumen_exacto(h)
    u = geo.booleano(base, h, "unir")
    if geo.esta_vacia(u):
        return u, ["G:vacia"]
    vu = geo.volumen_exacto(u)
    if ligero:
        tol_r = 1e-6 * (vb + vh) + 1e-3 * min(vb, vh)
        if not geo.es_valida(u):
            fallos.append("G:invalida")
        if vu < max(vb, vh) - tol_r or vu > vb + vh + tol_r:
            fallos.append(f"G:rango(vu={vu:.9g} vb={vb:.9g} vh={vh:.9g})")
        antes, ahora = rv.revisar(base, autointersecciones=False), rv.revisar(u, autointersecciones=False)
        if ((ahora["aristas_libres"], ahora["aristas_no_manifold"])
                > (antes["aristas_libres"], antes["aristas_no_manifold"])):
            fallos.append("N:no_estanca")
        return u, fallos
    comun = geo.booleano(base, h, "intersecar")
    vc = geo.volumen_exacto(comun) if not geo.esta_vacia(comun) else 0.0
    resto = geo.booleano(h, base, "cortar")
    vr = geo.volumen_exacto(resto) if not geo.esta_vacia(resto) else 0.0
    tol = max(vb, 1.0) * REL
    if not geo.es_valida(u):
        fallos.append("G:invalida")
    inf = rv.revisar(u, autointersecciones=False)
    if inf["aristas_libres"] or inf["aristas_no_manifold"] or not rv.es_estanca(u):
        antes = rv.revisar(base, autointersecciones=False)       # un defecto heredado de un paso anterior no cuenta
        if (inf["aristas_libres"], inf["aristas_no_manifold"]) > (antes["aristas_libres"], antes["aristas_no_manifold"]):
            fallos.append(f"N:no_estanca(libres={inf['aristas_libres']},nm={inf['aristas_no_manifold']})")
    a, b = vb + vh - vc, vb + vr
    tol_r = 1e-6 * (vb + vh) + 1e-3 * min(vb, vh)
    ref = []                                           # conteo por puntos, solo si hace falta arbitrar

    def verdad():
        if not ref:
            ref.append(fraccion_fuera(base, h))
        return vb + vh * ref[0]
    if vu < max(vb, vh) - tol_r or vu > vb + vh + tol_r:
        fallos.append(f"G:rango(vu={vu:.9g} vb={vb:.9g} vh={vh:.9g})")
    elif (abs(vu - a) > tol * 10 and abs(vu - b) > tol * 10) or (vh - vc <= tol and abs(vu - vb) > tol * 10):
        # la unión no coincide con NINGUNA de las otras dos cuentas (o dice que la herramienta está enterrada y la
        # unión cambia el volumen): arbitra el conteo por puntos
        if abs(vu - verdad()) > max(vh, 1.0) * 0.08:
            fallos.append(f"G:volumen(vu={vu:.9g} puntos={verdad():.9g} vb+vh-vc={a:.9g} vb+vr={b:.9g})")
        elif abs(vu - verdad()) > max(vh, 1.0) * 0.01:
            fallos.append(f"L:volumen(vu={vu:.9g} puntos={verdad():.9g})")
    ns = len(geo.solidos(u))
    if ns > len(geo.solidos(base)) and vc > tol and verdad() < vh * 0.999:
        fallos.append(f"G:solidos={ns}")
    return u, fallos


def correr_caso(semilla, indice, ligero=False):
    nombre, base, herr = generar(semilla, indice)
    fallos = []
    try:
        u = base
        for k, (_t, _tam, _e, _p, _m, _ep, h) in enumerate(herr):
            u, f = medir(u, h, ligero)
            if f == ["entrada_invalida"]:
                return nombre, herr, ["@saltado"]
            tipo, _tam, _e, _p, modo, eps, _ = herr[k]
            degenerada = modo != "enterrada" and abs(eps) <= 1e-6
            for x in f:
                if x.startswith("N:") and degenerada:
                    x = "D" + x[1:]        # contacto tangente casi exacto: arista no manifold admisible
                fallos.append(f"paso{k}:{x}")
        if len(herr) > 1 and not fallos and not ligero:
            # orden inverso: mismo volumen final
            w = base
            for *_, h in reversed(herr):
                w = geo.booleano(w, h, "unir")
            vu, vw = geo.volumen_exacto(u), geo.volumen_exacto(w)
            if abs(vu - vw) > max(vu, 1.0) * REL * 10:
                fallos.append(f"G:orden(vu={vu:.9g} vw={vw:.9g})")
            if not (geo.es_valida(w) and rv.es_estanca(w)):
                fallos.append("D:orden_no_estanca")
    except geo.ErrorGeometria as e:
        # rechazo limpio de un resultado imposible: error claro en vez de geometría equivocada (la defensa de B-39)
        fallos.append(f"E:rechazo:{e}" if "imposible" in str(e) else f"G:excepcion:{e}")
    except Exception as e:  # noqa: BLE001
        fallos.append(f"G:excepcion:{type(e).__name__}:{e}")
    return nombre, herr, fallos


def categoria(fallo):
    """G grave (resultado imposible, inválido, excepción) · N aristas nuevas · L volumen algo distinto · D contacto
    tangente casi exacto (aristas no manifold admisibles) · E rechazo limpio con error claro."""
    return fallo.split(":", 2)[1][0] if fallo.startswith("paso") else fallo[0]


def graves(fallos):
    """Los fallos que cuentan: los de categoría G y N."""
    return [f for f in fallos if f != "@saltado" and categoria(f) in ("G", "N")]


def descripcion(nombre, herr):
    pasos = "; ".join(f"{t}(tam={tam},eje={e},pos=({p[0]:.9g},{p[1]:.9g},{p[2]:.9g}),{m},eps={ep:g})"
                      for t, tam, e, p, m, ep, _ in herr)
    return f"base={nombre} :: {pasos}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--casos", type=int, default=300)
    ap.add_argument("--semilla", default="b39")
    ap.add_argument("--desde", type=int, default=0)
    ap.add_argument("--ligero", action="store_true", help="solo los chequeos baratos (los del test de regresión)")
    a = ap.parse_args()
    t0 = time.time()
    malos, saltados, por_cat = [], 0, {}
    for i in range(a.desde, a.desde + a.casos):
        nombre, herr, fallos = correr_caso(a.semilla, i, a.ligero)
        if fallos == ["@saltado"]:
            saltados += 1
        elif fallos:
            cats = {categoria(x) for x in fallos}
            for c in cats:
                por_cat[c] = por_cat.get(c, 0) + 1
            if not cats <= {"D", "E"}:
                malos.append(i)
            else:
                continue
            print(f"FALLO caso {i}: {descripcion(nombre, herr)}\n    -> {fallos}", flush=True)
    print(f"casos={a.casos} fallos={len(malos)} ({100 * len(malos) / a.casos:.2f}%) "
          f"saltados={saltados} categorias={por_cat} semilla={a.semilla} desde={a.desde} t={time.time() - t0:.0f}s indices={malos[:40]}")
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
