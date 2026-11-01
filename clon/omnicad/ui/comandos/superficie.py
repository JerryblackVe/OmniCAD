# -*- coding: utf-8 -*-
"""Comandos de la pestaña SUPERFICIE (y Engrosar, que también está en SÓLIDO › CREAR)."""
import numpy as np

from PySide6.QtWidgets import QAbstractItemView, QComboBox, QHeaderView, QTableWidget, QTableWidgetItem

from ...timeline.ops_superficie import (OpCoser, OpDescoser, OpDestrimar, OpEngrosar, OpExtenderSup,
                                        OpInvertirNormal, OpParche, OpRecortar, OpReglada, OpSupBarrido, OpSupBobina,
                                        OpSupDesfase, OpSupEmpalme, OpSupExtruir, OpSupPrimitiva, OpSupRevolucion,
                                        OpSupSolevacion, OpSupTuberia)
from ...timeline.parametros import ANGULO, ESCALAR
from ..comando import (Botones, Casilla, Comando, ErrorComando, Expresion, Info, Opciones, Personalizado, Seleccion, Texto,
                       exigir, hit_desde_ref, hits, hits_cuerpos as _hits_cuerpos, ref1, refs)
from . import registrar
from .comunes import DIRECCIONES_UI, OPCIONES_OPERACION, campo_objetivos, con_analisis, objetivos
from .crear import Bobina, Solevacion, Tuberia, _en_fila
from .primitivas import Caja, Cilindro, Esfera, Toroide

CURVAS = {"curva_boceto", "arista"}


def _h1(ref, estado):
    return [hit_desde_ref(ref, estado)] if ref else []


def _cuerpos(lista):
    return [h["ref"]["cuerpo"] for h in lista or [] if h["ref"].get("tipo") == "cuerpo"]


def _h_lista(lista, estado):
    return [hit_desde_ref(r, estado) for r in lista or [] if r]


class SupExtruir(Comando):
    CLAVE, TITULO, ICONO = "sup_extruir", "Extruir superficie", "sup_extruir"
    AYUDA = "Extruye curvas (abiertas o cerradas) o un texto de una línea y crea una superficie."
    CLASE_OP = OpSupExtruir

    def campos(self, ctx):
        dos = lambda v: v.get("lados") == "dos_lados"  # noqa: E731
        objeto = lambda v: v.get("extension") == "objeto"  # noqa: E731
        return [Seleccion("curvas", "Perfiles", CURVAS, maximo=None,
                          ayuda="Curvas de boceto o aristas. Un texto de una sola línea extruye todos sus trazos."),
                Opciones("inicio", "Inicio", {"plano": "Plano de perfil", "desfase": "Plano de desfase", "objeto": "Desde objeto"}),
                Expresion("desfase_inicio", "Desfase de inicio", "0 mm", visible_si=lambda v: v.get("inicio") == "desfase"),
                Seleccion("inicio_objeto", "Objeto de inicio", {"cara_plana", "plano"},
                          visible_si=lambda v: v.get("inicio") == "objeto"),
                Opciones("lados", "Dirección", DIRECCIONES_UI),
                Opciones("medida", "Medida", {"mitad": "Media longitud", "total": "Longitud total"},
                         visible_si=lambda v: v.get("lados") == "simetrica"),
                Opciones("extension", "Tipo de extensión", {"distancia": "Distancia", "objeto": "A objeto", "todo": "Todo"}),
                Expresion("distancia", "Distancia", "10 mm", visible_si=lambda v: v.get("extension") == "distancia"),
                Seleccion("hasta", "Objeto límite", {"cara", "plano", "cuerpo"}, visible_si=objeto),
                Expresion("desfase_hasta", "Desfase del límite", "0 mm", visible_si=objeto),
                Casilla("invertir", "Invertir dirección", visible_si=lambda v: v.get("extension") != "distancia"),
                Expresion("distancia2", "Distancia del lado 2", "10 mm", visible_si=dos),
                Expresion("conicidad", "Ángulo de conicidad", "0 deg", ANGULO, avanzado=True),
                Seleccion("direccion", "Eje de dirección", {"plano", "cara_plana", "eje", "arista_lineal"}, minimo=0,
                          ayuda="Sin selección: perpendicular al plano del boceto.")]

    def construir(self, v, ctx):
        exigir(v, "curvas", "Seleccioná las curvas.")
        ctx.evaluar(v["distancia"])
        if v.get("extension") == "objeto" and not v.get("hasta"):
            raise ErrorComando("Elegí el objeto hasta donde llega la extrusión.")
        if v.get("inicio") == "objeto" and not v.get("inicio_objeto"):
            raise ErrorComando("Elegí la cara plana o el plano donde empieza la extrusión.")
        for clave in ("desfase_inicio", "desfase_hasta", "distancia2"):
            ctx.evaluar(v.get(clave) or "0")
        lados = "simetrica" if v.get("simetrica") else v["lados"]      # `simetrica`: el campo de las recetas viejas
        params = {k: v[k] for k in ("distancia", "conicidad", "medida", "inicio", "desfase_inicio", "extension",
                                    "desfase_hasta", "distancia2", "invertir")}
        return self.crear_op(OpSupExtruir, v, ctx, curvas=refs(v, "curvas"), direccion=ref1(v, "direccion"),
                             simetrica=False, lados=lados, inicio_objeto=ref1(v, "inicio_objeto"),
                             hasta=ref1(v, "hasta"), **params)

    def desde_op(self, op, ctx):
        v = dict(op.p, curvas=hits(op.p["curvas"], ctx.estado), direccion=_h1(op.p["direccion"], ctx.estado),
                 inicio_objeto=_h1(op.p["inicio_objeto"], ctx.estado), hasta=_h1(op.p["hasta"], ctx.estado))
        if op.p.get("simetrica"):
            v.update(lados="simetrica", medida="total")
        return v


class SupRevolucion(Comando):
    CLAVE, TITULO, ICONO = "sup_revolucion", "Revolución de superficie", "sup_revolucion"
    AYUDA = "Gira curvas alrededor de un eje y crea una superficie."
    CLASE_OP = OpSupRevolucion

    def campos(self, ctx):
        angulo = lambda v: v.get("extension") == "angulo"  # noqa: E731
        return [Seleccion("curvas", "Perfil", CURVAS, maximo=None), Seleccion("eje", "Eje", {"eje"}),
                Opciones("extension", "Tipo de extensión", {"angulo": "Ángulo", "objeto": "A objeto", "completa": "Completo"}),
                Seleccion("hasta", "Objeto límite", {"vertice", "cara", "plano", "cuerpo"},
                          visible_si=lambda v: v.get("extension") == "objeto"),
                Opciones("lados", "Dirección", DIRECCIONES_UI, visible_si=angulo),
                Expresion("angulo", "Ángulo", "360 deg", ANGULO, visible_si=angulo,
                          etiqueta_si=lambda v: "Ángulo del lado 1" if v.get("lados") == "dos_lados" else "Ángulo"),
                Expresion("angulo2", "Ángulo del lado 2", "90 deg", ANGULO,
                          visible_si=lambda v: angulo(v) and v.get("lados") == "dos_lados"),
                Casilla("proyectar_eje", "Proyectar eje", avanzado=True,
                        ayuda="Lleva el eje al plano del perfil antes de girar (curvas de boceto). Desmarcado, el eje queda donde está.")]

    def construir(self, v, ctx):
        exigir(v, "curvas", "Seleccioná las curvas.")
        exigir(v, "eje", "Seleccioná el eje.")
        if v.get("extension") == "objeto" and not v.get("hasta"):
            raise ErrorComando("Elegí el objeto hasta donde gira el perfil.")
        ctx.evaluar(v["angulo"], ANGULO)
        ctx.evaluar(v.get("angulo2") or "0", ANGULO)
        return self.crear_op(OpSupRevolucion, v, ctx, curvas=refs(v, "curvas"), eje=ref1(v, "eje"),
                             hasta=ref1(v, "hasta"), **{k: v[k] for k in ("angulo", "angulo2", "extension", "lados",
                                                                          "proyectar_eje")})

    def desde_op(self, op, ctx):
        return dict(op.p, curvas=hits(op.p["curvas"], ctx.estado), eje=_h1(op.p["eje"], ctx.estado),
                    hasta=_h1(op.p["hasta"], ctx.estado))


@con_analisis
class SupBarrido(Comando):
    CLAVE, TITULO, ICONO = "sup_barrido", "Barrido de superficie", "sup_barrido"
    AYUDA = "Lleva un perfil abierto o cerrado a lo largo de una ruta."
    CLASE_OP = OpSupBarrido

    def campos(self, ctx):
        ruta = lambda v: v.get("tipo") == "ruta"  # noqa: E731
        carril = lambda v: v.get("tipo") == "ruta_carril"  # noqa: E731
        perpendicular = lambda v: ruta(v) and v.get("orientacion") == "perpendicular"  # noqa: E731
        return [Opciones("tipo", "Tipo", {"ruta": ("Ruta individual", "bar_ruta"), "ruta_carril": ("Ruta + Rail guía", "bar_carril"),
                                          "ruta_superficie": ("Trayectoria + Superficie guía", "bar_superficie")}),
                Seleccion("perfil", "Perfil", CURVAS | {"perfil", "cara_plana"}, maximo=None),
                Seleccion("ruta", "Ruta", CURVAS, maximo=None),
                Casilla("cadena", "Selección de cadena", True,
                        ayuda="Suma a cada arista o curva elegida las que le siguen tangentes."),
                Seleccion("carril", "Rail guía", CURVAS, maximo=None, visible_si=carril),
                Seleccion("superficie_guia", "Superficie guía", {"cara"}, maximo=None,
                          visible_si=lambda v: v.get("tipo") == "ruta_superficie"),
                Opciones("extension", "Extensión", {"perpendicular": "Perpendicular a la ruta", "completa": "Extensión completa"},
                         visible_si=carril),
                Expresion("distancia", "Fracción de la ruta", "1", ESCALAR,
                          ayuda="Fin del barrido sobre la ruta: fracción entre 0 y 1 (1 = el 100 % de la ruta)."),
                Expresion("distancia_carril", "Fracción del rail", "1", ESCALAR, ayuda="Fracción del rail guía que se usa, entre 0 y 1.",
                          visible_si=lambda v: carril(v) and v.get("extension") == "completa"),
                Opciones("escala_carril", "Escala del perfil", {"escalar": "Escalar", "estirar": "Estirar", "ninguna": "Ninguna"},
                         visible_si=carril, ayuda="Escalar: el perfil crece en las dos direcciones con la distancia entre la ruta y el "
                                                  "rail. Estirar: solo hacia el rail. Ninguna: el rail solo lo orienta."),
                Opciones("orientacion", "Orientación", {"perpendicular": "Perpendicular", "paralela": "Paralela"}, visible_si=ruta),
                Expresion("conicidad", "Ángulo de conicidad", "0 deg", ANGULO, visible_si=perpendicular),
                Expresion("torsion", "Ángulo de torsión", "0 deg", ANGULO, visible_si=perpendicular)]

    def construir(self, v, ctx):
        tipo = v.get("tipo")
        exigir(v, "perfil", "Seleccioná el perfil.")
        exigir(v, "ruta", "Seleccioná la ruta.")
        if tipo == "ruta_carril":
            exigir(v, "carril", "Seleccioná el rail guía.")
        elif tipo == "ruta_superficie":
            exigir(v, "superficie_guia", "Seleccioná la superficie guía.")
        ruta = tipo == "ruta"
        perpendicular = ruta and v["orientacion"] == "perpendicular"
        return self.crear_op(OpSupBarrido, v, ctx, perfil=refs(v, "perfil"), ruta=refs(v, "ruta"),
                             orientacion=v["orientacion"] if ruta else "perpendicular",
                             torsion=v["torsion"] if perpendicular else "0 deg",
                             conicidad=v["conicidad"] if perpendicular else "0 deg",
                             distancia=v["distancia"], cadena=bool(v.get("cadena")),
                             carril=refs(v, "carril") if tipo == "ruta_carril" else [],
                             superficie_guia=refs(v, "superficie_guia") if tipo == "ruta_superficie" else [],
                             distancia_carril=v["distancia_carril"] if tipo == "ruta_carril" else "1",
                             escala_carril=v["escala_carril"], extension=v["extension"])

    def desde_op(self, op, ctx):
        return dict(op.p, perfil=hits(op.p["perfil"], ctx.estado), ruta=hits(op.p["ruta"], ctx.estado),
                    carril=hits(op.p["carril"], ctx.estado), superficie_guia=hits(op.p["superficie_guia"], ctx.estado),
                    tipo="ruta_carril" if op.p["carril"] else "ruta_superficie" if op.p["superficie_guia"] else "ruta")


def _solo_cuerpo_nuevo(campos):
    """Las superficies siempre son un cuerpo nuevo (Fusion: New Body): sin Operación ni Objetos en el panel."""
    for c in campos:
        if c.clave in ("operacion", "objetivo", "objetivos"):
            c.visible_si = lambda v: False
    return campos


ALINEACION = {"libre": "Bordes libres", "alinear": "Alinear bordes", "superficie": "Alinear con superficie"}


@con_analisis
class SupSolevacion(Solevacion):
    """El panel de la solevación sólida (filas de perfiles con su condición, rieles o línea central), sin Operación. Suma
    lo que es de superficie: Punto tangente, alineación de bordes y la cara de Tangente, que sale sola del perfil."""
    CLAVE, TITULO, ICONO = "sup_solevacion", "Solevación de superficie", "sup_solevacion"
    AYUDA = "Crea una superficie que pasa por varias curvas (secciones) en orden."
    CLASE_OP = OpSupSolevacion

    def campos(self, ctx):
        campos = _solo_cuerpo_nuevo(super().campos(ctx))
        i = next(k for k, c in enumerate(campos) if c.clave == "guia")
        for lado in ("fin", "inicio"):
            campos.insert(i, Opciones(f"alineacion_{lado}", f"Alineación ({'primer' if lado == 'inicio' else 'último'} perfil)", ALINEACION,
                                      visible_si=lambda v, lado=lado: _en_fila(lado)(v) and v.get(f"condicion_{lado}") in ("tangente", "suave")))
        for c in campos:
            if c.clave in ("cara_inicio", "cara_fin"):
                c.ayuda = "Sin elegir: la cara de la que sale el perfil."
            elif c.clave in ("peso_inicio", "peso_fin"):
                lado = c.clave.removeprefix("peso_")
                c.visible_si = lambda v, antes=c.visible_si, lado=lado: antes(v) or (
                    _en_fila(lado)(v) and v.get(f"condicion_{lado}") == "punto_tangente")
        return campos

    def _celda(self, panel, i, n):
        """La celda de la solevación sólida, salvo en un punto del extremo: Aguda o Punto tangente."""
        extremo = "inicio" if i == 0 else "fin" if i == n - 1 else None
        if not extremo:
            return super()._celda(panel, i, n)
        punto = panel.valores["secciones"][i]["ref"]["tipo"] in ("vertice", "punto", "punto_boceto")
        actual = panel.valores.get(f"condicion_{extremo}")
        if actual not in ("libre", "punto_tangente") if punto else actual == "punto_tangente":
            panel.valores[f"condicion_{extremo}"] = "libre"      # era del perfil que ocupaba esta fila antes
        if not punto:
            return super()._celda(panel, i, n)
        w = QComboBox()
        w.addItem("Aguda", "libre")
        w.addItem("Tangente", "punto_tangente")            # Fusion: Point Tangent; la fila angosta corta el nombre largo
        w.setCurrentIndex(max(w.findData(panel.valores.get(f"condicion_{extremo}")), 0))
        w.currentIndexChanged.connect(lambda _=0: panel.set_valor(f"condicion_{extremo}", w.currentData()))
        return w

    @staticmethod
    def _condicion(v, lado):
        tipo = v.get(f"condicion_{lado}")
        if tipo == "direccion":
            return {"tipo": "direccion", "angulo": v[f"angulo_{lado}"], "peso": v[f"peso_{lado}"]}
        if tipo == "punto_tangente":
            return {"tipo": tipo, "angulo": "90 deg", "peso": v[f"peso_{lado}"]}
        if tipo in ("tangente", "suave"):
            return {"tipo": tipo, "angulo": "90 deg", "peso": v[f"peso_{lado}"], "cara": ref1(v, f"cara_{lado}"),
                    "alineacion": v.get(f"alineacion_{lado}") or "libre"}
        return None

    def crear_op(self, clase, v, ctx, **params):
        for k in ("operacion", "objetivos"):
            params.pop(k, None)
        return super().crear_op(OpSupSolevacion, v, ctx, condicion_exacta=True, **params)

    def desde_op(self, op, ctx):
        v = dict(super().desde_op(op, ctx), operacion="nuevo")
        for lado in ("inicio", "fin"):
            c = op.p.get(f"condicion_{lado}") or {}
            if c.get("tipo") == "punto_tangente":
                v[f"condicion_{lado}"] = "punto_tangente"
            v[f"alineacion_{lado}"] = c.get("alineacion", "libre")
        return v


def _lista_continuidades(texto, cuantas):
    """«G1, G0, G2» → ["G1", "G0", "G2"] (una por arista; «-» o las que faltan quedan vacías = la continuidad general)."""
    texto = str(texto or "").replace(";", ",")
    partes = [t.strip().upper() for t in texto.split(",")] if texto.strip() else []
    partes = ["" if t == "-" else t for t in partes]
    malas = [t for t in partes if t not in ("", "G0", "G1", "G2")]
    if malas:
        raise ErrorComando(f"La continuidad de cada arista es G0, G1 o G2; «{malas[0]}» no vale.")
    if len(partes) > cuantas:
        raise ErrorComando(f"Hay {len(partes)} continuidades y solo {cuantas} aristas elegidas.")
    return partes + [""] * (cuantas - len(partes))


@con_analisis
class Parche(Comando):
    CLAVE, TITULO, ICONO = "parche", "Parche", "parche"
    AYUDA = "Tapa un contorno cerrado de aristas o curvas con una superficie."
    CLASE_OP = OpParche

    def campos(self, ctx):
        return [Casilla("agrupar", "Agrupar aristas", True,
                        ayuda="Marcado: una sola continuidad para todo el contorno. Desmarcado: una por arista."),
                Seleccion("contorno", "Aristas de contorno", CURVAS, maximo=None),
                Opciones("continuidad", "Continuidad", {"G0": "Conexión (G0)", "G1": "Tangente (G1)",
                                                         "G2": "Curvatura (G2)"}),
                Texto("continuidades", "Continuidad por arista", "", visible_si=lambda v: not v.get("agrupar", True),
                      ayuda="Una por cada arista, en el orden elegido y separadas por coma: G0, G1 o G2 («-» o las que "
                            "falten usan la continuidad general)."),
                Seleccion("interior", "Rieles y puntos interiores", CURVAS | {"vertice", "punto"}, minimo=0,
                          maximo=None, ayuda="Curvas, aristas o puntos que guían la forma del parche."),
                Casilla("invertir", "Invertir normal", avanzado=True)]

    def construir(self, v, ctx):
        exigir(v, "contorno", "Seleccioná el contorno.")
        agrupar = bool(v.get("agrupar", True))
        continuidades = [] if agrupar else _lista_continuidades(v.get("continuidades"), len(v["contorno"]))
        return self.crear_op(OpParche, v, ctx, contorno=refs(v, "contorno"), continuidad=v["continuidad"],
                             agrupar=agrupar, continuidades=continuidades, interior=refs(v, "interior"),
                             invertir=bool(v.get("invertir")))

    def desde_op(self, op, ctx):
        return dict(op.p, contorno=hits(op.p["contorno"], ctx.estado), interior=_h_lista(op.p["interior"], ctx.estado),
                    continuidades=", ".join(c or "-" for c in op.p["continuidades"]))


@con_analisis
class Reglada(Comando):
    CLAVE, TITULO, ICONO = "reglada", "Superficie reglada", "reglada"
    AYUDA = "Crea superficies rectas que salen de aristas (normal, tangente o en una dirección)."
    CLASE_OP = OpReglada

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas", CURVAS, maximo=None),
                Opciones("tipo", "Tipo", {"normal": "Normal", "tangente": "Tangente", "direccion": "Dirección"}),
                Seleccion("direccion", "Dirección", {"plano", "cara_plana", "eje", "arista_lineal"},
                          visible_si=lambda v: v.get("tipo") == "direccion"),
                Expresion("distancia", "Distancia", "10 mm"), Expresion("angulo", "Ángulo", "0 deg", ANGULO),
                Casilla("ingletear", "Esquinas ingleteadas", avanzado=True,
                        ayuda="Corta en ángulo vivo las esquinas entre aristas (rectas, arcos o curvas); desmarcado, cada arista da su cara."),
                Casilla("alternas", "Caras alternas", avanzado=True,
                        ayuda="Si una arista comparte dos caras, usa la otra para la dirección y el ángulo.")]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná las aristas.")
        return self.crear_op(OpReglada, v, ctx, aristas=refs(v, "aristas"), tipo=v["tipo"],
                             direccion=ref1(v, "direccion"), distancia=v["distancia"], angulo=v["angulo"],
                             ingletear=bool(v.get("ingletear")), alternas=bool(v.get("alternas")))

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
                                                            "interiores": "Aristas interiores", "todos": "Todas",
                                                            "manual": "Manual"}),
                Seleccion("aristas", "Aristas a destrimar", {"arista"}, maximo=None,
                          visible_si=lambda v: v.get("contornos") == "manual",
                          ayuda="Un agujero se tapa; el borde exterior vuelve al límite natural."),
                Expresion("extension", "Extender", "0 mm", avanzado=True,
                          ayuda="Estira los bordes exteriores de la superficie destrimada esta distancia."),
                Casilla("mantener_copia", "Mantener copia", avanzado=True,
                        ayuda="Deja la superficie original como cuerpo aparte.")]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras.")
        if v["contornos"] == "manual":
            exigir(v, "aristas", "En el modo manual, seleccioná las aristas a destrimar.")
        ctx.evaluar(v.get("extension") or "0 mm")
        return self.crear_op(OpDestrimar, v, ctx, caras=refs(v, "caras"), contornos=v["contornos"],
                             aristas=refs(v, "aristas") if v["contornos"] == "manual" else [],
                             extension=v.get("extension") or "0 mm", mantener_copia=bool(v.get("mantener_copia")))

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado), aristas=_h_lista(op.p["aristas"], ctx.estado))


@con_analisis
class Extender(Comando):
    CLAVE, TITULO, ICONO = "extender_sup", "Extender", "extender_sup"
    AYUDA = "Alarga los bordes libres de una superficie."
    CLASE_OP = OpExtenderSup

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas", {"arista"}, maximo=None), Expresion("distancia", "Distancia", "5 mm"),
                Opciones("tipo", "Tipo de extensión", {"natural": "Natural", "tangente": "Tangente",
                                                       "perpendicular": "Perpendicular"}),
                Opciones("alineacion", "Alineación de bordes", {"alinear": "Alinear bordes (G1)", "libre": "Bordes libres (G0)"},
                         visible_si=lambda v: v.get("tipo") == "natural",
                         ayuda="Alinear: la extensión sigue los lados de la cara. Libres: además extiende caras que no son "
                               "rectangulares (las planas con una franja tangente, las curvas sobre su superficie).")]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná los bordes.")
        return self.crear_op(OpExtenderSup, v, ctx, aristas=refs(v, "aristas"), distancia=v["distancia"], tipo=v["tipo"],
                             alineacion=v["alineacion"])

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado))


class Coser(Comando):
    """Stitch: el panel dice cuántos bordes quedan libres y cuántas aristas se cosen; en la vista, las que entran en la
    tolerancia van en verde y las libres en rojo. La tabla «Aristas sin coser» recorre los bordes libres: la fila elegida
    se ve más gruesa y la vista se acerca a ella."""
    CLAVE, TITULO, ICONO = "coser", "Coser", "coser"
    AYUDA = "Une superficies por sus bordes; si quedan cerradas, el resultado es un sólido."
    CLASE_OP = OpCoser
    VERDE, ROJO, ELEGIDO = (0.15, 0.8, 0.3), (0.9, 0.2, 0.15), (1.0, 0.75, 0.0)
    _t, _panel, _datos, _fila, _clave = None, None, None, -1, None

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Superficies", {"cuerpo"}, maximo=None),
                Expresion("tolerancia", "Tolerancia", "0.01 mm"),
                Info("resultado", "Bordes libres", self._libres),
                Personalizado("tabla_bordes", "Aristas sin coser", self._tabla, ancho_completo=True,
                              ayuda="Recorré las filas para ver cada borde libre en la vista; el hueco es la tolerancia "
                                    "que haría falta para cerrarlo.")]

    def _tabla(self, panel):
        self._panel = panel
        t = QTableWidget(0, 3)
        t.setHorizontalHeaderLabels(["N.º", "Largo", "Hueco"])
        t.verticalHeader().hide()
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setMaximumHeight(150)
        t.currentCellChanged.connect(lambda fila, *_: self._elegir_fila(fila))
        self._t = t
        return t

    def _elegir_fila(self, fila):
        """La fila elegida se ve en la vista: más gruesa y con la cámara cerca (como Unstitched Edges de Fusion)."""
        self._fila = fila
        panel = self._panel
        panel._previa_vista(panel.ultima_op)
        if self._datos and 0 <= fila < len(self._datos["libres"]):
            b = self._datos["libres"][fila]
            margen = max(b["largo"], (b["hueco"] or 0.0) * 4, 1.0) * 0.75
            panel.visor.encuadrar(np.vstack([b["polilinea"] - margen, b["polilinea"] + margen]))

    def _llenar_tabla(self, datos):
        t, self._datos, self._fila = self._t, datos, -1
        if t is None:
            return
        t.blockSignals(True)
        libres = datos["libres"] if datos else []
        t.setRowCount(len(libres))
        for i, b in enumerate(libres):
            hueco = "—" if b["hueco"] is None else f"{b['hueco']:.3f} mm"
            for j, texto in enumerate((str(i + 1), f"{b['largo']:.2f} mm", hueco)):
                t.setItem(i, j, QTableWidgetItem(texto))
        t.setCurrentCell(-1, -1)
        t.blockSignals(False)

    def _bordes(self, v, ctx):
        """Los bordes de la costura de prueba (sobre copias), calculada una vez por selección y tolerancia."""
        from ...nucleo import superficies as sf
        ids = _cuerpos(v.get("cuerpos"))
        tolerancia = ctx.evaluar(v.get("tolerancia") or "0.01 mm")
        clave = (tuple((i, id(ctx.estado.cuerpos[i].forma)) for i in ids), tolerancia)
        if self._clave != clave:
            self._clave = clave
            self._llenar_tabla(sf.bordes_de_costura([ctx.estado.cuerpos[i].forma for i in ids], tolerancia))
        return self._datos

    def _libres(self, v, ctx):
        """Cuántos bordes quedarían abiertos y cuántas aristas se cosen con esta tolerancia."""
        ids = _cuerpos(v.get("cuerpos"))
        if len(ids) < 1 or any(i not in ctx.estado.cuerpos for i in ids):
            self._clave = None
            self._llenar_tabla(None)
            return "Elegí las superficies."
        try:
            r = self._bordes(v, ctx)
        except Exception:  # noqa: BLE001 — tolerancia mal escrita o forma rara: lo dice el botón Aceptar, no este texto
            self._clave = None
            self._llenar_tabla(None)
            return ""
        cosidas = f" · {r['aristas_cosidas']} {'arista se cose' if r['aristas_cosidas'] == 1 else 'aristas se cosen'}"
        if r["es_solido"]:
            return "Ninguno: se cierra un sólido." + cosidas
        n = r["total_libres"]
        return f"{n} {'borde libre' if n == 1 else 'bordes libres'}{cosidas}: el resultado sigue siendo una superficie."

    def previa_vista(self, ctx, v, op):
        from ..visor3d import _segmentos
        r = self._datos
        if not r:
            return None
        libres = [b["polilinea"] for i, b in enumerate(r["libres"]) if i != self._fila]
        prims = [("lineas", _segmentos(r["cosidas"]), self.VERDE, 3.0), ("lineas", _segmentos(libres), self.ROJO, 3.0)]
        if 0 <= self._fila < len(r["libres"]):
            prims.append(("lineas", _segmentos([r["libres"][self._fila]["polilinea"]]), self.ELEGIDO, 6.0))
        return [p for p in prims if len(p[1])]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná las superficies.")
        return self.crear_op(OpCoser, v, ctx, cuerpos=_cuerpos(v["cuerpos"]), tolerancia=v["tolerancia"])

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado))


class Descoser(Comando):
    CLAVE, TITULO, ICONO = "descoser", "Descoser", "descoser"
    AYUDA = "Separa las caras de un cuerpo en superficies sueltas: todas, o solo las caras elegidas."
    CLASE_OP = OpDescoser

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, minimo=0, maximo=None,
                          ayuda="Cada cara del cuerpo pasa a ser una superficie suelta."),
                Seleccion("caras", "Caras", {"cara"}, minimo=0, maximo=None,
                          ayuda="Solo estas caras se separan; el resto del cuerpo queda cosido.")]

    def construir(self, v, ctx):
        if not v.get("cuerpos") and not v.get("caras"):
            raise ErrorComando("Seleccioná los cuerpos o las caras.")
        return self.crear_op(OpDescoser, v, ctx, cuerpos=_cuerpos(v.get("cuerpos")), caras=refs(v, "caras"))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado), caras=_h_lista(op.p["caras"], ctx.estado))


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
        return [Seleccion("caras", "Caras/cuerpos", {"cara", "cuerpo"}, maximo=None),
                Casilla("cadena", "Selección de cadena", True),
                Expresion("espesor", "Grosor", "2 mm"),
                Opciones("direccion", "Dirección", {"un_lado": ("Un lado", "dir_un_lado"), "simetrica": ("Simétrico", "dir_simetrica")}),
                Botones("tipo", "Tipo de engrosado",
                        {"agudo": ("Engrosado agudo", "eng_agudo"), "redondeado": ("Engrosado redondeado", "eng_redondo")}),
                Opciones("operacion", "Operación", OPCIONES_OPERACION, "nuevo"), campo_objetivos()]

    def construir(self, v, ctx):
        exigir(v, "caras", "Seleccioná las caras.")
        ctx.evaluar(v["espesor"])
        return self.crear_op(OpEngrosar, v, ctx, caras=refs(v, "caras"), espesor=v["espesor"],
                             direccion=v["direccion"], tipo=v["tipo"], operacion=v["operacion"],
                             objetivos=objetivos(v), cadena=bool(v.get("cadena")))

    def desde_op(self, op, ctx):
        return dict(op.p, caras=hits(op.p["caras"], ctx.estado),
                    objetivos=_hits_cuerpos(op.p.get("objetivos") or [], ctx.estado))


class SupEmpalme(Comando):
    CLAVE, TITULO, ICONO = "sup_empalme", "Empalme de superficie", "sup_empalme"
    AYUDA = "Redondea o bisela aristas entre superficies."
    CLASE_OP = OpSupEmpalme
    TITULOS_MODO = ("tipo", {"empalme": ("Empalme de superficie", "sup_empalme"),
                             "chaflan": ("Chaflán de superficie", "chaflan_3d")})

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas", {"arista"}, maximo=None),
                Opciones("tipo", "Tipo", {"empalme": "Empalme", "chaflan": "Chaflán"}),
                Expresion("medida", "Radio / distancia", "1 mm",
                          etiqueta_si=lambda v: "Distancia" if v.get("tipo") == "chaflan" else "Radio")]

    def construir(self, v, ctx):
        exigir(v, "aristas", "Seleccioná las aristas.")
        return self.crear_op(OpSupEmpalme, v, ctx, aristas=refs(v, "aristas"), tipo=v["tipo"], medida=v["medida"])

    def desde_op(self, op, ctx):
        return dict(op.p, aristas=hits(op.p["aristas"], ctx.estado))


class _PrimitivaSup:
    """Primitiva de superficie: el panel de la primitiva sólida, sin Operación, y su paso de superficie. Fusion las deja
    solo en modelado directo; acá van en el timeline."""

    def campos(self, ctx):
        return _solo_cuerpo_nuevo(super().campos(ctx))

    def crear_op(self, clase, v, ctx, **params):
        params["operacion"] = "nuevo"
        return super().crear_op(self.CLASE_OP, v, ctx, **params)


class SupCaja(_PrimitivaSup, Caja):
    CLAVE, TITULO, ICONO, CLASE_OP = "sup_caja", "Caja de superficie", "sup_caja", OpSupPrimitiva
    AYUDA = "Superficie con forma de caja: clic en un plano o una cara para ubicarla, ancho, largo y alto."


class SupCilindro(_PrimitivaSup, Cilindro):
    CLAVE, TITULO, ICONO, CLASE_OP = "sup_cilindro", "Cilindro de superficie", "sup_cilindro", OpSupPrimitiva
    AYUDA = "Superficie con forma de cilindro: clic en un plano o una cara para el centro de la base, diámetro y altura."


class SupEsfera(_PrimitivaSup, Esfera):
    CLAVE, TITULO, ICONO, CLASE_OP = "sup_esfera", "Esfera de superficie", "sup_esfera", OpSupPrimitiva
    AYUDA = "Superficie con forma de esfera: clic en un plano, una cara o un punto para el centro y diámetro."


class SupToroide(_PrimitivaSup, Toroide):
    CLAVE, TITULO, ICONO, CLASE_OP = "sup_toroide", "Toroide de superficie", "sup_toroide", OpSupPrimitiva
    AYUDA = "Superficie con forma de toroide: clic en un plano o una cara para el centro, diámetro interior y del tubo."


class SupBobina(_PrimitivaSup, Bobina):
    CLAVE, TITULO, ICONO, CLASE_OP = "sup_bobina", "Bobina de superficie", "sup_bobina", OpSupBobina
    AYUDA = "Superficie con forma de resorte, hélice o espiral plana."


class SupTuberia(_PrimitivaSup, Tuberia):
    CLAVE, TITULO, ICONO, CLASE_OP = "sup_tuberia", "Tubería de superficie", "sup_tuberia", OpSupTuberia
    AYUDA = "Superficie con forma de caño de sección circular, cuadrada o triangular a lo largo de una ruta."


registrar(SupExtruir, SupRevolucion, SupBarrido, SupSolevacion, Parche, Reglada, SupDesfase, Recortar, Destrimar,
          Extender, Coser, Descoser, InvertirNormal, Engrosar, SupEmpalme, SupCaja, SupCilindro, SupEsfera, SupToroide,
          SupBobina, SupTuberia)
