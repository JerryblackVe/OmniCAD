# -*- coding: utf-8 -*-
"""
Operaciones de SÓLIDO › CREAR (además de Extruir, Revolución y las primitivas de `operaciones.py`):
barrido, solevación, nervio, red, repujado, agujero, rosca, bobina, tubería, patrones (rectangular,
circular, en ruta con giro y en puntos; de cuerpos o de operaciones), multitransformación, simetría, relleno de
contorno, sólido envolvente y las de plástico (saliente, labio).
El núcleo geométrico está en `nucleo/solidos_crear.py`.
"""
import numpy as np

from ..nucleo import geometria as geo
from . import entidades as ent
from .operaciones import (ANGULO, OPERACIONES_CUERPO, ErrorOperacion, Operacion, ParametroMalFormado, _deps_objetivo, _resolver,
                          _resolver_todas, aplicar_resultado, atributos_copia, registrar_operacion)

ESPESORES = ("simetrica", "lado1", "lado2")     # dirección del espesor de nervio y red (nucleo.solidos_crear)


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
    OPCIONES = {"orientacion": ("perpendicular", "paralela"), "escala_carril": ("escalar", "estirar", "ninguna"),
                "operacion": OPERACIONES_CUERPO}
    REFS = ("perfiles", "ruta", "carril")

    def ejecutar(self, estado, ctx):
        _, caras = _caras(self.p["perfiles"], estado)
        _, ruta = _aristas(self.p["ruta"], estado, "la ruta")
        carril = _aristas(self.p["carril"], estado)[1] if self.p["carril"] else None
        forma = _sc().barrer(caras, ruta, carril=carril, orientacion=self.p["orientacion"],
                             distancia=ctx.evaluar(self.p["distancia"], "escalar"),
                             torsion=ctx.evaluar(self.p["torsion"], ANGULO),
                             conicidad=ctx.evaluar(self.p["conicidad"], ANGULO), escala_carril=self.p["escala_carril"])
        if geo.sin_volumen(forma):
            raise ErrorOperacion("El barrido no encierra volumen: el plano del perfil no puede ser paralelo a la ruta.")
        self._aplicar(estado, ctx, forma)


class OpSolevacion(_OpCrear):
    """Solevación de Fusion [SLD-LOFT-SOLID]: perfiles en orden (o un punto en los extremos), carril o
    línea central, cerrada y tramos rectos."""
    TIPO, ETIQUETA, ICONO = "solevacion", "Solevación", "⌓"
    PARAMS = {"secciones": [], "carriles": [], "linea_central": [], "cerrada": False, "reglada": False,
              "operacion": "nuevo", "objetivos": []}
    OPCIONES = {"operacion": OPERACIONES_CUERPO}
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
        if geo.sin_volumen(forma):
            raise ErrorOperacion("La solevación no encierra volumen: los perfiles no pueden estar todos en el mismo "
                                 "plano y una solevación cerrada no puede volver sobre sí misma.")
        self._aplicar(estado, ctx, forma)


class OpNervio(_OpCrear):
    """Nervio de Fusion [SLD-RIB]: pared desde una curva abierta del boceto hasta el cuerpo."""
    TIPO, ETIQUETA, ICONO = "nervio", "Nervio", "⊥"
    PARAMS = {"curvas": [], "espesor": "2 mm", "extension": "hasta_siguiente", "profundidad": "10 mm",
              "direccion": "simetrica", "invertir": False, "objetivo": ""}
    EXPRESIONES = ("espesor", "profundidad")
    OPCIONES = {"extension": ("hasta_siguiente", "profundidad"), "direccion": ESPESORES}
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
    OPCIONES = {"tipo": ("relieve", "grabado")}
    REFS = ("perfiles", "cara")

    def ejecutar(self, estado, ctx):
        _, caras = _caras(self.p["perfiles"], estado)
        if not self.p["cara"]:
            raise ErrorOperacion("Elegí la cara sobre la que va el repujado.")
        e = _resolver(self.p["cara"], estado, ("cara",))
        cuerpo = estado.cuerpo(e.cuerpo)
        cuerpo.forma = _sc().repujado(cuerpo.forma, caras, e.forma, ctx.evaluar(self.p["profundidad"]),
                                      tipo=self.p["tipo"], envolver=self.p["envolver"])
        self._registrar_usados([cuerpo.id])


# Tipos de rosca: las claves de nucleo.solidos_crear.FAMILIAS_ROSCA (acá sin cargar el núcleo; un test las compara)
FAMILIAS_ROSCA = ("iso_metrica", "unificada", "trapezoidal", "acme", "bsp_paralela", "bsp_conica", "npt")


def _tol():
    from ..nucleo import tolerancias
    return tolerancias


class OpAgujero(_OpCrear):
    """Agujero de Fusion [GUID-0DFCBD4F, GUID-3A76B269]: posición en puntos de boceto, vértices, puntos sobre una
    cara o por referencias (dos aristas y dos distancias); simple, abocardado o avellanado; extensión distancia,
    todo o hasta (cara, plano o cuerpo); punta plana o en ángulo; rosca simple, con holgura (ISO 273), roscado
    cosmético o modelado (con clase y holgura para impresión 3D) o roscado cónico (tubería R/NPT)."""
    TIPO, ETIQUETA, ICONO = "agujero", "Agujero", "◎"
    # Las claves que siguen a "objetivos" son nuevas: una receta vieja que no las tiene se calcula igual que antes.
    PARAMS = {"posiciones": [], "puntos_cara": [], "tipo": "simple", "diametro": "6 mm", "extension": "distancia",
              "profundidad": "10 mm", "punta": "angulo", "angulo_punta": "118 deg", "diam_abocardado": "10 mm",
              "prof_abocardado": "4 mm", "diam_avellanado": "12 mm", "angulo_avellanado": "90 deg",
              "rosca": "simple", "designacion": "M6", "invertir": False, "objetivos": [],
              "clase_rosca": "", "holgura_3d": "0 mm", "mano": "derecha", "ajuste": "normal", "hasta": None,
              "desfase_hasta": "0 mm", "ref_cara": None, "ref_aristas": [], "ref_distancia1": "10 mm",
              "ref_distancia2": "10 mm"}
    EXPRESIONES = ("diametro", "profundidad", "angulo_punta", "diam_abocardado", "prof_abocardado", "diam_avellanado",
                   "angulo_avellanado", "holgura_3d", "desfase_hasta", "ref_distancia1", "ref_distancia2")
    OPCIONES = {"tipo": ("simple", "abocardado", "avellanado"), "extension": ("distancia", "todo", "hasta"),
                "punta": ("angulo", "plana"), "rosca": ("simple", "holgura", "cosmetica", "modelada", "conico"),
                "ajuste": ("fino", "normal", "grueso"), "mano": ("derecha", "izquierda")}
    REFS = ("posiciones", "hasta", "ref_cara", "ref_aristas")

    def dependencias(self):
        return super().dependencias() | ent.dependencias_de([d["cara"] for d in self.p.get("puntos_cara") or [] if isinstance(d, dict) and "cara" in d])

    def _colocaciones(self, estado, ctx=None):
        """[(punto, dirección hacia el material)] de cada agujero. La posición por referencias necesita `ctx`
        para evaluar sus distancias (sin él no se incluye)."""
        salida = []
        for e in _resolver_todas(self.p["posiciones"], estado):
            n = e.plano.normal if e.plano is not None else np.array([0.0, 0.0, 1.0])
            salida.append((ent.como_punto(e), -n))
        for d in self.p.get("puntos_cara") or []:
            if not isinstance(d, dict) or "cara" not in d:
                raise ParametroMalFormado(d, 'se esperaba {"cara": <referencia de cara>, "punto": [x, y, z]}', "puntos_cara")
            e = _resolver(d["cara"], estado, ("cara",))
            if e.plano is None:
                raise ErrorOperacion("El agujero va sobre una cara plana.")
            p = np.asarray(d["punto"], float)
            salida.append((e.plano.origen + (p - e.plano.origen) - e.plano.normal * float((p - e.plano.origen) @
                                                                                          e.plano.normal),
                           -e.plano.normal))
        if self.p.get("ref_cara") and ctx is not None:
            salida.append(self._por_referencias(estado, ctx))
        if not salida:
            raise ErrorOperacion("Elegí dónde van los agujeros (puntos de boceto, un punto sobre una cara o una cara "
                                 "con dos aristas de referencia).")
        return [(p, -d if self.p["invertir"] else d) for p, d in salida]

    def _por_referencias(self, estado, ctx):
        """Posición «Referencias»: el punto de la cara a las dos distancias de las dos aristas."""
        e = _resolver(self.p["ref_cara"], estado, ("cara",))
        if e.plano is None:
            raise ErrorOperacion("La posición por referencias va sobre una cara plana.")
        aristas = _resolver_todas(self.p.get("ref_aristas") or [], estado, ("arista",))
        if len(aristas) != 2:
            raise ErrorOperacion("La posición por referencias necesita dos aristas rectas de la cara.")
        distancias = [ctx.evaluar(self.p["ref_distancia1"]), ctx.evaluar(self.p["ref_distancia2"])]
        punto = _sc().punto_por_referencias(e.forma, [a.forma for a in aristas], distancias)
        return punto, -e.plano.normal

    def _objetivo_hasta(self, estado):
        if not self.p.get("hasta"):
            raise ErrorOperacion("Extensión «Hasta»: elegí la cara, el plano o el cuerpo donde termina el agujero.")
        e = _resolver(self.p["hasta"], estado, ("cara", "plano", "cuerpo"))
        if e.tipo == "plano":
            return e.plano
        return e.forma

    def opciones_herramienta(self, ctx, rapido=False):
        """Argumentos de `herramienta_agujero` (sin la profundidad) según el tipo de rosca. `rapido`: la rosca
        modelada se reemplaza por su agujero liso (vista previa)."""
        p, sc = self.p, _sc()
        A = lambda k: ctx.evaluar(p[k], ANGULO)  # noqa: E731
        L = lambda k: ctx.evaluar(p[k])  # noqa: E731
        opciones = {"tipo": p["tipo"], "punta": p["punta"], "angulo_punta": A("angulo_punta")}
        rosca = p["rosca"]
        if rosca == "modelada":
            datos = sc.datos_rosca(p["designacion"])
            if datos["conica"]:
                raise ErrorOperacion(f"{datos['designacion']} es una rosca cónica: usá «Roscado cónico».")
            clase, _ = _tol().resolver_clase(datos["familia"], datos["diametro"], datos["paso"],
                                             p.get("clase_rosca") or "", True)
            if rapido:
                opciones["diametro"] = sc.diametro_taladro_rosca(p["designacion"], clase, L("holgura_3d"))
            else:
                opciones.update(diametro=L("diametro"), roscado=p["designacion"], clase=clase,
                                holgura=L("holgura_3d"), mano=p.get("mano") or "derecha")
        elif rosca == "holgura":
            opciones["diametro"] = sc.diametro_paso_libre(p["designacion"], p.get("ajuste") or "normal")
        elif rosca == "conico":
            datos = sc.datos_rosca(p["designacion"])
            if not datos["conica"]:
                raise ErrorOperacion(f"Roscado cónico: {datos['designacion']} no es una rosca de tubería cónica "
                                     "(R/Rc o NPT).")
            opciones.update(diametro=datos["diametro_menor"], conicidad=datos["conicidad"])
        else:
            opciones["diametro"] = L("diametro")
        if p["tipo"] == "abocardado":
            opciones.update(diam_abocardado=L("diam_abocardado"), prof_abocardado=L("prof_abocardado"))
        elif p["tipo"] == "avellanado":
            opciones.update(diam_avellanado=L("diam_avellanado"), angulo_avellanado=A("angulo_avellanado"))
        return opciones

    def herramientas(self, estado, ctx, rapido=False):
        """Sólidos a restar, uno por agujero."""
        p, sc = self.p, _sc()
        solidos = [c.forma for c in estado.cuerpos.values() if getattr(c, "tipo", "solido") == "solido"]
        if not solidos:
            raise ErrorOperacion("No hay cuerpos sólidos para agujerear.")
        opciones = self.opciones_herramienta(ctx, rapido)
        todo = geo.compuesto(solidos) if p["extension"] == "todo" else None
        hasta = self._objetivo_hasta(estado) if p["extension"] == "hasta" else None
        herramientas = []
        for punto, direccion in self._colocaciones(estado, ctx):
            if p["extension"] == "todo":
                herramientas.append(sc.agujero(todo, punto, direccion, profundidad=None, **opciones))
            elif p["extension"] == "hasta":
                prof = sc.profundidad_hasta(punto, direccion, hasta, ctx.evaluar(p.get("desfase_hasta") or "0 mm"))
                herramientas.append(sc.herramienta_agujero(punto, direccion, profundidad=prof, **opciones))
            else:
                herramientas.append(sc.herramienta_agujero(punto, direccion, profundidad=ctx.evaluar(p["profundidad"]),
                                                           **opciones))
        return herramientas

    def ejecutar(self, estado, ctx):
        p = self.p
        herramientas = self.herramientas(estado, ctx)
        if p["rosca"] == "cosmetica":
            ctx.aviso(f"Rosca cosmética {p['designacion']}: no cambia la geometría.")
        elif p["rosca"] == "conico":
            ctx.aviso(f"Roscado cónico {p['designacion']}: el agujero se angosta 1:16 desde la boca (diámetro menor "
                      "en el plano de calibre); la rosca es cosmética.")
        elif p["rosca"] == "modelada" and p.get("clase_rosca"):
            datos = _sc().datos_rosca(p["designacion"])
            _, aviso = _tol().resolver_clase(datos["familia"], datos["diametro"], datos["paso"], p["clase_rosca"],
                                             True)
            if aviso:
                ctx.aviso(aviso)
        self._aplicar(estado, ctx, geo.unir_todos(herramientas), "cortar")


class OpRosca(_OpCrear):
    """Rosca de Fusion [GUID-7BD8CD24, GUID-C37E8172]: sobre una cara cilíndrica; tipo (familia: métrica ISO,
    unificada, trapezoidal, ACME, tubería BSP/NPT), tamaño automático o elegido, clase de tolerancia (6g/6H,
    2A/2B…) y holgura para impresión 3D; largo completo o con desfase; cosmética o modelada; mano derecha o
    izquierda."""
    TIPO, ETIQUETA, ICONO = "rosca", "Rosca", "⌇"
    PARAMS = {"caras": [], "designacion": "", "largo_completo": True, "longitud": "10 mm", "desfase": "0 mm",
              "modelada": True, "mano": "derecha", "invertir": False,
              "familia": "iso_metrica", "clase_rosca": "", "holgura_3d": "0 mm"}   # nuevas: «familia» y siguientes
    EXPRESIONES = ("longitud", "desfase", "holgura_3d")
    OPCIONES = {"mano": ("derecha", "izquierda"), "familia": FAMILIAS_ROSCA}
    REFS = ("caras",)

    def ejecutar(self, estado, ctx):
        ents = _resolver_todas(self.p["caras"], estado, ("cara",))
        if not ents:
            raise ErrorOperacion("Elegí las caras cilíndricas a roscar.")
        p, sc = self.p, _sc()
        holgura = ctx.evaluar(p.get("holgura_3d") or "0 mm")
        self.roscas = []                     # lo que quedó en cada cara (designación y clase): para informar
        for e in ents:
            cuerpo = estado.cuerpo(e.cuerpo)
            info = sc.analizar_rosca(cuerpo.forma, e.forma, designacion=p["designacion"] or None,
                                     familia=p.get("familia") or None)
            datos, modelada = info["datos"], p["modelada"]
            if modelada and datos["conica"]:
                ctx.aviso(f"{datos['designacion']} es una rosca cónica: sobre una cara cilíndrica queda cosmética.")
                modelada = False
            clase, aviso = _tol().resolver_clase(datos["familia"], datos["diametro"], datos["paso"],
                                                 p.get("clase_rosca") or "", info["interna"])
            if aviso and modelada:
                ctx.aviso(aviso)
            cuerpo.forma = sc.rosca(cuerpo.forma, e.forma, designacion=datos["designacion"],
                                    longitud=None if p["largo_completo"] else ctx.evaluar(p["longitud"]),
                                    desfase=ctx.evaluar(p["desfase"]), modelada=modelada, mano=p["mano"],
                                    invertir=p["invertir"], clase=clase, holgura=holgura)
            self.roscas.append({"cuerpo": cuerpo.id, "designacion": datos["designacion"], "clase": clase,
                                "interna": info["interna"], "modelada": modelada})
            if not modelada:
                ctx.aviso("Rosca cosmética: la geometría no cambia (como la rosca no modelada de Fusion).")


class OpBobina(_OpCrear):
    """Bobina de Fusion [SLD-COIL-SOLID]: plano/cara + centro, diámetro, tipo (revoluciones y altura,
    revoluciones y paso, altura y paso), ángulo, sección y su posición."""
    TIPO, ETIQUETA, ICONO = "bobina", "Bobina", "➰"
    PARAMS = {"plano": None, "centro": None, "diametro": "20 mm", "tipo": "rev_altura", "revoluciones": "5",
              "altura": "30 mm", "paso": "6 mm", "angulo": "0 deg", "seccion": "circular", "tamano": "3 mm",
              "posicion": "sobre", "horario": False, "operacion": "nuevo", "objetivos": []}
    EXPRESIONES = ("diametro", "revoluciones", "altura", "paso", "angulo", "tamano")
    DATOS = {"rev_altura": ("revoluciones", "altura"), "rev_paso": ("revoluciones", "paso"),
             "altura_paso": ("altura", "paso")}           # tipo → los dos datos que se dan
    OPCIONES = {"tipo": DATOS, "seccion": ("circular", "cuadrada", "triangular_externa", "triangular_interna"),
                "posicion": ("dentro", "sobre", "fuera"), "operacion": OPERACIONES_CUERPO}
    REFS = ("plano", "centro")

    def ejecutar(self, estado, ctx):
        p = self.p
        plano = ent.como_plano(_resolver(p["plano"], estado)) if p["plano"] else geo.Plano("XY")
        centro = ent.como_punto(_resolver(p["centro"], estado)) if p["centro"] else plano.origen
        datos = {"revoluciones": None, "altura": None, "paso": None}
        for k in self.DATOS[p["tipo"]]:
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
    OPCIONES = {"seccion": ("circular", "cuadrada", "triangular"), "operacion": OPERACIONES_CUERPO}
    REFS = ("ruta",)

    def ejecutar(self, estado, ctx):
        _, ruta = _aristas(self.p["ruta"], estado, "la ruta")
        forma = _sc().tuberia(ruta, seccion=self.p["seccion"], tamano=ctx.evaluar(self.p["tamano"]),
                              hueca=self.p["hueca"], espesor=ctx.evaluar(self.p["espesor"]),
                              distancia=ctx.evaluar(self.p["distancia"], "escalar"))
        self._aplicar(estado, ctx, forma)


# Tipos de paso que dejan su herramienta (el sólido que cortan, unen o crean, vía `aplicar_resultado`) y por eso se
# pueden repetir con un patrón de operaciones; también los patrones y multitransformaciones de operaciones. Es la
# lista que muestran los errores (la API y el diálogo la controlan antes de crear el paso).
TIPOS_REPETIBLES = ("extrusion", "revolucion", "agujero", "primitiva", "barrido", "solevacion", "bobina", "tuberia",
                    "relleno_contorno", "solido_envolvente", "patron", "multitransformar")
OBJETOS_PATRON = ("cuerpos", "operaciones")


def _ids_pasos(p):
    pasos = p.get("pasos") or []
    if not isinstance(pasos, (list, tuple)):
        raise ParametroMalFormado(pasos, "tiene que ser una lista de ids de pasos", "pasos")
    return [str(x) for x in pasos if x]


def _xyz(ctx, valores, que):
    """[x, y, z] de números o expresiones (mm) → array de 3 floats."""
    if not isinstance(valores, (list, tuple)) or len(valores) != 3:
        raise ErrorOperacion(f"{que} tiene que ser [x, y, z]: llegó {ent.describir_valor(valores)}.")
    return np.array([ctx.evaluar(v) if isinstance(v, str) else float(v) for v in valores], float)


def _puntos_de(entidad):
    """Puntos 3D de una entidad del patrón en puntos: un boceto entero da sus puntos sueltos (los que no son de
    ninguna curva); lo demás, su punto (punto de boceto, vértice, punto de construcción, centro de una curva)."""
    if entidad.tipo == "boceto":
        b = entidad.boceto.boceto
        en_curvas = {i for c in b.curvas.values() for i in c.puntos()}
        return [entidad.plano.a_3d(pt.x, pt.y) for pid, pt in sorted(b.puntos.items()) if pid not in en_curvas]
    return [ent.como_punto(entidad)]


def repetir_pasos(op, estado, ctx, trsfs):
    """Patrón de operaciones (el de features de Fusion, con cálculo «Idéntico»): la herramienta que dejó cada paso
    de `op.p["pasos"]` (la extrusión que corta, el agujero…) se copia con cada gp_Trsf de `trsfs` (sin el original)
    y se aplica con la MISMA operación (cortar, unir o cuerpo nuevo) a los mismos cuerpos que el paso original.
    Las extensiones no se recalculan por copia: un agujero «Todo» copiado a una zona más gruesa no la atraviesa.
    Devuelve los ids de los cuerpos afectados."""
    pasos = _ids_pasos(op.p)
    if not pasos:
        raise ErrorOperacion("Elegí las operaciones (pasos del timeline) que se repiten.")
    if not trsfs:
        ctx.aviso("El patrón no tiene copias: no cambió nada.")
        return []
    sc, afectados = _sc(), []
    for pid in pasos:
        registros = estado.herramientas.get(pid)
        if not registros:
            raise ErrorOperacion(
                f"El paso «{pid}» no dejó una herramienta que se pueda repetir: tiene que estar antes de este paso, "
                f"activo y sin error, y ser de un tipo que corta, une o crea con una herramienta. Tipos que se pueden "
                f"repetir: {', '.join(TIPOS_REPETIBLES)} (los dos últimos, de operaciones).")
        for forma, operacion, objetivo, tipo in registros:
            if operacion == "intersecar":
                raise ErrorOperacion(f"El paso «{pid}» interseca: repetirlo dejaría solo lo común a todas las copias. "
                                     "Se repiten los pasos que cortan, unen o crean un cuerpo nuevo.")
            copias = [sc.aplicar(forma, t) for t in trsfs]
            if operacion == "nuevo":              # cada copia, su propio cuerpo (aunque se toquen)
                for copia in copias:
                    afectados += aplicar_resultado(estado, ctx, op.id, copia, operacion, objetivo, tipo)
                continue
            herramienta = sc.unir_instancias(copias) if tipo == "solido" else geo.compuesto(copias)
            afectados += aplicar_resultado(estado, ctx, op.id, herramienta, operacion, objetivo, tipo)
    return afectados


def copiar_cuerpos(op, estado, trsfs):
    """Copias de los cuerpos de `op.p["cuerpos"]` con cada gp_Trsf de `trsfs`: cuerpos nuevos (heredan aspecto y
    material) o, con `combinar`, unidas al original."""
    for cid in op.p["cuerpos"]:
        c = estado.cuerpo(cid)
        copias = [_sc().aplicar(c.forma, t) for t in trsfs]
        if op.p["combinar"]:
            c.forma = geo.unir_todos([c.forma] + copias)
        else:
            for forma in copias:
                estado.nuevo_cuerpo(op.id, forma, c.tipo, **atributos_copia(c))


class OpPatron(_OpCrear):
    """Patrón rectangular, circular, en ruta o en puntos de Fusion [SLD-PATTERNS] (el «en puntos» es el Point Pattern
    de FreeCAD; el giro en ruta, su Twisted Path Array).
    `objeto` es el «Tipo de objeto» de Fusion: "cuerpos" (`cuerpos`: cada instancia es un cuerpo nuevo, o se une al
    original con «Combinar») u "operaciones" (`pasos`: ids de pasos anteriores —una extrusión que corta, un
    agujero…—; su herramienta se repite transformada y se aplica con la misma operación a los mismos cuerpos: ver
    `repetir_pasos`).
    `distribucion` es el «Tipo de distancia» de Fusion: con "extension" (por defecto) d1/d2 son la distancia TOTAL
    entre la primera y la última instancia y, en el circular, `angulo` es el ángulo total; con "espaciado" son la
    separación (o el ángulo) entre instancias consecutivas.
    En ruta, `giro` hace girar cada copia alrededor de la ruta, progresivo hasta ese ángulo total en la última.
    En puntos: `puntos` (puntos de boceto, vértices, puntos de construcción o un boceto entero = sus puntos sueltos)
    y `coordenadas` ([x, y, z], números o expresiones); cada copia lleva el punto de referencia (`referencia`, o
    `referencia_xyz` [x, y, z]; por defecto el origen) a uno de los puntos."""
    TIPO, ETIQUETA, ICONO = "patron", "Patrón", "⁂"
    PARAMS = {"forma_patron": "rectangular", "cuerpos": [], "dir1": None, "n1": 3, "d1": "30 mm", "dir2": None,
              "n2": 1, "d2": "30 mm", "distribucion": "extension", "simetrico": False, "eje": None, "n": 6,
              "angulo": "360 deg", "ruta": [], "orientacion": "identica", "inicio": "0", "suprimir": [],
              "combinar": False, "giro": "0 deg", "puntos": [], "coordenadas": [], "referencia": None,
              "referencia_xyz": [], "objeto": "cuerpos", "pasos": []}
    EXPRESIONES = ("d1", "d2", "angulo", "inicio", "giro")
    OPCIONES = {"forma_patron": ("rectangular", "circular", "ruta", "puntos"), "distribucion": ("extension", "espaciado"),
                "orientacion": ("identica", "direccion_ruta"), "objeto": OBJETOS_PATRON}
    REFS = ("dir1", "dir2", "eje", "ruta", "puntos", "referencia")

    def dependencias(self):
        try:
            pasos = set(_ids_pasos(self.p))
        except ErrorOperacion:
            pasos = set()
        return (super().dependencias() | pasos) - {self.id}

    def pasos_repetidos(self):
        """Pasos cuya herramienta repite (objeto = "operaciones"); [] con cuerpos."""
        try:
            return _ids_pasos(self.p) if self.p.get("objeto") == "operaciones" else []
        except ErrorOperacion:
            return []

    def expresiones(self):
        xyz = list(self.p.get("coordenadas") or []) + [self.p.get("referencia_xyz") or []]
        return super().expresiones() + [v for c in xyz if isinstance(c, (list, tuple)) for v in c if isinstance(v, str)]

    def puntos_patron(self, estado, ctx):
        """(puntos, referencia) del patrón en puntos, en 3D."""
        p = self.p
        coordenadas = p.get("coordenadas") or []
        if not isinstance(coordenadas, (list, tuple)):
            raise ParametroMalFormado(coordenadas, "tiene que ser una lista de [x, y, z]", "coordenadas")
        puntos = [q for e in _resolver_todas(p.get("puntos"), estado) for q in _puntos_de(e)]
        puntos += [_xyz(ctx, c, "Cada coordenada") for c in coordenadas]
        if not puntos:
            raise ErrorOperacion("Elegí los puntos del patrón (puntos de boceto, vértices, puntos de construcción, un "
                                 "boceto con puntos sueltos o coordenadas [x, y, z]).")
        if p.get("referencia"):
            ref = ent.como_punto(_resolver(p["referencia"], estado))
        elif p.get("referencia_xyz"):
            ref = _xyz(ctx, p["referencia_xyz"], "«referencia_xyz»")
        else:
            ref = np.zeros(3)
        return puntos, ref

    def aclaracion_distancias(self):
        """Frase que dice cómo se leen las distancias (o el ángulo) con la `distribucion` actual."""
        forma = self.p["forma_patron"]
        campo = {"circular": "angulo", "ruta": "d1"}.get(forma, "d1/d2")
        if self.p["distribucion"] == "espaciado":
            return f"{campo} es la separación entre instancias consecutivas (distribucion = \"espaciado\")."
        return (f"{campo} es la distancia TOTAL entre la primera y la última instancia (distribucion = \"extension\", "
                "como «Extensión» de Fusion); para dar la separación entre instancias usá distribucion = \"espaciado\".")

    def transformaciones(self, estado, ctx):
        p, sc = self.p, _sc()
        try:
            sup = tuple(int(i) for i in p.get("suprimir") or [])
        except (TypeError, ValueError):
            raise ErrorOperacion(f"«suprimir» tiene que ser una lista de números enteros (índices de copia): llegó "
                                 f"{ent.describir_valor(p.get('suprimir'))}.") from None
        if p["forma_patron"] == "rectangular":
            if not p["dir1"]:
                raise ErrorOperacion("Elegí la dirección 1.")
            d1 = ent.direccion(_resolver(p["dir1"], estado))
            d2 = ent.direccion(_resolver(p["dir2"], estado)) if p["dir2"] else None
            return sc.transformaciones_rectangulares(d1, self.entero("n1"), ctx.evaluar(p["d1"]), d2, self.entero("n2") if d2 is not None else 1,
                                                     ctx.evaluar(p["d2"]), distribucion=p["distribucion"],
                                                     simetrico1=p["simetrico"], simetrico2=p["simetrico"], suprimir=sup)
        if p["forma_patron"] == "circular":
            if not p["eje"]:
                raise ErrorOperacion("Elegí el eje.")
            punto, eje = ent.como_eje(_resolver(p["eje"], estado))
            return sc.transformaciones_circulares(punto, eje, self.entero("n"),
                                                  angulo_total=ctx.evaluar(p["angulo"], ANGULO),
                                                  distribucion="completa" if p["distribucion"] == "extension"
                                                  else "espaciado", simetrico=p["simetrico"], suprimir=sup)
        if p["forma_patron"] == "puntos":
            puntos, ref = self.puntos_patron(estado, ctx)
            return sc.transformaciones_en_puntos(puntos, ref, suprimir=sup)
        _, ruta = _aristas(p["ruta"], estado, "la ruta")
        return sc.transformaciones_en_ruta(ruta, self.entero("n1"), ctx.evaluar(p["d1"]), orientacion=p["orientacion"],
                                           inicio=ctx.evaluar(p["inicio"], "escalar"), distribucion=p["distribucion"],
                                           simetrico=p["simetrico"], suprimir=sup,
                                           giro=ctx.evaluar(p.get("giro") or "0", ANGULO))

    def ejecutar(self, estado, ctx):
        _ejecutar_patron(self, estado, ctx, "Elegí los cuerpos del patrón.")


def _ejecutar_patron(op, estado, ctx, sin_cuerpos):
    """`ejecutar` común del Patrón y la Multitransformación: repite pasos o copia cuerpos."""
    if op.p.get("objeto", "cuerpos") == "operaciones":
        if not _ids_pasos(op.p):
            raise ErrorOperacion("Elegí las operaciones (pasos del timeline) que se repiten.")
        op._registrar_usados(repetir_pasos(op, estado, ctx, op.transformaciones(estado, ctx)[1:]))
        return
    if not op.p["cuerpos"]:
        raise ErrorOperacion(sin_cuerpos)
    copiar_cuerpos(op, estado, op.transformaciones(estado, ctx)[1:])          # la primera es el original


TIPOS_TRANSFORMACION = ("rectangular", "circular", "ruta", "puntos", "simetria")


class OpMultitransformar(_OpCrear):
    """Multitransformación (PartDesign › MultiTransform de FreeCAD; en Fusion se encadenan patrones y simetrías):
    una lista de transformaciones apilables en un solo paso. Cada una se aplica a TODAS las instancias que dejaron
    las anteriores: patrón rectangular de 3 + simetría = 6 instancias.

    `transformaciones`: lista de dicts con "tipo" ("rectangular", "circular", "ruta", "puntos" o "simetria") y los
    campos de ese tipo con las mismas claves que el Patrón (dir1, n1, d1, dir2, n2, d2, distribucion, simetrico,
    eje, n, angulo, ruta, orientacion, inicio, giro, puntos, coordenadas, referencia, referencia_xyz, suprimir) o,
    en la simetría, "plano". `objeto`, `cuerpos`, `pasos` y `combinar`, como en el Patrón."""
    TIPO, ETIQUETA, ICONO = "multitransformar", "Multitransformación", "✣"
    PARAMS = {"objeto": "cuerpos", "cuerpos": [], "pasos": [], "transformaciones": [], "combinar": False}
    OPCIONES = {"objeto": OBJETOS_PATRON}

    def _lista(self):
        lista = self.p.get("transformaciones") or []
        if not isinstance(lista, (list, tuple)) or not all(isinstance(t, dict) for t in lista):
            raise ParametroMalFormado(lista, 'se esperaba una lista de dicts como {"tipo": "rectangular", …}',
                                      "transformaciones")
        return list(lista)

    def _patron(self, t):
        return OpPatron(self.id, forma_patron=t.get("tipo"), **{k: v for k, v in t.items() if k != "tipo"})

    def dependencias(self):
        deps = super().dependencias()
        try:
            lista, pasos = self._lista(), set(_ids_pasos(self.p))
        except ErrorOperacion:
            return deps
        for t in lista:
            deps |= ent.dependencias_de(*(t.get(k) for k in OpPatron.REFS + ("plano",)))
        return (deps | pasos) - {self.id}

    pasos_repetidos = OpPatron.pasos_repetidos

    def expresiones(self):
        try:
            lista = self._lista()
        except ErrorOperacion:
            return []
        return [e for t in lista if t.get("tipo") in TIPOS_TRANSFORMACION and t.get("tipo") != "simetria"
                for e in self._patron(t).expresiones()]

    def transformaciones(self, estado, ctx):
        """Lista compuesta de gp_Trsf (la primera, la identidad = el original)."""
        lista = self._lista()
        if not lista:
            raise ErrorOperacion("Agregá al menos una transformación (rectangular, circular, ruta, puntos o simetria).")
        from OCP.gp import gp_Trsf
        sc, listas = _sc(), []
        for i, t in enumerate(lista, start=1):
            tipo = t.get("tipo")
            if tipo not in TIPOS_TRANSFORMACION:
                raise ErrorOperacion(f"Transformación {i}: «tipo» tiene que ser uno de: {', '.join(TIPOS_TRANSFORMACION)}; "
                                     f"llegó {ent.describir_valor(tipo)}.")
            try:
                if tipo == "simetria":
                    if not t.get("plano"):
                        raise ErrorOperacion("elegí el plano de simetría.")
                    plano = ent.como_plano(_resolver(t["plano"], estado))
                    listas.append([gp_Trsf(), sc.transformacion_simetria(plano)])
                    continue
                patron = self._patron(t)
                patron.revisar_parametros()
                patron.validar_opciones()
                listas.append(patron.transformaciones(estado, ctx))
            except ParametroMalFormado:
                raise
            except (ErrorOperacion, ent.ErrorReferencia, geo.ErrorGeometria) as e:
                raise ErrorOperacion(f"Transformación {i} ({tipo}): {e}") from e
        return sc.componer_transformaciones(listas)

    def ejecutar(self, estado, ctx):
        _ejecutar_patron(self, estado, ctx, "Elegí los cuerpos de la multitransformación.")


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
                estado.nuevo_cuerpo(self.id, reflejo, c.tipo, **atributos_copia(c))


class OpRellenoContorno(_OpCrear):
    """Relleno de contorno de Fusion [GUID-575E005F]: las herramientas (cuerpos, caras, planos) forman celdas
    cerradas y las elegidas pasan a ser sólido.

    `herramientas`: lista de referencias: cuerpo {"tipo": "cuerpo", "cuerpo": "op1.c1"}, plano {"tipo": "plano",
    "id": "XY"} (o el id de un plano de construcción) o cara {"tipo": "cara", "cuerpo": …, "firma": …} (copiada de
    find_faces). `celdas`: índices de las regiones cerradas, ordenadas por centroide (x, y, z); [] = la celda 0.
    `operacion`: nuevo/unir/cortar/intersecar; `objetivos`: ids de los cuerpos a unir, cortar o intersecar."""
    TIPO, ETIQUETA, ICONO = "relleno_contorno", "Relleno de contorno", "▩"
    PARAMS = {"herramientas": [], "celdas": [], "operacion": "nuevo", "objetivos": []}
    OPCIONES = {"operacion": OPERACIONES_CUERPO}
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
    OPCIONES = {"tipo": ("caja", "cilindro"), "operacion": OPERACIONES_CUERPO}   # eje: "x", "y", "z" o un vector

    def ejecutar(self, estado, ctx):
        if not self.p["cuerpos"]:
            raise ErrorOperacion("Elegí los cuerpos.")
        formas = [estado.cuerpo(c).forma for c in self.p["cuerpos"]]
        forma = _sc().solido_envolvente(formas, tipo=self.p["tipo"], margen=ctx.evaluar(self.p["margen"]),
                                        eje=self.p["eje"])
        self._aplicar(estado, ctx, forma)


class OpSaliente(_OpCrear):
    """Saliente (Boss) de PLÁSTICO [SLD-BOSS], simplificado: columna con agujero que nace en un punto.

    `sentido` (hacia dónde crece, sobre la normal del plano del boceto): "auto" (como Fusion) = hacia afuera del
    material si el punto está sobre una cara del cuerpo, y hacia el cuerpo si está en el aire; "plano" = siempre
    −normal del plano (el cálculo de las recetas guardadas antes del automático, ver `migrar_receta`).
    `invertir` (Flip) da vuelta el sentido elegido."""
    TIPO, ETIQUETA, ICONO = "saliente", "Saliente", "⌾"
    PARAMS = {"posiciones": [], "diametro_exterior": "8 mm", "diametro_agujero": "3 mm", "altura": "",
              "profundidad_agujero": "", "angulo_desmoldeo": "0 deg", "invertir": False, "sentido": "auto"}
    EXPRESIONES = ("diametro_exterior", "diametro_agujero", "angulo_desmoldeo")
    OPCIONES = {"sentido": ("auto", "plano")}
    REFS = ("posiciones",)

    @staticmethod
    def migrar_receta(d):
        """Un saliente guardado sin «sentido» (antes del automático) conserva el cálculo de antes: "plano"."""
        params = d.get("params", {})
        if isinstance(params, dict) and "sentido" not in params:
            d = dict(d, params=dict(params, sentido="plano"))
        return d

    def ejecutar(self, estado, ctx):
        ents = _resolver_todas(self.p["posiciones"], estado)
        if not ents:
            raise ErrorOperacion("Elegí puntos de boceto donde van los salientes.")
        L = lambda k: ctx.evaluar(self.p[k]) if str(self.p.get(k) or "").strip() else None  # noqa: E731
        for e in ents:
            n = e.plano.normal if e.plano is not None else np.array([0.0, 0.0, 1.0])
            cuerpo = _cuerpo_objetivo(estado, [e] if e.forma is not None else
                                      [ent.Entidad("punto", forma=_vertice(ent.como_punto(e)))], self.p)
            d = _sentido_saliente(cuerpo.forma, ent.como_punto(e), n) if self.p["sentido"] == "auto" else -n
            if self.p["invertir"]:
                d = -d
            cuerpo.forma = _sc().saliente(cuerpo.forma, ent.como_punto(e), d, diametro_exterior=L("diametro_exterior"),
                                          diametro_agujero=L("diametro_agujero"), altura=L("altura"),
                                          profundidad_agujero=L("profundidad_agujero"),
                                          angulo_desmoldeo=ctx.evaluar(self.p["angulo_desmoldeo"], ANGULO))
            self._registrar_usados([cuerpo.id])


def _sentido_saliente(forma, punto, normal):
    """Sentido automático del saliente sobre `normal`: si `punto` está sobre una cara de `forma` (material de un
    solo lado), hacia afuera del material; si está en el aire (o dentro), hacia el cuerpo: +normal cuando el cuerpo
    entero queda de ese lado y −normal si no (lo de antes)."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN
    from OCP.gp import gp_Pnt
    n = np.asarray(normal, float) / np.linalg.norm(normal)
    p = np.asarray(punto, float)
    solidos = geo.solidos(forma) or [forma]

    def dentro(q):
        return any(BRepClass3d_SolidClassifier(s, gp_Pnt(*map(float, q)), 1e-7).State() == TopAbs_IN
                   for s in solidos)

    arriba, abajo = dentro(p + 1e-3 * n), dentro(p - 1e-3 * n)
    if arriba != abajo:
        return -n if arriba else n
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(forma)
    esquinas = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
    return n if float(((esquinas - p) @ n).min()) >= -1e-6 else -n


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
    OPCIONES = {"tipo": ("labio", "ranura")}
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
registrar_operacion(OpMultitransformar)
