# -*- coding: utf-8 -*-
"""Comandos de SÓLIDO › MODIFICAR con diálogo al estilo Fusion."""
from ...nucleo.analisis import TABLA_MATERIALES as MATERIALES
from ...timeline.operaciones import OPERACIONES_COMBINAR, OpCombinar
from ...timeline.ops_modificar import (TIPOS_MOVIMIENTO, OpAlinear, OpBorrarCaras, OpChaflan, OpDesfaseCara, OpQuitar,
                                       OpDesmoldeo, OpDivisionSilueta, OpDividirCara, OpDividirCuerpo, OpEmpalme,
                                       OpEscala, OpMover, OpReemplazarCara, OpVaciado)
from ...timeline.parametros import ANGULO, ESCALAR
from ..comando import (Casilla, Comando, ErrorComando, Expresion, Opciones, Seleccion, Texto, exigir, hit_desde_ref,
                       hits, ref1, refs)
from . import registrar
from .comunes import evaluar_o_cero


def _cuerpos(v, clave="cuerpos"):
    """Ids de los cuerpos elegidos (`v` es el dict de valores o directamente la lista de selección)."""
    lista = v if isinstance(v, list) else (v.get(clave) or [])
    return [h["ref"]["cuerpo"] for h in lista if h["ref"].get("tipo") == "cuerpo"]


def _hits_cuerpos(ids, estado):
    if isinstance(ids, str):
        ids = [ids] if ids else []
    return hits([{"tipo": "cuerpo", "cuerpo": c} for c in ids], estado)


def _hit1(ref, estado):
    return [hit_desde_ref(ref, estado)] if ref else []


def _con_cuerpos(ctx):
    return None if ctx.estado.cuerpos else "Este comando necesita al menos un cuerpo."


# ---------------------------------------------------------------- manipuladores en la vista
def _flecha_arista(ctx, seleccion, clave, chaflan=False):
    """Flecha de radio/distancia en el punto medio de la primera arista: arranca donde queda la superficie
    del empalme (o del chaflán) y avanza hacia donde crece, así la punta sigue al cursor."""
    import math

    from .. import manipuladores as mp
    arista = next((h for h in seleccion or [] if h["ref"].get("tipo") == "arista"), None)
    e = mp.entidad(arista, ctx.estado) if arista is not None else None
    if e is None or e.cuerpo not in ctx.estado.cuerpos:
        return []
    medio, hacia, fi = mp.datos_arista(e.forma, ctx.estado.cuerpos[e.cuerpo].forma)
    factor = math.sin(fi / 2) if chaflan else 1 / max(math.cos(fi / 2), 1e-3) - 1
    return [mp.Flecha(clave, medio, hacia, factor=max(factor, 0.15), minimo=0.0)]


def _cara_y_normal(ctx, seleccion):
    """(punto, normal hacia afuera) de la primera cara elegida o, si se eligió un cuerpo, de su cara más grande."""
    from ...nucleo import geometria as geo
    from .. import manipuladores as mp
    for h in seleccion or []:
        e = mp.entidad(h, ctx.estado)
        if e is None or e.forma is None:
            continue
        if e.tipo == "cara":
            return mp.punto_normal_cara(e.forma)
        if e.tipo == "cuerpo":
            caras = geo.caras(e.forma)
            if caras:
                return mp.punto_normal_cara(max(caras, key=geo.area))
    return None


class Empalme(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "empalme_3d", "Empalme", "empalme_3d", "F"
    AYUDA = "Redondea aristas (quita material en las exteriores y agrega en las interiores)."
    CLASE_OP = OpEmpalme
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        empalme = lambda v: v.get("tipo") != "reglas"  # noqa: E731
        reglas = lambda v: v.get("tipo") == "reglas"  # noqa: E731
        return [
            Opciones("tipo", "Tipo", {"empalme": "Empalme", "reglas": "Empalme de reglas"}),
            Seleccion("aristas", "Aristas", {"arista"}, maximo=None, visible_si=empalme),
            Opciones("tipo_radio", "Tipo de radio", {"constante": "Constante", "cuerda": "Longitud de cuerda",
                                                     "variable": "Variable"}, visible_si=empalme),
            Expresion("radio", "Radio", "1 mm",
                      visible_si=lambda v: v.get("tipo_radio") != "cuerda" or v.get("tipo") == "reglas"),
            Expresion("radio_fin", "Radio final", "2 mm",
                      visible_si=lambda v: empalme(v) and v.get("tipo_radio") == "variable"),
            Expresion("cuerda", "Longitud de cuerda", "1 mm",
                      visible_si=lambda v: empalme(v) and v.get("tipo_radio") == "cuerda"),
            Seleccion("caras_a", "Caras/operaciones", {"cara"}, maximo=None, visible_si=reglas),
            Opciones("regla", "Regla", {"todas": "Todas las aristas", "entre": "Entre caras/operaciones"},
                     visible_si=reglas),
            Seleccion("caras_b", "Caras/operaciones 2", {"cara"}, maximo=None,
                      visible_si=lambda v: reglas(v) and v.get("regla") == "entre"),
            Opciones("redondeos", "Topología", {"ambos": "Redondeos y empalmes", "redondeos": "Solo redondeos",
                                                "empalmes": "Solo empalmes"}, visible_si=reglas),
            Casilla("cadena_tangente", "Cadena tangente", True, visible_si=empalme),
        ]

    def construir(self, v, ctx):
        if v.get("tipo") == "reglas":
            exigir(v, "caras_a", "Seleccioná las caras para la regla.")
        else:
            exigir(v, "aristas", "Seleccioná las aristas a empalmar.")
        ctx.evaluar(v["radio"])
        return self.crear_op(OpEmpalme, v, ctx, tipo=v["tipo"], aristas=refs(v, "aristas"), tipo_radio=v["tipo_radio"],
                             radio=v["radio"], radio_fin=v["radio_fin"], cuerda=v["cuerda"],
                             cadena_tangente=v["cadena_tangente"], caras_a=refs(v, "caras_a"),
                             caras_b=refs(v, "caras_b"), regla=v["regla"], redondeos=v["redondeos"])

    def manipuladores(self, ctx, v):
        if v.get("tipo") == "reglas":
            return []
        return _flecha_arista(ctx, v.get("aristas"), "cuerda" if v.get("tipo_radio") == "cuerda" else "radio")

    def desde_op(self, op, ctx):
        v = dict(op.p)
        for k in ("aristas", "caras_a", "caras_b"):
            v[k] = hits(op.p[k], ctx.estado)
        return v


class Chaflan(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "chaflan_3d", "Chaflán", "chaflan_3d", "Ctrl+\\"
    AYUDA = "Bisela aristas con una distancia, dos distancias o distancia y ángulo."
    CLASE_OP = OpChaflan
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [
            Seleccion("aristas", "Aristas", {"arista"}, maximo=None),
            Opciones("tipo", "Tipo de chaflán", {"distancia_igual": "Distancia igual", "dos_distancias": "Dos distancias",
                                                 "distancia_angulo": "Distancia y ángulo"}),
            Expresion("distancia", "Distancia", "1 mm"),
            Expresion("distancia2", "Distancia 2", "1 mm", visible_si=lambda v: v.get("tipo") == "dos_distancias"),
            Expresion("angulo", "Ángulo", "45 deg", ANGULO, visible_si=lambda v: v.get("tipo") == "distancia_angulo"),
            Casilla("voltear", "Voltear", visible_si=lambda v: v.get("tipo") != "distancia_igual"),
            Casilla("cadena_tangente", "Cadena tangente", True),
        ]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná las aristas.")
        ctx.evaluar(v["distancia"])
        return self.crear_op(OpChaflan, v, ctx, aristas=refs(v, "aristas"),
                             **{k: v[k] for k in ("tipo", "distancia", "distancia2", "angulo", "voltear",
                                                  "cadena_tangente")})

    def manipuladores(self, ctx, v):
        return _flecha_arista(ctx, v.get("aristas"), "distancia", chaflan=True)

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado))


class Vaciado(Comando):
    CLAVE, TITULO, ICONO = "vaciado", "Vaciado", "vaciado"
    AYUDA = "Ahueca un cuerpo dejando paredes de espesor constante; las caras elegidas quedan abiertas."
    CLASE_OP = OpVaciado
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [
            Seleccion("caras", "Caras/cuerpo", {"cara", "cuerpo"}, maximo=None),
            Casilla("tangente", "Cadena tangente", True),
            Opciones("direccion", "Dirección", {"interior": "Interior", "exterior": "Exterior", "ambos": "Ambos"}),
            Expresion("espesor_interior", "Espesor interior", "1 mm",
                      visible_si=lambda v: v.get("direccion") != "exterior"),
            Expresion("espesor_exterior", "Espesor exterior", "1 mm",
                      visible_si=lambda v: v.get("direccion") != "interior"),
            Opciones("tipo", "Tipo de vaciado", {"afilado": "Desfase afilado", "redondeado": "Desfase redondeado"}),
        ]

    def construir(self, v, ctx):
        sel = exigir(v, "caras", "Seleccioná las caras a quitar o un cuerpo.")
        return self.crear_op(OpVaciado, v, ctx, caras=[h["ref"] for h in sel if h["ref"]["tipo"] == "cara"],
                             cuerpos=[h["ref"]["cuerpo"] for h in sel if h["ref"]["tipo"] == "cuerpo"],
                             **{k: v[k] for k in ("espesor_interior", "espesor_exterior", "direccion", "tangente",
                                                  "tipo")})

    def manipuladores(self, ctx, v):
        """Flecha de espesor sobre la cara elegida: hacia adentro (interior) y/o hacia afuera (exterior)."""
        from .. import manipuladores as mp
        base = _cara_y_normal(ctx, v.get("caras"))
        if base is None:
            return []
        punto, n = base
        salida = []
        if v.get("direccion") != "exterior":
            salida.append(mp.Flecha("espesor_interior", punto, -n, minimo=0.0))
        if v.get("direccion") != "interior":
            salida.append(mp.Flecha("espesor_exterior", punto, n, minimo=0.0))
        return salida

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado) + _hits_cuerpos(op.p["cuerpos"], ctx.estado))


class Desmoldeo(Comando):
    CLAVE, TITULO, ICONO = "desmoldeo", "Desmoldeo", "desmoldeo"
    AYUDA = "Inclina caras un ángulo respecto de la dirección de extracción del molde."
    CLASE_OP = OpDesmoldeo
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [
            Seleccion("plano", "Plano fijo", {"cara_plana", "plano"}),
            Seleccion("caras", "Caras", {"cara"}, maximo=None),
            Casilla("voltear", "Invertir dirección de extracción"),
            Opciones("lados", "Tipo de desmoldeo", {"uno": "Un lado", "dos": "Dos lados", "simetrico": "Simétrico"}),
            Expresion("angulo", "Ángulo", "3 deg", ANGULO),
            Expresion("angulo2", "Ángulo 2", "3 deg", ANGULO, visible_si=lambda v: v.get("lados") == "dos"),
        ]

    def construir(self, v, ctx):
        exigir(v, "plano", "Seleccioná el plano fijo.")
        exigir(v, "caras", "Seleccioná las caras a inclinar.")
        return self.crear_op(OpDesmoldeo, v, ctx, plano=ref1(v, "plano"), caras=refs(v, "caras"),
                             **{k: v[k] for k in ("angulo", "lados", "angulo2", "voltear")})

    def desde_op(self, op, ctx):
        return dict(op.p, plano=_hit1(op.p["plano"], ctx.estado), caras=hits(op.p["caras"], ctx.estado))


class Escala(Comando):
    CLAVE, TITULO, ICONO = "escala_3d", "Escala", "escala_3d"
    AYUDA = "Agranda o achica cuerpos respecto de un punto (uniforme o con un factor por eje)."
    CLASE_OP = OpEscala
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        no_uniforme = lambda v: v.get("tipo") == "no_uniforme"  # noqa: E731
        return [
            Seleccion("cuerpos", "Entidades", {"cuerpo"}, maximo=None),
            Seleccion("punto", "Punto", {"vertice", "punto"}, minimo=0,
                      ayuda="Punto base. Sin selección: el origen."),
            Opciones("tipo", "Tipo de escala", {"uniforme": "Uniforme", "no_uniforme": "No uniforme"}),
            Expresion("factor", "Factor de escala", "1", ESCALAR, visible_si=lambda v: not no_uniforme(v)),
            Expresion("fx", "Escala X", "1", ESCALAR, visible_si=no_uniforme),
            Expresion("fy", "Escala Y", "1", ESCALAR, visible_si=no_uniforme),
            Expresion("fz", "Escala Z", "1", ESCALAR, visible_si=no_uniforme),
        ]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos.")
        return self.crear_op(OpEscala, v, ctx, cuerpos=_cuerpos(v), punto=ref1(v, "punto"),
                             **{k: v[k] for k in ("tipo", "factor", "fx", "fy", "fz")})

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado), punto=_hit1(op.p["punto"], ctx.estado))


class CaraDesfase(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "desfase_cara", "Cara de desfase", "desfase_cara", "Shift+D"
    AYUDA = "Mueve caras del cuerpo a lo largo de su normal (agrega o quita material)."
    CLASE_OP = OpDesfaseCara
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("caras", "Caras", {"cara"}, maximo=None), Expresion("distancia", "Distancia", "1 mm"),
                Casilla("tangente", "Cadena tangente", True)]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras.")
        ctx.evaluar(v["distancia"])
        return self.crear_op(OpDesfaseCara, v, ctx, caras=refs(v, "caras"), distancia=v["distancia"],
                             tangente=v["tangente"])

    def manipuladores(self, ctx, v):
        from .. import manipuladores as mp
        base = _cara_y_normal(ctx, v.get("caras"))
        return [mp.Flecha("distancia", base[0], base[1])] if base is not None else []

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado))


class PulsarTirar(Comando):
    """Pulsar/tirar (Q): sobre una cara hace un desfase de cara; sobre una arista, un empalme."""
    CLAVE, TITULO, ICONO, ATAJO = "pulsar_tirar", "Pulsar/tirar", "pulsar_tirar", "Q"
    AYUDA = "Clic en una cara para desplazarla, o en una arista para redondearla."
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("objetos", "Cara o arista", {"cara", "arista"}, maximo=None),
                Expresion("distancia", "Distancia / radio", "1 mm")]

    def construir(self, v, ctx):
        sel = exigir(v, "objetos", "Seleccioná una cara o una arista.")
        tipos = {h["ref"]["tipo"] for h in sel}
        if len(tipos) > 1:
            raise ErrorComando("Elegí solo caras o solo aristas.")
        ctx.evaluar(v["distancia"])
        if tipos == {"cara"}:
            op = self.crear_op(OpDesfaseCara, v, ctx, caras=refs(v, "objetos"), distancia=v["distancia"])
            base = "Desfase de cara"
        else:
            op = self.crear_op(OpEmpalme, v, ctx, aristas=refs(v, "objetos"), radio=v["distancia"])
            base = "Empalme"
        if ctx.op is None:
            op.nombre = _siguiente(ctx, base)
        return op

    def manipuladores(self, ctx, v):
        """Sobre una cara: flecha de desfase por su normal (negativo = quita material); sobre una arista:
        la flecha del radio del empalme."""
        from .. import manipuladores as mp
        sel = v.get("objetos") or []
        if not sel:
            return []
        if sel[0]["ref"].get("tipo") == "arista":
            return _flecha_arista(ctx, sel, "distancia")
        base = _cara_y_normal(ctx, sel)
        return [mp.Flecha("distancia", base[0], base[1])] if base is not None else []


class ReemplazarCara(Comando):
    CLAVE, TITULO, ICONO = "reemplazar_cara", "Reemplazar cara", "reemplazar_cara"
    AYUDA = "Lleva caras del cuerpo hasta otra cara o un plano."
    CLASE_OP = OpReemplazarCara
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("caras", "Caras de origen", {"cara"}, maximo=None),
                Seleccion("destino", "Caras de destino", {"cara", "plano"})]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras de origen.")
        exigir(v, "destino", "Seleccioná la cara o el plano de destino.")
        return self.crear_op(OpReemplazarCara, v, ctx, caras=refs(v, "caras"), destino=ref1(v, "destino"))

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado), destino=_hit1(op.p["destino"], ctx.estado))


class DividirCara(Comando):
    CLAVE, TITULO, ICONO = "dividir_cara", "Dividir cara", "dividir_cara"
    AYUDA = "Parte caras con una cara, un plano o curvas."
    CLASE_OP = OpDividirCara
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("caras", "Caras para dividir", {"cara"}, maximo=None),
                Seleccion("herramienta", "Herramienta de división", {"cara", "plano", "arista", "curva_boceto"}),
                Casilla("extender", "Extender herramienta de división", True)]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras a dividir.")
        exigir(v, "herramienta", "Seleccioná la herramienta.")
        return self.crear_op(OpDividirCara, v, ctx, caras=refs(v, "caras"), herramienta=ref1(v, "herramienta"),
                             extender=v["extender"])

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado), herramienta=_hit1(op.p["herramienta"], ctx.estado))


class DividirCuerpo(Comando):
    CLAVE, TITULO, ICONO = "dividir_cuerpo", "Dividir cuerpo", "dividir_cuerpo"
    AYUDA = "Parte un cuerpo en varios con un plano, una cara o otro cuerpo."
    CLASE_OP = OpDividirCuerpo
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Cuerpo para dividir", {"cuerpo"}),
                Seleccion("herramienta", "Herramientas de división", {"cara", "plano", "cuerpo"}),
                Casilla("extender", "Extender herramienta de división", True)]

    def construir(self, v, ctx):
        exigir(v, "cuerpo", "Seleccioná el cuerpo.")
        exigir(v, "herramienta", "Seleccioná la herramienta.")
        return self.crear_op(OpDividirCuerpo, v, ctx, cuerpo=_cuerpos(v, "cuerpo")[0],
                             herramienta=ref1(v, "herramienta"), extender=v["extender"])

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpo=_hits_cuerpos(op.p["cuerpo"], ctx.estado),
                    herramienta=_hit1(op.p["herramienta"], ctx.estado))


class DivisionSilueta(Comando):
    CLAVE, TITULO, ICONO = "division_silueta", "División de silueta", "division_silueta"
    AYUDA = "Parte las caras de un cuerpo por su silueta vista desde una dirección."
    CLASE_OP = OpDivisionSilueta
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("direccion", "Dirección de vista", {"plano", "cara_plana", "eje", "arista_lineal"}),
                Seleccion("cuerpo", "Cuerpo de destino", {"cuerpo"})]

    def construir(self, v, ctx):
        exigir(v, "direccion", "Seleccioná la dirección.")
        exigir(v, "cuerpo", "Seleccioná el cuerpo.")
        return self.crear_op(OpDivisionSilueta, v, ctx, cuerpo=_cuerpos(v, "cuerpo")[0], direccion=ref1(v, "direccion"))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpo=_hits_cuerpos(op.p["cuerpo"], ctx.estado),
                    direccion=_hit1(op.p["direccion"], ctx.estado))


class MoverCopiar(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "mover_copiar", "Mover/copiar", "mover_copiar", "M"
    AYUDA = "Mueve, gira o copia cuerpos: libre, trasladar, girar, punto a punto o punto a posición."
    CLASE_OP = OpMover
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        t = lambda *tipos: (lambda v: v.get("tipo") in tipos)  # noqa: E731
        return [
            Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None),
            Opciones("tipo", "Tipo de movimiento", TIPOS_MOVIMIENTO),
            Seleccion("pivote", "Pivote", {"vertice", "punto"}, minimo=0, visible_si=t("libre"),
                      ayuda="Centro de giro. Sin selección: el centro de los cuerpos."),
            Seleccion("direccion", "Dirección", {"eje", "arista_lineal", "cara_plana", "plano"}, minimo=0,
                      visible_si=t("traslacion"), ayuda="Sin selección: ejes X, Y, Z del diseño."),
            Expresion("distancia", "Distancia", "10 mm", visible_si=lambda v: v.get("tipo") == "traslacion"
                      and bool(v.get("direccion"))),
            Expresion("dx", "Distancia X", "0 mm", visible_si=lambda v: v.get("tipo") == "libre" or (
                v.get("tipo") == "traslacion" and not v.get("direccion"))),
            Expresion("dy", "Distancia Y", "0 mm", visible_si=lambda v: v.get("tipo") == "libre" or (
                v.get("tipo") == "traslacion" and not v.get("direccion"))),
            Expresion("dz", "Distancia Z", "0 mm", visible_si=lambda v: v.get("tipo") == "libre" or (
                v.get("tipo") == "traslacion" and not v.get("direccion"))),
            Expresion("rx", "Ángulo X", "0 deg", ANGULO, visible_si=t("libre")),
            Expresion("ry", "Ángulo Y", "0 deg", ANGULO, visible_si=t("libre")),
            Expresion("rz", "Ángulo Z", "0 deg", ANGULO, visible_si=t("libre")),
            Seleccion("eje", "Eje", {"eje"}, visible_si=t("rotacion")),
            Expresion("angulo", "Ángulo", "90 deg", ANGULO, visible_si=t("rotacion")),
            Seleccion("origen", "Punto de origen", {"vertice", "punto"},
                      visible_si=t("punto_a_punto", "punto_a_posicion")),
            Seleccion("destino", "Punto de destino", {"vertice", "punto"}, visible_si=t("punto_a_punto")),
            Expresion("x", "X", "0 mm", visible_si=t("punto_a_posicion")),
            Expresion("y", "Y", "0 mm", visible_si=t("punto_a_posicion")),
            Expresion("z", "Z", "0 mm", visible_si=t("punto_a_posicion")),
            Casilla("copiar", "Crear copia"),
        ]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos a mover.")
        p = {k: v.get(k) for k in ("tipo", "dx", "dy", "dz", "rx", "ry", "rz", "distancia", "angulo", "x", "y", "z",
                                    "copiar")}
        p.update(cuerpos=_cuerpos(v), pivote=ref1(v, "pivote"), direccion=ref1(v, "direccion"), eje=ref1(v, "eje"),
                 origen=ref1(v, "origen"), destino=ref1(v, "destino"))
        return self.crear_op(OpMover, v, ctx, **p)

    def manipuladores(self, ctx, v):
        """La tríada de Fusion en el pivote (libre: flechas, arcos de giro, planos y esfera), la flecha de
        «Trasladar» con dirección, el arco de «Girar» y la tríada de «Punto a posición»."""
        import numpy as np

        from ...nucleo import geometria as geo
        from ...timeline import entidades as ent
        from .. import manipuladores as mp
        ids = [c for c in _cuerpos(v) if c in ctx.estado.cuerpos]
        if not ids:
            return []
        L = lambda k: evaluar_o_cero(ctx, v.get(k))  # noqa: E731
        centros = []
        for c in ids:
            try:
                caja = geo.caja_envolvente(ctx.estado.cuerpos[c].forma)
            except Exception:  # noqa: BLE001 — cuerpos de malla: sin caja exacta
                caja = None
            if caja:
                centros.append((np.array(caja[0]) + np.array(caja[1])) / 2)
        centro = np.mean(centros, axis=0) if centros else np.zeros(3)
        tipo = v.get("tipo")
        if tipo == "libre":
            e = mp.entidad(v["pivote"][0], ctx.estado) if v.get("pivote") else None
            pivote = ent.como_punto(e) if e is not None else centro
            return [mp.Triada(np.asarray(pivote, float) + [L("dx"), L("dy"), L("dz")])]
        if tipo == "traslacion":
            if v.get("direccion"):
                try:
                    d = ent.direccion(mp.entidad(v["direccion"][0], ctx.estado))
                except Exception:  # noqa: BLE001
                    return []
                return [mp.Flecha("distancia", centro, d)]
            return [mp.Triada(centro + [L("dx"), L("dy"), L("dz")], giros=None)]
        if tipo == "rotacion" and v.get("eje"):
            try:
                punto, d = ent.como_eje(mp.entidad(v["eje"][0], ctx.estado))
            except Exception:  # noqa: BLE001
                return []
            d = mp.unitario(d)
            pie = np.asarray(punto, float) + d * float((centro - punto) @ d)
            radio = float(np.linalg.norm(centro - pie))
            return [mp.Angulo("angulo", pie, d, centro - pie, radio if radio > 1e-6 else None)]
        if tipo == "punto_a_posicion":
            return [mp.Triada([L("x"), L("y"), L("z")], claves=("x", "y", "z"), giros=None)]
        return []

    def desde_op(self, op, ctx):
        v = dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado))
        for k in ("pivote", "direccion", "eje", "origen", "destino"):
            v[k] = _hit1(op.p.get(k), ctx.estado)
        return v


class Alinear(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "alinear", "Alinear", "alinear", "Alt+Shift+A"
    AYUDA = "Lleva un punto, plano o eje de los cuerpos sobre otro (las caras quedan enfrentadas)."
    CLASE_OP = OpAlinear
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        geom = {"vertice", "punto", "cara", "plano", "eje", "arista_lineal"}
        return [Seleccion("cuerpos", "Objetos", {"cuerpo"}, maximo=None), Seleccion("origen", "Desde", geom),
                Seleccion("destino", "Hasta", geom), Casilla("voltear", "Voltear"), Casilla("copiar", "Crear copia")]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos.")
        exigir(v, "origen", "Seleccioná la geometría de origen.")
        exigir(v, "destino", "Seleccioná la geometría de destino.")
        return self.crear_op(OpAlinear, v, ctx, cuerpos=_cuerpos(v), origen=ref1(v, "origen"),
                             destino=ref1(v, "destino"), voltear=v["voltear"], copiar=v["copiar"])

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado),
                    origen=_hit1(op.p["origen"], ctx.estado), destino=_hit1(op.p["destino"], ctx.estado))


class Combinar(Comando):
    CLAVE, TITULO, ICONO = "combinar", "Combinar", "combinar"
    AYUDA = "Une, corta o interseca cuerpos (operaciones booleanas)."
    CLASE_OP = OpCombinar

    def verificar(self, ctx):
        return None if len(ctx.estado.cuerpos) >= 2 else "Hacen falta al menos dos cuerpos para combinar."

    def campos(self, ctx):
        return [Seleccion("objetivo", "Cuerpo de destino", {"cuerpo"}),
                Seleccion("herramientas", "Cuerpos de herramienta", {"cuerpo"}, maximo=None),
                Opciones("operacion", "Operación", OPERACIONES_COMBINAR), Casilla("mantener", "Mantener herramientas")]

    def construir(self, v, ctx):
        exigir(v, "objetivo", "Seleccioná el cuerpo de destino.")
        exigir(v, "herramientas", "Seleccioná los cuerpos de herramienta.")
        obj, herr = _cuerpos(v, "objetivo")[0], _cuerpos(v, "herramientas")
        if obj in herr:
            raise ErrorComando("El cuerpo de destino no puede ser también herramienta.")
        return self.crear_op(OpCombinar, v, ctx, objetivo=obj, herramientas=herr, operacion=v["operacion"],
                             mantener=v["mantener"])

    def desde_op(self, op, ctx):
        return dict(op.p, objetivo=_hits_cuerpos(op.p["objetivo"], ctx.estado),
                    herramientas=_hits_cuerpos(op.p["herramientas"], ctx.estado))


class Quitar(Comando):
    CLAVE, TITULO, ICONO = "quitar", "Quitar", "quitar"
    AYUDA = "Saca cuerpos del diseño dejando el paso en el timeline."
    CLASE_OP = OpQuitar
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Objetos", {"cuerpo"}, maximo=None)]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos a quitar.")
        return self.crear_op(OpQuitar, v, ctx, cuerpos=_cuerpos(v))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado))


class Suprimir(Comando):
    """Suprimir (Supr) de Fusion: borra lo elegido. Caras → «Borrar caras» en el timeline. Un cuerpo
    cuyo paso creador no lo usa nadie más se borra junto con ese paso; si no, se quita con un paso
    «Quitar» (así el resto del timeline sigue funcionando)."""
    CLAVE, TITULO, ICONO, ATAJO = "suprimir", "Suprimir", "suprimir", "Del"
    AYUDA = "Borra cuerpos o caras elegidos."
    SIN_OP = True
    PREVIA = False

    def campos(self, ctx):
        return [Seleccion("objetos", "Objetos", {"cuerpo", "cara"}, maximo=None)]

    def construir(self, v, ctx):
        exigir(v, "objetos", "Seleccioná lo que querés borrar.")
        return None

    def aplicar(self, v, ctx):
        sel = exigir(v, "objetos", "Seleccioná lo que querés borrar.")
        doc, ventana = ctx.doc, ctx.ventana
        caras = [h["ref"] for h in sel if h["ref"]["tipo"] == "cara"]
        cuerpos = [h["ref"]["cuerpo"] for h in sel if h["ref"]["tipo"] == "cuerpo"]
        if caras:
            op = OpBorrarCaras(doc.nuevo_id(), _siguiente(ctx, "Borrar caras"), caras=caras)
            (ventana._agregar if ventana else doc.agregar)(op)
        quitar = []
        for cid in cuerpos:
            op_id = cid.split(".c")[0]
            hermanos = [c for c in doc.estado_final.cuerpos if c.split(".c")[0] == op_id]
            try:
                creador = doc.operacion(op_id)
            except ValueError:
                creador = None
            if creador is not None and len(hermanos) == 1 and not doc.dependientes(op_id):
                doc.eliminar(op_id)
            else:
                quitar.append(cid)
        if quitar:
            op = OpQuitar(doc.nuevo_id(), _siguiente(ctx, "Quitar"), cuerpos=quitar)
            (ventana._agregar if ventana else doc.agregar)(op)


def _siguiente(ctx, base):
    usados = {o.nombre for o in ctx.doc.operaciones}
    n = 1
    while f"{base}{n}" in usados:
        n += 1
    return f"{base}{n}"


# ---------------------------------------------------------------- propiedades (no son pasos del timeline)
class Aspecto(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "aspecto", "Aspecto", "aspecto", "A"
    AYUDA = "Cambia el color con que se ven los cuerpos (no cambia el material físico)."
    SIN_OP, PREVIA = True, False
    COLORES = {"acero": ("Acero - Satinado", (0.74, 0.76, 0.79)), "aluminio": ("Aluminio - Pulido", (0.85, 0.86, 0.88)),
               "negro": ("Plástico - Negro mate", (0.12, 0.12, 0.13)), "blanco": ("Plástico - Blanco", (0.95, 0.95, 0.95)),
               "rojo": ("Pintura - Rojo", (0.80, 0.15, 0.15)), "azul": ("Pintura - Azul", (0.15, 0.35, 0.80)),
               "verde": ("Pintura - Verde", (0.20, 0.60, 0.25)), "amarillo": ("Pintura - Amarillo", (0.95, 0.80, 0.15)),
               "naranja": ("Pintura - Naranja", (0.95, 0.50, 0.10)), "laton": ("Latón - Pulido", (0.80, 0.65, 0.30)),
               "cobre": ("Cobre", (0.78, 0.45, 0.28)), "madera": ("Madera - Pino", (0.85, 0.70, 0.48)),
               "vidrio": ("Vidrio", (0.70, 0.85, 0.85)), "goma": ("Goma - Negra", (0.18, 0.18, 0.18)),
               "ninguno": ("(quitar el aspecto)", None)}
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Aplicar a", {"cuerpo"}, maximo=None),
                Opciones("aspecto", "Aspecto", {k: t for k, (t, _) in self.COLORES.items()}, "rojo"),
                Texto("hex", "Color personalizado (#rrggbb)", "")]

    def construir(self, v, ctx):
        return None

    def aplicar(self, v, ctx):
        ids = _cuerpos(exigir(v, "cuerpos", "Seleccioná los cuerpos."))
        texto = (v.get("hex") or "").strip().lstrip("#")
        if texto:
            try:
                color = [int(texto[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            except ValueError as e:
                raise ErrorComando("El color tiene que tener el formato #rrggbb.") from e
        else:
            color = self.COLORES[v["aspecto"]][1]
        ctx.doc.set_propiedad(ids, "apariencia", list(color) if color else None)


class MaterialFisico(Comando):
    CLAVE, TITULO, ICONO = "material_fisico", "Material físico", "material_fisico"
    AYUDA = "Asigna el material (densidad para la masa y su aspecto) a los cuerpos."
    SIN_OP, PREVIA = True, False
    verificar = staticmethod(_con_cuerpos)

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Aplicar a", {"cuerpo"}, maximo=None),
                Opciones("material", "Material", {k: f"{k} ({m['densidad']:g} g/cm³)" for k, m in MATERIALES.items()},
                         "Acero")]

    def construir(self, v, ctx):
        return None

    def aplicar(self, v, ctx):
        ids = _cuerpos(exigir(v, "cuerpos", "Seleccioná los cuerpos."))
        ctx.doc.set_propiedad(ids, "material", v["material"])


registrar(PulsarTirar, Empalme, Chaflan, Vaciado, Desmoldeo, Escala, Combinar, CaraDesfase, ReemplazarCara,
          DividirCara, DividirCuerpo, DivisionSilueta, MoverCopiar, Alinear, Suprimir, Quitar, Aspecto, MaterialFisico)
