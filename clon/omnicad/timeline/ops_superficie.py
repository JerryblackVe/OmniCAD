# -*- coding: utf-8 -*-
"""
Operaciones de la pestaña SUPERFICIE de Fusion [Fusion-Patch]: crean o modifican cuerpos de superficie
(`tipo="superficie"`), que se ven en tono arena y pueden coserse o engrosarse para volver a ser sólidos.
"""
import math

import numpy as np

from ..nucleo import geometria as geo
from . import entidades as ent
from .operaciones import (ANGULO, OPERACIONES_CUERPO, ErrorOperacion, Operacion, OpPrimitiva, _caja_todo, _deps_objetivo,
                          _resolver, _resolver_todas, aplicar_resultado, registrar_operacion)
from .ops_solido import OpBobina, OpTuberia, _en_cadena

LADOS = {"un_lado": "Un lado", "dos_lados": "Dos lados", "simetrica": "Simétrica"}


def _sf():
    from ..nucleo import superficies
    return superficies


def _trazos_texto(ref, estado):
    """Las aristas de un texto de boceto de una sola línea (una por trazo); None si `ref` no es un texto. Fusion solo
    extruye como superficie los textos de una línea: con una fuente de contornos es un error con la causa."""
    if not (isinstance(ref, dict) and ref.get("tipo") == "curva_boceto" and ref.get("boceto") in estado.bocetos):
        return None
    br = estado.bocetos[ref["boceto"]]
    curva = br.boceto.curvas.get(ref.get("curva"))
    if curva is None or getattr(curva, "tipo", "") != "texto":
        return None
    from ..nucleo import fuentes, perfiles
    registro = fuentes.buscar_fuente(curva.fuente, curva.negrita, curva.cursiva)
    if not (registro or {}).get("una_linea"):
        raise ErrorOperacion(f"Un texto solo se extruye como superficie con una fuente de una línea (p. ej. «OmniCAD "
                             f"Trazo SHX» o una .shx): este usa «{curva.fuente}». Para letras con relleno, extruí sus "
                             "perfiles como sólido.")
    geom = [g for g in br.boceto.geometria(incluir_construccion=True) if g[1] == ref["curva"]]
    return [arista for _, arista in perfiles.aristas_boceto(geom, br.plano)]


def _curvas(refs, estado, que="curvas"):
    ents, aristas = [], []
    for ref in refs or []:
        trazos = _trazos_texto(ref, estado)
        resueltas = _resolver_todas([ref], estado)
        ents += resueltas
        nuevas = trazos if trazos else [e.forma for e in resueltas if e.forma is not None]
        aristas += [a for a in nuevas if not any(a.IsSame(x) for x in aristas)]
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
        caja = geo.caja_envolvente(forma)
        diagonal = math.dist(*caja) if caja else 0.0
        # SUP-6: un resultado inválido o sin extensión (área despreciable frente a su tamaño: aspecto > 1e6) no
        # puede quedar como cuerpo. `aplicar_resultado` solo mira que no esté vacío.
        if not geo.es_valida(forma) or diagonal <= 0 or geo.area(forma) <= 1e-6 * diagonal * diagonal:
            raise ErrorOperacion("La operación generó una superficie degenerada (sin área o inválida): revisá las "
                                 "curvas, la distancia y el ángulo.")
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, "nuevo", tipo="superficie"))


class OpSupExtruir(_OpSuperficie):
    """SUPERFICIE › Extruir [SFC-EXTRUDE]: curvas abiertas o cerradas (o un texto de una línea) → superficie.
    `inicio` (plano del perfil, desfase u objeto), `lados` (un lado, dos lados con distancias distintas, simétrica
    por longitud total o `medida` mitad) y `extension` (distancia, al objeto o todo). `simetrica` es el campo de las
    recetas viejas: vale como lados = simétrica."""
    TIPO, ETIQUETA, ICONO = "sup_extruir", "Extrusión de superficie", "⬆"
    PARAMS = {"curvas": [], "direccion": None, "distancia": "10 mm", "simetrica": False, "conicidad": "0 deg",
              "lados": "un_lado", "medida": "total", "distancia2": "10 mm", "inicio": "plano", "desfase_inicio": "0 mm",
              "inicio_objeto": None, "extension": "distancia", "hasta": None, "desfase_hasta": "0 mm", "invertir": False}
    EXPRESIONES = ("distancia", "conicidad", "distancia2", "desfase_inicio", "desfase_hasta")
    OPCIONES = {"lados": LADOS, "medida": ("mitad", "total"), "inicio": ("plano", "desfase", "objeto"),
                "extension": ("distancia", "objeto", "todo")}
    REFS = ("curvas", "direccion", "inicio_objeto", "hasta")

    def ejecutar(self, estado, ctx):
        p = self.p
        ents, aristas = _curvas(p["curvas"], estado)
        d = _direccion_curvas(ents, p["direccion"], estado) * (-1 if p["invertir"] else 1)
        lados = "simetrica" if p["simetrica"] else p["lados"]
        desfase = 0.0
        if p["inicio"] == "desfase":
            desfase = ctx.evaluar(p["desfase_inicio"])
        elif p["inicio"] == "objeto":
            e = _resolver(p["inicio_objeto"], estado) if p["inicio_objeto"] else None
            if e is None or e.plano is None:
                raise ErrorOperacion("Elegí una cara plana o un plano como inicio de la extrusión.")
            caja = geo.caja_envolvente(aristas[0])
            desfase = float((e.plano.origen - np.mean(caja, axis=0)) @ (d / np.linalg.norm(d)))
        hasta = caja_todo = None
        if p["extension"] == "objeto":
            if not p["hasta"]:
                raise ErrorOperacion("Elegí la cara, el plano o el cuerpo hasta donde llega la extrusión.")
            o = _resolver(p["hasta"], estado)
            hasta = o.forma if o.forma is not None else o.plano
            if hasta is None:
                raise ErrorOperacion("El objeto elegido no sirve como límite de la extrusión.")
        elif p["extension"] == "todo":
            caja_todo = _caja_todo(estado)
        self._nuevo(estado, ctx, _sf().extruir_superficie(
            aristas, d, ctx.evaluar(p["distancia"]), conicidad=ctx.evaluar(p["conicidad"], ANGULO), lados=lados,
            distancia2=ctx.evaluar(p["distancia2"]) if lados == "dos_lados" else None, medida=p["medida"],
            desfase_inicio=desfase, hasta=hasta, hasta_desfase=ctx.evaluar(p["desfase_hasta"]) if hasta is not None else 0.0,
            caja=caja_todo))


class OpSupRevolucion(_OpSuperficie):
    """SUPERFICIE › Revolución [SFC-REVOLVE]: `extension` (ángulo, completa o al objeto), `lados` (un lado, dos lados
    con `angulo2`, simétrica) y `proyectar_eje` (el eje se lleva al plano del perfil)."""
    TIPO, ETIQUETA, ICONO = "sup_revolucion", "Revolución de superficie", "↻"
    PARAMS = {"curvas": [], "eje": None, "angulo": "360 deg", "extension": "angulo", "lados": "un_lado",
              "angulo2": "90 deg", "hasta": None, "proyectar_eje": False}
    EXPRESIONES = ("angulo", "angulo2")
    OPCIONES = {"extension": ("angulo", "completa", "objeto"), "lados": LADOS}
    REFS = ("curvas", "eje", "hasta")

    def _objeto(self, estado):
        """El límite de «A objeto» como lo entiende `superficies.revolver_superficie`."""
        if not self.p["hasta"]:
            raise ErrorOperacion("Elegí el vértice, el plano, la cara plana o el cuerpo hasta donde gira el perfil.")
        e = _resolver(self.p["hasta"], estado)
        if e.tipo in ("vertice", "punto", "punto_boceto"):
            return "punto", ent.como_punto(e)
        if e.plano is not None:
            return "plano", e.plano
        if e.tipo == "cuerpo" and e.forma is not None:
            return "forma", e.forma
        raise ErrorOperacion("El objeto de la revolución tiene que ser un vértice, un plano, una cara plana o un cuerpo.")

    def ejecutar(self, estado, ctx):
        p = self.p
        ents, aristas = _curvas(p["curvas"], estado)
        if not p["eje"]:
            raise ErrorOperacion("Elegí el eje.")
        punto, d = ent.como_eje(_resolver(p["eje"], estado))
        if p["proyectar_eje"]:            # «Project Axis»: el eje se lleva al plano del perfil
            plano = next((e.plano for e in ents if e.plano is not None), None)
            if plano is None:
                raise ErrorOperacion("«Proyectar eje» necesita curvas de un boceto: es el plano del perfil.")
            n = np.asarray(plano.normal, float)
            punto = np.asarray(punto, float)
            punto = punto - n * float((punto - plano.origen) @ n)
            d = np.asarray(d, float)
            d = d - n * float(d @ n)
            if np.linalg.norm(d) < 1e-9:
                raise ErrorOperacion("El eje es perpendicular al plano del perfil: no se puede proyectar.")
        if p["extension"] == "objeto":
            forma = _sf().revolver_superficie(aristas, punto, d, 0.0, hasta=self._objeto(estado))
        else:
            completa = p["extension"] == "completa"
            lados = "un_lado" if completa else p["lados"]
            forma = _sf().revolver_superficie(
                aristas, punto, d, 360.0 if completa else ctx.evaluar(p["angulo"], ANGULO), direccion=lados,
                angulo2=ctx.evaluar(p["angulo2"], ANGULO) if lados == "dos_lados" else None)
        self._nuevo(estado, ctx, forma)


class OpSupBarrido(_OpSuperficie):
    """SUPERFICIE › Barrido [SFC-SWEEP]: el tipo sale de lo elegido: Ruta individual (`orientacion`, `torsion`,
    `conicidad`), Ruta + Riel guía (`carril`, `escala_carril`, `extension` y, con extensión completa, `distancia_carril`)
    o Ruta + Superficie guía (`superficie_guia`). `distancia` es la fracción de la ruta (Distance, de 0 a 1) y `cadena`
    (Chain Selection) suma a la ruta, al perfil y al riel lo que les sigue tangente."""
    TIPO, ETIQUETA, ICONO = "sup_barrido", "Barrido de superficie", "↝"
    PARAMS = {"perfil": [], "ruta": [], "orientacion": "perpendicular", "torsion": "0 deg", "distancia": "1",
              "conicidad": "0 deg", "carril": [], "escala_carril": "escalar", "extension": "perpendicular",
              "distancia_carril": "1", "superficie_guia": [], "cadena": False}
    EXPRESIONES = ("torsion", "distancia", "conicidad", "distancia_carril")
    OPCIONES = {"orientacion": ("perpendicular", "paralela"), "escala_carril": ("escalar", "estirar", "ninguna"),
                "extension": ("perpendicular", "completa")}
    REFS = ("perfil", "ruta", "carril", "superficie_guia")

    def _elegidas(self, clave, estado, que):
        ents, aristas = _curvas(self.p[clave], estado, que)
        return _en_cadena(ents, aristas, estado) if self.p["cadena"] else aristas

    def ejecutar(self, estado, ctx):
        p = self.p
        guia = [e.forma for e in _resolver_todas(p["superficie_guia"], estado)]
        self._nuevo(estado, ctx, _sf().barrer_superficie(
            self._elegidas("perfil", estado, "el perfil"), self._elegidas("ruta", estado, "la ruta"),
            orientacion=p["orientacion"], torsion=ctx.evaluar(p["torsion"], ANGULO),
            distancia=ctx.evaluar(p["distancia"], "escalar"), conicidad=ctx.evaluar(p["conicidad"], ANGULO),
            carril=self._elegidas("carril", estado, "el riel guía") if p["carril"] else None,
            escala=p["escala_carril"], extension=p["extension"], superficie_guia=guia or None,
            distancia_carril=ctx.evaluar(p["distancia_carril"], "escalar")))


class OpSupSolevacion(_OpSuperficie):
    """SUPERFICIE › Solevación [SFC-LOFT]: cada selección es una sección (curva, arista o punto). `carriles` (Rail) y
    `linea_central` (Centerline) guían la forma. `condicion_inicio`, `condicion_fin` y `condiciones_medias` son como en la
    solevación sólida, más `alineacion` (Edge Alignment) y el tipo `punto_tangente`; sin `cara`, una condición Tangente o
    Suave usa la cara de la que sale el perfil."""
    TIPO, ETIQUETA, ICONO = "sup_solevacion", "Solevación de superficie", "⌓"
    PARAMS = {"secciones": [], "cerrada": False, "reglada": False, "carriles": [], "linea_central": [],
              "condicion_inicio": None, "condicion_fin": None, "condiciones_medias": {}, "fusionar_tangentes": False,
              "cadena": False}
    REFS = ("secciones", "carriles", "linea_central")

    def dependencias(self):
        caras = [c.get("cara") for c in (self.p["condicion_inicio"], self.p["condicion_fin"]) if c]
        return super().dependencias() | ent.dependencias_de(*caras)

    def _condicion(self, cond, ents, i, ctx, estado):
        """La condición guardada para la sección `i`, con el ángulo y el peso evaluados y la cara resuelta (o la de la
        sección)."""
        if not cond:
            return None
        salida = {"tipo": cond.get("tipo", "libre"), "angulo": ctx.evaluar(str(cond.get("angulo", "90 deg")), ANGULO),
                  "peso": ctx.evaluar(str(cond.get("peso", "1")), "escalar"), "alineacion": cond.get("alineacion", "libre")}
        if salida["tipo"] in ("tangente", "suave"):
            e = _resolver(cond["cara"], estado) if cond.get("cara") else ents[i] if -len(ents) <= i < len(ents) else None
            if e is not None and e.tipo == "cara":
                salida["cara"] = e.forma
            elif e is not None and e.tipo == "arista" and e.cuerpo:
                caras = _sf()._caras_de(_sf()._mapa_aristas(estado.cuerpo(e.cuerpo).forma), e.forma)
                salida["cara"] = caras[0] if caras else None
            if salida.get("cara") is None:
                raise ErrorOperacion("La condición Tangente o Suave necesita un perfil que sea el borde de una cara, o "
                                     "elegir esa cara.")
        return salida

    def ejecutar(self, estado, ctx):
        p = self.p
        ents = _resolver_todas(p["secciones"], estado)
        secciones = []
        for e in ents:
            if p["cadena"] and e.tipo in ("arista", "curva_boceto"):
                secciones.append(geo.compuesto(_en_cadena([e], [e.forma], estado)))
            else:
                secciones.append(e.forma if e.forma is not None and e.tipo not in ("vertice",) else ent.como_punto(e))
        rieles, formas_boceto = [], {}
        for r in p["carriles"]:
            ents_riel, aristas = _curvas([r], estado, "el riel")
            riel = _en_cadena(ents_riel, aristas, estado, formas_boceto) if p["cadena"] else aristas
            if not any(a.IsSame(x) for otro in rieles for x in otro for a in riel):     # otro tramo de una cadena ya elegida
                rieles.append(riel)
        central = _curvas(p["linea_central"], estado, "la línea central")[1] if p["linea_central"] else None
        self._nuevo(estado, ctx, _sf().solevar_superficie(
            secciones, cerrada=p["cerrada"], reglada=p["reglada"], rieles=rieles, linea_central=central,
            condicion_inicio=self._condicion(p["condicion_inicio"], ents, 0, ctx, estado),
            condicion_fin=self._condicion(p["condicion_fin"], ents, -1, ctx, estado),
            condiciones_medias={int(k): self._condicion(c, ents, int(k), ctx, estado)
                                for k, c in p["condiciones_medias"].items()},
            fusionar_tangentes=p["fusionar_tangentes"]))


class OpParche(_OpSuperficie):
    """SUPERFICIE › Parche [SFC-PATCH]: cierra un contorno con una superficie. `agrupar` (Group Edges): una
    continuidad para todo el contorno; sin agrupar, `continuidades` da una por cada referencia de `contorno` (vacía =
    la general). `interior`: curvas, aristas o puntos que guían el parche. `invertir`: da vuelta la normal."""
    TIPO, ETIQUETA, ICONO = "parche", "Parche", "◍"
    PARAMS = {"contorno": [], "continuidad": "G0", "agrupar": True, "continuidades": [], "interior": [],
              "invertir": False}
    OPCIONES = {"continuidad": ("G0", "G1", "G2")}
    REFS = ("contorno", "interior")

    def ejecutar(self, estado, ctx):
        p = self.p
        ents, aristas = _curvas(p["contorno"], estado, "el contorno")
        cont = p["continuidad"]
        por = []
        if not p["agrupar"]:
            for ref, c in zip(p["contorno"], p["continuidades"], strict=False):
                if c in ("G0", "G1", "G2"):
                    e = _resolver(ref, estado)
                    if e.forma is not None:
                        por.append((e.forma, c))
        soporte = None
        if cont != "G0" or any(c != "G0" for _, c in por):
            cid = next((e.cuerpo for e in ents if e.cuerpo), None)
            soporte = estado.cuerpo(cid).forma if cid else None
        guias = []
        for e in _resolver_todas(p["interior"], estado):
            guias.append(e.forma if e.forma is not None else ent.como_punto(e))
        forma = _sf().parche(aristas, continuidad=cont, interior=guias, soporte=soporte, por_arista=por)
        self._nuevo(estado, ctx, _sf().invertir_normal(forma) if p["invertir"] else forma)


class OpReglada(_OpSuperficie):
    """SUPERFICIE › Reglada [SFC-RULED]."""
    TIPO, ETIQUETA, ICONO = "reglada", "Superficie reglada", "▥"
    PARAMS = {"aristas": [], "tipo": "normal", "distancia": "10 mm", "angulo": "0 deg", "direccion": None,
              "ingletear": False, "alternas": False}
    EXPRESIONES = ("distancia", "angulo")
    OPCIONES = {"tipo": ("normal", "tangente", "direccion")}
    REFS = ("aristas", "direccion")

    def ejecutar(self, estado, ctx):
        ents, aristas = _curvas(self.p["aristas"], estado, "las aristas")
        cid = next((e.cuerpo for e in ents if e.cuerpo), None)
        referencia = estado.cuerpo(cid).forma if cid else next((e.plano for e in ents if e.plano is not None), None)
        direccion = ent.direccion(_resolver(self.p["direccion"], estado)) if self.p["direccion"] else None
        avisos = []
        self._nuevo(estado, ctx, _sf().reglada(aristas, ctx.evaluar(self.p["distancia"]),
                                               ctx.evaluar(self.p["angulo"], ANGULO), tipo=self.p["tipo"],
                                               direccion=direccion, referencia=referencia,
                                               ingletear=self.p["ingletear"], alternas=self.p["alternas"],
                                               avisos=avisos))
        for texto in avisos:
            ctx.aviso(texto)


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
        antes = c.forma
        c.forma = _sf().recortar(c.forma, herramienta, np.asarray(self.p["punto"], float))
        estado.recortes[c.id] = antes       # SUP-5: Destrimar recupera los límites de la cara sin recortar


class OpDestrimar(_OpSuperficie):
    """SUPERFICIE › Destrimar [SFC-UNTRIM]: `contornos` exteriores, interiores, todos o manual (los de `aristas`);
    `extension` estira los bordes exteriores; `mantener_copia` deja la superficie original como cuerpo aparte."""
    TIPO, ETIQUETA, ICONO = "destrimar", "Destrimar", "◰"
    PARAMS = {"caras": [], "contornos": "exteriores", "aristas": [], "extension": "0 mm", "mantener_copia": False}
    EXPRESIONES = ("extension",)
    OPCIONES = {"contornos": ("exteriores", "interiores", "todos", "manual")}
    REFS = ("caras", "aristas")

    def ejecutar(self, estado, ctx):
        if not self.p["caras"]:
            raise ErrorOperacion("Elegí las caras a destrimar.")
        manual = self.p["contornos"] == "manual"
        elegidas = [e.forma for e in _resolver_todas(self.p["aristas"], estado, ("arista",))] if manual else []
        if manual and not elegidas:
            raise ErrorOperacion("En el modo manual elegí las aristas a destrimar.")
        extension = ctx.evaluar(self.p["extension"])
        for e in _resolver_todas(self.p["caras"], estado, ("cara",)):
            c = estado.cuerpo(e.cuerpo)
            original = _sf().cara_original(e.forma, estado.recortes.get(c.id))
            if manual:                    # las aristas elegidas son las de la cara que se ve, no las de la original
                nueva = _sf().destrimar(e.forma, contornos="manual", aristas=elegidas, extension=extension,
                                        original=original)
            else:
                nueva = _sf().destrimar(original or e.forma, contornos=self.p["contornos"], extension=extension)
            if self.p["mantener_copia"]:
                estado.nuevo_cuerpo(self.id, _sf().descoser(e.forma)[0], "superficie", apariencia=c.apariencia)
            resto = [f for f in geo.caras(c.forma) if not f.IsSame(e.forma)]
            c.forma = _sf().coser(resto + [nueva])["forma"] if resto else nueva


class OpExtenderSup(_OpSuperficie):
    """SUPERFICIE › Extender [SFC-EXTEND]."""
    TIPO, ETIQUETA, ICONO = "extender_sup", "Extender", "⇲"
    PARAMS = {"aristas": [], "distancia": "5 mm", "tipo": "natural", "alineacion": "alinear"}
    EXPRESIONES = ("distancia",)
    OPCIONES = {"tipo": ("natural", "tangente", "perpendicular"), "alineacion": ("libre", "alinear")}
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
            c.forma = _sf().extender(c.forma, aristas, ctx.evaluar(self.p["distancia"]), tipo=self.p["tipo"],
                                     alineacion=self.p["alineacion"])


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
            n = r["aristas_libres"]
            donde = ", ".join(str(q) for q in r["libres_en"][:3]) + ("…" if n > 3 else "")
            ctx.aviso(f"Quedaron {n} {'borde libre' if n == 1 else 'bordes libres'}"
                      + (f" (cerca de {donde} mm)" if donde else "") + ": el resultado sigue siendo una superficie.")


class OpDescoser(_OpSuperficie):
    """SUPERFICIE › Descoser [SFC-UNSTITCH]: cada cara de los `cuerpos` pasa a ser un cuerpo de superficie; con
    `caras` solo esas se separan y lo demás queda cosido en el cuerpo."""
    TIPO, ETIQUETA, ICONO = "descoser", "Descoser", "⧈"
    PARAMS = {"cuerpos": [], "caras": []}
    REFS = ("caras",)

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"] and not self.p["caras"]:
            raise ErrorOperacion("Elegí las caras o los cuerpos a descoser.")
        for cid in self.p["cuerpos"]:
            c = estado.cuerpo(cid)
            caras = _sf().descoser(c.forma)
            del estado.cuerpos[c.id]
            for cara in caras:
                estado.nuevo_cuerpo(self.id, cara, "superficie", apariencia=c.apariencia)
        por_cuerpo = {}
        for e in _resolver_todas(self.p["caras"], estado, ("cara",)):
            if e.cuerpo in estado.cuerpos:
                por_cuerpo.setdefault(e.cuerpo, []).append(e.forma)
        for cid, formas in por_cuerpo.items():
            c = estado.cuerpo(cid)
            resto, sueltas = _sf().descoser_caras(c.forma, formas)
            if resto is None:
                del estado.cuerpos[c.id]
            else:
                c.forma, c.tipo = resto, "superficie"
            for cara in sueltas:
                estado.nuevo_cuerpo(self.id, cara, "superficie", apariencia=c.apariencia)


class OpInvertirNormal(_OpSuperficie):
    """SUPERFICIE › Invertir normal [GUID-3B2D0A04]."""
    TIPO, ETIQUETA, ICONO = "invertir_normal", "Invertir normal", "⇅"
    PARAMS = {"cuerpos": []}

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos a invertir la normal.")
        for cid in self.p["cuerpos"]:
            c = estado.cuerpo(cid)
            c.forma = _sf().invertir_normal(c.forma)


class OpEngrosar(_OpSuperficie):
    """CREAR › Engrosar [GUID-471827A2]: da espesor a caras o superficies (cuerpo nuevo o booleana).
    `tipo`: "agudo" (Sharp Thicken, esquinas en punta) o "redondeado" (Rounded Thicken). `cadena` (Chain Selection)
    suma a cada cara de un cuerpo las que le siguen tangentes."""
    TIPO, ETIQUETA, ICONO = "engrosar", "Engrosar", "▤"
    PARAMS = {"caras": [], "espesor": "2 mm", "direccion": "un_lado", "tipo": "agudo", "operacion": "nuevo",
              "objetivos": [], "cadena": False}
    EXPRESIONES = ("espesor",)
    OPCIONES = {"direccion": ("un_lado", "simetrica"), "tipo": ("agudo", "redondeado"),
                "operacion": OPERACIONES_CUERPO}
    REFS = ("caras",)

    def ejecutar(self, estado, ctx):
        ents = _resolver_todas(self.p["caras"], estado)
        if not ents:
            raise ErrorOperacion("Elegí las caras o superficies a engrosar.")
        formas = [e.forma for e in ents]
        if self.p.get("cadena"):
            from ..nucleo.solidos_modificar import caras_en_cadena
            formas = [e.forma for e in ents if e.tipo != "cara"]
            cuerpos = dict.fromkeys(e.cuerpo for e in ents if e.tipo == "cara")
            for cid in cuerpos:
                formas += caras_en_cadena(estado.cuerpo(cid).forma, [e.forma for e in ents if e.tipo == "cara" and e.cuerpo == cid])
        base = geo.compuesto(formas) if len(formas) > 1 else formas[0]
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


class _Cascaron:
    """Primitiva de superficie [SFC-CREATE-SURFACE-PRIMITIVE]: el paso sólido de la misma forma, del que queda el cascarón
    como cuerpo de superficie. Fusion las limita al modelado directo; acá van en el timeline como cualquier paso."""

    def ejecutar(self, estado, ctx):
        antes = set(estado.cuerpos)
        super().ejecutar(estado, ctx)
        for cid in set(estado.cuerpos) - antes:
            c = estado.cuerpo(cid)
            c.forma, c.tipo = _sf().primitiva_superficie(c.forma), "superficie"


class OpSupPrimitiva(_Cascaron, OpPrimitiva):
    """SUPERFICIE › Caja, Cilindro, Esfera y Toroide [SFC-BOX, SFC-CYLINDER, SFC-SPHERE, SFC-TORUS]."""
    TIPO = "sup_primitiva"


class OpSupBobina(_Cascaron, OpBobina):
    """SUPERFICIE › Bobina [SFC-COIL]."""
    TIPO, ETIQUETA = "sup_bobina", "Bobina de superficie"


class OpSupTuberia(_Cascaron, OpTuberia):
    """SUPERFICIE › Tubería [SFC-PIPE]."""
    TIPO, ETIQUETA = "sup_tuberia", "Tubería de superficie"


registrar_operacion(OpSupExtruir, OpSupRevolucion, OpSupBarrido, OpSupSolevacion, OpParche, OpReglada, OpSupDesfase,
                    OpRecortar, OpDestrimar, OpExtenderSup, OpCoser, OpDescoser, OpInvertirNormal, OpEngrosar,
                    OpSupEmpalme, OpSupPrimitiva, OpSupBobina, OpSupTuberia)
