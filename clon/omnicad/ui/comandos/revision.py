# -*- coding: utf-8 -*-
"""INSPECCIONAR › Revisar geometría y Reparar cuerpo (F2 + B2 + RH13 de las listas de brechas).

- «Revisar geometría» no deja paso (como Medir): arma el informe en el panel con `nucleo.revision` (validez,
  estanqueidad, aristas abiertas y no manifold, autointersecciones, tolerancias y, con la casilla, la revisión de
  impresión 3D) y marca cada problema en la vista: rojo = error, naranja = aviso. Con «Reparar al aceptar» deja un
  paso «Reparar cuerpo».
- «Reparar cuerpo» crea o edita ese paso (doble clic en el timeline).
"""
import numpy as np

from ...nucleo import revision as rv
from ...timeline.ops_chapa import cuerpos_del_modelo
from ...timeline.ops_revision import OpReparar
from ...timeline.parametros import ANGULO
from .. import formato
from ..comando import Casilla, Comando, ErrorComando, Expresion, Info, Seleccion, exigir, hits
from . import registrar

_ROJO, _NARANJA, _NEGRO = (0.92, 0.12, 0.10), (1.0, 0.6, 0.05), (0.1, 0.1, 0.1)
_LISTA = 8                  # problemas que se listan por cuerpo en el panel (todos se marcan en la vista)
_DETALLADOS = 2             # con más cuerpos, el informe es una línea por cuerpo (el panel no crece sin fin)


def _ids(v):
    return [h["ref"]["cuerpo"] for h in v.get("cuerpos") or [] if h["ref"].get("tipo") == "cuerpo"]


def _hits(ids, estado):
    return hits([{"tipo": "cuerpo", "cuerpo": c} for c in ids], estado)


def _hay_cuerpos(ctx):
    return None if cuerpos_del_modelo(ctx.estado) else "No hay cuerpos para revisar."


def _nombre(ctx, c):
    return ctx.doc.propiedad(c.id, "nombre") or c.nombre


def _punto(p):
    return "(" + "; ".join(formato.numero(float(x)) for x in p) + ")"


def primitivas(informes):
    """Dibujo de los problemas para `visor.set_capa`: las aristas y bordes como líneas y el resto como puntos;
    rojo los errores y naranja los avisos (los errores van encima)."""
    prims = []
    for gravedad, color in (("aviso", _NARANJA), ("error", _ROJO)):
        segmentos, puntos = [], []
        for informe in informes:
            for p in informe["problemas"]:
                if p["gravedad"] != gravedad:
                    continue
                if p.get("segmentos") is not None and len(p["segmentos"]):
                    segmentos.append(p["segmentos"])
                elif p["punto"] is not None:
                    puntos.append(p["punto"])
        if segmentos:
            prims.append(("lineas", np.concatenate(segmentos).astype(np.float32), color, 3.5))
        if puntos:
            arr = np.array(puntos, np.float32)
            prims += [("puntos", arr, _NEGRO, 12), ("puntos", arr, color, 8)]
    return prims


class RevisarGeometria(Comando):
    CLAVE, TITULO, ICONO = "revisar_geometria", "Revisar geometría", "revisar_geometria"
    AYUDA = ("Diagnostica los cuerpos: sólido válido, estanco, aristas abiertas y no manifold, autointersecciones y "
             "tolerancias; con la casilla, también la impresión 3D (espesor mínimo, voladizos, aristas filosas). Marca "
             "cada problema en la vista y, con «Reparar al aceptar», deja un paso Reparar cuerpo.")
    SIN_OP = True
    verificar = staticmethod(_hay_cuerpos)

    def campos(self, ctx):
        def impresion(v):
            return bool(v.get("impresion"))
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, minimo=0, maximo=None, ayuda="Sin selección: todos."),
                Casilla("autointersecciones", "Buscar autointersecciones", True),
                Casilla("impresion", "Revisión de impresión 3D"),
                Expresion("espesor", "Espesor mínimo", "0.8 mm", visible_si=impresion,
                          ayuda="Pared más fina que esto: error (p. ej. 2 veces la boquilla)."),
                Expresion("voladizo", "Ángulo de voladizo", "45 deg", ANGULO, visible_si=impresion,
                          ayuda="Desde la vertical: más inclinado necesita soportes."),
                Expresion("filo", "Ángulo de arista filosa", "20 deg", ANGULO, visible_si=impresion,
                          ayuda="Aristas convexas con ángulo interior menor que esto."),
                Info("resultado", "Informe", self._resultado),
                Casilla("reparar", "Reparar al aceptar (agrega un paso)"),
                Expresion("tolerancia", "Tolerancia de reparación", "0.01 mm",
                          visible_si=lambda v: bool(v.get("reparar")))]

    def _cuerpos(self, v, ctx):
        ids = _ids(v) or [c.id for c in cuerpos_del_modelo(ctx.estado)]
        return [ctx.estado.cuerpos[c] for c in ids if c in ctx.estado.cuerpos]

    def calcular(self, v, ctx):
        """[(cuerpo, informe de geometría, informe de impresión o None)], recordado mientras no cambien los cuerpos ni
        las opciones (el panel lo pide en cada vista previa)."""
        cuerpos = self._cuerpos(v, ctx)
        impresion = None
        if v.get("impresion"):
            impresion = (ctx.evaluar(v["espesor"]), ctx.evaluar(v["voladizo"], ANGULO), ctx.evaluar(v["filo"], ANGULO))
        auto = bool(v.get("autointersecciones"))
        clave = (tuple((c.id, id(c.forma)) for c in cuerpos), auto, impresion)
        if getattr(self, "_clave", None) != clave:
            res = []
            for c in cuerpos:
                imp = None
                if impresion:
                    imp = rv.revisar_impresion(c.forma, espesor_minimo=impresion[0], angulo_voladizo=impresion[1],
                                               angulo_filoso=impresion[2])
                res.append((c, rv.revisar(c.forma, autointersecciones=auto), imp))
            self._clave, self._res = clave, res
        return self._res

    def _resultado(self, v, ctx):
        res = self.calcular(v, ctx)
        if not res:
            return "No hay cuerpos para revisar."
        detallado = len(res) <= _DETALLADOS
        bloques = []
        for c, geo_i, imp in res:
            problemas = list(geo_i["problemas"])
            errores, avisos = geo_i["errores"], geo_i["avisos"]
            if imp is not None:
                problemas += imp["problemas"]
                errores, avisos = errores + imp["errores"], avisos + imp["avisos"]
            if not detallado:                    # muchos cuerpos: una línea por cuerpo
                estado = "sin problemas" if not problemas else f"{errores} error(es), {avisos} aviso(s)"
                bloques.append(f"■ {_nombre(ctx, c)}: {'válido' if geo_i['valido'] else 'INVÁLIDO'}, "
                               f"{'estanco' if geo_i['cerrado'] else 'abierto'}; {estado}")
                continue
            lineas = [f"■ {_nombre(ctx, c)}"] + rv.resumen(geo_i)
            if imp is not None:
                lineas += ["Impresión 3D:"] + rv.resumen(imp)[:5]
            if not problemas:
                lineas.append("Sin problemas.")
            else:
                lineas.append(f"{errores} error(es) y {avisos} aviso(s):")
                for p in problemas[:_LISTA]:
                    lineas.append(f"• {p['mensaje']}" + ("" if p["punto"] is None else f" {_punto(p['punto'])}"))
                if errores + avisos > _LISTA:
                    lineas.append(f"… y {errores + avisos - _LISTA} más (marcados en la vista).")
            bloques.append("\n".join(lineas))
        return ("\n\n" if detallado else "\n").join(bloques)

    def construir(self, v, ctx):
        return None

    def mostrar(self, v, ctx):
        if ctx.ventana is None:
            return
        informes = [i for _c, g, imp in self.calcular(v, ctx) for i in (g, imp) if i is not None]
        ctx.ventana.visor.set_capa("medida", primitivas(informes))

    def aplicar(self, v, ctx):
        if not v.get("reparar"):
            return
        ctx.evaluar(v["tolerancia"])                      # una tolerancia mal escrita se avisa en el panel
        ids = _ids(v) or [c.id for c, g, _imp in self.calcular(v, ctx) if g["errores"] or g["avisos"]]
        if not ids:
            raise ErrorComando("Ningún cuerpo tiene problemas de geometría: no hace falta reparar. Destildá «Reparar "
                               "al aceptar» para cerrar.")
        op = OpReparar(ctx.doc.nuevo_id(), RepararCuerpo().nombre_nuevo(ctx), cuerpos=ids, tolerancia=v["tolerancia"])
        (ctx.ventana._agregar if ctx.ventana else ctx.doc.agregar)(op)

    def al_cerrar(self, ctx):
        if ctx.ventana:
            ctx.ventana.visor.set_capa("medida", None)


class RepararCuerpo(Comando):
    CLAVE, TITULO, ICONO = "reparar_cuerpo", "Reparar cuerpo", "reparar_cuerpo"
    CLASE_OP = OpReparar
    AYUDA = ("Arregla cuerpos sólidos, de superficie o de malla: cose aristas abiertas, baja las tolerancias, corrige "
             "la orientación y une caras coplanares. Queda como un paso editable del timeline.")
    verificar = staticmethod(_hay_cuerpos)

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None),
                Expresion("tolerancia", "Tolerancia", "0.01 mm",
                          ayuda="Distancia para coser y tope de las tolerancias del kernel; 0 = sin tope."),
                Casilla("coser", "Coser aristas abiertas", True),
                Casilla("arreglar", "Corregir orientación y contornos", True),
                Casilla("refinar", "Refinar (unir caras coplanares)", True),
                Info("antes", "Antes de reparar", self._antes)]

    def _antes(self, v, ctx):
        lineas = []
        for cid in _ids(v):
            c = ctx.estado.cuerpos.get(cid)
            if c is None:
                continue
            i = rv.revisar(c.forma, autointersecciones=False, max_problemas=0)
            lineas.append(f"{_nombre(ctx, c)}: {'válido' if i['valido'] else 'INVÁLIDO'}, "
                          f"{'estanco' if i['cerrado'] else 'abierto'}, {i['aristas_libres']} arista(s) libre(s), "
                          f"{i['aristas_no_manifold']} no manifold")
        return "\n".join(lineas) or "Elegí los cuerpos."

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos a reparar.")
        return self.crear_op(OpReparar, v, ctx, cuerpos=_ids(v), tolerancia=v["tolerancia"], coser=bool(v["coser"]),
                             refinar=bool(v["refinar"]), arreglar=bool(v["arreglar"]))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits(op.p["cuerpos"], ctx.estado))


registrar(RevisarGeometria, RepararCuerpo)
