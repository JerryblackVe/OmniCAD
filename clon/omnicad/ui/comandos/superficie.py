# -*- coding: utf-8 -*-
"""Comandos de la pestaña SUPERFICIE (y Engrosar, que también está en SÓLIDO › CREAR)."""
import numpy as np

from ...timeline.ops_superficie import (OpCoser, OpDescoser, OpDestrimar, OpEngrosar, OpExtenderSup,
                                        OpInvertirNormal, OpParche, OpRecortar, OpReglada, OpSupBarrido,
                                        OpSupDesfase, OpSupEmpalme, OpSupExtruir, OpSupRevolucion, OpSupSolevacion)
from ...timeline.parametros import ANGULO
from ..comando import Casilla, Comando, ErrorComando, Expresion, Opciones, Seleccion, exigir, hit_desde_ref, hits, ref1, refs
from . import registrar
from .comunes import OPCIONES_OPERACION, campo_objetivos, objetivos

CURVAS = {"curva_boceto", "arista"}


def _h1(ref, estado):
    return [hit_desde_ref(ref, estado)] if ref else []


def _cuerpos(lista):
    return [h["ref"]["cuerpo"] for h in lista or [] if h["ref"].get("tipo") == "cuerpo"]


def _hits_cuerpos(ids, estado):
    return hits([{"tipo": "cuerpo", "cuerpo": c} for c in ids], estado)


class SupExtruir(Comando):
    CLAVE, TITULO, ICONO = "sup_extruir", "Extruir superficie", "sup_extruir"
    AYUDA = "Extruye curvas (abiertas o cerradas) y crea una superficie."
    CLASE_OP = OpSupExtruir

    def campos(self, ctx):
        return [Seleccion("curvas", "Perfiles", CURVAS, maximo=None),
                Seleccion("direccion", "Dirección", {"plano", "cara_plana", "eje", "arista_lineal"}, minimo=0,
                          ayuda="Sin selección: perpendicular al plano del boceto."),
                Expresion("distancia", "Distancia", "10 mm"), Casilla("simetrica", "Simétrica"),
                Expresion("conicidad", "Ángulo de conicidad", "0 deg", ANGULO)]

    def construir(self, v, ctx):
        exigir(v, "curvas", "Seleccioná las curvas.")
        ctx.evaluar(v["distancia"])
        return self.crear_op(OpSupExtruir, v, ctx, curvas=refs(v, "curvas"), direccion=ref1(v, "direccion"),
                             distancia=v["distancia"], simetrica=v["simetrica"], conicidad=v["conicidad"])

    def desde_op(self, op, ctx):
        return dict(op.p, curvas=hits(op.p["curvas"], ctx.estado), direccion=_h1(op.p["direccion"], ctx.estado))


class SupRevolucion(Comando):
    CLAVE, TITULO, ICONO = "sup_revolucion", "Revolución de superficie", "sup_revolucion"
    AYUDA = "Gira curvas alrededor de un eje y crea una superficie."
    CLASE_OP = OpSupRevolucion

    def campos(self, ctx):
        return [Seleccion("curvas", "Perfil", CURVAS, maximo=None), Seleccion("eje", "Eje", {"eje"}),
                Expresion("angulo", "Ángulo", "360 deg", ANGULO)]

    def construir(self, v, ctx):
        exigir(v, "curvas", "Seleccioná las curvas.")
        exigir(v, "eje", "Seleccioná el eje.")
        return self.crear_op(OpSupRevolucion, v, ctx, curvas=refs(v, "curvas"), eje=ref1(v, "eje"), angulo=v["angulo"])

    def desde_op(self, op, ctx):
        return dict(op.p, curvas=hits(op.p["curvas"], ctx.estado), eje=_h1(op.p["eje"], ctx.estado))


class SupBarrido(Comando):
    CLAVE, TITULO, ICONO = "sup_barrido", "Barrido de superficie", "sup_barrido"
    AYUDA = "Lleva un perfil abierto o cerrado a lo largo de una ruta."
    CLASE_OP = OpSupBarrido

    def campos(self, ctx):
        return [Seleccion("perfil", "Perfil", CURVAS, maximo=None), Seleccion("ruta", "Ruta", CURVAS, maximo=None),
                Opciones("orientacion", "Orientación", {"perpendicular": "Perpendicular", "paralela": "Paralela"}),
                Expresion("torsion", "Ángulo de torsión", "0 deg", ANGULO,
                          visible_si=lambda v: v.get("orientacion") == "perpendicular")]

    def construir(self, v, ctx):
        exigir(v, "perfil", "Seleccioná el perfil.")
        exigir(v, "ruta", "Seleccioná la ruta.")
        return self.crear_op(OpSupBarrido, v, ctx, perfil=refs(v, "perfil"), ruta=refs(v, "ruta"),
                             orientacion=v["orientacion"], torsion=v["torsion"])

    def desde_op(self, op, ctx):
        return dict(op.p, perfil=hits(op.p["perfil"], ctx.estado), ruta=hits(op.p["ruta"], ctx.estado))


class SupSolevacion(Comando):
    CLAVE, TITULO, ICONO = "sup_solevacion", "Solevación de superficie", "sup_solevacion"
    AYUDA = "Crea una superficie que pasa por varias curvas (secciones) en orden."
    CLASE_OP = OpSupSolevacion

    def campos(self, ctx):
        return [Seleccion("secciones", "Perfiles", CURVAS | {"vertice", "punto"}, maximo=None),
                Casilla("cerrada", "Cerrado"), Casilla("reglada", "Tramos rectos (reglada)")]

    def construir(self, v, ctx):
        if len(v.get("secciones") or []) < 2:
            raise ErrorComando("Seleccioná al menos dos secciones, en orden.")
        return self.crear_op(OpSupSolevacion, v, ctx, secciones=refs(v, "secciones"), cerrada=v["cerrada"],
                             reglada=v["reglada"])

    def desde_op(self, op, ctx):
        return dict(op.p, secciones=hits(op.p["secciones"], ctx.estado))


class Parche(Comando):
    CLAVE, TITULO, ICONO = "parche", "Parche", "parche"
    AYUDA = "Tapa un contorno cerrado de aristas o curvas con una superficie."
    CLASE_OP = OpParche

    def campos(self, ctx):
        return [Seleccion("contorno", "Aristas de contorno", CURVAS, maximo=None),
                Opciones("continuidad", "Continuidad", {"G0": "Conexión (G0)", "G1": "Tangente (G1)",
                                                         "G2": "Curvatura (G2)"})]

    def construir(self, v, ctx):
        exigir(v, "contorno", "Seleccioná el contorno.")
        return self.crear_op(OpParche, v, ctx, contorno=refs(v, "contorno"), continuidad=v["continuidad"])

    def desde_op(self, op, ctx):
        return dict(op.p, contorno=hits(op.p["contorno"], ctx.estado))


class Reglada(Comando):
    CLAVE, TITULO, ICONO = "reglada", "Superficie reglada", "reglada"
    AYUDA = "Crea superficies rectas que salen de aristas (normal, tangente o en una dirección)."
    CLASE_OP = OpReglada

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas", CURVAS, maximo=None),
                Opciones("tipo", "Tipo", {"normal": "Normal", "tangente": "Tangente", "direccion": "Dirección"}),
                Seleccion("direccion", "Dirección", {"plano", "cara_plana", "eje", "arista_lineal"},
                          visible_si=lambda v: v.get("tipo") == "direccion"),
                Expresion("distancia", "Distancia", "10 mm"), Expresion("angulo", "Ángulo", "0 deg", ANGULO)]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná las aristas.")
        return self.crear_op(OpReglada, v, ctx, aristas=refs(v, "aristas"), tipo=v["tipo"],
                             direccion=ref1(v, "direccion"), distancia=v["distancia"], angulo=v["angulo"])

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado), direccion=_h1(op.p["direccion"], ctx.estado))


class SupDesfase(Comando):
    CLAVE, TITULO, ICONO = "sup_desfase", "Desfase de superficie", "sup_desfase"
    AYUDA = "Crea una superficie paralela a caras de un cuerpo."
    CLASE_OP = OpSupDesfase

    def campos(self, ctx):
        return [Seleccion("caras", "Caras", {"cara", "cuerpo"}, maximo=None),
                Expresion("distancia", "Distancia de desfase", "2 mm"),
                Opciones("tipo", "Tipo de desfase", {"agudo": "Desfase afilado", "redondeado": "Desfase redondeado"})]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras.")
        return self.crear_op(OpSupDesfase, v, ctx, caras=refs(v, "caras"), distancia=v["distancia"], tipo=v["tipo"])

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado))


class Recortar(Comando):
    CLAVE, TITULO, ICONO = "recortar_sup", "Recortar", "recortar_sup"
    AYUDA = "Corta una superficie con otra (o con un plano) y quita la parte elegida."
    CLASE_OP = OpRecortar

    def campos(self, ctx):
        return [Seleccion("herramienta", "Herramienta de recorte", {"cara", "plano", "cuerpo", "curva_boceto"}),
                Seleccion("region", "Región a quitar", {"cara"})]

    def construir(self, v, ctx):
        exigir(v, "herramienta", "Seleccioná la herramienta de recorte.")
        region = exigir(v, "region", "Hacé clic sobre la parte de la superficie que querés quitar.")[0]
        return self.crear_op(OpRecortar, v, ctx, cuerpo=region["ref"]["cuerpo"], herramienta=ref1(v, "herramienta"),
                             punto=[float(c) for c in np.asarray(region.get("punto", (0, 0, 0)), float)])

    def desde_op(self, op, ctx):
        return dict(op.p, herramienta=_h1(op.p["herramienta"], ctx.estado),
                    region=[{"ref": {"tipo": "cara", "cuerpo": op.p["cuerpo"]}, "tipo": "cara", "dibujo": [],
                             "punto": np.asarray(op.p["punto"], float)}])


class Destrimar(Comando):
    CLAVE, TITULO, ICONO = "destrimar", "Destrimar", "destrimar"
    AYUDA = "Devuelve una cara recortada a los límites naturales de su superficie."
    CLASE_OP = OpDestrimar

    def campos(self, ctx):
        return [Seleccion("caras", "Caras", {"cara"}, maximo=None),
                Opciones("contornos", "Tipo de destrimado", {"exteriores": "Aristas exteriores",
                                                            "interiores": "Aristas interiores", "todos": "Todas"})]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras.")
        return self.crear_op(OpDestrimar, v, ctx, caras=refs(v, "caras"), contornos=v["contornos"])

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado))


class Extender(Comando):
    CLAVE, TITULO, ICONO = "extender_sup", "Extender", "extender_sup"
    AYUDA = "Alarga los bordes libres de una superficie."
    CLASE_OP = OpExtenderSup

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas", {"arista"}, maximo=None), Expresion("distancia", "Distancia", "5 mm"),
                Opciones("tipo", "Tipo de extensión", {"natural": "Natural", "tangente": "Tangente",
                                                       "perpendicular": "Perpendicular"})]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná los bordes.")
        return self.crear_op(OpExtenderSup, v, ctx, aristas=refs(v, "aristas"), distancia=v["distancia"], tipo=v["tipo"])

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado))


class Coser(Comando):
    CLAVE, TITULO, ICONO = "coser", "Coser", "coser"
    AYUDA = "Une superficies por sus bordes; si quedan cerradas, el resultado es un sólido."
    CLASE_OP = OpCoser

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Superficies", {"cuerpo"}, maximo=None),
                Expresion("tolerancia", "Tolerancia", "0.01 mm")]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná las superficies.")
        return self.crear_op(OpCoser, v, ctx, cuerpos=_cuerpos(v["cuerpos"]), tolerancia=v["tolerancia"])

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado))


class Descoser(Comando):
    CLAVE, TITULO, ICONO = "descoser", "Descoser", "descoser"
    AYUDA = "Separa las caras de un cuerpo en superficies sueltas."
    CLASE_OP = OpDescoser

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None)]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos.")
        return self.crear_op(OpDescoser, v, ctx, cuerpos=_cuerpos(v["cuerpos"]))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado))


class InvertirNormal(Comando):
    CLAVE, TITULO, ICONO = "invertir_normal", "Invertir normal", "invertir_normal"
    AYUDA = "Da vuelta la cara de afuera de una superficie."
    CLASE_OP = OpInvertirNormal

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Superficies", {"cuerpo"}, maximo=None)]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná las superficies.")
        return self.crear_op(OpInvertirNormal, v, ctx, cuerpos=_cuerpos(v["cuerpos"]))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado))


class Engrosar(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "engrosar", "Engrosar", "engrosar", "Shift+C"
    AYUDA = "Da espesor a caras o superficies para hacer un sólido."
    CLASE_OP = OpEngrosar

    def campos(self, ctx):
        return [Seleccion("caras", "Caras", {"cara", "cuerpo"}, maximo=None),
                Expresion("espesor", "Grosor", "2 mm"),
                Opciones("direccion", "Dirección", {"un_lado": "Un lado", "simetrica": "Simétrica"}),
                Opciones("tipo", "Tipo de engrosado",
                         {"agudo": "Engrosado afilado", "redondeado": "Engrosado redondeado"}),
                Opciones("operacion", "Operación", OPCIONES_OPERACION, "nuevo"), campo_objetivos()]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras.")
        ctx.evaluar(v["espesor"])
        return self.crear_op(OpEngrosar, v, ctx, caras=refs(v, "caras"), espesor=v["espesor"],
                             direccion=v["direccion"], tipo=v["tipo"], operacion=v["operacion"],
                             objetivos=objetivos(v))

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado),
                    objetivos=_hits_cuerpos(op.p.get("objetivos") or [], ctx.estado))


class SupEmpalme(Comando):
    CLAVE, TITULO, ICONO = "sup_empalme", "Empalme de superficie", "empalme_3d"
    AYUDA = "Redondea o bisela aristas entre superficies."
    CLASE_OP = OpSupEmpalme

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas", {"arista"}, maximo=None),
                Opciones("tipo", "Tipo", {"empalme": "Empalme", "chaflan": "Chaflán"}),
                Expresion("medida", "Radio / distancia", "1 mm")]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná las aristas.")
        return self.crear_op(OpSupEmpalme, v, ctx, aristas=refs(v, "aristas"), tipo=v["tipo"], medida=v["medida"])

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado))


registrar(SupExtruir, SupRevolucion, SupBarrido, SupSolevacion, Parche, Reglada, SupDesfase, Recortar, Destrimar,
          Extender, Coser, Descoser, InvertirNormal, Engrosar, SupEmpalme)
