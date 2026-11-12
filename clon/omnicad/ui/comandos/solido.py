# -*- coding: utf-8 -*-
"""Comandos de SÓLIDO › CREAR con diálogo al estilo Fusion: Extruir y Revolución."""
import json
import math

import numpy as np

from ...nucleo import geometria as geo
from ...timeline.operaciones import OpExtrusion, OpRevolucion, espesor_plastico
from ...timeline.parametros import ANGULO, LONGITUD
from ..comando import (CARAS_PESADAS, Botones, Casilla, Comando, ErrorComando, Expresion, Opciones, Seleccion, exigir,
                       hit_desde_ref, hits, ref1)
from . import registrar
from .comunes import (DIRECCIONES_UI, campo_objetivos, campo_operacion, evaluar_o_cero as _evaluar, objetivos,
                      objetivos_desde_op, perfiles_a_params, perfiles_desde_op)


EXTENSIONES = {"distancia": ("Distancia", "ext_distancia"), "objeto": ("Al objeto", "ext_objeto"),
               "todo": ("Todo", "ext_todo")}


def _otro_plano(v, hit, ctx):
    """B-338, como Fusion («one or more coplanar … planar faces»): con algo ya elegido, una cara de otro plano no se
    suma a los perfiles; pasa a ser el «Hasta objeto»."""
    from .. import manipuladores as mp
    firma = hit["ref"].get("firma") or {}
    base = mp.base_perfiles(v.get("perfiles"), ctx.estado) if hit["ref"].get("tipo") == "cara" else None
    if base is None or "normal" not in firma:
        return None
    plano = base[1]
    n = mp.unitario(plano.normal)
    if np.linalg.norm(np.cross(n, firma["normal"])) < 1e-4 and abs((np.asarray(firma["centro"]) - plano.origen) @ n) < 1e-4:
        return None
    return "hasta", {"extension": "objeto"}


def _otro_plano_revolucion(v, hit, ctx):
    """B-339, como Fusion («a coplanar sketch profile or face»): lo de otro plano no se suma a «Perfil». Una cara de otro
    plano pasa a ser el «Objeto límite» (como en Extruir, B-338); un perfil de otro plano reemplaza a los elegidos (los
    coplanares no se mezclan con él)."""
    from .. import manipuladores as mp
    tipo = hit["ref"].get("tipo")
    base = mp.base_perfiles(v.get("perfiles"), ctx.estado) if tipo in ("cara", "perfil") else None
    entidad = mp.entidad(hit, ctx.estado) if base is not None else None
    if entidad is None or entidad.plano is None:
        return None
    plano, n = base[1], mp.unitario(base[1].normal)
    if (np.linalg.norm(np.cross(n, mp.unitario(entidad.plano.normal))) < 1e-4
            and abs((np.asarray(entidad.plano.origen) - plano.origen) @ n) < 1e-4):
        return None
    return ("hasta", {"extension": "objeto"}) if tipo == "cara" else ("perfiles", {})


_RADIOS_POR_CARA = []     # (cara, (adentro, afuera)) de los perfiles elegidos ahora


def _radios_conicidad(formas):
    """(adentro, afuera) de los perfiles, que frenan las asas de la conicidad (B-343); sin tope para lo que no se puede
    medir (curvas sueltas de la extrusión delgada). Se guarda por cara: las asas se rearman en cada cuadro del arrastre y
    en cada clic que suma un perfil, y así solo se mide el perfil nuevo (B-361)."""
    from ...nucleo.solidos_crear import radios_conicidad
    adentro = afuera = math.inf
    vistos = []
    for forma in formas:
        radios = next((r for cara, r in _RADIOS_POR_CARA if cara.IsSame(forma)), None)
        if radios is None:
            try:
                radios = radios_conicidad([forma])
            except Exception:  # noqa: BLE001 — una curva o un perfil raro: sin tope
                radios = (math.inf, math.inf)
        vistos.append((forma, radios))
        adentro, afuera = min(adentro, radios[0]), min(afuera, radios[1])
    _RADIOS_POR_CARA[:] = vistos
    return adentro, afuera


def _distancia_maxima(radios, conicidad):
    """Distancia a la que la conicidad cierra el perfil (Fusion frena ahí la flecha); None si no hay tope."""
    r = radios[0] if conicidad < 0 else radios[1]
    if abs(conicidad) < 1e-9 or math.isinf(r):
        return None
    return r / math.tan(math.radians(abs(conicidad)))


def _angulos(radios, distancia):
    """(mínimo, máximo) del asa de conicidad: ±89° o el ángulo que cierra el perfil a esa distancia."""
    d = abs(distancia)
    if d < 1e-9:
        return {"minimo": -89.0, "maximo": 89.0}
    return {"minimo": max(-89.0, -math.degrees(math.atan(radios[0] / d))),
            "maximo": min(89.0, math.degrees(math.atan(radios[1] / d)))}


class Extruir(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "extruir", "Extruir", "extruir", "E"
    AYUDA = "Agrega profundidad a perfiles de boceto o caras planas: cuerpo nuevo, unir, cortar o intersecar."
    CLASE_OP = OpExtrusion
    TITULOS_MODO = ("tipo", {"solida": ("Extruir", "extruir"), "delgada": ("Extrusión delgada", "extruir")})
    _herramienta_previa = None      # (estado, índice, receta del paso) → formas de `_formas_herramienta` (P-99)

    def verificar(self, ctx):
        if not ctx.estado.bocetos and not ctx.estado.cuerpos:
            return "Primero creá un boceto con un contorno cerrado (o elegí una cara plana de un cuerpo)."
        return None

    def campos(self, ctx):
        dos = lambda v: v.get("direccion") == "dos_lados"  # noqa: E731
        return [
            Botones("tipo", "Tipo", {"solida": ("Extruir", "extruir"), "delgada": ("Extrusión delgada", "ext_delgada")}),
            Seleccion("perfiles", "Perfiles", {"perfil", "cara_plana", "curva_boceto"}, maximo=None,
                      ayuda="Perfiles cerrados o caras planas; en la extrusión delgada también curvas abiertas.",
                      # B-265: en la sólida un clic sobre el borde elige el perfil, no la curva (Fusion: Extrude reference)
                      filtros_si=lambda v: {"perfil", "cara_plana"} | ({"curva_boceto"} if v.get("tipo") == "delgada" else set()),
                      desvio=_otro_plano),
            Opciones("inicio", "Inicio", {"plano": ("Plano de perfil", "ini_plano"), "desfase": ("Desfase", "ini_desfase"),
                                          "objeto": ("Objeto", "ini_objeto")}),
            Expresion("desfase_inicio", "Desfase de inicio", "0 mm", visible_si=lambda v: v.get("inicio") in ("desfase", "objeto")),
            Seleccion("inicio_objeto", "Objeto de inicio", {"cara_plana", "plano"},
                      visible_si=lambda v: v.get("inicio") == "objeto"),
            Opciones("direccion", "Dirección", DIRECCIONES_UI),
            Opciones("medida", "Medida", {"mitad": "Media longitud", "total": "Longitud total"}, defecto="total",
                     visible_si=lambda v: v.get("direccion") == "simetrica"),
            Opciones("extension", "Tipo de extensión", EXTENSIONES),
            Expresion("distancia", "Distancia", "0 mm", visible_si=lambda v: v.get("extension") == "distancia"),
            Seleccion("hasta", "Objeto límite", {"cara", "plano", "cuerpo"}, visible_si=lambda v: v.get("extension") == "objeto"),
            Opciones("hasta_modo", "Extender", {"cara": "Hasta la cara seleccionada", "cuerpo": "Hasta el cuerpo",
                                                "a_traves": "A través del cuerpo"},
                     visible_si=lambda v: v.get("extension") == "objeto"),
            Expresion("desfase_hasta", "Desfase del límite", "0 mm", visible_si=lambda v: v.get("extension") == "objeto"),
            Casilla("invertir", "Invertir dirección"),
            Opciones("extension2", "Tipo de extensión del lado 2", EXTENSIONES, visible_si=dos),
            Expresion("distancia2", "Distancia del lado 2", "0 mm",
                      visible_si=lambda v: dos(v) and v.get("extension2") == "distancia"),
            Seleccion("hasta2", "Objeto límite del lado 2", {"cara", "plano", "cuerpo"},
                      visible_si=lambda v: dos(v) and v.get("extension2") == "objeto"),
            Expresion("conicidad", "Ángulo de conicidad", "0 deg", ANGULO, avanzado=True),
            Expresion("conicidad2", "Conicidad del lado 2", "0 deg", ANGULO, visible_si=dos, avanzado=True),
            Expresion("espesor", "Grosor de pared", espesor_plastico(ctx.estado),
                      visible_si=lambda v: v.get("tipo") == "delgada"),
            Opciones("ubicacion", "Ubicación de pared", {"lado1": "Lado 1", "lado2": "Lado 2", "centro": "Centro"},
                     visible_si=lambda v: v.get("tipo") == "delgada"),
            campo_operacion(),
            campo_objetivos(),
        ]

    def construir(self, v, ctx):
        curvas = [h["ref"] for h in v.get("perfiles") or [] if h["ref"]["tipo"] == "curva_boceto"]
        resto = [h for h in v.get("perfiles") or [] if h["ref"]["tipo"] != "curva_boceto"]
        if curvas and v.get("tipo") != "delgada":
            raise ErrorComando("Las curvas abiertas solo se extruyen con «Extrusión delgada».")
        boceto, perfiles, caras = perfiles_a_params(resto) if resto or not curvas else ("", [], [])
        for clave, tipo in (("distancia", None), ("desfase_inicio", None), ("conicidad", ANGULO)):
            ctx.evaluar(v.get(clave) or "0", tipo or LONGITUD)
        if v.get("extension") == "distancia" and ctx.evaluar(v.get("distancia") or "0") == 0:
            raise ErrorComando("La distancia de extrusión no puede ser cero: arrastrá la flecha o escribí una distancia.")
        if (v.get("direccion") == "dos_lados" and v.get("extension2") == "distancia"
                and ctx.evaluar(v.get("distancia2") or "0") == 0):
            raise ErrorComando("La distancia del lado 2 no puede ser cero: arrastrá su flecha o escribí una distancia.")
        if v.get("extension") == "objeto" and not v.get("hasta"):
            raise ErrorComando("Elegí el objeto hasta donde llega la extrusión.")
        if v.get("direccion") == "dos_lados" and v.get("extension2") == "objeto" and not v.get("hasta2"):
            raise ErrorComando("Elegí el objeto hasta donde llega el lado 2 de la extrusión.")
        params = {k: v.get(k) for k in ("tipo", "inicio", "desfase_inicio", "direccion", "medida", "extension",
                                         "distancia", "invertir", "conicidad", "distancia2", "conicidad2", "espesor",
                                         "ubicacion", "operacion", "hasta_modo", "desfase_hasta", "extension2")}
        params.update(boceto=boceto, perfiles=perfiles, caras=caras, curvas=curvas, objetivos=objetivos(v),
                      objetivo="", inicio_objeto=ref1(v, "inicio_objeto"), hasta=ref1(v, "hasta"),
                      hasta2=ref1(v, "hasta2"), simetrica=False)
        return self.crear_op(OpExtrusion, v, ctx, **params)

    def manipuladores(self, ctx, v):
        """Flecha de distancia desde el centro del perfil a lo largo de la normal (la del lado 2 en «Dos
        lados»), el asa de la conicidad en el borde del perfil y, como Fusion, la flecha del desfase de
        inicio sobre el borde (solo con Inicio=Desfase) y la conicidad del lado 2 (solo en «Dos lados»)."""
        from .. import manipuladores as mp
        if v.get("extension") != "distancia":
            return []
        base = mp.base_perfiles(v.get("perfiles"), ctx.estado)
        if base is None:
            return []
        centro, plano, formas = base
        n = mp.unitario(plano.normal) * (-1.0 if v.get("invertir") else 1.0)
        lateral = mp.unitario(plano.u)
        borde = mp.punto_borde(formas, centro, lateral)
        antes = [mp.Flecha("desfase_inicio", borde, n)] if v.get("inicio") == "desfase" else []
        if v.get("inicio") == "desfase":
            centro = centro + n * _evaluar(ctx, v.get("desfase_inicio"))
        borde = borde + n * float((centro - borde) @ n)          # a la altura del inicio (desfase)
        direccion = v.get("direccion")
        if direccion == "simetrica":
            return antes + [mp.Flecha("distancia", centro, n, factor=1.0 if v.get("medida") != "total" else 0.5,
                                       minimo=0.0)]
        d = _evaluar(ctx, v.get("distancia"))
        radios = _radios_conicidad(formas)
        if direccion != "dos_lados":
            t = n * (-1.0 if d < 0 else 1.0)
            dmax = _distancia_maxima(radios, _evaluar(ctx, v.get("conicidad"), ANGULO))
            menos = None if dmax is None else -dmax
            return antes + [mp.Flecha("distancia", centro, n, minimo=menos, maximo=dmax, estricto=True),
                            mp.Angulo("conicidad", borde, np.cross(t, lateral), t, **_angulos(radios, d),
                                      caja="arrastre", estricto=True)]

        def lado(clave, valor, sentido, conicidad):
            # B-205: en «Dos lados» cada número es una magnitud de su lado; la flecha queda a |valor| de ese lado
            # y no cruza el cero (con un valor negativo, el eje se da vuelta y el tope pasa a ser el máximo)
            dmax = _distancia_maxima(radios, _evaluar(ctx, v.get(conicidad), ANGULO))
            if valor < 0:
                return mp.Flecha(clave, centro, -sentido, minimo=None if dmax is None else -dmax, maximo=0.0,
                                 estricto=True)
            return mp.Flecha(clave, centro, sentido, minimo=0.0, maximo=dmax, estricto=True)
        d2 = _evaluar(ctx, v.get("distancia2"))
        flechas = [lado("distancia", d, n, "conicidad")]
        if v.get("extension2", "distancia") == "distancia":
            flechas.append(lado("distancia2", d2, -n, "conicidad2"))
        return antes + flechas + [
            mp.Angulo(clave, borde, np.cross(t, lateral), t, **_angulos(radios, dist), caja="arrastre",
                      estricto=True)
            for clave, t, dist in (("conicidad", n, d), ("conicidad2", -n, d2))]

    @staticmethod
    def _herramienta(op):
        """La misma extrusión como cuerpo nuevo: el volumen que corta."""
        import copy
        herramienta = copy.copy(op)
        herramienta.p = dict(op.p, operacion="nuevo", objetivos=[])
        return herramienta

    def _formas_herramienta(self, ctx, op, en_vivo=False):
        # P-99: el rojo de «Cortar» y el choque con los sólidos piden la misma herramienta en el mismo clic
        clave = ctx.estado, ctx.indice, json.dumps(op.a_dict())
        if self._herramienta_previa is None or self._herramienta_previa[0] != clave:
            with geo.en_serie():         # B-293: previa dentro de la ventana
                estado, _avisos = ctx.doc.previsualizar(self._herramienta(op), ctx.indice, en_vivo=en_vivo)
            self._herramienta_previa = clave, [c.forma for k, c in estado.cuerpos.items() if k not in ctx.estado.cuerpos]
        return self._herramienta_previa[1]

    def previa_vista(self, ctx, v, op):
        """Con «Cortar», Fusion muestra en ROJO el volumen de la extrusión mientras el diálogo está abierto."""
        if op.p.get("operacion") != "cortar":
            return None
        from .. import manipuladores as mp
        return mp.herramientas_rojas(self._formas_herramienta(ctx, op))

    def preparar_panel(self, panel):
        self._fija = panel.ctx.op is not None    # un paso reabierto no cambia solo de operación
        self._antes_auto = None                  # la operación que había antes de pasar sola a Cortar o Unir
        self._ajustando = False
        self._cajas = {}                         # id de cuerpo → caja envolvente: el estado no cambia con el panel abierto
        self._hijo, self._op_hijo = None, None
        self._herramienta_previa = None
        self._t_hijo = None

    def al_cambiar(self, panel, clave):
        if clave == "operacion" and not self._ajustando:
            self._fija = True                    # la eligió la persona: queda hasta cerrar el panel
            self._cancelar_hijo()

    def al_cerrar(self, ctx):
        self._cancelar_hijo()

    def previa_lista(self, panel, estado):
        """Como Fusion: si la persona no tocó Operación, la extrusión que se mete con volumen en un sólido visible pasa
        a Cortar; la que sale de una cara de un sólido visible sin meterse, a Unir (B-338: rellenar un hueco); si deja
        de hacerlo, vuelve a lo que estaba. Primero las cajas envolventes (con la flecha agarrada,
        sin tocar el kernel); con un cuerpo pesado, el común se calcula en un proceso aparte."""
        op = panel.ultima_op
        if self._fija or op is None:
            return
        ctx = panel.ctx
        cajas, formas = getattr(estado, "_cajas_previa", None), None
        if cajas:
            cajas = list(cajas.values())
        else:   # P-99: la herramienta se extruye una vez por clic, y con «Nuevo» la previa exacta ya es la herramienta
            exacta = op.p.get("operacion") == "nuevo" and not hasattr(estado, "_mallas_previa")
            formas = ([c.forma for k, c in estado.cuerpos.items() if k not in ctx.estado.cuerpos] if exacta
                      else self._formas_herramienta(ctx, op, True))
            cajas = [geo.caja_envolvente(f) for f in formas]
        solidos = [c for c in self._visibles(ctx) if any(geo.cajas_solapan(self._caja(c), k) for k in cajas)]
        if any(len(geo.caras(c.forma)) >= CARAS_PESADAS for c in solidos):
            self._pedir_al_hijo(panel, op, solidos)
            return
        self._cancelar_hijo()
        if formas is None:
            formas = self._formas_herramienta(ctx, op, True) if solidos else []
        self._ajustar(panel, self._auto(ctx, op, any(geo.solapan(f, c.forma) for f in formas for c in solidos)))

    def _auto(self, ctx, op, solapa):
        """La operación automática: Cortar si se mete, Unir si nace de una cara de un sólido visible, None si ninguna."""
        if solapa:
            return "cortar"
        visibles = {c.id for c in self._visibles(ctx)}
        return "unir" if any(r.get("cuerpo") in visibles for r in op.p.get("caras") or []) else None

    @staticmethod
    def _visibles(ctx):
        ocultos = getattr(ctx.ventana, "_ocultos_efectivos", lambda _estado: ())(ctx.estado)
        return [c for c in ctx.estado.cuerpos.values() if c.tipo == "solido" and c.id not in ocultos]

    def _caja(self, cuerpo):
        if cuerpo.id not in self._cajas:
            self._cajas[cuerpo.id] = geo.caja_envolvente(cuerpo.forma)
        return self._cajas[cuerpo.id]

    def _ajustar(self, panel, auto):
        """`auto`: "cortar", "unir" o None (vuelve a la operación que había antes del cambio automático)."""
        actual = panel.valores.get("operacion")
        if auto is not None and actual != auto:
            if self._antes_auto is None:
                self._antes_auto = actual
            nueva = auto
        elif auto is None and self._antes_auto is not None:
            nueva, self._antes_auto = self._antes_auto, None
        else:
            return
        self._ajustando = True
        try:
            panel.set_valor("operacion", nueva)
        finally:
            self._ajustando = False

    def _pedir_al_hijo(self, panel, op, solidos):
        """Un solo cálculo a la vez: el que termina con una extrusión vieja pide otra vuelta de la previa."""
        # shortcut: aceptar antes de que vuelva el hijo deja la operación que estaba; esperarlo si alguien lo nota en piezas pesadas.
        from PySide6.QtCore import QTimer

        from ...nucleo.aislado import CalculoPendiente, TareaAislada
        if self._hijo is not None:
            return
        ctx = panel.ctx
        self._op_hijo = self._herramienta(op).a_dict()
        try:
            self._hijo = CalculoPendiente("solape_herramienta", {
                "receta": ctx.doc.a_dict(), "operacion": self._op_hijo, "indice": ctx.indice,
                "cuerpos": [c.id for c in solidos]})
        except TareaAislada as e:
            panel._mostrar(str(e), tipo="aviso")
            return
        self._t_hijo = QTimer(panel, interval=50)
        self._t_hijo.timeout.connect(lambda: self._leer_hijo(panel))
        self._t_hijo.start()

    def _leer_hijo(self, panel):
        try:
            salida = self._hijo.sondear()
            if salida is None:
                return
        except Exception as e:  # noqa: BLE001 — un hijo caído o vencido deja la operación que estaba
            self._cancelar_hijo()
            panel._mostrar(f"⚠ {e}", tipo="aviso")
            return
        vigente = panel.ultima_op is not None and self._herramienta(panel.ultima_op).a_dict() == self._op_hijo
        self._cancelar_hijo()
        if vigente:
            self._ajustar(panel, self._auto(panel.ctx, panel.ultima_op, salida["solapa"]))
        else:
            panel._programar()

    def _cancelar_hijo(self):
        if self._t_hijo is not None:
            self._t_hijo.stop()
            self._t_hijo.deleteLater()
            self._t_hijo = None
        if self._hijo is not None:
            self._hijo.cancelar()
            self._hijo = None

    def desde_op(self, op, ctx):
        v = dict(op.p)
        if op.p.get("simetrica"):
            v.update(direccion="simetrica", medida="total")
        v["perfiles"] = perfiles_desde_op(op, ctx.estado) + hits(op.p.get("curvas") or [], ctx.estado)
        v["objetivos"] = objetivos_desde_op(op, ctx.estado)
        for clave in ("inicio_objeto", "hasta", "hasta2"):
            v[clave] = [hit_desde_ref(op.p[clave], ctx.estado)] if op.p.get(clave) else []
        return v


class ExtruirCara(Comando):
    """Extruye SOLO la cara elegida: hacia afuera agrega material (unir) y hacia adentro lo corta."""

    CLAVE, TITULO, ICONO = "extruir_cara", "Extruir cara", "extruir_cara"
    AYUDA = "Extruye la cara plana elegida hacia afuera (agrega material) o hacia adentro (corta)."
    CLASE_OP = None          # el paso creado se edita con el comando «Extruir» de siempre

    def verificar(self, ctx):
        return None if ctx.estado.cuerpos else "Este comando necesita un cuerpo."

    def campos(self, ctx):
        return [
            Seleccion("caras", "Cara plana", {"cara_plana"}, maximo=None),
            Opciones("sentido", "Sentido", {"afuera": "Hacia afuera (agrega)", "adentro": "Hacia adentro (corta)"}),
            Expresion("distancia", "Distancia", "0 mm"),
        ]

    def construir(self, v, ctx):
        exigir(v, "caras", "Elegí una cara plana.")
        if ctx.evaluar(v.get("distancia") or "0") <= 0:
            raise ErrorComando("La distancia tiene que ser mayor que cero.")
        adentro = v.get("sentido") == "adentro"
        return self.crear_op(OpExtrusion, v, ctx,
                             caras=[h["ref"] for h in v["caras"]],
                             distancia=v.get("distancia") or "5 mm",
                             operacion="cortar" if adentro else "unir",
                             invertir=adentro)

    def manipuladores(self, ctx, v):
        """Flecha de distancia sobre la cara: apunta hacia donde crece la distancia."""
        from .. import manipuladores as mp
        base = mp.base_perfiles(v.get("caras"), ctx.estado)
        if base is None:
            return []
        centro, plano, _formas = base
        n = mp.unitario(plano.normal) * (-1.0 if v.get("sentido") == "adentro" else 1.0)
        return [mp.Flecha("distancia", centro, n)]


class Revolucion(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "revolucion", "Revolución", "revolucion", None
    AYUDA = "Gira perfiles de boceto o caras planas alrededor de un eje."
    CLASE_OP = OpRevolucion

    def verificar(self, ctx):
        return None if ctx.estado.bocetos or ctx.estado.cuerpos else "Primero creá un boceto con un contorno cerrado."

    def campos(self, ctx):
        return [
            Seleccion("perfiles", "Perfil", {"perfil", "cara_plana"}, maximo=None, desvio=_otro_plano_revolucion),
            Seleccion("eje", "Eje", {"eje"}),
            Opciones("extension", "Tipo de extensión", {"angulo": "Ángulo", "objeto": "A objeto", "completa": "Completo"}),
            Seleccion("hasta", "Objeto límite", {"vertice", "cara", "plano", "cuerpo"},
                      visible_si=lambda v: v.get("extension") == "objeto"),
            Opciones("direccion", "Dirección", DIRECCIONES_UI, visible_si=lambda v: v.get("extension") == "angulo"),
            Expresion("angulo", "Ángulo", "360 deg", ANGULO, visible_si=lambda v: v.get("extension") == "angulo",
                      etiqueta_si=lambda v: "Ángulo del lado 1" if v.get("direccion") == "dos_lados" else "Ángulo"),
            Expresion("angulo2", "Ángulo del lado 2", "90 deg", ANGULO,
                      visible_si=lambda v: v.get("extension") == "angulo" and v.get("direccion") == "dos_lados"),
            Casilla("proyectar_eje", "Eje de proyecto", True, ayuda="Proyecta el eje sobre el plano del perfil antes de girar."),
            Casilla("invertir", "Invertir dirección"),
            campo_operacion(),
            campo_objetivos(),
        ]

    def construir(self, v, ctx):
        boceto, perfiles, caras = perfiles_a_params(v.get("perfiles"))
        eje = ref1(v, "eje")
        if eje is None and boceto:
            # Como Fusion: si el boceto tiene una línea central, es el eje por defecto.
            br = ctx.estado.bocetos.get(boceto)
            central = next((c.id for c in br.boceto.curvas.values() if getattr(c, "eje", False)
                            and c.tipo == "linea"), None) if br else None
            if central is not None:
                eje = {"tipo": "curva_boceto", "boceto": boceto, "curva": central}
        if eje is None:
            raise ErrorComando("Seleccioná el eje de revolución (una línea, arista o eje).")
        ctx.evaluar(v.get("angulo") or "0", ANGULO)
        if v.get("extension") == "objeto":
            exigir(v, "hasta", "Seleccioná el objeto hasta donde gira el perfil.")
        params = {k: v.get(k) for k in ("extension", "direccion", "angulo", "angulo2", "invertir", "operacion")}
        params.update(boceto=boceto, perfiles=perfiles, caras=caras, eje_ref=eje, eje="v",
                      objetivos=objetivos(v), objetivo="", proyectar_eje=bool(v.get("proyectar_eje")),
                      hasta=ref1(v, "hasta") if v.get("extension") == "objeto" else None)
        return self.crear_op(OpRevolucion, v, ctx, **params)

    def manipuladores(self, ctx, v):
        """Arco con asa alrededor del eje, a la distancia del centro del perfil (el segundo lado en «Dos
        lados»; en «Simétrica» el asa va a la mitad del ángulo, como el resultado)."""
        from .. import manipuladores as mp
        if v.get("extension") != "angulo":
            return []
        base = mp.base_perfiles(v.get("perfiles"), ctx.estado)
        if base is None:
            return []
        try:
            op = self.construir(v, ctx)
            punto, d = op._eje(ctx.estado, base[1])
        except Exception:  # noqa: BLE001 — sin eje todavía no hay manipulador
            return []
        d = mp.unitario(d) * (-1.0 if v.get("invertir") else 1.0)
        if np.linalg.norm(d) < 1e-9:
            return []
        centro = base[0]
        pie = np.asarray(punto, float) + d * float((centro - punto) @ d)
        radio = float(np.linalg.norm(centro - pie))
        radio = radio if radio > 1e-6 else None
        if v.get("direccion") == "simetrica":
            return [mp.Angulo("angulo", pie, d, centro - pie, radio, factor=0.5)]
        # B-210: en «Dos lados» cada ángulo es una magnitud de su lado (el lado lo elige la dirección), como en
        # Extruir (B-205): el asa no se arrastra por debajo de 0, donde ya no cambiaría nada.
        dos = v.get("direccion") == "dos_lados"
        salida = [mp.Angulo("angulo", pie, d, centro - pie, radio, minimo=0.0 if dos else -360.0)]
        if dos:
            salida.append(mp.Angulo("angulo2", pie, -d, centro - pie, radio, minimo=0.0))
        return salida

    def desde_op(self, op, ctx):
        v = dict(op.p)
        v["perfiles"] = perfiles_desde_op(op, ctx.estado)
        v["objetivos"] = objetivos_desde_op(op, ctx.estado)
        v["hasta"] = [hit_desde_ref(op.p["hasta"], ctx.estado)] if op.p.get("hasta") else []
        if op.p.get("eje_ref"):
            v["eje"] = [hit_desde_ref(op.p["eje_ref"], ctx.estado)]
        elif op.p.get("eje") not in ("u", "v", None):
            v["eje"] = [hit_desde_ref({"tipo": "curva_boceto", "boceto": op.p["boceto"], "curva": int(op.p["eje"])},
                                      ctx.estado)]
        else:
            br = ctx.estado.bocetos.get(op.p.get("boceto"))
            v["eje"] = []
            if br is not None:              # eje u/v del boceto: equivale al eje de origen paralelo (si pasa por 0)
                import numpy as np
                d = br.plano.u if op.p["eje"] == "u" else br.plano.v
                nombre = "XYZ"[int(np.argmax(np.abs(d)))]
                if np.allclose(br.plano.origen, 0):
                    v["eje"] = [hit_desde_ref({"tipo": "eje", "id": nombre}, ctx.estado)]
        return v



registrar(Extruir, ExtruirCara, Revolucion)
