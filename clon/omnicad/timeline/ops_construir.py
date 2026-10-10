# -*- coding: utf-8 -*-
"""
CONSTRUIR de Fusion [SLD-CONSTRUCT-TOOLS]: planos, ejes, puntos y sistemas de coordenadas de usuario.

Los planos son `OpPlano` (en `operaciones.py`, con `tipo`); acá están el cálculo de cada tipo de plano
y las operaciones de ejes, puntos y SCU. Cada uno guarda referencias a lo elegido, así un plano medio
entre dos caras sigue a las caras cuando cambia una cota.
"""
import numpy as np

from ..nucleo import geometria as geo
from . import entidades as ent
from .operaciones import ANGULO, ErrorOperacion, Operacion, OpPlano, _resolver, registrar_operacion

TIPOS_PLANO = {"desfase": "Plano de desfase", "angulo": "Plano en el ángulo", "tangente": "Plano tangente",
               "medio": "Plano medio", "dos_aristas": "Plano a través de dos aristas",
               "tres_puntos": "Plano a través de tres puntos", "perpendicular": "Plano perpendicular",
               "ruta": "Plano en ruta"}
OpPlano.OPCIONES = {"tipo": TIPOS_PLANO}      # OpPlano vive en operaciones.py; sus tipos, acá
TIPOS_EJE = {"cilindro": "Eje a través de cilindro/cono/toroide", "perpendicular_cara": "Eje perpendicular a la cara",
             "dos_planos": "Eje a través de dos planos", "dos_puntos": "Eje a través de dos puntos",
             "arista": "Eje a través de arista"}
TIPOS_PUNTO = {"vertice": "Punto en vértice", "dos_aristas": "Punto a través de dos aristas",
               "tres_planos": "Punto a través de tres planos", "centro": "Punto en el centro de círculo/esfera/toroide",
               "arista_plano": "Punto en arista y plano", "ruta": "Punto a lo largo de la ruta"}


def _cs():
    from ..nucleo import construccion
    return construccion


def _eje(e):
    p, d = ent.como_eje(e)
    return _cs().Eje(np.asarray(p, float), np.asarray(d, float))


def _forma_o_plano(e):
    return e.forma if e.forma is not None else ent.como_plano(e)


def _plano_por_eje(e):
    """Plano de referencia que contiene un eje (el ángulo 0 del «Plano en el ángulo»): el plano del
    boceto si es una línea de boceto, la cara plana vecina si viene de una cara, o el plano que contiene
    al eje y es lo más vertical posible."""
    if e.tipo == "curva_boceto" and e.plano is not None:
        return e.plano
    p, d = ent.como_eje(e)
    d = np.asarray(d, float) / (np.linalg.norm(d) or 1.0)
    # Ángulo 0 = el plano horizontal que contiene al eje (normal = Z sin su componente sobre el eje);
    # si el eje es vertical, el plano frontal.
    ref = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    n = ref - d * float(ref @ d)
    return geo.Plano.desde_marco(p, n, d)


def calcular_plano(p, entidades, ctx):
    cs, t, E = _cs(), p.get("tipo", "desfase"), entidades
    faltan = {"desfase": 1, "angulo": 1, "tangente": 1, "medio": 2, "dos_aristas": 2, "tres_puntos": 3,
              "perpendicular": 2, "ruta": 1}[t]
    if len(E) < faltan:
        raise ErrorOperacion("Faltan referencias para el plano.")
    d = ctx.evaluar(p.get("distancia", "0"))
    if t == "desfase":
        return cs.plano_desfase(ent.como_plano(E[0]), d)
    if t == "angulo":
        punto, direccion = ent.como_eje(E[0])
        return cs.plano_en_angulo(_plano_por_eje(E[0]), punto, direccion, ctx.evaluar(p.get("angulo", "0"), ANGULO))
    if t == "tangente":
        ref = ent.como_plano(E[1]) if len(E) > 1 else None
        return cs.plano_tangente(E[0].forma, ctx.evaluar(p.get("angulo", "0"), ANGULO), ref)
    if t == "medio":
        return cs.plano_medio(ent.como_plano(E[0]), ent.como_plano(E[1]))
    if t == "dos_aristas":
        return cs.plano_dos_aristas(_eje(E[0]), _eje(E[1]))
    if t == "tres_puntos":
        return cs.plano_tres_puntos(*(ent.como_punto(e) for e in E[:3]))
    if t == "perpendicular":
        return cs.plano_perpendicular(_forma_o_plano(E[0]), ent.como_punto(E[1]))
    if t == "ruta":
        if E[0].forma is None:
            raise ErrorOperacion("La ruta tiene que ser una arista o una curva de boceto.")
        return cs.plano_en_ruta(E[0].forma, ctx.evaluar(p.get("posicion", "0.5"), "escalar"))
    raise ErrorOperacion(f"Tipo de plano desconocido: {t}")


class OpEje(Operacion):
    """Ejes de construcción de Fusion [SLD-CONSTRUCT-AXIS-*]."""
    TIPO, ETIQUETA, ICONO = "eje", "Eje", "╱"
    PARAMS = {"tipo": "arista", "refs": []}
    OPCIONES = {"tipo": TIPOS_EJE}

    def dependencias(self):
        return ent.dependencias_de(self.p["refs"]) - {self.id}

    def ejecutar(self, estado, ctx):
        cs, t = _cs(), self.p["tipo"]
        E = [_resolver(r, estado) for r in self.p["refs"]]
        faltan = {"cilindro": 1, "perpendicular_cara": 2, "dos_planos": 2, "dos_puntos": 2, "arista": 1}[t]
        if len(E) < faltan:
            raise ErrorOperacion("Faltan referencias para el eje.")
        if t == "cilindro":
            eje = cs.eje_cilindro(E[0].forma)
        elif t == "perpendicular_cara":
            eje = cs.eje_perpendicular_cara(_forma_o_plano(E[0]), ent.como_punto(E[1]))
        elif t == "dos_planos":
            eje = cs.eje_dos_planos(ent.como_plano(E[0]), ent.como_plano(E[1]))
        elif t == "dos_puntos":
            eje = cs.eje_dos_puntos(ent.como_punto(E[0]), ent.como_punto(E[1]))
        else:
            eje = _eje(E[0])
        estado.ejes[self.id] = (np.asarray(eje.punto, float), np.asarray(eje.direccion, float), self.nombre)


class OpPunto(Operacion):
    """Puntos de construcción de Fusion [SLD-CONSTRUCT-POINT-*]."""
    TIPO, ETIQUETA, ICONO = "punto", "Punto", "•"
    PARAMS = {"tipo": "vertice", "refs": [], "posicion": "0.5"}
    EXPRESIONES = ("posicion",)
    OPCIONES = {"tipo": TIPOS_PUNTO}

    def dependencias(self):
        return ent.dependencias_de(self.p["refs"]) - {self.id}

    def ejecutar(self, estado, ctx):
        cs, t = _cs(), self.p["tipo"]
        E = [_resolver(r, estado) for r in self.p["refs"]]
        faltan = {"vertice": 1, "dos_aristas": 2, "tres_planos": 3, "centro": 1, "arista_plano": 2, "ruta": 1}[t]
        if len(E) < faltan:
            raise ErrorOperacion("Faltan referencias para el punto.")
        if t == "vertice":
            p = ent.como_punto(E[0])
        elif t == "dos_aristas":
            p = cs.punto_dos_aristas(*(e.forma if e.forma is not None and e.eje is None else _eje(e) for e in E[:2]))
        elif t == "tres_planos":
            p = cs.punto_tres_planos(*(ent.como_plano(e) for e in E[:3]))
        elif t == "centro":
            p = cs.punto_centro(E[0].forma)
        elif t == "arista_plano":
            p = cs.punto_arista_plano(_eje(E[0]), ent.como_plano(E[1]))
        else:
            if E[0].forma is None:
                raise ErrorOperacion("La ruta tiene que ser una arista o una curva de boceto.")
            p = cs.punto_en_ruta(E[0].forma, ctx.evaluar(self.p["posicion"], "escalar"))
        estado.puntos[self.id] = (np.asarray(p, float), self.nombre)


class OpSCU(Operacion):
    """Sistema de coordenadas de usuario de Fusion [SLD-DEFINE-UCS]: origen, eje X y (opcional) eje Y,
    con giros y desfases. Agrega su punto de origen, sus tres ejes y sus tres planos a la construcción."""
    TIPO, ETIQUETA, ICONO = "scu", "SCU", "⊹"
    PARAMS = {"origen": None, "eje_x": None, "eje_y": None, "rx": "0 deg", "ry": "0 deg", "rz": "0 deg",
              "dx": "0 mm", "dy": "0 mm", "dz": "0 mm"}
    EXPRESIONES = ("rx", "ry", "rz", "dx", "dy", "dz")

    def dependencias(self):
        return ent.dependencias_de(self.p["origen"], self.p["eje_x"], self.p["eje_y"]) - {self.id}

    def ejecutar(self, estado, ctx):
        p = self.p
        origen = ent.como_punto(_resolver(p["origen"], estado)) if p["origen"] else np.zeros(3)
        x = _eje(_resolver(p["eje_x"], estado)).direccion if p["eje_x"] else np.array([1.0, 0, 0])
        y = _eje(_resolver(p["eje_y"], estado)).direccion if p["eje_y"] else None
        A = lambda k: ctx.evaluar(p[k], ANGULO)  # noqa: E731
        L = lambda k: ctx.evaluar(p[k])  # noqa: E731
        m = _cs().scu(origen, x, y, angulos=(A("rx"), A("ry"), A("rz")), desfase=(L("dx"), L("dy"), L("dz")))
        o, ex, ey, ez = (np.asarray(m[k], float) for k in ("origen", "x", "y", "z"))
        n = self.nombre
        estado.puntos[f"{self.id}_o"] = (o, f"{n} origen")
        for k, d in (("x", ex), ("y", ey), ("z", ez)):
            estado.ejes[f"{self.id}_{k}"] = (o, d, f"{n} {k.upper()}")
        for k, normal, u in (("xy", ez, ex), ("xz", -ey, ex), ("yz", ex, ey)):
            estado.planos[f"{self.id}_{k}"] = geo.Plano.desde_marco(o, normal, u, f"{n} {k.upper()}")


registrar_operacion(OpEje, OpPunto, OpSCU)
