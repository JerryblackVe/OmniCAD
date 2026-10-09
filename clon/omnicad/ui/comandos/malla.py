# -*- coding: utf-8 -*-
"""Comandos del espacio MALLA (pestaña MALLA de la cinta)."""
from ...timeline.ops_malla import (OpCombinarMallas, OpConvertirMalla, OpCortarPlanoMalla, OpEscalarMalla,
                                   OpGruposCaras, OpInvertirNormalMalla, OpReducirMalla, OpRemallar, OpRepararMalla,
                                   OpSepararMalla, OpSuavizarMalla, OpTeselar, OpVaciadoMalla)
from ...timeline.parametros import ANGULO, ESCALAR
from ..comando import Casilla, Comando, Entero, ErrorComando, Expresion, Opciones, Seleccion, exigir, hit_desde_ref, hits
from . import registrar


def _ids(lista):
    return [h["ref"]["cuerpo"] for h in lista or [] if h["ref"].get("tipo") == "cuerpo"]


def _hits(ids, estado):
    if isinstance(ids, str):
        ids = [ids] if ids else []
    return hits([{"tipo": "cuerpo", "cuerpo": c} for c in ids], estado)


def _mallas(ctx):
    return None if any(getattr(c, "tipo", "") == "malla" for c in ctx.estado.cuerpos.values()) else \
        "No hay cuerpos de malla: insertá una malla (STL, OBJ, 3MF o PLY) o teselá un cuerpo."


def _clase(clave, titulo, ico, clase_op, ayuda, extras=(), params=lambda v, ctx: {}):
    """Comando de malla de una sola selección de cuerpos + campos extra."""

    class _Cmd(Comando):
        CLAVE, TITULO, ICONO, AYUDA, CLASE_OP = clave, titulo, ico, ayuda, clase_op
        verificar = staticmethod(_mallas)

        def campos(self, ctx):
            return [Seleccion("cuerpos", "Cuerpos de malla", {"cuerpo"}, maximo=None)] + [f() for f in extras]

        def construir(self, v, ctx):
            exigir(v, "cuerpos", "Seleccioná los cuerpos de malla.")
            return self.crear_op(clase_op, v, ctx, cuerpos=_ids(v["cuerpos"]), **params(v, ctx))

        def desde_op(self, op, ctx):
            return dict(op.p, cuerpos=_hits(op.p["cuerpos"], ctx.estado))

    _Cmd.__name__ = f"Malla_{clave}"
    return _Cmd


Reparar = _clase("reparar_malla", "Reparar", "reparar_malla", OpRepararMalla,
                 "Une vértices, quita triángulos rotos, orienta normales y cierra agujeros.",
                 [lambda: Opciones("tipo", "Tipo de reparación", {"cerrar_agujeros": "Cerrar agujeros",
                                                                   "unir_vertices": "Unir vértices",
                                                                   "coser_y_quitar": "Coser y quitar",
                                                                   "reconstruir": "Reconstruir"})],
                 lambda v, ctx: {"tipo": v["tipo"]})
Grupos = _clase("grupos_caras", "Generar grupos de caras", "grupos_caras", OpGruposCaras,
                "Agrupa caras de la malla según el ángulo entre ellas.",
                [lambda: Expresion("angulo", "Ángulo", "30 deg", ANGULO)], lambda v, ctx: {"angulo": v["angulo"]})
Reducir = _clase("reducir_malla", "Reducir", "reducir_malla", OpReducirMalla, "Baja la cantidad de triángulos.",
                 [lambda: Opciones("tipo", "Tipo de reducción", {"proporcion": "Proporción", "caras": "Cantidad de caras",
                                                                  "tolerancia": "Tolerancia"}),
                  lambda: Expresion("proporcion", "Proporción", "0.5", ESCALAR,
                                    visible_si=lambda v: v.get("tipo") == "proporcion"),
                  lambda: Entero("caras", "Cantidad de caras", 1000, 4, 10_000_000,
                                 visible_si=lambda v: v.get("tipo") == "caras"),
                  lambda: Expresion("tolerancia", "Tolerancia", "0.1 mm",
                                    visible_si=lambda v: v.get("tipo") == "tolerancia")],
                 lambda v, ctx: {k: v[k] for k in ("tipo", "proporcion", "caras", "tolerancia")})
Remallar = _clase("remallar", "Remallar", "remallar", OpRemallar, "Rehace los triángulos con un tamaño parejo.",
                  [lambda: Expresion("densidad", "Densidad", "1", ESCALAR),
                   lambda: Casilla("preservar_bordes", "Conservar bordes", True),
                   lambda: Casilla("preservar_aristas_vivas", "Conservar aristas vivas", True)],
                  lambda v, ctx: {k: v[k] for k in ("densidad", "preservar_bordes", "preservar_aristas_vivas")})
Vaciado = _clase("vaciado_malla", "Vaciado", "vaciado_malla", OpVaciadoMalla, "Ahueca la malla con un espesor.",
                 [lambda: Expresion("espesor", "Espesor", "2 mm")], lambda v, ctx: {"espesor": v["espesor"]})
Suavizar = _clase("suavizar_malla", "Suavizar", "suavizar_malla", OpSuavizarMalla, "Suaviza la malla sin encogerla.",
                  [lambda: Expresion("intensidad", "Intensidad", "0.5", ESCALAR),
                   lambda: Entero("iteraciones", "Iteraciones", 10, 1, 500)],
                  lambda v, ctx: {"intensidad": v["intensidad"], "iteraciones": v["iteraciones"]})
InvertirNormal = _clase("invertir_normal_malla", "Invertir normal", "invertir_normal", OpInvertirNormalMalla,
                        "Da vuelta la orientación de los triángulos.")
Separar = _clase("separar_malla", "Separar", "separar_malla", OpSepararMalla,
                 "Separa la malla en un cuerpo por cáscara (o por grupo de caras).",
                 [lambda: Opciones("tipo", "Tipo", {"cascaras": "Cáscaras", "grupos": "Grupos de caras"})],
                 lambda v, ctx: {"tipo": v["tipo"]})
Escalar = _clase("escalar_malla", "Escalar malla", "escalar_malla", OpEscalarMalla, "Escala la malla en X, Y y Z.",
                 [lambda: Expresion("fx", "Escala X", "1", ESCALAR), lambda: Expresion("fy", "Escala Y", "1", ESCALAR),
                  lambda: Expresion("fz", "Escala Z", "1", ESCALAR)],
                 lambda v, ctx: {k: v[k] for k in ("fx", "fy", "fz")})
Convertir = _clase("convertir_malla", "Convertir malla", "convertir_malla", OpConvertirMalla,
                   "Convierte la malla en un cuerpo B-rep (sólido si está cerrada).",
                   [lambda: Opciones("metodo", "Método", {"facetado": "Facetado", "prismatico": "Prismático"}),
                    lambda: Casilla("mantener", "Conservar la malla original")],
                   lambda v, ctx: {"metodo": v["metodo"], "mantener": v["mantener"]})


class Teselar(Comando):
    CLAVE, TITULO, ICONO = "malla_teselar", "Malla de cuerpo B-Rep", "malla_teselar"
    AYUDA = "Convierte cuerpos sólidos o de superficie en cuerpos de malla."
    CLASE_OP = OpTeselar

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None),
                Opciones("refinamiento", "Refinamiento", {"bajo": "Bajo", "medio": "Medio", "alto": "Alto"}, "medio"),
                Casilla("mantener", "Conservar el cuerpo original", True)]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos.")
        return self.crear_op(OpTeselar, v, ctx, cuerpos=_ids(v["cuerpos"]), refinamiento=v["refinamiento"],
                             mantener=v["mantener"])

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits(op.p["cuerpos"], ctx.estado))


class CortarPlano(Comando):
    CLAVE, TITULO, ICONO = "cortar_plano", "Corte de plano", "cortar_plano"
    AYUDA = "Corta mallas con un plano: recorta (con tapa) o parte en dos cuerpos."
    CLASE_OP = OpCortarPlanoMalla
    verificar = staticmethod(_mallas)

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos de malla", {"cuerpo"}, maximo=None),
                Seleccion("plano", "Plano de corte", {"plano", "cara_plana"}),
                Opciones("tipo", "Tipo de corte", {"recortar": "Recortar", "partir": "Dividir cuerpo",
                                                   "partir_caras": "Dividir caras"}),
                Casilla("rellenar", "Rellenar", True), Casilla("invertir", "Invertir")]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná las mallas.")
        exigir(v, "plano", "Seleccioná el plano.")
        return self.crear_op(OpCortarPlanoMalla, v, ctx, cuerpos=_ids(v["cuerpos"]), plano=v["plano"][0]["ref"],
                             tipo=v["tipo"], rellenar=v["rellenar"], invertir=v["invertir"])

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits(op.p["cuerpos"], ctx.estado),
                    plano=[hit_desde_ref(op.p["plano"], ctx.estado)] if op.p["plano"] else [])


class CombinarMallas(Comando):
    CLAVE, TITULO, ICONO = "combinar_mallas", "Combinar mallas", "combinar_mallas"
    AYUDA = "Une, corta, interseca o fusiona cuerpos de malla."
    CLASE_OP = OpCombinarMallas
    verificar = staticmethod(_mallas)

    def campos(self, ctx):
        return [Seleccion("objetivo", "Cuerpo de destino", {"cuerpo"}),
                Seleccion("herramientas", "Cuerpos de herramienta", {"cuerpo"}, maximo=None),
                Opciones("operacion", "Operación", {"unir": "Unir", "cortar": "Cortar", "intersecar": "Intersecar",
                                                     "fusionar": "Fusionar"}),
                Casilla("mantener", "Mantener herramientas")]

    def construir(self, v, ctx):
        exigir(v, "objetivo", "Seleccioná el cuerpo de destino.")
        exigir(v, "herramientas", "Seleccioná las herramientas.")
        obj = _ids(v["objetivo"])[0]
        if obj in _ids(v["herramientas"]):
            raise ErrorComando("El destino no puede ser también herramienta.")
        return self.crear_op(OpCombinarMallas, v, ctx, objetivo=obj, herramientas=_ids(v["herramientas"]),
                             operacion=v["operacion"], mantener=v["mantener"])

    def desde_op(self, op, ctx):
        return dict(op.p, objetivo=_hits(op.p["objetivo"], ctx.estado), herramientas=_hits(op.p["herramientas"],
                                                                                          ctx.estado))


registrar(Teselar, Reparar, Grupos, Reducir, Remallar, CortarPlano, Vaciado, CombinarMallas, Suavizar, InvertirNormal,
          Separar, Escalar, Convertir)
