# -*- coding: utf-8 -*-
"""
Operaciones de SÓLIDO › CREAR (además de Extruir, Revolución y las primitivas de `operaciones.py`):
barrido, solevación, nervio, red, repujado, agujero, rosca, bobina, tubería, patrones (rectangular,
circular y en ruta), simetría, relleno de contorno, sólido envolvente y las de plástico (saliente, labio).
El núcleo geométrico está en `nucleo/solidos_crear.py`.
"""
import numpy as np

from ..nucleo import geometria as geo
from . import entidades as ent
from .operaciones import (ANGULO, ErrorOperacion, Operacion, _deps_objetivo, _resolver, _resolver_todas,
                          aplicar_resultado, registrar_operacion)


def _sc():
    from ..nucleo import solidos_crear
    return solidos_crear


def _caras(refs, estado, que="perfiles"):
    """(plano, caras) de perfiles de boceto y caras planas."""
    ents = _resolver_todas(refs, estado)
    caras = [e.forma for e in ents if e.forma is not None and e.tipo in ("perfil", "cara")]
    if not caras:
        raise ErrorOperacion(f"Elegí {que}.")
    plano = next((e.plano for e in ents if e.plano is not None), None)
    return plano, caras


def _aristas(refs, estado, que="curvas"):
    ents = _resolver_todas(refs, estado)
    aristas = [e.forma for e in ents if e.forma is not None]
    if not aristas:
        raise ErrorOperacion(f"Elegí {que}.")
    return ents, aristas


def _cuerpo_objetivo(estado, ents, p):
    """El cuerpo sobre el que trabaja un nervio/red/repujado: el elegido o el sólido más cercano a la curva."""
    if p.get("objetivo"):
        return estado.cuerpo(p["objetivo"])
    solidos = [c for c in estado.cuerpos.values() if getattr(c, "tipo", "solido") == "solido"]
    if not solidos:
        raise ErrorOperacion("No hay un cuerpo sólido sobre el que trabajar.")
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    forma = ents[0].forma
    return min(solidos, key=lambda c: BRepExtrema_DistShapeShape(c.forma, forma).Value())


class _OpCrear(Operacion):
    REFS = ()

    def dependencias(self):
        p = self.p
        return (ent.dependencias_de(*(p.get(k) for k in self.REFS)) | _deps_objetivo(p.get("objetivos")) |
                _deps_objetivo(p.get("objetivo")) | _deps_objetivo(p.get("cuerpos"))) - {self.id}

    def _aplicar(self, estado, ctx, forma, operacion=None):
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, operacion or self.p.get("operacion", "nuevo"),
                                                 self.p.get("objetivos") or ""))


class OpBarrido(_OpCrear):
    """Barrido de Fusion [SLD-SWEEP-SOLID]: tipo ruta única o ruta + carril guía; distancia, orientación,
    ángulo de torsión y de conicidad."""
    TIPO, ETIQUETA, ICONO = "barrido", "Barrido", "↝"
    PARAMS = {"perfiles": [], "ruta": [], "carril": [], "orientacion": "perpendicular", "distancia": "1",
              "torsion": "0 deg", "conicidad": "0 deg", "escala_carril": "escalar", "operacion": "nuevo",
              "objetivos": []}
    EXPRESIONES = ("distancia", "torsion", "conicidad")
    REFS = ("perfiles", "ruta", "carril")

    def ejecutar(self, estado, ctx):
        _, caras = _caras(self.p["perfiles"], estado)
        _, ruta = _aristas(self.p["ruta"], estado, "la ruta")
        carril = _aristas(self.p["carril"], estado)[1] if self.p["carril"] else None
        forma = _sc().barrer(caras, ruta, carril=carril, orientacion=self.p["orientacion"],
                             distancia=ctx.evaluar(self.p["distancia"], "escalar"),
                             torsion=ctx.evaluar(self.p["torsion"], ANGULO),
                             conicidad=ctx.evaluar(self.p["conicidad"], ANGULO), escala_carril=self.p["escala_carril"])
        self._aplicar(estado, ctx, forma)


class OpSolevacion(_OpCrear):
    """Solevación de Fusion [SLD-LOFT-SOLID]: perfiles en orden (o un punto en los extremos), carril o
    línea central, cerrada y tramos rectos."""
    TIPO, ETIQUETA, ICONO = "solevacion", "Solevación", "⌓"
    PARAMS = {"secciones": [], "carriles": [], "linea_central": [], "cerrada": False, "reglada": False,
              "operacion": "nuevo", "objetivos": []}
    REFS = ("secciones", "carriles", "linea_central")

    def ejecutar(self, estado, ctx):
        secciones = []
        for e in _resolver_todas(self.p["secciones"], estado):
            secciones.append(e.forma if e.forma is not None and e.tipo != "vertice" else ent.como_punto(e))
        if len(secciones) < 2:
            raise ErrorOperacion("Elegí al menos dos perfiles, en orden.")
        carriles = [_aristas([r], estado)[1] for r in self.p["carriles"]]
        central = _aristas(self.p["linea_central"], estado)[1] if self.p["linea_central"] else None
        forma = _sc().solevar(secciones, carriles=[c[0] if len(c) == 1 else c for c in carriles], linea_central=central,
                              cerrada=self.p["cerrada"], reglada=self.p["reglada"])
        self._aplicar(estado, ctx, forma)


class OpNervio(_OpCrear):
    """Nervio de Fusion [SLD-RIB]: pared desde una curva abierta del boceto hasta el cuerpo."""
    TIPO, ETIQUETA, ICONO = "nervio", "Nervio", "⊥"
    PARAMS = {"curvas": [], "espesor": "2 mm", "extension": "hasta_siguiente", "profundidad": "10 mm",
              "direccion": "simetrica", "invertir": False, "objetivo": ""}
    EXPRESIONES = ("espesor", "profundidad")
    REFS = ("curvas",)

    def ejecutar(self, estado, ctx):
        ents, aristas = _aristas(self.p["curvas"], estado)
        plano = next((e.plano for e in ents if e.plano is not None), None)
        if plano is None:
            raise ErrorOperacion("El nervio se dibuja con curvas de un boceto.")
        cuerpo = _cuerpo_objetivo(estado, ents, self.p)
        prof = ctx.evaluar(self.p["profundidad"]) if self.p["extension"] == "profundidad" else None
        forma = _sc().nervio(cuerpo.forma, aristas, plano.normal, ctx.evaluar(self.p["espesor"]), profundidad=prof,
                             direccion=self.p["direccion"], invertir=self.p["invertir"])
        cuerpo.forma = geo.booleano(cuerpo.forma, forma, "unir")
        self._registrar_usados([cuerpo.id])


class OpRed(OpNervio):
    """Red de Fusion [SLD-WEB]: varias curvas abiertas extruidas perpendiculares al boceto hasta el cuerpo."""
    TIPO, ETIQUETA, ICONO = "red", "Red", "#"

    def ejecutar(self, estado, ctx):
        ents, aristas = _aristas(self.p["curvas"], estado)
        plano = next((e.plano for e in ents if e.plano is not None), None)
        if plano is None:
            raise ErrorOperacion("La red se dibuja con curvas de un boceto.")
        cuerpo = _cuerpo_objetivo(estado, ents, self.p)
        prof = ctx.evaluar(self.p["profundidad"]) if self.p["extension"] == "profundidad" else None
        n = -plano.normal if self.p["invertir"] else plano.normal
        forma = _sc().red(cuerpo.forma, aristas, n, ctx.evaluar(self.p["espesor"]), prof, direccion=self.p["direccion"])
        cuerpo.forma = geo.booleano(cuerpo.forma, forma, "unir")
        self._registrar_usados([cuerpo.id])


class OpRepujado(_OpCrear):
    """Repujado de Fusion [SLD-EMBOSS]: relieve o grabado de perfiles (o texto) sobre una cara plana o
    envuelto en un cilindro."""
    TIPO, ETIQUETA, ICONO = "repujado", "Repujado", "Ⓐ"
    PARAMS = {"perfiles": [], "cara": None, "profundidad": "1 mm", "tipo": "relieve", "envolver": False}
    EXPRESIONES = ("profundidad",)
    REFS = ("perfiles", "cara")

    def ejecutar(self, estado, ctx):
        _, caras = _caras(self.p["perfiles"], estado)
        if not self.p["cara"]:
            raise ErrorOperacion("Elegí la cara sobre la que va el repujado.")
        e = _resolver(self.p["cara"], estado)
        cuerpo = estado.cuerpo(e.cuerpo)
        cuerpo.forma = _sc().repujado(cuerpo.forma, caras, e.forma, ctx.evaluar(self.p["profundidad"]),
                                      tipo=self.p["tipo"], envolver=self.p["envolver"])
        self._registrar_usados([cuerpo.id])


class OpAgujero(_OpCrear):
    """Agujero de Fusion [GUID-0DFCBD4F]: en puntos de boceto, vértices o puntos sobre una cara; simple,
    abocardado o avellanado; extensión distancia o todo; punta plana o en ángulo; simple o roscado."""
    TIPO, ETIQUETA, ICONO = "agujero", "Agujero", "◎"
    PARAMS = {"posiciones": [], "puntos_cara": [], "tipo": "simple", "diametro": "6 mm", "extension": "distancia",
              "profundidad": "10 mm", "punta": "angulo", "angulo_punta": "118 deg", "diam_abocardado": "10 mm",
              "prof_abocardado": "4 mm", "diam_avellanado": "12 mm", "angulo_avellanado": "90 deg",
              "rosca": "simple", "designacion": "M6", "invertir": False, "objetivos": []}
    EXPRESIONES = ("diametro", "profundidad", "angulo_punta", "diam_abocardado", "prof_abocardado", "diam_avellanado",
                   "angulo_avellanado")
    REFS = ("posiciones",)

    def dependencias(self):
        return super().dependencias() | ent.dependencias_de([d["cara"] for d in self.p.get("puntos_cara") or []])

    def _colocaciones(self, estado):
        salida = []
        for e in _resolver_todas(self.p["posiciones"], estado):
            n = e.plano.normal if e.plano is not None else np.array([0.0, 0.0, 1.0])
            salida.append((ent.como_punto(e), -n))
        for d in self.p.get("puntos_cara") or []:
            e = _resolver(d["cara"], estado)
            if e.plano is None:
                raise ErrorOperacion("El agujero va sobre una cara plana.")
            p = np.asarray(d["punto"], float)
            salida.append((e.plano.origen + (p - e.plano.origen) - e.plano.normal * float((p - e.plano.origen) @
                                                                                          e.plano.normal),
                           -e.plano.normal))
        if not salida:
            raise ErrorOperacion("Elegí dónde van los agujeros (puntos de boceto o un punto sobre una cara).")
        return [(p, -d if self.p["invertir"] else d) for p, d in salida]

    def ejecutar(self, estado, ctx):
        p, sc = self.p, _sc()
        A = lambda k: ctx.evaluar(p[k], ANGULO)  # noqa: E731
        L = lambda k: ctx.evaluar(p[k])  # noqa: E731
        opciones = {"tipo": p["tipo"], "diametro": L("diametro"), "punta": p["punta"], "angulo_punta": A("angulo_punta"),
                    "roscado": p["designacion"] if p["rosca"] == "modelada" else None}
        if p["tipo"] == "abocardado":
            opciones.update(diam_abocardado=L("diam_abocardado"), prof_abocardado=L("prof_abocardado"))
        elif p["tipo"] == "avellanado":
            opciones.update(diam_avellanado=L("diam_avellanado"), angulo_avellanado=A("angulo_avellanado"))
        solidos = [c.forma for c in estado.cuerpos.values() if getattr(c, "tipo", "solido") == "solido"]
        if not solidos:
            raise ErrorOperacion("No hay cuerpos sólidos para agujerear.")
        todo = geo.compuesto(solidos)
        herramientas = []
        for punto, direccion in self._colocaciones(estado):
            if p["extension"] == "todo":
                herramientas.append(sc.agujero(todo, punto, direccion, profundidad=None, **opciones))
            else:
                herramientas.append(sc.herramienta_agujero(punto, direccion, profundidad=L("profundidad"), **opciones))
        if p["rosca"] == "cosmetica":
            ctx.aviso(f"Rosca cosmética {p['designacion']}: no cambia la geometría.")
        self._aplicar(estado, ctx, geo.unir_todos(herramientas), "cortar")


class OpRosca(_OpCrear):
    """Rosca de Fusion [GUID-7BD8CD24]: sobre una cara cilíndrica, tamaño automático o elegido, largo completo o
    con desfase, cosmética o modelada, mano derecha o izquierda."""
    TIPO, ETIQUETA, ICONO = "rosca", "Rosca", "⌇"
    PARAMS = {"caras": [], "designacion": "", "largo_completo": True, "longitud": "10 mm", "desfase": "0 mm",
              "modelada": True, "mano": "derecha", "invertir": False}
    EXPRESIONES = ("longitud", "desfase")
    REFS = ("caras",)

    def ejecutar(self, estado, ctx):
        ents = _resolver_todas(self.p["caras"], estado)
        if not ents:
            raise ErrorOperacion("Elegí las caras cilíndricas a roscar.")
        for e in ents:
            cuerpo = estado.cuerpo(e.cuerpo)
            cuerpo.forma = _sc().rosca(cuerpo.forma, e.forma, designacion=self.p["designacion"] or None,
                                       longitud=None if self.p["largo_completo"] else ctx.evaluar(self.p["longitud"]),
                                       desfase=ctx.evaluar(self.p["desfase"]), modelada=self.p["modelada"],
                                       mano=self.p["mano"], invertir=self.p["invertir"])
            if not self.p["modelada"]:
                ctx.aviso("Rosca cosmética: la geometría no cambia (como la rosca no modelada de Fusion).")


class OpBobina(_OpCrear):
    """Bobina de Fusion [SLD-COIL-SOLID]: plano/cara + centro, diámetro, tipo (revoluciones y altura,
    revoluciones y paso, altura y paso), ángulo, sección y su posición."""
    TIPO, ETIQUETA, ICONO = "bobina", "Bobina", "➰"
    PARAMS = {"plano": None, "centro": None, "diametro": "20 mm", "tipo": "rev_altura", "revoluciones": "5",
              "altura": "30 mm", "paso": "6 mm", "angulo": "0 deg", "seccion": "circular", "tamano": "3 mm",
              "posicion": "sobre", "horario": False, "operacion": "nuevo", "objetivos": []}
    EXPRESIONES = ("diametro", "revoluciones", "altura", "paso", "angulo", "tamano")
    REFS = ("plano", "centro")

    def ejecutar(self, estado, ctx):
        p = self.p
        plano = ent.como_plano(_resolver(p["plano"], estado)) if p["plano"] else geo.Plano("XY")
        centro = ent.como_punto(_resolver(p["centro"], estado)) if p["centro"] else plano.origen
        datos = {"revoluciones": None, "altura": None, "paso": None}
        for k in {"rev_altura": ("revoluciones", "altura"), "rev_paso": ("revoluciones", "paso"),
                  "altura_paso": ("altura", "paso")}[p["tipo"]]:
            datos[k] = ctx.evaluar(p[k], "escalar" if k == "revoluciones" else "longitud")
        forma = _sc().bobina(centro, plano.normal, diametro=ctx.evaluar(p["diametro"]), angulo=ctx.evaluar(p["angulo"], ANGULO),
                             seccion=p["seccion"], tamano_seccion=ctx.evaluar(p["tamano"]), posicion_seccion=p["posicion"],
                             horario=p["horario"], eje_x=plano.u, **datos)
        self._aplicar(estado, ctx, forma)


class OpTuberia(_OpCrear):
    """Tubería de Fusion [SLD-PIPE-SOLID]: ruta, distancia, sección y tamaño, hueca con espesor."""
    TIPO, ETIQUETA, ICONO = "tuberia", "Tubería", "⊃"
    PARAMS = {"ruta": [], "distancia": "1", "seccion": "circular", "tamano": "5 mm", "hueca": False,
              "espesor": "0.5 mm", "operacion": "nuevo", "objetivos": []}
    EXPRESIONES = ("distancia", "tamano", "espesor")
    REFS = ("ruta",)

    def ejecutar(self, estado, ctx):
        _, ruta = _aristas(self.p["ruta"], estado, "la ruta")
        forma = _sc().tuberia(ruta, seccion=self.p["seccion"], tamano=ctx.evaluar(self.p["tamano"]),
                              hueca=self.p["hueca"], espesor=ctx.evaluar(self.p["espesor"]),
                              distancia=ctx.evaluar(self.p["distancia"], "escalar"))
        self._aplicar(estado, ctx, forma)


class OpPatron(_OpCrear):
    """Patrón rectangular, circular o en ruta de Fusion [SLD-PATTERNS] sobre cuerpos (o componentes): cada
    instancia es un cuerpo nuevo (o se une al original con «Combinar»)."""
    TIPO, ETIQUETA, ICONO = "patron", "Patrón", "⁂"
    PARAMS = {"forma_patron": "rectangular", "cuerpos": [], "dir1": None, "n1": 3, "d1": "30 mm", "dir2": None,
              "n2": 1, "d2": "30 mm", "distribucion": "extension", "simetrico": False, "eje": None, "n": 6,
              "angulo": "360 deg", "ruta": [], "orientacion": "identica", "inicio": "0", "suprimir": [],
              "combinar": False}
    EXPRESIONES = ("d1", "d2", "angulo", "inicio")
    REFS = ("dir1", "dir2", "eje", "ruta")

    def transformaciones(self, estado, ctx):
        p, sc = self.p, _sc()
        sup = tuple(int(i) for i in p.get("suprimir") or [])
        if p["forma_patron"] == "rectangular":
            if not p["dir1"]:
                raise ErrorOperacion("Elegí la dirección 1.")
            d1 = ent.direccion(_resolver(p["dir1"], estado))
            d2 = ent.direccion(_resolver(p["dir2"], estado)) if p["dir2"] else None
            return sc.transformaciones_rectangulares(d1, int(p["n1"]), ctx.evaluar(p["d1"]), d2, int(p["n2"]),
                                                     ctx.evaluar(p["d2"]), distribucion=p["distribucion"],
                                                     simetrico1=p["simetrico"], simetrico2=p["simetrico"], suprimir=sup)
        if p["forma_patron"] == "circular":
            if not p["eje"]:
                raise ErrorOperacion("Elegí el eje.")
            punto, eje = ent.como_eje(_resolver(p["eje"], estado))
            return sc.transformaciones_circulares(punto, eje, int(p["n"]), angulo_total=ctx.evaluar(p["angulo"], ANGULO),
                                                  distribucion="completa" if p["distribucion"] == "extension"
                                                  else "espaciado", simetrico=p["simetrico"], suprimir=sup)
        _, ruta = _aristas(p["ruta"], estado, "la ruta")
        return sc.transformaciones_en_ruta(ruta, int(p["n1"]), ctx.evaluar(p["d1"]), orientacion=p["orientacion"],
                                           inicio=ctx.evaluar(p["inicio"], "escalar"), distribucion=p["distribucion"],
                                           simetrico=p["simetrico"], suprimir=sup)

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos del patrón.")
        trsfs = self.transformaciones(estado, ctx)[1:]          # la primera es el original
        for cid in self.p["cuerpos"]:
            c = estado.cuerpo(cid)
            copias = [_sc().aplicar(c.forma, t) for t in trsfs]
            if self.p["combinar"]:
                c.forma = geo.unir_todos([c.forma] + copias)
            else:
                for forma in copias:
                    estado.nuevo_cuerpo(self.id, forma, c.tipo, apariencia=c.apariencia, material=c.material,
                                        componente=c.componente)


class OpSimetria(_OpCrear):
    """Simetría de Fusion [GUID-77CE43FF]: copia cuerpos reflejados en un plano (nuevos o unidos)."""
    TIPO, ETIQUETA, ICONO = "simetria", "Simetría", "⇋"
    PARAMS = {"cuerpos": [], "plano": None, "combinar": False}
    REFS = ("plano",)

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"] or not self.p["plano"]:
            raise ErrorOperacion("Elegí los cuerpos y el plano de simetría.")
        plano = ent.como_plano(_resolver(self.p["plano"], estado))
        for cid in self.p["cuerpos"]:
            c = estado.cuerpo(cid)
            reflejo = _sc().simetria(c.forma, plano)
            if self.p["combinar"]:
                c.forma = geo.booleano(c.forma, reflejo, "unir")
            else:
                estado.nuevo_cuerpo(self.id, reflejo, c.tipo, apariencia=c.apariencia, material=c.material,
                                    componente=c.componente)


class OpRellenoContorno(_OpCrear):
    """Relleno de contorno de Fusion [GUID-575E005F]: las herramientas (cuerpos, caras, planos) forman celdas
    cerradas y las elegidas pasan a ser sólido."""
    TIPO, ETIQUETA, ICONO = "relleno_contorno", "Relleno de contorno", "▩"
    PARAMS = {"herramientas": [], "celdas": [], "operacion": "nuevo", "objetivos": []}
    REFS = ("herramientas",)

    def formas_herramienta(self, estado):
        formas = []
        for e in _resolver_todas(self.p["herramientas"], estado):
            formas.append(e.plano if e.tipo == "plano" else e.forma)
        if len(formas) < 1:
            raise ErrorOperacion("Elegí las herramientas que encierran el volumen.")
        return formas

    def ejecutar(self, estado, ctx):
        celdas = self.p["celdas"] or [0]
        forma = _sc().relleno_contorno(self.formas_herramienta(estado), [int(i) for i in celdas])
        self._aplicar(estado, ctx, forma)


class OpSolidoEnvolvente(_OpCrear):
    """Sólido envolvente de Fusion [SLD-CREATE-BOUNDING-SOLID]: caja o cilindro que contiene los cuerpos."""
    TIPO, ETIQUETA, ICONO = "solido_envolvente", "Sólido envolvente", "⬚"
    PARAMS = {"cuerpos": [], "tipo": "caja", "margen": "0 mm", "eje": "z", "operacion": "nuevo", "objetivos": []}
    EXPRESIONES = ("margen",)

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos.")
        formas = [estado.cuerpo(c).forma for c in self.p["cuerpos"]]
        forma = _sc().solido_envolvente(formas, tipo=self.p["tipo"], margen=ctx.evaluar(self.p["margen"]),
                                        eje=self.p["eje"])
        self._aplicar(estado, ctx, forma)


class OpSaliente(_OpCrear):
    """Saliente (Boss) de PLÁSTICO [SLD-BOSS], simplificado: columna con agujero que nace en un punto."""
    TIPO, ETIQUETA, ICONO = "saliente", "Saliente", "⌾"
    PARAMS = {"posiciones": [], "diametro_exterior": "8 mm", "diametro_agujero": "3 mm", "altura": "",
              "profundidad_agujero": "", "angulo_desmoldeo": "0 deg", "invertir": False}
    EXPRESIONES = ("diametro_exterior", "diametro_agujero", "angulo_desmoldeo")
    REFS = ("posiciones",)

    def ejecutar(self, estado, ctx):
        ents = _resolver_todas(self.p["posiciones"], estado)
        if not ents:
            raise ErrorOperacion("Elegí puntos de boceto donde van los salientes.")
        L = lambda k: ctx.evaluar(self.p[k]) if str(self.p.get(k) or "").strip() else None  # noqa: E731
        for e in ents:
            n = e.plano.normal if e.plano is not None else np.array([0.0, 0.0, 1.0])
            d = n if self.p["invertir"] else -n
            cuerpo = _cuerpo_objetivo(estado, [e] if e.forma is not None else
                                      [ent.Entidad("punto", forma=_vertice(ent.como_punto(e)))], self.p)
            cuerpo.forma = _sc().saliente(cuerpo.forma, ent.como_punto(e), d, diametro_exterior=L("diametro_exterior"),
                                          diametro_agujero=L("diametro_agujero"), altura=L("altura"),
                                          profundidad_agujero=L("profundidad_agujero"),
                                          angulo_desmoldeo=ctx.evaluar(self.p["angulo_desmoldeo"], ANGULO))
            self._registrar_usados([cuerpo.id])


def _vertice(p):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.gp import gp_Pnt
    return BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, p))).Vertex()


class OpLabio(_OpCrear):
    """Labio / ranura de PLÁSTICO [SLD-LIP], simplificado: sección rectangular a lo largo del borde."""
    TIPO, ETIQUETA, ICONO = "labio", "Labio", "⊓"
    PARAMS = {"aristas": [], "tipo": "labio", "ancho": "1 mm", "alto": "1.5 mm", "holgura": "0.1 mm",
              "direccion": None, "invertir": False}
    EXPRESIONES = ("ancho", "alto", "holgura")
    REFS = ("aristas", "direccion")

    def ejecutar(self, estado, ctx):
        ents, aristas = _aristas(self.p["aristas"], estado, "las aristas del borde")
        cuerpo = estado.cuerpo(ents[0].cuerpo)
        d = ent.direccion(_resolver(self.p["direccion"], estado)) if self.p["direccion"] else np.array([0, 0, 1.0])
        cuerpo.forma = _sc().labio_ranura(cuerpo.forma, aristas, -d if self.p["invertir"] else d, tipo=self.p["tipo"],
                                          ancho=ctx.evaluar(self.p["ancho"]), alto=ctx.evaluar(self.p["alto"]),
                                          holgura=ctx.evaluar(self.p["holgura"]))
        self._registrar_usados([cuerpo.id])


registrar_operacion(OpBarrido, OpSolevacion, OpNervio, OpRed, OpRepujado, OpAgujero, OpRosca, OpBobina, OpTuberia,
                    OpPatron, OpSimetria, OpRellenoContorno, OpSolidoEnvolvente, OpSaliente, OpLabio)
