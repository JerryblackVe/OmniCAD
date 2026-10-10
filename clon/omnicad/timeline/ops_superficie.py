# -*- coding: utf-8 -*-
"""
Operaciones de la pestaña SUPERFICIE de Fusion [Fusion-Patch]: crean o modifican cuerpos de superficie
(`tipo="superficie"`), que se ven en tono arena y pueden coserse o engrosarse para volver a ser sólidos.
"""
import numpy as np

from ..nucleo import geometria as geo
from . import entidades as ent
from .operaciones import (ANGULO, OPERACIONES_CUERPO, ErrorOperacion, Operacion, _deps_objetivo, _resolver,
                          _resolver_todas, aplicar_resultado, registrar_operacion)


def _sf():
    from ..nucleo import superficies
    return superficies


def _curvas(refs, estado, que="curvas"):
    ents = _resolver_todas(refs, estado)
    aristas = [e.forma for e in ents if e.forma is not None]
    if not aristas:
        raise ErrorOperacion(f"Elegí {que}.")
    return ents, aristas


def _direccion_curvas(ents, ref_dir, estado):
    if ref_dir:
        return ent.direccion(_resolver(ref_dir, estado))
    plano = next((e.plano for e in ents if e.plano is not None), None)
    return plano.normal if plano is not None else np.array([0.0, 0.0, 1.0])


class _OpSuperficie(Operacion):
    REFS = ()

    def dependencias(self):
        return (ent.dependencias_de(*(self.p.get(k) for k in self.REFS)) |
                _deps_objetivo(self.p.get("cuerpos")) | _deps_objetivo(self.p.get("cuerpo"))) - {self.id}

    def _nuevo(self, estado, ctx, forma):
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, "nuevo", tipo="superficie"))


class OpSupExtruir(_OpSuperficie):
    """SUPERFICIE › Extruir [SFC-EXTRUDE]: curvas abiertas o cerradas → superficie."""
    TIPO, ETIQUETA, ICONO = "sup_extruir", "Extrusión de superficie", "⬆"
    PARAMS = {"curvas": [], "direccion": None, "distancia": "10 mm", "simetrica": False, "conicidad": "0 deg"}
    EXPRESIONES = ("distancia", "conicidad")
    REFS = ("curvas", "direccion")

    def ejecutar(self, estado, ctx):
        ents, aristas = _curvas(self.p["curvas"], estado)
        d = _direccion_curvas(ents, self.p["direccion"], estado)
        self._nuevo(estado, ctx, _sf().extruir_superficie(aristas, d, ctx.evaluar(self.p["distancia"]),
                                                          simetrica=self.p["simetrica"],
                                                          conicidad=ctx.evaluar(self.p["conicidad"], ANGULO)))


class OpSupRevolucion(_OpSuperficie):
    """SUPERFICIE › Revolución [SFC-REVOLVE]."""
    TIPO, ETIQUETA, ICONO = "sup_revolucion", "Revolución de superficie", "↻"
    PARAMS = {"curvas": [], "eje": None, "angulo": "360 deg"}
    EXPRESIONES = ("angulo",)
    REFS = ("curvas", "eje")

    def ejecutar(self, estado, ctx):
        _, aristas = _curvas(self.p["curvas"], estado)
        if not self.p["eje"]:
            raise ErrorOperacion("Elegí el eje.")
        p, d = ent.como_eje(_resolver(self.p["eje"], estado))
        self._nuevo(estado, ctx, _sf().revolver_superficie(aristas, p, d, ctx.evaluar(self.p["angulo"], ANGULO)))


class OpSupBarrido(_OpSuperficie):
    """SUPERFICIE › Barrido [SFC-SWEEP]."""
    TIPO, ETIQUETA, ICONO = "sup_barrido", "Barrido de superficie", "↝"
    PARAMS = {"perfil": [], "ruta": [], "orientacion": "perpendicular", "torsion": "0 deg"}
    EXPRESIONES = ("torsion",)
    OPCIONES = {"orientacion": ("perpendicular", "paralela")}
    REFS = ("perfil", "ruta")

    def ejecutar(self, estado, ctx):
        _, perfil = _curvas(self.p["perfil"], estado, "el perfil")
        _, ruta = _curvas(self.p["ruta"], estado, "la ruta")
        self._nuevo(estado, ctx, _sf().barrer_superficie(perfil, ruta, orientacion=self.p["orientacion"],
                                                         torsion=ctx.evaluar(self.p["torsion"], ANGULO)))


class OpSupSolevacion(_OpSuperficie):
    """SUPERFICIE › Solevación [SFC-LOFT]: cada selección es una sección (curva, arista o punto)."""
    TIPO, ETIQUETA, ICONO = "sup_solevacion", "Solevación de superficie", "⌓"
    PARAMS = {"secciones": [], "cerrada": False, "reglada": False}
    REFS = ("secciones",)

    def ejecutar(self, estado, ctx):
        secciones = []
        for e in _resolver_todas(self.p["secciones"], estado):
            secciones.append(e.forma if e.forma is not None and e.tipo not in ("vertice",) else ent.como_punto(e))
        self._nuevo(estado, ctx, _sf().solevar_superficie(secciones, cerrada=self.p["cerrada"],
                                                          reglada=self.p["reglada"]))


class OpParche(_OpSuperficie):
    """SUPERFICIE › Parche [SFC-PATCH]: cierra un contorno con una superficie."""
    TIPO, ETIQUETA, ICONO = "parche", "Parche", "◍"
    PARAMS = {"contorno": [], "continuidad": "G0"}
    OPCIONES = {"continuidad": ("G0", "G1", "G2")}
    REFS = ("contorno",)

    def ejecutar(self, estado, ctx):
        ents, aristas = _curvas(self.p["contorno"], estado, "el contorno")
        soporte = None
        if self.p["continuidad"] != "G0":
            cid = next((e.cuerpo for e in ents if e.cuerpo), None)
            soporte = estado.cuerpo(cid).forma if cid else None
        self._nuevo(estado, ctx, _sf().parche(aristas, continuidad=self.p["continuidad"], soporte=soporte))


class OpReglada(_OpSuperficie):
    """SUPERFICIE › Reglada [SFC-RULED]."""
    TIPO, ETIQUETA, ICONO = "reglada", "Superficie reglada", "▥"
    PARAMS = {"aristas": [], "tipo": "normal", "distancia": "10 mm", "angulo": "0 deg", "direccion": None}
    EXPRESIONES = ("distancia", "angulo")
    OPCIONES = {"tipo": ("normal", "tangente", "direccion")}
    REFS = ("aristas", "direccion")

    def ejecutar(self, estado, ctx):
        ents, aristas = _curvas(self.p["aristas"], estado, "las aristas")
        cid = next((e.cuerpo for e in ents if e.cuerpo), None)
        referencia = estado.cuerpo(cid).forma if cid else next((e.plano for e in ents if e.plano is not None), None)
        direccion = ent.direccion(_resolver(self.p["direccion"], estado)) if self.p["direccion"] else None
        self._nuevo(estado, ctx, _sf().reglada(aristas, ctx.evaluar(self.p["distancia"]),
                                               ctx.evaluar(self.p["angulo"], ANGULO), tipo=self.p["tipo"],
                                               direccion=direccion, referencia=referencia))


class OpSupDesfase(_OpSuperficie):
    """SUPERFICIE › Desfase [SFC-OFFSET]: crea una superficie paralela a caras o cuerpos."""
    TIPO, ETIQUETA, ICONO = "sup_desfase", "Desfase de superficie", "⧉"
    PARAMS = {"caras": [], "distancia": "2 mm", "tipo": "agudo"}
    EXPRESIONES = ("distancia",)
    OPCIONES = {"tipo": ("agudo", "redondeado")}
    REFS = ("caras",)

    def ejecutar(self, estado, ctx):
        ents = _resolver_todas(self.p["caras"], estado)
        if not ents:
            raise ErrorOperacion("Elegí caras o un cuerpo.")
        base = geo.compuesto([e.forma for e in ents]) if len(ents) > 1 else ents[0].forma
        self._nuevo(estado, ctx, _sf().desfasar_superficie(base, ctx.evaluar(self.p["distancia"]), tipo=self.p["tipo"]))


class OpRecortar(_OpSuperficie):
    """SUPERFICIE › Recortar [SFC-TRIM]: la herramienta parte el cuerpo y se quita la región elegida."""
    TIPO, ETIQUETA, ICONO = "recortar_sup", "Recortar", "✂"
    PARAMS = {"cuerpo": "", "herramienta": None, "punto": [0.0, 0.0, 0.0]}
    REFS = ("herramienta",)

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpo"] or not self.p["herramienta"]:
            raise ErrorOperacion("Elegí la herramienta y la región a quitar.")
        c = estado.cuerpo(self.p["cuerpo"])
        e = _resolver(self.p["herramienta"], estado)
        herramienta = ent.como_plano(e) if e.tipo == "plano" else e.forma
        c.forma = _sf().recortar(c.forma, herramienta, np.asarray(self.p["punto"], float))


class OpDestrimar(_OpSuperficie):
    """SUPERFICIE › Destrimar [SFC-UNTRIM]."""
    TIPO, ETIQUETA, ICONO = "destrimar", "Destrimar", "◰"
    PARAMS = {"caras": [], "contornos": "exteriores"}
    OPCIONES = {"contornos": ("exteriores", "interiores", "todos")}
    REFS = ("caras",)

    def ejecutar(self, estado, ctx):
        for e in _resolver_todas(self.p["caras"], estado, ("cara",)):
            c = estado.cuerpo(e.cuerpo)
            nueva = _sf().destrimar(e.forma, contornos=self.p["contornos"])
            resto = [f for f in geo.caras(c.forma) if not f.IsSame(e.forma)]
            c.forma = _sf().coser(resto + [nueva])["forma"] if resto else nueva


class OpExtenderSup(_OpSuperficie):
    """SUPERFICIE › Extender [SFC-EXTEND]."""
    TIPO, ETIQUETA, ICONO = "extender_sup", "Extender", "⇲"
    PARAMS = {"aristas": [], "distancia": "5 mm", "tipo": "natural"}
    EXPRESIONES = ("distancia",)
    OPCIONES = {"tipo": ("natural", "tangente", "perpendicular")}
    REFS = ("aristas",)

    def ejecutar(self, estado, ctx):
        grupos = {}
        for e in _resolver_todas(self.p["aristas"], estado, ("arista",)):
            if e.cuerpo is None:
                raise ErrorOperacion("Elegí bordes de un cuerpo de superficie.")
            grupos.setdefault(e.cuerpo, []).append(e.forma)
        if not grupos:
            raise ErrorOperacion("Elegí los bordes a extender.")
        for cid, aristas in grupos.items():
            c = estado.cuerpo(cid)
            c.forma = _sf().extender(c.forma, aristas, ctx.evaluar(self.p["distancia"]), tipo=self.p["tipo"])


class OpCoser(_OpSuperficie):
    """SUPERFICIE › Coser [SFC-STITCH]: une superficies; si quedan cerradas, el resultado es un sólido."""
    TIPO, ETIQUETA, ICONO = "coser", "Coser", "⧓"
    PARAMS = {"cuerpos": [], "tolerancia": "0.01 mm"}
    EXPRESIONES = ("tolerancia",)

    def ejecutar(self, estado, ctx):
        if len(self.p["cuerpos"]) < 1:
            raise ErrorOperacion("Elegí los cuerpos de superficie a coser.")
        cuerpos = [estado.cuerpo(c) for c in self.p["cuerpos"]]
        r = _sf().coser([c.forma for c in cuerpos], ctx.evaluar(self.p["tolerancia"]))
        principal = cuerpos[0]
        principal.forma, principal.tipo = r["forma"], "solido" if r["es_solido"] else "superficie"
        for c in cuerpos[1:]:
            del estado.cuerpos[c.id]
        if not r["es_solido"]:
            ctx.aviso("Quedaron bordes abiertos: el resultado sigue siendo una superficie.")


class OpDescoser(_OpSuperficie):
    """SUPERFICIE › Descoser [SFC-UNSTITCH]: cada cara pasa a ser un cuerpo de superficie."""
    TIPO, ETIQUETA, ICONO = "descoser", "Descoser", "⧈"
    PARAMS = {"cuerpos": []}

    def ejecutar(self, estado, ctx):
        for cid in self.p["cuerpos"]:
            c = estado.cuerpo(cid)
            caras = _sf().descoser(c.forma)
            del estado.cuerpos[c.id]
            for cara in caras:
                estado.nuevo_cuerpo(self.id, cara, "superficie", apariencia=c.apariencia)


class OpInvertirNormal(_OpSuperficie):
    """SUPERFICIE › Invertir normal [GUID-3B2D0A04]."""
    TIPO, ETIQUETA, ICONO = "invertir_normal", "Invertir normal", "⇅"
    PARAMS = {"cuerpos": []}

    def ejecutar(self, estado, ctx):
        for cid in self.p["cuerpos"]:
            c = estado.cuerpo(cid)
            c.forma = _sf().invertir_normal(c.forma)


class OpEngrosar(_OpSuperficie):
    """CREAR › Engrosar [GUID-471827A2]: da espesor a caras o superficies (cuerpo nuevo o booleana).
    `tipo`: "agudo" (Sharp Thicken, esquinas en punta) o "redondeado" (Rounded Thicken)."""
    TIPO, ETIQUETA, ICONO = "engrosar", "Engrosar", "▤"
    PARAMS = {"caras": [], "espesor": "2 mm", "direccion": "un_lado", "tipo": "agudo", "operacion": "nuevo",
              "objetivos": []}
    EXPRESIONES = ("espesor",)
    OPCIONES = {"direccion": ("un_lado", "simetrica"), "tipo": ("agudo", "redondeado"),
                "operacion": OPERACIONES_CUERPO}
    REFS = ("caras",)

    def ejecutar(self, estado, ctx):
        ents = _resolver_todas(self.p["caras"], estado)
        if not ents:
            raise ErrorOperacion("Elegí las caras o superficies a engrosar.")
        base = geo.compuesto([e.forma for e in ents]) if len(ents) > 1 else ents[0].forma
        forma = _sf().engrosar_superficie(base, ctx.evaluar(self.p["espesor"]),
                                          simetrica=self.p["direccion"] == "simetrica", tipo=self.p["tipo"])
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, self.p["operacion"],
                                                 self.p.get("objetivos") or ""))


class OpSupEmpalme(_OpSuperficie):
    """SUPERFICIE › Empalme/chaflán de aristas de superficies [SFC-FILLET-CHAMFER]."""
    TIPO, ETIQUETA, ICONO = "sup_empalme", "Empalme de superficie", "◜"
    PARAMS = {"aristas": [], "tipo": "empalme", "medida": "1 mm"}
    EXPRESIONES = ("medida",)
    OPCIONES = {"tipo": ("empalme", "chaflan")}
    REFS = ("aristas",)

    def ejecutar(self, estado, ctx):
        grupos = {}
        for e in _resolver_todas(self.p["aristas"], estado, ("arista",)):
            grupos.setdefault(e.cuerpo, []).append(e.forma)
        if not grupos:
            raise ErrorOperacion("Elegí las aristas.")
        for cid, aristas in grupos.items():
            c = estado.cuerpo(cid)
            f = _sf().empalme_superficie if self.p["tipo"] == "empalme" else _sf().chaflan_superficie
            c.forma = f(c.forma, aristas, ctx.evaluar(self.p["medida"]))


registrar_operacion(OpSupExtruir, OpSupRevolucion, OpSupBarrido, OpSupSolevacion, OpParche, OpReglada, OpSupDesfase,
                    OpRecortar, OpDestrimar, OpExtenderSup, OpCoser, OpDescoser, OpInvertirNormal, OpEngrosar,
                    OpSupEmpalme)
