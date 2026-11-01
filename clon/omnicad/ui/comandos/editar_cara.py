# -*- coding: utf-8 -*-
"""SÓLIDO › MODIFICAR › Editar cara (Fusion: Edit Face). Sin motor T-Spline: una grilla de control sobre la cara (ver
`nucleo/editar_cara.py`). La grilla se elige en la vista, con el filtro de vértice, arista o cara; la tríada, el manipulador
de escala o las Entradas numéricas mueven lo elegido. Lo que queda en el paso son los desplazamientos de los puntos."""
import math

import numpy as np
from PySide6.QtCore import QSize
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QGridLayout, QToolButton, QWidget

from ...timeline.ops_modificar import OpEditarCara
from ...timeline.parametros import ANGULO, ESCALAR
from .. import manipuladores as mp
from ..comando import Alternar, Botones, Casilla, Comando, Entero, Expresion, Personalizado, Seleccion, exigir, hits, ref1
from ..iconos import icono
from . import registrar

MODOS = {"multi": ("Multi", "mov_libre"), "traslacion": ("Traslación", "mov_trasladar"), "giro": ("Giro", "mov_rotar"),
         "escala": ("Escala", "esc_modo")}
ESPACIOS = {"universal": ("Universal", "ec_universal"), "vista": ("Vista", "ec_vista"), "seleccion": ("Selección", "ec_seleccion"),
            "local": ("Local por entidad", "ec_local")}
FILTROS = {"vertice": ("Vértice", "ec_vertice"), "arista": ("Arista", "ec_arista"), "cara": ("Cara", "ec_cara"), "todo": ("Todo", "ec_todo")}
OPCIONES_SEL = "Opciones de selección"
NUMERICAS = ("dx", "dy", "dz", "rx", "ry", "rz", "escala")
_NUMERICAS_CERO = {"dx": "0 mm", "dy": "0 mm", "dz": "0 mm", "rx": "0 deg", "ry": "0 deg", "rz": "0 deg", "escala": "1"}
AZUL, NARANJA, GRIS = (0.15, 0.45, 0.85), (0.95, 0.55, 0.10), (0.6, 0.6, 0.6)


# ---------------------------------------------------------------- selección en la grilla (conjuntos de (i, j))
def _vecinos(s, nu, nv):
    return {(i + a, j + b) for i, j in s for a in (-1, 0, 1) for b in (-1, 0, 1) if 0 <= i + a < nu and 0 <= j + b < nv}


def aumentar(s, nu, nv):
    return _vecinos(s, nu, nv)


def contraer(s, nu, nv):
    return {p for p in s if _vecinos({p}, nu, nv) <= s}


def _a_lo_largo(s):
    """¿La selección corre a lo largo de una fila (mismo j)? Si no, de una columna."""
    return len({j for _i, j in s}) <= len({i for i, _j in s})


def contorno(s, nu, nv):
    """Lazo: toda la fila (o la columna) de lo elegido."""
    if not s:
        return set()
    return {(i, j) for _i, j in s for i in range(nu)} if _a_lo_largo(s) else {(i, j) for i, _j in s for j in range(nv)}


def contorno_mas(s, nu, nv):
    fila = _a_lo_largo(s)
    return s | {(max(i - 1, 0), j) if fila else (i, max(j - 1, 0)) for i, j in s} | {(min(i + 1, nu - 1), j) if fila else (i, min(j + 1, nv - 1))
                                                                                  for i, j in s}


def contorno_menos(s, nu, nv):
    if not s:
        return s
    fila = _a_lo_largo(s)
    eje = [p[0 if fila else 1] for p in s]
    return {p for p in s if min(eje) < p[0 if fila else 1] < max(eje)} or s


def anilla(s, nu, nv):
    """Anilla: lo transversal a un lazo."""
    if not s:
        return set()
    return {(i, j) for i, _j in s for j in range(nv)} if _a_lo_largo(s) else {(i, j) for _i, j in s for i in range(nu)}


def anilla_mas(s, nu, nv):
    fila = _a_lo_largo(s)
    return s | {(i, min(j + 1, nv - 1)) if fila else (min(i + 1, nu - 1), j) for i, j in s} | {
        (i, max(j - 1, 0)) if fila else (max(i - 1, 0), j) for i, j in s}


def anilla_menos(s, nu, nv):
    if not s:
        return s
    fila = _a_lo_largo(s)
    eje = [p[1 if fila else 0] for p in s]
    return {p for p in s if min(eje) < p[1 if fila else 0] < max(eje)} or s


def invertir(s, nu, nv):
    return {(i, j) for i in range(nu) for j in range(nv)} - s


def rango(s, nu, nv):
    """Todo lo que queda entre lo elegido."""
    if not s:
        return s
    a, b = zip(*s, strict=True)
    return {(i, j) for i in range(min(a), max(a) + 1) for j in range(min(b), max(b) + 1)}


ACCIONES_SEL = {"aumentar": aumentar, "contraer": contraer, "contorno": contorno, "contorno_mas": contorno_mas,
                "contorno_menos": contorno_menos, "anilla": anilla, "anilla_mas": anilla_mas, "anilla_menos": anilla_menos,
                "invertir": invertir, "rango": rango}
FILAS_SEL = (("Aumentar/disminuir", (("aumentar", "sel_aumentar", "Aumentar la selección", "Shift+Up"),
                                     ("contraer", "sel_contraer", "Selección de contracción", "Shift+Down"))),
             ("Aumento/disminución del contorno", (("contorno", "sel_contorno", "Selección de contorno", "Alt+P"),
                                                   ("contorno_mas", "sel_mas_contorno", "Aumentar selección de contorno", "Alt+O"),
                                                   ("contorno_menos", "sel_menos_contorno", "Selección de disminución de contorno", "Alt+I"))),
             ("Aumento/disminución de la anilla", (("anilla", "sel_anilla", "Selección de anilla", "Alt+L"),
                                                   ("anilla_mas", "sel_mas_anilla", "Selección de aumento de anilla", "Alt+K"),
                                                   ("anilla_menos", "sel_menos_anilla", "Selección de disminución de anilla", "Alt+J"))),
             ("Invertir selección", (("invertir", "sel_invertir", "Invertir selección", "Alt+N"),)),
             ("Selección de rango", (("rango", "sel_rango", "Selección de rango", "Alt+M"),)))
ATAJOS_OPCION = {"Alt+W": ("modo", "traslacion"), "Alt+E": ("modo", "giro"), "Alt+R": ("modo", "escala"),
                 "Alt+Z": ("espacio", "universal"), "Alt+X": ("espacio", "vista"), "Alt+C": ("espacio", "seleccion"),
                 "Alt+V": ("espacio", "local"), "Alt+A": ("filtro", "vertice"), "Alt+S": ("filtro", "arista"),
                 "Alt+D": ("filtro", "cara"), "Alt+F": ("filtro", "todo")}


def _ec():
    from ...nucleo import editar_cara
    return editar_cara


def _clave(p):
    return f"{p[0]},{p[1]}"


def _rotacion(rx, ry, rz):
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    return (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))


class GrillaCara(mp.Manipulador):
    """La grilla en la vista: puntos, líneas y lo elegido; un clic elige según el filtro (Mayús suma)."""
    ident = "grilla_cara"

    def __init__(self, comando, panel, puntos, fijos):
        self.comando, self.panel, self.puntos, self.fijos = comando, panel, puntos, fijos

    def _segmentos(self):
        nu, nv = self.puntos.shape[:2]
        return [((i, j), (i + 1, j)) for i in range(nu - 1) for j in range(nv)] + [((i, j), (i, j + 1)) for i in range(nu) for j in range(nv - 1)]

    def dibujar(self, g, activo):
        k = g.escala(self.puntos.reshape(-1, 3).mean(0))
        prims = [("lineas", np.array([self.puntos[a] for s in self._segmentos() for a in s]), AZUL, 1.2)]
        sel = self.comando.sel
        for i in range(self.puntos.shape[0]):
            for j in range(self.puntos.shape[1]):
                color = NARANJA if (i, j) in sel else GRIS if self.fijos[i, j] else AZUL
                prims += mp._disco(g.visor, self.puntos[i, j], (5.5 if (i, j) == activo else 4.0) * k, color)
        return prims + self.comando.dibujo_peines(self.panel)

    def tocar(self, g, q):
        filtro = self.panel.valores.get("filtro", "todo")
        nu, nv = self.puntos.shape[:2]
        s, ok = g.pantalla(self.puntos.reshape(-1, 3))
        s = s.reshape(nu, nv, 2)
        ok = ok.reshape(nu, nv)
        mejor = (math.inf, None)
        if filtro in ("vertice", "todo"):
            d = np.linalg.norm(s - q, axis=2)
            d[~ok | self.fijos] = np.inf
            i, j = np.unravel_index(np.argmin(d), d.shape)
            if d[i, j] < mp.TOL_PX:
                return float(d[i, j]), (int(i), int(j))
        if filtro in ("arista", "todo"):
            for a, b in self._segmentos():
                if ok[a] and ok[b]:
                    d = mp._dist_segmentos_px(q, np.array([s[a], s[b]]), np.array([True, True]))
                    if d < mejor[0]:
                        mejor = (d, (a, b))
            if mejor[0] < mp.TOL_PX:
                return mejor
        if filtro in ("cara", "todo"):
            for i in range(nu - 1):
                for j in range(nv - 1):
                    if np.linalg.norm(s[i:i + 2, j:j + 2].mean((0, 1)) - q) < mejor[0]:
                        mejor = (float(np.linalg.norm(s[i:i + 2, j:j + 2].mean((0, 1)) - q)), ((i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1)))
        return mejor

    def empezar(self, g, pos, sub):
        puntos = {sub} if isinstance(sub[0], int) else set(sub)
        suma = bool(QApplication.keyboardModifiers() & mp.Qt.ShiftModifier)
        self.comando.elegir(self.panel, (self.comando.sel | puntos) if suma else puntos)
        return {}

    def mover(self, g, estado, pos):
        return {}


class EditarCara(Comando):
    CLAVE, TITULO, ICONO = "editar_cara", "Editar cara", "editar_cara"
    AYUDA = ("Deforma una cara con una grilla de control: elegí puntos, aristas o cuadros de la grilla y movelos. El contorno "
             "de la cara queda fijo. Dividir caras suma puntos.")
    CLASE_OP = OpEditarCara
    PLEGADAS = (OPCIONES_SEL, "Entradas numéricas")
    ANCHO_PANEL = "normal"

    def __init__(self):
        super().__init__()
        self.sel, self._base, self._memo, self._panel = set(), {}, (None, None), None

    def campos(self, ctx):
        kw = {"seccion": "Entradas numéricas"}
        return [Seleccion("cara", "Cara", {"cara"}),
                Botones("modo", "Modo de transformación", MODOS), Botones("espacio", "Espacio de coordenadas", ESPACIOS),
                Botones("filtro", "Filtro de selección", FILTROS, defecto="todo"),
                Alternar("comprobar", "Comprobación de vista preliminar", "comprobacion"),
                *[Personalizado(f"sel_{i}", titulo, lambda panel, b=botones: self._fila_botones(panel, b), seccion=OPCIONES_SEL)
                  for i, (titulo, botones) in enumerate(FILAS_SEL)],
                Entero("n_u", "Factor de longitud", 1, 1, 32, seccion="Dividir caras"),
                Entero("n_v", "Factor de anchura", 1, 1, 32, seccion="Dividir caras"),
                Casilla("peine_u", "Longitud", seccion="Curvatura en peines"), Casilla("peine_v", "Anchura", seccion="Curvatura en peines"),
                Casilla("sim_u", "Longitud", seccion="Simetría"), Casilla("sim_v", "Anchura", seccion="Simetría"),
                Expresion("dx", "X", "0 mm", **kw), Expresion("dy", "Y", "0 mm", **kw), Expresion("dz", "Z", "0 mm", **kw),
                Expresion("rx", "Giro X", "0 deg", ANGULO, **kw), Expresion("ry", "Giro Y", "0 deg", ANGULO, **kw),
                Expresion("rz", "Giro Z", "0 deg", ANGULO, **kw), Expresion("escala", "Escala", "1", ESCALAR, **kw)]

    def _fila_botones(self, panel, botones):
        w = QWidget()
        fila = QGridLayout(w)
        fila.setContentsMargins(0, 0, 0, 0)
        w.botones = {}
        for col, (accion, ico, texto, atajo) in enumerate(botones):
            b = w.botones[accion] = QToolButton(objectName="opcion_cmd", toolTip=f"{texto}\n{atajo.replace('Shift+Up', 'Mayús+Arriba').replace('Shift+Down', 'Mayús+Abajo')}",
                                                accessibleName=texto)
            b.setIcon(icono(ico))
            b.setIconSize(QSize(20, 20))
            b.clicked.connect(lambda _=False, a=accion: self.accion_sel(panel, a))
            fila.addWidget(b, 0, col)
        fila.setColumnStretch(len(botones), 1)
        return w

    def preparar_panel(self, panel):
        self._panel = panel
        for _titulo, botones in FILAS_SEL:
            for accion, _ico, _texto, atajo in botones:
                QShortcut(QKeySequence(atajo), panel, activated=lambda a=accion: self.accion_sel(panel, a))
        for atajo, (clave, valor) in ATAJOS_OPCION.items():
            QShortcut(QKeySequence(atajo), panel, activated=lambda c=clave, x=valor: panel.set_valor(c, x))

    # ------------------------------------------------------------ la grilla
    def grilla(self, v, ctx):
        """{"puntos", "fijos"} de la cara elegida y sus factores (la lectura se recuerda mientras no cambien)."""
        cara = (v.get("cara") or [None])[0]
        if cara is None:
            return None
        clave = repr((cara["ref"], v.get("n_u"), v.get("n_v")))
        if self._memo[0] != clave:
            e = mp.entidad(cara, ctx.estado)
            self._memo = clave, _ec().grilla_cara(e.forma, int(v.get("n_u") or 1), int(v.get("n_v") or 1))
        return self._memo[1]

    def _posiciones(self, v, grilla, despl=None):
        despl = v.get("despl", {}) if despl is None else despl
        p = grilla["puntos"].copy()
        for k, d in despl.items():
            i, j = map(int, k.split(","))
            if i < p.shape[0] and j < p.shape[1]:
                p[i, j] += d
        return p

    def _marco(self, panel, puntos, grilla):
        """Ejes de la transformación según el Espacio de coordenadas (filas: X, Y, Z)."""
        espacio = panel.valores.get("espacio")
        if espacio == "vista":
            return np.asarray(panel.visor.R, float).copy()
        if espacio == "universal" or not self.sel:
            return np.identity(3)
        nu, nv = puntos.shape[:2]
        normales = [np.cross(puntos[min(i + 1, nu - 1), j] - puntos[max(i - 1, 0), j], puntos[i, min(j + 1, nv - 1)] - puntos[i, max(j - 1, 0)])
                    for i, j in self.sel]
        n = grilla["signo"] * np.mean(normales, axis=0)
        n = n / max(np.linalg.norm(n), 1e-12)
        a, b = mp.perpendiculares(n)
        return np.array([a, b, n])

    def elegir(self, panel, puntos):
        grilla = self.grilla(panel.valores, panel.ctx)
        self.sel = {p for p in puntos if not grilla["fijos"][p]}
        self._base = dict(panel.valores.get("despl", {}))
        panel.set_valores(dict(_NUMERICAS_CERO))
        if panel.manipuladores is not None:
            panel.manipuladores.actualizar()

    def accion_sel(self, panel, accion):
        grilla = self.grilla(panel.valores, panel.ctx)
        if grilla is not None:
            self.elegir(panel, ACCIONES_SEL[accion](self.sel, *grilla["fijos"].shape))

    def _simetricos(self, v, grilla, p):
        nu, nv = grilla["fijos"].shape
        salida = [(p, (1, 1))]
        if v.get("sim_u"):
            salida.append(((nu - 1 - p[0], p[1]), (-1, 1)))
        if v.get("sim_v"):
            salida += [((q[0], nv - 1 - q[1]), (s[0], -1)) for q, s in list(salida)]
        return salida

    def _aplicar(self, panel):
        """Las Entradas numéricas (que escriben la tríada y el teclado) mueven lo elegido desde donde estaba."""
        v, ctx = panel.valores, panel.ctx
        grilla = self.grilla(v, ctx)
        if grilla is None or not self.sel:
            return
        puntos = self._posiciones(v, grilla, self._base)
        centro = np.mean([puntos[p] for p in self.sel], axis=0)
        t = np.array([ctx.evaluar(v[k]) for k in ("dx", "dy", "dz")], float)
        giro = _rotacion(*(math.radians(ctx.evaluar(v[k], ANGULO)) for k in ("rx", "ry", "rz")))
        escala = ctx.evaluar(v["escala"], ESCALAR)
        marco = self._marco(panel, puntos, grilla)
        local = v.get("espacio") == "local"
        ejes_u, ejes_v = puntos[-1, 0] - puntos[0, 0], puntos[0, -1] - puntos[0, 0]
        ejes_u, ejes_v = ejes_u / max(np.linalg.norm(ejes_u), 1e-12), ejes_v / max(np.linalg.norm(ejes_v), 1e-12)
        despl = dict(self._base)
        for p in self.sel:
            F = self._marco_punto(puntos, p, grilla["signo"]) if local else marco
            pivote = puntos[p] if local else centro
            nuevo = pivote + F.T @ (escala * giro @ (F @ (puntos[p] - pivote)) + t)
            d = nuevo - grilla["puntos"][p]
            for q, (su, sv) in self._simetricos(v, grilla, p):
                if grilla["fijos"][q]:
                    continue
                e = d - (1 - su) * (d @ ejes_u) * ejes_u - (1 - sv) * (d @ ejes_v) * ejes_v
                despl[_clave(q)] = [float(x) for x in e]
        v["despl"] = {k: x for k, x in despl.items() if any(abs(y) > 1e-9 for y in x)}

    @staticmethod
    def _marco_punto(puntos, p, signo):
        nu, nv = puntos.shape[:2]
        i, j = p
        n = signo * np.cross(puntos[min(i + 1, nu - 1), j] - puntos[max(i - 1, 0), j], puntos[i, min(j + 1, nv - 1)] - puntos[i, max(j - 1, 0)])
        n = n / max(np.linalg.norm(n), 1e-12)
        return np.array([*mp.perpendiculares(n), n])

    def al_cambiar(self, panel, clave):
        v = panel.valores
        if clave in ("cara", "n_u", "n_v"):
            if clave == "cara":
                v["despl"] = {}
            elif v.get("despl"):
                v["despl"] = self._remuestrear(v, clave)
            self.sel, self._base = set(), dict(v.get("despl") or {})
        elif clave in NUMERICAS:
            try:
                self._aplicar(panel)
            except Exception:  # noqa: BLE001 — una expresión a medio escribir: el panel la marca en rojo
                pass

    def _remuestrear(self, v, clave):
        """Al cambiar los factores la forma casi no cambia: el campo viejo se lee en los puntos nuevos."""
        nuevo, otro = int(v[clave]), "n_v" if clave == "n_u" else "n_u"
        viejos = {tuple(map(int, k.split(","))): d for k, d in v["despl"].items()}
        anterior = (int(self._memo[1]["puntos"].shape[0 if clave == "n_u" else 1]) - 3) if self._memo[1] is not None else nuevo
        n0 = (anterior, int(v[otro])) if clave == "n_u" else (int(v[otro]), anterior)
        n1 = (nuevo, int(v[otro])) if clave == "n_u" else (int(v[otro]), nuevo)
        if n0 == n1:                     # `set_valor` avisa dos veces
            return v["despl"]
        fijos = self.grilla(v, self._panel.ctx)["fijos"]
        return {_clave(k): d for k, d in _ec().remuestrear(viejos, n0, n1).items() if not fijos[k]}

    # ------------------------------------------------------------ operación
    def construir(self, v, ctx):
        exigir(v, "cara", "Seleccioná la cara.")
        return self.crear_op(OpEditarCara, v, ctx, cara=ref1(v, "cara"), n_u=int(v["n_u"]), n_v=int(v["n_v"]), desplazamientos=dict(v.get("despl") or {}))

    def desde_op(self, op, ctx):
        self._base = dict(op.p["desplazamientos"])
        return dict(op.p, cara=hits([op.p["cara"]], ctx.estado), despl=dict(op.p["desplazamientos"]))

    def dibujo_peines(self, panel):
        v = panel.valores
        if not (v.get("peine_u") or v.get("peine_v")):
            return []
        from ...nucleo import analisis as an
        e = mp.entidad(v["cara"][0], panel.ctx.estado)
        despl = {tuple(map(int, k.split(","))): d for k, d in v.get("despl", {}).items()}
        curvas = _ec().curvas_grilla(e.forma, int(v["n_u"]), int(v["n_v"]), despl)
        lista = (curvas["u"] if v.get("peine_u") else []) + (curvas["v"] if v.get("peine_v") else [])
        return [("lineas", np.asarray(an.peines_isocurva(lista, densidad=40, escala=5.0)["puas"], float).reshape(-1, 3), (0.55, 0.30, 0.85), 1.0)]

    def manipuladores(self, ctx, v):
        grilla = self.grilla(v, ctx) if v.get("cara") else None
        if grilla is None or v.get("comprobar"):
            return []
        puntos = self._posiciones(v, grilla)
        manips = [GrillaCara(self, self._panel, puntos, grilla["fijos"])]
        if self.sel:
            centro = np.mean([puntos[p] for p in self.sel], axis=0)
            ejes = self._marco(self._panel, puntos, grilla)
            modo = v.get("modo")
            if modo == "escala":
                manips.append(mp.Flecha("escala", centro, ejes[2], factor=0.02, minimo=0.01))
            else:
                manips.append(mp.Triada(centro, ejes=ejes, giros=None if modo == "traslacion" else ("rx", "ry", "rz"),
                                        solo_giros=modo == "giro", esfera=False))
        return manips


registrar(EditarCara)
