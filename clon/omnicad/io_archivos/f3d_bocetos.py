# -*- coding: utf-8 -*-
"""
Bocetos de un .f3d: Fusion guarda en `Breps.BlobParts/BREP.*.smb` (sin «h») los PERFILES de sus bocetos — las regiones
cerradas que usan Extruir, Revolución y los demás — como cuerpos de hoja de ShapeManager (el mismo formato SAB que los
`.smbh`), mezclados con cuerpos auxiliares de las herramientas (cilindros de un empalme, tapas de una extrusión…).
Este módulo saca de ahí los bocetos: cada cuerpo hecho solo de caras planas en un mismo plano es un boceto; las aristas
únicas de sus caras (líneas, círculos, arcos, elipses y splines) pasan a un `Boceto` de OmniCAD en el plano de esas caras.

Qué NO sale de ahí (queda en el flujo de diseño propietario): los trazos abiertos o que no cierran región, la geometría
de construcción, las cotas, las restricciones y el nombre del boceto. Un boceto con la región partida por otro trazo
entra con sus trazos partidos en los cruces.

Unidades: Fusion guarda centímetros; el boceto sale en milímetros. Sin Qt.
"""
import math

import numpy as np

from ..nucleo import acis_occ
from ..restricciones import boceto as rb
from . import sab

TOL_PLANO_MM = 1e-3            # dos caras son coplanares si sus planos coinciden a esta distancia (mm)
TOL_PUNTO_MM = 1e-4            # dos extremos a menos de esto son el mismo punto del boceto
CURVAS_MAX = 20000             # tope de trazos por boceto: un archivo hostil o enorme no llena la memoria
CARAS_MAX = 200000             # caras de un bloque: pasado esto se avisa y no se importan sus bocetos
BOCETOS_MAX = 150              # bocetos que se importan de un archivo (cada uno es un paso del historial)
CURVAS_TOTAL_MAX = 30000       # trazos de todos los bocetos de un archivo
_CM_A_MM = 10.0
_VUELTA = 2 * math.pi


def leer_bocetos(datos_smb, nombre="Fusion"):
    """Bocetos de un bloque `.smb` ya descomprimido: devuelve (bocetos, avisos). `bocetos` es una lista de dicts
    {"marco": {"origen", "normal", "u"} (mm, en las coordenadas del componente), "boceto": Boceto, "caras": n, "curvas": n}."""
    try:
        archivo = sab.leer(datos_smb)
    except sab.ErrorSAB as e:
        return [], [f"Los bocetos de {nombre} no se pudieron leer: {e}"]
    if len(archivo.de_tipo("face")) > CARAS_MAX:
        return [], [f"Los bocetos de {nombre} son demasiado grandes ({len(archivo.de_tipo('face'))} caras): no se importan."]
    conv = acis_occ._Convertidor(archivo)
    bocetos = []
    for cuerpo in archivo.de_tipo("body"):
        r = _boceto_del_cuerpo(conv, cuerpo)
        if r is not None and r["curvas"]:
            bocetos.append(r)
    return bocetos, []


# ---------------------------------------------------------------- un cuerpo → un boceto
def _boceto_del_cuerpo(conv, cuerpo):
    """El boceto de un cuerpo de hoja plano, o None si el cuerpo no es un perfil (tiene superficies curvas o caras en
    planos distintos)."""
    M, t = _matriz(conv, conv._ent(conv._c(cuerpo, 5)))
    caras = [f for lump in conv._lista(conv._c(cuerpo, 3), 3) for sh in conv._lista(conv._c(lump, 4), 3)
             for f in conv._lista(conv._c(sh, 5), 3)]
    if not caras:
        return None
    marco = None
    for f in caras:
        s = conv._ent(conv._c(f, 7))
        if s is None or s.tipo != "plane-surface":
            return None
        origen = (np.array(conv._c(s, 3), float) @ M.T + t) * _CM_A_MM
        normal = M @ np.array(conv._c(s, 4), float)
        u = M @ np.array(conv._c(s, 5), float)
        normal /= np.linalg.norm(normal) or 1.0
        if marco is None:
            marco = (origen, normal, u)
        elif abs(float(marco[1] @ normal)) < 1 - 1e-9 or abs(float((origen - marco[0]) @ marco[1])) > TOL_PLANO_MM:
            return None
    plano = _marco_boceto(*marco)
    b = _Constructor(plano, M, t)
    vistas = set()
    for f in caras:
        for loop in conv._lista(conv._c(f, 4), 3):
            for coedge in conv._ciclo(loop):
                arista = conv._ent(conv._c(coedge, 6))
                if arista is None or arista.indice in vistas:
                    continue
                vistas.add(arista.indice)
                if len(b.boceto.curvas) >= CURVAS_MAX:
                    break
                b.arista(conv, arista)
    return {"marco": {k: [float(x) for x in v] for k, v in plano.items()}, "boceto": b.boceto, "caras": len(caras),
            "curvas": len(b.boceto.curvas)}


def _matriz(conv, ent):
    """(M, t) del `transform` de un cuerpo: p' = M·p + t (en centímetros), con M de columnas a, b, c por la escala."""
    if ent is None or ent.tipo != "transform":
        return np.eye(3), np.zeros(3)
    filas = [v for v in ent.campos if isinstance(v, tuple)]
    escala = next((v for v in ent.campos if isinstance(v, float)), 1.0)
    if len(filas) < 4:
        return np.eye(3), np.zeros(3)
    return np.array(filas[:3], float).T * escala, np.array(filas[3], float)


def _marco_boceto(origen, normal, u):
    """Marco {"origen", "normal", "u"} (mm) del boceto, lo más parecido a como Fusion ubica sus planos: los de origen
    con sus ejes de siempre (XY, XZ, YZ); los demás, con el origen en el punto del plano más cercano al del mundo."""
    estandar = {"XY": ((0, 0, 1), (1, 0, 0)), "XZ": ((0, -1, 0), (1, 0, 0)), "YZ": ((1, 0, 0), (0, 1, 0))}
    for n, uu in estandar.values():
        n, uu = np.array(n, float), np.array(uu, float)
        if abs(float(normal @ n)) > 1 - 1e-9:
            return {"origen": n * float(origen @ n), "normal": n, "u": uu}
    n = normal if normal[np.argmax(np.abs(normal))] > 0 else -normal
    u = u - n * float(u @ n)
    u = u / (np.linalg.norm(u) or 1.0)
    return {"origen": n * float(origen @ n), "normal": n, "u": u}


class _Constructor:
    """Arma el Boceto con las aristas de un cuerpo, en las coordenadas del marco `plano`."""

    def __init__(self, plano, M, t):
        self.boceto = rb.Boceto()
        self.o, self.u, self.n = plano["origen"], plano["u"], plano["normal"]
        self.v = np.cross(self.n, self.u)
        self.M, self.t = M, t
        self.celdas = {}

    # --- puntos
    def a_2d(self, p3):
        """Punto de ACIS (cm, coordenadas del cuerpo) → (u, v) del boceto en mm."""
        q = (self.M @ np.asarray(p3, float) + self.t) * _CM_A_MM - self.o
        return float(q @ self.u), float(q @ self.v)

    def punto(self, xy):
        """Id del punto del boceto en `xy`; los extremos que coinciden dentro de la tolerancia son el mismo punto."""
        cx, cy = round(xy[0] / TOL_PUNTO_MM), round(xy[1] / TOL_PUNTO_MM)
        for i in (cx - 1, cx, cx + 1):
            for j in (cy - 1, cy, cy + 1):
                pid = self.celdas.get((i, j))
                if pid is not None and math.dist(self.boceto.coords(pid), xy) <= TOL_PUNTO_MM:
                    return pid
        pid = self.boceto.agregar_punto(*xy)
        self.celdas[(cx, cy)] = pid
        return pid

    # --- aristas
    def arista(self, conv, ent):
        curva = conv._ent(conv._c(ent, 8))
        if curva is None:
            return
        try:
            if curva.tipo == "straight-curve":
                self._linea(conv, ent)
            elif curva.tipo == "ellipse-curve":
                self._elipse(conv, ent, curva)
            elif curva.tipo == "intcurve-curve":
                self._spline(conv, ent, curva)
        except (rb.ErrorBoceto, acis_occ.ErrorACIS, ValueError, IndexError, TypeError, ZeroDivisionError):
            pass                                                   # una arista rara no tumba el resto del boceto

    def _extremos(self, conv, ent):
        return [self.a_2d(conv._c(conv._ent(conv._c(conv._ent(conv._c(ent, k)), 5)), 3)) for k in (3, 5)]

    def _rango(self, conv, ent):
        """Rango del parámetro de la curva que cubre la arista (el de la arista cambia de signo si va al revés)."""
        s0, s1 = conv._c(ent, 4), conv._c(ent, 6)
        return (-s1, -s0) if conv._c(ent, 9) else (s0, s1)

    def _linea(self, conv, ent):
        a, b = self._extremos(conv, ent)
        ia, ib = self.punto(a), self.punto(b)
        if ia != ib:
            self.boceto.agregar_linea(ia, ib)

    def _elipse(self, conv, ent, curva):
        centro, normal, mayor, razon = (np.array(conv._c(curva, k), float) if k < 6 else conv._c(curva, k)
                                        for k in (3, 4, 5, 6))
        a = float(np.linalg.norm(mayor))
        e1 = mayor / a
        e2 = np.cross(normal / np.linalg.norm(normal), e1)

        def en(t):
            return self.a_2d(centro + a * math.cos(t) * e1 + a * razon * math.sin(t) * e2)
        t0, t1 = self._rango(conv, ent)
        completa = abs((t1 - t0) - _VUELTA) < 1e-6
        if abs(razon - 1.0) < 1e-9:                               # círculo o arco
            if completa:
                self.boceto.agregar_circulo(self.punto(self.a_2d(centro)), a * _CM_A_MM)
            else:
                self.boceto.agregar_arco_3_puntos(self.punto(en(t0)), en((t0 + t1) / 2), self.punto(en(t1)))
            return
        # elipse o arco de elipse: spline de ajuste por puntos (la elipse exacta no se reconstruye desde un arco)
        pasos = 24 if completa else max(6, int(24 * (t1 - t0) / _VUELTA))
        pts = [self.punto(en(t0 + (t1 - t0) * k / pasos)) for k in range(pasos + 1 - (1 if completa else 0))]
        self.boceto.agregar_spline(pts, modo="ajuste", grado=3, cerrada=completa)

    def _spline(self, conv, ent, curva):
        sub = conv.sab.resolver(acis_occ._primer_subtipo(curva.campos))
        bs3 = None if sub is None else acis_occ._buscar_bs3(sub, superficie=False)
        if bs3 is None:
            raise acis_occ.ErrorACIS("intcurve sin aproximación")
        nudos, mults, puntos = bs3["nudos"], bs3["mults"], bs3["puntos"]
        if conv._c(curva, 3):                                      # curva recorrida al revés: t pasa a -t
            nudos, mults, puntos = [-k for k in reversed(nudos)], list(reversed(mults)), list(reversed(puntos))
        grado = bs3["grado"]
        mults = acis_occ._mults_occ(mults, grado, len(puntos))     # ACIS guarda los extremos con grado; el vector pide grado + 1
        completo = [k for k, m in zip(nudos, mults, strict=True) for _ in range(m)]
        polos = [self.a_2d(p[:3]) for p in puntos]
        pesos = [p[3] for p in puntos] if bs3["racional"] else None
        ta, tb = self._rango(conv, ent)
        if ta > completo[grado] + 1e-9 or tb < completo[-grado - 1] - 1e-9:
            polos, completo, pesos = rb.tramo_bspline(polos, completo, grado, pesos, ta, tb)
        ids = [self.punto(p) for p in polos]
        if len(set(ids)) < 2:
            return
        self.boceto.agregar_spline(ids, modo="control", grado=grado, pesos=pesos, nudos=completo)


def sin_repetidos(bocetos):
    """Quita los perfiles que son el mismo dibujo: el que Fusion guarda con el boceto y el de sus copias (las tapas de una
    extrusión caen en otro plano paralelo con la misma forma). De cada grupo queda el más cercano al origen (los bocetos
    se dibujan casi siempre en un plano de origen y la tapa queda a la distancia de la extrusión)."""
    grupos = {}
    for b in bocetos:
        clave = (tuple(np.round(np.abs(b["marco"]["normal"]), 2)), _firma(b["boceto"]))
        lejos = abs(float(np.dot(b["marco"]["origen"], b["marco"]["normal"])))
        if clave not in grupos or lejos < grupos[clave][0] - 1e-9:
            grupos[clave] = (lejos, b)
    elegidos = {id(b) for _, b in grupos.values()}
    return [b for b in bocetos if id(b) in elegidos]


def _firma(boceto):
    f = set()
    for c in boceto.curvas.values():
        pts = [boceto.coords(p) for p in (c.puntos()[:1] if c.tipo == "circulo" else c.puntos()[:2])]
        f.add((c.tipo, *sorted((round(x, 2), round(y, 2)) for x, y in pts)))
    return frozenset(f)


def limitar(bocetos, avisos, nombre="Fusion"):
    """Los primeros bocetos hasta BOCETOS_MAX y CURVAS_TOTAL_MAX trazos; avisa lo que queda afuera."""
    salida, curvas = [], 0
    for b in bocetos:
        if len(salida) >= BOCETOS_MAX or curvas + b["curvas"] > CURVAS_TOTAL_MAX:
            break
        salida.append(b)
        curvas += b["curvas"]
    if len(salida) < len(bocetos):
        avisos.append(f"{nombre} trae {len(bocetos)} bocetos: se importan los primeros {len(salida)} (tope de "
                      f"{BOCETOS_MAX} bocetos y {CURVAS_TOTAL_MAX} trazos por archivo).")
    return salida
