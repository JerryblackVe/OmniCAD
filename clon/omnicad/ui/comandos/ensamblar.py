# -*- coding: utf-8 -*-
"""Comandos de ENSAMBLAR: nuevo componente, unión, unión como está, origen de unión, grupo rígido,
accionar uniones, vínculo de movimiento y fijar componente."""
from ...timeline.operaciones import ErrorOperacion
from ...timeline.ops_ensamblar import (MOVIMIENTOS, TIPOS_UNION, OpComponente, OpGrupoRigido, OpOrigenUnion,
                                       OpUnion, OpVinculoMovimiento, componente_por_ref)
from ...timeline.parametros import ANGULO
from ..comando import Casilla, Comando, ErrorComando, Expresion, Opciones, Seleccion, exigir, hit_desde_ref, hits, ref1
from . import registrar

SNAP = {"cara", "arista", "vertice", "plano", "eje", "punto", "curva_boceto"}
EJES = {"Z": "Z", "X": "X", "Y": "Y"}
CLAVES = {"centro": "Centro / punto medio", "inicio": "Inicio (arista o cilindro)", "fin": "Fin (arista o cilindro)"}


def _hits_cuerpos(ids, estado):
    return hits([{"tipo": "cuerpo", "cuerpo": c} for c in ids], estado)


def _version(ctx, clase, clave):
    """Al editar, la versión de cálculo del paso (una receta vieja no cambia de marco); un paso nuevo usa
    la actual (la de PARAMS)."""
    return ctx.op.p.get(clave, 1) if ctx.op is not None else clase.PARAMS[clave]


def _gira(v):
    return bool(MOVIMIENTOS[v.get("tipo", "rigida")][0])


def _desliza(v):
    return bool(MOVIMIENTOS[v.get("tipo", "rigida")][1])


def _campos_movimiento():
    t = lambda *tipos: (lambda v: v.get("tipo") in tipos)  # noqa: E731
    return [
        Opciones("tipo", "Tipo de movimiento", TIPOS_UNION),
        Opciones("eje_giro", "Girar / normal / eje", EJES, visible_si=t("revolucion", "cilindrica", "pasador_ranura",
                                                                      "planar")),
        Opciones("eje_desliz", "Deslizar", {"X": "X", "Y": "Y", "Z": "Z"}, "X",
                 visible_si=t("deslizante", "pasador_ranura")),
        Expresion("giro", "Ángulo de giro", "0 deg", ANGULO, visible_si=_gira),
        Expresion("giro2", "Ángulo 2 (cabeceo)", "0 deg", ANGULO, visible_si=t("bola")),
        Expresion("giro3", "Ángulo 3 (guiñada)", "0 deg", ANGULO, visible_si=t("bola")),
        Expresion("desliz", "Distancia", "0 mm", visible_si=_desliza),
        Expresion("desliz2", "Distancia 2", "0 mm", visible_si=t("planar")),
        Expresion("minimo", "Límite mínimo", "", visible_si=lambda v: _gira(v) or _desliza(v)),
        Expresion("maximo", "Límite máximo", "", visible_si=lambda v: _gira(v) or _desliza(v)),
    ]


def _validar(v, ctx):
    for k in ("giro", "giro2", "giro3"):
        ctx.evaluar(v.get(k) or "0", ANGULO)
    for k in ("desliz", "desliz2", "dx", "dy", "dz"):
        if k in v:
            ctx.evaluar(v.get(k) or "0")


_MOVIMIENTO = ("tipo", "eje_giro", "eje_desliz", "giro", "giro2", "giro3", "desliz", "desliz2", "minimo", "maximo")


class NuevoComponente(Comando):
    CLAVE, TITULO, ICONO = "nuevo_componente", "Nuevo componente", "nuevo_componente"
    AYUDA = "Crea un componente con los cuerpos elegidos (las uniones mueven componentes)."
    CLASE_OP = OpComponente

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None), Casilla("fijo", "Fijo")]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos del componente.")
        return self.crear_op(OpComponente, v, ctx, cuerpos=[h["ref"]["cuerpo"] for h in v["cuerpos"]],
                             fijo=v["fijo"])

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado))


class Union(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "union", "Unión", "union", "J"
    AYUDA = "Pone el componente 1 sobre el componente 2 y define cómo se mueven."
    CLASE_OP = OpUnion
    COMO_ESTA = False

    def verificar(self, ctx):
        return None if ctx.estado.componentes else "Primero creá componentes (ENSAMBLAR › Nuevo componente)."

    def campos(self, ctx):
        campos = [Seleccion("origen1", "Componente 1: ajuste", SNAP),
                  Opciones("clave1", "Punto de ajuste 1", CLAVES)]
        if self.COMO_ESTA:
            campos += [Seleccion("origen2", "Componente 2 (elegí un cuerpo)", {"cuerpo"})]
        else:
            campos += [Seleccion("origen2", "Componente 2: ajuste", SNAP),
                       Opciones("clave2", "Punto de ajuste 2", CLAVES),
                       Expresion("angulo", "Ángulo", "0 deg", ANGULO), Expresion("dx", "Desfase X", "0 mm"),
                       Expresion("dy", "Desfase Y", "0 mm"), Expresion("dz", "Desfase Z", "0 mm"),
                       Casilla("voltear", "Voltear")]
        return campos + _campos_movimiento()

    def construir(self, v, ctx):
        exigir(v, "origen1", "Seleccioná el origen en el componente 1.")
        exigir(v, "origen2", "Seleccioná un cuerpo del componente 2." if self.COMO_ESTA else
               "Seleccioná el origen en el componente 2.")
        _validar(v, ctx)
        params = {k: v.get(k) for k in _MOVIMIENTO}
        params.update(origen1=ref1(v, "origen1"), clave1=v.get("clave1", "centro"), como_esta=self.COMO_ESTA,
                      origen2=ref1(v, "origen2"), version_marco=_version(ctx, OpUnion, "version_marco"))
        if not self.COMO_ESTA:
            params.update({k: v.get(k) for k in ("angulo", "dx", "dy", "dz", "voltear", "clave2")})
        return self.crear_op(OpUnion, v, ctx, **params)

    def desde_op(self, op, ctx):
        v = dict(op.p)
        for k in ("origen1", "origen2"):
            v[k] = [hit_desde_ref(op.p[k], ctx.estado)] if op.p.get(k) else []
        return v


class UnionComoEsta(Union):
    CLAVE, TITULO, ICONO, ATAJO = "union_construida", "Unión como está", "union_construida", "Shift+J"
    AYUDA = ("Une dos componentes en la posición en que están y define su movimiento. El componente 1 es "
             "la pieza que sigue al componente 2 cuando este se mueve.")
    COMO_ESTA = True
    VARIANTE = ("como_esta", True)      # doble clic en el timeline: edita con este diálogo, no con el de Unión


class OrigenUnion(Comando):
    CLAVE, TITULO, ICONO = "origen_union", "Origen de la unión", "origen_union"
    AYUDA = "Guarda un punto con orientación para usarlo después en una unión."
    CLASE_OP = OpOrigenUnion

    def campos(self, ctx):
        return [Seleccion("origen", "Ajuste", SNAP), Opciones("clave", "Punto de ajuste", CLAVES),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO), Expresion("dx", "Desfase X", "0 mm"),
                Expresion("dy", "Desfase Y", "0 mm"), Expresion("dz", "Desfase Z", "0 mm")]

    def construir(self, v, ctx):
        exigir(v, "origen", "Seleccioná dónde va el origen.")
        return self.crear_op(OpOrigenUnion, v, ctx, origen=ref1(v, "origen"),
                             version_marco=_version(ctx, OpOrigenUnion, "version_marco"),
                             **{k: v[k] for k in ("clave", "angulo", "dx", "dy", "dz")})

    def desde_op(self, op, ctx):
        return dict(op.p, origen=[hit_desde_ref(op.p["origen"], ctx.estado)] if op.p.get("origen") else [])


def _componentes_de(v, ctx):
    comps = []
    for h in v.get("cuerpos") or []:
        c = ctx.estado.cuerpos.get(h["ref"]["cuerpo"])
        if c is not None and c.componente and c.componente not in comps:
            comps.append(c.componente)
    return comps


class GrupoRigido(Comando):
    CLAVE, TITULO, ICONO = "grupo_rigido", "Grupo rígido", "grupo_rigido"
    AYUDA = "Hace que varios componentes se muevan juntos."
    CLASE_OP = OpGrupoRigido

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Componentes (elegí un cuerpo de cada uno)", {"cuerpo"}, maximo=None)]

    def construir(self, v, ctx):
        comps = _componentes_de(v, ctx)
        if len(comps) < 2:
            raise ErrorComando("Elegí cuerpos de al menos dos componentes distintos.")
        return self.crear_op(OpGrupoRigido, v, ctx, componentes=comps)

    def desde_op(self, op, ctx):
        comps = []
        for ref in op.p["componentes"]:
            try:
                comps.append(componente_por_ref(ctx.estado, ref))    # id, nombre o cuerpo del componente
            except ErrorOperacion:
                pass
        ids = [next((c for c, cu in ctx.estado.cuerpos.items() if cu.componente == k), None) for k in comps if k]
        return dict(op.p, cuerpos=_hits_cuerpos([i for i in ids if i], ctx.estado))


def _uniones(ctx):
    return {o.id: o.nombre for o in ctx.doc.operaciones if isinstance(o, OpUnion)}


class AccionarUniones(Comando):
    CLAVE, TITULO, ICONO = "accionar_uniones", "Accionar uniones", "accionar_uniones"
    AYUDA = "Cambia el ángulo o la distancia de una unión (mueve el mecanismo)."
    SIN_OP, PREVIA = True, False

    def verificar(self, ctx):
        return None if _uniones(ctx) else "Todavía no hay uniones."

    def campos(self, ctx):
        uniones = _uniones(ctx)
        return [Opciones("union", "Unión", uniones), Expresion("giro", "Ángulo", "0 deg", ANGULO),
                Expresion("desliz", "Distancia", "0 mm")]

    def construir(self, v, ctx):
        return None

    def mostrar(self, v, ctx):
        pass

    def aplicar(self, v, ctx):
        op = ctx.doc.operacion(v["union"])
        params = dict(op.p)
        if MOVIMIENTOS[op.p["tipo"]][0]:
            ctx.evaluar(v["giro"], ANGULO)
            params["giro"] = v["giro"]
        if MOVIMIENTOS[op.p["tipo"]][1]:
            ctx.evaluar(v["desliz"])
            params["desliz"] = v["desliz"]
        nueva = OpUnion(op.id, op.nombre, op.suprimida, **params)
        (ctx.ventana._reemplazar if ctx.ventana else lambda o: ctx.doc.reemplazar(o.id, o))(nueva)


class VinculoMovimiento(Comando):
    CLAVE, TITULO, ICONO = "vinculo_movimiento", "Vínculo de movimiento", "vinculo_movimiento"
    AYUDA = "Hace que una unión se mueva en proporción a otra (engranajes, cremalleras…)."
    CLASE_OP = OpVinculoMovimiento

    def verificar(self, ctx):
        return None if len(_uniones(ctx)) >= 2 else "Hacen falta dos uniones."

    def campos(self, ctx):
        uniones = _uniones(ctx)
        return [Opciones("union1", "Unión 1", uniones), Opciones("union2", "Unión 2", uniones,
                                                                list(uniones)[-1] if uniones else None),
                Expresion("factor", "Relación (unión 2 / unión 1)", "1", "escalar"), Casilla("invertir", "Invertir")]

    def construir(self, v, ctx):
        if v["union1"] == v["union2"]:
            raise ErrorComando("Elegí dos uniones distintas.")
        return self.crear_op(OpVinculoMovimiento, v, ctx, union1=v["union1"], union2=v["union2"], factor=v["factor"],
                             invertir=v["invertir"],
                             version_vinculo=_version(ctx, OpVinculoMovimiento, "version_vinculo"))


class FijarComponente(Comando):
    CLAVE, TITULO, ICONO = "fijar_componente", "Fijar / liberar componente", "fijar_componente"
    AYUDA = "Fija un componente en su lugar (Ground): las uniones no lo mueven."
    SIN_OP, PREVIA = True, False

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Componente (elegí un cuerpo)", {"cuerpo"})]

    def construir(self, v, ctx):
        return None

    def aplicar(self, v, ctx):
        comps = _componentes_de(v, ctx)
        if not comps:
            raise ErrorComando("Ese cuerpo no está en un componente.")
        op = ctx.doc.operacion(comps[0])
        nueva = OpComponente(op.id, op.nombre, op.suprimida, **dict(op.p, fijo=not op.p.get("fijo")))
        (ctx.ventana._reemplazar if ctx.ventana else lambda o: ctx.doc.reemplazar(o.id, o))(nueva)


registrar(NuevoComponente, Union, UnionComoEsta, OrigenUnion, GrupoRigido, AccionarUniones, VinculoMovimiento,
          FijarComponente)
