# -*- coding: utf-8 -*-
"""
ENSAMBLAR de Fusion [Fusion-Assemble]: componentes, uniones (las 7 de Fusion), uniones «como está»,
orígenes de unión, grupos rígidos, vínculos de movimiento e insertar otro diseño como componente.

Modelo: cada cuerpo pertenece a un componente (`Cuerpo.componente`, "" = la raíz). Una unión calcula un
marco (origen + ejes) sobre la geometría del componente 1 y otro sobre la del componente 2 y MUEVE los
cuerpos del componente 1 para que los marcos coincidan (caras enfrentadas, como en Fusion; «Voltear»
las pone del mismo lado), con ángulo y desfases. Después aplica el movimiento de la unión (giro,
deslizamiento…) según sus valores, que se cambian con «Accionar uniones». Cada unión deja en
`estado.uniones` lo necesario para accionarla o animarla sin recalcular.
"""
import math

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import referencias as refs
from . import entidades as ent
from .operaciones import ANGULO, ErrorOperacion, Operacion, _deps_objetivo, _resolver, registrar_operacion

TIPOS_UNION = {"rigida": "Rígida", "revolucion": "Revolución", "deslizante": "Deslizante", "cilindrica": "Cilíndrica",
               "pasador_ranura": "Pasador-ranura", "planar": "Planar", "bola": "Bola"}
# grados de libertad: (giros, desplazamientos) por tipo
MOVIMIENTOS = {"rigida": ([], []), "revolucion": (["giro"], []), "deslizante": ([], ["desliz"]),
               "cilindrica": (["giro"], ["desliz"]), "pasador_ranura": (["giro"], ["desliz"]),
               "planar": (["giro"], ["desliz", "desliz2"]), "bola": (["giro", "giro2", "giro3"], [])}
EJES = {"X": 0, "Y": 1, "Z": 2}


# ---------------------------------------------------------------- marcos (orígenes de unión)
def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ErrorOperacion("Dirección nula en el origen de la unión.")
    return v / n


def marco_desde(origen, z, x=None):
    """Matriz 4x4 (columnas: X, Y, Z, origen) de un marco ortonormal derecho."""
    z = _unit(z)
    if x is None or abs(float(np.dot(_unit(x), z))) > 0.999:
        x = np.cross((0, 0, 1.0), z) if abs(z[2]) < 0.9 else np.cross(z, (0, 1.0, 0))
        x = np.cross(z, np.cross(x, z))
    x = _unit(np.asarray(x, float) - z * float(np.dot(x, z)))
    y = np.cross(z, x)
    m = np.identity(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, np.asarray(origen, float)
    return m


def marco_de(e, punto_clave="centro"):
    """Origen de unión «simple» sobre una entidad resuelta (como el «Snap» del diálogo Unión)."""
    if e.tipo == "plano" or (e.tipo == "boceto" and e.plano is not None):
        return marco_desde(e.plano.origen, e.plano.normal, e.plano.u)
    if e.tipo == "cara":
        f = refs.firma_cara(e.forma)
        if e.plano is not None:
            centro = np.array(f["centro"])
            circ = _centro_circular(e.forma)
            return marco_desde(circ if circ is not None else centro, e.plano.normal, e.plano.u)
        if "eje" in f:
            p, d = ent.como_eje(e)
            c = np.array(f["centro"])
            pie = p + d * float((c - p) @ d)
            return marco_desde(pie, d)
        return marco_desde(f["centro"], (0, 0, 1))
    if e.tipo in ("arista", "curva_boceto") and e.forma is not None:
        f = refs.firma_arista(e.forma)
        if f["geom"] == "circulo":
            from OCP.BRepAdaptor import BRepAdaptor_Curve
            ax = BRepAdaptor_Curve(e.forma).Circle().Axis().Direction()
            return marco_desde(f["centro"], (ax.X(), ax.Y(), ax.Z()))
        a, b = (np.array(p) for p in f["extremos"])
        p = {"inicio": a, "fin": b}.get(punto_clave, np.array(f["medio"]))
        if f["geom"] == "linea":
            return marco_desde(p, b - a)
        return marco_desde(p, e.plano.normal if e.plano is not None else (0, 0, 1))
    if e.tipo == "eje":
        p, d = e.eje
        return marco_desde(p, d)
    if e.punto is not None:
        return marco_desde(e.punto, e.plano.normal if e.plano is not None else (0, 0, 1))
    raise ErrorOperacion("No se puede poner un origen de unión en esa selección.")


def _centro_circular(cara):
    """Centro del contorno circular de una cara plana (agujero o disco), si lo tiene."""
    circulos = [refs.firma_arista(a) for a in refs.subformas(cara, "arista")]
    circulos = [c for c in circulos if c["geom"] == "circulo"]
    if len(circulos) == 1 or (circulos and all(np.allclose(c["centro"], circulos[0]["centro"]) for c in circulos)):
        return np.array(circulos[0]["centro"])
    return None


def _rot(eje, grados):
    a = math.radians(grados)
    c, s = math.cos(a), math.sin(a)
    m = np.identity(4)
    i, j = {0: (1, 2), 1: (2, 0), 2: (0, 1)}[eje]
    m[i, i], m[i, j], m[j, i], m[j, j] = c, -s, s, c
    return m


def _tras(v):
    m = np.identity(4)
    m[:3, 3] = v
    return m


def movimiento(tipo, valores, eje_giro="Z", eje_desliz="X"):
    """Transformación (en el marco de la unión) que produce el movimiento con esos valores."""
    g, d = MOVIMIENTOS[tipo]
    m = np.identity(4)
    if tipo in ("deslizante", "cilindrica"):
        m = _tras(np.identity(3)[EJES[eje_giro if tipo == "cilindrica" else eje_desliz]] * valores.get("desliz", 0.0))
    elif tipo == "pasador_ranura":
        m = _tras(np.identity(3)[EJES[eje_desliz]] * valores.get("desliz", 0.0))
    elif tipo == "planar":
        normal = EJES[eje_giro]
        a, b = [i for i in range(3) if i != normal]
        m = _tras(np.identity(3)[a] * valores.get("desliz", 0.0) + np.identity(3)[b] * valores.get("desliz2", 0.0))
    if "giro" in g:
        m = m @ _rot(EJES[eje_giro] if tipo != "bola" else 2, valores.get("giro", 0.0))
    if tipo == "bola":
        m = m @ _rot(1, valores.get("giro2", 0.0)) @ _rot(0, valores.get("giro3", 0.0))
    return m


# ---------------------------------------------------------------- operaciones
def _componente_de(estado, e):
    if e.cuerpo is None:
        return None
    return estado.cuerpo(e.cuerpo).componente or ""


def _mover_componentes(estado, comps, m):
    for c in estado.cuerpos.values():
        if (c.componente or "") in comps:
            if getattr(c, "tipo", "solido") == "malla":
                nueva = c.forma.copia()
                nueva.vertices = (np.c_[nueva.vertices, np.ones(len(nueva.vertices))] @ m.T)[:, :3]
                c.forma = nueva
            else:
                c.forma = geo.transformar(c.forma, m)
    for k in comps:
        if k in estado.componentes:
            actual = np.asarray(estado.componentes[k].get("matriz", np.identity(4).tolist()), float)
            estado.componentes[k]["matriz"] = (m @ actual).tolist()


def _grupo(estado, comp):
    """El componente más los que están en un grupo rígido con él."""
    salida = {comp}
    for g in estado.grupos_rigidos:
        if comp in g:
            salida |= set(g)
    return salida


class OpComponente(Operacion):
    """ENSAMBLAR › Nuevo componente [GUID-5966BF6B]: crea un componente y le pasa los cuerpos elegidos
    («Desde cuerpos»). `fijo` es «Fijar» (Ground): una unión no puede moverlo."""
    TIPO, ETIQUETA, ICONO = "componente", "Componente", "▣"
    PARAMS = {"cuerpos": [], "fijo": False}

    def dependencias(self):
        return _deps_objetivo(self.p["cuerpos"]) - {self.id}

    def ejecutar(self, estado, ctx):
        estado.componentes[self.id] = {"nombre": self.nombre, "padre": "", "fijo": bool(self.p["fijo"]),
                                       "matriz": np.identity(4).tolist()}
        for cid in self.p["cuerpos"]:
            estado.cuerpo(cid).componente = self.id


class OpUnion(Operacion):
    """ENSAMBLAR › Unión [ASM-CREATE-JOINT] y Unión como está [ASM-CREATE-AS-BUILT-JOINT]."""
    TIPO, ETIQUETA, ICONO = "union", "Unión", "⚙"
    PARAMS = {"tipo": "rigida", "origen1": None, "origen2": None, "clave1": "centro", "clave2": "centro",
              "angulo": "0 deg", "dx": "0 mm", "dy": "0 mm", "dz": "0 mm", "voltear": False, "como_esta": False,
              "eje_giro": "Z", "eje_desliz": "X", "giro": "0 deg", "giro2": "0 deg", "giro3": "0 deg",
              "desliz": "0 mm", "desliz2": "0 mm", "minimo": "", "maximo": ""}
    EXPRESIONES = ("angulo", "dx", "dy", "dz", "giro", "giro2", "giro3", "desliz", "desliz2")

    def dependencias(self):
        return ent.dependencias_de(self.p["origen1"], self.p["origen2"]) - {self.id}

    def valores(self, ctx):
        g = {k: ctx.evaluar(self.p[k], ANGULO) for k in ("giro", "giro2", "giro3")}
        g.update({k: ctx.evaluar(self.p[k]) for k in ("desliz", "desliz2")})
        # Límites de movimiento (Joint Motion Limits): recortan el movimiento principal.
        gira = bool(MOVIMIENTOS[self.p["tipo"]][0])
        clave, tipo = ("giro", ANGULO) if gira else ("desliz", "longitud")
        if str(self.p.get("minimo") or "").strip():
            g[clave] = max(g[clave], ctx.evaluar(self.p["minimo"], tipo))
        if str(self.p.get("maximo") or "").strip():
            g[clave] = min(g[clave], ctx.evaluar(self.p["maximo"], tipo))
        return g

    def ejecutar(self, estado, ctx):
        p = self.p
        if not p["origen1"]:
            raise ErrorOperacion("Elegí el origen de la unión en el componente 1.")
        e1 = _resolver(p["origen1"], estado)
        comp1 = _componente_de(estado, e1)
        if not comp1:
            raise ErrorOperacion("El componente 1 tiene que ser un componente (no la raíz): creá uno con "
                                 "ENSAMBLAR › Nuevo componente.")
        if estado.componentes.get(comp1, {}).get("fijo"):
            raise ErrorOperacion("El componente 1 está fijo: no se puede mover con una unión.")
        F1 = marco_de(e1, p["clave1"])
        if p["como_esta"]:
            F2, comp2, alinear = F1, "", np.identity(4)
        else:
            if not p["origen2"]:
                raise ErrorOperacion("Elegí el origen de la unión en el componente 2.")
            e2 = _resolver(p["origen2"], estado)
            comp2 = _componente_de(estado, e2) or ""
            if comp2 == comp1:
                raise ErrorOperacion("Los dos orígenes están en el mismo componente.")
            F2 = marco_de(e2, p["clave2"])
            enfrentar = np.identity(4) if p["voltear"] else _rot(0, 180.0)
            desfase = _tras([ctx.evaluar(p[k]) for k in ("dx", "dy", "dz")])
            alinear = desfase @ _rot(2, ctx.evaluar(p["angulo"], ANGULO)) @ enfrentar
        mov = movimiento(p["tipo"], self.valores(ctx), p["eje_giro"], p["eje_desliz"])
        m = F2 @ mov @ alinear @ np.linalg.inv(F1)
        comps = _grupo(estado, comp1)
        _mover_componentes(estado, comps, m)
        estado.uniones[self.id] = {"nombre": self.nombre, "tipo": p["tipo"], "comp1": comp1, "comp2": comp2,
                                   "componentes": sorted(comps), "marco": F2.tolist(), "eje_giro": p["eje_giro"],
                                   "eje_desliz": p["eje_desliz"], "valores": self.valores(ctx)}


class OpOrigenUnion(Operacion):
    """ENSAMBLAR › Origen de la unión [ASM-CREATE-JOINT-ORIGIN]: un marco guardado que después sirve para
    unir. Se guarda como plano de construcción (su plano XY) con el ángulo pedido."""
    TIPO, ETIQUETA, ICONO = "origen_union", "Origen de unión", "⌖"
    PARAMS = {"origen": None, "clave": "centro", "angulo": "0 deg", "dx": "0 mm", "dy": "0 mm", "dz": "0 mm"}
    EXPRESIONES = ("angulo", "dx", "dy", "dz")

    def dependencias(self):
        return ent.dependencias_de(self.p["origen"]) - {self.id}

    def ejecutar(self, estado, ctx):
        if not self.p["origen"]:
            raise ErrorOperacion("Elegí dónde va el origen.")
        F = marco_de(_resolver(self.p["origen"], estado), self.p["clave"])
        F = F @ _tras([ctx.evaluar(self.p[k]) for k in ("dx", "dy", "dz")]) @ _rot(2, ctx.evaluar(self.p["angulo"], ANGULO))
        estado.planos[self.id] = geo.Plano.desde_marco(F[:3, 3], F[:3, 2], F[:3, 0], self.nombre)


class OpGrupoRigido(Operacion):
    """ENSAMBLAR › Grupo rígido [ASM-CREATE-RIGID-GROUP]: los componentes se mueven juntos."""
    TIPO, ETIQUETA, ICONO = "grupo_rigido", "Grupo rígido", "⛓"
    PARAMS = {"componentes": []}

    def dependencias(self):
        return set(self.p["componentes"]) - {self.id}

    def ejecutar(self, estado, ctx):
        faltan = [c for c in self.p["componentes"] if c not in estado.componentes]
        if len(self.p["componentes"]) < 2 or faltan:
            raise ErrorOperacion("Elegí al menos dos componentes existentes.")
        estado.grupos_rigidos = estado.grupos_rigidos + [list(self.p["componentes"])]


class OpVinculoMovimiento(Operacion):
    """ENSAMBLAR › Vínculo de movimiento [GUID-074622A9]: la unión 2 se mueve en proporción a la 1."""
    TIPO, ETIQUETA, ICONO = "vinculo_movimiento", "Vínculo de movimiento", "⇄"
    PARAMS = {"union1": "", "union2": "", "factor": "1", "invertir": False}
    EXPRESIONES = ("factor",)

    def dependencias(self):
        return {self.p["union1"], self.p["union2"]} - {"", self.id}

    def ejecutar(self, estado, ctx):
        u1, u2 = estado.uniones.get(self.p["union1"]), estado.uniones.get(self.p["union2"])
        if not u1 or not u2:
            raise ErrorOperacion("Las dos uniones tienen que existir antes del vínculo.")
        clave1 = "giro" if MOVIMIENTOS[u1["tipo"]][0] else "desliz"
        clave2 = "giro" if MOVIMIENTOS[u2["tipo"]][0] else "desliz"
        factor = ctx.evaluar(self.p["factor"], "escalar") * (-1 if self.p["invertir"] else 1)
        extra = dict.fromkeys(MOVIMIENTOS[u2["tipo"]][0] + MOVIMIENTOS[u2["tipo"]][1], 0.0)
        extra[clave2] = u1["valores"][clave1] * factor
        F2 = np.asarray(u2["marco"], float)
        m = F2 @ movimiento(u2["tipo"], extra, u2["eje_giro"], u2["eje_desliz"]) @ np.linalg.inv(F2)
        _mover_componentes(estado, set(u2["componentes"]), m)


class OpInsertarDiseno(Operacion):
    """INSERTAR › Insertar componente / derivación [ASM-INSERT-FUSION-DESIGN]: los cuerpos finales de otro
    diseño (.omnicad) entran como un componente nuevo. La receta se guarda adentro (copia independiente)."""
    TIPO, ETIQUETA, ICONO = "insertar_diseno", "Insertar diseño", "⇩"
    PARAMS = {"archivo": "", "receta": None}

    def ejecutar(self, estado, ctx):
        from .documento import Documento
        if not self.p["receta"]:
            raise ErrorOperacion("La inserción no tiene el diseño.")
        otro = Documento.desde_dict(self.p["receta"])
        estado.componentes[self.id] = {"nombre": self.p["archivo"] or self.nombre, "padre": "", "fijo": False,
                                       "matriz": np.identity(4).tolist()}
        for c in otro.estado_final.cuerpos.values():
            estado.nuevo_cuerpo(self.id, c.forma, c.tipo, nombre=c.nombre, apariencia=c.apariencia,
                                material=c.material, componente=self.id)


registrar_operacion(OpComponente, OpUnion, OpOrigenUnion, OpGrupoRigido, OpVinculoMovimiento, OpInsertarDiseno)
